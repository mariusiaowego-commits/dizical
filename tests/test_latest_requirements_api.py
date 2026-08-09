"""回归测试: /config/api/assignments/latest-requirements (S2, 2026-08-09).

需求 2 (B1): 预填每科目最近一次非空要求 + 来源日期.

修复的 bug (S2 发现): 旧实现用裸 cursor (conn.cursor()), MySQL 端返 tuple,
row["items"] 下标访问抛 TypeError 被 except Exception: continue 吞掉 -> 线上一直返
{"items":{}} (预填从未生效, 前端 catch 静默降级). SQLite 端 sqlite3.Row 支持下标所以正常.

修复: 改用 db.get_weekly_assignments_in_range (双后端兼容), 返回加 lesson_date.
本测试 mock 数据库层, 验证返回结构 + 回退逻辑, 不碰真实库.
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
def patch_db_assignments(monkeypatch):
    """mock db.get_weekly_assignments_in_range 返回固定数据."""
    import src.kid_app.routes.config as cfg

    def _set(assignments):
        fake = mock.MagicMock()
        fake.get_weekly_assignments_in_range.return_value = assignments
        monkeypatch.setattr(cfg, "db", fake)

    return _set


def test_latest_requirements_returns_lesson_date_and_metronome(patch_db_assignments):
    """返回含 lesson_date + metronome."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db_assignments([
        _make_assignment("2026-08-08", [
            {"item": "吸气长音", "item_id": 1034, "metronome": "♩=60",
             "requirements": "用八度练习"},
        ]),
    ])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/latest-requirements")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert "1034" in items
    assert items["1034"]["lesson_date"] == "2026-08-08"
    assert items["1034"]["metronome"] == "♩=60"
    assert items["1034"]["requirements"] == "用八度练习"


def test_latest_requirements_newest_wins(patch_db_assignments):
    """同一科目多次记录 -> 取最新 (按 lesson_date 倒序)."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db_assignments([
        _make_assignment("2026-07-26", [
            {"item": "吸气长音", "item_id": 1034, "metronome": "♩=55",
             "requirements": "旧要求"},
        ]),
        _make_assignment("2026-08-08", [
            {"item": "吸气长音", "item_id": 1034, "metronome": "♩=60",
             "requirements": "新要求"},
        ]),
    ])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/latest-requirements")
    items = resp.json()["items"]
    assert items["1034"]["lesson_date"] == "2026-08-08"
    assert items["1034"]["requirements"] == "新要求"
    assert items["1034"]["metronome"] == "♩=60"


def test_latest_requirements_empty_newest_falls_back(patch_db_assignments):
    """最新记录要求为空 -> 回退到更早的非空要求 (含 metronome + lesson_date)."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db_assignments([
        _make_assignment("2026-07-26", [
            {"item": "吸气长音", "item_id": 1034, "metronome": "♩=55",
             "requirements": "旧要求"},
        ]),
        _make_assignment("2026-08-08", [
            {"item": "吸气长音", "item_id": 1034, "metronome": "",
             "requirements": ""},
        ]),
    ])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/latest-requirements")
    items = resp.json()["items"]
    assert items["1034"]["lesson_date"] == "2026-07-26"
    assert items["1034"]["requirements"] == "旧要求"
    assert items["1034"]["metronome"] == "♩=55"


def test_latest_requirements_empty_db_returns_empty(patch_db_assignments):
    """无记录 -> 空 dict, 不报错."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    patch_db_assignments([])
    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/latest-requirements")
    assert resp.status_code == 200
    assert resp.json()["items"] == {}
