"""tests/test_badge_portal.py — 单元测试 badge_portal

V1: 调 `hermes --profile dizical portal status` 解析输出.
测试用 mock subprocess, 不真打 hermes.
"""
import subprocess
import time
from unittest import mock

import pytest

from src.kid_app import badge_portal


# ─── Sample hermes portal output (实测) ───────────────────────────

PORTAL_OK_OUTPUT = """
  Nous Portal
  ───────────
  Auth:    ✓ logged in
  Portal:  https://portal.nousresearch.com
  API:     https://inference-api.nousresearch.com/v1
  Model:   currently xiaomi (switch with `hermes model`)

  Tool Gateway
  ────────────
  Web tools            via Nous Portal
  Image generation     via Nous Portal
  Video generation     not configured
  OpenAI TTS           via Nous Portal
  Browser automation   via Nous Portal
  Modal execution      local
"""

PORTAL_AUTH_FAIL_OUTPUT = """
  Nous Portal
  ───────────
  Auth:    ✗ (not set)
  Portal:  https://portal.nousresearch.com
  API:     https://inference-api.nousresearch.com/v1
  Model:   currently xiaomi (switch with `hermes model`)

  Tool Gateway
  ────────────
  Web tools            via Nous Portal
  Image generation     via Nous Portal
  Video generation     not configured
"""

PORTAL_IMG_NOT_CONFIGURED_OUTPUT = """
  Nous Portal
  ───────────
  Auth:    ✓ logged in
  Portal:  https://portal.nousresearch.com
  API:     https://inference-api.nousresearch.com/v1
  Model:   currently xiaomi (switch with `hermes model`)

  Tool Gateway
  ────────────
  Web tools            via Nous Portal
  Image generation     not configured
  Video generation     not configured
"""


def _mock_subprocess_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    result = mock.Mock(spec=subprocess.CompletedProcess)
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


# ─── TestParsePortalOutput ─────────────────────────────────────

class TestParsePortalOutput:
    def test_full_ok(self):
        s = badge_portal._parse_portal_output(PORTAL_OK_OUTPUT)
        assert s.auth == "logged_in"
        assert s.image_generation == "via_portal"
        assert s.model == "xiaomi"
        assert s.ok_for_badge is True
        assert s.error is None

    def test_auth_fail(self):
        s = badge_portal._parse_portal_output(PORTAL_AUTH_FAIL_OUTPUT)
        assert s.auth == "not_logged_in"
        assert s.image_generation == "via_portal"
        assert s.ok_for_badge is False
        assert "portal auth" in s.error

    def test_image_not_configured(self):
        s = badge_portal._parse_portal_output(PORTAL_IMG_NOT_CONFIGURED_OUTPUT)
        assert s.auth == "logged_in"
        assert s.image_generation == "not_configured"
        assert s.ok_for_badge is False
        assert "image generation" in s.error

    def test_garbage_output(self):
        s = badge_portal._parse_portal_output("random text")
        assert s.auth == "unknown"
        assert s.image_generation == "unknown"
        assert s.ok_for_badge is False
        assert s.error is not None

    def test_empty_output(self):
        s = badge_portal._parse_portal_output("")
        assert s.auth == "unknown"
        assert s.image_generation == "unknown"
        assert s.model == "unknown"
        assert s.ok_for_badge is False


# ─── TestCheckPortalStatus ─────────────────────────────────────

class TestCheckPortalStatus:
    def setup_method(self):
        badge_portal.invalidate_cache()  # 每个 test 前清 cache

    def test_success_with_cache_miss(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=PORTAL_OK_OUTPUT, returncode=0),
        ) as m:
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.ok_for_badge is True
        assert s.model == "xiaomi"
        # 验证 subprocess 命令格式
        cmd = m.call_args[0][0]
        assert cmd[0].endswith("hermes")
        assert cmd[1:3] == ["--profile", "dizical"]
        assert cmd[3:5] == ["portal", "status"]

    def test_uses_default_profile_from_env(self, monkeypatch):
        monkeypatch.setenv("DIZICAL_HERMES_PROFILE", "dizical_test")
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=PORTAL_OK_OUTPUT, returncode=0),
        ) as m:
            badge_portal.check_portal_status(use_cache=False)
        cmd = m.call_args[0][0]
        assert cmd[2] == "dizical_test"

    def test_uses_cache_within_ttl(self):
        # 第一次调用
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=PORTAL_OK_OUTPUT, returncode=0),
        ) as m:
            s1 = badge_portal.check_portal_status(use_cache=True)
            s2 = badge_portal.check_portal_status(use_cache=True)
        # subprocess.run 应该只被调 1 次
        assert m.call_count == 1
        assert s1 is s2

    def test_no_cache_when_use_cache_false(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=PORTAL_OK_OUTPUT, returncode=0),
        ) as m:
            badge_portal.check_portal_status(use_cache=False)
            badge_portal.check_portal_status(use_cache=False)
        assert m.call_count == 2

    def test_cache_expired_after_ttl(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=PORTAL_OK_OUTPUT, returncode=0),
        ) as m:
            badge_portal.check_portal_status(use_cache=True)
            # 强制 cache 过期
            badge_portal._cache["ts"] = time.time() - badge_portal._CACHE_TTL - 1
            badge_portal.check_portal_status(use_cache=True)
        assert m.call_count == 2

    def test_invalidate_cache(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=PORTAL_OK_OUTPUT, returncode=0),
        ) as m:
            badge_portal.check_portal_status(use_cache=True)
            badge_portal.invalidate_cache()
            badge_portal.check_portal_status(use_cache=True)
        assert m.call_count == 2

    def test_timeout_returns_unkown(self):
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
            return_value=_mock_subprocess_result(
                stderr="some error", returncode=1,
            ),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.ok_for_badge is False
        assert s.error is not None
        assert "rc=1" in s.error

    def test_latency_tracked(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=PORTAL_OK_OUTPUT, returncode=0),
        ):
            s = badge_portal.check_portal_status(use_cache=False)
        assert s.latency_ms >= 0


# ─── TestIsReadyForBadgeWorkflow ──────────────────────────────

class TestIsReadyForBadgeWorkflow:
    def setup_method(self):
        badge_portal.invalidate_cache()

    def test_ready(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(stdout=PORTAL_OK_OUTPUT, returncode=0),
        ):
            ok, msg = badge_portal.is_ready_for_badge_workflow()
        assert ok is True
        assert "正常" in msg
        assert "xiaomi" in msg

    def test_not_ready(self):
        with mock.patch.object(
            badge_portal.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=PORTAL_AUTH_FAIL_OUTPUT, returncode=0,
            ),
        ):
            ok, msg = badge_portal.is_ready_for_badge_workflow()
        assert ok is False
        assert "portal auth" in msg
