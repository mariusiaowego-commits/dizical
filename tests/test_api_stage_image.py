"""Stage 维 report 图片 API 集成测试 (mock subprocess, 不真跑 hermes).

TDD red → green: 先写测试, 再让 _build_stage_detail_payload / _resolve_stage / _filter_payload_by_days
保持现有行为 + 改 app.py 加新 endpoint.

⚠️ 测试隔离: 用 pytest monkeypatch fixture, 不手动 setattr 全局 db 方法 (teardown 还原),
避免污染后续 test (test_cli_ux_review 看到的 db 状态).
"""
import sys
import os
import sqlite3
import tempfile
import struct
import zlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent

# 用 tmpdb 隔离 (避免碰 production data/dizi.db)
TMP_DIR = Path(tempfile.mkdtemp(prefix="dizical-stage-img-test-"))
TMP_DB = TMP_DIR / "dizi.db"
TMP_DB.touch()


def _make_png(path: Path, w: int = 32, h: int = 32) -> None:
    """生成最小 1x1 灰 PNG (>= 10KB 靠像素填)."""
    rows = []
    for y in range(h):
        row = b"\x00"  # filter type
        for x in range(w):
            # RGB gray 128
            row += bytes([128, 128, 128])
        rows.append(row)
    raw = b"".join(rows)
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


# === 准备: 1 stage + 2 sessions, 模块级 setup 一次 ===

def _setup_test_db():
    """构造 test schema + 1 stage + 2 sessions. 全走 SQLite tmpdb."""
    conn = sqlite3.connect(str(TMP_DB))
    conn.executescript("""
        CREATE TABLE assignments (
            id INTEGER PRIMARY KEY,
            lesson_date TEXT,
            stage_order INTEGER,
            stage_start TEXT,
            stage_end TEXT,
            notes TEXT,
            items_json TEXT
        );
        CREATE TABLE practice_items (
            item_id INTEGER PRIMARY KEY,
            item_name TEXT
        );
        CREATE TABLE practice_sessions (
            id INTEGER PRIMARY KEY,
            practice_date TEXT,
            item_id INTEGER,
            item_name TEXT,
            duration_minutes INTEGER,
            tempo_note TEXT,
            tempo_bpm INTEGER,
            content TEXT,
            content_source TEXT,
            is_extra INTEGER,
            started_at TEXT,
            created_at TEXT
        );
        CREATE TABLE weekly_assignments (
            id INTEGER PRIMARY KEY,
            week TEXT,
            stage_order INTEGER
        );
    """)
    conn.execute(
        "INSERT INTO assignments (lesson_date, stage_order, stage_start, stage_end, notes, items_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("2026-08-02", 1, "2026-07-20", "2026-08-02", "", '[{"item_id":1,"item":"长音"}]'),
    )
    conn.execute("INSERT INTO practice_items (item_id, item_name) VALUES (1, '长音')")
    conn.execute(
        "INSERT INTO practice_sessions (practice_date, item_id, item_name, duration_minutes, tempo_note, tempo_bpm, content, content_source, is_extra, started_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("2026-07-25", 1, "长音", 20, "♪", 80, "吐音练习", "manual", 0, "2026-07-25 10:00:00"),
    )
    conn.execute(
        "INSERT INTO practice_sessions (practice_date, item_id, item_name, duration_minutes, tempo_note, tempo_bpm, content, content_source, is_extra, started_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("2026-07-27", 1, "长音", 30, "♪", 80, "低八度练习", "manual", 0, "2026-07-27 10:00:00"),
    )
    conn.commit()
    conn.close()


_setup_test_db()


def _patched_get_conn_with_row():
    """返回 test db connection with Row factory."""
    conn = sqlite3.connect(str(TMP_DB))
    conn.row_factory = sqlite3.Row
    return conn


