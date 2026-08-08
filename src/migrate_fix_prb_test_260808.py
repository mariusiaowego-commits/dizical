"""
Migration: 清 prb_test_item + prb_test_item_3 脏数据 — sprint 26080803 (2026-08-08)

dad 8-08 反馈 + 三证据法验证:
1. 标识符: prb_test_item (item_id 999001), prb_test_item_3 (item_id 999003)
   "PRactice Bug test_item" 自标识, item_id 远超真实科目 id 1-47
2. created_at: 2026-08-07 13:13-13:20 集中创建, 跟 sprint 26080701 真云验证窗口对齐
3. practice_date vs created_at: 2026-07-28 (8天前) 但 created_at=2026-08-07 13:13-13:20
   → 真云验证脚本批量插入, 不是真练习

清理目标:
- DELETE practice_sessions WHERE item_id IN (999001, 999003) — 4 条 (id 1548/1550/1552/1554)
- DELETE practice_items WHERE item_id IN (999001, 999003) — 2 个科目
- 重算 daily_practices 7-28 items JSON + total_minutes (去除 prb_test)

执行模式 (互斥):
    python src/migrate_fix_prb_test_260808.py --target=local    # 改本地 SQLite
    python src/migrate_fix_prb_test_260808.py --target=cloud    # 改云端 MySQL (~/.dizical/.env)

idempotent: WHERE item_id IN (999001, 999003) 多次跑结果一致
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"

# 8-05 沉淀的红线: 不要 JSON_REMOVE 单独删字段, 必须重写整个 items JSON + 重算 total_minutes
PRB_ITEM_IDS = (999001, 999002, 999003)
PRB_NAME_PATTERN = "prb%"  # 兼容未来 prb_test_item_N 变种 (三证据法标识符匹配)


def _backup_local(snapshot: list[str]) -> Path:
    """本地备份, 让 dad 可回滚."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    p = BACKUP_DIR / f"prb-test-260808-pre-cleanup-{ts}.txt"
    with open(p, "w", encoding="utf-8") as f:
        f.write("# Pre-cleanup snapshot (sprint 26080803)\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write("# Format: table | key | old_value\n")
        for line in snapshot:
            f.write(line + "\n")
    return p


def _apply_local() -> None:
    """改本地 SQLite. idempotent — WHERE item_id IN (...) 限定."""
    if not DB_PATH.exists():
        print(f"DB 不存在 ({DB_PATH}), 跳过")
        return
    conn = sqlite3.connect(str(DB_PATH))
    try:
        snapshot: list[str] = []

        # 动态 IN 占位符 (sqlite3 tuple 长度必须匹配)
        placeholders = ",".join(["?"] * len(PRB_ITEM_IDS))
        ids_tuple = tuple(PRB_ITEM_IDS)

        # 1. 找出要删的 sessions
        cur = conn.execute(
            f"SELECT id, item_id, practice_date, duration_minutes, content "
            f"FROM practice_sessions WHERE item_id IN ({placeholders}) ORDER BY id",
            ids_tuple,
        )
        sessions = cur.fetchall()
        print(f"  本地 prb sessions: {len(sessions)} 条")
        for s in sessions:
            print(f"    id={s[0]} item_id={s[1]} date={s[2]} dur={s[3]}min content={s[4]!r}")
            snapshot.append(f"practice_sessions | id={s[0]} | item_id={s[1]} | {s[2]} | {s[3]}min | {s[4]!r}")

        if not sessions:
            print("  本地 SQLite 无 prb 脏数据, 跳过 (8-05 已清)")
            return

        # 2. 找出涉及的 daily_practices 日期
        cur = conn.execute(
            f"SELECT DISTINCT practice_date FROM practice_sessions WHERE item_id IN ({placeholders})",
            ids_tuple,
        )
        affected_dates = [r[0] for r in cur.fetchall()]
        print(f"  影响的 daily_practices 日期: {affected_dates}")

        # 3. 备份 daily_practices 旧 items
        for date in affected_dates:
            cur = conn.execute(
                "SELECT items, total_minutes, behavior_log FROM daily_practices WHERE date=?",
                (date,),
            )
            row = cur.fetchone()
            if row:
                snapshot.append(f"daily_practices | date={date} | items={row[0]} | total={row[1]} | behavior_log={row[2]}")

        # 4. 备份 practice_items (item_id + name LIKE 双重匹配)
        cur = conn.execute(
            f"SELECT item_id, name, is_archived FROM practice_items "
            f"WHERE item_id IN ({placeholders}) OR name LIKE ?",
            ids_tuple + (PRB_NAME_PATTERN,),
        )
        items = cur.fetchall()
        for it in items:
            snapshot.append(f"practice_items | item_id={it[0]} | name={it[1]} | is_archived={it[2]}")

        _backup_local(snapshot)
        print(f"  备份已写入 data/backups/")

        # 5. DELETE sessions
        cur = conn.execute(
            f"DELETE FROM practice_sessions WHERE item_id IN ({placeholders})",
            ids_tuple,
        )
        deleted_sess = cur.rowcount
        print(f"  DELETE sessions: {deleted_sess} 条")

        # 6. 重写 daily_practices.items (去除 prb_test 字段) + 重算 total_minutes
        for date in affected_dates:
            cur = conn.execute(
                "SELECT items, total_minutes, behavior_log FROM daily_practices WHERE date=?",
                (date,),
            )
            row = cur.fetchone()
            if not row:
                continue
            old_items_json, old_total, behavior_log = row
            try:
                items_list = json.loads(old_items_json) if old_items_json else []
            except json.JSONDecodeError:
                print(f"  WARN: daily {date} items JSON 解析失败, 跳过重写")
                continue

            new_items = [it for it in items_list if it.get("item_id") not in PRB_ITEM_IDS]
            removed_minutes = sum(
                it.get("minutes", 0) for it in items_list if it.get("item_id") in PRB_ITEM_IDS
            )
            new_total = max(0, old_total - removed_minutes)

            # 同时清 behavior_log 里的 prb 引用 (8-08 老 JSON 可能有)
            try:
                beh_log = json.loads(behavior_log) if behavior_log else []
            except json.JSONDecodeError:
                beh_log = []
            new_beh = []
            for entry in beh_log:
                if entry.get("item_id") in PRB_ITEM_IDS:
                    continue
                # 过滤该 item 的 sessions 引用
                if "sessions" in entry:
                    entry["sessions"] = [
                        s for s in entry["sessions"]
                        if s.get("item_id") not in PRB_ITEM_IDS
                    ]
                    if not entry["sessions"]:
                        continue
                new_beh.append(entry)

            conn.execute(
                "UPDATE daily_practices SET items=?, total_minutes=?, behavior_log=? WHERE date=?",
                (json.dumps(new_items, ensure_ascii=False), new_total,
                 json.dumps(new_beh, ensure_ascii=False), date),
            )
            print(f"  daily {date}: items {len(items_list)} → {len(new_items)} fields, "
                  f"total {old_total} → {new_total} (-{removed_minutes}min)")

        # 7. DELETE items (item_id + name LIKE 双重匹配, 兼容孤儿 items)
        cur = conn.execute(
            f"DELETE FROM practice_items WHERE item_id IN ({placeholders}) OR name LIKE ?",
            ids_tuple + (PRB_NAME_PATTERN,),
        )
        deleted_items = cur.rowcount
        print(f"  DELETE items: {deleted_items} 条")

        conn.commit()
        print(f"\n本地 SQLite prb_test 清理完成 ({deleted_sess} sessions + {deleted_items} items)")
    finally:
        conn.close()


def _apply_cloud() -> None:
    """改云端 MySQL. 优先 ~/.dizical/.env 里的 DATABASE_URL, 否则用 MYSQL_* 5 件套拼."""
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
        # 沿用 sprint 26080701 模式: 从 MYSQL_* 5 件套拼
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

    conn = pymysql.connect(
        host=host, port=port, user=user, password=pwd, database=db,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )
    _run_cloud_cleanup(conn)


def _run_cloud_cleanup(conn) -> None:
    """实际云端清理逻辑, conn 已建好."""
    try:
        with conn.cursor() as cur:
            # 1. 找 sessions
            placeholders = ",".join(["%s"] * len(PRB_ITEM_IDS))
            cur.execute(
                f"SELECT id, item_id, practice_date, duration_minutes, content "
                f"FROM practice_sessions WHERE item_id IN ({placeholders}) ORDER BY id",
                PRB_ITEM_IDS,
            )
            sessions = cur.fetchall()
            print(f"  云端 prb sessions: {len(sessions)} 条")
            for s in sessions:
                print(f"    id={s['id']} item_id={s['item_id']} date={s['practice_date']} "
                      f"dur={s['duration_minutes']}min content={s['content']!r}")

            if not sessions:
                print("  云端无 prb 脏数据, 跳过")
                return

            # 2. 涉及日期
            cur.execute(
                f"SELECT DISTINCT DATE(practice_date) AS d FROM practice_sessions "
                f"WHERE item_id IN ({placeholders})",
                PRB_ITEM_IDS,
            )
            affected_dates = [r["d"] for r in cur.fetchall()]
            print(f"  影响的 daily_practices 日期: {affected_dates}")

            # 3. 备份 + 重写 daily_practices (MySQL items 是 JSON 字符串)
            for date in affected_dates:
                cur.execute(
                    "SELECT items, total_minutes, behavior_log FROM daily_practices WHERE date=%s",
                    (date,),
                )
                row = cur.fetchone()
                if not row:
                    continue
                old_items_json = row["items"]
                old_total = row["total_minutes"]
                behavior_log = row["behavior_log"]

                try:
                    items_list = json.loads(old_items_json) if old_items_json else []
                except json.JSONDecodeError:
                    print(f"  WARN: daily {date} items JSON 解析失败, 跳过重写")
                    continue

                new_items = [it for it in items_list if it.get("item_id") not in PRB_ITEM_IDS]
                removed_minutes = sum(
                    it.get("minutes", 0) for it in items_list if it.get("item_id") in PRB_ITEM_IDS
                )
                new_total = max(0, old_total - removed_minutes)

                try:
                    beh_log = json.loads(behavior_log) if behavior_log else []
                except json.JSONDecodeError:
                    beh_log = []
                new_beh = []
                for entry in beh_log:
                    if entry.get("item_id") in PRB_ITEM_IDS:
                        continue
                    if "sessions" in entry:
                        entry["sessions"] = [
                            s for s in entry["sessions"]
                            if s.get("item_id") not in PRB_ITEM_IDS
                        ]
                        if not entry["sessions"]:
                            continue
                    new_beh.append(entry)

                cur.execute(
                    "UPDATE daily_practices SET items=%s, total_minutes=%s, behavior_log=%s WHERE date=%s",
                    (json.dumps(new_items, ensure_ascii=False), new_total,
                     json.dumps(new_beh, ensure_ascii=False), date),
                )
                print(f"  daily {date}: items {len(items_list)} → {len(new_items)} fields, "
                      f"total {old_total} → {new_total} (-{removed_minutes}min)")

            # 5. DELETE sessions
            cur.execute(
                f"DELETE FROM practice_sessions WHERE item_id IN ({placeholders})",
                PRB_ITEM_IDS,
            )
            deleted_sess = cur.rowcount
            print(f"  DELETE sessions: {deleted_sess} 条")

            # 6. DELETE items (item_id + name LIKE 双重匹配, 兼容孤儿 items 无 sessions)
            cur.execute(
                f"DELETE FROM practice_items WHERE item_id IN ({placeholders}) OR name LIKE %s",
                PRB_ITEM_IDS + (PRB_NAME_PATTERN,),
            )
            deleted_items = cur.rowcount
            print(f"  DELETE items: {deleted_items} 条")

            conn.commit()
            print(f"\n云端 MySQL prb_test 清理完成 ({deleted_sess} sessions + {deleted_items} items)")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="清 prb_test_item 脏数据 (sprint 26080803)")
    parser.add_argument("--target", choices=["local", "cloud"], required=True,
                        help="local=改本地 SQLite; cloud=改云端 MySQL (走 ~/.dizical/.env)")
    args = parser.parse_args()

    print(f"=== migrate_fix_prb_test_260808.py --target={args.target} ===")
    if args.target == "local":
        _apply_local()
    else:
        _apply_cloud()


if __name__ == "__main__":
    main()