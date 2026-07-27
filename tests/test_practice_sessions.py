"""
Tests for V3 (2026-07-27) feat/practice-session-detail:
每次计时细分内容 (tempo_note/tempo_bpm/content).

测试范围 (12 case):
1. create_practice_session 基本字段保存
2. 同科目两次 5min 计时 → 2 条 session (不合并)
3. tempo_note 非 ♪/♩ 拒
4. tempo_bpm 越界 (39/151) 拒
5. duration_minutes <= 0 拒
6. content 长度 > 200 拒
7. save_practice_session_and_daily_summary 同步 daily 汇总
8. delete_practice_session 删除最后一条 → total=0
9. delete_practice_session 删除中间一条 → 不影响其他
10. legacy 迁移幂等
11. 冗余列 (last_tempo_note/bpm) 正确更新
12. get_daily_practice 返回 practice_at 字段 (2026-07-27 bug fix)
"""
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# 注入测试 item (conftest 已建表, 跑 _ensure_badge_tables 时 db._get_connection() 触发 _init_tables 自动建 practice_items 等基础表)
from src.database import db


@pytest.fixture
def test_item():
    """准备一个测试用 practice_item, 返回 (item_id, name)"""
    # 用 db 单例 (conftest 已 monkeypatch 到 tmp db)
    # 清掉可能残留的测试 item
    db._get_connection().execute("DELETE FROM practice_items WHERE name = 'test_subject_zzz'")
    db._get_connection().commit()
    # 插入一个
    db._get_connection().execute(
        "INSERT INTO practice_items (name, is_active) VALUES ('test_subject_zzz', 1)"
    )
    db._get_connection().commit()
    item_id_row = db._get_connection().execute(
        "SELECT item_id FROM practice_items WHERE name = 'test_subject_zzz'"
    ).fetchone()
    assert item_id_row is not None, "test_item fixture: INSERT 后应能查到 item_id"
    item_id = item_id_row["item_id"]
    yield (item_id, "test_subject_zzz")
    # 清理
    conn = db._get_connection()
    conn.execute("DELETE FROM practice_sessions WHERE item_id = ?", (item_id,))
    conn.execute("DELETE FROM practice_items WHERE item_id = ?", (item_id,))
    conn.commit()


@pytest.fixture
def test_date():
    """固定测试日期, 自动清理"""
    d = dt.date(2024, 7, 27)
    conn = db._get_connection()
    conn.execute("DELETE FROM daily_practices WHERE date = ?", (d.isoformat(),))
    conn.execute("DELETE FROM practice_audit_log WHERE practice_date = ?", (d.isoformat(),))
    conn.execute("DELETE FROM practice_sessions WHERE practice_date = ?", (d.isoformat(),))
    conn.commit()
    yield d
    conn = db._get_connection()
    conn.execute("DELETE FROM daily_practices WHERE date = ?", (d.isoformat(),))
    conn.execute("DELETE FROM practice_audit_log WHERE practice_date = ?", (d.isoformat(),))
    conn.execute("DELETE FROM practice_sessions WHERE practice_date = ?", (d.isoformat(),))
    conn.commit()


class TestCreateSession:
    def test_basic_fields_saved(self, test_item, test_date):
        """Case 1: create_practice_session 基本字段保存 + 读取一致"""
        item_id, item_name = test_item
        s = db.create_practice_session(
            test_date, item_id, item_name, 5,
            tempo_note="♪", tempo_bpm=80, content="第一分句连吐",
        )
        assert s["id"] > 0
        assert s["practice_date"] == test_date.isoformat()
        assert s["item_id"] == item_id
        assert s["item_name"] == item_name
        assert s["duration_minutes"] == 5
        assert s["tempo_note"] == "♪"
        assert s["tempo_bpm"] == 80
        assert s["content"] == "第一分句连吐"
        assert s["content_source"] == "manual"
        assert s["is_extra"] == 0

    def test_two_sessions_same_item_not_merged(self, test_item, test_date):
        """Case 2: 同科目两次 5min 计时生成 2 条 session (不合并)"""
        item_id, item_name = test_item
        s1 = db.create_practice_session(
            test_date, item_id, item_name, 5,
            tempo_note="♪", tempo_bpm=80, content="第一分句",
        )
        s2 = db.create_practice_session(
            test_date, item_id, item_name, 3,
            tempo_note="♪", tempo_bpm=80, content="第二分句",
        )
        assert s1["id"] != s2["id"]
        sessions = db.get_practice_sessions(test_date, item_id=item_id)
        assert len(sessions) == 2
        assert {s["duration_minutes"] for s in sessions} == {5, 3}
        # 内容区分
        assert {s["content"] for s in sessions} == {"第一分句", "第二分句"}


