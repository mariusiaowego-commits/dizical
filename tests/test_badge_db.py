"""tests/test_badge_db.py — 单元测试 badge_db 模块

测试策略:
- 每个 test 方法 setUp 一个 Database(temp_path), 跑 migrate_achievements 建表
- monkeypatch src.kid_app.badge_db.db 指向新实例 (单例绕过)
- tearDown 清临时目录
"""
import os
import shutil
import sqlite3
import tempfile
from unittest import TestCase, mock

import pytest

from src.database import Database
from src.kid_app import badge_db


# ─── 复用 migrate_achievements.py 的建表 SQL ────────────────────────
# 简化: 直接用 schema_migrations + 三张表的核心 DDL
# 完整 migrate 脚本有更多表, 这里只跑我们关心的
_TEST_SCHEMA = """
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
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
    , seasonal_type TEXT DEFAULT 'monthly' CHECK(seasonal_type IN ('daily','weekly','monthly','stage'))
    , cond_text TEXT
);
CREATE TABLE IF NOT EXISTS achievement_stats (
    achievement_id   TEXT PRIMARY KEY REFERENCES achievements(id),
    achieved         TEXT DEFAULT 'N',
    achieved_at      DATETIME,
    raw_stats        TEXT,
    computed_value   TEXT,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
    , cycle_type TEXT, cycle_key TEXT, cycle_achieved_at DATETIME
);
CREATE TABLE IF NOT EXISTS achievement_badges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    achievement_id  TEXT NOT NULL REFERENCES achievements(id),
    url             TEXT NOT NULL,
    is_locked       INTEGER DEFAULT 0,
    version         INTEGER DEFAULT 1,
    is_current      INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def _make_test_db() -> Database:
    """建一个临时 Database 实例, 跑表 schema. 返回 Database."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_badge.db")
    test_db = Database(db_path)
    # Database 的 _init_tables 不会建 achievements/achievement_stats/achievement_badges
    # (这些表由 src/migrate_achievements.py 单独建). 手动跑 schema:
    conn = test_db._get_connection()
    conn.executescript(_TEST_SCHEMA)
    conn.commit()
    _TEMP_DIRS[id(test_db)] = temp_dir  # 留给 cleanup
    return test_db


def _cleanup_test_db(test_db: Database) -> None:
    temp_dir = _TEMP_DIRS.pop(id(test_db), None)
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)


# 临时目录跟踪 (不能用 instance attribute, 类型系统不知道)
_TEMP_DIRS: dict[int, str] = {}


# ─── Fixtures (pytest 风格, 跟 unittest 混合用) ──────────────────

@pytest.fixture
def patched_db():
    """替换 badge_db.db 为临时 db, yield 后清理."""
    test_db = _make_test_db()
    with mock.patch.object(badge_db, "db", test_db):
        yield test_db
    _cleanup_test_db(test_db)


# ─── TestCheckIdUnique ─────────────────────────────────────────────

class TestCheckIdUnique:
    def test_id_not_in_db(self, patched_db):
        assert badge_db.check_id_unique("new_badge_xyz") is True

    def test_id_in_db(self, patched_db):
        conn = patched_db._get_connection()
        conn.execute(
            """INSERT INTO achievements
               (id, name, type, category, stat_logic, description, display_format)
               VALUES (?, 'X', '突破', 'milestone', 'logic', 'desc', 'days')""",
            ("existing_badge",),
        )
        conn.commit()
        assert badge_db.check_id_unique("existing_badge") is False


# ─── TestFetchMaxSortOrder ─────────────────────────────────────────

class TestFetchMaxSortOrder:
    def test_empty_db(self, patched_db):
        assert badge_db.fetch_max_sort_order() == 0

    def test_with_data(self, patched_db):
        conn = patched_db._get_connection()
        for i, s in enumerate([10, 20, 30, 25]):
            conn.execute(
                """INSERT INTO achievements
                   (id, name, type, category, stat_logic, description,
                    display_format, sort_order)
                   VALUES (?, ?, '突破', 'milestone', 'logic', 'desc',
                           'days', ?)""",
                (f"id_{i}", f"name_{i}", s),
            )
        conn.commit()
        assert badge_db.fetch_max_sort_order() == 30


# ─── TestNextVersion ───────────────────────────────────────────────

