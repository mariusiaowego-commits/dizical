"""dizical 儿童版 Web 应用"""

import datetime as dt
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional, List, Tuple, Dict

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.database import db
from src import practice as practice_module
from src.kid_app.subject_info import get_subject_info
from src.kid_app.schemas import PracticeLogRequest  # PR-B: Pydantic 校验
from pydantic import ValidationError

# ─── App ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Bamboo Flute Practice")

# PR-D: 同 item + 同 minutes 5s 内防重窗口 (防双击 / 网络重传导致 2 条 session).
# 进程级 dict, 路由层 _dedup_practice_log() 入口检查; 不下到 middleware 改 body.
_DEDUP_WINDOW_SECONDS = 5
_dedup_cache: Dict[tuple, tuple] = {}


def _check_dedup(date: str, item_id: int, minutes: int,
                 tempo_bpm: int = 0, content: str = "",
                 practice_at: str = "") -> Optional[dict]:
    """5s 内 (date, item_id, minutes, tempo_bpm, content, practice_at) 重复 → 返回缓存 response JSON.

    2026-08-01 fix: 把 tempo_bpm / content / practice_at 加进 dedup key,
    解决 1 科目录 8 条 session 都被屏蔽的 bug (原 key 只看 minutes, 8 条同 5min 全算重复).
    副作用: 防双击/网络重传仍有效 (同一前端同一时刻连续 POST 仍被屏蔽).
    """
    if not date or not (item_id and minutes):
        return None
    key = (date, int(item_id), int(minutes), int(tempo_bpm or 0),
           content or "", practice_at or "")
    cached = _dedup_cache.get(key)
    if cached and (time.time() - cached[0]) < _DEDUP_WINDOW_SECONDS:
        return cached[1]
    return None


def _record_dedup(date: str, item_id: int, minutes: int, body_json: dict,
                   tempo_bpm: int = 0, content: str = "",
                   practice_at: str = "") -> None:
    """记录 (date, item_id, minutes, tempo_bpm, content, practice_at) → response JSON.
    2026-08-01 fix: key 扩展 (见 _check_dedup docstring)."""
    if not date or not (item_id and minutes):
        return
    key = (date, int(item_id), int(minutes), int(tempo_bpm or 0),
           content or "", practice_at or "")
    _dedup_cache[key] = (time.time(), body_json)
    if len(_dedup_cache) > 100:
        cutoff = time.time() - _DEDUP_WINDOW_SECONDS
        for k in list(_dedup_cache.keys()):
            if _dedup_cache[k][0] < cutoff:
                del _dedup_cache[k]


# CORS: web / Mac app 调 CloudRun 公网 HTTPS 时需要
# Phase 1 收紧: 只允许 dizical-prod-xxx 域名, spike 阶段先开
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # spike 阶段全开, Phase 1 改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health check (CloudRun 健康检查 + spike 验证) ──────────────────────
@app.get("/health")
def health():
    """健康检查: 验证 FastAPI 跑通, 数据库连接 OK"""
    db_status = "ok"
    db_error = None
    record_count = 0
    try:
        # 用 get_all_lessons 当 smoke test (业务方法, 验证 ORM + SQLite 都通)
        lessons = db.get_all_lessons()
        record_count = len(lessons)
    except Exception as e:
        db_status = "error"
        db_error = str(e)

    return {
        "status": "ok",
        "service": "dizical",
        "env": os.getenv("ENV", "unknown"),
        "database": db_status,
        "db_error": db_error,
        "lesson_count": record_count,
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
    }

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount uploads (assignment images, styled cards)
_uploads_path = _ROOT / "data" / "uploads"
_uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_path)), name="uploads")

# Mount reports (monthly practice report PNG)
_reports_path = _ROOT / "data" / "reports"
if _reports_path.exists():
    app.mount("/data/reports", StaticFiles(directory=str(_reports_path)), name="reports")

# ─── 模板渲染 ───────────────────────────────────────────────────────────────
from jinja2 import Environment, FileSystemLoader

_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))

def render(tpl, **kwargs):
    template = _env.get_template(tpl + ".html")
    return template.render(**kwargs)

# ─── 数据 helpers ───────────────────────────────────────────────────────────
def child_name():
    try:
        return db.get_setting("child_name") or "YoYo"
    except Exception:
        return "YoYo"


# ─── Badge URL cache (PR-B 2026-06-12, 取代 BADGE_URLS / BADGE_FILES dict) ──
# 设计: dict 写死是 wiki 5/21 踩坑的根因 (两处 dict 必须同步). PR-B 改读 DB,
# 加 60s cache (badge 集合稳定). 新 badge 走 badge_generator.commit_badge_to_db
# 末尾 _invalidate_badge_url_cache() 立即生效.

_BADGE_URL_CACHE: dict = {"ts": 0.0, "data": {}}
_BADGE_URL_CACHE_TTL = 60  # 秒


def _invalidate_badge_url_cache() -> None:
    """清 cache. badge_generator.commit_badge_to_db 成功后调, 让新 badge 立刻可见."""
    _BADGE_URL_CACHE["ts"] = 0.0
    _BADGE_URL_CACHE["data"] = {}


def _refresh_badge_url_cache() -> None:
    """从 achievement_badges 表刷一次 is_current=1 的全部 url."""
    with db._get_connection() as conn:
        # fix/achievements-mysql-conn (2026-07-24): MySQL conn 没 .execute() shortcut, 用 cursor
        cur = conn.cursor()
        cur.execute(
            "SELECT achievement_id, url FROM achievement_badges WHERE is_current = 1"
        )
        _BADGE_URL_CACHE["data"] = {row[0]: row[1] for row in cur.fetchall()}
        _BADGE_URL_CACHE["ts"] = time.time()


def get_badge_url(aid: str, default: str = "/static/badges/medal_badge.png") -> str:
    """返回当前生效的 badge url. 取代 BADGE_URLS / BADGE_FILES dict.

    Args:
        aid: achievement_id (e.g. "streak_7")
        default: cache miss 时的兜底图 (跟原 dict.get 行为一致)

    Returns:
        url 路径 (/static/badges/xxx.png) 或 default
    """
    now = time.time()
    if now - _BADGE_URL_CACHE["ts"] > _BADGE_URL_CACHE_TTL:
        _refresh_badge_url_cache()
    return _BADGE_URL_CACHE["data"].get(aid, default)

def week_start_of(today):
    return today - dt.timedelta(days=today.weekday())

def streak_days():
    """从昨天往前数，连续每天有练习的天数。今天没练不影响计数。"""
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
    return days

def total_practice_minutes():
    conn = db._get_connection()
    cur = conn.execute(
        "SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices WHERE date >= ?",
        (dt.date(2020, 1, 1).isoformat(),)
    )
    return cur.fetchone()[0]


def _calc_max_consecutive_streak():
    """计算历史最长连续练习天数（断掉后重新接上也能恢复）"""
    today = dt.date.today()
    practices = db.get_daily_practices_in_range(dt.date(2020, 1, 1), today)

    # 只遍历有练习的日期，而非逐日遍历整个时间范围
    practice_dates = sorted(
        p["date"] for p in practices if p.get("total_minutes", 0) > 0
    )

    if not practice_dates:
        return 0

    max_streak = 0
    cur_streak = 0
    prev_date = None

    for d in practice_dates:
        if prev_date is None:
            cur_streak = 1
        elif (d - prev_date).days == 1:
            cur_streak += 1
        else:
            cur_streak = 1
        max_streak = max(max_streak, cur_streak)
        prev_date = d

    return max_streak


def _calc_current_streak():
    """计算最近一次断掉之后的连续练习天数。
    从最后一次有练习的日期往前倒查，遇0即停。
    今天没练不影响——以昨天为终点计算。"""
    today = dt.date.today()
    practices = db.get_daily_practices_in_range(dt.date(2020, 1, 1), today)
    day_mins = {p["date"]: p.get("total_minutes", 0) for p in practices}

    if not day_mins:
        return 0

    # 从昨天开始往前倒查（今天可能没练）
    d = today - dt.timedelta(days=1)
    cur_streak = 0
    while d >= min(day_mins.keys()):
        if day_mins.get(d, 0) > 0:
            cur_streak += 1
            d -= dt.timedelta(days=1)
        else:
            break
    return cur_streak


def _calc_peak_week():
    """返回 (peak_mins, peak_label) peak_label='YYYY-MM-DD ~ YYYY-MM-DD'"""
    assignments = db.get_weekly_assignments_in_range(
        dt.date(2020, 1, 1), dt.date.today() + dt.timedelta(days=30)
    )
    if not assignments:
        return 0, ""

    best_mins = 0
    best_label = ""
    for a in assignments:
        ss = a.get("stage_start")
        se = a.get("stage_end")
        if not ss or not se:
            continue
        start = dt.date.fromisoformat(ss) if isinstance(ss, str) else ss
        end = dt.date.fromisoformat(se) if isinstance(se, str) else se
        practices = db.get_daily_practices_in_range(start, end)
        mins = sum(p.get("total_minutes", 0) for p in practices)
        if mins > best_mins:
            best_mins = mins
            best_label = f"{ss} ~ {se}"
    return best_mins, best_label


def _calc_peak_month():
    """返回 (peak_mins, peak_label) peak_label='YYYY年MM月'"""
    today = dt.date.today()
    start_year = 2020

    best_mins = 0
    best_label = ""
    for year in range(start_year, today.year + 2):
        for month in range(1, 13):
            if year == today.year and month > today.month:
                break
            if year == start_year and month < 1:
                continue
            sm = dt.date(year, month, 1)
            if month == 12:
                em = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
            else:
                em = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
            practices = db.get_daily_practices_in_range(sm, em)
            mins = sum(p.get("total_minutes", 0) for p in practices)
            if mins > best_mins:
                best_mins = mins
                best_label = f"{year}年{month}月"
    return best_mins, best_label


def _get_current_week_range():
    """返回当前周（基于最近的 weekly_assignment）的 stage_start, stage_end"""
    today = dt.date.today()
    # 找包含今天的 weekly_assignment
    assignments = db.get_weekly_assignments_in_range(
        today - dt.timedelta(days=30), today + dt.timedelta(days=30)
    )
    for a in assignments:
        ss = a.get("stage_start")
        se = a.get("stage_end")
        if not ss or not se:
            continue
        start = dt.date.fromisoformat(ss) if isinstance(ss, str) else ss
        end = dt.date.fromisoformat(se) if isinstance(se, str) else se
        if start <= today <= end:
            return start, end
    # fallback: calendar week
    ws = today - dt.timedelta(days=today.weekday())
    we = ws + dt.timedelta(days=6)
    return ws, we


def _week_progress():
    """本周练习进度：返回 (pct, text)"""
    start, end = _get_current_week_range()
    today = dt.date.today()
    # 不超出今天
    end = min(end, today)
    if end < start:
        return 0, "0/7 天"
    practices = db.get_daily_practices_in_range(start, end)
    days = len([p for p in practices if p.get("total_minutes", 0) > 0])
    goal = 7
    pct = min(int(days / goal * 100), 100)
    return pct, f"{days}/{goal} 天"


def _calc_yesterday_mins(days_ago: int = 1):
    d = dt.date.today() - dt.timedelta(days=days_ago)
    p = db.get_daily_practice(d)
    return p.get("total_minutes", 0) if p else 0


def _calc_total_all_time():
    """所有练习记录的总累计分钟数"""
    conn = db._get_connection()
    row = conn.execute("SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices").fetchone()
    return row[0] if row else 0


def _calc_week_peak():
    """历史单周日累计时长最高值（自然周）"""
    conn = db._get_connection()
    rows = conn.execute("""
        SELECT date, total_minutes FROM daily_practices
        WHERE total_minutes > 0
        ORDER BY date
    """).fetchall()
    if not rows:
        return 0
    # 按自然周聚合
    from collections import defaultdict
    week_totals = defaultdict(int)
    for d_str, mins in rows:
        d = dt.date.fromisoformat(d_str)
        # 该天所在自然周的周一
        monday = d - dt.timedelta(days=d.weekday())
        week_totals[monday] += mins
    return max(week_totals.values()) if week_totals else 0


def _calc_month_peak():
    """历史单月日累计时长最高值"""
    conn = db._get_connection()
    rows = conn.execute("""
        SELECT date, total_minutes FROM daily_practices
        WHERE total_minutes > 0
        ORDER BY date
    """).fetchall()
    if not rows:
        return 0
    from collections import defaultdict
    month_totals = defaultdict(int)
    for d_str, mins in rows:
        d = dt.date.fromisoformat(d_str)
        month_key = (d.year, d.month)
        month_totals[month_key] += mins
    return max(month_totals.values()) if month_totals else 0


def _calc_top_items(conn: sqlite3.Connection,
                    start: dt.date,
                    end: dt.date,
                    limit: int = 2) -> list[tuple[str, int]]:
    """指定日期范围内，按科目聚合取前N名"""
    cur = conn.execute(f"""
        SELECT pi.name, SUM(json_extract(je.value, '$.minutes')) as m
        FROM daily_practices dp, json_each(dp.items) je
        JOIN practice_items pi ON pi.item_id = json_extract(je.value, '$.item_id')
        WHERE dp.date >= ? AND dp.date <= ?
        AND pi.is_archived = 0
        GROUP BY pi.name ORDER BY m DESC LIMIT ?
    """, (start.isoformat(), end.isoformat(), limit))
    return [(r[0], int(r[1])) for r in cur.fetchall()]


