"""Abstract base class for all database backends (SQLite / MySQL).

独立模块避免 src.database <-> src.database_mysql 循环导入.

PR-A-2: 强制所有 backend 实现 4 个 session 方法, 防止漏方法 (7-28 教训).
"""
from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseBackend(ABC):
    """所有后端 backend 的抽象基类 (SQLite / MySQL).

    新增 backend 必须实现 4 个 session 方法, 否则在 import 阶段就会失败
    (而不是运行时调到一个 AttributeError).
    """

    @abstractmethod
    def create_practice_session(
        self,
        practice_date: dt.date,
        item_id: int,
        item_name: str,
        duration_minutes: int,
        tempo_note: str = "♪",
        tempo_bpm: int = 80,
        content: str = "",
        content_source: str = "manual",
        is_extra: bool = False,
        started_at: Optional[str] = None,
    ) -> Dict:
        """插入 1 条 practice_session, 返回 dict."""

    @abstractmethod
    def update_practice_session(
        self,
        session_id: int,
        tempo_note: Optional[str] = None,
        tempo_bpm: Optional[int] = None,
        content: Optional[str] = None,
        duration_minutes: Optional[int] = None,
    ) -> Optional[Dict]:
        """更新 session, duration 变化时重算 daily."""

    @abstractmethod
    def delete_practice_session(self, session_id: int) -> None:
        """删单条 session + 重算 daily + 写 audit."""

    @abstractmethod
    def save_practice_session_and_daily_summary(
        self,
        practice_date: dt.date,
        item: str,
        item_id: int,
        minutes: int,
        tempo_note: str,
        tempo_bpm: int,
        content: str,
        content_source: str = "manual",
        practice_at: Optional[str] = None,
        is_extra: bool = False,
    ) -> Dict:
        """事务: 写 session + 同步 daily + 写 audit + 更新冗余列."""
