"""
P2-6 / 任务 E：`/config/api/badge/*` 全量服务端鉴权收口 + 鉴权前置回归锁。

背景（dad 已批 B 扩围）：
  这批端点历史落在 `/config/api/` 公开白名单里，服务端不验身份，只靠 config 页
  localStorage 的 PIN 门。实测（扩围前）：匿名 DELETE 草稿返 200、匿名能列 discoveries、
  匿名能读全量 card-appearance。本文件把它们钉在 401 上。

锁定内容：
  1. 13 个端点匿名一律 401，且响应体不泄漏表名 / SQL / 堆栈
  2. 假 token 一律 401（机器通道不能被伪造头骗过）
  3. 真 token 不被 401（业务错可以：400/404 都算通过鉴权）
  4. [任务 C] POST manual 匿名空 body 必须 401 —— 不许退化回 422（鉴权必须早于 body 校验）
  5. [任务 D] DB 不可用时 503 固定文案，原始异常不外泄
"""
from __future__ import annotations

import pytest

# (method, path, 需要 body 的 JSON)
ENDPOINTS = [
    ("post", "/config/api/badge/draft", {}),
    ("get", "/config/api/badge/draft/probe-none", None),
    ("post", "/config/api/badge/commit-from-draft", {}),
    ("post", "/config/api/badge/replace-image-from-draft", {}),
    ("delete", "/config/api/badge/draft/probe-none", None),
    ("post", "/config/api/badge/ai-draft", {}),
    ("post", "/config/api/badge/ai-cond", {}),
    ("get", "/config/api/badge/discoveries", None),
    ("get", "/config/api/badge/draft-image?draft_id=probe-none", None),
    ("get", "/config/api/badge/card-appearance", None),
    ("post", "/config/api/badge/card-appearance", {}),
    ("get", "/config/api/badge/manual", None),
    ("post", "/config/api/badge/manual/tech_hua_yin", {"action": "award", "achieved_date": "2026-10-01"}),
]

LEAK_MARKERS = ("select ", "insert ", "achievement_stats", "achievement_badges",
                "traceback", "pymysql", "sqlite", "table '", "unique constraint")


def _call(client, method, path, body, headers=None):
    kw = {}
    if body is not None:
        kw["json"] = body
    if headers:
        kw["headers"] = headers
    return getattr(client, method)(path, **kw)


def _assert_no_leak(text: str):
    low = text.lower()
    hit = [m for m in LEAK_MARKERS if m in low]
    assert not hit, f"响应体泄漏敏感信息: {hit} | body={text[:300]}"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from src.kid_app.app import app
    return TestClient(app)


@pytest.mark.parametrize("method,path,body", ENDPOINTS,
                         ids=[f"{m.upper()} {p.split('?')[0]}" for m, p, _ in ENDPOINTS])
def test_anonymous_is_401(client, method, path, body):
    """13 个端点匿名一律 401（扩围前它们返 200/422/404，等于没有服务端鉴权）。"""
    r = _call(client, method, path, body)
    assert r.status_code == 401, f"{method.upper()} {path} 期望 401, 实得 {r.status_code}"
    _assert_no_leak(r.text)


@pytest.mark.parametrize("method,path,body", ENDPOINTS,
                         ids=[f"{m.upper()} {p.split('?')[0]}" for m, p, _ in ENDPOINTS])
def test_fake_token_is_401(client, method, path, body, monkeypatch):
    """机器通道不能被伪造头骗过。"""
    monkeypatch.setenv("BADGE_PUSH_TOKEN", "the-real-token")
    r = _call(client, method, path, body, headers={"X-Badge-Push-Token": "not-the-token"})
    assert r.status_code == 401, f"{method.upper()} {path} 假 token 竟拿到 {r.status_code}"


@pytest.mark.parametrize("method,path,body", ENDPOINTS,
                         ids=[f"{m.upper()} {p.split('?')[0]}" for m, p, _ in ENDPOINTS])
def test_real_token_passes_auth(client, method, path, body, monkeypatch):
    """真 token 必须过鉴权关（业务校验错 400/404/409 都算通过）。"""
    monkeypatch.setenv("BADGE_PUSH_TOKEN", "the-real-token")
    r = _call(client, method, path, body, headers={"X-Badge-Push-Token": "the-real-token"})
    assert r.status_code != 401, f"{method.upper()} {path} 真 token 仍被 401"


def test_manual_post_empty_body_is_401_not_422(client):
    """[任务 C] 鉴权必须早于 Pydantic **字段**校验。

    扩围前：匿名空 body → 422，detail 里直接暴露 `action` 字段名；带合法 body 才 401。
    修后：无 body / 空 JSON → 401。

    残留（已知且接受）：`Content-Type: application/json` 但内容不是合法 JSON 时，
    FastAPI 在解析阶段就返 422 `json_invalid` —— 这一步发生在依赖之前，属框架行为。
    判据：该 422 不得暴露任何字段名（action / achieved_date / pin）。
    """
    path = "/config/api/badge/manual/tech_hua_yin"
    for kwargs in ({}, {"json": {}}):
        r = client.post(path, **kwargs)
        assert r.status_code == 401, f"匿名 {kwargs} 期望 401, 实得 {r.status_code}: {r.text[:200]}"
        _assert_no_leak(r.text)

    r = client.post(path, content=b"not-json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    for field in ("action", "achieved_date", "pin"):
        assert field not in r.text, f"畸形 JSON 的 422 泄漏了字段名 {field!r}: {r.text[:200]}"
    _assert_no_leak(r.text)


def test_db_failure_503_has_no_raw_exception(client, monkeypatch):
    """[任务 D] DB 建连失败 → 503 固定文案，不许把异常原文拼给前端。"""
    monkeypatch.setenv("BADGE_PUSH_TOKEN", "the-real-token")

    def _boom():
        raise RuntimeError("secret-host-10.0.0.9 pymysql 1045 access denied")

    import src.db_adapter as db_adapter
    monkeypatch.setattr(db_adapter, "get_conn", _boom)

    r = client.post(
        "/config/api/badge/manual/tech_hua_yin",
        json={"action": "award", "achieved_date": "2026-10-01"},
        headers={"X-Badge-Push-Token": "the-real-token"},
    )
    assert r.status_code == 503, f"期望 503, 实得 {r.status_code}: {r.text[:200]}"
    body = r.text
    for bad in ("secret-host", "10.0.0.9", "pymysql", "access denied", "RuntimeError"):
        assert bad not in body, f"503 响应体泄漏了 {bad!r}: {body[:300]}"
    assert "数据库不可用" in body
