from datetime import date
from typing import Optional, Annotated, List, Dict
import curses
import io
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import wcwidth
import re as _re

_RICH_TAG = _re.compile(r"\[/?(?:red|green|blue|yellow|magenta|dim|bold|cyan)\]")
from .lesson_manager import LessonManager
from .payment import PaymentManager
from .models import LessonStatus
from .database import db

app = typer.Typer(help="🎵 竹笛学习助手 - 课程管理与缴费提醒")
console = Console()


def _pad(text: str, width: int = 4) -> str:
    """按终端显示宽度对齐（emoji占2列），忽略rich标签"""
    stripped = _RICH_TAG.sub("", text)
    visible = wcwidth.wcswidth(stripped)
    return text + " " * (width - visible)

def _visual_width(line: str) -> int:
    """计算一行去掉rich标签后的显示宽度"""
    return wcwidth.wcswidth(_RICH_TAG.sub("", line))

# curses.A_ITALIC 在部分平台/curses build 缺失，安全回退
_A_ITALIC = getattr(curses, 'A_ITALIC', 0)

# Rich 标签 → curses 属性映射（ANSI code → curses attr）
_RICH_STYLE_MAP = {
    "bold": curses.A_BOLD,
    "dim": curses.A_DIM,
    "italic": _A_ITALIC,
    "reverse": curses.A_REVERSE,
    "cyan": 1,   # 用 color_pair(1)
    "yellow": 2, # 用 color_pair(2)
    "red": 3,    # 用 color_pair(3)
    "green": 4,  # 用 color_pair(4)
    "magenta": 5,
}

