"""
Migration: add web_users + web_invites tables for Sprint 26081003 (web 用户体系).

2026-08-10: web 端用户体系 (B 方案本地化).
新建 web_users 表, 替代裸奔的 verify-pin 模式. dad 在 /config/users 后台
手动建账号 + 分配角色.

字段:
  user_id            主键
  username           登录名 (UNIQUE)
  display_name       UI 显示
  password_hash      scrypt hash (v3.2 改 stdlib)
  role               dad/student/family/teacher
  avatar_letter      单字母头像
  must_change_password 首次登录强制改密
  session_version    踢出所有设备用
  created_at/last_login_at
  revoked            软删
  login_failed_count Q4 lockout
  locked_until       Q4 lockout

v3.2 (2026-08-10): 加 MySQL DDL 支持, 双后端幂等迁移
  - 检测 DATABASE_URL=mysql* → 走 _migrate_mysql
  - 否则 → 走 _migrate_sqlite

执行:
    # 本地 SQLite
    cd /Users/mt16/dev/dizical
    python3 src/migrate_add_web_users.py

    # 云 MySQL (CloudRun 部署后)
    DATABASE_URL=mysql+pymysql://... python3 src/migrate_add_web_users.py

幂等: 已存在则跳过.
"""
import os
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

# ─── MySQL DDL (云端生产, v3.2) ──────────────────────────────────────
MYSQL_SCHEMA = """
CREATE TABLE IF NOT EXISTS web_users (
  user_id                INT AUTO_INCREMENT PRIMARY KEY,
  username               VARCHAR(64) NOT NULL UNIQUE,
  display_name           VARCHAR(64) NOT NULL,
  password_hash          VARCHAR(256) NOT NULL,
  role                   VARCHAR(16) NOT NULL,
  avatar_letter          VARCHAR(1),
  must_change_password   TINYINT DEFAULT 1,
  session_version        INT DEFAULT 0,
  created_by             INT,
  created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_login_at          DATETIME NULL,
  revoked                TINYINT DEFAULT 0,
  login_failed_count     INT DEFAULT 0,
  locked_until           DATETIME NULL,
  INDEX idx_username (username),
  INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

MYSQL_INVITES_SCHEMA = """
CREATE TABLE IF NOT EXISTS web_invites (
  invite_id      INT AUTO_INCREMENT PRIMARY KEY,
  invite_token   VARCHAR(64) NOT NULL UNIQUE,
  role           VARCHAR(16) NOT NULL,
  max_uses       INT DEFAULT 1,
  used_count     INT DEFAULT 0,
  expires_at     DATETIME NOT NULL,
  created_by     INT,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  revoked        TINYINT DEFAULT 0,
  note           VARCHAR(128)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# MySQL 增量 ALTER (用 information_schema 检查列)
LOCKOUT_MIGRATION_MYSQL = [
    "ALTER TABLE web_users ADD COLUMN login_failed_count INT DEFAULT 0",
    "ALTER TABLE web_users ADD COLUMN locked_until DATETIME NULL",
]


def _migrate_sqlite() -> None:
    """本地 SQLite 迁移."""
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
            print("✓ lockout 字段已存在")

        # web_invites 表 (Q7 邀请链接)
        conn.executescript(WEB_INVITES_SCHEMA)
        conn.commit()
        print("✓ web_invites 表已就绪 (Q7 邀请链接)")
    finally:
        conn.close()


def _migrate_mysql(database_url: str) -> None:
    """云 MySQL 迁移 (DATABASE_URL=mysql+pymysql://...)."""
    import pymysql
    from urllib.parse import urlparse
    u = urlparse(database_url.replace("mysql+pymysql://", "mysql://"))
    print(f"DB (云 MySQL): {u.hostname}:{u.port}/{u.path.lstrip('/')}")
    conn = pymysql.connect(
        host=u.hostname, port=u.port or 3306,
        user=u.username, password=u.password, database=u.path.lstrip('/'),
        autocommit=True,
    )
    try:
        cur = conn.cursor()

        # web_users
        cur.execute("SHOW TABLES LIKE 'web_users'")
        if cur.fetchone():
            print("✓ web_users 表已存在")
        else:
            for stmt in MYSQL_SCHEMA.strip().split(";"):
                s = stmt.strip()
                if s:
                    cur.execute(s)
            print("✓ 新建 web_users 表 + 索引")

        # 增量迁移: 检查列, 缺就 ALTER
        cur.execute("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'web_users'
        """)
        existing_cols = {row[0] for row in cur.fetchall()}
        added = []
        for stmt in LOCKOUT_MIGRATION_MYSQL:
            col_name = stmt.split("ADD COLUMN ")[1].split(" ")[0]
            if col_name not in existing_cols:
                cur.execute(stmt)
                added.append(col_name)
        if added:
            print(f"✓ 增量迁移: 加列 {added}")
        else:
            print("✓ lockout 字段已存在")

        # web_invites
        cur.execute("SHOW TABLES LIKE 'web_invites'")
        if cur.fetchone():
            print("✓ web_invites 表已存在")
        else:
            for stmt in MYSQL_INVITES_SCHEMA.strip().split(";"):
                s = stmt.strip()
                if s:
                    cur.execute(s)
            print("✓ 新建 web_invites 表")
    finally:
        conn.close()


def _ensure_dad_account(conn, is_mysql: bool) -> str | None:
    """若 web_users 里没 username='dad', 建 1 个 (role=dad, 随机强密码).

    Sprint 26081003 v3.3: dad root 账号 (替代全局 PIN 0905 模式).
    返新密码 (None = 已存在, 跳过).
    """
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM web_users WHERE username = 'dad'")
    if cur.fetchone():
        return None
    # 生成 12 位密码: 字母 + 数字 (无易混字符)
    import secrets, string
    alphabet = string.ascii_letters.replace("l", "").replace("I", "").replace("O", "") + string.digits.replace("0", "").replace("1", "")
    new_pw = "".join(secrets.choice(alphabet) for _ in range(12))
    pw_hash = _hash_password_scrypt(new_pw)
    # 写库
    if is_mysql:
        cur.execute("""
            INSERT INTO web_users
            (username, display_name, password_hash, role, avatar_letter,
             must_change_password, session_version, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
        """, ("dad", "爸爸", pw_hash, "dad", "爸", 1, 0))
    else:
        cur.execute("""
            INSERT INTO web_users
            (username, display_name, password_hash, role, avatar_letter,
             must_change_password, session_version, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
        """, ("dad", "爸爸", pw_hash, "dad", "爸", 1, 0))
    conn.commit()
    return new_pw


def _hash_password_scrypt(plain: str) -> str:
    """跟 auth.py 同样的 scrypt 实现 (避免循环 import)."""
    import os as _os, hashlib, hmac, base64
    N = 2**14; R = 8; P = 1; DK = 32
    salt = _os.urandom(16)
    hk = hashlib.scrypt(plain.encode("utf-8"), salt=salt,
                        n=N, r=R, p=P, dklen=DK, maxmem=64 * 1024 * 1024)
    return f"scrypt${base64.b64encode(salt).decode('ascii')}${base64.b64encode(hk).decode('ascii')}"


def ensure_dad_account_sqlite() -> None:
    """本地 SQLite: migrate 跑完调用, 建 dad 账号 (如果缺)."""
    import sqlite3 as _sq3
    if not _DB_PATH.exists():
        return
    conn = _sq3.connect(str(_DB_PATH))
    try:
        pw = _ensure_dad_account(conn, is_mysql=False)
        if pw:
            print(f"✓ 自动建 dad 账号 (root): username=dad, 初始密码={pw}")
            print(f"  请在首次登录后改密!")
        else:
            print(f"✓ dad 账号已存在")
    finally:
        conn.close()


def ensure_dad_account_mysql_if_needed(db_url: str) -> None:
    """云 MySQL: 同上 (migrate 跑过且 DATABASE_URL 是 mysql)."""
    if not db_url.startswith("mysql"):
        return
    import pymysql
    from urllib.parse import urlparse
    u = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
    conn = pymysql.connect(
        host=u.hostname, port=u.port or 3306,
        user=u.username, password=u.password, database=u.path.lstrip('/'),
        autocommit=True,
    )
    try:
        pw = _ensure_dad_account(conn, is_mysql=True)
        if pw:
            print(f"✓ 自动建 dad 账号 (云 MySQL): username=dad, 初始密码={pw}")
            print(f"  请在首次登录后改密!")
        else:
            print(f"✓ dad 账号已存在 (云 MySQL)")
    finally:
        conn.close()


def main() -> None:
    print(f"Migration: add web_users + web_invites (Sprint 26081003 v3.3)")
    # 检测 DATABASE_URL: 有 → 走云 MySQL, 无 → 本地 SQLite
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if db_url.startswith("mysql"):
        _migrate_mysql(db_url)
    else:
        _migrate_sqlite()
    # Sprint 26081003 v3.3: 自动建 dad root 账号 (一次性, 启动日志打印初始密码)
    ensure_dad_account_sqlite()
    ensure_dad_account_mysql_if_needed(db_url)

    print()
    print("下一步: 浏览器打开 /login, 点'管理员登录'按钮 (右上), 用 username=dad 登录.")
    print("dad 初始密码: 见服务启动日志 (/tmp/dizical-8765.log) 或本脚本输出.")


if __name__ == "__main__":
    main()