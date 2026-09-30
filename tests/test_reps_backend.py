"""practice_sessions.reps 后端：写入、空值、越界、修改、删除镜像、迁移、读出。"""
import datetime as dt
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import src.database as db_module
from src.kid_app.app import _build_stage_detail_payload, _filter_payload_by_days, app
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


def _raw_behavior_log(day):
    """直接读原始文本 (绕开 get_daily_practice 的 json 解析)."""
    conn = _db()._get_connection()
    row = conn.execute(
        "SELECT behavior_log FROM daily_practices WHERE date = ?", (day.isoformat(),)
    ).fetchone()
    return row["behavior_log"] if row else None


def _set_raw_behavior_log(day, raw):
    conn = _db()._get_connection()
    conn.execute(
        "UPDATE daily_practices SET behavior_log = ? WHERE date = ?", (raw, day.isoformat())
    )
    conn.commit()


def _append_raw_behavior_log_entries(day, extra):
    """在现有 behavior_log 尾部追加 entry (保留 session 自己的 entry)."""
    raw = _raw_behavior_log(day)
    entries = json.loads(raw) if raw else []
    entries.extend(extra)
    _set_raw_behavior_log(day, json.dumps(entries, ensure_ascii=False))


def test_legacy_entry_without_session_id_survives_put_and_delete(item, day):
    """FIX-1 负控: 无 session_id 的老 entry 绝不能被 enter_time 兜底误伤.

    复现真实数据形态 (真库 2025-09-27: 3 条 session 共用同一 started_at,
    4 条老 entry 都没有 session_id 但 enter_time 与该 started_at 完全相同).
    ① PUT reps 后老 entry 仍无 reps
    ② delete session 后老 entry 仍在
    """
    started_at = f"{day.isoformat()} 21:57:06.994"
    saved = _db().save_practice_session_and_daily_summary(
        day, "reps_subject", item, 5, "♪", 80, "右手持笛", "manual",
        practice_at=started_at, reps=None,
    )
    # 老 entry: 无 session_id, 但 enter_time 与该 session.started_at 完全相同
    _append_raw_behavior_log_entries(day, [
        {"enter_time": started_at, "item": "深呼吸、站姿1", "minutes": 5},
        {"enter_time": started_at, "item": "吹 e1", "minutes": 15},
    ])

    # ① PUT reps → 只有本 session 的 entry 带 reps, 两条老 entry 不许被写
    _db().update_practice_session(saved["id"], reps=7, apply_reps=True)
    raw = _raw_behavior_log(day)
    assert raw is not None, "behavior_log 行不应消失"
    by_item = {e.get("item"): e for e in json.loads(raw)}
    # 本 session 自己的 entry (session_id 匹配) 必须同步 reps
    mine = [e for e in json.loads(raw) if e.get("session_id") == saved["id"]]
    assert len(mine) == 1, "本 session 的 entry 应还在"
    assert mine[0]["reps"] == 7, "本 session 的 entry 必须同步 reps"
    assert "reps" not in by_item.get("深呼吸、站姿1", {}), "老 entry 被误写 reps (enter_time 兜底没删干净)"
    assert "reps" not in by_item.get("吹 e1", {}), "老 entry 被误写 reps (enter_time 兜底没删干净)"

    # ② delete session → 两条老 entry 必须还在
    _db().delete_practice_session(saved["id"])
    raw2 = _raw_behavior_log(day)
    assert raw2 is not None, "behavior_log 行不应消失"
    items_left = sorted(e.get("item") for e in json.loads(raw2))
    assert items_left == ["吹 e1", "深呼吸、站姿1"], "老 entry 被误删 (enter_time 兜底没删干净)"


def test_unparsable_behavior_log_is_not_overwritten(item, day):
    """FIX-2 负控: behavior_log 是非 JSON 文本时, PUT reps 不得把它清空."""
    saved = _save(day, item, 5, 3, "三遍")
    _set_raw_behavior_log(day, "TEXT-LEGACY-LOG")
    _db().update_practice_session(saved["id"], reps=5, apply_reps=True)
    assert _raw_behavior_log(day) == "TEXT-LEGACY-LOG", "非 JSON 文本被 [] 覆盖, 历史日志丢了"

    _db().delete_practice_session(saved["id"])
    assert _raw_behavior_log(day) == "TEXT-LEGACY-LOG", "删 session 把非 JSON 文本覆盖成 []"


def test_behavior_log_json_object_is_not_overwritten(item, day):
    """FIX-2 负控: behavior_log 是 JSON dict (非 list) 时原样保留."""
    saved = _save(day, item, 5, 3, "三遍")
    raw = json.dumps({"legacy": "shape"})
    _set_raw_behavior_log(day, raw)
    _db().update_practice_session(saved["id"], reps=5, apply_reps=True)
    assert _raw_behavior_log(day) == raw


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


# ── FIX-4 (审计 P1-4): by_item 遍数字段名契约 ──────────────────────
#
# 背景: 后端 _filter_payload_by_days 写的是 item_map[gid]["reps"], 而 stage-print.html
# 的 filterPayloadByDays 算 total_reps、renderHeader 读 it.total_reps —— 字段名三个
# 地方两个口径, 靠 renderHeader 里那段 undefined 兜底重算才能出数.
# 这条测试同时锁死「后端 payload 用 reps」和「前端两处都读 reps、不再有 total_reps」,
# 删掉前端任一处都会红.
def test_filter_payload_by_days_uses_reps_key(item, day):
    _save(day, item, 5, 4, "四遍")
    _save(day, item, 6, 6, "六遍")
    payload = _build_stage_detail_payload({
        "stage_order": 9,
        "stage_start": "2026-09-01",
        "stage_end": "2026-09-28",
        "items": [],
        "notes": "",
    })
    filtered = _filter_payload_by_days(payload, f"{day.isoformat()}")
    entry = filtered["by_item"][0]
    assert "reps" in entry, "后端 by_item 必须含 reps 键"
    assert "total_reps" not in entry, "total_reps 口径已废弃, 不能再出现"
    assert entry["reps"] == 10, "两条 session 遍数应累计 (4+6)"


def test_filter_payload_by_days_all_null_keeps_none(item, day):
    _save(day, item, 5, None, "空")
    payload = _build_stage_detail_payload({
        "stage_order": 9,
        "stage_start": "2026-09-01",
        "stage_end": "2026-09-28",
        "items": [],
        "notes": "",
    })
    filtered = _filter_payload_by_days(payload, f"{day.isoformat()}")
    assert filtered["by_item"][0]["reps"] is None, "全 NULL 必须保持 None, 不污染成 0"


def test_stage_print_html_uses_reps_key_only():
    """前端两处都必须用 reps: 算的 (filterPayloadByDays) + 读的 (renderHeader)."""
    html = Path(__file__).resolve().parents[1].joinpath(
        "src/kid_app/templates/stage-print.html"
    ).read_text(encoding="utf-8")
    assert "itemMap[id].reps" in html, "filterPayloadByDays 必须算 reps"
    assert "var rSum = it.reps;" in html, "renderHeader 必须读 reps"
    # 旧字段名除注释外不得残留
    live = [ln for ln in html.splitlines()
            if "total_reps" in ln and not ln.strip().startswith("//")]
    assert not live, f"前端仍有 total_reps 残留: {live}"
