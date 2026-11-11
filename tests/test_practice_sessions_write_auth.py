"""practice_sessions 写接口鉴权：匿名只读，写入只给 student/dad。

回归点（v3.51）：白名单曾写成 `path.startswith("/api/practice-sessions")`，
PUT/DELETE 也被当成公开路径直接放行，中间件里的 student/dad 角色检查
完全够不到 —— 匿名请求能直接进到真写逻辑（生产实测 DELETE 不存在的 id
返回 404 业务错误，而不是 401）。
"""
import pytest
from fastapi.testclient import TestClient

from src.kid_app.app import app


def _request(method, session_id=999999):
    body = {"content": "probe"} if method == "PUT" else None
    return TestClient(app).request(method, f"/api/practice-sessions/{session_id}", json=body)


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_anonymous_write_rejected_401(method):
    r = _request(method)
    assert r.status_code == 401, r.text
    assert r.json()["ok"] is False


@pytest.mark.parametrize("role", ["guest", "family", "reviewer"])
@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_non_writer_roles_forbidden_403(auth_as, role, method):
    auth_as(role)
    r = _request(method)
    assert r.status_code == 403, r.text
    assert r.json()["ok"] is False


@pytest.mark.parametrize("role", ["student", "dad"])
@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_writer_roles_reach_endpoint(auth_as, role, method):
    """过鉴权后落在「session 不存在」：用不存在的 id 断言，避免真写库。"""
    auth_as(role)
    r = _request(method)
    # 404 = DELETE 的 not-found；400 = PUT 端点历史上把 ValueError 统一映射成 400。
    assert r.status_code in (400, 404), r.text
    assert "不存在" in r.json()["error"]


def test_get_stays_public():
    r = TestClient(app).get("/api/practice-sessions/2026-01-01")
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
