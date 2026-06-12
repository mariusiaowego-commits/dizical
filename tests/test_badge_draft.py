"""tests/test_badge_draft.py — V2 draft CRUD 测试"""
import json
import re
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from src.kid_app import badge_draft


@pytest.fixture
def tmp_badge_data(monkeypatch, tmp_path):
    """重定向 badge_draft._badge_data_dir() 到临时目录."""
    data_dir = tmp_path / "badge_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(badge_draft, "_badge_data_dir", lambda: data_dir)
    return data_dir


class TestCreateDraft:
    def test_minimal_required(self, tmp_badge_data):
        meta = {
            "id": "grade_1", "name": "测试徽章", "type": "突破", "category": "milestone",
            "placeholder": "A cute chibi girl with bamboo flute",
            "zh_story": "孔子闻韶",
        }
        d = badge_draft.create_draft(meta)
        assert d.schema_version == badge_draft.SCHEMA_VERSION
        assert d.meta == meta
        assert d.image is None
        assert d.status == "draft_created"
        assert d.version == 1
        assert re.match(r"^\d{4}-\d{2}-\d{2}_grade_1_[a-z0-9]{6}$", d.draft_id)
        assert len(d.history) == 1
        assert d.history[0]["to"] == "draft_created"

    def test_missing_required_field(self, tmp_badge_data):
        with pytest.raises(ValueError, match="缺必填字段"):
            badge_draft.create_draft({"id": "x", "name": "y"})

    def test_invalid_id_format(self, tmp_badge_data):
        meta = {
            "id": "bad-id!", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story",
        }
        with pytest.raises(ValueError, match="格式不对"):
            badge_draft.create_draft(meta)

    def test_seasonal_requires_seasonal_type(self, tmp_badge_data):
        meta = {
            "id": "x_1", "name": "x", "type": "主题", "category": "seasonal",
            "placeholder": "ph", "zh_story": "story",
        }
        with pytest.raises(ValueError, match="seasonal_type"):
            badge_draft.create_draft(meta)


class TestSaveAndGet:
    def test_round_trip(self, tmp_badge_data):
        meta = {
            "id": "x_1", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story",
        }
        d = badge_draft.create_draft(meta)
        path = badge_draft.save_draft(d)
        assert path.exists()
        # 读回
        d2 = badge_draft.get_draft(d.draft_id)
        assert d2 is not None
        assert d2.draft_id == d.draft_id
        assert d2.meta == d.meta

    def test_get_nonexistent(self, tmp_badge_data):
        assert badge_draft.get_draft("2026-06-12_xxx_abc123") is None

    def test_get_invalid_format(self, tmp_badge_data):
        """非 draft_id 格式返 None (不抛异常, 防前端恶意输入)."""
        assert badge_draft.get_draft("../etc/passwd") is None
        assert badge_draft.get_draft("not_a_draft_id") is None


class TestUpdateDraftImage:
    def test_draft_created_to_awaiting_confirm(self, tmp_badge_data):
        meta = {
            "id": "x_1", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story",
        }
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        image = {
            "path": "/Users/mt16/dev/dizical/data/lib/badge_data/.tmp/x_1_v1.png",
            "model": "gpt-image-2",
            "prompt_used": "A chibi girl...",
            "alpha_verified": True,
            "version": 1,
        }
        d2 = badge_draft.update_draft_image(d.draft_id, image)
        assert d2.status == "draft_awaiting_confirm"
        assert d2.image == image
        assert d2.version == 1

    def test_invalid_status(self, tmp_badge_data):
        meta = {
            "id": "x_1", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story",
        }
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        # 强制 status=committed
        d.status = "committed"
        badge_draft.save_draft(d)
        with pytest.raises(ValueError, match="status=committed 不允许"):
            badge_draft.update_draft_image(d.draft_id, {"path": "x"})

    def test_nonexistent_draft(self, tmp_badge_data):
        with pytest.raises(FileNotFoundError):
            badge_draft.update_draft_image("2026-06-12_xxx_abc123", {"path": "x"})


class TestMarkDraftStatus:
    def test_draft_awaiting_to_committed(self, tmp_badge_data):
        meta = {
            "id": "x_1", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story",
        }
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        badge_draft.update_draft_image(d.draft_id, {"path": "x", "version": 1})
        badge_draft.mark_draft_status(d.draft_id, "committed", by="dizical",
                                    extra={"event": "user_confirmed"})
        d2 = badge_draft.get_draft(d.draft_id)
        assert d2.status == "committed"
        assert d2.history[-1]["event"] == "user_confirmed"
        assert d2.history[-1]["by"] == "dizical"

    def test_invalid_status_value(self, tmp_badge_data):
        with pytest.raises(ValueError, match="new_status"):
            badge_draft.mark_draft_status("2026-06-12_x_abc123", "nonsense")


class TestListDrafts:
    def test_empty(self, tmp_badge_data):
        assert badge_draft.list_drafts() == []

    def test_filter_by_status(self, tmp_badge_data):
        for _ in range(3):
            meta = {
                "id": "x_1", "name": "x", "type": "突破", "category": "milestone",
                "placeholder": "ph", "zh_story": "story",
            }
            d = badge_draft.create_draft(meta)
            badge_draft.save_draft(d)
        # 推 1 个到 awaiting_confirm
        drafts = badge_draft.list_drafts()
        badge_draft.update_draft_image(drafts[0].draft_id, {"path": "x", "version": 1})
        assert len(badge_draft.list_drafts()) == 3
        assert len(badge_draft.list_drafts(status="draft_created")) == 2
        assert len(badge_draft.list_drafts(status="draft_awaiting_confirm")) == 1

    def test_invalid_filter_status(self, tmp_badge_data):
        with pytest.raises(ValueError, match="不在"):
            badge_draft.list_drafts(status="bogus")

    def test_skips_corrupt_files(self, tmp_badge_data):
        """单文件坏不阻塞其他."""
        (tmp_badge_data / "bad.json").write_text("not json", encoding="utf-8")
        assert badge_draft.list_drafts() == []  # 没抛


class TestDeleteDraft:
    def test_delete_existing(self, tmp_badge_data):
        meta = {
            "id": "x_1", "name": "x", "type": "突破", "category": "milestone",
            "placeholder": "ph", "zh_story": "story",
        }
        d = badge_draft.create_draft(meta)
        badge_draft.save_draft(d)
        assert badge_draft.delete_draft(d.draft_id) is True
        assert badge_draft.get_draft(d.draft_id) is None

    def test_delete_nonexistent(self, tmp_badge_data):
        assert badge_draft.delete_draft("2026-06-12_xxx_abc123") is False


class TestTmpHelpers:
    def test_tmp_path_for(self, tmp_badge_data, monkeypatch):
        """临时图路径 (skill 写图用)."""
        monkeypatch.setattr(badge_draft, "_tmp_dir", lambda: tmp_badge_data / ".tmp")
        p = badge_draft.tmp_path_for("2026-06-12_x_abc123", 1)
        assert str(p).endswith("2026-06-12_x_abc123_v1.png")

    def test_cleanup_tmp(self, tmp_badge_data, monkeypatch):
        monkeypatch.setattr(badge_draft, "_tmp_dir", lambda: tmp_badge_data / ".tmp")
        (tmp_badge_data / ".tmp").mkdir(exist_ok=True)
        p = badge_draft.tmp_path_for("abc", 1)
        p.write_text("fake png", encoding="utf-8")
        assert p.exists()
        badge_draft.cleanup_tmp("abc", 1)
        assert not p.exists()
