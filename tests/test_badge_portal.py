"""tests/test_badge_portal.py — V1.1 改用 hermes tools list

V1 PR-A: 调 `hermes --profile dizical portal status` 解析输出.
V1.1: 改用 `hermes --profile dizical tools list` 报 image_gen 状态 (subprocess 友好,
OAuth 跨 subprocess 不可靠, 改用 tools list 看 built-in toolsets 启用).
"""
import subprocess
import time
from unittest import mock

import pytest

from src.kid_app import badge_portal


# ─── Sample hermes tools list output (实测) ───────────────────────────

# image_gen 启用场景
TOOLS_LIST_WITH_IMAGE_GEN = """Built-in toolsets (cli):
  ✓ enabled  web  🔍 Web Search & Scraping
  ✓ enabled  browser  🌐 Browser Automation
  ✓ enabled  terminal  💻 Terminal & Processes
  ✓ enabled  file  📁 File Operations
  ✓ enabled  image_gen  🎨 Image Generation
  ✗ disabled  video  🎬 Video Analysis
  ✓ enabled  tts  🔊 Text-to-Speech
"""

# image_gen 禁用场景
TOOLS_LIST_NO_IMAGE_GEN = """Built-in toolsets (cli):
  ✓ enabled  web  🔍 Web Search & Scraping
  ✓ enabled  browser  🌐 Browser Automation
  ✗ disabled  image_gen  🎨 Image Generation
  ✗ disabled  video  🎬 Video Analysis
"""

# 空 (没 tools)
TOOLS_LIST_EMPTY = ""


def _mock_subprocess_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    result = mock.Mock(spec=subprocess.CompletedProcess)
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


# ─── TestParsePortalOutput (V1.1 删除, 改用 _parse_tools_list_output) ──
# V1.1: 不再测旧 _parse_portal_output (portal info/status 格式)
# 改测 _parse_tools_list_output (新格式)


# ─── TestParseToolsListOutput ───────────────────────────────────

class TestParseToolsListOutput:
    def test_image_gen_enabled(self):
        parsed = badge_portal._parse_tools_list_output(TOOLS_LIST_WITH_IMAGE_GEN)
        assert parsed["image_gen_enabled"] is True
        assert parsed["web_enabled"] is True
        assert parsed["tts_enabled"] is True
        assert parsed["browser_enabled"] is True
        # raw_tools_count 包括 ✗ disabled (每行算 1)
        assert parsed["raw_tools_count"] >= 4

    def test_image_gen_disabled(self):
        parsed = badge_portal._parse_tools_list_output(TOOLS_LIST_NO_IMAGE_GEN)
        assert parsed["image_gen_enabled"] is False
        assert parsed["web_enabled"] is True
        assert parsed["browser_enabled"] is True
        assert parsed["tts_enabled"] is False  # 没出现

    def test_empty_output(self):
        parsed = badge_portal._parse_tools_list_output(TOOLS_LIST_EMPTY)
        assert parsed["image_gen_enabled"] is False
        assert parsed["raw_tools_count"] == 0

    def test_garbage_output(self):
        parsed = badge_portal._parse_tools_list_output("random text\nwithout tools list format")
        assert parsed["image_gen_enabled"] is False
        assert parsed["raw_tools_count"] == 0


# ─── TestCheckPortalStatus ──────────────────────────────────────

class TestCheckPortalStatus:
    """V1.1: check_portal_status 改用 hermes tools list 报 image_gen 状态."""

    def setup_method(self):
        badge_portal.invalidate_cache()

    def test_image_gen_enabled_returns_ok(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0,
            ),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.ok_for_badge is True
        assert s.auth == "logged_in"
        assert s.image_generation == "via_portal"

    def test_image_gen_disabled_returns_not_ok(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_NO_IMAGE_GEN, returncode=0,
            ),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.ok_for_badge is False
        assert "image_gen" in (s.error or "")

    def test_cache_hit_within_ttl(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0,
            ),
        ) as m:
            badge_portal.check_portal_status(use_cache=True)
            badge_portal.check_portal_status(use_cache=True)
        # 60s 内只调 1 次 subprocess
        assert m.call_count == 1

    def test_no_cache_when_disabled(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0,
            ),
        ) as m:
            badge_portal.check_portal_status(use_cache=False)
            badge_portal.check_portal_status(use_cache=False)
        assert m.call_count == 2

    def test_reloads_after_ttl_expired(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0,
            ),
        ) as m:
            badge_portal.check_portal_status(use_cache=True)
            # 强制 cache 过期
            badge_portal._cache["ts"] = time.time() - badge_portal._CACHE_TTL - 1
            badge_portal.check_portal_status(use_cache=True)
        assert m.call_count == 2

    def test_invalidate_cache(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0,
            ),
        ) as m:
            badge_portal.check_portal_status(use_cache=True)
            badge_portal.invalidate_cache()
            badge_portal.check_portal_status(use_cache=True)
        assert m.call_count == 2

    def test_timeout_returns_unknown(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd=["hermes"], timeout=10),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.auth == "unknown"
        assert s.image_generation == "unknown"
        assert s.ok_for_badge is False
        assert "超时" in s.error

    def test_hermes_not_found(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            side_effect=FileNotFoundError("hermes"),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.ok_for_badge is False
        assert "hermes CLI 找不到" in s.error

    def test_nonzero_exit(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stderr="some error", returncode=1),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.ok_for_badge is False
        assert s.error is not None
        assert "rc=1" in s.error

    def test_latency_tracked(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0,
            ),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.latency_ms >= 0


# ─── TestRefreshCache ──────────────────────────────────────────

class TestRefreshCache:
    def test_clears_cache(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0,
            ),
        ):
            badge_portal.check_portal_status(use_cache=True)
            # cache 里有 PortalStatus 对象
            assert badge_portal._cache["data"] is not None
            assert badge_portal._cache["data"].ok_for_badge is True
            # 失效
            badge_portal.invalidate_cache()
            assert badge_portal._cache["ts"] == 0.0
            assert badge_portal._cache["data"] is None


# ─── TestIsReadyForBadgeWorkflow ──────────────────────────────

class TestIsReadyForBadgeWorkflow:
    def setup_method(self):
        badge_portal.invalidate_cache()
    def test_ready(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0,
            ),
        ):
            ok, msg = badge_portal.is_ready_for_badge_workflow()
        assert ok is True
        assert "正常" in msg

    def test_not_ready(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_NO_IMAGE_GEN, returncode=0,
            ),
        ):
            ok, msg = badge_portal.is_ready_for_badge_workflow()
        assert ok is False
        # V1.1: msg 来源是 image_gen 未启用
        assert "image_gen" in msg or "未启用" in msg