def _calc_last_practice_top(limit: int = 2) -> dict:
    """最近一次有练习的TOP项目。

    返回 {date, top1_name, top1_mins, top2_name, top2_mins}
    date: 日期标签文字（昨天/今天/MM-DD）；无可用记录时 date="暂无"，name=""，mins=0
    """
    import sqlite3
    conn = db._get_connection()

    # 找最近一次有练习的日期
    row = conn.execute("""
        SELECT date FROM daily_practices
        WHERE total_minutes > 0
        ORDER BY date DESC LIMIT 1
    """).fetchone()
    if not row:
        return {"date": "暂无", "top1_name": "", "top1_mins": 0,
                "top2_name": "", "top2_mins": 0}

    d = dt.date.fromisoformat(row[0])
    items = _calc_top_items(conn, d, d, limit)  # [(name, mins), ...]

    # 日期标签
    today = dt.date.today()
    if d == today - dt.timedelta(days=1):
        date_label = "昨天"
    elif d == today:
        date_label = "今天"
    else:
        date_label = d.strftime("%m-%d")

    return {
        "date": date_label,
        "top1_name": items[0][0] if len(items) > 0 else "",
        "top1_mins": items[0][1] if len(items) > 0 else 0,
        "top2_name": items[1][0] if len(items) > 1 else "",
        "top2_mins": items[1][1] if len(items) > 1 else 0,
    }


def _calc_week_top(limit: int = 2) -> dict:
    """本周练习TOP项目。返回 {date, top1_name, top1_mins, top2_name, top2_mins}"""
    import sqlite3
    conn = db._get_connection()
    today = dt.date.today()
    ws = today - dt.timedelta(days=today.weekday())
    items = _calc_top_items(conn, ws, today, limit)
    return {
        "date": "本周",
        "top1_name": items[0][0] if len(items) > 0 else "",
        "top1_mins": items[0][1] if len(items) > 0 else 0,
        "top2_name": items[1][0] if len(items) > 1 else "",
        "top2_mins": items[1][1] if len(items) > 1 else 0,
    }


def _calc_month_top(limit: int = 2) -> dict:
    """本月练习TOP项目。返回 {date, top1_name, top1_mins, top2_name, top2_mins}"""
    import sqlite3
    conn = db._get_connection()
    today = dt.date.today()
    ms = dt.date(today.year, today.month, 1)
    items = _calc_top_items(conn, ms, today, limit)
    return {
        "date": f"{today.month}月",
        "top1_name": items[0][0] if len(items) > 0 else "",
        "top1_mins": items[0][1] if len(items) > 0 else 0,
        "top2_name": items[1][0] if len(items) > 1 else "",
        "top2_mins": items[1][1] if len(items) > 1 else 0,
    }


def _calc_week_mins_and_days():
    today = dt.date.today()
    ws = today - dt.timedelta(days=today.weekday())
    practices = db.get_daily_practices_in_range(ws, today)
    mins = sum(p.get("total_minutes", 0) for p in practices)
    days = len([p for p in practices if p.get("total_minutes", 0) > 0])
    return mins, days


