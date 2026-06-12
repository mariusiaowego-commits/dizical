"""
Badge 制作工作流 FastAPI 路由 (config 子路由).

设计 (用户 2026-06-12 拍板):
- 所有路径前缀 /config/badge* (跟现有 config-blindbox / config-praise 一致)
- SSE 流式返回状态 (复用 routes/config.py:955 月报框架的 StreamingResponse 模式)
- PIN 验证 (跟 config-blindbox 一致: localStorage + 入口检查 + 写操作时 verify)
- 跟其他 routes 模块同模式: 函数内延迟 import app.render (避免循环 import)

端点:
  GET  /config/badge               - 分步表单 HTML 页面
  GET  /config/api/badge/check-id  - 实时查重
  POST /config/api/badge/ai-draft  - AI 草拟 placeholder (调 hermes)
  POST /config/api/badge/preview   - SSE 流式: 跑 6 步流水线 (不写 DB)
  POST /config/api/badge/commit    - 写三表 (PIN 验证)
  GET  /config/api/badge/calc-snippet - 返回 calc logic 代码模板
  GET  /config/api/portal/status   - Nous Portal 状态 (dad_pin 验证后给全字段)
  POST /config/api/portal/refresh  - 强制刷新 portal cache

PR-C 端点 (批量模式) 在 routes/badge_batch.py 单独放

依赖:
- src.kid_app.badge_generator
- src.kid_app.badge_ai_placeholder
- src.kid_app.badge_portal
- src.kid_app.badge_db
- 路径: src/kid_app/routes/badge_workflow.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import queue
import re
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from src.kid_app import badge_ai_placeholder, badge_db, badge_generator, badge_portal
from src.kid_app.badge_prompts import build_unlocked_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["badge-workflow"])

# calc logic 模板 (跟 achievement_definitions.py:170-330 段对齐)
_CALC_TEMPLATES: dict[str, str] = {
    "milestone_streak": """# 贴到 src/achievement_definitions.py 的 _calc_milestone():
if aid == "{badge_id}":
    return CalcResult(
        achieved=streak >= {threshold},
        computed_value=streak,
        extra=None,
        achieved_at=achieved_at if streak >= {threshold} else None,
        "连续 ≥ {threshold} 天",
    )""",
    "milestone_total": """# 贴到 _calc_milestone():
if aid == "{badge_id}":
    return CalcResult(
        achieved=total_mins >= {threshold},
        computed_value=total_mins,
        extra=None,
        achieved_at=achieved_at if total_mins >= {threshold} else None,
        "累计 ≥ {threshold} 分钟",
    )""",
    "milestone_top": """# 贴到 _calc_milestone() (top1/top2/top3 共用, rank 从 id 末位取):
if aid == "{badge_id}":
    rank = int(aid[-1])
    ok = len(top_items) >= rank
    val = top_items[rank - 1][1] if ok else 0
    item_name = top_items[rank - 1][0] if ok else ""
    return CalcResult(
        ok, val, item_name,
        achieved_at if ok else None,
        f"累计时长第 {{rank}}: {{item_name}}({{val}}分钟)",
    )""",
    "milestone_grade": """# 贴到 _calc_milestone() (考级 grade_N):
if aid == "{badge_id}":
    g = int(aid.split("_")[1])
    row = stats.get(aid)
    if row:
        return CalcResult(
            row["achieved"] == "Y", g, None,
            row.get("achieved_at"),
            f"考取 {{g}} 级",
        )
    return CalcResult(False, 0, None, None, f"考取 {{g}} 级")""",
    "milestone_first_log": """# 贴到 _calc_milestone() (first_log):
if aid == "{badge_id}":
    return CalcResult(
        total_mins > 0, total_mins, None,
        achieved_at if total_mins > 0 else None,
        "完成第一次练习",
    )""",
    "seasonal_daily": """# 贴到 _calc_seasonal() (daily_checkin_N 每日打卡):
# 已经有现成实现, 你的 badge 复用 daily 类型即可, 不需要新代码""",
    "seasonal_monthly_lucky": """# 贴到 _calc_seasonal() (lucky_61_YYYY 节日徽章, 已有现成实现):
# aid 自动按 lucky_61_YYYY 模式解析年份, 不需要新代码""",
    "seasonal_stage_early": """# 贴到 _calc_seasonal() (early_riser / little_chick_commander / first_to_act):
# 已有现成实现, threshold_map 已包含 12/17/20, 不需要新代码""",
    "skip": "# 暂不绑定 calc logic. 上线后新 badge 在 /badges 显示但进度为 0",
}


# ─── 页面 ──────────────────────────────────────────────────────────

