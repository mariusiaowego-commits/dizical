#!/usr/bin/env python3
"""Idempotent migration: practice_items.content_options TEXT.

SQLite + MySQL. Safe to re-run.
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
        cols = [r[1] for r in conn.execute("PRAGMA table_info(practice_items)").fetchall()]
        if "content_options" in cols:
            return "sqlite: content_options already exists"
        conn.execute("ALTER TABLE practice_items ADD COLUMN content_options TEXT DEFAULT ''")
        conn.commit()
        return "sqlite: added content_options"
    finally:
        conn.close()


def migrate_mysql() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")
    if not url:
        return "mysql: skipped (no DATABASE_URL)"
    try:
        from database_mysql import Database as MySQLDatabase  # type: ignore
    except Exception as e:
        return f"mysql: skip import ({e})"
    db = MySQLDatabase()
    with db._get_connection() as conn:  # noqa: SLF001
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'practice_items'
                  AND COLUMN_NAME = 'content_options'
                """
            )
            row = cur.fetchone()
            exists = bool(row and (row[0] if not isinstance(row, dict) else row.get("c")))
            if exists:
                return "mysql: content_options already exists"
            cur.execute(
                "ALTER TABLE practice_items ADD COLUMN content_options TEXT NULL"
            )
        conn.commit()
    return "mysql: added content_options"


def main() -> int:
    db_path = os.environ.get("DIZI_DB_PATH") or str(ROOT / "data" / "dizi.db")
    results = []
    if Path(db_path).exists():
        results.append(migrate_sqlite(db_path))
    else:
        results.append(f"sqlite: skip missing {db_path}")
    results.append(migrate_mysql())
    for line in results:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
