"""
minip (微信小程序) 专用 API 端点。

这些端点只给小程序用，不影响 dizical 现有功能。
kid_app 主仓只新增，不改现有逻辑。

2026-06-18: dizical-minip 项目初始化。
"""
import datetime as dt
import json
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.database import db
from src import db_adapter  # fix/achievements-mysql-conn (2026-07-24): 跨后端 SQL 适配

router = APIRouter()

# PIN 失败计数持久化 constants
PIN_COOLDOWN_SEC = 60
PIN_MAX_FAILS = 3


@router.get("/api/streak")
def api_streak():
    """返回当前连续打卡天数。

    从昨天往前数，连续每天有练习的天数。
    今天没练不影响计数（跟 kid_app Web 版 streak_days() 逻辑一致）。
    """
    today = dt.date.today()
    days = 0
    d = today - dt.timedelta(days=1)  # 从昨天开始，不要求今天必须练
    for _ in range(365):
        p = db.get_daily_practice(d)
        if p and p.get("total_minutes", 0) > 0:
            days += 1
            d -= dt.timedelta(days=1)
        else:
            break
    return JSONResponse({"streak": days})


@router.get("/api/today-stats")
def api_today_stats():
    """返回今日累计练习分钟数。"""
    today = dt.date.today()
    p = db.get_daily_practice(today)
    total = p.get("total_minutes", 0) if p else 0
    return JSONResponse({"date": today.isoformat(), "total_minutes": total})


@router.get("/api/lessons/upcoming")
def api_lessons_upcoming():
    """返回下一个未上课程（日期 + 时间 + 倒计时）。"""
    today = dt.date.today()
    lessons = db.get_lessons_by_month(today.year, today.month)

    # 如果本月没有更多课程，查下个月
    upcoming = None
    for lesson in lessons:
        if lesson.date >= today and lesson.status not in ("cancelled", "completed"):
            upcoming = lesson
            break

    if not upcoming:
        # 查下个月
        next_month = today.month + 1
        next_year = today.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        next_lessons = db.get_lessons_by_month(next_year, next_month)
        for lesson in next_lessons:
            if lesson.status not in ("cancelled", "completed"):
                upcoming = lesson
                break

    if not upcoming:
        return JSONResponse({"upcoming": None})

    scheduled_date = upcoming.date
    scheduled_time = upcoming.time
    delta = scheduled_date - today
    days = delta.days

    if days > 0:
        countdown = f"{days}天后"
    elif days == 0:
        countdown = "今天"
    else:
        countdown = "已过"

    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_names[scheduled_date.weekday()]

    return JSONResponse({
        "upcoming": {
            "id": upcoming.id,
            "date": scheduled_date.isoformat(),
            "time": str(scheduled_time),
            "status": upcoming.status,
            "countdown": countdown,
            "weekday": weekday,
            "fee": upcoming.fee,
            "notes": upcoming.notes or "",
        }
    })


from src.kid_app.auth import (
    verify_password,
    get_user_by_username,
    is_user_locked,
    increment_login_failed,
    reset_login_failed,
    update_last_login,
    make_mp_session_token,
)


@router.post("/api/minip/verify-pin")
async def api_minip_verify_pin(request: Request):
    """小程序登录验证（对接 web_users 账号体系，支持 dad/family/student/reviewer）。"""
    try:
        body = json.loads(await request.body())
    except Exception:
        body = {}
    username = (body.get("username") or "").strip()
    password = (body.get("password") or "").strip()

    if not username or not password:
        return JSONResponse({"ok": False, "error": "username_password_required"}, status_code=400)

    # 1. 查 web_users
    user = get_user_by_username(username)
    if not user or user.get("revoked"):
        return JSONResponse({"ok": False, "error": "wrong_credentials"}, status_code=401)

    # 2. 账号锁定检查
    if is_user_locked(user):
        return JSONResponse({"ok": False, "error": "account_locked"}, status_code=429)

    # 3. 校验密码 (scrypt)
    if not verify_password(user["password_hash"], password):
        increment_login_failed(user["user_id"])
        return JSONResponse({"ok": False, "error": "wrong_credentials"}, status_code=401)

    # 4. 登录成功，重置失败计数并更新登录时间
    reset_login_failed(user["user_id"])
    update_last_login(user["user_id"])

    role = user["role"]  # dad / family / student / reviewer
    display_name = user["display_name"]
    return JSONResponse({
        "ok": True,
        "role": role,
        "display_name": display_name,
        "user_id": user["user_id"],
        "mp_token": make_mp_session_token(
            user["user_id"], role, user.get("session_version", 0)
        ),
    })


