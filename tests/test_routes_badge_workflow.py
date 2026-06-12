"""tests/test_routes_badge_workflow.py — V2 端点端到端测试 (FastAPI TestClient)

覆盖:
- POST /api/badge/draft (建草稿, 校验, 必填字段)
- GET /api/badge/draft/{id} (读草稿, 404)
- POST /api/badge/commit-from-draft (写三表, 状态机, stat_logic 默认值)
- GET /api/badge/discoveries (扫待确认)

V2 设计:
- Pydantic BaseModel 收 body (替代 V1 错法 request.scope.get("body"))
- stat_logic V2 meta 没收集, commit handler 默认 "无" (跟 V1 insert_achievement_row 兼容)
- 不 server-side PIN check (前端 localStorage 负责)
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
        parsed = json.loads(data["json"])
        assert parsed["meta"] == meta
        assert parsed["schema_version"] == 1
        assert parsed["status"] == "draft_created"

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
        tmp_png.write_bytes(b"fake png")
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

        # 验证 DB 三表 (用 badge_write_tx context manager 跟 V1 一致)
        with badge_db.badge_write_tx() as conn:
            ach = conn.execute(
                "SELECT id, name, type, category, stat_logic FROM achievements WHERE id=?",
                ("v2_test_commit_happy_xyz",)
            ).fetchone()
            assert ach is not None
            assert ach[0] == "v2_test_commit_happy_xyz"
            assert ach[1] == "测试徽章"
            # V2 meta 没 stat_logic, V2.1 commit handler 默认 "无"
            assert ach[4] == "无"

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
        # static/badges/ PNG 也清 (move_tmp_to_static 复制过去的)
        project_root = Path(tmp_png).resolve().parent.parent.parent.parent.parent
        static_png = project_root / "src" / "kid_app" / "static" / "badges" / f"v2_test_commit_happy_xyz_v1.png"
        if static_png.exists():
            static_png.unlink()

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
        """端到端: 1 个 pending draft, image_url 返 web 路径 /static/badges/{id}_v{n}.png (V2.1 修)."""
        meta = _make_valid_meta("disc_xyz")
        d = _make_awaiting_draft(tmp_badge_data, meta=meta)
        r = client.get("/config/api/badge/discoveries")
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data) == 1
        item = data[0]
        # V2.1: image_url 走 /static/badges/{id}_v{version}.png (前端可渲染)
        assert item["image_url"] == "/static/badges/v2_test_disc_xyz_v1.png"
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
