"""PR-A-4: MySQL append_behavior_log 原子追加.

旧实现: `behavior_log || %s` 字符串拼接, 破坏已有 JSON 结构.
新实现: `JSON_ARRAY_APPEND(COALESCE(behavior_log, JSON_ARRAY()), '$', CAST(%s AS JSON))`.

subprocess 隔离测试, 避免 pytest 进程内 MySQLBackend 单例缓存.
"""
import datetime as dt
import os
import subprocess
import sys

import pytest


# subprocess 测试需要 DATABASE_URL; 缺则 skip
DATABASE_URL = os.environ.get("MYSQL_TEST_URL") or os.environ.get("DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="MYSQL_TEST_URL 未配置, 跳过 MySQL append_behavior_log 测试")
def test_append_behavior_log_concat_format():
    """append 后 JSON 数组内容正确 (不是字符串拼接)."""
    code = """
import datetime as dt, json, os, sys
sys.path.insert(0, '.')
from src.database_mysql import MySQLBackend
db = MySQLBackend(os.environ['DATABASE_URL'])

# 1. 清残留
try:
    db.save_daily_practice(date=dt.date(2026, 7, 31), items=[], total_minutes=0, practiced='N', log='')
except Exception as e:
    pass

# 2. 新建 daily 行
db.save_daily_practice(date=dt.date(2026, 7, 31), items=[], total_minutes=0, practiced='N', log='')

# 3. append 2 条
db.append_behavior_log(dt.date(2026, 7, 31), {'enter_time': '2026-07-31 19:00:00', 'item': 'A', 'minutes': 5})
db.append_behavior_log(dt.date(2026, 7, 31), {'enter_time': '2026-07-31 19:05:00', 'item': 'B', 'minutes': 3})

# 4. 验证: JSON 数组长度 == 2, 元素是 dict 不是字符串
result = db.get_daily_practice(dt.date(2026, 7, 31))
blog = result['behavior_log']
assert isinstance(blog, list), f'应返 list, 实际 {type(blog)}: {blog!r}'
assert len(blog) == 2, f'应 2 条, 实际 {len(blog)}: {blog!r}'
assert blog[0]['item'] == 'A', f'第 0 条应 A, 实际 {blog[0]!r}'
assert blog[1]['item'] == 'B', f'第 1 条应 B, 实际 {blog[1]!r}'
assert blog[0]['minutes'] == 5
assert blog[1]['minutes'] == 3

# 5. 清理
db.save_daily_practice(date=dt.date(2026, 7, 31), items=[], total_minutes=0, practiced='N', log='')
print('PASS: append_behavior_log 原子追加 OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
    )
    if "PASS" not in result.stdout:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        pytest.fail(f"append_behavior_log 原子追加测试失败: {result.stderr[:1000] if result.stderr else result.stdout[:1000]}")


@pytest.mark.skipif(not DATABASE_URL, reason="MYSQL_TEST_URL 未配置, 跳过")
def test_append_to_null_behavior_log():
    """daily 行 behavior_log 列 NULL 时, 第一次 append 应正确初始化为 [entry]."""
    code = """
import datetime as dt, json, os, sys
sys.path.insert(0, '.')
from src.database_mysql import MySQLBackend
db = MySQLBackend(os.environ['DATABASE_URL'])

# 清空 (含 behavior_log)
try:
    db.save_daily_practice(date=dt.date(2026, 7, 30), items=[], total_minutes=0, practiced='N', log='')
except Exception:
    pass

# 直接 UPDATE 让 behavior_log = NULL (绕过 save_daily_practice 的默认空字符串)
from src.database import db as sqlite_db  # noqa: F401  # 占位, 防 lint

# 改用 mysql cursor
import pymysql
from urllib.parse import urlparse
parsed = urlparse(os.environ['DATABASE_URL'])
conn = pymysql.connect(
    host=parsed.hostname, port=parsed.port or 3306,
    user=parsed.username, password=parsed.password,
    database=parsed.path.lstrip('/'),
    charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
)
try:
    with conn.cursor() as cur:
        cur.execute("UPDATE daily_practices SET behavior_log = NULL WHERE date = %s", ('2026-07-30',))
    conn.commit()
finally:
    conn.close()

# append 1 条
db.append_behavior_log(dt.date(2026, 7, 30), {'enter_time': '2026-07-30 20:00:00', 'item': 'C', 'minutes': 7})

result = db.get_daily_practice(dt.date(2026, 7, 30))
blog = result['behavior_log']
assert isinstance(blog, list)
assert len(blog) == 1
assert blog[0]['item'] == 'C'

# 清理
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[], total_minutes=0, practiced='N', log='')
print('PASS: append_to_null_behavior_log OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
    )
    if "PASS" not in result.stdout:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        pytest.fail(f"append_to_null 测试失败: {result.stderr[:1000] if result.stderr else result.stdout[:1000]}")


@pytest.mark.skipif(not DATABASE_URL, reason="MYSQL_TEST_URL 未配置, 跳过")
def test_append_repeated_does_not_break_json():
    """连 append 3 次不破坏 JSON 结构 (旧实现会变成 '[1][2][3]')."""
    code = """
import datetime as dt, os, sys
sys.path.insert(0, '.')
from src.database_mysql import MySQLBackend
db = MySQLBackend(os.environ['DATABASE_URL'])

try:
    db.save_daily_practice(date=dt.date(2026, 7, 29), items=[], total_minutes=0, practiced='N', log='')
except Exception:
    pass
db.save_daily_practice(date=dt.date(2026, 7, 29), items=[], total_minutes=0, practiced='N', log='')

for i in range(3):
    db.append_behavior_log(dt.date(2026, 7, 29), {'enter_time': f'2026-07-29 20:0{i}:00', 'item': f'X{i}', 'minutes': i+1})

result = db.get_daily_practice(dt.date(2026, 7, 29))
blog = result['behavior_log']
assert isinstance(blog, list)
assert len(blog) == 3, f'应 3 条, 实际 {len(blog)}: {blog!r}'
for i, entry in enumerate(blog):
    assert entry['item'] == f'X{i}'

db.save_daily_practice(date=dt.date(2026, 7, 29), items=[], total_minutes=0, practiced='N', log='')
print('PASS: append_repeated_does_not_break_json OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
    )
    if "PASS" not in result.stdout:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        pytest.fail(f"repe append 测试失败: {result.stderr[:1000] if result.stderr else result.stdout[:1000]}")
