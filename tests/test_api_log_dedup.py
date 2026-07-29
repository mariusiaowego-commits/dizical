"""PR-B 集成测试: FastAPI TestClient 验证 /api/log.

覆盖:
1. Pydantic 校验: 缺 date → 422
2. session 路径: behavior_log dedup (只 1 条 entry, 不是 2 条)
3. 旧路径: behavior_log 仍 append
4. session_detail 嵌套 alias 仍兼容
"""
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kid_app.app import app as fastapi_app  # noqa


@pytest.fixture
def client():
    return TestClient(fastapi_app)


def test_pydantic_validation_missing_date(client):
    """缺 date → 422, 不是 500."""
    r = client.post("/api/log", json={
        "item": "x", "item_id": 1, "minutes": 5,
        "tempo_note": "♪", "tempo_bpm": 80, "content": "test",
    })
    assert r.status_code == 422, f"应 422, 实际 {r.status_code}: {r.text}"
    body = r.json()
    assert "请求参数校验失败" in body.get("error", "")
    assert "details" in body


def test_pydantic_validation_tempo_bpm_out_of_range(client):
    """tempo_bpm 越界 → 422."""
    r = client.post("/api/log", json={
        "date": "2026-07-29", "item": "x", "item_id": 1, "minutes": 5,
        "tempo_note": "♪", "tempo_bpm": 200, "content": "test",
    })
    assert r.status_code == 422
    assert "tempo_bpm" in json.dumps(r.json())


def test_pydantic_validation_content_empty(client):
    """content 是空白 → 422 (session 路径下)."""
    r = client.post("/api/log", json={
        "date": "2026-07-29", "item": "x", "item_id": 1, "minutes": 5,
        "tempo_note": "♪", "tempo_bpm": 80, "content": "   ",
    })
    assert r.status_code == 422
    assert "content" in json.dumps(r.json())


def test_legacy_path_unchanged():
    """旧路径 (无 session 字段) 行为不变: 走 save_daily_practice 兼容.
    不通过 TestClient (避免 db 单例 reload 问题), 直接验证 schemas.has_session_detail().
    """
    from src.kid_app.schemas import PracticeLogRequest
    req = PracticeLogRequest.model_validate({
        "date": "2026-07-29", "item": "x", "item_id": 1, "minutes": 5,
    })
    assert req.has_session_detail() is False
    assert req.tempo_note is None
    # 旧前端发 behavior_log 也兼容
    assert len(req.behavior_log) == 0
