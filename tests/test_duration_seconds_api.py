"""练习时长秒级：口径 B、/api/log 透传、去重 key、响应新增秒字段。

分钟字段的值和聚合方式保持原样。秒缺省时按 minutes * 60。
"""
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.kid_app.app import (
    _build_stage_detail_payload,
    _check_dedup,
    _filter_payload_by_days,
    _record_dedup,
    app as fastapi_app,
)
from src.kid_app.duration_fmt import fmt, pick_seconds, short, write_minutes
from src.kid_app.schemas import PracticeLogRequest
from src import practice as practice_module


SAMPLES = (0, 10, 60, 61, 599, 3600, 7325)
FMT_EXPECTED = {
    0: "",
    10: "10秒",
    60: "1分",
    61: "1分1秒",
    599: "9分59秒",
    3600: "60分",
    7325: "122分5秒",
}
SHORT_EXPECTED = {
    0: "",
    10: "0:10",
    60: "1:00",
    61: "1:01",
    599: "9:59",
    3600: "60:00",
    7325: "122:05",
}


@pytest.fixture
def client(monkeypatch):
    async def _mock_user(*args, **kwargs):
        return {"id": 1, "username": "dad", "role": "dad"}

    monkeypatch.setattr("src.kid_app.auth.get_current_user", _mock_user)
    return TestClient(fastapi_app)


def test_fmt_and_short_rule_b_branches():
    for sec in SAMPLES:
        assert fmt(sec) == FMT_EXPECTED[sec]
        assert short(sec) == SHORT_EXPECTED[sec]
    assert fmt(None) == ""
    assert pick_seconds(None, 5) == 300
    assert pick_seconds(0, 5) == 300
    assert pick_seconds(10, 5) == 10
    assert write_minutes(5, None) == 5
    assert write_minutes(1, 61) == 2
    assert write_minutes(9, 10) == 1


def test_js_duration_fmt_matches_python():
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    js = Path(__file__).resolve().parent.parent / "src/kid_app/static/js/duration-fmt.js"
    script = (
        "global.window = global;"
        "eval(require('fs').readFileSync(process.argv[1], 'utf8'));"
        "const xs = [0,10,60,61,599,3600,7325];"
        "process.stdout.write(JSON.stringify(xs.map(s => [DizicalDur.fmt(s), DizicalDur.short(s)])));"
    )
    proc = subprocess.run(
        [node, "-e", script, str(js)],
        check=True, capture_output=True, text=True,
    )
    got = json.loads(proc.stdout)
    for sec, pair in zip(SAMPLES, got):
        assert pair == [FMT_EXPECTED[sec], SHORT_EXPECTED[sec]]


def test_schema_seconds_bounds():
    base = {"date": "2099-01-01", "item": "长音", "item_id": 3, "minutes": 1}
    assert PracticeLogRequest.model_validate({**base, "seconds": 0}).seconds == 0
    assert PracticeLogRequest.model_validate({**base, "seconds": 86400}).seconds == 86400
    assert PracticeLogRequest.model_validate(base).seconds is None
    for bad in (-1, 86401):
        with pytest.raises(ValidationError):
            PracticeLogRequest.model_validate({**base, "seconds": bad})
    with pytest.raises(ValidationError):
        PracticeLogRequest.model_validate({**base, "minutes": 0})


def test_dedup_key_uses_seconds_so_10_and_50_do_not_collide():
    body = {"ok": True}
    _record_dedup("2099-03-01", 980, 1, body, seconds=10)
    assert _check_dedup("2099-03-01", 980, 1, seconds=50) is None
    assert _check_dedup("2099-03-01", 980, 1, seconds=10)["ok"] is True
    _record_dedup("2099-03-02", 981, 5, body)
    assert _check_dedup("2099-03-02", 981, 1, seconds=300)["ok"] is True
    assert _check_dedup("2099-03-02", 981, 5)["ok"] is True


def _legacy_body(**extra):
    body = {
        "date": "2099-05-01",
        "item": "长音",
        "item_id": 3,
        "minutes": 5,
    }
    body.update(extra)
    return body


