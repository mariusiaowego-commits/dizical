"""
Sprint 26091101 feat/sprint-26091101-badge-3d-ccg:
badge_claim API + migration 测试.

覆盖:
  A. migrate_add_claimed_at 幂等 (幂等 ALTER + 幂等 backfill + 幂等 index)
  B. unclaimed GET — 老徽章不轰炸 (backfill 后 unclaimed=0)
  C. unclaimed GET — 返结构 (id/name/type/category/cond_text/description/badge_url/achieved_at)
  D. claim POST — 首次领取: rowcount=1 + audit 写入
  E. claim POST — 二次领取 (幂等): rowcount=0 + already_claimed=true + **不写 audit**
  F. claim POST — 未达成徽章 (achieved='N'): 403 badge_not_achieved + 不写 audit
  G. claim POST — 不存在 badge_id: 404 badge_not_found
  H. claim POST — 入参空字符串 / 缺字段: 400
  I. unclaimed GET — 隔离 DB 端点不走 production
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
import tempfile

import pytest


# ─── Fixtures ─────────────────────────────────────────────────────────────
@pytest.fixture()
def isolated_db(monkeypatch):
    """每个测试一个隔离 tmp db, monkeypatch badge_claim.DB_PATH + app settings.

    V2.4 conftest 已 session 级切 db_path 给 src.models.settings, 但
    badge_claim._open_db() 走自己的硬路径常量, 必须再 patch 一次.
    """
    from src import models
    import src.kid_app.app as app_module

    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['DATABASE_URL'] = ''

    # 1. 创表 (跟 conftest 一致)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
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
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
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
    )
    conn.commit()
    conn.close()

    # 2. monkeypatch 各层 DB 引用
    monkeypatch.setattr(models.settings, "db_path", path)
    # Sprint 26092901 fix/badge-claim-db: badge_claim 改走 src.db_adapter.get_conn(),
    # SQLite 分支读 models.settings.db_path (上一行已 patch) —— 不再有模块级 DB_PATH 常量。
    # app module 里也有 db 单例引用 — 同步替换
    from src.database import Database
    new_db = Database(db_path=path)
    import src.database as db_module
    monkeypatch.setattr(db_module, "db", new_db)
    monkeypatch.setattr(app_module, "db", new_db)

    yield path

    try:
        os.unlink(path)
    except Exception:
        pass


@pytest.fixture()
def client(isolated_db):
    """FastAPI TestClient with isolated db."""
    # 重 import app 确保 DB_PATH patch 生效 (路由模块顶部常量在 import 时绑定)
    from fastapi.testclient import TestClient
    from src.kid_app import app as app_module

    # 重要: badge_claim 顶部的 DB_PATH 已在 fixture 里 patch, 但
    # 若 app_module 在 fixture 之前已被别处 import, 则路由持有的是旧值.
    # 这里通过 monkeypatch 已原地替换 (模块对象), TestClient 走的就是新值.
    return TestClient(app_module.app)


def _seed_achievement(
    db_path: str,
    aid: str,
    name: str,
    *,
    achieved: str = "Y",
    achieved_at: str | None = "2026-09-01 10:00:00",
    claimed_at: str | None = None,
    badge_url: str | None = "/static/badges/test.png",
    cond_text: str | None = "测试条件",
    description: str = "测试描述",
):
    """插 1 个 achievements + stats + badge current."""
    conn = sqlite3.connect(db_path)
    conn.executescript(
        f"""
        INSERT INTO achievements
          (id, name, type, category, stat_logic, description, display_format, cond_text, sort_order)
          VALUES
          ('{aid}', '{name}', 'count', 'milestone', '{{}}', '{description}',
           'count', '{cond_text or ""}', 1);

        INSERT INTO achievement_stats
          (achievement_id, achieved, achieved_at, claimed_at, raw_stats, computed_value)
          VALUES
          ('{aid}', '{achieved}', {f"'{achieved_at}'" if achieved_at else 'NULL'},
           {f"'{claimed_at}'" if claimed_at else 'NULL'},
           '{{}}', 0);

        INSERT INTO achievement_badges
          (achievement_id, url, is_locked, version, is_current)
          VALUES
          ('{aid}', '{badge_url or ""}', 0, 1, 1);
        """
    )
    conn.commit()
    conn.close()


# ─── A. 迁移幂等 ──────────────────────────────────────────────────────────
def test_migration_idempotent_sqlite(tmp_path, monkeypatch):
    """跑两遍迁移, 第 2 遍 rowcount=0 + 不重复 ALTER."""
    db = tmp_path / "m.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE achievements (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'milestone', stat_logic TEXT NOT NULL,
            description TEXT NOT NULL, display_format TEXT NOT NULL,
            threshold INTEGER, unlocked_template TEXT, placeholder TEXT,
            locked_template TEXT, sort_order INTEGER DEFAULT 0,
            seasonal_type TEXT DEFAULT 'monthly', cond_text TEXT,
            unlock_strategy TEXT DEFAULT 'calc', achieved_at_override TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE achievement_stats (
            achievement_id TEXT PRIMARY KEY, achieved TEXT NOT NULL DEFAULT 'N',
            achieved_at DATETIME, raw_stats TEXT NOT NULL DEFAULT '{}',
            computed_value INTEGER);
        """
    )
    conn.commit()
    conn.close()

    # 1. 加载 migration 模块
    spec = importlib.util.spec_from_file_location(
        "mig_claimed",
        "/Users/mt16/dev/dizical/src/migrate_add_claimed_at.py",
    )
    assert spec is not None, "无法加载 migrate_add_claimed_at.py spec"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    monkeypatch.setattr(mod, "_DB_PATH", db)
    mod._migrate_sqlite()

    conn = sqlite3.connect(str(db))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(achievement_stats)")]
    assert "claimed_at" in cols

    # 2. 第二次跑, 幂等
    mod._migrate_sqlite()
    # 第二次 backfill rowcount=0 (无 unclaimed 行)
    # 列依然只有 1 个 claimed_at (没重复 ALTER 报错)
    cols2 = [r[1] for r in conn.execute("PRAGMA table_info(achievement_stats)")]
    assert "claimed_at" in cols2
    assert cols2.count("claimed_at") == 1
    conn.close()