@router.get("/badge", response_class=HTMLResponse)
def config_badge():
    """分步表单 HTML 页面. PIN 验证由前端 localStorage 控制."""
    from src.kid_app.app import render
    from src.database import db
    pin_locked = "true" if db.get_setting("dad_pin") else "false"
    # render() returns HTMLResponse (str subclass), fastapi accepts it
    return render("config-badge", active_nav="portal", pin_locked=pin_locked)  # type: ignore[return-value]


# ─── API: 实时查重 ──────────────────────────────────────────────

@router.get("/api/badge/check-id")
def api_check_id(id: str) -> JSONResponse:
    """id 实时查重. 前端 Step 1 输入时调."""
    valid_id = bool(id) and bool(re.match(r"^[a-zA-Z0-9_]+$", id))
    if not valid_id:
        return JSONResponse({"ok": False, "unique": False, "error": "id 必须只含英文/数字/下划线"})
    return JSONResponse({"ok": True, "unique": badge_db.check_id_unique(id)})


# ─── API: AI 草拟 placeholder ───────────────────────────────────

@router.post("/api/badge/ai-draft")
async def api_ai_draft(request: Request) -> JSONResponse:
    """调 dizical hermes profile 生成英文 placeholder.

    Body: { story: str, name: str }
    """
    try:
        body = json.loads(await request.body())
    except json.JSONDecodeError:
        return JSONResponse({"ok": False, "error": "body 不是 JSON"}, status_code=400)

    zh_story = body.get("story", "").strip()
    badge_name = body.get("name", "").strip()

    try:
        placeholder = badge_ai_placeholder.draft_placeholder(zh_story, badge_name)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except RuntimeError as e:
        # hermes 失败, 透传错误 (含 profile not found 等)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)

    return JSONResponse({"ok": True, "placeholder": placeholder})


# ─── API: 预览 (SSE) ─────────────────────────────────────────────

@router.post("/api/badge/preview")
async def api_preview(request: Request) -> StreamingResponse:
    """SSE 流式: 跑 6 步流水线, 实时推 status, 完成后返回 image_path.

    Body: { id: str, placeholder: str, regenerate: bool = False }
    """
    try:
        body = json.loads(await request.body())
    except json.JSONDecodeError:
        # 改用纯文本 SSE 推 error
        async def err_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'body 不是 JSON'})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    badge_id = body.get("id", "").strip()
    placeholder = body.get("placeholder", "").strip()
    regenerate = body.get("regenerate", False)

    result_queue: queue.Queue = queue.Queue()

    def run() -> None:
        def on_status(stage: str, msg: str) -> None:
            result_queue.put(("status", stage, msg))

        result = badge_generator.run_badge_pipeline(
            badge_id=badge_id,
            placeholder=placeholder,
            on_status=on_status,
            regenerate=regenerate,
        )
        result_queue.put(("done", result))

    async def event_stream():
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        # 200s 超时 (FAL 30-60s + 缓冲 + 回滚)
        while True:
            try:
                item = await asyncio.to_thread(result_queue.get, timeout=200)
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': '生成超时 (200s)'})}\n\n"
                break

            if item[0] == "status":
                _, stage, msg = item
                yield f"data: {json.dumps({'type': 'status', 'stage': stage, 'message': msg}, ensure_ascii=False)}\n\n"
            elif item[0] == "done":
                _, result = item
                yield f"data: {json.dumps({'type': 'done', 'data': result}, ensure_ascii=False)}\n\n"
                break
        # 显式 None 给 async generator
        return
        yield  # unreachable, 满足 type checker

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── API: 写三表 (commit) ──────────────────────────────────────

@router.post("/api/badge/commit")
async def api_commit(request: Request) -> JSONResponse:
    """写 achievements + achievement_stats + achievement_badges 三表.

    Body: { ..., pin: str }
    PIN 验证: 跟 config-blindbox 一致.
    """
    from src.database import db

    try:
        body = json.loads(await request.body())
    except json.JSONDecodeError:
        return JSONResponse({"ok": False, "error": "body 不是 JSON"}, status_code=400)

    # ── PIN 验证 ──
    pin = body.get("pin", "")
    stored_pin = db.get_setting("dad_pin")
    if stored_pin and pin != stored_pin:
        return JSONResponse({"ok": False, "error": "PIN 不对"}, status_code=401)

    badge_id = body.get("id", "").strip()
    image_path = body.get("imagePath", "").strip()
    if not badge_id or not image_path:
        return JSONResponse({"ok": False, "error": "id 和 imagePath 必填"}, status_code=400)

    # ── 校验 category/seasonal_type ──
    category = body.get("category", "milestone")
    if category not in ("milestone", "seasonal"):
        return JSONResponse({"ok": False, "error": f"非法 category: {category}"}, status_code=400)
    seasonal_type = body.get("seasonalType", "monthly")
    if category == "seasonal" and seasonal_type not in ("daily", "weekly", "monthly", "stage"):
        return JSONResponse({"ok": False, "error": f"非法 seasonal_type: {seasonal_type}"}, status_code=400)

    try:
        placeholder = body.get("placeholder", "").strip()
        badge_generator.commit_badge_to_db(
            badge_id=badge_id,
            name=body.get("name", ""),
            type_label=body.get("type", "突破"),
            category=category,
            stat_logic=body.get("statLogic", ""),
            description=body.get("description", ""),
            display_format=body.get("displayFormat", "days"),
            threshold=body.get("threshold"),
            placeholder=placeholder,
            unlocked_template=build_unlocked_prompt(placeholder) if placeholder else "",
            seasonal_type=seasonal_type,
            image_path=image_path,
        )
    except Exception as e:
        # 失败: 删图片 + 错误透传
        try:
            Path(image_path).unlink(missing_ok=True)
            logger.warning(f"commit 失败, 已删图: {image_path}")
        except Exception:
            pass
        return JSONResponse({"ok": False, "error": f"写库失败: {e}"}, status_code=500)

    return JSONResponse({
        "ok": True,
        "badge_id": badge_id,
        "warning": None,  # 去背失败信息已在 preview 阶段展示过
        "calc_snippet": _render_calc_snippet(
            body.get("calcTemplate", "skip"), badge_id, body.get("threshold", 0)
        ),
    })


