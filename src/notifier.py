"""
Telegram 通知模块
封装 python-telegram-bot，支持文本消息、Markdown 格式
"""

import os
import logging
from typing import Optional

try:
    from telegram import Bot
    from telegram.error import TelegramError
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    Bot = None
    TelegramError = Exception

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram 通知发送器"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        初始化通知器

        Args:
            bot_token: Telegram Bot Token，从环境变量或配置读取
            chat_id: 目标聊天 ID
        """
        if bot_token is None:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if chat_id is None:
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot: Optional[Bot] = None

        if self.bot_token and HAS_TELEGRAM:
            try:
                self.bot = Bot(token=self.bot_token)
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram bot: {e}")

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.bot_token and self.chat_id and self.bot is not None)

    def send(
        self,
        message: str,
        parse_mode: str = "Markdown",
        disable_notification: bool = False,
    ) -> bool:
        """
        发送消息

        Args:
            message: 消息内容
            parse_mode: 解析模式，Markdown 或 HTML
            disable_notification: 静音发送

        Returns:
            是否发送成功
        """
        if not self.is_configured():
            logger.warning("Telegram not configured, skipping notification")
            return False

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_notification=disable_notification,
            )
            logger.info(f"Telegram message sent successfully")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_lesson_reminder(self, lesson_date: str, lesson_time: str) -> bool:
        """发送上课提醒"""
        message = f"🎵 *竹笛课提醒*\n\n📅 日期: {lesson_date}\n⏰ 时间: {lesson_time}\n\n请确认是否上课？"
        return self.send(message)

    def send_payment_reminder(
        self,
        amount: int,
        last_lesson_date: str,
    ) -> bool:
        """发送缴费提醒"""
        message = f"💰 *缴费提醒*\n\n应缴金额: *{amount}元*\n最后上课日: {last_lesson_date}\n\n请在上课时准备好现金缴费。"
        return self.send(message)

    def send_monthly_schedule(self, schedule_text: str) -> bool:
        """发送月度课程计划"""
        message = f"📅 *本月课程计划*\n\n{schedule_text}"
        return self.send(message)

    def send_lesson_confirmed(self, lesson_date: str) -> bool:
        """确认课程"""
        message = f"✅ *课程已确认*\n\n📅 {lesson_date} 竹笛课"
        return self.send(message)

    def send_lesson_cancelled(self, lesson_date: str, reason: str = "") -> bool:
        """取消课程"""
        reason_text = f"\n原因: {reason}" if reason else ""
        message = f"❌ *课程已取消*\n\n📅 {lesson_date} 竹笛课{reason_text}"
        return self.send(message)


# 全局单例
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """获取全局通知器实例"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier
