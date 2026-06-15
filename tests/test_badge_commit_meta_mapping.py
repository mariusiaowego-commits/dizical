"""
Tests for Bug #4 + #5: commit handler meta mapping (description=zh_story, stat_logic="").

User 2026-06-15: modal-desc 显示"无" + modal-cond 显示空白.

Bug 4 根因: routes/badge_workflow.py:155-156 setdefault 落 "无". zh_story 没进 db.
修法: description = zh_story, stat_logic = "" (calc 不靠它).

Bug 5 根因: data-cond 来自 CalcResult.condition (calc 返回), 不是 description.
修法: 前端 dataset.cond || dataset.desc fallback (本期先覆盖后端, 前端在 PR 2 改).
本期 pytest 验 description 写入正确 (前端的 fallback 在 UI 测试里看).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.test_badge_commit_version_sync import (
    isolated_db, _make_test_draft, _write_draft, _write_tmp_image, _cleanup,
    PNG_1x1,
)


class TestCommitMetaMapping:
    """Bug 4 修法: commit handler 写 description=zh_story, stat_logic=''."""

    def test_zh_story_writes_to_description(self, isolated_db):
        """meta.zh_story 存在 → achievements.description = zh_story 全文."""
        draft_id = "2026-06-15_test_b4_e5eeeee"
        badge_id = "test_b4_e5eeeee"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            draft_data["meta"]["zh_story"] = "**居里夫人**帮妈妈洗试管的故事。\n\n经典语录: 这孩子比我仔细。"
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True

            # 验: achievements.description == zh_story 全文
            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute("SELECT description, stat_logic FROM achievements WHERE id=?", (badge_id,))
            row = cur.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "**居里夫人**帮妈妈洗试管的故事。\n\n经典语录: 这孩子比我仔细。", \
                f"description should equal zh_story, got {row[0]!r}"
            # 验: stat_logic 是空字符串
            assert row[1] == "", f"stat_logic should be empty string, got {row[1]!r}"
        finally:
            _cleanup(draft_id, badge_id)

    def test_missing_zh_story_falls_back_to_wu(self, isolated_db):
        """meta.zh_story 缺 (老数据兼容) → description = "无"."""
        draft_id = "2026-06-15_test_b4_f6fffff"
        badge_id = "test_b4_f6fffff"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            del draft_data["meta"]["zh_story"]  # 删掉, 模拟老 draft
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute("SELECT description, stat_logic FROM achievements WHERE id=?", (badge_id,))
            row = cur.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "无", f"description should be '无' fallback, got {row[0]!r}"
            assert row[1] == "", f"stat_logic should be empty string, got {row[1]!r}"
        finally:
            _cleanup(draft_id, badge_id)

    def test_empty_zh_story_falls_back_to_wu(self, isolated_db):
        """meta.zh_story = '' (空字符串) → description = "无" (跟"缺"行为一致)."""
        draft_id = "2026-06-15_test_b4_g7000000"[:31]  # 截断
        badge_id = "test_b4_g70000"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            draft_data["meta"]["zh_story"] = ""
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute("SELECT description FROM achievements WHERE id=?", (badge_id,))
            row = cur.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "无", f"description should be '无' fallback for empty zh_story"
        finally:
            _cleanup(draft_id, badge_id)
