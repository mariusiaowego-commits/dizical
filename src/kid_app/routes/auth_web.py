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
    clear_pin_ok_cookie,  # agy review P2: 登出也清 PIN 解锁 cookie
    clear_session_cookie,
    fetch_user_by_username,
    hash_password,
    increment_login_failed,
    is_user_locked,
    reset_login_failed,
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
        if user and not user["revoked"]:
            # 失败计数 (Q4: 5 次锁 5 分钟)
            increment_login_failed(user["user_id"])
        return JSONResponse({"ok": False, "error": "用户名或密码错"},
                            status_code=401)

    # 锁住? (Q4)
    if is_user_locked(user):
        return JSONResponse({"ok": False, "error": "账号暂时锁定, 请 5 分钟后再试"},
                            status_code=423)  # 423 Locked

    # 登录成功: 清失败计数 + lockout
    reset_login_failed(user["user_id"])

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
    clear_pin_ok_cookie(response)  # agy review P2: PIN 解锁 cookie 也清, 防残留
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
    # update_password 默认 bump_session=True (Q6: 踢出其他设备)
    update_password(user["user_id"], new_hash)
    return JSONResponse({"ok": True, "note": "其他设备已自动登出"})


@router.get("/api/auth/me")
async def api_auth_me(request: Request):
    """返当前 user 或 401."""
    from src.kid_app.auth import get_current_user
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "error": "未登录"}, status_code=401)
    return JSONResponse({"ok": True, "user": _user_to_public(user)})


# ─── Q7: 邀请链接公开兑换 ─────────────────────────────────────
@router.post("/api/auth/redeem-invite")
async def api_auth_redeem_invite(request: Request):
    """{token, username, display_name, password} → 建账号 + 自动登录."""
    from src.kid_app.auth import (
        consume_invite, create_user, fetch_invite, fetch_user_by_username,
        hash_password, set_session_cookie, MIN_PASSWORD_LEN,
    )

    body = json.loads(await request.body() or b"{}")
    token = (body.get("token") or "").strip()
    username = (body.get("username") or "").strip()
    display_name = (body.get("display_name") or "").strip()
    password = body.get("password") or ""

    if not token or not username or not display_name or not password:
        return JSONResponse({"ok": False, "error": "参数缺失"},
                            status_code=400)
    if len(password) < MIN_PASSWORD_LEN:
        return JSONResponse({"ok": False, "error": f"密码至少 {MIN_PASSWORD_LEN} 位"},
                            status_code=400)
    if len(username) < 2 or len(username) > 64:
        return JSONResponse({"ok": False, "error": "用户名长度 2-64"},
                            status_code=400)

    invite = fetch_invite(token)
    if not invite:
        return JSONResponse({"ok": False, "error": "邀请链接无效 / 已过期 / 已用完"},
                            status_code=410)

    # username 重复?
    if fetch_user_by_username(username):
        return JSONResponse({"ok": False, "error": "用户名已存在, 请换别的"},
                            status_code=400)

    # 建账号 (must_change=0 — 用户自己设的密码)
    try:
        user_id = create_user(
            username=username, display_name=display_name,
            password_hash=hash_password(password),
            role=invite["role"], avatar_letter=display_name[:1].upper(),
            created_by=None,
        )
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

    # 兑换 invite
    consume_invite(token)

    # 自动登录
    user = fetch_user_by_username(username)
    from src.kid_app.auth import update_last_login
    update_last_login(user_id)
    response = JSONResponse({
        "ok": True,
        "user": _user_to_public(user),
        "auto_login": True,
    })
    set_session_cookie(response, user_id=user_id, role=user["role"],
                        session_version=user["session_version"], remember=True)
    return response


# ── Sprint 26081003 v3.3.2: dad 应急重置密码 (走 PIN=0905) ─────────
from src.kid_app.auth import check_dad_pin  # 复用双轨守门 (PIN=0905 校验)

@router.post("/api/admin/reset-password")
async def api_admin_reset_password(request: Request):
    """dad 应急重置: {username, pin} → {ok, new_password}.

    只在 dad PIN 验证通过 + username=dad 时重置.
    新密码随机生成 12 位强密码, 返明文一次.
    不 bump session_version (dad 当前 cookie 保留可用).
    """
    body = json.loads(await request.body() or b"{}")
    username = (body.get("username") or "").strip()
    pin = (body.get("pin") or "").strip()

    if username != "dad":
        return JSONResponse({"ok": False, "error": "只能重置 dad 账号"},
                            status_code=400)
    if not check_dad_pin(pin):
        return JSONResponse({"ok": False, "error": "PIN 错"}, status_code=401)

    user = fetch_user_by_username("dad")
    if not user:
        return JSONResponse({"ok": False, "error": "dad 账号不存在 (先跑 migrate)"},
                            status_code=404)

    # 生成新密码 (12 位强密码 — 字母 + 数字, 去除易混字符)
    import secrets, string
    alphabet = string.ascii_letters.replace("I", "").replace("O", "").replace("l", "") + string.digits.replace("0", "").replace("1", "")
    new_password = "".join(secrets.choice(alphabet) for _ in range(12))

    # 改密 (must_change=1 让 dad 强制改一次, 不 bump sv 避免 dad 当前 cookie 被踢)
    new_hash = hash_password(new_password)
    update_password(user["user_id"], new_hash, bump_session=False)
    # update_password 内部会清 must_change=0, 重新 set 1 (Sprint v3.3.2)
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        cur = conn.cursor()
        if is_mysql:
            cur.execute("UPDATE web_users SET must_change_password = 1 WHERE user_id = %s",
                        (user["user_id"],))
        else:
            cur.execute("UPDATE web_users SET must_change_password = 1 WHERE user_id = ?",
                        (user["user_id"],))
        conn.commit()
    finally:
        if not is_mysql:
            conn.close()

    return JSONResponse({
        "ok": True,
        "new_password": new_password,
        "warning": "请把新密码通过安全渠道记下. 首次登录后必须改密."
    })
