"""Sprint 26081001: list_stages 过滤 stage_order 无效值 (NULL + 0 + negative? no).

设计:
- list_stages 必须过滤 stage_order IS NULL / stage_order = 0 (老 NULL + 新 bug 数据)
- 保留所有 stage_order > 0 的行 (包括浮点 0.01-0.12 表示早期大课)
- 排序 ORDER BY stage_order DESC (浮点 OK, MySQL/SQLite 都支持)
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


def _insert_wa(db, rows_sql):
    """helper: 插入 weekly_assignments rows (用 _get_connection 跟 list_stages 同 connection 行为)."""
    conn = db._get_connection()
    cur = conn.cursor()
    cur.executescript("""
""" + rows_sql + """
    """)
    conn.commit()


def test_filter_null_stage_order(fresh_db):
    """stage_order=NULL 行被过滤."""
    db, _ = fresh_db
    _insert_wa(db, """
        INSERT INTO weekly_assignments (lesson_date, stage_start, stage_end, stage_order) VALUES
            ('2026-03-01', '2026-03-02', '2026-03-08', NULL),
            ('2026-04-01', '2026-04-02', '2026-04-08', NULL)
    """)
    stages = db.list_stages()
    assert all(s['stage_order'] is not None for s in stages), "NULL 行应被过滤"


def test_filter_zero_stage_order(fresh_db):
    """stage_order=0 行被过滤."""
    db, _ = fresh_db
    _insert_wa(db, """
        INSERT INTO weekly_assignments (lesson_date, stage_start, stage_end, stage_order) VALUES
            ('2026-03-01', '2026-03-02', '2026-03-08', 0),
            ('2026-04-01', '2026-04-02', '2026-04-08', 0)
    """)
    stages = db.list_stages()
    assert len(stages) == 0, f"stage_order=0 行应全被过滤, 实际返回 {len(stages)} 条"


def test_normal_stage_order_kept(fresh_db):
    """stage_order=1-5 行保留 + DESC 排序."""
    db, _ = fresh_db
    _insert_wa(db, """
        INSERT INTO weekly_assignments (lesson_date, stage_start, stage_end, stage_order) VALUES
            ('2026-03-01', '2026-03-02', '2026-03-08', 1),
            ('2026-04-01', '2026-04-02', '2026-04-08', 2),
            ('2026-05-01', '2026-05-02', '2026-05-08', 3),
            ('2026-06-01', '2026-06-02', '2026-06-08', 4),
            ('2026-07-01', '2026-07-02', '2026-07-08', 5)
    """)
    stages = db.list_stages()
    assert len(stages) == 5
    orders = [s['stage_order'] for s in stages]
    assert orders == [5, 4, 3, 2, 1], f"DESC 排序失败: {orders}"


def test_float_stage_order_kept(fresh_db):
    """浮点 stage_order (0.01-0.12 早期大课) 保留 + 排在整数后."""
    db, _ = fresh_db
    _insert_wa(db, """
        INSERT INTO weekly_assignments (lesson_date, stage_start, stage_end, stage_order) VALUES
            ('2025-11-08', '2025-11-09', '2025-11-15', 0.01),
            ('2025-12-06', '2025-12-07', '2025-12-13', 0.05),
            ('2026-03-14', '2026-03-15', '2026-03-21', 1),
            ('2026-08-08', '2026-08-09', '2026-08-15', 18)
    """)
    stages = db.list_stages()
    assert len(stages) == 4
    orders = [s['stage_order'] for s in stages]
    # 浮点按数值排序: 18 > 1 > 0.05 > 0.01 (DESC)
    assert orders == [18, 1, 0.05, 0.01], f"浮点 DESC 排序失败: {orders}"


def test_mixed_invalid_and_valid(fresh_db):
    """混合 NULL/0/正常 行: 只返正常 + 浮点."""
    db, _ = fresh_db
    _insert_wa(db, """
        INSERT INTO weekly_assignments (lesson_date, stage_start, stage_end, stage_order) VALUES
            ('2025-11-08', '2025-11-09', '2025-11-15', 0.01),
            ('2025-12-01', '2025-12-02', '2025-12-08', NULL),
            ('2026-03-01', '2026-03-02', '2026-03-08', 0),
            ('2026-04-01', '2026-04-02', '2026-04-08', 2),
            ('2026-08-08', '2026-08-09', '2026-08-15', 18)
    """)
    stages = db.list_stages()
    orders = [s['stage_order'] for s in stages]
    # SQL 过滤后 NULL/0 不在, 期望返 [18, 2, 0.01] (API DESC 顺序)
    assert orders == [18, 2, 0.01], f"混合过滤失败: {orders}"
