"""
Sprint 26091201 feat/badge-3d-ccg B-1:
card_theme 解析 + 端到端 payload 测试.

覆盖:
  1. resolve_card_theme 优先级 + 边界 (4 个优先级 + 脏数据容错)
  2. TYPE_THEME_MAP 全覆盖 + 计数 (对应 prod 44 行分布)
  3. badge_db.ensure_card_theme_column 幂等 (SQLite)
  4. badge_draft.create_draft 接受合法 card_theme, 拒绝非法
  5. /api/badge/unclaimed payload 含 card_theme (end-to-end via TestClient)
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.kid_app.badge_theme import (
    DEFAULT_CARD_THEME,
    TYPE_THEME_MAP,
    VALID_CARD_THEMES,
    resolve_card_theme,
)


# ─── 1. resolve_card_theme 优先级 ───────────────────────────────────────
class TestResolvePriority:
    def test_explicit_valid_card_theme_wins_over_type(self):
        # 显式 bamboo 优先于 type='巅峰' (coral 兜底)
        assert resolve_card_theme(badge_type="巅峰", card_theme="bamboo") == "bamboo"

    def test_explicit_valid_card_theme_wins_over_category(self):
        # 显式 imperial 优先于 category='seasonal' (frost 兜底)
        assert resolve_card_theme(card_theme="imperial", category="seasonal") == "imperial"

    def test_type_used_when_card_theme_none(self):
        assert resolve_card_theme(badge_type="段位", card_theme=None) == "bamboo"

    def test_type_used_when_card_theme_empty(self):
        assert resolve_card_theme(badge_type="巅峰", card_theme="") == "coral"

    def test_category_seasonal_used_when_type_missing(self):
        assert resolve_card_theme(card_theme=None, category="seasonal") == "frost"

    def test_default_when_all_missing(self):
        assert resolve_card_theme() == DEFAULT_CARD_THEME
        assert resolve_card_theme(badge_type=None, card_theme=None, category=None) == "azure"


# ─── 1b. 脏数据容错 ────────────────────────────────────────────────────
class TestDirtyDataFallback:
    def test_card_theme_non_string_falls_back(self):
        # None / int / list 都应走兜底
        for bad in [123, [], {}, 0]:
            assert resolve_card_theme(badge_type="巅峰", card_theme=bad) == "coral"

    def test_card_theme_unknown_string_falls_back(self):
        # "rainbow" 不在 VALID_CARD_THEMES, 走 type 兜底
        assert resolve_card_theme(badge_type="段位", card_theme="rainbow") == "bamboo"

    def test_card_theme_with_whitespace_and_case(self):
        # "  Coral  " → "coral" (大小写空格容错)
        assert resolve_card_theme(card_theme="  Coral  ") == "coral"
        assert resolve_card_theme(card_theme="AZURE") == "azure"

    def test_type_non_string_falls_back(self):
        # type=None 走 category seasonal
        assert resolve_card_theme(badge_type=None, category="seasonal") == "frost"

    def test_type_unknown_chinese_falls_back_to_default(self):
        # type="未知分类" 不在 TYPE_THEME_MAP, 走 category/default
        assert resolve_card_theme(badge_type="未知分类", category="milestone") == DEFAULT_CARD_THEME

    def test_no_exception_on_any_dirty_input(self):
        """脏数据永不抛."""
        cases = [
            {"card_theme": None},
            {"card_theme": "", "badge_type": None},
            {"card_theme": "  ", "badge_type": ""},
            {"card_theme": 42},
            {"card_theme": ["bamboo"]},
            {"card_theme": "rainbow", "badge_type": 99},
            {"card_theme": {"slug": "bamboo"}},
        ]
        for kw in cases:
            r = resolve_card_theme(**kw)
            assert r in VALID_CARD_THEMES, f"非法返回 {r!r} for kw={kw}"


# ─── 2. TYPE_THEME_MAP 全覆盖 + 分布 ────────────────────────────────────
class TestTypeThemeMap:
    def test_map_contains_all_known_chinese_types(self):
        # production 实际 type 值
        expected = {"突破", "执着", "段位", "巅峰", "晋级", "神秘"}
        assert set(TYPE_THEME_MAP.keys()) == expected

    def test_map_values_all_in_valid_themes(self):
        for t, theme in TYPE_THEME_MAP.items():
            assert theme in VALID_CARD_THEMES, f"type={t} → theme={theme!r} 非法"

    def test_production_44_badge_distribution(self):
        """模拟 production 44 行 type 分布, 验证解析计数.

        实测 prod 解析 (按 (type, category) 真实分布):
          突破+milestone(18) + 突破+seasonal(5)   = 23 → azure
          段位+milestone(10) + 执着+milestone(4) = 14 → bamboo
          巅峰+milestone(2) + 巅峰+seasonal(2) + 晋级+milestone(2) = 6 → coral
          神秘+milestone(1)                       = 1 → imperial
          frost: 0 (所有 seasonal 行 type 命中 TYPE_THEME_MAP, 没真正落到 seasonal 兜底)
        """
        # 真实 (type, category, n) 分布, 跟 prod query 一致
        rows = [
            ("突破", "milestone", 18),
            ("突破", "seasonal", 5),
            ("段位", "milestone", 10),
            ("执着", "milestone", 4),
            ("巅峰", "milestone", 2),
            ("巅峰", "seasonal", 2),
            ("晋级", "milestone", 2),
            ("神秘", "milestone", 1),
        ]

        tally = {}
        for t, cat, n in rows:
            theme = resolve_card_theme(badge_type=t, category=cat)
            tally[theme] = tally.get(theme, 0) + n

        assert tally == {
            "azure": 23,
            "bamboo": 14,
            "coral": 6,
            "imperial": 1,
        }, f"分布变化需要重写断言. got {tally}"
        assert sum(tally.values()) == 44
        # 文档验收 4 要求"季节限定 → frost"语义保留: 单测单独验证
        assert resolve_card_theme(badge_type="非映射", category="seasonal") == "frost"
        assert resolve_card_theme(category="seasonal") == "frost"


# ─── 3. ensure_card_theme_column 幂等 (SQLite) ───────────────────────────
class TestEnsureColumnSQLite:
    def test_idempotent_sqlite(self, tmp_path: Path):
        db_path = tmp_path / "t.db"
        conn = sqlite3.connect(str(db_path))
        # 创表 (无 card_theme 列)
        conn.executescript("""
            CREATE TABLE achievements (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                stat_logic TEXT NOT NULL,
                description TEXT NOT NULL,
                display_format TEXT NOT NULL,
                threshold INTEGER,
                unlocked_template TEXT,
                placeholder TEXT,
                sort_order INTEGER DEFAULT 0,
                seasonal_type TEXT DEFAULT 'monthly',
                cond_text TEXT,
                unlock_strategy TEXT DEFAULT 'calc',
                achieved_at_override TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

        # 跑 2 次幂等
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "badge_db", "/Users/mt16/dev/dizical/src/kid_app/badge_db.py"
        )
        assert spec is not None
        badge_db = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(badge_db)  # type: ignore[union-attr]

        # 第 1 次
        conn1 = sqlite3.connect(str(db_path))
        before = {r[1] for r in conn1.execute("PRAGMA table_info(achievements)")}
        assert "card_theme" not in before, "测试前提: 列不存在"
        badge_db.ensure_card_theme_column(conn1)
        conn1.close()

        # 验证列已加
        conn_check = sqlite3.connect(str(db_path))
        after = {r[1] for r in conn_check.execute("PRAGMA table_info(achievements)")}
        assert "card_theme" in after
        conn_check.close()

        # 第 2 次, 幂等不抛
        conn2 = sqlite3.connect(str(db_path))
        badge_db.ensure_card_theme_column(conn2)
        # 列依然只有一个 (没重复加)
        after2 = {r[1] for r in conn2.execute("PRAGMA table_info(achievements)")}
        assert "card_theme" in after2
        assert sum(1 for x in after2 if x == "card_theme") == 1
        conn2.close()