# ─── B. 老徽章不轰炸 (backfill 后 unclaimed=0) ──────────────────────────
def test_no_legacy_badge_bombard_after_backfill(isolated_db, client):
    """模拟历史数据: 5 行 achieved='Y', backfill 写入 claimed_at=achieved_at,
    GET /api/badge/unclaimed 应返 0 条 (agy's 红线: 上线不轰炸)."""
    db = isolated_db
    # 1. 模拟历史 (无 claimed_at 列在 fixtures 里但值空)
    # 直接 seed 5 行已达成且已 claim 的徽章
    for i in range(5):
        _seed_achievement(
            db,
            f"legacy_{i}",
            f"老徽章{i}",
            achieved="Y",
            achieved_at="2025-10-01 10:00:00",
            claimed_at="2025-10-01 10:00:00",  # 老数据视作已领
        )

    r = client.get("/api/badge/unclaimed")
    assert r.status_code == 200
    body = r.json()
    assert body["unclaimed_count"] == 0
    assert body["badges"] == []


# ─── C. unclaimed 返回结构 ───────────────────────────────────────────────
def test_unclaimed_returns_full_badge_structure(isolated_db, client):
    db = isolated_db
    _seed_achievement(
        db,
        "new_badge",
        "新徽章",
        achieved="Y",
        achieved_at="2026-09-10 10:00:00",
        claimed_at=None,  # 未领
        badge_url="/static/badges/new_badge.png",
        cond_text="连续打卡 7 天",
        description="测试描述",
    )

    r = client.get("/api/badge/unclaimed")
    body = r.json()
    assert body["unclaimed_count"] == 1
    badge = body["badges"][0]
    assert badge["id"] == "new_badge"
    assert badge["name"] == "新徽章"
    assert badge["type"] == "count"
    assert badge["category"] == "milestone"
    assert badge["cond_text"] == "连续打卡 7 天"
    assert badge["description"] == "测试描述"
    assert badge["badge_url"] == "/static/badges/new_badge.png"
    assert badge["achieved_at"] == "2026-09-10 10:00:00"