# ─── 成就殿堂 API（小程序用）────────────────────────────────────────────
@router.get("/api/achievements")
def api_achievements():
    """返回所有成就（已解锁 + 未解锁），跟 /badges 页面数据一致。"""
    from src.achievement_definitions import calc_all, CalcResult
    from src.kid_app.app import get_badge_url

    conn = db._get_connection()

    # 1. calc_all() 计算所有成就状态
    results = calc_all()

    # 2. 读 achievements 表
    cur = db_adapter.execute(conn,
        "SELECT id, name, type, category, description, threshold, cond_text, "
        "unlock_strategy, achieved_at_override FROM achievements "
        "WHERE category IN ('milestone', '突破', '巅峰', '执着', '段位', '晋级', '神秘', 'seasonal') "
        "ORDER BY sort_order"
    )
    cols = [d[0] for d in cur.description]
    ach_rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    # 3. 构建 badge 列表（复用 badges_page 逻辑）
    # 2026-08-07 sprint 26080702: 提前查当前赛季, 拼 season_info 字符串
    from src.kid_app.app import _get_current_season
    current_season = _get_current_season(conn)
    badges = []
    for ach in ach_rows:
        aid = ach["id"]
        res = results.get(aid)
        if res is None:
            continue

        # 纪念章/表彰型徽章特殊处理
        is_commemorative = (
            ach.get("unlock_strategy") == "immediate"
            or ach.get("achieved_at_override")
        )
        if is_commemorative:
            cur = db_adapter.execute(conn, 
                "SELECT achieved, achieved_at FROM achievement_stats WHERE achievement_id=?",
                (aid,),
            )
            row = cur.fetchone()
            override_at = ach.get("achieved_at_override")
            if override_at:
                res = CalcResult(True, 1, None, override_at, f"考出时间: {override_at}")
            elif row and row[0] == "Y":
                res = CalcResult(True, 1, None, row[1] or None, "立即解锁")

        badges.append({
            "id": aid,
            "name": ach["name"],
            "typ": ach["type"],
            "group": ach["category"],
            "description": ach["description"],
            "condition": res.condition,
            "cond_text": ach.get("cond_text") or "",
            "achieved": res.achieved,
            "achieved_at": res.achieved_at,
            "badge_url": get_badge_url(aid),
            "unlock_strategy": ach.get("unlock_strategy") or "calc",
            # 2026-08-07 sprint 26080702: seasonal badge 显示赛季+累计次数
            "season_info": (
                f"当前第 {current_season.get('order', '?')} 赛季 ("
                f"{str(current_season.get('start', '?'))[:10].replace('-', '.')} - "
                f"{str(current_season.get('end', '?'))[:10].replace('-', '.')}), "
                f"已累计获取 {res.extra_count if res.extra_count is not None else 0} 次"
            ) if ach["category"] == "seasonal" and current_season else "",
        })

    # 4. 分离已解锁/未解锁
    # fix/achievements-mysql-conn: achieved_at 跨后端 str/date 混, sort + JSON 序列化前统一 str
    def _strify_achieved_at(badge):
        # fix/achievements-mysql-conn: MySQL datetime/date 不能直接 JSON 序列化
        out = dict(badge)
        if out.get("achieved_at") is not None:
            out["achieved_at"] = str(out["achieved_at"])
        return out

    unlocked = sorted(
        [_strify_achieved_at(b) for b in badges if b["achieved"]],
        key=lambda b: b["achieved_at"] or "",
        reverse=True,
    )
    locked = sorted(
        [_strify_achieved_at(b) for b in badges if not b["achieved"]],
        key=lambda b: b.get("condition") or "",
    )

    return JSONResponse({
        "ok": True,
        "unlocked": unlocked,
        "locked": locked,
        "total": len(badges),
        "earned": len(unlocked),
    })

