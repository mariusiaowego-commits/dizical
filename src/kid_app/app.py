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
    except:
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
    practices = db.get_daily_practices_in_range(dt.date(2020, 1, 1), dt.date.today())
    return sum(p["total_minutes"] for p in practices)


def _calc_max_consecutive_streak():
    """计算历史最长连续练习天数（断掉后重新接上也能恢复）"""
    today = dt.date.today()
    practices = db.get_daily_practices_in_range(dt.date(2020, 1, 1), today)
    day_mins = {p["date"]: p.get("total_minutes", 0) for p in practices}

    if not day_mins:
        return 0

    dates_sorted = sorted(day_mins.keys())
    first_day = dates_sorted[0]

    max_streak = 0
    cur_streak = 0
    d = first_day
    while d <= today:
        if day_mins.get(d, 0) > 0:
            cur_streak += 1
            max_streak = max(max_streak, cur_streak)
        else:
            cur_streak = 0
        d += dt.timedelta(days=1)
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
        "SELECT id, name, type, category, description, threshold, "
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

        # 前端已传 item_id → 直接用；未传则 fuzzy match 回填
        item_id_from_ui = body.get("item_id")
        if item_id_from_ui is None:
            matched = db._match_practice_item_id(item_name)
            item_id_to_write = matched if matched else 1
        else:
            # 前端传了 item_id，验证合法性；无效则 fuzzy match 修复
            item_id_to_write = db.validate_item_id(item_id_from_ui, item_name)

        if is_extra:
            # extra 追加：每次创建独立 item 条目（带唯一 id），不与同名合并
            # 直接操作 DB，绕过 save_daily_practice 的 merge 逻辑
            existing = db.get_daily_practice(date)
            existing_items = existing.get("items", []) if existing else []
            new_item = {"item_id": item_id_to_write, "item": item_name, "minutes": minutes}
            all_items = existing_items + [new_item]
            total = sum(it.get('minutes', 0) for it in all_items)
            # 直接写 DB，不合并
            import sqlite3
            conn = sqlite3.connect('/Users/mt16/dev/dizical/data/dizi.db')
            conn.execute('''
                INSERT OR REPLACE INTO daily_practices (date, items, total_minutes, log, practiced)
                VALUES (?, ?, ?, ?, ?)
            ''', (date.isoformat(), json.dumps(all_items, ensure_ascii=False), total, '', 'Y'))
            conn.commit()
            conn.close()
            return JSONResponse({"ok": True})

        # 正常打卡：直接传给 save_daily_practice，由它处理合并逻辑
        # 注意：只传 [{item, item_id, minutes}]，不要预合并！save_daily_practice 内部会读 DB 合并
        items = [{"item": item_name, "item_id": item_id_to_write, "minutes": minutes}]
        total = minutes  # save_daily_practice 会重新计算，这里只作返回值参考
        db.save_daily_practice(date, items, total, log_note)

        # 打卡成功后，追加行为日志（在 save_daily_practice 之后）
        for entry in behavior_entries:
            db.append_behavior_log(date, entry)

        return JSONResponse({"ok": True, "total": total})

    except Exception as e:
        import traceback
        return JSONResponse({"ok": False, "error": str(e), "trace": traceback.format_exc()}, status_code=500)

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
        return JSONResponse({"ok": False, "error": str(e), "trace": traceback.format_exc()}, status_code=500)

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
        items_html += "<h3 style='font-size:16px;color:#4ECDC4;margin:12px 0 6px;'>" + cat + "</h3>"
        items_html += "<div class='item-grid'>"
        for it in sorted(cat_items, key=lambda x: x.get("sort_order", 0)):
            name = it["name"]
            pid = it.get("item_id")
            # 优先用 practice_item_id 精确匹配，fallback 用名称模糊匹配
            req_info = assign_by_pi_id.get(pid) or _find_requirement(name)
            req_text = req_info.get('req', '') if isinstance(req_info, dict) else req_info
            metro_text = req_info.get('metro', '') if isinstance(req_info, dict) else ''
            # tooltip 里：速度 + 要求（metronome 已含 ♩= 前缀）
            combined = (metro_text + '  ' if metro_text else '') + req_text
            has_req = bool(combined)
            tooltip_html = ""
            if has_req and combined:
                tooltip_html = "<div class='req-tooltip'>" + combined + "</div>"
            wrap_class = "item-btn-wrap" if has_req else ""
            has_req_class = "has-req" if has_req else ""
            items_html += (
                "<div class='" + wrap_class + "'>"
                + "<button class='item-btn " + has_req_class + "' data-id='" + str(it["item_id"]) + "' "
                + "data-req='" + combined.replace("'", "&#39;") + "' "
                + "onclick=\"selectItem('" + name.replace("'", "\\'") + "', " + str(it["item_id"]) + ")\">"
                + name + " <span style='font-size:11px;color:rgba(255,255,255,0.6)'>[" + str(it["item_id"]) + "]</span>"
                + tooltip_html
                + "</button></div>"
            )
        items_html += "</div>"

    if not items_html:
        items_html = "<p style='color:#7F8C8D;text-align:center;'>No practice items. Ask dad to add via dizical practice config</p>"

    today_p = db.get_daily_practice(today)
    today_mins = today_p["total_minutes"] if today_p else 0

    return render(
        "practice",
        child_name=child_name(),
        items_html=items_html,
        today_mins=today_mins,
        assign_json=assign_json,
        today_date=today.isoformat(),
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
        WHERE ? BETWEEN stage_start AND stage_end
        LIMIT 1
    """, (today.isoformat(),)).fetchone()
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
    # 获取当前成就数据
    today = dt.date.today()
    streak = streak_days()
    total_mins = total_practice_minutes()
    ws = week_start_of(today)
    week_prac = db.get_daily_practices_in_range(ws, today)
    week_mins = sum(p["total_minutes"] for p in week_prac)
    week_days = len([p for p in week_prac if p.get("total_minutes", 0) > 0])

    # 当前解锁的徽章
    unlocked = []
    if streak >= 3:
        unlocked.append({"type": "fire", "label": f"🔥 {streak}天连续", "desc": "坚持练习"})
    if streak >= 7:
        unlocked.append({"type": "star7", "label": "⭐ 7天连续达成", "desc": "超棒毅力"})
    if total_mins >= 60:
        unlocked.append({"type": "medal", "label": "🏅 练习达人", "desc": "累计60分钟+"})
    if week_mins >= 60:
        unlocked.append({"type": "weekstar", "label": "⭐ 本周之星", "desc": "本周60分钟+"})

    # 预设表扬语
    PRAISE_MSGS = [
        "太棒了！今天的你比昨天更好！🌟",
        "坚持就是胜利，你是最棒的！💪",
        "笛声悠扬，继续加油！🎵",
        "认真练习的样子真美！✨",
        "今天的进步爸爸都看到了！👍",
        "音乐小达人就是你！🥁",
        "练完就可以开心去玩啦！🎮",
    ]
    import random
    seed = today.year * 10000 + today.month * 100 + today.day
    random.seed(seed)
    daily_praise = random.choice(PRAISE_MSGS)
    random.seed()  # 恢复随机种子

    return render(
        "praise",
        child_name=child_name(),
        pin_locked="true" if get_setting("dad_pin") else "false",
        PIN_OVERLAY_DISPLAY="display:flex" if get_setting("dad_pin") else "display:none",
        PRAISE_CONTENT_DISPLAY="display:block" if not get_setting("dad_pin") else "display:none",
        unlocked=unlocked,
        daily_praise=daily_praise,
    )
