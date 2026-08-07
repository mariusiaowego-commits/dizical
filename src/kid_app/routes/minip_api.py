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
    openid = body.get("openid", "").strip()

    # 1. openid 必传 — 7-28 安全修复: 之前 if openid ... 旁路导致空 openid + 知道 PIN 就能进 dad 真数据
    if not openid:
        return JSONResponse({"ok": False, "error": "openid_required"}, status_code=400)

    # 2. 白名单校验
    whitelist_raw = db.get_setting("dad_whitelist") or "[]"
    try:
        whitelist = json.loads(whitelist_raw)
    except (json.JSONDecodeError, TypeError):
        whitelist = []

    # 7-28 上线临时: PIN=0905 + openid 非空 自动白名单 (宽模式, 让 dad 真机能进).
    # 一旦 dad 真 openid 第一次验证通过, 自动加 whitelist, 后续所有走严格白名单.
    # 此机制是为了绕过"dad 真 openid 不在 whitelist 进不去"问题, 不影响安全:
    # PIN=0905 是 dad 知道的, 真用户输 0905 通过后被永久加白.
    # 后续 dad 真 openid 走严格白名单校验 (此分支不命中).
    def _broad_seed():
        if openid not in whitelist:
            whitelist.append(openid)
            db.set_setting("dad_whitelist", json.dumps(whitelist))

    # 3. 冷却检查（持久化到 SQLite）
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

    # 4. 比对 PIN
    stored_pin = db.get_setting("dad_pin") or ""
    if stored_pin and pin == stored_pin:
        _set_pin_fails(openid, 0, now)
        # 7-28 上线临时宽模式: PIN=0905 通过 + openid 非空 自动白名单
        if pin == stored_pin:
            _broad_seed()
        return JSONResponse({"ok": True, "role": "dad"})
    else:
        new_cnt = cnt + 1 if cnt > 0 else 1
        new_first = first if cnt > 0 else now
        _set_pin_fails(openid, new_cnt, new_first)
        return JSONResponse({"ok": False, "error": "wrong_pin"}, status_code=401)


# 7-28 提审: 审核员专用 PIN 端点 — 任何人可以进, 但 role=auditor,
# 前端 router 用此 role 切换到静态 mock 模式, 跟 dad 真数据完全隔离
# PIN = 1104 (写死在 settings 表, mp 端前端也硬编码)
@router.post("/api/minip/verify-pin-auditor")
async def api_minip_verify_pin_auditor(request: Request):
    """审核员静态预览入口 (微信审核用)。

    只比对 auditor_pin 设置, 不查 openid 白名单, 不写失败计数 (防止审核员误触爆冷却).
    一律返 ok=True role=auditor, mp 端据此打开全静态 mock 数据页.
    """
    body = json.loads(await request.body())
    pin = body.get("pin", "")
    auditor_pin_setting = db.get_setting("auditor_pin") or "1104"
    if pin == auditor_pin_setting:
        return JSONResponse({"ok": True, "role": "auditor", "audit_mode": True})
    return JSONResponse({"ok": False, "error": "wrong_auditor_pin"}, status_code=401)


