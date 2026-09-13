"""tests/test_achievements_card_no.py — sprint 26091301 B1 徽章卡编号 (achievements.card_no)

依据: docs/AI-PRD-徽章卡编号-260912.md §3 (A 方案) + §5 验收标准.

覆盖:
  A. ensure_card_no_column 幂等迁移 (SQLite: 缺列 → 补列 + 部分唯一索引; 二次调用不动)
  B. backfill_card_no 回填 → 编号唯一且连续, 顺序 = (category, sort_order, created_at, id)
  C. backfill_card_no 幂等 → 第二次返回 0 且每一行 card_no 一字不动
  D. 已有编号的行绝不被改动 (预置 card_no=1 → 回填从 2 起, 跳号不占)
  E. 新徽章 insert_achievement_row 不传 card_no → MAX+1 (同事务); 显式传值则尊重
  F. 改 sort_order 后编号不变 (稳定性回归, 再跑回填也不动)
  G. GET /api/badge/unclaimed 返回可选字段 card_no (其它字段不变)
  H. GET /api/achievements 返回可选字段 card_no (小程序老包不受影响)
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from src.kid_app import badge_db

PROD_DB = Path("/Users/mt16/dev/dizical/data/dizi.db")


# ─── 建表 SQL (故意不含 card_no — 交给幂等迁移补) ────────────────────
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


def _add_achievement(conn, aid, category, sort_order, created_at, card_no=None,
                     name=None, typ="突破"):
    """插 1 行 achievements (可指定 card_no)."""
    conn.execute(
        "INSERT INTO achievements (id, name, type, category, stat_logic, description,"
        " display_format, sort_order, seasonal_type, cond_text, unlock_strategy,"
        " created_at, card_no)"
        " VALUES (?, ?, ?, ?, '', '', 'icon', ?, 'monthly', '', 'calc', ?, ?)",
        (aid, name or aid, typ, category, sort_order, created_at, card_no),
    )
    conn.commit()


def _card_nos(conn) -> dict[str, int | None]:
    rows = conn.execute("SELECT id, card_no FROM achievements").fetchall()
    return {r[0]: r[1] for r in rows}


@pytest.fixture()
def card_db(tmp_path, monkeypatch):
    """隔离 sqlite 文件 (无 card_no 列) + Database() 初始化 + patch badge_db.db 单例."""
    db_path = tmp_path / "card_no.db"
    raw = sqlite3.connect(str(db_path))
    raw.executescript(_SCHEMA)
    raw.commit()
    raw.close()

    from src.database import Database

    new_db = Database(db_path=str(db_path))  # _init_tables 幂等 ALTER 补 card_no
    monkeypatch.setattr(badge_db, "db", new_db)
    monkeypatch.setattr(badge_db, "_CARD_NO_COL_DONE", False)
    conn = new_db._get_connection()
    yield conn


# ─── A. 迁移幂等 ──────────────────────────────────────────────────────
def test_ensure_card_no_column_idempotent(tmp_path, monkeypatch):
    """缺列 → 补列 + 唯一索引; 二次调用不抛不改 (PRD §3.1)."""
    db_path = tmp_path / "mig.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.commit()
    assert "card_no" not in _cols(conn)

    monkeypatch.setattr(badge_db, "_CARD_NO_COL_DONE", False)
    badge_db.ensure_card_no_column(conn)

    assert "card_no" in _cols(conn)
    indexes = {r[1] for r in conn.execute("PRAGMA index_list(achievements)").fetchall()}
    assert "idx_achievements_card_no" in indexes

    # 二次调用: 幂等 (不抛异常, 列/索引仍在)
    badge_db.ensure_card_no_column(conn)
    assert "card_no" in _cols(conn)
    assert "idx_achievements_card_no" in {
        r[1] for r in conn.execute("PRAGMA index_list(achievements)").fetchall()
    }
    conn.close()


def test_ensure_card_no_column_via_database_init(card_db):
    """Database() 初始化路径 (dev SQLite / 测试夹具) 也应带上 card_no 列."""
    assert "card_no" in _cols(card_db)


# ─── B. 回填: 唯一 + 连续 + 编排顺序 ─────────────────────────────────
def test_backfill_unique_contiguous_and_ordered(card_db):
    """回填后编号唯一且连续; 顺序 = category → sort_order → created_at → id."""
    conn = card_db
    # 故意乱序插入 ('seasonal' < '巅峰' < '突破' 按 unicode 升序)
    _add_achievement(conn, "seasonal_b", "seasonal", 5, "2026-01-02 00:00:00")
    _add_achievement(conn, "break_a", "突破", 0, "2026-03-01 00:00:00")
    _add_achievement(conn, "peak_c", "巅峰", 0, "2026-02-01 00:00:00")
    _add_achievement(conn, "break_b", "突破", 0, "2026-01-15 00:00:00")
    _add_achievement(conn, "peak_a", "巅峰", 9, "2026-04-01 00:00:00")

    badge_db.ensure_card_no_column(conn)
    n = badge_db.backfill_card_no(conn)
    assert n == 5

    got = _card_nos(conn)
    expect = {
        "seasonal_b": 1,   # seasonal 组第一个
        "peak_c": 2,       # 巅峰 组 sort_order=0 (早)
        "peak_a": 3,       # 巅峰 组 sort_order=9
        "break_b": 4,      # 突破 组 sort_order 都是 0 → created_at 早者先
        "break_a": 5,
    }
    assert got == expect

    numbers = sorted(v for v in got.values() if v is not None)
    assert numbers == [1, 2, 3, 4, 5]          # 连续
    assert len(set(numbers)) == len(numbers)   # 唯一


# ─── C. 回填幂等 ──────────────────────────────────────────────────────
def test_backfill_idempotent_second_run_noop(card_db):
    """第二次回填返回 0, 且每一行 card_no 不变."""
    conn = card_db
    for i, aid in enumerate(["a1", "a2", "a3"]):
        _add_achievement(conn, aid, "突破", i, f"2026-01-0{i + 1} 00:00:00")

    assert badge_db.backfill_card_no(conn) == 3
    first = _card_nos(conn)

    assert badge_db.backfill_card_no(conn) == 0     # 幂等: 无 NULL 行
    assert _card_nos(conn) == first                 # 一字不动
    assert badge_db.backfill_card_no(conn) == 0
    assert _card_nos(conn) == first


# ─── D. 已有编号不被改动 / 跳号 ───────────────────────────────────────
def test_backfill_never_touches_existing_numbers(card_db):
    """预置 card_no=1 的行保持 1; 其余从 2 起补齐 (不占已用号)."""
    conn = card_db
    _add_achievement(conn, "keep_x", "突破", 0, "2026-01-01 00:00:00", card_no=1)
    _add_achievement(conn, "new_1", "突破", 1, "2026-01-02 00:00:00")
    _add_achievement(conn, "new_2", "突破", 2, "2026-01-03 00:00:00")
    _add_achievement(conn, "new_3", "突破", 3, "2026-01-04 00:00:00")

    assert badge_db.backfill_card_no(conn) == 3
    got = _card_nos(conn)
    assert got["keep_x"] == 1            # 已编号行不动
    assert sorted(v for k, v in got.items() if k != "keep_x") == [2, 3, 4]


# ─── E. 新徽章 MAX+1 ─────────────────────────────────────────────────
def _new_ach(aid: str, **extra) -> dict:
    ach = {
        "id": aid,
        "name": aid,
        "type": "突破",
        "category": "milestone",
        "stat_logic": "",
        "description": "测试",
        "display_format": "icon",
        "seasonal_type": "monthly",
    }
    ach.update(extra)
    return ach


def test_new_badge_gets_max_plus_one(card_db):
    """不传 card_no → MAX+1 (与 INSERT 同一事务)."""
    conn = card_db
    _add_achievement(conn, "old_1", "突破", 0, "2026-01-01 00:00:00")
    _add_achievement(conn, "old_2", "突破", 1, "2026-01-02 00:00:00")
    badge_db.backfill_card_no(conn)
    assert badge_db.fetch_max_card_no() == 2

    badge_db.insert_achievement_row(conn, _new_ach("brand_new"))
    got = _card_nos(conn)
    assert got["brand_new"] == 3                     # MAX+1
    assert badge_db.fetch_max_card_no() == 3

    # 再来一个 → 4 (不跳号)
    badge_db.insert_achievement_row(conn, _new_ach("brand_new_2"))
    assert _card_nos(conn)["brand_new_2"] == 4


def test_new_badge_explicit_card_no_respected(card_db):
    """draft JSON 显式给了 card_no → 尊重原值 (PRD §3.3 可选字段)."""
    conn = card_db
    _add_achievement(conn, "old_1", "突破", 0, "2026-01-01 00:00:00")
    badge_db.backfill_card_no(conn)

    badge_db.insert_achievement_row(conn, _new_ach("manual_no", card_no=77))
    assert _card_nos(conn)["manual_no"] == 77
    assert badge_db.fetch_max_card_no() == 77


# ─── F. 稳定性: 改 sort_order 不改号 ─────────────────────────────────
def test_sort_order_change_keeps_card_no(card_db):
    """改 sort_order (展示排序) / 再跑回填 → 编号不变 (PRD §5.3)."""
    conn = card_db
    for i, aid in enumerate(["s1", "s2", "s3"]):
        _add_achievement(conn, aid, "突破", i, f"2026-01-0{i + 1} 00:00:00")
    badge_db.backfill_card_no(conn)
    before = _card_nos(conn)

    # 把排在最后的挪到最前 (等价于 sort_order_override 覆盖展示顺序)
    conn.execute("UPDATE achievements SET sort_order = -99 WHERE id = 's3'")
    conn.commit()

    assert badge_db.backfill_card_no(conn) == 0      # 无 NULL 行 → 不回填
    assert _card_nos(conn) == before                 # 编号纹丝不动
    assert _card_nos(conn)["s1"] == 1
    assert _card_nos(conn)["s3"] == 3


# ─── G. API: /api/badge/unclaimed ────────────────────────────────────
@pytest.fixture()
def unclaimed_env(tmp_path, monkeypatch):
    """隔离 sqlite + patch badge_claim.DB_PATH + app db 单例, 供两个 API 测试用."""
    import src.database as db_module
    import src.kid_app.app as app_module
    import src.kid_app.routes.badge_claim as badge_claim_module

    db_path = tmp_path / "api.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA)
    conn.execute("ALTER TABLE achievements ADD COLUMN card_no INTEGER")  # 迁移等价
    # 1 个可领取 (achieved=Y + claimed_at NULL) + 1 个未达成
    conn.execute(
        "INSERT INTO achievements (id, name, type, category, stat_logic, description,"
        " display_format, sort_order, seasonal_type, cond_text, unlock_strategy, card_no)"
        " VALUES ('card_no_7', '编号七', '突破', 'milestone', '', '描述', 'icon', 1,"
        " 'monthly', '测试条件', 'calc', 7)"
    )
    conn.execute(
        "INSERT INTO achievements (id, name, type, category, stat_logic, description,"
        " display_format, sort_order, seasonal_type, cond_text, unlock_strategy, card_no)"
        " VALUES ('card_no_null', '编号空', '突破', 'milestone', '', '描述', 'icon', 2,"
        " 'monthly', '测试条件', 'calc', NULL)"
    )
    conn.execute(
        "INSERT INTO achievement_stats (achievement_id, achieved, achieved_at, claimed_at)"
        " VALUES ('card_no_7', 'Y', '2026-09-01 10:00:00', NULL)"
    )
    conn.execute(
        "INSERT INTO achievement_badges (achievement_id, url, is_locked, version, is_current)"
        " VALUES ('card_no_7', '/static/badges/test.png', 0, 1, 1)"
    )
    conn.commit()
    conn.close()

    from src.database import Database

    new_db = Database(db_path=str(db_path))
    monkeypatch.setattr(db_module, "db", new_db)
    monkeypatch.setattr(app_module, "db", new_db)
    monkeypatch.setattr(badge_claim_module, "DB_PATH", Path(str(db_path)))
    monkeypatch.setenv("DATABASE_URL", "")
    yield str(db_path)


def test_unclaimed_api_returns_card_no(unclaimed_env):
    """GET /api/badge/unclaimed 增字段 card_no; 其它字段保持不变."""
    from fastapi.testclient import TestClient
    from src.kid_app import app as app_module

    client = TestClient(app_module.app)
    resp = client.get("/api/badge/unclaimed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["unclaimed_count"] == 1

    badge = body["badges"][0]
    assert badge["id"] == "card_no_7"
    assert badge["card_no"] == 7
    # 老字段一个不少 (小程序/老前端不受影响)
    for key in ("id", "name", "type", "category", "cond_text", "description",
                "card_theme", "card_stars", "badge_url", "achieved_at"):
        assert key in badge, f"老字段丢失: {key}"
    assert badge["name"] == "编号七"
    assert badge["badge_url"] == "/static/badges/test.png"
    assert badge["achieved_at"] == "2026-09-01 10:00:00"


# ─── H. API: /api/achievements (小程序) ──────────────────────────────
def test_achievements_api_returns_card_no(monkeypatch, tmp_path):
    """GET /api/achievements 增字段 card_no (可选, 小程序本轮不改也能跑)."""
    if not PROD_DB.exists():
        pytest.skip(f"prod DB 不存在: {PROD_DB}")
    db_path = tmp_path / "prod_copy.db"
    shutil.copy2(PROD_DB, db_path)

    # 迁移等价: 给副本补 card_no 列 + 给 grade_1 显式 7
    from src import achievement_definitions, db_adapter, database

    conn = sqlite3.connect(str(db_path))
    monkeypatch.setattr(badge_db, "_CARD_NO_COL_DONE", False)
    badge_db.ensure_card_no_column(conn)
    conn.execute("UPDATE achievements SET card_no = 7 WHERE id = 'grade_1'")
    conn.commit()
    conn.close()

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr(achievement_definitions, "_DB_PATH", db_path)
    monkeypatch.setattr(
        db_adapter, "get_conn", lambda _p=db_path: (sqlite3.connect(str(_p)), False)
    )
    monkeypatch.setattr(
        database.db, "_get_connection", lambda _p=db_path: sqlite3.connect(str(_p))
    )

    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    client = TestClient(app)
    resp = client.get("/api/achievements")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True

    all_badges = body["unlocked"] + body["locked"]
    assert all_badges, "prod 副本没有 badge — 数据异常"
    by_id = {b["id"]: b for b in all_badges}

    assert "grade_1" in by_id, "prod 副本缺 grade_1"
    assert by_id["grade_1"]["card_no"] == 7          # 显式编号透传
    for b in all_badges:
        assert "card_no" in b                        # 可选字段人人都有 (可 NULL)
        assert b["card_no"] is None or isinstance(b["card_no"], int)
