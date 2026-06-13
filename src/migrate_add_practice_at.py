"""
迁移: 给 daily_practices 加 practice_at 列 (代表练习时间 CST ISO 字符串).
─────────────────────────────────────────────────────────────────────────────
背景 (2026-06-13):
- daily_practices.created_at = SQLite DEFAULT CURRENT_TIMESTAMP (UTC, DB 写入时间)
- behavior_log.enter_time = JS new Date().toISOString() (UTC ISO 带 Z)
- 两列都是 UTC, 但前端/业务解读都当本地时间用 — first_to_act 等 badge 算时间小时错位

修复方向 (2026-06-13 拍板):
- 新加 practice_at DATETIME 列, 存 CST ISO 字符串 (无 Z 后缀, 明确本地)
- 回填逻辑:
  - behavior_log 最早 enter_time, 且 enter_time 日期部分 == date 列当天
    → practice_at = enter_time + 8h 转 CST ISO
  - 跨日补录 (211 条) — enter_time 日期 != date 列
    → practice_at = date 列日期 + '12:00:00' (保守值, README 说明)
  - behavior_log 为空 (理论上不存在)
    → practice_at = date 列日期 + '12:00:00'
- 不动 created_at, 不动 behavior_log.enter_time (下一脚本 commit 2 改)

幂等: 二次运行检测到列已存在直接跳过.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def _utc_to_cst_iso(utc_iso: str) -> str | None:
    """UTC ISO 带 Z → CST ISO 字符串 (无 Z 后缀)."""
    try:
        # enter_time 是 '2026-06-13T02:27:12.290Z' 格式
        # fromisoformat 不能解析 'Z' 后缀 (Py 3.10 才行, 3.11+ 才行), 用 replace
        if utc_iso.endswith("Z"):
            utc_iso = utc_iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(utc_iso)
        cst = dt + timedelta(hours=8)
        # 输出 '2026-06-13 10:27:12.290' (无时区后缀, 明确 CST)
        return cst.strftime("%Y-%m-%d %H:%M:%S") + (f".{cst.microsecond // 1000:03d}" if cst.microsecond else "")
    except Exception as e:
        print(f"  ⚠️ 解析失败 {utc_iso!r}: {e}")
        return None


def _enter_time_date_part(utc_iso: str) -> str | None:
    """取 UTC ISO 字符串的日期部分 (YYYY-MM-DD)."""
    try:
        if utc_iso.endswith("Z"):
            utc_iso = utc_iso[:-1] + "+00:00"
        dt = datetime.fromisoformat(utc_iso)
        cst = dt + timedelta(hours=8)  # 解释为 CST 再取日期
        return cst.strftime("%Y-%m-%d")
    except Exception:
        return None


def _is_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(r[1] == column for r in cur.fetchall())


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # WAL-aware: 强制 checkpoint 后再操作 (避免 ALTER 期间 WAL 还在积累)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception:
        pass

    # ── 幂等: 列已存在直接退出 ──
    if _is_column_exists(conn, "daily_practices", "practice_at"):
        print("✓ daily_practices.practice_at 已存在, 无需迁移")
        conn.close()
        return

    print("=== 加 practice_at 列 ===")
    conn.execute(
        "ALTER TABLE daily_practices ADD COLUMN practice_at DATETIME"
    )

    print("=== 回填 237 行 ===")
    rows = conn.execute(
        "SELECT id, date, behavior_log FROM daily_practices ORDER BY date"
    ).fetchall()

    stats = {
        "same_day": 0,      # enter_time 日期 == date 列 → 用 enter_time + 8h
        "cross_day": 0,     # enter_time 日期 != date 列 → 跨日补录, 用 date + 12:00
        "empty_log": 0,     # behavior_log 为空 → 用 date + 12:00
        "no_enter_time": 0, # behavior_log 有但没有 enter_time 字段
        "failed": 0,
    }
    examples = {"same_day": None, "cross_day": None, "empty_log": None}

    for r in rows:
        rid = r["id"]
        date_str = r["date"]  # 'YYYY-MM-DD'
        log_json = r["behavior_log"]
        if not log_json or log_json == "[]":
            practice_at = f"{date_str} 12:00:00"
            stats["empty_log"] += 1
            if examples["empty_log"] is None:
                examples["empty_log"] = (rid, date_str, practice_at)
        else:
            try:
                log_list = json.loads(log_json)
            except Exception:
                practice_at = f"{date_str} 12:00:00"
                stats["failed"] += 1
                conn.execute(
                    "UPDATE daily_practices SET practice_at=? WHERE id=?",
                    (practice_at, rid),
                )
                continue
            # 找最早一条 enter_time
            enter_times = [e.get("enter_time") for e in log_list if e.get("enter_time")]
            if not enter_times:
                practice_at = f"{date_str} 12:00:00"
                stats["no_enter_time"] += 1
            else:
                earliest_utc = min(enter_times)
                enter_date_part = _enter_time_date_part(earliest_utc)
                if enter_date_part == date_str:
                    practice_at = _utc_to_cst_iso(earliest_utc)
                    stats["same_day"] += 1
                    if examples["same_day"] is None:
                        examples["same_day"] = (rid, date_str, earliest_utc, practice_at)
                else:
                    # 跨日补录: enter_time 不是 date 列当天, 用 date + 12:00 兜底
                    practice_at = f"{date_str} 12:00:00"
                    stats["cross_day"] += 1
                    if examples["cross_day"] is None:
                        examples["cross_day"] = (rid, date_str, earliest_utc, enter_date_part, practice_at)
        conn.execute(
            "UPDATE daily_practices SET practice_at=? WHERE id=?",
            (practice_at, rid),
        )

    conn.commit()

    print()
    print("=== 回填统计 ===")
    for k, v in stats.items():
        print(f"  {k}: {v} 行")
    print()
    print("=== 样本 (每类 1 条) ===")
    if examples["same_day"]:
        rid, d, utc, cst = examples["same_day"]
        print(f"  same_day  : id={rid} date={d} enter_time_utc={utc} → practice_at={cst}")
    if examples["cross_day"]:
        rid, d, utc, enter_d, cst = examples["cross_day"]
        print(f"  cross_day : id={rid} date={d} enter_time_utc={utc} (enter_date={enter_d}) → practice_at={cst}")
    if examples["empty_log"]:
        rid, d, cst = examples["empty_log"]
        print(f"  empty_log : id={rid} date={d} → practice_at={cst}")

    print()
    print("=== 验证: 抽查 practice_at 跟 date 列一致性 ===")
    cur = conn.execute(
        "SELECT COUNT(*) FROM daily_practices WHERE practice_at IS NULL OR practice_at = ''"
    )
    null_count = cur.fetchone()[0]
    print(f"  NULL/空: {null_count} 行 (期望 0)")
    cur = conn.execute(
        "SELECT COUNT(*) FROM daily_practices WHERE substr(practice_at, 1, 10) != date"
    )
    mismatch = cur.fetchone()[0]
    print(f"  practice_at 日期部分 != date 列: {mismatch} 行 (期望 0)")
    cur = conn.execute("SELECT COUNT(*) FROM daily_practices")
    total = cur.fetchone()[0]
    print(f"  总行数: {total}")

    conn.close()


if __name__ == "__main__":
    main()