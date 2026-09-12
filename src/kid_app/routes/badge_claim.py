"""
Sprint 26091101 feat/sprint-26091101-badge-3d-ccg:
徽章领取 API — 全局拦截弹窗 + 入库.

端点:
  GET  /api/badge/unclaimed    — 拉未领取徽章列表 (弹窗数据源)
  POST /api/badge/claim        — 幂等领取, 写 practice_audit_log

设计约束 (sprint 26091101 tech-spec §3):
  - 信任 caller = dizical web UI / mac-app WKWebView (跟 badge_workflow 同模式)
  - 弹窗是 child-facing, 不需 PIN
  - practice_audit_log.practice_date NOT NULL → 用当天 (CST) 占位, badge_id 走 detail
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/badge", tags=["badge-claim"])

# ─── 路径常量 ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent.parent.parent
DB_PATH = _ROOT / "data" / "dizi.db"


# ─── Pydantic models ──────────────────────────────────────────────────────
class ClaimRequest(BaseModel):
    """POST /api/badge/claim 入参."""

    badge_id: str = Field(..., min_length=1, max_length=64)


# ─── helpers ──────────────────────────────────────────────────────────────
def _cst_today_iso() -> str:
    """CST 当天 ISO date (跟 save_daily_practice 业务日期同语义, 避免 audit 报 NULL 违反 NOT NULL).

    Returns:
        'YYYY-MM-DD' (CST)
    """
    return (dt.datetime.utcnow() + dt.timedelta(hours=8)).strftime("%Y-%m-%d")


def _cst_now_iso() -> str:
    """CST 当前时间 ISO (跟 daily_practices.practice_at 同语义)."""
    return (dt.datetime.utcnow() + dt.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")


def _open_db() -> sqlite3.Connection:
    """直开 SQLite, 跟 badge_db.py / database.py 同路径约定.

    不用 db._get_connection() 是因为该方法在 app 启动时绑 settings.db_path,
    但 sprint 期间可能在 worktree 跑, 走直开更稳.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─── GET /api/badge/unclaimed ─────────────────────────────────────────────
@router.get("/unclaimed")
def api_unclaimed() -> JSONResponse:
    """返回当前未领取徽章列表 (achieved='Y' AND claimed_at IS NULL).

    Response:
        {
          "unclaimed_count": int,
          "badges": [
            {
              "id": str,           # achievements.id
              "name": str,         # achievements.name
              "type": str,
              "category": str,
              "cond_text": str | None,
              "description": str,  # achievements.description (替代 zh_story, 跟现有 calc 文案同源)
              "badge_url": str,    # achievement_badges 当前图 (is_current=1)
              "achieved_at": str | None
            }
          ]
        }
    """
    sql = """
        SELECT
          a.id           AS id,
          a.name         AS name,
          a.type         AS type,
          a.category     AS category,
          a.cond_text    AS cond_text,
          a.description       AS description,
          a.card_theme   AS card_theme,
          a.card_stars   AS card_stars,
          s.achieved_at  AS achieved_at,
          b.url          AS badge_url
        FROM achievement_stats s
        JOIN achievements a ON a.id = s.achievement_id
        LEFT JOIN achievement_badges b
          ON b.achievement_id = a.id AND b.is_current = 1
        WHERE s.achieved = 'Y'
          AND s.claimed_at IS NULL
        ORDER BY s.achieved_at DESC, a.sort_order ASC
    """
    try:
        conn = _open_db()
    except sqlite3.OperationalError as e:
        # DB 不存在 / 列缺失 (迁移未跑)
        logger.error(f"_open_db failed: {e}")
        return JSONResponse(
            {"unclaimed_count": 0, "badges": [], "error": "db_unreachable"},
            status_code=503,
        )

    try:
        rows = conn.execute(sql).fetchall()
        badges: list[dict[str, Any]] = []
        # Sprint 26091201 feat/badge-3d-ccg B-1: 兜底链解析 card_theme
        from src.kid_app.badge_theme import resolve_card_stars, resolve_card_theme
        for r in rows:
            badges.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "category": r["category"],
                    "cond_text": r["cond_text"],
                    "description": r["description"],
                    "card_theme": resolve_card_theme(
                        badge_type=r["type"],
                        card_theme=r["card_theme"],
                        category=r["category"],
                    ),
                    # dad image#9/4: 星级 (后端字段, 前端只钳位)
                    "card_stars": resolve_card_stars(
                        card_stars=r["card_stars"],
                        badge_type=r["type"],
                        category=r["category"],
                    ),
                    "badge_url": r["badge_url"],
                    "achieved_at": r["achieved_at"],
                }
            )
        return JSONResponse({"unclaimed_count": len(badges), "badges": badges})
    finally:
        conn.close()


