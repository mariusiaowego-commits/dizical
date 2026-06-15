"""
Tests for cond_text 字段: commit handler 把 meta.cond_text 写进 achievements.cond_text.

feat/badge-cond-text (2026-06-15) 需求:
modal-cond 跟 modal-desc 当前都用 zh_story (Bug #5 修法), 文案重复.
新增 cond_text 字段让用户手填 / AI 生成"达成条件"一句话, 跟"典故小故事"分开.

修法:
- commit handler: meta.cond_text 写 db achievements.cond_text (缺/空 → "")
- 前端 3 级 fallback: res.condition > user_cond_text > description
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


class TestCondTextMetaMapping:
    """cond_text 写库映射 (Step 6 修法)."""

    def test_cond_text_writes_to_db(self, isolated_db):
        """meta.cond_text 存在 → achievements.cond_text = cond_text 全文."""
        draft_id = "2026-06-15_test_ct_1a1a1a1"
        badge_id = "test_ct_1a1a1a1"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            draft_data["meta"]["cond_text"] = "练习任意 1 天里包含 '批改' 关键词"
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True, f"commit failed: {data}"

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute("SELECT cond_text FROM achievements WHERE id=?", (badge_id,))
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "练习任意 1 天里包含 '批改' 关键词", \
                f"cond_text should equal input, got {row[0]!r}"
        finally:
            _cleanup(draft_id, badge_id)

    def test_missing_cond_text_writes_null(self, isolated_db):
        """meta.cond_text 缺 (老 draft / 老 schema) → 写 None (DB 默认), 不报错."""
        draft_id = "2026-06-15_test_ct_2b2b2b2"
        badge_id = "test_ct_2b2b2b2"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            # 不设 cond_text, 模拟老 draft
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True, f"commit failed: {data}"

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute("SELECT cond_text FROM achievements WHERE id=?", (badge_id,))
            row = cur.fetchone()
            conn.close()
            assert row is not None
            # 老 draft 无 cond_text → None (DB 允许, 跟 description NOT NULL 区别)
            assert row[0] is None, f"cond_text should be None, got {row[0]!r}"
        finally:
            _cleanup(draft_id, badge_id)

    def test_empty_cond_text_writes_empty_string(self, isolated_db):
        """meta.cond_text = '' (用户留空) → 写空字符串, 不是 None."""
        draft_id = "2026-06-15_test_ct_3c3c3c3"
        badge_id = "test_ct_3c3c3c3"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            draft_data["meta"]["cond_text"] = ""
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True, f"commit failed: {data}"

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute("SELECT cond_text FROM achievements WHERE id=?", (badge_id,))
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "", f"cond_text should be empty string, got {row[0]!r}"
        finally:
            _cleanup(draft_id, badge_id)

    def test_cond_text_distinct_from_description(self, isolated_db):
        """cond_text ≠ description (zh_story). 验证两个字段独立."""
        draft_id = "2026-06-15_test_ct_4d4d4d4"
        badge_id = "test_ct_4d4d4d4"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            draft_data["meta"]["zh_story"] = "居里夫人帮妈妈洗试管的典故。完整长篇。"
            draft_data["meta"]["cond_text"] = "帮妈妈批数学作业 1 次"
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True, f"commit failed: {data}"

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute("SELECT description, cond_text FROM achievements WHERE id=?", (badge_id,))
            row = cur.fetchone()
            conn.close()
            assert row is not None
            # description = zh_story (跟 Bug ❹ 修法一致)
            assert row[0] == "居里夫人帮妈妈洗试管的典故。完整长篇。"
            # cond_text 独立存, 跟 description 不一样
            assert row[1] == "帮妈妈批数学作业 1 次"
            assert row[0] != row[1]
        finally:
            _cleanup(draft_id, badge_id)
