"""tests/test_badge_story_short.py — sprint 26091401 F1 卡背「典故·短板」

dad 2026-09-14 验收反馈 (4 问之 3): modal 右侧典故太长 → 新增后端字段
`achievements.story_short` (每 badge 一值, ≤60 字), 供卡背显示短板故事;
长典故 (`description`) 一字不动, modal 右侧继续读长文.

覆盖:
  A. ensure_story_short_column 幂等迁移 (SQLite: 缺列 → 补列; 二次调用不动)
  B. Database() 初始化路径也带上 story_short 列
  C. seed_story_short 播种 + 幂等 (第二次返 0, 值一字不动)
  D. 超 60 字的条目被跳过 (不入库, 保持 NULL) — dad 硬要求
  E. seed 只碰 story_short, 绝不改 description (长典故)
  F. 文案文件缺失 / 条目残缺 → no-op 不抛 (前端回落长典故)
  G. achievements_columns 反映真实列 (供页面 SELECT 侧拼可选列)
  H. 真文案文件 src/kid_app/badge_story_short.json 自检 (条数 / ≤60 字 / id 唯一)
  I. 真库副本端到端播种: 命中行写入正确 + 长典故不变
  J. _build_milestone_card 卡面带 data-story-short (图鉴列表路径, 上一轮漏探的地方)
  K. GET /api/achievements 载荷带 story_short (小程序老包不受影响)
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from src.kid_app import badge_db

PROD_DB = Path("/Users/mt16/dev/dizical/data/dizi.db")
SEED_JSON = Path(badge_db.__file__).with_name("badge_story_short.json")


# ─── 建表 SQL (故意不含 card_no / story_short — 交给幂等迁移补) ───────
_SCHEMA = """
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
    cond_text         TEXT,
    unlock_strategy   TEXT DEFAULT 'calc',
    achieved_at_override TEXT,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    card_theme        TEXT,
    card_stars        INTEGER
);
CREATE TABLE achievement_stats (
    achievement_id TEXT PRIMARY KEY,
    achieved       TEXT NOT NULL DEFAULT 'N',
    achieved_at    DATETIME,
    claimed_at     DATETIME,
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
CREATE TABLE practice_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    method TEXT NOT NULL,
    practice_date DATE NOT NULL,
    input_items JSON,
    result_items JSON,
    total_minutes INTEGER,
    session_id TEXT,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    detail TEXT
);
"""


def _cols(conn) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(achievements)").fetchall()}


def _add_achievement(conn, aid, description="长典故原文·二十字以内", category="突破",
                     sort_order=0):
    conn.execute(
        "INSERT INTO achievements (id, name, type, category, stat_logic, description,"
        " display_format, sort_order, seasonal_type, cond_text, unlock_strategy)"
        " VALUES (?, ?, '突破', ?, '', ?, 'icon', ?, 'monthly', '', 'calc')",
        (aid, aid, category, description, sort_order),
    )
    conn.commit()


def _story(aid: str, story: str) -> dict:
    return {"card_no": 1, "id": aid, "story": story}


@pytest.fixture()
def fresh_conn(tmp_path):
    """隔离 sqlite (无 story_short 列, 未走 Database 初始化), 单个 conn."""
    conn = sqlite3.connect(str(tmp_path / "story.db"))
    conn.executescript(_SCHEMA)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def seeded_conn(tmp_path, monkeypatch):
    """隔离 sqlite + Database() 初始化 (带上 story_short 列) + patch badge_db.db."""
    from src.database import Database

    db_path = tmp_path / "seeded.db"
    raw = sqlite3.connect(str(db_path))
    raw.executescript(_SCHEMA)
    raw.commit()
    raw.close()

    new_db = Database(db_path=str(db_path))
    monkeypatch.setattr(badge_db, "db", new_db)
    monkeypatch.setattr(badge_db, "_STORY_SHORT_COL_DONE", False)
    monkeypatch.setattr(badge_db, "_ACH_COLUMNS_CACHE", {})
    yield new_db._get_connection()


# ─── A. 迁移幂等 ──────────────────────────────────────────────────────
def test_ensure_story_short_column_idempotent(fresh_conn, monkeypatch):
    """缺列 → 补列; 二次调用不抛不改 (列还在)."""
    conn = fresh_conn
    assert "story_short" not in _cols(conn)

    monkeypatch.setattr(badge_db, "_STORY_SHORT_COL_DONE", False)
    badge_db.ensure_story_short_column(conn)
    assert "story_short" in _cols(conn)

    badge_db.ensure_story_short_column(conn)
    assert "story_short" in _cols(conn)


def test_ensure_story_short_column_missing_table_is_safe(tmp_path, monkeypatch):
    """表不存在 → 不抛, 且不置 DONE (下次再试)."""
    conn = sqlite3.connect(str(tmp_path / "empty.db"))
    monkeypatch.setattr(badge_db, "_STORY_SHORT_COL_DONE", False)
    badge_db.ensure_story_short_column(conn)
    assert badge_db._STORY_SHORT_COL_DONE is False
    conn.close()


# ─── B. Database() 初始化路径 ────────────────────────────────────────
def test_database_init_adds_story_short(seeded_conn):
    assert "story_short" in _cols(seeded_conn)


# ─── C. 播种 + 幂等 ──────────────────────────────────────────────────
def test_seed_story_short_writes_and_is_idempotent(seeded_conn, tmp_path):
    conn = seeded_conn
    _add_achievement(conn, "b1")
    _add_achievement(conn, "b2")

    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps({"version": 1, "stories": [
        _story("b1", "先声夺人领先了一整个午后。"),
        _story("b2", "指尖落下笛声先到。"),
    ]}, ensure_ascii=False), encoding="utf-8")

    assert badge_db.seed_story_short(conn, path=seed_file) == 2
    got = dict(conn.execute("SELECT id, story_short FROM achievements").fetchall())
    assert got == {"b1": "先声夺人领先了一整个午后。", "b2": "指尖落下笛声先到。"}

    # 幂等: 值相同 → 0 行, 内容一字不动
    assert badge_db.seed_story_short(conn, path=seed_file) == 0
    assert dict(conn.execute("SELECT id, story_short FROM achievements").fetchall()) == got


def test_seed_story_short_updates_changed_value(seeded_conn, tmp_path):
    """文案改版 → 只覆盖值变化的行."""
    conn = seeded_conn
    _add_achievement(conn, "b1")
    _add_achievement(conn, "b2")

    f1 = tmp_path / "v1.json"
    f1.write_text(json.dumps({"stories": [_story("b1", "旧文案"), _story("b2", "没改")]},
                             ensure_ascii=False), encoding="utf-8")
    badge_db.seed_story_short(conn, path=f1)

    f2 = tmp_path / "v2.json"
    f2.write_text(json.dumps({"stories": [_story("b1", "新文案"), _story("b2", "没改")]},
                             ensure_ascii=False), encoding="utf-8")
    assert badge_db.seed_story_short(conn, path=f2) == 1
    got = dict(conn.execute("SELECT id, story_short FROM achievements").fetchall())
    assert got == {"b1": "新文案", "b2": "没改"}


# ─── D. ≤60 字硬要求 ────────────────────────────────────────────────
def test_seed_skips_stories_over_60_chars(seeded_conn, tmp_path):
    """>60 字条目跳过 (保持 NULL), 合法的照写."""
    conn = seeded_conn
    _add_achievement(conn, "ok_one")
    _add_achievement(conn, "too_long")
    long_story = "很" * 61

    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps({"stories": [
        _story("ok_one", "短句刚好六十字以内。"),
        _story("too_long", long_story),
    ]}, ensure_ascii=False), encoding="utf-8")

    assert badge_db.seed_story_short(conn, path=seed_file) == 1
    got = dict(conn.execute("SELECT id, story_short FROM achievements").fetchall())
    assert got["ok_one"] == "短句刚好六十字以内。"
    assert got["too_long"] is None            # 超长不入库


def test_seed_accepts_exactly_60_chars(tmp_path):
    """边界: 正好 60 字 → 收."""
    f = tmp_path / "s.json"
    story = "字" * 60
    f.write_text(json.dumps({"stories": [_story("edge60", story)]}, ensure_ascii=False),
                 encoding="utf-8")
    assert badge_db.load_story_short_map(f) == {"edge60": story}


# ─── E. 不动长典故 ───────────────────────────────────────────────────
def test_seed_never_touches_description(seeded_conn, tmp_path):
    conn = seeded_conn
    _add_achievement(conn, "keep_desc", description="很长很长的典故原文不能被改写")
    seed_file = tmp_path / "seed.json"
    seed_file.write_text(json.dumps({"stories": [_story("keep_desc", "卡背短句")]},
                                    ensure_ascii=False), encoding="utf-8")

    badge_db.seed_story_short(conn, path=seed_file)
    row = conn.execute("SELECT description, story_short FROM achievements WHERE id = 'keep_desc'").fetchone()
    assert row[0] == "很长很长的典故原文不能被改写"
    assert row[1] == "卡背短句"


# ─── F. 残缺 / 缺失输入不抛 ─────────────────────────────────────────
def test_seed_missing_file_is_noop(seeded_conn, tmp_path):
    assert badge_db.seed_story_short(seeded_conn, path=tmp_path / "nope.json") == 0


def test_seed_leaves_no_open_transaction(seeded_conn, tmp_path):
    """回归 (F1 全量回归抓到的真 bug): 0 行变更也必须 commit.

    46 条 UPDATE 即使一条都不匹配也隐式开了写事务; 不 commit 会把 RESERVED
    锁留在库上 → 同进程其它连接 CREATE TABLE 直接 "database is locked"
    (实测 test_assign_draft + test_auth_web 必现, 75 error).
    """
    _add_achievement(seeded_conn, "m1")
    seed_file = tmp_path / "s.json"
    seed_file.write_text(json.dumps({"stories": [{"id": "m1", "story": "甲"}]},
                                    ensure_ascii=False), encoding="utf-8")
    assert badge_db.seed_story_short(seeded_conn, path=seed_file) == 1
    assert seeded_conn.in_transaction is False

    # 空跑一轮: 必须仍然不留事务
    assert badge_db.seed_story_short(seeded_conn, path=seed_file) == 0
    assert seeded_conn.in_transaction is False

    # 强证据: 另开连接写 DDL (锁没释放这里就抛 OperationalError)
    db_file = seeded_conn.execute("PRAGMA database_list").fetchone()[2]
    other = sqlite3.connect(db_file, timeout=2)
    try:
        other.execute("CREATE TABLE probe_lock_check (x INTEGER)")
        other.commit()
    finally:
        other.close()


def test_load_story_short_map_skips_malformed(tmp_path):
    """空 id / 空 story / 非 dict 条目 → 跳过; 坏 JSON → 空 dict."""
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"stories": [
        {"id": "", "story": "无 id"},
        {"id": "no_story", "story": "   "},
        "不是 dict",
        {"id": "good", "story": "有效文案"},
    ]}, ensure_ascii=False), encoding="utf-8")
    assert badge_db.load_story_short_map(f) == {"good": "有效文案"}

    broken = tmp_path / "broken.json"
    broken.write_text("{不是 json", encoding="utf-8")
    assert badge_db.load_story_short_map(broken) == {}


# ─── G. achievements_columns ────────────────────────────────────────
def test_achievements_columns_reports_real_columns(seeded_conn, monkeypatch):
    monkeypatch.setattr(badge_db, "_ACH_COLUMNS_CACHE", {})
    cols = badge_db.achievements_columns(seeded_conn)
    assert {"id", "description", "story_short"} <= cols


def test_achievements_columns_empty_on_failure(monkeypatch):
    """非 conn 对象 (查询抛错) → 空集降级, 不抛."""
    monkeypatch.setattr(badge_db, "_ACH_COLUMNS_CACHE", {})
    assert badge_db.achievements_columns("不是连接") == set()


# ─── H. 真文案文件自检 ──────────────────────────────────────────────
def test_real_seed_file_shape():
    if not SEED_JSON.exists():
        pytest.skip(f"文案文件不存在: {SEED_JSON}")
    data = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    stories = data["stories"]
    assert stories, "文案文件为空"

    ids = [s["id"] for s in stories]
    assert len(ids) == len(set(ids)), "存在重复 id"
    over = [(s["id"], len(s["story"])) for s in stories if len(s["story"]) > badge_db.STORY_SHORT_MAX_LEN]
    assert not over, f"存在超 60 字文案: {over}"
    malformed = [s for s in stories if not str(s.get("story") or "").strip()]
    assert not malformed, "存在空文案"
    # 每条都能被 load 收下 (content 合法)
    assert len(badge_db.load_story_short_map(SEED_JSON)) == len(ids)


# ─── I. 真库副本端到端 ──────────────────────────────────────────────
def test_seed_on_prod_db_copy(tmp_path, monkeypatch):
    """真库副本: 播种命中行 + 长典故一字不动."""
    if not PROD_DB.exists():
        pytest.skip(f"prod DB 不存在: {PROD_DB}")
    if not SEED_JSON.exists():
        pytest.skip("文案文件不存在")

    db_path = tmp_path / "prod_copy.db"
    shutil.copy2(PROD_DB, db_path)
    conn = sqlite3.connect(str(db_path))
    monkeypatch.setattr(badge_db, "_STORY_SHORT_COL_DONE", False)
    monkeypatch.setattr(badge_db, "_ACH_COLUMNS_CACHE", {})

    before = dict(conn.execute("SELECT id, description FROM achievements").fetchall())
    n = badge_db.seed_story_short(conn, path=SEED_JSON)
    assert n > 0, "真库副本一行都没播上"

    seed = badge_db.load_story_short_map(SEED_JSON)
    after_desc = dict(conn.execute("SELECT id, description FROM achievements").fetchall())
    after_story = dict(conn.execute("SELECT id, story_short FROM achievements").fetchall())

    assert after_desc == before, "长典故被改动了!"
    for bid in set(seed) & set(after_story):
        assert after_story[bid] == seed[bid]
    assert badge_db.seed_story_short(conn, path=SEED_JSON) == 0   # 幂等
    conn.close()


# ─── J. 卡面 data-story-short (图鉴列表路径) ─────────────────────────
def _build_card(**kw):
    from src.kid_app.app import _build_milestone_card

    params = dict(
        ach_id="b1", name="先声夺人", ach_type="突破",
        desc="这是很长的典故原文, 在 modal 右侧展示",
        badge_url="/static/badges/x.png", achieved=True, cv=1, threshold=1,
        condition="", cond_text="清晨六点前",
    )
    params.update(kw)
    return _build_milestone_card(**params)


def test_milestone_card_carries_data_story_short():
    html = _build_card(story_short="先声夺人领先了一整个午后。", card_no=12)
    assert "data-story-short='先声夺人领先了一整个午后。'" in html
    assert "data-no='12'" in html
    # 长典故仍在卡面 (modal 右侧读它)
    assert "这是很长的典故原文, 在 modal 右侧展示" in html


def test_milestone_card_empty_story_short_is_blank_attr():
    """未播种 (None) → data-story-short='' → 前端 normalize 回落长典故."""
    html = _build_card(story_short=None)
    assert "data-story-short=''" in html


def test_milestone_card_escapes_story_short():
    html = _build_card(story_short="a'b<c>d\"e")
    assert "a&#x27;b&lt;c&gt;d&quot;e" in html
    assert "a'b<c>d\"e" not in html


# ─── K. API 载荷 ────────────────────────────────────────────────────
def test_achievements_page_payload_includes_story_short(tmp_path, monkeypatch):
    """GET /api/achievements 增字段 story_short (老字段全在)."""
    if not PROD_DB.exists():
        pytest.skip(f"prod DB 不存在: {PROD_DB}")
    if not SEED_JSON.exists():
        pytest.skip("文案文件不存在")

    db_path = tmp_path / "prod_copy_api.db"
    shutil.copy2(PROD_DB, db_path)

    conn = sqlite3.connect(str(db_path))
    monkeypatch.setattr(badge_db, "_STORY_SHORT_COL_DONE", False)
    monkeypatch.setattr(badge_db, "_ACH_COLUMNS_CACHE", {})
    badge_db.seed_story_short(conn, path=SEED_JSON)
    conn.close()

    from src import achievement_definitions, db_adapter, database

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr(achievement_definitions, "_DB_PATH", db_path)
    monkeypatch.setattr(
        db_adapter, "get_conn", lambda _p=db_path: (sqlite3.connect(str(_p)), False)
    )
    monkeypatch.setattr(
        database.db, "_get_connection", lambda _p=db_path: sqlite3.connect(str(_p))
    )
    monkeypatch.setattr(badge_db, "_ACH_COLUMNS_CACHE", {})

    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    client = TestClient(app)
    resp = client.get("/api/achievements")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True

    all_badges = body["unlocked"] + body["locked"]
    assert all_badges, "prod 副本没有 badge — 数据异常"

    seed = badge_db.load_story_short_map(SEED_JSON)
    seeded = [b for b in all_badges if b["id"] in seed]
    assert seeded, "载荷里没有任何已播种 badge"
    for b in all_badges:
        assert "story_short" in b
        assert isinstance(b["story_short"], str)
        assert len(b["story_short"]) <= badge_db.STORY_SHORT_MAX_LEN
    for b in seeded:
        assert b["story_short"] == seed[b["id"]]
        assert b["description"], "长典故字段不能为空"
