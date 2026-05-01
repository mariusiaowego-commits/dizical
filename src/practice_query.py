"""
竹笛练习查询 TUI
交互式终端界面：浏览练习记录
  今日/本周视图 / 月历热力图 / 历史浏览 / 模糊搜索
"""

import datetime as dt
import curses
import re
from typing import List, Dict, Optional, Tuple

from .database import db
from . import practice


# ── 颜色对 ────────────────────────────────────────────────
class Colors:
    HEADER   = 1
    TODAY    = 2
    HIGHLIGHT = 3
    DIM      = 4
    RED      = 5
    GREEN    = 6


# ── 工具函数 ───────────────────────────────────────────────
def _week_start(date: dt.date) -> dt.date:
    return date - dt.timedelta(days=date.weekday())


def _month_days(year: int, month: int) -> List[dt.date]:
    """返回某月所有日期（含前后补白）"""
    first = dt.date(year, month, 1)
    if month == 12:
        last = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        last = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    # 补齐周一之前的空位
    start = first - dt.timedelta(days=first.weekday())
    # 补齐周日之后的空位
    end = last + dt.timedelta(days=6 - last.weekday())
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += dt.timedelta(days=1)
    return days


def _render_bar(minutes: int, target: int = 60, width: int = 10) -> Tuple[str, int]:
    """渲染进度条，返回 (bar_str, color_attr)。bar 形如 [████████░░░░] 80%"""
    if width <= 0:
        return '[ ]', Colors.DIM
    filled = min(minutes, target) * width // target
    empty = width - filled
    pct = min(minutes, target) * 100 // target if target else 0
    exceeded = max(0, minutes - target)
    # 颜色：未达目标用 HIGHLIGHT，达到/超过目标用 GREEN，超额用 RED
    if exceeded > 0:
        color = Colors.RED
    elif filled == width:
        color = Colors.GREEN
    else:
        color = Colors.HIGHLIGHT
    bar = '█' * filled + '░' * empty
    return f'[{bar}] {pct:>3}%', color


def _fuzzy_match(text: str, pattern: str) -> bool:
    """简单模糊匹配（子串 + 首字母）"""
    if not pattern:
        return True
    text = text.lower()
    pat = pattern.lower()
    # 检查所有字符按顺序出现
    j = 0
    for ch in text:
        if j < len(pat) and ch == pat[j]:
            j += 1
    return j == len(pat)


