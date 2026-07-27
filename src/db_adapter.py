"""
双后端连接 + 占位符兼容适配层
fix/achievements-mysql-conn (2026-07-24)

目的:
- 让 calc_all() / achievement_definitions.py 不再写死 sqlite3.connect
- SQLite (本地开发/单测) 和 MySQL (云生产) 共用同一套 SQL
- 占位符统一 `?`, 内部根据 backend 转 `%s` (MySQL)
- 默认 cursor 用 tuple 模式, fetch_dicts() 转 list[dict]

不要做:
- 不替换 src.database.Database / MySQLBackend 的接口 (已 merge 契约保持稳定)
- 不引入新依赖 (pymysql 已在 use)
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Iterable, Sequence

try:
    import pymysql
    from pymysql.cursors import DictCursor as _MySQLDictCursor
except ImportError:  # 极端情况 (CI 不装 pymysql)
    pymysql = None
    _MySQLDictCursor = None

import pymysql.cursors


def is_mysql_env() -> bool:
    """判断当前进程是否应走 MySQL"""
    return os.environ.get("DATABASE_URL", "").startswith("mysql")


def get_conn():
    """返 (conn, is_mysql).

    - MySQL: 走 src.database 工厂 (跟 LessonManager 等保持一致)
    - SQLite: 用 ../data/dizi.db (跟 _DB_PATH 老逻辑兼容)

    不引入新路径不引入新连接池, 复用现有 src.database.db.
    """
    if is_mysql_env():
        # 走全局 db 工厂 (跟 LessonManager 一致, 跟 Phase 1b 兼容)
        from src.database import db
        return db._get_connection(), True
    # SQLite fallback (本地/单测)
    from pathlib import Path
    db_path = Path(__file__).parent.parent / "data" / "dizi.db"
    return sqlite3.connect(str(db_path)), False


def _to_mysql_placeholders(sql: str) -> str:
    """SQLite `?` → MySQL `%s`. 其他不动 (防误转字符串里的?)."""
    return sql.replace("?", "%s")


def execute(conn, sql: str, params: Sequence[Any] = ()):
    """统一执行入口, 自动处理占位符.

    - SQLite: 用 `?` 直接执行 (sqlite3 内置支持)
    - MySQL: 把 SQL 里 `?` 换成 `%s` 再执行 (pymysql 要求)

    Returns: cursor
    """
    cur = conn.cursor()
    if is_mysql_env():
        cur.execute(_to_mysql_placeholders(sql), params)
    else:
        cur.execute(sql, params)
    return cur


def executemany(conn, sql: str, seq_params: Iterable[Sequence[Any]]):
    cur = conn.cursor()
    if is_mysql_env():
        cur.executemany(_to_mysql_placeholders(sql), seq_params)
    else:
        cur.executemany(sql, seq_params)
    return cur


def fetch_dicts(cur) -> list[dict]:
    """把当前 cursor 的 fetchall() 结果转 list[dict].

    - SQLite: 默认 cursor 没 row_factory, 这里手工 zip(cols, row)
    - MySQL: 用 DictCursor 替代默认 cursor (execute 之前要换 cursor 类型)
    """
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def fetch_tuples(cur):
    """直接透传 fetchall (tuple 列表)."""
    return cur.fetchall()


def execute_dicts(conn, sql: str, params: Sequence[Any] = ()) -> list[dict]:
    """一步: 执行 + 转 dict 列表. MySQL 自动切 DictCursor."""
    if is_mysql_env():
        cur = conn.cursor(_MySQLDictCursor)
        cur.execute(_to_mysql_placeholders(sql), params)
        return cur.fetchall()  # DictCursor 直接 list[dict]
    else:
        cur = execute(conn, sql, params)
        return fetch_dicts(cur)
