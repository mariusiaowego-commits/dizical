import datetime as dt
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class LessonStatus(str, Enum):
    SCHEDULED = "scheduled"
    ATTENDED = "attended"
    CANCELLED = "cancelled"


class Lesson(BaseModel):
    id: Optional[int] = None
    date: dt.date
    time: dt.time = Field(default_factory=lambda: dt.time(17, 15))
    status: LessonStatus = LessonStatus.SCHEDULED
    fee: int = Field(default=600, ge=0)
    fee_paid: bool = False
    is_holiday_conflict: bool = False
    notes: Optional[str] = None
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None

    @field_validator('fee')
    @classmethod
    def fee_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Fee must be non-negative')
        return v


class Payment(BaseModel):
    id: Optional[int] = None
    payment_date: dt.date
    amount: int = Field(ge=0)
    lesson_ids: str = ""
    payment_method: str = "现金"
    notes: Optional[str] = None
    created_at: Optional[dt.datetime] = None


class MonthlyLessonPlan(BaseModel):
    year: int
    month: int
    lessons: List[Lesson]
    total_lessons: int
    holiday_conflicts: int
    total_fee: int


class PaymentStatus(BaseModel):
    month: dt.date
    # 课程统计
    total_lessons: int           # 当月已安排课程（含取消）
    attended_lessons: int        # 当月已上课
    remaining_scheduled: int     # 当月剩余待上课程（SCHEDULED，未取消）
    cancelled_lessons: int       # 当月已取消
    # 费用统计
    total_fee: int               # 当月应缴（attended × fee）
    estimated_fee: int           # 当月预计缴费（attended + remaining_scheduled，用于月末提醒）
    paid_amount: int             # 当月已缴费
    historical_cumulative_paid: int  # 历史累计已缴总额（截至当月初）
    balance: int                 # 待缴余额
    # 缴费明细（展示用）
    payment_breakdown: str        # 费用说明
    # 日期
    last_lesson_date: Optional[dt.date]
    payment_reminder_date: Optional[dt.date]


class PracticeCategory(BaseModel):
    id: Optional[int] = None
    name: str
    sort_order: int = 99
    created_at: Optional[dt.datetime] = None


class DailyPracticeLog(BaseModel):
    id: Optional[int] = None
    date: dt.date
    items: List[Dict] = Field(default_factory=list)
    total_minutes: int = 0
    log: Optional[str] = None  # 详细练习记录/进展
    created_at: Optional[dt.datetime] = None


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    reminder_list_name: str = "dizi"
    obsidian_path: str = "/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/"
    default_fee: int = 600
    default_time: str = "17:15"
    default_weekday: int = 5  # 0=Monday, 5=Saturday
    db_path: str = "/Users/mt16/dev/dizical/data/dizi.db"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
