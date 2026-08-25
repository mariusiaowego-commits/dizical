"""Sprint stage-stage (2026-08-25): save_weekly_assignment stage_order 新算法。

背景: 云端 weekly_assignments 缺 UNIQUE(lesson_date) 索引 + stage_order 只按 attended 排序,
导致 cancelled/scheduled 课录作业时 stage_order 算不出 (NULL), 被 list_stages 过滤,
08-16 后练习无 stage 承接, stage 停在 18.

新算法 (agy review 确认): stage_order = 该课之前已录作业的课日数 + 1
  - 2026-03-14 起的正式 stage 序列 (排除旧体系负号 stage_order 的早期大课)
  - 任意课 (attended/scheduled/cancelled 任一) 录了 assignment 即拿下一个连续编号
  - 历史已录作业的课编号不变 (不漂移)
"""
import datetime as dt
import os
import tempfile

import pytest


@pytest.fixture
def fresh_db():
    """新建临时 SQLite DB + schema + 测试数据."""
    from src.database import Database
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    db = Database(db_path=path)
    yield db, path
    os.unlink(path)


def _insert_lessons(db, rows_sql):
    conn = db._get_connection()
    cur = conn.cursor()
    cur.executescript("""
""" + rows_sql + """
    """)
    conn.commit()


def _insert_wa(db, rows_sql):
    conn = db._get_connection()
    cur = conn.cursor()
    cur.executescript("""
""" + rows_sql + """
    """)
    conn.commit()


# ── 历史编号不漂移 ──────────────────────────────────────────────

def test_history_user_stage_order_stable_when_new_cancelled_added(fresh_db):
    """已有正式 stage 1..N (有作业课), 加一个 cancelled 课录作业 → 拿到 N+1, 历史不变."""
    db, _ = fresh_db
    # 正式 stage 1-3 (attended 课有作业)
    _insert_lessons(db, """
        INSERT INTO lessons (date, time, status) VALUES
            ('2026-03-14', '10:00', 'attended'),
            ('2026-03-28', '10:00', 'attended'),
            ('2026-04-11', '10:00', 'attended'),
            ('2026-04-18', '10:00', 'cancelled')
    """)
    _insert_wa(db, """
        INSERT INTO weekly_assignments
            (lesson_date, stage_start, stage_end, stage_order, items)
        VALUES
            ('2026-03-14', '2026-03-15', '2026-03-28', 1, '[]'),
            ('2026-03-28', '2026-03-29', '2026-04-11', 2, '[]'),
            ('2026-04-11', '2026-04-12', '2026-04-18', 3, '[]')
    """)
    # cancelled 课 04-18 录作业 → 应得 stage_order=4
    db.save_weekly_assignment(
        dt.date(2026, 4, 18),
        [{"item": "长音练习", "requirements": "", "metronome": ""}],
        notes=None,
    )
    wa = db.get_weekly_assignment(dt.date(2026, 4, 18))
    assert wa['stage_order'] == 4, f"cancelled 课录作业应得 stage_order=4, 实际 {wa['stage_order']}"
    # 历史 1-3 不变
    assert db.get_weekly_assignment(dt.date(2026, 3, 14))['stage_order'] == 1
    assert db.get_weekly_assignment(dt.date(2026, 3, 28))['stage_order'] == 2
    assert db.get_weekly_assignment(dt.date(2026, 4, 11))['stage_order'] == 3


# ── cancelled/scheduled 课连续编号 ──────────────────────────────

def test_cancelled_lesson_not_null_stage_order(fresh_db):
    """cancelled 课录作业: stage_order 不再是 NULL (旧逻辑), 而是连续编号."""
    db, _ = fresh_db
    _insert_lessons(db, """
        INSERT INTO lessons (date, time, status) VALUES
            ('2026-03-14', '10:00', 'attended'),
            ('2026-04-18', '10:00', 'cancelled')
    """)
    _insert_wa(db, """
        INSERT INTO weekly_assignments
            (lesson_date, stage_start, stage_end, stage_order, items)
        VALUES ('2026-03-14', '2026-03-15', '2026-03-21', 1, '[]')
    """)
    db.save_weekly_assignment(
        dt.date(2026, 4, 18),
        [{"item": "取消课补练", "requirements": "", "metronome": ""}],
    )
    wa = db.get_weekly_assignment(dt.date(2026, 4, 18))
    assert wa['stage_order'] is not None, "cancelled 课 stage_order 不应 NULL"
    assert wa['stage_order'] == 2


def test_scheduled_lesson_prebook_gets_stage(fresh_db):
    """scheduled 课提前录作业 → 立即分配下一个连续 stage_order (供预习/打卡)."""
    db, _ = fresh_db
    _insert_lessons(db, """
        INSERT INTO lessons (date, time, status) VALUES
            ('2026-03-14', '10:00', 'attended'),
            ('2026-04-11', '10:00', 'scheduled')
    """)
    _insert_wa(db, """
        INSERT INTO weekly_assignments
            (lesson_date, stage_start, stage_end, stage_order, items)
        VALUES ('2026-03-14', '2026-03-15', '2026-03-21', 1, '[]')
    """)
    db.save_weekly_assignment(
        dt.date(2026, 4, 11),
        [{"item": "预习内容", "requirements": "", "metronome": ""}],
    )
    wa = db.get_weekly_assignment(dt.date(2026, 4, 11))
    assert wa['stage_order'] == 2


# ── 旧体系负号 stage 不影响 ─────────────────────────────────────

def test_legacy_negative_stage_not_counted(fresh_db):
    """2025-11~2026-03-07 旧体系负 stage_order 行不被计入, 新 stage 继续从 1..N 排."""
    db, _ = fresh_db
    # 旧体系负行 (早期大课, stage_end 指向 03-14 分界)
    _insert_wa(db, """
        INSERT INTO weekly_assignments
            (lesson_date, stage_start, stage_end, stage_order, items)
        VALUES
            ('2025-11-08', '2025-11-09', '2026-03-14', -1, '[]'),
            ('2025-11-15', '2025-11-16', '2026-03-14', -2, '[]')
    """)
    _insert_lessons(db, """
        INSERT INTO lessons (date, time, status) VALUES ('2026-03-14', '10:00', 'attended')
    """)
    # 新体系第一条正式课 03-14 → stage_order 应为 1 (负行不被计入)
    db.save_weekly_assignment(
        dt.date(2026, 3, 14),
        [{"item": "正式课", "requirements": "", "metronome": ""}],
    )
    wa = db.get_weekly_assignment(dt.date(2026, 3, 14))
    assert wa['stage_order'] == 1, f"旧体系负行不应计入, 实际 {wa['stage_order']}"