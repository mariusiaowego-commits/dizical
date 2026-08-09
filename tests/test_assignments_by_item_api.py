"""回归测试: /config/api/assignments/by-item (S3, 2026-08-09).

需求3: 选中科目后展示该科目历史 3 次老师要求 (含速度), 可复制.

关键设计: 按 item_id 优先, 其次按科目名匹配 — 兼容历史数据 item_id 为 null 的记录
(云端 8-01 的记录 item_id 是 null, 只有 item 名; 只按 item_id 过滤会漏历史).

mock db.get_weekly_assignments_in_range, 不碰真实库.
"""
import datetime as dt
from unittest import mock

import pytest


def _make_assignment(lesson_date, items):
    return {
        "id": 1,
        "lesson_date": dt.date.fromisoformat(lesson_date),
        "stage_start": None,
        "stage_end": None,
        "stage_order": None,
        "items": items,
        "notes": "",
        "images": [],
    }


@pytest.fixture
def patch_db(monkeypatch):
    """mock db.get_weekly_assignments_in_range."""
    import src.kid_app.routes.config as cfg

    def _set(assignments):
        fake = mock.MagicMock()
        fake.get_weekly_assignments_in_range.return_value = assignments
        monkeypatch.setattr(cfg, "db", fake)

    return _set


def test_by_item_id_returns_history(patch_db):
    """按 item_id 查, 返回最近 3 次倒序."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db([
        _make_assignment("2026-07-26", [
            {"item": "吸气长音", "item_id": 1034, "metronome": "♩=55", "requirements": "旧要求"},
        ]),
        _make_assignment("2026-08-01", [
            {"item": "吸气长音", "item_id": None, "metronome": "♩=58", "requirements": "中要求"},
        ]),
        _make_assignment("2026-08-08", [
            {"item": "吸气长音", "item_id": 1034, "metronome": "♩=60", "requirements": "新要求"},
        ]),
    ])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/by-item?item_id=1034&limit=3")
    assert resp.status_code == 200
    hist = resp.json()["history"]
    # item_id=1034 匹配: 8-08 和 7-26 (8-01 是 null 不匹配 item_id)
    assert len(hist) == 2
    assert hist[0]["lesson_date"] == "2026-08-08"
    assert hist[0]["requirements"] == "新要求"
    assert hist[1]["lesson_date"] == "2026-07-26"


def test_by_item_name_catches_null_id(patch_db):
    """按科目名匹配, 能抓到 item_id 为 null 的历史 (兼容场景)."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db([
        _make_assignment("2026-08-01", [
            {"item": "吸气长音", "item_id": None, "metronome": "♩=58", "requirements": "中要求"},
        ]),
    ])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/by-item?item=%E5%90%B8%E6%B0%94%E9%95%BF%E9%9F%B3&limit=3")
    assert resp.status_code == 200
    hist = resp.json()["history"]
    assert len(hist) == 1
    assert hist[0]["lesson_date"] == "2026-08-01"
    assert hist[0]["metronome"] == "♩=58"


def test_by_item_limit_default_3(patch_db):
    """默认 limit=3, 最多返 3 条."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db([
        _make_assignment(f"2026-07-{d:02d}", [
            {"item": "单吐练习", "item_id": 1003, "metronome": "", "requirements": f"第{d}次"},
        ]) for d in range(20, 26)
    ])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/by-item?item_id=1003")
    hist = resp.json()["history"]
    assert len(hist) == 3
    assert hist[0]["lesson_date"] == "2026-07-25"


def test_by_item_no_params_400(patch_db):
    """无 item_id / item 参数 -> 400."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db([])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/by-item")
    assert resp.status_code == 400


def test_by_item_empty_history(patch_db):
    """无匹配记录 -> 空 history, 不报错."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db([])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/by-item?item_id=9999")
    assert resp.status_code == 200
    assert resp.json()["history"] == []