def _calc_month_mins_and_days():
    today = dt.date.today()
    start = dt.date(today.year, today.month, 1)
    if today.month == 12:
        end = dt.date(today.year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        end = dt.date(today.year, today.month + 1, 1) - dt.timedelta(days=1)
    end = min(end, today)
    practices = db.get_daily_practices_in_range(start, end)
    mins = sum(p.get("total_minutes", 0) for p in practices)
    days = len([p for p in practices if p.get("total_minutes", 0) > 0])
    return mins, days


def _ring_diff(current, previous, unit="天", ref_period="上周"):
    """计算环比差异文字（自然中文）: (diff_text, is_positive)
    ref_period: 对比周期文字，默认"上周"；可传"4月"等上月名称
    """
    if previous == 0:
        return "", False
    diff = current - previous
    if diff == 0:
        return f"与{ref_period}持平", False
    direction = "多" if diff > 0 else "少"
    if unit == "分":
        return f"比{ref_period}{direction}{abs(diff)}分钟", diff > 0
    else:
        return f"比{ref_period}{direction}{abs(diff)}天", diff > 0


def _milestone_html(category: Optional[str] = None):
    """生成勋章展示区 HTML

    - category=None: 所有成就（/badges 页面用）
    - category='seasonal': 仅赛季型（achievements tab 的 card-milestones 用）
    - category='milestone': 仅里程碑型（成就殿堂用）

    milestone 类型：已解锁全部展示，未解锁只展示最接近达成的 1 个
    seasonal 类型：全部展示（按达成状态分组）
    """
    import src.practice as _pm

    conn = db._get_connection()

    # ── 统一 calc_all() ───────────────────────────────────────────
    from src.achievement_definitions import calc_all
    results = calc_all()   # dict[aid] → CalcResult

    # ── 读 achievements 表元数据 ──────────────────────────────────
    cur = conn.execute(
        "SELECT id, name, type, category, stat_logic, description, threshold, "
        "unlocked_template, placeholder, cond_text FROM achievements" +
        (" WHERE category = ?" if category else "") +
        " ORDER BY sort_order",
        ((category,) if category else ()))
    cols = [d[0] for d in cur.description]
    ach_rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    # ── 分离已解锁 / 未解锁 (PR-B: badge_url 改读 DB + cache 60s) ──
    unlocked_list = []
    locked_list = []   # (ratio, card_html)

    for ach in ach_rows:
        aid = ach["id"]
        res = results.get(aid)
        if res is None:
            continue

        # V2.6 (2026-06-16) feat/badge-achieved-at-override:
        # 纪念章/表彰型徽章不走 calc, 直接读 achievement_stats.achieved + achievements.achieved_at_override
        # 触发条件: (a) unlock_strategy='immediate' (PR #101), 或 (b) achieved_at_override 非 NULL
        from src.achievement_definitions import CalcResult
        is_commemorative = (ach.get("unlock_strategy") == "immediate" or ach.get("achieved_at_override"))
        if is_commemorative:
            cur.execute("SELECT achieved, achieved_at FROM achievement_stats WHERE achievement_id=?", (aid,))
            row = cur.fetchone()
            override_at = ach.get("achieved_at_override")
            if override_at:
                # 通用字段: 用表单填的时间戳 (含 grade 1-10 考出时间)
                res = CalcResult(True, 1, None, override_at, f"考出时间: {override_at}")
            elif row and row[0] == 'Y':
                # immediate: 读 stats 表
                res = CalcResult(True, 1, None, row[1] or None, "立即解锁")

        achieved = res.achieved
        cv = res.computed_value
        threshold = ach.get("threshold")
        badge_url = get_badge_url(aid)  # PR-B: 取代 BADGE_URLS.get(aid, ...)

        # seasonal 类型 ratio=achieved（不显示进度条）
        if threshold and threshold > 0 and cv is not None:
            ratio = cv / threshold if not achieved else 1.0
        elif achieved:
            ratio = 1.0
        else:
            ratio = 0.0

        # ── 过滤"日期型 seasonal 徽章"（card-milestones 仅展示当年内可解锁/已解锁）──
        # 规则：从 stat_logic 提取 exists_practice_on_YYYY_MM_DD 模式：
        #   1) 未解锁 + (y,mo,d) != (today.year,today.month,today.day) → 隐藏
        #      （只有当天能解锁；不是当天/不是那年都不展示）
        #   2) 已解锁 + 解锁年 != 今年 → 隐藏
        #      （去年 6-1 解锁的 lucky_61_2026，到 2027-01-01 起不再展示，
        #       避免列表里堆历年已解锁的节日徽章）
        # 总之：节日徽章只在解锁年（已解锁）或目标年（未解锁）的当月展示。
        if category == "seasonal":
            import re as _re
            from datetime import date as _date
            m = _re.search(r"exists_practice_on_(\d{4})_(\d{2})_(\d{2})", ach.get("stat_logic", ""))
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                today_d = _date.today()
                if not achieved:
                    # 未解锁：只在目标日期 == 当天才显示
                    if (y, mo, d) != (today_d.year, today_d.month, today_d.day):
                        continue
                else:
                    # 已解锁：只在解锁年内显示
                    if y != today_d.year:
                        continue

        card_html = _build_milestone_card(
            aid, ach["name"], ach["type"], ach["description"],
            badge_url, achieved, cv, threshold, res.condition, ach.get("cond_text") or ""
        )

        if achieved:
            unlocked_list.append(card_html)
        else:
            locked_list.append((ratio, card_html))

    # milestone: 未解锁只展示最接近的 1 个；seasonal: 展示全部未解锁
    nearest_html = ""
    if locked_list:
        locked_list.sort(key=lambda x: x[0], reverse=True)
        if category != "seasonal":   # milestone 只展示最接近的 1 个
            locked_list = locked_list[:1]
        nearest_html = "".join(html for _, html in locked_list)

    return "".join(unlocked_list) + nearest_html


def _build_milestone_card(ach_id, name, ach_type, desc, badge_url, achieved, cv, threshold, condition="", cond_text=""):
    """生成单个 milestone 卡片 HTML（对应 .b-card 结构，与 badges 页面一致）

    V2.2 (2026-06-15) feat/badge-cond-text: cond_text 字段独立, modal-cond 3 级 fallback:
    cond (calc) > cond_text (user/AI) > desc (zh_story fallback)
    """
    import html as _html
    state_cls = "unlocked" if achieved else "locked"
    locked_flag = "yes" if not achieved else "no"
    cond_safe = _html.escape(condition or "")
    desc_safe = _html.escape(desc or "")
    cond_text_safe = _html.escape(cond_text or "")

    # 徽章统一用原图，灰化由 CSS .b-card.locked .b-img { grayscale(1) } 处理
    card_badge_url = badge_url

    pill_html = f"<span class='b-tag {ach_type}'>{ach_type}</span>"
    lock_icon = "" if achieved else (
        "<img class='b-lock' src=\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23999'%3E%3Cpath d='M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2z'/%3E%3C/svg%3E\" alt='🔒'>"
    )
    return (
        f"<div class='b-card {state_cls}' "
        f"data-id='{_html.escape(ach_id)}' "
        f"data-name='{_html.escape(name)}' "
        f"data-tag='{_html.escape(ach_type)}' "
        f"data-aid='{_html.escape(ach_id)}' "
        f"data-cond=\"{cond_safe}\" "
        f"data-cond-text=\"{cond_text_safe}\" "
        f"data-desc=\"{desc_safe}\" "
        f"data-img='{_html.escape(card_badge_url)}' "
        f"data-locked='{locked_flag}' "
        f"onclick='openModal(this)'>"
        f"  <div class='b-img-wrap'><img class='b-img' src='{_html.escape(card_badge_url)}' alt='{_html.escape(name)}' onerror=\"this.style.display='none'\"></div>"
        f"  <div class='b-name'>{_html.escape(name)}</div>"
        f"  {pill_html}"
        f"  {lock_icon}"
        f"</div>"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 每日打卡盲盒 · 主题注册中心
# ═══════════════════════════════════════════════════════════════════════════
# 每个主题 = 1 个 dict 集 (IMAGES/NAMES/DESCS/CONDS) + 1 个 meta dict (title/tag/desc/cover)
# 加新主题: 1) 写新 *_<SLUG>_* 4 个 dict  2) THEMES[slug] = {...}  3) 准备 7 张图
# ═══════════════════════════════════════════════════════════════════════════

# ─── 主题 1: ok哥赶海（原版） ──────────────────────────────────────────────
OK_SEA_IMAGES = {
    1: "/static/badges/daily_checkin_1.png",
    2: "/static/badges/daily_checkin_2.png",
    3: "/static/badges/daily_checkin_3.png",
    4: "/static/badges/daily_checkin_4.png",
    5: "/static/badges/daily_checkin_5.png",
    6: "/static/badges/daily_checkin_6.png",
    7: "/static/badges/daily_checkin_7.png",
}

OK_SEA_NAMES = {
    1: "🐡 惊喜起点",
    2: "🦀️ 爆桶狂欢",
    3: "🐙 爆笑羁绊",
    4: "🐚 声音共鸣",
    5: "🌟 狂欢大奖",
    6: "🪼 最后高光",
    7: "🗺️ 终极神话",
}

OK_SEA_DESCS = {
    1: "ok哥每天赶海第一件事不是看潮水，是看桶——今天桶空着，大海准备了什么？他刚弯腰，一只粉色河豚\"噗\"地蹦进桶里，气得圆滚滚的，像个生气的汤圆。ok哥说：\"哟，这河豚气鼓鼓的，跟我周一早上不想起床的样子一模一样！\"你周一打卡，河豚就是你的开工信号——它虽然气鼓鼓的，但它来了，就说明大海今天给你留了惊喜！",
    2: "ok哥最爱的词就是\"爆桶\"——桶装满了叫爆桶，桶装太满了也叫爆桶，桶里跳出一只大螃蟹还叫爆桶。今天他从沙子里拽出一只拳头大的红螃蟹，螃蟹死活不肯松钳，一夹——正好夹住YoYo的笛梢！YoYo使劲拔笛子，螃蟹使劲夹笛子，ok哥在旁边不帮忙，光顾着喊：\"大货！大货！别动让我拍！\"你周二打卡，这只螃蟹就是你的——它夹着你的笛子不放，就像你坚持练笛不放弃一样！",
    3: "ok哥抓过无数海鲜，但章鱼是他一生的对手。上次他抓了一只，章鱼八条腿分别吸在他的帽子、眼镜、桶、YoYo的笛子上，还剩三条腿悠闲地给自己扇风。ok哥说：\"这哥们比我还能抓——它把我抓住了！\"你周三打卡，章鱼就是你的\"周中恶魔\"——练笛练到周三最累了，这只章鱼就像你的疲惫，缠着你不放，但你看ok哥笑成那样，就知道其实它也是你的开心果！",
    4: "赶海最浪漫的时刻不是抓到大货，是你在海边捡到一枚海螺，贴到耳朵上——\"呜——\"，里面好像藏着整片大海的声音。ok哥说：\"我赶海十几年，海螺听过无数，但没有一个像今天这枚——它里面传出来的不是海浪声，是笛声！\"他把海螺递给YoYo，YoYo贴到耳朵上，里面飘出了彩虹色的乐谱。你周四打卡，这枚极光海螺就是你的回声——你吹进去的每一个音符，大海都记住了！",
    5: "周五了！ok哥说：\"赶海一整周，今天该开大奖了！\"他一铲子下去，沙子里蹦出一个金灿灿的宝箱，打开一看——不是金币，不是珍珠，是一枚比脸还大的黄金海星和一本发光的乐谱！ok哥愣了一秒，然后对着镜头比了个\"OK\"：\"收货！比爆桶还爽！\"你周五打卡，放学了大解放，宝箱为你打开，这周最亮的奖励归你！",
    6: "ok哥赶海赶了一周，今晚他决定来点不一样的——夜赶海！手电筒一开，海面突然浮起一只半透明的魔鬼鱼，浑身发着梦幻紫光，像一片会飞的光。ok哥说：\"我赶海这么多年，夜光的见过不少，但会跟着笛声游的我头一回见！\"YoYo开始吹笛，魔鬼鱼真的跟着笛声的节奏游。你周六打卡，夜光魔鬼鱼为你亮起来——周末的夜晚，笛声和荧光交织，这是属于你的深海演唱会！",
    7: "ok哥换上了他的船长服——虽然这衣服他自己都忘了什么时候买的，但他说：\"大结局必须有仪式感！\"海浪突然退去，沙滩上浮现出一个蓝色光环，一条由海水聚成的小神龙从光环中腾空而起，嘴里叼着一个玻璃漂流瓶。ok哥说：\"我赶了一辈子海，今天终于赶到了龙！\"瓶子里面是一张金色的乐谱，是这周你吹过的所有曲子的终极合集。你周日打卡，一周完美收官，神龙亲自给你颁奖！",
}

OK_SEA_CONDS = {d: "完成今日练习即可解锁" for d in range(1, 8)}

# ─── 主题 2: 长发公主的冒险 ────────────────────────────────────────────────
RAPUNZEL_IMAGES = {
    1: "/static/badges/rapunzel_1.png",
    2: "/static/badges/rapunzel_2.png",
    3: "/static/badges/rapunzel_3.png",
    4: "/static/badges/rapunzel_4.png",
    5: "/static/badges/rapunzel_5.png",
    6: "/static/badges/rapunzel_6.png",
    7: "/static/badges/rapunzel_7.png",
}

RAPUNZEL_NAMES = {
    1: "🌅 塔窗之光",
    2: "🐿️ 松鼠朋友",
    3: "🌸 花园发现",
    4: "🎨 彩虹编织",
    5: "⛈️ 风雨挑战",
    6: "✨ 魔法时刻",
    7: "🚪 自由之门",
}

RAPUNZEL_DESCS = {
    1: "小公主每天在塔里练习用长发扫地，今天她抬起头，看到窗外有一朵粉色的小花。她深吸一口气，把长发甩出去——\"噗\"一声，长发缠住了花茎！她小心翼翼地拉回来，花瓣上的露珠在阳光下闪闪发光。小公主笑了：\"原来我的头发可以够到外面的世界！\"你周一打卡，就像小公主第一次用长发够到窗外的花，虽然只是小小的尝试，但已经迈出了第一步！",
    2: "一阵风吹过，一只小松鼠\"啪\"地掉在窗台上，吓得瑟瑟发抖。小公主赶紧把长发甩过去，松鼠抓住头发，像荡秋千一样飞进房间。松鼠抖了抖蓬松的尾巴，好奇地看着公主。公主摸摸它的头：\"别怕，我叫长发公主，你呢？\"松鼠\"吱吱\"叫了两声，好像在说\"谢谢你\"。你周二打卡，就像小公主救了松鼠，你的坚持帮助了需要帮助的朋友！",
    3: "小公主从窗户往下看，发现塔下有一片美丽的花园，开满了五颜六色的花。她灵机一动，把长发甩下去，\"噗噗噗\"——长发像绳子一样，把花朵一朵一朵拉上来！松鼠在旁边帮忙递花，房间瞬间变成了花园。公主开心地转圈，长发上的花朵像星星一样闪烁。你周三打卡，就像小公主发现了花园，你的努力正在把美好的事物带到你身边！",
    4: "小公主把长发分成几股，用花朵和藤蔓编织成彩色的绳子。她把绳子挂在窗边，阳光照进来——\"哇！\"整个房间出现了彩虹！松鼠兴奋地跳来跳去，用爪子去抓彩虹。公主笑着说：\"原来我的头发不只能扫地，还能编织彩虹！\"你周四打卡，就像小公主编织彩虹，你的坚持正在创造意想不到的美好！",
    5: "暴风雨来了！窗户被吹开，雨水灌进来，小松鼠和几只小鸟吓得缩在角落。小公主深吸一口气，把长发甩出去，像一把大伞一样罩住小动物们。风雨打在长发上，公主咬着牙撑住。雨停了，小动物们都安全，公主累得坐在地上，但笑得很开心。你周五打卡，就像小公主面对风雨，虽然很累，但你保护了重要的东西！",
    6: "深夜，月光从窗户照进来。小公主的长发突然开始发光——金色的光芒像星星一样闪烁！小动物们都醒了，围着公主看。公主把长发甩向天花板，光芒像烟花一样散开，照亮了整个房间。松鼠\"吱吱\"叫着，好像在说：\"好美啊！\"你周六打卡，就像小公主发现长发的秘密，你的坚持正在积累看不见的力量！",
    7: "小公主站在高塔的大门前，心跳得很快。她深吸一口气，推开门——阳光照进来，长发铺在地上，像一条金色的地毯。松鼠跳到她肩膀上，小鸟围着她飞。公主迈出第一步，踩在金色的长发上，走向外面的世界。她回头看了看高塔，笑了：\"谢谢你，我的头发，你让我有勇气走出这里。\"你周日打卡，就像小公主推开大门，一周的坚持让你有勇气走向新的世界！",
}

RAPUNZEL_CONDS = {d: "完成今日练习即可解锁" for d in range(1, 8)}

# ─── THEMES 注册中心 ──────────────────────────────────────────────────────
# 主题元信息: card title (前 emoji + 名称) / modal tag / 描述 / cover 图
THEMES = {
    "ok_sea": {
        "slug": "ok_sea",
        "title": "🎁 每日打卡盲盒",         # 卡片标题
        "tag": "突破",                     # modal 标签
        "desc": "ok哥赶海，每天一个小惊喜。",  # portal 描述
        "cover": "/static/badges/daily_checkin_5.png",  # portal 预览图
        "dicts": (OK_SEA_IMAGES, OK_SEA_NAMES, OK_SEA_DESCS, OK_SEA_CONDS),
    },
    "rapunzel": {
        "slug": "rapunzel",
        "title": "👸 长发公主盲盒",
        "tag": "成长",
        "desc": "小公主在高塔里每天用长发帮助小动物，逐渐获得勇气，最终走出高塔。",
        "cover": "/static/badges/rapunzel_5.png",
        "dicts": (RAPUNZEL_IMAGES, RAPUNZEL_NAMES, RAPUNZEL_DESCS, RAPUNZEL_CONDS),
    },
}

DEFAULT_THEME = "ok_sea"
ACTIVE_THEME_SETTING_KEY = "active_blindbox_theme"


def get_active_theme() -> dict:
    """从 settings 表读当前生效主题，缺失/未注册时回退 DEFAULT_THEME。"""
    try:
        slug = db.get_setting(ACTIVE_THEME_SETTING_KEY) or DEFAULT_THEME
    except Exception:
        slug = DEFAULT_THEME
    if slug not in THEMES:
        slug = DEFAULT_THEME
    return THEMES[slug]


def _daily_blindbox_html():
    """生成每日打卡盲盒卡片 HTML（主题由 settings['active_blindbox_theme'] 决定）"""
    conn = db._get_connection()
    today = dt.date.today()

    # 加载当前主题
    theme = get_active_theme()
    theme_meta = {"title": theme["title"], "tag": theme["tag"]}
    IMAGES, NAMES, DESCS, CONDS = theme["dicts"]

    # 获取当前stage
    cur = conn.execute("""
        SELECT stage_start, stage_end, stage_order
        FROM weekly_assignments
        WHERE stage_order = (SELECT MAX(stage_order) FROM weekly_assignments)
    """)
    stage_row = cur.fetchone()
    if not stage_row:
        return "", 0

    stage_start_str, stage_end_str, stage_order = stage_row
    if not stage_start_str:
        return "", 0
    # stage_end 为 NULL 时视为 today（当前 stage 尚未结束）
    stage_end_date = dt.date.fromisoformat(stage_end_str) if stage_end_str else today
    stage_start = dt.date.fromisoformat(stage_start_str)

    # 计算今天是stage的第几天（1-7）
    stage_day = (today - stage_start).days + 1
    if stage_day < 1:
        return "", 0  # stage 还没开始
    # 盲盒就 7 天 (图也只设计了 7 张), cap at 7
    # stage 已结束 (today > stage_end) 时, stage_day 仍显示 7, 表示"本周第 7 天"
    stage_day = min(stage_day, 7)

    # 计算本周打卡了几天
    cur = conn.execute("""
        SELECT COUNT(DISTINCT date)
        FROM daily_practices
        WHERE date >= ? AND date <= ?
    """"", (stage_start_str, stage_end_date.isoformat()))
    checkin_days = cur.fetchone()[0]

    # 查询每一天是否已打卡
    checked_days = set()
    cur = conn.execute("""
        SELECT DISTINCT date
        FROM daily_practices
        WHERE date >= ? AND date <= ?
    """"", (stage_start_str, stage_end_date.isoformat()))
    for row in cur.fetchall():
        checked_days.add(row[0])

    import html as _html

    # 生成所有badge的HTML
    badges_html = ""
    for day in range(1, stage_day + 1):
        day_date = stage_start + dt.timedelta(days=day - 1)
        day_date_str = day_date.isoformat()
        is_checked = day_date_str in checked_days
        is_today = day == stage_day

        image = IMAGES.get(day, "")
        name = NAMES.get(day, "")
        desc = DESCS.get(day, "")
        cond = CONDS.get(day, "")

        checked_class = "unlocked" if is_checked else "locked"
        today_class = "today" if is_today and not is_checked else ""
        locked_flag = "no" if is_checked else "yes"

        badges_html += f"""
        <div class="b-card {checked_class} {today_class}"
             data-id="daily_checkin_{day}"
             data-name="{_html.escape(name)}"
             data-tag="{_html.escape(theme_meta['tag'])}"
             data-cond="{_html.escape(cond)}"
             data-desc="{_html.escape(desc)}"
             data-img="{_html.escape(image)}"
             data-locked="{locked_flag}"
             onclick="openModal(this)">
          <div class="b-img-wrap"><img class="b-img" src="{image}" alt="{name}" onerror="this.style.display='none'"></div>
          <div class="b-name">第{day}天</div>
          {"<span class='b-lock'>🔒</span>" if not is_checked else ""}
        </div>
        """

    # 判断今天是否已打卡
    today_checked = today.isoformat() in checked_days

    html = f"""
    <div class="ac-card" id="card-daily-blindbox" data-theme="{theme['slug']}">
      <div class="blindbox-header">
        <span class="blindbox-title">{_html.escape(theme_meta['title'])}</span>
        <span class="blindbox-progress">{checkin_days}/7</span>
      </div>

      <div class="blindbox-stage-info">
        <span>Stage {stage_order} · 第{stage_day}天</span>
      </div>

      <div class="blindbox-badges-grid">
        {badges_html}
      </div>

      <div class="blindbox-hint">
        {"<span class='hint-unlocked'>✅ 今日已解锁</span>" if today_checked else "<span class='hint-locked'>🔒 完成今日练习解锁</span>"}
      </div>
    </div>
    """
    return html, checkin_days

# ─── API: 某日练习明细 ─────────────────────────────────────────────────────
# ─── API: 月份数据 (feat/month-chart) - 必须注册在 /api/practices/{date_str} 之前避免路由抢占
@app.get("/api/practices/monthly")
def api_practices_monthly(month: str):
    """返回指定自然月 (YYYY-MM) 的练习数据. 与 stage chart 同结构, 前端复用 SVG 渲染."""
    try:
        parts = month.split("-")
        view_year = int(parts[0])
        view_month = int(parts[1])
        if not (1 <= view_month <= 12) or view_year < 2000:
            raise ValueError
    except (IndexError, ValueError):
        return JSONResponse({"error": "month 格式必须是 YYYY-MM"}, status_code=400)

    today = dt.date.today()
    if (view_year, view_month) > (today.year, today.month):
        view_year, view_month = today.year, today.month

    month_start = dt.date(view_year, view_month, 1)
    if view_month == 12:
        month_end = dt.date(view_year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        month_end = dt.date(view_year, view_month + 1, 1) - dt.timedelta(days=1)

    # 当前月截止今天, 历史月画完整
    if view_year == today.year and view_month == today.month:
        end_date = today
    else:
        end_date = month_end

    dates_in_month = []
    cur = month_start
    while cur <= end_date:
        dates_in_month.append(cur.isoformat())
        cur += dt.timedelta(days=1)

    c = db._conn.cursor()
    rows = c.execute(
        "SELECT date, items FROM daily_practices WHERE date BETWEEN ? AND ?",
        (month_start.isoformat(), end_date.isoformat())
    ).fetchall()
    practices = {}
    for r in rows:
        practices[r[0]] = {"items": json.loads(r[1])}

    all_item_ids = set()
    for p in practices.values():
        for it in p.get("items", []):
            all_item_ids.add(it.get("item_id"))
    all_item_ids = sorted(all_item_ids)
    if not all_item_ids:
        return JSONResponse({
            "month": f"{view_year}-{view_month:02d}",
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "end_date": end_date.isoformat(),
            "dates": dates_in_month,
            "items": [],
            "data": {},
        })

    item_names = {}
    for iid in all_item_ids:
        nm = c.execute("SELECT name FROM practice_items WHERE item_id = ?", (iid,)).fetchone()
        item_names[iid] = nm[0] if nm else f"科目{iid}"

    data = {}
    for d in dates_in_month:
        data[d] = {}
        p = practices.get(d, {"items": []})
        item_map = {it.get("item_id"): it.get("minutes", 0) for it in p.get("items", [])}
        for iid in all_item_ids:
            data[d][iid] = item_map.get(iid, None)

    return JSONResponse({
        "month": f"{view_year}-{view_month:02d}",
        "month_start": month_start.isoformat(),
        "month_end": month_end.isoformat(),
        "end_date": end_date.isoformat(),
        "dates": dates_in_month,
        "items": [{"id": iid, "name": item_names[iid]} for iid in all_item_ids],
        "data": data,
    })


# ─── API: stage 列表 + stage 维 session 明细 (feat/stage-session-print) ─────
# 必须注册在 /api/practices/{date_str} 之前, 避免 "stages"/"stage-detail" 被当日期

def _iso_date_field(v) -> Optional[str]:
    """date/str/None → ISO 字符串 (JSON 安全)."""
    if v is None or v == "":
        return None
    if isinstance(v, dt.date) and not isinstance(v, dt.datetime):
        return v.isoformat()
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    return str(v)[:10]


def _build_stage_detail_payload(stage: dict) -> dict:
    """把 assignment row + sessions 聚合成打印页 payload."""
    stage_start = _iso_date_field(stage.get("stage_start"))
    stage_end = _iso_date_field(stage.get("stage_end"))
    if not stage_start:
        return {"error": "stage 缺少 stage_start"}
    today_s = dt.date.today().isoformat()
    effective_end = stage_end or today_s
    # 进行中 stage: 明细截止今天; 历史 stage: 用 stage_end
    end_for_sessions = min(effective_end, today_s) if stage_end is None or stage_end >= today_s else effective_end

    start_d = dt.date.fromisoformat(stage_start)
    end_d = dt.date.fromisoformat(end_for_sessions)
    sessions = db.get_practice_sessions_in_range(start_d, end_d)

    # by_item 聚合
    by_item_map = {}  # item_id -> {item_name, minutes, session_count}
    for s in sessions:
        iid = s.get("item_id")
        if iid is None:
            continue
        if iid not in by_item_map:
            by_item_map[iid] = {
                "item_id": iid,
                "item_name": s.get("item_name") or "未知科目",
                "minutes": 0,
                "session_count": 0,
            }
        by_item_map[iid]["minutes"] += int(s.get("duration_minutes") or 0)
        by_item_map[iid]["session_count"] += 1
        if s.get("item_name"):
            by_item_map[iid]["item_name"] = s["item_name"]

    by_item = sorted(by_item_map.values(), key=lambda x: (-x["minutes"], x["item_id"]))
    total_minutes = sum(x["minutes"] for x in by_item)
    practice_dates = sorted({s.get("practice_date") for s in sessions if s.get("practice_date")})

    # days: 按日 → 科目 → session (dad 拍板 A)
    days_map = {}  # date -> {item_id -> {meta, sessions[]}}
    item_order_in_day = {}
    for s in sessions:
        d = s.get("practice_date")
        if not d:
            continue
        if isinstance(d, dt.date):
            d = d.isoformat()
        else:
            d = str(d)[:10]
        iid = s.get("item_id")
        if d not in days_map:
            days_map[d] = {}
            item_order_in_day[d] = []
        if iid not in days_map[d]:
            days_map[d][iid] = {
                "item_id": iid,
                "item_name": s.get("item_name") or "未知科目",
                "minutes": 0,
                "sessions": [],
            }
            item_order_in_day[d].append(iid)
        row = {
            "id": s.get("id"),
            "started_at": s.get("started_at"),
            "duration_minutes": int(s.get("duration_minutes") or 0),
            "tempo_note": s.get("tempo_note") or "",
            "tempo_bpm": s.get("tempo_bpm") or 0,
            "content": s.get("content") or "",
            "content_source": s.get("content_source") or "",
            "is_extra": bool(s.get("is_extra")),
        }
        days_map[d][iid]["sessions"].append(row)
        days_map[d][iid]["minutes"] += row["duration_minutes"]
        if s.get("item_name"):
            days_map[d][iid]["item_name"] = s["item_name"]

    days = []
    for d in sorted(days_map.keys()):
        groups = []
        day_total = 0
        sess_n = 0
        for iid in item_order_in_day[d]:
            g = days_map[d][iid]
            groups.append(g)
            day_total += g["minutes"]
            sess_n += len(g["sessions"])
        days.append({
            "date": d,
            "total_minutes": day_total,
            "session_count": sess_n,
            "groups": groups,
        })

    # assignment 老师要求全文 (单独卡片)
    assign_items = []
    for it in (stage.get("items") or []):
        assign_items.append({
            "item_id": it.get("item_id"),
            "item": it.get("item") or it.get("item_name") or "未知",
            "metronome": it.get("metronome") or "",
            "requirements": it.get("requirements") or it.get("requirement") or "",
        })

    return {
        "ok": True,
        "stage_order": stage.get("stage_order"),
        "lesson_date": _iso_date_field(stage.get("lesson_date")),
        "stage_start": stage_start,
        "stage_end": stage_end,
        "effective_end": end_for_sessions,
        "notes": stage.get("notes") or "",
        "summary": {
            "total_minutes": total_minutes,
            "practice_days": len(practice_dates),
            "session_count": len(sessions),
            "item_count": len(by_item),
        },
        "assignment_items": assign_items,
        "by_item": by_item,
        "days": days,
    }


@app.get("/api/practices/stages")
def api_practices_stages():
    """历史 stage 列表 (打印页切换器用). 字段全字符串, JSON 安全."""
    stages = db.list_stages()
    out = []
    for s in stages:
        out.append({
            "id": s["id"],
            "stage_order": s.get("stage_order"),
            "lesson_date": _iso_date_field(s.get("lesson_date")),
            "stage_start": _iso_date_field(s.get("stage_start")),
            "stage_end": _iso_date_field(s.get("stage_end")),
            "item_count": s.get("item_count") or 0,
        })
    return JSONResponse({"ok": True, "count": len(out), "stages": out})


@app.get("/api/practices/stage-detail")
def api_practices_stage_detail(
    date: Optional[str] = None,
    stage_order: Optional[int] = None,
):
    """Stage 维 session 明细 (按日→科目→session). 打印页数据源.

    查询优先级: stage_order > date(所属 stage) > 今天所属 stage.
    """
    stage = None
    if stage_order is not None:
        stage = db.get_stage_by_order(int(stage_order))
        if not stage:
            return JSONResponse({"ok": False, "error": f"找不到 Stage {stage_order}"}, status_code=404)
    else:
        day_s = date
        if not day_s:
            day_s = dt.date.today().isoformat()
        try:
            day = dt.date.fromisoformat(day_s)
        except ValueError:
            return JSONResponse({"ok": False, "error": "date 格式必须 YYYY-MM-DD"}, status_code=400)
        stage = db.get_stage_containing_date(day)
        if not stage:
            return JSONResponse({"ok": False, "error": f"{day_s} 不在任何 stage 中"}, status_code=404)

    payload = _build_stage_detail_payload(stage)
    if payload.get("error"):
        return JSONResponse({"ok": False, "error": payload["error"]}, status_code=400)
    return JSONResponse(payload)


# ─── API: stage 维 report 图片 (sprint-26080103) ──────────────────────────────
# 走 hermes chat + FAL GPT Image 2, 跟月报 /api/practice-report/generate 同模式
# 落盘到 data/reports/stage-{order}-{timestamp}.png, 写 report_artifacts 表 (新表)


def _resolve_stage(stage_order: Optional[int], date: Optional[str]) -> Optional[dict]:
    """复用 api_practices_stage_detail 内部 stage 查询逻辑 (提取为共用 helper)."""
    if stage_order is not None:
        return db.get_stage_by_order(int(stage_order))
    day_s = date
    if not day_s:
        day_s = dt.date.today().isoformat()
    try:
        day = dt.date.fromisoformat(day_s)
    except ValueError:
        return None
    return db.get_stage_containing_date(day)


def _filter_payload_by_days(payload: dict, days_csv: Optional[str]) -> dict:
    """按 days CSV (逗号分隔 YYYY-MM-DD) 过滤 payload.days, 重算 summary / by_item."""
    if not days_csv:
        return payload
    keep = {d.strip() for d in days_csv.split(",") if d.strip()}
    if not keep:
        return payload
    days = [d for d in (payload.get("days") or []) if d.get("date") in keep]
    total = sum(int(d.get("total_minutes") or 0) for d in days)
    sess_n = sum(int(d.get("session_count") or 0) for d in days)
    item_map: dict = {}
    for d in days:
        for g in d.get("groups") or []:
            gid = g.get("item_id")
            if gid is None:
                continue
            if gid not in item_map:
                item_map[gid] = {
                    "item_id": gid,
                    "item_name": g.get("item_name") or "未知科目",
                    "minutes": 0,
                    "session_count": 0,
                }
            item_map[gid]["minutes"] += int(g.get("minutes") or 0)
            item_map[gid]["session_count"] += len(g.get("sessions") or [])
            if g.get("item_name"):
                item_map[gid]["item_name"] = g["item_name"]
    by_item = sorted(item_map.values(), key=lambda x: (-x["minutes"], x["item_id"]))
    payload["days"] = days
    payload["by_item"] = by_item
    payload["summary"] = {
        "total_minutes": total,
        "practice_days": len(days),
        "session_count": sess_n,
        "item_count": len(by_item),
    }
    return payload


@app.post("/api/practices/stage-image")
async def api_practices_stage_image(
    stage_order: Optional[int] = None,
    date: Optional[str] = None,
    days: Optional[str] = None,
):
    """生成 stage 维 report 图片 (SSE 流式状态).

    复用 _build_stage_detail_payload 的数据, 走 hermes + FAL GPT Image 2.
    days: 可选, "2026-07-01,2026-07-02,..." 过滤; 不传=全 stage 日子.
    落盘: data/reports/stage-{order}-{timestamp}.png
    写表: report_artifacts (kind='stage_image', ref_id=stage_order)
    """
    from src.report_templates import build_stage_image_prompt
    from src.database import db as _db  # noqa: F401  # 用 _db._get_connection() 写表

    stage = _resolve_stage(stage_order, date)
    if not stage:
        return JSONResponse(
            {"ok": False, "error": "找不到 stage (stage_order/date 都不在已有 stage 范围内)"},
            status_code=404,
        )
    payload = _build_stage_detail_payload(stage)
    if payload.get("error"):
        return JSONResponse({"ok": False, "error": payload["error"]}, status_code=400)
    payload = _filter_payload_by_days(payload, days)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    from fastapi.responses import StreamingResponse
    import json as _json
    import threading
    import queue as _q
    from datetime import datetime as _dt

    def _generate_stream():
        result_queue: "_q.Queue" = _q.Queue()

        def run_generation():
            try:
                result_queue.put(("status", "构建 prompt..."))
                prompt, aspect_ratio = build_stage_image_prompt(payload, child_name())
                result_queue.put(("status", f"Prompt 已构建（{len(prompt)} 字符）· {aspect_ratio}"))

                import subprocess
                import tempfile
                result_queue.put(("status", "正在调用 hermes + FAL gpt-image-2 生成图片，约需 30-60 秒..."))
                query = f"用 image_generate 工具生成图片，prompt 如下，aspect_ratio 用 {aspect_ratio}：\n\n{prompt}"
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    f.write(query)
                    tmp_path = f.name
                shell_cmd = f'hermes chat -q "$(cat {tmp_path})" -t image_gen --yolo -Q'
                proc = subprocess.Popen(
                    shell_cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=project_root, bufsize=1, text=True,
                )
                output_lines = []
                stdout = proc.stdout
                if stdout is not None:
                    for line in stdout:
                        line = line.rstrip()
                        output_lines.append(line)
                        result_queue.put(("output", line))
                proc.wait(timeout=120)
                output = "\n".join(output_lines)
                result_queue.put(("status", f"hermes 进程结束 (exit={proc.returncode})"))
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

                image_source = None
                for line in output.split("\n"):
                    line = line.strip()
                    if "MEDIA:" in line:
                        parts = line.split("MEDIA:")
                        if len(parts) > 1:
                            cand = parts[1].strip().split()[0]
                            if os.path.exists(cand):
                                image_source = cand
                                break
                    if line.startswith("http") and (".png" in line or ".jpg" in line or "fal" in line):
                        image_source = line
                        break
                    if line.startswith("/") and (line.endswith(".png") or line.endswith(".jpg")):
                        if os.path.exists(line):
                            image_source = line
                            break
                if not image_source:
                    result_queue.put(("error", f"未找到图片。hermes 输出:\n{output[:300]}"))
                    return

                result_queue.put(("status", "图片已获取，正在保存..."))
                report_dir = os.path.join(project_root, "data", "reports")
                os.makedirs(report_dir, exist_ok=True)
                ts = _dt.now().strftime("%Y%m%d-%H%M")
                order = payload.get("stage_order")
                filename = f"stage-{order}-{ts}.png"
                dest_path = os.path.join(report_dir, filename)

                import urllib.request
                if image_source.startswith("http"):
                    urllib.request.urlretrieve(image_source, dest_path)
                else:
                    import shutil
                    shutil.copy2(image_source, dest_path)

                result_queue.put(("status", "图片已保存，正在记录到数据库..."))
                with _db._get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "CREATE TABLE IF NOT EXISTS report_artifacts ("
                        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
                        " kind TEXT NOT NULL,"
                        " ref_id TEXT,"
                        " prompt TEXT,"
                        " image_path TEXT NOT NULL,"
                        " created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
                        ")"
                    )
                    cur.execute(
                        "INSERT INTO report_artifacts (kind, ref_id, prompt, image_path) VALUES (?, ?, ?, ?)",
                        ("stage_image", str(order) if order is not None else None, prompt, dest_path),
                    )
                    artifact_id = cur.lastrowid
                    conn.commit()

                result_queue.put(("done", {
                    "ok": True,
                    "report_id": artifact_id,
                    "image_path": dest_path,
                    "image_url": f"/api/practices/stage-image/file/{artifact_id}",
                    "stage_order": order,
                }))
            except Exception as e:
                result_queue.put(("error", str(e)))

        thread = threading.Thread(target=run_generation, daemon=True)
        thread.start()

        while True:
            try:
                msg_type, msg_data = result_queue.get(timeout=125)
            except _q.Empty:
                yield f"data: {_json.dumps({'type': 'error', 'message': '生成超时（125秒）'})}\n\n"
                break
            if msg_type == "status":
                yield f"data: {_json.dumps({'type': 'status', 'message': msg_data})}\n\n"
            elif msg_type == "output":
                yield f"data: {_json.dumps({'type': 'output', 'message': msg_data})}\n\n"
            elif msg_type == "error":
                yield f"data: {_json.dumps({'type': 'error', 'message': msg_data})}\n\n"
                break
            elif msg_type == "done":
                yield f"data: {_json.dumps({'type': 'done', 'data': msg_data})}\n\n"
                break

        thread.join(timeout=5)

    return StreamingResponse(
        _generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/practices/stage-image/file/{artifact_id}")
def api_stage_image_file(artifact_id: int):
    """返回 stage 维 report 图片文件 (跟月报 /api/practice-report/image/{id} 同款)."""
    from src.database import db as _db
    from fastapi.responses import FileResponse
    with _db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT image_path FROM report_artifacts WHERE id=?", (artifact_id,))
        row = cur.fetchone()
    if not row:
        return JSONResponse({"ok": False, "error": "report not found"}, status_code=404)
    image_path = row["image_path"] if isinstance(row, dict) else row[0]
    if not image_path or not os.path.exists(image_path):
        return JSONResponse({"ok": False, "error": "image file missing"}, status_code=404)
    return FileResponse(image_path, media_type="image/png")


@app.get("/api/practices/stage-image/history")
def api_stage_image_history(limit: int = 20):
    """查最近 N 个 stage 维 report artifact."""
    from src.database import db as _db
    with _db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, kind, ref_id, image_path, created_at FROM report_artifacts "
            "WHERE kind='stage_image' ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r["id"] if isinstance(r, dict) else r[0],
            "kind": r["kind"] if isinstance(r, dict) else r[1],
            "stage_order": r["ref_id"] if isinstance(r, dict) else r[2],
            "image_path": r["image_path"] if isinstance(r, dict) else r[3],
            "image_url": f"/api/practices/stage-image/file/{r['id'] if isinstance(r, dict) else r[0]}",
            "created_at": r["created_at"] if isinstance(r, dict) else r[4],
        })
    return JSONResponse({"ok": True, "artifacts": out})


@app.get("/api/practices/{date_str}")
def api_practice_day(date_str: str):
    """返回指定日期的练习明细 (兼容旧 items 字段, 2026-07-27 新增 sessions[])"""
    try:
        day = dt.date.fromisoformat(date_str)
    except ValueError:
        return JSONResponse({"error": "无效日期格式"}, status_code=400)
    practice = db.get_daily_practice(day)
    if not practice:
        return JSONResponse({
            "date": date_str, "id": None, "items": [], "total_minutes": 0,
            "log": "", "behavior_log": [], "sessions": [],
        })
    # 2026-07-27: 新增 sessions[] (按时间升序), 老客户端不读这个字段无影响
    sessions = db.get_practice_sessions(day)
    return JSONResponse({
        "date": date_str,
        "id": practice.get("id"),
        "items": practice.get("items", []),
        "total_minutes": practice.get("total_minutes", 0),
        "log": practice.get("log", ""),
        "behavior_log": practice.get("behavior_log", []),
        "sessions": sessions,
    })


# 2026-07-27: 新增 session 专用端点 (PRD: AI-PRD-练习计时细分内容-260727.md)
# ⚠️ 路由顺序: 静态路径 (/latest) 必须在变量路径 (/{date_str}) 之前
# 跟 sibling endpoint param parsing 7-23 教训一致 (PR #165)
@app.get("/api/practice-sessions/latest")
def api_practice_sessions_latest(item_id: int):
    """返回某 item_id 最近一次 session (Q1=B 速度默认值用).

    优先读 practice_items 冗余列 (last_tempo_note/last_tempo_bpm), 走 save 时同步,
    避免每次切科目查整张 sessions 表.
    """
    if not item_id:
        return JSONResponse({"ok": False, "error": "缺少 item_id"}, status_code=400)
    tempo = db.get_latest_session_tempo(int(item_id))
    if not tempo:
        return JSONResponse({
            "ok": True,
            "found": False,
            "item_id": item_id,
            "tempo_note": None,
            "tempo_bpm": None,
        })
    return JSONResponse({
        "ok": True,
        "found": True,
        "item_id": item_id,
        "tempo_note": tempo["last_tempo_note"],
        "tempo_bpm": tempo["last_tempo_bpm"],
        "last_session_at": tempo.get("last_session_at"),
    })


@app.get("/api/practice-sessions/{date_str}")
def api_practice_sessions(date_str: str, item_id: Optional[int] = None):
    """返回某日全部 session, 可选 ?item_id= 过滤. 顺序: created_at ASC."""
    try:
        day = dt.date.fromisoformat(date_str)
    except ValueError:
        return JSONResponse({"ok": False, "error": "无效日期格式"}, status_code=400)
    sessions = db.get_practice_sessions(day, item_id=item_id)
    return JSONResponse({
        "ok": True,
        "date": date_str,
        "count": len(sessions),
        "sessions": sessions,
    })


@app.delete("/api/practice-sessions/{session_id}")
async def api_delete_practice_session(session_id: int):
    """删单条 session, 重算 daily 汇总, 写 audit."""
    try:
        db.delete_practice_session(int(session_id))
        return JSONResponse({"ok": True, "session_id": session_id})
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=404)
    except Exception as e:
        import traceback, logging
        logging.error(f"API error: {e}\n{traceback.format_exc()}")
        return JSONResponse({"ok": False, "error": "服务器内部错误"}, status_code=500)


