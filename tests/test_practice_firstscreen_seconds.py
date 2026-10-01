"""sprint 26100101 F2 锁：practice 首屏「今日已练习」与保存后同口径（口径 B，用秒）。

改前首屏渲染 `{{today_mins}} 分钟`（例：90 秒 → "2 分钟"），保存后 JS 却写
`DizicalDur.fmt(todaySec)`（"1分30秒"）→ 同页两处口径不一致。

负控（人工验证过）：把 app.py 的 `today_text` 换回 `today_mins` + " 分钟" 模板 → 红（找不到 "1分30秒"）。
"""
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


def _patch_today(monkeypatch, items, total_minutes):
    monkeypatch.setattr(
        "src.kid_app.app.db.get_daily_practice",
        lambda day: {"total_minutes": total_minutes, "items": items},
    )


def test_firstscreen_uses_seconds_rule_b(client, monkeypatch):
    """90 秒 → 首屏必须是 "1分30秒"（旧文案是 "2 分钟"）。"""
    _patch_today(monkeypatch, [{"item": "长音", "item_id": 3, "minutes": 1, "seconds": 90}], 2)
    r = client.get("/practice")
    assert r.status_code == 200, r.text
    html = r.text
    assert "今日已练习: 1分30秒" in html, "首屏未用秒口径"
    assert "今日已练习: 2 分钟" not in html, "旧格式还在"


def test_firstscreen_empty_day(client, monkeypatch):
    _patch_today(monkeypatch, [], 0)
    r = client.get("/practice")
    assert r.status_code == 200
    assert "今日已练习: 0分" in r.text


def test_mobile_topbar_injects_seconds_and_uses_them_directly(client, monkeypatch):
    """移动端注入秒值，且不得再 ×60（防"注入秒却按分钟换算"）。"""
    _patch_today(monkeypatch, [{"item": "长音", "item_id": 3, "minutes": 1, "seconds": 90}], 2)
    html = client.get("/practice").text
    assert "var ts = parseInt('90')" in html, "移动端注入的不是秒"
    assert "DizicalDur.fmt(ts)" in html, "移动端未按秒格式化"
    assert "ts * 60" not in html, "移动端又把秒乘了 60"
    assert "today_mins" not in html, "模板仍在读分钟"
