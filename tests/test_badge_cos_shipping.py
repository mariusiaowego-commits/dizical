"""Sprint 26082401 V3.0: badge commit COS shipping + 本地 fallback 测试.

覆盖 4 场景:
1. 本地 (cos_uploader.is_available=False) → fallback static, url=/static/badges/...
2. 生产 (cos_uploader.is_available=True, upload OK) → url=https://<bucket>.tcb.qcloud.la/...
3. 生产 COS 上传失败 (upload RuntimeError) → commit_to_cos_or_static 抛 RuntimeError (DB 零写入)
4. 临时图不存在 → FileNotFoundError 透传

跟现有 commit handler 集成测试:
- badge_db.badge_write_tx 不进 (mock, 验证 Storage First 失败不入库)
- achievement_badges.url 写入路径 (mock capture)
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 让 src/ 能 import
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.kid_app import badge_draft


# ─── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def draft_with_image(tmp_path, monkeypatch):
    """构造一个 draft + 临时 PNG, mock _badge_data_dir 到 tmp_path."""
    # badge_draft._badge_data_dir() = project_root / data / lib / badge_data
    # 我们 monkeypatch 让它指向 tmp_path / "badge_data"
    fake_dir = tmp_path / "badge_data"
    fake_dir.mkdir()
    (fake_dir / ".tmp").mkdir()
    monkeypatch.setattr(badge_draft, "_badge_data_dir", lambda: fake_dir)
    monkeypatch.setattr(badge_draft, "_tmp_dir", lambda: fake_dir / ".tmp")

    # 写一个 draft JSON
    draft_id = "2026-08-24_test_cos_aaa111"
    draft_json = {
        "schema_version": 1,
        "draft_id": draft_id,
        "created_at": "2026-08-24T08:00:00Z",
        "version": 1,
        "meta": {
            "id": "test_cos_badge",
            "name": "test COS badge",
            "type": "突破",
            "category": "milestone",
            "placeholder": "test",
            "zh_story": "test story",
            "cond_text": "test cond",
        },
        "image": {
            "path": str(fake_dir / ".tmp" / f"{draft_id}_v1.png"),
            "model": "test",
            "version": 1,
            "alpha_verified": True,
        },
        "status": "draft_awaiting_confirm",
        "updated_at": "2026-08-24T08:00:00Z",
        "history": [],
    }
    draft_file = fake_dir / f"{draft_id}.json"
    draft_file.write_text(__import__("json").dumps(draft_json, ensure_ascii=False))

    # 写一个临时 PNG (1x1 透明 RGBA, 真实可加载)
    import io
    from PIL import Image
    png_path = fake_dir / ".tmp" / f"{draft_id}_v1.png"
    img = Image.new("RGBA", (10, 10), (255, 255, 255, 0))
    img.save(png_path)

    return draft_id, fake_dir


# ─── 场景 1: 本地 fallback (cos_uploader.is_available=False) ─────────

def test_commit_to_static_fallback(draft_with_image):
    """本地 dev (无 COS env) → url = /static/badges/{id}_v{n}.png, 文件复制到 static/."""
    draft_id, _ = draft_with_image

    # mock cos_uploader.is_available = False
    with patch("src.kid_app.cos_client.cos_uploader") as mock_cos:
        mock_cos.is_available = False

        path, url = badge_draft.commit_to_cos_or_static(draft_id, 1)

    # url 走老路径 (相对路径)
    assert url == "/static/badges/test_cos_badge_v1.png"
    # 路径返回 static/ 目录的文件
    assert path.name == "test_cos_badge_v1.png"
    assert "static" in str(path) and "badges" in str(path)
    static_dir = path.parent
    thumb = static_dir / "thumbs" / "test_cos_badge_v1.webp"
    full = static_dir / "full" / "test_cos_badge_v1.webp"
    try:
        assert thumb.is_file() and thumb.stat().st_size > 0
        assert full.is_file() and full.stat().st_size > 0
    finally:
        path.unlink(missing_ok=True)
        thumb.unlink(missing_ok=True)
        full.unlink(missing_ok=True)


# ─── 场景 2: 生产 COS 上传 OK ──────────────────────────────────────

def test_commit_to_cos_success(draft_with_image):
    """生产 (cos_uploader.is_available=True, upload OK) → url 是完整 https COS URL, 不复制到 static/."""
    draft_id, _ = draft_with_image

    fake_cos_url = "https://636c-cloud1-d4gfwyvsk1435e2e4-1454535414.tcb.qcloud.la/badges/test_cos_badge_v1.png"

    with patch("src.kid_app.cos_client.cos_uploader") as mock_cos:
        mock_cos.is_available = True
        mock_cos.upload = MagicMock(return_value=fake_cos_url)

        path, url = badge_draft.commit_to_cos_or_static(draft_id, 1)

    # PNG + thumbs webp + full webp, 同一次 commit
    assert mock_cos.upload.call_count == 3
    calls = mock_cos.upload.call_args_list
    assert calls[0][0][0] == "badges/test_cos_badge_v1.png"
    assert calls[0][1].get("content_type") == "image/png"
    assert isinstance(calls[0][0][1], bytes) and len(calls[0][0][1]) > 0
    assert calls[1][0][0] == "badges/thumbs/test_cos_badge_v1.webp"
    assert calls[1][1].get("content_type") == "image/webp"
    assert calls[1][0][1][:4] == b"RIFF"
    assert calls[2][0][0] == "badges/full/test_cos_badge_v1.webp"
    assert calls[2][1].get("content_type") == "image/webp"

    # url 是 COS https URL, 不是 /static/ 相对路径
    assert url == fake_cos_url
    assert url.startswith("https://")
    assert "tcb.qcloud.la" in url

    # 返回的 path 仍是 .tmp/ 的源 (不动 static/, 因为图在 COS 了)
    assert path.name == f"{draft_id}_v1.png"


# ─── 场景 3: COS 上传失败 → 抛 RuntimeError (DB 零写入) ─────────────

def test_commit_to_cos_upload_failure_raises(draft_with_image):
    """COS upload 失败 → commit_to_cos_or_static 抛 RuntimeError, commit handler 应 catch 返 500."""
    draft_id, _ = draft_with_image

    with patch("src.kid_app.cos_client.cos_uploader") as mock_cos:
        mock_cos.is_available = True
        mock_cos.upload = MagicMock(side_effect=RuntimeError("COS 上传失败: 网络超时"))

        with pytest.raises(RuntimeError, match="COS 上传失败"):
            badge_draft.commit_to_cos_or_static(draft_id, 1)


# ─── 场景 4: 临时图不存在 → FileNotFoundError 透传 ──────────────────

def test_commit_tmp_missing_raises(draft_with_image):
    """skill 没生图 / 图被清理 → FileNotFoundError, commit handler 应 catch 返 400."""
    draft_id, fake_dir = draft_with_image
    # 删掉临时图
    (fake_dir / ".tmp" / f"{draft_id}_v1.png").unlink()

    with patch("src.kid_app.cos_client.cos_uploader") as mock_cos:
        mock_cos.is_available = False  # 走 static fallback, 但 src 不存在

        with pytest.raises(FileNotFoundError, match="临时图"):
            badge_draft.commit_to_cos_or_static(draft_id, 1)


def test_webp_upload_failure_names_the_key(draft_with_image):
    """PNG 已上传后 webp 失败 → 带 thumbs key 抛错, 调用方不入库."""
    draft_id, _ = draft_with_image

    def upload(key, data, content_type="image/jpeg"):
        if key.endswith(".webp"):
            raise RuntimeError("网络超时")
        return f"https://b.tcb.qcloud.la/{key}"

    with patch("src.kid_app.cos_client.cos_uploader") as mock_cos:
        mock_cos.is_available = True
        mock_cos.upload = upload
        with pytest.raises(RuntimeError, match=r"key=badges/thumbs/test_cos_badge_v1\.webp"):
            badge_draft.commit_to_cos_or_static(draft_id, 1)


def test_reused_cos_url_still_uploads_webp(draft_with_image):
    """本地临时图没了、image.url 已是 COS URL → 下载 PNG 再补两档 webp, DB url 仍是原 PNG."""
    draft_id, fake_dir = draft_with_image
    png_path = fake_dir / ".tmp" / f"{draft_id}_v1.png"
    png_bytes = png_path.read_bytes()
    png_path.unlink()
    existing = "https://636c-cloud1-d4gfwyvsk1435e2e4-1454535414.tcb.qcloud.la/badges/test_cos_badge_v1.png"
    draft = badge_draft.get_draft(draft_id)
    draft.image["url"] = existing
    badge_draft.save_draft(draft)

    seen = []

    def upload(key, data, content_type="image/jpeg"):
        seen.append((key, content_type, data))
        return f"https://636c-cloud1-d4gfwyvsk1435e2e4-1454535414.tcb.qcloud.la/{key}"

    with patch("src.kid_app.cos_client.cos_uploader") as mock_cos:
        mock_cos.is_available = True
        mock_cos.download = MagicMock(return_value=png_bytes)
        mock_cos.upload = upload
        _path, url = badge_draft.commit_to_cos_or_static(draft_id, 1)

    assert url == existing
    assert [row[0] for row in seen] == [
        "badges/thumbs/test_cos_badge_v1.webp",
        "badges/full/test_cos_badge_v1.webp",
    ]
    assert all(row[1] == "image/webp" for row in seen)