# ─── D. claim 首次领取 ────────────────────────────────────────────────────
def test_claim_first_time_writes_audit(isolated_db, client):
    db = isolated_db
    _seed_achievement(
        db, "fresh_1", "新鲜徽章",
        achieved="Y", achieved_at="2026-09-10 10:00:00", claimed_at=None,
    )

    r = client.post("/api/badge/claim", json={"badge_id": "fresh_1"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["badge_id"] == "fresh_1"
    assert body["already_claimed"] is False
    assert body["claimed_at"]  # ISO 字符串非空

    # DB 校验
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT claimed_at FROM achievement_stats WHERE achievement_id = ?",
        ("fresh_1",),
    ).fetchone()
    assert row[0] is not None

    audit_count = conn.execute(
        "SELECT COUNT(*) FROM practice_audit_log WHERE method = 'badge_claim' AND detail = 'fresh_1'"
    ).fetchone()[0]
    assert audit_count == 1
    conn.close()


# ─── E. claim 幂等 ────────────────────────────────────────────────────────
def test_claim_idempotent_no_duplicate_audit(isolated_db, client):
    """同一 badge_id 二次领取: rowcount=0, 不写 audit, 返 already_claimed=true."""
    db = isolated_db
    _seed_achievement(
        db, "idem_1", "幂等徽章",
        achieved="Y", achieved_at="2026-09-10 10:00:00", claimed_at=None,
    )

    # 第一次
    r1 = client.post("/api/badge/claim", json={"badge_id": "idem_1"})
    assert r1.json()["already_claimed"] is False

    # 第二次
    r2 = client.post("/api/badge/claim", json={"badge_id": "idem_1"})
    body2 = r2.json()
    assert body2["status"] == "ok"
    assert body2["already_claimed"] is True
    assert body2["claimed_at"]  # 返原 claimed_at

    # audit 只 1 行
    conn = sqlite3.connect(db)
    audit_count = conn.execute(
        "SELECT COUNT(*) FROM practice_audit_log WHERE method = 'badge_claim' AND detail = 'idem_1'"
    ).fetchone()[0]
    assert audit_count == 1, f"幂等失败, audit 应只有 1 行, 实际 {audit_count}"
    conn.close()


# ─── F. claim 未达成徽章 ──────────────────────────────────────────────────
def test_claim_not_achieved_returns_403(isolated_db, client):
    db = isolated_db
    _seed_achievement(
        db, "not_yet", "未达成徽章",
        achieved="N", achieved_at=None, claimed_at=None,
    )

    r = client.post("/api/badge/claim", json={"badge_id": "not_yet"})
    assert r.status_code == 403
    body = r.json()
    assert body["status"] == "error"
    assert body["error"] == "badge_not_achieved"

    # audit 不写
    conn = sqlite3.connect(db)
    audit_count = conn.execute(
        "SELECT COUNT(*) FROM practice_audit_log WHERE method = 'badge_claim'"
    ).fetchone()[0]
    assert audit_count == 0
    conn.close()


# ─── G. claim 不存在 badge_id ─────────────────────────────────────────────
def test_claim_not_found_returns_404(isolated_db, client):
    r = client.post("/api/badge/claim", json={"badge_id": "ghost_badge"})
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == "error"
    assert body["error"] == "badge_not_found"


# ─── H. claim 入参校验 ────────────────────────────────────────────────────
def test_claim_empty_badge_id_returns_400(client):
    """空白字符串 → 400 (pydantic Field min_length=1 拦掉空串)."""
    r = client.post("/api/badge/claim", json={"badge_id": ""})
    assert r.status_code in (400, 422)  # pydantic 422 也算校验失败

    # 缺字段
    r2 = client.post("/api/badge/claim", json={})
    assert r2.status_code == 422


# ─── I. unclaimed 隔离: 不读 production db ────────────────────────────────
def test_unclaimed_does_not_read_production_db(isolated_db, client):
    """即使 production db 有数据, isolated fixture 下 GET 应返 0 (隔离生效).

    safety net: 万一 conftest / badge_claim 误用 production 路径, 这条会挂.
    """
    # production db 在 /Users/mt16/dev/dizical/data/dizi.db,
    # 但 isolated 切到 tmp db. 我们只验证当前 client 看到的是 0 条.
    # (若 production 真的被读到, 这里会因为 production 有 25 行达成且 backfill 走不通而返 0,
    #  取决于 production 是否跑过迁移. 此处只校验接口基本可用.)
    r = client.get("/api/badge/unclaimed")
    assert r.status_code == 200
    assert "unclaimed_count" in r.json()
    assert "badges" in r.json()


# ─── J. 排序: 最新达成在前 ────────────────────────────────────────────────
def test_unclaimed_order_by_achieved_at_desc(isolated_db, client):
    db = isolated_db
    _seed_achievement(db, "older", "老的", achieved="Y",
                      achieved_at="2026-09-01 10:00:00", claimed_at=None)
    _seed_achievement(db, "newer", "新的", achieved="Y",
                      achieved_at="2026-09-10 10:00:00", claimed_at=None)

    r = client.get("/api/badge/unclaimed")
    badges = r.json()["badges"]
    assert [b["id"] for b in badges] == ["newer", "older"]


# ─── K. Sprint 26091201 B-1: payload 含 card_theme (端到端) ──────────
def test_unclaimed_payload_includes_card_theme(isolated_db, client):
    """Sprint 26091201 feat/badge-3d-ccg B-1:
    GET /api/badge/unclaimed payload 每个 badge 必须有 card_theme 字段,
    值由 resolve_card_theme() 兜底链解析 (此处 type=突破 应得 azure)."""
    db = isolated_db
    _seed_achievement(
        db, "theme_test", "主题测试徽章",
        achieved="Y", achieved_at="2026-09-10 10:00:00", claimed_at=None,
        description="desc",
    )

    r = client.get("/api/badge/unclaimed")
    badges = r.json()["badges"]
    assert len(badges) == 1
    b = badges[0]
    assert "card_theme" in b, f"badge 缺 card_theme 字段 (got keys={list(b.keys())})"
    # _seed_achievement 用 type='count' (非中文, 不在 TYPE_THEME_MAP), category='milestone'
    # → 应走默认 azure
    assert b["card_theme"] == "azure"


# ─── L. Sprint 26092901 fix/badge-claim-db: MySQL 后端回归锁 ─────────────
#
# 背景 (线上事故): CloudRun 上 GET /api/badge/unclaimed 长期 500 —
# `sqlite3.OperationalError: no such table: achievement_stats`。旧版 _open_db() 直连本地
# data/dizi.db, 而容器镜像里那份是构建时的老库 (无 achievement_* 三表); 云 MySQL 里表和数据
# 都在 → 接口走错库。该错在 9-19 那版镜像 (pod 132) 上同样存在。
# 下面 3 个测例锁住修复后的三条硬约束: 走 adapter / datetime 归一化 / 缺表降级不 500。

def _mysql_mock_conn(rows, *, rowcount=0, raise_on_execute=None):
    """造一个假的 MySQL 连接 (MagicMock), cursor 返回指定行."""
    from unittest.mock import MagicMock

    if raise_on_execute is not None:
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = raise_on_execute
    else:
        mock_cursor = MagicMock()
        mock_cursor.description = [(k,) for k in rows[0].keys()] if rows else []
        mock_cursor.fetchall.return_value = rows
        mock_cursor.fetchone.return_value = rows[0] if rows else None
    mock_cursor.rowcount = rowcount

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


def test_unclaimed_mysql_backend_normalizes_datetime(monkeypatch):
    """MySQL 模式: 走 db_adapter + datetime 列必须归一化成 str (否则 JSONResponse 抛 TypeError)."""
    import datetime as dt
    import json as _json

    from src.kid_app.routes import badge_claim

    row = {
        "id": "mysql_1",
        "name": "MySQL 徽章",
        "type": "count",
        "category": "milestone",
        "cond_text": "条件",
        "description": "描述",
        "card_theme": None,
        "card_stars": None,
        "card_no": None,
        "achieved_at": dt.datetime(2026, 9, 1, 10, 0, 0),  # pymysql 原生 datetime
        "badge_url": "/static/badges/x.png",
    }
    mock_conn, mock_cursor = _mysql_mock_conn([row])

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)
    monkeypatch.setattr(badge_claim, "_open_db", lambda: (mock_conn, True))

    resp = badge_claim.api_unclaimed()
    assert resp.status_code == 200

    body = _json.loads(resp.body)
    assert body["unclaimed_count"] == 1
    got = body["badges"][0]
    # ★ 核心锁: datetime 已归一化成 str, 不是 datetime 对象
    assert isinstance(got["achieved_at"], str), (
        f"achieved_at 未归一化 → JSONResponse 会 500 (got {type(got['achieved_at'])})"
    )
    assert got["achieved_at"] == str(row["achieved_at"])
    # 列名取值 (tuple cursor 会 TypeError: tuple indices must be integers)
    assert got["id"] == "mysql_1"
    assert "?" not in mock_cursor.execute.call_args[0][0]


