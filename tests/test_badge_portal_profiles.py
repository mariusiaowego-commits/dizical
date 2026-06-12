"""tests/test_badge_portal_profiles.py — V1.1 改用 hermes tools list

按用户拍板: "只查 hermes portal status 和 dizical portal status" — 但 hermes OAuth
跨 subprocess 不可靠 (subprocess 永远报 not_logged_in 即使 OAuth 还在).
V1.1 改用 hermes tools list 看 image_gen 启用 (subprocess 友好, OAuth 无关).

覆盖:
- _parse_tools_list_output 解析 built-in toolsets 启用状态
- _check_one_profile_portal 单个 profile 状态查 (mock subprocess)
- check_two_profiles_portal 查 hermes CLI 默认 + dizical 2 个 (并发)
- 错误兜底 (timeout, file not found, nonzero exit)
- 固定顺序输出 (default 在前, dizical 在后)
"""
import subprocess
from unittest import mock

import pytest

from src.kid_app import badge_portal


# ─── Helpers ──────────────────────────────────────────────────────

def _mock_subprocess_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    result = mock.Mock(spec=subprocess.CompletedProcess)
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


# hermes tools list 输出格式 (实测, image_gen 启用场景)
TOOLS_LIST_WITH_IMAGE_GEN = """Built-in toolsets (cli):
  ✓ enabled  web  🔍 Web Search & Scraping
  ✓ enabled  browser  🌐 Browser Automation
  ✓ enabled  terminal  💻 Terminal & Processes
  ✓ enabled  file  📁 File Operations
  ✓ enabled  image_gen  🎨 Image Generation
  ✗ disabled  video  🎬 Video Analysis
  ✓ enabled  tts  🔊 Text-to-Speech
"""

# hermes tools list 输出 (image_gen 禁用场景)
TOOLS_LIST_NO_IMAGE_GEN = """Built-in toolsets (cli):
  ✓ enabled  web  🔍 Web Search & Scraping
  ✓ enabled  browser  🌐 Browser Automation
  ✗ disabled  image_gen  🎨 Image Generation
  ✗ disabled  video  🎬 Video Analysis
"""


# ─── TestParseToolsListOutput ───────────────────────────────────

class TestParseToolsListOutput:
    def test_image_gen_enabled(self):
        parsed = badge_portal._parse_tools_list_output(TOOLS_LIST_WITH_IMAGE_GEN)
        assert parsed["image_gen_enabled"] is True
        assert parsed["web_enabled"] is True
        assert parsed["tts_enabled"] is True
        assert parsed["browser_enabled"] is True
        # raw_tools_count 包括 ✗ disabled (都算 1 行)
        assert parsed["raw_tools_count"] >= 4

    def test_image_gen_disabled(self):
        parsed = badge_portal._parse_tools_list_output(TOOLS_LIST_NO_IMAGE_GEN)
        assert parsed["image_gen_enabled"] is False
        assert parsed["web_enabled"] is True  # 还在
        assert parsed["browser_enabled"] is True
        assert parsed["tts_enabled"] is False  # 没出现

    def test_empty_output(self):
        parsed = badge_portal._parse_tools_list_output("")
        assert parsed["image_gen_enabled"] is False
        assert parsed["raw_tools_count"] == 0

    def test_garbage_output(self):
        parsed = badge_portal._parse_tools_list_output("random text\nwithout tools list format")
        assert parsed["image_gen_enabled"] is False
        assert parsed["raw_tools_count"] == 0


# ─── TestCheckOneProfilePortal ─────────────────────────────────

class TestCheckOneProfilePortal:
    def test_image_gen_enabled_explicit_profile(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0),
        ):
            result = badge_portal._check_one_profile_portal("dizical")
        assert result["profile"] == "dizical"
        assert result["auth"] == "logged_in"
        assert result["image_generation"] == "via_portal"
        assert result["ok_for_badge"] is True

    def test_image_gen_disabled(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=TOOLS_LIST_NO_IMAGE_GEN, returncode=0),
        ):
            result = badge_portal._check_one_profile_portal("coder")
        assert result["auth"] == "not_logged_in"
        assert result["image_generation"] == "not_configured"
        assert result["ok_for_badge"] is False
        assert "image_gen 未启用" in result["error"]

    def test_none_profile_uses_hermes_default(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0),
        ) as m:
            result = badge_portal._check_one_profile_portal(None)
        # display name 应该是 "default"
        assert result["profile"] == "default"
        # 命令里**没有** --profile flag
        cmd = m.call_args[0][0]
        assert "--profile" not in cmd
        # 但有 "tools" 和 "list"
        assert "tools" in cmd
        assert "list" in cmd

    def test_explicit_profile_includes_flag(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=TOOLS_LIST_WITH_IMAGE_GEN, returncode=0),
        ) as m:
            result = badge_portal._check_one_profile_portal("coder")
        cmd = m.call_args[0][0]
        assert "--profile" in cmd
        assert cmd[cmd.index("--profile") + 1] == "coder"

    def test_timeout(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd=["hermes"], timeout=8),
        ):
            result = badge_portal._check_one_profile_portal("dizical")
        assert result["auth"] == "unknown"
        assert "超时" in result["error"]

    def test_hermes_not_found(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            side_effect=FileNotFoundError("hermes"),
        ):
            result = badge_portal._check_one_profile_portal("dizical")
        assert "hermes CLI 找不到" in result["error"]

    def test_nonzero_exit(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stderr="profile not found", returncode=1),
        ):
            result = badge_portal._check_one_profile_portal("ghost")
        assert "rc=1" in result["error"]


