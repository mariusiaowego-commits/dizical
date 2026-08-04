"""MAINTENANCE_MODE middleware — 切云/升级窗口的只读保护 (2026-08-04 Sprint 08).

模式 (env: MAINTENANCE_MODE):
- off          (默认): 正常读写
- readonly     写操作 (POST/PUT/DELETE/PATCH) 返 503 MAINTENANCE_READONLY, 读操作照常
- maintenance  所有非状态请求返 503 MAINTENANCE (维护页用)

设计要点:
- /health /health/live /health/ready /api/__maintenance__ 永不拦截
- OPTIONS (CORS preflight) 永不拦截 — middleware 注册在 CORSMiddleware 之后,
  FastAPI 后注册先执行, 必须放行 OPTIONS 否则 CORS 全断
- 静态文件 /static /uploads /data/reports 放行 (GET 只读)
- 只读模式下 POST 练习记录被 503 拦截 → 前端显示 "系统升级中" (由调用方处理)
"""

import os
import time
from fastapi import Request
from fastapi.responses import JSONResponse

MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "off")  # off | readonly | maintenance
MAINTENANCE_STARTED_AT = time.time() if MAINTENANCE_MODE != "off" else None
MAINTENANCE_EXPECTED_RESUME = os.getenv("MAINTENANCE_EXPECTED_RESUME", "2026-08-04 13:00")

_BLOCKED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
_ALWAYS_ALLOWED_PREFIXES = (
    "/health",
    "/api/__maintenance__",
    "/static",
    "/uploads",
    "/data/reports",
)


def _is_status_or_static(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    return path.startswith(_ALWAYS_ALLOWED_PREFIXES)


async def maintenance_middleware(request: Request, call_next):
    path = request.url.path
    mode = MAINTENANCE_MODE

    if mode == "off" or _is_status_or_static(path, request.method):
        return await call_next(request)

    if mode == "maintenance":
        return JSONResponse(
            status_code=503,
            content={
                "error": "MAINTENANCE",
                "message": "系统维护中，请稍后重试",
                "path": path,
                "expected_resume": MAINTENANCE_EXPECTED_RESUME,
            },
        )

    if mode == "readonly" and request.method in _BLOCKED_METHODS:
        return JSONResponse(
            status_code=503,
            content={
                "error": "MAINTENANCE_READONLY",
                "message": "系统升级中，预计 13:00 恢复，请稍后录入",
                "path": path,
                "expected_resume": MAINTENANCE_EXPECTED_RESUME,
            },
        )

    return await call_next(request)