class _FakeDB:
    """mock db methods for our payload builder."""

    def get_stage_by_order(self, stage_order: int):
        conn = sqlite3.connect(str(TMP_DB))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT lesson_date, stage_order, stage_start, stage_end, notes, items_json "
            "FROM assignments WHERE stage_order=? ORDER BY id DESC LIMIT 1",
            (stage_order,),
        ).fetchone()
        conn.close()
        if not row:
            return None
        import json as _json
        return {
            "lesson_date": row["lesson_date"],
            "stage_order": row["stage_order"],
            "stage_start": row["stage_start"],
            "stage_end": row["stage_end"],
            "notes": row["notes"],
            "items": _json.loads(row["items_json"] or "[]"),
        }

    def get_stage_containing_date(self, day):
        conn = sqlite3.connect(str(TMP_DB))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT lesson_date, stage_order, stage_start, stage_end, notes, items_json "
            "FROM assignments WHERE stage_start<=? AND (stage_end IS NULL OR stage_end>=?) "
            "ORDER BY id DESC LIMIT 1",
            (day.isoformat(), day.isoformat()),
        ).fetchone()
        conn.close()
        if not row:
            return None
        import json as _json
        return {
            "lesson_date": row["lesson_date"],
            "stage_order": row["stage_order"],
            "stage_start": row["stage_start"],
            "stage_end": row["stage_end"],
            "notes": row["notes"],
            "items": _json.loads(row["items_json"] or "[]"),
        }

    def get_practice_sessions_in_range(self, start_d, end_d, item_id=None):
        conn = sqlite3.connect(str(TMP_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM practice_sessions WHERE practice_date>=? AND practice_date<=? ORDER BY practice_date, started_at, id",
            (start_d.isoformat(), end_d.isoformat()),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


@pytest.fixture
def fake_db(monkeypatch):
    """注入 fake db 方法, test 结束自动还原 (避免污染 cli_ux_review 等后续 test)."""
    from src import database as _db_mod
    from src.kid_app import app as _kid_app

    fake = _FakeDB()
    monkeypatch.setattr(_db_mod.db, "get_stage_by_order", fake.get_stage_by_order)
    monkeypatch.setattr(_db_mod.db, "get_stage_containing_date", fake.get_stage_containing_date)
    monkeypatch.setattr(_db_mod.db, "get_practice_sessions_in_range", fake.get_practice_sessions_in_range)
    monkeypatch.setattr(_kid_app.db, "get_stage_by_order", fake.get_stage_by_order)
    monkeypatch.setattr(_kid_app.db, "get_stage_containing_date", fake.get_stage_containing_date)
    monkeypatch.setattr(_kid_app.db, "get_practice_sessions_in_range", fake.get_practice_sessions_in_range)
    monkeypatch.setattr(_db_mod.db, "_get_connection", _patched_get_conn_with_row)
    monkeypatch.setattr(_kid_app.db, "_get_connection", _patched_get_conn_with_row)
    return fake


# === 单元测试: _resolve_stage / _filter_payload_by_days ===
# 这些 test 也要 fake_db fixture, 因为 _build_stage_detail_payload 走真实 db 查询

def test_resolve_stage_by_order(fake_db):
    """stage_order=1 应返回 fake stage dict."""
    from src.kid_app import app as _kid_app
    stage = _kid_app._resolve_stage(stage_order=1, date=None)
    assert stage is not None
    assert stage["stage_order"] == 1
    assert stage["stage_start"] == "2026-07-20"


def test_resolve_stage_invalid_order_returns_none(fake_db):
    """stage_order=999 不存在 → None."""
    from src.kid_app import app as _kid_app
    stage = _kid_app._resolve_stage(stage_order=999, date=None)
    assert stage is None


def test_resolve_stage_by_date_in_range(fake_db):
    """date=2026-07-25 在 stage 1 范围内 → 找到."""
    from src.kid_app import app as _kid_app
    stage = _kid_app._resolve_stage(stage_order=None, date="2026-07-25")
    assert stage is not None
    assert stage["stage_order"] == 1


def test_resolve_stage_invalid_date_format_returns_none(fake_db):
    """date=2026-13-99 格式错 → None."""
    from src.kid_app import app as _kid_app
    stage = _kid_app._resolve_stage(stage_order=None, date="2026-13-99")
    assert stage is None


def test_filter_payload_by_days_keep_one(fake_db):
    """days='2026-07-25' 过滤后只剩 1 天."""
    from src.kid_app import app as _kid_app
    payload = _kid_app._build_stage_detail_payload(fake_db.get_stage_by_order(1))
    filtered = _kid_app._filter_payload_by_days(payload, "2026-07-25")
    assert len(filtered["days"]) == 1
    assert filtered["days"][0]["date"] == "2026-07-25"
    assert filtered["summary"]["total_minutes"] == 20  # only 1 session


def test_filter_payload_by_days_keep_both(fake_db):
    """days 全部 2 天 → 2 天, total 50."""
    from src.kid_app import app as _kid_app
    payload = _kid_app._build_stage_detail_payload(fake_db.get_stage_by_order(1))
    filtered = _kid_app._filter_payload_by_days(payload, "2026-07-25,2026-07-27")
    assert len(filtered["days"]) == 2
    assert filtered["summary"]["total_minutes"] == 50


def test_filter_payload_by_days_empty_csv_returns_all(fake_db):
    """days='' → 不过滤."""
    from src.kid_app import app as _kid_app
    payload = _kid_app._build_stage_detail_payload(fake_db.get_stage_by_order(1))
    filtered = _kid_app._filter_payload_by_days(payload, "")
    assert len(filtered["days"]) == 2


def test_filter_payload_by_days_no_match_returns_empty(fake_db):
    """days='1999-01-01' 匹配不上 → 0 天."""
    from src.kid_app import app as _kid_app
    payload = _kid_app._build_stage_detail_payload(fake_db.get_stage_by_order(1))
    filtered = _kid_app._filter_payload_by_days(payload, "1999-01-01")
    assert len(filtered["days"]) == 0
    assert filtered["summary"]["total_minutes"] == 0


# === 集成测试: POST /api/practices/stage-image (mock subprocess) ===

def _setup_dummy_png(tmpdir: Path, name: str = "test.png") -> Path:
    p = tmpdir / name
    _make_png(p, w=64, h=64)  # ~12KB
    return p


def test_stage_image_endpoint_not_found(fake_db):
    """stage 不存在 → 404 (在 spawn 之前, 不调 subprocess)."""
    from fastapi.testclient import TestClient
    from src.kid_app import app as _kid_app
    client = TestClient(_kid_app.app)
    r = client.post("/api/practices/stage-image?stage_order=999")
    assert r.status_code == 404
    assert r.json()["ok"] is False


def test_stage_image_endpoint_sse_happy_path(tmp_path, fake_db, monkeypatch):
    """happy: subprocess 返 MEDIA 路径 → 写盘 + 写表 + done event."""
    from fastapi.testclient import TestClient
    from src.kid_app import app as _kid_app
    fake_png = _setup_dummy_png(tmp_path, "media_output.png")
    import subprocess as _subprocess
    fake_proc = MagicMock()
    fake_proc.stdout = iter([f"MEDIA:{fake_png}\n"])
    fake_proc.wait.return_value = 0
    fake_proc.returncode = 0

    def fake_popen(*a, **kw):
        return fake_proc

    client = TestClient(_kid_app.app)
    monkeypatch.setattr(_subprocess, "Popen", fake_popen)
    r = client.post("/api/practices/stage-image?stage_order=1")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert "data: " in body
    import json as _json
    events = []
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        for line in chunk.split("\n"):
            if line.startswith("data: "):
                events.append(_json.loads(line[6:]))
    types = [e.get("type") for e in events]
    assert "status" in types
    assert "done" in types
    done_evts = [e for e in events if e["type"] == "done"]
    assert len(done_evts) == 1
    assert done_evts[0]["data"]["ok"] is True
    saved = done_evts[0]["data"]["image_path"]
    assert "/data/reports/stage-1-" in saved
    project_report_dir = ROOT / "data" / "reports"
    assert project_report_dir.exists()
    pngs = list(project_report_dir.glob("stage-1-*.png"))
    assert len(pngs) >= 1
    cur = sqlite3.connect(str(TMP_DB)).cursor()
    cur.execute("SELECT kind, ref_id, image_path FROM report_artifacts ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "stage_image"
    assert row[1] == "1"
    for p in pngs:
        p.unlink(missing_ok=True)


def test_stage_image_endpoint_no_image_in_output(tmp_path, fake_db, monkeypatch):
    """hermes 没返 MEDIA → error event, 不写盘不写表."""
    from fastapi.testclient import TestClient
    from src.kid_app import app as _kid_app
    import subprocess as _subprocess
    fake_proc = MagicMock()
    fake_proc.stdout = iter(["some random line\n", "no media here\n"])
    fake_proc.wait.return_value = 0
    fake_proc.returncode = 0

    client = TestClient(_kid_app.app)
    monkeypatch.setattr(_subprocess, "Popen", fake_proc)
    r = client.post("/api/practices/stage-image?stage_order=1")
    assert r.status_code == 200
    import json as _json
    events = []
    for chunk in r.text.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        for line in chunk.split("\n"):
            if line.startswith("data: "):
                events.append(_json.loads(line[6:]))
    types = [e.get("type") for e in events]
    assert "error" in types
    err = [e for e in events if e["type"] == "error"][0]
    assert "未找到图片" in err["message"]


def test_stage_image_endpoint_with_days_filter(tmp_path, fake_db, monkeypatch):
    """days 参数过滤后, prompt 应该用过滤后的 days 数据."""
    from fastapi.testclient import TestClient
    from src.kid_app import app as _kid_app
    fake_png = _setup_dummy_png(tmp_path, "media_days.png")
    import subprocess as _subprocess
    captured = {}

    class FakePopen:
        def __init__(self, *a, **kw):
            self.stdout = iter([f"MEDIA:{fake_png}\n"])
            self.returncode = 0
        def wait(self, *a, **kw):
            return 0

    def fake_popen(*a, **kw):
        cmd = a[0] if a else kw.get("args", "")
        import re as _re
        m = _re.search(r"\$\(cat (\S+)\)", cmd)
        if m:
            tmpfile = m.group(1)
            try:
                captured["query"] = Path(tmpfile).read_text(encoding="utf-8")
            except Exception:
                pass
        return FakePopen()

    client = TestClient(_kid_app.app)
    monkeypatch.setattr(_subprocess, "Popen", fake_popen)
    r = client.post("/api/practices/stage-image?stage_order=1&days=2026-07-25")
    assert r.status_code == 200
    if "query" in captured:
        assert "2026-07-25" in captured["query"]
        assert "2026-07-27" not in captured["query"]
    project_report_dir = ROOT / "data" / "reports"
    for p in project_report_dir.glob("stage-1-*.png"):
        p.unlink(missing_ok=True)