@app.put("/api/practice-sessions/{session_id}")
async def api_update_practice_session(session_id: int, request: Request):
    """更新 session 的 tempo/content (不改 duration)."""
    try:
        body = json.loads(await request.body())
        tempo_note = body.get("tempo_note")
        tempo_bpm = body.get("tempo_bpm")
        content = body.get("content")
        duration_minutes = body.get("duration_minutes")
        if not any([tempo_note, tempo_bpm is not None, content, duration_minutes is not None]):
            return JSONResponse({"ok": False, "error": "至少传一个字段"}, status_code=400)
        updated = db.update_practice_session(int(session_id), tempo_note=tempo_note, tempo_bpm=tempo_bpm, content=content, duration_minutes=duration_minutes)
        return JSONResponse({"ok": True, "session": updated})
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except Exception as e:
        import traceback, logging
        logging.error(f"API error: {e}\n{traceback.format_exc()}")
        return JSONResponse({"ok": False, "error": "服务器内部错误"}, status_code=500)


@app.get("/api/assignments/latest")
def api_assignments_latest(item_id: int):
    """返回某 item_id 最近一次 assignment 的 metronome 字段 (Q1=B fallback 用).

    metronome 字段格式: '♩=82' / '♪=85' (跟 weekly_assignments.items[].metronome 保持一致).
    解析失败 → 尝试宽松匹配 (从 '4/4 ♪=80, 2/4 ♪=69-80' 抓任何一个 ♪=N / ♩=N).
    全部失败 → 返回 found=False, 让前端走硬编码 ♪/80 fallback.

    2026-08-01 fix: 改自己倒序遍历 (DB 是升序), 同时返回 requirements 供前端 tooltip.
    """
    import re
    if not item_id:
        return JSONResponse({"ok": False, "error": "缺少 item_id"}, status_code=400)
    target_id = int(item_id)
    assignments = practice_module.query_assignments(weeks=8)
    # 倒序遍历 (DB 返的是升序, 最新在最后)
    for a in reversed(assignments):
        for it in a.get("items", []):
            if it.get("item_id") == target_id:
                metronome = (it.get("metronome") or "").strip()
                # 严格匹配 ♪=N / ♩=N
                m = re.match(r"^([♪♩♬♯])=(\d+)$", metronome)
                # 宽松匹配: 从长串里抓任一 ♪=N / ♩=N
                if not m:
                    m = re.search(r"([♪♩♬♯])=(\d+)", metronome)
                if m:
                    ld = a.get("lesson_date")
                    reqs = it.get("requirements") or it.get("requirement") or ""
                    return JSONResponse({
                        "ok": True,
                        "found": True,
                        "item_id": target_id,
                        "tempo_note": m.group(1),
                        "tempo_bpm": int(m.group(2)),
                        "lesson_date": str(ld) if ld else None,
                        "requirements": reqs,
                        "metronome_raw": metronome,
                    })
    return JSONResponse({
        "ok": True,
        "found": False,
        "item_id": target_id,
        "tempo_note": None,
        "tempo_bpm": None,
    })

