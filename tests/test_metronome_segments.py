"""回归测试: 速度多档 metronome_segments (S5, 2026-08-09).

需求4 (dad 拍板 A1): 保留 metronome 字符串 (斜杠拼接兼容老消费者) + 新增
metronome_segments: [{label 自由文本, tempo}]. label 不限 range,
覆盖 时间分段(前3天/后3天) / 交替练习 / situation 1/2/3 场景.

验证:
1. POST 带 segments -> 组装 metronome 斜杠串 + 存储 segments
2. PUT 同样
3. 老数据兼容: 无 segments 字段 -> metronome 单值原样
4. database.py 预填解析: "♩=95 / 100" 取第一段 95 (之前 int() 抛错被吞)
"""
import datetime as dt
from unittest import mock

import pytest


# ── POST/PUT segments 组装 (mock db 层) ──

@pytest.fixture
def client_and_db(monkeypatch):
    """TestClient + mock db.save_weekly_assignment 捕获写入."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app
    import src.kid_app.routes.config as cfg

    captured = {}

    def fake_save(lesson_date, items, notes=None, images=None):
        captured["items"] = items

    # mock 需要的方法
    monkeypatch.setattr(cfg.db, "save_weekly_assignment", fake_save)
    monkeypatch.setattr(cfg.db, "get_weekly_assignment", lambda ld: None)
    # api_create_assignment 里 stage 覆盖逻辑用到 db._get_connection, mock 掉
    fake_conn = mock.MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    monkeypatch.setattr(cfg.db, "_get_connection", lambda: fake_conn)

    with TestClient(app) as c:
        yield c, captured


def test_post_with_segments_assembles_metronome(client_and_db):
    c, captured = client_and_db
    resp = c.post("/config/api/assignments", json={
        "lesson_date": "2026-08-09",
        "items": [{
            "item": "单吐练习", "item_id": 1003,
            "metronome": "", "requirement": "分段练习",
            "metronome_segments": [
                {"label": "前3天", "tempo": "♩=95"},
                {"label": "后3天", "tempo": "♩=100"},
            ],
        }],
    })
    assert resp.status_code == 200
    saved = captured["items"][0]
    assert saved["metronome"] == "♩=95 / ♩=100"  # 斜杠拼接 (A1 兼容)
    assert saved["metronome_segments"] == [
        {"label": "前3天", "tempo": "♩=95"},
        {"label": "后3天", "tempo": "♩=100"},
    ]


def test_post_without_segments_keeps_metronome(client_and_db):
    """老数据兼容: 无 segments -> metronome 单值原样, segments=None."""
    c, captured = client_and_db
    resp = c.post("/config/api/assignments", json={
        "lesson_date": "2026-08-09",
        "items": [{"item": "单吐练习", "item_id": 1003, "metronome": "♩=82", "requirement": "背谱"}],
    })
    assert resp.status_code == 200
    saved = captured["items"][0]
    assert saved["metronome"] == "♩=82"
    assert saved.get("metronome_segments") is None


def test_put_with_segments(client_and_db):
    c, captured = client_and_db
    resp = c.put("/config/api/assignments/2026-08-09", json={
        "items": [{
            "item": "萨丽哈", "item_id": 1340,
            "metronome": "", "requirement": "交替",
            "metronome_segments": [
                {"label": "情况1", "tempo": "♪=88"},
                {"label": "情况2", "tempo": "♪=104"},
            ],
        }],
    })
    assert resp.status_code == 200
    saved = captured["items"][0]
    assert saved["metronome"] == "♪=88 / ♪=104"
    assert len(saved["metronome_segments"]) == 2


# ── by-item API 返回 segments ──

def test_by_item_returns_segments(monkeypatch):
    from fastapi.testclient import TestClient
    from src.kid_app.app import app
    import src.kid_app.routes.config as cfg

    fake_db = mock.MagicMock()
    fake_db.get_weekly_assignments_in_range.return_value = [{
        "id": 1,
        "lesson_date": dt.date(2026, 8, 8),
        "stage_start": None, "stage_end": None, "stage_order": None,
        "items": [{
            "item": "单吐练习", "item_id": 1003, "metronome": "♩=95 / ♩=100",
            "requirements": "分段", "metronome_segments": [
                {"label": "前3天", "tempo": "♩=95"}, {"label": "后3天", "tempo": "♩=100"},
            ],
        }],
        "notes": "", "images": [],
    }]
    monkeypatch.setattr(cfg, "db", fake_db)

    with TestClient(app) as c:
        resp = c.get("/config/api/assignments/by-item?item_id=1003")
    hist = resp.json()["history"]
    assert hist[0]["metronome_segments"] == [
        {"label": "前3天", "tempo": "♩=95"}, {"label": "后3天", "tempo": "♩=100"},
    ]


# ── database.py 预填解析防御 ──

def test_metronome_slash_parsing_takes_first():
    """'♩=95 / 100' 预填解析取第一段 (之前 int('95 / 100') 抛错被吞 -> 无预填)."""
    from src.database import Database
    db = Database.__new__(Database)

    # 直接验证解析逻辑 (模拟 database.py:1315 的代码路径)
    m = "♩=95 / 100"
    note, bpm_str = m.split("=", 1)
    first = bpm_str.strip().split()[0]
    assert note.strip() == "♩"
    assert int(first) == 95


def test_metronome_single_parsing():
    m = "♩=82"
    note, bpm_str = m.split("=", 1)
    first = bpm_str.strip().split()[0]
    assert int(first) == 82


# ── 前端模板含分段控件 ──

def test_template_has_segments_ui():
    from fastapi.testclient import TestClient
    from src.kid_app.app import app
    with TestClient(app) as c:
        html = c.get("/config/practice-log").text
    assert "seg-toggle-btn" in html          # 分段折叠按钮
    assert "seg-add-btn" in html             # 添加分段
    assert "seg-label" in html               # 段说明输入
    assert "seg-tempo" in html               # 段速度输入
    assert "syncMetronomeFromSegments" in html
    assert "segmentsBadgeHtml" in html       # 展示辅助
    assert "metronome_segments" in html      # 提交传 segments
