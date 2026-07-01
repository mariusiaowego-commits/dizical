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

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["badge-workflow"])


# ─── Pydantic models (替代手写 json.loads) ───────────────────────────

class DraftRequest(BaseModel):
    """STEP 1 收 meta."""
    meta: dict[str, Any]
    image_path: str | None = None  # 用户已有图片时, 本地文件路径


class CommitFromDraftRequest(BaseModel):
    """STEP 3 收 draft_id."""
    draft_id: str = Field(..., min_length=1)


class ReplaceImageFromDraftRequest(BaseModel):
    """2026-07-01 feat/badges-streak-image-regen: 替换已有 badge 的图.

    跟 commit-from-draft 区别: 这条**不写 achievements/stats 表**, 只换
    achievement_badges.url + version (走 update_badge_current).

    场景: V1 老图错了 (e.g. streak_7 显示 14), 重生图后用本端点换.
    """
    draft_id: str = Field(..., min_length=1)
    badge_id: str = Field(..., min_length=1, pattern=r"^[a-zA-Z0-9_]+$")


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
    """STEP 1: 收 meta, 写 lib/badge_data/{draft_id}.json, 返 draft_id + json.

    新增 image_path 可选字段: 用户已有图片时传本地路径, 后端复制到 .tmp/,
    直接跳到 draft_awaiting_confirm (跳过 STEP 2 生图).
    """
    from src.kid_app import badge_draft

    if not req.meta:
        return JSONResponse({"ok": False, "error": "缺 meta 字段"}, status_code=400)

    try:
        draft = badge_draft.create_draft(req.meta)

        # 新增: 用户已有图片 → 复制到 .tmp/, 直接进 draft_awaiting_confirm
        if req.image_path:
            version = 1
            badge_draft.copy_external_image(req.image_path, draft.draft_id, version)
            draft.image = {
                "path": str(badge_draft.tmp_path_for(draft.draft_id, version)),
                "source": "user_import",
                "version": version,
            }
            draft.status = "draft_awaiting_confirm"

        badge_draft.save_draft(draft)
    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

    import json
    result = {
        "ok": True,
        "draft_id": draft.draft_id,
        "json": json.dumps(draft.to_dict(), ensure_ascii=False, indent=2),
    }
    # 有图片时提示可直接跳到待确认
    if req.image_path:
        result["image_imported"] = True
        result["hint"] = "图片已导入, 可直接切到'待确认' tab 确认上线"
    return JSONResponse(result)


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


# ─── POST /config/api/badge/replace-image-from-draft (V2.1 替换老图) ──

