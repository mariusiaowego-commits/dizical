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
  revoked                BOOLEAN DEFAULT 0,
  login_failed_count     INTEGER DEFAULT 0,
  locked_until           DATETIME NULL
);
CREATE INDEX IF NOT EXISTS idx_web_users_username ON web_users(username);
CREATE INDEX IF NOT EXISTS idx_web_users_role ON web_users(role);
"""

# Sprint 26081003 v3.1 (dad 8-10): 增量迁移 lockout 字段 (幂等, 加列)
# 老 web_users 表没这两个字段, 用 ALTER TABLE 兼容 (SQLite 不支持 IF NOT EXISTS on ADD COLUMN)
# 用 PRAGMA table_info 判断, 在缺字段时 ALTER
LOCKOUT_MIGRATION_SQLITE = [
    ("login_failed_count", "INTEGER DEFAULT 0"),
    ("locked_until", "DATETIME NULL"),
]

WEB_INVITES_SCHEMA = """
CREATE TABLE IF NOT EXISTS web_invites (
  invite_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  invite_token   VARCHAR(64) UNIQUE NOT NULL,
  role           VARCHAR(16) NOT NULL,
  max_uses       INTEGER DEFAULT 1,
  used_count     INTEGER DEFAULT 0,
  expires_at     DATETIME NOT NULL,
  created_by     INTEGER,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  revoked        BOOLEAN DEFAULT 0,
  note           VARCHAR(128)
);
CREATE INDEX IF NOT EXISTS idx_web_invites_token ON web_invites(invite_token);
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
            print("✓ web_users 表已存在")
        else:
            conn.executescript(SQLITE_SCHEMA)
            conn.commit()
            print("✓ 新建 web_users 表 + 索引 (idx_username, idx_role)")

        # 增量迁移: 给老 web_users 表加 lockout 字段 (幂等)
        cur = conn.execute("PRAGMA table_info(web_users)")
        existing_cols = {row[1] for row in cur.fetchall()}
        added_cols = []
        for col_name, col_def in LOCKOUT_MIGRATION_SQLITE:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE web_users ADD COLUMN {col_name} {col_def}")
                added_cols.append(col_name)
        if added_cols:
            conn.commit()
            print(f"✓ 增量迁移: 加列 {added_cols}")
        else:
            print("✓ lockout 字段已存在 (login_failed_count / locked_until)")

        # web_invites 表 (Q7 邀请链接)
        conn.executescript(WEB_INVITES_SCHEMA)
        conn.commit()
        print("✓ web_invites 表已就绪 (Q7 邀请链接)")

        print()
        print("下一步: 浏览器打开 /config/users (dad 输 PIN 0905), 点'新建账号'开始.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()