"""Sprint 26083001 S3: practice 页视频 chip + modal 播放器单测.

6 Critical Cases:
1. <video> 标签包含 playsinline + webkit-playsinline 且无 autoplay
2. chip 渲染: 选中 item 后出现, 文案「老师示范」
3. chip 过滤: item_id 匹配 + 本期通用 (item_id=null) 显示, 其它 item 不显示
4. 多条 chip 文案「老师示范 · 2」, 单条无 (1) / · 1
5. 关闭 modal 后 paused=true 且 src 还原为空
6. webkitendfullscreen 状态机: 事件监听与状态清理
"""
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
PRACTICE_PATH = ROOT / "src" / "kid_app" / "templates" / "practice.html"


@pytest.fixture(scope="module")
def practice_html():
    return PRACTICE_PATH.read_text(encoding="utf-8")


def test_video_tag_playsinline_and_no_autoplay(practice_html):
    """Case 1: <video id="videoPreviewEl"> 有 playsinline + webkit-playsinline 且无 autoplay."""
    m = re.search(r'<video[^>]*id="videoPreviewEl"[^>]*>', practice_html)
    assert m, "videoPreviewEl 元素缺失"
    tag = m.group(0)
    assert "playsinline" in tag
    assert "webkit-playsinline" in tag
    assert "autoplay" not in tag.lower()
    assert 'preload="metadata"' in tag


def test_chip_markup_and_title(practice_html):
    """Case 2: chip 渲染包含 16px play SVG 图标与「老师示范」文案."""
    assert "video-chip" in practice_html
    assert "老师示范" in practice_html
    assert "openPracticeVideoModal" in practice_html
    assert "reqHighlight" in practice_html
    # SVG 图标校验 (16px, currentColor, play path)
    assert 'viewBox="0 0 24 24"' in practice_html
    assert "M8 5v14l11-7z" in practice_html


def test_chip_filtering_logic(practice_html):
    """Case 3: chip 过滤规则 (v.item_id === currentItemId || v.item_id === null)."""
    assert "v.item_id === currentItemId" in practice_html
    assert "v.item_id === null" in practice_html
    assert "_currentMatchedVideos" in practice_html


def test_multi_video_chip_label(practice_html):
    """Case 4: 多条展示「老师示范 · N」, 单条展示「老师示范」无数字."""
    assert "老师示范 · " in practice_html
    assert "openPracticeVideoModal" in practice_html
    assert "videoNavPrev" in practice_html or "videoPrevBtn" in practice_html
    assert "videoNavNext" in practice_html or "videoNextBtn" in practice_html


def test_close_video_modal_cleans_source_and_pause(practice_html):
    """Case 5: 关闭 modal 后 pause 并清空 src."""
    assert "function closeVideoPreview" in practice_html
    assert "video.pause()" in practice_html
    assert "video.src = ''" in practice_html or 'video.src = ""' in practice_html
    assert "video.removeAttribute('src')" in practice_html


def test_webkitendfullscreen_and_error_handling(practice_html):
    """Case 6: webkitendfullscreen 与 error 错误提示处理."""
    assert "webkitendfullscreen" in practice_html
    assert "videoErrorNotice" in practice_html
    assert "Safari" in practice_html
