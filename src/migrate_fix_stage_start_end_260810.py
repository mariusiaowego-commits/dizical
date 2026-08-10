"""
Migration: 修复 stage_start/stage_end 边界算法 (sprint 26081002, 2026-08-10)

dad 8-10 浏览器反馈 Stage 17 只有 8-01 一天, Stage 18 只有 8-08 一天,
但 8-02~8-07 (Stage 17) + 8-09 (Stage 18) 都有练习数据.

根因: id=78 (8-01) 和 id=79 (8-08) 是切云早期 (sprint 26080601) 用 MySQL 路径
老 fallback 代码首次 INSERT 写入, 当时 code:
    stage_start = row.get("stage_start") if row else lesson_date.isoformat()
    stage_end = row.get("stage_end") if row else lesson_date.isoformat()
→ fallback 写 lesson_date, stage_start=stage_end=lesson_date (1 天 1 stage).

正确算法 (跟 SQLite `database.py:710-740` + MySQL PR #256 算法一致):
    stage_start = lesson_date + 1 day
    stage_end = next future lesson (attended + scheduled) date, 或 lesson_date + 7 day

修复: id=78, 79 (仅 2 行) 重算 stage_start/stage_end, 不动其他行.

执行模式 (互斥):
    python src/migrate_fix_stage_start_end_260810.py --target=local    # 改本地 SQLite
    python src/migrate_fix_stage_start_end_260810.py --target=cloud    # 改云端 MySQL

idempotent: WHERE stage_start = lesson_date OR stage_start IS NULL, 多次跑 diff=0
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Any

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"


def _backup_snapshot(snapshot: List[str], label: str) -> Path:
    """文本 dump 备份, 让 dad 可回滚."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    p = BACKUP_DIR / f"stage-start-end-260810-{label}-{ts}.txt"
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# Pre-migrate snapshot (sprint 26081002 {label})\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write("# Format: id | lesson_date | old_ss | old_se | new_ss | new_se\n")
        for line in snapshot:
            f.write(line + "\n")
    return p


def _compute_diffs_local(conn) -> List[Tuple[int, str, Any, Any, Any, Any]]:
    """本地 SQLite: 算 stage_start 异常行的新值.

    算法 (跟 SQLite `database.py:710-740` 一致):
      - stage_start = lesson_date + 1 day
      - stage_end = next future lesson (attended + scheduled) date, 或 lesson_date + 7 day
    """
    cur = conn.execute("""
        SELECT id, lesson_date, stage_start, stage_end
        FROM weekly_assignments
        WHERE stage_start IS NULL OR stage_start = lesson_date
        ORDER BY lesson_date
    """)
    candidates = cur.fetchall()

    # 取所有 lesson (attended + scheduled) 按日期排序
    cur.execute("SELECT date FROM lessons ORDER BY date")
    all_lessons = [dt.date.fromisoformat(r[0]) for r in cur.fetchall()]

    diffs = []
    for rid, ld, old_ss, old_se in candidates:
        ld_dt = dt.date.fromisoformat(ld) if isinstance(ld, str) else ld
        # 正确算法
        new_ss = (ld_dt + timedelta(days=1)).isoformat()
        future = [d for d in all_lessons if d > ld_dt]
        new_se = future[0].isoformat() if future else (ld_dt + timedelta(days=7)).isoformat()

        if (old_ss != new_ss) or (old_se != new_se):
            ld_str = ld if isinstance(ld, str) else ld.isoformat()
            old_ss_str = old_ss if isinstance(old_ss, str) else (old_ss.isoformat() if old_ss else 'NULL')
            old_se_str = old_se if isinstance(old_se, str) else (old_se.isoformat() if old_se else 'NULL')
            diffs.append((rid, ld_str, old_ss_str, old_se_str, new_ss, new_se))
    return diffs


def _apply_local() -> None:
    """改本地 SQLite. idempotent."""
    if not DB_PATH.exists():
        print(f"DB 不存在 ({DB_PATH}), 跳过")
        return
    conn = sqlite3.connect(str(DB_PATH))
    try:
        diffs = _compute_diffs_local(conn)
        print(f"=== local: {len(diffs)} 行待改 ===")
        snapshot = []
        for d in diffs:
            print(f"  id={d[0]} lesson={d[1]} ss {d[2]} → {d[4]}, se {d[3]} → {d[5]}")
            snapshot.append(f"{d[0]} | {d[1]} | {d[2]} | {d[3]} | {d[4]} | {d[5]}")

        if not diffs:
            print("  本地 SQLite 无 stage_start 异常, 跳过 (idempotent)")
            return

        _backup_snapshot(snapshot, "local-pre")
        print(f"  备份已写入 data/backups/")

        for rid, _, _, _, new_ss, new_se in diffs:
            conn.execute(
                "UPDATE weekly_assignments SET stage_start = ?, stage_end = ? WHERE id = ?",
                (new_ss, new_se, rid),
            )
        conn.commit()
        print(f"\n本地 SQLite stage_start/end 修复完成")
    finally:
        conn.close()


