"""tests/test_routes_badge_workflow.py — V2 端点端到端测试 (FastAPI TestClient)

覆盖:
- POST /api/badge/draft (建草稿, 校验, 必填字段)
- GET /api/badge/draft/{id} (读草稿, 404)
- POST /api/badge/commit-from-draft (写三表, 状态机, stat_logic 默认值)
- GET /api/badge/discoveries (扫待确认)
- POST /api/badge/draft/{id}/image (回传成品图; 鉴权 401/200, 见 TestUploadDraftImageAuth)

V2 设计:
- Pydantic BaseModel 收 body (替代 V1 错法 request.scope.get("body"))
- stat_logic V2 meta 没收集, commit handler 默认 "无" (跟 V1 insert_achievement_row 兼容)
- 老端点沿用前端 localStorage PIN (不做 server-side PIN check) —— 例外: 回传成品图端点
  会写盘 + 传 COS, P0b audit (2026-10-13) 起**默认拒绝**, 必须带 dad 凭据或 push token。
"""
import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from src.kid_app.app import app
from src.kid_app import badge_db, badge_draft, badge_discovery
from src.database import db


@pytest.fixture
def tmp_badge_data(monkeypatch, tmp_path):
    """重定向 lib/badge_data/ 到临时目录, 跟生产隔离."""
    data_dir = tmp_path / "badge_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(badge_draft, "_badge_data_dir", lambda: data_dir)
    # _tmp_dir 同步
    monkeypatch.setattr(badge_draft, "_tmp_dir", lambda: data_dir / ".tmp")
    return data_dir


@pytest.fixture
def client():
    return TestClient(app)


def _make_valid_meta(id_suffix="curl_xyz"):
    return {
        "id": f"v2_test_{id_suffix}",
        "name": "测试徽章",
        "type": "突破",
        "category": "milestone",
        "display_format": "days",
        "placeholder": "A cute chibi girl with bamboo flute",
        "zh_story": "孔子闻韶",
        "cond_text": "测试条件文案 (V2.2.1 必填)",  # V2.2.1 (2026-06-15) 必填
    }


def _make_awaiting_draft(badge_data_dir, meta=None, version=1):
    """helper: 写一个 status=draft_awaiting_confirm + 临时图 + version 的 draft."""
    meta = meta or _make_valid_meta("pending_xyz")
    d = badge_draft.create_draft(meta)
    badge_draft.save_draft(d)
    # 写临时图 (commit-from-draft 会 move 到 static/)
    (badge_data_dir / ".tmp").mkdir(exist_ok=True)
    tmp_png = badge_draft.tmp_path_for(d.draft_id, version)
    tmp_png.write_bytes(b"fake png content")
    badge_draft.update_draft_image(d.draft_id, {
        "path": str(tmp_png),
        "model": "gpt-image-2",
        "alpha_verified": True,
        "version": version,
    })
    return d


# ─── TestPostDraft ──────────────────────────────────────────────

