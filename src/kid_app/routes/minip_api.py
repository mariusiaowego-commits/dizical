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
