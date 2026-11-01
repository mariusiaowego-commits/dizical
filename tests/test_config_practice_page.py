"""练习页配置：计时蒙版颜色读写。"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

DEFAULT_COLOR = "rgba(44, 62, 80, 0.35)"
DEFAULT_OPACITY = "0.35"
MASK_KEYS = ("practice_mask_color", "practice_mask_opacity")


@pytest.fixture()
def client():
    """临时 SQLite，不碰 data/dizi.db。"""
    from src.database import Database
    from src.kid_app.app import app as fastapi_app
    from src import models
    import src.database as db_module
    import src.kid_app.app as app_module

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = ""
    new_db = Database(db_path=path)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(models.settings, "db_path", path)
    monkeypatch.setattr(db_module, "db", new_db)
    monkeypatch.setattr(app_module, "db", new_db)

    with TestClient(fastapi_app) as test_client:
        yield test_client, new_db

    monkeypatch.undo()
    try:
        os.unlink(path)
    except Exception:
        pass


def _mask_rows(db):
    with db._get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM settings WHERE key IN (?, ?) ORDER BY key",
            MASK_KEYS,
        ).fetchall()
    return [(row["key"], row["value"]) for row in rows]


def _all_keys(db):
    with db._get_connection() as conn:
        rows = conn.execute("SELECT key FROM settings ORDER BY key").fetchall()
    return [row["key"] for row in rows]


def test_get_default_when_unset(client):
    test_client, db = client
    response = test_client.get("/config/api/practice-page/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["mask_color"] == DEFAULT_COLOR
    assert body["mask_opacity"] == DEFAULT_OPACITY
    assert _mask_rows(db) == []


def test_post_roundtrip_and_only_expected_keys(client):
    test_client, db = client
    response = test_client.post(
        "/config/api/practice-page/settings",
        json={"mask_color": "#2C3E50", "mask_opacity": 0.5},
    )
    assert response.status_code == 200
    saved = response.json()
    assert saved == {
        "ok": True,
        "mask_color": "rgba(44, 62, 80, 0.5)",
        "mask_opacity": "0.5",
    }

    again = test_client.get("/config/api/practice-page/settings")
    assert again.status_code == 200
    assert again.json()["mask_color"] == "rgba(44, 62, 80, 0.5)"
    assert again.json()["mask_opacity"] == "0.5"
    assert _all_keys(db) == ["practice_mask_color", "practice_mask_opacity"]

    rgb = test_client.post(
        "/config/api/practice-page/settings",
        json={"mask_color": "rgb(10, 20, 30)", "mask_opacity": "0"},
    )
    assert rgb.status_code == 200
    assert rgb.json()["mask_color"] == "rgba(10, 20, 30, 0)"
    assert rgb.json()["mask_opacity"] == "0"

    composed = test_client.post(
        "/config/api/practice-page/settings",
        json={"mask_color": "rgba(1, 2, 3, 0.9)", "mask_opacity": 0.35},
    )
    assert composed.status_code == 200
    assert composed.json()["mask_color"] == "rgba(1, 2, 3, 0.35)"
    assert _all_keys(db) == ["practice_mask_color", "practice_mask_opacity"]


def test_invalid_color_keeps_stored_value(client):
    test_client, db = client
    first = test_client.post(
        "/config/api/practice-page/settings",
        json={"mask_color": "#112233", "mask_opacity": 0.2},
    )
    assert first.status_code == 200

    rejected = test_client.post(
        "/config/api/practice-page/settings",
        json={"mask_color": "blue", "mask_opacity": 0.8},
    )
    assert rejected.status_code == 400
    assert "颜色" in rejected.json()["error"]

    current = test_client.get("/config/api/practice-page/settings").json()
    assert current["mask_color"] == "rgba(17, 34, 51, 0.2)"
    assert current["mask_opacity"] == "0.2"
    assert _all_keys(db) == ["practice_mask_color", "practice_mask_opacity"]


def test_invalid_opacity_keeps_stored_value(client):
    test_client, db = client
    test_client.post(
        "/config/api/practice-page/settings",
        json={"mask_color": "rgba(44, 62, 80, 0.35)", "mask_opacity": "0.35"},
    )

    rejected = test_client.post(
        "/config/api/practice-page/settings",
        json={"mask_color": "#2C3E50", "mask_opacity": 1.5},
    )
    assert rejected.status_code == 400
    assert "透明" in rejected.json()["error"]

    missing = test_client.post(
        "/config/api/practice-page/settings",
        json={"mask_color": "#2C3E50"},
    )
    assert missing.status_code == 400

    current = test_client.get("/config/api/practice-page/settings").json()
    assert current["mask_color"] == DEFAULT_COLOR
    assert current["mask_opacity"] == DEFAULT_OPACITY
    assert _mask_rows(db) == [
        ("practice_mask_color", DEFAULT_COLOR),
        ("practice_mask_opacity", DEFAULT_OPACITY),
    ]
