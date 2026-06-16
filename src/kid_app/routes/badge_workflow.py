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


class AICondRequest(BaseModel):
    """ai-cond 端点收 name + placeholder + zh_story + type."""
    name: str = Field(..., min_length=1)
    type: str = ""
    placeholder: str = Field(..., min_length=1)
    zh_story: str = Field(..., min_length=1)


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
    from src.kid_app import badge_draft, badge_db

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
        # Bug #1 修法 (2026-06-15): commit handler 用 image.version 不用顶层 version.
        # 根因: hermes chat 多轮时直接编辑 draft.json 改 image.version=2,
        # 但顶层 draft.version 还是 1. 修前 commit 复制 v1.png, url 写 _v1.png,
        # 前端加载到 v1 (旧图) 而不是 v2 (新图).
        # 修后: commit 拿 image_version 单一数据源, 顶层 version 写库前同步.
        if draft.image is None:
            return JSONResponse({"ok": False, "error": "draft 还没 image 字段"}, status_code=400)
        image_version = draft.image.get("version", draft.version)

        # 1. 复制临时图到 static/badges/{id}_v{image_version}.png
        static_path = badge_draft.move_tmp_to_static(req.draft_id, image_version)

        # 2. 调 badge_db 写三表 (achievements + stats + badges)
        # V2 注意: V1 insert_achievement_row 必填 stat_logic + description,
        # V2 meta 简化表单不收集, commit handler 默认值兜底
        # (V2.1 calc 修法 1 走 git apply 写 achievement_definitions.py, 跟这里解耦)
        # Bug #4 修法 (2026-06-15): description 取 meta.zh_story (典故小故事),
        # 不是默认"无". stat_logic 改空字符串 (calc 不靠它, 留"无"是历史包袱).
        meta_for_db = dict(draft.meta)
        meta_for_db["description"] = meta_for_db.get("zh_story") or "无"
        meta_for_db["stat_logic"] = ""
        # feat/badge-cond-text (2026-06-15): cond_text 字段.
        # - 用户填 / AI 生成 → 写
        # - 缺 / 空 → 写 None (DB nullable) 走前端 fallback 到 desc
        # 显式不 setdefault "" (老数据兼容, DB 允许 NULL)
        if "cond_text" in meta_for_db and meta_for_db["cond_text"] is not None:
            # 用户的空字符串保留为 "" (跟 None 区分)
            pass
        else:
            # 缺字段 → None (DB 默认, 老 draft 不报错)
            meta_for_db["cond_text"] = meta_for_db.get("cond_text")  # None

        # feat/badge-unlock-strategy (2026-06-16): unlock_strategy 字段
        # - 'immediate': commit 时直接 achieved='Y' + achieved_at=now (纪念章场景)
        # - 'calc' (默认): 老行为, achieved='N', 走 calc 评估
        # - 缺字段 → 默认 'calc' (老 data 兼容)
        # - enum 校验: 拒绝 invalid 值
        unlock_strategy = draft.meta.get("unlock_strategy", "calc")
        if unlock_strategy not in ("immediate", "calc"):
            return JSONResponse({
                "ok": False,
                "error": f"unlock_strategy 必须是 'immediate' 或 'calc', 收到: {unlock_strategy!r}",
            }, status_code=400)
        meta_for_db["unlock_strategy"] = unlock_strategy

        # V2.6 (2026-06-16) feat/badge-achieved-at-override: 通用字段
        # - grade 1-10 考出时间, 表彰型徽章 etc.
        # - 用户填 → 写 db (TEXT YYYY-MM-DD, nullable)
        # - 留空 → None
        achieved_at_override = draft.meta.get("achieved_at_override", "").strip() or None
        meta_for_db["achieved_at_override"] = achieved_at_override

        # 立即解锁时 achieved_at = 当前 UTC ISO
        if unlock_strategy == "immediate":
            import datetime as _dt
            achieved_at_iso = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        elif achieved_at_override:
            # V2.6: 纪念章 + override 路径, achieved_at = override 时间
            achieved_at_iso = achieved_at_override + " 00:00:00"
        else:
            achieved_at_iso = None

        with badge_db.badge_write_tx() as conn:
            badge_db.insert_achievement_row(conn, meta_for_db)
            if draft.meta.get("category") == "milestone":
                # V2.6: override 也立即 unlocked
                is_unlocked_now = (unlock_strategy == "immediate" or achieved_at_override)
                badge_db.insert_achievement_stats_row(
                    conn, badge_id,
                    achieved="Y" if is_unlocked_now else "N",
                    achieved_at=achieved_at_iso,
                )
            badge_db.insert_badge_row(
                conn,
                badge_id=badge_id,
                url=f"/static/badges/{badge_id}_v{image_version}.png",
                version=image_version,
            )

        # 3. 状态变 committed + 顶层 version 跟 image.version 同步 (状态自洽)
        draft.version = image_version  # Bug #1 同步
        from src.kid_app import badge_draft as _bd
        _bd.save_draft(draft)
        badge_draft.mark_draft_status(req.draft_id, "committed", by="dizical",
                                    extra={"event": "user_confirmed", "badge_id": badge_id})

        # 4. 清理临时图 (image_version, 不是 draft.version)
        badge_draft.cleanup_tmp(req.draft_id, image_version)
    except Exception as e:
        logger.exception("commit_from_draft failed for %s", req.draft_id)
        return JSONResponse({"ok": False, "error": f"commit 失败: {e}"}, status_code=500)

    return JSONResponse({
        "ok": True,
        "badge_id": badge_id,
        "image_url": f"/static/badges/{badge_id}_v{image_version}.png",
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


# ─── DELETE /config/api/badge/draft/{draft_id} (V2.1 阶段 2.2 放弃按钮) ─

@router.delete("/api/badge/draft/{draft_id}")
def api_delete_draft(draft_id: str) -> JSONResponse:
    """V2.1: 删 draft (idempotent). 待确认列表的"删除"按钮用.

    同时清理 .tmp/ 临时图 (V2 skill 写图可能留在那里).
    """
    from src.kid_app import badge_draft

    draft = badge_draft.get_draft(draft_id)
    if draft is None:
        return JSONResponse({"ok": True, "deleted": False, "note": "draft 不存在 (idempotent)"})

    try:
        badge_draft.cleanup_tmp(draft_id, draft.version)
    except Exception:
        pass  # tmp 清理失败不阻塞主流程

    deleted = badge_draft.delete_draft(draft_id)
    return JSONResponse({"ok": True, "deleted": deleted})


# ─── POST /config/api/badge/ai-draft (V2.1 STEP 1 AI 草拟) ─────

class AIDraftRequest(BaseModel):
    """V2.1 STEP 1 表单的 "AI 草拟 placeholder" 按钮请求."""
    name: str = Field(..., min_length=1)
    zh_story: str = Field(..., min_length=1)


@router.post("/api/badge/ai-draft")
def api_ai_draft(req: AIDraftRequest) -> JSONResponse:
    """V2.1: 调 hermes sub-agent 草拟 placeholder 英文描述.

    实际委托给 src.kid_app.badge_ai_placeholder.draft_placeholder (已存在, V1 就有).
    不阻塞前端: 失败返默认 placeholder 让用户手动改.
    """
    from src.kid_app.badge_ai_placeholder import draft_placeholder, is_configured

    if not is_configured():
        return JSONResponse({
            "ok": False,
            "error": "AI placeholder 草拟未配置 (检查 ~/.hermes/profiles/dizical/)",
            "placeholder": "",
        }, status_code=503)

    try:
        result = draft_placeholder(zh_story=req.zh_story, badge_name=req.name)
    except Exception as e:
        logger.exception("ai-draft failed for %s", req.name)
        return JSONResponse({
            "ok": False,
            "error": f"AI 草拟失败: {e}",
            "placeholder": "",
        }, status_code=500)

    return JSONResponse({"ok": True, "placeholder": result})


# ─── POST /config/api/badge/ai-cond (V2.2 条件文案 AI 生成) ─────

@router.post("/api/badge/ai-cond")
def api_ai_cond(req: AICondRequest) -> JSONResponse:
    """V2.2: 调 LLM 生成一句话"达成条件"文案, 给表单 v21CondText 字段填.

    复用 src.kid_app.subject_info._gemini_stream (流式 Gemini 2.5 Flash-Lite).

    失败兜底: LLM 没返 / 网络断 → 返 fallback 文本, ok=True 让前端有内容可填.
    """
    from src.kid_app.subject_info import _gemini_stream

    # prompt: 简洁, 给出 badge 名 + 类型 + 描述 + 典故, 让 LLM 有 context
    prompt = (
        f"你是 dizical 竹笛成就系统的文案助手. "
        f"用户在做一枚新徽章, 需要一句话 '达成条件' 文案 (弹窗里给孩子看, 解释为什么能获得这个徽章).\n\n"
        f"Badge 名称: {req.name}\n"
        f"类型: {req.type or '未指定'}\n"
        f"英文描述 (给 AI 生图用): {req.placeholder}\n"
        f"中文典故: {req.zh_story}\n\n"
        f"要求:\n"
        f"1. 一句话, ≤30 字\n"
        f"2. 解释孩子为什么能获得这个徽章 (e.g. '练习任意 1 天里包含批改关键词')\n"
        f"3. 不用 emoji, 不用引号\n"
        f"4. 不用 markdown\n"
        f"只返文案本身, 不要解释."
    )

    fallback = "AI 暂时没灵感, 请手动编辑"
    chunks: list[str] = []
    try:
        for token in _gemini_stream(prompt):
            chunks.append(token)
    except Exception as e:
        logger.exception("ai-cond LLM stream failed for %s", req.name)
        return JSONResponse({
            "ok": True,
            "cond_text": fallback,
            "fallback_reason": str(e),
        })

    cond_text = "".join(chunks).strip()
    if not cond_text:
        # LLM 返空 → 兜底, 不报错 (跟 generate_mood_stream 设计一致)
        # 注: V2.2.1 后端 cond_text 必填, fallback 文本用户必改
        return JSONResponse({"ok": True, "cond_text": fallback, "fallback": True})

    # 去掉引号包裹 (LLM 偶尔返 '"...') 
    cond_text = cond_text.strip('"\'`')

    return JSONResponse({"ok": True, "cond_text": cond_text})
