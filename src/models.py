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
    total_lessons: int
    attended_lessons: int
    unpaid_lessons: int
    total_fee: int
    paid_amount: int
    balance: int
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
    db_path: str = "data/dizi.db"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
