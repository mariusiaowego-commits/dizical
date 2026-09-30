"""
双后端连接 + 占位符兼容适配层
fix/achievements-mysql-conn (2026-07-24)

目的:
- 让 calc_all() / achievement_definitions.py 不再写死 sqlite3.connect
- SQLite (本地开发/单测) 和 MySQL (云生产) 共用同一套 SQL
- 占位符统一 `?`, 内部根据 backend 转 `%s` (MySQL)
- cursor 两种: 默认 tuple 模式 (fetch_dicts() 手工转 list[dict]);
  execute_dicts() 走 MySQL DictCursor + `_normalize_datetimes()` 归一化,
  避免 pymysql 的 datetime 直接进 JSONResponse (见 database_mysql.py:16 同类前科)

不要做:
- 不替换 src.database.Database / MySQLBackend 的接口 (已 merge 契约保持稳定)
- 不引入新依赖 (pymysql 已在 use)
"""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
from typing import Any, Iterable, Sequence

# pymysql 是硬依赖 (requirements.txt 已列)。旧版这里有 try/except ImportError 兜底,
# 但紧随其后是无条件的 `import pymysql.cursors` → 兜底永远不生效, 是死代码
# (2026-09-29 PR 级审计 P3-2)。去掉兜底, 让缺依赖直接报错, 不假装能跑。
import pymysql.cursors
from pymysql.cursors import DictCursor as _MySQLDictCursor


def is_mysql_env() -> bool:
    """判断当前进程是否应走 MySQL"""
    return os.environ.get("DATABASE_URL", "").startswith("mysql")


def get_conn():
    """返 (conn, is_mysql).

    - MySQL: 走 src.database 工厂 (跟 LessonManager 等保持一致)
    - SQLite: 用 src.models.settings.db_path (默认 prod, 单测被 conftest 改)

    Sprint 26081003: 改用 settings.db_path 让单测能改 tmp db (不用绝对路径).
    """
    if is_mysql_env():
        # 走全局 db 工厂 (跟 LessonManager 一致, 跟 Phase 1b 兼容)
        from src.database import db
        return db._get_connection(), True
    # SQLite fallback (本地/单测) — 用 settings.db_path 允许 conftest 改 tmp db
    from src.models import settings as _settings
    return sqlite3.connect(str(_settings.db_path)), False


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


_SAFE_CURSOR_CLS = None


def _safe_mysql_dict_cursor():
    """MySQL dict cursor: 优先复用 database_mysql.DatetimeSafeDictCursor.

    Why: pymysql 把 DATETIME 列返成 `datetime.datetime`, FastAPI 的 JSONResponse
    遇到它直接 `TypeError: Object of type datetime is not JSON serializable`
    (本仓 2026-08-16 已为同类 500 在 database_mysql.py:16-39 建过该 cursor)。
    拿不到 (极端情况: 循环 import 等) 时回退普通 DictCursor —
    此时靠 `_normalize_datetimes()` 兜底, 保证 datetime 不外泄。
    """
    global _SAFE_CURSOR_CLS
    if _SAFE_CURSOR_CLS is None:
        try:
            from src.database_mysql import DatetimeSafeDictCursor

            _SAFE_CURSOR_CLS = DatetimeSafeDictCursor
        except Exception:  # pragma: no cover - 极端回退路径
            _SAFE_CURSOR_CLS = _MySQLDictCursor or None
    return _SAFE_CURSOR_CLS


def _normalize_datetimes(row: dict) -> dict:
    """datetime / date 值 → str (跟 DatetimeSafeDictCursor 同口径 `str(v)`).

    幂等: 已经是字符串的值原样返回, 所以即使 cursor 层已转换也无副作用.
    """
    for k, v in list(row.items()):
        if isinstance(v, (dt.datetime, dt.date)):
            row[k] = str(v)
    return row


def execute_dicts(conn, sql: str, params: Sequence[Any] = ()) -> list[dict]:
    """一步: 执行 + 转 dict 列表. MySQL 自动切 DictCursor + datetime 归一化."""
    if is_mysql_env():
        cur = conn.cursor(_safe_mysql_dict_cursor())
        cur.execute(_to_mysql_placeholders(sql), params)
        rows = cur.fetchall()
        # DictCursor 直接给 list[dict]; 再过一道归一化防 datetime 泄漏 (见 _normalize_datetimes)
        return [_normalize_datetimes(r) for r in rows]
    else:
        cur = execute(conn, sql, params)
        return fetch_dicts(cur)