def _connect_cloud():
    """云端 MySQL 连接."""
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
    if 'DATABASE_URL' not in os.environ:
        if all(k in os.environ for k in ['MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']):
            os.environ['DATABASE_URL'] = f"mysql+pymysql://{os.environ['MYSQL_USER']}:{os.environ['MYSQL_PASSWORD']}@{os.environ['MYSQL_HOST']}:{os.environ['MYSQL_PORT']}/{os.environ['MYSQL_DATABASE']}"
    db_url = os.environ['DATABASE_URL']
    import pymysql
    from urllib.parse import urlparse, unquote
    parsed = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
    return pymysql.connect(
        host=parsed.hostname, port=parsed.port, user=unquote(parsed.username),
        password=unquote(parsed.password), database=parsed.path.lstrip("/"),
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )


def _compute_diffs_cloud(conn) -> List[Tuple[int, str, Any, Any, Any, Any]]:
    """云端 MySQL: 算 stage_start 异常行的新值 (跟 SQLite 算法一致)."""
    import datetime as dt
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, lesson_date, stage_start, stage_end
            FROM weekly_assignments
            WHERE stage_start IS NULL OR stage_start = lesson_date
            ORDER BY lesson_date
        """)
        candidates = cur.fetchall()

        cur.execute("SELECT date FROM lessons ORDER BY date")
        all_lessons_raw = cur.fetchall()
        all_lessons = [
            r['date'] if isinstance(r['date'], dt.date) else dt.date.fromisoformat(r['date'])
            for r in all_lessons_raw
        ]

        diffs = []
        for row in candidates:
            rid = row['id']
            ld = row['lesson_date']
            old_ss = row['stage_start']
            old_se = row['stage_end']
            ld_dt = ld if isinstance(ld, dt.date) else dt.date.fromisoformat(ld)

            new_ss = (ld_dt + timedelta(days=1)).isoformat()
            future = [d for d in all_lessons if d > ld_dt]
            new_se = future[0].isoformat() if future else (ld_dt + timedelta(days=7)).isoformat()

            # 比较 (考虑 datetime 跟 str 转换)
            old_ss_str = old_ss.isoformat() if hasattr(old_ss, 'isoformat') else (str(old_ss) if old_ss else 'NULL')
            old_se_str = old_se.isoformat() if hasattr(old_se, 'isoformat') else (str(old_se) if old_se else 'NULL')
            ld_str = ld.isoformat() if hasattr(ld, 'isoformat') else str(ld)

            if (old_ss_str != new_ss) or (old_se_str != new_se):
                diffs.append((rid, ld_str, old_ss_str, old_se_str, new_ss, new_se))
        return diffs


def _apply_cloud() -> None:
    """改云端 MySQL. idempotent."""
    conn = _connect_cloud()
    try:
        diffs = _compute_diffs_cloud(conn)
        print(f"=== cloud: {len(diffs)} 行待改 ===")
        snapshot = []
        for d in diffs:
            print(f"  id={d[0]} lesson={d[1]} ss {d[2]} → {d[4]}, se {d[3]} → {d[5]}")
            snapshot.append(f"{d[0]} | {d[1]} | {d[2]} | {d[3]} | {d[4]} | {d[5]}")

        if not diffs:
            print("  云端 MySQL 无 stage_start 异常, 跳过 (idempotent)")
            return

        _backup_snapshot(snapshot, "cloud-pre")
        print(f"  备份已写入 data/backups/")

        with conn.cursor() as cur:
            for rid, _, _, _, new_ss, new_se in diffs:
                cur.execute(
                    "UPDATE weekly_assignments SET stage_start = %s, stage_end = %s WHERE id = %s",
                    (new_ss, new_se, rid),
                )
        conn.commit()
        print(f"\n云端 MySQL stage_start/end 修复完成")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="修复 weekly_assignments.stage_start/stage_end 边界 (sprint 26081002)")
    parser.add_argument("--target", choices=["local", "cloud"], required=True,
                        help="local=改本地 SQLite; cloud=改云端 MySQL (走 ~/.dizical/.env)")
    args = parser.parse_args()

    print(f"=== migrate_fix_stage_start_end_260810.py --target={args.target} ===\n")
    if args.target == "local":
        _apply_local()
    else:
        _apply_cloud()


if __name__ == "__main__":
    import datetime as dt
    main()