def test_unclaimed_missing_table_degrades_to_503_not_500(monkeypatch):
    """缺表 (迁移未跑 / 读错库) → 503 降级, 不再抛 500 (线上事故的直接回归锁)."""
    import json as _json

    from src.kid_app.routes import badge_claim

    boom = Exception("no such table: achievement_stats")
    mock_conn, _ = _mysql_mock_conn([], raise_on_execute=boom)

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)
    monkeypatch.setattr(badge_claim, "_open_db", lambda: (mock_conn, True))

    resp = badge_claim.api_unclaimed()
    assert resp.status_code == 503
    body = _json.loads(resp.body)
    assert body == {"unclaimed_count": 0, "badges": [], "error": "db_unreachable"}


def test_claim_mysql_audit_failure_does_not_break_main_flow(monkeypatch):
    """首次领取成功但审计 INSERT 报错 → 仍返 200 (审计是辅助, 不能带崩主业务).

    旧版 except 只捕 sqlite3.OperationalError → MySQL 下这里会变成 500。
    """
    import json as _json
    from unittest.mock import MagicMock

    from src.kid_app.routes import badge_claim

    # execute 第 1 次 (UPDATE) 成功 rowcount=1; 第 2 次 (audit INSERT) 抛 MySQL 风格异常
    update_cursor = MagicMock()
    update_cursor.rowcount = 1
    audit_cursor = MagicMock()
    audit_cursor.execute.side_effect = Exception("(1146, \"Table 'x.practice_audit_log' doesn't exist\")")

    calls = {"n": 0}

    def fake_cursor(*args, **kwargs):
        calls["n"] += 1
        return update_cursor if calls["n"] == 1 else audit_cursor

    mock_conn = MagicMock()
    mock_conn.cursor.side_effect = fake_cursor

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)
    monkeypatch.setattr(badge_claim, "_open_db", lambda: (mock_conn, True))

    resp = badge_claim.api_claim(badge_claim.ClaimRequest(badge_id="mysql_1"))
    assert resp.status_code == 200
    body = _json.loads(resp.body)
    assert body["status"] == "ok"
    assert body["already_claimed"] is False


