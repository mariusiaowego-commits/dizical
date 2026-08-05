"""
Sprint 09 P0-22 (PR-E): audit log 事务对齐测试

目标: 业务失败 → 整事务 rollback → practice_audit_log 也不该有该行.

覆盖:
1. save_daily_practice 成功 (channel/method) → audit 有行
2. save_daily_practice 业务失败 (无效 item_id) → audit 无行 (rollback 原子性)
3. save_practice_session_and_daily_summary 成功 → audit 有行
4. delete_practice_session 成功 → audit 有行
5. 无 channel/method → 不写 audit (兼容旧调用)
"""
import os
import tempfile

import pytest


@pytest.fixture()
def db():
    """临时 SQLite Database 实例, 每次测试独立文件."""
    from src.database import Database
    from src import models

    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['DATABASE_URL'] = ''
    original = models.settings.db_path
    models.settings.db_path = path

    import src.database as db_module
    db_module.db = Database(db_path=path)
    yield db_module.db, path

    models.settings.db_path = original
    try:
        os.unlink(path)
    except Exception:
        pass


def _count_audit(db, method):
    with db._get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM practice_audit_log WHERE method = ?", (method,)
        ).fetchone()
    return row["c"]


def _seed_item(db):
    """插入一个练习科目, 返回 item_id."""
    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO practice_items (item_id, name, category_id, sort_order, is_active) VALUES (?, ?, NULL, 0, 1)",
                    (9001, '音阶',))
        conn.commit()
    return 9001


def test_save_daily_success_writes_audit(db):
    d, path = db
    _seed_item(d)
    import datetime as dt
    d.save_daily_practice(
        dt.date(2026, 8, 5),
        [{'item': '音阶', 'item_id': 9001, 'minutes': 5}],
        5, '',
        channel='web', method='config-records',
    )
    assert _count_audit(d, 'config-records') == 1


def test_save_daily_failure_no_audit(db):
    d, path = db
    import datetime as dt
    # 无效 item_id → ValueError (业务失败)
    with pytest.raises(ValueError):
        d.save_daily_practice(
            dt.date(2026, 8, 5),
            [{'item': '不存在', 'item_id': 99999, 'minutes': 5}],
            5, '',
            channel='web', method='config-records',
        )
    # 事务 rollback → audit 无该行
    assert _count_audit(d, 'config-records') == 0
    # daily 也没有该日记录
    with d._get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM daily_practices WHERE date = '2026-08-05'").fetchone()
    assert row["c"] == 0


def test_save_daily_no_channel_no_audit(db):
    d, path = db
    _seed_item(d)
    import datetime as dt
    # 无 channel/method → 不写 audit (兼容旧调用)
    d.save_daily_practice(
        dt.date(2026, 8, 5),
        [{'item': '音阶', 'item_id': 9001, 'minutes': 5}],
        5, '',
    )
    assert _count_audit(d, 'config-records') == 0


def test_save_session_success_writes_audit(db):
    d, path = db
    _seed_item(d)
    import datetime as dt
    s = d.save_practice_session_and_daily_summary(
        dt.date(2026, 8, 5), '音阶', 9001, 5, '♪', 80, '练习', 'manual',
    )
    assert s is not None
    assert _count_audit(d, 'save_session') == 1


def test_delete_session_writes_audit(db):
    d, path = db
    _seed_item(d)
    import datetime as dt
    s = d.save_practice_session_and_daily_summary(
        dt.date(2026, 8, 5), '音阶', 9001, 5, '♪', 80, '练习', 'manual',
    )
    sid = s['id']
    d.delete_practice_session(sid, expected_version=1)
    assert _count_audit(d, 'delete_session') == 1
