"""Tests for teacher requirement video upload pipeline and migration (Sprint 26083001 S1).

5 Critical Cases:
1. COS upload branch (mock cos_uploader)
2. Over 200MB file returns 413 Payload Too Large
3. Unsupported video format (.webm / .avi) returns 400 Bad Request
4. PUT /api/assignments/{date} without videos keeps existing videos (P0 silence wipe prevention)
5. Database migration script idempotency (repeat run without error)
"""
import io
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.kid_app.app import app
    return TestClient(app)


def test_upload_video_cos_branch(client, monkeypatch):
    """Case 1: COS available -> calls cos_uploader.upload_stream and returns COS url."""
    import src.kid_app.cos_client as cos_mod
    import src.kid_app.routes.config as config_mod

    mock_uploader = mock.MagicMock()
    mock_uploader.is_available = True
    mock_uploader.upload_stream.return_value = "https://test-bucket.tcb.qcloud.la/videos/mock123.mp4"

    monkeypatch.setattr(cos_mod, "cos_uploader", mock_uploader)

    fake_video_content = b"\x00\x00\x00 ftypisom" + b"A" * 1024
    files = {"file": ("demo.mp4", io.BytesIO(fake_video_content), "video/mp4")}

    resp = client.post("/config/api/assignments/upload-video", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["url"] == "https://test-bucket.tcb.qcloud.la/videos/mock123.mp4"
    assert data["filename"].endswith(".mp4")
    assert data["size"] == len(fake_video_content)
    assert data["mime"] == "video/mp4"
    assert mock_uploader.upload_stream.called
    called_key = mock_uploader.upload_stream.call_args[0][0]
    assert called_key.startswith("videos/")


def test_upload_video_over_200mb_returns_413(client, monkeypatch):
    """Case 2: Video file exceeding 200MB limit returns 413."""
    import src.kid_app.routes.config as config_mod

    # Monkeypatch MAX_VIDEO_SIZE to smaller value for test speed (e.g. 10KB)
    monkeypatch.setattr(config_mod, "MAX_VIDEO_SIZE", 10 * 1024)

    oversized_content = b"X" * (10 * 1024 + 100)
    files = {"file": ("toolarge.mp4", io.BytesIO(oversized_content), "video/mp4")}

    resp = client.post("/config/api/assignments/upload-video", files=files)
    assert resp.status_code == 413
    data = resp.json()
    assert data["ok"] is False
    assert "超过限制" in data["error"]


def test_upload_video_unsupported_format_returns_400(client):
    """Case 3: Unsupported formats (.webm, .avi, etc.) return 400 Bad Request."""
    files = {"file": ("video.webm", io.BytesIO(b"webm content"), "video/webm")}
    resp = client.post("/config/api/assignments/upload-video", files=files)
    assert resp.status_code == 400
    data = resp.json()
    assert data["ok"] is False
    assert "不支持的格式" in data["error"]

    files_avi = {"file": ("sample.avi", io.BytesIO(b"avi content"), "video/x-msvideo")}
    resp_avi = client.post("/config/api/assignments/upload-video", files=files_avi)
    assert resp_avi.status_code == 400


def test_put_assignment_preserves_existing_videos(client, monkeypatch):
    """Case 4: PUT without videos field preserves existing videos (P0 wipe prevention)."""
    import src.kid_app.routes.config as config_mod

    fake_db = mock.MagicMock()
    existing_assignment = {
        "id": 10,
        "lesson_date": "2026-08-30",
        "items": [{"item": "长音练习", "requirements": "5分钟"}],
        "notes": "旧备注",
        "images": ["https://cdn.com/img1.jpg"],
        "videos": [
            {
                "url": "https://cdn.com/videos/vid1.mp4",
                "filename": "vid1.mp4",
                "item_label": "长音练习",
                "size_bytes": 10240,
            }
        ],
    }
    fake_db.get_weekly_assignment.return_value = existing_assignment
    mock_conn = mock.MagicMock()
    fake_db._get_connection.return_value.__enter__.return_value = mock_conn

    monkeypatch.setattr(config_mod, "db", fake_db)

    # PUT request without 'videos' field
    payload = {
        "items": [{"item": "长音练习", "requirements": "更新要求为10分钟"}],
        "notes": "新备注",
    }
    resp = client.put("/config/api/assignments/2026-08-30", json=payload)
    assert resp.status_code == 200

    # Ensure db.save_weekly_assignment was called with preserved existing videos
    assert fake_db.save_weekly_assignment.called
    call_kwargs = fake_db.save_weekly_assignment.call_args
    # signature: (ld, formatted, notes=..., images=..., videos=...)
    passed_videos = call_kwargs[1].get("videos") or (call_kwargs[0][4] if len(call_kwargs[0]) > 4 else None)
    assert passed_videos == existing_assignment["videos"]


def test_migration_add_videos_column_idempotent(tmp_path):
    """Case 5: Migration script idempotency on SQLite and MySQL."""
    from src.migrate_add_videos_column import migrate_sqlite, migrate_mysql

    test_db_path = str(tmp_path / "test_dizi.db")
    conn = sqlite3.connect(test_db_path)
    conn.execute(
        """
        CREATE TABLE weekly_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_date DATE NOT NULL,
            items TEXT NOT NULL DEFAULT '[]',
            notes TEXT,
            images TEXT NOT NULL DEFAULT '[]'
        )
    """
    )
    conn.commit()
    conn.close()

    # First run -> adds column
    res1 = migrate_sqlite(test_db_path)
    assert "successfully added" in res1

    # Verify column exists
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(weekly_assignments)")
    cols = [r[1] for r in cursor.fetchall()]
    assert "videos" in cols
    conn.close()

    # Second run -> idempotent
    res2 = migrate_sqlite(test_db_path)
    assert "already exists" in res2

    # MySQL branch mock test
    with mock.patch("src.database_mysql.MySQLBackend") as mock_mysql_cls:
        mock_backend = mock.MagicMock()
        mock_mysql_cls.return_value = mock_backend
        mock_conn = mock.MagicMock()
        mock_backend._get_connection.return_value.__enter__.return_value = mock_conn
        mock_cursor = mock.MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock column not exists first
        mock_cursor.fetchone.return_value = {"c": 0}
        res_my1 = migrate_mysql("mysql+pymysql://root:pass@localhost:3306/dizi")
        assert "successfully added" in res_my1

        # Mock column exists next
        mock_cursor.fetchone.return_value = {"c": 1}
        res_my2 = migrate_mysql("mysql+pymysql://root:pass@localhost:3306/dizi")
        assert "already exists" in res_my2


def test_upload_empty_video_returns_400(client):
    """Case 6: Empty 0-byte video returns 400 Bad Request."""
    files = {"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")}
    resp = client.post("/config/api/assignments/upload-video", files=files)
    assert resp.status_code == 400
    data = resp.json()
    assert data["ok"] is False
    assert "为空" in data["error"]


def test_api_get_assignments_includes_videos(client, monkeypatch):
    """Case 7: GET /config/api/assignments returns videos field."""
    import src.kid_app.routes.config as config_mod
    import datetime as dt

    fake_assignments = [
        {
            "id": 1,
            "lesson_date": dt.date(2026, 8, 30),
            "stage_start": dt.date(2026, 8, 31),
            "stage_end": dt.date(2026, 9, 6),
            "stage_order": 20,
            "items": [{"item": "长音练习", "requirements": "5分钟"}],
            "notes": "备注",
            "images": ["https://cdn.com/img.jpg"],
            "videos": [
                {
                    "url": "https://cdn.com/videos/v1.mp4",
                    "filename": "v1.mp4",
                    "item_id": 1001,
                    "item_label": "长音练习",
                }
            ],
        }
    ]

    monkeypatch.setattr(config_mod.practice_module, "query_assignments", lambda weeks=8: fake_assignments)

    resp = client.get("/config/api/assignments?weeks=8")
    assert resp.status_code == 200
    data = resp.json()
    assert "assignments" in data
    first = data["assignments"][0]
    assert "videos" in first
    assert len(first["videos"]) == 1
    assert first["videos"][0]["filename"] == "v1.mp4"