class TestNextVersion:
    def test_no_existing_version(self, patched_db):
        # 新 badge, 没有任何行
        assert badge_db.next_version("new_id") == 1

    def test_existing_v1(self, patched_db):
        conn = patched_db._get_connection()
        conn.execute(
            """INSERT INTO achievements
               (id, name, type, category, stat_logic, description, display_format)
               VALUES ('x1', 'X', '突破', 'milestone', 'l', 'd', 'days')"""
        )
        conn.execute(
            """INSERT INTO achievement_badges
               (achievement_id, url, is_locked, version, is_current)
               VALUES ('x1', '/static/badges/x1_v1.png', 0, 1, 1)"""
        )
        conn.commit()
        assert badge_db.next_version("x1") == 2

    def test_existing_v1_v2(self, patched_db):
        conn = patched_db._get_connection()
        conn.execute(
            """INSERT INTO achievements
               (id, name, type, category, stat_logic, description, display_format)
               VALUES ('x1', 'X', '突破', 'milestone', 'l', 'd', 'days')"""
        )
        for v in [1, 2]:
            conn.execute(
                """INSERT INTO achievement_badges
                   (achievement_id, url, is_locked, version, is_current)
                   VALUES ('x1', ?, 0, ?, ?)""",
                (f"/static/badges/x1_v{v}.png", v, 1 if v == 2 else 0),
            )
        conn.commit()
        assert badge_db.next_version("x1") == 3


# ─── TestFetchBadgeUrl ─────────────────────────────────────────────

class TestFetchBadgeUrl:
    def test_not_found(self, patched_db):
        assert badge_db.fetch_badge_url("nonexistent") is None

    def test_found_current(self, patched_db):
        conn = patched_db._get_connection()
        conn.execute(
            """INSERT INTO achievements
               (id, name, type, category, stat_logic, description, display_format)
               VALUES ('x1', 'X', '突破', 'milestone', 'l', 'd', 'days')"""
        )
        conn.execute(
            """INSERT INTO achievement_badges
               (achievement_id, url, is_locked, version, is_current)
               VALUES ('x1', '/static/badges/x1_v1.png', 0, 1, 1)"""
        )
        conn.commit()
        assert badge_db.fetch_badge_url("x1") == "/static/badges/x1_v1.png"

    def test_returns_current_only(self, patched_db):
        """多版本时只返回 is_current=1"""
        conn = patched_db._get_connection()
        conn.execute(
            """INSERT INTO achievements
               (id, name, type, category, stat_logic, description, display_format)
               VALUES ('x1', 'X', '突破', 'milestone', 'l', 'd', 'days')"""
        )
        conn.execute(
            """INSERT INTO achievement_badges
               (achievement_id, url, is_locked, version, is_current)
               VALUES ('x1', '/static/badges/x1_v1.png', 0, 1, 0)"""
        )
        conn.execute(
            """INSERT INTO achievement_badges
               (achievement_id, url, is_locked, version, is_current)
               VALUES ('x1', '/static/badges/x1_v2.png', 0, 2, 1)"""
        )
        conn.commit()
        assert badge_db.fetch_badge_url("x1") == "/static/badges/x1_v2.png"


# ─── TestListAllCurrentBadgeUrls ──────────────────────────────────

class TestListAllCurrentBadgeUrls:
    def test_empty(self, patched_db):
        assert badge_db.list_all_current_badge_urls() == {}

    def test_multiple_badges(self, patched_db):
        conn = patched_db._get_connection()
        for bid in ["a", "b", "c"]:
            conn.execute(
                """INSERT INTO achievements
                   (id, name, type, category, stat_logic, description, display_format)
                   VALUES (?, ?, '突破', 'milestone', 'l', 'd', 'days')""",
                (bid, bid),
            )
            conn.execute(
                """INSERT INTO achievement_badges
                   (achievement_id, url, is_locked, version, is_current)
                   VALUES (?, ?, 0, 1, 1)""",
                (bid, f"/static/badges/{bid}.png"),
            )
        conn.commit()
        result = badge_db.list_all_current_badge_urls()
        assert result == {
            "a": "/static/badges/a.png",
            "b": "/static/badges/b.png",
            "c": "/static/badges/c.png",
        }

    def test_excludes_non_current(self, patched_db):
        """is_current=0 的行不返回"""
        conn = patched_db._get_connection()
        conn.execute(
            """INSERT INTO achievements
               (id, name, type, category, stat_logic, description, display_format)
               VALUES ('a', 'A', '突破', 'milestone', 'l', 'd', 'days')"""
        )
        conn.execute(
            """INSERT INTO achievement_badges
               (achievement_id, url, is_locked, version, is_current)
               VALUES ('a', '/static/badges/a_old.png', 0, 1, 0)"""
        )
        conn.execute(
            """INSERT INTO achievement_badges
               (achievement_id, url, is_locked, version, is_current)
               VALUES ('a', '/static/badges/a_v2.png', 0, 2, 1)"""
        )
        conn.commit()
        result = badge_db.list_all_current_badge_urls()
        assert result == {"a": "/static/badges/a_v2.png"}


