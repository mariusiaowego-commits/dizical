#!/usr/bin/env python3
"""Idempotent migration: add videos column to weekly_assignments.

Supports SQLite + Cloud MySQL. Safe to re-run.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def migrate_sqlite(db_path: str) -> str:
    """Check and add videos column in SQLite weekly_assignments."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(weekly_assignments)")
        cols = [r[1] for r in cursor.fetchall()]
        if "videos" in cols:
            return f"sqlite ({db_path}): weekly_assignments.videos column already exists"
        cursor.execute("ALTER TABLE weekly_assignments ADD COLUMN videos TEXT NOT NULL DEFAULT '[]'")
        conn.commit()
        return f"sqlite ({db_path}): successfully added weekly_assignments.videos column"
    finally:
        conn.close()


def migrate_mysql(database_url: str | None = None) -> str:
    """Check and add videos column in Cloud MySQL weekly_assignments."""
    url = database_url or os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")
    if not url:
        return "mysql: skipped (no DATABASE_URL provided)"
    try:
        from src.database_mysql import MySQLBackend
    except Exception as e:
        return f"mysql: skip import error ({e})"

    db = MySQLBackend(url)
    with db._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'weekly_assignments'
                  AND COLUMN_NAME = 'videos'
                """
            )
            row = cur.fetchone()
            exists = bool(row and (row[0] if not isinstance(row, dict) else row.get("c")))
            if exists:
                return "mysql: weekly_assignments.videos column already exists"
            cur.execute(
                "ALTER TABLE weekly_assignments ADD COLUMN videos TEXT NULL"
            )
        conn.commit()
    return "mysql: successfully added weekly_assignments.videos column"


def main() -> int:
    parser = argparse.ArgumentParser(description="Migration: add videos column to weekly_assignments")
    parser.add_argument("--mysql", action="store_true", help="Run migration on Cloud MySQL")
    parser.add_argument("--database-url", type=str, default=None, help="MySQL Database URL")
    parser.add_argument("--db-path", type=str, default=None, help="Path to SQLite database")
    args = parser.parse_args()

    results = []
    if args.mysql:
        results.append(migrate_mysql(args.database_url))
    else:
        db_path = args.db_path or os.environ.get("DIZI_DB_PATH") or str(ROOT / "data" / "dizi.db")
        if Path(db_path).exists():
            results.append(migrate_sqlite(db_path))
        else:
            results.append(f"sqlite: skip missing {db_path}")
        # If DATABASE_URL is in env, also run MySQL
        if os.environ.get("DATABASE_URL"):
            results.append(migrate_mysql(os.environ.get("DATABASE_URL")))

    for line in results:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
