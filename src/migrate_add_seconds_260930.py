#!/usr/bin/env python3
"""幂等迁移: 练习时长秒级落地 (sprint 26093002).

加两列 + 回填:
  daily_practices.total_seconds     BIGINT/INTEGER NOT NULL DEFAULT 0
  practice_sessions.duration_seconds BIGINT/INTEGER NOT NULL DEFAULT 0
  daily_practices.items[].seconds   (JSON 内字段, 没有则按 minutes * 60 补)

回填口径: 老数据只有分钟, 秒字段 = minutes * 60. 10 秒被 ceil 成 1 分钟的历史**无法还原**,
这是既成事实; ×60 不会把已解锁的徽章打回 (徽章判读走 total_minutes, 语义不变).

幂等: 列已存在则跳过; 回填只更新 seconds = 0 且 minutes > 0 的行.
只跑一次 sqlite(本机) + 一次 mysql(生产, 需显式置 DATABASE_URL).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# 与 migrate_add_session_reps.py 同规: 加 repo ROOT, 让 src.xxx 包路径导入成立
sys.path.insert(0, str(ROOT))


def _sqlite_items_backfill(conn: sqlite3.Connection) -> int:
    """items JSON 里缺 seconds 的条目补 minutes * 60. 返回改动行数."""
    try:
        rows = conn.execute("SELECT date, items FROM daily_practices").fetchall()
    except sqlite3.Error:
        return 0
    changed = 0
    for date, raw in rows:
        if not raw:
            continue
        try:
            items = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(items, list) or not items:
            continue
        touched = False
        for it in items:
            if isinstance(it, dict) and "seconds" not in it:
                it["seconds"] = int(it.get("minutes", 0) or 0) * 60
                touched = True
        if touched:
            conn.execute(
                "UPDATE daily_practices SET items = ? WHERE date = ?",
                (json.dumps(items, ensure_ascii=False), date),
            )
            changed += 1
    return changed


def migrate_sqlite(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    try:
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        out: list[str] = []
        # 1. daily_practices.total_seconds
        dp_cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_practices)").fetchall()]
        if dp_cols and "total_seconds" not in dp_cols:
            conn.execute("ALTER TABLE daily_practices ADD COLUMN total_seconds INTEGER NOT NULL DEFAULT 0")
            out.append("dp.total_seconds added")
        if dp_cols:
            cur = conn.execute(
                "UPDATE daily_practices SET total_seconds = total_minutes * 60 "
                "WHERE (total_seconds IS NULL OR total_seconds = 0) AND total_minutes > 0"
            )
            out.append(f"dp backfilled {cur.rowcount}")
            out.append(f"items backfilled {_sqlite_items_backfill(conn)}")
        # 2. practice_sessions.duration_seconds
        ps_cols = [r[1] for r in conn.execute("PRAGMA table_info(practice_sessions)").fetchall()]
        if ps_cols and "duration_seconds" not in ps_cols:
            conn.execute("ALTER TABLE practice_sessions ADD COLUMN duration_seconds INTEGER NOT NULL DEFAULT 0")
            out.append("ps.duration_seconds added")
        if ps_cols:
            cur = conn.execute(
                "UPDATE practice_sessions SET duration_seconds = duration_minutes * 60 "
                "WHERE (duration_seconds IS NULL OR duration_seconds = 0) AND duration_minutes > 0"
            )
            out.append(f"ps backfilled {cur.rowcount}")
        conn.commit()
        msg = "sqlite: " + ("; ".join(out) if out else "两表都不存在, 跳过")
        print(msg)
        return msg
    finally:
        conn.close()


def migrate_mysql() -> tuple[str, bool]:
    """返回 (状态串, ok 布尔). 不抛异常 —— mysql 失败不该吞掉 sqlite 结果."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL") or ""
    if not url.startswith("mysql"):
        return "mysql: skipped (no DATABASE_URL)", True
    try:
        from src.database_mysql import MySQLBackend
    except Exception as e:  # 缺 pymysql 等
        msg = f"mysql: 导入 MySQLBackend 失败 ({type(e).__name__}: {e}), 跳过"
        print(msg)
        return msg, False

    def _has_col(cur, table: str, col: str) -> bool:
        cur.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
            """,
            (table, col),
        )
        row = cur.fetchone()
        return bool(row and row[0])

    try:
        db = MySQLBackend(url)
        out: list[str] = []
        with db._get_connection() as conn:  # noqa: SLF001
            with conn.cursor() as cur:
                if not _has_col(cur, "daily_practices", "total_seconds"):
                    cur.execute("ALTER TABLE daily_practices ADD COLUMN total_seconds BIGINT NOT NULL DEFAULT 0")
                    out.append("dp.total_seconds added")
                cur.execute(
                    "UPDATE daily_practices SET total_seconds = total_minutes * 60 "
                    "WHERE total_seconds = 0 AND total_minutes > 0"
                )
                out.append(f"dp backfilled {cur.rowcount}")
                if not _has_col(cur, "practice_sessions", "duration_seconds"):
                    cur.execute("ALTER TABLE practice_sessions ADD COLUMN duration_seconds BIGINT NOT NULL DEFAULT 0")
                    out.append("ps.duration_seconds added")
                cur.execute(
                    "UPDATE practice_sessions SET duration_seconds = duration_minutes * 60 "
                    "WHERE duration_seconds = 0 AND duration_minutes > 0"
                )
                out.append(f"ps backfilled {cur.rowcount}")
                # items JSON 秒补齐 (无 JSON 函数的兼容写法: 拉到 Python 里改)
                cur.execute("SELECT date, items FROM daily_practices")
                rows = cur.fetchall()
                changed = 0
                for date, raw in rows:
                    if not raw:
                        continue
                    try:
                        items = json.loads(raw)
                    except (TypeError, ValueError):
                        continue
                    if not isinstance(items, list) or not items:
                        continue
                    touched = False
                    for it in items:
                        if isinstance(it, dict) and "seconds" not in it:
                            it["seconds"] = int(it.get("minutes", 0) or 0) * 60
                            touched = True
                    if touched:
                        cur.execute(
                            "UPDATE daily_practices SET items = %s WHERE date = %s",
                            (json.dumps(items, ensure_ascii=False), date),
                        )
                        changed += 1
                out.append(f"items backfilled {changed}")
            conn.commit()
        msg = "mysql: " + "; ".join(out)
        print(msg)
        return msg, True
    except Exception as e:
        msg = f"mysql: 迁移失败 ({type(e).__name__}: {e})"
        print(msg)
        return msg, False


def main() -> int:
    db_path = os.environ.get("DIZI_DB_PATH") or str(ROOT / "data" / "dizi.db")
    if Path(db_path).exists():
        migrate_sqlite(db_path)
    else:
        print(f"sqlite: 找不到 {db_path}, 跳过")
    mysql_msg, mysql_ok = migrate_mysql()
    print(mysql_msg)
    return 0 if mysql_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
