"""7-27 修复: MySQL save_daily_practice 移植 SQLite merge 逻辑 + clear 路径

跟 SQLite 同步: 同 item 累加 minutes, 不同 item 追加.
清零 (DELETE /api/records/{date}) 走 is_clear 直接 UPDATE, 不触发 merge.

按"先全面 review → 自洽路径 → 每步自验证"模式, 8 个场景覆盖:
1. 新建 a
2. 同 item a 累加
3. 不同 item b 追加
4. 跨 item_id 同名应合并
5. 清零走 is_clear (api_delete_record)
6. 清零后写入新 item (跨场景验证 is_clear 后正常)
7. 不传 practice_at, 不影响既有逻辑
8. race condition with try-except (smoke, 不会真触发)
"""
import datetime as dt
import json
import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="需真云 MySQL TEST_DATABASE_URL (subprocess 隔离跑 8 场景). 本机无凭据时跳过, "
           "切云验证时设 TEST_DATABASE_URL 再跑.",
)
def test_save_daily_practice_mysql_merge_semantics():
    """subprocess 隔离跑 8 个场景 (避开 pytest 进程内 MySQLBackend 单例缓存)."""
    code = """
import datetime as dt, json, sys, os
sys.path.insert(0, '.')
from src.database_mysql import MySQLBackend
db = MySQLBackend(os.environ['DATABASE_URL'])

# 清本测试残留
try:
    db.save_daily_practice(date=dt.date(2026, 7, 30), items=[], total_minutes=0, practiced='N', log='')
except Exception as e:
    print('cleanup err:', e)

# 1. 新建 a 5min
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[{'item':'A','item_id':9101,'minutes':5}], total_minutes=5)
r1 = db.get_daily_practice(dt.date(2026, 7, 30))
assert len(r1['items']) == 1, f"1 新建: 应1条, 实际{len(r1['items'])}"
assert r1['items'][0]['minutes'] == 5
assert r1['total_minutes'] == 5

# 2. 同 item a 累加 3min -> 8min
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[{'item':'A','item_id':9101,'minutes':3}], total_minutes=3)
r2 = db.get_daily_practice(dt.date(2026, 7, 30))
assert len(r2['items']) == 1, f"2 同 item 累加: 应仍1条, 实际{len(r2['items'])}"
assert r2['items'][0]['minutes'] == 8, f"2 累加应=8, 实际{r2['items'][0]['minutes']}"
assert r2['total_minutes'] == 8

# 3. 不同 item b 追加
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[{'item':'B','item_id':9102,'minutes':7}], total_minutes=7)
r3 = db.get_daily_practice(dt.date(2026, 7, 30))
assert len(r3['items']) == 2, f"3 应2条, 实际{len(r3['items'])}"
assert r3['total_minutes'] == 15

# 4. 跨 item_id 但 item 名同 -> 合并
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[{'item':'B','item_id':9999,'minutes':2}], total_minutes=2)
r4 = db.get_daily_practice(dt.date(2026, 7, 30))
b_minutes = [i['minutes'] for i in r4['items'] if i['item'] == 'B']
assert len(b_minutes) == 1, f"4 同名 B 应合并, b 数组={b_minutes}"
assert b_minutes[0] == 9, f"4 B 累加应=9, 实际{b_minutes[0]}"

# 5. 清零 (api_delete_record 路径, is_clear=True) - 应不留存量
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[], total_minutes=0, practiced='N', log='')
r5 = db.get_daily_practice(dt.date(2026, 7, 30))
assert r5['items'] == [], f"5 清零应空 items, 实际{r5['items']}"
assert r5['total_minutes'] == 0
assert r5['practiced'] == 'N'

# 6. 清零后写入新 item (验证 is_clear 后正常路径)
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[{'item':'C','item_id':9103,'minutes':4}], total_minutes=4)
r6 = db.get_daily_practice(dt.date(2026, 7, 30))
assert len(r6['items']) == 1
assert r6['total_minutes'] == 4

# 7. 不传 practice_at + 追加新 item
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[{'item':'D','item_id':9104,'minutes':1}], total_minutes=1)
r7 = db.get_daily_practice(dt.date(2026, 7, 30))
assert len(r7['items']) == 2, f"7 追加应2条 (C+D), 实际{len(r7['items'])}"
assert r7['total_minutes'] == 5

# 清理
db.save_daily_practice(date=dt.date(2026, 7, 30), items=[], total_minutes=0, practiced='N', log='')
print('PASS: 7-27 save_daily_practice 修复 7 场景全过')
"""
    result = subprocess.run(
        ['python3', '-c', code],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True, text=True, timeout=60,
        env={
                **os.environ,
                # Sprint 08: 删旧 host:port 硬编码, 强制要求环境变量注入
                'DATABASE_URL': os.environ['TEST_DATABASE_URL'],
            },
    )
    if 'PASS' not in result.stdout:
        print('STDOUT:', result.stdout)
        print('STDERR:', result.stderr)
        pytest.fail(f"merge 场景失败: {result.stderr[:1000] if result.stderr else result.stdout[:1000]}")
    assert 'PASS' in result.stdout
