from datetime import date
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from .lesson_manager import LessonManager
from .payment import PaymentManager
from .models import LessonStatus

app = typer.Typer(help="🎵 竹笛学习助手 - 课程管理与缴费提醒")
console = Console()

lesson_app = typer.Typer(help="课程管理")
payment_app = typer.Typer(help="缴费管理")
stat_app = typer.Typer(help="统计报表")

app.add_typer(lesson_app, name="lesson")
app.add_typer(payment_app, name="payment")
app.add_typer(stat_app, name="stat")

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
                    day_str = f"[red]{day:2d}❌[/red]"
                elif lesson.is_holiday_conflict:
                    day_str = f"[yellow]{day:2d}⚠️[/yellow]"
                elif lesson.fee_paid:
                    day_str = f"[green]{day:2d}💰[/green]"
                else:
                    day_str = f"[blue]{day:2d}🎵[/blue]"
            else:
                day_str = f"{day:2d}  "

            week.append(day_str)

            if len(week) == 7:
                console.print("".join(f"{d:<4}" for d in week))
                week = []

        if week:
            console.print("".join(f"{d:<4}" for d in week))

        # 下一个月
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    console.print("\n[dim]图例: [/dim][blue]🎵 有课[/blue] [green]💰 已缴费[/green] [yellow]⚠️ 节假日冲突[/yellow] [red]❌ 已取消[/red]")


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
    console.print(f"  - 应缴总额: {payment_status.total_fee} 元")
    console.print(f"  - 已缴金额: {payment_status.paid_amount} 元")
    console.print(f"  - 待缴余额: {payment_status.balance} 元")

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


# ============== 提醒系统 ==============
remind_app = typer.Typer(help="提醒通知")
app.add_typer(remind_app, name="remind")


@remind_app.command("monthly")
def remind_monthly():
    """发送月度课程计划通知"""
    from .notifier import Notifier

    today = date.today()
    plan = lesson_manager.generate_monthly_lessons(today.year, today.month)

    notifier = Notifier()
    notifier.send_monthly_lesson_plan(
        today.year, today.month, plan.lessons,
        plan.total_lessons, plan.holiday_conflicts, plan.total_fee
    )
    console.print(Panel("[green]✅ 已发送月度课程计划[/green]"))


@remind_app.command("weekly")
def remind_weekly():
    """发送下周上课确认提醒（每周日运行）"""
    from .notifier import Notifier
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
        (l for l in lessons if l.date == next_saturday and l.status != 'cancelled'),
        None
    )

    notifier = Notifier()

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
    from .notifier import Notifier

    today = date.today()
    lessons = lesson_manager.get_lessons(today.year, today.month)
    today_lesson = next((l for l in lessons if l.date == today and l.status != 'cancelled'), None)

    if not today_lesson:
        console.print(Panel("[yellow]📭 今日无课程安排[/yellow]"))
        return

    notifier = Notifier()
    notifier.send_daily_reminder(today_lesson.date, today_lesson.time)
    console.print(Panel(f"[green]✅ 已发送今日上课提醒 {today_lesson.time}[/green]"))


@remind_app.command("payment")
def remind_payment():
    """检查并发送缴费提醒（每月最后一节课当天 + 次月1号二次兜底）"""
    from .notifier import Notifier
    from datetime import timedelta

    today = date.today()

    # ========== 次月1号二次兜底逻辑 ==========
    # 如果今天是1号，检查上个月是否还有欠费
    if today.day == 1:
        last_month = today.replace(day=1) - timedelta(days=1)
        last_month_status = payment_manager.get_monthly_payment_status(last_month.year, last_month.month)
        if last_month_status.balance > 0:
            notifier = Notifier()
            notifier.send_payment_overdue_reminder(
                last_month.month, last_month_status.balance, last_month_status.unpaid_lessons
            )
            console.print(Panel(f"[red]✅ 已发送上月欠费催缴提醒，待缴: {last_month_status.balance} 元[/red]"))
            return

    # ========== 当月最后一节课当天提醒 ==========
    status = payment_manager.get_monthly_payment_status(today.year, today.month)

    # 已缴清，不提醒
    if status.balance <= 0:
        console.print(Panel("[green]✅ 本月已缴清学费[/green]"))
        return

    # 找到当月最后一节非取消的课程
    lessons = lesson_manager.get_lessons(today.year, today.month)
    active_lessons = [l for l in lessons if l.status != 'cancelled']

    if not active_lessons:
        console.print(Panel("[yellow]📭 本月无有效课程[/yellow]"))
        return

    last_lesson_date = max(l.date for l in active_lessons)

    # 只有当天是最后一节课才发提醒
    if today == last_lesson_date:
        notifier = Notifier()
        notifier.send_payment_reminder(last_lesson_date, status.balance, status.unpaid_lessons)
        console.print(Panel(f"[green]✅ 已发送缴费提醒，待缴: {status.balance} 元[/green]"))
    else:
        console.print(Panel(
            f"[dim]📅 本月最后一节课是 {last_lesson_date}，当天会自动提醒缴费[/dim]"
        ))


# ============== Reminders 同步 ==============
reminders_app = typer.Typer(help="Apple Reminders 同步")
app.add_typer(reminders_app, name="reminders")


@reminders_app.command("check")
def check_reminders():
    """检查 Reminders 列表中的指令"""
    from .reminders import RemindersSync

    sync = RemindersSync()

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


@reminders_app.command("sync")
def sync_reminders():
    """执行 Reminders 指令并标记为已完成"""
    from .reminders import RemindersSync

    sync = RemindersSync()

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