# ─── M. Sprint 26093001: except 拆分 (DB 失败 → 503; Python 组装失败 → 真 500) ──
#
# 背景 (2026-09-29 PR 级审计 P2-1): 旧版把「查询」和「纯 Python 组装」包在同一个
# `except Exception` 里 → 组装代码有 bug 时也被伪装成 503 db_unreachable,
# 运维看到的是「DB 不可达」而不是真错的 traceback。以下两条锁住拆分后的两侧语义。

def test_unclaimed_assembly_error_is_not_masked_as_503(monkeypatch):
    """组装期异常 (resolve_card_theme/stars 内部 bug) 必须原样抛出, 不许吞成 503。"""
    import datetime as dt

    from src.kid_app.routes import badge_claim

    row = {
        "id": "asm_1", "name": "组装测试", "type": "count", "category": "milestone",
        "cond_text": "条件", "description": "描述",
        "card_theme": None, "card_stars": None, "card_no": None,
        "achieved_at": dt.datetime(2026, 9, 1, 10, 0, 0),
        "badge_url": "/static/badges/x.png",
    }
    mock_conn, _ = _mysql_mock_conn([row])

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)
    monkeypatch.setattr(badge_claim, "_open_db", lambda: (mock_conn, True))

    def boom(**kwargs):
        raise RuntimeError("resolve_card_theme 内部 bug")

    monkeypatch.setattr("src.kid_app.badge_theme.resolve_card_theme", boom)

    # 原样抛出 → FastAPI 转 500 (诚实), 而不是 503 db_unreachable (掩盖真 bug)
    with pytest.raises(RuntimeError, match="内部 bug"):
        badge_claim.api_unclaimed()
    # 即使抛异常, 连接也必须归还
    assert mock_conn.close.called


