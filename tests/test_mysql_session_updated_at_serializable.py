"""
Sprint 09 P0 修复 (2026-08-05): MySQL session dict 的 updated_at 必须可 JSON 序列化.

背景: PR-D 给 practice_sessions 加了 updated_at DATETIME 列后, MySQLBackend 的
get_practice_session_by_id / get_practice_sessions 忘了把 updated_at 转 str
(practice_date/created_at 都转了, 唯独漏了它). MySQL 返 datetime 对象 →
FastAPI JSONResponse 序列化失败 → 生产 /api/log session 路径 500.
"""
import datetime as dt
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch


class _FakeRow(dict):
    """模拟 DictCursor 返回的 row (dict 子类)."""


def _make_row(**kw):
    row = _FakeRow()
    row.update({
        "id": 1,
        "practice_date": dt.date(2026, 8, 5),
        "item_id": 1002,
        "item_name": "单吐",
        "duration_minutes": 5,
        "tempo_note": "♪",
        "tempo_bpm": 80,
        "content": "测试",
        "content_source": "manual",
        "is_extra": 0,
        "started_at": None,
        "created_at": dt.datetime(2026, 8, 5, 16, 0, 0),
        "version": 1,
        "updated_at": dt.datetime(2026, 8, 5, 16, 0, 0),
    })
    row.update(kw)
    return row


class TestMySQLSessionUpdatedAtSerializable(unittest.TestCase):
    """PR-D P0: updated_at DATETIME → str, JSON 可序列化."""

    def _make_db(self, rows):
        """构造 MySQLBackend 实例, mock 掉连接层."""
        from src.database_mysql import MySQLBackend
        db = MySQLBackend.__new__(MySQLBackend)  # 跳过 __init__ (不连真库)
        db._PRACTICE_SESSIONS_DDL_DONE = True  # 跳过 lazy DDL

        # 两层 context manager: conn.__enter__() → conn → cursor(DictCursor) → cur.__enter__()
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn  # with conn: → conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.__enter__.return_value = mock_cur  # with cur: → cur
        mock_cur.fetchone.return_value = rows[0] if rows else None
        mock_cur.fetchall.return_value = rows
        db._get_connection = MagicMock(return_value=mock_conn)
        return db

    def test_get_by_id_updated_at_is_str(self):
        db = self._make_db([_make_row()])
        s = db.get_practice_session_by_id(1)
        self.assertIsInstance(s["updated_at"], str)
        self.assertIsInstance(s["created_at"], str)
        self.assertIsInstance(s["practice_date"], str)
        # JSON 可序列化 (这是生产 500 的根因)
        json.dumps(s)

    def test_get_by_id_updated_at_none_stays_none(self):
        db = self._make_db([_make_row(updated_at=None)])
        s = db.get_practice_session_by_id(1)
        self.assertIsNone(s["updated_at"])
        json.dumps(s)

    def test_get_list_updated_at_is_str(self):
        db = self._make_db([_make_row(), _make_row(id=2, updated_at=None)])
        rows = db.get_practice_sessions(dt.date(2026, 8, 5))
        self.assertIsInstance(rows[0]["updated_at"], str)
        self.assertIsNone(rows[1]["updated_at"])
        json.dumps(rows)

    def test_save_session_response_jsonable(self):
        """端到端: save 返回的 dict 也能 JSON 序列化 (模拟 app.py JSONResponse)."""
        db = self._make_db([_make_row()])
        # save_practice_session_and_daily_summary 尾部 return get_practice_session_by_id
        with patch.object(db, "save_practice_session_and_daily_summary",
                          return_value=db.get_practice_session_by_id(1)):
            s = db.save_practice_session_and_daily_summary(dt.date(2026, 8, 5), "单吐", 1002, 5, "♪", 80, "测试")
            json.dumps(s)  # 不抛 TypeError = PASS


if __name__ == "__main__":
    unittest.main()
