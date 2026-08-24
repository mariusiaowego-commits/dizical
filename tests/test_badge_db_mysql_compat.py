"""Sprint 26082401 PR #287: badge_db 双后端兼容测试.

背景: badge_db.py 原本用 sqlite3 风格 `conn.execute(sql, params)` + sqlite3 named
param (`:name`). 在 pymysql (云端 MySQL backend) Connection 对象上没有 `execute` 方法,
且 pymysql 不支持 `:name` named param, 导致 commit-from-draft 在生产 500.

修法: 全改用 `?` positional + src.db_adapter.execute() 统一入口 (sqlite3 + pymysql 双兼容).

测试覆盖:
1. sqlite3 backend: 走 _db_execute, 用 `?`, OK (跟现有 158 个 badge 测试一致)
2. pymysql backend mock: 走 _db_execute, 验证 SQL 中 `?` 被替换为 `%s`, 验证
   insert_tuple 顺序对得上 VALUES 列数
3. insert_achievement_row 在 pymysql backend 用 positional tuple (不再 named dict)
4. update_badge_current 走 badge_write_tx() 事务 + _db_execute
"""
import sqlite3 as _sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.kid_app import badge_db


# ─── Case 1: sqlite3 backend 走 _db_execute (跟现有测试一致) ──────

def test_check_id_unique_sqlite(tmp_path, monkeypatch):
    """sqlite3 backend: check_id_unique 用 `?` 走 _db_execute → 不破."""
    import sqlite3
    db_file = tmp_path / "badge_test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("""CREATE TABLE achievements (
        id TEXT PRIMARY KEY, name TEXT, category TEXT, stat_logic TEXT,
        description TEXT, display_format TEXT, sort_order INTEGER,
        seasonal_type TEXT, unlock_strategy TEXT DEFAULT 'calc'
    )""")
    conn.execute("INSERT INTO achievements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 ("first", "First Badge", "milestone", "", "first", "icon", 1, "monthly", "calc"))
    conn.commit()

    # Mock db._get_connection → 返我们建的 sqlite conn
    monkeypatch.setattr(badge_db.db, "_get_connection", lambda: conn)

    assert badge_db.check_id_unique("first") is False  # 已存在
    assert badge_db.check_id_unique("second") is True   # 不存在


# ─── Case 2: pymysql backend mock, 验证 SQL 占位符转换 ─────────────

def test_db_adapter_translates_q_to_percent_s(monkeypatch):
    """mock is_mysql_env=True: db_adapter.execute 应把 `?` 转 `%s` 给 pymysql."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # 直接 monkeypatch module attribute
    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)

    from src.db_adapter import execute
    cur = execute(mock_conn, "SELECT * FROM achievements WHERE id = ?", ("abc123",))

    # 验证 SQL 转换
    mock_cursor.execute.assert_called_once_with(
        "SELECT * FROM achievements WHERE id = %s",
        ("abc123",),
    )


def test_db_adapter_keeps_q_for_sqlite(monkeypatch):
    """mock is_mysql_env=False: db_adapter.execute 应保留 `?` (sqlite3 内置支持)."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: False)

    from src.db_adapter import execute
    cur = execute(mock_conn, "SELECT * FROM achievements WHERE id = ?", ("abc123",))

    mock_cursor.execute.assert_called_once_with(
        "SELECT * FROM achievements WHERE id = ?",
        ("abc123",),
    )


# ─── Case 3: insert_achievement_row 用 positional tuple (pymysql) ──

def test_insert_achievement_row_pymysql_uses_positional(monkeypatch):
    """pymysql backend: insert_achievement_row 调 _db_execute 用 positional tuple, 不用 named dict.

    regression trap: 老代码用 `ach` dict 直接传 named param, pymysql 报
    'pymysql.err.ProgrammingError: not enough arguments for format string'.
    """
    mock_cursor = MagicMock()
    mock_cursor.lastrowid = 42
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)

    ach = {
        "id": "join_exam_23",
        "name": "加入考级",
        "type": "晋级",
        "category": "milestone",
        "stat_logic": "",
        "description": "通过考级",
        "display_format": "icon",
        "threshold": None,
        "unlocked_template": None,
        "placeholder": "test",
        "seasonal_type": "monthly",
        "cond_text": "通过考级",
        "unlock_strategy": "calc",
        "achieved_at_override": None,
    }

    badge_db.insert_achievement_row(mock_conn, ach)

    # 验证调 _db_execute (走 db_adapter), 用 positional tuple
    mock_cursor.execute.assert_called_once()
    args = mock_cursor.execute.call_args
    sql_str = args[0][0]
    params = args[0][1]

    # SQL 已转 `?` → `%s` (15 个 %s, 0 个 ?) — INSERT 15 列 (跟 VALUES tuple 长度对齐)
    assert sql_str.count("?") == 0  # 全部已转 %s
    assert sql_str.count("%s") == 15  # 15 列 INSERT

    # Params 应是 15-元素 tuple (用 list 检查更稳, MagicMock tuple isinstance 会 false)
    assert not isinstance(params, dict), f"params 应是 tuple, 拿到 dict: {params}"
    params_list = list(params)
    assert len(params_list) == 15
    # 第一个是 id, 第二个是 name
    assert params_list[0] == "join_exam_23"
    assert params_list[1] == "加入考级"


def test_insert_badge_row_pymysql_uses_positional(monkeypatch):
    """pymysql backend: insert_badge_row 4 个 positional `?`."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)

    badge_db.insert_badge_row(mock_conn, "test_badge", "/static/badges/test_badge_v1.png", 1)

    args = mock_cursor.execute.call_args
    sql_str = args[0][0]
    params = args[0][1]

    # SQL 已转 `?` → `%s` (3 个 %s, 0 个 ?) — INSERT 3 个 positional + 2 个字面常量 (is_locked=0, is_current=1)
    assert sql_str.count("?") == 0
    assert sql_str.count("%s") == 3
    assert len(params) == 3
    assert params[0] == "test_badge"
    assert params[1] == "/static/badges/test_badge_v1.png"
    assert params[2] == 1


def test_insert_achievement_stats_row_pymysql_uses_positional(monkeypatch):
    """pymysql backend: insert_achievement_stats_row 3 个 positional `?` (raw_stats='{}' 写死, computed_value=NULL 写死)."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)

    badge_db.insert_achievement_stats_row(mock_conn, "test_badge", achieved="N", achieved_at=None)

    args = mock_cursor.execute.call_args
    sql_str = args[0][0]
    params = args[0][1]

    # SQL 3 个 positional `?`, raw_stats='{}' 写死字符串
    assert sql_str.count("%s") == 3
    assert len(params) == 3
    assert params == ("test_badge", "N", None)


def test_update_badge_current_pymysql(monkeypatch):
    """pymysql backend: update_badge_current 走事务 + _db_execute."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # badge_write_tx() 走 db._get_connection → mock conn
    monkeypatch.setattr(badge_db.db, "_get_connection", lambda: mock_conn)
    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)

    badge_db.update_badge_current("test_badge", "/new/url.png", 2)

    # 验证 UPDATE 调 _db_execute (走 db_adapter)
    mock_conn.commit.assert_called_once()
    assert mock_cursor.execute.call_count == 2  # UPDATE + INSERT