"""
Sprint 09 P0-12 (PR-D): practice_sessions 乐观锁测试

跨端写入冲突时 (web + mac app 同时改同 session), 旧版本不能覆盖新版本.
SQLite + MySQL 后端必须一致返回 ConflictError.

跑法:
  uv run --with pytest python3 -m pytest tests/test_practice_sessions_version.py -v

状态 (2026-08-05 单兵实施):
- ✅ 兼容路径: database.py update/delete 接受 expected_version=None (跳过校验),
    既有 test_practice_sessions.py / test_api_log_dedup.py / test_dedup_window.py 30 个测试 PASSED.
- ⏸️ 乐观锁真路径 (If-Match → 409): 单兵实施期间被 SQLite 测试 setup 跨单例 conn 引用问题卡住
    (Database 实例化后 _conn 复用, 多个测试间 cleanup 后又 create 新实例时旧 conn 指向 readonly 文件),
    已用 @pytest.mark.skip 标记, 等 dad 回来在真云环境 (TEST_DATABASE_URL) 或修测试 setup 后跑.
- ✅ routes 层 If-Match → 409 实现完整, app.py:1593 / 1607 接入 ConflictError.
"""
import datetime as dt
import json
import os
import sys
import tempfile
import sqlite3

import pytest


# 2026-08-05 修正: 之前这里定义了一个从未赋值给 pytestmark 的 skip 标记,
# 导致 handoff 误报 "10 个测试 skip". 实际是 8 failed / 2 passed.
# 真路径测试 (If-Match → 409) 现在由 _use_test_db() 正确注入 app.py 的 db 单例, 全绿.



def _use_test_db(db):
    """把测试 Database 实例注入 app.py 模块, 让 endpoint 测试走临时库.

    之前只替换 src.database.db (db_module.db = db), 但 app.py 顶层
    `from src.database import db` 绑定了首次 import 时的旧实例 → 写已 unlink
    的临时文件 → "attempt to write a readonly database".

    正确做法: 同时替换 app 模块属性 (app.db), 让 app.py 内的 db 引用指向新实例.
    """
    import src.database as db_module
    db_module.db = db
    # app.py 可能已 import 过, 直接替换模块属性
    import src.kid_app.app as app_module
    app_module.db = db
    # 也处理函数内 `from src.database import db as _db` 的惰性引用 (它们每次调用时重新读,
    # 只要 src.database.db 指向新实例即可, 上面已做)
    return db


# ── SQLite 端 (内存隔离, 跑得快) ──────────────────────────────────────────


def _make_sqlite_db():
    """返回 (db, models, original) — SQLiteBackend + 干净 sessions 表.

    通过 DATABASE_URL='' 强制走 SQLite 后端, 让 Database() 重建 + 跑全部 migration.
    """
    from src.database import Database
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    # 不 unlink — tempfile 真实创建的文件, Database() 在此基础上建表.
    # 强制 DATABASE_URL=sqlite:// → 走 SQLiteBackend (而非 MySQL)
    os.environ['DATABASE_URL'] = ''
    # 修改 settings.db_path 指向临时路径, 让 Database() 新实例化时建在临时文件
    from src import models
    original = models.settings.db_path
    models.settings.db_path = path
    # 让 src.database.db 全局单例指向新实例 (跑完 _init_tables 后所有迁移就位)
    import src.database as db_module
    db_module.db = Database(db_path=path)
    return db_module.db, models, original


def _cleanup_sqlite(db, models, original):
    models.settings.db_path = original
    try:
        os.unlink(db.db_path)
    except Exception:
        pass


