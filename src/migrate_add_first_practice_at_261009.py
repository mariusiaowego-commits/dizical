#!/usr/bin/env python3
"""幂等迁移: daily_practices.first_practice_at (2026-10-09, dad ack).

背景: `daily_practices.practice_at` 的语义是「该日**首次写入**记录时的练习时间」(UPDATE 永不覆盖),
不能表达「当天最早开始练习的时刻」。D5 今日练习卡 / D6 今日时长卡要画**一天自然跨度**
(如 19:10 开始 → 20:07 结束, 中间 9 段练习 + 8 段休息), 需要这个起点。

加一列 + 回填:
  daily_practices.first_practice_at  DATETIME (CST ISO 'YYYY-MM-DD HH:MM:SS[.fff]', 不带 Z)

语义: **单调取早** —— 新建行 = 本次 practice_at; 更新行 = MIN(已有, 本次)。
      补录一个更早的时刻要能把它拉早 (这是它跟 practice_at 的关键差别)。

回填口径: 优先 `behavior_log[0].enter_time` (比 practice_at 更接近真实练习时刻);
          没有 behavior_log 就退回 `practice_at`; 两者都没有则留 NULL (读接口会回退 practice_at)。

幂等: 列已存在则跳过; 回填**只填 IS NULL 的行**, 绝不覆盖已有值。
安全: 默认 dry-run 只打印; 加 --apply 才写盘。生产 MySQL 的 DDL/DML 按规矩走 MCP 工具留审计,
      本脚本的 MySQL 分支仅在显式提供 DATABASE_URL 且加 --apply 时执行。
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COL = "first_practice_at"


def _first_from_behavior_log(raw) -> str | None:
    """behavior_log[0].enter_time (CST ISO), 取不到返回 None."""
    if not raw:
        return None
    try:
        log = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return None
    if isinstance(log, list) and log and isinstance(log[0], dict):
        v = log[0].get("enter_time")
        return str(v) if v else None
    return None


def migrate_sqlite(db_path: str, apply: bool) -> str:
    conn = sqlite3.connect(db_path)
    try:
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass
        out: list[str] = []
        cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_practices)").fetchall()]
        if not cols:
            return "sqlite: daily_practices 不存在, 跳过"
        if COL not in cols:
            if apply:
                conn.execute(f"ALTER TABLE daily_practices ADD COLUMN {COL} DATETIME")
            out.append(f"{COL} added" if apply else f"{COL} WOULD ADD (dry-run)")
        # 回填: 只碰 IS NULL 的行
        rows = conn.execute(
            f"SELECT id, date, practice_at, behavior_log FROM daily_practices WHERE {COL} IS NULL"
        ).fetchall()
        samples = []
        changed = 0
        for rid, d, practice_at, blog in rows:
            val = _first_from_behavior_log(blog) or practice_at
            if not val:
                continue
            samples.append((rid, d, val))
            if apply:
                conn.execute(f"UPDATE daily_practices SET {COL} = ? WHERE id = ?", (val, rid))
            changed += 1
        out.append(f"{COL} {'backfilled' if apply else 'WOULD BACKFILL'} {changed} rows")
        out.append(f"still NULL after: {len(rows) - changed}")
        if apply:
            conn.commit()
        msg = "sqlite: " + "; ".join(out)
        print(msg)
        print(f"  抽样 (最多 10 行, {'已写' if apply else 'dry-run 预览'}):")
        for rid, d, v in samples[:10]:
            print(f"    id={rid} date={d} → {COL}={v}")
        return msg
    finally:
        conn.close()


def migrate_mysql(apply: bool) -> tuple[str, bool]:
    url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL") or ""
    if not url.startswith("mysql"):
        return "mysql: skipped (no DATABASE_URL)", True
    if not apply:
        return "mysql: skipped (dry-run; 生产请走 MCP 工具并加 --apply)", True
    try:
        from src.database_mysql import MySQLBackend
    except Exception as e:  # 缺 pymysql 等
        msg = f"mysql: 导入 MySQLBackend 失败 ({type(e).__name__}: {e}), 跳过"
        print(msg)
        return msg, False

    def _has_col(cur, table: str, col: str) -> bool:
        cur.execute(
            """SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s""",
            (table, col),
        )
        row = cur.fetchone()
        return bool(row and row[0])

    try:
        db = MySQLBackend(url)
        out: list[str] = []
        with db._get_connection() as conn:  # noqa: SLF001
            with conn.cursor() as cur:
                if not _has_col(cur, "daily_practices", COL):
                    cur.execute(f"ALTER TABLE daily_practices ADD COLUMN {COL} DATETIME NULL")
                    out.append(f"{COL} added")
                cur.execute(
                    f"SELECT id, practice_at, behavior_log FROM daily_practices WHERE {COL} IS NULL"
                )
                rows = cur.fetchall()
                changed = 0
                for rid, practice_at, blog in rows:
                    val = _first_from_behavior_log(blog) or (str(practice_at) if practice_at else None)
                    if not val:
                        continue
                    cur.execute(
                        f"UPDATE daily_practices SET {COL} = %s WHERE id = %s", (val, rid)
                    )
                    changed += 1
                out.append(f"{COL} backfilled {changed} rows")
            conn.commit()
        msg = "mysql: " + "; ".join(out)
        print(msg)
        return msg, True
    except Exception as e:
        msg = f"mysql: 迁移失败 ({type(e).__name__}: {e})"
        print(msg)
        return msg, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写盘 (默认 dry-run)")
    ap.add_argument("--db", default=os.environ.get("DIZI_DB_PATH") or str(ROOT / "data" / "dizi.db"))
    args = ap.parse_args()
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== migrate_add_first_practice_at_261009 [{mode}] ===")
    if Path(args.db).exists():
        migrate_sqlite(args.db, args.apply)
    else:
        print(f"sqlite: 找不到 {args.db}, 跳过")
    mysql_msg, mysql_ok = migrate_mysql(args.apply)
    print(mysql_msg)
    return 0 if mysql_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
