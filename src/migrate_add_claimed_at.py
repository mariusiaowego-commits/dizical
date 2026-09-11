"""Migration: 给 achievement_stats 加 claimed_at 列 (sprint 26091101 badge-3d-CCG).

2026-09-11 feat/sprint-26091101-badge-3d-ccg:
把徽章"获得"和"领取"两个语义拆开:
- achieved='Y' (已有) — calc 评估通过 / 设计时纪念章
- claimed_at IS NULL — UI 全局拦截弹窗仍要弹
- claimed_at NOT NULL — 已领取, 不再弹窗

变更:
  1. ALTER TABLE achievement_stats ADD COLUMN claimed_at TEXT DEFAULT NULL (幂等)
  2. 历史平滑: achieved='Y' AND claimed_at IS NULL 的行 → claimed_at = achieved_at
     (老徽章视作已领取, 避免上线当天全部弹窗轰炸)
  3. CREATE INDEX IF NOT EXISTS idx_achievement_stats_unclaimed 部分索引

支持双后端 (跟 migrate_add_web_users.py 同模式):
  - 默认 SQLite: data/dizi.db
  - DATABASE_URL=mysql* → MySQL (CloudRun 生产)

幂等: 已存在则跳过; 重复运行结果一致 (除了 history fill 会变 rowcount=0).

执行:
    # 本地 SQLite
    cd /Users/mt16/dev/dizical
    python3 src/migrate_add_claimed_at.py

    # 云 MySQL (CloudRun 部署后)
    DATABASE_URL=mysql+pymysql://... python3 src/migrate_add_claimed_at.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

# ─── 路径 & 后端检测 ────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
_DB_PATH = _ROOT / "data" / "dizi.db"
_DBAL_URL = os.environ.get("DATABASE_URL", "")


def _is_mysql() -> bool:
    return _DBAL_URL.startswith("mysql")


# ─── SQLite DDL ────────────────────────────────────────────────────────────
SQLITE_ADD_COLUMN = "ALTER TABLE achievement_stats ADD COLUMN claimed_at TEXT DEFAULT NULL"
SQLITE_CREATE_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_achievement_stats_unclaimed "
    "ON achievement_stats(achievement_id) "
    "WHERE achieved = 'Y' AND claimed_at IS NULL"
)
SQLITE_BACKFILL = (
    "UPDATE achievement_stats "
    "SET claimed_at = achieved_at "
    "WHERE achieved = 'Y' AND claimed_at IS NULL AND achieved_at IS NOT NULL"
)


def _table_exists_sqlite(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def _column_exists_sqlite(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def _migrate_sqlite() -> None:
    if not _DB_PATH.exists():
        print(f"❌ SQLite DB not found at {_DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # 1. 列检查 + 幂等 ALTER
        if _column_exists_sqlite(conn, "achievement_stats", "claimed_at"):
            print("ℹ️  achievement_stats.claimed_at 已存在, 跳过 ALTER")
        else:
            conn.executescript(SQLITE_ADD_COLUMN)
            conn.commit()
            print("✅ ALTER TABLE: achievement_stats.claimed_at 已新增")

        if _table_exists_sqlite(conn, "practice_audit_log"):
            if _column_exists_sqlite(conn, "practice_audit_log", "detail"):
                print("ℹ️  practice_audit_log.detail 已存在, 跳过 ALTER")
            else:
                conn.executescript("ALTER TABLE practice_audit_log ADD COLUMN detail TEXT DEFAULT NULL")
                conn.commit()
                print("✅ ALTER TABLE: practice_audit_log.detail 已新增")

        # 2. 历史 backfill (幂等: 没有新行就 0 rowcount, 安全)
        cur = conn.execute(SQLITE_BACKFILL)
        conn.commit()
        print(f"✅ Backfill: {cur.rowcount} 行老徽章 claimed_at ← achieved_at")

        # 3. 部分索引 (IF NOT EXISTS 自带幂等)
        conn.executescript(SQLITE_CREATE_INDEX)
        conn.commit()
        print("✅ Index: idx_achievement_stats_unclaimed (achieved=Y AND claimed_at IS NULL)")

        # 4. 终态校验
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM achievement_stats WHERE achieved='Y'"
        ).fetchone()["c"]
        unclaimed = conn.execute(
            "SELECT COUNT(*) AS c FROM achievement_stats "
            "WHERE achieved='Y' AND claimed_at IS NULL"
        ).fetchone()["c"]
        claimed = conn.execute(
            "SELECT COUNT(*) AS c FROM achievement_stats "
            "WHERE achieved='Y' AND claimed_at IS NOT NULL"
        ).fetchone()["c"]
        print(
            f"📊 终态: achieved=Y 共 {total} 行 "
            f"(unclaimed={unclaimed}, claimed={claimed})"
        )
    finally:
        conn.close()


# ─── MySQL DDL (CloudRun 生产) ─────────────────────────────────────────────
MYSQL_ADD_COLUMN = (
    "ALTER TABLE achievement_stats "
    "ADD COLUMN claimed_at DATETIME NULL DEFAULT NULL"
)
MYSQL_CREATE_INDEX = (
    "CREATE INDEX idx_achievement_stats_unclaimed "
    "ON achievement_stats (achievement_id, claimed_at)"
)
MYSQL_BACKFILL = (
    "UPDATE achievement_stats "
    "SET claimed_at = achieved_at "
    "WHERE achieved = 'Y' AND claimed_at IS NULL AND achieved_at IS NOT NULL"
)


def _table_exists_mysql(conn, table: str) -> bool:
    cur = conn.execute(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
        (table,),
    )
    return cur.fetchone() is not None


def _column_exists_mysql(conn, table: str, col: str) -> bool:
    cur = conn.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table,),
    )
    return cur.fetchone() is not None


def _index_exists_mysql(conn, index_name: str) -> bool:
    cur = conn.execute(
        "SELECT INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() AND INDEX_NAME = %s",
        (index_name,),
    )
    return cur.fetchone() is not None


def _migrate_mysql() -> None:
    import pymysql

    # 解析 DATABASE_URL=mysql+pymysql://user:pwd@host:port/db
    # sqlalchemy URL → pymysql kwargs
    from urllib.parse import urlparse

    u = urlparse(_DBAL_URL.replace("mysql+pymysql://", "mysql://"))
    # u.path 可能是 str / bytes / None; urlparse 默认 str
    db_name_raw = u.path.lstrip("/")
    database_name = (
        db_name_raw.decode("utf-8") if isinstance(db_name_raw, bytes) else db_name_raw
    )
    conn = pymysql.connect(
        host=u.hostname or "",
        port=u.port or 3306,
        user=u.username or "",
        password=u.password or "",
        database=database_name,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        with conn.cursor() as cur:
            # 1. 列幂等
            if _column_exists_mysql(cur, "achievement_stats", "claimed_at"):
                print("ℹ️  achievement_stats.claimed_at 已存在, 跳过 ALTER")
            else:
                cur.execute(MYSQL_ADD_COLUMN)
                print("✅ ALTER TABLE: achievement_stats.claimed_at 已新增")

            if _table_exists_mysql(cur, "practice_audit_log"):
                if _column_exists_mysql(cur, "practice_audit_log", "detail"):
                    print("ℹ️  practice_audit_log.detail 已存在, 跳过 ALTER")
                else:
                    cur.execute("ALTER TABLE practice_audit_log ADD COLUMN detail VARCHAR(255) DEFAULT NULL")
                    print("✅ ALTER TABLE: practice_audit_log.detail 已新增")

            # 2. backfill (不区分 already-done, MySQL rowcount 0/受影响行数都对)
            cur.execute(MYSQL_BACKFILL)
            print(f"✅ Backfill: {cur.rowcount} 行老徽章 claimed_at ← achieved_at")

            # 3. 部分索引 — MySQL 不支持 partial index, 用复合索引替代
            #    (achievement_id, claimed_at) — 大部分查询都带 achievement_id, 命中率高
            if _index_exists_mysql(cur, "idx_achievement_stats_unclaimed"):
                print("ℹ️  idx_achievement_stats_unclaimed 已存在, 跳过 CREATE")
            else:
                cur.execute(MYSQL_CREATE_INDEX)
                print("✅ Index: idx_achievement_stats_unclaimed (achievement_id, claimed_at)")

            conn.commit()
    finally:
        conn.close()


# ─── 入口 ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if _is_mysql():
        print(f"🔌 检测到 DATABASE_URL, 走 MySQL 迁移")
        _migrate_mysql()
    else:
        print(f"📁 本地 SQLite: {_DB_PATH}")
        _migrate_sqlite()
    print("🎉 migrate_add_claimed_at 完成")