# ─── TestBadgeExists ──────────────────────────────────────────────

class TestBadgeExists:
    def test_not_exists(self, patched_db):
        assert badge_db.badge_exists("not_there") is False

    def test_exists(self, patched_db):
        conn = patched_db._get_connection()
        conn.execute(
            """INSERT INTO achievements
               (id, name, type, category, stat_logic, description, display_format)
               VALUES ('here', 'H', '突破', 'milestone', 'l', 'd', 'days')"""
        )
        conn.commit()
        assert badge_db.badge_exists("here") is True


# ─── TestInsertAchievementRow ──────────────────────────────────────

class TestInsertAchievementRow:
    def test_basic_insert(self, patched_db):
        conn = patched_db._get_connection()
        badge_db.insert_achievement_row(conn, {
            "id": "x1",
            "name": "X1",
            "type": "突破",
            "category": "milestone",
            "stat_logic": "logic1",
            "description": "desc1",
            "display_format": "days",
            "threshold": 7,
            "unlocked_template": "An emoji-adjacent 3D enamel pin of X.",
            "placeholder": "X",
            "seasonal_type": "monthly",
        })
        conn.commit()
        cur = conn.execute("SELECT * FROM achievements WHERE id='x1'")
        row = cur.fetchone()
        assert row is not None
        assert dict(row)["name"] == "X1"
        assert dict(row)["category"] == "milestone"
        assert dict(row)["threshold"] == 7
        assert dict(row)["sort_order"] == 1  # auto max+1

    def test_sort_order_explicit(self, patched_db):
        """显式传 sort_order, 不覆盖"""
        conn = patched_db._get_connection()
        badge_db.insert_achievement_row(conn, {
            "id": "x1",
            "name": "X1",
            "type": "突破",
            "category": "milestone",
            "stat_logic": "l",
            "description": "d",
            "display_format": "days",
            "sort_order": 999,  # explicit
        })
        conn.commit()
        cur = conn.execute("SELECT sort_order FROM achievements WHERE id='x1'")
        assert cur.fetchone()[0] == 999

    def test_seasonal_type_default(self, patched_db):
        """不传 seasonal_type → 默认 monthly (避免 CHECK 约束失败)"""
        conn = patched_db._get_connection()
        badge_db.insert_achievement_row(conn, {
            "id": "x1",
            "name": "X1",
            "type": "突破",
            "category": "seasonal",
            "stat_logic": "l",
            "description": "d",
            "display_format": "days",
        })
        conn.commit()
        cur = conn.execute("SELECT seasonal_type FROM achievements WHERE id='x1'")
        assert cur.fetchone()[0] == "monthly"


# ─── TestInsertAchievementStatsRow ─────────────────────────────────

class TestInsertAchievementStatsRow:
    def test_milestone_insert(self, patched_db):
        conn = patched_db._get_connection()
        # 先插 achievements (FK 依赖)
        badge_db.insert_achievement_row(conn, {
            "id": "x1", "name": "X", "type": "突破", "category": "milestone",
            "stat_logic": "l", "description": "d", "display_format": "days",
        })
        badge_db.insert_achievement_stats_row(conn, "x1")
        conn.commit()
        cur = conn.execute("SELECT * FROM achievement_stats WHERE achievement_id='x1'")
        row = dict(cur.fetchone())
        assert row["achieved"] == "N"
        assert row["raw_stats"] == "{}"
        assert row["computed_value"] is None
        assert row["achieved_at"] is None


# ─── TestInsertBadgeRow (V1 路径 A 核心测试) ──────────────────────

