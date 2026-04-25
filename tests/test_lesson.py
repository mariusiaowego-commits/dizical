import os
import tempfile
import shutil
from datetime import date, time
from unittest import TestCase
from src.models import Lesson, LessonStatus, Payment
from src.database import Database
from src.lesson_manager import LessonManager
from src.payment import PaymentManager
from src.holiday import HolidayChecker


class TestLesson(TestCase):
    """课程模型测试"""

    def test_lesson_creation(self):
        """测试课程创建"""
        lesson = Lesson(
            date=date(2026, 5, 3),
            time=time(17, 15),
            fee=600,
        )
        self.assertEqual(lesson.date, date(2026, 5, 3))
        self.assertEqual(lesson.status, LessonStatus.SCHEDULED)
        self.assertEqual(lesson.fee, 600)
        self.assertFalse(lesson.fee_paid)

    def test_lesson_status_enum(self):
        """测试状态枚举"""
        lesson = Lesson(date=date(2026, 5, 3))
        lesson.status = LessonStatus.ATTENDED
        self.assertEqual(lesson.status, LessonStatus.ATTENDED)

    def test_invalid_fee(self):
        """测试无效学费"""
        with self.assertRaises(ValueError):
            Lesson(date=date(2026, 5, 3), fee=-100)


class TestDatabase(TestCase):
    """数据库测试"""

    def setUp(self):
        """创建临时数据库"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Database(self.db_path)

    def tearDown(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir)

    def test_add_lesson(self):
        """测试添加课程"""
        lesson = Lesson(
            date=date(2026, 5, 3),
            time=time(17, 15),
            fee=600,
        )
        saved = self.db.add_lesson(lesson)
        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.date, date(2026, 5, 3))

    def test_get_lesson_by_date(self):
        """测试按日期查询课程"""
        lesson = Lesson(date=date(2026, 5, 3), fee=600)
        self.db.add_lesson(lesson)

        found = self.db.get_lesson_by_date(date(2026, 5, 3))
        self.assertIsNotNone(found)
        self.assertEqual(found.date, date(2026, 5, 3))

    def test_get_lessons_by_month(self):
        """测试按月查询课程"""
        for day in [3, 10, 17]:
            self.db.add_lesson(Lesson(date=date(2026, 5, day)))

        lessons = self.db.get_lessons_by_month(2026, 5)
        self.assertEqual(len(lessons), 3)

    def test_update_lesson(self):
        """测试更新课程"""
        lesson = self.db.add_lesson(Lesson(date=date(2026, 5, 3)))
        lesson.status = LessonStatus.ATTENDED
        lesson.fee_paid = True

        updated = self.db.update_lesson(lesson)
        self.assertEqual(updated.status, LessonStatus.ATTENDED)
        self.assertTrue(updated.fee_paid)

    def test_cancel_lesson(self):
        """测试取消课程"""
        self.db.add_lesson(Lesson(date=date(2026, 5, 3)))
        result = self.db.cancel_lesson_by_date(date(2026, 5, 3))
        self.assertTrue(result)

        lesson = self.db.get_lesson_by_date(date(2026, 5, 3))
        self.assertEqual(lesson.status, LessonStatus.CANCELLED)

    def test_add_payment(self):
        """测试添加缴费记录"""
        payment = Payment(
            payment_date=date(2026, 5, 31),
            amount=1800,
            lesson_ids="1,2,3",
        )
        saved = self.db.add_payment(payment)
        self.assertIsNotNone(saved.id)
        self.assertEqual(saved.amount, 1800)


class TestLessonManager(TestCase):
    """课程管理测试"""

    def setUp(self):
        """创建临时数据库"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Database(self.db_path)
        self.manager = LessonManager(self.db)

    def tearDown(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir)

    def test_get_saturdays(self):
        """测试获取某月所有周六"""
        # 2026年5月有3个周六（假设是5月2、9、16、23、30）
        saturdays = self.manager.get_saturdays(2026, 5)
        self.assertGreater(len(saturdays), 0)
        # 检查每个都是周六 (weekday 5)
        for d in saturdays:
            self.assertEqual(d.weekday(), 5)

    def test_generate_monthly_lessons(self):
        """测试生成月度课程"""
        plan = self.manager.generate_monthly_lessons(2026, 5)
        self.assertEqual(plan.year, 2026)
        self.assertEqual(plan.month, 5)
        self.assertGreater(plan.total_lessons, 0)
        self.assertGreater(plan.total_fee, 0)

    def test_add_duplicate_lesson(self):
        """测试添加重复课程"""
        self.manager.add_lesson(date(2026, 5, 3))
        with self.assertRaises(ValueError):
            self.manager.add_lesson(date(2026, 5, 3))

    def test_reschedule_lesson(self):
        """测试调课"""
        self.manager.add_lesson(date(2026, 5, 3))
        updated = self.manager.reschedule_lesson(date(2026, 5, 3), date(2026, 5, 10))
        self.assertIsNotNone(updated)
        self.assertEqual(updated.date, date(2026, 5, 10))

    def test_confirm_attendance(self):
        """测试确认上课"""
        self.manager.add_lesson(date(2026, 5, 3))
        updated = self.manager.confirm_attendance(date(2026, 5, 3))
        self.assertEqual(updated.status, LessonStatus.ATTENDED)

    def test_get_last_lesson_date(self):
        """测试获取最后上课日"""
        self.manager.generate_monthly_lessons(2026, 5)
        last_date = self.manager.get_last_lesson_date(2026, 5)
        self.assertIsNotNone(last_date)
        self.assertEqual(last_date.month, 5)


