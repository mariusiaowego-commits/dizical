"""
Dad 后台用户管理路由 (Sprint 26081003 v3.3).

GET  /config/users                              用户管理页 (HTML, dad PIN 或 dad session)
POST /config/api/users/create                   建账号 (返明文初始密码 1 次)
POST /config/api/users/{id}/reset-password      重置密码 (返新明文 1 次)
POST /config/api/users/{id}/role                改 role
POST /config/api/users/{id}/revoke              软删
POST /config/api/users/{id}/logout-all          踢出所有设备
POST /config/api/invites/create                  生成邀请链接
GET  /config/api/invites/list                   邀请列表
POST /config/api/invites/{id}/revoke            撤销邀请

Sprint 26081003 v3.3 双轨守门:
- PIN 应急 (curl / dad 忘了密码): X-Dad-Pin header = settings.dad_pin
- dad role session (浏览器): get_current_user(role=dad)
普通 web_users (student/family/teacher) 拒绝.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.kid_app.auth import (
    ROLE_LABELS,
    bump_session_version,
    check_dad_pin,
    create_user,
    generate_random_password,
    hash_password,
    list_users,
    load_pin_ok_cookie,
    revoke_user,
    set_pin_ok_cookie,
    update_role,
)

# Jinja 模板 (跟 minip_api.py 同款 env)
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_env = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


async def _check_dad_or_401(request: Request):
    """dad 守门 (Sprint 26081003 v3.3 + 26082901 增强): 三轨.

    - PIN (应急 curl): body pin / X-Dad-Pin header
    - dad role session (浏览器): get_current_user(role=dad)
    - pin_ok cookie (已验证, Sprint 26082901): 前端改 POST verify 后种下的
      HttpOnly 签名 cookie, 页面后续写接口走它 (避免 URL 再带 PIN)
    普通 web_users (student/family/teacher) 拒绝.
    """
    # 1) PIN 守门 (从 body / header 取)
    pin = ""
    try:
        body = json.loads(await request.body() or b"{}")
        pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    except Exception:  # noqa: BLE001
        pin = request.headers.get("X-Dad-Pin", "")
    if pin and check_dad_pin(pin):
        return None
    # 2) dad session 守门
    from src.kid_app.auth import get_current_user
    user = await get_current_user(request)
    if user and user.get("role") == "dad":
        return None
    # 3) pin_ok cookie 守门 (已验证签名, 无 URL 泄漏)
    if load_pin_ok_cookie(request):
        return None
    return JSONResponse({"ok": False, "error": "需要 dad 登录或 PIN"}, status_code=401)


def _check_pin_or_401(pin: str):
    """PIN-only 守门 (兼容老逻辑, 仅 invite/list GET 仍可用 — 查询参数)."""
    if not check_dad_pin(pin):
        return JSONResponse({"ok": False, "error": "PIN 错"}, status_code=401)
    return None


@router.get("/config/users", response_class=HTMLResponse)
async def config_users_page(request: Request, pin: str = ""):
    """dad 用户管理 UI. 三轨守门: dad session OR PIN OR pin_ok cookie.

    Sprint 26082901 PIN 残留 URL 修复:
      - query ?pin=0905 (老链接/curl) → 校验通过后 303 种 pin_ok cookie 清 URL
      - 前端已改 POST /config/users/verify, 不依赖 URL PIN
    """
    from src.kid_app.auth import get_current_user
    user = await get_current_user(request)
    dad_via_session = bool(user and user.get("role") == "dad")

    # query PIN 正确 → 洗白: 303 + 种 pin_ok cookie, 丢 URL PIN
    if pin and check_dad_pin(pin):
        resp = RedirectResponse(url="/config/users", status_code=303)
        set_pin_ok_cookie(resp)
        return resp

    pin_ok_cookie = load_pin_ok_cookie(request)
    pin_valid = bool(pin) and check_dad_pin(pin)
    has_access = dad_via_session or pin_valid or pin_ok_cookie
    users = list_users() if has_access else []
    # dad session: 前端写接口走 session cookie. PIN 路径: 走 pin_ok cookie, 不放真 PIN.
    # CURRENT_PIN 哨兵 "session" 表示"已有有效凭据, 前端写接口不带 URL PIN".
    effective_pin = pin if pin_valid else "session"

    # 转 datetime 为字符串 (Jinja 不能直接渲染)
    for u in users:
        for k in ("created_at", "last_login_at"):
            if u.get(k) and not isinstance(u[k], str):
                u[k] = str(u[k])

    return _env.TemplateResponse(
        request,
        "config-users.html",
        {
            "active_nav": "config_users",
            "pin": effective_pin,
            "pin_valid": has_access,
            "users": users,
            "role_labels": ROLE_LABELS,
            "today": __import__("datetime").date.today().isoformat(),
            "current_user": user,  # 给前端 navbar 用 (dad 头像/登出)
            "dad_via_session": dad_via_session,
        },
    )


@router.post("/config/api/users/create")
async def api_users_create(request: Request):
    """{username, display_name, role, avatar_letter, pin} → 返 initial_password 一次."""
    body = json.loads(await request.body() or b"{}")
    pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    err = await _check_dad_or_401(request)
    if err: return err

    username = (body.get("username") or "").strip()
    display_name = (body.get("display_name") or "").strip()
    role = (body.get("role") or "").strip()
    avatar_letter = (body.get("avatar_letter") or display_name[:1] or "U").strip()[:1].upper()

    if not username or not display_name or role not in ("student", "family", "teacher", "dad"):
        return JSONResponse({"ok": False, "error": "参数缺失或 role 不合法"},
                            status_code=400)
    if len(username) < 2 or len(username) > 64:
        return JSONResponse({"ok": False, "error": "用户名长度 2-64"},
                            status_code=400)

    initial_password = generate_random_password(12)
    try:
        user_id = create_user(
            username=username,
            display_name=display_name,
            password_hash=hash_password(initial_password),
            role=role,
            avatar_letter=avatar_letter,
            created_by=None,  # 简化: 不传 dad user_id (dad 走 PIN 不走 web_users)
        )
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

    return JSONResponse({
        "ok": True,
        "user_id": user_id,
        "username": username,
        "initial_password": initial_password,
        "warning": "请把初始密码通过安全渠道 (微信/电话) 告知该用户, 首次登录后必须改密.",
    })


@router.post("/config/api/users/{user_id}/reset-password")
async def api_users_reset_password(request: Request, user_id: int):
    body = json.loads(await request.body() or b"{}")
    pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    err = await _check_dad_or_401(request)
    if err: return err

    new_password = generate_random_password(12)
    from src.kid_app.auth import fetch_user_by_id, update_password
    user = fetch_user_by_id(user_id)
    if not user:
        return JSONResponse({"ok": False, "error": "用户不存在"}, status_code=404)

    update_password(user_id, hash_password(new_password))
    # 重置后必须改密
    from src.db_adapter import execute as _db_execute, get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(conn, "UPDATE web_users SET must_change_password = 1 WHERE user_id = ?",
                    (user_id,))
        conn.commit()
    finally:
        if not is_mysql: conn.close()

    return JSONResponse({
        "ok": True,
        "user_id": user_id,
        "username": user["username"],
        "new_password": new_password,
        "must_change": True,
    })


@router.post("/config/api/users/{user_id}/set-password")
async def api_users_set_password(request: Request, user_id: int):
    """{pin, new_password} → 把该用户密码设为 dad 指定的明文.

    Sprint 26082901 dad 拍板方案 ① "重置为指定密码": dad 想"看到当前密码"
    以便微信/电话告知家人, 但密码是 scrypt 单向哈希, 原明文无法回看.
    折中: dad 自己设一个新密码 (他知道的), 当场返回明文 1 次 → 设置的就是
    记得住的密码. 不存明文 (安全), 设完即忘, 保持和现有 reset-password 一致的
    dad 守门 (PIN 或 dad role session).

    与 reset-password 差异:
      - 接受 dad 提供的 new_password (非随机), 校验 >= MIN_PASSWORD_LEN (hash_password 抛 ValueError)
      - 设置后不强制 must_change_password (dad 设的就是用户该用的密码); reset 会置 1
      - 不 bump session (不把用户/设备登出), 和 reset 一致 (dad 重置设密码是帮用户)
    """
    body = json.loads(await request.body() or b"{}")
    pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    err = await _check_dad_or_401(request)
    if err: return err

    new_password = (body.get("new_password") or "").strip()
    if not new_password:
        return JSONResponse({"ok": False, "error": "密码不能为空"}, status_code=400)

    from src.kid_app.auth import fetch_user_by_id, update_password
    user = fetch_user_by_id(user_id)
    if not user:
        return JSONResponse({"ok": False, "error": "用户不存在"}, status_code=404)

    try:
        new_hash = hash_password(new_password)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

    update_password(user_id, new_hash, bump_session=False)
    return JSONResponse({
        "ok": True,
        "user_id": user_id,
        "username": user["username"],
        "new_password": new_password,
        "must_change": False,
    })


@router.post("/config/api/users/{user_id}/role")
async def api_users_change_role(request: Request, user_id: int):
    body = json.loads(await request.body() or b"{}")
    pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    err = await _check_dad_or_401(request)
    if err: return err

    new_role = (body.get("role") or "").strip()
    if new_role not in ("student", "family", "teacher", "dad"):
        return JSONResponse({"ok": False, "error": "role 不合法"}, status_code=400)

    update_role(user_id, new_role)
    return JSONResponse({"ok": True, "user_id": user_id, "role": new_role})


@router.post("/config/api/users/{user_id}/revoke")
async def api_users_revoke(request: Request, user_id: int):
    body = json.loads(await request.body() or b"{}")
    pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    err = await _check_dad_or_401(request)
    if err: return err

    revoke_user(user_id)
    return JSONResponse({"ok": True, "user_id": user_id, "revoked": True})


@router.post("/config/api/users/{user_id}/logout-all")
async def api_users_logout_all(request: Request, user_id: int):
    """踢出该用户所有设备. 递增 session_version."""
    body = json.loads(await request.body() or b"{}")
    pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    err = await _check_dad_or_401(request)
    if err: return err

    bump_session_version(user_id)
    return JSONResponse({"ok": True, "user_id": user_id, "kicked": True})


# ─── Q7: 邀请链接管理 (dad 后台) ─────────────────────────────────
from datetime import datetime, timedelta
from src.kid_app.auth import (
    create_invite, fetch_invite, list_invites, revoke_invite,
)


@router.post("/config/api/invites/create")
async def api_invites_create(request: Request):
    """{role, expires_hours=24, max_uses=1, note=""} → 返 invite_token + URL.

    dad 把 URL 通过微信/电话发给被邀请人. URL 形如:
      http://localhost:8765/accept-invite?token=xxxx
    """
    body = json.loads(await request.body() or b"{}")
    pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    err = await _check_dad_or_401(request)
    if err: return err

    role = (body.get("role") or "").strip()
    expires_hours = int(body.get("expires_hours") or 24)
    max_uses = int(body.get("max_uses") or 1)
    note = (body.get("note") or "").strip()[:128]

    if role not in ("student", "family", "teacher"):
        return JSONResponse({"ok": False, "error": "role 不合法 (student/family/teacher)"},
                            status_code=400)
    if expires_hours < 1 or expires_hours > 24 * 30:
        return JSONResponse({"ok": False, "error": "过期时间 1-720 小时"},
                            status_code=400)
    if max_uses < 1 or max_uses > 100:
        return JSONResponse({"ok": False, "error": "max_uses 1-100"},
                            status_code=400)

    expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
    token = create_invite(role=role, expires_at=expires_at,
                          max_uses=max_uses, note=note, created_by=None)

    # 返完整 URL. Sprint v3.3.2 修: 不要用 request.base_url (在 0.0.0.0:8765 监听的
    # 服务下返 "http://0.0.0.0:8765" 给 dad, dad 复制走 iPad 打不开).
    # 优先 DIZICAL_PUBLIC_BASE env (dad 在 start-prod.sh 设), 否则 fallback Tailscale IP,
    # 否则 fallback 局域网 IP, 否则兜底 request.base_url.
    import os as _os
    public_base = _os.environ.get("DIZICAL_PUBLIC_BASE", "").rstrip("/")
    if not public_base:
        # 尝试用 ifconfig / Tailscale 自动检测
        tailscale_ip = ""
        lan_ip = ""
        try:
            import subprocess as _sp
            r = _sp.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=2)
            tailscale_ip = (r.stdout.strip().split("\n")[0] if r.returncode == 0 else "")
        except Exception:
            pass
        if not tailscale_ip:
            try:
                import subprocess as _sp, re as _re
                r = _sp.run(["ifconfig"], capture_output=True, text=True, timeout=2)
                # 私人 IP 段: 10.x.x.x / 172.16-31.x.x / 192.168.x.x
                # 跳过 127.x / 198.18.x / 169.254.x / fe80
                m = _re.search(
                    r"inet ((?:10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.)\d+\.\d+\.\d+)",
                    r.stdout)
                lan_ip = m.group(1) if m else ""
            except Exception:
                pass
        if tailscale_ip:
            public_base = f"http://{tailscale_ip}:8765"
        elif lan_ip:
            public_base = f"http://{lan_ip}:8765"
        else:
            public_base = str(request.base_url).rstrip("/")
    url = f"{public_base}/accept-invite?token={token}"

    return JSONResponse({
        "ok": True,
        "token": token,
        "url": url,
        "role": role,
        "expires_at": expires_at.isoformat(),
        "max_uses": max_uses,
        "note": note,
    })


@router.get("/config/api/invites/list")
async def api_invites_list(request: Request, pin: str = ""):
    """列所有 invite (含已用/过期). 三轨守门 (Sprint 26082901: 支持 pin_ok cookie)."""
    # 兼容老 client 的 ?pin= query (旧前端 / curl)
    if pin and check_dad_pin(pin):
        pass  # 有效, 继续
    else:
        err = await _check_dad_or_401(request)
        if err: return err

    invites = list_invites()
    # 转 datetime 为字符串
    for inv in invites:
        for k in ("expires_at", "created_at"):
            if inv.get(k) and not isinstance(inv[k], str):
                inv[k] = str(inv[k])
    return JSONResponse({"ok": True, "invites": invites})


# ─── PIN 页面解锁 verify (Sprint 26082901) ─────────────────────
import time as _time

# IP 限流: 5 次 / 5 分钟 (防 4 位 PIN 爆破). 简单位 dict (单进程够用).
_PIN_FAIL: dict[str, list[float]] = {}


def _rate_limited(ip: str) -> int:
    """记录一次失败. 若 5 分钟内失败 >=5 次返 429 秒数, 否则 0."""
    now = _time.time()
    tries = _PIN_FAIL.setdefault(ip, [])
    tries = [t for t in tries if now - t < 300]
    _PIN_FAIL[ip] = tries
    if len(tries) >= 5:
        return int(300 - (now - tries[0]))
    return 0


def _record_fail(ip: str) -> None:
    _PIN_FAIL.setdefault(ip, []).append(_time.time())


def _reject_cross_origin(request: Request) -> Optional[JSONResponse]:
    """SameSite=Lax 已挡跨站 POST, 加 Origin/Referer 校验兜底 (grok reference)."""
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if not origin:
        return None  # curl / 无浏览器 → 允许 (已有 body PIN 校验是真实凭据)
    from urllib.parse import urlparse
    try:
        o = urlparse(origin)
    except Exception:  # noqa: BLE001
        return None
    host = request.headers.get("host", "")
    if o.netloc == host or (o.hostname and host.startswith(o.hostname)):
        return None
    return JSONResponse({"ok": False, "error": "跨源请求被拒绝"}, status_code=403)


@router.post("/config/users/verify")
async def api_verify_pin(request: Request):
    """{pin} → 验 PIN, 通过则种 pin_ok cookie (HttpOnly, 2h), 返 {ok:True}.

    前端 submitPin() 改 POST 到此处, location.replace('/config/users')
    地址栏不再出现 PIN.
    """
    cross = _reject_cross_origin(request)
    if cross: return cross

    body = json.loads(await request.body() or b"{}")
    pin = (body.get("pin") or "").strip()

    # 限流 (IP)
    ip = request.client.host if request.client else "unknown"
    locked = _rate_limited(ip)
    if locked > 0:
        return JSONResponse({"ok": False, "error": f"尝试过于频繁, 请 {locked} 秒后重试"},
                            status_code=429)

    if not check_dad_pin(pin):
        _record_fail(ip)
        return JSONResponse({"ok": False, "error": "PIN 错误"}, status_code=401)

    resp = JSONResponse({"ok": True})
    set_pin_ok_cookie(resp)
    return resp


@router.post("/config/api/invites/{invite_id}/revoke")
async def api_invites_revoke(request: Request, invite_id: int):
    body = json.loads(await request.body() or b"{}")
    pin = body.get("pin") or request.headers.get("X-Dad-Pin", "")
    err = await _check_dad_or_401(request)
    if err: return err

    revoke_invite(invite_id)
    return JSONResponse({"ok": True, "invite_id": invite_id, "revoked": True})