# ─── 4. badge_draft.create_draft card_theme 校验 ─────────────────────────
class TestBadgeDraftCardTheme:
    def test_valid_card_theme_accepted(self):
        """合法 card_theme 被规整 (strip + lower) 并保留."""
        from src.kid_app.badge_draft import create_draft
        meta = {
            "id": "test_theme_1",
            "name": "测试徽章",
            "type": "突破",
            "category": "milestone",
            "placeholder": "p",
            "zh_story": "z",
            "cond_text": "c",
            "card_theme": "  Coral  ",  # 大小写空格都接受
        }
        draft = create_draft(meta)
        assert draft.meta["card_theme"] == "coral"  # 规整后

    def test_invalid_card_theme_rejected(self):
        """非法 card_theme 抛 ValueError (draft 阶段严, 不走兜底)."""
        from src.kid_app.badge_draft import create_draft
        meta = {
            "id": "test_theme_2",
            "name": "测试徽章",
            "type": "突破",
            "category": "milestone",
            "placeholder": "p",
            "zh_story": "z",
            "cond_text": "c",
            "card_theme": "rainbow",  # 非法
        }
        with pytest.raises(ValueError, match="card_theme"):
            create_draft(meta)

    def test_no_card_theme_field_works(self):
        """不传 card_theme 走默认 (resolve_card_theme 兜底链)."""
        from src.kid_app.badge_draft import create_draft
        meta = {
            "id": "test_theme_3",
            "name": "测试徽章",
            "type": "突破",
            "category": "milestone",
            "placeholder": "p",
            "zh_story": "z",
            "cond_text": "c",
        }
        draft = create_draft(meta)
        assert "card_theme" not in draft.meta or draft.meta.get("card_theme") is None

    def test_none_card_theme_works(self):
        """显式 None 等同不传."""
        from src.kid_app.badge_draft import create_draft
        meta = {
            "id": "test_theme_4",
            "name": "测试徽章",
            "type": "突破",
            "category": "milestone",
            "placeholder": "p",
            "zh_story": "z",
            "cond_text": "c",
            "card_theme": None,
        }
        draft = create_draft(meta)
        assert draft.meta["card_theme"] is None


