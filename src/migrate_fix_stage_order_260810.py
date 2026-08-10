"""
Migration: 修复 stage_order 字段 — sprint 26081001 (2026-08-10)

dad 8-10 浏览器反馈 + 三证据法验证:
1. Stage 0 (id=79, lesson=2026-08-08): MySQL save_weekly_assignment 写 0 当 fallback
   - 应得 stage_order = 18 (18th attended lesson, 2026-08-08 是第 18 个 attended)
   - 根因: src/database_mysql.py:425 旧代码 `stage_order = row.get(...) if row else 0`
2. Stage null (id 27-38, 12 个老 schema lesson 2025-11-08 ~ 2026-03-07):
   - 老 lesson 不在 lessons 表 (lessons 从 2026-03-14 起), 7-13 PR #155 算法返 None
   - dad 拍板: 用 0.01-0.12 浮点表示"早期大课" (早于小课 stage 1)
   - lesson_date 升序排号: 2025-11-08 → 0.01, ..., 2026-03-07 → 0.12

修复目标:
- UPDATE weekly_assignments SET stage_order = ? WHERE id IN (...)
- 12 个 NULL → 0.01-0.12 (按 lesson_date 升序, 跟小课 stage 1 自然衔接)
- 1 个 0 (8-08) → 18 (云端; 本地 8-08 不在 lessons 表 → 算法返 None, 但 SQL 过滤掉, 不显示)
- 13 行 UPDATE 全部 idempotent (新值已正确时 UPDATE 是 no-op)

执行模式 (互斥):
    python src/migrate_fix_stage_order_260810.py --target=local    # 改本地 SQLite
    python src/migrate_fix_stage_order_260810.py --target=cloud    # 改云端 MySQL (~/.dizical/.env)

idempotent: 多次跑 diff 为 0 (除 timestamp)
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Any

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"


def _backup_snapshot(snapshot: List[str], label: str) -> Path:
    """文本 dump 备份 13 行 stage_order 改动, 让 dad 可回滚."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    p = BACKUP_DIR / f"stage-order-260810-{label}-{ts}.txt"
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# Pre-migrate snapshot (sprint 26081001 {label})\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write("# Format: id | lesson_date | old_stage_order | new_stage_order\n")
        for line in snapshot:
            f.write(line + "\n")
    return p


def _compute_diffs_local(conn) -> List[Tuple[int, str, Any, Any]]:
    """本地 SQLite: 算 13 行 (或子集) stage_order 改动."""
    cur = conn.execute(
        "SELECT id, lesson_date, stage_order FROM weekly_assignments "
        "WHERE stage_order IS NULL OR stage_order = 0 ORDER BY lesson_date"
    )
    candidates = cur.fetchall()
    diffs = []
    for rid, ld, old_so in candidates:
        ld_str = ld if isinstance(ld, str) else ld.isoformat()
        # 本地 lessons 表从 2026-03-14 起, 老 lesson (NULL 12 个) 不在 attended 列表
        # → 用 0.01-0.12 浮点 (按 lesson_date 升序排号)
        # 新 lesson (8-08 等) 在 attended 列表 → 用 index+1 (跟 SQLite 算法一致)
        cur2 = conn.execute(
            "SELECT date FROM lessons WHERE status = 'attended' ORDER BY date"
        )
        attended_dates = [r[0] for r in cur2.fetchall()]
        attended_strs = [d if isinstance(d, str) else d.isoformat() for d in attended_dates]

        if ld_str in attended_strs:
            # 小课: attended index + 1
            new_so = attended_strs.index(ld_str) + 1
        else:
            # 早期大课: 按 lesson_date 升序排号 0.01-0.12
            # 先找出所有 stage_order IS NULL 或 = 0 的 lesson_date 升序
            cur3 = conn.execute(
                "SELECT id, lesson_date FROM weekly_assignments "
                "WHERE stage_order IS NULL OR stage_order = 0 ORDER BY lesson_date"
            )
            null_ids_ordered = [r[0] for r in cur3.fetchall()]
            try:
                offset = null_ids_ordered.index(rid)
                new_so = round(0.01 * (offset + 1), 2)
            except ValueError:
                new_so = None

        if new_so != old_so:
            diffs.append((rid, ld_str, old_so, new_so))
    return diffs


def _apply_local() -> None:
    """改本地 SQLite. idempotent — 只 UPDATE 真有差异的行."""
    if not DB_PATH.exists():
        print(f"DB 不存在 ({DB_PATH}), 跳过")
        return
    conn = sqlite3.connect(str(DB_PATH))
    try:
        diffs = _compute_diffs_local(conn)
        print(f"=== local: {len(diffs)} 行待改 ===")
        snapshot = []
        for d in diffs:
            print(f"  id={d[0]} lesson={d[1]} stage_order {d[2]} → {d[3]}")
            snapshot.append(f"{d[0]} | {d[1]} | {d[2]} | {d[3]}")

        if not diffs:
            print("  本地 SQLite 无 stage_order 噪音, 跳过 (idempotent)")
            return

        _backup_snapshot(snapshot, "local-pre")
        print(f"  备份已写入 data/backups/")

        # 事务包裹 UPDATE
        for rid, _, _, new_so in diffs:
            conn.execute(
                "UPDATE weekly_assignments SET stage_order = ? WHERE id = ?",
                (new_so, rid),
            )
        conn.commit()

        # verify
        cur = conn.execute(
            "SELECT COUNT(*) FROM weekly_assignments WHERE stage_order IS NULL OR stage_order = 0"
        )
        remaining = cur.fetchone()[0]
        print(f"\n本地 SQLite stage_order 修复完成, remaining invalid = {remaining}")
    finally:
        conn.close()