@router.post("/api/badge/replace-image-from-draft")
def api_replace_image_from_draft(req: ReplaceImageFromDraftRequest) -> JSONResponse:
    """2026-07-01 feat/badges-streak-image-regen: 替换已有 badge 的图, 不写 achievements 表.

    流程:
    1. 收 draft_id + badge_id
    2. 校验 draft.status == draft_awaiting_confirm 且 draft.image 存在
    3. 校验 badge_id 已存在 (achievement_badges 表, 不管 is_current)
    4. 拿 image.version (跟 commit-from-draft 一样的 Bug #1 修法)
    5. 复制 tmp 图到 static/badges/{badge_id}_v{new_version}.png
    6. 调 badge_db.update_badge_current(badge_id, new_url, new_version)
       (UPDATE 老行 is_current=0 + INSERT 新行 is_current=1, 走事务)
    7. 标 draft.status=committed, 清理 .tmp/

    跟 commit-from-draft 区别:
    - commit 走 insert_achievement_row + insert_badge_row (INSERT 新表行)
    - replace 走 update_badge_current (UPDATE is_current + INSERT 新行)
    """
    from src.kid_app import badge_draft, badge_db

    draft = badge_draft.get_draft(req.draft_id)
    if draft is None:
        return JSONResponse({"ok": False, "error": f"draft '{req.draft_id}' 不存在"}, status_code=404)

    if draft.status != "draft_awaiting_confirm":
        return JSONResponse({
            "ok": False,
            "error": f"draft 状态 '{draft.status}' 不允许 replace (必须是 draft_awaiting_confirm)",
        }, status_code=400)

    if draft.image is None:
        return JSONResponse({"ok": False, "error": "draft 还没 image 字段"}, status_code=400)

    if not badge_db.badge_exists(req.badge_id):
        return JSONResponse({
            "ok": False,
            "error": f"badge_id='{req.badge_id}' 不在 DB, 请走 commit-from-draft (V2.x 仅替换已有图)"
        }, status_code=404)

    try:
        # Bug #1 同步: 拿 image.version (跟 commit 同源修法)
        image_version = draft.image.get("version", draft.version)

        # 1. 复制 tmp 图到 static/badges/{badge_id}_v{image_version}.png
        static_path = badge_draft.move_tmp_to_static(req.draft_id, image_version)

        # 2. 换 badge 行 (UPDATE 老 is_current=0 + INSERT 新 is_current=1)
        new_url = f"/static/badges/{req.badge_id}_v{image_version}.png"
        badge_db.update_badge_current(
            badge_id=req.badge_id,
            new_url=new_url,
            new_version=image_version,
        )

        # 3. 标 draft status = committed
        draft.version = image_version  # 跟 commit 一致
        from src.kid_app import badge_draft as _bd
        _bd.save_draft(draft)
        badge_draft.mark_draft_status(req.draft_id, "committed", by="dizical",
                                    extra={"event": "image_replaced", "badge_id": req.badge_id})

        # 4. 清理临时图
        badge_draft.cleanup_tmp(req.draft_id, image_version)
    except Exception as e:
        logger.exception("replace_image_from_draft failed for %s", req.draft_id)
        return JSONResponse({"ok": False, "error": f"replace 失败: {e}"}, status_code=500)

    logger.info("replace image: badge_id=%s → %s (draft=%s)", req.badge_id, new_url, req.draft_id)
    return JSONResponse({
        "ok": True,
        "badge_id": req.badge_id,
        "image_url": new_url,
        "version": image_version,
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


# ─── GET /config/api/badge/draft-image (V2.6 待确认列表预览图) ─────

@router.get("/api/badge/draft-image")
def api_draft_image(draft_id: str) -> Response:
    r"""V2.6: 待确认 badge 列表的预览图, 从 .tmp/ 临时图读取.

    根因 (2026-06-30): discovery 之前返 /static/badges/{id}_v{n}.png,
    但 commit 前的草稿图实际在 .tmp/ (生图 skill 写盘位置),
    不在 static mount 下, 前端 fetch 永远 404 → "图加载失败".

    修法: 加这个端点走 FileResponse 返真图. discovery 优先返
    commit 后的 static/badges/ 路径 (commit 后 image.path 被
    commit-from-draft 改成 static 路径), fallback 到这个端点.

    安全:
    - draft_id 走 SAFE_ID_RE (^[a-zA-Z0-9_-]+$) → 杜绝 path traversal
      注: DRAFT_ID_RE 跟实际草稿 ID 格式不匹配 (DRAFT_ID_RE 要求
      6+ 位 hash, 但草稿用顺序 ID 或短 hash), 所以这里不复用
    - 真实路径必须 resolve 后仍在 _badge_data_dir() 内
      → 即使 image.path 字段被恶意改, 也读不到项目外文件
    - 仅返 image/png (Content-Type)
    """
    import re as _re
    from pathlib import Path as _P
    from src.kid_app import badge_draft

    # path traversal 防御: 字符白名单
    if not _re.match(r"^[a-zA-Z0-9_-]+$", draft_id) or ".." in draft_id:
        return JSONResponse({"ok": False, "error": "draft_id 非法"}, status_code=400)

    # 直接读 json, 不走 get_draft (它有 DRAFT_ID_RE 校验跟实际格式不一致)
    draft_path = badge_draft._badge_data_dir() / f"{draft_id}.json"
    if not draft_path.is_file():
        return JSONResponse({"ok": False, "error": "draft 不存在"}, status_code=404)

    try:
        import json as _json
        draft_data = _json.loads(draft_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return JSONResponse({"ok": False, "error": f"draft 解析失败: {e}"}, status_code=400)

    img_path_str = (draft_data.get("image") or {}).get("path")
    if not img_path_str:
        return JSONResponse({"ok": False, "error": "draft 还没 image 字段"}, status_code=404)

    # path traversal 防御: resolve 后必须仍在 badge_data_dir 内
    try:
        img_path = _P(img_path_str).resolve()
        data_dir = badge_draft._badge_data_dir().resolve()
    except (OSError, RuntimeError):
        return JSONResponse({"ok": False, "error": "image.path 无效"}, status_code=400)

    # 必须在 data_dir 子目录 (.tmp/ 或根目录)
    try:
        img_path.relative_to(data_dir)
    except ValueError:
        return JSONResponse(
            {"ok": False, "error": "image.path 越界 (不在 badge_data_dir 内)"},
            status_code=400,
        )

    if not img_path.is_file():
        return JSONResponse({"ok": False, "error": f"图不存在: {img_path}"}, status_code=404)

    return FileResponse(
        path=str(img_path),
        media_type="image/png",
        headers={"Cache-Control": "no-cache"},  # 草稿图会换, 不缓存
    )


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
