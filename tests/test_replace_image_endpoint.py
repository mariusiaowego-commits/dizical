"""2026-07-01 feat/badges-streak-image-regen.

测 POST /config/api/badge/replace-image-from-draft.
走 conftest 里 _ensure_badge_tables fixture 已创的 tmp db, 不碰 prod.
需要在 tmp_db_path 注入 streak_7 row (achievements + achievement_badges) 才能过 happy path.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterator

import pytest

# 跟 conftest 一致: settings.db_path 是 session fixture 在 runtime 设置的
# 这里唯一拿到 db_path 的方法是临时 import settings (已被 monkeypatch 改了)
DRAFT_DIR = Path(__file__).parent.parent / "data" / "lib" / "badge_data"
TMP_DIR = DRAFT_DIR / ".tmp"
STATIC_BADGES = Path(__file__).parent.parent / "src" / "kid_app" / "static" / "badges"

ONE_PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c63f8cf0000000300010073a6cb710000000049454e44ae426082"
)


def _tmp_db_path() -> Path:
    """Session-scope: 拿 conftest 创的 tmp db 路径 (跟 src.database.db 同步)."""
    from src.models import settings
    return Path(settings.db_path)


def _ensure_streak_7_in_db():
    """保证 tmp db 里 streak_7 row 存在 (achievements + achievement_badges).
    Tests 无 destructive 操作 (DELETE/REPLACE); delete_per_test 又 reset 回 baseline."""
    conn = sqlite3.connect(str(_tmp_db_path()))
    try:
        cur = conn.execute("SELECT 1 FROM achievements WHERE id=?", ("streak_7",))
        if cur.fetchone() is None:
            conn.execute("""
                INSERT INTO achievements
                  (id, name, type, category, stat_logic, description, display_format, sort_order)
                VALUES ('streak_7', '周冠军', '突破', 'milestone', '连续 >= 7 天', '历史首次连续 ≥ 7 天',
                        'achieved_flag', 0)
            """)
        cur = conn.execute("SELECT 1 FROM achievement_badges WHERE achievement_id=? AND is_current=1",
                          ("streak_7",))
        if cur.fetchone() is None:
            conn.execute("""
                INSERT INTO achievement_badges
                  (achievement_id, url, is_locked, version, is_current)
                VALUES ('streak_7', '/static/badges/streak_7.png', 0, 1, 1)
            """)
        conn.commit()
    finally:
        conn.close()


def _read_body(resp) -> dict:
    raw = resp.body
    if isinstance(raw, (bytes, bytearray)):
        return json.loads(raw)
    if isinstance(raw, str):
        return json.loads(raw)
    raise TypeError(f"unexpected body type {type(raw)}")


@pytest.fixture
def fresh_draft(monkeypatch, tmp_path) -> Iterator[tuple[str, Path]]:
    """建一个 draft_awaiting_confirm draft. 跑完 cleanup.

    P0-2026-08-05 修复: 自建独立临时 DB, 把 badge_db.db / db_module.db /
    app_module.db / settings.db_path 全部 patch 到这一个库.
    旧设计 (注释声称"走 conftest tmp db 不碰 prod") 从未成立:
    conftest session fixture 只改 settings.db_path, 而 api_replace 走 badge_db.db
    (模块顶层绑定原单例 = prod). 单独跑时 settings 恰好也是 prod 自洽通过;
    全量跑时 settings=conftest tmp 而 badge_db.db=prod → 不一致 → 失败, 且污染生产库.
    """
    from src.kid_app import badge_db
    from src import database as db_module
    from src import models
    import src.kid_app.app as app_module
    from src.database import Database

    # 1. 自建独立临时 DB (跟 conftest / 其他测试完全隔离)
    db_file = tmp_path / "replace_test.db"
    new_db = Database(db_path=str(db_file))

    # 1b. 建 badge 三表 (Database 只建基础表, badge 表需手动建, 跟 conftest _ensure_badge_tables 同 SQL)
    _conn = sqlite3.connect(str(db_file))
    _conn.executescript("""
        CREATE TABLE IF NOT EXISTS achievements (
            id                TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            type              TEXT NOT NULL,
            category          TEXT NOT NULL DEFAULT 'milestone',
            stat_logic        TEXT NOT NULL,
            description       TEXT NOT NULL,
            display_format    TEXT NOT NULL,
            threshold         INTEGER,
            unlocked_template TEXT,
            placeholder       TEXT,
            locked_template   TEXT,
            sort_order        INTEGER DEFAULT 0,
            seasonal_type     TEXT DEFAULT 'monthly',
            cond_text         TEXT,
            unlock_strategy   TEXT DEFAULT 'calc',
            achieved_at_override TEXT,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS achievement_stats (
            achievement_id TEXT PRIMARY KEY,
            achieved       TEXT NOT NULL DEFAULT 'N',
            raw_stats      TEXT NOT NULL DEFAULT '{}',
            achieved_at    DATETIME,
            computed_value INTEGER
        );
        CREATE TABLE IF NOT EXISTS achievement_badges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            achievement_id  TEXT NOT NULL,
            url             TEXT NOT NULL,
            is_locked       INTEGER NOT NULL DEFAULT 0,
            version         INTEGER NOT NULL DEFAULT 1,
            is_current      INTEGER NOT NULL DEFAULT 1,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    _conn.commit()
    _conn.close()

    # 2. 四个入口全部指向这个库 (badge_db.db 是 api_replace 用的, 必须一致)
    monkeypatch.setattr(models.settings, "db_path", str(db_file))
    monkeypatch.setattr(db_module, "db", new_db)
    monkeypatch.setattr(badge_db, "db", new_db)
    monkeypatch.setattr(app_module, "db", new_db)

    _ensure_streak_7_in_db()  # 往独立库注入 streak_7 baseline (非 prod)

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    draft_id = "2026-07-01_test-replace_abcdef"
    draft_path = DRAFT_DIR / f"{draft_id}.json"
    tmp_png = TMP_DIR / f"{draft_id}_v1.png"
    tmp_png.write_bytes(ONE_PX)

    draft = {
        "draft_id": draft_id,
        "meta": {"id": "streak_7", "name": "周冠军", "category": "milestone"},
        "image": {"path": str(tmp_png), "version": 1, "alpha_verified": True},
        "status": "draft_awaiting_confirm",
        "version": 1,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
        "history": [],
    }
    draft_path.write_text(json.dumps(draft, ensure_ascii=False))
    yield draft_id, tmp_png

    # teardown
    if draft_path.exists():
        draft_path.unlink()
    for png in [
        tmp_png,
        STATIC_BADGES / "streak_7_v1.png",
    ]:
        if png.exists():
            png.unlink()
    # DB cleanup: 独立临时库, monkeypatch 自动恢复, 无需手动清 (删库文件即可)
    monkeypatch.undo()


def test_replace_happy_path(fresh_draft):
    from src.kid_app.routes.badge_workflow import (
        api_replace_image_from_draft, ReplaceImageFromDraftRequest,
    )

    draft_id, _ = fresh_draft
    req = ReplaceImageFromDraftRequest(draft_id=draft_id, badge_id="streak_7")
    resp = api_replace_image_from_draft(req)
    body = _read_body(resp)

    assert resp.status_code == 200, f"resp body: {body}"
    assert body["ok"] is True
    assert body["badge_id"] == "streak_7"
    assert body["image_url"] == "/static/badges/streak_7_v1.png"
    assert body["version"] == 1
    assert (STATIC_BADGES / "streak_7_v1.png").exists()

    conn = sqlite3.connect(str(_tmp_db_path()))
    try:
        rows = conn.execute(
            "SELECT version, url, is_current FROM achievement_badges "
            "WHERE achievement_id = ? ORDER BY version",
            ("streak_7",),
        ).fetchall()
    finally:
        conn.close()
    assert any(r[2] == 1 for r in rows), "应有 is_current=1 行"
    assert any(r[1] == "/static/badges/streak_7_v1.png" for r in rows), "应有新 url"

    # draft status 已 committed
    draft_after = json.loads((DRAFT_DIR / f"{draft_id}.json").read_text())
    assert draft_after["status"] == "committed"


def test_replace_rejects_wrong_status(fresh_draft):
    from src.kid_app.routes.badge_workflow import (
        api_replace_image_from_draft, ReplaceImageFromDraftRequest,
    )

    draft_id, _ = fresh_draft
    draft_path = DRAFT_DIR / f"{draft_id}.json"
    draft = json.loads(draft_path.read_text())
    draft["status"] = "draft_created"
    draft_path.write_text(json.dumps(draft))

    req = ReplaceImageFromDraftRequest(draft_id=draft_id, badge_id="streak_7")
    resp = api_replace_image_from_draft(req)
    assert resp.status_code == 400
    body = _read_body(resp)
    assert body["ok"] is False
    assert "draft_awaiting_confirm" in body["error"]


def test_replace_rejects_unknown_badge(fresh_draft):
    from src.kid_app.routes.badge_workflow import (
        api_replace_image_from_draft, ReplaceImageFromDraftRequest,
    )

    draft_id, _ = fresh_draft
    req = ReplaceImageFromDraftRequest(draft_id=draft_id, badge_id="ghost_badge_xyz")
    resp = api_replace_image_from_draft(req)
    assert resp.status_code == 404
    body = _read_body(resp)
    assert body["ok"] is False
    assert "不在 DB" in body["error"]


def test_replace_draft_without_image(fresh_draft):
    from src.kid_app.routes.badge_workflow import (
        api_replace_image_from_draft, ReplaceImageFromDraftRequest,
    )

    draft_id, _ = fresh_draft
    draft_path = DRAFT_DIR / f"{draft_id}.json"
    draft = json.loads(draft_path.read_text())
    draft["image"] = None
    draft_path.write_text(json.dumps(draft))

    req = ReplaceImageFromDraftRequest(draft_id=draft_id, badge_id="streak_7")
    resp = api_replace_image_from_draft(req)
    assert resp.status_code == 400
    body = _read_body(resp)
    assert body["ok"] is False
    assert "image" in body["error"]


def test_replace_invalid_draft_id():
    """不存在的 draft_id (DRAFT_ID_RE 也通不过) → 404."""
    from src.kid_app.routes.badge_workflow import (
        api_replace_image_from_draft, ReplaceImageFromDraftRequest,
    )

    req = ReplaceImageFromDraftRequest(
        draft_id="1970-01-01_ghost_abcdef", badge_id="streak_7"
    )
    resp = api_replace_image_from_draft(req)
    assert resp.status_code == 404
