"""streak_* / recovery_first_practice_* 进度展示测试.

验证 _calc_milestone 对 streak_N / recovery_N:
- 已解锁: "你在 YYYY-MM-DD 第一次连着打卡 N 天" (历史首次)
- 未解锁 streak: "连着打卡 N 天就能拿到（当前连续 X 天，还差 N-X 天）"
- 未解锁 recovery: "自2026-07-08起累计打卡 N 天（当前 X/N，还差 N-X 天）"
- computed_value 未解锁时 = 当前 streak (用于前端模板拼)
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.achievement_definitions import (
    _calc_milestone,
    _get_consecutive_streak,
    _recovery_current_streak,
)


def _make_conn(practices: list[tuple[str, int]]):
    """practices: list of (date_str, total_minutes)."""
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
    for d, m in practices:
        conn.execute(
            "INSERT INTO daily_practices (date, items, total_minutes) VALUES (?, '[]', ?)",
            (d, m),
        )
    conn.commit()
    return conn


def _calc(conn, aid: str, today: date):
    """helper: 跑一次 _calc_milestone, 拿 result."""
    from src.achievement_definitions import _get_practice_dates, _get_consecutive_streak
    dates = _get_practice_dates(conn)
    streak = _get_consecutive_streak(dates, today)
    return _calc_milestone(
        conn, aid, stats={}, streak=streak, total_mins=0,
        top_items=[], has_all_items=False, all_items_achieved_at=None,
        has_double=False, today=today,
    )


# ── streak 测试 ──────────────────────────────────────────────


def test_streak_unlocked_shows_achieved_date():
    # 7 天连续 (包含 today)
    conn = _make_conn([(f"2026-08-0{i}", 10) for i in range(2, 9)])  # 8-02..8-08
    r = _calc(conn, "streak_7", date(2026, 8, 8))
    assert r.achieved is True
    assert r.achieved_at == "2026-08-08"  # 史上首次达成 ≥7 天的那天 (连续第 7 天)
    assert "你在 2026-08-08 第一次连着打卡 7 天" == r.condition
    assert r.computed_value == 7
    print("PASS: streak_7 已解锁展示达成日")


def test_streak_locked_shows_progress():
    # 当前 9 天连续 (streak_100 没达成)
    conn = _make_conn([(f"2026-07-{i:02d}", 10) for i in range(25, 32)] +
                      [(f"2026-08-{i:02d}", 10) for i in range(1, 3)])  # 7-25..8-02 = 9 天
    r = _calc(conn, "streak_100", date(2026, 8, 2))
    assert r.achieved is False
    assert "当前连续" in r.condition, f"got: {r.condition}"
    assert "还差 91 天" in r.condition, f"got: {r.condition}"
    assert r.computed_value == 9  # 当前 streak
    print("PASS: streak_100 未解锁展示进度 (当前 9, 还差 91)")


def test_streak_locked_zero_progress():
    # today 跟 yesterday 都没练, streak 才 0
    conn = _make_conn([(f"2026-08-0{i}", 10) for i in range(2, 5)])  # 8-02..8-04
    r = _calc(conn, "streak_7", date(2026, 8, 6))
    assert r.achieved is False
    assert "当前连续 0 天" in r.condition, f"got: {r.condition}"
    assert "还差 7 天" in r.condition, f"got: {r.condition}"
    print("PASS: streak_7 today+yesterday 都没练, 显示 0")


# ── recovery 测试 ─────────────────────────────────────────────


def test_recovery_unlocked():
    # 烫伤日 2026-07-08, 7-08..7-14 连续 7 天
    conn = _make_conn([(f"2026-07-{i:02d}", 10) for i in range(8, 15)])
    r = _calc(conn, "recovery_first_practice_7", date(2026, 7, 14))
    assert r.achieved is True
    assert r.achieved_at == "2026-07-14"
    assert "你在 2026-07-14 烫伤后连着打卡 7 天" == r.condition
    print("PASS: recovery_7 已解锁")


def test_recovery_locked_with_progress():
    # 烫伤日 2026-07-08, 当前 9 天 (7-25..8-02), 但 recovery_21 没达成
    conn = _make_conn([(f"2026-07-{i:02d}", 10) for i in range(25, 32)] +
                      [(f"2026-08-{i:02d}", 10) for i in range(1, 3)])
    r = _calc(conn, "recovery_first_practice_21", date(2026, 8, 2))
    assert r.achieved is False
    assert "自2026-07-08起累计打卡 21 天" in r.condition, f"got: {r.condition}"
    assert "当前 9/21" in r.condition, f"got: {r.condition}"
    assert "还差 12 天" in r.condition, f"got: {r.condition}"
    assert r.computed_value == 9
    print("PASS: recovery_21 未解锁展示进度 (当前 9/21, 还差 12)")


def test_recovery_excludes_practice_before_injury():
    # 烫伤前有练习 (6-27..7-04 共 8 天) 不算 recovery streak
    conn = _make_conn(
        [(f"2026-06-{i:02d}", 10) for i in range(27, 31)] +
        [(f"2026-07-0{i}", 10) for i in range(1, 5)] +  # 6-27..7-04 烫伤前
        [(f"2026-07-{i:02d}", 10) for i in range(25, 32)] +
        [(f"2026-08-{i:02d}", 10) for i in range(1, 3)]   # 7-25..8-02 烫伤后 9 天
    )
    cur = _recovery_current_streak(conn, "2026-07-08", date(2026, 8, 2))
    assert cur == 9, f"recovery_current_streak 应排除烫伤前, got {cur}"
    print(f"PASS: recovery_current_streak = {cur} (排除烫伤前)")


def test_recovery_streak_zero_when_today_not_practiced():
    conn = _make_conn([(f"2026-07-{i:02d}", 10) for i in range(10, 15)])  # 7-10..7-14
    cur = _recovery_current_streak(conn, "2026-07-08", date(2026, 7, 20))
    assert cur == 0
    print("PASS: today 没练 → recovery streak = 0")


# ── _get_consecutive_streak sanity ─────────────────────────────


def test_get_consecutive_streak_basic():
    # dates 必须倒序 (跟 _get_practice_dates 一致)
    dates = ["2026-08-03", "2026-08-02", "2026-08-01"]
    assert _get_consecutive_streak(dates, date(2026, 8, 3)) == 3
    # today=8-04 没练, 但 yesterday 8-03 有 → fallback 到 8-03 数
    assert _get_consecutive_streak(dates, date(2026, 8, 4)) == 3
    # today=8-02, dates 倒序 [8-03,8-02,8-01] 但 today=8-02 在 dset → 从 8-02 数到 8-01 = 2
    assert _get_consecutive_streak(dates, date(2026, 8, 2)) == 2
    # today=8-02, dates 倒序 [8-02, 8-01] → today 在, 数 2
    assert _get_consecutive_streak(["2026-08-02", "2026-08-01"], date(2026, 8, 2)) == 2
    print("PASS: _get_consecutive_streak 基本场景")


if __name__ == "__main__":
    test_streak_unlocked_shows_achieved_date()
    test_streak_locked_shows_progress()
    test_streak_locked_zero_progress()
    test_recovery_unlocked()
    test_recovery_locked_with_progress()
    test_recovery_excludes_practice_before_injury()
    test_recovery_streak_zero_when_today_not_practiced()
    test_get_consecutive_streak_basic()
    print("\nAll tests passed.")