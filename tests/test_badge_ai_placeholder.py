"""tests/test_badge_ai_placeholder.py — 单元测试薄壳版 badge_ai_placeholder

V1 改方向后 (用户 2026-06-12 拍板): dizical 不再直连 DeepSeek, 走 hermes dizical profile.
所有测试用 mock subprocess.run, 不真打 hermes.
"""
import subprocess
from unittest import mock

import pytest

from src.kid_app import badge_ai_placeholder


# ─── Mock helpers ──────────────────────────────────────────────

def _mock_subprocess_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    """建一个 mock CompletedProcess-like 对象."""
    result = mock.Mock(spec=subprocess.CompletedProcess)
    result.stdout = stdout
    result.stderr = stderr
    result.returncode = returncode
    return result


def _mock_hermes_output(content: str) -> str:
    """模拟 hermes chat -Q 输出 (第一行 session_id, 之后 content)."""
    return f"session_id: abc-123-def\n{content}\n"


# ─── TestInputValidation ───────────────────────────────────────

class TestInputValidation:
    def test_zh_story_too_short(self):
        with pytest.raises(ValueError, match="zh_story 至少 5 字符"):
            badge_ai_placeholder.draft_placeholder("ab", "name")

    def test_zh_story_empty(self):
        with pytest.raises(ValueError, match="zh_story 至少 5 字符"):
            badge_ai_placeholder.draft_placeholder("", "name")

    def test_zh_story_whitespace(self):
        with pytest.raises(ValueError, match="zh_story 至少 5 字符"):
            badge_ai_placeholder.draft_placeholder("   ", "name")

    def test_badge_name_empty(self):
        with pytest.raises(ValueError, match="badge_name 不能为空"):
            badge_ai_placeholder.draft_placeholder("a story", "")

    def test_badge_name_whitespace(self):
        with pytest.raises(ValueError, match="badge_name 不能为空"):
            badge_ai_placeholder.draft_placeholder("a story", "   ")


# ─── TestFindHermes ──────────────────────────────────────────────

class TestFindHermes:
    def test_default_path_exists(self):
        # /Users/mt16/.local/bin/hermes 已确认存在 (实测 coder profile 在用)
        path = badge_ai_placeholder._find_hermes()
        assert path  # 非空字符串

    def test_fallback_to_which(self, monkeypatch):
        # 删掉 hardcoded path, 走 which
        monkeypatch.setattr(
            badge_ai_placeholder, "_HERMES_PATH",
            badge_ai_placeholder.Path("/nonexistent/hermes"),
        )
        path = badge_ai_placeholder._find_hermes()
        # 兜底走 which
        assert path.endswith("hermes") or path == "/usr/bin/hermes"

    def test_not_found_raises(self, monkeypatch):
        # 模拟两个都找不到
        monkeypatch.setattr(
            badge_ai_placeholder, "_HERMES_PATH",
            badge_ai_placeholder.Path("/nonexistent/hermes"),
        )
        monkeypatch.setattr(
            "shutil.which", lambda x: None,
        )
        with pytest.raises(RuntimeError, match="hermes CLI 找不到"):
            badge_ai_placeholder._find_hermes()


# ─── TestGetProfile ──────────────────────────────────────────────

class TestGetProfile:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("DIZICAL_HERMES_PROFILE", raising=False)
        assert badge_ai_placeholder._get_profile() == "dizical"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("DIZICAL_HERMES_PROFILE", "dizical_custom")
        assert badge_ai_placeholder._get_profile() == "dizical_custom"

    def test_empty_env_uses_default(self, monkeypatch):
        monkeypatch.setenv("DIZICAL_HERMES_PROFILE", "   ")
        # 空白 trim 后用 default
        assert badge_ai_placeholder._get_profile() == "dizical"


# ─── TestDraftPlaceholder (mock subprocess) ──────────────────────

