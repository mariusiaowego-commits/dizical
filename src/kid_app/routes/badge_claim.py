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

Sprint 26092901 fix/badge-claim-db-260929 (P0 修复: 线上长期 500):
  旧版 `_open_db()` 直连本地 sqlite (`data/dizi.db`)。线上 CloudRun 走云 MySQL,
  但容器镜像里那份 `data/dizi.db` 是构建时的老文件 (没有 achievement_* 三张表)
  → `/api/badge/unclaimed` 报 `no such table: achievement_stats` 500。
  该错误在 9-19 那版镜像上就已存在 (pod dizical-prod-132, 9-28 20:51/20:56/21:07)。
  修法 (对齐 badge_db.py PR #287 的范式):
    - 连接走 `src.db_adapter.get_conn()` (MySQL = src.database 连接池 / SQLite = settings.db_path)
    - 占位符统一 `?`, adapter 内部按后端转 `%s`
    - 读用 `execute_dicts` (列名取值 + datetime → str 归一化)
    - 写用 `execute` + `commit`
    - 异常捕获宽化: 旧版只捕 `sqlite3.OperationalError`, MySQL 下 pymysql 异常会击穿成 500
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src import db_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/badge", tags=["badge-claim"])


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


def _open_db():
    """统一连接入口 (双后端).

    Sprint 26092901: 替换旧版直连 sqlite 的 `_open_db()`。
    MySQL 走 src.database 连接池, SQLite 走 settings.db_path (单测可 monkeypatch)。

    Returns:
        (conn, is_mysql) — 调用方负责 conn.close() (MySQL 下 = 归还连接池)。
    """
    return db_adapter.get_conn()


def _close_quietly(conn) -> None:
    """关连接但不让关闭异常影响响应 (MySQL 池归还失败不该变 500)."""
    try:
        conn.close()
    except Exception as e:  # pragma: no cover - 关闭异常只记日志
        logger.warning(f"badge_claim close failed: {e}")


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
          a.card_no      AS card_no,
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
        conn, _ = _open_db()
    except Exception as e:
        # DB 连不上 / 配置缺失 → 503 降级 (旧版此处只捕 sqlite3.OperationalError)
        logger.error(f"badge_claim open db failed: {e}")
        return JSONResponse(
            {"unclaimed_count": 0, "badges": [], "error": "db_unreachable"},
            status_code=503,
        )

    try:
        # execute_dicts: 列名取值 + MySQL datetime → ISO 字符串 (避免 JSONResponse TypeError)
        rows = db_adapter.execute_dicts(conn, sql)
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
                    # sprint 26091301 B1: 图鉴编号 (可空 — 前端 None 时显示 '—')
                    "card_no": r["card_no"],
                    "badge_url": r["badge_url"],
                    "achieved_at": r["achieved_at"],
                }
            )
        return JSONResponse({"unclaimed_count": len(badges), "badges": badges})
    except Exception as e:
        # 表/列缺失 (迁移未跑) / 连接中断 / 其它后端异常 → 503 降级, 不抛 500
        logger.error(f"badge_claim unclaimed query failed: {e}")
        return JSONResponse(
            {"unclaimed_count": 0, "badges": [], "error": "db_unreachable"},
            status_code=503,
        )
    finally:
        _close_quietly(conn)


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
        conn, _ = _open_db()
    except Exception as e:
        logger.error(f"badge_claim open db failed: {e}")
        return JSONResponse(
            {"status": "error", "error": "db_unreachable"}, status_code=503
        )

    try:
        # 1. 幂等 UPDATE
        cur = db_adapter.execute(conn, update_sql, (claimed_at_iso, badge_id))
        rowcount = getattr(cur, "rowcount", 0) or 0
        conn.commit()

        if rowcount == 0:
            # 已领取过 / 不存在 / 未达成, 返幂等语义
            # 区分: 真已领取 vs 真不存在 vs 未达成
            check_rows = db_adapter.execute_dicts(
                conn,
                "SELECT achieved, claimed_at FROM achievement_stats "
                "WHERE achievement_id = ?",
                (badge_id,),
            )
            check = check_rows[0] if check_rows else None
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
            db_adapter.execute(
                conn,
                audit_sql,
                (
                    "web",
                    "badge_claim",
                    practice_date,
                    json.dumps({"badge_id": badge_id}),
                    json.dumps({"claimed_at": claimed_at_iso}),
                    # session_id: badge 领取无练习 session 语义, 留空 (原误塞 badge_id)
                    None,
                    badge_id,
                ),
            )
            conn.commit()
        except Exception as e:
            # audit 写失败不阻塞主流程 (业务已落地, 审计是辅助)。
            # Sprint 26092901: 旧版只捕 sqlite3.OperationalError → MySQL 下审计报错会把
            # 主业务成功响应带崩成 500, 这里宽化为 Exception。
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
    except Exception as e:
        # 领取写路径异常 (缺表 / 连接中断 / 后端差异) → 503 降级, 不抛 500
        logger.error(f"badge_claim claim failed (badge={badge_id}): {e}")
        return JSONResponse(
            {"status": "error", "error": "db_unreachable"}, status_code=503
        )
    finally:
        _close_quietly(conn)