def _seed_session(db, date_str='2026-08-05'):
    """绕开 save_daily_practice (历史 schema 列名不一致问题), 直接 INSERT 干净 daily + session.

    返回 (session_id, version=1).
    """
    import json as _json
    practice_date = date_str
    # 1. 直接 INSERT daily_practices (避免 save_daily_practice 内部 SELECT item_id 报错)
    with db._get_connection() as conn:
        cursor = conn.cursor()
        # 检查 daily 是否已存在
        cursor.execute('SELECT date FROM daily_practices WHERE date = ?', (practice_date,))
        if cursor.fetchone() is None:
            cursor.execute(
                '''INSERT INTO daily_practices (date, items, total_minutes, log, practiced, practice_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (practice_date, _json.dumps([{'item': '音阶', 'item_id': 9001, 'minutes': 5}]),
                 5, '', 'Y', None),
            )
        # 2. INSERT practice_session (走 INSERT 然后读 row)
        cursor.execute(
            '''INSERT INTO practice_sessions
               (practice_date, item_id, item_name, duration_minutes, tempo_note, tempo_bpm, content,
                content_source, is_extra, started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (practice_date, 9001, '音阶', 5, '♪', 80, 'C 大调上下行', 'manual', 0, None),
        )
        new_id = cursor.lastrowid
        conn.commit()
    sess = db.get_practice_session_by_id(new_id)
    return sess['id'], sess.get('version', 1)


def test_create_session_default_version_is_1():
    """新插 session 默认 version=1 (兼容旧代码)."""
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        assert ver == 1, f"新 session version 应=1, 实际={ver}"
    finally:
        _cleanup_sqlite(db, models, original)


def test_update_with_correct_version_succeeds():
    """expected_version 匹配 → UPDATE 成功, version 自增."""
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        # 更新 tempo, expected_version=1 (当前)
        from src.kid_app.errors import ConflictError
        updated = db.update_practice_session(
            sid, tempo_bpm=85, expected_version=1,
        )
        assert updated is not None
        new_ver = updated['version'] if isinstance(updated, dict) else 0
        assert new_ver == 2, f"UPDATE 后 version 应=2, 实际={new_ver}"
    finally:
        _cleanup_sqlite(db, models, original)


def test_update_with_stale_version_raises_conflict():
    """expected_version 不匹配 → ConflictError, session 不变."""
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        from src.kid_app.errors import ConflictError
        # 模拟别人刚改过, 当前 version=2, 但客户端拿的是 version=1
        db.update_practice_session(sid, tempo_bpm=85, expected_version=1)
        # 现在版本是 2, 客户端再发 version=1
        with pytest.raises(ConflictError) as exc:
            db.update_practice_session(sid, tempo_bpm=90, expected_version=1)
        assert exc.value.current_version == 2, f"ConflictError 应携带 current_version=2"
    finally:
        _cleanup_sqlite(db, models, original)


def test_update_without_expected_version_skips_check():
    """expected_version=None → 跳过校验 (兼容旧调用), version 仍自增."""
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        updated = db.update_practice_session(sid, tempo_bpm=85)  # 无 expected_version
        assert updated is not None
        new_ver = updated['version'] if isinstance(updated, dict) else 0
        assert new_ver == 2, f"无 expected_version 也应自增, 实际={new_ver}"
    finally:
        _cleanup_sqlite(db, models, original)


def test_delete_with_correct_version_succeeds():
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        db.delete_practice_session(sid, expected_version=1)
        # 确认 session 已删
        with pytest.raises(ValueError):
            db.get_practice_session_by_id(sid)
    finally:
        _cleanup_sqlite(db, models, original)


def test_delete_with_stale_version_raises_conflict():
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        from src.kid_app.errors import ConflictError
        # 模拟别人刚 UPDATE 过, 当前 version=2, 客户端拿 version=1 来删
        db.update_practice_session(sid, tempo_bpm=85, expected_version=1)
        with pytest.raises(ConflictError) as exc:
            db.delete_practice_session(sid, expected_version=1)
        assert exc.value.current_version == 2
    finally:
        _cleanup_sqlite(db, models, original)


# ── HTTP endpoint 层 (FastAPI TestClient) ─────────────────────────────────


def _client_with_sqlite():
    """返回 TestClient + 干净 SQLite DB."""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app as fastapi_app
    from src.database import Database
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.unlink(path)
    # 强制 DATABASE_URL=sqlite://
    os.environ['DATABASE_URL'] = ''
    from src import models
    models.settings.db_path = path
    # 重新实例化 Database 单例 — 简单办法: 把全局 db 替换
    import src.database as db_module
    db_module.db = Database(db_path=path)
    return TestClient(fastapi_app), db_module.db, models


def _seed(client, db):
    """插 1 条 session via /api/log, 返回 (session_id, version=1).

    注意: schemas.py:87 要求 item 必传 (min_length=1), 单独传 item_id 不够.
    """
    r = client.post('/api/log', json={
        'item': '音阶',
        'item_id': 9001,
        'date': '2026-08-05',
        'minutes': 5,
        'tempo_bpm': 80,
        'content': '音阶练习',
    })
    assert r.status_code == 200, r.text
    j = r.json()
    return j['session_id'], 1


def test_endpoint_put_if_match_correct_version_200():
    """HTTP 端 PUT 路径 — 用 Database 直插种 (避免 /api/log 路径上 item_id 列名不一致历史遗留问题)."""
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        # 替换全局 db 让 app.py 看到我们这个实例 (注入 app 模块属性, 不只 src.database.db)
        _use_test_db(db)
        from fastapi.testclient import TestClient
        from src.kid_app.app import app as fastapi_app
        client = TestClient(fastapi_app)
        r = client.put(
            f'/api/practice-sessions/{sid}',
            json={'tempo_bpm': 85},
            headers={'If-Match': '1'},
        )
        assert r.status_code == 200, r.text
        assert r.json()['session']['version'] == 2
    finally:
        try:
            os.unlink(db.db_path)
        except Exception:
            pass
        models.settings.db_path = original


def test_endpoint_put_if_match_stale_version_409():
    """HTTP 端 PUT 路径 — 跨端模拟 (双 PUT 不同 version) 走完整乐观锁流程."""
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        _use_test_db(db)
        from fastapi.testclient import TestClient
        from src.kid_app.app import app as fastapi_app
        client = TestClient(fastapi_app)
        # 第 1 个客户端先 UPDATE 成功, version → 2
        r1 = client.put(
            f'/api/practice-sessions/{sid}',
            json={'tempo_bpm': 85},
            headers={'If-Match': '1'},
        )
        assert r1.status_code == 200, r1.text
        # 第 2 个客户端拿老 version=1 改 → 409
        r2 = client.put(
            f'/api/practice-sessions/{sid}',
            json={'tempo_bpm': 90},
            headers={'If-Match': '1'},
        )
        assert r2.status_code == 409, r2.text
        body = r2.json()
        assert body['code'] == 'VERSION_CONFLICT'
        assert body['current_version'] == 2
    finally:
        try:
            os.unlink(db.db_path)
        except Exception:
            pass
        models.settings.db_path = original


def test_endpoint_put_without_if_match_skips_check():
    """旧客户端不带 If-Match → 跳过校验 (向后兼容), 仍自增."""
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        _use_test_db(db)
        from fastapi.testclient import TestClient
        from src.kid_app.app import app as fastapi_app
        client = TestClient(fastapi_app)
        r = client.put(
            f'/api/practice-sessions/{sid}',
            json={'tempo_bpm': 85},
            # 无 If-Match
        )
        assert r.status_code == 200, r.text
        assert r.json()['session']['version'] == 2
    finally:
        try:
            os.unlink(db.db_path)
        except Exception:
            pass
        models.settings.db_path = original


def test_endpoint_delete_if_match_stale_version_409():
    db, models, original = _make_sqlite_db()
    try:
        sid, ver = _seed_session(db)
        _use_test_db(db)
        from fastapi.testclient import TestClient
        from src.kid_app.app import app as fastapi_app
        client = TestClient(fastapi_app)
        # 别人刚改过
        client.put(f'/api/practice-sessions/{sid}', json={'tempo_bpm': 85}, headers={'If-Match': '1'})
        # 我拿老 version 来删
        r = client.delete(
            f'/api/practice-sessions/{sid}',
            headers={'If-Match': '1'},
        )
        assert r.status_code == 409, r.text
        body = r.json()
        assert body['code'] == 'VERSION_CONFLICT'
        assert body['current_version'] == 2
    finally:
        try:
            os.unlink(db.db_path)
        except Exception:
            pass
        models.settings.db_path = original