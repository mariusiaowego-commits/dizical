"""
Migration: add cond_text column to achievements table.

2026-06-15: feat/badge-cond-text 需求.
modal-cond 跟 modal-desc 当前都用 zh_story (Bug #5 修法), 文案重复.
新增 cond_text 字段, 让用户手填 / AI 生成 "达成条件" 一句话,
跟 "典故小故事" (description=zh_story) 分开显示.

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/migrate_add_cond_text.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def main() -> None:
    print(f"Migration: add cond_text to achievements")
    print(f"DB: {DB_PATH}")
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在 ({DB_PATH}), 跳过 (生产会通过 init + base migration 创表)")
        return

    conn = sqlite3.connect(str(DB_PATH))
    try:
        if _has_column(conn, "achievements", "cond_text"):
            print("✓ cond_text 列已存在, 跳过")
        else:
            conn.execute("ALTER TABLE achievements ADD COLUMN cond_text TEXT")
            conn.commit()
            print("✓ 加 cond_text 列 (TEXT, nullable, 默认 NULL)")
    finally:
        conn.close()

    # 验证
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute("PRAGMA table_info(achievements)")
        cols = [row[1] for row in cur.fetchall()]
        print(f"\n当前 achievements 列: {cols}")
        assert "cond_text" in cols, "cond_text 添加失败"
        print("\n✅ Migration 完成")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
