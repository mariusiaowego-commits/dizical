from datetime import date
from typing import Optional, Annotated
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

app = typer.Typer(help="🎵 竹笛学习助手 - 课程管理与缴费提醒")
console = Console()


def _pad(text: str, width: int = 4) -> str:
    """按终端显示宽度对齐（emoji占2列），忽略rich标签"""
    stripped = _RICH_TAG.sub("", text)
    visible = wcwidth.wcswidth(stripped)
    return text + " " * (width - visible)

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
        console.print(f"[red]❌ 待缴余额: {status.balance} 元[/red]")
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
        console.print(f"  - 待缴余额: [red]{payment_status.balance} 元[/red]")
    else:
        console.print(f"  - 待缴余额: [green]{payment_status.balance} 元[/green]")
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
    console.print(f"❌ 待缴余额: {total_fee - total_paid} 元")


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
    console.print(f"❌ 待缴余额: {total_fee - total_paid} 元")



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

    # 最后上课前一天晚上提醒
    if today == last_lesson_date - timedelta(days=1):
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
            f"[dim]📅 本月最后一节课是 {last_lesson_date}，"
            f"{last_lesson_date - timedelta(days=1)} 前一天会发送预计缴费提醒[/dim]"
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


if __name__ == "__main__":
    app()


# ============== 练习管理命令 ==============
from . import practice as practice_module


@practice_app.command("log")
def practice_log(
    ctx: typer.Context,
    date: str = typer.Option(None, "--date", "-d", help="日期，格式 YYYY-MM-DD，默认今天"),
    log: Optional[str] = typer.Option(None, "--log", "-l", help="详细练习记录/进展"),
    items: Annotated[list[str], typer.Argument(help="练习内容，格式 项目:分钟")] = [],
):
    """记录每日练习

    示例:
        dizical practice log 基本功:20 单吐:15 采茶扑蝶:10
        dizical practice log --date 2026-04-26 基本功:20
        dizical practice log --log "今天单吐终于连上了" 基本功:20
    """
    import datetime as dt

    items_list = list(items) + list(ctx.args)

    if date:
        practice_date = parse_date(date)
    else:
        # 默认补录昨天
        practice_date = dt.date.today() - dt.timedelta(days=1)

    # 解析 items
    parsed = []
    for part in items_list:
        if ':' in part:
            item_name, mins = part.split(':', 1)
            try:
                minutes = int(mins)
                parsed.append({'item': item_name.strip(), 'minutes': minutes})
            except ValueError:
                console.print(f"[red]❌ 无效时长: {mins}[/red]")
                return

    if parsed or log:
        total = practice_module.save_practice(practice_date, parsed, log=log)
        msg = f"已记录 {practice_date} 练习: {total} 分钟"
        if log:
            msg += f"\n📝 {log}"
        console.print(f"[green]✅ {msg}[/green]")
    else:
        console.print("[yellow]请提供练习内容或记录，如: dizical practice log '基本功:20' --log '今天有进步'[/yellow]")
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
    date: str = typer.Option(None, "--date", "-d", help="周开始日期（周一），格式 YYYY-MM-DD"),
    notes: Optional[str] = typer.Option(None, "--notes", "-n", help="老师补充说明"),
    items: Annotated[list[str], typer.Argument(help="练习项目和要求，格式 项目:要求")] = [],
):
    """录入每周老师要求

    示例:
        dizical practice assign 单吐练习:♩=82,84,86各两天 回娘家:连线小节♩=78
        dizical practice assign -d 2026-04-20 单吐练习:♩=82,84,86各两天
    """
    items_list = list(items) + list(ctx.args)

    if date:
        week_start = parse_date(date)
    else:
        # 自动推算：取最近一次已上课的下一天作为 WeekStart
        inferred = practice_module.get_last_attended_lesson_date_next()
        if inferred:
            week_start = inferred
            console.print(f"[blue]ℹ️  自动推算 WeekStart: {week_start}（上次课后次日）[/blue]")
        else:
            console.print("[yellow]无法推算 WeekStart：请先用 'dizical lesson confirm' 确认上课日期，或使用 -d 指定[/yellow]")
            return

    if not items_list:
        console.print("[yellow]请提供练习项目和要求，格式 '项目:要求'[/yellow]")
        return

    parsed = []
    for part in items_list:
        if ':' in part:
            item_name, req = part.split(':', 1)
            parsed.append({'item': item_name.strip(), 'requirement': req.strip()})

    if parsed:
        practice_module.save_weekly_assignment(week_start, parsed, notes)
        console.print(f"[green]✅ 已录入 {week_start} 的每周要求[/green]")


