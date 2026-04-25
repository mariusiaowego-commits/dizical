import os
import tempfile
import shutil
from datetime import date
from unittest import TestCase
from src.models import Payment
from src.database import Database
from src.lesson_manager import LessonManager
from src.payment import PaymentManager


class TestPaymentModel(TestCase):
    """缴费模型测试"""

    def test_payment_creation(self):
        """测试缴费记录创建"""
        payment = Payment(
            payment_date=date(2026, 5, 31),
            amount=1800,
            lesson_ids="1,2,3",
        )
        self.assertEqual(payment.amount, 1800)
        self.assertEqual(payment.payment_method, "现金")
        self.assertEqual(payment.lesson_ids, "1,2,3")


class TestPaymentDatabase(TestCase):
    """缴费数据库操作测试"""

    def setUp(self):
        """创建临时数据库"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = Database(self.db_path)

    def tearDown(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir)

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

    def test_get_payments_by_month(self):
        """测试按月查询缴费记录"""
        for day, amount in [(10, 600), (20, 600), (31, 600)]:
            self.db.add_payment(Payment(
                payment_date=date(2026, 5, day),
                amount=amount,
            ))

        payments = self.db.get_payments_by_month(2026, 5)
        self.assertEqual(len(payments), 3)
        self.assertEqual(sum(p.amount for p in payments), 1800)

    def test_get_all_payments(self):
        """测试获取所有缴费记录"""
        for month in [4, 5, 6]:
            self.db.add_payment(Payment(
                payment_date=date(2026, month, 15),
                amount=600,
            ))

        payments = self.db.get_all_payments()
        self.assertEqual(len(payments), 3)


class TestPaymentManagerAdvanced(TestCase):
    """缴费管理高级功能测试"""

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

    def test_payment_status_with_partial_payment(self):
        """测试部分缴费后的状态"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        status = self.payment_manager.get_monthly_payment_status(2026, 5)

        # 部分缴费
        partial_amount = status.total_fee // 2
        self.payment_manager.record_payment(partial_amount)

        new_status = self.payment_manager.get_monthly_payment_status(2026, 5)
        self.assertEqual(new_status.paid_amount, partial_amount)
        self.assertEqual(new_status.balance, status.total_fee - partial_amount)

    def test_payment_history(self):
        """测试缴费历史查询"""
        self.payment_manager.record_payment(600, date(2026, 5, 10))
        self.payment_manager.record_payment(600, date(2026, 5, 20))
        self.payment_manager.record_payment(600, date(2026, 5, 31))

        history = self.payment_manager.get_payment_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(sum(p.amount for p in history), 1800)

    def test_get_unpaid_lessons(self):
        """测试获取未缴费课程"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        unpaid = self.payment_manager.get_unpaid_lessons(2026, 5)
        self.assertGreater(len(unpaid), 0)

    def test_should_send_reminder(self):
        """测试是否应该发送提醒"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        status = self.payment_manager.get_monthly_payment_status(2026, 5)

        if status.payment_reminder_date:
            # 在提醒日应该发送提醒
            self.assertTrue(self.payment_manager.should_send_reminder(status.payment_reminder_date))

    def test_should_not_send_reminder_when_paid(self):
        """测试缴清后不应发送提醒"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        status = self.payment_manager.get_monthly_payment_status(2026, 5)

        # 缴清所有费用
        self.payment_manager.record_payment(status.total_fee)

        if status.payment_reminder_date:
            self.assertFalse(self.payment_manager.should_send_reminder(status.payment_reminder_date))

    def test_reminder_message_content(self):
        """测试提醒消息内容"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        message = self.payment_manager.get_reminder_message(2026, 5)

        self.assertIn("缴费提醒", message)
        self.assertIn("本月课程", message)
        self.assertIn("已上课", message)
        self.assertIn("应缴总额", message)
        self.assertIn("已缴金额", message)

    def test_reminder_message_when_paid(self):
        """测试已缴费时的提醒消息"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        status = self.payment_manager.get_monthly_payment_status(2026, 5)
        self.payment_manager.record_payment(status.total_fee)

        message = self.payment_manager.get_reminder_message(2026, 5)
        self.assertIn("已缴清", message)

    def test_mark_lessons_paid_with_lesson_ids(self):
        """测试通过lesson_ids标记课程已缴费"""
        self.lesson_manager.generate_monthly_lessons(2026, 5)
        lessons = self.db.get_lessons_by_month(2026, 5)
        lesson_ids = ",".join(str(l.id) for l in lessons[:3])

        # 记录缴费并指定课程ID
        self.payment_manager.record_payment(1800, lesson_ids=lesson_ids)

        # 检查课程是否被标记为已缴费
        for l in lessons[:3]:
            updated = self.db.get_lesson(l.id)
            self.assertTrue(updated.fee_paid)
