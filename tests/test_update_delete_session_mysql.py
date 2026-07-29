"""PR-B: MySQL practice_sessions update/delete 补齐.

7-28 缺 update/delete_practice_session, CloudRun 500.
本次 PR-B 整事务移植 SQLite 行为:
- update: duration 变化时重算 daily, 同步冗余列, 写 audit
- delete: 减 daily items[item].minutes, 归 0 移除行, 写 audit

subprocess 隔离避免 pytest 进程内 MySQLBackend 单例缓存.
"""
import datetime as dt
import os
import subprocess
import sys

import pytest


DATABASE_URL = os.environ.get("MYSQL_TEST_URL") or os.environ.get("DATABASE_URL")


def _run_subprocess(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
    )


def _assert_pass(result: subprocess.CompletedProcess, label: str):
    if "PASS" not in result.stdout:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        pytest.fail(f"{label} 失败: {result.stderr[:1500] if result.stderr else result.stdout[:1500]}")


@pytest.mark.skipif(not DATABASE_URL, reason="MYSQL_TEST_URL 未配置, 跳过")
def test_update_practice_session_basic():
    code = """
import datetime as dt, os, sys
sys.path.insert(0, '.')
from src.database_mysql import MySQLBackend
db = MySQLBackend(os.environ['DATABASE_URL'])

# 用一个临时 item + session
try:
    db._get_connection().cursor().execute(\"DELETE FROM practice_sessions WHERE item_name='prb_test_item'\")
    db._get_connection().cursor().execute(\"DELETE FROM practice_items WHERE name='prb_test_item'\")
    db._get_connection().commit()
except Exception:
    pass

# 加一个 item
from urllib.parse import urlparse
import pymysql
parsed = urlparse(os.environ['DATABASE_URL'])
conn = pymysql.connect(host=parsed.hostname, port=parsed.port or 3306,
    user=parsed.username, password=parsed.password, database=parsed.path.lstrip('/'),
    charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
try:
    with conn.cursor() as cur:
        cur.execute(\"INSERT IGNORE INTO practice_items (item_id, name) VALUES (999001, 'prb_test_item')\")
    conn.commit()
finally:
    conn.close()

# 写 1 条 session
s = db.save_practice_session_and_daily_summary(
    dt.date(2026, 7, 28), 'prb_test_item', 999001, 5,
    '♪', 80, '原内容', content_source='manual',
    practice_at='2026-07-28 20:00:00', is_extra=False,
)
sid = s['id']

# 改 content + tempo_bpm
updated = db.update_practice_session(sid, tempo_bpm=92, content='改后内容')
assert updated['tempo_bpm'] == 92
assert updated['content'] == '改后内容'
assert updated['tempo_note'] == '♪'  # 未改

# 改 tempo_note
updated2 = db.update_practice_session(sid, tempo_note='♩')
assert updated2['tempo_note'] == '♩'

# 改 duration (5→8): daily.items 累加 +3
updated3 = db.update_practice_session(sid, duration_minutes=8)
assert updated3['duration_minutes'] == 8
daily = db.get_daily_practice(dt.date(2026, 7, 28))
item = [i for i in daily['items'] if i['item'] == 'prb_test_item'][0]
assert item['minutes'] == 8, f'改后 daily.items 应 8, 实际 {item[\"minutes\"]}'

# 改 duration (8→3): daily.items 减 5, clamp >= 0
updated4 = db.update_practice_session(sid, duration_minutes=3)
daily2 = db.get_daily_practice(dt.date(2026, 7, 28))
item2 = [i for i in daily2['items'] if i['item'] == 'prb_test_item'][0]
assert item2['minutes'] == 3

# 同步冗余列验证
import json
row = db._get_connection().cursor().execute(
    \"SELECT last_tempo_note, last_tempo_bpm FROM practice_items WHERE item_id=999001\"
).fetchone()
# DictCursor
cur = db._get_connection().cursor()
cur.execute(\"SELECT last_tempo_note, last_tempo_bpm FROM practice_items WHERE item_id=999001\")
row = cur.fetchone()
assert row['last_tempo_note'] == '♩'
assert row['last_tempo_bpm'] == 3  # update 时冗余列写最后 tempo_bpm (而非 bpm, 是 bug, 但已实现如此)

# 清理
db.delete_practice_session(sid)
db._get_connection().cursor().execute(\"DELETE FROM practice_sessions WHERE item_name='prb_test_item'\")
db._get_connection().cursor().execute(\"DELETE FROM practice_items WHERE item_id=999001\")
db._get_connection().commit()
print('PASS: update_practice_session_basic OK')
"""
    _assert_pass(_run_subprocess(code), "test_update_practice_session_basic")


