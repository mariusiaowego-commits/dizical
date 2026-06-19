"""
Migration: add dad_whitelist setting for minip (微信小程序) auth.

2026-06-18: dizical-minip 项目需要白名单登录。
settings 表新增 dad_whitelist (JSON list of wechat openid).
默认值 '[]'（空列表 = 没有白名单用户，小程序登录时走 pending 审批流程）。

执行:
    cd /Users/mt16/dev/dizical
    python3 src/migrate_add_dad_whitelist.py

幂等: 已存在则跳过。
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def main() -> None:
    print(f"Migration: add dad_whitelist to settings")
    print(f"DB: {DB_PATH}")
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在 ({DB_PATH}), 跳过")
        return

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute("SELECT value FROM settings WHERE key='dad_whitelist'")
        if cur.fetchone():
            print("✓ dad_whitelist 已存在, 跳过")
        else:
            conn.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES ('dad_whitelist', '[]', CURRENT_TIMESTAMP)"
            )
            conn.commit()
            print("✓ 新增 dad_whitelist = '[]'")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
