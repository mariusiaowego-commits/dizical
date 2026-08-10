"""
Migration: add web_users table for Sprint 26081003 (web 用户体系).

2026-08-10: web 端用户体系 (B 方案本地化).
新建 web_users 表, 替代裸奔的 verify-pin 模式. dad 在 /config/users 后台
手动建账号 + 分配角色.

字段:
  user_id            主键
  username           登录名 (UNIQUE)
  display_name       UI 显示
  password_hash      argon2 hash
  role               dad/student/family/teacher
  avatar_letter      单字母头像
  must_change_password 首次登录强制改密
  session_version    踢出所有设备用
  created_at/last_login_at
  revoked            软删

执行:
    cd /Users/mt16/dev/dizical
    python3 src/migrate_add_web_users.py

幂等: 已存在则跳过.
"""
import sys
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS web_users (
  user_id                INTEGER PRIMARY KEY AUTOINCREMENT,
  username               VARCHAR(64) UNIQUE NOT NULL,
  display_name           VARCHAR(64) NOT NULL,
  password_hash          VARCHAR(256) NOT NULL,
  role                   VARCHAR(16) NOT NULL,
  avatar_letter          VARCHAR(1),
  must_change_password   BOOLEAN DEFAULT 1,
  session_version        INTEGER DEFAULT 0,
  created_by             INTEGER,
  created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_login_at          DATETIME NULL,
  revoked                BOOLEAN DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_web_users_username ON web_users(username);
CREATE INDEX IF NOT EXISTS idx_web_users_role ON web_users(role);
"""

# MySQL schema (云端生产) — 跟 sprint 26081002 stage-list 迁移同款
# 留 placeholder, 实际跑由 CloudRun 启动时通过 env DATABASE_URL=mysql 触发
# 本脚本只本地跑 (无 DATABASE_URL)
MYSQL_SCHEMA_NOTE = """
云端 MySQL 通过 src/db_adapter.get_conn() 双写 (sprint 09 PR-G).
web_users 表在 CloudRun 启动后自动建 (走 fix/schema-init 云端镜像流程).
本地迁移只管 SQLite.
"""


def main() -> None:
    print(f"Migration: add web_users table (Sprint 26081003)")
    print(f"DB: {_DB_PATH}")
    if not _DB_PATH.exists():
        print(f"WARNING: DB 不存在 ({_DB_PATH}), 跳过 (新项目请先跑 db init)")
        return

    import sqlite3
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='web_users'"
        )
        if cur.fetchone():
            print("✓ web_users 表已存在, 跳过 (幂等)")
            return

        conn.executescript(SQLITE_SCHEMA)
        conn.commit()
        print("✓ 新建 web_users 表 + 索引 (idx_username, idx_role)")
        print()
        print("下一步: 浏览器打开 /config/users (dad 输 PIN 0905), 点'新建账号'开始.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()