"""
Sprint 26091301 B2 — 卡片外观设计期入口.

覆盖 config 内部两个端点:
  GET  /config/api/badge/card-appearance  — 全量列表 + theme_source 正确性
  POST /config/api/badge/card-appearance  — 单卡改主题/星级, 清列回落, 校验

走 conftest 的 session 级 tmp db (settings.db_path 已被指向临时库),
自己 seed 带前缀 appr_test_ 的行并在测试后清掉, 不碰 production dizi.db。
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from src.kid_app.badge_theme import (
    DARK_CARD_THEMES,
    LIGHT_CARD_THEMES,
    THEME_LABELS,
    VALID_CARD_THEMES,
)

GET_URL = "/config/api/badge/card-appearance"
POST_URL = "/config/api/badge/card-appearance"
PREFIX = "appr_test_"

# (id, name, type, category, card_theme, card_stars)
SEEDS = [
    (f"{PREFIX}type", "类型兜底卡", "突破", "milestone", None, None),
    (f"{PREFIX}db", "显式淡色卡", "突破", "milestone", "sakura", None),
    (f"{PREFIX}fallback", "季节兜底卡", "未知分类", "seasonal", None, None),
    (f"{PREFIX}stars", "显式星级卡", "段位", "milestone", None, 4),
]


def _db_path() -> Path:
    from src.models import settings
    return Path(settings.db_path)


def _seed() -> None:
    """幂等 seed 4 行 (先删后插)."""
    conn = sqlite3.connect(str(_db_path()))
    try:
        conn.execute(f"DELETE FROM achievements WHERE id LIKE '{PREFIX}%'")
        for i, (aid, name, typ, cat, theme, stars) in enumerate(SEEDS):
            conn.execute(
                "INSERT INTO achievements "
                "(id, name, type, category, stat_logic, description, display_format, "
                " sort_order, card_theme, card_stars) "
                "VALUES (?, ?, ?, ?, '{}', 'desc', 'icon', ?, ?, ?)",
                (aid, name, typ, cat, 100 + i, theme, stars),
            )
        conn.commit()
    finally:
        conn.close()


def _cleanup() -> None:
    conn = sqlite3.connect(str(_db_path()))
    try:
        conn.execute(f"DELETE FROM achievements WHERE id LIKE '{PREFIX}%'")
        conn.commit()
    finally:
        conn.close()


def _row(client, badge_id: str) -> dict:
    body = client.get(GET_URL).json()
    by_id = {r["id"]: r for r in body["data"]}
    assert badge_id in by_id, f"{badge_id} 不在列表: {sorted(by_id)[:5]}"
    return by_id[badge_id]


@pytest.fixture(autouse=True)
def _force_sqlite_backend(monkeypatch):
    """本模块必须走 SQLite 分支 (双后端适配层)."""
    monkeypatch.setenv("DATABASE_URL", "")


@pytest.fixture()
def client():
    _seed()
    from fastapi.testclient import TestClient
    import src.kid_app.app as app_module
    yield TestClient(app_module.app)
    _cleanup()


# ─── GET 列表 ────────────────────────────────────────────────────────

class TestCardAppearanceList:
    def test_ok_and_row_shape(self, client):
        r = client.get(GET_URL)
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["count"] == len(body["data"])
        assert body["count"] >= len(SEEDS)

        required = {
            "id", "name", "type", "category", "sort_order",
            "card_theme", "card_stars", "resolved_theme", "theme_source",
        }
        for row in body["data"]:
            assert required <= set(row), f"缺字段: {required - set(row)}"
            assert row["resolved_theme"] in VALID_CARD_THEMES
            assert row["theme_source"] in ("db", "type", "fallback")

    def test_theme_catalog_lists_8_themes_dark_first(self, client):
        themes = client.get(GET_URL).json()["themes"]
        assert themes["dark"] == list(DARK_CARD_THEMES)
        assert themes["light"] == list(LIGHT_CARD_THEMES)
        assert len(themes["dark"]) == 5 and len(themes["light"]) == 3
        assert themes["labels"] == THEME_LABELS

    def test_theme_source_type_when_column_null(self, client):
        row = _row(client, f"{PREFIX}type")
        assert row["card_theme"] is None and row["card_stars"] is None
        assert row["theme_source"] == "type"
        assert row["resolved_theme"] == "azure"      # type=突破 → azure
        assert row["resolved_stars"] == 2            # type=突破 → 2★

    def test_theme_source_db_wins_over_type(self, client):
        row = _row(client, f"{PREFIX}db")
        assert row["card_theme"] == "sakura"
        assert row["theme_source"] == "db"
        assert row["resolved_theme"] == "sakura"     # 淡色被 Python 侧认了

    def test_theme_source_fallback_for_unmapped_seasonal(self, client):
        row = _row(client, f"{PREFIX}fallback")
        assert row["theme_source"] == "fallback"
        assert row["resolved_theme"] == "frost"      # category=seasonal → frost

    def test_raw_stars_passthrough(self, client):
        row = _row(client, f"{PREFIX}stars")
        assert row["card_stars"] == 4
        assert row["resolved_stars"] == 4
        assert row["card_theme"] is None
        assert row["resolved_theme"] == "bamboo"     # type=段位


# ─── POST 改主题 ─────────────────────────────────────────────────────

class TestCardAppearanceThemeWrite:
    @pytest.mark.parametrize("theme", list(VALID_CARD_THEMES))
    def test_each_of_8_themes_accepted(self, client, theme):
        r = client.post(POST_URL, json={"id": f"{PREFIX}type", "card_theme": theme})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["card_theme"] == theme
        assert data["resolved_theme"] == theme
        assert data["theme_source"] == "db"
        # 落库持久: 重读 GET 仍是该主题
        assert _row(client, f"{PREFIX}type")["resolved_theme"] == theme

    def test_light_theme_resolves(self, client):
        r = client.post(POST_URL, json={"id": f"{PREFIX}type", "card_theme": "mint"})
        assert r.status_code == 200
        assert r.json()["data"]["resolved_theme"] == "mint"

    def test_upper_case_and_space_normalized(self, client):
        r = client.post(POST_URL, json={"id": f"{PREFIX}type", "card_theme": "  Pearl  "})
        assert r.status_code == 200
        assert r.json()["data"]["card_theme"] == "pearl"

    def test_change_theme_updates_resolve_order(self, client):
        # 改前: type=突破 → azure (type 兜底)
        assert _row(client, f"{PREFIX}type")["resolved_theme"] == "azure"
        # 改后: 显式 imperial 压过 type
        client.post(POST_URL, json={"id": f"{PREFIX}type", "card_theme": "imperial"})
        assert _row(client, f"{PREFIX}type")["resolved_theme"] == "imperial"

    @pytest.mark.parametrize("clear", [None, ""])
    def test_clear_theme_falls_back_to_type(self, client, clear):
        client.post(POST_URL, json={"id": f"{PREFIX}db", "card_theme": "sakura"})
        assert _row(client, f"{PREFIX}db")["theme_source"] == "db"

        r = client.post(POST_URL, json={"id": f"{PREFIX}db", "card_theme": clear})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["card_theme"] is None
        assert data["theme_source"] == "type"        # 回落 type 兜底
        assert data["resolved_theme"] == "azure"     # type=突破
        assert _row(client, f"{PREFIX}db")["theme_source"] == "type"

    @pytest.mark.parametrize("bad", ["rainbow", "AZUREE", "深海蓝", "azure ", "pearl."])
    def test_invalid_theme_400_with_valid_list(self, client, bad):
        r = client.post(POST_URL, json={"id": f"{PREFIX}type", "card_theme": bad})
        # "azure " 带尾空格 → 规整后合法, 200; 其余 400
        if bad.strip().lower() in VALID_CARD_THEMES:
            assert r.status_code == 200, r.text
            return
        assert r.status_code == 400, r.text
        body = r.json()
        assert body["ok"] is False
        assert body["valid_themes"] == list(VALID_CARD_THEMES)

    def test_invalid_theme_does_not_mutate_row(self, client):
        before = _row(client, f"{PREFIX}db")
        client.post(POST_URL, json={"id": f"{PREFIX}db", "card_theme": "rainbow"})
        assert _row(client, f"{PREFIX}db") == before


# ─── POST 改星级 ─────────────────────────────────────────────────────

class TestCardAppearanceStarsWrite:
    @pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
    def test_stars_1_to_5_ok(self, client, n):
        r = client.post(POST_URL, json={"id": f"{PREFIX}type", "card_stars": n})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["card_stars"] == n
        assert data["resolved_stars"] == n
        assert _row(client, f"{PREFIX}type")["card_stars"] == n

    @pytest.mark.parametrize("bad", [0, 6, -1, 99])
    def test_stars_out_of_range_400(self, client, bad):
        r = client.post(POST_URL, json={"id": f"{PREFIX}type", "card_stars": bad})
        assert r.status_code == 400, r.text
        assert r.json()["valid_range"] == [1, 5]

    @pytest.mark.parametrize("bad", ["abc", 3.5, []])
    def test_stars_non_integer_400(self, client, bad):
        r = client.post(POST_URL, json={"id": f"{PREFIX}type", "card_stars": bad})
        assert r.status_code == 400, r.text

    @pytest.mark.parametrize("clear", [None, ""])
    def test_stars_null_clears_and_falls_back(self, client, clear):
        client.post(POST_URL, json={"id": f"{PREFIX}stars", "card_stars": 5})
        r = client.post(POST_URL, json={"id": f"{PREFIX}stars", "card_stars": clear})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["card_stars"] is None
        assert data["resolved_stars"] == 3           # type=段位 → 3★


# ─── POST 边界 ───────────────────────────────────────────────────────

class TestCardAppearanceBounds:
    def test_unknown_id_404(self, client):
        r = client.post(POST_URL, json={"id": f"{PREFIX}missing", "card_theme": "azure"})
        assert r.status_code == 404, r.text
        assert r.json()["ok"] is False

    def test_omitted_fields_do_not_touch_columns(self, client):
        before = _row(client, f"{PREFIX}db")
        r = client.post(POST_URL, json={"id": f"{PREFIX}db"})
        assert r.status_code == 200, r.text
        assert r.json()["updated"] == []
        assert r.json()["data"] == before

    def test_partial_update_stars_keeps_theme(self, client):
        client.post(POST_URL, json={"id": f"{PREFIX}db", "card_theme": "mint"})
        r = client.post(POST_URL, json={"id": f"{PREFIX}db", "card_stars": 5})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["card_theme"] == "mint"
        assert data["card_stars"] == 5

    def test_updated_field_names_reported(self, client):
        r = client.post(POST_URL, json={
            "id": f"{PREFIX}type", "card_theme": "frost", "card_stars": 2,
        })
        assert r.status_code == 200, r.text
        assert r.json()["updated"] == ["card_stars", "card_theme"]

    def test_string_stars_accepted(self, client):
        r = client.post(POST_URL, json={"id": f"{PREFIX}type", "card_stars": "4"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["card_stars"] == 4
