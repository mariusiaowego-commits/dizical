"""
Web 用户登录/登出/改密/me 路由 (Sprint 26081003).

POST /api/auth/login              登录 (可选 remember)
POST /api/auth/logout             登出 (清 cookie)
POST /api/auth/change-password    改密 (含 must_change 强制改密)
GET  /api/auth/me                 查当前 user

mp 端 0 改动 (沿用 verify-pin + openid).
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.kid_app.auth import (
    COOKIE_MAX_AGE,
    ROLE_LABELS,
    clear_session_cookie,
    fetch_user_by_username,
    hash_password,
    set_session_cookie,
    update_last_login,
    update_password,
    verify_password,
)

router = APIRouter()


def _user_to_public(d: dict, include_password_hash: bool = False) -> dict:
    """user dict → JSON-safe (去 password_hash)."""
    out = {
        "user_id": d["user_id"],
        "username": d["username"],
        "display_name": d["display_name"],
        "role": d["role"],
        "role_label": ROLE_LABELS.get(d["role"], d["role"]),
        "avatar_letter": d.get("avatar_letter") or d["display_name"][:1],
        "must_change_password": bool(d.get("must_change_password", 0)),
    }
    if include_password_hash:
        out["password_hash"] = d.get("password_hash")
    return out


@router.post("/api/auth/login")
async def api_auth_login(request: Request):
    """{username, password, remember=true} → {ok, user} + Set-Cookie."""
    body = json.loads(await request.body() or b"{}")
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    remember = bool(body.get("remember", True))

    if not username or not password:
        return JSONResponse({"ok": False, "error": "用户名或密码错"},
                            status_code=401)

    user = fetch_user_by_username(username)
    # 通用错 (不区分用户名错/密码错, 防撞库)
    if not user or user["revoked"] or not verify_password(user["password_hash"], password):
        return JSONResponse({"ok": False, "error": "用户名或密码错"},
                            status_code=401)

    # 更新 last_login
    update_last_login(user["user_id"])

    response = JSONResponse({
        "ok": True,
        "user": _user_to_public(user),
        "max_age_days": 30 if remember else 0,
    })
    set_session_cookie(
        response,
        user_id=user["user_id"],
        role=user["role"],
        session_version=user["session_version"],
        remember=remember,
    )
    return response


@router.post("/api/auth/logout")
async def api_auth_logout(request: Request):
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@router.post("/api/auth/change-password")
async def api_auth_change_password(request: Request):
    """{old_password, new_password} → 改密 + 清 must_change.

    即使未登录也能调 (登录流程强制改密不依赖当前 session) — 简化处理:
    客户端在登录响应里拿到 user_id, 调这个端端用 {user_id, old_password, new_password}.
    """
    from src.kid_app.auth import fetch_user_by_id, MIN_PASSWORD_LEN

    body = json.loads(await request.body() or b"{}")
    user_id = body.get("user_id")
    old_password = body.get("old_password") or ""
    new_password = body.get("new_password") or ""

    if not user_id or not old_password or not new_password:
        return JSONResponse({"ok": False, "error": "参数缺失"},
                            status_code=400)
    if len(new_password) < MIN_PASSWORD_LEN:
        return JSONResponse({"ok": False, "error": f"新密码至少 {MIN_PASSWORD_LEN} 位"},
                            status_code=400)

    user = fetch_user_by_id(int(user_id))
    if not user or user["revoked"]:
        return JSONResponse({"ok": False, "error": "用户不存在"},
                            status_code=404)
    if not verify_password(user["password_hash"], old_password):
        return JSONResponse({"ok": False, "error": "旧密码错"},
                            status_code=401)

    new_hash = hash_password(new_password)
    update_password(user["user_id"], new_hash)
    return JSONResponse({"ok": True})


@router.get("/api/auth/me")
async def api_auth_me(request: Request):
    """返当前 user 或 401."""
    from src.kid_app.auth import get_current_user
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
    return JSONResponse({"ok": True, "user": _user_to_public(user)})