def test_api_log_legacy_without_seconds_stores_minutes_times_60(client, monkeypatch):
    saved = {}

    def fake_save(date, items, total, log_note, **kwargs):
        saved["items"] = items
        saved["total"] = total

    monkeypatch.setattr("src.kid_app.app.db.save_daily_practice", fake_save)
    monkeypatch.setattr("src.kid_app.app.db.append_behavior_log", lambda *a, **k: None)
    r = client.post("/api/log", json=_legacy_body(
        date="2099-05-11",
        behavior_log=[{"enter_time": "2099-05-11 19:00:00", "item": "长音", "minutes": 5}],
    ))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 5
    assert body["seconds"] == 300
    assert saved["total"] == 5
    assert saved["items"][0]["minutes"] == 5
    assert saved["items"][0]["seconds"] == 300


def test_api_log_legacy_with_seconds_ceils_minutes(client, monkeypatch):
    saved = {}

    def fake_save(date, items, total, log_note, **kwargs):
        saved["items"] = items
        saved["total"] = total

    monkeypatch.setattr("src.kid_app.app.db.save_daily_practice", fake_save)
    monkeypatch.setattr("src.kid_app.app.db.append_behavior_log", lambda *a, **k: saved.setdefault("log", []).append(a[1]))
    r = client.post("/api/log", json=_legacy_body(
        date="2099-05-12", item_id=982, minutes=1, seconds=61,
        behavior_log=[{"enter_time": "2099-05-12 19:00:00", "item": "长音", "minutes": 0}],
    ))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert body["seconds"] == 61
    assert saved["items"][0]["minutes"] == 2
    assert saved["items"][0]["seconds"] == 61
    # sprint 26100101 F5: 条目自己的 minutes=0（"进来看一眼没练"）不得继承 session 总秒 61
    # 旧实现: em * 60 if em else seconds → 61（此处曾是 == 61, 即 bug 被测试锁死）
    assert saved["log"][0]["seconds"] == 0


def test_api_log_session_path_passes_seconds(client, monkeypatch):
    saved = {}

    def fake_session(*args, **kwargs):
        saved["minutes"] = args[3]
        saved["seconds"] = kwargs.get("seconds")
        return {"id": 7, "duration_minutes": args[3], "duration_seconds": kwargs.get("seconds")}

    monkeypatch.setattr("src.kid_app.app.db.save_practice_session_and_daily_summary", fake_session)
    monkeypatch.setattr(
        "src.kid_app.app.db.get_daily_practice",
        lambda day: {"total_minutes": 5, "items": []},
    )
    r = client.post("/api/log", json=_legacy_body(
        date="2099-05-13", item_id=983,
        tempo_note="♪", tempo_bpm=80, content="第一分句",
    ))
    assert r.status_code == 200, r.text
    body = r.json()
    assert saved["minutes"] == 5
    assert saved["seconds"] == 300
    assert body["total"] == 5
    assert body["seconds"] == 300

    monkeypatch.setattr(
        "src.kid_app.app.db.get_daily_practice",
        lambda day: {"total_minutes": 2, "items": []},
    )
    r2 = client.post("/api/log", json=_legacy_body(
        date="2099-05-14", item_id=984, minutes=1, seconds=61,
        tempo_note="♪", tempo_bpm=80, content="第二分句",
    ))
    assert r2.status_code == 200, r2.text
    assert saved["minutes"] == 2
    assert saved["seconds"] == 61
    assert r2.json()["total"] == 2
    assert r2.json()["seconds"] == 61


def test_api_log_dedup_10s_and_50s_both_persist(client, monkeypatch):
    calls = []

    def fake_save(date, items, total, log_note, **kwargs):
        calls.append(items[0]["seconds"])

    monkeypatch.setattr("src.kid_app.app.db.save_daily_practice", fake_save)
    monkeypatch.setattr("src.kid_app.app.db.append_behavior_log", lambda *a, **k: None)
    common = dict(date="2099-05-15", item="长音", item_id=985, minutes=1)
    assert client.post("/api/log", json={**common, "seconds": 10}).status_code == 200
    assert client.post("/api/log", json={**common, "seconds": 50}).status_code == 200
    again = client.post("/api/log", json={**common, "seconds": 10})
    assert again.status_code == 200
    assert calls == [10, 50]


