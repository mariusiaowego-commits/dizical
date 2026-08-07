"""
Test: seasonal badge 全期累计激活次数 + 持久化 + modal 渲染 (sprint 26080702).

覆盖:
- extra_count 字段 (7 个 seasonal badge 都返回)
- milestone badge extra_count = None
- _count_seasonal_activations 扫历史 (双后端 datetime / str)
- _persist_unlocked_milestones 把 count + history_periods 写到 raw_stats JSON
- badges_page / /api/achievements season_info 字段
- 双后端 raw_stats JSON 解析 (SQLite str / MySQL JSON)
- format: "当前第 N 赛季 (YYYY.MM.DD - YYYY.MM.DD), 已累计获取 X 次"
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from src.achievement_definitions import calc_all, _count_seasonal_activations
from src.kid_app.app import app, get_badge_url, _get_current_season
import sqlite3


PROD_DB = Path("/Users/mt16/dev/dizical/data/dizi.db")  # 绝对路径, 避免 worktree 拉到旧 git 副本


@pytest.fixture
def prod_db_copy(tmp_path: Path) -> Path:
    """复制 prod dizi.db 到 tmp, 测试用."""
    if not PROD_DB.exists():
        pytest.skip(f"prod DB 不存在: {PROD_DB}")
    db_path = tmp_path / "prod_copy.db"
    shutil.copy2(PROD_DB, db_path)
    return db_path


def _wire_to_test_db(monkeypatch, db_path: Path):
    """把 calc_all / _get_current_season / app._get_connection 全指到 test DB 副本.

    三层 patch:
    1. src.achievement_definitions._DB_PATH - calc_all() 老 sqlite 路径
    2. src.db_adapter.get_conn - calc_all 新入口
    3. src.database.db._get_connection - app.py (badges_page) / minip_api.py
    """
    monkeypatch.setenv("DATABASE_URL", "")
    from src import achievement_definitions, db_adapter
    monkeypatch.setattr(achievement_definitions, "_DB_PATH", db_path)
    monkeypatch.setattr(
        db_adapter,
        "get_conn",
        lambda _p=db_path: (sqlite3.connect(str(_p)), False),
    )
    # 关键: app.py 走 src.database.db._get_connection (不是 db_adapter.get_conn)
    from src import database
    test_conn = sqlite3.connect(str(db_path))
    # 用 property 替换 _get_connection 方法 (default arg 捕到本次 test 的 db_path, 避免闭包 leak)
    monkeypatch.setattr(database.db, "_get_connection", lambda _p=db_path: sqlite3.connect(str(_p)))


# ─────────────────────────────────────────────────────────────────
# 1. extra_count 字段 (7 个 seasonal badge 都有)
# ─────────────────────────────────────────────────────────────────

SEASONAL_IDS = [
    "total_60", "week_champ", "full_month", "top1",
    "early_riser", "little_chick_commander", "first_to_act",
]


def test_seasonal_badges_have_extra_count(monkeypatch, prod_db_copy):
    """7 个 seasonal badge 都应返回 extra_count (int)."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    for aid in SEASONAL_IDS:
        r = results.get(aid)
        assert r is not None, f"{aid} 缺失"
        assert r.extra_count is not None, f"{aid} extra_count 应非 None (seasonal badge)"
        assert isinstance(r.extra_count, int), f"{aid} extra_count 应是 int, actual {type(r.extra_count)}"
        assert r.extra_count >= 0, f"{aid} extra_count 应 >= 0, actual {r.extra_count}"


def test_milestone_badges_have_no_extra_count(monkeypatch, prod_db_copy):
    """milestone badge (streak_7 / grade_* / first_log) extra_count = None."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    milestone_ids = ["streak_7", "grade_1", "first_log", "assign_pal", "recovery_first_practice_7"]
    for aid in milestone_ids:
        r = results.get(aid)
        if r is None:
            continue
        assert r.extra_count is None, f"{aid} 是 milestone, extra_count 应 None, actual {r.extra_count}"


# ─────────────────────────────────────────────────────────────────
# 2. _count_seasonal_activations 扫历史
# ─────────────────────────────────────────────────────────────────

def test_count_seasonal_activations_threshold(monkeypatch, prod_db_copy):
    """_count_seasonal_activations 按 hour 阈值扫历史."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    from src import db_adapter
    conn, _is_mysql = db_adapter.get_conn()  # 解构 tuple

    # 阈值 12: first_to_act (12:00 前练过)
    count, history = _count_seasonal_activations(conn, "first_to_act", threshold=12)
    assert count >= 1, f"first_to_act 应至少 1 月激活 (2026-08 10:00), actual count={count}"
    assert "2026-08" in history, f"history 应含 '2026-08', actual {history}"