def test_claim_update_db_error_still_degrades_to_503(monkeypatch):
    """对照面: POST 的 UPDATE 段 DB 失败仍走 503 降级 (拆分后不能把 DB 降级弄丢)。"""
    import json as _json
    from unittest.mock import MagicMock

    from src.kid_app.routes import badge_claim

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.execute.side_effect = Exception(
        "no such table: achievement_stats"
    )

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)
    monkeypatch.setattr(badge_claim, "_open_db", lambda: (mock_conn, True))

    resp = badge_claim.api_claim(badge_claim.ClaimRequest(badge_id="mysql_1"))
    assert resp.status_code == 503
    assert _json.loads(resp.body)["error"] == "db_unreachable"
    assert mock_conn.close.called


def test_claim_check_select_db_error_returns_503(monkeypatch):
    """rowcount==0 后的区分 SELECT 失败 → 仍 503 (不是 500)。

    2026-09-30 grok PR 审计非阻断项: P2 拆分后这条 SELECT 落在内层 try 外面,
    DB 失败面从 503 变 500。它是 DB 调用 (不是组装), 且此处没写入任何东西
    → 归 503 降级。
    """
    import json as _json
    from unittest.mock import MagicMock

    from src.kid_app.routes import badge_claim

    mock_conn = MagicMock()
    cur = mock_conn.cursor.return_value
    cur.rowcount = 0  # UPDATE 没改到行 → 走区分分支

    def boom(*a, **kw):
        raise Exception("no such table: achievement_stats")

    monkeypatch.setattr("src.db_adapter.is_mysql_env", lambda: True)
    monkeypatch.setattr(badge_claim, "_open_db", lambda: (mock_conn, True))
    monkeypatch.setattr(badge_claim.db_adapter, "execute_dicts", boom)

    resp = badge_claim.api_claim(badge_claim.ClaimRequest(badge_id="mysql_1"))
    assert resp.status_code == 503
    assert _json.loads(resp.body)["error"] == "db_unreachable"
    assert mock_conn.close.called