def _connect_cloud():
    """云端 MySQL 连接 — 沿用 sprint 26080803 模式."""
    env_path = Path.home() / ".dizical" / ".env"
    if not env_path.exists():
        print(f"~/.dizical/.env 不存在, 无法连云")
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
    db_url = os.environ.get("DATABASE_URL")
    import pymysql
    if db_url and db_url.startswith("mysql"):
        from urllib.parse import urlparse, unquote
        parsed = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
        user = unquote(parsed.username or "")
        pwd = unquote(parsed.password or "")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 3306
        db = parsed.path.lstrip("/")
    else:
        host = os.environ.get("MYSQL_HOST")
        port = os.environ.get("MYSQL_PORT")
        user = os.environ.get("MYSQL_USER")
        pwd = os.environ.get("MYSQL_PASSWORD")
        db = os.environ.get("MYSQL_DATABASE")
        if not all([host, port, user, pwd, db]):
            print(f"DATABASE_URL 未设或非 mysql, MYSQL_* 也不全: "
                  f"DATABASE_URL={db_url!r} MYSQL_HOST={host!r}")
            sys.exit(1)
        port = int(port)

    return pymysql.connect(
        host=host, port=port, user=user, password=pwd, database=db,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )


def _compute_diffs_cloud(conn) -> List[Tuple[int, str, Any, Any]]:
    """云端 MySQL: 算 13 行 stage_order 改动 (跟 SQLite 算法一致)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, lesson_date, stage_order FROM weekly_assignments "
            "WHERE stage_order IS NULL OR stage_order = 0 ORDER BY lesson_date"
        )
        candidates = cur.fetchall()

        # 取 attended (跟 SQLite 一致: lessons.status='attended' ORDER BY date)
        cur.execute("SELECT date FROM lessons WHERE status = 'attended' ORDER BY date")
        attended_rows = cur.fetchall()
        attended_strs = [
            r['date'].isoformat() if hasattr(r['date'], 'isoformat') else str(r['date'])
            for r in attended_rows
        ]

        # 取 NULL/0 行 (按 lesson_date 升序) 用于浮点排号
        null_ids_ordered = []
        for r in candidates:
            null_ids_ordered.append(r['id'])

        diffs = []
        for row in candidates:
            rid = row['id']
            ld = row['lesson_date']
            old_so = row['stage_order']
            ld_str = ld.isoformat() if hasattr(ld, 'isoformat') else str(ld)

            if ld_str in attended_strs:
                # 小课: attended index + 1
                new_so = attended_strs.index(ld_str) + 1
            else:
                # 早期大课: 浮点 0.01-0.12 按 lesson_date 升序排号
                if rid in null_ids_ordered:
                    offset = null_ids_ordered.index(rid)
                    new_so = round(0.01 * (offset + 1), 2)
                else:
                    new_so = None

            if new_so != old_so:
                diffs.append((rid, ld_str, old_so, new_so))
        return diffs


def _apply_cloud() -> None:
    """改云端 MySQL. idempotent."""
    conn = _connect_cloud()
    try:
        diffs = _compute_diffs_cloud(conn)
        print(f"=== cloud: {len(diffs)} 行待改 ===")
        snapshot = []
        for d in diffs:
            print(f"  id={d[0]} lesson={d[1]} stage_order {d[2]} → {d[3]}")
            snapshot.append(f"{d[0]} | {d[1]} | {d[2]} | {d[3]}")

        if not diffs:
            print("  云端 MySQL 无 stage_order 噪音, 跳过 (idempotent)")
            return

        _backup_snapshot(snapshot, "cloud-pre")
        print(f"  备份已写入 data/backups/")

        with conn.cursor() as cur:
            for rid, _, _, new_so in diffs:
                cur.execute(
                    "UPDATE weekly_assignments SET stage_order = %s WHERE id = %s",
                    (new_so, rid),
                )
        conn.commit()

        # verify
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM weekly_assignments WHERE stage_order IS NULL OR stage_order = 0"
            )
            remaining = cur.fetchone()['cnt']
        print(f"\n云端 MySQL stage_order 修复完成, remaining invalid = {remaining}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="修复 weekly_assignments.stage_order 字段 (sprint 26081001)")
    parser.add_argument("--target", choices=["local", "cloud"], required=True,
                        help="local=改本地 SQLite; cloud=改云端 MySQL (走 ~/.dizical/.env)")
    args = parser.parse_args()

    print(f"=== migrate_fix_stage_order_260810.py --target={args.target} ===\n")
    if args.target == "local":
        _apply_local()
    else:
        _apply_cloud()


if __name__ == "__main__":
    main()