def _render_rich_line(line: str, stdscr, row: int, col: int, w: int) -> None:
    """
    解析 line 中的 Rich ANSI 标签（来自 Console(force_terminal=False) 输出），
    按显示内容逐段写到 curses（带样式）并截断到 w 宽度。
    """
    if curses.has_colors():
        if not hasattr(_render_rich_line, '_inited'):
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_YELLOW, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            curses.init_pair(4, curses.COLOR_GREEN, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
            _render_rich_line._inited = True

    # 解析 ANSI 色码（如 \x1b[1;36m）并分段
    import re as _re2
    ANSI_RE = _re2.compile(r'\x1b\[[0-9;]*m')
    parts = ANSI_RE.split(line)
    codes = ANSI_RE.findall(line)

    attr = curses.A_NORMAL
    pos = col
    for i, segment in enumerate(parts):
        if not segment:
            continue
        # 当前段的 ANSI 属性
        if i < len(codes):
            code = codes[i].strip('\x1b[]')
            attr = curses.A_NORMAL
            for part in code.split(';'):
                p = part.strip()
                if p == '1':
                    attr |= curses.A_BOLD
                elif p == '2':
                    attr |= curses.A_DIM
                elif p == '3':
                    attr |= _A_ITALIC
                elif p == '7':
                    attr |= curses.A_REVERSE
                elif p in ('30', '36') and '36' in code:
                    attr |= curses.color_pair(1)
                elif p in ('33',) and '33' in code:
                    attr |= curses.color_pair(2)
                elif p == '31':
                    attr |= curses.color_pair(3)
                elif p == '32':
                    attr |= curses.color_pair(4)
                elif p == '35':
                    attr |= curses.color_pair(5)

        vis = _visual_width(segment)
        if pos + vis > w - 1:
            segment = _truncate_to_width(segment, w - 1 - pos)
            vis = _visual_width(segment)
        if vis <= 0:
            break
        try:
            stdscr.addstr(row, pos, segment, attr)
        except curses.error:
            pass
        pos += vis

def _truncate_to_width(line: str, max_width: int) -> str:
    """截断到最大显示宽度（忽略标签）"""
    stripped = _RICH_TAG.sub("", line)
    vis = wcwidth.wcswidth(stripped)
    if vis <= max_width:
        return line
    # 从右往左截
    result = []
    consumed = 0
    for ch in line:
        cw = wcwidth.wcswidth(ch)
        if cw < 0:
            cw = 0
        if consumed + cw > max_width:
            break
        result.append(ch)
        consumed += cw
    return ''.join(result)

lesson_app = typer.Typer(help="课程管理")
payment_app = typer.Typer(help="缴费管理")
stat_app = typer.Typer(help="统计报表")
practice_app = typer.Typer(help="练习管理")
remind_app = typer.Typer(help="提醒管理")
backup_app = typer.Typer(help="数据备份")

# category 子命令组
practice_category_app = typer.Typer()
practice_app.add_typer(practice_category_app, name="category", help="大科目管理")
export_app = typer.Typer(help="导出管理")

practice_app.add_typer(remind_app, name="remind")
practice_app.add_typer(export_app, name="export")

app.add_typer(lesson_app, name="lesson")
app.add_typer(payment_app, name="payment")
app.add_typer(stat_app, name="stat")
app.add_typer(practice_app, name="practice")
app.add_typer(backup_app, name="backup")

# kid_app 子命令（儿童版 Web 界面）
from src.kid_app.__main__ import kid_app as _kid_app
app.add_typer(_kid_app, name="kid", help="🎵 竹笛练习助手（儿童版）")

lesson_manager = LessonManager()
payment_manager = PaymentManager()


def parse_date(date_str: str) -> date:
    """解析日期字符串 YYYY-MM-DD"""
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise typer.BadParameter(f"日期格式错误，请使用 YYYY-MM-DD 格式: {date_str}")


def parse_month(month_str: str) -> tuple[int, int]:
    """解析月份字符串 YYYY-MM"""
    try:
        year, month = map(int, month_str.split('-'))
        return year, month
    except ValueError:
        raise typer.BadParameter(f"月份格式错误，请使用 YYYY-MM 格式: {month_str}")


@lesson_app.command("generate")
def generate_lessons(
    month: str = typer.Argument(..., help="月份，格式 YYYY-MM"),
    overwrite: bool = typer.Option(False, "--overwrite", "-o", help="覆盖已存在的课程"),
):
    """生成指定月份的课程计划"""
    year, month_num = parse_month(month)
    plan = lesson_manager.generate_monthly_lessons(year, month_num, overwrite=overwrite)

    console.print(Panel(f"[green]✅ 已生成 {year}年{month_num}月 课程计划[/green]"))
    console.print(f"📚 总课程数: {plan.total_lessons} 节")
    console.print(f"⚠️  节假日冲突: {plan.holiday_conflicts} 节")
    console.print(f"💰 总学费: {plan.total_fee} 元")
    console.print()

    print_lesson_table(plan.lessons)


@lesson_app.command("list")
def list_lessons(month: Optional[str] = typer.Argument(None, help="月份，格式 YYYY-MM，默认当前月")):
    """列出课程"""
    if month:
        year, month_num = parse_month(month)
        lessons = lesson_manager.get_lessons(year, month_num)
        title = f"{year}年{month_num}月 课程列表"
    else:
        today = date.today()
        lessons = lesson_manager.get_lessons(today.year, today.month)
        title = f"{today.year}年{today.month}月 课程列表"

    if not lessons:
        console.print("[yellow]⚠️  暂无课程记录[/yellow]")
        return

    console.print(Panel(f"[blue]{title}[/blue]"))
    print_lesson_table(lessons)


@lesson_app.command("calendar")
def calendar_view(months: int = typer.Argument(3, help="显示几个月，默认3个月")):
    """日历视图显示课程（历史+未来）"""
    from datetime import timedelta
    import calendar

    today = date.today()
    # 从上个月开始，显示上个月、当月、下个月，共3个月
    if today.month == 1:
        start_month = date(today.year - 1, 12, 1)
    else:
        start_month = date(today.year, today.month - 1, 1)

    console.print(Panel(f"[blue]📅 竹笛课程日历（最近{months}个月）[/blue]"))

    all_lessons = []
    current = start_month
    for i in range(months):
        lessons = lesson_manager.get_lessons(current.year, current.month)
        all_lessons.extend(lessons)
        # 下一个月
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    lesson_dates = {l.date: l for l in all_lessons}

    # 打印月度日历
    cal = calendar.Calendar(firstweekday=0)  # 0=周一
    current = start_month

    for _ in range(months):
        year, month = current.year, current.month
        console.print(f"\n[bold magenta]{year}年{month}月[/bold magenta]")
        console.print("一  二  三  四  五  六  日")

        week = []
        for day in cal.itermonthdays(year, month):
            if day == 0:
                week.append("    ")
                continue

            day_date = date(year, month, day)
            lesson = lesson_dates.get(day_date)

            if lesson:
                if lesson.status == LessonStatus.CANCELLED:
                    day_str = f"[red]{day:2d}X[/red]"
                elif lesson.is_holiday_conflict:
                    day_str = f"[yellow]{day:2d}![/yellow]"
                elif lesson.fee_paid:
                    day_str = f"[green]{day:2d}$[/green]"
                else:
                    day_str = f"[blue]{day:2d}*[/blue]"
            else:
                day_str = f"{day:2d} "

            week.append(day_str)

            if len(week) == 7:
                console.print("".join(_pad(d) for d in week))
                week = []

        if week:
            console.print("".join(_pad(d) for d in week))

        # 下一个月
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    console.print("\n[dim]图例:[/dim] [blue]* 有课[/blue] [yellow]! 节假日冲突[/yellow] [red]X 已取消[/red]  |  [green]$ 已缴费[/green]")


def print_lesson_table(lessons):
    """打印课程表格"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("日期", style="dim")
    table.add_column("时间")
    table.add_column("状态")
    table.add_column("学费")
    table.add_column("缴费")
    table.add_column("节假日")
    table.add_column("备注")

    for lesson in lessons:
        status_style = {
            LessonStatus.SCHEDULED: "blue",
            LessonStatus.ATTENDED: "green",
            LessonStatus.CANCELLED: "red",
        }

        status_text = Text(
            {
                LessonStatus.SCHEDULED: "已安排",
                LessonStatus.ATTENDED: "已上课",
                LessonStatus.CANCELLED: "已取消",
            }[lesson.status],
            style=status_style[lesson.status],
        )

        fee_paid_text = Text("已缴费", style="green") if lesson.fee_paid else Text("未缴费", style="red")
        holiday_text = Text("⚠️ 冲突", style="yellow") if lesson.is_holiday_conflict else ""

        table.add_row(
            str(lesson.date),
            str(lesson.time),
            status_text,
            f"{lesson.fee} 元",
            fee_paid_text,
            holiday_text,
            lesson.notes or "",
        )

    console.print(table)


@lesson_app.command("add")
def add_lesson(date_str: str = typer.Argument(..., help="日期，格式 YYYY-MM-DD")):
    """添加课程"""
    lesson_date = parse_date(date_str)
    try:
        lesson = lesson_manager.add_lesson(lesson_date)
        console.print(f"[green]✅ 已添加课程: {lesson.date}[/green]")
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")


@lesson_app.command("cancel")
def cancel_lesson(date_str: str = typer.Argument(..., help="日期，格式 YYYY-MM-DD")):
    """取消课程"""
    lesson_date = parse_date(date_str)
    success = lesson_manager.cancel_lesson(lesson_date)
    if success:
        console.print(f"[green]✅ 已取消课程: {lesson_date}[/green]")
    else:
        console.print(f"[yellow]⚠️  未找到课程: {lesson_date}[/yellow]")


@lesson_app.command("reschedule")
def reschedule_lesson(
    from_date: str = typer.Argument(..., help="原日期，格式 YYYY-MM-DD"),
    to_date: str = typer.Argument(..., help="新日期，格式 YYYY-MM-DD"),
):
    """调课"""
    from_dt = parse_date(from_date)
    to_dt = parse_date(to_date)

    try:
        lesson = lesson_manager.reschedule_lesson(from_dt, to_dt)
        if lesson:
            console.print(f"[green]✅ 已调课: {from_dt} -> {to_dt}[/green]")
        else:
            console.print(f"[yellow]⚠️  未找到课程: {from_dt}[/yellow]")
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")


@lesson_app.command("confirm")
def confirm_lesson(date_str: str = typer.Argument(..., help="日期，格式 YYYY-MM-DD")):
    """确认已上课"""
    lesson_date = parse_date(date_str)
    lesson = lesson_manager.confirm_attendance(lesson_date)
    if lesson:
        console.print(f"[green]✅ 已确认上课: {lesson_date}[/green]")
    else:
        console.print(f"[yellow]⚠️  未找到课程: {lesson_date}[/yellow]")


@lesson_app.command("stats")
def lesson_stats(month: Optional[str] = typer.Argument(None, help="月份（YYYY-MM）、年份（YYYY）或 all，默认当前月")):
    """课程统计（上课明细+缴费汇总）"""
    today = date.today()

    # 解析参数：all / YYYY / YYYY-MM
    if month is None:
        year, month_num = today.year, today.month
        _show_detail(year, month_num)
        return

    if month.lower() == "all":
        _show_all_stats()
        return

    # 尝试年份
    if _re.match(r"^\d{4}$", month):
        year = int(month)
        _show_year_stats(year)
        return

    # 月份 YYYY-MM
    year, month_num = parse_month(month)
    _show_detail(year, month_num)


def _show_detail(year: int, month_num: int):
    """显示指定月份的明细+汇总"""
    lessons = lesson_manager.get_lessons(year, month_num)
    payment_status = payment_manager.get_monthly_payment_status(year, month_num)

    console.print(Panel(f"[blue]📊 {year}年{month_num}月 上课统计[/blue]"))

    if lessons:
        print_lesson_table(lessons)
    else:
        console.print("[dim]暂无课程记录[/dim]")

    console.print()
    _print_lesson_summary(lessons, payment_status)

    if payment_status.last_lesson_date:
        console.print(f"\n📆 最后上课日: {payment_status.last_lesson_date}")


def _show_year_stats(year: int):
    """显示全年的月度汇总"""
    console.print(Panel(f"[blue]📊 {year}年 课程统计[/blue]"))

    all_lessons = lesson_manager.get_lessons(year)
    if not all_lessons:
        console.print(f"[dim]{year}年暂无课程记录[/dim]")
        return

    # 按月分组
    from collections import defaultdict
    by_month = defaultdict(list)
    for l in all_lessons:
        by_month[l.date.month].append(l)

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("月份", style="dim")
    table.add_column("日期", style="dim")
    table.add_column("状态", style="dim")
    table.add_column("应缴", justify="right")
    table.add_column("已缴", justify="right")
    table.add_column("待缴", justify="right")

    total_arranged = total_attended = total_cancelled = 0
    total_fee = total_paid = total_balance = 0

    for m in range(1, 13):
        lessons = by_month.get(m, [])
        if not lessons:
            continue
        ps = payment_manager.get_monthly_payment_status(year, m)
        arranged = len([l for l in lessons if l.status == LessonStatus.SCHEDULED])
        attended = len([l for l in lessons if l.status == LessonStatus.ATTENDED])
        cancelled = len([l for l in lessons if l.status == LessonStatus.CANCELLED])
        total_arranged += arranged
        total_attended += attended
        total_cancelled += cancelled
        total_fee += ps.estimated_fee
        total_paid += ps.paid_amount
        total_balance += ps.balance

        # 拼装日期明细
        date_parts = []
        for l in sorted(lessons, key=lambda x: x.date):
            if l.status == LessonStatus.ATTENDED:
                date_parts.append(f"[green]{l.date.day}[/green]")
            elif l.status == LessonStatus.CANCELLED:
                date_parts.append(f"[red]{l.date.day}X[/red]")
            else:
                date_parts.append(f"{l.date.day}")

        date_str = "、".join(date_parts)

        balance_str = f"[red]{ps.balance}[/red]" if ps.balance > 0 else f"[green]{ps.balance}[/green]"
        table.add_row(
            f"{m}月", date_str,
            f"[green]上{attended}[/green] [blue]安{arranged}[/blue] [red]消{cancelled}[/red]",
            f"{ps.estimated_fee}", f"{ps.paid_amount}", balance_str,
        )

    console.print(table)
    console.print()
    console.print(f"  - 已安排: {total_arranged} 节")
    console.print(f"  - 已上课: {total_attended} 节")
    console.print(f"  - 已取消: {total_cancelled} 节")
    console.print(f"\n💰 全年汇总:")
    console.print(f"  - 应缴: {total_fee} 元 / 已缴: {total_paid} 元 / 待缴: [red]{total_balance}[/red] 元")


def _show_all_stats():
    """显示所有时间的累计汇总（按年+月明细）"""
    console.print(Panel(f"[blue]📊 累计课程统计[/blue]"))

    all_lessons = lesson_manager.get_lessons()
    if not all_lessons:
        console.print("[dim]暂无课程记录[/dim]")
        return

    attended = [l for l in all_lessons if l.status == LessonStatus.ATTENDED]
    scheduled = [l for l in all_lessons if l.status == LessonStatus.SCHEDULED]
    cancelled = [l for l in all_lessons if l.status == LessonStatus.CANCELLED]

    total_fee = sum(l.fee for l in attended)
    total_paid = sum(l.fee for l in attended if l.fee_paid)
    balance = total_fee - total_paid

    console.print(f"  - 累计课程: {len(all_lessons)} 节")
    console.print(f"  - 已上课: {len(attended)} 节")
    console.print(f"  - 已安排: {len(scheduled)} 节")
    console.print(f"  - 已取消: {len(cancelled)} 节")
    console.print(f"\n💰 累计财务:")
    console.print(f"  - 应缴合计: {total_fee} 元")
    console.print(f"  - 已缴合计: {total_paid} 元")
    if balance > 0:
        console.print(f"  - 累计待缴金额: [red]{balance} 元[/red]")
    else:
        console.print(f"  - 累计待缴金额: [green]{balance} 元[/green]")

    # 按年分组
    from collections import defaultdict
    by_year = defaultdict(lambda: defaultdict(list))
    for l in all_lessons:
        by_year[l.date.year][l.date.month].append(l)

    for yr in sorted(by_year.keys(), reverse=True):
        months_data = by_year[yr]
        yr_attended = [l for l in all_lessons if l.date.year == yr and l.status == LessonStatus.ATTENDED]
        yr_total = [l for l in all_lessons if l.date.year == yr]
        yr_fee = sum(l.fee for l in yr_attended)
        yr_paid = sum(l.fee for l in yr_attended if l.fee_paid)

        console.print(f"\n[bold]{yr}年[/bold]  {len(yr_total)} 节（已上 {len(yr_attended)} 节）/ {yr_fee} 元")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("月份", style="dim")
        table.add_column("日期", style="dim")
        table.add_column("状态", style="dim")
        table.add_column("应缴", justify="right")
        table.add_column("已缴", justify="right")
        table.add_column("待缴", justify="right")

        total_arranged = total_attended = total_cancelled = 0
        total_fee_y = total_paid_y = total_balance_y = 0

        for m in sorted(months_data.keys()):
            lessons = sorted(months_data[m], key=lambda x: x.date)
            arranged = len([l for l in lessons if l.status == LessonStatus.SCHEDULED])
            attended_c = len([l for l in lessons if l.status == LessonStatus.ATTENDED])
            cancelled_c = len([l for l in lessons if l.status == LessonStatus.CANCELLED])
            total_arranged += arranged
            total_attended += attended_c
            total_cancelled += cancelled_c

            # 计算当月应缴（仅已上课）
            month_fee = sum(l.fee for l in lessons if l.status == LessonStatus.ATTENDED)
            month_paid = sum(l.fee for l in lessons if l.status == LessonStatus.ATTENDED and l.fee_paid)
            month_balance = month_fee - month_paid
            total_fee_y += month_fee
            total_paid_y += month_paid
            total_balance_y += month_balance

            date_parts = []
            for l in lessons:
                if l.status == LessonStatus.ATTENDED:
                    date_parts.append(f"[green]{l.date.day}[/green]")
                elif l.status == LessonStatus.CANCELLED:
                    date_parts.append(f"[red]{l.date.day}X[/red]")
                else:
                    date_parts.append(f"{l.date.day}")

            balance_str = f"[red]{month_balance}[/red]" if month_balance > 0 else f"[green]{month_balance}[/green]"
            table.add_row(
                f"{m}月", "、".join(date_parts),
                f"[green]上{attended_c}[/green] [blue]安{arranged}[/blue] [red]消{cancelled_c}[/red]",
                f"{month_fee}", f"{month_paid}", balance_str,
            )

        balance_y_str = f"[red]{total_balance_y}[/red]" if total_balance_y > 0 else f"[green]{total_balance_y}[/green]"
        table.add_row(
            "[bold]合计[/bold]", "",
            f"[green]上{total_attended}[/green] [blue]安{total_arranged}[/blue] [red]消{total_cancelled}[/red]",
            f"{total_fee_y}", f"{total_paid_y}", balance_y_str,
        )
        console.print(table)


def _print_lesson_summary(lessons, payment_status):
    """打印课程汇总行"""
    status_counts = {
        "已安排": len([l for l in lessons if l.status == LessonStatus.SCHEDULED]),
        "已上课": len([l for l in lessons if l.status == LessonStatus.ATTENDED]),
        "已取消": len([l for l in lessons if l.status == LessonStatus.CANCELLED]),
    }
    for s, count in status_counts.items():
        console.print(f"  - {s}: {count} 节")

    console.print(f"\n💰 财务:")
    console.print(f"  - 费用明细: {payment_status.payment_breakdown}")
    console.print(f"  - 预计缴费: {payment_status.estimated_fee} 元")
    console.print(f"  - 当月已缴: {payment_status.paid_amount} 元")
    if payment_status.balance > 0:
        console.print(f"  - 累计待缴金额: [red]{payment_status.balance} 元[/red]")
    else:
        console.print(f"  - 累计待缴金额: [green]{payment_status.balance} 元[/green]")


@payment_app.command("status")
def payment_status(month: Optional[str] = typer.Argument(None, help="月份，格式 YYYY-MM，默认当前月")):
    """查看缴费状态"""
    if month:
        year, month_num = parse_month(month)
    else:
        today = date.today()
        year, month_num = today.year, today.month

    status = payment_manager.get_monthly_payment_status(year, month_num)

    console.print(Panel(f"[blue]💰 {year}年{month_num}月 缴费状态[/blue]"))
    console.print(f"📚 本月课程: {status.total_lessons} 节")
    console.print(f"✅ 已上课: {status.attended_lessons} 节")
    console.print(f"💰 应缴总额: {status.total_fee} 元")
    console.print(f"💵 已缴金额: {status.paid_amount} 元")

    if status.balance > 0:
        console.print(f"[red]❌ 累计待缴金额: {status.balance} 元[/red]")
        if status.last_lesson_date:
            console.print(f"📆 最后上课日: {status.last_lesson_date}")
    else:
        console.print("[green]✅ 本月费用已缴清[/green]")


@payment_app.command("record")
def record_payment(
    amount: int = typer.Argument(..., help="缴费金额"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="备注"),
):
    """记录缴费（现金）"""
    payment = payment_manager.record_payment(amount=amount, notes=notes)
    console.print(f"[green]✅ 已记录缴费: {amount} 元（现金）[/green]")
    console.print(f"📅 缴费日期: {payment.payment_date}")
    if notes:
        console.print(f"📝 备注: {notes}")


@payment_app.command("history")
def payment_history():
    """查看缴费历史"""
    payments = payment_manager.get_payment_history()

    if not payments:
        console.print("[yellow]⚠️  暂无缴费记录[/yellow]")
        return

    console.print(Panel("[blue]💰 缴费历史[/blue]"))

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("日期")
    table.add_column("金额", justify="right")
    table.add_column("方式")
    table.add_column("备注")

    for p in payments:
        table.add_row(
            str(p.payment_date),
            f"{p.amount} 元",
            p.payment_method,
            p.notes or "",
        )

    console.print(table)
    console.print(f"\n[green]总计: {sum(p.amount for p in payments)} 元[/green]")


@stat_app.command("monthly")
def monthly_stat(month: Optional[str] = typer.Argument(None, help="月份，格式 YYYY-MM，默认当前月")):
    """本月统计"""
    if month:
        year, month_num = parse_month(month)
    else:
        today = date.today()
        year, month_num = today.year, today.month

    lessons = lesson_manager.get_lessons(year, month_num)
    payment_status = payment_manager.get_monthly_payment_status(year, month_num)

    console.print(Panel(f"[blue]📊 {year}年{month_num}月 统计报表[/blue]"))

    status_counts = {
        "已安排": len([l for l in lessons if l.status == LessonStatus.SCHEDULED]),
        "已上课": len([l for l in lessons if l.status == LessonStatus.ATTENDED]),
        "已取消": len([l for l in lessons if l.status == LessonStatus.CANCELLED]),
    }

    console.print("📚 课程统计:")
    for status, count in status_counts.items():
        console.print(f"  - {status}: {count} 节")

    console.print(f"\n💰 财务统计:")
    console.print(f"  - 费用明细: {payment_status.payment_breakdown}")
    console.print(f"  - 预计缴费: {payment_status.estimated_fee} 元")
    console.print(f"  - 当月已缴: {payment_status.paid_amount} 元")
    if payment_status.balance > 0:
        console.print(f"  - 累计待缴金额: [red]{payment_status.balance} 元[/red]")
    else:
        console.print(f"  - 累计待缴金额: [green]{payment_status.balance} 元[/green]")
    if payment_status.historical_cumulative_paid > 0:
        console.print(f"  - 历史累计已缴: {payment_status.historical_cumulative_paid} 元")

    if payment_status.last_lesson_date:
        console.print(f"\n📆 最后上课日: {payment_status.last_lesson_date}")

@stat_app.command("quarterly")
def quarterly_stat():
    """季度统计"""
    today = date.today()
    quarter = (today.month - 1) // 3 + 1
    start_month = (quarter - 1) * 3 + 1

    console.print(Panel(f"[blue]📊 {today.year}年 Q{quarter} 季度统计[/blue]"))

    total_lessons = 0
    total_attended = 0
    total_fee = 0
    total_paid = 0

    for month in range(start_month, start_month + 3):
        if month > 12:
            continue
        status = payment_manager.get_monthly_payment_status(today.year, month)
        total_lessons += status.total_lessons
        total_attended += status.attended_lessons
        total_fee += status.total_fee
        total_paid += status.paid_amount

    console.print(f"📚 总课程数: {total_lessons} 节")
    console.print(f"✅ 已上课: {total_attended} 节")
    console.print(f"💰 应缴总额: {total_fee} 元")
    console.print(f"💵 已缴金额: {total_paid} 元")
    console.print(f"❌ 累计待缴金额: {total_fee - total_paid} 元")


@stat_app.command("yearly")
def yearly_stat():
    """年度统计"""
    today = date.today()

    console.print(Panel(f"[blue]📊 {today.year}年 度统计[/blue]"))

    total_lessons = 0
    total_attended = 0
    total_fee = 0
    total_paid = 0

    for month in range(1, 13):
        status = payment_manager.get_monthly_payment_status(today.year, month)
        total_lessons += status.total_lessons
        total_attended += status.attended_lessons
        total_fee += status.total_fee
        total_paid += status.paid_amount

    console.print(f"📚 总课程数: {total_lessons} 节")
    console.print(f"✅ 已上课: {total_attended} 节")
    console.print(f"💰 应缴总额: {total_fee} 元")
    console.print(f"💵 已缴金额: {total_paid} 元")
    console.print(f"❌ 累计待缴金额: {total_fee - total_paid} 元")



@remind_app.command("monthly")
def remind_monthly():
    """发送月度课程计划通知"""
    from .notifier import TelegramNotifier

    today = date.today()
    plan = lesson_manager.generate_monthly_lessons(today.year, today.month)

    notifier = TelegramNotifier()
    notifier.send_monthly_lesson_plan(
        today.year, today.month, plan.lessons,
        plan.total_lessons, plan.holiday_conflicts, plan.total_fee
    )
    console.print(Panel("[green]✅ 已发送月度课程计划[/green]"))


@remind_app.command("weekly")
def remind_weekly():
    """发送下周上课确认提醒（每周日运行）"""
    from .notifier import TelegramNotifier
    from datetime import timedelta

    today = date.today()
    # 找到下周六
    days_until_saturday = (5 - today.weekday() + 7) % 7
    if days_until_saturday == 0:
        next_saturday = today
    else:
        next_saturday = today + timedelta(days=days_until_saturday)

    # 查询下周六的课程
    lessons = lesson_manager.get_lessons(next_saturday.year, next_saturday.month)
    next_saturday_lesson = next(
        (l for l in lessons if l.date == next_saturday and l.status != LessonStatus.CANCELLED),
        None
    )

    notifier = TelegramNotifier()

    if next_saturday_lesson:
        notifier.send_weekly_reminder(next_saturday, next_saturday_lesson.time, has_conflict=False)
        console.print(Panel(f"[green]✅ 已发送下周上课确认提醒 {next_saturday}[/green]"))
    else:
        # 检查是否有节假日冲突的课程
        conflict_lesson = next(
            (l for l in lessons if l.date == next_saturday and l.is_holiday_conflict),
            None
        )
        if conflict_lesson:
            notifier.send_weekly_reminder(next_saturday, None, has_conflict=True)
            console.print(Panel(f"[yellow]⚠️  下周 {next_saturday} 节假日冲突，已提醒调课[/yellow]"))
        else:
            console.print(Panel(f"[yellow]📭 下周 {next_saturday} 无课程安排[/yellow]"))


@remind_app.command("daily")
def remind_daily():
    """检查并发送当日上课提醒"""
    from .notifier import TelegramNotifier

    today = date.today()
    lessons = lesson_manager.get_lessons(today.year, today.month)
    today_lesson = next((l for l in lessons if l.date == today and l.status != LessonStatus.CANCELLED), None)

    if not today_lesson:
        console.print(Panel("[yellow]📭 今日无课程安排[/yellow]"))
        return

    notifier = TelegramNotifier()
    notifier.send_daily_reminder(today_lesson.date, today_lesson.time)
    console.print(Panel(f"[green]✅ 已发送今日上课提醒 {today_lesson.time}[/green]"))


@remind_app.command("payment")
def remind_payment():
    """检查并发送缴费提醒（当月最后一节课前一天晚上）"""
    from .notifier import TelegramNotifier
    from datetime import timedelta

    today = date.today()

    # ========== 次月1号二次兜底逻辑 ==========
    if today.day == 1:
        last_month = today.replace(day=1) - timedelta(days=1)
        last_month_status = payment_manager.get_monthly_payment_status(last_month.year, last_month.month)
        if last_month_status.balance > 0:
            notifier = TelegramNotifier()
            notifier.send_payment_overdue_reminder(
                last_month.month, last_month_status.balance, 0
            )
            console.print(Panel(f"[red]✅ 已发送上月欠费催缴提醒，待缴: {last_month_status.balance} 元[/red]"))
            return

    # ========== 当月最后一节课前一天提醒 ==========
    status = payment_manager.get_monthly_payment_status(today.year, today.month)

    lessons = lesson_manager.get_lessons(today.year, today.month)
    active_lessons = [l for l in lessons if l.status != LessonStatus.CANCELLED]

    if not active_lessons:
        console.print(Panel("[yellow]📭 本月无有效课程[/yellow]"))
        return

    last_lesson_date = max(l.date for l in active_lessons)

    # 已缴清，不提醒
    if status.balance <= 0:
        console.print(Panel("[green]✅ 本月已缴清学费[/green]"))
        return

    # 找到当月最后一个周六
    from calendar import monthrange
    last_saturday = None
    _, num_days = monthrange(today.year, today.month)
    for day in range(num_days, 0, -1):
        candidate = date(today.year, today.month, day)
        if candidate.weekday() == 5:
            last_saturday = candidate
            break
    reminder_trigger_date = last_saturday - timedelta(days=3) if last_saturday else None

    # 最后上课前一天晚上提醒（逻辑保留供参考）
    # if today == last_lesson_date - timedelta(days=1):
    if reminder_trigger_date and today == reminder_trigger_date:
        payload = payment_manager.get_payment_reminder_payload(today.year, today.month)
        notifier = TelegramNotifier()
        notifier.send(payload['message'])
        reason = 'N/A'
        if '原因：' in payload['message']:
            reason = payload['message'].split('原因：')[1].split('\n')[0]
        console.print(Panel(
            f"[green]✅ 已发送缴费提醒[/green]\n"
            f"💰 预计缴费: {payload['amount']} 元\n"
            f"📝 原因: {reason}"
        ))
    else:
        console.print(Panel(
            f"[dim]📅 本月最后一个周六是 {last_saturday}，"
            f"{reminder_trigger_date}（前3天）会发送预计缴费提醒[/dim]"
        ))

@remind_app.command("check")
def check_reminders():
    """检查 Reminders 列表中的指令"""
    from .reminders import RemindersManager

    sync = RemindersManager()

    if not sync.is_available:
        console.print(Panel("[red]❌ remindctl 不可用，请先安装[/red]"))
        raise typer.Exit(1)

    if not sync.list_exists():
        console.print(Panel(f"[yellow]⚠️  Reminders 列表 '{sync.list_name}' 不存在[/yellow]"))
        if typer.confirm("是否创建？"):
            sync.create_list()
            console.print(Panel("[green]✅ 已创建 Reminders 列表[/green]"))
        return

    commands = sync.check_new_commands()

    if not commands:
        console.print(Panel("[yellow]📭 未发现新指令[/yellow]"))
        return

    console.print(Panel(f"[blue]📋 发现 {len(commands)} 条新指令[/blue]"))
    for cmd in commands:
        console.print(f"- {cmd.action}: {cmd.date or cmd.amount or ''}")


@remind_app.command("sync")
def sync_reminders():
    """执行 Reminders 指令并标记为已完成"""
    from .reminders import RemindersManager

    sync = RemindersManager()

    if not sync.is_available:
        console.print(Panel("[red]❌ remindctl 不可用[/red]"))
        raise typer.Exit(1)

    commands = sync.check_new_commands()

    if not commands:
        console.print(Panel("[yellow]📭 无待执行指令[/yellow]"))
        return

    executed = 0
    for cmd in commands:
        try:
            if cmd.action == 'cancel' and cmd.date:
                lesson_manager.cancel_lesson(cmd.date)
                console.print(f"✅ 已取消课程: {cmd.date}")
                executed += 1
            elif cmd.action == 'add' and cmd.date:
                lesson_manager.add_lesson(cmd.date)
                console.print(f"✅ 已添加课程: {cmd.date}")
                executed += 1
            elif cmd.action == 'payment' and cmd.amount:
                payment_manager.record_payment(cmd.amount)
                console.print(f"✅ 已记录缴费: {cmd.amount} 元")
                executed += 1

            # 标记为已完成
            if hasattr(cmd, 'reminder_id'):
                sync.complete_reminder(cmd.reminder_id)

        except Exception as e:
            console.print(f"❌ 执行失败: {e}")

    console.print(Panel(f"[green]✅ 已执行 {executed}/{len(commands)} 条指令[/green]"))


# ============== Obsidian 导出 ==============
obsidian_app = typer.Typer(help="Obsidian 导出")
app.add_typer(obsidian_app, name="obsidian")


@obsidian_app.command("export")
def export_obsidian(
    month: Optional[str] = typer.Argument(None, help="月份，格式 YYYY-MM，默认当前月"),
):
    """导出月度报告到 Obsidian"""
    from .obsidian import ObsidianExporter

    exporter = ObsidianExporter()

    if month:
        year, month_num = parse_month(month)
    else:
        today = date.today()
        year, month_num = today.year, today.month

    lessons = lesson_manager.get_lessons(year, month_num)
    payments = payment_manager.get_payments(year, month_num)

    # 计算金额
    total_fee = sum(l.fee for l in lessons if l.status != 'cancelled')
    paid_amount = sum(p.amount for p in payments)

    filepath = exporter.export_monthly_report(year, month_num, lessons, payments, total_fee, paid_amount)

    # 创建索引
    exporter.create_index()

    console.print(Panel(f"[green]✅ 已导出到 Obsidian[/green]"))
    console.print(f"📄 文件: {filepath}")


@obsidian_app.command("note")
def create_note(
    date_str: str = typer.Argument(..., help="课程日期，格式 YYYY-MM-DD"),
):
    """创建单次课程笔记模板"""
    from .obsidian import ObsidianExporter

    lesson_date = parse_date(date_str)
    exporter = ObsidianExporter()
    filepath = exporter.export_lesson_note(lesson_date)

    console.print(Panel(f"[green]✅ 已创建课程笔记[/green]"))
    console.print(f"📄 文件: {filepath}")



# ============== 练习管理命令 ==============
from . import practice as practice_module


@practice_app.command("log")
def practice_log(
    ctx: typer.Context,
    date: str = typer.Option(None, "--date", "-d", help="日期，格式 YYYY-MM-DD，默认今天"),
    log: Optional[str] = typer.Option(None, "--log", "-l", help="详细练习记录/进展"),
    items: Annotated[list[str], typer.Argument(help="练习内容，格式 item_id:分钟")] = [],
):
    """记录每日练习（必须使用 item_id）

    示例:
        dizical practice log 1034:20 1003:15 1004:10
        dizical practice log --date 2026-04-26 1034:20
        dizical practice log --log "今天单吐终于连上了" 1003:15

    录入前可查看本周/历史练习要求中的 item_id：
        dizical practice assign --show-items
    """
    import datetime as dt

    items_list = list(items) + list(ctx.args)

    if date:
        practice_date = parse_date(date)
    else:
        practice_date = dt.date.today()

    # ── 录入前先展示推荐 item_id（本周 + 历史练习要求）───────────────
    today = dt.date.today()
    current_week_start = today - dt.timedelta(days=today.weekday())
    last_week_start = current_week_start - dt.timedelta(days=7)

    this_week_assign = db.get_weekly_assignment_for_week(today)
    last_week_assign = db.get_weekly_assignment_for_week(last_week_start)

    recommended_ids = set()
    assign_items = []
    for assign in [this_week_assign, last_week_assign]:
        if assign and assign.get('items'):
            for it in assign['items']:
                iid = it.get('item_id')
                if iid:
                    recommended_ids.add(iid)
                    assign_items.append({'item_id': iid, 'item': it.get('item') or it.get('name', '?'),
                                         'requirements': it.get('requirements') or it.get('requirement', '')})

    shown = []
    # 展示推荐练习
    if assign_items:
        console.print("\n[bold cyan]📋 练习要求中的科目：[/bold cyan]")
        for it in assign_items:
            if it['item_id'] not in shown:
                shown.append(it['item_id'])
                req_preview = it['requirements'][:30] + '...' if len(it['requirements']) > 30 else it['requirements']
                console.print(f"  [yellow]{it['item_id']}[/yellow]  {it['item']}  [dim]{req_preview}[/dim]")

    # 如果有遗漏的活跃科目也展示
    all_items = db.get_practice_items(active_only=True)
    shown_ids = set(shown)
    other_items = [it for it in all_items if it['item_id'] not in shown_ids]
    if other_items:
        console.print("\n[bold cyan]📚 其他活跃科目：[/bold cyan]")
        for it in other_items:
            console.print(f"  [yellow]{it['item_id']}[/yellow]  {it['name']}")

    console.print()

    # ── 解析输入（必须是 item_id:分钟）─────────────────────────────
    if not items_list and not log:
        console.print("[yellow]请提供练习内容，格式: item_id:分钟[/yellow]")
        console.print("[dim]示例: dizical practice log 1034:20 1003:15[/dim]")
        return

    raw_parts = ' '.join(items_list)
    raw_parts = raw_parts.replace('，', ' ').replace(',', ' ')
    all_parts = raw_parts.split()

    parsed = []
    invalid_entries = []
    for part in all_parts:
        if ':' in part:
            item_id_str, mins = part.split(':', 1)
            try:
                item_id = int(item_id_str.strip())
                minutes = int(mins)
                # 严格验证 item_id 必须存在
                if not db.validate_item_id(item_id):
                    invalid_entries.append((item_id_str.strip(), f"item_id {item_id} 不存在或已归档"))
                    continue
                parsed.append({'item_id': item_id, 'minutes': minutes})
            except ValueError:
                invalid_entries.append((item_id_str.strip(), "item_id 必须是整数"))
                continue

    if invalid_entries:
        for entry, reason in invalid_entries:
            console.print(f"[red]❌ 「{entry}:??」— {reason}[/red]")
        console.print("[yellow]使用 dizical practice log 查看可用 item_id[/yellow]")
        return

    if not parsed and not log:
        console.print("[yellow]请提供练习内容，格式: item_id:分钟[/yellow]")
        return

    # ── 写入 DB ────────────────────────────────────────────────────
    # 构建带 item_id 和 item_name 的 items 列表
    item_map = {it['item_id']: it['name'] for it in all_items}
    resolved_items = [{'item_id': p['item_id'], 'item': item_map.get(p['item_id'], '?'), 'minutes': p['minutes']} for p in parsed]

    total = practice_module.save_practice(practice_date, resolved_items, log=log,
                                        channel='cli', method='cli_log')
    msg = f"已记录 {practice_date} 练习: {total} 分钟"
    if log:
        msg += f"\n📝 {log}"
    console.print(f"[green]✅ {msg}[/green]")
    return


@practice_app.command("note")
def practice_note(
    ctx: typer.Context,
    date: str = typer.Option(None, "--date", "-d", help="日期，格式 YYYY-MM-DD，默认今天"),
    note_text: Annotated[list[str], typer.Argument(help="一句话进展描述")] = [],
):
    """记录每日一句话进展

    示例:
        dizical practice note 今天 基本功，纠正吹口位置
        dizical practice note -d 2026-04-26 采茶扑蝶有突破
    """
    from datetime import date as date_type

    note = ' '.join(list(note_text) + list(ctx.args))

    if date:
        practice_date = parse_date(date)
    else:
        practice_date = date_type.today()

    if not note.strip():
        console.print("[yellow]请提供进展描述[/yellow]")
        return

    practice_module.save_progress(practice_date, note.strip())
    console.print(f"[green]✅ 已记录进展: {note.strip()}[/green]")


@practice_app.command("assign")
def practice_assign(
    ctx: typer.Context,
    date: str = typer.Option(None, "--date", "-d", help="上课日期（YYYY-MM-DD），格式：2026-04-18"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="老师补充说明"),
    show_items: bool = typer.Option(False, "--show-items", help="录入前列出已有练习项目供补全"),
    img: list[str] = typer.Option([], "--image", "-i", help="老师要求配图路径，可多次指定"),
    items: Annotated[list[str], typer.Argument(help="练习项目和要求，格式 项目:要求")] = [],
):
    """录入每课老师要求（支持增量追加，漏了可以再执行追加）

    示例:
        dizical practice assign 单吐练习:♩=82,84,86各两天 回娘家:连线小节♩=78
        dizical practice assign -d 2026-04-20 单吐练习:♩=82,84,86各两天
        dizical practice assign -d 2026-04-20 回娘家:连线小节♩=78  # 增量追加，不会覆盖单吐练习
        dizical practice assign --show-items  # 先看有哪些项目，再录入
        dizical practice assign -d 2026-05-05 单吐练习:♩=82 -i ~/photos/req.jpg
        dizical practice assign -d 2026-05-05 1003:♩=82 1026:♩=80  # 用 item_id 直接命中科目
    """
    from . import practice as pm

    items_list = list(items) + list(ctx.args)

    # --show-items: 先列出已有项目
    if show_items:
        all_items = pm.db.get_practice_items(active_only=False)
        if all_items:
            item_names = sorted(set(it['name'] for it in all_items))
            console.print(f"[blue]已有练习项目 ({len(item_names)} 个)：[/blue]")
            for name in item_names:
                console.print(f"  • {name}")
        else:
            console.print("[yellow]暂无练习项目[/yellow]")
        # --show-items 只展示，不录入
        if not items_list:
            return

    if date:
        lesson_date = parse_date(date)
    else:
        # 自动推算：取最近一次已上课的日期
        lessons = pm.db.get_all_lessons()
        attended = [l for l in lessons if l.status == pm.LessonStatus.ATTENDED]
        if attended:
            last_lesson = max(attended, key=lambda l: l.date)
            lesson_date = last_lesson.date
            console.print(f"[blue]ℹ️  自动推算 lesson_date: {lesson_date}（最近已上课）[/blue]")
        else:
            console.print("[yellow]无法推算 lesson_date：请先用 'dizical lesson confirm' 确认上课日期，或使用 -d 指定[/yellow]")
            return

    if not items_list:
        console.print("[yellow]请提供练习项目和要求，格式 '项目:要求'[/yellow]")
        return

    parsed = []
    for part in items_list:
        if ':' not in part:
            continue
        item_key, req = part.split(':', 1)
        item_key = item_key.strip()
        req = req.strip()
        # 支持数字 ID 直接引用 practice_items
        if item_key.isdigit():
            pid = int(item_key)
            # 查 practice_items 表获取名称
            pi = pm.db.get_practice_item_by_id(pid)
            if pi:
                parsed.append({'item': pi['name'], 'item_id': pid, 'requirement': req})
            else:
                console.print(f"[yellow]⚠️  未找到 item_id={pid}，已跳过[/yellow]")
        else:
            parsed.append({'item': item_key, 'item_id': None, 'requirement': req})

    # ── Phase 2: 模糊匹配 + 确认拦截（参考 practice_log）─────────────────────────
    resolved_items = []
    for entry in parsed:
        raw_name = entry['item']
        # 精确匹配 → 直接收录
        all_items = pm.db.get_practice_items(active_only=False)
        exact = next((it['name'] for it in all_items if it['name'] == raw_name), None)
        if exact:
            resolved_items.append({'item': exact, 'item_id': next(it['item_id'] for it in all_items if it['name'] == exact), 'requirement': entry['requirement']})
            continue

        # 模糊匹配
        similar = pm.find_similar_items(raw_name)
        if not similar:
            # 无相似 → 直接新建（自动创建 practice_items 条目）
            new_id = pm.db.create_practice_item(raw_name)
            resolved_items.append({'item': raw_name, 'item_id': new_id, 'requirement': entry['requirement']})
            continue

        # 有相似 → 打印候选并等待用户选择
        console.print(f"\n[yellow]未找到完全匹配的小科目「{raw_name}」。[/yellow]")
        console.print("以下小科目与你的输入相似：")
        for i, (iid, name, score) in enumerate(similar[:5], 1):
            label = "高" if score >= 0.8 else "中" if score >= 0.5 else "低"
            console.print(f"  [{i}] {name} [dim]#{iid}[/dim]（相似度：{label}）")
        console.print(f"  [{len(similar)+1}] 新建小科目「{raw_name}（item_id=?）」")

        choice = None
        while choice is None:
            user_input = console.input("\n请选择 [1-{}/Enter取消]: ".format(len(similar)+1))
            if user_input.strip() == "":
                console.print("[dim]已取消本次录入[/dim]")
                return
            try:
                idx = int(user_input.strip())
                if 1 <= idx <= len(similar) + 1:
                    choice = idx
                else:
                    console.print(f"[red]请输入 1~{len(similar)+1} 或直接回车[/red]")
            except ValueError:
                console.print(f"[red]请输入 1~{len(similar)+1} 或直接回车[/red]")

        if choice <= len(similar):
            resolved_name = similar[choice - 1][1]
            resolved_id = similar[choice - 1][0]
            console.print(f"[dim]  → 关联已有科目：{resolved_name}[/dim]")
        else:
            resolved_name = raw_name
            new_id = pm.db.create_practice_item(raw_name)
            resolved_id = new_id
            console.print(f"[dim]  → 新建科目：{resolved_name}（item_id={new_id}）[/dim]")

        resolved_items.append({'item': resolved_name, 'item_id': resolved_id, 'requirement': entry['requirement']})

    if resolved_items:
        # 增量追加
        img_list = list(img) if img else None
        pm.save_weekly_assignment(lesson_date, resolved_items, notes, img_list)
        # 确认打印
        item_names = [p['item'] for p in resolved_items]
        for name in item_names:
            console.print(f"  • {name}")
        if img_list:
            console.print(f"[green]📷 配图 {len(img_list)} 张已保存[/green]")


@practice_app.command("assignments")
def practice_assignments(
    weeks: int = typer.Option(8, "--weeks", "-w", help="过去 N 课"),
    start: Optional[str] = typer.Option(None, "--start", "-s", help="开始日期 YYYY-MM-DD"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="结束日期 YYYY-MM-DD"),
    item: Optional[str] = typer.Option(None, "--item", "-i", help="只看某个练习项目"),
):
    """查询每课老师要求 — 交互式浏览，最新课在前面

    默认显示过去 8 课。支持 --weeks、--start/--end、--item 过滤。
    方向键 ↑↓ 浏览，回车展开科目要求，ESC 退出。
    """
    from . import practice as pm
    import datetime as dt

    # 解析日期范围
    if start and end:
        start_date = parse_date(start)
        end_date = parse_date(end)
        if not start_date or not end_date:
            console.print("[red]日期格式错误，使用 YYYY-MM-DD[/red]")
            return
        assignments = pm.query_assignments(start=start_date, end=end_date)
    else:
        assignments = pm.query_assignments(weeks=weeks)

    # 倒序：最新课在前
    assignments = sorted(assignments, key=lambda a: a['lesson_date'], reverse=True)

    if not assignments:
        console.print("[yellow]没有找到老师要求记录[/yellow]")
        return

    # 按项目过滤
    if item:
        filtered: List[Dict] = []
        for a in assignments:
            matched = [it for it in a['items'] if item in it['item']]
            if matched:
                filtered.append({**a, 'items': matched})
        assignments = filtered
        if not assignments:
            console.print(f"[yellow]没有找到包含「{item}」的记录[/yellow]")
            return

    # 启动 curses TUI
    curses.wrapper(_AssignmentsTUI(assignments).run)


# ── assignments TUI ───────────────────────────────────────────────────────────
class _AssignmentsTUI:
    """交互式浏览每课老师要求 — Rich Table 风格"""

    def __init__(self, assignments: List[Dict]):
        self.assignments = assignments
        self.cursor = 0       # 当前选中课
        self.expanded: set[int] = set()  # 展开的课索引

    def run(self, stdscr: curses.window) -> None:
        # 颜色初始化：透明背景以继承终端主题色
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(101, curses.COLOR_CYAN, -1)   # 标题
            curses.init_pair(102, curses.COLOR_WHITE, -1) # 默认文本（透明背景）
            curses.init_pair(103, curses.COLOR_YELLOW, -1) # 选中行
        stdscr.attrset(0)

        curses.curs_set(0)
        stdscr.nodelay(False)
        stdscr.keypad(True)
        stdscr.clear()

        h, w = stdscr.getmaxyx()
        while True:
            stdscr.clear()
            self._draw(stdscr, h, w)
            key = stdscr.getch()
            if key in (curses.KEY_UP,):
                self.cursor = max(0, self.cursor - 1)
            elif key in (curses.KEY_DOWN,):
                self.cursor = min(len(self.assignments) - 1, self.cursor + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                if self.cursor in self.expanded:
                    self.expanded.discard(self.cursor)
                else:
                    self.expanded.add(self.cursor)
            elif key in (ord('q'), ord('Q'), 27):
                break

    def _draw(self, stdscr: curses.window, h: int, w: int) -> None:
        try:
            # 标题行
            stdscr.addstr(0, 0, f" 🎵 每课老师要求  │  {len(self.assignments)} 课  │  [↑↓]浏览  [Enter]展开/收起  [Q/ESC]退出")
            stdscr.clrtoeol()
            stdscr.addstr(1, 0, "─" * (w - 1))
        except curses.error:
            pass

        row = 2
        for idx, a in enumerate(self.assignments):
            if row >= h - 3:
                break

            is_selected = (idx == self.cursor)
            ss = a.get('stage_start')
            se = a.get('stage_end')
            so = a.get('stage_order')
            order_str = f"第{so}课" if so else ""
            ld = a['lesson_date'].strftime('%m-%d')

            if ss and se:
                stage_str = f"{ss.strftime('%m-%d')}~{se.strftime('%m-%d')}"
            elif ss:
                stage_str = f"{ss.strftime('%m-%d')}~（未安排）"
            else:
                stage_str = "（无阶段）"

            item_count = len(a.get('items', []))
            img_count = len(a.get('images', []))

            prefix = "▶ " if is_selected else "  "
            extra = f"  📷{img_count}" if img_count else ""
            line = f"{prefix}{order_str} | {ld} | {stage_str} | {item_count}项{extra}"

            attr = curses.A_REVERSE if is_selected else curses.A_NORMAL
            try:
                stdscr.addstr(row, 0, line[:w-1], attr)
                stdscr.clrtoeol()
            except curses.error:
                pass
            row += 1

            # 展开的明细 — Rich Table 风格
            if is_selected and idx in self.expanded:
                items = a.get('items', [])
                notes = a.get('notes', '')
                if items or notes:
                    buf = io.StringIO()
                    rc = Console(file=buf, force_terminal=False, width=max(w - 8, 40))
                    rc.print(Panel(f"[bold cyan]{order_str}[/bold cyan]  {a['lesson_date'].strftime('%Y-%m-%d')}  老师要求", expand=False))

                    tbl = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
                    tbl.add_column("#", style="dim", width=2, justify="right")
                    tbl.add_column("ID", style="dim", width=5, justify="right")
                    tbl.add_column("练习项", style="bold white", width=14)
                    tbl.add_column("速度", style="dim", width=10)
                    tbl.add_column("老师要求", style="italic dim")

                    for i, it in enumerate(items, 1):
                        mins = it.get('minutes', 0)
                        mins_str = f"{mins}′" if mins else ""
                        req = (it.get('requirements') or "").strip().replace('\n', ' ')
                        item_id = it.get('item_id') or ''
                        metro = it.get('metronome') or ''
                        tbl.add_row(str(i), str(item_id), it.get('item', ''), metro, req)

                    rc.print(tbl)

                    if notes:
                        rc.print(Panel(f"[yellow]📝 {notes}[/yellow]", expand=False, style="yellow"))

                    for line in buf.getvalue().splitlines():
                        if row >= h - 2:
                            break
                        _render_rich_line(line, stdscr, row, 4, w)
                        row += 1


@practice_app.command("today")
def practice_today():
    """查看/录入今日练习"""
    from datetime import date as date_type

    today = date_type.today()
    existing = practice_module.db.get_daily_practice(today)

    if existing:
        console.print(Panel(f"[blue]📅 {today} 今日练习[/blue]"))
        console.print(f"总时长: {existing['total_minutes']} 分钟")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("项目")
        table.add_column("时长")
        for item in existing['items']:
            table.add_row(item['item'], f"{item['minutes']} 分钟")
        console.print(table)
    else:
        console.print(Panel(f"[yellow]📅 {today} 今日暂无练习记录[/yellow]"))
        console.print("使用 'dizical practice log 今天 基本功:20' 来记录")


@practice_app.command("query", help="交互式练习查询 TUI")
def practice_query():
    """启动交互式练习记录查询界面"""
    from . import practice_query as pq
    pq.launch()


@practice_app.command("thisweek")
def practice_thisweek():
    """查看本周练习情况"""
    from datetime import date as date_type

    today = date_type.today()
    week_start = practice_module.get_week_start(today)
    summary = practice_module.get_week_summary(week_start)

    console.print(Panel(f"[blue]📅 {week_start} ~ {summary['week_end']} 本周练习[/blue]"))
    console.print(f"练习天数: {summary['practice_days']} 天")
    console.print(f"总时长: {summary['total_minutes']} 分钟")

    if summary['item_totals']:
        console.print("\n[bold]各项目时长:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("项目")
        table.add_column("时长")
        for item, minutes in sorted(summary['item_totals'].items(), key=lambda x: -x[1]):
            table.add_row(item, f"{minutes} 分钟")
        console.print(table)

    if summary['assignment']:
        console.print("\n[bold]本周老师要求:[/bold]")
        for item in summary['assignment']['items']:
            console.print(f"  • {item['item']}: {item['requirement']}")


@practice_app.command("week")
def practice_week(
    date_str: Optional[str] = typer.Argument(None, help="该周任意日期，默认本周"),
):
    """本周练习日历视图"""
    from datetime import timedelta

    if date_str:
        week_start = practice_module.get_week_start(parse_date(date_str))
    else:
        today = date.today()
        week_start = practice_module.get_week_start(today)

    summary = practice_module.get_week_summary(week_start)
    days_data = practice_module.get_week_days(week_start)

    # ── 头部统计 ──
    week_num = week_start.isocalendar()[1]
    total_days = 7
    practiced_days = summary['practice_days']
    total_min = summary['total_minutes']
    pct = practiced_days / total_days * 100

    console.print(f"\n🎵 dizical 练习监控台")
    console.print(f"📅 {week_start} ~ {summary['week_end']} (第 {week_num} 周)")
    console.print(f"───────────────────────────────────────────")
    console.print(f"  本周练习: {practiced_days}/{total_days} 天   ⏱ {total_min} 分钟   📊 {pct:.0f}%")

    # ── 日历网格 ──
    console.print(f"───────────────────────────────────────────")
    console.print(f"   一    二    三    四    五    六    日")

    day_cells = []
    date_labels = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        key = d.isoformat()
        day_cells.append(days_data[key])
        date_labels.append(f"{d.month}/{d.day:02d}")

    # 日期行
    console.print("  " + "  ".join(f"{l:>4}" for l in date_labels))

    # 练习数据行 (合并到一行，7列)
    row_parts = []
    for i, (key, day) in enumerate(zip([(week_start + timedelta(days=i)).isoformat() for i in range(7)], day_cells)):
        if day['is_future']:
            row_parts.append("   - ")
        elif day['has_practice']:
            mins = day['total_minutes']
            if mins >= 60:
                row_parts.append(f"[green]{mins:>3}'*[green]")
            else:
                row_parts.append(f"[green]{mins:>3}' [green]")
        elif day['progress']:
            row_parts.append("[cyan]  +  [cyan]")
        else:
            row_parts.append("   - ")

    # 用空格连接，不破坏Rich标签
    console.print("  " + "  ".join(row_parts))

    # ── 项目分布 ──
    if summary['item_totals']:
        console.print(f"───────────────────────────────────────────")
        console.print(f"  📊 项目分布:")
        total = sum(summary['item_totals'].values())
        for item, mins in sorted(summary['item_totals'].items(), key=lambda x: -x[1]):
            pct_i = mins / total * 100 if total > 0 else 0
            bar_len = int(pct_i / 5)
            bar = "█" * bar_len + "." * (20 - bar_len)
            console.print(f"  {item:>6}: {mins:>3}' ({pct_i:>4.1f}%)  {bar}")

    # ── 每日详情（有练习或进展的天） ──
    detail_lines = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        key = d.isoformat()
        day = days_data[key]
        if day['is_future']:
            continue
        if day['has_practice']:
            items_str = " ".join(f"{it['item']}{it['minutes']}'" for it in day['items'])
            detail_lines.append(f"  [{d.month}/{d.day:02d}] {day['total_minutes']}' - {items_str}")
            if day['progress']:
                detail_lines.append(f"         📝 {day['progress']}")
        elif day['progress']:
            detail_lines.append(f"  [{d.month}/{d.day:02d}] (仅进展) {day['progress']}")

    if detail_lines:
        console.print(f"───────────────────────────────────────────")
        console.print(f"  📝 每日详情:")
        for line in detail_lines:
            console.print(line)

    console.print(f"\n  💡 补录昨天: dizical practice log 基本功:20")
    console.print(f"  💡 指定日期: dizical practice log -d 2026-04-29 基本功:20\n")


@practice_app.command("dashboard")
def practice_dashboard():
    """全貌仪表盘"""
    from . import practice as pm

    today = date.today()
    year, month = today.year, today.month

    # 本月热力图
    cal_data = pm.get_practice_calendar(year, month)
    import calendar
    cal = calendar.Calendar(firstweekday=0)

    console.print(Panel(f"[blue]📅 {year}年{month}月 练习热力图[/blue]"))
    console.print("  一   二   三   四   五   六   日")

    week = []
    for day in cal.itermonthdays(year, month):
        if day == 0:
            week.append("    ")
        else:
            day_date = f"{year:04d}-{month:02d}-{day:02d}"
            info = cal_data.get(day_date, {})
            if info.get('has_practice'):
                mins = info.get('total_minutes', 0)
                if mins >= 60:
                    week.append(f"[green]{day:2d}* [green]")
                else:
                    week.append(f"[green]{day:2d}- [green]")
            elif info.get('progress'):
                week.append(f"[cyan]{day:2d}+ [cyan]")
            else:
                week.append(f" {day:2d}  ")

        if len(week) == 7:
            console.print("  " + "  ".join(week))
            week = []

    console.print("  [dim]图例: [green]* 60+分钟[green] [green]- 有练习[green] [cyan]+ 有进展[cyan]  空白: 无记录[/dim]")

    # 本月统计
    summary = pm.get_month_summary(year, month)
    total_days = summary['total_days']
    practiced = summary['practice_days']
    total_min = summary['total_minutes']
    console.print(f"\n  📊 本月: {practiced}/{total_days} 天 ({practiced/total_days*100:.0f}%)  "
                  f"⏱ {total_min} 分钟 ({total_min//60}h {total_min%60}m)")

    # 项目分布 — Rich Table
    if summary['item_totals']:
        total = sum(summary['item_totals'].values())
        table = Table(show_header=True, header_style="bold magenta", title="📊 项目累计")
        table.add_column("项目", style="dim", width=14)
        table.add_column("分钟", justify="right")
        table.add_column("占比", justify="right")
        table.add_column("分布", width=22)
        for item, mins in sorted(summary['item_totals'].items(), key=lambda x: -x[1]):
            pct = mins / total * 100
            bar_len = int(pct / 5)
            bar = "█" * bar_len + "·" * (20 - bar_len)
            table.add_row(item, f"{mins}'", f"{pct:.1f}%", bar)
        console.print(table)

    # 近8周趋势
    console.print(f"\n  📈 近8周趋势:")
    import datetime as dtt
    week_starts = []
    for w in range(7, -1, -1):
        w_start = pm.get_week_start(today - dtt.timedelta(weeks=w))
        ws_summary = pm.get_week_summary(w_start)
        week_starts.append((w_start, ws_summary['total_minutes'], ws_summary['practice_days']))

    max_min = max(m for _, m, _ in week_starts) if week_starts else 1
    for row in range(11, -1, -1):
        line = "  "
        for _, m, _ in week_starts:
            if m == 0:
                line += "  "
            else:
                h = int(m / max_min * 12)
                line += "█" if h >= row else " "
        console.print(line)
    console.print("  " + "".join(f"W{(ws.isocalendar()[1] % 100):02d}" for ws, _, _ in week_starts))

    console.print()

@practice_app.command("calendar")
def practice_calendar(
    month: Optional[str] = typer.Argument(None, help="月份，格式 YYYY-MM，默认当前月"),
):
    """月度练习日历"""
    import calendar

    if month:
        year, month_num = parse_month(month)
    else:
        today = date.today()
        year, month_num = today.year, today.month

    cal_data = practice_module.get_practice_calendar(year, month_num)

    console.print(Panel(f"[blue]{year}年{month_num}月 练习日历[/blue]"))

    cal = calendar.Calendar(firstweekday=0)
    console.print("一  二  三  四  五  六  日")

    week = []
    for day in cal.itermonthdays(year, month_num):
        if day == 0:
            week.append("    ")
            continue

        day_date = f"{year:04d}-{month_num:02d}-{day:02d}"
        day_info = cal_data.get(day_date, {})

        # 进展标记+优先显示（独立于练习记录）
        if day_info.get('progress'):
            day_str = f"[cyan]{day:2d}+[/cyan]"
        elif day_info.get('has_practice'):
            mins = day_info.get('total_minutes', 0)
            if mins >= 60:
                day_str = f"[green]{day:2d}*[/green]"
            else:
                day_str = f"[green]{day:2d}-[/green]"
        else:
            day_str = f"{day:2d}  "

        week.append(day_str)

        if len(week) == 7:
            console.print("".join(_pad(d) for d in week))
            week = []

    if week:
        console.print("".join(_pad(d) for d in week))

    console.print("\n[dim]图例:[/dim] [cyan]+有进展[/cyan] [green]*60+分钟[/green] [green]-有练习[/green]  (空白)无记录")


@practice_app.command("stats")
def practice_stats(
    month: Optional[str] = typer.Argument(None, help="月份，格式 YYYY-MM，默认当前月"),
):
    """统计报表"""
    if month:
        year, month_num = parse_month(month)
    else:
        today = date.today()
        year, month_num = today.year, today.month

    summary = practice_module.get_month_summary(year, month_num)

    console.print(Panel(f"[blue]📊 {year}年{month_num}月 练习统计[/blue]"))
    console.print(f"练习天数: {summary['practice_days']} / {summary['total_days']} 天")
    console.print(f"总时长: {summary['total_minutes']} 分钟 ({summary['total_minutes'] // 60} 小时 {summary['total_minutes'] % 60} 分)")

    if summary['item_totals']:
        console.print("\n[bold]各项目时长:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("项目")
        table.add_column("时长")
        table.add_column("占比")
        total = summary['total_minutes']
        for item, minutes in sorted(summary['item_totals'].items(), key=lambda x: -x[1]):
            pct = minutes / total * 100
            table.add_row(item, f"{minutes} 分钟", f"{pct:.1f}%")
        console.print(table)


@practice_app.command("import")
def practice_import(
    csv_path: str = typer.Argument(..., help="CSV 文件路径"),
):
    """导入历史练习记录（从 Notion CSV）"""
    success, failures = practice_module.import_from_csv(csv_path)
    if success > 0:
        console.print(f"[green]✅ 成功导入 {success} 天练习记录[/green]")
    if failures > 0:
        console.print(f"[yellow]⚠️  {failures} 行导入失败[/yellow]")


@practice_app.command("import_logs")
def practice_import_logs(
    csv_path: str = typer.Argument(..., help="CSV 文件路径（Date,Log）"),
):
    """批量导入练习进展log（CSV格式：Date,Log）"""
    success, failures = practice_module.import_logs_from_csv(csv_path)
    if success > 0:
        console.print(f"[green]✅ 成功导入 {success} 条进展log[/green]")
    if failures > 0:
        console.print(f"[yellow]⚠️  {failures} 行导入失败[/yellow]")


@practice_app.command("import-assignments")
def practice_import_assignments(
    csv_path: str = typer.Argument(..., help="CSV 文件路径（WeekStart,Item,Requirement）"),
):
    """批量导入每周老师要求（CSV格式：WeekStart,Item,Requirement）"""
    success, failures = practice_module.import_assignments_from_csv(csv_path)
    if success > 0:
        console.print(f"[green]✅ 成功导入 {success} 周老师要求[/green]")
    if failures > 0:
        console.print(f"[yellow]⚠️  {failures} 行导入失败[/yellow]")


@practice_app.command("config")
def practice_config():
    """打开练习配置 TUI（大小科目管理）"""
    from .practice_config import launch
    launch()


@practice_app.command("items")
def practice_items():
    """查看所有练习项目"""
    items = practice_module.db.get_practice_items(active_only=False)
    if items:
        console.print(Panel("[blue]📋 练习项目库[/blue]"))
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID")
        table.add_column("名称")
        table.add_column("大科目")
        table.add_column("状态")
        for item in items:
            status = "[green]活跃[/green]" if item['is_active'] else "[dim]已停用[/dim]"
            cat = item.get('category_name') or '[dim]-[/dim]'
            table.add_row(str(item['item_id']), item['name'], cat, status)
        console.print(table)
    else:
        console.print("[yellow]暂无练习项目[/yellow]")


@practice_app.command("report")
def practice_report(
    ctx: typer.Context,
    year: int = typer.Option(None, "--year", "-y", help="年份，默认今年"),
    month: int = typer.Option(None, "--month", "-m", help="月份，默认本月"),
    style: str = typer.Option("academic", "--style", "-s", help="模板风格（academic/cute/minimal/vintage）"),
    aspect: str = typer.Option(None, "--aspect", help="图片比例（portrait/landscape/square），覆盖模板默认值"),
):
    """
    生成练习月报图片（调用 Hermes image generation）

    示例:
        dizical practice report -y 2026 -m 3
        dizical practice report --style academic
        dizical practice report -s cute -m 4
        dizical practice report --style vintage --aspect landscape
    """
    from .report_templates import list_templates, get_template, build_prompt
    import datetime as dt

    today = dt.date.today()
    year = year or today.year
    month = month or today.month

    # 列出可用模板
    templates = list_templates()
    available = list(templates.keys())
    if style not in available:
        console.print(f"[yellow]⚠️  未知风格 '{style}'，可用: {', '.join(available)}[/yellow]")
        console.print("使用默认 academic...")
        style = "academic"

    tmpl_info = templates[style]
    console.print(Panel(f"[blue]练习月报生成中[/blue]\n"
                        f"📅 {year}年{month}月 | 🎨 {tmpl_info['name']} ({tmpl_info['description']})"))

    # 获取数据
    data = practice_module.get_month_summary(year, month)
    if data["total_minutes"] == 0 and not data["item_totals"]:
        console.print("[yellow]⚠️  当月无练习数据，无法生成报告[/yellow]")
        return

    # 构建 prompt
    prompt, default_aspect = build_prompt(year, month, data, template_id=style)
    aspect_ratio = aspect or default_aspect

    console.print(f"[green]✅ Prompt 构建完成[/green]")
    console.print(f"   模板: {style} ({tmpl_info['name']})")
    console.print(f"   比例: {aspect_ratio}")
    console.print(f"   数据: {data['total_minutes']}分钟 / {data['practice_days']}天")
    console.print(f"\n[dim]提示：通过 alcove profile 说「生成{year}年{month}月练习报告，使用{style}风格」可自动完成图像生成和保存[/dim]")


@practice_category_app.command("list")
def practice_category_list():
    """查看所有大科目及其小科目"""
    categories = practice_module.get_categories()
    items = practice_module.db.get_practice_items(active_only=False)

    console.print(Panel("[blue]🏷️  练习大科目[/blue]"))
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("大科目")
    table.add_column("小科目")
    for cat in categories:
        cat_items = sorted((i for i in items if i.get('category_id') == cat['id']), key=lambda x: x.get('item_id', 0))
        sub_items = '、'.join(f"{i['name']}({i['item_id']})" for i in cat_items) if cat_items else '[dim]无[/dim]'
        table.add_row(str(cat['id']), cat['name'], sub_items)
    console.print(table)


@practice_category_app.command("add")
def practice_category_add(
    name: str = typer.Argument(..., help="大科目名称"),
    sort_order: int = typer.Option(99, "--order", "-o", help="排序序号，越小越靠前"),
):
    """新增大科目"""
    cat_id = practice_module.add_category(name, sort_order)
    console.print(f"[green]✅ 已新增大科目: {name} (ID={cat_id})[/green]")


@practice_category_app.command("del")
def practice_category_del(
    cat_id: int = typer.Argument(..., help="大科目ID"),
):
    """删除大科目（不会删除小科目）"""
    practice_module.delete_category(cat_id)
    console.print(f"[green]✅ 已删除大科目 ID={cat_id}[/green]")


@practice_category_app.command("update")
def practice_category_update(
    cat_id: int = typer.Argument(..., help="大科目ID"),
    name: str = typer.Option(None, "--name", "-n", help="新名称"),
    sort_order: int = typer.Option(None, "--order", "-o", help="排序序号，越小越靠前"),
):
    """更新大科目名称或排序

    示例:
        dizical practice category update 1 -n 基本功2 -o 1
        dizical practice category update 3 --name 气息 --order 2
    """
    if not name and sort_order is None:
        console.print("[yellow]请提供 --name 或 --order 参数[/yellow]")
        return
    practice_module.update_category(cat_id, name, sort_order)
    console.print(f"[green]✅ 已更新大科目 ID={cat_id}[/green]")


@practice_category_app.command("set-item")
def practice_category_set_item(
    item_name: str = typer.Argument(..., help="小科目名称"),
    category: str = typer.Argument(..., help="大科目名称或 '-' 取消归属"),
):
    """设置小科目归属的大科目

    示例:
        dizical practice category set-item 单吐练习 基本功
        dizical practice category set-item 采茶扑蝶 -
    """
    if category == '-':
        practice_module.set_item_category(item_name, None)
        console.print(f"[green]✅ 已取消 {item_name} 的归属[/green]")
    else:
        categories = practice_module.get_categories()
        cat_map = {c['name']: c['id'] for c in categories}
        if category not in cat_map:
            console.print(f"[red]❌ 未找到大科目: {category}，可用: {', '.join(cat_map.keys())}[/red]")
            return
        practice_module.set_item_category(item_name, cat_map[category])
        console.print(f"[green]✅ 已将 {item_name} 归属到 {category}[/green]")


# ============== 提醒管理命令 ==============
from .reminders import get_reminders_manager
from .notifier import get_notifier


@remind_app.command("check")
def reminders_check():
    """检查并处理待处理的 Reminder 指令"""
    manager = get_reminders_manager()
    lesson_mgr = LessonManager()
    payment_mgr = PaymentManager()

    success, failed = manager.process_pending(lesson_mgr, payment_mgr)

    if success > 0:
        console.print(f"[green]✅ 成功处理 {success} 条指令[/green]")
    if failed > 0:
        console.print(f"[red]❌ 失败 {failed} 条[/red]")
    if success == 0 and failed == 0:
        console.print("[yellow]没有待处理的指令[/yellow]")


@remind_app.command("list")
def reminders_list():
    """列出所有待处理的 Reminder"""
    manager = get_reminders_manager()
    items = manager.get_pending_items()

    if not items:
        console.print("[yellow]没有待处理的提醒[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("标题")
    table.add_column("到期日")
    for item in items:
        table.add_row(
            item.get("id", ""),
            item.get("title", ""),
            item.get("due", ""),
        )
    console.print(table)


@remind_app.command("send")
def reminders_send(
    type: str = typer.Argument(..., help="提醒类型: lesson/payment/monthly"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="日期"),
):
    """手动发送 Telegram 提醒"""
    notifier = get_notifier()
    if not notifier.is_configured():
        console.print("[yellow]Telegram 未配置，跳过发送[/yellow]")
        return

    if type == "lesson":
        lesson_date = date or str(date.today())
        notifier.send_lesson_reminder(lesson_date, "17:15")
    elif type == "payment":
        lesson_mgr = LessonManager()
        payment_mgr = PaymentManager()
        status = payment_mgr.get_monthly_payment_status(date.today().year, date.today().month)
        last_date = lesson_mgr.get_last_lesson_date(date.today().year, date.today().month)
        notifier.send_payment_reminder(status["total_unpaid"], str(last_date))
    elif type == "monthly":
        notifier.send_monthly_schedule("本月课程计划已生成")
    else:
        console.print(f"[red]未知类型: {type}[/red]")
        return

    console.print("[green]✅ 提醒已发送[/green]")


# ============== 导出管理命令 ==============
from .obsidian import get_exporter


@export_app.command("monthly")
def export_monthly(
    year: int = typer.Option(None, "--year", "-y", help="年份，默认今年"),
    month: int = typer.Option(None, "--month", "-m", help="月份，默认本月"),
):
    """导出月度报告到 Obsidian"""
    today = date.today()
    year = year or today.year
    month = month or today.month

    exporter = get_exporter()
    try:
        file_path = exporter.export_monthly_report(year, month)
        console.print(f"[green]✅ 月报已导出: {file_path}[/green]")
    except Exception as e:
        console.print(f"[red]❌ 导出失败: {e}[/red]")


@export_app.command("yearly")
def export_yearly(
    year: int = typer.Option(None, "--year", "-y", help="年份，默认今年"),
):
    """导出年度总结到 Obsidian"""
    year = year or date.today().year

    exporter = get_exporter()
    try:
        file_path = exporter.export_yearly_report(year)
        console.print(f"[green]✅ 年度总结已导出: {file_path}[/green]")
    except Exception as e:
        console.print(f"[red]❌ 导出失败: {e}[/red]")


@export_app.command("practice")
def export_practice(
    week_start: str = typer.Argument(..., help="周开始日期（周一），格式 YYYY-MM-DD"),
):
    """导出周练习报告到 Obsidian"""
    from datetime import datetime as dt

    try:
        ws = dt.strptime(week_start, "%Y-%m-%d").date()
    except ValueError:
        console.print("[red]❌ 日期格式错误，请使用 YYYY-MM-DD[/red]")
        return

    exporter = get_exporter()
    try:
        file_path = exporter.export_weekly_practice_report(ws)
        console.print(f"[green]✅ 周练习报告已导出: {file_path}[/green]")
    except Exception as e:
        console.print(f"[red]❌ 导出失败: {e}[/red]")


# ============== 服务状态监控命令 ==============
import subprocess
import urllib.request
import urllib.error
import time as _time
from datetime import datetime, date
import curses


def _check_kid_app_process() -> tuple[bool, int | None]:
    """检查 kid-app 进程是否存在，返回 (运行中, PID)"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn.*8765"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            pid = int(result.stdout.strip().split()[0])
            return True, pid
        return False, None
    except Exception:
        return False, None


def _check_port_listening(port: int = 8765) -> bool:
    """检查端口是否在监听"""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True,
        )
        return result.returncode == 0 and result.stdout.strip()
    except Exception:
        return False


