"""
Tests for V2.5 (2026-06-16) feat/badge-night-owl-calc: night_owl calc 规则

背景: night_owl 是 milestone 类型 (db category='milestone'), 但 _calc_milestone
没 night_owl 处理分支, 走通用 fallback return CalcResult(False, ...), UI 永远 locked.

修法: 加 calc 分支, 找历史任意一天 practice_at CST hour >= 20 → unlock.
跟 early_riser/little_chick_commander/first_to_act 一样的 pattern
(2026-06-13 PR #87 era 拍板"永久解锁版").
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Use isolated tmp db (跟 test_badge_commit_version_sync 同模式)
@pytest.fixture
def conn(tmp_path):
    db = sqlite3.connect(str(tmp_path / "test.db"))
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE achievements (
            id TEXT PRIMARY KEY, name TEXT, type TEXT, category TEXT,
            stat_logic TEXT, description TEXT, display_format TEXT,
            threshold INTEGER, unlocked_template TEXT, placeholder TEXT,
            locked_template TEXT, sort_order INTEGER DEFAULT 0,
            seasonal_type TEXT DEFAULT 'monthly', cond_text TEXT,
            unlock_strategy TEXT DEFAULT 'calc', created_at DATETIME
        );
        CREATE TABLE achievement_stats (
            achievement_id TEXT PRIMARY KEY,
            achieved TEXT NOT NULL DEFAULT 'N',
            achieved_at DATETIME, raw_stats TEXT NOT NULL DEFAULT '{}',
            computed_value INTEGER
        );
        CREATE TABLE daily_practices (
            date TEXT PRIMARY KEY, items TEXT, total_minutes INTEGER,
            created_at DATETIME, practice_at TEXT, behavior_log TEXT
        );
    """)
    yield db
    db.close()


class TestNightOwlCalc:
    def test_unlocks_when_practice_at_cst_hour_ge_20(self, conn):
        """CST hour >= 20 应 unlock"""
        # 1 条 20:30 练习
        conn.execute(
            "INSERT INTO daily_practices (date, total_minutes, practice_at) "
            "VALUES (?, ?, ?)",
            ("2026-06-13", 25, "2026-06-13 20:30:00.000")
        )
        conn.execute(
            "INSERT INTO achievements (id, name, type, category, stat_logic, display_format) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("night_owl", "夜猫子", "突破", "milestone",
             "晚上 8 点后 (CST 20:00) 还在练习", "achieved_flag")
        )
        conn.commit()

        from src.achievement_definitions import _calc_milestone
        result = _calc_milestone(
            conn, "night_owl", stats={}, streak=1, total_mins=25,
            top_items=[], has_all_items=False, all_items_achieved_at=None,
            has_double=False
        )
        assert result.achieved is True
        assert result.achieved_at == "2026-06-13"

    def test_no_unlock_when_no_evening_practice(self, conn):
        """没有 20:00 后练习 → 不 unlock"""
        conn.execute(
            "INSERT INTO daily_practices (date, total_minutes, practice_at) "
            "VALUES (?, ?, ?)",
            ("2026-06-13", 25, "2026-06-13 12:30:00.000")
        )
        conn.execute(
            "INSERT INTO achievements (id, name, type, category, stat_logic, display_format) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("night_owl", "夜猫子", "突破", "milestone",
             "晚上 8 点后 (CST 20:00) 还在练习", "achieved_flag")
        )
        conn.commit()

        from src.achievement_definitions import _calc_milestone
        result = _calc_milestone(
            conn, "night_owl", stats={}, streak=1, total_mins=25,
            top_items=[], has_all_items=False, all_items_achieved_at=None,
            has_double=False
        )
        assert result.achieved is False
        assert result.achieved_at is None

    def test_unlocks_at_20_00_strictly(self, conn):
        """CST hour = 20:00 应 unlock (用户拍板 21:00 我改 20:00)"""
        conn.execute(
            "INSERT INTO daily_practices (date, total_minutes, practice_at) "
            "VALUES (?, ?, ?)",
            ("2026-06-13", 25, "2026-06-13 20:00:00.000")
        )
        conn.execute(
            "INSERT INTO achievements (id, name, type, category, stat_logic, display_format) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("night_owl", "夜猫子", "突破", "milestone",
             "晚上 8 点后 (CST 20:00) 还在练习", "achieved_flag")
        )
        conn.commit()

        from src.achievement_definitions import _calc_milestone
        result = _calc_milestone(
            conn, "night_owl", stats={}, streak=1, total_mins=25,
            top_items=[], has_all_items=False, all_items_achieved_at=None,
            has_double=False
        )
        assert result.achieved is True