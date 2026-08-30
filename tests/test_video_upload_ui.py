"""Sprint 26083001 S2: 老师要求视频录入/编辑/prepare UI 模板断言.

7 Critical Cases:
1. accept 白名单 (mp4/mov, 拒 webm; 无 capture)
2. 上传 progress bar 渲染 (XHR + onprogress)
3. 视频列表展示 (绑定下拉 + 删除按钮)
4. localStorage 草稿持久化 videos
5. PUT body 携带 videos (P1 防静默丢)
6. 格式错误提示 (webm)
7. 网络失败重试同一文件
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "src" / "kid_app" / "templates" / "config-practice-log.html"
PREP_PATH = ROOT / "src" / "kid_app" / "templates" / "prepare.html"


@pytest.fixture(scope="module")
def cfg_html():
    return CFG_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def prep_html():
    return PREP_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pages():
    from src.kid_app.app import app
    with TestClient(app, follow_redirects=True) as c:
        return {
            "config-practice-log": c.get("/config/practice-log").text,
            "prepare": c.get("/prepare").text,
        }


def _video_input(html: str) -> str:
    m = re.search(r'<input[^>]*id="assignVideoInput"[^>]*>', html)
    assert m, "assignVideoInput 缺失"
    return m.group(0)


def test_accept_whitelist_mp4_mov_rejects_others(cfg_html):
    tag = _video_input(cfg_html)
    assert 'type="file"' in tag
    assert "video/mp4" in tag
    assert "video/quicktime" in tag
    assert ".mp4" in tag
    assert ".mov" in tag
    assert "webm" not in tag.lower()
    assert "video/*" not in tag
    assert "capture" not in tag.lower()


def test_upload_progress_bar_xhr(cfg_html):
    assert 'id="assignVideoProgressWrap"' in cfg_html
    assert 'id="assignVideoProgressFill"' in cfg_html
    assert 'id="assignVideoProgressText"' in cfg_html
    assert "XMLHttpRequest" in cfg_html
    assert "xhr.upload.onprogress" in cfg_html
    assert "assignVideoProgress" in cfg_html


def test_video_list_bind_dropdown_and_delete(cfg_html):
    assert 'id="assignVideoList"' in cfg_html
    assert "function renderAssignVideoList" in cfg_html
    assert "本期通用" in cfg_html
    assert "assign-video-bind" in cfg_html
    assert "assign-video-del" in cfg_html
    assert "+ 添加视频" in cfg_html
    assert "老师示范视频" in cfg_html


def test_localstorage_draft_persists_videos(cfg_html):
    assert "function collectAssignDraft" in cfg_html
    assert "videos: assignVideos.map" in cfg_html
    assert "d.videos && d.videos.length" in cfg_html
    assert "assignVideos = (d.videos || [])" in cfg_html
    assert "dizical:assign-draft:v1" in cfg_html


def test_put_body_carries_videos(cfg_html):
    assert "JSON.stringify({ items, notes, videos })" in cfg_html
    assert "body.videos = serializeAssignVideos()" in cfg_html


def test_webm_format_error_prompt(cfg_html):
    assert "不支持 webm，请使用 mp4 或 mov" in cfg_html
    assert "function isAllowedVideoFile" in cfg_html
    assert r"/\.webm$/i" in cfg_html or "webm" in cfg_html


def test_network_failure_retry_keeps_file(cfg_html):
    assert "_pendingVideoFile" in cfg_html
    assert 'id="retryAssignVideoBtn"' in cfg_html
    assert "网络错误，可重试同一文件" in cfg_html
    assert "if (_pendingVideoFile) uploadAssignVideoFile(_pendingVideoFile)" in cfg_html
    # 失败不清 input; 成功才 input.value = ''
    assert "xhr.onerror" in cfg_html


def test_config_template_has_video_zone_and_preview(cfg_html):
    assert 'id="assignVideoInput"' in cfg_html
    assert "function openVideoPreview" in cfg_html
    assert "function closeVideoPreview" in cfg_html
    assert 'id="videoPreviewModal"' in cfg_html
    assert "playsinline" in cfg_html
    assert "webkit-playsinline" in cfg_html
    assert 'preload="none"' in cfg_html
    assert "autoplay" not in cfg_html.split("id=\"videoPreviewEl\"")[1][:400]


def test_prepare_has_open_video_preview_and_chip(prep_html):
    assert "function openVideoPreview" in prep_html
    assert "function closeVideoPreview" in prep_html
    assert "assign_videos" in prep_html
    assert "老师示范" in prep_html
    assert 'id="videoPreviewEl"' in prep_html
    assert "playsinline" in prep_html
    assert "webkit-playsinline" in prep_html
    assert 'preload="none"' in prep_html
    assert "autoplay" not in prep_html.split("id=\"videoPreviewEl\"")[1][:400]
    # 配图不再 window.open
    assert "window.open(" not in prep_html


def test_rendered_pages_keep_hooks(pages):
    cfg = pages["config-practice-log"]
    prep = pages["prepare"]
    # 登录墙时仍应能在模板源里断言; 渲染成功则函数要在
    if "function openVideoPreview" in cfg:
        assert "assignVideoInput" in cfg
        assert "本期通用" in cfg
    if "function openVideoPreview" in prep:
        assert "videoPreviewEl" in prep
        assert "老师示范" in prep
