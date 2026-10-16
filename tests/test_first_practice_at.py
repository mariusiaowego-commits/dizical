"""锁: daily_practices.first_practice_at (当天最早练习时刻) + span_seconds (自然跨度)。

2026-10-09 dad ack。D5/D6 要画「一天自然跨度」:
  19:10 开始 → 20:07 结束, 中间 9 段练习 + 8 段休息.
`practice_at` 表达不了它 (语义 = 该日首次写入时刻, UPDATE 永不覆盖), 故新增:
  first_practice_at  单调取早 (补录更早的时刻要能拉早)
  span_seconds       读接口派生 = max(段落结束) − min(段落开始)
"""
from __future__ import annotations

import datetime as dt
import json

from src.database import Database, _span_seconds_from_behavior_log


def _mk(tmp_path, name="t.db") -> Database:
    return Database(str(tmp_path / name))


# ── 1. 新建行: first_practice_at = 传入的 practice_at ─────────────────────────
def test_new_row_sets_first_practice_at(tmp_path):
    db = _mk(tmp_path)
    day = dt.date(2026, 10, 9)
    item_id = db.create_practice_item("长音")
    db.save_daily_practice(
        day, [{"item": "长音", "item_id": item_id, "minutes": 10, "seconds": 600}], 10, "",
        channel="test", method="unit", practice_at="2026-10-09 19:10:00",
    )
    daily = db.get_daily_practice(day)
    assert daily["first_practice_at"] == "2026-10-09 19:10:00"
    assert daily["practice_at"] == "2026-10-09 19:10:00"


# ── 2. 同日再写更晚的时刻: first_practice_at 不变 (仍是更早那次) ──────────────
def test_later_write_keeps_earliest(tmp_path):
    db = _mk(tmp_path)
    day = dt.date(2026, 10, 9)
    item_id = db.create_practice_item("长音")
    db.save_daily_practice(day, [{"item": "长音", "item_id": item_id, "minutes": 5, "seconds": 300}], 5, "",
                           channel="test", method="unit", practice_at="2026-10-09 19:10:00")
    db.save_daily_practice(day, [{"item": "长音", "item_id": item_id, "minutes": 5, "seconds": 300}], 5, "",
                           channel="test", method="unit", practice_at="2026-10-09 20:00:00")
    daily = db.get_daily_practice(day)
    assert daily["first_practice_at"] == "2026-10-09 19:10:00", "晚的时刻不得把起点推后"
    # practice_at 语义不变: 仍是首次写入时刻
    assert daily["practice_at"] == "2026-10-09 19:10:00"


# ── 3. 同日补录一个更早的时刻: first_practice_at 被拉早 (单调取早) ────────────
def test_backfilled_earlier_time_pulls_start_earlier(tmp_path):
    db = _mk(tmp_path)
    day = dt.date(2026, 10, 9)
    item_id = db.create_practice_item("长音")
    db.save_daily_practice(day, [{"item": "长音", "item_id": item_id, "minutes": 5, "seconds": 300}], 5, "",
                           channel="test", method="unit", practice_at="2026-10-09 19:10:00")
    db.save_daily_practice(day, [{"item": "长音", "item_id": item_id, "minutes": 5, "seconds": 300}], 5, "",
                           channel="test", method="unit", practice_at="2026-10-09 18:30:00")
    daily = db.get_daily_practice(day)
    assert daily["first_practice_at"] == "2026-10-09 18:30:00"
    assert daily["practice_at"] == "2026-10-09 19:10:00", "practice_at 不该被补录改动"


