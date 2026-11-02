"""票夹科目历史和连续天数改读真数据。"""
import datetime as dt

import pytest
from fastapi.testclient import TestClient

from src.database import db
from src.kid_app.app import app

ROOT_TPL = __import__("pathlib").Path(__file__).resolve().parents[1] / "src" / "kid_app" / "templates" / "practice-dsh.html"


@pytest.fixture
def client(monkeypatch):
    async def _mock_user(*args, **kwargs):
        return {"id": 1, "username": "yoyo", "role": "student"}

    monkeypatch.setattr("src.kid_app.auth.get_current_user", _mock_user)
    return TestClient(app)


def _day(offset):
    return dt.date.today() + dt.timedelta(days=offset)


def _insert_day(day, minutes):
    conn = db._get_connection()
    conn.execute(
        "INSERT INTO daily_practices (date, items, total_minutes, practiced) VALUES (?, ?, ?, ?)",
        (day.isoformat(), "[]", minutes, "Y"),
    )
    conn.commit()


def test_item_stats_route_is_not_captured_as_a_date(client):
    resp = client.get("/api/practices/item-stats")
    assert resp.status_code == 400
    assert resp.json()["error"] == "item_id 必须是整数"


def test_item_stats_rejects_bad_month(client):
    resp = client.get("/api/practices/item-stats?item_id=1034&month=2026-13")
    assert resp.status_code == 400
    assert "YYYY-MM" in resp.json()["error"]


def test_item_stats_aggregates_seconds_days_and_month(client):
    db.create_practice_session(
        dt.date(2026, 10, 2), 1034, "吸气长音", 2,
        content="上午", duration_seconds=90,
    )
    db.create_practice_session(
        dt.date(2026, 10, 2), 1034, "吸气长音", 1,
        content="下午", duration_seconds=30,
    )
    db.create_practice_session(
        dt.date(2026, 11, 1), 1034, "吸气长音", 2,
        content="晚上", duration_seconds=120,
    )
    # 秒没回填的旧行：duration_seconds=0，应按分钟 × 60 计入。
    db.create_practice_session(
        dt.date(2026, 11, 3), 1034, "吸气长音", 5,
        content="旧行", duration_seconds=0,
    )
    db.create_practice_session(
        dt.date(2026, 11, 1), 9999, "别的科目", 4,
        content="无关", duration_seconds=240,
    )

    resp = client.get("/api/practices/item-stats?item_id=1034&month=2026-10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["item_id"] == 1034
    assert body["name"] == "吸气长音"
    assert body["sessions"] == 4
    assert body["days"] == 3
    assert body["total_seconds"] == 90 + 30 + 120 + 300
    assert body["minutes"] == (540 + 59) // 60
    assert body["max_seconds"] == 300
    assert body["max_minutes"] == 5
    assert body["last_date"] == "2026-11-03"
    assert body["days_ago"] == (dt.date.today() - dt.date(2026, 11, 3)).days
    assert body["month"] == "2026-10"
    assert body["practice_dates"] == ["2026-10-02"]

    nov = client.get("/api/practices/item-stats?item_id=1034&month=2026-11")
    assert nov.status_code == 200
    assert nov.json()["practice_dates"] == ["2026-11-01", "2026-11-03"]

    empty = client.get("/api/practices/item-stats?item_id=4242&month=2026-11")
    assert empty.status_code == 200
    zero = empty.json()
    assert zero["sessions"] == 0
    assert zero["days"] == 0
    assert zero["total_seconds"] == 0
    assert zero["minutes"] == 0
    assert zero["last_date"] == ""
    assert zero["days_ago"] is None
    assert zero["practice_dates"] == []


def test_overview_counts_practice_days_and_reuses_streak(client):
    _insert_day(_day(-1), 12)
    _insert_day(_day(-2), 8)
    _insert_day(_day(-4), 3)  # 中间隔了一天，不进当前连续

    resp = client.get("/api/practices/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["practice_days"] == 3
    assert body["streak"] == 2
    assert body["last_date"] == _day(-1).isoformat()


def test_practice_dsh_template_reads_live_stats_not_the_frozen_snapshot():
    html = ROOT_TPL.read_text()
    assert "function ensureItemStats" in html
    assert "/api/practices/item-stats" in html
    assert "/api/practices/overview" in html
    assert "['A', 'D', 'R']" in html
    assert "function paintCollapsedOverview" in html
    assert "ITEM_STATS[cur.id]._live" in html
