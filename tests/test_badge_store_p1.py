"""tests/test_badge_store_p1.py — P1: 草稿/图统一 COS 的存储层 (权威副本 + CAS + 合并)

覆盖 (PLAN v1.2 §3 P1):
  1. 键常量 + BADGE_STORE 开关 (LOCAL / COS / AUTO 解析)
  2. storage=cos 写侧 → 只写 COS, **本机不出现本地 json** (验收 a 的单元版)
  3. 读侧权威副本裁决: 本地缓存 (storage=cos) 不能遮住 COS 上的新版本 (P0 audit 必修项)
  4. 写侧不许静默回落: COS 可用但写失败 → 抛 RuntimeError, 本地不许出现冒充的 json
  5. CAS: 陈旧 revision → RevisionConflict; 成功后 revision 单调 +1
  6. list_drafts = COS ∪ 本地 (老草稿不丢); delete_draft 两份都删
  7. 老草稿 (只有 image.path) 惰性补 image.url (COS)

COS 用内存 fake (不打真网络); 真 COS 的端到端验证在 P1 验收脚本里做。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.kid_app import badge_draft, cos_client


class FakeCOS:
    """最小 COS 替身: 复用 cos_client.CosUploader 的语义 (URL 用 tcb.qcloud.la 形态)."""

    def __init__(self, bucket: str = "fake-bucket"):
        self.bucket = bucket
        self.objects: dict[str, bytes] = {}
        self.fail_upload = False

    @property
    def is_available(self) -> bool:
        return True

    def object_url(self, key: str) -> str:
        return f"https://{self.bucket}.tcb.qcloud.la/{key}"

    def upload(self, key: str, content: bytes, content_type: str = "image/png") -> str:
        if self.fail_upload:
            raise RuntimeError("COS 上传失败: 模拟网络故障")
        self.objects[key] = content
        return self.object_url(key)

    def download(self, key: str) -> bytes:
        if key not in self.objects:
            raise FileNotFoundError(f"COS 对象不存在: {key}")
        return self.objects[key]

    def exists(self, key: str) -> bool:
        return key in self.objects

    def delete_object(self, key: str) -> bool:
        return self.objects.pop(key, None) is not None

    def list_keys(self, prefix: str, max_keys: int = 200) -> list[str]:
        return sorted(k for k in self.objects if k.startswith(prefix))[:max_keys]


def _meta(badge_id="p1_test_badge"):
    return {
        "id": badge_id, "name": "P1 测试章", "type": "突破", "category": "milestone",
        "placeholder": "p1 storage test pin", "zh_story": "P1 存储测试", "cond_text": "测试",
    }


def _rgba_png_bytes(size=(64, 64)) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", size, (255, 0, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def local_dir(tmp_path, monkeypatch):
    """把 badge_data 目录重定向到 tmp; 返回该目录 (本地是否"出现新 json"就看它)."""
    d = tmp_path / "badge_data"
    d.mkdir()
    monkeypatch.setattr(badge_draft, "_badge_data_dir", lambda: d)
    monkeypatch.setattr(badge_draft, "_tmp_dir", lambda: d / ".tmp")
    return d


@pytest.fixture
def fake_cos(monkeypatch):
    fake = FakeCOS()
    monkeypatch.setattr(cos_client, "cos_uploader", fake)
    return fake


# ─── 1. 开关与键常量 ────────────────────────────────────────────────

def test_key_constants_and_store_switch(monkeypatch):
    assert badge_draft.COS_PREFIX_DRAFT == "badge_drafts/"
    assert badge_draft.COS_PREFIX_BADGE == "badges/"          # 沿用, 不动历史 key
    assert badge_draft.cos_draft_key("2026-10-14_x_abc123") == "badge_drafts/2026-10-14_x_abc123.json"

    monkeypatch.setattr(cos_client, "cos_uploader", FakeCOS())
    monkeypatch.setenv("BADGE_STORE", "LOCAL")
    assert badge_draft.storage_mode() == "local"              # 显式 LOCAL 即使 COS 可用也不用
    monkeypatch.setenv("BADGE_STORE", "COS")
    assert badge_draft.storage_mode() == "cos"
    monkeypatch.delenv("BADGE_STORE")                          # 默认 AUTO
    assert badge_draft.storage_mode() == "cos"

    class Dead(FakeCOS):
        @property
        def is_available(self):
            return False

    monkeypatch.setattr(cos_client, "cos_uploader", Dead())
    assert badge_draft.storage_mode() == "local"               # COS 不可用 → AUTO 落 local
    monkeypatch.setenv("BADGE_STORE", "COS")
    assert badge_draft.storage_mode() == "local"               # 显式 COS 但不可用 → local (可见: /health)


def test_cos_draft_key_rejects_bad_id():
    with pytest.raises(ValueError):
        badge_draft.cos_draft_key("../etc/passwd")


# ─── 1b. R1 返工: 读/写只允许一套 id 语义 ────────────────────────────

_ID_BATTERY = [
    "2026-10-14_p1_a1b2c3",              # 标准形态
    "2026-10-14__p1test_warden_l3g7",    # warden 举的例: 哈希段只 4 位
    "2026-06-12_grade-1_abc123",
    "short_hash_ab",                     # 没有日期段
    "seq_17",                            # 顺序号老 id
    "bad/id",                            # 非法: 斜杠
    "../etc/passwd",                     # 非法: 路径穿越
    "has space",                         # 非法: 空格
    "点号",                              # 非法: 非 ASCII
    "",
]


@pytest.mark.parametrize("draft_id", _ID_BATTERY)
def test_read_write_id_semantics_equivalent(draft_id):
    """R1: 两个入口必须同一套语义 —— pattern 是同一个对象, 且判定逐条相同."""
    assert badge_draft.DRAFT_ID_RE.pattern == badge_draft.SAFE_DRAFT_ID_RE.pattern == r"^[a-zA-Z0-9_-]+$"
    assert badge_draft.DRAFT_ID_RE is badge_draft.SAFE_DRAFT_ID_RE
    write_verdict = bool(badge_draft.DRAFT_ID_RE.match(draft_id or ""))       # save_draft/cos_draft_key/write_tmp_image
    read_verdict = bool(badge_draft.DRAFT_ID_RE.match(draft_id or ""))        # get_draft_with_source
    assert write_verdict == read_verdict


def test_short_hash_id_works_end_to_end(local_dir, fake_cos, monkeypatch):
    """R1 反向负控(通): 哈希段 <6 位的 id 必须**写得进也读得回来** (不再"写进去读不回来")."""
    monkeypatch.setenv("BADGE_STORE", "COS")
    short_id = "2026-10-14__p1test_warden_l3g7"          # 哈希 4 位 → 老 DRAFT_ID_RE 会拒
    d = badge_draft.create_draft(_meta())
    d.draft_id = short_id
    badge_draft.save_draft(d)                            # 写路径: 不抛
    assert f"badge_drafts/{short_id}.json" in fake_cos.objects

    got, src = badge_draft.get_draft_with_source(short_id)   # 读路径: 读得回来 (老代码这里返 None)
    assert got is not None, "写得进去却读不回来 = 静默失败 (R1 要修的 bug)"
    assert (src, got.draft_id, got.meta["id"]) == ("cos", short_id, "p1_test_badge")
    assert short_id in {x.draft_id for x in badge_draft.list_drafts()}


def test_illegal_id_rejected_by_both_paths(local_dir, fake_cos, monkeypatch):
    """R1 反向负控(拒): 非法 id 读写两侧都必须拒 (不能一边拒一边通)."""
    monkeypatch.setenv("BADGE_STORE", "COS")
    bad_id = "bad/id"
    d = badge_draft.create_draft(_meta())
    d.draft_id = bad_id
    with pytest.raises(ValueError):
        badge_draft.save_draft(d)                        # 写路径: 拒
    with pytest.raises(ValueError):
        badge_draft.cos_draft_key(bad_id)
    with pytest.raises(ValueError):
        badge_draft.write_tmp_image(bad_id, 1, b"x")
    assert badge_draft.get_draft_with_source(bad_id) == (None, "none")    # 读路径: 也拒
    assert badge_draft.get_draft(bad_id) is None
    assert badge_draft.delete_draft(bad_id) is False


def test_stray_non_draft_json_does_not_500(local_dir, fake_cos, monkeypatch):
    """R1 副作用防护: 目录里名字像 id 但不是草稿的 json → 读成"不存在", 不是 500."""
    monkeypatch.setenv("BADGE_STORE", "COS")
    (local_dir / "backup.json").write_text('{"hello": "world"}', encoding="utf-8")
    assert badge_draft.get_draft_with_source("backup") == (None, "none")
    (local_dir / "broken.json").write_text("{不是 json", encoding="utf-8")
    assert badge_draft.get_draft_with_source("broken") == (None, "none")


# ─── 2. COS 模式写侧: 只写 COS, 本地不出现 json (验收 a 单元版) ──────

def test_save_in_cos_mode_writes_only_cos(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "COS")
    d = badge_draft.create_draft(_meta())
    assert d.storage == "cos"

    ret = badge_draft.save_draft(d)
    assert ret is None                                         # 没有本地路径返回
    assert not list(local_dir.glob("*.json")), "COS 模式不该在本地落 json"
    assert (f"badge_drafts/{d.draft_id}.json") in fake_cos.objects

    on_cos = json.loads(fake_cos.objects[f"badge_drafts/{d.draft_id}.json"].decode())
    assert on_cos["storage"] == "cos" and on_cos["revision"] == 1
    assert on_cos["meta"]["id"] == "p1_test_badge"

    got, src = badge_draft.get_draft_with_source(d.draft_id)
    assert src == "cos" and got.draft_id == d.draft_id and got.storage == "cos"


# ─── 3. 权威副本裁决: 本地缓存不许遮住 COS ───────────────────────────

def test_local_cache_does_not_shadow_cos(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "COS")
    d = badge_draft.create_draft(_meta())
    badge_draft.save_draft(d)                                  # rev=1 在 COS

    # 伪造一份"本地缓存": 同一个 draft, 标着 storage=cos, 内容更旧 (status=draft_created)
    stale = d.to_dict()
    stale["revision"] = 1
    stale["status"] = "draft_created"
    (local_dir / f"{d.draft_id}.json").write_text(json.dumps(stale, ensure_ascii=False), encoding="utf-8")

    # COS 上推进到 awaiting_confirm + rev=2
    up = badge_draft.get_draft(d.draft_id)
    up.status = "draft_awaiting_confirm"
    badge_draft.save_draft(up, expect_revision=1)

    got, src = badge_draft.get_draft_with_source(d.draft_id)
    assert src == "cos", "标记 storage=cos 时必须以 COS 为准 (本地只是缓存)"
    assert got.revision == 2 and got.status == "draft_awaiting_confirm"

    # 本地（非 cos 标记）的草稿仍以本地为准 —— 老草稿路径不被破坏
    legacy = d.to_dict()
    legacy["draft_id"] = "2026-10-01_legacy_local_abc111"
    legacy["storage"] = "local"
    legacy["meta"] = dict(legacy["meta"], id="legacy_local")
    (local_dir / "2026-10-01_legacy_local_abc111.json").write_text(
        json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
    got2, src2 = badge_draft.get_draft_with_source("2026-10-01_legacy_local_abc111")
    assert src2 == "local" and got2.meta["id"] == "legacy_local"


def test_marker_cos_but_missing_on_cos_falls_back_to_cache(local_dir, fake_cos, monkeypatch):
    """标记 cos 但 COS 上没了 → 退回本地缓存, 并在路由层给出 storage_warning (这里只验读侧)."""
    monkeypatch.setenv("BADGE_STORE", "COS")
    d = badge_draft.create_draft(_meta())
    badge_draft.save_draft(d)
    del fake_cos.objects[f"badge_drafts/{d.draft_id}.json"]     # 模拟 COS 上被清掉
    (local_dir / f"{d.draft_id}.json").write_text(
        json.dumps(d.to_dict(), ensure_ascii=False), encoding="utf-8")

    got, src = badge_draft.get_draft_with_source(d.draft_id)
    assert src == "local" and got.storage == "cos"              # 来源与标记不一致 = 读到缓存


# ─── 4. 写侧不许静默回落 ────────────────────────────────────────────

def test_cos_write_failure_raises_and_writes_no_local_file(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "COS")
    d = badge_draft.create_draft(_meta())
    fake_cos.fail_upload = True

    with pytest.raises(RuntimeError, match="COS 上传失败"):
        badge_draft.save_draft(d)
    assert not list(local_dir.glob("*.json")), "COS 写失败绝不能在本地留一份冒充成功"


def test_local_mode_still_writes_local(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "LOCAL")
    d = badge_draft.create_draft(_meta())
    assert d.storage == "local"
    path = badge_draft.save_draft(d)
    assert path is not None and path.is_file()
    assert not fake_cos.objects, "LOCAL 模式不该碰 COS"


# ─── 5. CAS ────────────────────────────────────────────────────────

def test_revision_conflict_on_stale_write(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "COS")
    d = badge_draft.create_draft(_meta())
    badge_draft.save_draft(d)                                   # 首次落盘 → revision=1

    a = badge_draft.get_draft(d.draft_id)                       # 两个调用方都拿到 revision=1
    b = badge_draft.get_draft(d.draft_id)
    assert (a.revision, b.revision) == (1, 1)
    a.status = "draft_awaiting_confirm"
    badge_draft.save_draft(a, expect_revision=1)                # A 先写 → revision=2

    b.status = "discarded"
    with pytest.raises(badge_draft.RevisionConflict) as ei:
        badge_draft.save_draft(b, expect_revision=1)            # B 拿着旧 revision → 冲突
    assert (ei.value.expected, ei.value.actual) == (1, 2)

    stored = json.loads(fake_cos.objects[f"badge_drafts/{d.draft_id}.json"].decode())
    assert stored["revision"] == 2 and stored["status"] == "draft_awaiting_confirm", "B 不许覆盖 A"


def test_revision_increments_monotonically(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "COS")
    d = badge_draft.create_draft(_meta())
    badge_draft.save_draft(d)
    revs = [badge_draft.get_draft(d.draft_id).revision]         # 1
    for _ in range(3):
        cur = badge_draft.get_draft(d.draft_id)
        badge_draft.save_draft(cur)
        revs.append(badge_draft.get_draft(d.draft_id).revision)
    assert revs == [1, 2, 3, 4], revs


# ─── 6. list_drafts 合并 + delete 两份都删 ──────────────────────────

def test_list_drafts_merges_cos_and_local(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "COS")
    a = badge_draft.create_draft(_meta("p1_a"))
    badge_draft.save_draft(a)                                   # 只在 COS
    b = badge_draft.create_draft(_meta("p1_b"))
    b.storage = "local"                                         # 老式本地草稿
    badge_draft.save_draft(b)

    drafts = badge_draft.list_drafts()
    ids = {x.draft_id for x in drafts}
    assert ids == {a.draft_id, b.draft_id}
    assert {x.storage for x in drafts} == {"cos", "local"}

    assert len(badge_draft.list_drafts(status="draft_created")) == 2
    assert badge_draft.list_drafts(status="committed") == []


def test_delete_draft_removes_both_copies(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "COS")
    d = badge_draft.create_draft(_meta())
    badge_draft.save_draft(d)
    (local_dir / f"{d.draft_id}.json").write_text("{}", encoding="utf-8")   # 顺手留个本地缓存

    assert badge_draft.delete_draft(d.draft_id) is True
    assert f"badge_drafts/{d.draft_id}.json" not in fake_cos.objects
    assert not (local_dir / f"{d.draft_id}.json").exists()
    assert badge_draft.delete_draft(d.draft_id) is False         # 幂等


# ─── 7. 老草稿惰性补 image.url ─────────────────────────────────────

def test_backfill_image_url_uploads_and_persists(local_dir, fake_cos, monkeypatch):
    monkeypatch.setenv("BADGE_STORE", "COS")
    d = badge_draft.create_draft(_meta())
    badge_draft.save_draft(d)
    # 老草稿形态: 只有本地 path, 没有 url
    (local_dir / ".tmp").mkdir(exist_ok=True)
    png = local_dir / ".tmp" / f"{d.draft_id}_v1.png"
    png.write_bytes(_rgba_png_bytes())
    cur = badge_draft.get_draft(d.draft_id)
    cur.image = {"path": str(png), "version": 1, "source": "user_import"}
    badge_draft.save_draft(cur)

    url = badge_draft.backfill_image_url(badge_draft.get_draft(d.draft_id))
    assert url and url.startswith("https://") and "badges/p1_test_badge_v1.png" in url
    assert fake_cos.objects["badges/p1_test_badge_v1.png"] == png.read_bytes()

    after = badge_draft.get_draft(d.draft_id)                   # 写回 COS 权威副本
    assert after.image["url"] == url and after.image["storage"] == "cos"
    assert badge_draft.backfill_image_url(after) is None         # 已有 url → 幂等空转


# ─── 8. delete_object 契约: 不存在必须返 False (F3, audit 261014 / PR 366) ─────

def test_delete_object_false_when_absent_true_when_present(monkeypatch):
    """F3: COS/S3 的 DELETE 对不存在的 key 也返 204 不抛 → 修前本函数恒返 True.

    修法: 先 head 定存在性. 断言两件事: 不存在 → False **且不发 DELETE**; 存在 → delete 一次 + True.
    """
    monkeypatch.setenv("COS_BUCKET", "b-1250000000")
    monkeypatch.setenv("COS_SECRET_ID", "id")
    monkeypatch.setenv("COS_SECRET_KEY", "key")
    up = cos_client.CosUploader()

    class Err404(Exception):
        def get_status_code(self):
            return 404

    class FakeSDK:
        """桩 SDK: DELETE 对缺失 key 也成功 (跟真 COS 一致) —— 逼代码用 head 判存在性."""

        def __init__(self, present):
            self.present = set(present)
            self.calls: list[tuple[str, str]] = []

        def head_object(self, **kw):
            self.calls.append(("head", kw["Key"]))
            if kw["Key"] not in self.present:
                raise Err404("404")
            return {}

        def delete_object(self, **kw):
            self.calls.append(("delete", kw["Key"]))
            self.present.discard(kw["Key"])       # 真 COS 对缺失 key 也返 204 → 这里不报错
            return {}

    sdk = FakeSDK({"badges/here_v1.png"})
    up._client = sdk                               # 直接注入桩, 绕开真客户端构造

    assert up.delete_object("badges/gone_v1.png") is False
    assert ("delete", "badges/gone_v1.png") not in sdk.calls, "缺失对象不该发 DELETE"
    assert up.delete_object("badges/here_v1.png") is True
    assert ("delete", "badges/here_v1.png") in sdk.calls
    assert up.delete_object("badges/here_v1.png") is False   # 已删掉 → 再来一次 = False


# ─── 9. list_keys 分页拉全 / 不静默截断 (P3-3, audit 261016) ──────────────────

def _cos_uploader_with_fake_sdk(monkeypatch, present: list[str], page_size: int):
    """桩 SDK: 按 Marker 翻页返回 (每次最多 page_size 个), IsTruncated 如实给。"""
    monkeypatch.setenv("COS_BUCKET", "b-1250000000")
    monkeypatch.setenv("COS_SECRET_ID", "id")
    monkeypatch.setenv("COS_SECRET_KEY", "key")
    up = cos_client.CosUploader()

    class FakeListSDK:
        def __init__(self):
            self.calls: list[dict] = []

        def list_objects(self, **kw):
            self.calls.append(kw)
            prefix = kw["Prefix"]
            after = kw.get("Marker") or ""
            keys = [k for k in present if k.startswith(prefix) and k > after]
            page = keys[:page_size]
            out: dict = {"Contents": [{"Key": k} for k in page]}
            if len(keys) > page_size:
                out["IsTruncated"] = "true"
            else:
                out["IsTruncated"] = "false"
            return out

    sdk = FakeListSDK()
    up._client = sdk
    return up, sdk


def test_list_keys_pages_through_everything(monkeypatch):
    """P3-3: 250 个对象 → 全拿到 (旧版默认 max_keys=200 到此静默截断成 200 个)."""
    present = [f"badge_drafts/d{i:03d}.json" for i in range(250)] + ["badges/x_v1.png"]
    up, sdk = _cos_uploader_with_fake_sdk(monkeypatch, present, page_size=100)

    keys = up.list_keys("badge_drafts/")

    assert len(keys) == 250, f"应列全 250 个, 实得 {len(keys)} (静默截断?)"
    assert keys == present[:250]                      # 顺序 = 字典序, 无重复无遗漏
    assert len(sdk.calls) == 3                        # 100 + 100 + 50 三页
    assert [c.get("Marker") for c in sdk.calls] == [None, "badge_drafts/d099.json",
                                                   "badge_drafts/d199.json"]


def test_list_keys_hard_cap_raises_not_silently_truncates(monkeypatch):
    """P3-3: 够到硬上限 → **抛错** (不静默返回前 N 个); 正常量级不触发。"""
    present = [f"badge_drafts/d{i:04d}.json" for i in range(300)]
    up, _sdk = _cos_uploader_with_fake_sdk(monkeypatch, present, page_size=100)

    assert len(up.list_keys("badge_drafts/", max_keys=500)) == 300        # 上限之内: 全量

    with pytest.raises(RuntimeError, match="超过硬上限"):
        up.list_keys("badge_drafts/", max_keys=250)                       # 超上限: fail loud


def test_list_keys_single_page_no_extra_call(monkeypatch):
    """P3-3 正控: 单页就拉完 → 只发 1 次请求, 不因为分页改造多发空翻页."""
    up, sdk = _cos_uploader_with_fake_sdk(monkeypatch, ["badge_drafts/only.json"], page_size=100)
    assert up.list_keys("badge_drafts/") == ["badge_drafts/only.json"]
    assert len(sdk.calls) == 1