# ── 4. 迁移脚本: 老行 (first_practice_at 为空) 回填 ──────────────────────────
def test_migration_backfills_legacy_rows(tmp_path):
    from src.migrate_add_first_practice_at_261009 import migrate_sqlite

    db_path = str(tmp_path / "legacy.db")
    db = Database(db_path)  # ensure-schema: 列会被建出来
    day_a, day_b, day_c = dt.date(2026, 10, 1), dt.date(2026, 10, 2), dt.date(2026, 10, 3)
    blog = json.dumps([{"enter_time": "2026-10-01 19:05:00", "minutes": 10, "seconds": 600}], ensure_ascii=False)
    with db._get_connection() as conn:  # noqa: SLF001
        cur = conn.cursor()
        # A: 有 behavior_log → 用它的首条 enter_time (比 practice_at 更准)
        cur.execute(
            "INSERT INTO daily_practices (date, items, total_minutes, total_seconds, log, practiced, behavior_log, practice_at, first_practice_at) "
            "VALUES (?, '[]', 0, 0, '', 'Y', ?, ?, NULL)",
            (day_a.isoformat(), blog, "2026-10-01 19:20:00"),
        )
        # B: 无 behavior_log → 回退 practice_at
        cur.execute(
            "INSERT INTO daily_practices (date, items, total_minutes, total_seconds, log, practiced, behavior_log, practice_at, first_practice_at) "
            "VALUES (?, '[]', 0, 0, '', 'Y', '', ?, NULL)",
            (day_b.isoformat(), "2026-10-02 20:00:00"),
        )
        # C: 两者都没有 → 留 NULL
        cur.execute(
            "INSERT INTO daily_practices (date, items, total_minutes, total_seconds, log, practiced, behavior_log, practice_at, first_practice_at) "
            "VALUES (?, '[]', 0, 0, '', 'Y', '', NULL, NULL)",
            (day_c.isoformat(),),
        )
        conn.commit()

    migrate_sqlite(db_path, apply=True)

    assert db.get_daily_practice(day_a)["first_practice_at"] == "2026-10-01 19:05:00", "应优先 behavior_log 首条"
    assert db.get_daily_practice(day_b)["first_practice_at"] == "2026-10-02 20:00:00", "无 log 回退 practice_at"
    assert db.get_daily_practice(day_c)["first_practice_at"] is None

    # 幂等: 再跑一次, 已填的行不被覆盖 (A 不会被 practice_at 的 19:20 拉后)
    migrate_sqlite(db_path, apply=True)
    assert db.get_daily_practice(day_a)["first_practice_at"] == "2026-10-01 19:05:00"


# ── 5. DDL 幂等: 连跑两次 ensure-schema, 列只有一个 ─────────────────────────
def test_ddl_idempotent(tmp_path):
    db_path = str(tmp_path / "idem.db")
    Database(db_path)
    db2 = Database(db_path)  # 第二次 init 会再跑 ensure-schema
    with db2._get_connection() as conn:  # noqa: SLF001
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(daily_practices)")
        cols = [r[1] for r in cur.fetchall()]
    assert cols.count("first_practice_at") == 1


# ── 6. span_seconds: 9 段样本 → 末段结束 − 首段开始 ─────────────────────────
def test_span_seconds_across_segments(tmp_path):
    db = _mk(tmp_path)
    day = dt.date(2026, 10, 9)
    # 19:10 起 9 段, 每段 10 分钟, 段间休息 3 分钟 → 末段结束 19:10 + 9*13min
    log = []
    t = dt.datetime(2026, 10, 9, 19, 10, 0)
    for i in range(9):
        log.append({"enter_time": t.strftime("%Y-%m-%d %H:%M:%S"), "item": f"科目{i}", "minutes": 10, "seconds": 600})
        t += dt.timedelta(minutes=13)
    expected = int((log[-1] and (dt.datetime.fromisoformat(log[-1]["enter_time"]) + dt.timedelta(seconds=600)
                                - dt.datetime.fromisoformat(log[0]["enter_time"])).total_seconds()))
    with db._get_connection() as conn:  # noqa: SLF001
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO daily_practices (date, items, total_minutes, total_seconds, log, practiced, behavior_log) "
            "VALUES (?, '[]', 90, 5400, '', 'Y', ?)",
            (day.isoformat(), json.dumps(log, ensure_ascii=False)),
        )
        conn.commit()

    daily = db.get_daily_practice(day)
    assert daily["span_seconds"] == expected
    # 纯函数口径核对: 108 分钟 = 8*13 + 10 分钟
    assert daily["span_seconds"] == (8 * 13 + 10) * 60
    assert _span_seconds_from_behavior_log([]) == 0
    assert _span_seconds_from_behavior_log(None) == 0
