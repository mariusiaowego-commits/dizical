"""Pydantic schemas for kid_app API request validation.

PR-A-1: 替代手写 body.get() 类型转换, 422 错误统一格式.

覆盖端点 (本次):
- POST /api/log  (web 端, dizical-minip 走 /config/api/records 不在此)
- POST /config/api/records  (config.py:550, 后续 task 接入)

不覆盖:
- GET 端点 (query params, 本次不重构)
- 内部 helper (badge_workflow 已有 Pydantic)
"""
from __future__ import annotations

import datetime as dt
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─── Constants ───────────────────────────────────────────────────────────

ALLOWED_TEMPO_NOTES = ("♪", "♩", "♬")
BPM_MIN = 40
BPM_MAX = 150
CONTENT_MAX_LEN = 200
CONTENT_MIN_LEN = 1
ALLOWED_CONTENT_SOURCES = ("manual", "legacy", "backfill")


# ─── Sub-models ──────────────────────────────────────────────────────────

class SessionDetail(BaseModel):
    """嵌套 alias: { tempo_note, tempo_bpm, content, content_source }.

    7-28 引入, 7-29 实际 Web 快速补录还嵌套发, 后端用本 schema 合并到顶层.
    """

    model_config = ConfigDict(extra="forbid")

    tempo_note: str = Field(..., description="音符 ♪/♩/♬")
    tempo_bpm: int = Field(..., ge=BPM_MIN, le=BPM_MAX)
    content: str = Field(..., min_length=CONTENT_MIN_LEN, max_length=CONTENT_MAX_LEN)
    content_source: str = "manual"

    @field_validator("tempo_note")
    @classmethod
    def _check_tempo_note(cls, v: str) -> str:
        if v not in ALLOWED_TEMPO_NOTES:
            raise ValueError(f"tempo_note 必须是 {ALLOWED_TEMPO_NOTES} 之一, 收到 {v!r}")
        return v

    @field_validator("content_source")
    @classmethod
    def _check_content_source(cls, v: str) -> str:
        if v not in ALLOWED_CONTENT_SOURCES:
            raise ValueError(f"content_source 必须是 {ALLOWED_CONTENT_SOURCES} 之一, 收到 {v!r}")
        return v


class BehaviorLogEntry(BaseModel):
    """deprecated: session 事务已自动写 behavior_log, 旧前端可能仍发."""

    model_config = ConfigDict(extra="ignore")

    enter_time: str = ""
    item: str = ""
    minutes: int = 0


# ─── Main request schema ────────────────────────────────────────────────

class PracticeLogRequest(BaseModel):
    """POST /api/log body schema.

    双路径共存:
    - has_session_detail() == True  → 走 save_practice_session_and_daily_summary
    - has_session_detail() == False → 走 save_daily_practice 兼容

    session_detail 嵌套 alias 会被合并到顶层 (兼容 Web 快速补录).
    """

    model_config = ConfigDict(extra="ignore")  # 旧前端可能带未知字段, 忽略

    # ── 必填 ──
    date: dt.date
    item: str = Field(..., min_length=1)
    item_id: int = Field(..., ge=1)
    minutes: int = Field(..., ge=1)

    # ── 可选 ──
    is_extra: bool = False
    log: str = ""
    practice_at: Optional[str] = None  # CST ISO 'YYYY-MM-DD HH:MM:SS[.fff]'
    behavior_log: List[BehaviorLogEntry] = Field(default_factory=list)

    # ── Session 路径字段 (三个全在 → 走 session 写入) ──
    tempo_note: Optional[str] = None
    tempo_bpm: Optional[int] = None
    content: Optional[str] = None
    content_source: str = "manual"

    # ── 嵌套 alias (兼容性, 会被 model_validator 合并到顶层) ──
    session_detail: Optional[SessionDetail] = None

    @field_validator("tempo_note")
    @classmethod
    def _check_tempo_note(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_TEMPO_NOTES:
            raise ValueError(f"tempo_note 必须是 {ALLOWED_TEMPO_NOTES} 之一, 收到 {v!r}")
        return v

    @field_validator("tempo_bpm")
    @classmethod
    def _check_tempo_bpm(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (BPM_MIN <= v <= BPM_MAX):
            raise ValueError(f"tempo_bpm 必须在 {BPM_MIN}-{BPM_MAX} 之间, 收到 {v}")
        return v

    @field_validator("content")
    @classmethod
    def _check_content(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("content 不能为空字符串")
        if len(v) > CONTENT_MAX_LEN:
            raise ValueError(f"content 长度不能超过 {CONTENT_MAX_LEN} 字符, 收到 {len(v)}")
        return v

    @field_validator("content_source")
    @classmethod
    def _check_content_source(cls, v: str) -> str:
        if v not in ALLOWED_CONTENT_SOURCES:
            raise ValueError(f"content_source 必须是 {ALLOWED_CONTENT_SOURCES} 之一, 收到 {v!r}")
        return v

    @model_validator(mode="after")
    def _merge_session_detail(self) -> "PracticeLogRequest":
        """session_detail 嵌套 alias 合并到顶层 (仅当顶层字段为 None 时)."""
        if self.session_detail is not None:
            sd = self.session_detail
            # 顶层字段未填才用 session_detail 的值
            if self.tempo_note is None:
                self.tempo_note = sd.tempo_note
            if self.tempo_bpm is None:
                self.tempo_bpm = sd.tempo_bpm
            if self.content is None:
                self.content = sd.content
            if self.content_source == "manual" and sd.content_source != "manual":
                self.content_source = sd.content_source
        return self

    def has_session_detail(self) -> bool:
        """3 个核心字段全部存在 → 走 session 路径.

        路由层用这个判断走 save_practice_session_and_daily_summary
        还是 save_daily_practice (兼容).
        """
        return self.tempo_note is not None and self.tempo_bpm is not None and self.content is not None
