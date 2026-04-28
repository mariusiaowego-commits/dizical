import datetime as dt
import re
from typing import List, Optional, Dict
from .models import Payment, PaymentStatus, LessonStatus, settings


class PaymentManager:
    """缴费管理核心逻辑"""

    def __init__(self, db=None):
        from .database import Database
        from .lesson_manager import LessonManager
        self.db = db or Database()
        self.lesson_manager = LessonManager(self.db)

    def _get_month_payments(self, year: int, month: int) -> List[Payment]:
        """
        获取当月应缴的缴费记录。

        优先按 lesson_ids 关联课程所属月份；无 lesson_ids 则按 payment_date。
        这样避免「4月缴3月课费」被误归入4月的问题。
        """
        all_payments = self.db.get_all_payments()
        target_month_payments = []

        for p in all_payments:
            # 优先通过 lesson_ids 关联课程月份
            if p.lesson_ids:
                try:
                    lesson_ids = [int(id_str.strip()) for id_str in p.lesson_ids.split(',') if id_str.strip()]
                    if lesson_ids:
                        first_lesson = self.db.get_lesson(lesson_ids[0])
                        if first_lesson and first_lesson.date.year == year and first_lesson.date.month == month:
                            target_month_payments.append(p)
                            continue
                except (ValueError, TypeError):
                    pass

            # 无 lesson_ids：优先从 notes 解析月份（如 "3月课费" → 3月）
            matched = False
            if p.notes:
                m = re.search(r'(\d+)月', p.notes)
                if m:
                    notes_month = int(m.group(1))
                    if notes_month == month:
                        target_month_payments.append(p)
                        matched = True
            # 有 notes 但月份不匹配：不归入任何月份（防误归）
            # 无 notes 且 payment_date 匹配：按日期归类（兼容无备注的新数据）
            if not matched and not p.notes and p.payment_date.year == year and p.payment_date.month == month:
                target_month_payments.append(p)

        return target_month_payments

    def _get_lesson_fee(self, lesson) -> int:
        """获取课程费用，优先用课程自己的 fee，否则用默认配置"""
        return lesson.fee if lesson.fee > 0 else settings.default_fee

    def get_monthly_payment_status(self, year: int, month: int) -> PaymentStatus:
        """
        获取指定月份的缴费状态

        费用计算逻辑：
        - total_fee：已上课节数 × 课时费（历史准确值）
        - estimated_fee：当月预计缴费 = (已上课 + 剩余待上课) × 课时费
          用于月末最后上课前一天的预计缴费提醒
        """
        today = dt.date.today()
        lessons = self.db.get_lessons_by_month(year, month)

        # 分类统计
        attended = [l for l in lessons if l.status == LessonStatus.ATTENDED]
        scheduled = [l for l in lessons if l.status == LessonStatus.SCHEDULED]
        cancelled = [l for l in lessons if l.status == LessonStatus.CANCELLED]

        attended_count = len(attended)
        scheduled_count = len(scheduled)
        cancelled_count = len(cancelled)

        # 课时费
        fee_per_lesson = self._get_lesson_fee(attended[0]) if attended else settings.default_fee

        # 当月应缴 = 已上课 × 课时费
        total_fee = attended_count * fee_per_lesson

        # 当月预计缴费 = (已上课 + 剩余待上) × 课时费
        # 只有在当月还未结束，或有未上课的 SCHEDULED 课程时才与 total_fee 不同
        estimated_fee = total_fee + scheduled_count * fee_per_lesson

        # 当月已缴费（仅统计当月 date 的缴费记录）
        month_payments = self._get_month_payments(year, month)
        paid_amount = sum(p.amount for p in month_payments)

        # 余额 = 预计缴费 - 已缴
        balance = estimated_fee - paid_amount

        # 费用明细
        if scheduled_count > 0:
            payment_breakdown = (
                f"{attended_count}节已上({total_fee}) "
                f"+ {scheduled_count}节待上({scheduled_count * fee_per_lesson})"
            )
        else:
            payment_breakdown = f"{attended_count}节已上({total_fee})"

        # 最后上课日
        all_active = attended + scheduled
        last_lesson_date = max((l.date for l in all_active), default=None)

        # 缴费提醒日：最后上课前一天
        payment_reminder_date = last_lesson_date - dt.timedelta(days=1) if last_lesson_date else None

        # 判断是否当月
        is_current_month = (year == today.year and month == today.month)
        is_past_month = (year < today.year) or (year == today.year and month < today.month)

        # 过往月份：用准确值（无预计）
        if is_past_month:
            estimated_fee = total_fee
            balance = total_fee - paid_amount
            payment_breakdown = f"{attended_count}节({total_fee})"

        # 历史累计已缴：从去年9月至当月底的所有缴费总额
        # 用于展示「一开始到现在共缴了多少」
        START_YEAR, START_MONTH = 2025, 9
        historical_cumulative_paid = 0
        for p in self.db.get_all_payments():
            pym = (p.payment_date.year, p.payment_date.month)
            sm = (START_YEAR, START_MONTH)
            em = (year, month)
            if sm <= pym <= em:
                historical_cumulative_paid += p.amount

        return PaymentStatus(
            month=dt.date(year, month, 1),
            total_lessons=len(lessons),
            attended_lessons=attended_count,
            remaining_scheduled=scheduled_count,
            cancelled_lessons=cancelled_count,
            total_fee=total_fee,
            estimated_fee=estimated_fee,
            paid_amount=paid_amount,
            historical_cumulative_paid=historical_cumulative_paid,
            balance=balance,
            payment_breakdown=payment_breakdown,
            last_lesson_date=last_lesson_date,
            payment_reminder_date=payment_reminder_date,
        )

    def get_payment_history_summary(self) -> Dict:
        """
        获取历史累计缴费概况
        """
        all_lessons = self.db.get_all_lessons()
        all_payments = self.db.get_all_payments()

        total_attended = sum(1 for l in all_lessons if l.status == LessonStatus.ATTENDED)
        total_cancelled = sum(1 for l in all_lessons if l.status == LessonStatus.CANCELLED)

        # 按月统计上课次数
        monthly_attended: Dict[str, int] = {}
        for l in all_lessons:
            if l.status == LessonStatus.ATTENDED:
                key = l.date.strftime('%Y-%m')
                monthly_attended[key] = monthly_attended.get(key, 0) + 1

        total_paid = sum(p.amount for p in all_payments)

        return {
            'total_attended': total_attended,
            'total_cancelled': total_cancelled,
            'monthly_attended': monthly_attended,
            'total_paid': total_paid,
        }

    def get_monthly_payment_detail(self, year: int, month: int) -> Dict:
        """
        获取指定月份的详细财务明细
        """
        status = self.get_monthly_payment_status(year, month)
        lessons = self.db.get_lessons_by_month(year, month)
        month_payments = self._get_month_payments(year, month)

        # 课程明细
        lesson_details = []
        for l in sorted(lessons, key=lambda x: x.date):
            lesson_details.append({
                'date': l.date.isoformat(),
                'status': l.status.value,
                'fee': self._get_lesson_fee(l),
                'fee_paid': l.fee_paid,
            })

        return {
            'status': status,
            'lessons': lesson_details,
            'payments': [{'date': p.payment_date.isoformat(), 'amount': p.amount} for p in month_payments],
        }

    def record_payment(self, amount: int, payment_date: Optional[dt.date] = None,
                       lesson_ids: str = "", notes: Optional[str] = None) -> Payment:
        """记录缴费"""
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
                pass

        return self.db.add_payment(payment)

    def get_payment_history(self) -> List[Payment]:
        """获取所有缴费历史"""
        return self.db.get_all_payments()

    def get_unpaid_lessons(self, year: Optional[int] = None, month: Optional[int] = None) -> List[int]:
        """获取未缴费的课程ID列表"""
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
        """判断指定日期是否应该发送缴费提醒"""
        if check_date is None:
            check_date = dt.date.today()

        status = self.get_monthly_payment_status(check_date.year, check_date.month)

        if status.balance <= 0:
            return False

        if status.payment_reminder_date == check_date:
            return True

        return False

    def get_payments(self, year: int, month: int):
        """获取指定月份的缴费记录"""
        return self.db.get_payments_by_month(year, month)

    def get_reminder_message(self, year: int, month: int) -> str:
        """
        生成缴费提醒消息（含预计缴费金额和明细原因）
        """
        today = dt.date.today()
        status = self.get_monthly_payment_status(year, month)
        lessons = self.db.get_lessons_by_month(year, month)
        attended = [l for l in lessons if l.status == LessonStatus.ATTENDED]
        scheduled = [l for l in lessons if l.status == LessonStatus.SCHEDULED]

        lines = [
            f"📅 {year}年{month}月 缴费提醒",
            "",
            f"📚 本月课程: {status.total_lessons} 节",
            f"✅ 已上课: {status.attended_lessons} 节",
            f"📋 费用明细: {status.payment_breakdown}",
            f"💰 预计缴费: {status.estimated_fee} 元",
            f"💵 已缴金额: {status.paid_amount} 元",
        ]

        if status.balance > 0:
            lines.append(f"❌ 待缴余额: {status.balance} 元")
            if status.last_lesson_date:
                lines.append(f"📆 最后上课日: {status.last_lesson_date}")
                lines.append(f"⏰ 请在 {status.last_lesson_date} 上课前缴清")
        else:
            lines.append("✅ 本月费用已缴清")

        lines.append("")
        lines.append(f"💡 提示: 学费为{self._get_lesson_fee(lessons[0]) if lessons else settings.default_fee}元/节，现金支付")

        return "\n".join(lines)

    def get_payment_reminder_payload(self, year: int, month: int) -> Dict:
        """
        获取缴费提醒数据（供 remind payment 命令使用）
        返回 dict，包含 message 和 amount
        """
        today = dt.date.today()
        status = self.get_monthly_payment_status(year, month)
        lessons = self.db.get_lessons_by_month(year, month)

        attended = [l for l in lessons if l.status == LessonStatus.ATTENDED]
        scheduled = [l for l in lessons if l.status == LessonStatus.SCHEDULED]

        # 构造原因说明
        reason_parts = []
        if attended:
            fee_per = self._get_lesson_fee(attended[0])
            reason_parts.append(f"{len(attended)}节已上({len(attended) * fee_per})")
        if scheduled:
            fee_per = self._get_lesson_fee(scheduled[0]) if scheduled else settings.default_fee
            reason_parts.append(f"{len(scheduled)}节待上({len(scheduled) * fee_per})")

        reason = " + ".join(reason_parts) if reason_parts else f"{status.estimated_fee}"

        # 日期列表
        all_dates = sorted([l.date for l in lessons if l.status != LessonStatus.CANCELLED])
        date_list = "、".join(d.strftime('%m-%d') for d in all_dates)

        message = (
            f"💰 *缴费提醒*\n\n"
            f"{year}年{month}月 明天本月最后一节课，"
            f"本月预计缴费 *{status.estimated_fee}* 元\n"
            f"原因：{reason}\n"
            f"上课日：{date_list}\n"
            f"最后上课日：{status.last_lesson_date}\n\n"
            f"请准备好现金缴费。"
        )

        return {
            'amount': status.estimated_fee,
            'balance': status.balance,
            'message': message,
            'last_lesson_date': status.last_lesson_date,
            'attended_count': len(attended),
            'scheduled_count': len(scheduled),
        }
