"""数据模型模块"""
from datetime import date, time, datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class LessonStatus(str, Enum):
    """课程状态"""
    SCHEDULED = "scheduled"
    ATTENDED = "attended"
    CANCELLED = "cancelled"


class Lesson(BaseModel):
    """课程数据模型"""
    id: Optional[int] = None
    date: date
    time: time = Field(default=time(17, 15))
    status: LessonStatus = LessonStatus.SCHEDULED
    fee: int = Field(default=600, ge=0)
    fee_paid: bool = False
    is_holiday_conflict: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('time', mode='before')
    @classmethod
    def parse_time(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%H:%M").time()
        return v

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d").date()
        return v


class Payment(BaseModel):
    """缴费数据模型"""
    id: Optional[int] = None
    payment_date: date
    amount: int = Field(ge=0)
    lesson_ids: str = ""  # 逗号分隔的课程ID
    payment_method: str = "现金"
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator('payment_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, "%Y-%m-%d").date()
        return v

    def get_lesson_ids_list(self) -> List[int]:
        """获取课程ID列表"""
        if not self.lesson_ids:
            return []
        return [int(id_str.strip()) for id_str in self.lesson_ids.split(",") if id_str.strip()]


class Setting(BaseModel):
    """配置数据模型"""
    key: str
    value: str
    updated_at: Optional[datetime] = None


class MonthlyLessonSummary(BaseModel):
    """月度课程摘要"""
    year: int
    month: int
    total_lessons: int
    attended_lessons: int
    cancelled_lessons: int
    scheduled_lessons: int
    total_fee: int
    paid_fee: int
    unpaid_fee: int
    last_lesson_date: Optional[date] = None
    payment_reminder_date: Optional[date] = None