# ─── TestCheckTwoProfilesPortal ─────────────────────────────────

class TestCheckTwoProfilesPortal:
    def setup_method(self):
        badge_portal.invalidate_cache()
    def test_returns_two_results(self):
        def fake_check(profile_arg, **kw):
            return {
                "profile": "default" if profile_arg is None else "dizical",
                "auth": "logged_in", "image_generation": "via_portal",
                "model": "hermes", "ok_for_badge": True, "error": None, "latency_ms": 100,
            }
        with mock.patch.object(
            badge_portal, "_check_one_profile_portal",
            side_effect=fake_check,
        ):
            results = badge_portal.check_two_profiles_portal()
        # 调 _check 2 次
        assert len(results) == 2

    def test_first_is_default(self):
        """输出顺序: default 在前 (按用户拍板 '只查 hermes 和 dizical')."""
        def fake_check(profile_arg, **kw):
            return {
                "profile": "default" if profile_arg is None else "dizical",
                "auth": "logged_in", "image_generation": "via_portal",
                "model": "hermes", "ok_for_badge": True, "error": None, "latency_ms": 100,
            }
        with mock.patch.object(
            badge_portal, "_check_one_profile_portal",
            side_effect=fake_check,
        ):
            results = badge_portal.check_two_profiles_portal()
        # 2 个 result, 第一个 profile 名是 default, 第二个是 dizical
        assert results[0]["profile"] == "default"
        assert results[1]["profile"] == "dizical"

    def test_dizical_profile_uses_env(self, monkeypatch):
        """DIZICAL_HERMES_PROFILE env 覆盖时, 2nd profile 用新名."""
        monkeypatch.setenv("DIZICAL_HERMES_PROFILE", "dizical_custom")
        def fake_check(profile_arg, **kw):
            return {
                "profile": "default" if profile_arg is None else profile_arg,
                "auth": "logged_in", "image_generation": "via_portal",
                "model": "hermes", "ok_for_badge": True, "error": None, "latency_ms": 100,
            }
        with mock.patch.object(
            badge_portal, "_check_one_profile_portal",
            side_effect=fake_check,
        ):
            results = badge_portal.check_two_profiles_portal()
        # 查 _get_profile() 拿 env
        assert results[1]["profile"] == "dizical_custom"

    def test_exception_caught_not_blocking(self):
        """某 1 个 profile _check 抛异常, 包成 dict 不阻断."""
        with mock.patch.object(
            badge_portal, "_check_one_profile_portal",
            side_effect=[
                {"profile": "default", "auth": "logged_in", "image_generation": "via_portal",
                 "model": "hermes", "ok_for_badge": True, "error": None, "latency_ms": 100},
                RuntimeError("boom"),
            ],
        ):
            results = badge_portal.check_two_profiles_portal()
        # 2 个 result (含异常 1 个)
        assert len(results) == 2
        # 异常的包成 "concurrent: boom"
        assert any((r.get("error") or "") and "concurrent: boom" in r["error"] for r in results)


# ─── TestCheckPortalStatus (V1.1 改用 tools list) ───────────────────

class TestCheckPortalStatus:
    """V1.1: check_portal_status 改用 hermes tools list 报 image_gen 状态."""

    def setup_method(self):
        badge_portal.invalidate_cache()

    def test_image_gen_disabled_returns_not_ok(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=TOOLS_LIST_NO_IMAGE_GEN, returncode=0,
            ),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.ok_for_badge is False
        # error msg 含 image_gen 提示 (跟 check_portal_status 实际错误信息匹配)
        assert "image_gen" in (s.error or "")
        assert "未启用" in (s.error or "")
        assert s.image_generation == "not_configured"
