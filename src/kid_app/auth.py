"""
Web 用户体系核心 (Sprint 26081003).

- stdlib scrypt 密码哈希 (不引新依赖, 跟 prod Python 3.14 100% 兼容)
- stdlib hmac + base64 + json 自签签名 cookie (HMAC-SHA256)
- FastAPI Dependencies: get_current_user / require_login / require_role
- Session 版本号支持 dad 踢出所有设备

环境变量:
  DIZICAL_SESSION_SECRET  强密码 (CloudRun 必须设, dev 用 fallback)
  DIZICAL_INSECURE_COOKIE  1=dev 允许 http (默认 0=prod 要求 https)

Cookie 设计:
  - 名: dizical_session
  - 内容: 签名 {user_id, role, sv}
  - max_age: 30 天 (Q3=A)
  - HttpOnly+Secure+SameSite=Lax
  - 改 web_users.session_version 字段 = 踢出所有老 cookie
"""
from __future__ import annotations

import os
import json
from typing import Optional

from fastapi import HTTPException, Request, Response


from src.database import db

# ─── 密码哈希 (stdlib scrypt, 不引新依赖) ───────────────────────
# Sprint 26081003 v3.2 决策: 改用 hashlib.scrypt (NIST SP 800-132 推荐,
# 安全等级 ≈ argon2id, 字符串格式 "scrypt$<salt_b64>$<hash_b64>").
# 原因: prod Python 3.14 没装 argon2-cffi (PEP 668 拦), stdlib 始终可用.
import hashlib
import hmac
import base64

_SCRYPT_N = 2**14  # CPU cost (n=2^14 ~16MB, 跟 OpenSSL 默认 maxmem=32MB 兼容)
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32

MIN_PASSWORD_LEN = 6


def hash_password(plain: str) -> str:
    """scrypt hash. raise ValueError if 长度不足."""
    if len(plain) < MIN_PASSWORD_LEN:
        raise ValueError(f"密码至少 {MIN_PASSWORD_LEN} 位")
    salt = os.urandom(16)
    hk = hashlib.scrypt(plain.encode("utf-8"), salt=salt,
                        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
                        dklen=_SCRYPT_DKLEN, maxmem=64 * 1024 * 1024)
    return f"scrypt${base64.b64encode(salt).decode('ascii')}${base64.b64encode(hk).decode('ascii')}"