def test_get_practice_day_adds_seconds_keeps_minutes(client, monkeypatch):
    practice = {
        "id": 1,
        "items": [
            {"item": "长音", "item_id": 3, "minutes": 5},
            {"item": "吐音", "item_id": 4, "minutes": 2, "seconds": 0},
            {"item": "活指", "item_id": 5, "minutes": 1, "seconds": 10},
        ],
        "total_minutes": 8,
        "log": "",
        "behavior_log": [{"enter_time": "t", "item": "长音", "minutes": 5}],
    }
    sessions = [{
        "id": 9, "duration_minutes": 1, "item_name": "活指",
        "duration_seconds": 10,
    }]
    monkeypatch.setattr("src.kid_app.app.db.get_daily_practice", lambda day: practice)
    monkeypatch.setattr("src.kid_app.app.db.get_practice_sessions", lambda day: sessions)
    body = client.get("/api/practices/2099-06-01").json()
    assert body["total_minutes"] == 8
    assert body["total_seconds"] == 300 + 120 + 10
    assert [it["seconds"] for it in body["items"]] == [300, 120, 10]
    assert [it["minutes"] for it in body["items"]] == [5, 2, 1]
    assert body["behavior_log"][0]["seconds"] == 300
    assert body["behavior_log"][0]["minutes"] == 5
    assert body["sessions"][0]["duration_seconds"] == 10
    assert body["sessions"][0]["duration_minutes"] == 1

    monkeypatch.setattr("src.kid_app.app.db.get_daily_practice", lambda day: None)
    empty = client.get("/api/practices/2099-06-02").json()
    assert empty["total_minutes"] == 0
    assert empty["total_seconds"] == 0


def test_today_stats_adds_total_seconds(client, monkeypatch):
    monkeypatch.setattr(
        "src.kid_app.routes.minip_api.db.get_daily_practice",
        lambda day: {
            "total_minutes": 8,
            "items": [
                {"item": "长音", "minutes": 5, "seconds": 10},
                {"item": "吐音", "minutes": 3},
            ],
        },
    )
    body = client.get("/api/today-stats").json()
    assert body["total_minutes"] == 8
    assert body["total_seconds"] == 10 + 180


def test_stage_payload_seconds_do_not_change_minutes(monkeypatch):
    sessions = [
        {
            "id": 1, "practice_date": "2026-07-25", "item_id": 3, "item_name": "长音",
            "duration_minutes": 1, "duration_seconds": 10,
            "started_at": "2026-07-25 19:00:00", "tempo_note": "♪", "tempo_bpm": 80,
            "content": "a", "reps": None, "is_extra": 0,
        },
        {
            "id": 2, "practice_date": "2026-07-25", "item_id": 3, "item_name": "长音",
            "duration_minutes": 5,
            "started_at": "2026-07-25 19:10:00", "tempo_note": "♪", "tempo_bpm": 80,
            "content": "b", "reps": None, "is_extra": 0,
        },
    ]
    monkeypatch.setattr(
        "src.kid_app.app.db.get_practice_sessions_in_range",
        lambda start, end: sessions,
    )
    payload = _build_stage_detail_payload({
        "stage_order": 1,
        "stage_start": "2026-07-20",
        "stage_end": "2026-07-26",
        "lesson_date": "2026-07-20",
        "notes": "",
        "items": [],
    })
    assert payload["summary"]["total_minutes"] == 6
    assert payload["summary"]["total_seconds"] == 310
    assert payload["by_item"][0]["minutes"] == 6
    assert payload["by_item"][0]["seconds"] == 310
    assert payload["days"][0]["total_minutes"] == 6
    assert payload["days"][0]["total_seconds"] == 310
    assert payload["days"][0]["groups"][0]["sessions"][1]["duration_seconds"] == 300
    filtered = _filter_payload_by_days(payload, "2026-07-25")
    assert filtered["summary"]["total_minutes"] == 6
    assert filtered["summary"]["total_seconds"] == 310
    assert filtered["by_item"][0]["seconds"] == 310


