"""
Apple Reminders 同步模块
使用 remindctl CLI 监控 dizi 列表，解析自然语言指令
"""

import os
import re
import logging
import subprocess
import datetime as dt
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class RemindersManager:
    """Apple Reminders 管理器"""

    def __init__(self, list_name: str = "dizi"):
        """
        初始化

        Args:
            list_name: 监控的 Reminder 列表名，默认 'dizi'
        """
        self.list_name = list_name
        self._available = self._check_remindctl()

    @property
    def is_available(self) -> bool:
        """remindctl 是否可用"""
        return self._available

    def check_new_commands(self) -> List:
        """获取待执行指令"""
        return self.get_pending_items()

    def list_exists(self) -> bool:
        """检查 Reminders 列表是否存在"""
        try:
            result = subprocess.run(
                ["remindctl", "list"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False
            return any(line.strip().startswith(self.list_name) for line in result.stdout.splitlines())
        except Exception:
            return False

    def create_list(self) -> bool:
        """创建 Reminders 列表（实际上 remindctl 不需要预创建，直接用就行）"""
        return True

    def _check_remindctl(self) -> bool:
        """检查 remindctl 是否可用"""
        try:
            result = subprocess.run(
                ["which", "remindctl"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.warning("remindctl not found, reminders sync disabled")
                return False
            return True
        except Exception:
            logger.warning("remindctl not available")
            return False

    def get_pending_items(self) -> List[dict]:
        """
        获取待处理的 reminder 项

        Returns:
            [{'id': str, 'title': str, 'notes': str, 'due': str}, ...]
        """
        if not self._check_remindctl():
            return []

        try:
            result = subprocess.run(
                ["remindctl", "list", self.list_name, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []

            import json
            items = json.loads(result.stdout)
            return items
        except Exception as e:
            logger.error(f"Failed to get reminders: {e}")
            return []

    def complete_item(self, item_id: str) -> bool:
        """标记 reminder 为已完成"""
        try:
            result = subprocess.run(
                ["remindctl", "complete", item_id],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to complete reminder: {e}")
            return False

    # CLI 兼容别名
    complete_reminder = complete_item

    def parse_instruction(self, text: str) -> Tuple[Optional[str], dict]:
        """
        解析自然语言指令

        Args:
            text: reminder 文本内容

        Returns:
            (action, params) - action 为 'cancel'/'add'/'payment'/'reschedule'/'confirm'，params 为解析出的参数
        """
        text = text.strip()

        # 取消/请假
        if "取消" in text or "请假" in text:
            date = self._extract_date(text)
            if date:
                return "cancel", {"date": date}
            return "cancel", {}

        # 加课
        if "加课" in text or "新增" in text:
            date = self._extract_date(text)
            if date:
                return "add", {"date": date}
            return "add", {}

        # 缴费
        if "缴费" in text or "交钱" in text:
            amount = self._extract_amount(text)
            return "payment", {"amount": amount}

        # 确认上课
        if "确认" in text or "到课" in text or "上课" in text:
            date = self._extract_date(text)
            return "confirm", {"date": date}

        # 改时间/调课
        match = re.search(r"改.*?(\d{1,2})[月/-](\d{1,2})?.?到(\d{1,2})[月/-](\d{1,2})", text)
        if match:
            from_date = self._parse_month_day(match.group(1), match.group(2))
            to_date = self._parse_month_day(match.group(3), match.group(4))
            return "reschedule", {"from": from_date, "to": to_date}

        return None, {}

    def _extract_date(self, text: str) -> Optional[str]:
        """提取日期"""
        year = dt.date.today().year

        # 格式: YYYY-MM-DD, YYYY/MM/DD
        match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

        # 格式: MM-DD, MM/DD
        match = re.search(r"(\d{1,2})[-/](\d{1,2})", text)
        if match:
            return f"{year}-{int(match.group(1)):02d}-{int(match.group(2)):02d}"

        # 相对日期: 今天, 明天, 后天
        if "今天" in text:
            return str(dt.date.today())
        if "明天" in text:
            return str(dt.date.today() + dt.timedelta(days=1))
        if "后天" in text:
            return str(dt.date.today() + dt.timedelta(days=2))

        return None

    def _extract_amount(self, text: str) -> Optional[int]:
        """提取金额"""
        match = re.search(r"(\d+)", text)
        if match:
            return int(match.group(1))
        return None

    def _parse_month_day(self, month: str, day: Optional[str]) -> str:
        """解析月日"""
        year = dt.date.today().year
        m = int(month)
        if day:
            d = int(day)
        else:
            # 没有日期，默认该月1日
            d = 1
        return f"{year}-{m:02d}-{d:02d}"

    def process_pending(self, lesson_manager=None, payment_manager=None) -> Tuple[int, int]:
        """
        处理所有待处理的 reminder

        Args:
            lesson_manager: LessonManager 实例
            payment_manager: PaymentManager 实例

        Returns:
            (成功数, 失败数)
        """
        items = self.get_pending_items()
        success = 0
        failed = 0

        for item in items:
            action, params = self.parse_instruction(item.get("title", ""))

            if action is None:
                continue

            try:
                if action == "cancel" and lesson_manager:
                    date = params.get("date")
                    if date:
                        lesson_manager.cancel_lesson(date)
                        self.complete_item(item["id"])
                        success += 1
                        logger.info(f"Cancelled lesson on {date}")

                elif action == "add" and lesson_manager:
                    date = params.get("date")
                    if date:
                        lesson_manager.add_lesson(date)
                        self.complete_item(item["id"])
                        success += 1
                        logger.info(f"Added lesson on {date}")

                elif action == "payment" and payment_manager:
                    amount = params.get("amount")
                    if amount:
                        payment_manager.record_payment(amount)
                        self.complete_item(item["id"])
                        success += 1
                        logger.info(f"Recorded payment {amount}")

                elif action == "confirm" and lesson_manager:
                    date = params.get("date")
                    if date:
                        lesson_manager.confirm_attendance(date)
                        self.complete_item(item["id"])
                        success += 1
                        logger.info(f"Confirmed lesson on {date}")

                elif action == "reschedule" and lesson_manager:
                    from_date = params.get("from")
                    to_date = params.get("to")
                    if from_date and to_date:
                        lesson_manager.reschedule_lesson(from_date, to_date)
                        self.complete_item(item["id"])
                        success += 1
                        logger.info(f"Rescheduled lesson from {from_date} to {to_date}")

            except Exception as e:
                logger.error(f"Failed to process action {action}: {e}")
                failed += 1

        return success, failed


# 全局单例
_manager: Optional[RemindersManager] = None


def get_reminders_manager() -> RemindersManager:
    """获取全局 reminders 管理器实例"""
    global _manager
    if _manager is None:
        list_name = os.getenv("REMINDER_LIST_NAME", "dizi")
        _manager = RemindersManager(list_name=list_name)
    return _manager