def verify_password(hash_str: str, plain: str) -> bool:
    """校验 scrypt 密码. 返 True/False (不抛)."""
    if not hash_str or not plain:
        return False
    try:
        parts = hash_str.split("$")
        if len(parts) != 3 or parts[0] != "scrypt":
            return False
        salt = base64.b64decode(parts[1])
        expected = base64.b64decode(parts[2])
        actual = hashlib.scrypt(plain.encode("utf-8"), salt=salt,
                                n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
                                dklen=_SCRYPT_DKLEN, maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(actual, expected)
    except (ValueError, Exception):  # noqa: BLE001
        return False


# ─── Cookie 签名 ────────────────────────────────────────
import time

SESSION_SECRET = os.getenv("DIZICAL_SESSION_SECRET", "dev-fallback-please-set-DIZICAL_SESSION_SECRET")
SESSION_SALT = "dizical-web-session-v1"
COOKIE_NAME = "dizical_session"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 天
INSECURE_COOKIE = os.getenv("DIZICAL_INSECURE_COOKIE", "0") == "1"


def _cookie_sign(payload: dict) -> str:
    """签发 'base64url(json).base64url(hmac_sha256)' cookie 字符串."""
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    exp = int(payload.get("exp", 0))
    msg = raw + b"|" + str(exp).encode("ascii")
    sig = hmac.new(SESSION_SECRET.encode("utf-8"), msg, hashlib.sha256).digest()
    return (base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
            + "."
            + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii"))


def _cookie_verify(token: str) -> dict | None:
    """验签 + 检查 exp. 失败返 None."""
    try:
        raw_b64, sig_b64 = token.split(".", 1)
    except (ValueError, AttributeError):
        return None
    try:
        raw = base64.urlsafe_b64decode(raw_b64 + "=" * (-len(raw_b64) % 4))
        sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
    except Exception:  # noqa: BLE001
        return None
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return None
    exp = int(payload.get("exp", 0))
    msg = raw + b"|" + str(exp).encode("ascii")
    expected = hmac.new(SESSION_SECRET.encode("utf-8"), msg, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return None
    if exp and int(time.time()) > exp:
        return None
    return payload




def make_session_cookie(user_id: int, role: str, session_version: int) -> str:
    """签发 HMAC-SHA256 签名 cookie (含 exp)."""
    return _cookie_sign({
        "user_id": user_id, "role": role, "sv": session_version,
        "exp": int(time.time()) + COOKIE_MAX_AGE,
    })


def load_session_cookie(raw: str) -> Optional[dict]:
    """校验签名 + 过期. 返 None 表示无效/过期/篡改."""
    if not raw:
        return None
    return _cookie_verify(raw)


def make_mp_session_token(user_id: int, role: str, session_version: int) -> str:
    """复用 web cookie HMAC 机制, 给 mp 用 (X-Mp-Session header)."""
    return make_session_cookie(user_id, role, session_version)


def load_mp_session_token(raw: str) -> Optional[dict]:
    """复用 web cookie HMAC 校验. 返 payload dict (含 user_id, role, sv, exp) 或 None."""
    return load_session_cookie(raw)


async def get_mp_current_user(request: Request) -> Optional[dict]:
    """从 X-Mp-Session header 解析 mp user dict 并校验 session_version."""
    sig = (
        request.headers.get("X-Mp-Session")
        or request.headers.get("x-mp-session")
        or request.headers.get("Authorization")
    )
    if not sig:
        return None
    if sig.startswith("Bearer "):
        sig = sig[7:].strip()
    session = load_mp_session_token(sig)
    if not session:
        return None
    user = fetch_user_by_id(session["user_id"])
    if not user or user.get("revoked"):
        return None
    if session.get("sv", 0) != user.get("session_version", 0):
        return None
    return user


def set_session_cookie(response: Response, user_id: int, role: str,
                        session_version: int, remember: bool = True) -> None:
    sig = make_session_cookie(user_id, role, session_version)
    response.set_cookie(
        key=COOKIE_NAME,
        value=sig,
        max_age=COOKIE_MAX_AGE if remember else None,
        httponly=True,
        secure=not INSECURE_COOKIE,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


# ─── DB 查询 (双后端兼容: SQLite 本地 / MySQL 云) ─────────
# 用 src/db_adapter 走 db.execute (双后端占位符兼容)
from src.db_adapter import execute as _db_execute


def _fetchone_dict(sql: str, params: tuple = ()) -> Optional[dict]:
    """单行查询, 返 dict 或 None. 双后端兼容.

    pymysql 默认 tuple cursor, 即使 row 是 tuple — dict(row) 在 Python 3.14
    抛 "Cannot convert ..." (dict constructor 把 tuple 当 pairs, 失败).
    统一用 cur.description 取列名 + zip — 双后端一致.
    """
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        cur = _db_execute(conn, sql, params)
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row  # DictCursor 已返 dict
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        if not is_mysql:
            conn.close()


def fetch_user_by_username(username: str) -> Optional[dict]:
    return _fetchone_dict(
        "SELECT user_id, username, display_name, password_hash, role, avatar_letter, "
        "must_change_password, session_version, revoked, login_failed_count, locked_until "
        "FROM web_users WHERE username = ?",
        (username,),
    )


# Alias for backward/forward compatibility
get_user_by_username = fetch_user_by_username


def fetch_user_by_id(user_id: int) -> Optional[dict]:
    return _fetchone_dict(
        "SELECT user_id, username, display_name, password_hash, role, avatar_letter, "
        "must_change_password, session_version, revoked, login_failed_count, locked_until "
        "FROM web_users WHERE user_id = ?",
        (user_id,),
    )


def update_last_login(user_id: int) -> None:
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(
            conn,
            "UPDATE web_users SET last_login_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        if not is_mysql:
            conn.close()


def create_user(username: str, display_name: str, password_hash: str,
                role: str, avatar_letter: str, created_by: Optional[int]) -> int:
    """建账号. 返 user_id. 重复 username 抛 ValueError."""
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        cur = _db_execute(
            conn,
            "INSERT INTO web_users (username, display_name, password_hash, role, "
            "avatar_letter, must_change_password, created_by) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (username, display_name, password_hash, role, avatar_letter, created_by),
        )
        conn.commit()
        if cur.lastrowid is None:
            raise RuntimeError("INSERT 未返回 lastrowid, 表创建失败?")
        return int(cur.lastrowid)
    except Exception as e:
        # SQLite UNIQUE / MySQL Duplicate entry
        if "UNIQUE" in str(e) or "Duplicate" in str(e) or "1062" in str(e):
            raise ValueError(f"用户名 '{username}' 已存在")
        raise
    finally:
        if not is_mysql:
            conn.close()


def update_password(user_id: int, new_hash: str, bump_session: bool = True) -> None:
    """改密. bump_session=True (默认) 时 session_version+=1, 自动踢出其他设备 (Q6).

    dad 重置密码 (config_users.reset-password) 显式传 False — 老 cookie 保留以便
    dad 不用每次都重登, 但 must_change=1 自动让用户改密一次.
    """
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        if bump_session:
            _db_execute(
                conn,
                "UPDATE web_users SET password_hash = ?, must_change_password = 0, "
                "session_version = session_version + 1, login_failed_count = 0 "
                "WHERE user_id = ?",
                (new_hash, user_id),
            )
        else:
            _db_execute(
                conn,
                "UPDATE web_users SET password_hash = ?, must_change_password = 0, "
                "login_failed_count = 0 "
                "WHERE user_id = ?",
                (new_hash, user_id),
            )
        conn.commit()
    finally:
        if not is_mysql:
            conn.close()


def update_role(user_id: int, role: str) -> None:
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(
            conn,
            "UPDATE web_users SET role = ? WHERE user_id = ?",
            (role, user_id),
        )
        conn.commit()
    finally:
        if not is_mysql:
            conn.close()


# ─── Login lockout (Q4: 输错 5 次锁 5 分钟) ─────────────────
LOGIN_MAX_FAILED = 5
LOGIN_LOCKOUT_SECONDS = 300  # 5 分钟


def is_user_locked(user: dict) -> bool:
    """检查用户是否处于 lockout 状态. user dict 需含 locked_until."""
    from datetime import datetime
    lu = user.get("locked_until")
    if not lu:
        return False
    # SQLite 返回字符串, MySQL 可能返 datetime
    if isinstance(lu, str):
        try:
            lu = datetime.fromisoformat(lu)
        except (ValueError, TypeError):
            return False
    if isinstance(lu, datetime):
        from datetime import datetime as _dt
        return lu > _dt.utcnow()
    return False


def increment_login_failed(user_id: int) -> int:
    """登录失败计数 +1. 若到阈值, 锁账号 5 分钟. 返当前失败次数."""
    from datetime import datetime, timedelta
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(
            conn,
            "UPDATE web_users SET login_failed_count = login_failed_count + 1 "
            "WHERE user_id = ?",
            (user_id,),
        )
        # 取当前 count
        cur = _db_execute(conn, "SELECT login_failed_count FROM web_users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        cnt = (row[0] if row and not isinstance(row, dict) else (row.get("login_failed_count", 0) if row else 0))
        if cnt >= LOGIN_MAX_FAILED:
            locked_until = datetime.utcnow() + timedelta(seconds=LOGIN_LOCKOUT_SECONDS)
            _db_execute(
                conn,
                "UPDATE web_users SET locked_until = ? WHERE user_id = ?",
                (locked_until.isoformat() if is_mysql else locked_until.strftime("%Y-%m-%d %H:%M:%S"),
                 user_id),
            )
        conn.commit()
        return int(cnt) if cnt is not None else 0
    finally:
        if not is_mysql:
            conn.close()


def reset_login_failed(user_id: int) -> None:
    """登录成功时清零 + 清 lockout."""
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(
            conn,
            "UPDATE web_users SET login_failed_count = 0, locked_until = NULL WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        if not is_mysql:
            conn.close()


def revoke_user(user_id: int) -> None:
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(
            conn,
            "UPDATE web_users SET revoked = 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        if not is_mysql:
            conn.close()


def bump_session_version(user_id: int) -> None:
    """踢出所有设备: 递增 session_version, 老 cookie sv 字段不匹配 → 401."""
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(
            conn,
            "UPDATE web_users SET session_version = session_version + 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        if not is_mysql:
            conn.close()


# ─── web_invites (Q7: 一次性邀请链接) ─────────────────
import secrets


def create_invite(role: str, expires_at, max_uses: int = 1,
                   note: str = "", created_by: Optional[int] = None) -> str:
    """建邀请链接. 返 invite_token (URL 用)."""
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        token = secrets.token_urlsafe(32)  # 32 字节随机 → 43 字符 url-safe
        _db_execute(
            conn,
            "INSERT INTO web_invites (invite_token, role, max_uses, expires_at, note, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (token, role, max_uses,
             expires_at.isoformat() if hasattr(expires_at, "isoformat") else expires_at,
             note, created_by),
        )
        conn.commit()
        return token
    finally:
        if not is_mysql:
            conn.close()


def fetch_invite(token: str) -> Optional[dict]:
    """查 invite. 返 None 表示不存在/已撤销/已过期/已用完."""
    from datetime import datetime
    invite = _fetchone_dict(
        "SELECT invite_id, invite_token, role, max_uses, used_count, expires_at, revoked "
        "FROM web_invites WHERE invite_token = ?",
        (token,),
    )
    if not invite or invite["revoked"]:
        return None
    if invite["used_count"] >= invite["max_uses"]:
        return None
    ea = invite.get("expires_at")
    if ea and isinstance(ea, str):
        try:
            ea_dt = datetime.fromisoformat(ea.replace(" ", "T") if "T" not in ea else ea)
            if ea_dt < datetime.utcnow():
                return None
        except (ValueError, TypeError):
            pass
    return invite


def consume_invite(token: str) -> bool:
    """兑换 invite (used_count+=1). 返 True 表示成功."""
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        cur = _db_execute(
            conn,
            "UPDATE web_invites SET used_count = used_count + 1 "
            "WHERE invite_token = ? AND revoked = 0 AND used_count < max_uses",
            (token,),
        )
        conn.commit()
        # SQLite/MySQL rowcount 兼容
        return (cur.rowcount or 0) > 0
    finally:
        if not is_mysql:
            conn.close()


def list_invites() -> list[dict]:
    """dad 后台列所有 invite. 双后端统一 (Sprint 26081004 修 list_invites tuple path bug)."""
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        cur = _db_execute(
            conn,
            "SELECT invite_id, invite_token, role, max_uses, used_count, "
            "expires_at, created_at, revoked, note "
            "FROM web_invites ORDER BY invite_id DESC",
            (),
        )
        rows = cur.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], dict):
            return list(rows)  # DictCursor
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        if not is_mysql:
            conn.close()


def revoke_invite(invite_id: int) -> None:
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(conn, "UPDATE web_invites SET revoked = 1 WHERE invite_id = ?", (invite_id,))
        conn.commit()
    finally:
        if not is_mysql:
            conn.close()


def list_users() -> list[dict]:
    """列 web_users. 双后端统一用 description + zip 转 dict (Sprint v3.3 修)."""
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        cur = _db_execute(
            conn,
            "SELECT user_id, username, display_name, role, avatar_letter, "
            "must_change_password, last_login_at, revoked, created_at "
            "FROM web_users ORDER BY user_id",
            (),
        )
        rows = cur.fetchall()
        if not rows:
            return []
        if isinstance(rows[0], dict):
            return list(rows)  # DictCursor
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    finally:
        if not is_mysql:
            conn.close()


# ─── FastAPI Dependencies ──────────────────────────────────────────
ROLE_PERMISSIONS = {
    "dad": {
        "practice", "prepare", "report", "achievements", "badges",
        "config", "praise", "config_users", "admin",
    },
    "student": {"practice", "prepare", "report", "achievements", "badges"},
    "family": {"report", "achievements", "badges"},
    "teacher": {"practice", "prepare", "report", "achievements", "badges"},
    "reviewer": {"report", "achievements", "badges"},
}

ROLE_LABELS = {
    "dad": "管理员",
    "student": "学习者",
    "family": "家人",
    "teacher": "老师",
    "reviewer": "审核员",
}


async def get_current_user(request: Request) -> Optional[dict]:
    """返 None (未登录) 或 user dict."""
    sig = request.cookies.get(COOKIE_NAME)
    if not sig:
        return None
    session = load_session_cookie(sig)
    if not session:
        return None
    user = fetch_user_by_id(session["user_id"])
    if not user or user["revoked"]:
        return None
    # session_version 校验: 老 cookie sv < 当前 sv → 失效 (dad 踢出)
    if session.get("sv", 0) != user["session_version"]:
        return None
    return user


async def require_login(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        # 302 → /login (FastAPI 用 HTTPException 302 + Location header)
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


def require_role(*roles: str):
    """Dependency factory: 仅允许指定 role 通过."""
    async def _dependency(request: Request) -> dict:
        user = await require_login(request)
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return _dependency


def check_dad_pin(pin: str) -> bool:
    """dad (root) PIN 守门. 沿用 settings.dad_pin, 不走 web_users 体系."""
    stored = db.get_setting("dad_pin") or ""
    return bool(pin) and bool(stored) and (pin == stored)


# ─── PIN 页面解锁 cookie (Sprint 26082901: PIN 残留 URL 修复) ───────
# dad 报: 用 PIN 进 /config/users 时 PIN 留 URL (?pin=0905). 改用:
#   前端 POST /config/users/verify → 服务端验 PIN → 种 "已验证" 签名 cookie
#   → 302/303 清 URL. cookie 存的是签名标记 (非 PIN 明文), 窃 cookie 只拿
#   到本网关短时访问, 不能解出 PIN 跨服务复用.
PIN_OK_COOKIE_NAME = "dizical_pin_ok"
PIN_OK_COOKIE_MAX_AGE = 120 * 60  # 120 分钟 (管理页解锁凭据, 比 30 天 session 短)


def make_pin_ok_cookie() -> str:
    """签发 HttpOnly '已验证' cookie 值. 不含 PIN, 只含 scope+exp 签名."""
    import time as _t
    return _cookie_sign({"scope": "dad_pin", "exp": int(_t.time()) + PIN_OK_COOKIE_MAX_AGE})


def load_pin_ok_cookie(request: Request) -> bool:
    """读并验签 pin_ok cookie, 有效返 True. 有效期+签名双校验."""
    raw = request.cookies.get(PIN_OK_COOKIE_NAME) or ""
    if not raw:
        return False
    payload = _cookie_verify(raw)
    return bool(payload and payload.get("scope") == "dad_pin")


def set_pin_ok_cookie(response: Response) -> None:
    response.set_cookie(
        key=PIN_OK_COOKIE_NAME,
        value=make_pin_ok_cookie(),
        max_age=PIN_OK_COOKIE_MAX_AGE,
        httponly=True,
        secure=not INSECURE_COOKIE,  # iPad LAN http 必须 not, 否则静默丢弃
        samesite="lax",
        path="/config",
    )


def clear_pin_ok_cookie(response: Response) -> None:
    response.delete_cookie(PIN_OK_COOKIE_NAME, path="/config")


def generate_random_password(length: int = 12) -> str:
    """生成初始密码. 排除 0/O/1/l 等易混字符."""
    import secrets
    import string
    # 字母 (大写小写) + 数字, 排除易混字符
    chars = "".join(c for c in (string.ascii_letters + string.digits)
                    if c not in "0O1lI")
    return "".join(secrets.choice(chars) for _ in range(length))


# 公开导出
__all__ = [
    "hash_password", "verify_password", "MIN_PASSWORD_LEN",
    "make_session_cookie", "load_session_cookie", "set_session_cookie",
    "clear_session_cookie", "COOKIE_NAME", "COOKIE_MAX_AGE",
    "make_mp_session_token", "load_mp_session_token", "get_mp_current_user",
    "fetch_user_by_username", "get_user_by_username", "fetch_user_by_id", "update_last_login",
    "create_user", "update_password", "update_role", "revoke_user",
    "bump_session_version", "list_users",
    "is_user_locked", "increment_login_failed", "reset_login_failed",
    "LOGIN_MAX_FAILED", "LOGIN_LOCKOUT_SECONDS",
    "create_invite", "fetch_invite", "consume_invite", "list_invites", "revoke_invite",
    "get_current_user", "require_login", "require_role",
    "ROLE_PERMISSIONS", "ROLE_LABELS",
    "check_dad_pin", "generate_random_password",
    "make_pin_ok_cookie", "load_pin_ok_cookie", "set_pin_ok_cookie",
    "clear_pin_ok_cookie", "PIN_OK_COOKIE_NAME", "PIN_OK_COOKIE_MAX_AGE",
]
