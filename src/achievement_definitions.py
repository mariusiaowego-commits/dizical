"""
dizical 成就定义统一数据源

- 所有成就元数据（从 achievements 表读取）
- milestone 类型：calc() 读 achievement_stats
- seasonal 类型：calc() 实时计算，不写 achievement_stats
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional
import sqlite3  # 保留类型 hint 用, 实际连接走 src.db_adapter
import logging
import re
from pathlib import Path

from . import db_adapter

logger = logging.getLogger(__name__)


_DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def _db_conn():
    """双后端连接入口. fix/achievements-mysql-conn (2026-07-24)
    替代老版 sqlite3.connect(_DB_PATH), 现在:
    - DATABASE_URL 以 mysql 开头 → 走 MySQLBackend 工厂
    - 否则 → SQLite 本地 (兼容本地开发)
    """
    return db_adapter.get_conn()


def _exec(conn, sql: str, params=()):
    """统一执行入口, 自动处理 SQLite `?` ↔ MySQL `%s` 占位符.
    返回 cursor, fetchall/fetchone 行为一致 (row factory 都是 tuple).
    """
    return db_adapter.execute(conn, sql, params)


def _to_date(v):
    """跨后端 date 字段归一化. SQLite 返 str 'YYYY-MM-DD', MySQL 返 datetime.date."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        return date.fromisoformat(v)
    raise TypeError(f"_to_date: unsupported type {type(v)}")


def _date_str(v) -> str | None:
    """Normalize SQLite date strings and MySQL DATETIME values to YYYY-MM-DD."""
    parsed = _to_date(v)
    return parsed.isoformat() if parsed is not None else None


@dataclass
class CalcResult:
    achieved: bool
    computed_value: int | None
    extra: object          # 额外数据（如 top_items 列表）
    achieved_at: str | None
    condition: str         # 显示用条件文案
    seasonal_type: str = "monthly"  # seasonal badge 的周期类型
    # 2026-08-07 sprint 26080702: seasonal badge 全期累计激活次数
    # milestone badge 默认 None, modal 不显示 season_info
    extra_count: int | None = None


# ─────────────────────────────────────────────────────────────────────────────
# 数据获取工具
# ─────────────────────────────────────────────────────────────────────────────

def _get_conn():
    return _db_conn()


def _get_achievements(conn: sqlite3.Connection) -> list[dict]:
    """从 achievements 表读取所有定义，按 sort_order 排序"""
    cur = _exec(conn, "SELECT * FROM achievements ORDER BY sort_order")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _get_achievement_stats(conn: sqlite3.Connection) -> dict[str, dict]:
    """读 achievement_stats，返回 {id: {achieved, achieved_at, computed_value, ...}}"""
    cur = _exec(conn, "SELECT * FROM achievement_stats")
    cols = [d[0] for d in cur.description]
    return {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}


def _get_practice_dates(conn: sqlite3.Connection) -> list[str]:
    """所有练习日期，倒序"""
    cur = _exec(conn, "SELECT date FROM daily_practices ORDER BY date DESC")
    return [_to_date(r[0]).isoformat() for r in cur.fetchall() if r[0] is not None]


def _get_total_mins(conn: sqlite3.Connection) -> int:
    cur = _exec(conn, "SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices")
    return int(cur.fetchone()[0])


def _get_top_items(conn: sqlite3.Connection, limit: int = 3,
                   start: Optional[date] = None, end: Optional[date] = None) -> list[tuple[str, int]]:
    """累计时长前 N 科目。指定日期范围时做自然月/自然周过滤。

    fix/achievements-mysql-conn (2026-07-24): 不用 SQLite 的 json_each, 改成
    拉 date+items + practice_items, Python 端解析 JSON 聚合, 跨后端通用.
    """
    import json as _json
    where = ""
    params: list = []
    if start and end:
        # 2026-08-03 修: 原 SQL 是 dp.date 但 from 没 alias, 报 no such column: dp.date
        where = " AND date >= ? AND date <= ? "
        params = [start.isoformat(), end.isoformat()]
    # 1. 拉所有 item_id -> name 映射 (活跃科目)
    cur = _exec(conn, "SELECT item_id, name FROM practice_items WHERE is_archived = 0")
    item_name = {int(r[0]): r[1] for r in cur.fetchall()}
    # 2. 拉日期范围内的 (date, items) (items 是 JSON 字符串)
    cur = _exec(conn,
        f"SELECT items FROM daily_practices WHERE 1=1 {where}",
        tuple(params))
    # 3. Python 端聚合 (item_id -> total minutes)
    minutes_by_id: dict[int, int] = {}
    for (items_str,) in cur.fetchall():
        if not items_str:
            continue
        try:
            items = _json.loads(items_str)
        except (ValueError, TypeError):
            continue
        for it in items:
            iid = it.get("item_id")
            mins = it.get("minutes") or 0
            if iid is None:
                continue
            minutes_by_id[int(iid)] = minutes_by_id.get(int(iid), 0) + int(mins)
    # 4. 转 name + 排序
    pairs = [(item_name.get(iid, f"?{iid}"), mins) for iid, mins in minutes_by_id.items()]
    pairs.sort(key=lambda x: x[1], reverse=True)
    return pairs[:limit]


def _get_consecutive_streak(dates: list[str], today: date, min_mins: int = 10) -> int:
    """从 today 往前数, 连续每天有练习的天数.

    2026-08-03 拍板: 若 today 没练, 从 yesterday 开始数 (之前 today 没练 → 0,
    对 streak_N progress 展示不友好, 用户看不到 "当前连续 9 天" 的进度).

    算法: 先尝试从 today 开始, 若 today 不在 dates, 从 today - 1 开始.
    """
    if not dates:
        return 0
    dset = set(dates)
    start = today if today.isoformat() in dset else today - timedelta(days=1)
    streak = 0
    check = start
    while check.isoformat() in dset:
        streak += 1
        check -= timedelta(days=1)
    return streak


