"""
Migration: add unlock_strategy column to achievements table.

2026-06-16: feat/badge-unlock-strategy 需求.
设计新 badge 时, 用户选 1 种解锁策略 (跟 category 正交):
- 'immediate': 立即解锁 (纪念章, commit 时直接 achieved='Y' + achieved_at=now)
- 'calc': 走 calc 评估 (跟现状一致, 需 calc 接入后由 calc_all 决定)

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/migrate_add_unlock_strategy.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def main() -> None:
    print(f"Migration: add unlock_strategy to achievements")
    print(f"DB: {DB_PATH}")
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在 ({DB_PATH}), 跳过 (生产会通过 init + base migration 创表)")
        return

    conn = sqlite3.connect(str(DB_PATH))
    try:
        if not _has_table(conn, "achievements"):
            print("⚠️  achievements 表不存在, 跳过 (conftest / production migration 会创表带列)")
            return
        if _has_column(conn, "achievements", "unlock_strategy"):
            print("✓ unlock_strategy 列已存在, 跳过")
        else:
            # DEFAULT 'calc' 跟老行为兼容: 老 badge 没填 unlock_strategy 时
            # DB 默认 calc, 不需要 backfill 老数据
            conn.execute(
                "ALTER TABLE achievements ADD COLUMN unlock_strategy TEXT DEFAULT 'calc'"
            )
            conn.commit()
            print("✓ 加 unlock_strategy 列 (TEXT, default='calc', 老数据兼容)")
    finally:
        conn.close()

    # 验证
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute("PRAGMA table_info(achievements)")
        cols = [row[1] for row in cur.fetchall()]
        if not cols:
            print("\n⚠️  achievements 表不存在, 跳过 verify")
            return
        print(f"\n当前 achievements 列: {cols}")
        assert "unlock_strategy" in cols, "unlock_strategy 添加失败"
        # 验证老数据
        cur = conn.execute("SELECT COUNT(*) FROM achievements")
        n = cur.fetchone()[0]
        print(f"现有 achievements 行: {n} (老数据 unlock_strategy 默认为 NULL, 走 calc fallback)")
        print("\n✅ Migration 完成")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
