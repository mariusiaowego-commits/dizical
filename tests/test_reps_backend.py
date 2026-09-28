"""practice_sessions.reps 后端：写入、空值、越界、修改、删除镜像、迁移、读出。"""
import datetime as dt
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import src.database as db_module
from src.kid_app.app import _build_stage_detail_payload, app
from src.kid_app.schemas import PracticeLogRequest
from src.migrate_add_session_reps import migrate_sqlite

# 模块导入时拿到 conftest 会改路径的那份库。后面的测试可能把 app.db 换成只读临时文件。
_SESSION_DB = db_module.db


@pytest.fixture(autouse=True)
def _pin_session_db():
    import src.kid_app.app as app_module
    import src.kid_app.routes.config as config_module
    prev = (app_module.db, config_module.db, db_module.db)
    app_module.db = _SESSION_DB
    config_module.db = _SESSION_DB
    db_module.db = _SESSION_DB
    yield
    app_module.db, config_module.db, db_module.db = prev


def _db():
    return _SESSION_DB


@pytest.fixture
def item():
    conn = _db()._get_connection()
    conn.execute("DELETE FROM practice_items WHERE name = 'reps_subject'")
    conn.commit()
    conn.execute("INSERT INTO practice_items (name, is_active) VALUES ('reps_subject', 1)")
    conn.commit()
    item_id = conn.execute(
        "SELECT item_id FROM practice_items WHERE name = 'reps_subject'"
    ).fetchone()["item_id"]
    yield item_id
    conn = _db()._get_connection()
    conn.execute("DELETE FROM practice_sessions WHERE item_id = ?", (item_id,))
    conn.execute("DELETE FROM practice_items WHERE item_id = ?", (item_id,))
    conn.commit()


@pytest.fixture
def day():
    d = dt.date(2026, 9, 20)
    conn = _db()._get_connection()
    conn.execute("DELETE FROM daily_practices WHERE date = ?", (d.isoformat(),))
    conn.execute("DELETE FROM practice_sessions WHERE practice_date = ?", (d.isoformat(),))
    conn.execute("DELETE FROM practice_audit_log WHERE practice_date = ?", (d.isoformat(),))
    conn.commit()
    yield d
    conn = _db()._get_connection()
    conn.execute("DELETE FROM daily_practices WHERE date = ?", (d.isoformat(),))
    conn.execute("DELETE FROM practice_sessions WHERE practice_date = ?", (d.isoformat(),))
    conn.execute("DELETE FROM practice_audit_log WHERE practice_date = ?", (d.isoformat(),))
    conn.commit()


def _save(day, item_id, minutes, reps, content):
    return _db().save_practice_session_and_daily_summary(
        day, "reps_subject", item_id, minutes,
        "♪", 80, content, "manual",
        practice_at=f"{day.isoformat()} 09:00:00",
        reps=reps,
    )


def test_reps_roundtrip(item, day):
    saved = _save(day, item, 5, 8, "八遍")
    got = _db().get_practice_session_by_id(saved["id"])
    assert got["reps"] == 8


def test_reps_none_stays_none(item, day):
    saved = _save(day, item, 5, None, "未记")
    got = _db().get_practice_session_by_id(saved["id"])
    assert got["reps"] is None
    assert got["reps"] != 0


def test_reps_out_of_range_rejected(item, day):
    with pytest.raises(ValueError):
        _save(day, item, 5, 0, "零")
    with pytest.raises(ValueError):
        _save(day, item, 5, 100, "一百")
    with pytest.raises(ValidationError):
        PracticeLogRequest.model_validate({
            "date": day.isoformat(), "item": "reps_subject", "item_id": item,
            "minutes": 5, "tempo_note": "♪", "tempo_bpm": 80, "content": "x",
            "reps": 0,
        })


def test_put_updates_reps(item, day):
    saved = _save(day, item, 5, 3, "先三遍")
    client = TestClient(app)
    resp = client.put(f"/api/practice-sessions/{saved['id']}", json={"reps": 12})
    assert resp.status_code == 200, resp.text
    assert resp.json()["session"]["reps"] == 12
    assert _db().get_practice_session_by_id(saved["id"])["reps"] == 12


def test_delete_does_not_drift_reps(item, day):
    first = _save(day, item, 5, 4, "四遍")
    second = _save(day, item, 6, 9, "九遍")
    _db().delete_practice_session(first["id"])
    left = _db().get_practice_sessions(day)
    assert [s["id"] for s in left] == [second["id"]]
    assert left[0]["reps"] == 9
    daily = _db().get_daily_practice(day)
    assert daily["total_minutes"] == 6
    assert "reps" not in daily["items"][0]
    blog = daily["behavior_log"]
    assert [e.get("session_id") for e in blog] == [second["id"]]
    assert blog[0]["reps"] == 9


def test_behavior_log_mirrors_reps(item, day):
    saved = _save(day, item, 5, 7, "七遍")
    blog = _db().get_daily_practice(day)["behavior_log"]
    assert len(blog) == 1
    assert blog[0]["session_id"] == saved["id"]
    assert blog[0]["reps"] == 7


def test_migration_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "reps.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE practice_sessions (
            id INTEGER PRIMARY KEY,
            practice_date TEXT,
            duration_minutes INTEGER
        )"""
    )
    conn.commit()
    conn.close()
    first = migrate_sqlite(str(db_path))
    second = migrate_sqlite(str(db_path))
    assert "added" in first
    assert "已存在，跳过" in second
    cols = [r[1] for r in sqlite3.connect(db_path).execute("PRAGMA table_info(practice_sessions)")]
    assert "reps" in cols


def test_records_get_includes_sessions(item, day):
    _save(day, item, 5, 2, "两遍")
    client = TestClient(app)
    resp = client.get(f"/config/api/records/{day.isoformat()}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "sessions" in body
    assert body["sessions"][0]["reps"] == 2


def test_stage_payload_whitelists_reps(item, day):
    _save(day, item, 5, 6, "六遍")
    payload = _build_stage_detail_payload({
        "stage_order": 9,
        "stage_start": "2026-09-01",
        "stage_end": "2026-09-28",
        "items": [],
        "notes": "",
    })
    sessions = payload["days"][0]["groups"][0]["sessions"]
    assert "reps" in sessions[0]
    assert sessions[0]["reps"] == 6
    assert payload["by_item"][0]["reps"] == 6


def test_stage_reps_all_null_is_null(item, day):
    _save(day, item, 5, None, "空")
    payload = _build_stage_detail_payload({
        "stage_order": 9,
        "stage_start": "2026-09-01",
        "stage_end": "2026-09-28",
        "items": [],
        "notes": "",
    })
    assert payload["by_item"][0]["reps"] is None
    assert payload["days"][0]["groups"][0]["sessions"][0]["reps"] is None