class TestPostDraft:
    def test_happy_path(self, client, tmp_badge_data):
        meta = _make_valid_meta("post_happy_xyz")
        r = client.post("/config/api/badge/draft", json={"meta": meta})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "draft_id" in data
        assert data["json"]
        assert "file_contract_path" in data
        assert data["file_contract_path"].endswith(f"{data['draft_id']}.json")
        parsed = json.loads(data["json"])
        assert parsed["meta"] == meta
        assert parsed["schema_version"] == 1
        assert parsed["status"] == "draft_created"

    def test_disk_verification_failure_returns_500(self, client, monkeypatch, tmp_badge_data):
        """Sprint 26090902: 模拟落盘后 get_draft 查空, 接口应返 500."""
        from src.kid_app import badge_draft
        meta = _make_valid_meta("post_fail_disk_xyz")
        monkeypatch.setattr(badge_draft, "get_draft", lambda did: None)
        r = client.post("/config/api/badge/draft", json={"meta": meta})
        assert r.status_code == 500
        assert "草稿落盘失败" in r.json()["error"]

    def test_missing_meta(self, client, tmp_badge_data):
        """Pydantic 校验: 没 meta 字段返 422 (Pydantic BaseModel 自动校验)."""
        r = client.post("/config/api/badge/draft", json={})
        # Pydantic 返 422 (Unprocessable Entity) 因为 meta 必填
        assert r.status_code == 422

    def test_empty_meta(self, client, tmp_badge_data):
        """meta={} 应 400 (空 dict 走我自己代码 not req.meta 校验)."""
        r = client.post("/config/api/badge/draft", json={"meta": {}})
        # meta={} 不是 None, 走我们自己代码 `if not req.meta` (dict 空 falsy) 返 400
        assert r.status_code == 400
        assert "缺 meta 字段" in r.json()["error"]

    def test_missing_required_field(self, client, tmp_badge_data):
        """缺 placeholder 应 400 (create_draft 校验)."""
        meta = _make_valid_meta("post_no_ph_xyz")
        del meta["placeholder"]
        r = client.post("/config/api/badge/draft", json={"meta": meta})
        assert r.status_code == 400
        assert "缺必填字段" in r.json()["error"]

    def test_invalid_id_format(self, client, tmp_badge_data):
        meta = _make_valid_meta("post_bad_id!")
        r = client.post("/config/api/badge/draft", json={"meta": meta})
        assert r.status_code == 400
        assert "格式不对" in r.json()["error"]

    def test_seasonal_requires_seasonal_type(self, client, tmp_badge_data):
        meta = _make_valid_meta("post_seasonal_xyz")
        meta["category"] = "seasonal"
        r = client.post("/config/api/badge/draft", json={"meta": meta})
        assert r.status_code == 400
        assert "seasonal_type" in r.json()["error"]


# ─── TestGetDraft ───────────────────────────────────────────────

