"""
dizical 成就定义统一数据源

- 所有成就元数据（从 achievements 表读取）
- milestone 类型：calc() 读 achievement_stats
- seasonal 类型：calc() 实时计算，不写 achievement_stats
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional
import sqlite3
import re
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


@dataclass
class CalcResult:
    achieved: bool
    computed_value: int | None
    extra: object          # 额外数据（如 top_items 列表）
    achieved_at: str | None
    condition: str         # 显示用条件文案
    seasonal_type: str = "monthly"  # seasonal badge 的周期类型


# ─────────────────────────────────────────────────────────────────────────────
# 数据获取工具
# ─────────────────────────────────────────────────────────────────────────────

def _get_conn():
    return sqlite3.connect(_DB_PATH)


def _get_achievements(conn: sqlite3.Connection) -> list[dict]:
    """从 achievements 表读取所有定义，按 sort_order 排序"""
    cur = conn.execute("SELECT * FROM achievements ORDER BY sort_order")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _get_achievement_stats(conn: sqlite3.Connection) -> dict[str, dict]:
    """读 achievement_stats，返回 {id: {achieved, achieved_at, computed_value, ...}}"""
    cur = conn.execute("SELECT * FROM achievement_stats")
    cols = [d[0] for d in cur.description]
    return {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}


def _get_practice_dates(conn: sqlite3.Connection) -> list[str]:
    """所有练习日期，倒序"""
    cur = conn.execute("SELECT date FROM daily_practices ORDER BY date DESC")
    return [r[0] for r in cur.fetchall()]


def _get_total_mins(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices")
    return int(cur.fetchone()[0])


def _get_top_items(conn: sqlite3.Connection, limit: int = 3,
                   start: Optional[date] = None, end: Optional[date] = None) -> list[tuple[str, int]]:
    """累计时长前 N 科目。指定日期范围时做自然月/自然周过滤。"""
    where = ""
    params: list = []
    if start and end:
        where = " AND dp.date >= ? AND dp.date <= ? "
        params = [start.isoformat(), end.isoformat()]
    cur = conn.execute(f"""
        SELECT pi.name, SUM(je.value->>'$.minutes') as m
        FROM daily_practices dp, json_each(dp.items) je
        JOIN practice_items pi ON pi.item_id = je.value->>'$.item_id'
        WHERE pi.is_archived = 0 {where}
        GROUP BY pi.name ORDER BY m DESC LIMIT ?
    """, (*params, limit))
    return [(r[0], int(r[1])) for r in cur.fetchall()]


def _get_consecutive_streak(dates: list[str], today: date, min_mins: int = 10) -> int:
    """从今天往前数，连续每天有练习的天数"""
    streak = 0
    check = today
    for d in dates:
        if d == check.isoformat():
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


def _get_stage_range(conn: sqlite3.Connection) -> tuple[Optional[dict], Optional[dict]]:
    """
    返回（当前stage，上一个stage）的 {stage_start, stage_end, stage_order} 字典。
    当前 stage = MAX(stage_order)。上一个 = MAX(stage_order) - 1。
    """
    cur = conn.execute("""
        SELECT stage_order, stage_start, stage_end
        FROM weekly_assignments
        WHERE stage_order IS NOT NULL
        ORDER BY stage_order DESC LIMIT 2
    """)
    rows = cur.fetchall()
    if len(rows) < 2:
        return None, None
    prev = {"stage_order": rows[1][0], "stage_start": rows[1][1], "stage_end": rows[1][2]}
    curr = {"stage_order": rows[0][0], "stage_start": rows[0][1], "stage_end": rows[0][2]}
    return curr, prev


def _get_mins_in_range(conn: sqlite3.Connection, start: date, end: date) -> int:
    cur = conn.execute(
        "SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices WHERE date >= ? AND date <= ?",
        (start.isoformat(), end.isoformat()))
    return int(cur.fetchone()[0])


def _get_peak_week_mins(conn: sqlite3.Connection) -> int:
    """历史单周日累计时长最高值"""
    cur = conn.execute("""
        SELECT SUM(total_minutes) as wm, strftime('%Y-%W', date) as wy
        FROM daily_practices GROUP BY wy ORDER BY wm DESC LIMIT 1
    """)
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _get_peak_month_mins(conn: sqlite3.Connection) -> int:
    """历史单月日累计时长最高值"""
    cur = conn.execute("""
        SELECT SUM(total_minutes) as wm, strftime('%Y-%m', date) as my
        FROM daily_practices GROUP BY my ORDER BY wm DESC LIMIT 1
    """)
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _get_all_item_ids(conn: sqlite3.Connection) -> set[int]:
    cur = conn.execute("SELECT item_id FROM practice_items WHERE is_active=1")
    return {r[0] for r in cur.fetchall()}


def _has_all_items_today(conn: sqlite3.Connection, all_item_ids: set[int]) -> bool:
    if not all_item_ids:
        return False
    cur = conn.execute(
        "SELECT date, json_each.value->>'$.item_id' FROM daily_practices dp, json_each(dp.items)")
    day_items: dict[str, set[int]] = {}
    for day, iid in cur.fetchall():
        if iid:
            day_items.setdefault(day, set()).add(int(iid))
    all_dates = set(day_items.keys())
    return any(day_items.get(d, set()) == all_item_ids for d in all_dates)


def _has_double_practice(conn: sqlite3.Connection) -> bool:
    """是否存在同日 ≥2 条记录"""
    cur = conn.execute("""
        SELECT date, COUNT(*) as cnt FROM daily_practices
        GROUP BY date HAVING cnt >= 2
    """)
    return cur.fetchone() is not None


# ─────────────────────────────────────────────────────────────────────────────
# Milestone 计算（读 achievement_stats）
# ─────────────────────────────────────────────────────────────────────────────

def _calc_milestone(conn: sqlite3.Connection, aid: str,
                    stats: dict[str, dict],
                    streak: int, total_mins: int,
                    top_items: list[tuple[str, int]],
                    has_all_items: bool, has_double: bool) -> CalcResult:
    """计算单个 milestone 类型成就"""
    s = stats.get(aid, {})
    achieved = s.get("achieved", "N") == "Y"
    achieved_at = s.get("achieved_at")
    computed = s.get("computed_value")

    if aid == "streak_1":
        return CalcResult(streak >= 1, streak, None,
                          achieved_at if streak >= 1 else None, "连续 ≥ 1 天")
    if aid == "streak_3":
        return CalcResult(streak >= 3, streak, None,
                          achieved_at if streak >= 3 else None, "连续 ≥ 3 天")
    if aid == "streak_7":
        return CalcResult(streak >= 7, streak, None,
                          achieved_at if streak >= 7 else None, "连续 ≥ 7 天")
    if aid == "streak_14":
        return CalcResult(streak >= 14, streak, None,
                          achieved_at if streak >= 14 else None, "连续 ≥ 14 天")
    if aid == "streak_30":
        return CalcResult(streak >= 30, streak, None,
                          achieved_at if streak >= 30 else None, "连续 ≥ 30 天")
    if aid == "streak_100":
        return CalcResult(streak >= 100, streak, None,
                          achieved_at if streak >= 100 else None, "连续 ≥ 100 天")
    if aid == "total_300":
        return CalcResult(total_mins >= 300, total_mins, None,
                          achieved_at if total_mins >= 300 else None, "累计 ≥ 300 分钟")
    if aid == "total_600":
        return CalcResult(total_mins >= 600, total_mins, None,
                          achieved_at if total_mins >= 600 else None, "累计 ≥ 600 分钟")
    if aid == "total_1000":
        return CalcResult(total_mins >= 1000, total_mins, None,
                          achieved_at if total_mins >= 1000 else None, "累计 ≥ 1000 分钟")
    if aid == "first_log":
        return CalcResult(total_mins > 0, total_mins, None,
                          achieved_at if total_mins > 0 else None, "完成第一次练习")
    if aid == "all_items":
        return CalcResult(has_all_items, 1 if has_all_items else 0, None,
                          achieved_at if has_all_items else None, "同一天练所有科目")
    if aid == "double":
        return CalcResult(has_double, 1 if has_double else 0, None,
                          achieved_at if has_double else None, "同日 ≥ 2 次打卡")
    if aid in ("top1", "top2", "top3"):
        rank = int(aid[-1])
        ok = len(top_items) >= rank
        val = top_items[rank - 1][1] if ok else 0
        item_name = top_items[rank - 1][0] if ok else ""
        cond = f"累计时长第 {rank}：{item_name}({val}分钟)"
        return CalcResult(ok, val, item_name,
                          achieved_at if ok else None, cond)
    if aid.startswith("grade_"):
        g = int(aid.split("_")[1])
        row = stats.get(aid)
        if row:
            return CalcResult(row["achieved"] == "Y", g, None,
                              row.get("achieved_at"), f"考取 {g} 级")
        return CalcResult(False, 0, None, None, f"考取 {g} 级")

    return CalcResult(False, 0, None, None, "")


# ─────────────────────────────────────────────────────────────────────────────
# Seasonal 计算（实时，不写 achievement_stats）
# ─────────────────────────────────────────────────────────────────────────────

def _calc_seasonal(conn: sqlite3.Connection, aid: str,
                   seasonal_type: str,
                   today: date,
                   streak: int, total_mins: int,
                   all_item_ids: set[int]) -> CalcResult:
    """
    计算单个 seasonal 类型成就。返回 CalcResult，achieved_at=None（seasonal 无固定解锁日期）。
    seasonal_type: 'daily' | 'weekly' | 'monthly' | 'stage'
    """
    now_year, now_month = today.year, today.month

    # ── daily: 基于 stage 的每日打卡盲盒 ───────────────────────
    if seasonal_type == "daily":
        # 获取当前stage
        cur = conn.execute("""
            SELECT stage_start, stage_end, stage_order 
            FROM weekly_assignments 
            WHERE stage_order = (SELECT MAX(stage_order) FROM weekly_assignments)
        """)
        stage_row = cur.fetchone()
        if not stage_row:
            return CalcResult(False, 0, None, None, "无stage数据")
        
        stage_start_str, stage_end_str, stage_order = stage_row
        if not stage_start_str:
            return CalcResult(False, 0, None, None, "无stage数据")
        stage_start = date.fromisoformat(stage_start_str)
        # stage_end 为 NULL 时视为今天（当前 stage 尚未结束）
        stage_end = date.fromisoformat(stage_end_str) if stage_end_str else today
        
        # 计算今天是stage的第几天（1-7）
        stage_day = (today - stage_start).days + 1
        if stage_day < 1 or stage_day > 7:
            return CalcResult(False, 0, None, None, "不在stage范围内")
        
        # 计算本周打卡了几天
        cur = conn.execute("""
            SELECT COUNT(DISTINCT date) 
            FROM daily_practices 
            WHERE date >= ? AND date <= ?
        """, (stage_start_str, stage_end_str))
        checkin_days = cur.fetchone()[0]
        
        # 判断今天是否已打卡
        cur = conn.execute("""
            SELECT 1 FROM daily_practices WHERE date = ? LIMIT 1
        """, (today.isoformat(),))
        today_checked = cur.fetchone() is not None
        
        achieved = today_checked
        cond = f"Stage {stage_order} 第{stage_day}天，本周 {checkin_days}/7"
        
        return CalcResult(achieved, checkin_days, None, None, cond)

    # ── weekly: 自然周（周一~周日）周期 ─────────────────────────
    if seasonal_type == "weekly":
        # 当前自然周：周一 ~ 周日
        days_since_monday = today.weekday()  # Mon=0, Sun=6
        week_start = today - timedelta(days=days_since_monday)
        week_end   = week_start + timedelta(days=6)
        week_mins = _get_mins_in_range(conn, week_start, today)
        week_end_s = week_end if week_end <= today else today
        cond = f"本周累计 ≥ 10 分钟（当前 {week_mins} 分钟）"
        achieved = week_mins >= 10
        return CalcResult(achieved, week_mins, None, None, cond)

    # ── monthly: 自然月周期 ────────────────────────────────────
    if seasonal_type == "monthly":
        # 节日限定徽章（lucky_61_YYYY）走独立分支，不按"当月 60 分钟"判断
        if aid.startswith("lucky_61_") and len(aid) == len("lucky_61_2026"):
            try:
                y = int(aid[-4:])
                target = f"{y:04d}-06-01"
                cur = conn.execute(
                    "SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices WHERE date = ?",
                    (target,))
                mins = int(cur.fetchone()[0])
                achieved = mins > 0
                cond = f"{y}年6月1日当天练习（{mins}分钟）"
                return CalcResult(achieved, mins if achieved else 0, None, None, cond)
            except (ValueError, sqlite3.Error) as e:
                return CalcResult(False, 0, None, None, f"节日徽章解析失败: {e}")
        month_start = date(now_year, now_month, 1)
        if now_month == 12:
            month_end = date(now_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(now_year, now_month + 1, 1) - timedelta(days=1)
        month_mins = _get_mins_in_range(conn, month_start, today)
        achieved = month_mins >= 60
        cond = f"当月累计 ≥ 60 分钟（当前 {month_mins} 分钟）"
        return CalcResult(achieved, month_mins, None, None, cond)

    # ── stage: 课程赛季周期 ────────────────────────────────────
    # early_riser / little_chick_commander / first_to_act — 按小时判断
    # 2026-06-13 拍板: 永久解锁版 — 历史任意一天 enter_time CST hour < 阈值 → 永久解锁
    # (之前 "monthly_first_practice_before_X" 卡死 bug: 6/1 12:56 卡住全月, 6/13 早练不算)
    threshold_map = {"early_riser": 20, "little_chick_commander": 17, "first_to_act": 12}
    if aid in threshold_map:
        threshold = threshold_map[aid]
        # 找历史任意一天, 该天 practice_at 的 CST 小时 < threshold
        # practice_at 是 CST ISO 字符串 'YYYY-MM-DD HH:MM:SS[.fff]'
        cur = conn.execute(
            "SELECT date, practice_at FROM daily_practices "
            "WHERE practice_at IS NOT NULL AND practice_at != '' "
            "ORDER BY date ASC"
        )
        from datetime import datetime
        achieved = False
        achieved_date = None
        achieved_at = None
        for date_str, p_at in cur.fetchall():
            if not p_at:
                continue
            try:
                # CST ISO 'YYYY-MM-DD HH:MM:SS[.fff]' 取前 19 字符
                ts = datetime.strptime(p_at[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if ts.hour < threshold:
                achieved = True
                achieved_date = date_str
                achieved_at = p_at
                break  # 最早一次达成, 后续不用看
        if achieved:
            cond = f"首次达成 {achieved_date} {achieved_at[11:16]} (需早于{threshold}:00)"
        else:
            cond = f"暂无 {threshold}:00 前的练习记录"
        return CalcResult(achieved, threshold, None, achieved_at, cond)

    if aid == "total_60":
        month_start = date(now_year, now_month, 1)
        if now_month == 12:
            month_end = date(now_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(now_year, now_month + 1, 1) - timedelta(days=1)
        month_mins = _get_mins_in_range(conn, month_start, today)
        achieved = month_mins >= 60
        cond = f"当月累计 ≥ 60 分钟（当前 {month_mins} 分钟）"
        return CalcResult(achieved, month_mins, None, None, cond)

    if aid == "week_champ":
        curr_stage, prev_stage = _get_stage_range(conn)
        if not curr_stage or not prev_stage:
            return CalcResult(False, 0, None, None,
                              "暂无完整上下周数据")
        if not curr_stage.get("stage_end") or not curr_stage.get("stage_start"):
            return CalcResult(False, 0, None, None,
                              "本周数据不完整")
        if not prev_stage.get("stage_end") or not prev_stage.get("stage_start"):
            return CalcResult(False, 0, None, None,
                              "上周数据不完整")
        curr_start = date.fromisoformat(curr_stage["stage_start"])
        curr_end   = date.fromisoformat(curr_stage["stage_end"])
        prev_start = date.fromisoformat(prev_stage["stage_start"])
        prev_end   = date.fromisoformat(prev_stage["stage_end"])
        curr_mins = _get_mins_in_range(conn, curr_start, curr_end)
        prev_mins = _get_mins_in_range(conn, prev_start, prev_end)
        achieved = curr_mins > prev_mins
        cond = (f"本周 {curr_mins} > 上周 {prev_mins}，"
                f"阶段 {curr_stage['stage_order']} vs {prev_stage['stage_order']}")
        return CalcResult(achieved, curr_mins, prev_mins, None, cond)

    if aid == "full_month":
        this_month_start = date(now_year, now_month, 1)
        if now_month == 1:
            last_month_start = date(now_year - 1, 12, 1)
            last_month_end  = date(now_year - 1, 12, 31)
        else:
            last_month_start = date(now_year, now_month - 1, 1)
            last_month_end   = date(now_year, now_month, 1) - timedelta(days=1)
        this_mins = _get_mins_in_range(conn, this_month_start, today)
        last_mins = _get_mins_in_range(conn, last_month_start, last_month_end)
        achieved = this_mins > last_mins
        cond = f"本月 {this_mins} > 上月 {last_mins}"
        return CalcResult(achieved, this_mins, last_mins, None, cond)

    if aid == "top1":
        month_start = date(now_year, now_month, 1)
        month_top = _get_top_items(conn, limit=1, start=month_start, end=today)
        if month_top:
            item_name, mins = month_top[0]
            cond = f"当月第1：{item_name}（{mins}分钟）"
            return CalcResult(True, mins, item_name, None, cond)
        else:
            return CalcResult(False, 0, None, None, "当月第1科目（暂无数据）")

    return CalcResult(False, 0, None, None, "")


# ─────────────────────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────────────────────

def calc_all() -> dict[str, CalcResult]:
    """
    主力计算函数：返回所有成就的当前计算结果。
    milestone 读 achievement_stats；seasonal 实时计算。
    """
    conn = _get_conn()
    today = dt.date.today()

    achievements = _get_achievements(conn)
    stats        = _get_achievement_stats(conn)
    dates        = _get_practice_dates(conn)
    total_mins   = _get_total_mins(conn)
    top_items    = _get_top_items(conn, limit=3)
    all_item_ids = _get_all_item_ids(conn)
    has_all_items = _has_all_items_today(conn, all_item_ids)
    has_double    = _has_double_practice(conn)
    streak        = _get_consecutive_streak(dates, today)

    results: dict[str, CalcResult] = {}

    for ach in achievements:
        aid = ach["id"]
        cat = ach["category"]

        if cat == "seasonal":
            seasonal_type = ach.get("seasonal_type", "monthly")
            results[aid] = _calc_seasonal(
                conn, aid, seasonal_type, today, streak, total_mins, all_item_ids)
        else:  # milestone
            results[aid] = _calc_milestone(
                conn, aid, stats, streak, total_mins,
                top_items, has_all_items, has_double)

    conn.close()
    return results


def get_achievements_by_type(category: str) -> list[dict]:
    """按 category 过滤 achievements 表数据"""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM achievements WHERE category = ? ORDER BY sort_order",
        (category,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows


# 复用 datetime
import datetime as dt