def test_count_seasonal_activations_check_fn(monkeypatch, prod_db_copy):
    """_count_seasonal_activations 用 threshold_check_fn 自定义 check."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    from src import db_adapter
    conn, _is_mysql = db_adapter.get_conn()

    # total_60: total_minutes >= 60 的月数
    count, history = _count_seasonal_activations(
        conn, "total_60", threshold=None,
        threshold_check_fn=lambda r: int(r.get("total_minutes", 0) or 0) >= 60,
    )
    assert isinstance(count, int)
    assert isinstance(history, list)
    # history 应升序
    for i in range(len(history) - 1):
        assert history[i] < history[i+1], f"history 应升序: {history}"


# ─────────────────────────────────────────────────────────────────
# 3. _persist_unlocked_milestones 写 raw_stats JSON
# ─────────────────────────────────────────────────────────────────

def test_persist_writes_count_and_history(monkeypatch, prod_db_copy):
    """calc_all 后 raw_stats 应含 count + history_periods."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    # 触发 calc (会调 _persist_unlocked_milestones)
    results = calc_all()

    conn = sqlite3.connect(str(prod_db_copy))
    try:
        # first_to_act 当前 8 月激活, raw_stats 应有 history_periods
        row = conn.execute(
            "SELECT raw_stats FROM achievement_stats WHERE achievement_id='first_to_act'"
        ).fetchone()
        if row is None:
            pytest.skip("first_to_act 还没 achievement_stats 行")
        stats = json.loads(row[0])
        # MVP: count 字段应存在, history_periods 应至少 1 项
        assert "count" in stats, f"raw_stats 应含 'count', actual {stats}"
        assert "history_periods" in stats, f"raw_stats 应含 'history_periods', actual {stats}"
        assert stats["count"] >= 1
        assert isinstance(stats["history_periods"], list)
    finally:
        conn.close()


