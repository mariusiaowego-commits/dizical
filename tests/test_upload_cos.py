"""PR-F: /uploads 切 COS 测试.

策略: mock CosUploader, 不真连 COS. 验证:
1. 有 COS 配置 → 上传走 COS, 返回 COS URL
2. 无 COS 配置 → 回落本地, 返回 /uploads/raw/ URL
3. 格式白名单: 不支持的格式 → 400
4. HEIC/HEIF 拒绝 (2026-08-09 需求6): 上传端拦截, 提示转 jpg/png
5. COS 上传失败 → 500 (fail loud)
"""
import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def client(tmp_path):
    """TestClient + 隔离 uploads 目录."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    # 隔离 _UPLOAD_RAW
    import src.kid_app.routes.config as cfg
    cfg._UPLOAD_RAW = tmp_path / "uploads_raw"
    cfg._UPLOAD_RAW.mkdir(parents=True, exist_ok=True)

    with TestClient(app) as c:
        yield c, cfg


def _png_bytes() -> bytes:
    """最小合法 PNG (1x1)."""
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d494844520000000100000001080600000"
        "01f15c4890000000d49444154789c626001000000ffff030000060005"
        "57bfabd40000000049454e44ae426082"
    )


class TestCosUploadAvailable:
    """COS 配置存在 → 走 COS."""

    def test_upload_goes_cos(self, client, monkeypatch):
        c, cfg = client
        from src.kid_app import cos_client as cos_mod
        class FakeUploader:
            is_available = True
            def upload(self, filename, content, content_type="image/jpeg"):
                assert filename.endswith(".png")
                return f"https://636c-cloud1-d4gfwyvsk1435e2e4-1454535414.tcb.qcloud.la/{filename}"
        monkeypatch.setattr(cos_mod, "cos_uploader", FakeUploader())

        resp = c.post(
            "/config/api/assignments/upload",
            files={"file": ("test.png", _png_bytes(), "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["url"].startswith("https://636c-cloud1-d4gfwyvsk1435e2e4-1454535414.tcb.qcloud.la/")
        assert data["url"].endswith(".png")

    def test_cos_upload_failure_returns_500(self, client, monkeypatch):
        c, cfg = client
        from src.kid_app import cos_client as cos_mod
        class FailingUploader:
            is_available = True
            def upload(self, filename, content, content_type="image/jpeg"):
                raise RuntimeError("COS 连接失败")
        monkeypatch.setattr(cos_mod, "cos_uploader", FailingUploader())

        resp = c.post(
            "/config/api/assignments/upload",
            files={"file": ("test.png", _png_bytes(), "image/png")},
        )
        assert resp.status_code == 500
        assert "COS 上传失败" in resp.json()["error"]


class TestCosUploadUnavailable:
    """无 COS 配置 → 回落本地 (开发环境)."""

    def test_upload_falls_back_to_local(self, client, monkeypatch):
        c, cfg = client
        from src.kid_app import cos_client as cos_mod
        class LocalUploader:
            is_available = False
        monkeypatch.setattr(cos_mod, "cos_uploader", LocalUploader())

        resp = c.post(
            "/config/api/assignments/upload",
            files={"file": ("test.png", _png_bytes(), "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["url"].startswith("/uploads/raw/")
        # 文件确实写在本地
        fname = data["filename"]
        assert (cfg._UPLOAD_RAW / fname).exists()


class TestFormatWhitelist:
    """格式白名单."""

    def test_unsupported_format_400(self, client, monkeypatch):
        c, cfg = client
        from src.kid_app import cos_client as cos_mod
        class AnyUploader:
            is_available = True
            def upload(self, *a, **k):
                raise AssertionError("不该被调用")
        monkeypatch.setattr(cos_mod, "cos_uploader", AnyUploader())

        resp = c.post(
            "/config/api/assignments/upload",
            files={"file": ("test.gif", b"GIF89a", "image/gif")},
        )
        assert resp.status_code == 400
        assert "不支持的格式" in resp.json()["error"]


class TestHeicRejected:
    """2026-08-09 (需求6): HEIC/HEIF 直接拒绝 (dad 拍板: 用户自行转 jpg/png).

    旧行为是 sips 转换上传, 但 CloudRun Linux 容器无 sips → heic 原样存 COS →
    Chrome 无法预览. 现在上传端拦截, 提示用户转格式.
    """

    def test_heic_rejected_400(self, client, monkeypatch):
        c, cfg = client
        from src.kid_app import cos_client as cos_mod
        class AnyUploader:
            is_available = True
            def upload(self, *a, **k):
                raise AssertionError("不该被调用")
        monkeypatch.setattr(cos_mod, "cos_uploader", AnyUploader())

        resp = c.post(
            "/config/api/assignments/upload",
            files={"file": ("photo.heic", b"\x00\x00\x00\x18ftypheic", "image/heic")},
        )
        assert resp.status_code == 400
        assert "HEIC" in resp.json()["error"]

    def test_heif_rejected_400(self, client, monkeypatch):
        c, cfg = client
        from src.kid_app import cos_client as cos_mod
        class AnyUploader:
            is_available = True
            def upload(self, *a, **k):
                raise AssertionError("不该被调用")
        monkeypatch.setattr(cos_mod, "cos_uploader", AnyUploader())

        resp = c.post(
            "/config/api/assignments/upload",
            files={"file": ("photo.heif", b"\x00\x00\x00\x18ftypheic", "image/heif")},
        )
        assert resp.status_code == 400
        assert "HEIC" in resp.json()["error"]

    def test_jpg_still_ok(self, client, monkeypatch):
        """jpg 正常上传不受影响."""
        c, cfg = client
        from src.kid_app import cos_client as cos_mod
        class FakeUploader:
            is_available = True
            def upload(self, filename, content, content_type="image/jpeg"):
                return f"https://636c-cloud1-d4gfwyvsk1435e2e4-1454535414.tcb.qcloud.la/{filename}"
        monkeypatch.setattr(cos_mod, "cos_uploader", FakeUploader())

        resp = c.post(
            "/config/api/assignments/upload",
            files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["url"].endswith(".jpg")
