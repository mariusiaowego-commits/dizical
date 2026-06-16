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
    unlock_strategy   TEXT DEFAULT 'calc',
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS achievement_stats (
    achievement_id TEXT PRIMARY KEY,
    achieved       TEXT NOT NULL DEFAULT 'N',
    achieved_at    DATETIME,
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
def _ensure_badge_tables(tmp_path_factory, monkeypatch_session):
    """Session 级: 创 achievements/stats/badges 表 (worktree 隔离环境).

    V2.4 (2026-06-16) 关键修法: 用 **tmp_path_factory 创临时 db** (session-scoped),
    **完全不碰 production db** (/Users/mt16/dev/dizical/data/dizi.db).

    V2.3 之前是 bug: 直接用 _worktree_db() = production db, session fixture 用
    DROP TABLE IF EXISTS 会清空 production 3 张 badge 表 (6-16 事故).
    现在测试用隔离的 tmp db, production 数据安全.

    实现: pytest 不支持 session-scope monkeypatch, 用临时改 src.models.settings.db_path
    (Database 单例初始化时读 settings.db_path).
    """
    tmp_db_dir = tmp_path_factory.mktemp("test_db")
    tmp_db_path = tmp_db_dir / "test_dizi.db"

    # 1. 临时改 settings.db_path → tmp db path (Database 单例下次初始化时读这个)
    from src import models
    monkeypatch_session.setattr(models.settings, "db_path", str(tmp_db_path))

    # 2. 触发 Database 单例初始化 (会创 lessons/payments/settings 等基表 + 用 tmp db)
    from src import database
    _ = database.db._get_connection()

    # 3. 创 badge 三表 (CREATE IF NOT EXISTS, 不 DROP)
    conn = sqlite3.connect(str(tmp_db_path))
    conn.executescript(_INIT_SQL)
    conn.commit()
    conn.close()
    yield
    # 测试结束: monkeypatch_session 自动还原 settings.db_path
    # Database 单例在 production 进程 (8765) 是独立的, 不受影响


@pytest.fixture(scope="session")
def monkeypatch_session():
    """Session-scope monkeypatch: 跟 pytest monkeypatch 一样 API, 但 session 范围."""
    import pytest as _pytest
    from pytest import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()
