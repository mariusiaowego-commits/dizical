"""
feat/badge-manual-award-261020 — 徽章「手动颁发 (manual)」策略单测 + 负控.

覆盖 (8 条):
  1. 列表只返 unlock_strategy='manual' (calc / immediate 不得混入)
  2. 颁发 → /api/badge/unclaimed 出现 → claim → 撤销归零 → 重颁再弹 (完整闭环)
  3. 幂等: 已领取后重颁保留 claimed_at; 重复撤销恒 200
  4. CST 未来日期 / 非法日期 → 400 (future_date_not_allowed / invalid_date)
  5. 非 manual 徽章 → 400 not_manual_badge; 未知 id → 404
  6. dad 三轨鉴权: 匿名 401, X-Dad-Pin 200
  7. calc_all() 与 GET /api/achievements 保持 manual 状态 (颁发 True / 撤销 False)
  8. 卡面与故事缺失降级: badge_url='' + story_text='故事准备中', 全程 200 不 500

设计要点:
- 每个测试一条隔离 tmp sqlite (不碰 production data/dizi.db, 同 tests/test_badge_claim.py 口径).
- achievements / achievement_stats / achievement_badges 三表 + practice_audit_log (claim 审计用).
- 4 枚 manual 资产由 p1 的 feat/badge-manual4-art-261020 并行提供, 本文件只用占位 id + 无图无故事,
  正好覆盖「缺资产也能跑」的降级要求.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
import tempfile

import pytest

PIN = "0905"
CST = dt.timezone(dt.timedelta(hours=8))

MANUAL_WITH_ART = "tech_hua_yin"      # 有卡面 + 有故事
MANUAL_BARE = "lore_ling_lun"         # 无卡面 + 无故事 (description='无')
CALC_ID = "streak_7"
IMMEDIATE_ID = "grade_1"

SCHEMA = """
CREATE TABLE achievements (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    type              TEXT NOT NULL,
    category          TEXT NOT NULL DEFAULT 'milestone',
    stat_logic        TEXT NOT NULL DEFAULT '',
    description       TEXT NOT NULL DEFAULT '',
    display_format    TEXT NOT NULL DEFAULT 'count',
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
    card_stars        INTEGER,
    card_no           INTEGER,
    story_short       TEXT
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


def _cst_today() -> dt.date:
    return dt.datetime.now(CST).date()


@pytest.fixture()
def db_path(monkeypatch):
    """隔离 tmp db + 三层 patch (settings / database.db / app.db)."""
    from src import models
    import src.kid_app.app as app_module
    from src.database import Database
    import src.database as db_module

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["DATABASE_URL"] = ""

    raw = sqlite3.connect(path)
    raw.executescript(SCHEMA)
    raw.commit()
    raw.close()

    # 新 Database 会在 __init__ 里建 settings / lessons 等基表 (dad_pin 需要)
    new_db = Database(db_path=path)
    monkeypatch.setattr(models.settings, "db_path", path)
    monkeypatch.setattr(db_module, "db", new_db)
    monkeypatch.setattr(app_module, "db", new_db)
    # auth.check_dad_pin 用的是 auth 模块自己的 db 引用 (from src.database import db,
    # import 时就绑定) —— 不 patch 它的话 X-Dad-Pin 永远读不到 tmp db 里的 dad_pin;
    # minip_api.api_achievements 同理 (自己绑定 db, 不 patch 会读 conftest 的 session 库)。
    import src.kid_app.auth as auth_module
    import src.kid_app.badge_db as badge_db_module
    import src.kid_app.routes.config as config_routes
    import src.kid_app.routes.minip_api as minip_api_module
    for mod in (auth_module, badge_db_module, config_routes, minip_api_module):
        monkeypatch.setattr(mod, "db", new_db)
    new_db.set_setting("dad_pin", PIN)

    conn = sqlite3.connect(path)
    conn.executescript(
        f"""
        INSERT INTO achievements
            (id, name, type, category, description, sort_order, cond_text,
             unlock_strategy, card_theme, card_stars, card_no, story_short)
        VALUES
            ('{MANUAL_WITH_ART}', '流云滑指灵', '技巧', 'milestone',
             '在乐曲练习中完成三次圆润滑音动作', 57, '三次圆润滑音', 'manual',
             'azure', 3, 63, '指尖一抹，滑过竹林的风。'),
            ('{MANUAL_BARE}', '轮指小满', '技巧', 'milestone',
             '无', 66, '轮指连续十六分', 'manual', 'pearl', 2, 72, NULL),
            ('{CALC_ID}', '连续七天', '执着', 'milestone',
             '连续七天练习', 5, '连续七天', 'calc', 'sakura', 2, 7, '七天不断。'),
            ('{IMMEDIATE_ID}', '一级', '晋级', 'milestone',
             '考出一级', 20, '考出一级', 'immediate', 'imperial', 4, 20, '一级到手。');

        INSERT INTO achievement_stats (achievement_id, achieved, achieved_at, claimed_at, raw_stats, computed_value)
        VALUES
            ('{MANUAL_WITH_ART}', 'N', NULL, NULL, '{{}}', NULL),
            ('{IMMEDIATE_ID}', 'Y', '2026-06-16 00:00:00', '2026-06-16 00:00:00', '{{}}', 1);

        INSERT INTO achievement_badges (achievement_id, url, is_current)
        VALUES
            ('{MANUAL_WITH_ART}', '/static/badges/tech_hua_yin_v1.png', 1),
            ('{CALC_ID}', '/static/badges/streak_7_v1.png', 1),
            ('{IMMEDIATE_ID}', '/static/badges/grade_1_v1.png', 1);
        """
    )
    conn.commit()
    conn.close()

    yield path

    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture()
def client(db_path):
    from fastapi.testclient import TestClient
    from src.kid_app import app as app_module
    # 关掉 session 重定向干扰不必要 —— /config/api/ 与 /api/ 均在公开白名单,
    # 鉴权由端点自身负责 (本文件正是要验这一点)。
    return TestClient(app_module.app)


@pytest.fixture()
def auth_headers():
    return {"X-Dad-Pin": PIN}


def _get_manual(client, headers):
    r = client.get("/config/api/badge/manual", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _row_by_id(payload, badge_id):
    for row in payload["data"]:
        if row["id"] == badge_id:
            return row
    return None


def _stats_row(db_path, badge_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT achieved, achieved_at, claimed_at FROM achievement_stats "
            "WHERE achievement_id = ?", (badge_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ─── 1. 列表只返 manual ────────────────────────────────────────────────
def test_list_manual_badges_only(client, auth_headers):
    payload = _get_manual(client, auth_headers)
    ids = [row["id"] for row in payload["data"]]
    assert ids == [MANUAL_WITH_ART, MANUAL_BARE], ids          # 按 card_no 63 → 72
    assert payload["count"] == 2
    assert payload["today_cst"] == str(_cst_today())
    assert CALC_ID not in ids and IMMEDIATE_ID not in ids
    for row in payload["data"]:
        assert row["unlock_strategy"] == "manual"
        assert row["achieved"] is False
        assert row["achieved_date"] is None
        assert row["achieved_at"] is None
        assert row["claimed_at"] is None


# ─── 2. 颁发 → 弹窗 → 领取 → 撤销 → 重颁 ───────────────────────────────
def test_award_popup_claim_revoke_reaward_cycle(client, auth_headers, db_path):
    today = str(_cst_today())

    # 颁发
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award", "achieved_date": today}, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["achieved"] is True
    assert data["achieved_date"] == today
    assert data["achieved_at"] == f"{today} 00:00:00"
    assert data["claimed_at"] is None

    # kid 端弹窗队列出现
    unclaimed = client.get("/api/badge/unclaimed").json()
    assert MANUAL_WITH_ART in [b["id"] for b in unclaimed["badges"]]

    # 领取 → claimed_at 落库
    claim = client.post("/api/badge/claim", json={"badge_id": MANUAL_WITH_ART})
    assert claim.status_code == 200, claim.text
    assert claim.json()["already_claimed"] is False
    assert _stats_row(db_path, MANUAL_WITH_ART)["claimed_at"] is not None

    # 撤销 → 完全归零, 不再进弹窗队列
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "revoke"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["achieved"] is False
    row = _stats_row(db_path, MANUAL_WITH_ART)
    assert row["achieved"] == "N"
    assert row["achieved_at"] is None
    assert row["claimed_at"] is None
    unclaimed = client.get("/api/badge/unclaimed").json()
    assert MANUAL_WITH_ART not in [b["id"] for b in unclaimed["badges"]]

    # 重颁 → 再次可弹 (claimed_at 已归 NULL)
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award", "achieved_date": today}, headers=auth_headers)
    assert r.status_code == 200, r.text
    unclaimed = client.get("/api/badge/unclaimed").json()
    assert MANUAL_WITH_ART in [b["id"] for b in unclaimed["badges"]]


# ─── 3. 幂等 ──────────────────────────────────────────────────────────
def test_award_and_revoke_idempotent(client, auth_headers, db_path):
    today = _cst_today()
    first = str(today - dt.timedelta(days=3))

    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award", "achieved_date": first}, headers=auth_headers)
    assert r.status_code == 200
    assert client.post("/api/badge/claim", json={"badge_id": MANUAL_WITH_ART}).status_code == 200
    claimed_at = _stats_row(db_path, MANUAL_WITH_ART)["claimed_at"]
    assert claimed_at is not None

    # 已领取后重复颁发 (只改日期) → claimed_at 不许被清空 (防连点重弹)
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award", "achieved_date": str(today)}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["achieved_date"] == str(today)
    after = _stats_row(db_path, MANUAL_WITH_ART)
    assert after["claimed_at"] == claimed_at
    assert after["achieved_at"] == f"{today} 00:00:00"

    # 连续撤销 → 恒 200 (幂等)
    for _ in range(2):
        r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                        json={"action": "revoke"}, headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["achieved"] is False
    assert _stats_row(db_path, MANUAL_WITH_ART)["achieved"] == "N"

    # 从未颁发过的徽章直接撤销 → 200 (写一行 N 占位, 不报错)
    r = client.post(f"/config/api/badge/manual/{MANUAL_BARE}",
                    json={"action": "revoke"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert _stats_row(db_path, MANUAL_BARE)["achieved"] == "N"


# ─── 4. CST 未来日期 / 非法日期 ────────────────────────────────────────
def test_reject_future_and_invalid_date(client, auth_headers):
    future = str(_cst_today() + dt.timedelta(days=1))
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award", "achieved_date": future}, headers=auth_headers)
    assert r.status_code == 400
    assert r.json()["code"] == "future_date_not_allowed"

    for bad in ("2026-02-30", "bad", "", "2026-13-01"):
        r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                        json={"action": "award", "achieved_date": bad}, headers=auth_headers)
        assert r.status_code == 400, (bad, r.text)
        assert r.json()["code"] == "invalid_date", (bad, r.text)

    # 缺 achieved_date (None) 也算非法
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award"}, headers=auth_headers)
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_date"


# ─── 5. 非 manual 徽章 / 未知 id ───────────────────────────────────────
def test_reject_non_manual_badge(client, auth_headers):
    today = str(_cst_today())
    for badge_id in (CALC_ID, IMMEDIATE_ID):
        r = client.post(f"/config/api/badge/manual/{badge_id}",
                        json={"action": "award", "achieved_date": today}, headers=auth_headers)
        assert r.status_code == 400, (badge_id, r.text)
        assert r.json()["code"] == "not_manual_badge"

    r = client.post("/config/api/badge/manual/no_such_badge",
                    json={"action": "award", "achieved_date": today}, headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"

    # 非法 action 先于库校验 → 400 invalid_action
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "drop"}, headers=auth_headers)
    assert r.status_code == 400
    assert r.json()["code"] == "invalid_action"


# ─── 6. dad 鉴权 ──────────────────────────────────────────────────────
def test_manual_endpoints_require_dad_auth(client):
    r = client.get("/config/api/badge/manual")
    assert r.status_code == 401
    assert r.json()["ok"] is False

    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award", "achieved_date": str(_cst_today())})
    assert r.status_code == 401
    assert r.json()["ok"] is False

    # X-Dad-Pin 通道
    assert client.get("/config/api/badge/manual",
                      headers={"X-Dad-Pin": PIN}).status_code == 200
    # body pin 通道 (POST)
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award", "achieved_date": str(_cst_today()), "pin": PIN})
    assert r.status_code == 200, r.text


# ─── 7. calc_all / /api/achievements 保持 manual 状态 ──────────────────
def test_calc_all_and_achievements_api_preserve_manual(client, auth_headers):
    from src.achievement_definitions import calc_all

    today = str(_cst_today())
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "award", "achieved_date": today}, headers=auth_headers)
    assert r.status_code == 200, r.text

    results = calc_all()
    assert results[MANUAL_WITH_ART].achieved is True
    assert results[MANUAL_WITH_ART].condition == f"颁发时间: {today}"
    # 未颁发的 manual 徽章保持锁定 (calc 不得凭空点亮)
    assert results[MANUAL_BARE].achieved is False

    api = client.get("/api/achievements")
    assert api.status_code == 200, api.text
    payload = api.json()
    item = next(b for b in payload["unlocked"] if b["id"] == MANUAL_WITH_ART)
    assert item["achieved"] is True
    assert item["condition"] == f"颁发时间: {today}"

    # 撤销 → calc_all 与 API 同步回落 False
    r = client.post(f"/config/api/badge/manual/{MANUAL_WITH_ART}",
                    json={"action": "revoke"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    results = calc_all()
    assert results[MANUAL_WITH_ART].achieved is False
    payload = client.get("/api/achievements").json()
    locked_ids = [b["id"] for b in payload["locked"]]
    assert MANUAL_WITH_ART in locked_ids
    item = next(b for b in payload["locked"] if b["id"] == MANUAL_WITH_ART)
    assert item["achieved"] is False
    assert item["condition"] == ""


# ─── 8. 卡面 / 故事缺失降级 (资产由 art 分支并行提供) ──────────────────
def test_missing_art_and_story_graceful_fallback(client, auth_headers, db_path):
    """无 achievement_badges 记录 + description='无' → 200 + badge_url='' + story_text='故事准备中'."""
    payload = _get_manual(client, auth_headers)
    bare = _row_by_id(payload, MANUAL_BARE)
    assert bare is not None
    assert bare["badge_url"] == ""
    assert bare["story_text"] == "故事准备中"

    # 有故事有图的徽章 → story_text 取 story_short (不是 description), 图 URL 原样
    with_art = _row_by_id(payload, MANUAL_WITH_ART)
    assert with_art["story_text"] == "指尖一抹，滑过竹林的风。"
    assert with_art["badge_url"] == "/static/badges/tech_hua_yin_v1.png"

    # 缺资产的徽章照常可颁发/撤销, 全程 200
    today = str(_cst_today())
    r = client.post(f"/config/api/badge/manual/{MANUAL_BARE}",
                    json={"action": "award", "achieved_date": today}, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["badge_url"] == ""
    assert data["story_text"] == "故事准备中"
    assert data["achieved"] is True

    r = client.post(f"/config/api/badge/manual/{MANUAL_BARE}",
                    json={"action": "revoke"}, headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["story_text"] == "故事准备中"

    # 成就 JSON API 也不许因缺图缺故事 500
    assert client.get("/api/achievements").status_code == 200

    # ── Rework 1 (261020 p1 裁定): description='无' + story_short 非空 ──
    # 必须优先返回 story_short, 不许被 '无' 短路吞成 '故事准备中'
    real_story = "伶伦截竹，定十二律。"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE achievements SET story_short = ? WHERE id = ?", (real_story, MANUAL_BARE))
        conn.commit()
    finally:
        conn.close()

    payload = _get_manual(client, auth_headers)
    bare = _row_by_id(payload, MANUAL_BARE)
    assert bare["story_text"] == real_story, bare["story_text"]

    r = client.post(f"/config/api/badge/manual/{MANUAL_BARE}",
                    json={"action": "award", "achieved_date": str(_cst_today())},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["story_text"] == real_story

    # 两者都是 '无' / 空 → 回落 '故事准备中'
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE achievements SET story_short = '无', description = '无' WHERE id = ?",
            (MANUAL_BARE,))
        conn.commit()
    finally:
        conn.close()
    payload = _get_manual(client, auth_headers)
    assert _row_by_id(payload, MANUAL_BARE)["story_text"] == "故事准备中"

    # story_short 清空 (NULL) + description 有真内容 → 回落 description
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE achievements SET story_short = NULL, description = '轮指练到腕子发酸。' "
            "WHERE id = ?", (MANUAL_BARE,))
        conn.commit()
    finally:
        conn.close()
    payload = _get_manual(client, auth_headers)
    assert _row_by_id(payload, MANUAL_BARE)["story_text"] == "轮指练到腕子发酸。"
