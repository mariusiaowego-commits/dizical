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
sys.path.insert(0, str(ROOT / "src"))


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


def migrate_mysql() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL") or ""
    if not url.startswith("mysql"):
        print("mysql: 无 DATABASE_URL, 跳过")
        return "mysql: skipped (no DATABASE_URL)"
    from database_mysql import MySQLBackend

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
                print("已存在，跳过")
                return "mysql: reps 已存在，跳过"
            cur.execute("ALTER TABLE practice_sessions ADD COLUMN reps BIGINT NULL")
        conn.commit()
    print("mysql: 已添加 practice_sessions.reps")
    return "mysql: added reps"


def main() -> int:
    db_path = os.environ.get("DIZI_DB_PATH") or str(ROOT / "data" / "dizi.db")
    if Path(db_path).exists():
        print(migrate_sqlite(db_path))
    else:
        print(f"sqlite: 找不到 {db_path}, 跳过")
    print(migrate_mysql())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
