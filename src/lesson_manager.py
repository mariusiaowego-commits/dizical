import datetime as dt
from typing import List, Optional
from calendar import monthrange
from .models import Lesson, LessonStatus, MonthlyLessonPlan, settings
from .database import db
from .holiday import HolidayChecker


class LessonManager:
    """课程管理核心逻辑"""

    DEFAULT_WEEKDAY = 5  # 周六 (0=周一, 5=周六)
    DEFAULT_TIME = dt.time(17, 15)
    DEFAULT_FEE = 600

    def __init__(self, db=None):
        from .database import Database
        self.db = db or Database()
        self.default_weekday = settings.default_weekday
        self.default_time = self._parse_time(settings.default_time)
        self.default_fee = settings.default_fee

    @staticmethod
    def _parse_time(time_str: str) -> dt.time:
        """解析时间字符串"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return dt.time(hour, minute)
        except Exception:
            return LessonManager.DEFAULT_TIME

    def get_saturdays(self, year: int, month: int) -> List[dt.date]:
        """
        获取指定月份的所有周六

        Args:
            year: 年份
            month: 月份

        Returns:
            该月所有周六的日期列表
        """
        _, num_days = monthrange(year, month)
        saturdays = []

        for day in range(1, num_days + 1):
            current_date = dt.date(year, month, day)
            if current_date.weekday() == self.default_weekday:
                saturdays.append(current_date)

        return saturdays

    def generate_monthly_lessons(self, year: int, month: int, overwrite: bool = False) -> MonthlyLessonPlan:
        """
        生成指定月份的课程计划

        Args:
            year: 年份
            month: 月份
            overwrite: 是否覆盖已存在的课程

        Returns:
            月度课程计划
        """
        saturdays = self.get_saturdays(year, month)
        existing_lessons = {l.date: l for l in self.db.get_lessons_by_month(year, month)}

        lessons = []

        for lesson_date in saturdays:
            # 检查是否已存在
            if lesson_date in existing_lessons and not overwrite:
                lessons.append(existing_lessons[lesson_date])
                continue

            # 检查节假日冲突 - 只有法定节假日（有名称）才标记冲突，普通周末不算
            is_holiday, holiday_name = HolidayChecker.check_holiday_status(lesson_date)
            has_holiday_conflict = is_holiday and holiday_name is not None

            lesson = Lesson(
                date=lesson_date,
                time=self.default_time,
                status=LessonStatus.SCHEDULED,
                fee=self.default_fee,
                fee_paid=False,
                is_holiday_conflict=has_holiday_conflict,
                notes=f"节假日冲突: {holiday_name}" if has_holiday_conflict else None,
            )

            if overwrite and lesson_date in existing_lessons:
                existing = existing_lessons[lesson_date]
                lesson.id = existing.id
                lesson = self.db.update_lesson(lesson)
            else:
                lesson = self.db.add_lesson(lesson)

            lessons.append(lesson)

        # 统计节假日冲突 - 只有法定节假日（有名称）才算冲突，普通周末不算
        holiday_conflicts = sum(1 for l in lessons if l.is_holiday_conflict)

        return MonthlyLessonPlan(
            year=year,
            month=month,
            lessons=lessons,
            total_lessons=len(lessons),
            holiday_conflicts=holiday_conflicts,
            total_fee=sum(l.fee for l in lessons if l.status != LessonStatus.CANCELLED),
        )

    def add_lesson(self, lesson_date: dt.date, lesson_time: Optional[dt.time] = None,
                   fee: Optional[int] = None) -> Lesson:
        """
        添加单个课程

        Args:
            lesson_date: 上课日期
            lesson_time: 上课时间，默认使用配置
            fee: 学费，默认使用配置

        Returns:
            创建的课程对象
        """
        # 检查是否已存在
        existing = self.db.get_lesson_by_date(lesson_date)
        if existing:
            raise ValueError(f"课程已存在: {lesson_date}")

        is_holiday, holiday_name = HolidayChecker.check_holiday_status(lesson_date)

        lesson = Lesson(
            date=lesson_date,
            time=lesson_time or self.default_time,
            status=LessonStatus.SCHEDULED,
            fee=fee or self.default_fee,
            fee_paid=False,
            is_holiday_conflict=is_holiday,
            notes=f"节假日冲突: {holiday_name}" if is_holiday and holiday_name else None,
        )

        return self.db.add_lesson(lesson)

    def cancel_lesson(self, lesson_date: dt.date) -> bool:
        """
        取消课程

        Args:
            lesson_date: 上课日期

        Returns:
            是否成功取消
        """
        return self.db.cancel_lesson_by_date(lesson_date)

    def reschedule_lesson(self, from_date: dt.date, to_date: dt.date,
                          to_time: Optional[dt.time] = None) -> Optional[Lesson]:
        """
        调课

        Args:
            from_date: 原日期
            to_date: 新日期
            to_time: 新时间，默认不变

        Returns:
            更新后的课程对象
        """
        existing = self.db.get_lesson_by_date(from_date)
        if not existing:
            return None

        # 检查目标日期是否已存在
        target_existing = self.db.get_lesson_by_date(to_date)
        if target_existing:
            raise ValueError(f"目标日期已存在课程: {to_date}")

        # 检查节假日冲突
        is_holiday, holiday_name = HolidayChecker.check_holiday_status(to_date)

        existing.date = to_date
        existing.time = to_time or existing.time
        existing.is_holiday_conflict = is_holiday
        if is_holiday and holiday_name:
            existing.notes = f"节假日冲突: {holiday_name}"
        else:
            existing.notes = None

        return self.db.update_lesson(existing)

    def confirm_attendance(self, lesson_date: dt.date) -> Optional[Lesson]:
        """
        确认已上课

        Args:
            lesson_date: 上课日期

        Returns:
            更新后的课程对象
        """
        existing = self.db.get_lesson_by_date(lesson_date)
        if not existing:
            return None

        existing.status = LessonStatus.ATTENDED
        return self.db.update_lesson(existing)

    def get_lessons(self, year: Optional[int] = None, month: Optional[int] = None) -> List[Lesson]:
        """
        获取课程列表

        Args:
            year: 年份，可选
            month: 月份，可选

        Returns:
            课程列表
        """
        if year and month:
            return self.db.get_lessons_by_month(year, month)
        return self.db.get_all_lessons()

    def get_last_lesson_date(self, year: int, month: int) -> Optional[dt.date]:
        """
        获取指定月份最后一个上课日

        Args:
            year: 年份
            month: 月份

        Returns:
            最后一个上课日，如果没有则返回 None
        """
        lessons = self.db.get_lessons_by_month(year, month)
        active_lessons = [
            l for l in lessons
            if l.status != LessonStatus.CANCELLED
        ]
        if not active_lessons:
            return None
        return max(l.date for l in active_lessons)

    def mark_fee_paid(self, lesson_date: dt.date, paid: bool = True) -> Optional[Lesson]:
        """
        标记课程已缴费

        Args:
            lesson_date: 上课日期
            paid: 是否已缴费

        Returns:
            更新后的课程对象
        """
        existing = self.db.get_lesson_by_date(lesson_date)
        if not existing:
            return None

        existing.fee_paid = paid
        return self.db.update_lesson(existing)