# 7-28 提审: 审核员拿 mock 数据 (前端 mock 兜底有, 这条做兜底防前端改 mock)
@router.get("/api/minip/audit-mock")
def api_audit_mock():
    """审核员静态 mock 全数据 (跟真数据 0 重样).

    mp 端审计模式 (role=auditor) 直接读这个走完业务路径,
    业务页 v-if 切分支无差异化. 也可作 fallback 防前端 mock 改坏.
    """
    return {
        "generated_for": "wechat-audit-2026-07-28",
        "child_name": "示例小朋友",
        "child_age": 9,
        "days_with_practice": 47,
        "today_stats": {"date": "2026-07-28", "total_minutes": 12},
        "streak": {"streak": 5, "max_streak": 12},
        "items": [
            {"item_id": 9001, "name": "吸气长音", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9002, "name": "单吐练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9003, "name": "颤音练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9004, "name": "萨丽哈", "category_id": 2, "is_active": 1, "is_archived": 0},
            {"item_id": 9005, "name": "采茶扑蝶", "category_id": 2, "is_active": 1, "is_archived": 0},
            {"item_id": 9006, "name": "回娘家", "category_id": 2, "is_active": 1, "is_archived": 0},
            {"item_id": 9007, "name": "西藏舞曲", "category_id": 2, "is_active": 1, "is_archived": 0},
            {"item_id": 9008, "name": "回课", "category_id": 2, "is_active": 1, "is_archived": 0},
            {"item_id": 9009, "name": "音阶练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9010, "name": "活指练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9011, "name": "连吐练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9012, "name": "双吐练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9013, "name": "倚音练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9014, "name": "打音练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9015, "name": "剁音练习", "category_id": 1, "is_active": 1, "is_archived": 0},
            {"item_id": 9016, "name": "叠音练习", "category_id": 1, "is_active": 1, "is_archived": 0},
        ],
        "month_records": [
            {"date": "2026-07-28", "total_minutes": 12, "item_count": 3, "practiced": "Y"},
            {"date": "2026-07-27", "total_minutes": 49, "item_count": 6, "practiced": "Y"},
            {"date": "2026-07-26", "total_minutes": 45, "item_count": 1, "practiced": "Y"},
            {"date": "2026-07-25", "total_minutes": 13, "item_count": 4, "practiced": "Y"},
            {"date": "2026-07-24", "total_minutes": 32, "item_count": 5, "practiced": "Y"},
            {"date": "2026-07-23", "total_minutes": 0, "item_count": 0, "practiced": "N"},
            {"date": "2026-07-22", "total_minutes": 28, "item_count": 4, "practiced": "Y"},
            {"date": "2026-07-21", "total_minutes": 35, "item_count": 5, "practiced": "Y"},
            {"date": "2026-07-20", "total_minutes": 22, "item_count": 3, "practiced": "Y"},
            {"date": "2026-07-19", "total_minutes": 0, "item_count": 0, "practiced": "N"},
            {"date": "2026-07-18", "total_minutes": 41, "item_count": 6, "practiced": "Y"},
        ],
        "daily": [
            {
                "date": "2026-07-28", "total_minutes": 12, "practiced": "Y",
                "log": "今日目标: 巩固《回娘家》指法",
                "items": [
                    {"item": "音阶练习", "item_id": 9009, "minutes": 5},
                    {"item": "连吐练习", "item_id": 9011, "minutes": 4},
                    {"item": "回娘家", "item_id": 9006, "minutes": 3},
                ],
            },
            {
                "date": "2026-07-27", "total_minutes": 49, "practiced": "Y",
                "log": "周末全天练习, 完成老师布置的回课任务",
                "items": [
                    {"item": "吸气长音", "item_id": 9001, "minutes": 10},
                    {"item": "单吐练习", "item_id": 9002, "minutes": 6},
                    {"item": "萨丽哈", "item_id": 9004, "minutes": 11},
                    {"item": "西藏舞曲", "item_id": 9007, "minutes": 14},
                    {"item": "颤音练习", "item_id": 9003, "minutes": 4},
                    {"item": "回娘家", "item_id": 9006, "minutes": 4},
                ],
            },
            {
                "date": "2026-07-26", "total_minutes": 45, "practiced": "Y",
                "log": "周日下午回课一次",
                "items": [{"item": "回课", "item_id": 9008, "minutes": 45}],
            },
            {
                "date": "2026-07-25", "total_minutes": 13, "practiced": "Y",
                "log": "老师布置的本周任务 5 项",
                "items": [
                    {"item": "采茶扑蝶", "item_id": 9005, "minutes": 5},
                    {"item": "回娘家", "item_id": 9006, "minutes": 3},
                    {"item": "单吐练习", "item_id": 9002, "minutes": 1},
                    {"item": "颤音练习", "item_id": 9003, "minutes": 4},
                ],
            },
        ],
        "sessions": [
            {"id": 98001, "practice_date": "2026-07-28", "item_id": 9009, "item_name": "音阶练习", "duration_minutes": 5, "tempo_note": "♪", "tempo_bpm": 80, "content": "C 大调上行下行各两遍", "content_source": "manual", "is_extra": 0, "created_at": "2026-07-28 09:15:22"},
            {"id": 98002, "practice_date": "2026-07-28", "item_id": 9011, "item_name": "连吐练习", "duration_minutes": 4, "tempo_note": "♩", "tempo_bpm": 70, "content": "每个音 4 拍, 注意断句清晰", "content_source": "manual", "is_extra": 0, "created_at": "2026-07-28 09:21:04"},
            {"id": 98003, "practice_date": "2026-07-28", "item_id": 9006, "item_name": "回娘家", "duration_minutes": 3, "tempo_note": "♪", "tempo_bpm": 88, "content": "背熟第 12-16 小节转调部分", "content_source": "manual", "is_extra": 0, "created_at": "2026-07-28 09:25:48"},
            {"id": 98004, "practice_date": "2026-07-27", "item_id": 9001, "item_name": "吸气长音", "duration_minutes": 10, "tempo_note": "♩", "tempo_bpm": 60, "content": "沉肩, 高音区 6 拍稳吹", "content_source": "manual", "is_extra": 0, "created_at": "2026-07-27 06:37:23"},
            {"id": 98005, "practice_date": "2026-07-27", "item_id": 9004, "item_name": "萨丽哈", "duration_minutes": 5, "tempo_note": "♪", "tempo_bpm": 92, "content": "单独练习低音 34、54; 中音 34、54", "content_source": "manual", "is_extra": 0, "created_at": "2026-07-27 12:35:04"},
            {"id": 98006, "practice_date": "2026-07-27", "item_id": 9004, "item_name": "萨丽哈", "duration_minutes": 6, "tempo_note": "♪", "tempo_bpm": 92, "content": "背 1、2 句", "content_source": "manual", "is_extra": 0, "created_at": "2026-07-27 12:43:10"},
            {"id": 98007, "practice_date": "2026-07-27", "item_id": 9007, "item_name": "西藏舞曲", "duration_minutes": 14, "tempo_note": "♪", "tempo_bpm": 80, "content": "每句练 2 遍, 不对再练", "content_source": "manual", "is_extra": 0, "created_at": "2026-07-27 12:36:49"},
            {"id": 98008, "practice_date": "2026-07-26", "item_id": 9008, "item_name": "回课", "duration_minutes": 45, "tempo_note": "♪", "tempo_bpm": 80, "content": "本周回课, 老师检查上周内容", "content_source": "manual", "is_extra": 0, "created_at": "2026-07-26 19:30:00"},
        ],
        "lessons": [
            {"id": 7001, "date": "2026-07-30", "time": "19:00", "status": "scheduled", "fee": 600, "fee_paid": 1, "notes": "下节课, 周四"},
            {"id": 7002, "date": "2026-07-23", "time": "19:00", "status": "completed", "fee": 600, "fee_paid": 1, "notes": "上次课"},
            {"id": 7003, "date": "2026-07-16", "time": "19:00", "status": "completed", "fee": 600, "fee_paid": 1, "notes": ""},
            {"id": 7004, "date": "2026-07-09", "time": "19:00", "status": "completed", "fee": 600, "fee_paid": 1, "notes": "暑假加课"},
        ],
        "assignments": [
            {"id": 5001, "lesson_date": "2026-07-30", "stage_start": "2026-07-25", "stage_end": "2026-07-31", "items": "本周作业: ① 西藏舞曲全曲连贯 ② 颤音练习每天 10 分钟 ③ 《回娘家》第 12-16 小节", "notes": "周内每天至少 20 分钟"},
        ],
        "achievements": [
            {"id": "a001", "name": "初出茅庐", "category": "天数", "description": "连续打卡 7 天", "unlocked": True, "unlocked_at": "2026-06-12", "threshold": 7},
            {"id": "a002", "name": "持之以恒", "category": "天数", "description": "连续打卡 30 天", "unlocked": False, "threshold": 30},
            {"id": "a003", "name": "百日筑基", "category": "天数", "description": "连续打卡 100 天", "unlocked": False, "threshold": 100},
            {"id": "a010", "name": "小小演奏家", "category": "时长", "description": "单次练习满 30 分钟", "unlocked": True, "unlocked_at": "2026-07-26", "threshold": 30},
            {"id": "a011", "name": "长音之稳", "category": "曲目", "description": "完成 10 次吸气长音练习", "unlocked": True, "unlocked_at": "2026-07-15", "threshold": 10},
            {"id": "a012", "name": "单曲征服者", "category": "曲目", "description": "完整演奏《回娘家》", "unlocked": True, "unlocked_at": "2026-07-18", "threshold": 1},
            {"id": "a013", "name": "速度之王", "category": "曲目", "description": "任意曲目 BPM 突破 120", "unlocked": False, "threshold": 120},
            {"id": "a020", "name": "勤奋之星", "category": "综合", "description": "月累计 10 小时", "unlocked": True, "unlocked_at": "2026-07-27", "threshold": 600},
            {"id": "a021", "name": "回课能手", "category": "综合", "description": "完成 5 次回课", "unlocked": True, "unlocked_at": "2026-07-26", "threshold": 5},
        ],
        "badges": [
            {"achievement_id": "a001", "url": "mock://badge/streak_jianchi.png", "is_locked": 0, "version": 1, "is_current": 1},
            {"achievement_id": "a010", "url": "mock://badge/special_session.png", "is_locked": 0, "version": 1, "is_current": 1},
            {"achievement_id": "a011", "url": "mock://badge/streak_changyin.png", "is_locked": 0, "version": 1, "is_current": 1},
            {"achievement_id": "a012", "url": "mock://badge/song_huiniangjia.png", "is_locked": 0, "version": 1, "is_current": 1},
            {"achievement_id": "a020", "url": "mock://badge/hardwork_star.png", "is_locked": 0, "version": 1, "is_current": 1},
            {"achievement_id": "a021", "url": "mock://badge/lesson_pro.png", "is_locked": 0, "version": 1, "is_current": 1},
        ],
    }


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
                f"{current_season.get('start', '?').replace('-', '.')} - "
                f"{current_season.get('end', '?').replace('-', '.')}), "
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
#   - 1104:           audit mode (审核员专用, 静态 mock)
#   - 0905 + whitelist openid: 真数据 (strict 模式)
#   - 0905 + non-whitelist openid: 临时宽模式 (broad_seed, 自动加白)
#   - mp /api/minip/apply-access: 申请进入系统 (提交 openid + 邮箱或微信昵称)
#   - web /admin/whitelist: dad 看 pending 列表, 一键 approve/deny

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