# ─── 5. /api/badge/unclaimed payload 含 card_theme ──────────────────────
class TestUnclaimedPayload:
    """端到端: 起 TestClient, GET /api/badge/unclaimed, 验 payload."""

    @pytest.fixture()
    def client(self):
        """隔离 tmp DB, 创 achievements + stats + badges + audit 表."""
        from src import models
        import src.kid_app.app as app_module
        import src.kid_app.routes.badge_claim as claim_mod
        from src.database import Database
        import src.database as db_module

        fd, path = tempfile.mkstemp(suffix=".db")
        import os
        os.close(fd)
        os.environ["DATABASE_URL"] = ""

        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE achievements (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'milestone', stat_logic TEXT NOT NULL,
                description TEXT NOT NULL, display_format TEXT NOT NULL,
                threshold INTEGER, unlocked_template TEXT, placeholder TEXT,
                locked_template TEXT, sort_order INTEGER DEFAULT 0,
                seasonal_type TEXT DEFAULT 'monthly', cond_text TEXT,
                unlock_strategy TEXT DEFAULT 'calc', achieved_at_override TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                card_theme TEXT);
            CREATE TABLE achievement_stats (
                achievement_id TEXT PRIMARY KEY, achieved TEXT NOT NULL DEFAULT 'N',
                achieved_at DATETIME, claimed_at DATETIME,
                raw_stats TEXT NOT NULL DEFAULT '{}', computed_value INTEGER);
            CREATE TABLE achievement_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT, achievement_id TEXT NOT NULL,
                url TEXT NOT NULL, is_locked INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 1, is_current INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE practice_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT NOT NULL,
                method TEXT NOT NULL, practice_date DATE NOT NULL,
                detail TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        """)
        # seed 4 个跨 type 的 badge
        seeds = [
            ("badge_break", "突破徽章", "突破", "milestone", None),  # azure
            ("badge_dw", "段位徽章", "段位", "milestone", None),     # bamboo
            ("badge_seasonal", "赛季徽章", "巅峰", "seasonal", None), # coral (type) → frost (category) ... 实际 type 命中 coral
            ("badge_explicit", "自定义徽章", "突破", "milestone", "imperial"),  # imperial 显式
        ]
        for aid, name, typ, cat, ct in seeds:
            conn.executescript(f"""
                INSERT INTO achievements
                  (id, name, type, category, stat_logic, description, display_format,
                   sort_order, cond_text, card_theme)
                  VALUES
                  ('{aid}', '{name}', '{typ}', '{cat}', '{{}}', 'desc', 'icon', 1, 'cond',
                   {f"'{ct}'" if ct else 'NULL'});
                INSERT INTO achievement_stats
                  (achievement_id, achieved, achieved_at, claimed_at)
                  VALUES
                  ('{aid}', 'Y', '2026-09-10 10:00:00', NULL);
                INSERT INTO achievement_badges
                  (achievement_id, url, is_locked, version, is_current)
                  VALUES
                  ('{aid}', '/static/badges/{aid}.png', 0, 1, 1);
            """)
        conn.commit()
        conn.close()

        # monkeypatch 多层 DB 引用 (用 mock.patch as context manager)
        from unittest.mock import patch as _patch
        new_db = Database(db_path=path)
        from fastapi.testclient import TestClient
        p1 = _patch.object(models.settings, "db_path", path); p1.start()
        p2 = _patch.object(db_module, "db", new_db); p2.start()
        p3 = _patch.object(app_module, "db", new_db); p3.start()
        p4 = _patch.object(claim_mod, "DB_PATH", Path(path)); p4.start()
        yield TestClient(app_module.app)
        for p in (p1, p2, p3, p4):
            p.stop()

    def test_unclaimed_badge_has_card_theme_field(self, client):
        r = client.get("/api/badge/unclaimed")
        assert r.status_code == 200
        body = r.json()
        assert body["unclaimed_count"] == 4
        for b in body["badges"]:
            assert "card_theme" in b, f"badge {b['id']} 缺 card_theme"
            assert b["card_theme"] in VALID_CARD_THEMES

    def test_unclaimed_resolve_correct_mapping(self, client):
        r = client.get("/api/badge/unclaimed")
        body = r.json()
        theme_by_id = {b["id"]: b["card_theme"] for b in body["badges"]}
        assert theme_by_id["badge_break"] == "azure"     # 突破
        assert theme_by_id["badge_dw"] == "bamboo"        # 段位
        assert theme_by_id["badge_seasonal"] == "coral"   # 巅峰 (type 命中) — 不是 frost, 因为 type='巅峰' 在 TYPE_THEME_MAP
        assert theme_by_id["badge_explicit"] == "imperial"  # 显式 card_theme='imperial'


# ─── dad image#9/4: card_stars 后端字段 ─────────────────────────────


def test_resolve_card_stars_priority_and_clamp():
    from src.kid_app.badge_theme import DEFAULT_CARD_STARS, resolve_card_stars

    # 1. 显式 card_stars 优先 + 钳位 + 字符串容错
    assert resolve_card_stars(5) == 5
    assert resolve_card_stars("4") == 4
    assert resolve_card_stars(99) == 5
    assert resolve_card_stars(0) == 1
    # 2. 非法值落 type 兜底
    assert resolve_card_stars("脏", "巅峰") == 5
    assert resolve_card_stars(None, "突破") == 2
    assert resolve_card_stars(None, "段位") == 3
    # 3. seasonal 兜底
    assert resolve_card_stars(None, None, "seasonal") == 4
    # 4. 全空兜底
    assert resolve_card_stars(None, "不存在", "milestone") == DEFAULT_CARD_STARS
    assert resolve_card_stars(True) == DEFAULT_CARD_STARS  # bool 不算数


def test_resolve_card_stars_range_contract():
    from src.kid_app.badge_theme import STARS_MAX, STARS_MIN, TYPE_STARS_MAP

    for v in TYPE_STARS_MAP.values():
        assert STARS_MIN <= v <= STARS_MAX


# ─── sprint 26091301 B2: 主题目录扩到 8 套 (5 深 + 3 淡) ─────────────


class TestThemeCatalog:
    def test_valid_card_themes_is_8_dark_then_light(self):
        from src.kid_app.badge_theme import (
            DARK_CARD_THEMES,
            LIGHT_CARD_THEMES,
        )

        assert DARK_CARD_THEMES == ("azure", "bamboo", "coral", "imperial", "frost")
        assert LIGHT_CARD_THEMES == ("pearl", "mint", "sakura")
        assert VALID_CARD_THEMES == DARK_CARD_THEMES + LIGHT_CARD_THEMES
        assert len(VALID_CARD_THEMES) == 8
        # 深在前淡在后 (前端下拉顺序依赖)
        assert VALID_CARD_THEMES[:5] == DARK_CARD_THEMES
        assert set(DARK_CARD_THEMES).isdisjoint(LIGHT_CARD_THEMES)

    def test_theme_labels_cover_all_8(self):
        from src.kid_app.badge_theme import THEME_LABELS

        assert set(THEME_LABELS) == set(VALID_CARD_THEMES)
        assert THEME_LABELS["azure"] == "深海蓝"
        assert THEME_LABELS["bamboo"] == "竹林翠"
        assert THEME_LABELS["coral"] == "珊瑚红"
        assert THEME_LABELS["imperial"] == "皇紫金"
        assert THEME_LABELS["frost"] == "霜白"
        assert THEME_LABELS["pearl"] == "珠光象牙"
        assert THEME_LABELS["mint"] == "薄荷玉"
        assert THEME_LABELS["sakura"] == "樱雪"
        for v in THEME_LABELS.values():
            assert v and not any(ord(c) > 0x1F000 for c in v)  # 无 emoji

    @pytest.mark.parametrize("slug", ["pearl", "mint", "sakura"])
    def test_light_theme_resolvable(self, slug):
        """淡色 3 套 Python 侧必须认 (之前只在 CSS 里存在)."""
        assert resolve_card_theme(card_theme=slug) == slug
        assert resolve_card_theme(card_theme=slug.upper()) == slug
        assert resolve_card_theme(card_theme=f"  {slug}  ") == slug
        # 显式淡色压过 type 兜底
        assert resolve_card_theme(badge_type="巅峰", card_theme=slug) == slug

    def test_light_theme_accepted_by_draft_validation(self):
        from src.kid_app.badge_draft import create_draft

        for slug in ("pearl", "mint", "sakura"):
            draft = create_draft({
                "id": f"test_light_{slug}",
                "name": "淡色测试徽章",
                "type": "突破",
                "category": "milestone",
                "placeholder": "p",
                "zh_story": "z",
                "cond_text": "c",
                "card_theme": slug,
            })
            assert draft.meta["card_theme"] == slug

    def test_light_themes_not_used_as_type_fallback(self):
        from src.kid_app.badge_theme import LIGHT_CARD_THEMES

        assert set(TYPE_THEME_MAP.values()).isdisjoint(LIGHT_CARD_THEMES)

    def test_dirty_data_still_never_returns_light_mismatch(self):
        """脏值仍走兜底链 (扩表没改优先级)."""
        for bad in ["rainbow", "Pearl.", 7, []]:
            assert resolve_card_theme(badge_type="段位", card_theme=bad) == "bamboo"