class TestInsertBadgeRow:
    def test_v1_unlocked_only(self, patched_db):
        """V1 路径 A: 只写 1 行 unlocked (is_locked=0)"""
        conn = patched_db._get_connection()
        badge_db.insert_achievement_row(conn, {
            "id": "x1", "name": "X", "type": "突破", "category": "milestone",
            "stat_logic": "l", "description": "d", "display_format": "days",
        })
        badge_db.insert_badge_row(conn, "x1", "/static/badges/x1_v1.png", 1)
        conn.commit()
        # 只应该 1 行
        cur = conn.execute(
            "SELECT COUNT(*) FROM achievement_badges WHERE achievement_id='x1'"
        )
        assert cur.fetchone()[0] == 1
        # 该行 is_locked=0, is_current=1
        cur = conn.execute(
            "SELECT is_locked, is_current FROM achievement_badges WHERE achievement_id='x1'"
        )
        row = cur.fetchone()
        assert row[0] == 0
        assert row[1] == 1

    def test_version_n(self, patched_db):
        """version 字段按调用方传值"""
        conn = patched_db._get_connection()
        badge_db.insert_achievement_row(conn, {
            "id": "x1", "name": "X", "type": "突破", "category": "milestone",
            "stat_logic": "l", "description": "d", "display_format": "days",
        })
        badge_db.insert_badge_row(conn, "x1", "/static/badges/x1_v3.png", 3)
        conn.commit()
        cur = conn.execute(
            "SELECT version FROM achievement_badges WHERE achievement_id='x1'"
        )
        assert cur.fetchone()[0] == 3


# ─── TestUpdateBadgeCurrent (换新图流程) ──────────────────────────

class TestUpdateBadgeCurrent:
    def test_replace_old_with_new(self, patched_db):
        """UPDATE 旧行 is_current=0, INSERT 新行 is_current=1"""
        conn = patched_db._get_connection()
        # 初始 v1
        badge_db.insert_achievement_row(conn, {
            "id": "x1", "name": "X", "type": "突破", "category": "milestone",
            "stat_logic": "l", "description": "d", "display_format": "days",
        })
        badge_db.insert_badge_row(conn, "x1", "/static/badges/x1_v1.png", 1)
        conn.commit()

        # 换 v2
        badge_db.update_badge_current("x1", "/static/badges/x1_v2.png", 2)

        # 验证: v1 is_current=0, v2 is_current=1
        rows = conn.execute(
            "SELECT version, is_current FROM achievement_badges "
            "WHERE achievement_id='x1' ORDER BY version"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][0] == 1
        assert rows[0][1] == 0
        assert rows[1][0] == 2
        assert rows[1][1] == 1

    def test_atomic(self, patched_db):
        """update 失败 → rollback (旧行不变)"""
        conn = patched_db._get_connection()
        badge_db.insert_achievement_row(conn, {
            "id": "x1", "name": "X", "type": "突破", "category": "milestone",
            "stat_logic": "l", "description": "d", "display_format": "days",
        })
        badge_db.insert_badge_row(conn, "x1", "/static/badges/x1_v1.png", 1)
        conn.commit()

        # 模拟 update 失败: mock 替换 conn 让 INSERT 抛异常
        original = badge_db.insert_badge_row

        def fail_on_insert(c, badge_id, url, version):
            raise RuntimeError("simulated insert failure")

        with mock.patch.object(badge_db, "insert_badge_row", side_effect=fail_on_insert):
            with pytest.raises(RuntimeError, match="simulated"):
                badge_db.update_badge_current("x1", "/static/badges/x1_v2.png", 2)

        # rollback 应该让 v1 仍是 is_current=1
        cur = conn.execute(
            "SELECT is_current FROM achievement_badges WHERE achievement_id='x1'"
        )
        assert cur.fetchone()[0] == 1


# ─── TestBadgeWriteTx (事务上下文管理器) ──────────────────────────

class TestBadgeWriteTx:
    def test_commit_on_success(self, patched_db):
        conn = patched_db._get_connection()
        with badge_db.badge_write_tx() as c:
            c.execute(
                """INSERT INTO achievements
                   (id, name, type, category, stat_logic, description, display_format)
                   VALUES ('x1', 'X', '突破', 'milestone', 'l', 'd', 'days')"""
            )
        # 提交后应可见
        cur = conn.execute("SELECT id FROM achievements WHERE id='x1'")
        assert cur.fetchone() is not None

    def test_rollback_on_exception(self, patched_db):
        conn = patched_db._get_connection()
        with pytest.raises(RuntimeError, match="boom"):
            with badge_db.badge_write_tx() as c:
                c.execute(
                    """INSERT INTO achievements
                       (id, name, type, category, stat_logic, description, display_format)
                       VALUES ('x1', 'X', '突破', 'milestone', 'l', 'd', 'days')"""
                )
                raise RuntimeError("boom")
        # rollback 后应不可见
        cur = conn.execute("SELECT id FROM achievements WHERE id='x1'")
        assert cur.fetchone() is None