def test_week_summary_sums_seconds_without_re_ceiling(monkeypatch):
    rows = [{
        "date": dt.date(2026, 7, 6),
        "total_minutes": 2,
        "items": [
            {"item": "长音", "minutes": 1, "seconds": 10},
            {"item": "吐音", "minutes": 1, "seconds": 50},
        ],
    }]
    monkeypatch.setattr(practice_module.db, "get_daily_practices_in_range", lambda a, b: rows)
    monkeypatch.setattr(practice_module.db, "get_weekly_assignment", lambda d: None)
    monkeypatch.setattr(practice_module.db, "get_progress_from_log_in_range", lambda a, b: {})
    out = practice_module.get_week_summary(dt.date(2026, 7, 6))
    assert out["total_minutes"] == 2
    assert out["total_seconds"] == 60
    assert out["item_seconds"]["长音"] == 10
    assert out["item_seconds"]["吐音"] == 50


def test_post_records_server_sums_seconds_and_keeps_minutes(client, monkeypatch):
    saved = {}

    def fake_save(**kwargs):
        saved.update(kwargs)

    monkeypatch.setattr("src.kid_app.routes.config.db.save_daily_practice", fake_save)
    r = client.post("/config/api/records", json={
        "date": "2099-04-01",
        "items": [
            {"item": "长音", "item_id": 3, "minutes": 1, "seconds": 10},
            {"item": "吐音", "item_id": 4, "minutes": 2},
        ],
        "total_minutes": 3,
        "total_seconds": 99999,
    })
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert r.json()["total_seconds"] == 130
    assert saved["total_minutes"] == 3
    assert saved["items"][0]["minutes"] == 1
    assert saved["items"][0]["seconds"] == 10
    assert saved["items"][1]["seconds"] == 120

    bad = client.post("/config/api/records", json={
        "date": "2099-04-02",
        "items": [{"item": "长音", "item_id": 3, "minutes": 1, "seconds": 90000}],
        "total_minutes": 1,
    })
    assert bad.status_code == 400


def test_put_session_duration_seconds_also_writes_ceiled_minutes(client, monkeypatch):
    seen = {}

    def fake_update(session_id, **kwargs):
        seen["id"] = session_id
        seen["kwargs"] = kwargs
        return {
            "id": session_id,
            "duration_minutes": kwargs.get("duration_minutes"),
            "duration_seconds": kwargs.get("duration_seconds"),
        }

    monkeypatch.setattr("src.kid_app.app.db.update_practice_session", fake_update)
    r = client.put("/api/practice-sessions/42", json={"duration_seconds": 61})
    assert r.status_code == 200, r.text
    assert seen["kwargs"]["duration_seconds"] == 61
    assert seen["kwargs"]["duration_minutes"] == 2
    session = r.json()["session"]
    assert session["duration_minutes"] == 2
    assert session["duration_seconds"] == 61


def test_behavior_log_entry_seconds_follow_its_own_minutes(client, monkeypatch):
    """F5: 条目 seconds 只由自己的 minutes 决定，不借用 session 总秒。"""
    saved = {}

    monkeypatch.setattr("src.kid_app.app.db.save_daily_practice",
                        lambda *a, **k: None)
    monkeypatch.setattr("src.kid_app.app.db.append_behavior_log",
                        lambda *a, **k: saved.setdefault("log", []).append(a[1]))

    r = client.post("/api/log", json=_legacy_body(
        date="2099-05-16", item_id=986, minutes=10, seconds=600,
        behavior_log=[
            {"enter_time": "2099-05-16 19:00:00", "item": "长音", "minutes": 0},   # 看一眼没练
            {"enter_time": "2099-05-16 19:05:00", "item": "吐音", "minutes": 2},   # 练了 2 分钟
            {"enter_time": "2099-05-16 19:09:00", "item": "活指", "minutes": 0, "seconds": 0},
        ],
    ))
    assert r.status_code == 200, r.text
    got = [e["seconds"] for e in saved["log"]]
    assert got == [0, 120, 0], f"期望 [0,120,0]，实际 {got}（旧实现给 [600,120,600]）"
