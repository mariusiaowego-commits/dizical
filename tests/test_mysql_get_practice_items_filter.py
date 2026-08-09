"""回归测试: MySQLBackend.get_practice_items 的 archived 过滤 (S1, 2026-08-09).

需求 5 (PRD config配置-老师要求录入优化): 科目 picker 只列 active 科目.
bug 根因 (S0 发现): database_mysql.py 旧实现 `if active_only and not include_archived`
依赖 active_only=True, 但路由 config.py:292 调用传 active_only=False → 条件永远 False
→ 全量返回 (47 项含 37 archived). SQLite 版 (`if not include_archived:`) 逻辑正确.

修复: 对齐 SQLite 版语义 — active_only → is_active=1, not include_archived → is_archived=0.
本测试 mock 连接, 断言生成的 SQL 过滤子句, 不碰真实库.
"""
from unittest import mock

import pytest

from src.database_mysql import MySQLBackend


@pytest.fixture
def mysql_backend():
    """跳过 __init__ (避免解析真实 DATABASE_URL), 只测方法逻辑."""
    backend = MySQLBackend.__new__(MySQLBackend)
    return backend


def _mock_cursor_factory(backend):
    """返回 (fake_cur, fake_conn, patch_ctx) — 两层 context manager mock."""
    fake_cur = mock.MagicMock()
    fake_cur.fetchall.return_value = []
    fake_cur.__enter__.return_value = fake_cur  # with conn.cursor() as cur → cur 就是 fake_cur
    fake_cur.__exit__.return_value = False

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self, cursor_class=None):
            return fake_cur

    fake_conn = FakeConn()
    ctx = mock.patch.object(backend, "_get_connection", return_value=fake_conn)
    return fake_cur, fake_conn, ctx


def _capture_sql(fake_cur):
    """抓 execute 第一次调用的 SQL 参数."""
    call = fake_cur.execute.call_args
    return call[0][0]


def test_mysql_items_filter_not_include_archived(mysql_backend):
    """include_archived=False (picker 场景) → WHERE is_archived = 0."""
    fake_cur, _, ctx = _mock_cursor_factory(mysql_backend)
    with ctx:
        mysql_backend.get_practice_items(active_only=False, include_archived=False)
    sql = _capture_sql(fake_cur)
    assert "is_archived = 0" in sql
    assert "is_active" not in sql  # active_only=False 不过滤 is_active


def test_mysql_items_filter_include_archived_true(mysql_backend):
    """include_archived=True → 不过滤 archived, 全量返回."""
    fake_cur, _, ctx = _mock_cursor_factory(mysql_backend)
    with ctx:
        mysql_backend.get_practice_items(active_only=False, include_archived=True)
    sql = _capture_sql(fake_cur)
    assert "WHERE" not in sql
    assert "is_archived" not in sql


def test_mysql_items_filter_active_only_and_not_archived(mysql_backend):
    """active_only=True + include_archived=False → 两个条件都加."""
    fake_cur, _, ctx = _mock_cursor_factory(mysql_backend)
    with ctx:
        mysql_backend.get_practice_items(active_only=True, include_archived=False)
    sql = _capture_sql(fake_cur)
    assert "is_active = 1" in sql
    assert "is_archived = 0" in sql


def test_mysql_items_active_only_alone(mysql_backend):
    """active_only=True + include_archived=True → 只过滤 is_active."""
    fake_cur, _, ctx = _mock_cursor_factory(mysql_backend)
    with ctx:
        mysql_backend.get_practice_items(active_only=True, include_archived=True)
    sql = _capture_sql(fake_cur)
    assert "is_active = 1" in sql
    assert "is_archived" not in sql


def test_mysql_items_returns_rows(mysql_backend):
    """fetchall 结果原样返回."""
    fake_cur, _, ctx = _mock_cursor_factory(mysql_backend)
    fake_cur.fetchall.return_value = [{"item_id": 1, "name": "单吐练习"}]
    with ctx:
        rows = mysql_backend.get_practice_items(active_only=False, include_archived=False)
    assert len(rows) == 1
    assert rows[0]["name"] == "单吐练习"