def _check_http_response(port: int = 8765, path: str = "/prepare") -> tuple[int | None, float | None]:
    """检查 HTTP 响应码和耗时(秒)，失败返回 (None, None)"""
    url = f"http://localhost:{port}{path}"
    start = _time.time()
    try:
        req = urllib.request.urlopen(url, timeout=3)
        elapsed = _time.time() - start
        return req.status, elapsed
    except urllib.error.HTTPError as e:
        elapsed = _time.time() - start
        return e.code, elapsed
    except Exception:
        return None, None


def _get_local_ip() -> str:
    try:
        import socket as _s
        s = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _get_last_practice() -> str | None:
    """获取最近一次练习记录"""
    try:
        from src.database import db
        from src.models import DailyPractice
        row = db.query(
            "SELECT date, minutes, items FROM daily_practice ORDER BY date DESC LIMIT 1"
        ).fetchone()
        if row:
            d, minutes, items_json = row
            from src.practice import parse_items_json
            items = parse_items_json(items_json) if items_json else []
            item_names = [i.get("name", "?") for i in items[:3]]
            items_str = " / ".join(item_names) if item_names else "无科目"
            return f"{d}  {minutes}分钟  {items_str}"
        return None
    except Exception:
        return None


def _render_dashboard(stdscr, running: bool, pid: int | None, port_ok: bool,
                       status: int | None, elapsed: float | None,
                       local_ip: str, last_practice: str | None,
                       refresh_time: str):
    """在 curses 窗口上渲染 dashboard"""
    curses.curs_set(0)
    stdscr.clear()

    # 颜色初始化
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        GREEN = curses.color_pair(1)
        RED = curses.color_pair(2)
        YELLOW = curses.color_pair(3)
        CYAN = curses.color_pair(4)
        MAGENTA = curses.color_pair(5)
        BOLD = curses.A_BOLD
    else:
        GREEN = RED = YELLOW = CYAN = MAGENTA = 0
        BOLD = curses.A_BOLD

    h, w = stdscr.getmaxyx()
    if h < 12 or w < 60:
        stdscr.addstr(0, 0, "窗口太小，请放大终端")
        stdscr.refresh()
        return

    # ---- 标题栏 ----
    title = "  dizical status  "
    stdscr.attrset(BOLD | CYAN)
    stdscr.addstr(0, 0, f"┌{'─' * (w - 2)}┐")
    stdscr.addstr(1, 0, "│" + title.center(w - 2) + "│")
    stdscr.addstr(2, 0, f"└{'─' * (w - 2)}┘")

    # ---- 进程状态 ----
    row = 4
    stdscr.attrset(BOLD)
    stdscr.addstr(row, 0, "  🛰  kid-app 进程")
    row += 1
    if running and pid:
        stdscr.attrset(GREEN)
        stdscr.addstr(row, 2, f"✅ 运行中  (PID {pid})")
    else:
        stdscr.attrset(RED)
        stdscr.addstr(row, 2, "❌ 未运行  →  执行: dizical-kid start")
    row += 2

    # ---- 端口状态 ----
    stdscr.attrset(BOLD)
    stdscr.addstr(row, 0, "  🔌  端口 8765")
    row += 1
    if port_ok:
        stdscr.attrset(GREEN)
        stdscr.addstr(row, 2, "✅ 监听中")
    else:
        stdscr.attrset(RED)
        stdscr.addstr(row, 2, "❌ 未监听")
    row += 2

    # ---- HTTP 状态 ----
    stdscr.attrset(BOLD)
    stdscr.addstr(row, 0, "  🌐  HTTP /prepare")
    row += 1
    if status == 200:
        elaps_ms = round(elapsed * 1000) if elapsed else 0
        stdscr.attrset(GREEN)
        stdscr.addstr(row, 2, f"✅ {status}  ({elaps_ms}ms)")
    elif status is not None:
        stdscr.attrset(YELLOW)
        stdscr.addstr(row, 2, f"⚠️  HTTP {status}")
    else:
        stdscr.attrset(RED)
        stdscr.addstr(row, 2, "❌ 无法访问")
    row += 2

    # ---- iPad 访问地址 ----
    stdscr.attrset(BOLD)
    stdscr.addstr(row, 0, "  📱  iPad 访问")
    row += 1
    stdscr.attrset(CYAN)
    stdscr.addstr(row, 2, f"  http://{local_ip}:8765")
    row += 2

    # ---- 最近练习 ----
    stdscr.attrset(BOLD)
    stdscr.addstr(row, 0, "  🎵  最近练习")
    row += 1
    if last_practice:
        stdscr.attrset(0)
        stdscr.addstr(row, 2, f"  {last_practice}")
    else:
        stdscr.attrset(MAGENTA)
        stdscr.addstr(row, 2, "  暂无记录")
    row += 2

    # ---- 刷新时间 + 帮助 ----
    stdscr.attrset(curses.A_DIM)
    stdscr.addstr(row, 0, f"  刷新: {refresh_time}    Q=退出  R=手动刷新")
    row += 1

    stdscr.refresh()


