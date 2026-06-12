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
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from src.database import db


# ─── 事务 ─────────────────────────────────────────────────────────

@contextmanager
def badge_write_tx() -> Iterator[sqlite3.Connection]:
    """Badge 上线 / 批量写入的事务封装.

    成功: 自动 commit
    失败: 自动 rollback + 抛异常 (让调用方知道)

    警告: 不要在事务内调 db._get_connection() (会另开连接, 看不到未提交数据).
    """
    conn = db._get_connection()
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
        cur = conn.execute(
            "SELECT 1 FROM achievements WHERE id = ? LIMIT 1",
            (badge_id,),
        )
        return cur.fetchone() is None
    finally:
        pass  # 单例连接, 不关


def fetch_max_sort_order() -> int:
    """返回当前 max(sort_order), 给新 badge 默认 sort_order = max+1."""
    conn = db._get_connection()
    cur = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM achievements")
    return int(cur.fetchone()[0])


def next_version(badge_id: str) -> int:
    """返回下一个 version 号 (= MAX+1, 最小 1).

    用途:
    - V1 新建 badge: 返回 1
    - PR-C 批量新建 (新派生 id): 返回 1
    - V1.x 换新图 (re-generate): 返回 MAX+1
    """
    conn = db._get_connection()
    cur = conn.execute(
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
    cur = conn.execute(
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
    cur = conn.execute(
        "SELECT achievement_id, url FROM achievement_badges WHERE is_current = 1"
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def badge_exists(badge_id: str) -> bool:
    """检查 achievement_id 是否在 achievements 表 (任何 category). True=存在."""
    return not check_id_unique(badge_id)


# ─── 写入 (走 badge_write_tx) ────────────────────────────────────

def insert_achievement_row(conn: sqlite3.Connection, ach: dict[str, Any]) -> None:
    """写 achievements 表 1 行.

    必填 key: id, name, type, category, stat_logic, description, display_format
    可选: threshold, unlocked_template, placeholder, sort_order, seasonal_type

    seasonal_type 必填 (CHECK 约束 default='monthly' 也行, 但 V1 显式传)
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
    }
    for k, v in defaults.items():
        ach.setdefault(k, v)

    conn.execute(
        """
        INSERT INTO achievements
          (id, name, type, category, stat_logic, description,
           display_format, threshold, unlocked_template, placeholder,
           sort_order, seasonal_type)
        VALUES
          (:id, :name, :type, :category, :stat_logic, :description,
           :display_format, :threshold, :unlocked_template, :placeholder,
           :sort_order, :seasonal_type)
        """,
        ach,
    )


def insert_achievement_stats_row(conn: sqlite3.Connection, badge_id: str) -> None:
    """写 achievement_stats 表 1 行 (仅 milestone).

    achieved='N' (初始未达成), raw_stats='{}' (空 JSON), computed_value=NULL.
    """
    conn.execute(
        """
        INSERT INTO achievement_stats
          (achievement_id, achieved, raw_stats, computed_value)
        VALUES (?, 'N', '{}', NULL)
        """,
        (badge_id,),
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
    conn.execute(
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
        conn.execute(
            "UPDATE achievement_badges SET is_current = 0 "
            "WHERE achievement_id = ? AND is_current = 1",
            (badge_id,),
        )
        insert_badge_row(conn, badge_id, new_url, new_version)
