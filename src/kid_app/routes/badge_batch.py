"""
Badge 批量模式路由 (PR-C, 2026-06-12).

设计: 基于一个已上线 badge 的元数据, 衍生 N 个同风格新 badge.
继承自 PR-A 的 routes/badge_workflow.py 模式 (FastAPI Router, 延迟 import app.render).

端点:
  POST /config/api/badge/batch-preview  - SSE 流式: 跑 N 条流水线 (每条 30-60s)
  POST /config/api/badge/batch-commit   - 写三表 (一次事务 N 行)
  GET  /config/api/badge/batch-progress/{batch_id}  - 查询批量进度 (预留, V1.1 实现)

依赖:
- src.kid_app.badge_generator (run_badge_pipeline_batch + commit_badge_batch_to_db)
- src.kid_app.badge_db
- 路径: src/kid_app/routes/badge_batch.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.kid_app import badge_generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["badge-workflow-batch"])


# ─── API: 批量预览 (SSE) ──────────────────────────────────────

@router.post("/api/badge/batch-preview")
async def api_batch_preview(request: Request) -> StreamingResponse:
    """SSE 流式: 跑 N 条流水线 (每条 30-60s).

    Body: {
        source_badge_meta: { id, name, type, category, statLogic, description,
                             displayFormat, seasonalType },
        placeholders: [str, str, ...]   # N <= 20
    }

    SSE events:
      type=status,  stage=batch_start|batch_progress|step{0..5}_*, badge_id=xxx, message=...
      type=item_done, badge_id=xxx, ok=true/false, image_path=..., dedupe_ok=...
      type=batch_done, n_total, n_success, n_failed
      type=error, message=...
    """
    try:
        body = json.loads(await request.body())
    except json.JSONDecodeError:
        async def err_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'body 不是 JSON'})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    source_badge_meta = body.get("source_badge_meta", {})
    placeholders = body.get("placeholders", [])

    if not isinstance(placeholders, list):
        async def err_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'placeholders 必须是 list'})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")
    if not placeholders:
        async def err_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'placeholders 至少 1 项'})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")
    if len(placeholders) > badge_generator.BATCH_MAX_N:
        async def err_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': f'N 最多 {badge_generator.BATCH_MAX_N}'})}\n\n"
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    result_queue: queue.Queue = queue.Queue()

    def run() -> None:
        def on_status(stage: str, badge_id: str, msg: str) -> None:
            result_queue.put(("status", stage, badge_id, msg))

        result = badge_generator.run_badge_pipeline_batch(
            source_badge_meta=source_badge_meta,
            placeholders=placeholders,
            on_status=on_status,
        )
        result_queue.put(("done", result))

    async def event_stream():
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        # 200s * N (worst case), but we cap at 20 items so 4000s
        # 实际上 N=20 × 60s/FAL = 1200s, 200s 不够
        # V1 不做进度保存, 客户端必须 keep-alive
        # 改用动态 timeout: 60s × N + 30s 缓冲
        dynamic_timeout = 60 * len(placeholders) + 30
        while True:
            try:
                item = await asyncio.to_thread(result_queue.get, timeout=dynamic_timeout)
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': f'批量超时 ({dynamic_timeout}s)'})}\n\n"
                break

            if item[0] == "status":
                _, stage, badge_id, msg = item
                yield f"data: {json.dumps({'type': 'status', 'stage': stage, 'badge_id': badge_id, 'message': msg}, ensure_ascii=False)}\n\n"
            elif item[0] == "done":
                # done 返回整体结果, 前端再逐条展示
                _, result = item
                # 先推每条 item_done
                for r in result.get("results", []):
                    yield f"data: {json.dumps({'type': 'item_done', 'data': r}, ensure_ascii=False)}\n\n"
                # 再推 batch_done 汇总
                yield f"data: {json.dumps({'type': 'batch_done', 'n_total': result.get('n_total'), 'n_success': result.get('n_success'), 'n_failed': result.get('n_failed'), 'ok': result.get('ok')})}\n\n"
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


# ─── API: 批量写库 ──────────────────────────────────────────

@router.post("/api/badge/batch-commit")
async def api_batch_commit(request: Request) -> JSONResponse:
    """批量写三表. 一次事务 N 行.

    Body: {
        source_badge_meta: { id, name, type, category, statLogic, description, ... },
        items: [ { badge_id, image_path, version, placeholder, ok, ... }, ... ]
    }

    PIN 验证: 跟单条 commit 一致.
    """
    from src.database import db

    try:
        body = json.loads(await request.body())
    except json.JSONDecodeError:
        return JSONResponse({"ok": False, "error": "body 不是 JSON"}, status_code=400)

    # PIN 验证
    pin = body.get("pin", "")
    stored_pin = db.get_setting("dad_pin")
    if stored_pin and pin != stored_pin:
        return JSONResponse({"ok": False, "error": "PIN 不对"}, status_code=401)

    source_badge_meta = body.get("source_badge_meta", {})
    items = body.get("items", [])

    try:
        result = badge_generator.commit_badge_batch_to_db(
            source_badge_meta=source_badge_meta,
            items=items,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"批量写库失败: {e}"}, status_code=500)

    return JSONResponse({
        "ok": result.get("ok"),
        "committed_count": result.get("committed_count"),
        "failed": result.get("failed"),
    })
