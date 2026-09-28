#!/usr/bin/env python3
"""幂等迁移: practice_sessions.reps INTEGER/BIGINT NULL.

不回填历史行. NULL = 未记录.
SQLite 与 MySQL 都支持. 列已存在则跳过.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 2026-09-28 FIX-3 (审计 P1-1): 加 repo ROOT 而不是 src/ ——
# database_mysql.py 内部用相对 import (from .models import ...), 只有把 ROOT
# 放进 sys.path 再按 src.xxx 包路径导入才成立. 原来加 src/ + `from database_mysql`
# 在脚本上下文里必然 ImportError (exit 1).
sys.path.insert(0, str(ROOT))


def migrate_sqlite(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    try:
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'practice_sessions'"
        ).fetchone()
        if not exists:
            print("sqlite: practice_sessions 不存在, 跳过")
            return "sqlite: practice_sessions 不存在, 跳过"
        cols = [r[1] for r in conn.execute("PRAGMA table_info(practice_sessions)").fetchall()]
        if "reps" in cols:
            print("已存在，跳过")
            return "sqlite: reps 已存在，跳过"
        conn.execute("ALTER TABLE practice_sessions ADD COLUMN reps INTEGER")
        conn.commit()
        print("sqlite: 已添加 practice_sessions.reps")
        return "sqlite: added reps"
    finally:
        conn.close()


def migrate_mysql() -> tuple[str, bool]:
    """返回 (状态串, ok 布尔). 不抛异常 —— mysql 失败不该影响 sqlite 结果与退出码."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL") or ""
    if not url.startswith("mysql"):
        return "mysql: skipped (no DATABASE_URL)", True
    try:
        from src.database_mysql import MySQLBackend
    except Exception as e:  # 缺 pymysql / import 失败等
        msg = f"mysql: 导入 MySQLBackend 失败 ({type(e).__name__}: {e}), 跳过"
        print(msg)
        return msg, False
    try:
        db = MySQLBackend(url)
        with db._get_connection() as conn:  # noqa: SLF001
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'practice_sessions'
                      AND COLUMN_NAME = 'reps'
                    """
                )
                row = cur.fetchone()
                count = row[0] if row is not None else 0
                if count:
                    return "mysql: reps 已存在，跳过", True
                cur.execute("ALTER TABLE practice_sessions ADD COLUMN reps BIGINT NULL")
            conn.commit()
        return "mysql: added reps", True
    except Exception as e:
        msg = f"mysql: 迁移失败 ({type(e).__name__}: {e})"
        print(msg)
        return msg, False


def main() -> int:
    db_path = os.environ.get("DIZI_DB_PATH") or str(ROOT / "data" / "dizi.db")
    if Path(db_path).exists():
        print(migrate_sqlite(db_path))
    else:
        print(f"sqlite: 找不到 {db_path}, 跳过")
    # 2026-09-28 FIX-3: mysql 失败不吞掉 sqlite 的成功, 但也不假装整体成功.
    # 两个后端都失败才返回非 0; 单个后端失败按部分成功报告.
    mysql_msg, mysql_ok = migrate_mysql()
    print(mysql_msg)
    if not mysql_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
