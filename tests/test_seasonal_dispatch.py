"""seasonal badge dispatch 测试 (2026-08-03 修复).

bug: _calc_seasonal 之前在 `if seasonal_type == "monthly":` 分支里直接 return
月度通用 fallback, 导致 aid-specific 分支 (week_champ / full_month / top1 /
early_riser / total_60) 永远走不到, 全部 cond 都返"当月累计 ≥ 60 分钟".

修法: 把 aid-specific 分支移进 monthly 分支, fallback 在最后.
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.achievement_definitions import _calc_seasonal


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE daily_practices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL UNIQUE,
            items TEXT NOT NULL DEFAULT '[]',
            total_minutes INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            log TEXT,
            practiced TEXT NOT NULL DEFAULT 'Y',
            behavior_log TEXT NOT NULL DEFAULT '[]',
            practice_at DATETIME
        )
    """)
    # weekly_assignments 表 (week_champ 用)
    conn.execute("""
        CREATE TABLE weekly_assignments (
            stage_order INTEGER,
            stage_start DATE,
            stage_end DATE
        )
    """)
    conn.execute("""
        CREATE TABLE practice_items (
            item_id INTEGER PRIMARY KEY,
            name TEXT,
            total_minutes INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0
        )
    """)
    return conn


def test_week_champ_returns_correct_cond():
    """week_champ 不再返'月累计 60 分钟' fallback."""
    conn = _make_conn()
    # 一些练习 (本周 stage 范围内)
    for d in ["2026-08-01", "2026-08-02"]:
        conn.execute("INSERT INTO daily_practices (date, total_minutes) VALUES (?, ?)", (d, 30))
    # 上下 stage (week_champ 需要)
    conn.execute("INSERT INTO weekly_assignments VALUES (1, '2026-07-20', '2026-07-26')")
    conn.execute("INSERT INTO weekly_assignments VALUES (2, '2026-07-27', '2026-08-02')")
    conn.commit()
    r = _calc_seasonal(conn, "week_champ", "monthly", date(2026, 8, 2),
                       streak=2, total_mins=60, all_item_ids=set())
    assert "月累计" not in r.condition, f"应不再是 fallback, got: {r.condition}"
    assert "本周" in r.condition, f"应展示本周/上周对比, got: {r.condition}"
    print(f"PASS: week_champ 独立 cond = '{r.condition}'")


def test_top1_returns_correct_cond():
    """top1 不再返 fallback.

    注: _get_top_items 有 pre-existing SQL bug (用 dp.date alias 但 from 没 alias).
    这里验证 _calc_seasonal 优先进入 top1 分支 (而非 fallback).
    通过 mock _get_top_items 避免触发 pre-existing bug.
    """
    from unittest.mock import patch as _patch
    conn = _make_conn()
    conn.execute(
        "INSERT INTO daily_practices (date, items, total_minutes) "
        "VALUES ('2026-08-01', '[{\"item_id\":100,\"minutes\":30,\"item\":\"长音\"}]', 30)"
    )
    conn.commit()
    with _patch("src.achievement_definitions._get_top_items",
                return_value=[("长音", 30)]):
        r = _calc_seasonal(conn, "top1", "monthly", date(2026, 8, 1),
                           streak=1, total_mins=30, all_item_ids={100})
    assert "月累计" not in r.condition, f"got: {r.condition}"
    assert "当月第1" in r.condition, f"got: {r.condition}"
    print(f"PASS: top1 独立 cond = '{r.condition}'")


def test_full_month_returns_correct_cond():
    """full_month 不再返 fallback."""
    conn = _make_conn()
    conn.execute("INSERT INTO daily_practices (date, total_minutes) VALUES ('2026-08-01', 100)")
    conn.execute("INSERT INTO daily_practices (date, total_minutes) VALUES ('2026-07-15', 50)")
    conn.commit()
    r = _calc_seasonal(conn, "full_month", "monthly", date(2026, 8, 1),
                       streak=1, total_mins=100, all_item_ids=set())
    assert "月累计" not in r.condition, f"got: {r.condition}"
    assert "本月" in r.condition and "上月" in r.condition, f"got: {r.condition}"
    print(f"PASS: full_month 独立 cond = '{r.condition}'")


def test_early_riser_returns_correct_cond():
    """early_riser 按小时判断, 不再返 fallback."""
    conn = _make_conn()
    conn.execute(
        "INSERT INTO daily_practices (date, total_minutes, practice_at) VALUES (?, ?, ?)",
        ("2026-05-17", 30, "2026-05-17 19:30:00"),
    )
    conn.commit()
    r = _calc_seasonal(conn, "early_riser", "monthly", date(2026, 8, 2),
                       streak=0, total_mins=30, all_item_ids=set())
    assert "月累计" not in r.condition, f"got: {r.condition}"
    assert "20:00" in r.condition or "早于" in r.condition, f"got: {r.condition}"
    print(f"PASS: early_riser 独立 cond = '{r.condition}'")


def test_total_60_still_fallback():
    """total_60 本身就是月度 60 分钟, cond 应该是 fallback 文本 (允许)."""
    conn = _make_conn()
    conn.execute("INSERT INTO daily_practices (date, total_minutes) VALUES ('2026-08-01', 70)")
    conn.commit()
    r = _calc_seasonal(conn, "total_60", "monthly", date(2026, 8, 1),
                       streak=1, total_mins=70, all_item_ids=set())
    assert r.achieved is True
    assert "60 分钟" in r.condition
    print(f"PASS: total_60 fallback = '{r.condition}'")


def test_unknown_monthly_falls_back_to_60min():
    """未知 monthly aid → 走 fallback 60 分钟."""
    conn = _make_conn()
    conn.execute("INSERT INTO daily_practices (date, total_minutes) VALUES ('2026-08-01', 70)")
    conn.commit()
    r = _calc_seasonal(conn, "totally_unknown_aid", "monthly", date(2026, 8, 1),
                       streak=1, total_mins=70, all_item_ids=set())
    assert "当月累计 ≥ 60 分钟" in r.condition
    print(f"PASS: 未知 monthly aid fallback = '{r.condition}'")


if __name__ == "__main__":
    test_week_champ_returns_correct_cond()
    test_top1_returns_correct_cond()
    test_full_month_returns_correct_cond()
    test_early_riser_returns_correct_cond()
    test_total_60_still_fallback()
    test_unknown_monthly_falls_back_to_60min()
    print("\nAll tests passed.")