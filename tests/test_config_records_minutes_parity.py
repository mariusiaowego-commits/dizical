"""sprint 26100101 F6 锁：两个写入口的「分钟」必须同口径。

改前：`/api/log` 用服务端 `write_minutes(minutes, seconds)` = ceil(秒/60)，
而 `/config/api/records` 沿用客户端 minutes，只把 total_seconds 服务端求和
→ 同一次练习两入口写出的分钟不同，下游按分钟做的阈值（徽章/打卡）跟着漂。

另外：`database.save_daily_practice` 的**新建当天**路径直接用传入 total（database.py:1051），
所以 config 入口传错合计会被永久写库 —— 本文件也锁这一条。

负控（人工验证过）：
- 注掉 config.py 的 `it['minutes'] = write_minutes(...)` → test_item_minutes_match_api_log_and_config 红（1 vs 2）
- 合计改回 `total_minutes if total_minutes else sum(...)` → test_wrong_client_total_is_ignored 红（99 vs 2）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kid_app.app import app as fastapi_app  # noqa


@pytest.fixture
def client(monkeypatch):
    async def _mock_user(*args, **kwargs):
        return {"id": 1, "username": "dad", "role": "dad"}
    monkeypatch.setattr("src.kid_app.auth.get_current_user", _mock_user)
    return TestClient(fastapi_app)


@pytest.fixture
def captured(monkeypatch):
    """在 Database 类上截存储层入参 —— config 与 app 是同一个 db 单例，
    且 config 全 kwargs / app 走位置参数，所以按位置名 + kwargs 合并记录。"""
    box = {"calls": [], "session": []}

    from src.database import Database

    names = ["date", "items", "total_minutes", "log", "practiced", "channel", "method", "practice_at"]

    def fake_save(*args, **kwargs):
        argv = args[1:]                 # 类属性打桩后实例访问会绑 self，先去掉
        rec = {n: v for n, v in zip(names, argv)}
        rec.update(kwargs)
        box["calls"].append(rec)

    def fake_session(*args, **kwargs):
        argv = args[1:]                 # 去掉 self
        box["session"].append({
            "minutes": argv[3] if len(argv) > 3 else kwargs.get("minutes"),
            "seconds": kwargs.get("seconds"),
        })
        return {"id": 1}

    monkeypatch.setattr(Database, "save_daily_practice", fake_save)
    monkeypatch.setattr(Database, "save_practice_session_and_daily_summary", fake_session)
    monkeypatch.setattr(Database, "get_daily_practice", lambda self, d: None)
    monkeypatch.setattr(Database, "append_behavior_log", lambda self, *a, **k: None)
    return box


def _records_body(**over):
    body = {
        "date": "2099-07-01",
        "items": [{"item": "长音", "item_id": 3, "minutes": 1, "seconds": 90}],
        "total_minutes": 0,
    }
    body.update(over)
    return body


def test_item_minutes_match_api_log_and_config(client, captured):
    """同 (minutes=1, seconds=90)：两入口落库分钟都必须是 2。"""
    r1 = client.post("/config/api/records", json=_records_body())
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/log", json={
        "date": "2099-07-02", "item": "长音", "item_id": 3, "minutes": 1, "seconds": 90,
    })
    assert r2.status_code == 200, r2.text

    cfg_item = captured["calls"][0]["items"][0]["minutes"]
    app_item = captured["calls"][1]["items"][0]["minutes"]
    assert cfg_item == 2, f"config 入口分钟没按秒派生（实际 {cfg_item}）"
    assert app_item == 2, f"/api/log 入口分钟（实际 {app_item}）"
    assert cfg_item == app_item


def test_wrong_client_total_is_ignored(client, captured):
    """客户端传错合计 99 → 落库合计必须是派生和 2（新建当天会被直接写库）。"""
    r = client.post("/config/api/records", json=_records_body(total_minutes=99))
    assert r.status_code == 200, r.text
    saved = captured["calls"][0]
    assert saved["total_minutes"] == 2, f"错合计被采信（实际 {saved['total_minutes']}）"
    assert saved["items"][0]["minutes"] == 2


def test_self_consistent_minutes_untouched(client, captured):
    """没带秒的自洽输入不被改动：3 分钟 → 3。"""
    r = client.post("/config/api/records", json={
        "date": "2099-07-03",
        "items": [{"item": "长音", "item_id": 3, "minutes": 3}],
        "total_minutes": 3,
    })
    assert r.status_code == 200, r.text
    saved = captured["calls"][0]
    assert saved["items"][0]["minutes"] == 3
    assert saved["items"][0]["seconds"] == 180
    assert saved["total_minutes"] == 3


def test_session_branch_also_derives_minutes(client, captured):
    """session 分支（带齐 tempo 三字段）同样按秒派生分钟。"""
    r = client.post("/config/api/records", json=_records_body(
        tempo_note="♪", tempo_bpm=80, content="第一分句",
    ))
    assert r.status_code == 200, r.text
    assert captured["session"][0]["minutes"] == 2
    assert captured["session"][0]["seconds"] == 90


def test_multi_item_total_is_sum_of_derived(client, captured):
    """多条：10 秒 + 50 秒 = 派生 1 + 1 = 2（不是客户端合计）。"""
    r = client.post("/config/api/records", json={
        "date": "2099-07-04",
        "items": [
            {"item": "长音", "item_id": 3, "minutes": 1, "seconds": 10},
            {"item": "吐音", "item_id": 4, "minutes": 1, "seconds": 50},
        ],
        "total_minutes": 0,
    })
    assert r.status_code == 200, r.text
    saved = captured["calls"][0]
    assert [it["minutes"] for it in saved["items"]] == [1, 1]
    assert saved["total_minutes"] == 2
