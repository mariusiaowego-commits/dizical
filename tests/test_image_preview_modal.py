"""回归测试: 配图预览 modal (2026-08-09 需求6).

背景: 点击配图 window.open 在 Chrome 对 COS 图片 URL 触发下载 (dad 反馈).
改 openImagePreview(url) modal — 全屏遮罩 + 居中大图 + 关闭按钮.

本测试渲染两个模板页面, 断言:
1. openImagePreview / closeImagePreview 函数存在
2. imagePreviewModal 容器存在
3. 配图点击不再用 window.open (onclick 改 openImagePreview)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(scope="module")
def pages():
    """渲染两个模板, 返回 {name: html}."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    with TestClient(app) as c:
        return {
            "config-practice-log": c.get("/config/practice-log").text,
            "practice": c.get("/practice").text,
        }


def test_config_practice_log_has_modal(pages):
    html = pages["config-practice-log"]
    assert "imagePreviewModal" in html
    assert "function openImagePreview" in html
    assert "function closeImagePreview" in html
    assert "imagePreviewImg" in html


def test_practice_has_modal(pages):
    html = pages["practice"]
    assert "imagePreviewModal" in html
    assert "function openImagePreview" in html
    assert "function closeImagePreview" in html
    assert "imagePreviewImg" in html


def test_no_window_open_for_images(pages):
    """配图点击不能用 window.open (会触发下载)."""
    for name, html in pages.items():
        assert "window.open('" not in html, f"{name} 仍有 window.open 配图点击"
        assert "window.open(`" not in html, f"{name} 仍有 window.open 配图点击"