class TestDraftPlaceholder:
    def test_success(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=_mock_hermes_output("a cute chibi girl with a magical bamboo flute"),
            ),
        ) as m:
            result = badge_ai_placeholder.draft_placeholder("孔子闻韶三月不知肉味", "闻韶")
        assert result == "a cute chibi girl with a magical bamboo flute"
        # 验证调 hermes 时带了 --profile dizical
        cmd = m.call_args[0][0]
        assert "--profile" in cmd
        idx = cmd.index("--profile")
        assert cmd[idx + 1] == "dizical"
        # 验证非交互模式
        assert "-Q" in cmd
        assert "--yolo" in cmd

    def test_uses_env_profile(self, monkeypatch):
        monkeypatch.setenv("DIZICAL_HERMES_PROFILE", "dizical_test")
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=_mock_hermes_output("test placeholder here"),
            ),
        ) as m:
            result = badge_ai_placeholder.draft_placeholder("story", "name")
        cmd = m.call_args[0][0]
        assert cmd[cmd.index("--profile") + 1] == "dizical_test"

    def test_no_shell_true(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=_mock_hermes_output("placeholder content"),
            ),
        ) as m:
            badge_ai_placeholder.draft_placeholder("story", "name")
        # subprocess.run 必须是 list argv, 不是 string
        cmd = m.call_args[0][0]
        assert isinstance(cmd, list), "必须用 list argv, 不能 shell=True"
        # shell kwarg 必须是 False (默认)
        assert m.call_args.kwargs.get("shell", False) is False

    def test_timeout(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd=["hermes"], timeout=60),
        ):
            with pytest.raises(RuntimeError, match="超时"):
                badge_ai_placeholder.draft_placeholder("story", "name")

    def test_hermes_not_found(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            side_effect=FileNotFoundError("hermes not on PATH"),
        ):
            with pytest.raises(RuntimeError, match="hermes CLI 不在 PATH"):
                badge_ai_placeholder.draft_placeholder("story", "name")

    def test_hermes_nonzero_exit(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stderr="some error", returncode=1,
            ),
        ):
            with pytest.raises(RuntimeError, match="hermes chat 失败"):
                badge_ai_placeholder.draft_placeholder("story", "name")

    def test_profile_not_found_specific_error(self):
        # hermes 错误含 "profile ... not found"
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stderr="Error: profile 'dizical' not found",
                returncode=1,
            ),
        ):
            with pytest.raises(RuntimeError, match="profile 'dizical' 不存在"):
                badge_ai_placeholder.draft_placeholder("story", "name")

    def test_strips_session_id_line(self):
        # hermes chat -Q 输出含 session_id 行, 应该被剥
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout="session_id: xyz-789\nplaceholder text here",
            ),
        ):
            result = badge_ai_placeholder.draft_placeholder("story", "name")
        assert "session_id" not in result
        assert "xyz" not in result
        assert result == "placeholder text here"

    def test_strips_json_fence(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=_mock_hermes_output('```json\n{"placeholder": "x"}\n```'),
            ),
        ):
            result = badge_ai_placeholder.draft_placeholder("story", "name")
        assert "```" not in result

    def test_strips_quotes(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=_mock_hermes_output('"a cute girl playing flute"'),
            ),
        ):
            result = badge_ai_placeholder.draft_placeholder("story", "name")
        assert result == "a cute girl playing flute"

    def test_response_too_short_raises(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=_mock_hermes_output("abc"),
            ),
        ):
            with pytest.raises(RuntimeError, match="太短"):
                badge_ai_placeholder.draft_placeholder("story", "name")

    def test_empty_response_raises(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout="session_id: xyz\n",
            ),
        ):
            with pytest.raises(RuntimeError, match="hermes 返回空"):
                badge_ai_placeholder.draft_placeholder("story", "name")


# ─── TestIsConfigured ──────────────────────────────────────────

class TestIsConfigured:
    def test_true_when_profile_exists(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout="Profile: dizical\nPath: /Users/mt16/.hermes/profiles/dizical",
                returncode=0,
            ),
        ):
            assert badge_ai_placeholder.is_configured() is True

    def test_false_when_profile_not_found(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stderr="profile not found", returncode=1,
            ),
        ):
            assert badge_ai_placeholder.is_configured() is False

    def test_false_when_timeout(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd=["hermes"], timeout=5),
        ):
            assert badge_ai_placeholder.is_configured() is False

    def test_false_when_hermes_not_found(self):
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            side_effect=FileNotFoundError("hermes"),
        ):
            assert badge_ai_placeholder.is_configured() is False


# ─── TestPrivacy (key 不泄漏到 prompt / args) ──────────────────

class TestPrivacy:
    def test_no_key_in_subprocess_args(self):
        """确认调 hermes 时 argv 不含 API key."""
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=_mock_hermes_output("placeholder here"),
            ),
        ) as m:
            badge_ai_placeholder.draft_placeholder("story", "name")
        cmd = m.call_args[0][0]
        cmd_str = " ".join(cmd)
        # 任何 provider key 前缀都不应出现
        for prefix in ("sk-", "sk_", "AIza", "nvap", "gsk_"):
            assert prefix not in cmd_str, f"API key prefix '{prefix}' 不应出现在 hermes argv"

    def test_no_key_in_env_passed(self, monkeypatch):
        """确认未把 key 通过 env 传给 hermes."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-leaked-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-leak")
        with mock.patch.object(
            badge_ai_placeholder.subprocess, "run",
            return_value=_mock_subprocess_result(
                stdout=_mock_hermes_output("placeholder here"),
            ),
        ) as m:
            badge_ai_placeholder.draft_placeholder("story", "name")
        # 没传 env=..., hermes 自己读 .env
        env_kw = m.call_args.kwargs.get("env")
        assert env_kw is None
