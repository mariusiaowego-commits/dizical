"""dizical 儿童版 Web 应用"""

import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional, List, Tuple

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.database import db
from src import practice as practice_module
from src.kid_app.subject_info import get_subject_info

# ─── App ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Bamboo Flute Practice")

static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

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
        "unlocked_template, placeholder FROM achievements" +
        (" WHERE category = ?" if category else "") +
        " ORDER BY sort_order",
        ((category,) if category else ()))
    cols = [d[0] for d in cur.description]
    ach_rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    # ── badge URL 映射 ───────────────────────────────────────────
    BADGE_URLS = {
        **{f"streak_{n}": f"/static/badges/streak_{n}.png" for n in [1, 3, 7, 14, 30, 100]},
        "total_60": "/static/badges/total_60.png",
        "total_300": "/static/badges/total_300.png",
        "total_600": "/static/badges/total_600.png",
        "total_1000": "/static/badges/total_1000.png",
        "first_log": "/static/badges/first_log.png",
        "all_items": "/static/badges/all_items.png",
        "double": "/static/badges/double.png",
        "week_champ": "/static/badges/week_champ.png",
        "full_month": "/static/badges/full_month.png",
        "top1": "/static/badges/top1.png",
        "top2": "/static/badges/top2.png",
        "top3": "/static/badges/top3.png",
        "early_riser": "/static/badges/early_bird_A.png",
        "little_chick_commander": "/static/badges/early_bird_B.png",
        "first_to_act": "/static/badges/early_bird_C.png",
        **{f"grade_{n}": f"/static/badges/grade_{n}-u.png" for n in range(1, 11)},
        **{f"lucky_61_{y}": f"/static/badges/lucky_61_{y}.png" for y in range(2026, 2031)},
    }

    # ── 分离已解锁 / 未解锁 ──────────────────────────────────────
    unlocked_list = []
    locked_list = []   # (ratio, card_html)

    for ach in ach_rows:
        aid = ach["id"]
        res = results.get(aid)
        if res is None:
            continue

        achieved = res.achieved
        cv = res.computed_value
        threshold = ach.get("threshold")
        badge_url = BADGE_URLS.get(aid, "/static/badges/medal_badge.png")

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
            badge_url, achieved, cv, threshold, res.condition
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


def _build_milestone_card(ach_id, name, ach_type, desc, badge_url, achieved, cv, threshold, condition=""):
    """生成单个 milestone 卡片 HTML（对应 .b-card 结构，与 badges 页面一致）"""
    import html as _html
    state_cls = "unlocked" if achieved else "locked"
    locked_flag = "yes" if not achieved else "no"
    cond_safe = _html.escape(condition or "")
    desc_safe = _html.escape(desc or "")

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


