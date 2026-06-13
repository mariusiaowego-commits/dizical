"""
迁移: behavior_log JSON 内的 enter_time 字段值从 UTC ISO → CST ISO.

背景 (2026-06-13):
- commit 1 已加 daily_practices.practice_at 列 (代表练习时间)
- commit 2 改 behavior_log.enter_time 值:
  - 旧: UTC ISO 带 Z, e.g. "2026-06-13T02:27:12.290Z"
  - 新: CST ISO 不带 Z, e.g. "2026-06-13 10:27:12.290"
- 字段名 enter_time 保留 (前端 / report.html 已用, 避免破坏 grep)
- 语义变更: enter_time 不再是 UTC, 而是 CST 本地时间 (无 Z 后缀)

执行步骤:
1. 读 daily_practices.behavior_log JSON
2. parse 每条 entry, 把 enter_time UTC ISO → CST ISO (+8h, 去 Z)
3. UPDATE 回去

幂等: 检测到 enter_time 字符串已经是 CST 格式 (无 Z 后缀) 跳过.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def _utc_to_cst_iso(utc_iso: str) -> str | None:
    """'2026-06-13T02:27:12.290Z' → '2026-06-13 10:27:12.290'."""
    try:
        if utc_iso.endswith("Z"):
            utc_iso = utc_iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(utc_iso)
        cst = dt + timedelta(hours=8)
        ms = f".{cst.microsecond // 1000:03d}" if cst.microsecond else ""
        return f"{cst.strftime('%Y-%m-%d %H:%M:%S')}{ms}"
    except Exception:
        return None


def _is_already_cst(s: str) -> bool:
    """判断字符串是否已经是 CST ISO 格式 (无 Z 后缀, 空格分隔日期时间)."""
    if s.endswith("Z"):
        return False
    if "T" in s:
        return False  # UTC ISO 用 T 分隔
    # CST 是 'YYYY-MM-DD HH:MM:SS[.fff]' 格式
    try:
        datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        return True
    except Exception:
        return False


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # WAL-aware: checkpoint
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception:
        pass

    print("=== 迁移 behavior_log.enter_time UTC → CST ===")
    rows = conn.execute(
        "SELECT id, date, behavior_log FROM daily_practices "
        "WHERE behavior_log IS NOT NULL AND behavior_log != '[]'"
    ).fetchall()

    stats = {
        "rows_total": len(rows),
        "rows_changed": 0,
        "entries_changed": 0,
        "entries_already_cst": 0,
        "entries_parse_fail": 0,
        "no_enter_time": 0,
    }
    examples = []

    for r in rows:
        rid = r["id"]
        log_json = r["behavior_log"]
        try:
            log_list = json.loads(log_json)
        except Exception:
            continue

        changed = False
        for entry in log_list:
            old = entry.get("enter_time")
            if not old:
                stats["no_enter_time"] += 1
                continue
            if _is_already_cst(old):
                stats["entries_already_cst"] += 1
                continue
            new = _utc_to_cst_iso(old)
            if new is None:
                stats["entries_parse_fail"] += 1
                continue
            entry["enter_time"] = new
            stats["entries_changed"] += 1
            changed = True
            if len(examples) < 3:
                examples.append((rid, old, new))

        if changed:
            conn.execute(
                "UPDATE daily_practices SET behavior_log=? WHERE id=?",
                (json.dumps(log_list, ensure_ascii=False), rid),
            )
            stats["rows_changed"] += 1

    conn.commit()

    print()
    print("=== 迁移统计 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()
    print("=== 样本 (3 条 enter_time 转换) ===")
    for rid, old, new in examples:
        print(f"  id={rid}: {old} → {new}")

    print()
    print("=== 验证: 二次扫描是否还有 UTC 格式 enter_time ===")
    # 重新从 DB 读 (rows 是 commit 前的内存数据, 不能用作验证)
    verify_rows = conn.execute(
        "SELECT id, behavior_log FROM daily_practices "
        "WHERE behavior_log IS NOT NULL AND behavior_log != '[]'"
    ).fetchall()
    leftover = 0
    sample_leftover = []
    for r in verify_rows:
        log_json = r["behavior_log"]
        try:
            log_list = json.loads(log_json)
        except Exception:
            continue
        for entry in log_list:
            old = entry.get("enter_time", "")
            if old.endswith("Z") or "T" in old[:11]:
                leftover += 1
                if len(sample_leftover) < 3:
                    sample_leftover.append((r["id"], old))
    print(f"  残留 UTC 格式: {leftover} 条 (期望 0)")
    for rid, old in sample_leftover:
        print(f"    id={rid}: {old}")

    conn.close()


if __name__ == "__main__":
    main()