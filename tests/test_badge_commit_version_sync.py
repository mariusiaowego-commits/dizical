"""
Tests for Bug #1: commit handler must use draft.image["version"] as single source of truth.

User 2026-06-15 走完一次完整 badge workflow, 发现 commit 后 v2 图没被复制到 static.
根因: hermes chat 多轮对话时直接编辑 draft.json 改 image.version=2, 但顶层 draft.version 还是 1.
routes/badge_workflow.py:148,161-166,173,181 commit handler 用顶层 draft.version → 复制 v1.png,
写 url=_v1.png, 前端加载到 v1 ("蒙正好少年") 而不是 v2 ("批改小帮手").

修法: commit handler 改用 image_version = draft.image["version"], 顶层 version 写库前同步.

测试策略: 用临时 db 文件 + 手动建表, 完全隔离主仓. 用 tmp_path fixture 管理清理.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ── 路径 ─────────────────────────────────────────────────────────

def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


# 1x1 透明 PNG
PNG_1x1 = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfa\xff'
    b'\xff?\x00\x05\xfe\x02\xfe\xa3V\xbd\xf1\x00\x00\x00\x00IEND\xaeB`\x82'
)


# ── fixtures: 临时 db + 创表 + 替换 src.database.db 单例 ─────────

@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """建一个临时 sqlite db, 创表 achievements/stats/badges, 替换 src.database.db 单例."""
    tmp_db = tmp_path / "test_dizi.db"
    conn = sqlite3.connect(str(tmp_db))
    conn.executescript("""
        CREATE TABLE achievements (
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
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE achievement_stats (
            achievement_id TEXT PRIMARY KEY,
            achieved       TEXT NOT NULL DEFAULT 'N',
            raw_stats      TEXT NOT NULL DEFAULT '{}',
            computed_value INTEGER
        );
        CREATE TABLE achievement_badges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            achievement_id  TEXT NOT NULL,
            url             TEXT NOT NULL,
            is_locked       INTEGER NOT NULL DEFAULT 0,
            version         INTEGER NOT NULL DEFAULT 1,
            is_current      INTEGER NOT NULL DEFAULT 1,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

    # 替换 src.database.db 单例: 直接 monkeypatch 它
    from src import database
    real_db = database.db  # 原单例
    real_db._conn = None  # 关闭旧连接

    # mock: _get_connection 返回 tmp conn
    new_conn = sqlite3.connect(str(tmp_db))
    new_conn.row_factory = sqlite3.Row

    def _fake_get_connection():
        return new_conn

    # 同时让 src.database.db._get_connection 走 fake
    monkeypatch.setattr(real_db, "_get_connection", _fake_get_connection)
    # badge_db 引用 from src.database import db, 所以替换的就是同一个对象
    yield tmp_db

    new_conn.close()
    real_db._conn = None  # 恢复


class _FakeCtx:
    """模拟 database._get_connection() 的 contextmanager 行为."""
    def __init__(self, conn):
        self.conn = conn
    def __enter__(self):
        return self.conn
    def __exit__(self, *args):
        return False


# ── helpers: 写 draft + 临时图 ──────────────────────────────────

def _make_test_draft(draft_id, top_version, image_version):
    return {
        "schema_version": 1,
        "draft_id": draft_id,
        "created_at": "2026-06-15T07:00:00Z",
        "version": top_version,
        "meta": {
            "id": f"test_bug1_{draft_id[-6:]}",
            "name": "测试badge",
            "type": "突破",
            "category": "milestone",
            "placeholder": "a cute chibi girl test",
            "zh_story": "测试典故小故事 — Bug 1 修复验证",
            "display_format": "achieved_flag",
            "sort_order": 999,
        },
        "image": {
            "path": "/tmp/fake.png",
            "model": "test-model",
            "prompt_used": "test prompt",
            "alpha_verified": True,
            "version": image_version,
        },
        "status": "draft_awaiting_confirm",
        "updated_at": "2026-06-15T07:30:00Z",
        "history": [],
    }


def _write_draft(draft_id, data, badge_id=None):
    draft_path = _project_root() / "data" / "lib" / "badge_data" / f"{draft_id}.json"
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    if badge_id:
        data["meta"]["id"] = badge_id
    draft_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return draft_path


def _write_tmp_image(draft_id, image_version):
    tmp_dir = _project_root() / "data" / "lib" / "badge_data" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    p = tmp_dir / f"{draft_id}_v{image_version}.png"
    p.write_bytes(PNG_1x1)
    return p


def _cleanup(draft_id, badge_id):
    draft_path = _project_root() / "data" / "lib" / "badge_data" / f"{draft_id}.json"
    if draft_path.exists():
        draft_path.unlink()
    for v in (1, 2, 3):
        for p in [
            _project_root() / "data" / "lib" / "badge_data" / ".tmp" / f"{draft_id}_v{v}.png",
            _project_root() / "src" / "kid_app" / "static" / "badges" / f"{badge_id}_v{v}.png",
        ]:
            if p.exists():
                p.unlink()


# ── Tests ────────────────────────────────────────────────────────

class TestCommitVersionSync:
    """Bug 1 修法: commit handler 用 image.version 不用顶层 version."""

    def test_top_v1_image_v2_writes_v2_to_static(self, isolated_db):
        """复现 bug: top=1, image=2 → commit 后 static 必须有 _v2.png, achievement_badges.url 必须是 _v2.png."""
        draft_id = "2026-06-15_test_b1_a1aaaaa"
        badge_id = "test_b1_a1aaaaa"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=2)
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 2))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)

            # 验: commit 成功, 写的是 v2
            assert data["ok"] is True, f"commit failed: {data}"
            assert data["image_url"] == f"/static/badges/{badge_id}_v2.png", \
                f"image_url should be v2, got {data['image_url']}"

            # 验: static 真的有 v2, 不应有 v1
            static_dir = _project_root() / "src" / "kid_app" / "static" / "badges"
            assert (static_dir / f"{badge_id}_v2.png").exists(), "v2 png missing in static"
            assert not (static_dir / f"{badge_id}_v1.png").exists(), "v1 png should not be in static"

            # 验: DB achievement_badges.url 写的是 v2
            conn = sqlite3.connect(str(isolated_db))
            cur = conn.execute(
                "SELECT url, version FROM achievement_badges WHERE achievement_id=?",
                (badge_id,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None, "achievement_badges row missing"
            assert row[0] == f"/static/badges/{badge_id}_v2.png", f"DB url={row[0]}"
            assert row[1] == 2, f"DB version={row[1]}, expected 2"
        finally:
            _cleanup(draft_id, badge_id)

    def test_top_v2_image_v2_writes_v2_to_static(self, isolated_db):
        """回归: top=image=2 → url=v2.png (跟修前一致)."""
        draft_id = "2026-06-15_test_b1_b2bbbbb"
        badge_id = "test_b1_b2bbbbb"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=2, image_version=2)
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 2))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)

            assert data["ok"] is True
            assert data["image_url"] == f"/static/badges/{badge_id}_v2.png"
            assert (_project_root() / "src" / "kid_app" / "static" / "badges" / f"{badge_id}_v2.png").exists()
        finally:
            _cleanup(draft_id, badge_id)

    def test_commit_syncs_top_level_version_to_image_version(self, isolated_db):
        """commit 后 draft.json 顶层 version 跟 image.version 同步 (状态自洽)."""
        draft_id = "2026-06-15_test_b1_c3ccccc"
        badge_id = "test_b1_c3ccccc"
        _cleanup(draft_id, badge_id)

        try:
            draft_data = _make_test_draft(draft_id, top_version=1, image_version=2)
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(_write_tmp_image(draft_id, 2))

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True

            draft_after = json.loads(
                (_project_root() / "data" / "lib" / "badge_data" / f"{draft_id}.json")
                .read_text(encoding="utf-8")
            )
            assert draft_after["version"] == 2, \
                f"top version should sync to 2, got {draft_after['version']}"
            assert draft_after["image"]["version"] == 2
        finally:
            _cleanup(draft_id, badge_id)

    def test_commit_cleans_image_version_tmp(self, isolated_db):
        """commit 后 .tmp/{id}_v{image_version}.png 被清, 不留残骸."""
        draft_id = "2026-06-15_test_b1_d4ddddd"
        badge_id = "test_b1_d4ddddd"
        _cleanup(draft_id, badge_id)

        try:
            # 模拟: v1.png 跟 v2.png 都在 .tmp
            _write_tmp_image(draft_id, 1)
            _write_tmp_image(draft_id, 2)

            draft_data = _make_test_draft(draft_id, top_version=1, image_version=2)
            _write_draft(draft_id, draft_data, badge_id=badge_id)
            draft_data["image"]["path"] = str(
                _project_root() / "data" / "lib" / "badge_data" / ".tmp" / f"{draft_id}_v2.png"
            )

            from src.kid_app.routes.badge_workflow import api_commit_from_draft
            req = MagicMock()
            req.draft_id = draft_id
            resp = api_commit_from_draft(req)
            data = json.loads(resp.body)
            assert data["ok"] is True

            tmp_dir = _project_root() / "data" / "lib" / "badge_data" / ".tmp"
            assert not (tmp_dir / f"{draft_id}_v2.png").exists(), "v2 tmp should be cleaned"
        finally:
            _cleanup(draft_id, badge_id)
