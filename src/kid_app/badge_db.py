"""
Badge 三表写入 + 事务 + 查询 helper.

设计:
- 所有 INSERT 走 badge_write_tx() 事务, 失败自动回滚
- 查询走单例 db._get_connection() 读 (badge_db.py 不缓存, 让调用方决定是否 cache)
- V1 路径 A (用户 2026-06-12 拍板): 只写 1 行 unlocked, 不沿用老 migrate_achievements.py 写 2 行的逻辑
- batch insert (PR-C) 走相同的 INSERT, 多个 row 共享一个事务

依赖:
- src.database.db (单例 Database, 持有 sqlite3 连接)
- 路径: src/kid_app/badge_db.py

V3.1 (sprint 26082401 PR #287, 2026-08-24):
- commit-from-draft 在云端 MySQL backend 报 AttributeError, 根因是本文件
  sqlite3 风格 `conn.execute(sqlite_sql, params)` 在 pymysql Connection 不工作
- 修法: 全改用 `?` positional + src.db_adapter.execute() 统一双后端
- src.db_adapter 把 `?` 转 `%s` 给 pymysql, sqlite3 直接吃 `?`
- 验证: tests/test_badge_db_mysql_compat.py (4 case: sqlite + pymysql mock)
"""
from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from src.database import db
from src.db_adapter import execute as _db_execute  # PR #287: 双后端统一入口

logger = logging.getLogger(__name__)

# Sprint 26091201 feat/badge-3d-ccg B-1:
# ensure_card_theme_column() 模块级幂等标志 — 每进程只跑一次
_CARD_THEME_COL_DONE = False


# ─── 迁移 (双后端幂等) ───────────────────────────────────────────────

def _ensure_card_theme_sqlite(conn: sqlite3.Connection) -> bool:
    """SQLite 幂等加 card_theme 列. 返 True=本次新增列, False=列已存在."""
    rows = conn.execute("PRAGMA table_info(achievements)").fetchall()
    existing = {r[1] for r in rows}  # r[1] = name
    if "card_theme" in existing:
        return False
    conn.execute("ALTER TABLE achievements ADD COLUMN card_theme TEXT")
    conn.commit()
    return True


