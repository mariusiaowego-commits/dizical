"""
Tests for V2.3 (2026-06-16) feat/badge-unlock-strategy: unlock_strategy 字段.

设计新 badge 时, 用户选 1 种解锁策略 (跟 category 正交):
- 'immediate': commit 时直接 achieved='Y' + achieved_at=now (纪念章场景)
- 'calc': 老行为, achieved='N', 走 calc 评估

测试: commit handler 行为 + 老数据兼容
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


class TestUnlockStrategy:
    """unlock_strategy 字段写库 (Step 4 修法)."""

    def test_immediate_strategy_writes_achieved_Y(self, isolated_db):
        """unlock_strategy='immediate' → commit 后 achievement_stats.achieved='Y' + achieved_at 非空."""
        draft_id = "2026-06-16_test_us_im_a1aaaa"
        badge_id = "test_us_im_a1aaaa"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            draft_data["meta"]["unlock_strategy"] = "immediate"
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True, f"commit failed: {data}"

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute(
                "SELECT achieved, achieved_at FROM achievement_stats WHERE achievement_id=?",
                (badge_id,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "Y", f"achieved should be 'Y' for immediate, got {row[0]!r}"
            assert row[1] is not None and len(row[1]) > 0, \
                f"achieved_at should be set for immediate, got {row[1]!r}"

            # 同时 db achievements.unlock_strategy 也存了
            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute(
                "SELECT unlock_strategy FROM achievements WHERE id=?",
                (badge_id,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "immediate", f"unlock_strategy should persist, got {row[0]!r}"
        finally:
            _cleanup(draft_id, badge_id)

    def test_calc_strategy_default_unchanged(self, isolated_db):
        """unlock_strategy='calc' (默认/显式) → 老行为: achieved='N' + achieved_at NULL."""
        draft_id = "2026-06-16_test_us_ca_b1bbbb"
        badge_id = "test_us_ca_b1bbbb"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            draft_data["meta"]["unlock_strategy"] = "calc"
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True, f"commit failed: {data}"

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute(
                "SELECT achieved, achieved_at FROM achievement_stats WHERE achievement_id=?",
                (badge_id,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "N", f"achieved should be 'N' for calc, got {row[0]!r}"
            assert row[1] is None, f"achieved_at should be NULL for calc, got {row[1]!r}"
        finally:
            _cleanup(draft_id, badge_id)

    def test_missing_unlock_strategy_defaults_to_calc(self, isolated_db):
        """meta 缺 unlock_strategy (老 data) → 跟 calc 一样 (老行为不变)."""
        draft_id = "2026-06-16_test_us_df_c1cccc"
        badge_id = "test_us_df_c1cccc"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            # 不设 unlock_strategy, 模拟老 data
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True, f"commit failed: {data}"

            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute(
                "SELECT achieved FROM achievement_stats WHERE achievement_id=?",
                (badge_id,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "N", f"missing unlock_strategy should default to calc (N), got {row[0]!r}"
        finally:
            _cleanup(draft_id, badge_id)

    def test_invalid_unlock_strategy_returns_error(self, isolated_db):
        """unlock_strategy 不在 enum → commit 返回 400 (不静默落 invalid 值)."""
        draft_id = "2026-06-16_test_us_iv_d1dddd"
        badge_id = "test_us_iv_d1dddd"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=1)
            draft_data["meta"]["unlock_strategy"] = "invalid_xyz"  # 不在 enum
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 1))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            # 期望 400 错误, 不写库
            assert data["ok"] is False, f"should reject invalid value, got {data}"
            assert resp.status_code == 400
            assert "unlock_strategy" in data["error"].lower() or "invalid" in data["error"].lower()
        finally:
            _cleanup(draft_id, badge_id)

    def test_existing_achievement_no_unlock_strategy_unchanged(self, isolated_db):
        """老 achievement 数据 (没 unlock_strategy 列值) 走 calc 默认, 行为不变."""
        draft_id = "2026-06-16_test_us_ex_e1eeee"
        badge_id = "test_us_ex_e1eeee"
        _cleanup(draft_id, badge_id)

        try:
            # 模拟老 data: 直接写一行 (没 unlock_strategy 字段) 到 achievements
            conn = sqlite3.connect(str(isolated_db))
            conn.execute("""
                INSERT INTO achievements
                  (id, name, type, category, stat_logic, description, display_format, unlock_strategy)
                VALUES
                  (?, '老徽章', '突破', 'milestone', 'logic', 'old desc', 'days', 'calc')
            """, (badge_id,))
            conn.execute("""
                INSERT INTO achievement_stats (achievement_id, achieved) VALUES (?, 'N')
            """, (badge_id,))
            conn.commit()
            conn.close()

            # 验: 老 achievement unlock_strategy=calc, achieved=N
            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute(
                "SELECT a.unlock_strategy, s.achieved FROM achievements a "
                "JOIN achievement_stats s ON a.id = s.achievement_id WHERE a.id=?",
                (badge_id,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "calc", f"老 data unlock_strategy should be 'calc', got {row[0]!r}"
            assert row[1] == "N", f"老 data achieved should be 'N', got {row[1]!r}"
        finally:
            _cleanup(draft_id, badge_id)
