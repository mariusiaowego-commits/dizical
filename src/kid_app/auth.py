"""
Web 用户体系核心 (Sprint 26081003).

- argon2 密码哈希 (pyproject 已有 argon2-cffi)
- itsdangerous 签名 cookie (pyproject 已有)
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
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.database import db

# ─── 密码哈希 ──────────────────────────────────────────
_ph = PasswordHasher()  # m=65536, t=3, p=4 (OWASP 推荐)

MIN_PASSWORD_LEN = 8


def hash_password(plain: str) -> str:
    """argon2 hash. raise ValueError if 长度不足."""
    if len(plain) < MIN_PASSWORD_LEN:
        raise ValueError(f"密码至少 {MIN_PASSWORD_LEN} 位")
    return _ph.hash(plain)


def verify_password(hash_str: str, plain: str) -> bool:
    """校验密码. 返 True/False (不抛)."""
    if not hash_str or not plain:
        return False
    try:
        _ph.verify(hash_str, plain)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


# ─── Cookie 签名 ────────────────────────────────────────
SESSION_SECRET = os.getenv("DIZICAL_SESSION_SECRET", "dev-fallback-please-set-DIZICAL_SESSION_SECRET")
SESSION_SALT = "dizical-web-session-v1"
COOKIE_NAME = "dizical_session"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 天
INSECURE_COOKIE = os.getenv("DIZICAL_INSECURE_COOKIE", "0") == "1"

_serializer = URLSafeTimedSerializer(SESSION_SECRET, salt=SESSION_SALT)


def make_session_cookie(user_id: int, role: str, session_version: int) -> str:
    return _serializer.dumps({"user_id": user_id, "role": role, "sv": session_version})


def load_session_cookie(raw: str) -> Optional[dict]:
    """校验签名 + 过期. 返 None 表示无效/过期/篡改."""
    if not raw:
        return None
    try:
        return _serializer.loads(raw, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


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
    """单行查询, 返 dict 或 None. 双后端兼容."""
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        cur = _db_execute(conn, sql, params)
        row = cur.fetchone()
        if not row:
            return None
        if is_mysql:
            # MySQL DictCursor 返 dict, 但为安全起见强转
            return dict(row) if not isinstance(row, dict) else row
        # SQLite tuple → dict (需要 column names)
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    finally:
        if not is_mysql:
            conn.close()


def fetch_user_by_username(username: str) -> Optional[dict]:
    return _fetchone_dict(
        "SELECT user_id, username, display_name, password_hash, role, avatar_letter, "
        "must_change_password, session_version, revoked "
        "FROM web_users WHERE username = ?",
        (username,),
    )


def fetch_user_by_id(user_id: int) -> Optional[dict]:
    return _fetchone_dict(
        "SELECT user_id, username, display_name, password_hash, role, avatar_letter, "
        "must_change_password, session_version, revoked "
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


def update_password(user_id: int, new_hash: str) -> None:
    from src.db_adapter import get_conn
    conn, is_mysql = get_conn()
    try:
        _db_execute(
            conn,
            "UPDATE web_users SET password_hash = ?, must_change_password = 0 "
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


def list_users() -> list[dict]:
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
        if is_mysql:
            return list(rows)
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
}

ROLE_LABELS = {
    "dad": "管理员",
    "student": "学习者",
    "family": "家人",
    "teacher": "老师",
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
    """Dependency factory:  仅允许指定 role 通过."""

    async def dep(request: Request) -> dict:
        user = await require_login(request)
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user

    return dep


def check_dad_pin(pin: str) -> bool:
    """dad (root) PIN 守门. 沿用 settings.dad_pin, 不走 web_users 体系."""
    stored = db.get_setting("dad_pin") or ""
    return bool(pin) and bool(stored) and (pin == stored)


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
    "fetch_user_by_username", "fetch_user_by_id", "update_last_login",
    "create_user", "update_password", "update_role", "revoke_user",
    "bump_session_version", "list_users",
    "get_current_user", "require_login", "require_role",
    "ROLE_PERMISSIONS", "ROLE_LABELS",
    "check_dad_pin", "generate_random_password",
]