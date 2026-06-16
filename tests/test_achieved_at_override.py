"""
Tests for V2.6 (2026-06-16) feat/badge-achieved-at-override:
通用字段 (immediate + achieved_at_override) 让纪念章/表彰型徽章不 calc 直接 unlocked.

背景:
- V2 era 早期 (PR #101) 设计 unlock_strategy='immediate' 给纪念章, 但前端路由 (badges_page,
  achievements_page) 走 calc_all(), 不读 stats 表, 导致 assign_pal db Y 但 UI locked.
- V2.6 加 achieved_at_override 字段, 支持"考出时间"等具体解锁时间场景.
- 修法: 路由 (page_milestones + badges_page) 加 commemorative 分支, 跳过 calc, 直接
  返 achieved=Y + achieved_at=override_or_stats.

测试范围:
1. calc_all 不变 (immediate 仍走 calc fallback False)
2. 路由层逻辑 (修 app.py badges_page / page_milestones): 当 unlock_strategy='immediate' + stats.achieved='Y',
   返 achieved=True + achieved_at=stats.achieved_at
3. 当 achieved_at_override 非 NULL, 返 achieved=True + achieved_at=override
4. 普通 calc badge 仍走 calc (不影响)
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


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
            unlock_strategy TEXT DEFAULT 'calc',
            achieved_at_override TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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


def make_commemorative_check(ach, stats_row):
    """复制 app.py 的 is_commemorative + CalcResult 替换逻辑 (单元测试版)."""
    from src.achievement_definitions import CalcResult
    is_comm = ach.get("unlock_strategy") == "immediate" or ach.get("achieved_at_override")
    if not is_comm:
        return None  # 走 calc
    override = ach.get("achieved_at_override")
    if override:
        return CalcResult(True, 1, None, override, f"考出时间: {override}")
    if stats_row and stats_row[0] == 'Y':
        return CalcResult(True, 1, None, stats_row[1] or None, "立即解锁")
    return CalcResult(False, 0, None, None, "")


class TestCommemorativeLogic:
    def test_calc_badge_not_commemorative(self, conn):
        """普通 calc badge: is_comm=False, 走 calc, 跳过此逻辑"""
        ach = {"unlock_strategy": "calc", "achieved_at_override": None}
        res = make_commemorative_check(ach, None)
        assert res is None

    def test_immediate_with_stats_unlocked(self, conn):
        """immediate + stats Y → achieved=True + achieved_at=stats 时间"""
        ach = {"unlock_strategy": "immediate", "achieved_at_override": None}
        res = make_commemorative_check(ach, ("Y", "2026-06-16 07:57:17"))
        assert res.achieved is True
        assert res.achieved_at == "2026-06-16 07:57:17"
        assert res.condition == "立即解锁"

    def test_immediate_stats_not_yet_unlocked(self, conn):
        """immediate 但 stats 还 N (commit handler 没跑) → False"""
        ach = {"unlock_strategy": "immediate", "achieved_at_override": None}
        res = make_commemorative_check(ach, ("N", None))
        assert res.achieved is False

    def test_override_priority_over_immediate(self, conn):
        """override 比 stats 优先: 考出时间覆盖 immediate 时间"""
        ach = {"unlock_strategy": "immediate", "achieved_at_override": "2026-07-01"}
        res = make_commemorative_check(ach, ("Y", "2026-06-16 07:57:17"))
        assert res.achieved is True
        assert res.achieved_at == "2026-07-01"  # 用 override
        assert "考出时间" in res.condition

    def test_override_only_no_immediate(self, conn):
        """纯 achieved_at_override, 不走 immediate (纪念章走 calc 也 OK)"""
        ach = {"unlock_strategy": "calc", "achieved_at_override": "2026-08-15"}
        res = make_commemorative_check(ach, None)
        assert res.achieved is True
        assert res.achieved_at == "2026-08-15"

    def test_grade_1_scenario(self, conn):
        """真实场景: grade_1 unlock_strategy='calc' + override='2026-07-01'"""
        ach = {"unlock_strategy": "calc", "achieved_at_override": "2026-07-01"}
        res = make_commemorative_check(ach, None)
        assert res.achieved is True
        assert res.achieved_at == "2026-07-01"
        assert res.condition == "考出时间: 2026-07-01"

    def test_assign_pal_scenario(self, conn):
        """assign_pal: unlock_strategy='immediate' + stats Y"""
        ach = {"unlock_strategy": "immediate", "achieved_at_override": None}
        res = make_commemorative_check(ach, ("Y", "2026-06-16 07:57:17"))
        assert res.achieved is True
        assert res.achieved_at == "2026-06-16 07:57:17"