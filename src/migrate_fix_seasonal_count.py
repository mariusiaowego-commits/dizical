"""
Migration: 一次性回填 seasonal badge 的 raw_stats JSON (count + history_periods).

执行模式 (互斥):
    python src/migrate_fix_seasonal_count.py --target=local    # 改本地 SQLite data/dizi.db
    python src/migrate_fix_seasonal_count.py --target=cloud    # 改云端 MySQL (用 ~/.dizical/.env)

idempotent: 多次跑结果一致 (用 raw_stats JSON merge, 不覆盖)

sprint 26080702 (2026-08-07): 配合 feat/badges-26080702-seasonal-modal-season-info PR #234.
老 raw_stats 是 '{}' (没 count/history_periods). 部署后跑一次本脚本让云端数据有 season_info 文案.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"


# 7 个 seasonal badge (跟 PR #234 sprint 26080702 一致)
SEASONAL_IDS = [
    "total_60", "week_champ", "full_month", "top1",
    "early_riser", "little_chick_commander", "first_to_act",
]

# MVP threshold/check_fn 映射 (跟 PR #234 achievement_definitions.py:716+ 一致)
SEASONAL_CALC = {
    "total_60":          (None, lambda r: int(r.get("total_minutes", 0) or 0) >= 60),
    "week_champ":        (None, lambda r: True),  # MVP
    "full_month":        (None, lambda r: True),  # MVP
    "top1":              (None, lambda r: True),  # MVP
    "early_riser":       (20, None),
    "little_chick_commander": (17, None),
    "first_to_act":      (12, None),
}


def _count_activations_sqlite(conn, aid: str) -> tuple[int, list[str]]:
    """SQLite 端: 扫 daily_practices 算 count + history_periods (YYYY-MM list)."""
    from datetime import datetime
    from collections import defaultdict

    threshold, check_fn = SEASONAL_CALC[aid]
    cur = conn.execute(
        "SELECT date, practice_at, total_minutes, items FROM daily_practices "
        "ORDER BY date ASC"
    )
    rows = cur.fetchall()
    monthly_achieved: dict[str, bool] = defaultdict(bool)
    for row in rows:
        date_str = str(row[0])[:7]  # YYYY-MM
        if not date_str or date_str == "":
            continue
        if check_fn is not None:
            if check_fn({"total_minutes": row[2], "items": row[3]}):
                monthly_achieved[date_str] = True
        elif threshold is not None:
            pat = row[1]
            if not pat:
                continue
            try:
                ts = datetime.strptime(str(pat)[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if ts.hour < threshold:
                monthly_achieved[date_str] = True

    history_periods = sorted(monthly_achieved.keys())
    count = sum(1 for v in monthly_achieved.values() if v)
    return count, history_periods


def _apply_local() -> None:
    """改本地 SQLite. idempotent — raw_stats JSON merge."""
    if not DB_PATH.exists():
        print(f"DB 不存在 ({DB_PATH}), 跳过")
        return
    conn = sqlite3.connect(str(DB_PATH))
    try:
        for aid in SEASONAL_IDS:
            count, history = _count_activations_sqlite(conn, aid)
            if count == 0:
                print(f"  {aid}: 无历史激活, 跳过")
                continue
            cur = conn.execute(
                "SELECT raw_stats FROM achievement_stats WHERE achievement_id=?",
                (aid,),
            )
            row = cur.fetchone()
            existing: dict = {}
            if row is not None and row[0]:
                try:
                    existing = json.loads(row[0])
                except (TypeError, ValueError):
                    existing = {}

            # 合并: count 走最新计算, history_periods 去重合并
            new_stats = {
                "count": count,
                "history_periods": sorted(set(existing.get("history_periods", []) + history)),
            }

            if row is None:
                # stats 行不存在, 跳过 (跟 PR #234 行为一致: calc_all INSERT 时才建)
                print(f"  {aid}: stats 行不存在, 跳过 (等 calc_all 首次调用自动建)")
                continue
            else:
                # 合并现有 raw_stats (不覆盖其他字段)
                merged = {**existing, **new_stats}
                conn.execute(
                    "UPDATE achievement_stats SET raw_stats=? WHERE achievement_id=?",
                    (json.dumps(merged, ensure_ascii=False, sort_keys=True), aid),
                )
                conn.commit()
                print(f"  {aid}: count={count}, history_periods={new_stats['history_periods'][:5]}{'...' if len(new_stats['history_periods'])>5 else ''}")
    finally:
        conn.close()
    print("\n本地 SQLite 回填完成")


def _apply_cloud() -> None:
    """改云端 MySQL. 用 pymysql 直连 (DATABASE_URL 从 ~/.dizical/.env 读)."""
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
    if not db_url or not db_url.startswith("mysql"):
        print(f"DATABASE_URL 未设或非 mysql: {db_url!r}")
        sys.exit(1)

    import pymysql
    from urllib.parse import urlparse, unquote
    parsed = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
    user = unquote(parsed.username or "")
    pwd = unquote(parsed.password or "")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 3306
    db = parsed.path.lstrip("/")

    conn = pymysql.connect(
        host=host, port=port, user=user, password=pwd, database=db,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        for aid in SEASONAL_IDS:
            # 1. 算 count + history (用 SQLite 算法, 因为 MySQL 表结构一样)
            # 临时拉 daily_practices 到内存
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT date, practice_at, total_minutes, items FROM daily_practices "
                    "ORDER BY date ASC"
                )
                rows = cur.fetchall()
            from datetime import datetime
            from collections import defaultdict
            threshold, check_fn = SEASONAL_CALC[aid]
            monthly_achieved: dict[str, bool] = defaultdict(bool)
            for row in rows:
                # MySQL 端 date / practice_at 是 datetime 对象, str() 转 ISO
                date_str = str(row["date"])[:7]
                if not date_str or date_str == "":
                    continue
                if check_fn is not None:
                    if check_fn({"total_minutes": row["total_minutes"], "items": row["items"]}):
                        monthly_achieved[date_str] = True
                elif threshold is not None:
                    pat = row["practice_at"]
                    if not pat:
                        continue
                    try:
                        ts = datetime.strptime(str(pat)[:19], "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        continue
                    if ts.hour < threshold:
                        monthly_achieved[date_str] = True

            count = sum(1 for v in monthly_achieved.values() if v)
            history_periods = sorted(monthly_achieved.keys())
            if count == 0:
                print(f"  {aid}: 无历史激活, 跳过")
                continue

            # 2. UPDATE raw_stats (合并现有)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT raw_stats FROM achievement_stats WHERE achievement_id=%s",
                    (aid,),
                )
                row = cur.fetchone()
                existing: dict = {}
                if row is not None and row["raw_stats"]:
                    try:
                        existing = json.loads(row["raw_stats"])
                    except (TypeError, ValueError):
                        existing = {}

                if row is None:
                    print(f"  {aid}: stats 行不存在, 跳过 (等 calc_all 首次调用自动建)")
                    continue

                new_stats = {
                    "count": count,
                    "history_periods": sorted(set(existing.get("history_periods", []) + history_periods)),
                }
                merged = {**existing, **new_stats}
                cur.execute(
                    "UPDATE achievement_stats SET raw_stats=%s WHERE achievement_id=%s",
                    (json.dumps(merged, ensure_ascii=False, sort_keys=True), aid),
                )
                conn.commit()
                print(f"  {aid}: count={count}, history_periods[:5]={new_stats['history_periods'][:5]}{'...' if len(new_stats['history_periods'])>5 else ''}")
    finally:
        conn.close()
    print("\n云端 MySQL 回填完成")


def main():
    parser = argparse.ArgumentParser(description="Backfill seasonal badge raw_stats JSON (sprint 26080702)")
    parser.add_argument("--target", choices=["local", "cloud"], required=True,
                        help="local=改本地 SQLite; cloud=改云端 MySQL (走 ~/.dizical/.env)")
    args = parser.parse_args()

    print(f"=== backfill_seasonal_count.py --target={args.target} ===")
    if args.target == "local":
        _apply_local()
    else:
        _apply_cloud()


if __name__ == "__main__":
    main()