class TestGetDraft:
    def test_happy_path(self, client, tmp_badge_data):
        meta = _make_valid_meta("get_happy_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        r = client.get(f"/config/api/badge/draft/{d.draft_id}")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert r.json()["draft"]["draft_id"] == d.draft_id

    def test_not_found(self, client, tmp_badge_data):
        r = client.get("/config/api/badge/draft/2026-06-12_xxx_abcdef")
        assert r.status_code == 404
        assert "不存在" in r.json()["error"]

    def test_invalid_format(self, client, tmp_badge_data):
        r = client.get("/config/api/badge/draft/not_a_valid_id")
        assert r.status_code == 404
        assert "不存在" in r.json()["error"]


# ─── TestCommitFromDraft (含 V2 stat_logic 默认值 bug 复现) ───────

class TestCommitFromDraft:
    def test_happy_path_writes_three_tables(self, client, tmp_badge_data):
        """端到端: 建草稿 → image → commit → DB 三表都写."""
        # 用 unique id (避免跟 V1 老 badge 冲突)
        meta = _make_valid_meta("commit_happy_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        # 模拟 skill 写 image + 临时图
        (tmp_badge_data / ".tmp").mkdir(exist_ok=True)
        tmp_png = badge_draft.tmp_path_for(d.draft_id, 1)
        import io
        from PIL import Image
        _png = io.BytesIO()
        Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(_png, format="PNG")
        tmp_png.write_bytes(_png.getvalue())
        badge_draft.update_draft_image(d.draft_id, {
            "path": str(tmp_png), "model": "gpt-image-2",
            "alpha_verified": True, "version": 1,
        })

        r = client.post("/config/api/badge/commit-from-draft",
                       json={"draft_id": d.draft_id})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["badge_id"] == "v2_test_commit_happy_xyz"
        assert data["image_url"] == "/static/badges/v2_test_commit_happy_xyz_v1.png"
        assert "prod_visibility" in data
        pv = data["prod_visibility"]
        assert pv["deployed"] is False
        assert pv["db_written"] is True
        assert pv["image_on"] == "local_static_only"
        assert len(pv["needs"]) == 5
        assert "thumbs/v2_test_commit_happy_xyz_v1.webp" in pv["needs"][1]
        assert "full/v2_test_commit_happy_xyz_v1.webp" in pv["needs"][2]
        assert "hint" in pv

        # 验证 DB 三表 (用 badge_write_tx context manager 跟 V1 一致)
        with badge_db.badge_write_tx() as conn:
            ach = conn.execute(
                "SELECT id, name, type, category, stat_logic FROM achievements WHERE id=?",
                ("v2_test_commit_happy_xyz",)
            ).fetchone()
            assert ach is not None
            assert ach[0] == "v2_test_commit_happy_xyz"
            assert ach[1] == "测试徽章"
            # V2 meta 没 stat_logic, V2.1 commit handler 默认空字符串 (Bug #4 修法, 2026-06-15)
            assert ach[4] == ""

            stats = conn.execute(
                "SELECT achievement_id, achieved FROM achievement_stats WHERE achievement_id=?",
                ("v2_test_commit_happy_xyz",)
            ).fetchone()
            assert stats is not None
            assert stats[1] == "N"

            badges = conn.execute(
                "SELECT achievement_id, url, version, is_current FROM achievement_badges WHERE achievement_id=?",
                ("v2_test_commit_happy_xyz",)
            ).fetchone()
            assert badges is not None
            assert badges[1] == "/static/badges/v2_test_commit_happy_xyz_v1.png"
            assert badges[2] == 1
            assert badges[3] == 1

        # 验证 draft 状态变 committed
        d2 = badge_draft.get_draft(d.draft_id)
        assert d2 is not None
        assert d2.status == "committed"
        assert d2.history[-1]["event"] == "user_confirmed"
        assert d2.history[-1]["badge_id"] == "v2_test_commit_happy_xyz"

        # 清理测试数据 (DB + 静态文件)
        with badge_db.badge_write_tx() as conn:
            conn.execute("DELETE FROM achievements WHERE id=?", ("v2_test_commit_happy_xyz",))
            conn.execute("DELETE FROM achievement_stats WHERE achievement_id=?", ("v2_test_commit_happy_xyz",))
            conn.execute("DELETE FROM achievement_badges WHERE achievement_id=?", ("v2_test_commit_happy_xyz",))
        # static PNG + 两档 webp (commit_image_from_draft 写在仓库 static/badges/)
        static_dir = Path(badge_draft.__file__).resolve().parent / "static" / "badges"
        stem = "v2_test_commit_happy_xyz_v1"
        for extra in (
            static_dir / f"{stem}.png",
            static_dir / "thumbs" / f"{stem}.webp",
            static_dir / "full" / f"{stem}.webp",
        ):
            if extra.exists():
                extra.unlink()

    def test_status_must_be_awaiting(self, client, tmp_badge_data):
        """status=draft_created commit 应 400."""
        meta = _make_valid_meta("commit_status_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        # 没 update_draft_image (status 仍 draft_created)
        r = client.post("/config/api/badge/commit-from-draft",
                       json={"draft_id": d.draft_id})
        assert r.status_code == 400
        assert "draft 状态" in r.json()["error"]
        assert "draft_awaiting_confirm" in r.json()["error"]

    def test_missing_image(self, client, tmp_badge_data):
        """status=awaiting_confirm 但 image=None (异常状态) 应 400."""
        meta = _make_valid_meta("commit_no_img_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        # 强制标 awaiting_confirm 但 image 仍 None
        d.status = "draft_awaiting_confirm"
        badge_draft.save_draft(d)
        r = client.post("/config/api/badge/commit-from-draft",
                       json={"draft_id": d.draft_id})
        assert r.status_code == 400
        assert "image 字段" in r.json()["error"]

    def test_draft_not_found(self, client, tmp_badge_data):
        r = client.post("/config/api/badge/commit-from-draft",
                       json={"draft_id": "2026-06-12_xxx_abc999"})
        assert r.status_code == 404

    def test_db_conflict_returns_409(self, client, tmp_badge_data):
        """DB 已有同 id 应 409 (防止重复 commit)."""
        meta = _make_valid_meta("commit_dup_xyz")
        # 直接 SQL 插一条 achievements 制造冲突 (用 badge_write_tx context manager)
        with badge_db.badge_write_tx() as conn:
            conn.execute(
                "INSERT INTO achievements (id, name, type, category, stat_logic, description, display_format) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("v2_test_commit_dup_xyz", "预存", "突破", "milestone", "无", "test", "days"),
            )
        d = _make_awaiting_draft(tmp_badge_data, meta=meta)
        try:
            r = client.post("/config/api/badge/commit-from-draft",
                           json={"draft_id": d.draft_id})
            assert r.status_code == 409
            assert "DB 已有" in r.json()["error"]
        finally:
            # 清理
            with badge_db.badge_write_tx() as conn:
                conn.execute("DELETE FROM achievements WHERE id=?", ("v2_test_commit_dup_xyz",))
            badge_draft.delete_draft(d.draft_id)
            badge_draft.cleanup_tmp(d.draft_id, 1)
            project_root = Path(tmp_badge_data).resolve().parent.parent.parent.parent
            static_png = project_root / "src" / "kid_app" / "static" / "badges" / "v2_test_commit_dup_xyz_v1.png"
            if static_png.exists():
                static_png.unlink()


# ─── TestDiscoveries (返 [pending] + image_url web 路径) ─────

class TestDiscoveries:
    def test_empty(self, client, tmp_badge_data):
        r = client.get("/config/api/badge/discoveries")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert r.json()["data"] == []
        assert r.json()["count"] == 0

    def test_with_pending_image_url_web_path(self, client, tmp_badge_data):
        """端到端: 1 个 pending draft, image_url 走 draft-image 端点 (V2.6 修).

        V2.6 (2026-06-30) 修: 待确认状态时 .tmp/ 图真实存在,
        /static/badges/{id}_v{n}.png 拼接路径 404, fallback 到
        /config/api/badge/draft-image?draft_id=... 端点 (FileResponse).
        """
        meta = _make_valid_meta("disc_xyz")
        d = _make_awaiting_draft(tmp_badge_data, meta=meta)
        r = client.get("/config/api/badge/discoveries")
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data) == 1
        item = data[0]
        # V2.6: image_url 走 draft-image 端点 (tmp_badge_data fixture 里
        # src/kid_app/static/badges/ 不存在, 所以不命中 commit-static-path 分支)
        assert item["image_url"] == f"/config/api/badge/draft-image?draft_id={d.draft_id}"
        assert item["is_committable"] is True
        assert item["db_status"] == "not_exists"
        # 清理
        badge_draft.delete_draft(d.draft_id)
        badge_draft.cleanup_tmp(d.draft_id, 1)

    def test_skips_draft_created(self, client, tmp_badge_data):
        """status=draft_created 不入选 (没 awaiting_confirm)."""
        meta = _make_valid_meta("disc_skip_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        r = client.get("/config/api/badge/discoveries")
        assert r.json()["data"] == []


# ─── TestDraftImage (V2.6 待确认列表预览图端点) ─────────────

class TestDraftImage:
    """V2.6 (2026-06-30): GET /api/badge/draft-image 端点.

    修待确认 badge 列表预览图 404 现象:
    之前 discovery 返 /static/badges/{id}_v{n}.png, 但 commit 前
    .tmp/ 图不在 static mount 下, 前端 fetch 永远 404.

    新端点: 走 FileResponse 返 .tmp/ 真图, discovery fallback 链上.
    """

    def test_happy_path_returns_png(self, client, tmp_badge_data):
        """待确认 draft + 临时图 → 200 + image/png + 真图字节."""
        meta = _make_valid_meta("dimg_xyz")
        d = _make_awaiting_draft(tmp_badge_data, meta=meta)
        r = client.get(f"/config/api/badge/draft-image?draft_id={d.draft_id}")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        # _make_awaiting_draft 写的是 b"fake png content"
        assert r.content == b"fake png content"
        # 清理
        badge_draft.delete_draft(d.draft_id)
        badge_draft.cleanup_tmp(d.draft_id, 1)

    def test_path_traversal_blocked(self, client, tmp_badge_data):
        """?draft_id=../etc/passwd → 400 (字符白名单拦截)."""
        r = client.get("/config/api/badge/draft-image?draft_id=../etc/passwd")
        assert r.status_code == 400
        assert "draft_id 非法" in r.json()["error"]

    def test_slash_in_id_blocked(self, client, tmp_badge_data):
        """?draft_id=foo/bar → 400 (slash 不在白名单)."""
        r = client.get("/config/api/badge/draft-image?draft_id=foo/bar")
        assert r.status_code == 400
        assert "draft_id 非法" in r.json()["error"]

    def test_nonexistent_draft_404(self, client, tmp_badge_data):
        """?draft_id=does_not_exist_xxx → 404."""
        r = client.get("/config/api/badge/draft-image?draft_id=does_not_exist_xxx")
        assert r.status_code == 404
        assert "draft 不存在" in r.json()["error"]

    def test_draft_without_image_404(self, client, tmp_badge_data):
        """draft 存在但没 image 字段 → 404."""
        meta = _make_valid_meta("dimg_noimg_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        # 不调 update_draft_image, 留空
        r = client.get(f"/config/api/badge/draft-image?draft_id={d.draft_id}")
        assert r.status_code == 404
        assert "还没 image" in r.json()["error"]
        # 清理
        badge_draft.delete_draft(d.draft_id)

    def test_image_path_outside_data_dir_blocked(self, client, tmp_badge_data):
        """恶意 image.path 指向项目外 → 400 (relative_to 防御)."""
        meta = _make_valid_meta("dimg_evil_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        # 手动写 image.path 指向 /etc/passwd
        badge_draft.update_draft_image(d.draft_id, {
            "path": "/etc/passwd",
            "model": "evil",
            "version": 1,
        })
        r = client.get(f"/config/api/badge/draft-image?draft_id={d.draft_id}")
        assert r.status_code == 400
        assert "越界" in r.json()["error"]
        # 清理
        badge_draft.delete_draft(d.draft_id)


# ─── TestUploadDraftImageAuth ───────────────────────────────────
# P0b audit (2026-10-13): POST /config/api/badge/draft/{id}/image 在 /config/api/ 公开
# 白名单里 ⇒ 匿名可写盘 + 触发 COS 计费面。改成显式默认拒绝, 两条通道:
#   ① 机器: X-Badge-Push-Token == env BADGE_PUSH_TOKEN (env 未设 = 通道关闭)
#   ② dad 守门: X-Dad-Pin header / dad 会话 / pin_ok cookie (复用 config_users._check_dad_or_401)


def _rgba_png(size=(1024, 1024), color=(255, 0, 255, 255)) -> bytes:
    """真 1024×1024 RGBA PNG (端点有尺寸/模式硬校验, 不能用假字节)."""
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _push_image(client, draft_id, png: bytes = None, headers: dict = None):
    return client.post(
        f"/config/api/badge/draft/{draft_id}/image",
        files={"file": ("badge.png", png or _rgba_png(), "image/png")},
        headers=headers or {},
    )


class TestUploadDraftImageAuth:
    def test_no_credentials_401(self, client, tmp_badge_data, monkeypatch):
        """① 无 cookie / 无 token → 401, 且**没写盘** (临时图保持原样)."""
        monkeypatch.delenv("BADGE_PUSH_TOKEN", raising=False)
        monkeypatch.setenv("BADGE_STORE", "LOCAL")
        d = _make_awaiting_draft(tmp_badge_data)
        tmp_png = badge_draft.tmp_path_for(d.draft_id, 1)

        r = _push_image(client, d.draft_id)
        assert r.status_code == 401, r.text
        # P1: 鉴权改挂路由依赖 → 401 body 是 FastAPI 的 {"detail": ...} (不再是 {"ok":false,...})
        assert "未授权" in r.text
        assert tmp_png.read_bytes() == b"fake png content"      # 一个字节都没被覆盖
        # 草稿 image 仍是 helper 写的那份 (helper 不写 source 字段 → None 即"没被换成 api_upload")
        assert badge_draft.get_draft(d.draft_id).image.get("source") is None

    def test_non_ascii_token_header_401_not_500(self, client, tmp_badge_data, monkeypatch):
        """P0b audit 收口 c: 非 ASCII 的 token header 不许把端点打成 500 (compare_digest TypeError).

        用**原始 bytes** 发 header (httpx 拒绝非 ASCII 的 str header) —— 服务端按 latin-1 解码
        后就是非 ASCII str, 正是审计说的那条路径。
        """
        monkeypatch.setenv("BADGE_PUSH_TOKEN", "ascii-only-token")
        monkeypatch.setenv("BADGE_STORE", "LOCAL")
        d = _make_awaiting_draft(tmp_badge_data)

        r = _push_image(client, d.draft_id, headers={"X-Badge-Push-Token": b"t\xf6ken-non-ascii"})
        assert r.status_code == 401, f"期望 401 (非 ASCII 不等即拒), 实际 {r.status_code}: {r.text[:200]}"

    def test_auth_wired_as_route_dependency(self):
        """P0b audit 收口 a: 鉴权必须是**路由级依赖** —— 删 handler 里那行也不会静默重开."""
        from src.kid_app.routes import badge_workflow as bw

        route = next(
            r for r in bw.router.routes
            if getattr(r, "path", "") == "/config/api/badge/draft/{draft_id}/image"
            and "POST" in (r.methods or set())
        )
        dep_calls = [d.call for d in route.dependant.dependencies]
        assert bw.require_badge_push_auth in dep_calls, f"路由依赖里没有鉴权: {dep_calls}"

    def test_stale_revision_409_no_silent_overwrite(self, client, tmp_badge_data, monkeypatch):
        """P1 CAS: 带着过期 revision 推图 → 409, 且旧图/旧 revision 一字不动."""
        import hashlib

        monkeypatch.setenv("BADGE_PUSH_TOKEN", "cas-token")
        monkeypatch.setenv("BADGE_STORE", "LOCAL")
        meta = _make_valid_meta("cas_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        assert badge_draft.get_draft(d.draft_id).revision == 1

        png1 = _rgba_png(color=(255, 0, 255, 255))
        png2 = _rgba_png(color=(0, 255, 0, 255))
        hdr = {"X-Badge-Push-Token": "cas-token"}

        ok = _push_image(client, d.draft_id, png1, hdr)           # 用最新 revision (无 header) → 成功
        assert ok.status_code == 200, ok.text
        assert ok.json()["revision"] == 2

        stale = dict(hdr, **{"X-Draft-Revision": "1"})            # 手里还是 1 → 后写方
        r = _push_image(client, d.draft_id, png2, stale)
        assert r.status_code == 409, r.text
        body = r.json()
        assert body["code"] == "revision_conflict"
        assert (body["expected_revision"], body["actual_revision"]) == (1, 2)

        after = badge_draft.get_draft(d.draft_id)                 # 没被静默覆盖
        assert after.revision == 2
        assert after.image["sha256"] == hashlib.sha256(png1).hexdigest()
        assert after.image["sha256"] != hashlib.sha256(png2).hexdigest()

    def test_bad_revision_header_400(self, client, tmp_badge_data, monkeypatch):
        monkeypatch.setenv("BADGE_PUSH_TOKEN", "cas-token")
        monkeypatch.setenv("BADGE_STORE", "LOCAL")
        d = _make_awaiting_draft(tmp_badge_data)
        r = _push_image(client, d.draft_id,
                        headers={"X-Badge-Push-Token": "cas-token", "X-Draft-Revision": "abc"})
        assert r.status_code == 400, r.text
        assert "X-Draft-Revision" in r.text

    def test_wrong_token_401(self, client, tmp_badge_data, monkeypatch):
        """② token 错 → 401."""
        monkeypatch.setenv("BADGE_PUSH_TOKEN", "right-token")
        monkeypatch.setenv("BADGE_STORE", "LOCAL")
        d = _make_awaiting_draft(tmp_badge_data)

        r = _push_image(client, d.draft_id, headers={"X-Badge-Push-Token": "wrong-token"})
        assert r.status_code == 401, r.text
        assert badge_draft.tmp_path_for(d.draft_id, 1).read_bytes() == b"fake png content"

    def test_token_channel_closed_when_env_unset_401(self, client, tmp_badge_data, monkeypatch):
        """④ env 未设 → 该通道关闭 (带了任意 header 也 401), 不给默认 token."""
        monkeypatch.delenv("BADGE_PUSH_TOKEN", raising=False)
        monkeypatch.setenv("BADGE_STORE", "LOCAL")
        d = _make_awaiting_draft(tmp_badge_data)

        r = _push_image(client, d.draft_id, headers={"X-Badge-Push-Token": "any-value"})
        assert r.status_code == 401, r.text

    def test_valid_token_200_and_status_advances(self, client, tmp_badge_data, monkeypatch):
        """③ token 对 → 200, 图落盘 + status 推进 draft_created → draft_awaiting_confirm."""
        import hashlib

        monkeypatch.setenv("BADGE_PUSH_TOKEN", "s3cret-push-token")
        monkeypatch.setenv("BADGE_STORE", "LOCAL")     # 不碰真 COS
        meta = _make_valid_meta("push_ok_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        assert badge_draft.get_draft(d.draft_id).status == "draft_created"
        png = _rgba_png()

        r = _push_image(client, d.draft_id, png, {"X-Badge-Push-Token": "s3cret-push-token"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["status"] == "draft_awaiting_confirm"
        assert body["storage"] == "local"
        assert body["image"]["sha256"] == hashlib.sha256(png).hexdigest()
        assert body["image"]["source"] == "api_upload"

        after = badge_draft.get_draft(d.draft_id)
        assert after.status == "draft_awaiting_confirm"
        assert after.image["sha256"] == hashlib.sha256(png).hexdigest()
        assert after.history[-1]["event"] == "image_generated"
        assert badge_draft.tmp_path_for(d.draft_id, 1).read_bytes() == png

    def test_dad_pin_header_200_channel_b(self, client, tmp_badge_data, monkeypatch):
        """通道 ② 单独可用: token 通道关闭, 只带 X-Dad-Pin header 也能 200.

        只桩**存储** (settings 表读), PIN 比较逻辑仍是真代码 (check_dad_pin) —— 不是测试开关。
        """
        monkeypatch.delenv("BADGE_PUSH_TOKEN", raising=False)
        monkeypatch.setenv("BADGE_STORE", "LOCAL")
        real_get_setting = db.get_setting
        monkeypatch.setattr(
            db, "get_setting",
            lambda key, *a, **kw: ("0905" if key == "dad_pin" else real_get_setting(key, *a, **kw)),
        )
        meta = _make_valid_meta("push_pin_xyz")
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)

        bad = _push_image(client, d.draft_id, headers={"X-Dad-Pin": "0000"})
        assert bad.status_code == 401, bad.text

        ok = _push_image(client, d.draft_id, headers={"X-Dad-Pin": "0905"})
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == "draft_awaiting_confirm"
