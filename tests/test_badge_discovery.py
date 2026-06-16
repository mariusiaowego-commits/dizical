"""tests/test_badge_discovery.py — V2 discovery 测试"""
from unittest import mock

import pytest

from src.kid_app import badge_discovery, badge_draft, badge_db


@pytest.fixture
def tmp_badge_data(monkeypatch, tmp_path):
    """重定向 badge_draft._badge_data_dir() 到临时目录."""
    data_dir = tmp_path / "badge_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(badge_draft, "_badge_data_dir", lambda: data_dir)
    return data_dir


def _make_draft_pending(badge_data_dir, badge_id="grade_1", draft_id=None):
    """helper: 写一个 status=draft_awaiting_confirm 的 draft."""
    meta = {
        "id": badge_id, "name": "x", "type": "突破", "category": "milestone",
        "placeholder": "ph", "zh_story": "story", "cond_text": "V2.2.1 必填",
    }
    d = badge_draft.create_draft(meta)
    if draft_id:
        d.draft_id = draft_id
    badge_draft.save_draft(d)
    badge_draft.update_draft_image(d.draft_id, {
        "path": "/Users/mt16/dev/dizical/data/lib/badge_data/.tmp/x.png",
        "model": "gpt-image-2",
        "alpha_verified": True,
        "version": 1,
    })
    return d


class TestScanBadgeDataDir:
    def test_empty(self, tmp_badge_data):
        assert badge_discovery.scan_badge_data_dir() == []

    def test_only_pending(self, tmp_badge_data):
        # 用不存在的 id (测试临时 draft, 不跟 V1 真实 DB 冲突)
        _make_draft_pending(tmp_badge_data, badge_id="v2_test_unique_xyz")
        with mock.patch.object(badge_db, "badge_exists", return_value=False):
            items = badge_discovery.scan_badge_data_dir()
        assert len(items) == 1
        item = items[0]
        assert item["is_committable"] is True
        assert item["db_status"] == "not_exists"
        assert item["conflict_reason"] is None

    def test_skip_non_pending(self, tmp_badge_data):
        # draft_created 跳过
        meta = {
            "id": "x_1", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story", "cond_text": "V2.2.1 必填",
        }
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        # confirmed 跳过
        meta2 = {
            "id": "x_2", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story", "cond_text": "V2.2.1 必填",
        }
        d2 = badge_draft.create_draft(meta2)
        badge_draft.save_draft(d2)
        badge_draft.mark_draft_status(d2.draft_id, "confirmed", by="dizical")
        # 只 awaiting_confirm 入选
        items = badge_discovery.scan_badge_data_dir()
        assert len(items) == 0

    def test_image_url_extraction(self, tmp_badge_data):
        """image.path 含 /static/badges/ → 转 web URL (V2.1 修: 优先用 meta.id + version 拼 web 路径, draft 写 .tmp/ 也能渲染)."""
        meta = {
            "id": "v2_test_url_xyz", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story", "cond_text": "V2.2.1 必填",
        }
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        badge_draft.update_draft_image(d.draft_id, {
            "path": "/Users/mt16/dev/dizical/src/kid_app/static/badges/x_1_v1.png",
            "model": "gpt-image-2",
            "alpha_verified": True,
            "version": 1,
        })
        items = badge_discovery.scan_badge_data_dir()
        # V2.1: image_url 走 /static/badges/{id}_v{version}.png (从 meta.id 拼)
        assert items[0]["image_url"] == "/static/badges/v2_test_url_xyz_v1.png"

    def test_image_url_fallback_when_no_id(self, tmp_badge_data):
        """V2.1 兜底: 没 meta.id 时, 走旧逻辑 strip /static/badges/ 前缀."""
        meta = {
            "id": "v2_test_fallback_xyz", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story", "cond_text": "V2.2.1 必填",
        }
        d = badge_draft.create_draft(meta)
        # 拿掉 id (在 save 前改 meta dict 引用)
        d.meta.pop("id", None)
        badge_draft.save_draft(d)
        badge_draft.update_draft_image(d.draft_id, {
            "path": "/Users/mt16/dev/dizical/data/lib/badge_data/.tmp/x.png",
            "model": "gpt-image-2",
            "alpha_verified": True,
            "version": 1,
        })
        items = badge_discovery.scan_badge_data_dir()
        # fallback: strip 绝对路径前缀, 但 .tmp/ 没 /static/badges/ 所以原样返
        # (前端拿不到 web 路径 → 显兜底)
        assert items[0]["image_url"] == "/Users/mt16/dev/dizical/data/lib/badge_data/.tmp/x.png"

    def test_skip_awaiting_without_image(self, tmp_badge_data, caplog):
        """status=awaiting_confirm 但 image=None 跳过 (skill 失败中间状态)."""
        meta = {
            "id": "v2_test_skip_xyz", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story", "cond_text": "V2.2.1 必填",
        }
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        # 手动标记 awaiting 但没 image (异常状态, 不该入选)
        d.status = "draft_awaiting_confirm"
        badge_draft.save_draft(d)
        items = badge_discovery.scan_badge_data_dir()
        assert len(items) == 0

    def test_db_conflict_marks_not_committable(self, tmp_badge_data):
        _make_draft_pending(tmp_badge_data, badge_id="existing_badge")
        # mock DB 说已存在
        with mock.patch.object(badge_db, "badge_exists", return_value=True):
            items = badge_discovery.scan_badge_data_dir()
        assert len(items) == 1
        assert items[0]["is_committable"] is False
        assert items[0]["db_status"] == "exists_committed"
        assert "DB 已有" in items[0]["conflict_reason"]


class TestGetPendingConfirmations:
    def test_delegates_to_scan(self, tmp_badge_data):
        _make_draft_pending(tmp_badge_data)
        result = badge_discovery.get_pending_confirmations()
        assert result == badge_discovery.scan_badge_data_dir()


class TestGetCommittCandidate:
    def test_found(self, tmp_badge_data):
        d = _make_draft_pending(tmp_badge_data)
        result = badge_discovery.get_committ_candidate(d.draft_id)
        assert result is not None
        assert result["draft"]["draft_id"] == d.draft_id

    def test_not_found(self, tmp_badge_data):
        assert badge_discovery.get_committ_candidate("2026-06-12_xxx_abc123") is None