# ─── 盲盒 API（小程序用）────────────────────────────────────────────
@router.get("/api/blindbox")
def api_blindbox():
    """返回每日打卡盲盒数据。"""
    from src.achievement_definitions import _to_date  # 跨后端 date 归一化
    today = dt.date.today()
    conn = db._get_connection()

    # 获取当前 stage
    cur = db_adapter.execute(conn,
        "SELECT stage_start, stage_end, stage_order "
        "FROM weekly_assignments "
        "WHERE stage_order = (SELECT MAX(stage_order) FROM weekly_assignments)"
    )
    stage_row = cur.fetchone()
    if not stage_row:
        return JSONResponse({"ok": True, "blindbox": None})

    # fix/achievements-mysql-conn: SQLite 返 str 'YYYY-MM-DD', MySQL 返 datetime.date
    # 用 _to_date 归一化, 后续计算跟 isin 判断都对
    stage_start = _to_date(stage_row[0])
    stage_end = _to_date(stage_row[1])
    if stage_start is None:
        return JSONResponse({"ok": True, "blindbox": None})
    stage_end = stage_end or today
    stage_day = (today - stage_start).days + 1
    if stage_day < 1:
        return JSONResponse({"ok": True, "blindbox": None})
    stage_day = min(stage_day, 7)

    # 本周打卡天数
    cur = db_adapter.execute(conn,
        "SELECT COUNT(DISTINCT date) FROM daily_practices WHERE date >= ? AND date <= ?",
        (stage_start.isoformat(), stage_end.isoformat()),
    )
    checkin_days = cur.fetchone()[0]

    # 每天打卡状态 (归一化到 set of date)
    checked_dates: set = set()
    cur = db_adapter.execute(conn,
        "SELECT DISTINCT date FROM daily_practices WHERE date >= ? AND date <= ?",
        (stage_start.isoformat(), stage_end.isoformat()),
    )
    for (d,) in cur.fetchall():
        nd = _to_date(d)
        if nd is not None:
            checked_dates.add(nd)

    days = []
    for day in range(1, stage_day + 1):
        day_date = stage_start + dt.timedelta(days=day - 1)
        is_checked = day_date in checked_dates  # set of date 跟 date 比
        days.append({
            "day": day,
            "date": day_date.isoformat(),
            "checked": is_checked,
            "is_today": day == stage_day,
        })

    # 主题信息
    active_theme = db.get_setting("active_blindbox_theme") or "default"

    return JSONResponse({
        "ok": True,
        "blindbox": {
            "theme": active_theme,
            "stage_start": stage_start.isoformat(),
            "stage_end": stage_end.isoformat(),
            "stage_day": stage_day,
            "checkin_days": checkin_days,
            "days": days,
        },
    })


# ─── 小程序 /api/lessons 别名 ─────────────────────────────────────────────
from src.kid_app.routes.config import api_lessons as _config_get_lessons


@router.get("/api/lessons")
def _minip_lessons(year: int, month: int):
    import asyncio
    return asyncio.run(_config_get_lessons(year=year, month=month))

# ─── 7-28 用户体系 (Phase B): admin whitelist approval ──────────────────────
# 设计: pin 路由分流
#   - 0905 + whitelist openid: 真数据 (strict 模式)
#   - 0905 + non-whitelist openid: 临时宽模式 (broad_seed, 自动加白)
#   - mp /api/minip/apply-access: 申请进入系统 (提交 openid + 邮箱或微信昵称)
#   - dad CLI/API 审批: GET /api/admin/whitelist/{pending,active} + POST {approve,deny} (Sprint 26081004 删 web UI, 改 CLI 查)

def _load_pending_whitelist():
    """返回待审批 openid 列表"""
    raw = db.get_setting("pending_whitelist") or "[]"
    try:
        result = json.loads(raw)
        if not isinstance(result, list):
            return []
        return result
    except (json.JSONDecodeError, TypeError):
        return []


def _save_pending_whitelist(items):
    db.set_setting("pending_whitelist", json.dumps(items, ensure_ascii=False))


def _load_whitelist():
    raw = db.get_setting("dad_whitelist") or "[]"
    try:
        result = json.loads(raw)
        if not isinstance(result, list):
            return []
        return result
    except (json.JSONDecodeError, TypeError):
        return []


def _save_whitelist(items):
    db.set_setting("dad_whitelist", json.dumps(items, ensure_ascii=False))


