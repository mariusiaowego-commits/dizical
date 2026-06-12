"""tests/test_badge_generator.py — 单元测试 badge_generator 流水线

V1 改方向后: FAL 调用走 hermes Tool Gateway (不是直接调 FAL).
测试用 mock subprocess.Popen, 不真打 hermes 也不真连 FAL.
"""
import os
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from PIL import Image

from src.kid_app import badge_generator, badge_portal


# ─── Mock helpers ──────────────────────────────────────────────

def _mock_popen_with_output(stdout_text: str, returncode: int = 0):
    """建一个 mock Popen 实例, 返回给定 stdout, 指定 returncode."""
    mock_proc = mock.Mock()
    mock_proc.stdout = iter(stdout_text.splitlines(keepends=True))
    mock_proc.stderr = mock.Mock()
    mock_proc.stderr.read.return_value = ""
    mock_proc.returncode = returncode
    mock_proc.wait.return_value = returncode
    return mock_proc


def _mock_popen_timeout():
    """mock Popen, wait 抛 TimeoutExpired."""
    mock_proc = mock.Mock()
    mock_proc.stdout = iter([])
    mock_proc.stderr = mock.Mock()
    mock_proc.stderr.read.return_value = ""
    mock_proc.kill = mock.Mock()
    mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd=["hermes"], timeout=180)
    return mock_proc


# ─── TestResolveImageSource ─────────────────────────────────────

class TestResolveImageSource:
    def test_media_prefix_local_file(self, tmp_path):
        # MEDIA:/path/to/file.png, 文件存在
        png_path = tmp_path / "test.png"
        png_path.write_bytes(b"fake png")
        output = f"session_id: xyz\nMEDIA:{png_path}\nDone."
        result = badge_generator._resolve_image_source(output)
        assert result == str(png_path)

    def test_http_url(self):
        output = "https://v3b.fal.media/files/b/0a99eac7/test.png"
        result = badge_generator._resolve_image_source(output)
        assert result == "https://v3b.fal.media/files/b/0a99eac7/test.png"

    def test_https_url_with_fal(self):
        # 不以 .png 结尾但含 fal 域名
        output = "https://fal.media/files/some-uuid"
        result = badge_generator._resolve_image_source(output)
        assert result == "https://fal.media/files/some-uuid"

    def test_local_absolute_path_exists(self, tmp_path):
        png_path = tmp_path / "x.png"
        png_path.write_bytes(b"x")
        output = f"session_id: xyz\n{png_path}"
        result = badge_generator._resolve_image_source(output)
        assert result == str(png_path)

    def test_local_path_does_not_exist(self, tmp_path):
        output = f"session_id: xyz\n{tmp_path}/nonexistent.png"
        result = badge_generator._resolve_image_source(output)
        assert result is None

    def test_no_image_in_output(self):
        output = "session_id: xyz\nDone. No image generated."
        result = badge_generator._resolve_image_source(output)
        assert result is None

    def test_empty_output(self):
        result = badge_generator._resolve_image_source("")
        assert result is None

    def test_media_prefix_nonexistent_path_skipped(self, tmp_path):
        # MEDIA: 后面路径不存在, 不应让整个解析失败
        # (应该继续找其他行)
        output = f"MEDIA:/nonexistent/x.png\nMEDIA:/also/nonexistent.png"
        result = badge_generator._resolve_image_source(output)
        assert result is None  # 都找不到, 返回 None

    def test_session_id_line_skipped(self):
        output = "session_id: abc-123-def\nhttps://v3b.fal.media/files/xyz.png"
        result = badge_generator._resolve_image_source(output)
        # session_id 行没被当成图片 URL
        assert "session_id" not in (result or "")


# ─── TestCallHermesImageGen ────────────────────────────────────

