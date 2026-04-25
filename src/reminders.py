"""
Apple Reminders 同步模块
使用 remindctl CLI 进行双向同步和指令解析
"""
import json
import os
import re
from datetime import date, datetime
from typing import Optional, Tuple, List
from subprocess import run, PIPE, CalledProcessError

from dotenv import load_dotenv

load_dotenv()


class ReminderCommand:
    """解析后的 Reminder 指令"""

    def __init__(self, action: str, **kwargs):
        self.action = action  # add, cancel, reschedule, payment, none
        self.date: Optional[date] = kwargs.get('date')
        self.new_date: Optional[date] = kwargs.get('new_date')
        self.amount: Optional[int] = kwargs.get('amount')
        self.notes: str = kwargs.get('notes', '')

    def __repr__(self):
        return f"ReminderCommand({self.action}, {self.__dict__})"


class RemindersSync:
    """Apple Reminders 同步器"""

    def __init__(self, list_name: Optional[str] = None):
        self.list_name = list_name or os.getenv("REMINDER_LIST_NAME", "dizi")

    @property
    def is_available(self) -> bool:
        """检查 remindctl 是否可用"""
        try:
            result = run(["remindctl", "status"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, CalledProcessError, TimeoutError):
            return False

    def _run_command(self, args: List[str]) -> str:
        """运行 remindctl 命令"""
        result = run(
            ["remindctl"] + args,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            raise RuntimeError(f"remindctl 失败: {result.stderr}")
        return result.stdout

    def list_exists(self) -> bool:
        """检查提醒列表是否存在"""
        try:
            output = self._run_command(["list"])
            return self.list_name in output
        except RuntimeError:
            return False

    def create_list(self) -> bool:
        """创建提醒列表"""
        try:
            self._run_command(["list", "add", self.list_name])
            return True
        except RuntimeError:
            return False

    def get_reminders(self, include_completed: bool = False) -> List[dict]:
        """
        获取列表中的所有提醒

        Returns:
            [{'id': '...', 'title': '...', 'date': '...', 'completed': bool}, ...]
        """
        args = ["list", self.list_name, "--json"]
        if include_completed:
            args.append("--completed")

        output = self._run_command(args)
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return []

    def add_reminder(self, title: str, due_date: Optional[date] = None,
                      notes: Optional[str] = None) -> str:
        """
        添加提醒

        Returns:
            提醒 ID
        """
        args = ["add", "--list", self.list_name, title]

        if due_date:
            args.extend(["--date", due_date.strftime("%Y-%m-%d")])
        if notes:
            args.extend(["--notes", notes])

        output = self._run_command(args)
        # 输出通常包含新创建的提醒信息，解析ID
        return output.strip()

    def complete_reminder(self, reminder_id: str):
        """标记提醒为已完成"""
        self._run_command(["complete", reminder_id])

    def delete_reminder(self, reminder_id: str):
        """删除提醒"""
        self._run_command(["delete", reminder_id])

    @staticmethod
    def parse_date(text: str) -> Optional[date]:
        """
        从文本中解析日期，支持以下格式：
        - YYYY-MM-DD
        - MM-DD
        - MM月DD日
        - 明天 / 后天
        - 下周一 / 下周六
        """
        today = date.today()

        # 完整日期 YYYY-MM-DD
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', text)
        if match:
            try:
                return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                pass

        # 月份日期 MM-DD 或 MM/DD
        match = re.search(r'(\d{1,2})[-/](\d{1,2})', text)
        if match:
            try:
                return date(today.year, int(match.group(1)), int(match.group(2)))
            except ValueError:
                pass

        # 中文日期: X月X日
        match = re.search(r'(\d{1,2})月(\d{1,2})日', text)
        if match:
            try:
                return date(today.year, int(match.group(1)), int(match.group(2)))
            except ValueError:
                pass

        # 相对日期
        if '明天' in text:
            return today.replace(day=today.day + 1) if today.day < 28 else (
                today.replace(month=today.month + 1, day=1) if today.month < 12 else today.replace(year=today.year + 1, month=1, day=1)
            )
        if '后天' in text:
            return today.replace(day=today.day + 2) if today.day < 27 else (
                today.replace(month=today.month + 1, day=2) if today.month < 12 else today.replace(year=today.year + 1, month=1, day=2)
            )

        return None

    @staticmethod
    def parse_amount(text: str) -> Optional[int]:
        """从文本中解析金额"""
        match = re.search(r'(\d+)\s*(?:元|块|钱|缴费)', text)
        if match:
            return int(match.group(1))

        # 纯数字
        match = re.search(r'(\d{3,})', text)
        if match:
            return int(match.group(1))

        return None

    def parse_command(self, title: str, notes: str = "") -> ReminderCommand:
        """
        解析提醒标题中的指令

        支持的指令:
        - 取消 + 日期 → 取消课程
        - 请假 + 日期 → 取消课程
        - 加课 + 日期 → 添加课程
        - 缴费 + 金额 → 记录缴费
        - 改 + 日期 + 到 + 日期 → 调课
        """
        full_text = f"{title} {notes}"

        # 缴费
        if any(keyword in full_text for keyword in ['缴费', '交钱', '已交']):
            amount = self.parse_amount(full_text)
            return ReminderCommand('payment', amount=amount, notes=notes)

        # 调课: 改 X到Y
        if '改' in full_text and ('到' in full_text or '为' in full_text):
            dates = []
            text_to_parse = full_text.replace('到', ' ').replace('为', ' ')
            for _ in range(2):
                d = self.parse_date(text_to_parse)
                if d:
                    dates.append(d)
                    text_to_parse = text_to_parse.replace(d.strftime("%m-%d"), '')
                    text_to_parse = text_to_parse.replace(d.strftime("%m月%d日"), '')
            if len(dates) >= 2:
                return ReminderCommand('reschedule', date=dates[0], new_date=dates[1], notes=notes)

        # 取消/请假
        if any(keyword in full_text for keyword in ['取消', '请假', '不上']):
            d = self.parse_date(full_text)
            if d:
                return ReminderCommand('cancel', date=d, notes=notes)

        # 加课
        if any(keyword in full_text for keyword in ['加课', '加一节']):
            d = self.parse_date(full_text)
            if d:
                return ReminderCommand('add', date=d, notes=notes)

        return ReminderCommand('none', notes=notes)

    def check_new_commands(self) -> List[ReminderCommand]:
        """检查新的指令（未完成的提醒）"""
        reminders = self.get_reminders(include_completed=False)
        commands = []

        for reminder in reminders:
            if reminder.get('completed', False):
                continue

            title = reminder.get('title', '')
            notes = reminder.get('notes', '') or ''

            cmd = self.parse_command(title, notes)
            if cmd.action != 'none':
                cmd.reminder_id = reminder.get('id')
                commands.append(cmd)

        return commands