@practice_app.command("assignments")
def practice_assignments(
    weeks: int = typer.Option(4, "--weeks", "-w", help="过去 N 周"),
    start: Optional[str] = typer.Option(None, "--start", "-s", help="开始日期 YYYY-MM-DD"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="结束日期 YYYY-MM-DD"),
    item: Optional[str] = typer.Option(None, "--item", "-i", help="只看某个练习项目"),
):
    """查询每周老师要求（明细 + 汇总）

    默认显示过去 4 周。支持 --weeks、--start/--end、--item 过滤。
    """
    from . import practice as pm

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

    # ── 汇总头部 ──
    total_items = sum(len(a['items']) for a in assignments)
    date_range = f"{assignments[0]['week_start_date']} ~ {assignments[-1]['week_start_date']}"
    console.print(f"\n📋 每周老师要求")
    console.print(f"  范围: {date_range}  ({len(assignments)} 周, {total_items} 条要求)")

    # ── 项目频次汇总 ──
    item_counts: Dict[str, int] = {}
    for a in assignments:
        for it in a['items']:
            item_counts[it['item']] = item_counts.get(it['item'], 0) + 1
    if item_counts:
        console.print(f"\n  📊 项目频次:")
        for name, cnt in sorted(item_counts.items(), key=lambda x: -x[1]):
            console.print(f"    {name}: {cnt} 次")

    # ── 每周明细 ──
    import sys
    out = lambda msg: sys.stdout.write(msg + '\n')

    out("")
    out(f"  周起始      项目            要求")
    out(f"  {'─' * 72}")

    for a in assignments:
        week_str = a['week_start_date'].isoformat()
        for idx, it in enumerate(a['items']):
            req_preview = it['requirement'].strip().replace('\n', ' ')
            if len(req_preview) > 40:
                req_preview = req_preview[:40] + '...'
            out(f"  {week_str}  {it['item']:<12}  {req_preview}")
        if a.get('notes'):
            notes_preview = a['notes'].replace('\n', ' ')[:44]
            out(f"  {' ' * len(week_str)}  {'📝':<12}  {notes_preview}")
        out("")

    out(f"  💡 补录: dizical practice assign -d {assignments[-1]['week_start_date']} 项目:要求")


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
            bar = "#" * bar_len + "." * (20 - bar_len)
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

    console.print(f"\n📅 {year}年{month}月 练习热力图")
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

    # 项目分布
    if summary['item_totals']:
        total = sum(summary['item_totals'].values())
        console.print(f"\n  📊 项目累计:")
        for item, mins in sorted(summary['item_totals'].items(), key=lambda x: -x[1]):
            pct = mins / total * 100
            bar_len = int(pct / 5)
            bar = "#" * bar_len + "." * (20 - bar_len)
            console.print(f"  {item:>8}: {mins:>3}' ({pct:>5.1f}%)  {bar}")

    # 近8周趋势
    console.print(f"\n  📈 近8周趋势:")
    import datetime as dtt
    week_starts = []
    for w in range(7, -1, -1):
        w_start = pm.get_week_start(today - dtt.timedelta(weeks=w))
        ws_summary = pm.get_week_summary(w_start)
        week_starts.append((w_start, ws_summary['total_minutes'], ws_summary['practice_days']))

    max_min = max(m for _, m, _ in week_starts) if week_starts else 1
    # 趋势条形图（每列高度=时长比例，12行高度）
    for row in range(11, -1, -1):
        line = "  "
        for _, m, _ in week_starts:
            if m == 0:
                line += "  "
            else:
                h = int(m / max_min * 12)
                line += "#" if h >= row else " "
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
            table.add_row(str(item['id']), item['name'], cat, status)
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
        cat_items = [i['name'] for i in items if i.get('category_id') == cat['id']]
        sub_items = '、'.join(cat_items) if cat_items else '[dim]无[/dim]'
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


# ============== 备份管理命令 ==============
from .backup import backup_all, list_backups, backup_info


@backup_app.command("run")
def backup_run():
    """执行数据库备份"""
    try:
        results = backup_all()
        if results:
            console.print(f"[green]✅ 备份成功，共 {len(results)} 个文件:[/green]")
            for r in results:
                console.print(f"  {r.name}")
        else:
            console.print("[yellow]⚠️  没有找到需要备份的数据库文件[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 备份失败: {e}[/red]")


@backup_app.command("list")
def backup_list():
    """列出所有备份"""
    info = backup_info()
    console.print(Panel(info, title="数据库备份状态"))