class TestPaymentManager(TestCase):
    """缴费管理测试"""

    def setUp(self):
        """创建临时数据库"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Database(self.db_path)
        self.lesson_manager = LessonManager(self.db)
        self.payment_manager = PaymentManager(self.db)

    def tearDown(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir)

    def test_monthly_payment_status(self):
        """测试月度缴费状态"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        status = self.payment_manager.get_monthly_payment_status(2026, 5)
        self.assertEqual(status.month, date(2026, 5, 1))
        self.assertGreater(status.total_lessons, 0)
        self.assertGreater(status.total_fee, 0)
        self.assertEqual(status.paid_amount, 0)

    def test_record_payment(self):
        """测试记录缴费"""
        payment = self.payment_manager.record_payment(1800, date(2026, 5, 31))
        self.assertIsNotNone(payment.id)
        self.assertEqual(payment.amount, 1800)
        self.assertEqual(payment.payment_method, "现金")

    def test_payment_balance(self):
        """测试余额计算"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        status_before = self.payment_manager.get_monthly_payment_status(2026, 5)

        self.payment_manager.record_payment(status_before.total_fee)
        status_after = self.payment_manager.get_monthly_payment_status(2026, 5)

        self.assertEqual(status_after.balance, 0)

    def test_payment_reminder_message(self):
        """测试提醒消息生成"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        message = self.payment_manager.get_reminder_message(2026, 5)
        self.assertIn("缴费提醒", message)
        self.assertIn("应缴总额", message)


class TestHolidayChecker(TestCase):
    """节假日检测测试"""

    def test_is_holiday(self):
        """测试节假日检测"""
        # 测试劳动节 - 2026年5月1日是周五
        may_day = date(2026, 5, 1)
        is_holiday = HolidayChecker.is_holiday(may_day)
        # 2026年5月1日应该是劳动节假期
        self.assertTrue(is_holiday)

    def test_is_workday(self):
        """测试工作日检测"""
        # 普通周三应该是工作日（5月7日周三，不在劳动节假期后）
        wednesday = date(2026, 5, 6)
        self.assertTrue(HolidayChecker.is_workday(wednesday))

    def test_get_holiday_name(self):
        """测试获取节假日名称"""
        may_day = date(2026, 5, 1)
        name = HolidayChecker.get_holiday_name(may_day)
        if HolidayChecker.is_holiday(may_day):
            self.assertIsNotNone(name)

    def test_month_holidays(self):
        """测试获取月度节假日"""
        holidays = HolidayChecker.get_month_holidays(2026, 5)
        self.assertIsInstance(holidays, dict)
