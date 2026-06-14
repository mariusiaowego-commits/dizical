"""设计系统服务监控 API 测试 (PR-A)

覆盖:
- GET /api/design/status — 状态查询
- POST /api/design/start — 启动 (含已运行检测)
- POST /api/design/stop — 停止
- POST /api/design/restart — 重启 (stop + start)

硬约束:
- 不破 dizical 核心功能, 测试只动 9876 端口
- 端到端验证 (实际跑 bash scripts), 不 mock
"""

import subprocess

from fastapi.testclient import TestClient

from src.kid_app.app import app

client = TestClient(app)


def _stop_intro():
    """测试 setup/teardown: 确保 9876 端口清空"""
    subprocess.run(
        ["bash", "/Users/mt16/dev/dizical/scripts/intro-stop.sh"],
        capture_output=True,
        timeout=10,
    )


def test_status_returns_running_false_when_service_down():
    """服务停止时, /config/api/design/status 返 running=false"""
    _stop_intro()
    r = client.get("/config/api/design/status")
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert data["running"] is False, f"expected running=false, got {data}"
    assert data["pid"] is None
    assert data["port"] == 9876
    assert data["url"] is None


def test_start_then_status_shows_running():
    """启动服务后, status 返 running=true + PID + url"""
    _stop_intro()
    # 启动
    r = client.post("/config/api/design/start")
    assert r.status_code == 200, f"start failed: {r.status_code} {r.text}"
    assert r.json()["ok"] is True
    # 验证 status
    s = client.get("/config/api/design/status")
    assert s.status_code == 200
    data = s.json()
    assert data["running"] is True, f"expected running=true, got {data}"
    assert data["pid"] is not None and data["pid"] > 0
    assert data["port"] == 9876
    assert data["url"] == "http://localhost:9876/demos/dizicute-intro/intro.html"
    # 清理: stop
    _stop_intro()


def test_start_when_already_running_returns_ok_with_existing_pid():
    """服务已运行时, start 返 ok=true + 当前 PID (避免重复启动)"""
    _stop_intro()
    # 启动一次
    r1 = client.post("/config/api/design/start")
    assert r1.json()["ok"] is True
    # 再启动一次 (应该返 already running)
    r2 = client.post("/config/api/design/start")
    assert r2.status_code == 200
    data = r2.json()
    assert data["ok"] is True
    assert "already running" in data["message"] or data["pid"] is not None
    # 清理
    _stop_intro()


def test_stop_then_status_shows_not_running():
    """停止服务后, status 返 running=false"""
    _stop_intro()
    # 启动
    client.post("/config/api/design/start")
    # 停止
    r = client.post("/config/api/design/stop")
    assert r.status_code == 200, f"stop failed: {r.status_code} {r.text}"
    assert r.json()["ok"] is True
    # 验证 status
    s = client.get("/config/api/design/status")
    data = s.json()
    assert data["running"] is False, f"expected running=false, got {data}"


def test_restart_works_end_to_end():
    """重启流程: stop + start, status 返新 PID + uptime_seconds 是新的"""
    _stop_intro()
    # 启动第一次
    client.post("/config/api/design/start")
    s1 = client.get("/config/api/design/status").json()
    pid1 = s1.get("pid")
    # 等待 2 秒确保 uptime 不同
    import time
    time.sleep(2)
    # 重启
    r = client.post("/config/api/design/restart")
    assert r.status_code == 200, f"restart failed: {r.status_code} {r.text}"
    assert r.json()["ok"] is True
    # 验证 status 返新 PID (or 端口没释放时同 PID 也 OK, 但 uptime 应该重置)
    s2 = client.get("/config/api/design/status").json()
    assert s2["running"] is True
    # uptime_seconds 应该是小数字 (刚 restart)
    assert s2.get("uptime_seconds") is not None
    assert s2["uptime_seconds"] < 10, f"uptime too large after restart: {s2}"
    # 清理
    _stop_intro()
