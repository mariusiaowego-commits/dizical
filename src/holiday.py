import datetime as dt
from typing import Optional, Tuple
import chinese_calendar as cc

# 英文到中文的节假日名称映射
HOLIDAY_NAME_MAP = {
    "New Year's Day": "元旦",
    "Spring Festival": "春节",
    "Tomb-sweeping Day": "清明节",
    "Labour Day": "劳动节",
    "Dragon Boat Festival": "端午节",
    "National Day": "国庆节",
    "Mid-autumn Festival": "中秋节",
    "Anti-Fascist 70th Day": "反法西斯胜利70周年纪念日",
}


class HolidayChecker:
    """中国节假日检测工具"""

    @staticmethod
    def is_holiday(check_date: dt.date) -> bool:
        """
        检查指定日期是否是节假日

        Args:
            check_date: 要检查的日期

        Returns:
            True 如果是节假日，False 否则
        """
        try:
            return cc.is_holiday(check_date)
        except Exception:
            # 如果 chinese_calendar 出错（比如日期超出范围），默认返回 False
            return False

    @staticmethod
    def is_workday(check_date: dt.date) -> bool:
        """
        检查指定日期是否是工作日（包括调休的周末）

        Args:
            check_date: 要检查的日期

        Returns:
            True 如果是工作日，False 否则
        """
        try:
            return cc.is_workday(check_date)
        except Exception:
            # 如果出错，默认周一到周五是工作日
            return check_date.weekday() < 5

    @staticmethod
    def get_holiday_name(check_date: dt.date) -> Optional[str]:
        """
        获取节假日名称

        Args:
            check_date: 要检查的日期

        Returns:
            节假日名称（中文），如果不是节假日返回 None
        """
        try:
            if not cc.is_holiday(check_date):
                return None
            # 获取节假日详情 - 返回 tuple (is_holiday, holiday_name)
            holiday_detail = cc.get_holiday_detail(check_date)
            if holiday_detail and holiday_detail[1]:
                # 英文转中文
                return HOLIDAY_NAME_MAP.get(holiday_detail[1], holiday_detail[1])
            return None
        except Exception:
            return None

    @staticmethod
    def check_holiday_status(check_date: dt.date) -> Tuple[bool, Optional[str]]:
        """
        检查日期是否为节假日，并返回名称

        Args:
            check_date: 要检查的日期

        Returns:
            (是否为节假日, 节假日名称)
        """
        is_holiday = HolidayChecker.is_holiday(check_date)
        holiday_name = HolidayChecker.get_holiday_name(check_date) if is_holiday else None
        return is_holiday, holiday_name

    @staticmethod
    def get_holidays_in_range(start_date: dt.date, end_date: dt.date) -> dict:
        """
        获取指定日期范围内的所有节假日

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            字典: {日期: 节假日名称}
        """
        holidays = {}
        current = start_date
        while current <= end_date:
            is_holiday, name = HolidayChecker.check_holiday_status(current)
            if is_holiday and name:
                holidays[current] = name
            current = current + dt.timedelta(days=1)
        return holidays

    @staticmethod
    def get_month_holidays(year: int, month: int) -> dict:
        """
        获取指定月份的所有节假日

        Args:
            year: 年份
            month: 月份

        Returns:
            字典: {日期: 节假日名称}
        """
        from calendar import monthrange

        _, num_days = monthrange(year, month)
        start_date = dt.date(year, month, 1)
        end_date = dt.date(year, month, num_days)
        return HolidayChecker.get_holidays_in_range(start_date, end_date)