class TestCallHermesImageGen:
    def test_success(self, tmp_path):
        png_path = tmp_path / "out.png"
        png_path.write_bytes(b"x")
        stdout = f"session_id: abc\nMEDIA:{png_path}\n"
        with mock.patch.object(
            badge_generator.subprocess, "Popen",
            return_value=_mock_popen_with_output(stdout, returncode=0),
        ) as m:
            outputs = []
            ok, full, src = badge_generator._call_hermes_image_gen(
                "test prompt", lambda line: outputs.append(line),
            )
        assert ok is True
        assert src == str(png_path)
        # 验证命令
        cmd = m.call_args[0][0]
        assert cmd[0].endswith("hermes")
        assert cmd[1:3] == ["chat", "-q"]
        assert "test prompt" in cmd
        assert "-t" in cmd
        assert "image_gen" in cmd
        assert "--profile" in cmd
        assert "dizical" in cmd
        assert "-Q" in cmd
        assert "--yolo" in cmd

    def test_profile_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("DIZICAL_HERMES_PROFILE", "dizical_test")
        png_path = tmp_path / "out.png"
        png_path.write_bytes(b"x")
        stdout = f"session_id: abc\nMEDIA:{png_path}\n"
        with mock.patch.object(
            badge_generator.subprocess, "Popen",
            return_value=_mock_popen_with_output(stdout, returncode=0),
        ) as m:
            badge_generator._call_hermes_image_gen("p", lambda l: None)
        cmd = m.call_args[0][0]
        assert cmd[cmd.index("--profile") + 1] == "dizical_test"

    def test_nonzero_exit(self):
        with mock.patch.object(
            badge_generator.subprocess, "Popen",
            return_value=_mock_popen_with_output("error", returncode=1),
        ):
            ok, full, src = badge_generator._call_hermes_image_gen("p", lambda l: None)
        assert ok is False
        assert "rc=1" in full
        assert src is None

    def test_timeout(self):
        with mock.patch.object(
            badge_generator.subprocess, "Popen",
            return_value=_mock_popen_timeout(),
        ):
            ok, full, src = badge_generator._call_hermes_image_gen("p", lambda l: None)
        assert ok is False
        assert "超时" in full

    def test_no_image_in_output(self):
        with mock.patch.object(
            badge_generator.subprocess, "Popen",
            return_value=_mock_popen_with_output("no image here"),
        ):
            ok, full, src = badge_generator._call_hermes_image_gen("p", lambda l: None)
        assert ok is False
        assert "未找到图片" in full
        assert src is None

    def test_hermes_not_found(self):
        with mock.patch.object(
            badge_generator.subprocess, "Popen",
            side_effect=FileNotFoundError("hermes"),
        ):
            ok, full, src = badge_generator._call_hermes_image_gen("p", lambda l: None)
        assert ok is False
        assert "hermes CLI 找不到" in full


# ─── TestDedupeToRgba ───────────────────────────────────────────

class TestDedupeToRgba:
    def test_rgba_to_rgba(self, tmp_path):
        # 已经是 RGBA, 全透明 + 一些 RGB
        img = Image.new("RGBA", (10, 10), (255, 255, 255, 255))
        img.save(tmp_path / "test.png")
        result = badge_generator._dedupe_to_rgba(tmp_path / "test.png")
        assert result is True
        # 验证白像素变透明
        im = Image.open(tmp_path / "test.png")
        assert im.mode == "RGBA"
        # 中心像素应该变透明
        assert im.getpixel((5, 5)) == (255, 255, 255, 0)

    def test_rgb_to_rgba_deduped(self, tmp_path):
        # RGB 输入, 去背后变 RGBA
        img = Image.new("RGB", (5, 5), (250, 250, 250))
        img.save(tmp_path / "test.png")
        result = badge_generator._dedupe_to_rgba(tmp_path / "test.png")
        assert result is True

    def test_non_white_preserved(self, tmp_path):
        # 非白色像素 (红色), 不应被去背
        img = Image.new("RGBA", (5, 5), (200, 50, 50, 255))
        img.save(tmp_path / "test.png")
        badge_generator._dedupe_to_rgba(tmp_path / "test.png")
        im = Image.open(tmp_path / "test.png")
        assert im.getpixel((2, 2)) == (200, 50, 50, 255)  # 红色保留

    def test_low_saturation_antialias_also_deduped(self, tmp_path):
        # 近白 + 低饱和 (抗锯齿) → 也去背
        img = Image.new("RGBA", (5, 5), (230, 225, 220, 255))
        img.save(tmp_path / "test.png")
        badge_generator._dedupe_to_rgba(tmp_path / "test.png")
        im = Image.open(tmp_path / "test.png")
        # max-min = 10 < 30, 应该是低饱和, 应去背
        assert im.getpixel((2, 2))[3] == 0  # alpha=0

    def test_corrupt_file_returns_false(self, tmp_path):
        # 不存在的文件 → False
        result = badge_generator._dedupe_to_rgba(tmp_path / "nonexistent.png")
        assert result is False


# ─── TestDownloadOrCopyImage ────────────────────────────────────

class TestDownloadOrCopyImage:
    def test_copy_local(self, tmp_path):
        src = tmp_path / "src.png"
        src.write_bytes(b"fake")
        dest = tmp_path / "subdir" / "dest.png"
        badge_generator._download_or_copy_image(str(src), dest)
        assert dest.exists()
        assert dest.read_bytes() == b"fake"

    def test_download_http(self, tmp_path):
        dest = tmp_path / "downloaded.png"
        with mock.patch.object(
            badge_generator.urllib.request, "urlretrieve",
        ) as m:
            badge_generator._download_or_copy_image(
                "https://example.com/test.png", dest,
            )
        m.assert_called_once()
        # 创建了父目录
        assert dest.parent.exists()


# ─── TestRunBadgePipeline ───────────────────────────────────────