def _get_stage_range(conn: sqlite3.Connection) -> tuple[Optional[dict], Optional[dict]]:
    """
    返回（当前stage，上一个stage）的 {stage_start, stage_end, stage_order} 字典。
    当前 stage = MAX(stage_order)。上一个 = MAX(stage_order) - 1。
    """
    cur = _exec(conn, """
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
    cur = _exec(conn, 
        "SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices WHERE date >= ? AND date <= ?",
        (start.isoformat(), end.isoformat()))
    return int(cur.fetchone()[0])


def _get_peak_week_mins(conn: sqlite3.Connection) -> int:
    """历史单周日累计时长最高值. fix/achievements-mysql-conn: Python group, 跨后端."""
    cur = _exec(conn, "SELECT date, total_minutes FROM daily_practices")
    from collections import defaultdict
    wk_mins = defaultdict(int)
    for d, m in cur.fetchall():
        if d is None or m is None: continue
        dt_v = _to_date(d)
        # ISO 周: (year, ISO week number)
        iy, iw, _ = dt_v.isocalendar()
        wk_mins[(iy, iw)] += int(m or 0)
    return max(wk_mins.values()) if wk_mins else 0


def _get_peak_month_mins(conn: sqlite3.Connection) -> int:
    """历史单月日累计时长最高值. fix/achievements-mysql-conn: Python group."""
    cur = _exec(conn, "SELECT date, total_minutes FROM daily_practices")
    from collections import defaultdict
    mo_mins = defaultdict(int)
    for d, m in cur.fetchall():
        if d is None or m is None: continue
        dt_v = _to_date(d)
        mo_mins[(dt_v.year, dt_v.month)] += int(m or 0)
    return max(mo_mins.values()) if mo_mins else 0


def _get_all_item_ids(conn: sqlite3.Connection) -> set[int]:
    """当前"未归档且活跃"科目全集.
    跟 get_practice_items(active_only=True) 保持一致 (is_active=1 AND is_archived=0).
    2026-06-13 修复: 之前没 is_archived 过滤, 跟 UI 视角不一致.
    """
    cur = _exec(conn, 
        "SELECT item_id FROM practice_items WHERE is_active=1 AND is_archived=0"
    )
    return {r[0] for r in cur.fetchall()}


def _get_latest_stage_item_ids(conn: sqlite3.Connection) -> set[int]:
    """最新 stage (MAX stage_order) 的 items 列表.
    2026-06-13: all_items 判定基准从"全局活跃 item 集"改成"最新 stage 老师要求集".
    """
    cur = _exec(conn, 
        "SELECT items FROM weekly_assignments "
        "WHERE stage_order = (SELECT MAX(stage_order) FROM weekly_assignments) "
        "LIMIT 1"
    )
    row = cur.fetchone()
    if not row or not row[0]:
        return set()
    import json as _json
    items = _json.loads(row[0])
    return {it["item_id"] for it in items if it.get("item_id")}


def _has_all_items_ever(conn: sqlite3.Connection) -> tuple[bool, str | None]:
    """判断 all_items 是否史上达成.

    语义 (2026-06-13 拍板): 历史任意一天, 该日练习 item 集 ⊇ 最新 stage 老师要求集.
    - 用最新 stage (MAX stage_order) 的 items 列表, 不是全局活跃集
    - 永久解锁版: 一次达成后永久保留
    - 用 "⊇" (superset) 而非 "==" 允许哪天多练

    Returns:
        (达成?, 最早达成日期 YYYY-MM-DD).
    """
    all_item_ids = _get_latest_stage_item_ids(conn)
    if not all_item_ids:
        return False, None
    # fix/achievements-mysql-conn (2026-07-24): 不用 SQLite json_each,
    # 改拉 date+items, Python 解析.
    cur = _exec(conn, "SELECT date, items FROM daily_practices")
    import json as _json
    day_items: dict[str, set[int]] = {}
    for date_str, items_str in cur.fetchall():
        if not items_str:
            continue
        try:
            items = _json.loads(items_str)
        except (ValueError, TypeError):
            continue
        iids = {int(it["item_id"]) for it in items if it.get("item_id")}
        if iids:
            day_items.setdefault(date_str, set()).update(iids)
    if not day_items:
        return False, None
    for day in sorted(day_items.keys()):
        if day_items[day] >= all_item_ids:
            return True, day
    return False, None


def _has_double_practice(conn: sqlite3.Connection) -> bool:
    """是否存在同日 ≥2 个 distinct session.

    daily_practices.date UNIQUE 约束导致同日第二次练习走 UPDATE 合并 items,
    永远不会出现 ≥2 条记录. 真正的"加练"语义看 behavior_log 里 distinct session_id 数.
    老 entries 没 session_id 算 1 个 session.
    """
    return _double_first_achieved_at(conn) is not None


# ─────────────────────────────────────────────────────────────────────────────
# 历史达成时间 helper (2026-06-13 添加: 让 _calc_milestone 能算出"首次达成日",
# 给 _persist_unlocked_milestones hook 写库用 — 之前 calc 只读 stats, 没有自动
# 持久化路径; 现在 calc 顺便算出达成日, 让所有"史上已达成"的 milestone 自动解锁).
# ─────────────────────────────────────────────────────────────────────────────

def _first_practice_date(conn: sqlite3.Connection) -> str | None:
    """全练习最早一条日期 (total_minutes > 0)."""
    cur = _exec(conn, 
        "SELECT MIN(date) FROM daily_practices WHERE total_minutes > 0"
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def _streak_first_achieved_at(conn: sqlite3.Connection, n: int) -> str | None:
    """史上首次达成"连续 ≥ n 天"打卡的日期.

    算法: DISTINCT date 正序扫, 维护 streak, 第一次 streak >= n 那一天.
    首次练习那一天就是 streak=1 (达成 streak_1).
    """
    cur = _exec(conn, 
        "SELECT DISTINCT date FROM daily_practices "
        "WHERE total_minutes > 0 ORDER BY date"
    )
    dates = [_date_str(r[0]) for r in cur.fetchall() if _date_str(r[0]) is not None]
    if len(dates) < n:
        return None
    if n == 1:
        return dates[0]  # 首次练习日就是 streak_1 达成日
    streak = 1
    for i in range(1, len(dates)):
        prev = _to_date(dates[i - 1])
        curr = _to_date(dates[i])
        if (curr - prev).days == 1:
            streak += 1
            if streak >= n:
                return dates[i]
        else:
            streak = 1
    return None


def _recovery_current_streak(conn: sqlite3.Connection, injury_date: str, today: date) -> int:
    """烫伤后当前连续天数 (从 today 往前数, 必须 >= injury_date).

    2026-08-03 拍板: 跟 _get_consecutive_streak 一致 — today 没练时从 yesterday 开始数,
    让用户看到 "当前连续 N/21" 的进度 (而不是 0).
    """
    cur = _exec(conn,
        "SELECT DISTINCT date FROM daily_practices "
        "WHERE total_minutes > 0 AND date >= ? AND date <= ? ORDER BY date DESC",
        (injury_date, today.isoformat()),
    )
    dates = [_date_str(r[0]) for r in cur.fetchall() if _date_str(r[0]) is not None]
    if not dates:
        return 0
    dset = set(dates)
    start = today if today.isoformat() in dset else today - timedelta(days=1)
    streak = 0
    check = start
    while check.isoformat() in dset and check.isoformat() >= injury_date:
        streak += 1
        check -= timedelta(days=1)
    return streak


def _recovery_practice_count(conn: sqlite3.Connection, injury_date: str) -> int:
    """烫伤后累计打卡天数 (DISTINCT date, total_minutes > 0, date >= injury_date)."""
    cur = _exec(conn,
        "SELECT DISTINCT date FROM daily_practices "
        "WHERE total_minutes > 0 AND date >= ?",
        (injury_date,),
    )
    dates = {_date_str(r[0]) for r in cur.fetchall() if _date_str(r[0]) is not None}
    return len(dates)


def _recovery_first_achieved_at(conn: sqlite3.Connection, injury_date: str, n: int) -> str | None:
    """烫伤/事故后累计打卡天数首次 >= n 的最早日期.

    2026-08-13 拍板 (按 A): 语义改为"累计打卡", 不是"连续".
    模板抄自 _total_first_achieved_at, 加 WHERE date >= injury_date 过滤.
    """
    cur = _exec(conn,
        "SELECT DISTINCT date FROM daily_practices "
        "WHERE total_minutes > 0 AND date >= ? ORDER BY date",
        (injury_date,),
    )
    dates = [_date_str(r[0]) for r in cur.fetchall() if _date_str(r[0]) is not None]
    if len(dates) < n:
        return None
    return dates[n - 1]


def _total_first_achieved_at(conn: sqlite3.Connection, threshold_mins: int) -> str | None:
    """累计 total_minutes 首次 ≥ threshold_mins 的日期 (按 date 正序累加)."""
    cur = _exec(conn, 
        "SELECT date, total_minutes FROM daily_practices "
        "WHERE total_minutes > 0 ORDER BY date"
    )
    cumulative = 0
    for date_str, mins in cur.fetchall():
        cumulative += int(mins or 0)
        if cumulative >= threshold_mins:
            return date_str
    return None


def _double_first_achieved_at(conn: sqlite3.Connection) -> str | None:
    """史上首次同日 ≥2 个 distinct session 的最早日期.

    算法: 遍历每日 behavior_log, 统计 distinct session_id 数, ≥2 则算达成.
    老 entries (无 session_id) 算 1 个 session, 自然不会触发 false-positive.
    """
    cur = _exec(conn,
        "SELECT date, behavior_log FROM daily_practices "
        "WHERE behavior_log IS NOT NULL AND behavior_log != '[]' "
        "ORDER BY date"
    )
    import json as _json
    for date_str, log_str in cur.fetchall():
        try:
            entries = _json.loads(log_str)
        except (ValueError, TypeError):
            continue
        sessions = {e["session_id"] for e in entries if e.get("session_id") is not None}
        if len(sessions) >= 2:
            return date_str
    return None


def _one_breath_first_achieved_at(conn: sqlite3.Connection) -> str | None:
    """史上首次出现单个练习科目 ≥10 分钟的日期.

    遍历 daily_practices.items JSON, 找第一个 minutes >= 10 的 item.
    """
    cur = _exec(conn, 
        "SELECT date, items FROM daily_practices ORDER BY date"
    )
    import json as _json
    for date_str, items_str in cur.fetchall():
        try:
            items = _json.loads(items_str)
        except (ValueError, TypeError):
            continue
        for item in items:
            if item.get("minutes", 0) >= 10:
                return date_str
    return None


def _top_first_achieved_at(conn: sqlite3.Connection, rank: int) -> str | None:
    """某科目累计时长排第 N 名 — 给出"历史上累计达到该名次门槛"的最早日期.

    简化算法: 用当前 topN 中最小的累计时长作为门槛, 累计首次达该值的最早日期.
    (这个语义对儿童成就展示足够, 不区分具体哪个 item.)
    """
    top = _get_top_items(conn, limit=rank)
    if len(top) < rank:
        return None
    target_min = top[-1][1]
    return _total_first_achieved_at(conn, target_min)


# ─────────────────────────────────────────────────────────────────────────────
# Milestone 计算（读 achievement_stats）
# ─────────────────────────────────────────────────────────────────────────────

def _calc_milestone(conn: sqlite3.Connection, aid: str,
                    stats: dict[str, dict],
                    streak: int, total_mins: int,
                    top_items: list[tuple[str, int]],
                    has_all_items: bool, all_items_achieved_at: str | None,
                    has_double: bool,
                    today: date) -> CalcResult:
    """计算单个 milestone 类型成就.

    achieved_at 优先 stats (历史已写入, 不可变), 否则用 helper 算首次达成日.
    这样 _persist_unlocked_milestones hook 写库时能拿到非 None 时间.
    """
    s = stats.get(aid, {})
    stat_achieved = s.get("achieved", "N") == "Y"
    stat_achieved_at = s.get("achieved_at")

    # 决定 achieved_at: stats 已 Y 用 stats 时间, 否则算首次达成日
    def _at(calc_achieved: bool, computed_at: str | None) -> str | None:
        if stat_achieved and stat_achieved_at:
            return stat_achieved_at
        return computed_at if calc_achieved else None

    # ── sprint badge-batch-261017 (2026-10-17): 练习记录型 milestone (30 枚) ──
    # 判定全部基于 practice_sessions / daily_practices 的可靠字段
    # (item_id / 时长 / tempo / 日期), 规则表在文件末尾 PRACTICE_BADGE_RULES。
    # 不在规则表里 → 返回 None, 落回下面的原有链路。
    _practice = _calc_practice_badge(conn, aid, stats)
    if _practice is not None:
        return _practice

    # ── streak_* 系列: 史上首次达成"连续 ≥ n 天"即永久解锁 ──────
    # 2026-07-01 拍板: 之前用"今日 streak"是错的 — 今天没练 streak=0
    # → milestone 永远不解锁. milestone 必须走历史首次.
    # 2026-08-03 拍板: 未解锁时, 模板展示"当前连续 X 天, 还差 N-X 天"进度.
    # computed_value 传 streak (当前), 让模板拼"还差多少".
    if aid.startswith("streak_") and aid[7:].isdigit():
        n = int(aid.split("_")[1])
        first_at = _streak_first_achieved_at(conn, n)
        achieved = first_at is not None
        if achieved:
            cond = f"你在 {first_at} 第一次连着打卡 {n} 天"
        else:
            cur_streak_val = streak  # 全局 streak (从今天往前数)
            gap = max(0, n - cur_streak_val)
            cond = f"连着打卡 {n} 天就能拿到（当前连续 {cur_streak_val} 天，还差 {gap} 天）"
        return CalcResult(achieved, n if achieved else streak, None, first_at, cond)

    # ── recovery_first_practice_7 / 14 / 21 系列: 烫伤后累计打卡 7/14/21 天 ─────
    # 2026-07-14 拍板: 烫伤日 2026-07-08 (左手小臂烫伤, 脸大小一块)
    # 2026-08-13 拍板 (按 A): 语义改为"累计打卡", 不是"连续".
    # 不要求连续 — 累计 21 天任意分布都达成.
    # 跟 streak_* 区别: streak 是全历史连续, recovery 是烫伤后累计.
    # 未解锁时, 模板展示"自烫伤日 X 起算累计, 当前 Y/N 天".
    if aid in ("recovery_first_practice_7", "recovery_first_practice_14", "recovery_first_practice_21"):
        n = int(aid.rsplit("_", 1)[-1])
        injury_date = "2026-07-08"  # 烫伤日 (2026-07-14 拍板, 写死, 后续事故再加新 aid)
        first_at = _recovery_first_achieved_at(conn, injury_date, n)
        achieved = first_at is not None
        cur_count = _recovery_practice_count(conn, injury_date)
        if achieved:
            cond = f"你在 {first_at} 烫伤后累计打卡 {n} 天"
        else:
            gap = max(0, n - cur_count)
            cond = f"自{injury_date}起累计打卡 {n} 天（当前 {cur_count}/{n}，还差 {gap} 天）"
        return CalcResult(achieved, n if achieved else cur_count, None, first_at, cond)

    # ── lucky_61_YYYY 系列: 六一节永久里程碑 ─────────────────────
    # 2026-07-01 拍板: 用户认为这是 milestone (永久徽章, 像考级一样).
    # 之前 seasonal/monthly 走"当月 60 分钟" — 跟节日语义不符.
    # 改成 milestone: 对应年份 06-01 当天练过 (total_minutes > 0) → 永久解锁.
    # 注意: achievements 表里的 category/seasonal_type 字段保持不动 (V2 数据契约).
    # calc_milestone 用 aid 前缀识别即可.
    if aid.startswith("lucky_61_") and aid[9:].isdigit():
        try:
            y = int(aid[9:])
            target = f"{y:04d}-06-01"
            cur = _exec(conn, 
                "SELECT MIN(date), COALESCE(SUM(total_minutes), 0) "
                "FROM daily_practices WHERE date = ?",
                (target,))
            row = cur.fetchone()
            first_at = row[0] if row else None
            mins = int(row[1]) if row and row[1] else 0
            achieved = first_at is not None and mins > 0
            # 2026-07-01 拍板: cond 改成小朋友能懂 (之前"2026年6月1日当天练习过（29 分钟）"工程味)
            if achieved:
                cond = f"你在 {target} 六一儿童节当天练过竹笛 ({mins} 分钟)"
            else:
                cond = f"{y}年6月1日练习就能拿到"
            return CalcResult(achieved, mins if achieved else 0, None,
                              first_at, cond)
        except (ValueError, sqlite3.Error):
            pass
    if aid == "total_300":
        at = _at(total_mins >= 300, _total_first_achieved_at(conn, 300))
        return CalcResult(total_mins >= 300, total_mins, None, at, "累计 ≥ 300 分钟")
    if aid == "total_600":
        at = _at(total_mins >= 600, _total_first_achieved_at(conn, 600))
        return CalcResult(total_mins >= 600, total_mins, None, at, "累计 ≥ 600 分钟")
    if aid == "total_1000":
        at = _at(total_mins >= 1000, _total_first_achieved_at(conn, 1000))
        return CalcResult(total_mins >= 1000, total_mins, None, at, "累计 ≥ 1000 分钟")
    if aid == "first_log":
        at = _at(total_mins > 0, _first_practice_date(conn))
        return CalcResult(total_mins > 0, total_mins, None, at, "完成第一次练习")
    if aid == "all_items":
        at = _at(has_all_items, all_items_achieved_at)
        if has_all_items:
            cond = f"首次达成 {all_items_achieved_at} 一天内练齐最新 stage 老师布置的所有科目"
        else:
            # 列出"最新 stage 还差哪些"给用户清晰反馈
            latest_ids = _get_latest_stage_item_ids(conn)
            cur = _exec(conn, 
                "SELECT name FROM practice_items WHERE is_active=1 AND item_id IN ("
                + ",".join("?" * len(latest_ids)) + ") ORDER BY item_id",
                list(latest_ids)) if latest_ids else []
            required_names = [r[0] for r in cur]
            cond = f"最新 stage 要求 {len(latest_ids)} 个科目: {', '.join(required_names) if required_names else '(无)'} — 还没达成"
        return CalcResult(has_all_items, 1 if has_all_items else 0, None,
                          at, cond)
    if aid == "double":
        at = _at(has_double, _double_first_achieved_at(conn))
        return CalcResult(has_double, 1 if has_double else 0, None, at, "同日 ≥ 2 次打卡")

    if aid == "one_breath":
        achieved_at_val = _one_breath_first_achieved_at(conn)
        ok = achieved_at_val is not None
        at = _at(ok, achieved_at_val)
        return CalcResult(ok, 1 if ok else 0, None, at, "单个科目一口气练 ≥ 10 分钟")

    if aid == "night_owl":
        # V2.5 (2026-06-16): 加 night_owl calc 规则.
        # 用户 phase2 拍板: 晚上 8 点后 (CST 20:00) 还在练习
        # 跟 early_riser/little_chick_commander/first_to_act 一样的 pattern (PR #87 era 拍板
        # '永久解锁版'): 历史任意一天 practice_at CST hour >= 20 → 永久解锁.
        # fix/achievements-mysql-conn: 不用 SQLite strftime, Python 端解析.
        cur = _exec(conn,
            "SELECT practice_at FROM daily_practices WHERE practice_at IS NOT NULL"
        )
        first_at: str | None = None
        for (pat,) in cur.fetchall():
            if not pat:
                continue
            # practice_at 格式: 'YYYY-MM-DD HH:MM:SS' (SQLite 返 str, MySQL 返 datetime)
            pat_str = str(pat)
            if len(pat_str) < 13:
                continue
            hour_part = pat_str[11:13]
            try:
                hour = int(hour_part)
            except ValueError:
                continue
            if hour >= 20:
                first_at = pat_str[:10]
                break
        return CalcResult(first_at is not None, 1 if first_at else 0, None,
                          first_at, "晚上 8 点后 (CST 20:00) 还在练习")

    if aid in ("top1", "top2", "top3"):
        rank = int(aid[-1])
        ok = len(top_items) >= rank
        val = top_items[rank - 1][1] if ok else 0
        item_name = top_items[rank - 1][0] if ok else ""
        cond = f"累计时长第 {rank}：{item_name}({val}分钟)"
        at = _at(ok, _top_first_achieved_at(conn, rank)) if ok else None
        return CalcResult(ok, val, item_name, at, cond)
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

    # ── daily: 基于 stage 的每日打卡 (seasonal daily 成就) ────────
    if seasonal_type == "daily":
        # 获取当前stage
        cur = _exec(conn, """
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
        cur = _exec(conn, """
            SELECT COUNT(DISTINCT date) 
            FROM daily_practices 
            WHERE date >= ? AND date <= ?
        """, (stage_start_str, stage_end_str))
        checkin_days = cur.fetchone()[0]
        
        # 判断今天是否已打卡
        cur = _exec(conn, """
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
    # 2026-08-03 拍板: dispatch bug 修复. 之前 monthly fallback 走到 line 717 就 return,
    # 导致 threshold_map / total_60 / week_champ / full_month / top1 等 aid-specific
    # 分支永远走不到 (db 里所有 seasonal badge seasonal_type 都是 "monthly").
    # 改为: 先尝试 aid-specific 分支, 都不命中才走月度通用 fallback.
    if seasonal_type == "monthly":
        # 节日限定徽章（lucky_61_YYYY）
        if aid.startswith("lucky_61_") and len(aid) == len("lucky_61_2026"):
            try:
                y = int(aid[-4:])
                target = f"{y:04d}-06-01"
                cur = _exec(conn,
                    "SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices WHERE date = ?",
                    (target,))
                mins = int(cur.fetchone()[0])
                achieved = mins > 0
                # 2026-07-01 拍板: cond 改成小朋友能懂
                if achieved:
                    cond = f"你在 {target} 六一儿童节当天练过竹笛 ({mins} 分钟)"
                else:
                    cond = f"{y}年6月1日练习就能拿到"
                return CalcResult(achieved, mins if achieved else 0, None, None, cond)
            except (ValueError, sqlite3.Error) as e:
                return CalcResult(False, 0, None, None, f"节日徽章解析失败: {e}")

        # 早练类（按小时判断, monthly 重置 — 跟 total_60 同模式）
        # 2026-08-07 sprint 26080701: dad 拍板 "seasonal badge 应该按月算", 跟 DB 字段 category=seasonal/seasonal_type=monthly 一致.
        # 之前代码是"全历史首次达成即永久解锁", 跟 category=seasonal 矛盾.
        threshold_map = {"early_riser": 20, "little_chick_commander": 17, "first_to_act": 12}
        if aid in threshold_map:
            threshold = threshold_map[aid]
            month_start = date(now_year, now_month, 1)
            if now_month == 12:
                month_end = date(now_year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(now_year, now_month + 1, 1) - timedelta(days=1)
            cur = _exec(conn,
                "SELECT date, practice_at FROM daily_practices "
                "WHERE practice_at IS NOT NULL "
                "AND date >= ? AND date <= ? "
                "ORDER BY date ASC",
                (month_start.isoformat(), month_end.isoformat())
            )
            from datetime import datetime
            achieved = False
            achieved_date = None
            achieved_at = None
            for date_str, p_at in cur.fetchall():
                if not p_at:
                    continue
                try:
                    # 双后端兼容: SQLite practice_at 是 str, MySQL 是 datetime 对象
                    # datetime 不支持切片, 必须先 str() (pitfall 38, sprint 26080701)
                    ts = datetime.strptime(str(p_at)[:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if ts.hour < threshold:
                    achieved = True
                    achieved_date = date_str
                    achieved_at = p_at
                    break
            if achieved:
                cond = f"{now_year}-{now_month:02d} 本月首次早于 {threshold}:00 练习: {str(achieved_date)[:10]} {str(achieved_at)[11:16]}"
            else:
                cond = f"{now_year}-{now_month:02d} 本月暂无 {threshold}:00 前的练习记录"
            # 2026-08-07 sprint 26080702: 全期累计激活次数
            cnt, _hist = _count_seasonal_activations(conn, aid, threshold=threshold)
            return CalcResult(achieved, threshold, None, achieved_at, cond,
                              extra_count=cnt)

        # total_60: 当月累计 ≥ 60 分钟
        if aid == "total_60":
            month_start = date(now_year, now_month, 1)
            if now_month == 12:
                month_end = date(now_year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(now_year, now_month + 1, 1) - timedelta(days=1)
            month_mins = _get_mins_in_range(conn, month_start, today)
            achieved = month_mins >= 60
            cond = f"当月累计 ≥ 60 分钟（当前 {month_mins} 分钟）"
            # 2026-08-07 sprint 26080702: 全期累计 (当月 ≥ 60 分钟的月数)
            cnt, _hist = _count_seasonal_activations(
                conn, aid, threshold=None,
                threshold_check_fn=lambda r: int(r.get("total_minutes", 0) or 0) >= 60,
            )
            return CalcResult(achieved, month_mins, None, None, cond, extra_count=cnt)

        # week_champ: 本周 vs 上周 stage 对比
        if aid == "week_champ":
            curr_stage, prev_stage = _get_stage_range(conn)
            if not curr_stage or not prev_stage:
                return CalcResult(False, 0, None, None, "暂无完整上下周数据")
            if not curr_stage.get("stage_end") or not curr_stage.get("stage_start"):
                return CalcResult(False, 0, None, None, "本周数据不完整")
            if not prev_stage.get("stage_end") or not prev_stage.get("stage_start"):
                return CalcResult(False, 0, None, None, "上周数据不完整")
            curr_start = _to_date(curr_stage["stage_start"])
            curr_end   = _to_date(curr_stage["stage_end"])
            prev_start = _to_date(prev_stage["stage_start"])
            prev_end   = _to_date(prev_stage["stage_end"])
            if not (curr_start and curr_end and prev_start and prev_end):
                return CalcResult(False, 0, None, None, "阶段日期解析失败")
            curr_mins = _get_mins_in_range(conn, curr_start, curr_end)
            prev_mins = _get_mins_in_range(conn, prev_start, prev_end)
            achieved = curr_mins > prev_mins
            cond = (f"本周 {curr_mins} > 上周 {prev_mins}，"
                    f"阶段 {curr_stage.get('stage_order', '?')} vs {prev_stage.get('stage_order', '?')}")
            # 2026-08-07 sprint 26080702: 全期累计 (MVP)
            cnt, _hist = _count_seasonal_activations(
                conn, aid, threshold=None,
                threshold_check_fn=lambda r: True,
            )
            return CalcResult(achieved, curr_mins, prev_mins, None, cond, extra_count=cnt)

        # full_month: 本月 vs 上月
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
            cond = f"本月 {this_mins} 分钟 > 上月 {last_mins} 分钟"
            # 2026-08-07 sprint 26080702: 全期累计 (MVP)
            cnt_fm, _hist = _count_seasonal_activations(
                conn, aid, threshold=None,
                threshold_check_fn=lambda r: True,
            )
            return CalcResult(achieved, this_mins, last_mins, None, cond, extra_count=cnt_fm)

        # top1: 当月第 1 名科目
        if aid == "top1":
            month_start = date(now_year, now_month, 1)
            month_top = _get_top_items(conn, limit=1, start=month_start, end=today)
            if month_top:
                item_name, mins = month_top[0]
                cond = f"当月第1：{item_name}（{mins}分钟）"
                # 2026-08-07 sprint 26080702: 全期累计 (MVP)
                cnt_top1s, _hist = _count_seasonal_activations(
                    conn, aid, threshold=None,
                    threshold_check_fn=lambda r: True,
                )
                return CalcResult(True, mins, item_name, None, cond, extra_count=cnt_top1s)
            else:
                # 2026-08-07 sprint 26080702: 全期累计
                cnt_top1f, _hist = _count_seasonal_activations(
                    conn, aid, threshold=None,
                    threshold_check_fn=lambda r: True,
                )
                return CalcResult(False, 0, None, None, "当月第1科目（暂无数据）", extra_count=cnt_top1f)

        # ── fallback: 当月累计 ≥ 60 分钟 (其他未知 monthly badge) ──
        month_start = date(now_year, now_month, 1)
        if now_month == 12:
            month_end = date(now_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(now_year, now_month + 1, 1) - timedelta(days=1)
        month_mins = _get_mins_in_range(conn, month_start, today)
        achieved = month_mins >= 60
        cond = f"当月累计 ≥ 60 分钟（当前 {month_mins} 分钟）"
        return CalcResult(achieved, month_mins, None, None, cond)

    return CalcResult(False, 0, None, None, "")


# ─────────────────────────────────────────────────────────────────────────────
# 公开 API
# ─────────────────────────────────────────────────────────────────────────────

def _persist_unlocked_milestones(conn: sqlite3.Connection,
                                results: dict[str, CalcResult]) -> None:
    """把 calc_all() 算出来的新解锁 milestone 写进 achievement_stats.

    2026-08-07 sprint 26080702: 同时持久化 seasonal badge 的 extra_count + history_periods 到
    raw_stats JSON (append-only, 老 raw_stats '{}' 兼容). 改 calc 不动 grade_*.

    条件: calc.achieved=True AND calc.achieved_at != None AND stats.achieved != 'Y'.
    """
    import json as _json
    for aid, res in results.items():
        if not res.achieved or not res.achieved_at:
            continue
        cur = _exec(conn,
            "SELECT achieved, raw_stats FROM achievement_stats WHERE achievement_id = ?", (aid,)
        )
        row = cur.fetchone()
        # 解析现有 raw_stats JSON (append 不覆盖)
        existing_stats: dict = {}
        if row is not None and row[1]:
            try:
                existing_stats = _json.loads(row[1])
            except (TypeError, ValueError):
                existing_stats = {}

        # 2026-08-07 sprint 26080702: extra_count + history_periods (seasonal badge)
        if res.extra_count is not None:
            current_period = str(res.achieved_at)[:7]  # 'YYYY-MM'
            history_periods = list(existing_stats.get("history_periods", []))
            if current_period not in history_periods:
                history_periods.append(current_period)
            existing_stats["history_periods"] = history_periods
            existing_stats["count"] = res.extra_count
        raw_stats_json = _json.dumps(existing_stats, ensure_ascii=False, sort_keys=True)

        if row is None:
            _exec(conn,
                "INSERT INTO achievement_stats "
                "(achievement_id, achieved, achieved_at, raw_stats, computed_value) "
                "VALUES (?, 'Y', ?, ?, ?)",
                (aid, res.achieved_at, raw_stats_json, str(res.computed_value or "1")),
            )
        elif row[0] != "Y":
            _exec(conn,
                "UPDATE achievement_stats SET achieved='Y', achieved_at=?, raw_stats=? "
                "WHERE achievement_id=? AND achieved != 'Y'",
                (res.achieved_at, raw_stats_json, aid),
            )
        else:
            # 已 achieved, 只更新 raw_stats (count + history_periods)
            _exec(conn,
                "UPDATE achievement_stats SET raw_stats=? WHERE achievement_id=?",
                (raw_stats_json, aid),
            )
    conn.commit()




def _count_seasonal_activations(conn, aid: str, threshold: int | None = None,
                                 threshold_check_fn=None) -> tuple[int, list[str]]:
    """扫历史 daily_practices, 算全期累计激活次数 + 历史激活月份列表.

    Args:
        conn: db connection
        aid: achievement_id (for future per-aid logic, currently unused)
        threshold: 小时阈值 (e.g. 20 for early_riser). None 走 custom check fn.
        threshold_check_fn: 自定义 check 函数, 接受 daily_practices row dict, 返 bool.
            用于 week_champ/full_month/top1/total_60 这类非小时阈值.

    Returns:
        (count, history_periods) — count 全期累计激活月数, history_periods 升序 'YYYY-MM' 列表

    性能: daily_practices ~250 行, 每月 group 一次 + dict count. <50ms.
    """
    from collections import defaultdict
    cur = _exec(conn,
        "SELECT date, practice_at, total_minutes, items FROM daily_practices "
        "ORDER BY date ASC"
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    rows_dict = [dict(zip(cols, r)) for r in rows]

    monthly_achieved: dict[str, bool] = defaultdict(bool)
    for row in rows_dict:
        date_str = str(row.get("date", ""))[:7]  # YYYY-MM
        if not date_str or date_str == "":
            continue
        if threshold_check_fn is not None:
            if threshold_check_fn(row):
                monthly_achieved[date_str] = True
        elif threshold is not None:
            pat = row.get("practice_at")
            if not pat:
                continue
            from datetime import datetime
            try:
                ts = datetime.strptime(str(pat)[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if ts.hour < threshold:
                monthly_achieved[date_str] = True

    history_periods = sorted(monthly_achieved.keys())
    count = sum(1 for v in monthly_achieved.values() if v)
    return count, history_periods


def calc_all() -> dict[str, CalcResult]:
    """
    主力计算函数：返回所有成就的当前计算结果。
    milestone 读 achievement_stats；seasonal 实时计算。
    calc 完毕自动把新解锁的 milestone 写进 stats (持久化 hook).
    """
    conn, _is_mysql = _get_conn()
    try:
        today = dt.date.today()

        achievements = _get_achievements(conn)
        stats        = _get_achievement_stats(conn)
        dates        = _get_practice_dates(conn)
        total_mins   = _get_total_mins(conn)
        top_items    = _get_top_items(conn, limit=3)
        all_item_ids = _get_all_item_ids(conn)
        has_all_items, all_items_achieved_at = _has_all_items_ever(conn)
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
                    top_items, has_all_items, all_items_achieved_at, has_double, today)

        # 持久化 hook: 把新解锁的 milestone 写进 stats
        _persist_unlocked_milestones(conn, results)

        return results
    finally:
        # MySQL 侧是池连接: close = 归还池; 异常路径也必须归还 (旧写法只在成功路径 close)
        conn.close()


def get_achievements_by_type(category: str) -> list[dict]:
    """按 category 过滤 achievements 表数据"""
    conn, _is_mysql = _get_conn()
    try:
        cur = _exec(conn, 
            "SELECT * FROM achievements WHERE category = ? ORDER BY sort_order",
            (category,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


# 复用 datetime
import datetime as dt


# ═════════════════════════════════════════════════════════════════════════════
# sprint badge-batch-261017 (2026-10-17): 练习记录型 milestone calc (30 枚)
# -----------------------------------------------------------------------------
# 这批徽章的条件全部建立在**真实练习记录**上, 数据源:
#   practice_sessions  practice_date / item_id / duration_minutes / tempo_bpm
#   daily_practices    date / total_minutes
#   practice_items     曲目 / 技巧的 item_id (见 PIECE_ITEM_IDS)
#
# 设计要点 (踩坑留痕, 改本段前先读):
#   1. practice_sessions.content 是**手打自由文本** ("最后两行 （♬=120）" / "一次不错" /
#      "全曲（#4注意手指远离指孔）"), 口径会随录入漂移 → 本段**一律不用 content 判定**,
#      只用 item_id / 时长 / tempo / 日期 四个可靠字段。
#   2. practice_sessions.reps 目前**全 NULL** (没有任何写入路径) → "重复几遍"类条件
#      不可算, 对应徽章走 unlock_strategy='immediate' 手动点亮, 不进本表。
#   3. _persist_unlocked_milestones 只在 **achieved_at 非 None** 时落库 → 每个分支
#      必须返回"首次达成日", 否则徽章永远停在灰卡 (2026-07-01 streak 事故同款)。
#   4. 表可能不存在 (老库 / 单测临时库) → _ps_sessions 返空表, 不抛异常。
#   5. 农历节日的公历日期是**查实后硬编码**的 (来源 usemooncal 农历换算, 2026-10-17),
#      只覆盖 2026~2030; 2031 起需要补表, 否则节日徽章不再解锁 (不报错)。
# ═════════════════════════════════════════════════════════════════════════════

# 曲目类 item_id (练习记录里真实存在的考级曲目)
PIECE_ITEM_IDS: tuple[int, ...] = (1004, 1026, 1340, 1346, 1348, 1351, 1352)

# 农历/节气节日的公历日期 (2026-2030)
HOLIDAY_DATES: dict[str, tuple[str, ...]] = {
    "mid_autumn": ("2026-09-25", "2027-09-15", "2028-10-03", "2029-09-22", "2030-09-12"),
    "spring_festival": ("2026-02-17", "2027-02-06", "2028-01-26", "2029-02-13", "2030-02-03"),
    "dragon_boat": ("2026-06-19", "2027-06-09", "2028-05-28", "2029-06-16", "2030-06-05"),
    "winter_solstice": ("2026-12-22", "2027-12-22", "2028-12-21", "2029-12-21", "2030-12-22"),
}


def _ps_sessions(conn) -> list[tuple[str, int, int, int]]:
    """读 practice_sessions → [(date, item_id, minutes, tempo)], 按日期升序。

    表不存在 / 字段异常 → 跳过该行 (不抛)。SQLite / MySQL 双后端走 _exec。
    """
    try:
        cur = _exec(conn, "SELECT practice_date, item_id, duration_minutes, tempo_bpm "
                          "FROM practice_sessions")
        rows = cur.fetchall()
    except Exception as e:                                    # noqa: BLE001
        # 表缺失 / SQL 失败 ⇒ 本轮视为 0 段练习。必须吞掉 (抛出去会打断整轮 calc_all,
        # 30 枚徽章一起不亮), 但一定要留一条日志 —— 否则线上集体不亮时毫无线索。
        logger.warning("practice_sessions 读取失败, 本轮 calc 视为 0 段练习: %s", e)
        return []
    out: list[tuple[str, int, int, int]] = []
    for r in rows:
        try:
            d = _date_str(r[0])
            if d is None:
                continue
            out.append((d, int(r[1]), int(r[2] or 0), int(r[3] or 0)))
        except (TypeError, ValueError):
            # 脏行 (日期不可解析 / 数字字段是文本) → 跳过该行。
            # 必须吞掉: 这里抛出去会打断整轮 calc_all, 所有徽章一起不解锁。
            continue
    out.sort()
    return out


def _daily_totals(conn) -> dict[str, int]:
    """daily_practices → {date: total_minutes}。"""
    cur = _exec(conn, "SELECT date, total_minutes FROM daily_practices")
    out: dict[str, int] = {}
    for r in cur.fetchall():
        try:
            d = _date_str(r[0])
            if d is None:
                continue
            out[d] = out.get(d, 0) + int(r[1] or 0)
        except (TypeError, ValueError):
            # 同 _ps_sessions: 脏行跳过, 不许把整轮 calc 打断。
            continue
    return out


def _d(s: str) -> date:
    return date.fromisoformat(s)


# ─── 取「首次达成日」的原语 (返回 (first_at | None, 展示用数值)) ──────────────

def _first_single_min(sess, ids, m):
    """某 item 单次时长 >= m 分钟。"""
    best, val = None, 0
    for d, iid, mins, _t in sess:
        if iid not in ids:
            continue
        val = max(val, mins)
        if best is None and mins >= m:
            best = d
    return best, val


def _first_over_min(sess, ids, m):
    """严格大于 m (给"超过 10 分钟"这类口径)。"""
    best, val = None, 0
    for d, iid, mins, _t in sess:
        if iid not in ids:
            continue
        val = max(val, mins)
        if best is None and mins > m:
            best = d
    return best, val


def _first_session_count(sess, ids, n):
    """累计 session 段数 >= n。"""
    cnt, best = 0, None
    for d, iid, _m, _t in sess:
        if iid not in ids:
            continue
        cnt += 1
        if best is None and cnt >= n:
            best = d
    return best, cnt


def _first_days(sess, ids, n):
    """覆盖的不同练习日数 >= n。"""
    days = sorted({d for d, iid, _m, _t in sess if iid in ids})
    return (days[n - 1] if len(days) >= n else None), len(days)


def _first_day_sessions(sess, ids, n):
    """同一天练习的段数合计 >= n (跨曲目/跨科目合计, 同日细分练习)。

    口径 2026-10-19 改 (D1=A): 分组键由 `(日期, item_id)` 改为**只按日期**。
    改前测的是"单曲单日" (PIECE 曲目下峰值 8), 跟卡面「同一天分段练满 15 段」/
    卡背「一天里扎扎实实练满十五段」的文案对不上 —— 文案没限定同一首曲子。
    改后同日跨曲目合计 (实测峰值 12), 与文案一致。

    ids 只有 1 个时两种口径等价 (分组键里的 item_id 是常量), 所以
    rep_xizang_wuqu(1346) / rep_xiao_kanxi(1351) 逐值不变。
    """
    cnt: dict[str, int] = {}
    best, val = None, 0
    for d, iid, _m, _t in sess:
        if iid not in ids:
            continue
        cnt[d] = cnt.get(d, 0) + 1
        val = max(val, cnt[d])
        if best is None and cnt[d] >= n:
            best = d
    return best, val


def _first_two_day_sum(sess, ids, m):
    """连续两天累计分钟 >= m (达成日 = 第二天)。"""
    per: dict[str, int] = {}
    for d, iid, mins, _t in sess:
        if iid in ids:
            per[d] = per.get(d, 0) + mins
    ds = sorted(per)
    for a, b in zip(ds, ds[1:]):
        if (_d(b) - _d(a)).days == 1 and per[a] + per[b] >= m:
            return b, per[a] + per[b]
    return None, (max(per.values()) if per else 0)


def _first_total_min(daily: dict[str, int], m: int):
    """累计练习分钟 >= m (达成日 = 累计跨过阈值那天)。

    口径 = `daily_practices.total_minutes`（孩子端看到的「累计总时长」就是这一列），
    与本批的 month_minutes / week_minutes 同一口径。
    不用 practice_sessions 分段求和：分段和有明细分历史的日期才算得进, 数字比
    daily 小一大截 (实测 6496 vs 9419), 且不是她看得见的那个数。
    """
    tot, best = 0, None
    for d in sorted(daily):
        tot += daily[d]
        if best is None and tot >= m:
            best = d
    return best, tot


def _first_days_and_tempo(sess, ids, n, t):
    """覆盖 >= n 天 且 历史最快 tempo >= t (两个条件都满足那天)。"""
    days = sorted({d for d, iid, _m, _tp in sess if iid in ids})
    tempo_days = [d for d, iid, _m, tp in sess if iid in ids and tp >= t]
    if len(days) < n or not tempo_days:
        return None, len(days)
    return max(days[n - 1], min(tempo_days)), len(days)


def _first_single_min_tempo(sess, ids, m, t):
    """同一段练习既 >= m 分钟又 tempo >= t。"""
    best, val = None, 0
    for d, iid, mins, tp in sess:
        if iid not in ids:
            continue
        val = max(val, mins)
        if best is None and mins >= m and tp >= t:
            best = d
    return best, val


def _first_tempo(sess, ids, t):
    """历史最快 tempo >= t。"""
    best, mx = None, 0
    for d, iid, _m, tp in sess:
        if iid not in ids:
            continue
        mx = max(mx, tp)
        if best is None and tp >= t:
            best = d
    return best, mx


def _first_consec_item_days(sess, ids, n):
    """任一 item 连续 n 天有记录 (达成日 = 第 n 天), 取最早。"""
    per: dict[int, set[str]] = {}
    for d, iid, _m, _t in sess:
        if iid in ids:
            per.setdefault(iid, set()).add(d)
    best = None
    for _iid, ds in per.items():
        sd = sorted(_d(x) for x in ds)
        run = 1
        for i in range(1, len(sd)):
            run = run + 1 if (sd[i] - sd[i - 1]).days == 1 else 1
            if run >= n:
                cand = sd[i].isoformat()
                if best is None or cand < best:
                    best = cand
                break
    return best, 0


def _first_days_and_total(sess, ids, n, m):
    """覆盖 >= n 天 且 累计 >= m 分钟 (两个条件都满足那天)。"""
    days = sorted({d for d, iid, _mm, _t in sess if iid in ids})
    if len(days) < n:
        return None, len(days)
    tot, best = 0, None
    for d, iid, mins, _t in sess:
        if iid not in ids:
            continue
        tot += mins
        if best is None and tot >= m and days[n - 1] <= d:
            best = d
    return best, len(days)


def _first_items_over_days(sess, ids, n, dmin):
    """有 >= n 个 item 各自覆盖 >= dmin 天 (达成日 = 第 n 个达标那天)。"""
    per: dict[int, set[str]] = {}
    for d, iid, _m, _t in sess:
        if iid in ids:
            per.setdefault(iid, set()).add(d)
    reached = []
    for _iid, ds in per.items():
        sd = sorted(ds)
        if len(sd) >= dmin:
            reached.append(sd[dmin - 1])
    if len(reached) < n:
        return None, len(reached)
    reached.sort()
    return reached[n - 1], len(reached)


def _first_month_days(dates, n):
    """任一自然月内练习天数 >= n (达成日 = 该月第 n 个练习日)。"""
    per: dict[str, list[str]] = {}
    for d in dates:
        per.setdefault(d[:7], []).append(d)
    for m in sorted(per):
        ds = sorted(per[m])
        if len(ds) >= n:
            return ds[n - 1], len(ds)
    return None, (max(len(v) for v in per.values()) if per else 0)


def _first_month_minutes(daily: dict[str, int], m: int):
    """任一自然月内累计练习分钟 >= m (达成日 = 跨过阈值那天)。

    为「天数已饱和」的徽章准备的强度口径: 她一年练 326 天、单月最多练满 31 天,
    按"天数"计的条件早就成立, 只有按时长才还有区分度。
    """
    per: dict[str, list[tuple[str, int]]] = {}
    for d, mins in daily.items():
        per.setdefault(d[:7], []).append((d, mins))
    best = 0
    for mo in sorted(per):
        run = 0
        for d, mins in sorted(per[mo]):
            run += mins
            best = max(best, run)
            if run >= m:
                return d, run
    return None, best


def _first_week_minutes(daily: dict[str, int], m):
    """任一自然周(周一~周日)练习分钟 >= m (达成日 = 跨过阈值那天)。"""
    per: dict[tuple[int, int], list[tuple[str, int]]] = {}
    for d, mins in daily.items():
        y, mo, da = (int(x) for x in d.split("-"))
        per.setdefault(date(y, mo, da).isocalendar()[:2], []).append((d, mins))
    for k in sorted(per):
        tot = 0
        for d, mins in sorted(per[k]):
            tot += mins
            if tot >= m:
                return d, tot
    return None, 0


def _first_gap(dates, days_gte):
    """相邻两个练习日间隔 >= days_gte 天 (达成日 = 后一天) = 中断后重新开练。"""
    sd = sorted(dates)
    for a, b in zip(sd, sd[1:]):
        gap = (_d(b) - _d(a)).days
        if gap >= days_gte:
            return b, gap
    return None, 0


def _first_in_holiday(dates, key, before=0, after=0):
    """节日窗口 [节日-before, 节日+after] 内有练习 (达成日 = 窗口内最早练习日)。"""
    out = None
    for h in HOLIDAY_DATES.get(key, ()):
        hd = _d(h)
        for d in sorted(dates):
            dd = _d(d)
            if -before <= (dd - hd).days <= after:
                if out is None or d < out:
                    out = d
    return out, 0


def _first_school_week(dates, need=3):
    """每年 9/1~9/7 开学周内练习 >= need 天 (达成日 = 第 need 天)。"""
    for y in sorted({_d(d).year for d in dates}):
        start, end = date(y, 9, 1), date(y, 9, 7)
        hits = sorted(d for d in dates if start <= _d(d) <= end)
        if len(hits) >= need:
            return hits[need - 1], len(hits)
    return None, 0


def _first_summer_days(dates, need=20, daily=None, min_day=0):
    """某年 7~8 月累计练习 >= need 天 (达成日 = 第 need 天)。

    ``min_day > 0`` 时只数"单日 >= min_day 分钟"的达标日 (强度口径), 需要 ``daily``。
    """
    per: dict[int, list[str]] = {}
    for d in dates:
        dt = _d(d)
        if not (7 <= dt.month <= 8):
            continue
        if min_day > 0 and (daily or {}).get(d, 0) < min_day:
            continue
        per.setdefault(dt.year, []).append(d)
    for y in sorted(per):
        hits = sorted(per[y])
        if len(hits) >= need:
            return hits[need - 1], len(hits)
    return None, (max((len(v) for v in per.values()), default=0))


def _first_holiday_item_min(sess, key, item_id, m):
    """节日当天某 item 累计 >= m 分钟 (达成日 = 该节日)。"""
    per: dict[str, int] = {}
    for d, iid, mins, _t in sess:
        if iid == item_id:
            per[d] = per.get(d, 0) + mins
    for h in sorted(HOLIDAY_DATES.get(key, ())):
        if per.get(h, 0) >= m:
            return h, per[h]
    return None, (max(per.values()) if per else 0)


def _first_new_item_window(sess, ids, window=7, need=3):
    """某曲目**首次出现**后 window 天内练 >= need 天 (新曲开荒)。"""
    per: dict[int, set[str]] = {}
    for d, iid, _m, _t in sess:
        if iid in ids:
            per.setdefault(iid, set()).add(d)
    for iid, ds in per.items():
        sd = sorted(_d(x) for x in ds)
        d0 = sd[0]
        hits = [x for x in sd if (x - d0).days < window]
        if len(hits) >= need:
            return hits[need - 1].isoformat(), len(hits)
    return None, 0


# ─── 规则表: 徽章 id → 判定原语 ───────────────────────────────────────────────
# kind 取值见上面各原语; cond 文案与 achievements.cond_text 保持一致口径。
#
# 支持的 kind 白名单 —— 规则表里写错 kind (拼错 / 改名) 会让那枚徽章**永远灰着**:
# dispatch 落到 else 返 None → 走 legacy 链路 → 未达成, 而且异常、日志、测试全都不响
# (同类事故的成因, 见本文件 _calc_practice_badge 注释)。所以这里显式列出支持的集合,
# dispatch 入口逐个校验, 表外 kind 直接 logger.error。
PRACTICE_RULE_KINDS: frozenset[str] = frozenset({
    "single_min", "over_min", "session_count", "days", "day_sessions",
    "two_day_sum", "total_min", "days_and_tempo", "single_min_tempo", "tempo",
    "consec_item_days", "days_and_total", "items_over_days", "month_days",
    "month_minutes", "week_minutes", "gap", "holiday", "school_week",
    "summer_days", "holiday_item_min", "new_item_window",
})
#
# 阈值口径 (2026-10-17 按 dad 的 C 方案重设): 真实记录显示她一年练 326 天、
# 单月最多 31 天、全站最长连续 61 天 —— 凡按"累计天数"计的条件早就饱和, 一入库
# 就会立刻点亮。所以门槛整体抬到"刚超过她的现有记录", 并且能改的都从**天数**口径
# 换到**强度**口径 (单次时长 / tempo / 单曲连续天数 / 单月或单周时长)。
# **时长类口径统一走 daily_practices** (total_min / month_minutes / week_minutes),
# 不用 practice_sessions 分段求和 —— 分段和会漏掉没有明细的历史日期, 数字比
# 孩子端看得见的累计时长短一大截 (实测 6496 vs 9419)。
# 对应实测值写在每条注释里, 便于日后按记录再调。
PRACTICE_BADGE_RULES: dict[str, dict] = {
    # 组1 曲目
    "rep_hui_niangjia": {"kind": "single_min", "ids": (1004,), "m": 15},      # 实测 10
    "rep_caicha_pudie": {"kind": "two_day_sum", "ids": (1026,), "m": 40},     # 实测 32
    "rep_saliha": {"kind": "single_min", "ids": (1340,), "m": 25},            # 实测 18
    "rep_xizang_wuqu": {"kind": "day_sessions", "ids": (1346,), "n": 10},     # 实测 8
    "rep_zi_zhu_diao": {"kind": "days_and_total", "ids": (1348,), "n": 20, "m": 180},  # 16 天/112
    "rep_xiao_kanxi": {"kind": "day_sessions", "ids": (1351,), "n": 5},       # 实测 3
    "rep_chun_geng_qu": {"kind": "over_min", "ids": (1352,), "m": 10},        # 实测 5 (未达成)
    "rep_moli_hua": {"kind": "session_count", "ids": (1028, 1032), "n": 12},  # 实测 6
    "rep_xin_qu_kai_huang": {"kind": "new_item_window", "ids": PIECE_ITEM_IDS,
                             "window": 14, "need": 14},                        # 实测最多 13 天
    # 组2 技巧
    "tech_chang_yin": {"kind": "single_min", "ids": (1034,), "m": 20},        # 实测 17
    "tech_dan_tu": {"kind": "days_and_tempo", "ids": (1343,), "n": 20, "t": 120},  # 天够, 速度 118
    "tech_shuang_tu": {"kind": "single_min_tempo", "ids": (1350,), "m": 3, "t": 90},  # 实测 70
    "tech_chan_yin": {"kind": "consec_item_days", "ids": (1337, 1347), "n": 10},  # 单项目实测最长 5
    "tech_dan_tu_4": {"kind": "tempo", "ids": (1349,), "t": 110},             # 实测 100 (未达成)
    "tech_ji_ben_gong": {"kind": "consec_item_days", "ids": (1033,), "n": 5},  # 实测连续 3
    # 组3 典故
    "lore_xiao_shi": {"kind": "total_min", "ids": (), "m": 10000},            # daily 口径实测 9419
    "lore_huan_yi": {"kind": "day_sessions", "ids": PIECE_ITEM_IDS, "n": 15},  # 实测 12
    "lore_li_guinian": {"kind": "items_over_days", "ids": PIECE_ITEM_IDS, "n": 5, "dmin": 20},
    #   实测 >=20 天的曲目只有 4 首
    "lore_li_mo": {"kind": "consec_item_days", "ids": PIECE_ITEM_IDS, "n": 15},  # 单曲实测最长连续 8
    "lore_cai_yong": {"kind": "month_minutes", "m": 1500},                    # 实测单月最高 1418
    "lore_ma_rong": {"kind": "week_minutes", "m": 450},                       # 实测最高一周 410
    # 组4 节令
    "season_mid_autumn": {"kind": "holiday", "key": "mid_autumn", "before": 3, "after": 3},
    "season_new_year": {"kind": "holiday", "key": "spring_festival", "before": 0, "after": 2},
    "season_duan_wu": {"kind": "holiday", "key": "dragon_boat", "before": 0, "after": 0},
    "season_school_start": {"kind": "school_week", "need": 3},
    "season_summer": {"kind": "summer_days", "need": 10, "min_day": 60},      # 实测 6 天
    "season_dong_zhi": {"kind": "holiday_item_min", "key": "winter_solstice",
                        "item_id": 1034, "m": 5},
    # 组5 勇气
    "brave_sick_back": {"kind": "gap", "days_gte": 8},                        # 实测 7 (未达成)
    "brave_exam_pass": {"kind": "single_min", "ids": (1339,), "m": 60},       # 实测 50
    "brave_class_back": {"kind": "single_min", "ids": (1338,), "m": 75},      # 实测 60
}


def _calc_practice_badge(conn, aid: str, stats: dict[str, dict]) -> Optional["CalcResult"]:
    """练习记录型 milestone 的 calc 分支。不在规则表里 → 返回 None (交回原链路)。

    返回的 achieved_at 必须是**首次达成日**: _persist_unlocked_milestones 只在
    achieved_at 非 None 时落库 (否则灰卡永不解锁)。
    """
    rule = PRACTICE_BADGE_RULES.get(aid)
    if rule is None:
        return None

    s = stats.get(aid, {})
    stat_achieved = s.get("achieved") == "Y"
    stat_at = s.get("achieved_at")

    sess = _ps_sessions(conn)
    daily = _daily_totals(conn)
    dates = sorted(set(daily) | {d for d, _i, _m, _t in sess})

    kind = rule["kind"]
    if kind not in PRACTICE_RULE_KINDS:
        # 规则表写错 kind ⇒ 这枚徽章会永远灰着, 而且不抛异常、不报错、测试也全绿。
        # 显式报出来, 别让拼写错误变成静默失活。
        logger.error("practice badge %s: 规则表 kind=%r 不在支持集合内, 该徽章按未达成处理",
                     aid, kind)
        return None
    v = 0
    if kind == "single_min":
        first, v = _first_single_min(sess, rule["ids"], rule["m"])
    elif kind == "over_min":
        first, v = _first_over_min(sess, rule["ids"], rule["m"])
    elif kind == "session_count":
        first, v = _first_session_count(sess, rule["ids"], rule["n"])
    elif kind == "days":
        first, v = _first_days(sess, rule["ids"], rule["n"])
    elif kind == "day_sessions":
        first, v = _first_day_sessions(sess, rule["ids"], rule["n"])
    elif kind == "two_day_sum":
        first, v = _first_two_day_sum(sess, rule["ids"], rule["m"])
    elif kind == "total_min":
        first, v = _first_total_min(daily, rule["m"])
    elif kind == "days_and_tempo":
        first, v = _first_days_and_tempo(sess, rule["ids"], rule["n"], rule["t"])
    elif kind == "single_min_tempo":
        first, v = _first_single_min_tempo(sess, rule["ids"], rule["m"], rule["t"])
    elif kind == "tempo":
        first, v = _first_tempo(sess, rule["ids"], rule["t"])
    elif kind == "consec_item_days":
        first, v = _first_consec_item_days(sess, rule["ids"], rule["n"])
    elif kind == "days_and_total":
        first, v = _first_days_and_total(sess, rule["ids"], rule["n"], rule["m"])
    elif kind == "items_over_days":
        first, v = _first_items_over_days(sess, rule["ids"], rule["n"], rule["dmin"])
    elif kind == "month_days":
        first, v = _first_month_days(dates, rule["n"])
    elif kind == "month_minutes":
        first, v = _first_month_minutes(daily, rule["m"])
    elif kind == "week_minutes":
        first, v = _first_week_minutes(daily, rule["m"])
    elif kind == "gap":
        first, v = _first_gap(dates, rule["days_gte"])
    elif kind == "holiday":
        first, v = _first_in_holiday(dates, rule["key"],
                                     rule.get("before", 0), rule.get("after", 0))
    elif kind == "school_week":
        first, v = _first_school_week(dates, rule["need"])
    elif kind == "summer_days":
        first, v = _first_summer_days(dates, rule["need"], daily, rule.get("min_day", 0))
    elif kind == "holiday_item_min":
        first, v = _first_holiday_item_min(sess, rule["key"], rule["item_id"], rule["m"])
    elif kind == "new_item_window":
        first, v = _first_new_item_window(sess, rule["ids"],
                                         rule.get("window", 7), rule.get("need", 3))
    else:
        return None

    achieved = first is not None
    # stats 里已有历史达成时间 → 用它 (不可变); 否则用算出来的首次达成日
    at = stat_at if (stat_achieved and stat_at) else (first if achieved else None)
    # 展示文案: 这里**不读 DB** (calc_all 会被整页调用, 每次开连接会打爆池);
    # 卡片 modal 的 cond_text 由调用方从 achievements.cond_text 取 (app.py 已传),
    # 所以这里留空即可, 需要回落时才用规则里的兜底文案。
    return CalcResult(achieved, v, None, at, rule.get("cond", ""))