@app.get("/api/practices/stage/{date_str}")
def api_practice_stage(date_str: str):
    """返回指定日期所在stage的练习数据，end_date=date_str（截止到点击日期）"""
    try:
        day = dt.date.fromisoformat(date_str)
    except ValueError:
        return JSONResponse({"error": "无效日期格式"}, status_code=400)

    c = db._conn.cursor()
    row = c.execute(
        """SELECT stage_start, stage_end FROM weekly_assignments
           WHERE ? >= stage_start
             AND (stage_end IS NULL OR ? <= stage_end)""",
        (date_str, date_str)
    ).fetchone()
    if not row:
        return JSONResponse({"error": "该日期不在任何stage中"}, status_code=404)

    stage_start, stage_end = row
    # 截止日期 = min(date_str, today)，不超过stage_end（stage_end为NULL则用today）
    today_str = dt.date.today().isoformat()
    effective_end = stage_end if stage_end else today_str
    end_date = min(date_str, today_str, effective_end)
    stage_end_actual = min(effective_end, today_str)

    # 生成日期列表：stage_start 到 end_date
    dates_in_stage = []
    cur = stage_start
    while cur <= stage_end_actual:
        cur_str = str(cur)
        if cur_str <= end_date:
            dates_in_stage.append(cur_str)
        cur = (dt.date.fromisoformat(cur) + dt.timedelta(days=1)).isoformat()

    # 收集所有练习数据（只查有数据的）
    practices = {}
    rows = c.execute(
        "SELECT date, items, total_minutes FROM daily_practices WHERE date BETWEEN ? AND ?",
        (stage_start, stage_end_actual)
    ).fetchall()
    for r in rows:
        practices[r[0]] = {"items": json.loads(r[1]), "total_minutes": r[2]}

    # 收集所有出现的科目（按item_id升序）
    all_item_ids = set()
    for p in practices.values():
        for it in p.get("items", []):
            all_item_ids.add(it.get("item_id"))
    all_item_ids = sorted(all_item_ids)
    if not all_item_ids:
        return JSONResponse({"dates": dates_in_stage, "items": [], "data": {}, "stage_start": stage_start, "stage_end": stage_end})

    # 按item_id获取科目名
    item_names = {}
    for iid in all_item_ids:
        nm = c.execute("SELECT name FROM practice_items WHERE item_id = ?", (iid,)).fetchone()
        item_names[iid] = nm[0] if nm else f"科目{iid}"

    # 构建每个日期每科目的分钟数矩阵
    data = {}
    for d in dates_in_stage:
        data[d] = {}
        p = practices.get(d, {"items": []})
        item_map = {it.get("item_id"): it.get("minutes", 0) for it in p.get("items", [])}
        for iid in all_item_ids:
            data[d][iid] = item_map.get(iid, None)

    return JSONResponse({
        "stage_start": stage_start,
        "stage_end": stage_end,
        "end_date": end_date,
        "dates": dates_in_stage,
        "items": [{"id": iid, "name": item_names[iid]} for iid in all_item_ids],
        "data": data,
    })