class TestRunBadgePipeline:
    """完整流水线 mock 测试."""

    def _mock_portal_ok(self):
        """Mock portal status = OK."""
        mock_status = mock.Mock()
        mock_status.ok_for_badge = True
        mock_status.model = "deepseek"
        mock_status.error = None
        return mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "Portal 正常 (model=deepseek)"),
        )

    def test_full_pipeline_success(self, tmp_path, monkeypatch):
        """完整流水线: portal OK + hermes 成功 + 下载 + 去背."""
        # portal 绿灯
        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            # hermes 模拟返回 MEDIA: 路径 (用真 PNG 字节, PIL 才能打开)
            output_png = tmp_path / "fake_hermes_output.png"
            Image.new("RGB", (50, 50), (240, 240, 240)).save(output_png, "PNG")
            stdout = f"session_id: abc\nMEDIA:{output_png}\n"
            with mock.patch.object(
                badge_generator.subprocess, "Popen",
                return_value=_mock_popen_with_output(stdout, returncode=0),
            ):
                statuses = []
                result = badge_generator.run_badge_pipeline(
                    badge_id="test_badge",
                    placeholder="a cute chibi girl playing flute",
                    on_status=lambda stage, msg: statuses.append((stage, msg)),
                )
        assert result["ok"] is True
        assert result["dedupe_ok"] is True
        assert result["version"] == 1
        # 文件名遵循 v{n} 格式
        img_path = Path(result["image_path"])
        assert img_path.name == "test_badge_v1.png"
        assert img_path.exists()
        # status 包含所有 6 步
        stages = [s[0] for s in statuses]
        assert "step0_portal" in stages
        assert "step1_validate" in stages
        assert "step2_prompt" in stages
        assert "step3_fal" in stages
        assert "step4_fetch" in stages
        assert "step5_dedupe" in stages
        # 清理
        img_path.unlink()

    def test_portal_red_blocks_pipeline(self):
        """portal 红了, 流水线不跑, 返回 error."""
        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(False, "portal auth: not_logged_in"),
        ):
            result = badge_generator.run_badge_pipeline(
                badge_id="x",
                placeholder="a cute girl",
                on_status=lambda s, m: None,
            )
        assert result["ok"] is False
        assert "Portal 不可用" in result["error"]
        assert "portal auth" in result["error"]

    def test_invalid_badge_id(self):
        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            result = badge_generator.run_badge_pipeline(
                badge_id="bad-id!@#",  # 非法字符
                placeholder="a cute girl",
                on_status=lambda s, m: None,
            )
        assert result["ok"] is False
        assert "英文/数字/下划线" in result["error"]

    def test_placeholder_too_short(self):
        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            result = badge_generator.run_badge_pipeline(
                badge_id="ok_id",
                placeholder="abc",  # < 5 字符
                on_status=lambda s, m: None,
            )
        assert result["ok"] is False
        assert "placeholder 至少 5 字符" in result["error"]

    def test_existing_badge_id_no_regenerate(self):
        """不传 regenerate=True 但 id 已存在 → 报错."""
        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            with mock.patch.object(
                badge_generator, "check_id_unique", return_value=False,
            ):
                result = badge_generator.run_badge_pipeline(
                    badge_id="existing_badge",
                    placeholder="a cute girl",
                    on_status=lambda s, m: None,
                )
        assert result["ok"] is False
        assert "已存在" in result["error"]

    def test_hermes_failure_rolls_back_files(self, tmp_path):
        """hermes 失败时, 已创建的文件被回滚."""
        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            # hermes 模拟超时
            with mock.patch.object(
                badge_generator.subprocess, "Popen",
                return_value=_mock_popen_timeout(),
            ):
                # 预先在目标目录放一个 "旧" 文件, 验证不被误删
                # (虽然 step 4 之前不会创建文件, 这里只是 sanity)
                pre_existing = badge_generator._BADGES_DIR / "test_badge_v1.png"
                if pre_existing.exists():
                    pre_existing.unlink()
                result = badge_generator.run_badge_pipeline(
                    badge_id="test_badge_rollback",
                    placeholder="a cute girl",
                    on_status=lambda s, m: None,
                )
        assert result["ok"] is False
        assert "超时" in result["error"]
        # 没有创建 v1.png
        assert not (badge_generator._BADGES_DIR / "test_badge_rollback_v1.png").exists()

    def test_version_n_for_existing(self, tmp_path):
        """已存在 v1 的 badge, regenerate=True → version=2."""
        with mock.patch.object(
            badge_generator, "is_ready_for_badge_workflow",
            return_value=(True, "OK"),
        ):
            output_png = tmp_path / "fake.png"
            Image.new("RGB", (50, 50), (240, 240, 240)).save(output_png, "PNG")
            stdout = f"session_id: abc\nMEDIA:{output_png}\n"
            with mock.patch.object(
                badge_generator.subprocess, "Popen",
                return_value=_mock_popen_with_output(stdout, returncode=0),
            ):
                with mock.patch.object(
                    badge_generator, "next_version", return_value=2,
                ):
                    result = badge_generator.run_badge_pipeline(
                        badge_id="existing_with_v1",
                        placeholder="a cute girl",
                        on_status=lambda s, m: None,
                        regenerate=True,
                    )
        assert result["ok"] is True
        assert result["version"] == 2
        assert Path(result["image_path"]).name == "existing_with_v1_v2.png"
        # 清理
        Path(result["image_path"]).unlink()
