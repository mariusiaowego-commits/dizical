"""
全局 conftest: 给 worktree 测试用, 创表 achievements/achievement_stats/achievement_badges.

worktree 是新 git worktree, data/dizi.db 是新建的. production 跑的
migrate_achievements.py 会 DROP 旧表 (重置用), 不能直接调.
这里 session 级别创表, 给所有 test 共享.
"""
import sqlite3
from pathlib import Path

import pytest


def _worktree_db() -> Path:
    """worktree 数据库路径 (跟生产 src.models.settings 一致)."""
    from src.models import settings
    return Path(settings.db_path)


# 建表 SQL (跟 production 一致, 不带 seasonal_type 默认 'monthly' 是 PR #96 加的,
# cond_text 列是 feat/badge-cond-text 2026-06-15 加的)
_INIT_SQL = """
CREATE TABLE IF NOT EXISTS achievements (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    type              TEXT NOT NULL,
    category          TEXT NOT NULL DEFAULT 'milestone',
    stat_logic        TEXT NOT NULL,
    description       TEXT NOT NULL,
    display_format    TEXT NOT NULL,
    threshold         INTEGER,
    unlocked_template TEXT,
    placeholder       TEXT,
    locked_template   TEXT,
    sort_order        INTEGER DEFAULT 0,
    seasonal_type     TEXT DEFAULT 'monthly',
    cond_text         TEXT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS achievement_stats (
    achievement_id TEXT PRIMARY KEY,
    achieved       TEXT NOT NULL DEFAULT 'N',
    raw_stats      TEXT NOT NULL DEFAULT '{}',
    computed_value INTEGER
);
CREATE TABLE IF NOT EXISTS achievement_badges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    achievement_id  TEXT NOT NULL,
    url             TEXT NOT NULL,
    is_locked       INTEGER NOT NULL DEFAULT 0,
    version         INTEGER NOT NULL DEFAULT 1,
    is_current      INTEGER NOT NULL DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture(scope="session", autouse=True)
def _ensure_badge_tables():
    """Session 级: 创 achievements/stats/badges 表 (worktree 第一次跑)."""
    db_path = _worktree_db()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # 先 init Database 单例 (创 lessons/payments/settings 等基表)
    from src import database
    _ = database.db._get_connection()

    # 创 badge 表
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_INIT_SQL)
    conn.commit()
    conn.close()
    yield
    # 测试结束不清理 (worktree 是隔离环境, 下次跑会重置)
