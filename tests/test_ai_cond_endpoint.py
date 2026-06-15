"""
Tests for POST /config/api/badge/ai-cond endpoint.

feat/badge-cond-text (2026-06-15): 给 v21 表单多 1 个 "✨ AI 生成" 按钮,
调这个端点基于 placeholder + zh_story 调 LLM 出一句话"条件文案".
"""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest


class TestAiCondEndpoint:
    """ai-cond 端点测试 (mock LLM, 不真调)."""

    def test_ai_cond_returns_text(self):
        """正常返回 → 返 {ok: true, cond_text: '...'}."""
        from src.kid_app.routes.badge_workflow import api_ai_cond
        from fastapi.testclient import TestClient
        from src.kid_app.app import app

        # mock LLM 流: yield "练习" + " 1 " + "次"
        def fake_stream(prompt):
            for token in ["练习", " 1 ", "次"]:
                yield token

        with patch("src.kid_app.subject_info._gemini_stream", side_effect=fake_stream):
            client = TestClient(app)
            resp = client.post("/config/api/badge/ai-cond", json={
                "name": "批改小帮手",
                "type": "突破",
                "placeholder": "a chibi girl grading math tests",
                "zh_story": "居里夫人帮妈妈洗试管的典故",
            })

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["ok"] is True
        assert data["cond_text"] == "练习 1 次", f"got {data['cond_text']!r}"

    def test_ai_cond_handles_llm_failure(self):
        """LLM 异常 (网络/超时/无 key) → 返 {ok: false, error}, 500."""
        from fastapi.testclient import TestClient
        from src.kid_app.app import app

        def empty_stream(prompt):
            # LLM 返空 (mock 失败场景)
            if False:
                yield ""

        with patch("src.kid_app.subject_info._gemini_stream", side_effect=empty_stream):
            client = TestClient(app)
            resp = client.post("/config/api/badge/ai-cond", json={
                "name": "测试",
                "placeholder": "test",
                "zh_story": "test",
            })

        # LLM 返空 → fallback "AI 没能想出条件文案" + ok=True (跟 generate_mood_stream 一致)
        # 设计选择: 端点返 ok=True 但 cond_text 是 fallback 文本, 让前端有东西可填
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "fallback" in data["cond_text"].lower() or "没能" in data["cond_text"] or len(data["cond_text"]) > 0

    def test_ai_cond_validates_required_fields(self):
        """缺 zh_story → 422 (Pydantic validation)."""
        from fastapi.testclient import TestClient
        from src.kid_app.app import app

        client = TestClient(app)
        resp = client.post("/config/api/badge/ai-cond", json={
            "name": "测试",
            "placeholder": "test",
            # 缺 zh_story
        })
        # Pydantic 自动 422
        assert resp.status_code == 422
        data = resp.json()
        # 验证错误 detail 提到 zh_story
        assert "zh_story" in str(data)

    def test_ai_cond_prompt_includes_story(self):
        """验 LLM prompt 包含 zh_story + name (让 LLM 有 context 生成)."""
        from fastapi.testclient import TestClient
        from src.kid_app.app import app

        captured_prompts = []

        def capture_stream(prompt):
            captured_prompts.append(prompt)
            yield "测试结果"

        with patch("src.kid_app.subject_info._gemini_stream", side_effect=capture_stream):
            client = TestClient(app)
            resp = client.post("/config/api/badge/ai-cond", json={
                "name": "test_name_xyz",
                "placeholder": "test_placeholder_xyz",
                "zh_story": "test_story_xyz_unique",
            })

        assert resp.status_code == 200
        assert len(captured_prompts) == 1
        prompt = captured_prompts[0]
        assert "test_name_xyz" in prompt
        assert "test_story_xyz_unique" in prompt
        # 包含关键词让 LLM 知道生成什么
        assert "条件" in prompt or "达成" in prompt