class TestSessionValidation:
    def test_tempo_note_whitelist(self, test_item, test_date):
        """Case 3: tempo_note 非 ♪/♩ 拒"""
        item_id, item_name = test_item
        with pytest.raises(ValueError, match="tempo_note 必须是"):
            db.create_practice_session(
                test_date, item_id, item_name, 5,
                tempo_note="X", tempo_bpm=80, content="test",
            )

    def test_tempo_bpm_bounds(self, test_item, test_date):
        """Case 4: tempo_bpm 越界 39 / 151 都拒"""
        item_id, item_name = test_item
        with pytest.raises(ValueError, match="tempo_bpm 必须在"):
            db.create_practice_session(
                test_date, item_id, item_name, 5,
                tempo_note="♪", tempo_bpm=39, content="test",
            )
        with pytest.raises(ValueError, match="tempo_bpm 必须在"):
            db.create_practice_session(
                test_date, item_id, item_name, 5,
                tempo_note="♪", tempo_bpm=151, content="test",
            )
        # 边界值应通过
        s = db.create_practice_session(
            test_date, item_id, item_name, 5,
            tempo_note="♪", tempo_bpm=40, content="test",
        )
        assert s["tempo_bpm"] == 40
        s2 = db.create_practice_session(
            test_date, item_id, item_name, 5,
            tempo_note="♪", tempo_bpm=150, content="test",
        )
        assert s2["tempo_bpm"] == 150

    def test_minutes_must_be_positive(self, test_item, test_date):
        """Case 5: duration_minutes <= 0 拒"""
        item_id, item_name = test_item
        with pytest.raises(ValueError, match="duration_minutes 必须 > 0"):
            db.create_practice_session(
                test_date, item_id, item_name, 0,
                tempo_note="♪", tempo_bpm=80, content="test",
            )
        with pytest.raises(ValueError, match="duration_minutes 必须 > 0"):
            db.create_practice_session(
                test_date, item_id, item_name, -3,
                tempo_note="♪", tempo_bpm=80, content="test",
            )

    def test_content_length_limit(self, test_item, test_date):
        """Case 6: content 长度 > 200 拒"""
        item_id, item_name = test_item
        with pytest.raises(ValueError, match="content 必须是"):
            db.create_practice_session(
                test_date, item_id, item_name, 5,
                tempo_note="♪", tempo_bpm=80, content="x" * 201,
            )
        # 200 字符应通过
        s = db.create_practice_session(
            test_date, item_id, item_name, 5,
            tempo_note="♪", tempo_bpm=80, content="x" * 200,
        )
        assert len(s["content"]) == 200


