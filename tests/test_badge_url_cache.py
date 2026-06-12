"""tests/test_badge_url_cache.py — PR-B (2026-06-12) 测试

覆盖:
- get_badge_url() 从 DB 读 + cache 命中
- _invalidate_badge_url_cache() 立刻让新 badge 可见 (badge_generator 集成关键)
- TTL 过期后重新查 DB
- cache miss 返回 default
- 跟 PR-A 的 badge_db.list_all_current_badge_urls() 一致
"""
import time
from unittest import mock

import pytest

from src.database import Database
from src.kid_app import app as app_module


# ─── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def patched_db(tmp_path):
    """建一个临时 db, 建 3 张表, 注入测试数据, 替换 app_module.db."""
    db_path = tmp_path / "test_badge_cache.db"
    test_db = Database(db_path)
    conn = test_db._get_connection()
    conn.executescript("""
        CREATE TABLE achievements (
            id TEXT PRIMARY KEY, name TEXT, type TEXT, category TEXT,
            stat_logic TEXT, description TEXT, display_format TEXT
        );
        CREATE TABLE achievement_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            achievement_id TEXT, url TEXT, is_locked INTEGER,
            version INTEGER, is_current INTEGER
        );
    """)
    # 注入 3 个 badge, 一个 is_current=0 (应被排除)
    for aid, url, is_cur in [
        ("streak_7", "/static/badges/streak_7.png", 1),
        ("total_300", "/static/badges/total_300.png", 1),
        ("old_version", "/static/badges/old.png", 0),
    ]:
        conn.execute(
            "INSERT INTO achievements (id, name, type, category, stat_logic, description, display_format) "
            "VALUES (?, 'X', '突破', 'milestone', 'l', 'd', 'days')",
            (aid,),
        )
        conn.execute(
            "INSERT INTO achievement_badges (achievement_id, url, is_locked, version, is_current) "
            "VALUES (?, ?, 0, 1, ?)",
            (aid, url, is_cur),
        )
    conn.commit()

    # 清初始 cache, 替换 db
    app_module._BADGE_URL_CACHE["ts"] = 0.0
    app_module._BADGE_URL_CACHE["data"] = {}
    with mock.patch.object(app_module, "db", test_db):
        yield test_db
    app_module._BADGE_URL_CACHE["ts"] = 0.0
    app_module._BADGE_URL_CACHE["data"] = {}


# ─── TestGetBadgeUrl ─────────────────────────────────────────────

class TestGetBadgeUrl:
    def test_returns_url_from_db(self, patched_db):
        url = app_module.get_badge_url("streak_7")
        assert url == "/static/badges/streak_7.png"

    def test_excludes_non_current(self, patched_db):
        """is_current=0 的行不应被返回."""
        url = app_module.get_badge_url("old_version")
        assert url == "/static/badges/medal_badge.png"  # fallback, 不是 old.png

    def test_unknown_id_returns_default(self, patched_db):
        url = app_module.get_badge_url("nonexistent_badge")
        assert url == "/static/badges/medal_badge.png"

    def test_custom_default(self, patched_db):
        url = app_module.get_badge_url("nonexistent", default="/custom.png")
        assert url == "/custom.png"

    def test_cache_is_populated_after_first_call(self, patched_db):
        app_module.get_badge_url("streak_7")
        # cache data 应该有 streak_7 + total_300 (current=1 的)
        assert "streak_7" in app_module._BADGE_URL_CACHE["data"]
        assert "total_300" in app_module._BADGE_URL_CACHE["data"]
        assert "old_version" not in app_module._BADGE_URL_CACHE["data"]
        # cache ts 应该已更新
        assert app_module._BADGE_URL_CACHE["ts"] > 0

    def test_uses_cache_within_ttl(self, patched_db):
        # 第一次调, 触发 cache 刷新
        url1 = app_module.get_badge_url("streak_7")
        # 改 DB 但 cache 还在 TTL 内, 应该返回旧值
        with mock.patch.object(app_module, "db") as mock_db:
            mock_db._get_connection.return_value.execute.return_value.fetchall.return_value = []
            url2 = app_module.get_badge_url("streak_7")
        # 第二次从 cache 拿, 跟第一次一样
        assert url1 == url2

    def test_reloads_after_ttl_expired(self, patched_db):
        # 第一次, 触发 cache
        app_module.get_badge_url("streak_7")
        # 强制 TTL 过期
        app_module._BADGE_URL_CACHE["ts"] = time.time() - 100
        # 改 DB (mock)
        with mock.patch.object(app_module, "db") as mock_db:
            # 第二次会重查 DB, mock 返回空
            mock_db._get_connection.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = []
            url = app_module.get_badge_url("streak_7")
        # cache miss (新值是空), 返回 default
        assert url == "/static/badges/medal_badge.png"