def _render_calc_snippet(template: str, badge_id: str, threshold: int) -> str:
    """渲染 calc logic 代码模板."""
    tpl = _CALC_TEMPLATES.get(template, _CALC_TEMPLATES["skip"])
    return tpl.format(badge_id=badge_id, threshold=threshold)


# ─── API: calc logic 代码片段 ──────────────────────────────────

@router.get("/api/badge/calc-snippet")
def api_calc_snippet(template: str, badge_id: str, threshold: int = 0) -> JSONResponse:
    """返回 calc logic 代码片段 (前端 Step 3 / 上线成功页用)."""
    return JSONResponse({
        "ok": True,
        "code": _render_calc_snippet(template, badge_id, threshold),
    })


# ─── API: Nous Portal 状态 (用户 2026-06-12 拍板, V1 必须) ───

@router.get("/api/portal/status")
def api_portal_status(request: Request) -> JSONResponse:
    """Nous Portal + Tool Gateway 状态.

    dad_pin 验证后给全部字段 (用户 2026-06-12 拍板 Q5).
    无 PIN 验证的访客只能拿到 ok_for_badge boolean.
    """
    from src.database import db

    # 检查 dad_pin 是否已设 (已设 → 必须 verify)
    stored_pin = db.get_setting("dad_pin")
    pin_verified = False
    if not stored_pin:
        pin_verified = True  # 未设 PIN, 公开访问
    else:
        # 从 query string 或 header 拿 PIN
        pin = request.query_params.get("pin", "")
        if pin == stored_pin:
            pin_verified = True

    status = badge_portal.check_portal_status()

    if pin_verified:
        return JSONResponse({
            "ok": True,
            "data": {
                "auth": status.auth,
                "image_generation": status.image_generation,
                "model": status.model,
                "provider": status.provider,
                "ok_for_badge": status.ok_for_badge,
                "error": status.error,
                "latency_ms": status.latency_ms,
                "checked_at": status.checked_at,
                "raw_output": status.raw_output[:1000] if status.raw_output else "",
            },
        })
    else:
        # 未 verify, 只给 boolean
        return JSONResponse({
            "ok": True,
            "data": {
                "ok_for_badge": status.ok_for_badge,
                "error": status.error,
                "checked_at": status.checked_at,
            },
        })


@router.post("/api/portal/refresh")
def api_portal_refresh() -> JSONResponse:
    """强制刷新 portal cache (用户点 '刷新状态' 按钮时调)."""
    badge_portal.invalidate_cache()
    status = badge_portal.check_portal_status(use_cache=False)
    return JSONResponse({
        "ok": True,
        "data": {
            "auth": status.auth,
            "image_generation": status.image_generation,
            "model": status.model,
            "ok_for_badge": status.ok_for_badge,
            "error": status.error,
            "latency_ms": status.latency_ms,
            "checked_at": status.checked_at,
        },
    })


@router.get("/api/portal/profiles")
def api_portal_profiles() -> JSONResponse:
    """查 hermes CLI 默认 + dizical profile 2 个 portal 状态 (V1.1 改进, 用户 2026-06-12 OUT-OF-BAND).

    前端 Portal 卡 status-red 时调, 显示 2 个 profile 的 Auth + Image Generation 灯,
    帮用户定位哪个 profile 没连 portal.

    按用户拍板 "只查 hermes portal status 和 dizical portal status" — 11 个 KNOWN_PROFILES 太冗余.
    不缓存 (用户手动刷新, 2 个并发 ~700ms).
    """
    profiles = badge_portal.check_two_profiles_portal()
    return JSONResponse({"ok": True, "data": profiles})