class TestSaveAndDailySummary:
    def test_daily_summary_synced(self, test_item, test_date):
        """Case 7: save_practice_session_and_daily_summary 同步 daily 汇总 + 写 audit + 更新冗余列"""
        item_id, item_name = test_item
        s1 = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 5,
            tempo_note="♪", tempo_bpm=80, content="第一分句",
            practice_at="2024-07-27 19:00:00.000",
        )
        s2 = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 3,
            tempo_note="♪", tempo_bpm=85, content="第二分句",
            practice_at="2024-07-27 19:30:00.000",
        )
        # daily 汇总
        daily = db.get_daily_practice(test_date)
        assert daily["total_minutes"] == 8
        assert daily["items"] == [{"item": item_name, "item_id": item_id, "minutes": 8}]
        assert daily["practice_at"] == "2024-07-27 19:00:00.000"  # 首次写入, 保留
        # sessions
        sessions = db.get_practice_sessions(test_date)
        assert len(sessions) == 2
        # audit (save_session 2 次)
        conn = db._get_connection()
        audit_rows = conn.execute(
            "SELECT method, session_id FROM practice_audit_log WHERE practice_date = ? ORDER BY id",
            (test_date.isoformat(),),
        ).fetchall()
        assert [r["method"] for r in audit_rows] == ["save_session", "save_session"]
        assert audit_rows[0]["session_id"] == str(s1["id"])
        assert audit_rows[1]["session_id"] == str(s2["id"])

    def test_delete_last_session_resets_daily(self, test_item, test_date):
        """Case 8: 删最后一条 session → total=0, items='[]'"""
        item_id, item_name = test_item
        s1 = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 5,
            tempo_note="♪", tempo_bpm=80, content="第一分句",
        )
        # 删
        db.delete_practice_session(s1["id"])
        daily = db.get_daily_practice(test_date)
        assert daily["total_minutes"] == 0
        assert daily["items"] == []
        # 删应不残留 session
        sessions = db.get_practice_sessions(test_date)
        assert sessions == []

    def test_delete_middle_session_keeps_others(self, test_item, test_date):
        """Case 9: 删中间一条不影响其他 session + daily total 正确"""
        item_id, item_name = test_item
        s1 = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 5,
            tempo_note="♪", tempo_bpm=80, content="第一分句",
        )
        s2 = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 3,
            tempo_note="♪", tempo_bpm=80, content="第二分句",
        )
        s3 = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 4,
            tempo_note="♪", tempo_bpm=80, content="第三分句",
        )
        # 删 s2
        db.delete_practice_session(s2["id"])
        # daily 5+4=9
        daily = db.get_daily_practice(test_date)
        assert daily["total_minutes"] == 9
        # sessions 还剩 2
        sessions = db.get_practice_sessions(test_date)
        assert len(sessions) == 2
        assert {s["id"] for s in sessions} == {s1["id"], s3["id"]}
        assert {s["duration_minutes"] for s in sessions} == {5, 4}

    def test_legacy_migration_idempotent(self, test_date):
        """Case 10: legacy migration 幂等 (跑 2 次不重复生成 session)"""
        from src.migrate_add_practice_sessions import _migrate
        # _migrate 函数检测表已存在直接 return already_exists=True
        # 第一次跑 (可能已存在, 已存在则 already_exists=True)
        stats1 = _migrate()
        # 第二次跑 (必 already_exists=True)
        stats2 = _migrate()
        assert stats2["already_exists"] is True

    def test_last_tempo_columns_updated(self, test_item, test_date):
        """Case 11: practice_items.last_tempo_note/bpm 正确更新 (Q1=B 性能优化)"""
        item_id, item_name = test_item
        # 写 ♩/85
        s1 = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 5,
            tempo_note="♩", tempo_bpm=85, content="test",
        )
        tempo = db.get_latest_session_tempo(item_id)
        assert tempo is not None
        assert tempo["last_tempo_note"] == "♩"
        assert tempo["last_tempo_bpm"] == 85
        # 再写 ♪/90 → 冗余列应更新
        s2 = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 3,
            tempo_note="♪", tempo_bpm=90, content="test",
        )
        tempo2 = db.get_latest_session_tempo(item_id)
        assert tempo2["last_tempo_note"] == "♪"
        assert tempo2["last_tempo_bpm"] == 90

    def test_get_daily_practice_returns_practice_at(self, test_item, test_date):
        """Case 12: get_daily_practice 返回 practice_at 字段 (2026-07-27 bug fix)"""
        item_id, item_name = test_item
        s = db.save_practice_session_and_daily_summary(
            test_date, item_name, item_id, 5,
            tempo_note="♪", tempo_bpm=80, content="test",
            practice_at="2024-07-27 19:00:00.000",
        )
        daily = db.get_daily_practice(test_date)
        # 关键: 字段存在 + 值正确 (修复前 KeyError)
        assert "practice_at" in daily
        assert daily["practice_at"] == "2024-07-27 19:00:00.000"