def _ensure_card_theme_mysql(conn) -> bool:
    """MySQL 幂等加 card_theme 列. 返 True=本次新增列, False=列已存在."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'achievements'"
    )
    rows = cur.fetchall()
    if not rows:
        # 表不存在 (极少见), 跳过 ALTER — 由后续 _init_tables 建表时负责
        return False
    existing = {r[0] if not isinstance(r, dict) else r["COLUMN_NAME"] for r in rows}
    if "card_theme" in existing:
        return False
    cur.execute("ALTER TABLE achievements ADD COLUMN card_theme TEXT NULL")
    # 不在此处 commit: MySQL DDL 隐式提交 (ALTER 本身已生效), 且调用方
    # (badge_write_tx / 启动 hook) 负责提交 — 避免写事务内多一次 commit.
    return True


def ensure_card_theme_column(conn: Any) -> None:
    """ensure_card_theme_column: 双后端幂等 ALTER TABLE achievements ADD card_theme TEXT.

    失败只 logger.warning, 不抛 (读页面不能因为迁移失败 500).
    成功才置 _CARD_THEME_COL_DONE=True, 后续调用直接 return.

    Args:
        conn: sqlite3.Connection (dev) 或 pymysql.Connection (cloud)
    """
    global _CARD_THEME_COL_DONE
    if _CARD_THEME_COL_DONE:
        return
    try:
        # 检测后端类型 — sqlite3.Connection 必有 cursor() + 不带 pymysql 特性
        # 简单 heuristic: sqlite3.Connection .row_factory 是 sqlite3.Row-like, pymysql 不带
        if isinstance(conn, sqlite3.Connection):
            added = _ensure_card_theme_sqlite(conn)
        else:
            added = _ensure_card_theme_mysql(conn)
        if added:
            logger.info("badge_db: ALTER TABLE achievements ADD COLUMN card_theme (本次新增)")
        _CARD_THEME_COL_DONE = True
    except Exception as e:
        # 读路径不能因为迁移失败 500 — 降级为 warning, 下次还会重试 (避免静默卡住)
        logger.warning(f"badge_db.ensure_card_theme_column 失败 (下次还会重试): {e}")


# ─── 事务 ─────────────────────────────────────────────────────────

@contextmanager
def badge_write_tx() -> Iterator[sqlite3.Connection]:
    """Badge 上线 / 批量写入的事务封装.

    成功: 自动 commit
    失败: 自动 rollback + 抛异常 (让调用方知道)

    警告: 不要在事务内调 db._get_connection() (会另开连接, 看不到未提交数据).
    """
    # Sprint 26091201 B-1: 写事务进入时确保 card_theme 列就绪
    # (V2.1 INSERT 引用该列, 缺则 OperationalError)
    conn = db._get_connection()
    ensure_card_theme_column(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass  # rollback 失败也继续抛原异常
        raise


# ─── 查询 ─────────────────────────────────────────────────────────

def check_id_unique(badge_id: str) -> bool:
    """检查 badge id 在 achievements 表唯一. True=可用, False=已存在."""
    conn = db._get_connection()
    try:
        cur = _db_execute(
            conn,
            "SELECT 1 FROM achievements WHERE id = ? LIMIT 1",
            (badge_id,),
        )
        return cur.fetchone() is None
    finally:
        pass  # 单例连接, 不关


def fetch_max_sort_order() -> int:
    """返回当前 max(sort_order), 给新 badge 默认 sort_order = max+1."""
    conn = db._get_connection()
    cur = _db_execute(conn, "SELECT COALESCE(MAX(sort_order), 0) FROM achievements")
    return int(cur.fetchone()[0])


def next_version(badge_id: str) -> int:
    """返回下一个 version 号 (= MAX+1, 最小 1).

    用途:
    - V1 新建 badge: 返回 1
    - PR-C 批量新建 (新派生 id): 返回 1
    - V1.x 换新图 (re-generate): 返回 MAX+1
    """
    conn = db._get_connection()
    cur = _db_execute(
        conn,
        "SELECT COALESCE(MAX(version), 0) + 1 FROM achievement_badges "
        "WHERE achievement_id = ?",
        (badge_id,),
    )
    return int(cur.fetchone()[0])


def fetch_badge_url(badge_id: str) -> str | None:
    """返回 is_current=1 行的 url. None=未找到.

    用途: PR-B 改造 BADGE_URLS / BADGE_FILES 时调用, 也给前端直接查图.
    """
    conn = db._get_connection()
    cur = _db_execute(
        conn,
        "SELECT url FROM achievement_badges "
        "WHERE achievement_id = ? AND is_current = 1 LIMIT 1",
        (badge_id,),
    )
    row = cur.fetchone()
    return row[0] if row else None


def list_all_current_badge_urls() -> dict[str, str]:
    """返回 {badge_id: url} 字典 (is_current=1).

    用途: PR-B BADGE_URLS / BADGE_FILES cache 刷新时调用, 一次 SQL 拿全表.
    """
    conn = db._get_connection()
    cur = _db_execute(
        conn,
        "SELECT achievement_id, url FROM achievement_badges WHERE is_current = 1",
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def badge_exists(badge_id: str) -> bool:
    """检查 achievement_id 是否在 achievements 表 (任何 category). True=存在."""
    return not check_id_unique(badge_id)


# ─── 写入 (走 badge_write_tx) ────────────────────────────────────

def insert_achievement_row(conn: sqlite3.Connection, ach: dict[str, Any]) -> None:
    """写 achievements 表 1 行.

    必填 key: id, name, type, category, stat_logic, description, display_format
    可选: threshold, unlocked_template, placeholder, sort_order, seasonal_type, cond_text, unlock_strategy

    seasonal_type 必填 (CHECK 约束 default='monthly' 也行, 但 V1 显式传)
    cond_text 是 feat/badge-cond-text (2026-06-15) 加的可选字段, 用户/AI 填的"条件一句话"
    unlock_strategy 是 feat/badge-unlock-strategy (2026-06-16) 加的 enum ('immediate'|'calc')
    """
    # sort_order 不传时取 max+1
    if "sort_order" not in ach or ach["sort_order"] is None:
        ach["sort_order"] = fetch_max_sort_order() + 1

    # seasonal_type 不传时给默认值 (防止 CHECK 约束失败)
    if "seasonal_type" not in ach or not ach["seasonal_type"]:
        ach["seasonal_type"] = "monthly"

    # 补全 named param 需要的 key (sqlite3 strict named param, 缺 key 抛错)
    defaults = {
        "threshold": None,
        "unlocked_template": None,
        "placeholder": None,
        "cond_text": None,  # feat/badge-cond-text 2026-06-15
        "unlock_strategy": "calc",  # feat/badge-unlock-strategy 2026-06-16
        "achieved_at_override": None,  # V2.6 (2026-06-16) feat/badge-achieved-at-override
        "display_format": "icon",  # PR #287 follow-up: V2 表单不收 display_format, 给默认值防 KeyError
        "card_theme": None,  # Sprint 26091201 feat/badge-3d-ccg B-1: 卡面主题 (NULL → resolve_card_theme 兜底)
    }
    for k, v in defaults.items():
        ach.setdefault(k, v)

    # PR #287: sqlite3 named param (`:id`/`:name`) 不被 pymysql 支持
    # 改为 positional `?` + tuple, 由 src.db_adapter 转 `?` → `%s` 给 MySQL
    # 字段顺序必须跟 INSERT 列对齐 (16 列, Sprint 26091201 B-1 加 card_theme)
    insert_tuple = (
        ach["id"],
        ach["name"],
        ach["type"],
        ach["category"],
        ach["stat_logic"],
        ach["description"],
        ach["display_format"],
        ach["threshold"],
        ach["unlocked_template"],
        ach["placeholder"],
        ach["sort_order"],
        ach["seasonal_type"],
        ach["cond_text"],
        ach["unlock_strategy"],
        ach["achieved_at_override"],
        ach["card_theme"],
    )
    _db_execute(
        conn,
        """
        INSERT INTO achievements
          (id, name, type, category, stat_logic, description,
           display_format, threshold, unlocked_template, placeholder,
           sort_order, seasonal_type, cond_text, unlock_strategy,
           achieved_at_override, card_theme)
        VALUES
          (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        insert_tuple,
    )