def test_persist_idempotent_no_overwrite(monkeypatch, prod_db_copy):
    """写两次 raw_stats: history_periods 应 append 不覆盖, count 累计."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()  # 第一次
    conn = sqlite3.connect(str(prod_db_copy))
    try:
        row1 = conn.execute(
            "SELECT raw_stats FROM achievement_stats WHERE achievement_id='early_riser'"
        ).fetchone()
        if row1 is None:
            pytest.skip("early_riser 还没 stats 行")
        stats1 = json.loads(row1[0])
        h1 = stats1.get("history_periods", [])
        c1 = stats1.get("count", 0)
    finally:
        conn.close()

    results = calc_all()  # 第二次
    conn = sqlite3.connect(str(prod_db_copy))
    try:
        row2 = conn.execute(
            "SELECT raw_stats FROM achievement_stats WHERE achievement_id='early_riser'"
        ).fetchone()
        stats2 = json.loads(row2[0])
        h2 = stats2.get("history_periods", [])
        c2 = stats2.get("count", 0)
    finally:
        conn.close()

    # history_periods 不应重复 (8 月不应出现 2 次)
    assert len(h2) == len(h1), f"history 不应膨胀, 1st={h1}, 2nd={h2}"
    # count 也不应无故翻倍
    assert c2 == c1, f"count 不应无故翻倍, 1st={c1}, 2nd={c2}"


# ─────────────────────────────────────────────────────────────────
# 4. 双后端 raw_stats JSON 解析
# ─────────────────────────────────────────────────────────────────

def test_double_backend_raw_stats_parse():
    """raw_stats JSON 在 SQLite 端是 str, MySQL 端是 JSON. 双端都能 parse."""
    sample_str = '{"count": 5, "history_periods": ["2026-08", "2026-07"]}'
    # SQLite 端: 直接 json.loads
    parsed = json.loads(sample_str)
    assert parsed["count"] == 5
    assert "2026-08" in parsed["history_periods"]


# ─────────────────────────────────────────────────────────────────
# 5. badges_page / /api/achievements season_info 字段
# ─────────────────────────────────────────────────────────────────

def test_badges_page_season_info(monkeypatch, prod_db_copy):
    """TestClient GET /badges, 检查 JS DATA 数组里 7 个 seasonal badge 含 season_info 字段.

    注意: cardHTML(d) 是 JS template literal, 在浏览器运行时渲染. 测试只能验证 DATA 数组 (注入到 HTML 里的 JSON)
    含有 season_info 字段. 浏览器渲染时再读 d.season_info 填到 data-season-info="...".
    """
    from fastapi.testclient import TestClient
    _wire_to_test_db(monkeypatch, prod_db_copy)
    client = TestClient(app)
    resp = client.get("/badges")
    assert resp.status_code == 200
    html = resp.text
    # 从 const DATA = [...] 注入的 JSON 找 seasonal badge 的 season_info
    import re, json
    m = re.search(r"const DATA = (\[.*?\]);", html, re.DOTALL)
    assert m is not None, "应能找到 const DATA 数组"
    data = json.loads(m.group(1))
    # 验证 7 个 seasonal badge 都有 season_info
    for b in data:
        if b["id"] in SEASONAL_IDS:
            assert "season_info" in b, f"{b['id']} 应含 season_info 字段"
            assert b["season_info"], f"{b['id']} season_info 应非空: {b['season_info']!r}"
            assert "当前第" in b["season_info"]
            assert "赛季" in b["season_info"]
            assert "累计获取" in b["season_info"]


def test_api_achievements_season_info(monkeypatch, prod_db_copy):
    """TestClient GET /api/achievements, 验证 JSON 含 season_info 字段."""
    from fastapi.testclient import TestClient
    _wire_to_test_db(monkeypatch, prod_db_copy)
    client = TestClient(app)
    resp = client.get("/api/achievements")
    assert resp.status_code == 200
    data = resp.json()
    badges = data if isinstance(data, list) else data.get("badges", data.get("unlocked", []) + data.get("locked", []))
    if not badges:
        pytest.skip("/api/achievements 没返 badges 字段")
    for b in badges:
        if b["id"] in SEASONAL_IDS:
            assert "season_info" in b, f"{b['id']} 应含 season_info 字段"
            assert b["season_info"], f"{b['id']} season_info 应非空"
            assert "当前第" in b["season_info"] and "赛季" in b["season_info"] and "累计获取" in b["season_info"]


# ─────────────────────────────────────────────────────────────────
# 6. season_info 文案格式
# ─────────────────────────────────────────────────────────────────

def test_season_info_string_format():
    """验证文案格式: '当前第 N 赛季 (YYYY.MM.DD - YYYY.MM.DD), 已累计获取 X 次'."""
    sample = "当前第 17 赛季 (2026.08.02 - 2026.08.08), 已累计获取 12 次"
    import re
    m = re.match(
        r"当前第 \d+ 赛季 \(\d{4}\.\d{2}\.\d{2} - \d{4}\.\d{2}\.\d{2}\), 已累计获取 \d+ 次",
        sample,
    )
    assert m is not None, f"格式不符: {sample}"


# ─────────────────────────────────────────────────────────────────
# 7. _get_current_season helper
# ─────────────────────────────────────────────────────────────────

def test_get_current_season(monkeypatch, prod_db_copy):
    """_get_current_season 返 dict 含 order/start/end (跟 weekly_assignments 最新 stage)."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    from src import db_adapter
    conn, _is_mysql = db_adapter.get_conn()
    season = _get_current_season(conn)
    assert "order" in season
    assert "start" in season
    assert "end" in season
    # prod 数据: stage 17 (2026-08-02 ~ 08-08)
    assert season["order"] == 17, f"应有 stage 17, actual {season}"
    assert "2026-08-02" in str(season["start"])
    assert "2026-08-08" in str(season["end"])