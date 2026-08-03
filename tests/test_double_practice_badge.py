"""加练狂魔 (double) badge calc 测试.

验证 _double_first_achieved_at / _has_double_practice 行为:
- 同日 ≥2 个 distinct session_id → 解锁
- 同日 1 个 session → 不解锁
- 老 entries 无 session_id → 不解锁 (算 1 个 session)
- UNIQUE date 约束下, 同日多条记录不可能, 旧 calc 永远 False
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.achievement_definitions import (
    _double_first_achieved_at,
    _has_double_practice,
)


def _make_conn() -> sqlite3.Connection:
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
    return conn


def _insert_practice(conn, date, entries):
    """entries: list of dict, 每个有 session_id + enter_time"""
    import json
    bl = json.dumps(entries, ensure_ascii=False)
    items = [{"item": e["item"], "item_id": 100, "minutes": e["minutes"]} for e in entries]
    conn.execute(
        "INSERT INTO daily_practices (date, items, total_minutes, behavior_log) "
        "VALUES (?, ?, ?, ?)",
        (date, json.dumps(items), sum(e["minutes"] for e in entries), bl),
    )
    conn.commit()


def test_double_unlocks_when_two_sessions_same_day():
    conn = _make_conn()
    _insert_practice(conn, "2026-07-29", [
        {"session_id": 1, "enter_time": "2026-07-29 10:00", "item": "x", "minutes": 3},
        {"session_id": 2, "enter_time": "2026-07-29 20:00", "item": "y", "minutes": 5},
    ])
    assert _has_double_practice(conn) is True
    assert _double_first_achieved_at(conn) == "2026-07-29"
    print("PASS: 同日 2 distinct session 解锁")


def test_double_locked_when_single_session():
    conn = _make_conn()
    _insert_practice(conn, "2026-07-29", [
        {"session_id": 1, "enter_time": "2026-07-29 10:00", "item": "x", "minutes": 5},
        {"session_id": 1, "enter_time": "2026-07-29 10:01", "item": "y", "minutes": 5},
    ])
    assert _has_double_practice(conn) is False
    assert _double_first_achieved_at(conn) is None
    print("PASS: 同日 1 distinct session 不解锁")


def test_double_locked_for_legacy_entries_no_session_id():
    conn = _make_conn()
    # 模拟老 entries: 多条但都没 session_id 字段 (初始导入)
    _insert_practice(conn, "2025-09-27", [
        {"enter_time": "2026-06-11 21:57:06.994", "item": "右手持笛", "minutes": 5},
        {"enter_time": "2026-06-11 21:57:06.994", "item": "吹 e1", "minutes": 15},
        {"enter_time": "2026-06-11 21:57:06.994", "item": "左手持笛", "minutes": 5},
    ])
    assert _has_double_practice(conn) is False
    assert _double_first_achieved_at(conn) is None
    print("PASS: 老 entries 无 session_id 不解锁")


def test_double_earliest_date_when_multiple_days():
    conn = _make_conn()
    _insert_practice(conn, "2026-07-27", [
        {"session_id": 100, "enter_time": "2026-07-27 10:00", "item": "a", "minutes": 5},
        {"session_id": 101, "enter_time": "2026-07-27 20:00", "item": "b", "minutes": 5},
    ])
    _insert_practice(conn, "2026-07-29", [
        {"session_id": 200, "enter_time": "2026-07-29 10:00", "item": "c", "minutes": 5},
        {"session_id": 201, "enter_time": "2026-07-29 20:00", "item": "d", "minutes": 5},
    ])
    # 历史上最早达到 ≥2 session 的一天
    assert _double_first_achieved_at(conn) == "2026-07-27"
    print("PASS: 返回史上首次达成日")


def test_double_empty_db():
    conn = _make_conn()
    assert _has_double_practice(conn) is False
    assert _double_first_achieved_at(conn) is None
    print("PASS: 空数据库返回 False / None")


if __name__ == "__main__":
    test_double_unlocks_when_two_sessions_same_day()
    test_double_locked_when_single_session()
    test_double_locked_for_legacy_entries_no_session_id()
    test_double_earliest_date_when_multiple_days()
    test_double_empty_db()
    print("\nAll tests passed.")