def insert_achievement_stats_row(
    conn: sqlite3.Connection,
    badge_id: str,
    achieved: str = "N",
    achieved_at: str | None = None,
) -> None:
    """写 achievement_stats 表 1 行 (仅 milestone).

    V2.3 (2026-06-16) feat/badge-unlock-strategy:
    - achieved 默认 'N' (老行为, 走 calc 评估)
    - achieved='Y' + achieved_at=ISO 时 立即解锁 (设计时纪念章场景, 跳过 calc)
    - raw_stats='{}' (空 JSON), computed_value=NULL
    """
    _db_execute(
        conn,
        """
        INSERT INTO achievement_stats
          (achievement_id, achieved, achieved_at, raw_stats, computed_value)
        VALUES
          (?, ?, ?, '{}', NULL)
        """,
        (badge_id, achieved, achieved_at),
    )

def insert_badge_row(
    conn: sqlite3.Connection,
    badge_id: str,
    url: str,
    version: int,
) -> None:
    """写 achievement_badges 表 1 行 (V1 路径 A: unlocked only).

    is_locked=0 固定, is_current=1 固定 (新 badge 第 1 张图).
    """
    _db_execute(
        conn,
        """
        INSERT INTO achievement_badges
          (achievement_id, url, is_locked, version, is_current)
        VALUES (?, ?, 0, ?, 1)
        """,
        (badge_id, url, version),
    )


def update_badge_current(badge_id: str, new_url: str, new_version: int) -> None:
    """换新图: UPDATE 旧行 is_current=0, INSERT 新行 is_current=1.

    走事务. 失败自动回滚 (旧行 is_current 保持原状).
    """
    with badge_write_tx() as conn:
        _db_execute(
            conn,
            "UPDATE achievement_badges SET is_current = 0 "
            "WHERE achievement_id = ? AND is_current = 1",
            (badge_id,),
        )
        insert_badge_row(conn, badge_id, new_url, new_version)
