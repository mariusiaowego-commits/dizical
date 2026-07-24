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


# ─── PIN 失败计数持久化（SQLite settings 表）──────────────────────────
def _pin_fail_key(openid: str) -> str:
    return f"pin_fail_count:{openid}"


def _get_pin_fails(openid: str) -> tuple:
    """返回 (count, first_attempt_ts)"""
    raw = db.get_setting(_pin_fail_key(openid))
    if not raw:
        return (0, 0.0)
    try:
        data = json.loads(raw)
        return (data.get("count", 0), data.get("first", 0.0))
    except (json.JSONDecodeError, TypeError):
        return (0, 0.0)


def _set_pin_fails(openid: str, count: int, first_ts: float):
    db.set_setting(_pin_fail_key(openid), json.dumps({"count": count, "first": first_ts}))


@router.post("/api/minip/verify-pin")
async def api_minip_verify_pin(request: Request):
    """小程序专用 PIN 验证（白名单 + 失败计数 + 冷却）。

    不改现有 /api/verify-pin 逻辑，这是 minip 专用的新端点。
    """
    body = json.loads(await request.body())
    pin = body.get("pin", "")
    openid = body.get("openid", "")

    # 1. 白名单校验
    whitelist_raw = db.get_setting("dad_whitelist") or "[]"
    try:
        whitelist = json.loads(whitelist_raw)
    except (json.JSONDecodeError, TypeError):
        whitelist = []

    if openid and openid not in whitelist:
        return JSONResponse({"ok": False, "error": "not_in_whitelist"}, status_code=403)

    # 2. 冷却检查（持久化到 SQLite）
    cnt, first = _get_pin_fails(openid)
    now = time.time()
    if cnt >= PIN_MAX_FAILS and (now - first) < PIN_COOLDOWN_SEC:
        retry_after = int(PIN_COOLDOWN_SEC - (now - first))
        return JSONResponse(
            {"ok": False, "error": "cooldown", "retry_after": retry_after},
            status_code=429,
        )
    if cnt >= PIN_MAX_FAILS and (now - first) >= PIN_COOLDOWN_SEC:
        _set_pin_fails(openid, 0, now)

    # 3. 比对 PIN
    stored_pin = db.get_setting("dad_pin") or ""
    if stored_pin and pin == stored_pin:
        _set_pin_fails(openid, 0, now)
        return JSONResponse({"ok": True, "role": "dad"})
    else:
        new_cnt = cnt + 1 if cnt > 0 else 1
        new_first = first if cnt > 0 else now
        _set_pin_fails(openid, new_cnt, new_first)
        return JSONResponse({"ok": False, "error": "wrong_pin"}, status_code=401)


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
