"""
Test for V2.2.1 (2026-06-15): cond_text 强制必填 (用户 2026-06-15 拍板).

修法:
- badge_draft.create_draft required 字段加 cond_text
- 表单 required 跟验证
- 不再支持"留空走 fallback", 用户必须填 (手填 OR 点 AI 按钮)
- modal-cond 跟 modal-desc 永远分开 (无 fallback 兜底撞车风险)
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.test_badge_commit_version_sync import (
    isolated_db, _make_test_draft, _write_draft, _write_tmp_image, _cleanup,
)


class TestCondTextRequired:
    """cond_text 必填 (V2.2.1)."""

    def test_cond_text_required_at_create_draft(self, isolated_db):
        """meta 缺 cond_text → create_draft 抛 ValueError (跟 zh_story 一样必填)."""
        from src.kid_app import badge_draft

        meta = {
            "id": "test_required_xyz",
            "name": "测试",
            "type": "突破",
            "category": "milestone",
            "placeholder": "a cute chibi test",
            "zh_story": "测试典故",
            # 缺 cond_text
            "display_format": "achieved_flag",
        }
        with pytest.raises(ValueError, match="cond_text"):
            badge_draft.create_draft(meta)

    def test_cond_text_empty_string_at_create_draft(self, isolated_db):
        """meta.cond_text = '' (空字符串) → 抛 ValueError (跟缺一样, 都是空)."""
        from src.kid_app import badge_draft

        meta = {
            "id": "test_required_abc",
            "name": "测试",
            "type": "突破",
            "category": "milestone",
            "placeholder": "a cute chibi test",
            "zh_story": "测试典故",
            "cond_text": "",  # 空字符串
            "display_format": "achieved_flag",
        }
        with pytest.raises(ValueError, match="cond_text"):
            badge_draft.create_draft(meta)

    def test_cond_text_with_value_creates_draft(self, isolated_db):
        """meta.cond_text 有值 → create_draft 成功."""
        from src.kid_app import badge_draft

        meta = {
            "id": "test_required_ok",
            "name": "测试",
            "type": "突破",
            "category": "milestone",
            "placeholder": "a cute chibi test",
            "zh_story": "测试典故",
            "cond_text": "帮妈妈批 1 次",  # 有值
            "display_format": "achieved_flag",
        }
        d = badge_draft.create_draft(meta)
        assert d.meta["cond_text"] == "帮妈妈批 1 次"
