"""
Badge 制作工作流路由 (V2, 2026-06-12 重构).

V2 设计 (用户拍板):
- STEP 1 表单填元数据 → 调 POST /api/badge/draft 写 lib/badge_data/{id}.json → 返 draft_id
- STEP 2 hermes chat 调 skill → 调 (subprocess) 调 POST /api/badge/draft/{id} 写回 image 字段 + 状态变更
- STEP 3 待确认 Tab → 调 GET /api/badge/discoveries 拉待确认列表 → 调 POST /api/badge/commit-from-draft 写三表

V2 端点 (3 个, 替代 V1 7 个):
  POST /config/api/badge/draft                 - STEP 1: 创建 draft, 返 draft_id + json
  GET  /config/api/badge/draft/{draft_id}      - STEP 2: skill 读 draft, 调 image_gen
  POST /config/api/badge/commit-from-draft     - STEP 3: 确认上线, 写三表
  GET  /config/api/badge/discoveries           - STEP 3: 拉待确认列表 (按需扫, 不后台)

设计原则 (用户 2026-06-12 OUT-OF-BAND):
- 不后台定时器 (浪费资源)
- 文件契约: lib/badge_data/*.json (dizical 跟 hermes skill 跨进程交流唯一接口)
- schema_version=1 锁定 (未来改 schema +1, 老 dizical 端只读 schema=1 字段)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["badge-workflow"])


# ─── Pydantic models (替代手写 json.loads) ───────────────────────────

class DraftRequest(BaseModel):
    """STEP 1 收 meta."""
    meta: dict[str, Any]


class CommitFromDraftRequest(BaseModel):
    """STEP 3 收 draft_id."""
    draft_id: str = Field(..., min_length=1)


# ─── helpers ───────────────────────────────────────────────────────
# V2 设计: dad_pin 验证在前端 localStorage (V1.1 PIN 模式), 端点不做
# server-side PIN check (V1 routes/badge_workflow.py 9 端点全有 _check_pin
# 已删, V2 3 端点信任 caller = dizical web UI 跟 hermes skill)


# ─── GET /config/badge (HTML page) ───────────────────────────────

@router.get("/badge", response_class=HTMLResponse)
def config_badge():
    """config-badge.html 2 tab 页面 (V2: 新建 draft + 待确认).

    PIN 验证前端 localStorage 控制.
    """
    from src.kid_app.app import render
    from src.database import db
    pin_locked = "true" if db.get_setting("dad_pin") else "false"
    return render(
        "config-badge",
        pin_locked=pin_locked,
    )


# ─── POST /config/api/badge/draft (STEP 1) ───────────────────────

@router.post("/api/badge/draft")
def api_create_draft(req: DraftRequest) -> JSONResponse:
    """STEP 1: 收 meta, 写 lib/badge_data/{draft_id}.json, 返 draft_id + json."""
    from src.kid_app import badge_draft

    if not req.meta:
        return JSONResponse({"ok": False, "error": "缺 meta 字段"}, status_code=400)

    try:
        draft = badge_draft.create_draft(req.meta)
        badge_draft.save_draft(draft)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

    import json
    return JSONResponse({
        "ok": True,
        "draft_id": draft.draft_id,
        "json": json.dumps(draft.to_dict(), ensure_ascii=False, indent=2),
    })


# ─── GET /config/api/badge/draft/{draft_id} (STEP 2 read) ────────

@router.get("/api/badge/draft/{draft_id}")
def api_get_draft(draft_id: str) -> JSONResponse:
    """STEP 2: skill 读 draft (校验 + 返完整 draft).

    Returns:
        {ok: True, draft: dict} or {ok: False, error: str}
    """
    from src.kid_app import badge_draft

    draft = badge_draft.get_draft(draft_id)
    if draft is None:
        return JSONResponse({"ok": False, "error": f"draft '{draft_id}' 不存在"}, status_code=404)

    return JSONResponse({"ok": True, "draft": draft.to_dict()})


# ─── POST /config/api/badge/commit-from-draft (STEP 3 write) ─────

@router.post("/api/badge/commit-from-draft")
def api_commit_from_draft(req: CommitFromDraftRequest) -> JSONResponse:
    """STEP 3: 收 draft_id, 校验 + 写三表 + 标 status=committed.

    Returns:
        {ok: True, badge_id: str, image_url: str}
    """
    from src.kid_app import badge_draft, badge_db, badge_generator

    draft = badge_draft.get_draft(req.draft_id)
    if draft is None:
        return JSONResponse({"ok": False, "error": f"draft '{req.draft_id}' 不存在"}, status_code=404)

    if draft.status != "draft_awaiting_confirm":
        return JSONResponse({
            "ok": False,
            "error": f"draft 状态 '{draft.status}' 不允许 commit (必须是 draft_awaiting_confirm)",
        }, status_code=400)

    if draft.image is None:
        return JSONResponse({"ok": False, "error": "draft 还没 image 字段"}, status_code=400)

    badge_id = draft.meta.get("id")
    if not badge_id:
        return JSONResponse({"ok": False, "error": "draft.meta 缺 id 字段"}, status_code=400)

    # 跟 DB 重复检查
    if badge_db.badge_exists(badge_id):
        return JSONResponse({
            "ok": False,
            "error": f"DB 已有 id='{badge_id}' 的 badge, 不能重复 commit (V1.1 暂无删除 API)",
        }, status_code=409)

    try:
        # 1. 复制临时图到 static/badges/{id}_v{n}.png
        static_path = badge_draft.move_tmp_to_static(req.draft_id, draft.version)

        # 2. 调 badge_db 写三表 (achievements + stats + badges)
        # V2 注意: V1 insert_achievement_row 必填 stat_logic, V2 meta 简化表单不收集
        # 默认 "无" (V2.1 calc 修法 1 走 git apply 写 achievement_definitions.py, 跟这里解耦)
        meta_for_db = dict(draft.meta)
        meta_for_db.setdefault("stat_logic", "无")
        with badge_db.badge_write_tx() as conn:
            badge_db.insert_achievement_row(conn, meta_for_db)
            if draft.meta.get("category") == "milestone":
                badge_db.insert_achievement_stats_row(conn, badge_id)
            badge_db.insert_badge_row(
                conn,
                badge_id=badge_id,
                url=f"/static/badges/{badge_id}_v{draft.version}.png",
                version=draft.version,
            )

        # 3. 状态变 committed
        badge_draft.mark_draft_status(req.draft_id, "committed", by="dizical",
                                    extra={"event": "user_confirmed", "badge_id": badge_id})

        # 4. 清理临时图
        badge_draft.cleanup_tmp(req.draft_id, draft.version)
    except Exception as e:
        logger.exception("commit_from_draft failed for %s", req.draft_id)
        return JSONResponse({"ok": False, "error": f"commit 失败: {e}"}, status_code=500)

    return JSONResponse({
        "ok": True,
        "badge_id": badge_id,
        "image_url": f"/static/badges/{badge_id}_v{draft.version}.png",
    })


# ─── GET /config/api/badge/discoveries (STEP 3 list) ─────────────

@router.get("/api/badge/discoveries")
def api_discoveries(request: Request) -> JSONResponse:
    """STEP 3: 按需扫 lib/badge_data/, 返 [draft_awaiting_confirm] 列表.

    不缓存, 不后台 (用户拍板). 单次调用 < 50ms (10 个 draft 内).
    """
    from src.kid_app import badge_discovery

    items = badge_discovery.get_pending_confirmations()
    return JSONResponse({"ok": True, "data": items, "count": len(items)})
