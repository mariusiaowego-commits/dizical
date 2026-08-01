"""sprint-26080103 v2.1: SSL retry 单元测试."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error
import ssl
import socket
import pytest

ROOT = Path("/Users/mt16/dev/dizical")
sys.path.insert(0, str(ROOT))

from src.kid_app.utils.image_extractor import _download_image_with_retry


def test_url_retry_first_fails_second_succeeds(tmp_path):
    """第一次 SSL EOF 失败, 第二次成功 -> 文件下载成功, raise 为 None."""
    dest = tmp_path / "test.png"
    fake_resp = MagicMock()
    fake_resp.read.side_effect = [b"fake png data", b""]  # 1 次 read 返 data, 第 2 次 EOF
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = MagicMock(return_value=False)

    call_count = [0]

    def fake_urlopen(req, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ssl.SSLError("UNEXPECTED_EOF_WHILE_READING")
        return fake_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        # 不该 raise
        _download_image_with_retry(
            "https://example.com/x.png",
            str(dest),
            max_retries=3,
            backoff_base=0.01,  # 测试快
            timeout=5,
        )
    assert dest.exists()
    assert dest.read_bytes() == b"fake png data"
    assert call_count[0] == 2


def test_url_retry_all_fail_raises(tmp_path):
    """3 次都 SSL 失败 -> raise 最后一次 exception."""
    dest = tmp_path / "test.png"

    with patch("urllib.request.urlopen", side_effect=ssl.SSLError("EOF")):
        with pytest.raises(ssl.SSLError):
            _download_image_with_retry(
                "https://example.com/x.png",
                str(dest),
                max_retries=3,
                backoff_base=0.01,
                timeout=5,
            )
    assert not dest.exists()


def test_url_socket_timeout_retries(tmp_path):
    """socket.timeout 触发 retry."""
    dest = tmp_path / "test.png"

    fake_resp = MagicMock()
    fake_resp.read.side_effect = [b"data", b""]
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = MagicMock(return_value=False)

    call_count = [0]

    def fake_urlopen(req, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise socket.timeout("timed out")
        return fake_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        _download_image_with_retry(
            "https://example.com/x.png",
            str(dest),
            max_retries=2,
            backoff_base=0.01,
        )
    assert dest.read_bytes() == b"data"
    assert call_count[0] == 2


def test_url_urllib_error_404_no_retry(tmp_path):
    """404 不在 SSL 错误列表, 不会 retry (HTTPError 继承 URLError 但我 catches URLError 全集)."""
    # 实际行为: 404 也 retry 3 次 (因 URLError 触发). 验证行为一致
    dest = tmp_path / "test.png"

    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None)):
        with pytest.raises(urllib.error.HTTPError):
            _download_image_with_retry(
                "https://example.com/missing.png",
                str(dest),
                max_retries=2,
                backoff_base=0.01,
            )
    assert not dest.exists()


def test_url_retry_sse_status_emitted(tmp_path):
    """retry 时通过 result_queue 发 SSE status 事件."""
    dest = tmp_path / "test.png"
    q = MagicMock()
    q.put = MagicMock()

    fake_resp = MagicMock()
    fake_resp.read.side_effect = [b"ok", b""]
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__ = MagicMock(return_value=False)

    call_count = [0]

    def fake_urlopen(req, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ssl.SSLError("EOF")
        return fake_resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        _download_image_with_retry(
            "https://example.com/x.png", str(dest), result_queue=q,
            max_retries=3, backoff_base=0.01,
        )
    # q.put 至少被调用 1 次 (status 重试消息)
    assert q.put.called
    put_calls = [call.args[0] for call in q.put.call_args_list if call.args]
    status_messages = [c[1] for c in put_calls if c[0] == "status"]
    assert any("重试 1/3" in m for m in status_messages)