# ── 主 TUI 类 ─────────────────────────────────────────────
class PracticeQueryTUI:
    VIEWS = ['today', 'week', 'month', 'history']

    def __init__(self, stdscr: curses.window):
        self.stdscr = stdscr
        self.h, self.w = stdscr.getmaxyx()
        curses.curs_set(0)
        self.stdscr.keypad(True)
        self.stdscr.nodelay(False)

        self.view_idx = 0          # 0=today 1=week 2=month 3=history
        self.today = dt.date.today()
        self.week_start = _week_start(self.today)
        self.month_year = (self.today.year, self.today.month)
        self.history_cursor = 0   # 历史记录偏移
        self.search_pattern = ""
        self.history_records: List[Dict] = []
        self._load_history()
        self._init_colors()

    def _init_colors(self) -> None:
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(Colors.HEADER,   curses.COLOR_CYAN,    -1)
            curses.init_pair(Colors.TODAY,     curses.COLOR_GREEN,   -1)
            curses.init_pair(Colors.HIGHLIGHT, curses.COLOR_YELLOW,  -1)
            curses.init_pair(Colors.DIM,       curses.COLOR_WHITE,   -1)
            curses.init_pair(Colors.RED,       curses.COLOR_RED,     -1)
            curses.init_pair(Colors.GREEN,    curses.COLOR_GREEN,   -1)

    def _load_history(self, limit: int = 100) -> None:
        """加载最近打卡记录"""
        end = self.today
        start = end - dt.timedelta(days=365)
        rows = db.get_daily_practices_in_range(start, end)
        # 按日期倒序
        self.history_records = sorted(rows, key=lambda r: r['date'], reverse=True)

    # ── 绘制 ──────────────────────────────────────────────
    def draw(self) -> None:
        self.stdscr.clear()
        self._draw_title()
        view = self.VIEWS[self.view_idx]
        if view == 'today':
            self._draw_today()
        elif view == 'week':
            self._draw_week()
        elif view == 'month':
            self._draw_month()
        elif view == 'history':
            self._draw_history()
        self._draw_footer()
        self.stdscr.refresh()

    def _draw_title(self) -> None:
        title = f" 🎵 笛子练习查询  │  [←/→]切换视图  [↑/↓]浏览  /搜索  ESC/Q退出 "
        self._attr(0, 0, title, Colors.HEADER, bold=True)
        self.stdscr.addstr(0, len(title), ' ' * max(0, self.w - len(title) - 1))
        self._hline(1, 0, '─', Colors.DIM)

    def _draw_footer(self) -> None:
        row = self.h - 1
        hints = "[←/→]视图  [↑/↓]浏览  [/]搜索  [H]本周作业  [Q/ESC]退出"
        self._attr(row, 0, hints, Colors.DIM)
        self.stdscr.addstr(row, len(hints), ' ' * max(0, self.w - len(hints) - 1))

    def _draw_today(self) -> None:
        row = 3
        date_str = self.today.isoformat()
        p = db.get_daily_practice(self.today)

        header = f" 今日 {self.today.month}月{self.today.day}日 "
        self._center(row, header, Colors.TODAY, bold=True)
        row += 2

        if not p or p['total_minutes'] == 0:
            self._center(row, "  今日暂无练习记录  ", Colors.DIM)
            row += 2
            self._draw_prompt(row, "  按 [→] 看本周总览  或  / 搜索历史  ")
            return

        # 总时长 + 进度条
        total = p['total_minutes']
        bar_str, bar_color = _render_bar(total, 60, 14)
        self._attr(row, 2, f"总练习: {total} 分钟", Colors.HIGHLIGHT, bold=True)
        self.stdscr.addstr(row, 22, bar_str, curses.color_pair(bar_color))
        row += 2

        # 各项目
        self._hline(row, 2, '─', Colors.DIM)
        row += 1
        for it in p.get('items', []):
            bar_str, bar_color = _render_bar(it['minutes'], 60, 10)
            self.stdscr.addstr(row, 4, f"{it['item']:<8}")
            self.stdscr.addstr(row, 14, f"{it['minutes']:>4}分")
            self.stdscr.addstr(row, 20, bar_str, curses.color_pair(bar_color))
            row += 1

        # 备注
        if p.get('log'):
            row += 1
            self._hline(row, 2, '─', Colors.DIM)
            row += 1
            log_lines = p['log'].split('\n')
            for ln in log_lines[:3]:
                self._attr(row, 4, f"📝 {ln[:self.w-6]}", Colors.DIM)
                row += 1

        row += 1
        self._draw_prompt(row, "  [→] 本周  [↑/↓] 查历史  ")

    def _draw_week(self) -> None:
        row = 3
        week_label = f" 本周 {_fmt_week(self.week_start)} "
        self._center(row, week_label, Colors.HEADER, bold=True)
        row += 2

        days = practice.get_week_days(self.week_start)
        day_names = ['一', '二', '三', '四', '五', '六', '日']

        # 星期头
        self.stdscr.addstr(row, 2, "  ")
        for i, dn in enumerate(day_names):
            col = 4 + i * (self.w - 8) // 7
            attr = Colors.TODAY if (self.week_start + dt.timedelta(days=i)) == self.today else Colors.DIM
            self._attr(row, col, f"{dn}", attr, bold=(attr == Colors.TODAY))
        row += 1

        # 日历网格
        for iso, d in days.items():
            col = 4 + d['date'].weekday() * (self.w - 8) // 7
            if d['is_future']:
                self._attr(row, col, f"{d['date'].day:>2} ", Colors.DIM)
            elif d['has_practice']:
                clr = Colors.GREEN if d['total_minutes'] >= 60 else Colors.HIGHLIGHT
                self._attr(row, col, f"{d['date'].day:>2} ", clr, bold=True)
            else:
                self._attr(row, col, f"{d['date'].day:>2} ", Colors.DIM)
        row += 2

        # 每日明细
        self._hline(row, 2, '─', Colors.DIM)
        row += 1
        for iso, d in days.items():
            if not d['has_practice'] and not d['is_today']:
                continue
            dn = day_names[d['date'].weekday()]
            date_lbl = f"{dn}({d['date'].month}/{d['date'].day})"
            if d['is_today']:
                self._attr(row, 4, f"● {date_lbl}", Colors.TODAY, bold=True)
            else:
                self._attr(row, 4, f"  {date_lbl}", Colors.DIM)

            if d['has_practice']:
                mins = d['total_minutes']
                bar_str, bar_color = _render_bar(mins, 60, 10)
                self.stdscr.addstr(row, 14, f"{mins:>4}分 ", curses.color_pair(Colors.DIM))
                self.stdscr.addstr(row, 21, bar_str, curses.color_pair(bar_color))
                items_str = ' '.join(f"{x['item']}{x['minutes']}" for x in d['items'][:4])
                self.stdscr.addstr(row, 36, f" {items_str[:self.w-38]}")
            else:
                self._attr(row, 14, "  休息", Colors.DIM)
            row += 1

        row += 1
        # 本周作业
        assignment = db.get_weekly_assignment(self.week_start)
        if assignment:
            self._hline(row, 2, '─', Colors.DIM)
            row += 1
            self._attr(row, 4, "📋 本周作业:", Colors.HIGHLIGHT, bold=True)
            row += 1
            for it in assignment.get('items', [])[:5]:
                self.stdscr.addstr(row, 6, f"• {it['item']}: {it.get('requirement','')[:self.w-10]}")
                row += 1
        self._draw_prompt(row, "  [←]今日  [→]月视图  [↑/↓]历史  ")

    def _draw_month(self) -> None:
        row = 3
        year, month = self.month_year
        month_str = f" {year}年{month}月 "
        self._center(row, month_str, Colors.HEADER, bold=True)
        row += 2

        days = _month_days(year, month)
        day_names = ['一', '二', '三', '四', '五', '六', '日']

        # 星期头
        for i, dn in enumerate(day_names):
            col = 2 + i * (self.w - 4) // 7
            self._attr(row, col, f"{dn}", Colors.DIM)
        row += 1

        # 日历格
        week_rows = len(days) // 7
        practices = db.get_daily_practices_in_range(days[0], days[-1])
        pmap = {p['date'].isoformat(): p for p in practices}

        for r in range(week_rows):
            self.stdscr.addstr(row, 2, "")
            for c in range(7):
                idx = r * 7 + c
                if idx >= len(days):
                    break
                d = days[idx]
                key = d.isoformat()
                p = pmap.get(key)
                col = 2 + c * (self.w - 4) // 7
                day_str = f"{d.day:>2}"
                if d.month != month:
                    self._attr(row, col, day_str, Colors.DIM)
                elif d == self.today:
                    self._attr(row, col, day_str, Colors.TODAY, bold=True)
                elif p and p['total_minutes'] >= 60:
                    self._attr(row, col, day_str, Colors.GREEN, bold=True)
                elif p and p['total_minutes'] > 0:
                    self._attr(row, col, day_str, Colors.HIGHLIGHT)
                else:
                    self._attr(row, col, day_str, Colors.DIM)
                # 热力：0=空 1-30=淡 31-60=中 61+=深
                if p and p['total_minutes'] > 0:
                    intensity = min(p['total_minutes'], 90)
                    # 用字符密度表示热度
                    heat = '·' if intensity < 30 else '◦' if intensity < 60 else '●'
                    self._attr(row, col + 2, heat,
                               Colors.GREEN if intensity >= 60 else Colors.HIGHLIGHT)
            row += 1

        row += 1
        # 月统计摘要
        month_start = dt.date(year, month, 1)
        if month == 12:
            month_end = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
        else:
            month_end = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
        month_ps = [p for p in practices if month_start <= p['date'] <= month_end]
        total_min = sum(p['total_minutes'] for p in month_ps)
        practice_days = len(month_ps)
        self._hline(row, 2, '─', Colors.DIM)
        row += 1
        self._attr(row, 4, f"本月: {practice_days}天练习 / {total_min}分钟", Colors.HIGHLIGHT, bold=True)
        row += 1
        self._draw_prompt(row, "  [←]本周  [↑/↓]月份  [Q]退出  ")

    def _draw_history(self) -> None:
        row = 3
        self._center(row, " 历史记录 ", Colors.HEADER, bold=True)
        row += 2

        # 搜索提示
        if self.search_pattern:
            self._attr(row, 2, f"  🔍 搜索: {self.search_pattern}  (共{len(self.history_records)}条)", Colors.HIGHLIGHT)
            row += 1
        self._hline(row, 0, '─', Colors.DIM)
        row += 1

        # 过滤记录
        if self.search_pattern:
            filtered = [r for r in self.history_records
                        if any(_fuzzy_match(it.get('item', ''), self.search_pattern)
                               for it in r.get('items', []))
                        or _fuzzy_match(r.get('log', ''), self.search_pattern)]
        else:
            filtered = self.history_records

        page_size = self.h - row - 3
        page = filtered[self.history_cursor: self.history_cursor + page_size]

        if not page:
            self._center(row + 1, "  无匹配记录  ", Colors.DIM)
        else:
            for rec in page:
                d = rec['date']
                total = rec['total_minutes']
                items_str = ' '.join(f"{x['item']}{x['minutes']}分" for x in rec.get('items', [])[:5])
                is_today = (d == self.today)
                lbl = f"{d.isoformat()}  {total:>4}分"
                attr = Colors.TODAY if is_today else Colors.HIGHLIGHT if total > 0 else Colors.DIM
                self._attr(row, 2, lbl, attr, bold=is_today)
                self.stdscr.addstr(row, 22, f" {items_str[:self.w-24]}")
                row += 1

        total_pages = (len(filtered) + page_size - 1) // page_size if filtered else 1
        current_page = self.history_cursor // page_size + 1
        self._attr(self.h - 2, 2, f"  第{current_page}/{total_pages}页  共{len(filtered)}条  [↑/↓]翻页  [/]搜索", Colors.DIM)
        self._draw_prompt(row, "  [←]今日  [/]搜索  [Q]退出  ")

    # ── 辅助绘制 ─────────────────────────────────────────
    def _center(self, row: int, text: str, attr: int, bold: bool = False) -> None:
        x = max(0, (self.w - len(text)) // 2)
        self._attr(row, x, text, attr, bold=bold)

    def _attr(self, row: int, col: int, text: str, attr: int, bold: bool = False) -> None:
        try:
            a = curses.color_pair(attr) | (curses.A_BOLD if bold else 0)
            self.stdscr.addstr(row, col, text, a)
        except curses.error:
            pass

    def _hline(self, row: int, col: int, ch: str, attr: int) -> None:
        try:
            a = curses.color_pair(attr)
            # BSD ncurses chtype 仅 4 字节，Unicode 字符无法装入；改用 addstr
            self.stdscr.addstr(row, col, ch * max(0, self.w - col), a)
        except curses.error:
            pass

    def _draw_prompt(self, row: int, text: str) -> None:
        if row < self.h - 1:
            self._attr(row, 2, text, Colors.DIM)

    # ── 键盘事件 ─────────────────────────────────────────
    def handle_key(self, key: int) -> bool:
        """返回 True 表示退出"""
        view = self.VIEWS[self.view_idx]

        if key in (curses.KEY_LEFT,):
            self.view_idx = max(0, self.view_idx - 1)
        elif key in (curses.KEY_RIGHT,):
            self.view_idx = min(len(self.VIEWS) - 1, self.view_idx + 1)
        elif key in (curses.KEY_UP,):
            if view == 'history':
                self.history_cursor = max(0, self.history_cursor - 1)
            elif view == 'month':
                y, m = self.month_year
                m -= 1
                if m < 1:
                    y -= 1; m = 12
                self.month_year = (y, m)
            elif view == 'week':
                self.week_start -= dt.timedelta(weeks=1)
        elif key in (curses.KEY_DOWN,):
            if view == 'history':
                self.history_cursor += 1
            elif view == 'month':
                y, m = self.month_year
                m += 1
                if m > 12:
                    y += 1; m = 1
                self.month_year = (y, m)
            elif view == 'week':
                self.week_start += dt.timedelta(weeks=1)
        elif key == ord('/'):
            self._do_search()
        elif key in (ord('h'), ord('H')):
            if view in ('today', 'week'):
                self.view_idx = 1  # 切到week显示作业
        elif key in (ord('q'), ord('Q'), 27):
            return True
        return False

    def _do_search(self) -> None:
        """底部搜索栏"""
        curses.curs_set(1)
        self.stdscr.attrset(0)
        row = self.h - 2
        self.stdscr.addstr(row, 0, '  🔍 搜索项目: ' + ' ' * (self.w - 16))
        self.stdscr.clrtoeol()
        curses.echo()
        try:
            curses.nodelay(self.stdscr, False)
            s = self.stdscr.getstr(row, 14, 30).decode('utf-8', errors='replace')
            self.search_pattern = s.strip()
        except curses.error:
            pass
        finally:
            curses.noecho()
            curses.curs_set(0)
            self.stdscr.nodelay(False)


def _fmt_week(ws: dt.date) -> str:
    we = ws + dt.timedelta(days=6)
    return f"{ws.month}/{ws.day} - {we.month}/{we.day}"


# ── 入口 ─────────────────────────────────────────────────
def run(stdscr: curses.window) -> None:
    tui = PracticeQueryTUI(stdscr)
    while True:
        tui.draw()
        key = tui.stdscr.getch()
        if tui.handle_key(key):
            break


def launch() -> None:
    curses.wrapper(run)