# ─── POST /api/badge/claim ────────────────────────────────────────────────
@router.post("/claim")
def api_claim(req: ClaimRequest) -> JSONResponse:
    """幂等领取徽章.

    1. UPDATE achievement_stats SET claimed_at = now WHERE achieved='Y'
       AND claimed_at IS NULL  (原子, rowcount 决定 idempotent 语义)
    2. 若 rowcount > 0 → 写 practice_audit_log (channel='web', method='badge_claim')
       若 rowcount == 0 → 已领取过, 不写 audit (幂等不污染审计)

    Response 200:
        {
          "status": "ok",
          "badge_id": str,
          "claimed_at": str,            # 首次领取
          "already_claimed": bool       # true if 重复领取
        }
    """
    badge_id = req.badge_id.strip()
    if not badge_id:
        return JSONResponse(
            {"status": "error", "error": "badge_id 必填"}, status_code=400
        )

    claimed_at_iso = _cst_now_iso()
    practice_date = _cst_today_iso()  # audit 表 practice_date NOT NULL 占位

    update_sql = (
        "UPDATE achievement_stats "
        "SET claimed_at = ? "
        "WHERE achievement_id = ? AND achieved = 'Y' AND claimed_at IS NULL"
    )
    audit_sql = (
        "INSERT INTO practice_audit_log "
        "(channel, method, practice_date, input_items, result_items, session_id, detail) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )

    try:
        conn = _open_db()
    except sqlite3.OperationalError as e:
        logger.error(f"_open_db failed: {e}")
        return JSONResponse(
            {"status": "error", "error": "db_unreachable"}, status_code=503
        )

    try:
        # 1. 幂等 UPDATE
        cur = conn.execute(update_sql, (claimed_at_iso, badge_id))
        rowcount = cur.rowcount
        conn.commit()

        if rowcount == 0:
            # 已领取过 / 不存在 / 未达成, 返幂等语义
            # 区分: 真已领取 vs 真不存在 vs 未达成
            check = conn.execute(
                "SELECT achieved, claimed_at FROM achievement_stats "
                "WHERE achievement_id = ?",
                (badge_id,),
            ).fetchone()
            if check is None:
                return JSONResponse(
                    {"status": "error", "error": "badge_not_found"},
                    status_code=404,
                )
            if check["achieved"] != "Y":
                return JSONResponse(
                    {"status": "error", "error": "badge_not_achieved"},
                    status_code=403,
                )
            # 真已领取 — 不写 audit, 返 already_claimed=true
            return JSONResponse(
                {
                    "status": "ok",
                    "badge_id": badge_id,
                    "already_claimed": True,
                    "claimed_at": check["claimed_at"],
                }
            )

        # 2. 首次领取成功 → 写审计
        try:
            conn.execute(
                audit_sql,
                (
                    "web",
                    "badge_claim",
                    practice_date,
                    json.dumps({"badge_id": badge_id}),
                    json.dumps({"claimed_at": claimed_at_iso}),
                    badge_id,
                    badge_id,
                ),
            )
            conn.commit()
        except sqlite3.OperationalError as e:
            # audit 写失败不阻塞主流程 (业务已落地, 审计是辅助)
            logger.warning(
                f"badge_claim audit insert failed (badge={badge_id}): {e}"
            )

        return JSONResponse(
            {
                "status": "ok",
                "badge_id": badge_id,
                "claimed_at": claimed_at_iso,
                "already_claimed": False,
            }
        )
    finally:
        conn.close()