def _check_admin_pin(pin_input: str) -> bool:
    """dad web 后台管理专用 PIN 校验

    复用 dad_pin 设置. 不写失败计数 (只读 admin 操作).
    """
    stored = db.get_setting("dad_pin") or ""
    return bool(stored) and pin_input == stored


@router.get("/api/admin/whitelist/pending")
def api_admin_whitelist_pending(pin: str = ""):
    """列出待审批 openid 申请. 需 PIN 验证."""
    if not _check_admin_pin(pin):
        return JSONResponse({"ok": False, "error": "wrong_admin_pin"}, status_code=401)
    return JSONResponse({"ok": True, "pending": _load_pending_whitelist()})


@router.get("/api/admin/whitelist/active")
def api_admin_whitelist_active(pin: str = ""):
    """列出当前已激活的 openid 白名单"""
    if not _check_admin_pin(pin):
        return JSONResponse({"ok": False, "error": "wrong_admin_pin"}, status_code=401)
    return JSONResponse({"ok": True, "active": _load_whitelist()})


@router.post("/api/admin/whitelist/approve")
async def api_admin_whitelist_approve(request: Request):
    """审批通过一个 openid, 移到 active 白名单.

    body: {pin: "0905", openid: "oXXX...", nickname: optional}
    """
    body = json.loads(await request.body())
    pin = body.get("pin", "")
    openid = body.get("openid", "").strip()
    nickname = body.get("nickname", "")

    if not _check_admin_pin(pin):
        return JSONResponse({"ok": False, "error": "wrong_admin_pin"}, status_code=401)
    if not openid:
        return JSONResponse({"ok": False, "error": "openid_required"}, status_code=400)

    # 从 pending 移除, 加 active
    pending = _load_pending_whitelist()
    pending = [p for p in pending if p.get("openid") != openid]
    _save_pending_whitelist(pending)

    active = _load_whitelist()
    if openid not in active:
        active.append(openid)
        _save_whitelist(active)

    return JSONResponse({"ok": True, "openid": openid, "nickname": nickname})


@router.post("/api/admin/whitelist/deny")
async def api_admin_whitelist_deny(request: Request):
    """拒绝一个申请, 从 pending 移除不加入 active"""
    body = json.loads(await request.body())
    pin = body.get("pin", "")
    openid = body.get("openid", "").strip()

    if not _check_admin_pin(pin):
        return JSONResponse({"ok": False, "error": "wrong_admin_pin"}, status_code=401)
    if not openid:
        return JSONResponse({"ok": False, "error": "openid_required"}, status_code=400)

    pending = _load_pending_whitelist()
    pending = [p for p in pending if p.get("openid") != openid]
    _save_pending_whitelist(pending)

    return JSONResponse({"ok": True, "openid": openid, "denied": True})


@router.post("/api/minip/apply-access")
async def api_minip_apply_access(request: Request):
    """mp 端: 提交申请进入系统. 上传 openid + 可选昵称/备注.

    走任何 PIN (甚至是错的也行, 防刷) 都能提交. 申请写到 pending_whitelist,
    等 dad 在 web /admin/whitelist 一键 approve.

    命中条件:
    - openid 必传
    - openid 不在 active whitelist (已经在白名单的请直接输 PIN=0905 进系统)
    """
    body = json.loads(await request.body())
    openid = body.get("openid", "").strip()
    nickname = body.get("nickname", "").strip() or ""
    note = body.get("note", "").strip() or ""

    if not openid:
        return JSONResponse({"ok": False, "error": "openid_required"}, status_code=400)

    # 已经在白名单, 不需要申请
    active = _load_whitelist()
    if openid in active:
        return JSONResponse({
            "ok": True,
            "status": "already_active",
            "message": "已激活账号, 请用 PIN 0905 直接登录"
        })

    # 已经申请过, 不重复
    pending = _load_pending_whitelist()
    if any(p.get("openid") == openid for p in pending):
        return JSONResponse({
            "ok": True,
            "status": "already_pending",
            "message": "你的申请在审批中, 请耐心等待"
        })

    # 写到 pending
    import datetime as _dt
    pending.append({
        "openid": openid,
        "nickname": nickname,
        "note": note,
        "applied_at": _dt.datetime.now().isoformat(timespec="seconds")
    })
    _save_pending_whitelist(pending)

    return JSONResponse({
        "ok": True,
        "status": "submitted",
        "message": "申请已提交, 等待 dad 审批"
    })


