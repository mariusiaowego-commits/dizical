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

from fastapi import APIRouter, File, Request, Response, UploadFile
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

    # V2.7 (sprint 26090902): 落盘校验 — 防"UI 显示成功但后端没写盘"
    # dad 9-9 实踩: 前端显示草稿已创建, hermes /badge-image 查 draft_id 404
    verify = badge_draft.get_draft(draft.draft_id)
    if verify is None:
        return JSONResponse(
            {"ok": False, "error": f"草稿落盘失败: {draft.draft_id}.json 未写入, 请重试"},
            status_code=500,
        )

    import json
    result = {
        "ok": True,
        "draft_id": draft.draft_id,
        "json": json.dumps(draft.to_dict(), ensure_ascii=False, indent=2),
        "file_contract_path": str(badge_draft._badge_data_dir() / f"{draft.draft_id}.json"),
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

    P0 (sprint-26101302, 2026-10-13): 支持 COS 源 —— 本地 json 没有时从 COS 读 (生产容器
    重建后草稿仍在 COS); 老草稿 (有 image.path 无 image.url) 在这里**惰性补 url**。
    读侧本轮只做这一条路径, 其余读点 (list/discovery/draft-image/commit 侧) 归 P1。

    Returns:
        {ok: True, draft: dict, source: "local"|"cos", storage_mode: "local"|"cos"} or {ok: False, error}
    """
    from src.kid_app import badge_draft

    try:
        draft, source = badge_draft.get_draft_with_source(draft_id)
    except Exception as e:  # COS 可用但读失败 → 502, 不许假装"不存在"
        logger.exception("read draft failed: %s", draft_id)
        return JSONResponse(
            {"ok": False, "error": f"读草稿失败 (存储不可用?): {e}"}, status_code=502,
        )

    if draft is None:
        return JSONResponse({"ok": False, "error": f"draft '{draft_id}' 不存在"}, status_code=404)

    backfilled = None
    try:
        backfilled = badge_draft.backfill_image_url(draft)   # 唯一允许的读侧写副作用
    except Exception as e:  # 补 url 失败不阻塞读草稿 (草稿内容仍可用, 只是图还没远端化)
        logger.warning("backfill image.url failed for %s: %r", draft_id, e)

    result = {
        "ok": True,
        "draft": draft.to_dict(),
        "source": source,
        "storage_mode": badge_draft.storage_mode(),
    }
    if backfilled:
        result["image_url_backfilled"] = backfilled
    return JSONResponse(result)


# ─── POST /config/api/badge/draft/{draft_id}/image (P0 回传端点) ─────

# 成品图规格 = badge 管线出图口径 (1024×1024 RGBA PNG)
DRAFT_IMAGE_SIZE = (1024, 1024)
DRAFT_IMAGE_MAX_BYTES = 8 * 1024 * 1024

# ─── 回传端点鉴权 (P0b audit, 2026-10-13) ────────────────────────────
# audit 发现: /config/api/ 在 app.py 的 _auth_guard_middleware 里是**公开白名单**,
# 本端点不带任何凭据也能调 (匿名可写盘 + 触发 COS 计费面)。这里改成显式**默认拒绝**。
# 为什么不直接把它从白名单剔除: 中间件那条 401 分支只认 web session cookie, 表达不了
# "机器 token"通道 —— 剔出白名单会把合法机器推送一起挡掉, 且会波及同前缀的其它 /config/api
# 端点 (前置/顺序风险)。所以选择"白名单 + 端点内自查", 鉴权是本端点的第一条语句。
BADGE_PUSH_TOKEN_HEADER = "X-Badge-Push-Token"
BADGE_PUSH_TOKEN_ENV = "BADGE_PUSH_TOKEN"


def _push_token_ok(request: Request) -> bool:
    """机器通道: 请求头 X-Badge-Push-Token == env BADGE_PUSH_TOKEN.

    env 未设 (或空) = 该通道关闭 (不给默认 token)。常数时间比较, 不引新依赖 (hmac 是 stdlib)。
    """
    import hmac
    import os

    expected = (os.getenv(BADGE_PUSH_TOKEN_ENV) or "").strip()
    if not expected:
        return False
    supplied = (request.headers.get(BADGE_PUSH_TOKEN_HEADER) or "").strip()
    return bool(supplied) and hmac.compare_digest(supplied, expected)


async def _badge_push_authorized(request: Request) -> bool:
    """两条通道任一通过即可:

      ① 机器: X-Badge-Push-Token == env BADGE_PUSH_TOKEN
      ② 人/浏览器: /config 现有的 dad 守门 —— 直接复用 routes/config_users._check_dad_or_401
         (X-Dad-Pin header、dad 角色 web 会话、dizical_pin_ok cookie 三轨), 不另造一套。
         multipart 请求读不出 body 里的 pin, 该轨自然只走 header/cookie (helper 内部已 try/except)。
    """
    if _push_token_ok(request):
        return True

    from src.kid_app.routes.config_users import _check_dad_or_401

    return (await _check_dad_or_401(request)) is None


@router.post("/api/badge/draft/{draft_id}/image")
async def api_upload_draft_image(
    request: Request, draft_id: str, file: UploadFile = File(...)
) -> JSONResponse:
    """P0 (sprint-26101302): 异机把成品图**推回**服务, 不用碰服务所在机器的盘。

    鉴权 (P0b): 默认拒绝, 见 _badge_push_authorized (机器 token / dad 守门); 未过 → 401。

    之前只有 image_path (服务端本地绝对路径) ⇒ 异机根本推不进来 (2026-10-13 只能人工搬文件)。
    本端点收 multipart PNG:
      1. draft 必须存在, status ∈ {draft_created, draft_awaiting_confirm}
      2. 图必须是 1024×1024 RGBA (尺寸/模式硬校验; alpha 门禁读数仍由客户端 skill 负责)
      3. 落 .tmp/{draft_id}_v{n}.png (与 skill 生图同一路径约定 → commit/预览不用改)
      4. COS 可用则同时上传 badges/{badge_id}_v{n}.png 并写 image.url
      5. 走 update_draft_image 推进 status=draft_awaiting_confirm (状态机 + history 留痕)
    """
    import hashlib
    import io

    from src.kid_app import badge_draft
    from src.kid_app.cos_client import cos_uploader

    # 0. 鉴权 (默认拒绝, 第一条语句): 未授权不许触发任何写盘/COS 动作
    if not await _badge_push_authorized(request):
        logger.warning(
            "draft image push denied: draft=%s client=%s token_header=%s",
            draft_id, getattr(request.client, "host", "?"),
            bool(request.headers.get(BADGE_PUSH_TOKEN_HEADER)),
        )
        return JSONResponse(
            {"ok": False,
             "error": "未授权: 需要 dad 凭据 (X-Dad-Pin / dad 会话 / pin_ok cookie) 或 X-Badge-Push-Token"},
            status_code=401,
        )

    if not badge_draft.SAFE_DRAFT_ID_RE.match(draft_id or ""):
        return JSONResponse({"ok": False, "error": "draft_id 非法"}, status_code=400)

    draft = badge_draft.get_draft(draft_id)
    if draft is None:
        return JSONResponse({"ok": False, "error": f"draft '{draft_id}' 不存在"}, status_code=404)

    if draft.status not in ("draft_created", "draft_awaiting_confirm"):
        return JSONResponse({
            "ok": False,
            "error": f"draft.status='{draft.status}' 不允许换图 (必须 draft_created / draft_awaiting_confirm)",
        }, status_code=409)

    raw = await file.read()
    if not raw:
        return JSONResponse({"ok": False, "error": "空文件"}, status_code=400)
    if len(raw) > DRAFT_IMAGE_MAX_BYTES:
        return JSONResponse(
            {"ok": False, "error": f"文件过大: {len(raw)}B > {DRAFT_IMAGE_MAX_BYTES}B"},
            status_code=413,
        )

    try:
        from PIL import Image as _PILImage
        with _PILImage.open(io.BytesIO(raw)) as im:
            got_size, got_mode, got_fmt = im.size, im.mode, (im.format or "")
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": f"不是可解析的图片: {e}"}, status_code=400)

    if got_size != DRAFT_IMAGE_SIZE or got_mode != "RGBA":
        return JSONResponse({
            "ok": False,
            "error": (f"图规格不对: 需要 {DRAFT_IMAGE_SIZE[0]}×{DRAFT_IMAGE_SIZE[1]} RGBA, "
                      f"收到 {got_size[0]}×{got_size[1]} {got_mode} ({got_fmt})"),
        }, status_code=400)

    badge_id = draft.meta.get("id")
    if not badge_id:
        return JSONResponse({"ok": False, "error": "draft.meta 缺 id"}, status_code=400)

    # 版本沿用草稿当前 image.version (缺省 1) —— 重推同版本 = 覆盖, 与 skill 的 v1 约定一致
    version = int((draft.image or {}).get("version", 1) or 1) if isinstance(draft.image, dict) else 1
    sha256 = hashlib.sha256(raw).hexdigest()

    try:
        tmp = badge_draft.write_tmp_image(draft_id, version, raw)
        storage = badge_draft.storage_mode()
        image_url = None
        if storage == "cos":
            key = f"{badge_draft.COS_PREFIX_BADGE}{badge_id}_v{version}.png"
            image_url = cos_uploader.upload(key, raw, content_type="image/png")
        image_info = {
            "path": str(tmp),
            "url": image_url,          # None = 只有本地 (COS 不可用), commit 时会再试
            "source": "api_upload",
            "version": version,
            "bytes": len(raw),
            "sha256": sha256,
            # 服务端只校验尺寸/模式: alpha 门禁读数由客户端 skill 产出 → 不冒充"已验"
            "alpha_verified": False,
        }
        badge_draft.update_draft_image(draft_id, image_info, by="api")
        updated = badge_draft.get_draft(draft_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("upload draft image failed: %s", draft_id)
        return JSONResponse({"ok": False, "error": f"写图失败: {e}"}, status_code=500)

    logger.info(
        "draft image uploaded: draft=%s badge=%s v=%d bytes=%d storage=%s url=%s",
        draft_id, badge_id, version, len(raw), storage, image_url,
    )
    return JSONResponse({
        "ok": True,
        "draft_id": draft_id,
        "badge_id": badge_id,
        "status": (updated.status if updated else "draft_awaiting_confirm"),
        "storage": storage,
        "image": image_info,
        "image_url": image_url,
    })


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

        # 1. P0 (sprint-26101302): commit_image_from_draft 返 storage 口径 (cos|static),
        #    响应据此回话 —— 不再固定写"还需要 PR+deploy" (与真实路径不一致会误导操作者)
        _commit = badge_draft.commit_image_from_draft(req.draft_id, image_version)
        badge_image_url = _commit["url"]
        image_storage = _commit["storage"]
        logger.info(
            "badge commit image written: draft=%s version=%d storage=%s url=%s",
            req.draft_id, image_version, image_storage, badge_image_url,
        )

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
                url=badge_image_url,  # V3.0 (sprint 26082401): COS https URL 或 /static/ 路径
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

    # P0 (sprint-26101302, 2026-10-13): 去硬编码 —— 按实际走的存储回话。
    # 旧版固定写 needs=[git add/PR/deploy] 且 image_url 固定拼 /static/..., COS 上传成功时
    # 也在说"要去 deploy" → 误导操作者 (2026-10-13 实测)。
    if image_storage == "cos":
        prod_visibility = {
            "deployed": True,              # 图对象已在 COS 公开读 + 三表已指向它 → prod 立即可见
            "db_written": True,
            "image_on": "cos",
            "image_url": badge_image_url,
            "needs": [],
            "hint": "图在 COS(公开读) 且三表已写 → 生产 kid-app 立即能看到, 不需要 git/PR/deploy。",
        }
    else:
        prod_visibility = {
            "deployed": False,
            "db_written": True,
            "image_on": "local_static_only",
            "image_url": badge_image_url,
            "needs": [
                "git add src/kid_app/static/badges/{stem}.png".format(
                    stem=f"{badge_id}_v{image_version}"),
                "git add src/kid_app/static/badges/thumbs/{stem}.webp".format(
                    stem=f"{badge_id}_v{image_version}"),
                "git add src/kid_app/static/badges/full/{stem}.webp".format(
                    stem=f"{badge_id}_v{image_version}"),
                "git commit + push + PR + merge to main",
                "CloudRun deploy (跟 hermes 说 'deploy badge' 或跑 dizical-cloudrun-deploy 5 步 SOP)",
            ],
            "hint": "本地已生效; 生产 kid-app 还需 git+deploy (约 10-15 分钟). 图片 URL 在 prod 生效前显示占位图.",
        }
    return JSONResponse({
        "ok": True,
        "badge_id": badge_id,
        "image_url": badge_image_url,      # 真实值: COS https URL 或 /static/badges/...
        "image_storage": image_storage,
        "prod_visibility": prod_visibility,
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
    5. 走 commit_image_from_draft (与 commit 同一派生: PNG + thumbs/full webp)
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

        # 1. 与 commit 同一函数: PNG + 两档 webp, 失败抛错 (本 except 返 500, 不换行)
        _commit = badge_draft.commit_image_from_draft(
            req.draft_id, image_version, badge_id=req.badge_id,
        )
        new_url = _commit["url"]

        # 2. 换 badge 行 (UPDATE 老 is_current=0 + INSERT 新 is_current=1)
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


# ─── 卡片外观设计期入口 (sprint 26091301 B2) ────────────────────────
# dad 硬约束: 主题是**设计期配置项** (dad 自己在 config 里改), 不做用户端
# 主题选择器, dizical-minip 不调用这组端点 (见 API-CHANGELOG §2.3).
# PIN: 跟本文件既有 /config/api/badge/* 端点一致 — 不 server-side 校验,
# 由 config 页 localStorage PIN gate 守入口 (见本文件顶部 helpers 注释).
#
# 单点解析不复制: 主题走 badge_theme.resolve_card_theme,
# 星级走 badge_theme.resolve_card_stars (优先级链一个字不改).

_SELECT_APPEARANCE_ROW = (
    "SELECT id, name, type, category, sort_order, card_theme, card_stars "
    "FROM achievements"
)


class CardAppearanceUpdateRequest(BaseModel):
    """卡片外观单行更新 body.

    card_theme / card_stars 用 pydantic model_fields_set 区分三种语义:
    - 字段没传      → 不动该列
    - 传 null / ""  → 清空该列 (回落 type 兜底)
    - 传合法值      → 写该列
    """
    id: str = Field(..., min_length=1)
    card_theme: Any = None
    card_stars: Any = None


def _appearance_row(row: dict) -> dict:
    """DB 行 → API 结构 (原始列值 + 解析值 + theme_source)."""
    from src.kid_app import badge_theme

    raw_theme = row.get("card_theme")
    raw_stars = row.get("card_stars")
    badge_type = row.get("type")
    category = row.get("category")

    # theme_source: db (显式列合法) > type (TYPE_THEME_MAP) > fallback
    if badge_theme._normalize_card_theme(raw_theme) is not None:
        theme_source = badge_theme.THEME_SOURCE_DB
    elif isinstance(badge_type, str) and badge_type.strip() in badge_theme.TYPE_THEME_MAP:
        theme_source = badge_theme.THEME_SOURCE_TYPE
    else:
        theme_source = badge_theme.THEME_SOURCE_FALLBACK

    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "type": badge_type,
        "category": category,
        "sort_order": row.get("sort_order"),
        "card_theme": raw_theme,
        "card_stars": raw_stars,
        "resolved_theme": badge_theme.resolve_card_theme(badge_type, raw_theme, category),
        "resolved_stars": badge_theme.resolve_card_stars(raw_stars, badge_type, category),
        "theme_source": theme_source,
    }


@router.get("/api/badge/card-appearance")
def api_card_appearance_list() -> JSONResponse:
    """列出全部 achievements 的卡片外观 (设计期表格用).

    Returns:
        {ok, count, data: [...], themes: {dark, light, labels}}
    """
    from src import db_adapter
    from src.kid_app import badge_db, badge_theme

    conn, _ = db_adapter.get_conn()
    try:
        # 幂等确保 card_theme / card_stars 列 (双后端)
        badge_db.ensure_card_theme_column(conn)
        badge_db.ensure_card_stars_column(conn)
        rows = db_adapter.execute_dicts(
            conn, _SELECT_APPEARANCE_ROW + " ORDER BY sort_order, id",
        )
    except Exception as e:
        logger.exception("card-appearance list failed")
        return JSONResponse({"ok": False, "error": f"读取失败: {e}"}, status_code=500)
    finally:
        # MySQL 侧是 DBUtils PooledDB 连接: close() = 归还池 (不销毁)。
        # 旧版对 MySQL 跳过 close → 只能靠 GC 兜底, 高并发下耗尽池 (审计 P3-1)。
        try:
            conn.close()
        except Exception:
            pass

    data = [_appearance_row(r) for r in rows]
    return JSONResponse({
        "ok": True,
        "count": len(data),
        "data": data,
        "themes": {
            "dark": list(badge_theme.DARK_CARD_THEMES),
            "light": list(badge_theme.LIGHT_CARD_THEMES),
            "labels": dict(badge_theme.THEME_LABELS),
        },
    })


@router.post("/api/badge/card-appearance")
def api_card_appearance_update(req: CardAppearanceUpdateRequest) -> JSONResponse:
    """更新单张卡的 card_theme / card_stars, 返更新后完整单行结构.

    校验 (严, 不走兜底):
    - card_theme 非空必须在 8 套 (VALID_CARD_THEMES) 内, 否则 400 + 合法清单
    - card_stars 必须 1..5 或 null, 越界 400
    - id 不存在 404
    """
    from src import db_adapter
    from src.kid_app import badge_db, badge_theme

    badge_id = (req.id or "").strip()
    if not badge_id:
        return JSONResponse({"ok": False, "error": "id 必填"}, status_code=400)

    fields = req.model_fields_set
    updates: dict[str, Any] = {}

    if "card_theme" in fields:
        raw_theme = req.card_theme
        if raw_theme is None or (isinstance(raw_theme, str) and not raw_theme.strip()):
            updates["card_theme"] = None  # 清列 → 解析回落 type/category 兜底
        elif isinstance(raw_theme, str) and raw_theme.strip().lower() in badge_theme.VALID_CARD_THEMES:
            updates["card_theme"] = raw_theme.strip().lower()
        else:
            return JSONResponse({
                "ok": False,
                "error": f"card_theme 非法: {raw_theme!r}, 必须是合法主题之一 (或 null/空串清空)",
                "valid_themes": list(badge_theme.VALID_CARD_THEMES),
            }, status_code=400)

    if "card_stars" in fields:
        raw_stars = req.card_stars
        if raw_stars is None or (isinstance(raw_stars, str) and not raw_stars.strip()):
            updates["card_stars"] = None
        else:
            try:
                n = int(str(raw_stars).strip())
            except (TypeError, ValueError):
                return JSONResponse({
                    "ok": False,
                    "error": f"card_stars 非法: {raw_stars!r}, 必须是 1..5 的整数 (或 null/空串清空)",
                    "valid_range": [badge_theme.STARS_MIN, badge_theme.STARS_MAX],
                }, status_code=400)
            if not (badge_theme.STARS_MIN <= n <= badge_theme.STARS_MAX):
                return JSONResponse({
                    "ok": False,
                    "error": f"card_stars 越界: {n}, 必须是 {badge_theme.STARS_MIN}..{badge_theme.STARS_MAX} (或 null/空串清空)",
                    "valid_range": [badge_theme.STARS_MIN, badge_theme.STARS_MAX],
                }, status_code=400)
            updates["card_stars"] = n

    conn, _ = db_adapter.get_conn()
    try:
        badge_db.ensure_card_theme_column(conn)
        badge_db.ensure_card_stars_column(conn)

        cur = db_adapter.execute(
            conn, "SELECT id FROM achievements WHERE id = ? LIMIT 1", (badge_id,),
        )
        if cur.fetchone() is None:
            return JSONResponse(
                {"ok": False, "error": f"id={badge_id!r} 不存在"}, status_code=404,
            )

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            db_adapter.execute(
                conn,
                f"UPDATE achievements SET {set_clause} WHERE id = ?",
                list(updates.values()) + [badge_id],
            )
            conn.commit()
            logger.info("card-appearance update: id=%s %s", badge_id, updates)

        rows = db_adapter.execute_dicts(
            conn, _SELECT_APPEARANCE_ROW + " WHERE id = ? LIMIT 1", (badge_id,),
        )
    except Exception as e:
        logger.exception("card-appearance update failed for %s", badge_id)
        return JSONResponse({"ok": False, "error": f"更新失败: {e}"}, status_code=500)
    finally:
        # MySQL 侧是 DBUtils PooledDB 连接: close() = 归还池 (不销毁)。
        # 旧版对 MySQL 跳过 close → 只能靠 GC 兜底, 高并发下耗尽池 (审计 P3-1)。
        try:
            conn.close()
        except Exception:
            pass

    if not rows:
        return JSONResponse(
            {"ok": False, "error": f"id={badge_id!r} 更新后读取失败"}, status_code=500,
        )
    return JSONResponse({
        "ok": True,
        "data": _appearance_row(rows[0]),
        "updated": sorted(updates.keys()),
    })