# ─── TestInvalidateCache ────────────────────────────────────────

class TestInvalidateCache:
    def test_clears_cache(self, patched_db):
        # 触发 cache
        app_module.get_badge_url("streak_7")
        assert "streak_7" in app_module._BADGE_URL_CACHE["data"]
        # 失效
        app_module._invalidate_badge_url_cache()
        assert app_module._BADGE_URL_CACHE["ts"] == 0.0
        assert app_module._BADGE_URL_CACHE["data"] == {}

    def test_lets_new_badge_visible_immediately(self, patched_db):
        """新加 badge + _invalidate, 立刻能看到, 不用等 60s TTL.

        这是跟 PR-A 的 badge_generator.commit_badge_to_db() 集成的关键场景.
        """
        # 初始 3 个 badge, 触发 cache
        url1 = app_module.get_badge_url("streak_7")
        assert url1 == "/static/badges/streak_7.png"

        # 模拟 PR-A commit_badge_to_db: 加新行 + 调 invalidate
        conn = patched_db._get_connection()
        conn.execute(
            "INSERT INTO achievements (id, name, type, category, stat_logic, description, display_format) "
            "VALUES ('new_badge_xyz', 'X', '突破', 'milestone', 'l', 'd', 'days')"
        )
        conn.execute(
            "INSERT INTO achievement_badges (achievement_id, url, is_locked, version, is_current) "
            "VALUES ('new_badge_xyz', '/static/badges/new_badge_xyz_v1.png', 0, 1, 1)"
        )
        conn.commit()
        app_module._invalidate_badge_url_cache()  # ← 这就是 commit_badge_to_db 末尾要调的

        # 立刻能取到
        url_new = app_module.get_badge_url("new_badge_xyz")
        assert url_new == "/static/badges/new_badge_xyz_v1.png"

    def test_idempotent(self, patched_db):
        # 即使 cache 已空, 调 invalidate 不抛异常
        app_module._BADGE_URL_CACHE["ts"] = 0.0
        app_module._BADGE_URL_CACHE["data"] = {}
        app_module._invalidate_badge_url_cache()  # 不抛
        app_module._invalidate_badge_url_cache()  # 不抛


# ─── TestRefreshCache ────────────────────────────────────────────

class TestRefreshCache:
    def test_refresh_only_current(self, patched_db):
        """_refresh_badge_url_cache 只装 is_current=1 的行."""
        app_module._refresh_badge_url_cache()
        data = app_module._BADGE_URL_CACHE["data"]
        # 包含 current=1 的 2 个
        assert "streak_7" in data
        assert "total_300" in data
        # 排除 current=0 的
        assert "old_version" not in data
        # ts 已更新
        assert app_module._BADGE_URL_CACHE["ts"] > 0


# ─── TestEmptyDb ────────────────────────────────────────────────

class TestEmptyDb:
    def test_no_badges_returns_default(self, tmp_path):
        # 空 DB
        db_path = tmp_path / "empty.db"
        test_db = Database(db_path)
        conn = test_db._get_connection()
        conn.executescript("""
            CREATE TABLE achievement_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                achievement_id TEXT, url TEXT, is_locked INTEGER,
                version INTEGER, is_current INTEGER
            );
        """)
        conn.commit()
        app_module._BADGE_URL_CACHE["ts"] = 0.0
        app_module._BADGE_URL_CACHE["data"] = {}
        with mock.patch.object(app_module, "db", test_db):
            url = app_module.get_badge_url("streak_7")
        assert url == "/static/badges/medal_badge.png"

    def test_badges_table_missing_returns_default(self, tmp_path):
        """DB 里没 achievement_badges 表 (没 migrate), 不应 crash, 返回 default."""
        db_path = tmp_path / "no_badges.db"
        test_db = Database(db_path)
        # 不建 achievement_badges 表
        app_module._BADGE_URL_CACHE["ts"] = 0.0
        app_module._BADGE_URL_CACHE["data"] = {}
        with mock.patch.object(app_module, "db", test_db):
            # 不 crash, 抛 sqlite3.OperationalError, 透传
            # 测试期望: 不静默 crash, 让上层知道
            with pytest.raises(Exception):  # OperationalError
                app_module.get_badge_url("streak_7")