def _daily_blindbox_html():
    """生成每日打卡盲盒卡片 HTML"""
    conn = db._get_connection()
    today = dt.date.today()

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

    # 计算本周打卡了几天
    cur = conn.execute("""
        SELECT COUNT(DISTINCT date) 
        FROM daily_practices 
        WHERE date >= ? AND date <= ?
    """, (stage_start_str, stage_end_date.isoformat()))
    checkin_days = cur.fetchone()[0]

    # 查询每一天是否已打卡
    checked_days = set()
    cur = conn.execute("""
        SELECT DISTINCT date 
        FROM daily_practices 
        WHERE date >= ? AND date <= ?
    """, (stage_start_str, stage_end_date.isoformat()))
    for row in cur.fetchall():
        checked_days.add(row[0])

    # 图片映射
    DAILY_CHECKIN_IMAGES = {
        1: "/static/badges/daily_checkin_1.png",
        2: "/static/badges/daily_checkin_2.png",
        3: "/static/badges/daily_checkin_3.png",
        4: "/static/badges/daily_checkin_4.png",
        5: "/static/badges/daily_checkin_5.png",
        6: "/static/badges/daily_checkin_6.png",
        7: "/static/badges/daily_checkin_7.png",
    }

    # 盲盒名称
    DAILY_CHECKIN_NAMES = {
        1: "🐡 惊喜起点",
        2: "🦀️ 爆桶狂欢",
        3: "🐙 爆笑羁绊",
        4: "🐚 声音共鸣",
        5: "🌟 狂欢大奖",
        6: "🪼 最后高光",
        7: "🗺️ 终极神话",
    }

    # 盲盒描述
    DAILY_CHECKIN_DESCS = {
        1: "ok哥每天赶海第一件事不是看潮水，是看桶——今天桶空着，大海准备了什么？他刚弯腰，一只粉色河豚\"噗\"地蹦进桶里，气得圆滚滚的，像个生气的汤圆。ok哥说：\"哟，这河豚气鼓鼓的，跟我周一早上不想起床的样子一模一样！\"你周一打卡，河豚就是你的开工信号——它虽然气鼓鼓的，但它来了，就说明大海今天给你留了惊喜！",
        2: "ok哥最爱的词就是\"爆桶\"——桶装满了叫爆桶，桶装太满了也叫爆桶，桶里跳出一只大螃蟹还叫爆桶。今天他从沙子里拽出一只拳头大的红螃蟹，螃蟹死活不肯松钳，一夹——正好夹住YoYo的笛梢！YoYo使劲拔笛子，螃蟹使劲夹笛子，ok哥在旁边不帮忙，光顾着喊：\"大货！大货！别动让我拍！\"你周二打卡，这只螃蟹就是你的——它夹着你的笛子不放，就像你坚持练笛不放弃一样！",
        3: "ok哥抓过无数海鲜，但章鱼是他一生的对手。上次他抓了一只，章鱼八条腿分别吸在他的帽子、眼镜、桶、YoYo的笛子上，还剩三条腿悠闲地给自己扇风。ok哥说：\"这哥们比我还能抓——它把我抓住了！\"你周三打卡，章鱼就是你的\"周中恶魔\"——练笛练到周三最累了，这只章鱼就像你的疲惫，缠着你不放，但你看ok哥笑成那样，就知道其实它也是你的开心果！",
        4: "赶海最浪漫的时刻不是抓到大货，是你在海边捡到一枚海螺，贴到耳朵上——\"呜——\"，里面好像藏着整片大海的声音。ok哥说：\"我赶海十几年，海螺听过无数，但没有一个像今天这枚——它里面传出来的不是海浪声，是笛声！\"他把海螺递给YoYo，YoYo贴到耳朵上，里面飘出了彩虹色的乐谱。你周四打卡，这枚极光海螺就是你的回声——你吹进去的每一个音符，大海都记住了！",
        5: "周五了！ok哥说：\"赶海一整周，今天该开大奖了！\"他一铲子下去，沙子里蹦出一个金灿灿的宝箱，打开一看——不是金币，不是珍珠，是一枚比脸还大的黄金海星和一本发光的乐谱！ok哥愣了一秒，然后对着镜头比了个\"OK\"：\"收货！比爆桶还爽！\"你周五打卡，放学了大解放，宝箱为你打开，这周最亮的奖励归你！",
        6: "ok哥赶海赶了一周，今晚他决定来点不一样的——夜赶海！手电筒一开，海面突然浮起一只半透明的魔鬼鱼，浑身发着梦幻紫光，像一片会飞的光。ok哥说：\"我赶海这么多年，夜光的见过不少，但会跟着笛声游的我头一回见！\"YoYo开始吹笛，魔鬼鱼真的跟着笛声的节奏游。你周六打卡，夜光魔鬼鱼为你亮起来——周末的夜晚，笛声和荧光交织，这是属于你的深海演唱会！",
        7: "ok哥换上了他的船长服——虽然这衣服他自己都忘了什么时候买的，但他说：\"大结局必须有仪式感！\"海浪突然退去，沙滩上浮现出一个蓝色光环，一条由海水聚成的小神龙从光环中腾空而起，嘴里叼着一个玻璃漂流瓶。ok哥说：\"我赶了一辈子海，今天终于赶到了龙！\"瓶子里面是一张金色的乐谱，是这周你吹过的所有曲子的终极合集。你周日打卡，一周完美收官，神龙亲自给你颁奖！",
    }

    # 盲盒条件描述
    DAILY_CHECKIN_CONDS = {
        1: "完成今日练习即可解锁",
        2: "完成今日练习即可解锁",
        3: "完成今日练习即可解锁",
        4: "完成今日练习即可解锁",
        5: "完成今日练习即可解锁",
        6: "完成今日练习即可解锁",
        7: "完成今日练习即可解锁",
    }

    import html as _html

    # 生成所有badge的HTML
    badges_html = ""
    for day in range(1, stage_day + 1):
        day_date = stage_start + dt.timedelta(days=day - 1)
        day_date_str = day_date.isoformat()
        is_checked = day_date_str in checked_days
        is_today = day == stage_day

        image = DAILY_CHECKIN_IMAGES.get(day, "")
        name = DAILY_CHECKIN_NAMES.get(day, "")
        desc = DAILY_CHECKIN_DESCS.get(day, "")
        cond = DAILY_CHECKIN_CONDS.get(day, "")

        checked_class = "unlocked" if is_checked else "locked"
        today_class = "today" if is_today and not is_checked else ""
        locked_flag = "no" if is_checked else "yes"

        badges_html += f"""
        <div class="blindbox-badge {checked_class} {today_class} b-card" 
             data-id="daily_checkin_{day}"
             data-name="{_html.escape(name)}"
             data-tag="突破"
             data-cond="{_html.escape(cond)}"
             data-desc="{_html.escape(desc)}"
             data-img="{_html.escape(image)}"
             data-locked="{locked_flag}"
             onclick="openModal(this)">
          <img src="{image}" alt="{name}" class="blindbox-img">
          <div class="blindbox-day-label">第{day}天</div>
        </div>
        """

    # 判断今天是否已打卡
    today_checked = today.isoformat() in checked_days

    html = f"""
    <div class="ac-card" id="card-daily-blindbox">
      <div class="blindbox-header">
        <span class="blindbox-title">🎁 每日打卡盲盒</span>
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
@app.get("/api/practices/{date_str}")
def api_practice_day(date_str: str):
    """返回指定日期的练习明细"""
    try:
        day = dt.date.fromisoformat(date_str)
    except ValueError:
        return JSONResponse({"error": "无效日期格式"}, status_code=400)
    practice = db.get_daily_practice(day)
    if not practice:
        return JSONResponse({"date": date_str, "id": None, "items": [], "total_minutes": 0, "log": ""})
    return JSONResponse({
        "date": date_str,
        "id": practice.get("id"),
        "items": practice.get("items", []),
        "total_minutes": practice.get("total_minutes", 0),
        "log": practice.get("log", ""),
        "behavior_log": practice.get("behavior_log", []),
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
    try:
        body = json.loads(await request.body())
        date_str = body.get("date")
        item_name = body.get("item")
        minutes = int(body.get("minutes", 0))
        log_note = body.get("log", "")
        is_extra = body.get("is_extra", False)
        behavior_entries = body.get("behavior_log", [])  # [{enter_time, item, minutes}, ...]

        date = dt.date.fromisoformat(date_str) if date_str else dt.date.today()

        item_id = body.get("item_id")

        if is_extra:
            # extra 追加：创建独立 item 条目，通过 save_daily_practice 合并
            # 同名 item 累加分钟数；不同 item 追加
            items = [{"item": item_name, "item_id": item_id, "minutes": minutes, "is_extra": True}]
            db.save_daily_practice(date, items, minutes, '',
                                   channel='kid_app', method='extra')
            return JSONResponse({"ok": True})

        # 正常打卡：直接传给 save_daily_practice，由它处理合并逻辑
        # 注意：只传 [{item, item_id, minutes}]，不要预合并！save_daily_practice 内部会读 DB 合并
        items = [{"item": item_name, "item_id": item_id, "minutes": minutes}]
        total = minutes  # save_daily_practice 会重新计算，这里只作返回值参考
        db.save_daily_practice(date, items, total, log_note,
                               channel='kid_app', method='timer')

        # 打卡成功后，追加行为日志（在 save_daily_practice 之后）
        for entry in behavior_entries:
            db.append_behavior_log(date, entry)

        return JSONResponse({"ok": True, "total": total})

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
    {"main": "吹久一些",       "accent": "也许会有新发现"},
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
    if assign and assign.get("items"):
        assign_eyebrow = f"本周练习要求 · 第 {assign.get('stage_order', '?')} 课"
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
            assign_items_html += f"<li>{it['item']} {req}</li>"
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
            items_html += (
                "<button class='item-btn " + has_req_class + "' data-id='" + str(it["item_id"]) + "' "
                + "data-req='" + combined.replace("'", "&#39;") + "' "
                + "data-name='" + name.replace("'", "&#39;") + "' "
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
    if cur_week_row:
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
        "SELECT id, name, type, category, description, threshold FROM achievements "
        "WHERE category IN ('milestone', '突破', '巅峰', '执着', '段位', '晋级', '神秘', 'seasonal') "
        "ORDER BY sort_order")
    cols = [d[0] for d in cur.description]
    ach_rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    BADGE_FILES = {
        **{f"streak_{n}": f"/static/badges/streak_{n}.png" for n in [1, 3, 7, 14, 30, 100]},
        "total_60": "/static/badges/total_60.png",
        "total_300": "/static/badges/total_300.png",
        "total_600": "/static/badges/total_600.png",
        "total_1000": "/static/badges/total_1000.png",
        "first_log": "/static/badges/first_log.png",
        "all_items": "/static/badges/all_items.png",
        "double": "/static/badges/double.png",
        "week_champ": "/static/badges/week_champ.png",
        "full_month": "/static/badges/full_month.png",
        "top1": "/static/badges/top1.png",
        "top2": "/static/badges/top2.png",
        "top3": "/static/badges/top3.png",
        "early_riser": "/static/badges/early_bird_A.png",
        "little_chick_commander": "/static/badges/early_bird_B.png",
        "first_to_act": "/static/badges/early_bird_C.png",
        **{f"grade_{n}": f"/static/badges/grade_{n}-u.png" for n in range(1, 11)},
        **{f"lucky_61_{y}": f"/static/badges/lucky_61_{y}.png" for y in range(2026, 2031)},
    }

    # 构建 badge 列表
    badges = []
    for ach in ach_rows:
        aid = ach["id"]
        res = results.get(aid)
        if res is None:
            continue
        badges.append({
            "id": aid,
            "name": ach["name"],
            "typ": ach["type"],   # 中文标签（突破/巅峰/执着/段位/晋级）
            "group": ach["category"],  # milestone / seasonal
            "description": ach["description"],
            "condition": res.condition,
            "achieved": res.achieved,
            "achieved_at": res.achieved_at,
            "badge_url": BADGE_FILES.get(aid, "/static/badges/medal_badge.png"),
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


@app.get("/report", response_class=HTMLResponse)
def report_page():
    today = dt.date.today()
    data = practice_module.get_month_summary(today.year, today.month)

    start = dt.date(today.year, today.month, 1)
    if today.month == 12:
        end = dt.date(today.year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        end = dt.date(today.year, today.month + 1, 1) - dt.timedelta(days=1)

    practices = {p["date"].isoformat(): p for p in db.get_daily_practices_in_range(start, end)}

    cal_html = ""
    for _ in range(start.weekday()):
        cal_html += "<div class='cal-day empty'></div>"
    for d in range(1, end.day + 1):
        day_date = dt.date(today.year, today.month, d)
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

    return render(
        "report",
        active_nav="dashboard",  # sidebar: Dashboard (report 页面对应 Dashboard)
        child_name=child_name(),
        month_str=today.strftime("%Y/%m"),
        total_mins=str(data["total_minutes"]),
        practice_days=str(data["practice_days"]),
        cal_html=cal_html,
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
