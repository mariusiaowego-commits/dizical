---
id: 26080404
type: test-plan
sprint: sprint-08-cutover-parity-fix-2026-08-04
project: dizical
date: 2026-08-04
status: 进行中
priority: 高
related:
  - "[[plan-cutover-parity-fix-2026-08-04]]"
  - "[[prd-cutover-parity-fix-2026-08-04]]"
tags: [test-plan, sprint-08, dizical, parity-fix]
---

# Sprint 08 — Cutover Parity Fix Test Plan

## TC-01: MAINTENANCE_MODE readonly
```bash
MAINTENANCE_MODE=readonly bash scripts/start-prod.sh
curl http://127.0.0.1:8765/api/practice/items  # 200
curl -X POST http://127.0.0.1:8765/api/log -d '{}' -H 'Content-Type: application/json'  # 503
curl http://127.0.0.1:8765/api/__maintenance__  # {"mode": "readonly", ...}
```

## TC-02: MAINTENANCE_MODE off
```bash
MAINTENANCE_MODE=off bash scripts/start-prod.sh
curl -X POST http://127.0.0.1:8765/api/log -d '{}' -H 'Content-Type: application/json'  # 4xx (validation), not 503
```

## TC-03: 17 处裸 SQL 已收口
```bash
grep -rn "conn\.execute" /Users/mt16/dev/dizical/src/ | grep -v "db_adapter"  # 0 命中
grep -rn "json_each\|json_extract" /Users/mt16/dev/dizical/src/  # 0 命中
grep -rn "?" /Users/mt16/dev/dizical/src/kid_app/routes/config.py  # 0 在 SQL 字符串内
```

## TC-04: weekly_assignments parity
```bash
DATABASE_URL=mysql+pymysql://... bash scripts/start-prod.sh
curl -X POST http://127.0.0.1:8765/config/api/assignments -d '{"lesson_date":"2026-08-04","items":[{"item":"长音","item_id":1,"metronome":"♪=80"}]}'  # 200
curl http://127.0.0.1:8765/api/assignments/latest?item_id=1  # 200 + items JSON
```

## TC-05: 4 个 MySQL 方法
```bash
curl http://127.0.0.1:8765/api/practices/stages  # 200
curl 'http://127.0.0.1:8765/api/practices/stage-detail?stage_order=1'  # 200
curl 'http://127.0.0.1:8765/api/practices/stage/2026-08-04'  # 200
```

## TC-06: 显式事务
```bash
DATABASE_URL=mysql+pymysql://... bash scripts/start-prod.sh
# 双发测试（同时 2 个 POST 同 date）
# 用 curl 并行
seq 2 | xargs -I{} -P2 curl -X POST http://127.0.0.1:8765/api/log -d '...' 
# 期望：daily_practices.total_minutes 累加 1 次
```

## TC-07: /health/ready
```bash
curl http://127.0.0.1:8765/health/live  # 200
curl http://127.0.0.1:8765/health/ready  # 200 + database=ok
# 拔 DATABASE_URL，期望 /health/ready 返 503
```

## TC-08: 凭据清理
```bash
grep -n "Qpwoei\|dizical:.*@" /Users/mt16/dev/dizical/tests/test_save_daily_practice_mysql.py  # 0 命中
grep -n "sh-cynosdbmysql" /Users/mt16/dev/dizical/Dockerfile  # 0 命中
```

## TC-09: pytest 已有
```bash
DATABASE_URL=mysql+pymysql://... pytest tests/test_save_daily_practice_mysql.py -v
```

## TC-10: 本地行数与 backup 一致
```bash
python3 -c "
import sqlite3
backup = sqlite3.connect('/Users/mt16/.dizical/backups/manual/dizi-20260804-105520.db')
local = sqlite3.connect('/Users/mt16/dev/dizical/data/dizi.db')
for t in ['practice_items', 'daily_practices', 'practice_sessions']:
    bc = backup.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    lc = local.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    assert bc == lc, f'{t}: backup={bc} local={lc}'
print('OK: local == backup')
"
```

## TC-11: 女儿下午录入端到端
- 14:00 dad 回来
- 女儿 web 端练一次
- curl /api/practices/{today_date} 验证数据已写

## 53 写端点 smoke matrix

执行脚本（伪代码）：

```python
endpoints = [
    ("POST", "/api/log", {"date":"2026-08-04","items":[{"item":"长音","item_id":1,"minutes":5}],"total_minutes":5}),
    ("PUT", "/api/practice-sessions/1", {"tempo_note":"♪=80"}),
    ("DELETE", "/api/practice-sessions/999", None),  # 期望 404
    ("POST", "/config/api/records", {"date":"2026-08-04","items":[]}),
    ("POST", "/config/api/assignments", {"lesson_date":"2026-08-04","items":[]}),
    # ... 47 more
]
for method, path, data in endpoints:
    r = httpx.request(method, f"http://127.0.0.1:8765{path}", json=data, timeout=5)
    assert r.status_code in (200, 201, 204, 400, 401, 404, 422), f"{method} {path}: {r.status_code} {r.text}"
print(f"OK: {len(endpoints)} endpoints tested")
```

完成所有 TC 后，sprint 8 才算 closeout。

## Negative test

- 故意停 MySQL → /health/ready 返 503
- 故意给错 id → DELETE /api/practice-sessions/{bad} 返 404
- 故意给空 items → POST /api/log 返 422

## Skip 条件

- `pytest -k "skipif"` 已有测试跳过的保留
- 数据库环境特殊（无 MYSQL_TEST_URL）时跳过 TC-06/09
