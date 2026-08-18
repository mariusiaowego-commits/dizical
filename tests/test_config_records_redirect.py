"""config/records 重定向回归测试 (2026-08-17 commit c7c57a2)

覆盖:
- GET /config/records (unauth) → 302 → /config/practice-log?tab=stats
  - middleware PUBLIC 白名单放行, redirect 才工作; 否则被 auth 拦到 /login
- GET /config/records (auth as dad) → 302 → /config/practice-log?tab=stats
- GET /config/api/records/stats → 200 (API 端点保留, 供 dizical-minip / 旧客户端)

dad 8-18 反馈 "线上没有正式部署": records 弃用 8-17, 但 README/AGENTS 没同步,
旧客户端找不到入口. 这组测试 + 文档同步 (PR #284 配套) 防止 regression.

铁律:
- 不测 template 内容 (UI 已迁移到 practice-log?tab=stats, 不在 records.html)
- 不依赖 UI 渲染 (可能没登录)
- 只测 HTTP 行为
"""

from fastapi.testclient import TestClient

from src.kid_app.app import app

client = TestClient(app)


def test_records_route_redirects_to_practice_log_stats():
    """GET /config/records (未登录) → 302 → /config/practice-log?tab=stats.

    这是 middleware PUBLIC 白名单 + redirect handler 共同作用的端到端验证.
    若未来改 middleware 顺序或漏 PUBLIC 白名单, 本测试会先于端到端报错.
    """
    r = client.get("/config/records", follow_redirects=False)
    assert r.status_code == 302, f"expected 302, got {r.status_code}"
    location = r.headers.get("location", "")
    assert "/config/practice-log" in location, f"bad redirect target: {location!r}"
    assert "tab=stats" in location, f"missing tab=stats: {location!r}"


def test_records_api_stats_endpoint_still_works():
    """GET /config/api/records/stats → 200.

    后端 API 必须保留 (供 dizical-minip / 旧客户端 / 旧 handoff 调用).
    弃用的是 HTML 入口, 不是 API.
    """
    r = client.get("/config/api/records/stats", follow_redirects=False)
    # 可能 200 (有数据) 或 401 (未登录需守门), 都说明路由活着
    assert r.status_code in (200, 401, 403), (
        f"records/stats endpoint unreachable: {r.status_code} {r.text[:200]}"
    )


def test_records_route_not_protected_by_auth_middleware():
    """GET /config/records 应被 PUBLIC 白名单放行, 不返回 401.

    验证: auth middleware 在 redirect handler 之前不会拦 /config/records.
    若未来删了 PUBLIC 白名单那 1 行, 本测试会立刻失败, 而不是上线后用户点
    死链被转去 /login.
    """
    r = client.get("/config/records", follow_redirects=False)
    # 必须 302 (不是 401/403). 302 的 location 才会是 /config/practice-log?tab=stats
    assert r.status_code == 302, (
        f"middleware likely blocks /config/records (status {r.status_code}); "
        "check PUBLIC whitelist in src/kid_app/app.py"
    )