# ─── API: 练习项目列表 ─────────────────────────────────────────────────────
@app.get("/api/items")
def api_items(include_archived: bool = False):
    items = db.get_practice_items(active_only=True, include_archived=include_archived)
    categories = practice_module.get_categories()
    return JSONResponse({"items": items, "categories": categories})


# ─── API: 归档 / 取消归档练习项目 ───────────────────────────────────────────
@app.post("/api/items/{item_id}/archive")
async def api_archive_item(item_id: int):
    db.archive_practice_item(item_id)
    return JSONResponse({"ok": True})


@app.post("/api/items/{item_id}/unarchive")
async def api_unarchive_item(item_id: int):
    db.unarchive_practice_item(item_id)
    return JSONResponse({"ok": True})

# ─── API: 打卡 ─────────────────────────────────────────────────────────────
@app.post("/api/log")
async def api_log(request: Request):
    """PR-B: 用 PracticeLogRequest Pydantic 校验 + behavior_log dedup.

    双路径:
    - has_session_detail() == True  → save_practice_session_and_daily_summary (事务内写 behavior_log)
    - has_session_detail() == False → save_daily_practice (兼容旧前端, append_behavior_log)
    """
    try:
        req = PracticeLogRequest.model_validate(json.loads(await request.body()))
    except ValidationError as e:
        # Pydantic v2: e.errors() 含 ctx.error (ValueError), json 序列化失败.
        # 用 json(e.json()) 字符串避免 ValueError 落到 ctx.
        return JSONResponse(
            {"ok": False, "error": "请求参数校验失败", "details": json.loads(e.json())},
            status_code=422,
        )

    date = req.date
    item_name = req.item
    item_id = req.item_id
    minutes = req.minutes
    is_extra = req.is_extra
    practice_at = req.practice_at
    has_session_detail = req.has_session_detail()
    tempo_note = req.tempo_note or "♪"
    tempo_bpm = req.tempo_bpm or 80
    content = req.content or ""
    content_source = req.content_source
    behavior_entries = [e.model_dump() for e in req.behavior_log]
    log_note = req.log

    # 用 str(date) 统一 key 格式 (ISO YYYY-MM-DD)
    date_key = str(date)

    # PR-D: 5s dedup — 同 (date, item_id, minutes) 5s 内重复 → 返缓存, 不再写 session/daily.
    dedup_cached = _check_dedup(date_key, int(item_id), int(minutes),
                                  tempo_bpm, content, practice_at)
    if dedup_cached is not None:
        return JSONResponse(dedup_cached)

    try:
        if is_extra:
            # 2026-07-29 fix: 有 session detail 时只走 save_practice_session_and_daily_summary,
            # 避免 save_daily_practice + save_practice_session_and_daily_summary 双重合并 items
            if has_session_detail:
                s = db.save_practice_session_and_daily_summary(
                    date, item_name, int(item_id), minutes,
                    tempo_note, tempo_bpm, content, content_source,
                    practice_at=practice_at, is_extra=True,
                )
                # PR-B dedup: session 事务已写 behavior_log, 不再外部 append
                resp = {"ok": True, "total": minutes, "session": s}
                _record_dedup(date_key, int(item_id), int(minutes), resp,
                       tempo_bpm, content, practice_at)
                return JSONResponse(resp)
            # 旧路径: 无 session detail, 只走 save_daily_practice
            items = [{"item": item_name, "item_id": item_id, "minutes": minutes, "is_extra": True}]
            db.save_daily_practice(date, items, minutes, '',
                                   channel='kid_app', method='extra',
                                   practice_at=practice_at)
            for entry in behavior_entries:
                db.append_behavior_log(date, entry)
            resp_legacy = {"ok": True, "total": minutes}
            _record_dedup(date_key, int(item_id), int(minutes), resp_legacy,
                       tempo_bpm, content, practice_at)
            return JSONResponse(resp_legacy)

        # 正常打卡路径
        if has_session_detail:
            # 新路径: 写 session + 同步 daily + 写 audit + 更新冗余列 (整事务)
            s = db.save_practice_session_and_daily_summary(
                date, item_name, int(item_id), minutes,
                tempo_note, tempo_bpm, content, content_source,
                practice_at=practice_at, is_extra=False,
            )
            # PR-B dedup: session 事务已写 behavior_log, 不再外部 append
            daily = db.get_daily_practice(date)
            resp_normal = {
                "ok": True,
                "total": daily["total_minutes"] if daily else minutes,
                "session": s,
            }
            _record_dedup(date_key, int(item_id), int(minutes), resp_normal,
                       tempo_bpm, content, practice_at)
            return JSONResponse(resp_normal)

        # 旧路径: 走 save_daily_practice 兼容逻辑 (不创建空 session, 避免污染 sessions 表)
        # 注意：只传 [{item, item_id, minutes}]，不要预合并！save_daily_practice 内部会读 DB 合并
        items = [{"item": item_name, "item_id": item_id, "minutes": minutes}]
        total = minutes  # save_daily_practice 会重新计算，这里只作返回值参考
        db.save_daily_practice(date, items, total, log_note,
                               channel='kid_app', method='timer',
                               practice_at=practice_at)

        # 打卡成功后，追加行为日志（仅旧路径，session 路径已在事务内写）
        for entry in behavior_entries:
            db.append_behavior_log(date, entry)

        resp_legacy_normal = {"ok": True, "total": total}
        _record_dedup(date_key, int(item_id), int(minutes), resp_legacy_normal,
                       tempo_bpm, content, practice_at)
        return JSONResponse(resp_legacy_normal)

    except ValueError as e:
        # 后端兜底校验 (防绕过, 但不向用户展示技术细节)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except Exception as e:
        import traceback
        import logging
        logging.error(f"API error: {e}\n{traceback.format_exc()}")
        return JSONResponse({"ok": False, "error": "服务器内部错误"}, status_code=500)

# ─── API: 删除单条练习记录 ─────────────────────────────────────────────────
@app.delete("/api/log")
async def api_delete_log(request: Request):
    import traceback
    try:
        body = json.loads(await request.body())
        date_str = body.get("date")
        item_name = body.get("item")
        item_id = int(body.get("id", 0))
        if not date_str:
            return JSONResponse({"ok": False, "error": "缺少参数"}, status_code=400)
        date = dt.date.fromisoformat(date_str)
        if item_id:
            db.remove_daily_practice_record_by_id(date, item_id)
            after = db.get_daily_practice(date)
        elif item_name:
            db.remove_daily_practice_item(date, item_name)
            after = db.get_daily_practice(date)
        else:
            return JSONResponse({"ok": False, "error": "缺少参数"}, status_code=400)
        return JSONResponse({"ok": True, "items": after["items"] if after else [], "total_minutes": after["total_minutes"] if after else 0})
    except Exception as e:
        import traceback
        import logging
        logging.error(f"API error: {e}\n{traceback.format_exc()}")
        return JSONResponse({"ok": False, "error": "服务器内部错误"}, status_code=500)

# ─── API: 更新练习项目排序 ─────────────────────────────────────────────────
@app.put("/api/items/order")
async def api_update_items_order(request: Request):
    body = json.loads(await request.body())
    orders = body.get("orders", [])
    for entry in orders:
        db.update_practice_item_sort_order(entry["item_id"], entry["sort_order"])
    return JSONResponse({"ok": True})

# ─── API: 表扬海报生成 ─────────────────────────────────────────────────────
# 已下线：图片生成需在 Hermes Agent 对话窗口进行，见 /praise 页面
@app.get("/api/subject_mood/{item_id}")
async def api_subject_mood(item_id: int, name: str = ""):
    """流式生成练习心情 SSE。"""
    from fastapi.responses import StreamingResponse
    from src.kid_app.subject_info import generate_mood_stream

    async def event_stream():
        for token in generate_mood_stream(name):
            yield f"data: {json.dumps({'text': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/api/subject_summary/{item_id}")
async def api_subject_summary(item_id: int, name: str = ""):
    """流式生成完整科目摘要 SSE。"""
    from fastapi.responses import StreamingResponse
    from src.kid_app.subject_info import generate_summary_stream

    async def event_stream():
        for token in generate_summary_stream(name):
            yield f"data: {json.dumps({'text': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/api/praise")
async def api_praise(request: Request):
    return JSONResponse({
        "ok": False,
        "error": "Praise poster generation has moved to Hermes Agent. Open /praise and click '打开 Hermes Agent'."
    }, status_code=410)

# ─── 页面路由 ───────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    return prepare_page()

@app.get("/gsap-demo", response_class=HTMLResponse)
def gsap_demo():
    demo_path = Path(__file__).parent.parent.parent / "gsap-demo.html"
    return HTMLResponse(demo_path.read_text())

ENCOURAGEMENTS = [
    "今天也要加油哦！💪",
    "吹笛子真好听 🎵",
    "坚持就是胜利 🏆",
    "爸爸相信你！🌟",
    "一天比一天进步 📈",
    "音乐小达人 🥁",
    "认真练习的样子真棒 👍",
    "加油！你是最棒的 ✨",
    "笛声悠扬，真好听 🎶",
    "练完就可以去玩啦 🎮",
    "今天的你比昨天更好 💐",
]

# 默认祝福语池（settings 表无数据时的 fallback）
_DEFAULT_BLESS_POOL = [
    {"main": "每一次练习",     "accent": "都是新的进步"},
    {"main": "坚持练习",       "accent": "让音乐自然流淌"},
    {"main": "今天的你",       "accent": "比昨天更棒"},
    {"main": "一步一步",       "accent": "奏出属于自己的旋律"},
    {"main": "认真吹过",       "accent": "就是最好的练习"},
    {"main": "每一次吹奏",     "accent": "都在靠近更好"},
    {"main": "认真对待",       "accent": "每一个音符"},
    {"main": "不必比较",       "accent": "你有你的节奏"},
    {"main": "慢慢积累",       "accent": "笛声会越来越好听"},
    {"main": "慢慢来",         "accent": "比较快"},
    {"main": "不怕慢",         "accent": "只怕站"},
    {"main": "音乐是",         "accent": "一辈子的朋友"},
    {"main": "吹笛真棒",       "accent": "为你鼓掌👏"},
    {"main": "音符在等你",     "accent": "去拥抱它"},
    {"main": "笛声响起",       "accent": "世界更美好"},
    {"main": "每天进步一点点", "accent": "就是最好的成长"},
    {"main": "练习时专注的你", "accent": "闪闪发光✨"},
    {"main": "音乐是魔法",     "accent": "你就是魔法师🪄"},
    {"main": "坚持吹奏",       "accent": "会越来越动听"},
    {"main": "累了休息一下",   "accent": "再继续也不迟"},
    {"main": "吹得真棒",       "accent": "再玩一会儿吧"},
    {"main": "音乐之路",       "accent": "你才刚开始"},
    {"main": "每个音符",       "accent": "都是小小的胜利"},
    {"main": "爸爸爱听",       "accent": "你吹的每一首曲子"},
    {"main": "不用和别人比",   "accent": "只要比昨天好"},
    {"main": "声音会说话",     "accent": "告诉世界你在"},
    {"main": "你的笛声",       "accent": "是家里最美的音乐"},
    {"main": "今天也坚持了",   "accent": "真了不起🌟"},
    {"main": "音乐相伴",       "accent": "快乐成长🎵"},
    {"main": "笛子会说",       "accent": "谢谢你的陪伴"},
    {"main": "吹久一些",         "accent": "也许会有新发现"},
    {"main": "小小的坚持",       "accent": "大大的收获"},
    {"main": "今天的笛声",       "accent": "比昨天更自信"},
    {"main": "音乐会记得",       "accent": "你每一次努力"},
    {"main": "吹出快乐就好",     "accent": "不用完美"},
    {"main": "你认真吹笛的样子", "accent": "特别好看"},
    {"main": "每一首都值得",     "accent": "为自己鼓掌"},
    {"main": "休息好了就继续",   "accent": "不着急"},
    {"main": "你的节奏",         "accent": "就是最好的节奏"},
    {"main": "笛声里有你的故事", "accent": "继续写下去"},
    {"main": "今天的练习",       "accent": "未来的你会感谢"},
    {"main": "喜欢就是最好的老师", "accent": "继续喜欢就好"},
    {"main": "嘴角上扬地吹",     "accent": "音乐也会开心"},
    {"main": "不着急长大",       "accent": "慢慢享受音乐"},
    {"main": "一首曲子",         "accent": "一个小小冒险"},
    {"main": "你已经很棒了",     "accent": "再吹一首试试"},
    {"main": "呼吸稳了",         "accent": "音色就稳了"},
    {"main": "每天一小步",       "accent": "一年一大步"},
    {"main": "累了就放下",       "accent": "明天再来"},
    {"main": "笛子在等你",       "accent": "每一天"},
    {"main": "妈妈最爱听",       "accent": "你练笛的声音"},
    {"main": "你吹笛的时候",     "accent": "眼睛会发光"},
    {"main": "慢慢吹",           "accent": "好好听"},
    {"main": "今天的风",         "accent": "会带着你的笛声飞很远"},
    {"main": "坚持的人",         "accent": "运气都不会差"},
    {"main": "从第一个音开始",   "accent": "世界就不一样了"},
    # ── 新增 24 条 (2026-06-22) ──
    {"main": "深吸一口气",       "accent": "让笛声更饱满"},
    {"main": "手指记住的",       "accent": "比脑子更多"},
    {"main": "吹错也没关系",     "accent": "重来就是勇气"},
    {"main": "今天多吹了一首",   "accent": "这就是进步"},
    {"main": "安静地吹一曲",     "accent": "世界都温柔了"},
    {"main": "嘴巴酸了",         "accent": "说明你在认真"},
    {"main": "第一个音最难",     "accent": "吹出来就好了"},
    {"main": "笛膜振动的瞬间",   "accent": "就是音乐在呼吸"},
    {"main": "慢练一遍",         "accent": "胜过快吹十遍"},
    {"main": "今天的练习",       "accent": "明天会记得"},
    {"main": "你和笛子",         "accent": "越来越默契了"},
    {"main": "吹完一首曲子",     "accent": "那种满足感真好"},
    {"main": "气息稳了",         "accent": "音色就好听了"},
    {"main": "闭上眼睛吹",       "accent": "感受声音在飞"},
    {"main": "高音上去了",       "accent": "又突破了一点"},
    {"main": "练完记得喝水",     "accent": "照顾好自己"},
    {"main": "你吹的每个音",     "accent": "爸爸都听得见"},
    {"main": "今天比昨天",       "accent": "多坚持了一分钟"},
    {"main": "笛声是你的语言",   "accent": "不需要翻译"},
    {"main": "坐在那里吹笛",     "accent": "时间变得好慢"},
    {"main": "新的曲子",         "accent": "新的冒险开始了"},
    {"main": "你练笛的样子",     "accent": "是家里最好的风景"},
    {"main": "今天吹得开心吗",   "accent": "开心就好"},
    {"main": "每一次呼吸",       "accent": "都在为音乐准备"},
]


