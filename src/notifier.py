"""
通知格式化模块
配合 Hermes Telegram Gateway 使用，输出直接发送到 home channel
"""
from typing import Optional
from datetime import date


class Notifier:
    """通知格式化器"""

    def __init__(self):
        pass

    def format_message(self, text: str) -> str:
        """格式化消息"""
        return text

    def send_monthly_lesson_plan(self, year: int, month: int, lessons: list,
                                 total_lessons: int, holiday_conflicts: int,
                                 total_fee: int) -> str:
        """
        格式化月度课程计划

        Returns:
            格式化后的消息文本，Hermes 会自动发送到 Telegram
        """
        lines = [
            f"📅 *{year}年{month}月 课程计划*",
            f"",
            f"📚 总课程数: {total_lessons} 节",
            f"⚠️  节假日冲突: {holiday_conflicts} 节",
            f"💰 总学费: {total_fee} 元",
            f"",
            f"*课程列表:*",
        ]

        for lesson in lessons:
            status_icon = "⚠️ " if lesson.is_holiday_conflict else "✅ "
            lines.append(f"{status_icon} {lesson.date.strftime('%m-%d')} {lesson.time}")

        lines.extend([
            f"",
            f"如有冲突提前调课"
        ])

        text = "\n".join(lines)
        print(text)  # Hermes 会捕获输出并发送到 Telegram
        return text

    def send_weekly_reminder(self, lesson_date, lesson_time, has_conflict: bool = False) -> str:
        """
        格式化下周上课确认提醒
        """
        # 去掉时间的秒部分
        time_str = str(lesson_time)[:5]  # 17:15:00 → 17:15

        if has_conflict:
            text = (
                f"⚠️ 下周竹笛课冲突\n\n"
                f"{lesson_date.strftime('%m-%d')} 周六是节假日\n"
                f"需调课的话，去 Reminders 改就行"
            )
        else:
            text = (
                f"🎵 下周竹笛课\n\n"
                f"周六 {lesson_date.strftime('%m-%d')} {time_str}\n"
                f"有变化去 Reminders 改"
            )
        print(text)
        return text

    def send_daily_reminder(self, lesson_date: date, lesson_time) -> str:
        """
        格式化当日上课提醒
        """
        text = (
            f"🔔 *今日上课提醒*\n"
            f"\n"
            f"日期: {lesson_date.strftime('%Y年%m月%d日')}\n"
            f"时间: {lesson_time}\n"
            f"\n"
            f"记得带竹笛和乐谱 🎵"
        )
        print(text)
        return text

    def send_payment_reminder(self, due_date: date, amount_due: int,
                               unpaid_lessons: int) -> str:
        """
        格式化缴费提醒
        """
        text = (
            f"💰 该交学费啦\n\n"
            f"本月还有 {unpaid_lessons} 节课\n"
            f"应交: {amount_due} 元\n\n"
            f"月底前记得交一下哈"
        )
        print(text)
        return text

    def send_payment_overdue_reminder(self, month: int, amount_due: int, unpaid_lessons: int) -> str:
        """
        格式化上月欠费催缴提醒（次月1号兜底）
        """
        text = (
            f"🔴 *上月欠费提醒*\n"
            f"\n"
            f"{month}月还有 {unpaid_lessons} 节课未缴费\n"
            f"合计: {amount_due} 元\n"
            f"\n"
            f"及时缴费"
        )
        print(text)
        return text

    def send_payment_confirmation(self, amount: int, payment_date: date) -> str:
        """
        格式化缴费确认
        """
        text = (
            f"✅ *缴费确认*\n"
            f"\n"
            f"缴费金额: {amount} 元\n"
            f"缴费日期: {payment_date.strftime('%Y年%m月%d日')}\n"
            f"\n"
            f"已收到学费 🎵"
        )
        print(text)
        return text

    def send_lesson_change_notification(self, action: str, lesson_date: date,
                                        new_date: Optional[date] = None) -> str:
        """
        格式化课程变动通知
        """
        if action == "add":
            text = f"📝 *加课通知*\n\n已添加课程: {lesson_date.strftime('%Y年%m月%d日')}"
        elif action == "cancel":
            text = f"❌ *取消课程*\n\n已取消课程: {lesson_date.strftime('%Y年%m月%d日')}"
        elif action == "reschedule":
            text = (
                f"🔄 *调课通知*\n\n"
                f"原课程: {lesson_date.strftime('%Y年%m月%d日')}\n"
                f"调整为: {new_date.strftime('%Y年%m月%d日')}"
            )
        else:
            text = f"📋 *课程变动*\n\n{action}: {lesson_date.strftime('%Y年%m月%d日')}"

        print(text)
        return text