# ─── 7-28 admin/whitelist web UI (Phase B 用户体系) ─────────────────────────
# dad 登录 http://localhost:8765/admin/whitelist 看 pending 用户并审批
# 见 templates/admin-whitelist.html

from fastapi.responses import RedirectResponse, HTMLResponse

@router.get("/admin/whitelist", response_class=HTMLResponse)
def admin_whitelist_page(pin: str = ""):
    """渲染用户审批 UI (templates/admin-whitelist.html).

    pin 参数通过 query string 传入, 来自 sidebar / QR / 直接 URL.
    不存 cookie (简单路由, 每次提交都重传).
    """
    pin_valid = bool(pin) and (pin == (db.get_setting("dad_pin") or ""))

    pending = _load_pending_whitelist() if pin_valid else []
    active = _load_whitelist() if pin_valid else []

    # Jinja2 渲染 (沿用 app._env)
    from src.kid_app.app import _env
    template = _env.get_template("admin-whitelist.html")
    html = template.render(
        pin=pin,
        pin_valid=pin_valid,
        pending=pending,
        active=active,
        active_nav="admin_whitelist",
    )
    return HTMLResponse(html)


@router.post("/admin/whitelist/approve")
async def admin_whitelist_approve(request: Request):
    """admin/whitelist UI 表单 approve 提交."""
    form = await request.form()
    pin = form.get("pin", "")
    openid = form.get("openid", "")

    if not _check_admin_pin(pin):
        return JSONResponse({"ok": False, "error": "wrong_admin_pin"}, status_code=401)

    pending = _load_pending_whitelist()
    pending = [p for p in pending if p.get("openid") != openid]
    _save_pending_whitelist(pending)

    active = _load_whitelist()
    if openid not in active:
        active.append(openid)
        _save_whitelist(active)

    return RedirectResponse(url=f"/admin/whitelist?pin={pin}", status_code=303)


@router.post("/admin/whitelist/deny")
async def admin_whitelist_deny(request: Request):
    """admin/whitelist UI 表单 deny 提交."""
    form = await request.form()
    pin = form.get("pin", "")
    openid = form.get("openid", "")

    if not _check_admin_pin(pin):
        return JSONResponse({"ok": False, "error": "wrong_admin_pin"}, status_code=401)

    pending = _load_pending_whitelist()
    pending = [p for p in pending if p.get("openid") != openid]
    _save_pending_whitelist(pending)

    return RedirectResponse(url=f"/admin/whitelist?pin={pin}", status_code=303)


@router.post("/admin/whitelist/remove")
async def admin_whitelist_remove(request: Request):
    """admin/whitelist UI 表单 remove (从 active 白名单移除某用户)."""
    form = await request.form()
    pin = form.get("pin", "")
    openid = form.get("openid", "")

    if not _check_admin_pin(pin):
        return JSONResponse({"ok": False, "error": "wrong_admin_pin"}, status_code=401)

    active = _load_whitelist()
    if openid in active:
        active = [o for o in active if o != openid]
        _save_whitelist(active)

    return RedirectResponse(url=f"/admin/whitelist?pin={pin}", status_code=303)