def _get_bless_pool() -> list[dict]:
    """从 settings 表读取 bless_pool，fallback 到默认列表"""
    try:
        raw = db.get_setting("bless_pool")
        if raw:
            import json as _json
            return _json.loads(raw)
    except Exception:
        pass
    return _DEFAULT_BLESS_POOL


# 可配置的准备步骤（后端可通过设置表动态调整）
PREPARE_STEPS = [
    {"title": "热身呼吸",    "desc": "深呼吸 3~5 次，放松身体，让气息更顺畅。", "color": "sage"},
    {"title": "基础音阶练习", "desc": "从低音到高音慢速吹奏，熟悉指法位置。",    "color": "rose"},
    {"title": "复习老师要求", "desc": "查看本周练习重点，有针对性地练习。",        "color": "lavender"},
]


def _bless_for_today() -> dict:
    """每次调用随机选一条（每次打开页面都会刷新）"""
    import random
    pool = _get_bless_pool()
    return random.choice(pool)


def _daily_encouragement() -> str:
    """按今天日期 seed 选固定的鼓励语（同一天刷新也同一条）"""
    today = dt.date.today()
    seed = today.year * 10000 + today.month * 100 + today.day
    idx = seed % len(ENCOURAGEMENTS)
    return ENCOURAGEMENTS[idx]


def _build_steps_html(steps: list[dict]) -> str:
    """把步骤列表渲染成 HTML card 字符串"""
    html = ""
    for i, step in enumerate(steps, 1):
        cid = step['color']
        html += f"""
  <div class="step-card" id="step{i}" onclick="toggleStep(this)">
    <div class="step-num {cid}">{i}</div>
    <div class="step-body">
      <h3 class="step-title">{step['title']}</h3>
      <p class="step-desc">{step['desc']}</p>
    </div>
    <div class="step-check" id="check{i}">✓</div>
  </div>"""
    return html


@app.get("/prepare", response_class=HTMLResponse)
def prepare_page():
    today = dt.date.today()
    ws = week_start_of(today)

    # 祝福语
    bless = _bless_for_today()

    # 本周老师要求
    assign = db.get_weekly_assignment_for_week(today)
    assign_images = []
    if assign and assign.get("items"):
        assign_eyebrow = f"本周练习要求 · 第 {assign.get('stage_order', '?')} 期"
        stage_start = assign.get('stage_start', today)
        stage_end   = assign.get('stage_end', today)
        # 确保 start ≤ end（数据可能有误，统一兜底）
        if stage_start and stage_end:
            if hasattr(stage_start, 'strftime') and hasattr(stage_end, 'strftime'):
                if stage_start > stage_end:
                    stage_start, stage_end = stage_end, stage_start
                assign_title = f"{stage_start.strftime('%m月%d日')} ~ {stage_end.strftime('%m月%d日')}"
            else:
                assign_title = str(stage_start) + " ~ " + str(stage_end)
        else:
            assign_title = "本周练习安排"
        assign_items_html = ""
        for it in assign["items"]:
            req = it.get('requirements') or it.get('requirement', '')
            reqs = req.split("\n") if req else []
            req_lines = "".join(f"      <li>{r}</li>\n" for r in reqs)
            item_id_str = f"(item_id: {it.get('item_id')})" if it.get('item_id') else ""
            assign_items_html += f"""<div class="assign-subject">
        <div class="assign-subject-header">
          <span class="assign-subject-name">{it['item']}</span>
          <span class="assign-subject-id">{item_id_str}</span>
        </div>
        <ul class="assign-subject-reqs">
{req_lines}
        </ul>
      </div>
"""
        assign_images = assign.get("images", [])
    else:
        assign_eyebrow  = "本周老师要求"
        assign_title    = "暂无老师要求"
        assign_items_html = "<li>直接开始练习吧！🎵</li>"

    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    return render(
        "prepare",
        active_nav="prepare",  # sidebar: 准备 (默认高亮, prepare 是落地页)
        eyebrow="竹笛练习准备",
        bless_main=bless["main"],
        bless_accent=bless["accent"],
        today_str=today.strftime("%m月%d日"),
        weekday=weekday_names[today.weekday()],
        streak=streak_days(),
        encouragement=_daily_encouragement(),
        enc_list_json=json.dumps(_get_bless_pool()),
        steps_html=_build_steps_html(PREPARE_STEPS),
        assign_eyebrow=assign_eyebrow,
        assign_title=assign_title,
        assign_items_html=assign_items_html,
        assign_images=assign_images,
        cta_title="准备好啦！",
        cta_sub="三个步骤都完成后，开始今天的练习。",
        cta_btn_text="开始行动",
    )

@app.get("/practice", response_class=HTMLResponse)
def practice_page():
    today = dt.date.today()
    items = db.get_practice_items(active_only=True, include_archived=False)
    categories = practice_module.get_categories()

    # 本周老师要求（date 字段转字符串避免 JSON 序列化报错）
    assign = db.get_weekly_assignment_for_week(today)
    import json as _json
    if assign:
        assign = dict(assign)
        for k in ('lesson_date', 'stage_start', 'stage_end'):
            if assign.get(k):
                assign[k] = str(assign[k])
    assign_json = _json.dumps(assign) if assign else "null"

    assign_item_names = {}
    if assign and assign.get("items"):
        for a in assign["items"]:
            req = a.get('requirements') or a.get('requirement', '')
            metro = a.get('metronome', '')
            assign_item_names[a["item"]] = {'req': req, 'metro': metro}

    # 建立 practice_item_id → {req, metro} 的映射（精确匹配）
    assign_by_pi_id = {}
    if assign and assign.get("items"):
        for a in assign["items"]:
            pid = a.get("item_id")
            if pid:
                req = a.get('requirements') or a.get('requirement', '')
                metro = a.get('metronome', '')
                assign_by_pi_id[pid] = {'req': req, 'metro': metro}

    def _find_requirement(item_name):
        """精确匹配 name（不用模糊，避免 '长音' 错误匹配 '吸气长音'）"""
        return assign_item_names.get(item_name, {})

    cat_map = {c["id"]: c["name"] for c in categories}
    by_cat = {}
    for it in items:
        cid = it.get("category_id")
        cat = cat_map.get(cid, "Other")
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(it)

    items_html = ""
    for cat, cat_items in sorted(by_cat.items(), key=lambda x: next((c["sort_order"] for c in categories if c["name"] == x[0]), 99)):
        cat_count = len(cat_items)
        items_html += "<h3>" + cat + "<span class='cat-count'>" + str(cat_count) + "</span></h3>"
        items_html += "<div class='item-grid'>"
        for it in sorted(cat_items, key=lambda x: x.get("sort_order", 0)):
            name = it["name"]
            pid = it.get("item_id")
            req_info = assign_by_pi_id.get(pid) or _find_requirement(name)
            req_text = req_info.get('req', '') if isinstance(req_info, dict) else req_info
            metro_text = req_info.get('metro', '') if isinstance(req_info, dict) else ''
            combined = (metro_text + '  ' if metro_text else '') + req_text
            has_req = bool(combined)
            has_req_class = "has-req" if has_req else ""
            req_dot = "<span class='req-dot'></span>" if has_req else ""
            content_opts = (it.get("content_options") or "").replace("'", "&#39;")
            items_html += (
                "<button class='item-btn " + has_req_class + "' data-id='" + str(it["item_id"]) + "' "
                + "data-req='" + combined.replace("'", "&#39;") + "' "
                + "data-name='" + name.replace("'", "&#39;") + "' "
                + "data-content-options='" + content_opts + "' "
                + "onclick=\"selectItem('" + name.replace("'", "\\'") + "', " + str(it["item_id"]) + ", this, event)\">"
                + req_dot
                + "<span class='btn-name'>" + name + "</span>"
                + "</button>"
            )
        items_html += "</div>"

    if not items_html:
        items_html = "<p style='color:#7F8C8D;text-align:center;'>No practice items. Ask dad to add via dizical practice config</p>"

    today_p = db.get_daily_practice(today)
    today_mins = today_p["total_minutes"] if today_p else 0

    # ── 科目摘要 ──
    subject_info_dict = {}
    for it in items:
        name = it["name"]
        pid = it["item_id"]
        info = get_subject_info(name)
        if info:
            subject_info_dict[pid] = {
                "emoji": info["emoji"],
                "title": info["title"],
                "one_liner": info["one_liner"],
                "what": info.get("what", ""),
                "how": info.get("how", []),
                "why": info.get("why", ""),
                "story": info.get("story", ""),
                "tip": info.get("tip", ""),
            }

    subject_info_json = json.dumps(subject_info_dict, ensure_ascii=False)

    return render(
        "practice",
        active_nav="practice",  # sidebar: 练习
        child_name=child_name(),
        items_html=items_html,
        today_mins=today_mins,
        assign_json=assign_json,
        today_date=today.isoformat(),
        subject_info_json=subject_info_json,
    )