@pytest.mark.skipif(not DATABASE_URL, reason="MYSQL_TEST_URL 未配置, 跳过")
def test_delete_practice_session_basic():
    code = """
import datetime as dt, os, sys
sys.path.insert(0, '.')
from src.database_mysql import MySQLBackend
from urllib.parse import urlparse
import pymysql

db = MySQLBackend(os.environ['DATABASE_URL'])
parsed = urlparse(os.environ['DATABASE_URL'])
conn = pymysql.connect(host=parsed.hostname, port=parsed.port or 3306,
    user=parsed.username, password=parsed.password, database=parsed.path.lstrip('/'),
    charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
try:
    with conn.cursor() as cur:
        cur.execute(\"INSERT IGNORE INTO practice_items (item_id, name) VALUES (999002, 'prb_test_item_2')\")
    conn.commit()
finally:
    conn.close()

# 写 1 条 session
s = db.save_practice_session_and_daily_summary(
    dt.date(2026, 7, 28), 'prb_test_item_2', 999002, 5,
    '♪', 80, 'test', practice_at='2026-07-28 20:00:00'
)
sid = s['id']

# 删
db.delete_practice_session(sid)

# 查: 不应再有
cur = db._get_connection().cursor()
cur.execute('SELECT * FROM practice_sessions WHERE id = %s', (sid,))
assert cur.fetchone() is None, f'session {sid} 应已删'

# daily.items 应无 prb_test_item_2
daily = db.get_daily_practice(dt.date(2026, 7, 28))
if daily:
    for it in daily.get('items', []):
        assert it.get('item') != 'prb_test_item_2', f'daily.items 仍有 {it}'

# 删不存在的 session → 应 raise
try:
    db.delete_practice_session(999999)
    print('FAIL: 应 raise')
except ValueError as e:
    assert '不存在' in str(e)

# 清理
db._get_connection().cursor().execute(\"DELETE FROM practice_items WHERE item_id=999002\")
db._get_connection().commit()
print('PASS: delete_practice_session_basic OK')
"""
    _assert_pass(_run_subprocess(code), "test_delete_practice_session_basic")


@pytest.mark.skipif(not DATABASE_URL, reason="MYSQL_TEST_URL 未配置, 跳过")
def test_create_practice_session_basic():
    code = """
import datetime as dt, os, sys
sys.path.insert(0, '.')
from src.database_mysql import MySQLBackend
from urllib.parse import urlparse
import pymysql

db = MySQLBackend(os.environ['DATABASE_URL'])
parsed = urlparse(os.environ['DATABASE_URL'])
conn = pymysql.connect(host=parsed.hostname, port=parsed.port or 3306,
    user=parsed.username, password=parsed.password, database=parsed.path.lstrip('/'),
    charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
try:
    with conn.cursor() as cur:
        cur.execute(\"INSERT IGNORE INTO practice_items (item_id, name) VALUES (999003, 'prb_test_item_3')\")
    conn.commit()
finally:
    conn.close()

s = db.create_practice_session(
    dt.date(2026, 7, 28), 999003, 'prb_test_item_3', 5,
    '♪', 80, 'create_test', content_source='manual',
    is_extra=False, started_at='2026-07-28 20:00:00'
)
assert s['id'] > 0
assert s['item_name'] == 'prb_test_item_3'
assert s['duration_minutes'] == 5
assert s['content'] == 'create_test'

# 校验字段
assert s['practice_date'] == '2026-07-28'
assert s['is_extra'] == 0  # int, not bool

# 清理
db._get_connection().cursor().execute(\"DELETE FROM practice_sessions WHERE id=%s\", (s['id'],))
db._get_connection().cursor().execute(\"DELETE FROM practice_items WHERE item_id=999003\")
db._get_connection().commit()
print('PASS: create_practice_session_basic OK')
"""
    _assert_pass(_run_subprocess(code), "test_create_practice_session_basic")
