import datetime as dt
from typing import List, Optional
from .models import Payment, PaymentStatus, LessonStatus


class PaymentManager:
    """缴费管理核心逻辑"""

    def __init__(self, db=None):
        from .database import Database
        from .lesson_manager import LessonManager
        self.db = db or Database()
        self.lesson_manager = LessonManager(self.db)

    def get_monthly_payment_status(self, year: int, month: int) -> PaymentStatus:
        """
        获取指定月份的缴费状态

        Args:
            year: 年份
            month: 月份

        Returns:
            缴费状态对象
        """
        lessons = self.db.get_lessons_by_month(year, month)
        # 统计所有缴费记录，不限制月份（缴费可以在任何时间）
        all_payments = self.db.get_all_payments()

        # 统计有效课程（未取消的）
        active_lessons = [l for l in lessons if l.status != LessonStatus.CANCELLED]
        attended_lessons = [l for l in lessons if l.status == LessonStatus.ATTENDED]
        unpaid_lessons = [l for l in active_lessons if not l.fee_paid]

        total_fee = sum(l.fee for l in active_lessons)
        # 计算该月的已缴金额
        # 简单做法：所有缴费都计入（因为缴费记录可能没有明确对应到月份）
        # 更好的做法是：只统计 lesson_ids 包含该月课程的缴费
        paid_amount = sum(p.amount for p in all_payments)

        # 获取最后一个上课日
        last_lesson_date = self.lesson_manager.get_last_lesson_date(year, month)

        # 计算缴费提醒日期（最后一课前2天）
        payment_reminder_date = None
        if last_lesson_date:
            payment_reminder_date = last_lesson_date - dt.timedelta(days=2)

        return PaymentStatus(
            month=dt.date(year, month, 1),
            total_lessons=len(active_lessons),
            attended_lessons=len(attended_lessons),
            unpaid_lessons=len(unpaid_lessons),
            total_fee=total_fee,
            paid_amount=paid_amount,
            balance=total_fee - paid_amount,
            last_lesson_date=last_lesson_date,
            payment_reminder_date=payment_reminder_date,
        )

    def record_payment(self, amount: int, payment_date: Optional[dt.date] = None,
                       lesson_ids: str = "", notes: Optional[str] = None) -> Payment:
        """
        记录缴费

        Args:
            amount: 缴费金额
            payment_date: 缴费日期，默认今天
            lesson_ids: 覆盖的课程ID（逗号分隔）
            notes: 备注

        Returns:
            缴费记录对象
        """
        if payment_date is None:
            payment_date = dt.date.today()

        payment = Payment(
            payment_date=payment_date,
            amount=amount,
            lesson_ids=lesson_ids,
            payment_method="现金",
            notes=notes,
        )

        # 自动标记相关课程为已缴费
        if lesson_ids:
            try:
                ids = [int(id_str.strip()) for id_str in lesson_ids.split(',') if id_str.strip()]
                for lesson_id in ids:
                    lesson = self.db.get_lesson(lesson_id)
                    if lesson:
                        lesson.fee_paid = True
                        self.db.update_lesson(lesson)
            except (ValueError, TypeError):
                # 如果解析失败，继续创建缴费记录
                pass

        return self.db.add_payment(payment)

    def get_payment_history(self) -> List[Payment]:
        """
        获取所有缴费历史

        Returns:
            所有缴费记录列表
        """
        return self.db.get_all_payments()

    def get_unpaid_lessons(self, year: Optional[int] = None, month: Optional[int] = None) -> List[int]:
        """
        获取未缴费的课程ID列表

        Args:
            year: 年份，可选
            month: 月份，可选

        Returns:
            未缴费的课程ID列表
        """
        if year and month:
            lessons = self.db.get_lessons_by_month(year, month)
        else:
            lessons = self.db.get_all_lessons()

        active_lessons = [
            l for l in lessons
            if l.status != LessonStatus.CANCELLED and not l.fee_paid
        ]

        return [l.id for l in active_lessons if l.id is not None]

    def should_send_reminder(self, check_date: Optional[dt.date] = None) -> bool:
        """
        判断指定日期是否应该发送缴费提醒

        Args:
            check_date: 检查的日期，默认今天

        Returns:
            是否应该发送缴费提醒
        """
        if check_date is None:
            check_date = dt.date.today()

        status = self.get_monthly_payment_status(check_date.year, check_date.month)

        # 如果已经缴清费用，不需要提醒
        if status.balance <= 0:
            return False

        # 如果缴费提醒日期是今天，需要发送提醒
        if status.payment_reminder_date == check_date:
            return True

        return False

    def get_payments(self, year: int, month: int):
        """
        获取指定月份的缴费记录

        Args:
            year: 年份
            month: 月份

        Returns:
            缴费记录列表
        """
        return self.db.get_payments_by_month(year, month)

    def get_reminder_message(self, year: int, month: int) -> str:
        """
        生成缴费提醒消息

        Args:
            year: 年份
            month: 月份

        Returns:
            缴费提醒消息字符串
        """
        status = self.get_monthly_payment_status(year, month)

        lines = [
            f"📅 {year}年{month}月 缴费提醒",
            "",
            f"📚 本月课程: {status.total_lessons} 节",
            f"✅ 已上课: {status.attended_lessons} 节",
            f"💰 应缴总额: {status.total_fee} 元",
            f"💵 已缴金额: {status.paid_amount} 元",
        ]

        if status.balance > 0:
            lines.append(f"❌ 待缴余额: {status.balance} 元")
            if status.last_lesson_date:
                lines.append(f"📆 最后上课日: {status.last_lesson_date}")
                lines.append(f"⏰ 请在 {status.last_lesson_date} 上课前缴清当月费用")
        else:
            lines.append("✅ 本月费用已缴清")

        lines.append("")
        lines.append("💡 提示: 学费为600元/节，现金支付")

        return "\n".join(lines)