@app.get("/achievements", response_class=HTMLResponse)
def achievements_page():
    today = dt.date.today()

    # ── 卡片1: 本周目标进度 ─────────────────────────────
    week_pct, week_pct_text = _week_progress()

    # ── 卡片2: 练习看板 ────────────────────────────────
    # 连续练习：从今天往前倒查，遇0分钟即停
    streak = _calc_current_streak()
    yesterday_mins = _calc_yesterday_mins()
    yesterday_prev = _calc_yesterday_mins(days_ago=2)  # 前天

    week_mins, week_days_count = _calc_week_mins_and_days()
    # 上周：找上一条 weekly_assignment（stage_order = 当前stage_order - 1）
    ws_cur, we_cur = _get_current_week_range()
    # 找当前周的 stage_order
    conn = db._get_connection()
    cur_week_row = conn.execute("""
        SELECT stage_order FROM weekly_assignments
        WHERE ? >= stage_start
          AND (stage_end IS NULL OR ? <= stage_end)
        LIMIT 1
    """, (today.isoformat(), today.isoformat())).fetchone()
    week_days_prev = 0
    if cur_week_row and cur_week_row[0] is not None:
        cur_order = cur_week_row[0]
        prev_week_row = conn.execute("""
            SELECT stage_start, stage_end FROM weekly_assignments
            WHERE stage_order = ?
            LIMIT 1
        """, (cur_order - 1,)).fetchone()
        if prev_week_row:
            ps = dt.date.fromisoformat(prev_week_row[0])
            pe = dt.date.fromisoformat(prev_week_row[1])
            practices_prev = db.get_daily_practices_in_range(ps, pe)
            week_days_prev = len([p for p in practices_prev if p.get("total_minutes", 0) > 0])

    month_mins, month_days_count = _calc_month_mins_and_days()
    # 上月同日期范围（4/1-5/20 vs 5/1-5/20）
    prev_month = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1
    month_start_prev = dt.date(prev_year, prev_month, 1)
    month_end_prev = min(today - dt.timedelta(days=28), dt.date(prev_year, prev_month, 1) + dt.timedelta(days=29))
    # 确保不超出今天所在月的实际范围
    month_end_prev = min(month_end_prev, dt.date(today.year, today.month, today.day))
    practices_m_prev = db.get_daily_practices_in_range(month_start_prev, month_end_prev)
    month_days_prev = len([p for p in practices_m_prev if p.get("total_minutes", 0) > 0])

    # 环比文字
    yd_diff_txt, yd_pos = _ring_diff(yesterday_mins, yesterday_prev, "分")
    wm_diff_txt, wm_pos = _ring_diff(week_days_count, week_days_prev)
    # 月份对比：用上月月份名称（如"4月"）
    prev_month_name = f"{prev_month}月"
    mm_diff_txt, mm_pos = _ring_diff(month_days_count, month_days_prev, ref_period=prev_month_name)

    # ── 卡片3: 勋章展示 ────────────────────────────────
    milestone_html = _milestone_html("seasonal")

    # ── 卡片3.5: 每日打卡盲盒 ─────────────────────────
    daily_blindbox_html, checkin_days = _daily_blindbox_html()

    # ── 练习看板后3格：TOP项目展示 ───────────────────
    last_top = _calc_last_practice_top(2)
    week_top = _calc_week_top(2)
    month_top = _calc_month_top(2)

    # 拆解为扁平变量（_calc_last_practice_top 等返回扁平字段）
    last_date = last_top["date"]
    last_top1_name = last_top["top1_name"]
    last_top1_mins = last_top["top1_mins"]
    last_top2_name = last_top["top2_name"]
    last_top2_mins = last_top["top2_mins"]

    week_date = week_top["date"]
    week_top1_name = week_top["top1_name"]
    week_top1_mins = week_top["top1_mins"]
    week_top2_name = week_top["top2_name"]
    week_top2_mins = week_top["top2_mins"]

    month_date = month_top["date"]
    month_top1_name = month_top["top1_name"]
    month_top1_mins = month_top["top1_mins"]
    month_top2_name = month_top["top2_name"]
    month_top2_mins = month_top["top2_mins"]

    return render(
        "achievements",
        active_nav="achievements",  # sidebar: 成就
        child_name=child_name(),
        week_pct=week_pct,
        week_pct_text=week_pct_text,
        streak=str(streak),
        streak_unit="天",
        streak_label="已连续练习",
        yesterday_mins=str(yesterday_mins),
        yesterday_unit="分钟",
        yesterday_label="昨天练习",
        yesterday_diff=yd_diff_txt,
        yesterday_pos="up" if yd_pos else "",
        week_days=str(week_days_count),
        week_unit="天",
        week_label="本周练习",
        week_diff=wm_diff_txt,
        week_pos="up" if wm_pos else "",
        month_days=str(month_days_count),
        month_unit="天",
        month_label="本月练习",
        month_diff=mm_diff_txt,
        month_pos="up" if mm_pos else "",
        last_date=last_date,
        last_top1_name=last_top1_name,
        last_top1_mins=last_top1_mins,
        last_top2_name=last_top2_name,
        last_top2_mins=last_top2_mins,
        week_date=week_date,
        week_top1_name=week_top1_name,
        week_top1_mins=week_top1_mins,
        week_top2_name=week_top2_name,
        week_top2_mins=week_top2_mins,
        month_date=month_date,
        month_top1_name=month_top1_name,
        month_top1_mins=month_top1_mins,
        month_top2_name=month_top2_name,
        month_top2_mins=month_top2_mins,
        milestone_html=milestone_html,
        daily_blindbox_html=daily_blindbox_html,
        checkin_days=checkin_days,
    )

@app.get("/badges", response_class=HTMLResponse)
def badges_page():
    """勋章墙完整页（成就殿堂）— milestone 类型 badge"""
    import json as _json
    from src.achievement_definitions import calc_all, get_achievements_by_type

    conn = db._get_connection()

    # ── 统一 calc_all() ───────────────────────────────────────────
    results = calc_all()   # dict[aid] → CalcResult

    # ── 读所有需要展示的 achievements（排除神秘/晋级等纯统计类） ──────
    cur = conn.execute(
        "SELECT id, name, type, category, description, threshold, cond_text, "
        "unlock_strategy, achieved_at_override FROM achievements "
        "WHERE category IN ('milestone', '突破', '巅峰', '执着', '段位', '晋级', '神秘', 'seasonal') "
        "ORDER BY sort_order")
    cols = [d[0] for d in cur.description]
    ach_rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    # 构建 badge 列表 (PR-B: badge_url 改读 DB + cache 60s)
    badges = []
    for ach in ach_rows:
        aid = ach["id"]
        res = results.get(aid)
        if res is None:
            continue

        # V2.6 (2026-06-16) feat/badge-achieved-at-override:
        # 纪念章/表彰型徽章不走 calc, 直接读 achievement_stats.achieved + achievements.achieved_at_override
        # 触发条件: (a) unlock_strategy='immediate' (PR #101), 或 (b) achieved_at_override 非 NULL
        from src.achievement_definitions import CalcResult
        is_commemorative = (ach.get("unlock_strategy") == "immediate" or ach.get("achieved_at_override"))
        if is_commemorative:
            cur.execute("SELECT achieved, achieved_at FROM achievement_stats WHERE achievement_id=?", (aid,))
            row = cur.fetchone()
            override_at = ach.get("achieved_at_override")
            if override_at:
                res = CalcResult(True, 1, None, override_at, f"考出时间: {override_at}")
            elif row and row[0] == 'Y':
                res = CalcResult(True, 1, None, row[1] or None, "立即解锁")

        badges.append({
            "id": aid,
            "name": ach["name"],
            "typ": ach["type"],   # 中文标签（突破/巅峰/执着/段位/晋级）
            "group": ach["category"],  # milestone / seasonal
            "description": ach["description"],
            "condition": res.condition,
            "cond_text": ach.get("cond_text") or "",  # V2.2 (2026-06-15) feat/badge-cond-text
            "achieved": res.achieved,
            "achieved_at": res.achieved_at,
            "badge_url": get_badge_url(aid),
            "unlock_strategy": ach.get("unlock_strategy") or "calc",
            "achieved_at_override": ach.get("achieved_at_override") or "",
        })

    # 分离已解锁/未解锁，各按 achieved_at 降序
    def sort_key(b):
        if b["achieved_at"] is None:
            return (1, "")
        return (0, b["achieved_at"])

    unlocked = sorted([b for b in badges if b["achieved"]], key=sort_key, reverse=True)
    locked   = sorted([b for b in badges if not b["achieved"]], key=sort_key, reverse=True)
    sorted_badges = unlocked + locked

    total_count   = len(badges)
    earned_count = len(unlocked)

    return render("badges",
        child_name=child_name(),
        data_json=_json.dumps(sorted_badges, ensure_ascii=False),
        total_count=total_count,
        earned_count=earned_count,
    )


@app.get("/report/stage-print", response_class=HTMLResponse)
def report_stage_print_page(request: Request):
    """Stage 维 session 明细打印页 (A4 单页). 独立页可查历史 stage."""
    return render("stage-print", child_name=child_name())


@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request, month: Optional[str] = None):
    """
    练习报告页 (feat/happy-month-switch):
    - `month=YYYY-MM` 可选查询参数; 缺省=当前月; 非法值 fallback 当前月
    - 模板显示左右箭头月份切换器; 当月锁住右箭头
    """
    today = dt.date.today()

    # 解析 month 参数 (YYYY-MM), fallback 当前月
    if month:
        try:
            parts = month.split("-")
            view_year = int(parts[0])
            view_month = int(parts[1])
            if not (1 <= view_month <= 12) or view_year < 2000 or view_year > today.year + 1:
                raise ValueError
            # 未来月 fallback 当前月
            if (view_year, view_month) > (today.year, today.month):
                view_year, view_month = today.year, today.month
        except (IndexError, ValueError):
            view_year, view_month = today.year, today.month
    else:
        view_year, view_month = today.year, today.month

    data = practice_module.get_month_summary(view_year, view_month)

    start = dt.date(view_year, view_month, 1)
    if view_month == 12:
        end = dt.date(view_year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        end = dt.date(view_year, view_month + 1, 1) - dt.timedelta(days=1)

    practices = {p["date"].isoformat(): p for p in db.get_daily_practices_in_range(start, end)}

    cal_html = ""
    for _ in range(start.weekday()):
        cal_html += "<div class='cal-day empty'></div>"
    for d in range(1, end.day + 1):
        day_date = dt.date(view_year, view_month, d)
        key = day_date.isoformat()
        p = practices.get(key)
        mins = p["total_minutes"] if p else 0
        if mins == 0:
            cls = "cal-day"
            label = '<span class="day-num">' + str(d) + '</span><span class="sel-bar"></span>'
        elif mins < 20:
            cls = "cal-day low"
            label = '<span class="day-num">' + str(d) + '<br><small>' + str(mins) + 'm</small></span><span class="sel-bar"></span>'
        elif mins < 40:
            cls = "cal-day mid"
            label = '<span class="day-num">' + str(d) + '<br><small>' + str(mins) + 'm</small></span><span class="sel-bar"></span>'
        else:
            cls = "cal-day high"
            label = '<span class="day-num">' + str(d) + '<br><small>' + str(mins) + 'm</small></span><span class="sel-bar"></span>'
        if day_date == today:
            cls += " today"
        cal_html += "<div class='" + cls + "' data-date='" + key + "'>" + label + "</div>"

    # 月份切换器上下文 (feat/happy-month-switch)
    is_current_month = (view_year == today.year and view_month == today.month)
    if view_month == 1:
        prev_year, prev_month = view_year - 1, 12
    else:
        prev_year, prev_month = view_year, view_month - 1
    if view_month == 12:
        next_year, next_month = view_year + 1, 1
    else:
        next_year, next_month = view_year, view_month + 1

    return render(
        "report",
        active_nav="dashboard",  # sidebar: Dashboard (report 页面对应 Dashboard)
        child_name=child_name(),
        month_str=f"{view_year}/{view_month:02d}",
        total_mins=str(data["total_minutes"]),
        practice_days=str(data["practice_days"]),
        cal_html=cal_html,
        # 月份切换器
        prev_month=f"{prev_year}-{prev_month:02d}",
        next_month=f"{next_year}-{next_month:02d}",
        is_current_month=is_current_month,
        current_month_label=today.strftime("%Y/%m"),
    )

# ─── PIN 验证 ───────────────────────────────────────────────────────────────
def get_setting(key, default=""):
    try:
        return db.get_setting(key) or default
    except Exception:
        return default


@app.get("/api/bless-pool", response_class=JSONResponse)
def api_get_bless_pool():
    """返回当前祝福语池（需 PIN 验证）"""
    pin = get_setting("dad_pin")
    if not pin:
        pool = _get_bless_pool()
        return JSONResponse({"pool": pool})
    # 无 PIN 时也返回池内容（编辑需验证）
    return JSONResponse({"pool": _get_bless_pool()})


@app.put("/api/bless-pool", response_class=JSONResponse)
async def api_put_bless_pool(request: Request):
    """更新祝福语池（需 PIN 验证）"""
    body = json.loads(await request.body())
    pin = body.get("pin", "")
    stored_pin = get_setting("dad_pin")
    if stored_pin and pin != stored_pin:
        return JSONResponse({"ok": False, "error": "PIN 不对"}, status_code=401)

    new_pool = body.get("pool", [])
    if not isinstance(new_pool, list):
        return JSONResponse({"ok": False, "error": "格式错误"}, status_code=400)

    db.set_setting("bless_pool", json.dumps(new_pool, ensure_ascii=False))
    return JSONResponse({"ok": True})

@app.post("/api/verify-pin")
async def api_verify_pin(request: Request):
    body = json.loads(await request.body())
    pin = body.get("pin", "")
    stored_pin = get_setting("dad_pin")
    if stored_pin and pin == stored_pin:
        return JSONResponse({"ok": True, "role": "dad"})
    return JSONResponse({"ok": False}, status_code=401)

@app.get("/praise", response_class=HTMLResponse)
def praise_page():
    # 重定向到配置管理台
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/config", status_code=302)


# ─── 注册配置管理台路由 ─────────────────────────────────────────────────────
from src.kid_app.routes.config import router as config_router
app.include_router(config_router)

# ─── 注册 Badge 制作工作流路由 (V2, 2026-06-12 重构) ─────────────
# V2 简化: routes/badge_workflow.py 只 3 端点 (draft / commit-from-draft / discoveries)
# V1 9 端点 + routes/badge_batch.py 整文件删 (批量模式 V2 不做)
from src.kid_app.routes.badge_workflow import router as badge_workflow_router
app.include_router(badge_workflow_router)

# ─── 注册 minip (微信小程序) 专用路由 ─────────────────────────────────────
# dizical-minip 项目: 只新增端点，不影响现有功能
from src.kid_app.routes.minip_api import router as minip_router
app.include_router(minip_router)