def _status_loop(stdscr):
    """curses 事件循环：支持 Q 退出、R 刷新、自动 3 秒刷新"""
    local_ip = _get_local_ip()
    refresh_time = datetime.now().strftime("%H:%M:%S")
    last_practice = _get_last_practice()
    auto_refresh_count = 0

    # 初始状态
    running, pid = _check_kid_app_process()
    port_ok = _check_port_listening()
    status, elapsed = _check_http_response()
    _render_dashboard(stdscr, running, pid, port_ok, status, elapsed,
                      local_ip, last_practice, refresh_time)

    stdscr.nodelay(True)  # 非阻塞

    while True:
        # 自动刷新：每 3 秒
        stdscr.addstr(0, 0, "")  # 重置位置（避免报错）
        try:
            key = stdscr.getch()
            if key != -1:
                ch = chr(key) if 32 <= key < 127 else ""
                if ch in ("q", "Q", "\x1b"):  # Q 或 Esc
                    break
                if ch in ("r", "R"):
                    refresh_time = datetime.now().strftime("%H:%M:%S")
                    last_practice = _get_last_practice()
                    running, pid = _check_kid_app_process()
                    port_ok = _check_port_listening()
                    status, elapsed = _check_http_response()
                    auto_refresh_count = 0
                    _render_dashboard(stdscr, running, pid, port_ok, status, elapsed,
                                      local_ip, last_practice, refresh_time)
                continue
        except curses.error:
            pass

        auto_refresh_count += 1
        if auto_refresh_count >= 30:  # ~3 秒（100ms * 30）
            auto_refresh_count = 0
            refresh_time = datetime.now().strftime("%H:%M:%S")
            last_practice = _get_last_practice()
            running, pid = _check_kid_app_process()
            port_ok = _check_port_listening()
            status, elapsed = _check_http_response()
            _render_dashboard(stdscr, running, pid, port_ok, status, elapsed,
                              local_ip, last_practice, refresh_time)
        _time.sleep(0.1)


@app.command("status")
def dizical_status():
    """🎛  实时监控 dizical kid-app 服务状态"""
    curses.wrapper(_status_loop)


# ============== 备份管理命令 ==============
from .backup import backup_all, list_backups, backup_info


@backup_app.command("run")
def backup_run():
    """执行数据库备份（本地 + iCloud 双重冗余）"""
    try:
        results = backup_all()
        if results:
            console.print(f"[green]✅ 备份成功，共 {len(results)} 个文件:[/green]\n")
            for r in results:
                p = r["path"]
                console.print(f"  📦 {p.name}")
                console.print(f"     本地: {p}")
                console.print(f"     {r['verify_msg']}")
                console.print(f"     {r['icloud_msg']}")
                console.print()
        else:
            console.print("[yellow]⚠️  没有找到需要备份的数据库文件[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 备份失败: {e}[/red]")


@backup_app.command("list")
def backup_list():
    """列出所有备份"""
    info = backup_info()
    console.print(Panel(info, title="数据库备份状态"))

if __name__ == "__main__":
    app()
