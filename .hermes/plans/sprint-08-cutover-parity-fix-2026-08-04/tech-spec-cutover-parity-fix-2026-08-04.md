---
id: 26080403
type: tech-spec
sprint: sprint-08-cutover-parity-fix-2026-08-04
project: dizical
date: 2026-08-04
status: 进行中
priority: 高
related:
  - "[[plan-cutover-parity-fix-2026-08-04]]"
  - "[[../moa-unified-redteam-reference-2026-08-04]]"
tags: [tech-spec, sprint-08, dizical, parity-fix]
---

# Sprint 08 — Cutover Parity Fix Tech Spec

## 1. MAINTENANCE_MODE middleware

### 1.1 文件：`src/kid_app/maintenance.py`（新增）

```python
import os
from fastapi import Request
from fastapi.responses import JSONResponse

MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "off")  # off | readonly | maintenance

READONLY_BLOCKED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# Paths always allowed even in readonly (health, maintenance status, read-only GET)
def is_status_path(path: str) -> bool:
    return path in ("/health", "/health/live", "/health/ready", "/api/__maintenance__", "/")

async def maintenance_middleware(request: Request, call_next):
    path = request.url.path
    if is_status_path(path):
        return await call_next(request)
    if MAINTENANCE_MODE == "off":
        return await call_next(request)
    if MAINTENANCE_MODE == "maintenance":
        return JSONResponse(
            status_code=503,
            content={
                "error": "MAINTENANCE",
                "message": "系统维护中，预计稍后恢复",
                "path": path,
            },
        )
    if MAINTENANCE_MODE == "readonly" and request.method in READONLY_BLOCKED_METHODS:
        return JSONResponse(
            status_code=503,
            content={
                "error": "MAINTENANCE_READONLY",
                "message": "系统升级中，预计 13:00 恢复。请稍后录入。",
                "path": path,
            },
        )
    return await call_next(request)
```

### 1.2 注册：`src/kid_app/app.py:73-77`

```python
app.add_middleware(MaintenanceMiddleware)  # after CORSMiddleware
```

注：FastAPI middleware stack 后注册的先执行。Maintenance 应在 CORSMiddleware 之后，让 CORS preflight 不被拦截。

### 1.3 端点：`src/kid_app/app.py`

```python
@app.get("/api/__maintenance__")
def maintenance_status():
    return {
        "mode": MAINTENANCE_MODE,
        "started_at": _MAINTENANCE_STARTED_AT,  # if not off
        "expected_resume": "2026-08-04 13:00 (Asia/Shanghai)",
    }
```

### 1.4 启动脚本：`scripts/start-prod.sh`

```bash
# 在 exec uvicorn 之前
export MAINTENANCE_MODE="${MAINTENANCE_MODE:-off}"
```

## 2. app.py 17 处裸 SQL 收口

### 2.1 全局规则

```python
# 旧：
cur = conn.execute("SELECT ... WHERE date = ?", (date,))

# 新（两选一）：
# 选项 A：db_adapter.execute（推荐，自动转 %s）
from src.db_adapter import execute
cur = execute(conn, "SELECT ... WHERE date = ?", (date,))

# 选项 B：cursor.execute
with conn.cursor() as cur:
    cur.execute("SELECT ... WHERE date = %s", (date,))
```

### 2.2 json_extract / json_each 适配

**SQLite 端** (`app.py:405-408`):
```sql
SELECT pi.name, SUM(json_extract(je.value, '$.minutes'))
FROM daily_practices dp, json_each(dp.items) je
JOIN practice_items pi ON ...
```

**MySQL 端**（重写为 JSON_TABLE）:
```sql
SELECT pi.name, SUM(jt.minutes)
FROM daily_practices dp
JOIN JSON_TABLE(dp.items, '$[*]' COLUMNS (
    item_id INT PATH '$.item_id',
    minutes INT PATH '$.minutes'
)) AS jt
JOIN practice_items pi ON ...
```

抽到 `database_mysql.py:_calc_top_items()` 方法，避免路由层直接用 SQL。

### 2.3 完整清单

| 文件:行 | 旧 | 新 |
|---------|-----|-----|
| app.py:199 | `cur = conn.execute("SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices WHERE date >= ?", (start,))` | `cur = db_adapter.execute(conn, "SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices WHERE date >= %s", (start,))` |
| app.py:356 | `row = conn.execute("SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices").fetchone()` | `with conn.cursor() as cur: cur.execute("SELECT COALESCE(SUM(total_minutes), 0) FROM daily_practices"); row = cur.fetchone()` |
| app.py:363, 384 | 同上模式 | 同上 |
| app.py:405 | json_extract + json_each | 抽到 database_mysql.py |
| app.py:426, 546, 799, 824, 833, 2243, 2252, 2367 | conn.execute | db_adapter.execute 或 cursor.execute |
| config.py:1018, 1052, 1071, 1083 | conn.execute + ? | db_adapter.execute + %s |

## 3. weekly_assignments MySQL 重写

### 3.1 schema_mysql.sql:169-178

```sql
CREATE TABLE IF NOT EXISTS weekly_assignments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    lesson_date DATE NOT NULL,
    items       TEXT NOT NULL,
    notes       TEXT,
    images      TEXT,
    stage_start DATE,
    stage_end   DATE,
    stage_order INT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_lesson_date (lesson_date)  -- 新增
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

迁移时先 `SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS` 检查 uk_lesson_date 是否存在，存在则跳过。

### 3.2 database_mysql.py:384-410 save_weekly_assignment

```python
def save_weekly_assignment(self, lesson_date, items, notes, images, stage_start, stage_end, stage_order):
    import json
    items_json = json.dumps(items, ensure_ascii=False) if not isinstance(items, str) else items
    images_json = json.dumps(images, ensure_ascii=False) if images else None
    with self._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO weekly_assignments
                (lesson_date, items, notes, images, stage_start, stage_end, stage_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                items = VALUES(items),
                notes = VALUES(notes),
                images = VALUES(images),
                stage_start = VALUES(stage_start),
                stage_end = VALUES(stage_end),
                stage_order = VALUES(stage_order)
            """, (lesson_date, items_json, notes, images_json, stage_start, stage_end, stage_order))
        conn.commit()
```

### 3.3 database_mysql.py:414-420 get_weekly_assignment_for_week

```python
def get_weekly_assignment_for_week(self, anchor_date):
    import json
    with self._get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lesson_date, items, notes, images, stage_start, stage_end, stage_order
                FROM weekly_assignments
                WHERE lesson_date <= %s
                ORDER BY lesson_date DESC
                LIMIT 1
            """, (anchor_date,))
            row = cur.fetchone()
    if not row:
        return None
    return {
        "lesson_date": row[0],
        "items": json.loads(row[1]) if row[1] else [],
        "notes": row[2],
        "images": json.loads(row[3]) if row[3] else [],
        "stage_start": row[4],
        "stage_end": row[5],
        "stage_order": row[6],
    }
```

## 4. MySQL 补 4 个方法

### 4.1 list_stages

参照 SQLite `database.py` 同名方法。返回值结构 byte-equivalent。

### 4.2 get_stage_by_order

参照 SQLite，WHERE stage_order = %s。

### 4.3 get_stage_containing_date

参照 SQLite，WHERE %s BETWEEN stage_start AND stage_end。

### 4.4 get_practice_sessions_in_range

参照 SQLite，按日期范围 + 可选 item_id 查询。

每个方法必须：
- 用 `with self._get_connection() as conn` + `conn.cursor()`
- 用 `%s` 占位符
- 显式 commit/rollback
- 返回值结构跟 SQLite 一致

## 5. /health 拆分

### 5.1 app.py

```python
@app.get("/health/live")
def health_live():
    return {"status": "alive"}

@app.get("/health/ready")
def health_ready():
    try:
        lessons = db.get_all_lessons()
        return {"status": "ready", "database": "ok", "lesson_count": len(lessons)}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "error", "error": str(e)},
        )

# 保留 /health 兼容
@app.get("/health")
def health():
    return health_ready()  # 旧 endpoint 仍工作
```

### 5.2 CloudRun 控制台

dad 后续手动改：readiness probe 路径 = `/health/ready`（或保留 `/health`，因为仍返 200/503）

本次 sprint 不直接动 CloudRun 控制台。

## 6. MySQL 客户端超时

### 6.1 database_mysql.py:36-66

```python
pymysql.connect(
    host=...,
    port=...,
    user=...,
    password=...,
    database=...,
    charset='utf8mb4',
    connect_timeout=5,
    read_timeout=10,
    write_timeout=10,
    cursorclass=DictCursor,
    ping=1,  # 自动 ping 检查
)
```

## 7. audit log 事务对齐

### 7.1 database.py:837-841 (SQLite)

```python
# 旧：commit 在 audit 之前
cursor.execute("INSERT INTO practice_audit_log ...")
conn.commit()

# 新：audit 移入事务
try:
    cursor.execute("INSERT INTO practice_audit_log ...")
    conn.commit()
except Exception:
    conn.rollback()
    raise
```

## 8. behavior_log 合并 SELECT

### 8.1 database_mysql.py:1187-1194

```python
# 旧：先 SELECT daily，再 SELECT behavior_log（独立事务，行锁失效）
# 新：合并为单次 SELECT FOR UPDATE
SELECT items, log, practiced, practice_at, behavior_log
FROM daily_practices
WHERE date = %s
FOR UPDATE
```

## 9. 凭据清理

### 9.1 tests/test_save_daily_practice_mysql.py:96-97

```python
# 旧：硬编码连接串含明文密码
DATABASE_URL = "mysql+pymysql://dizical:****@..."

# 新：从环境变量读，无默认
DATABASE_URL = os.environ["MYSQL_TEST_URL"]
```

### 9.2 Dockerfile:28

删旧注释 `# DATABASE_URL=mysql+pymysql://...@host:port/dizical`

## 10. 实施顺序

按批次顺序：
1. 备份 + 分支 ✅
2. MAINTENANCE_MODE middleware (T3)
3. 部署只读 + 通知 (T4-T5)
4. 批次 1: 17 处裸 SQL 收口
5. 批次 2: json_extract/json_each
6. 批次 3: weekly_assignments
7. 批次 4: 4 个 MySQL 方法
8. 批次 5-6: 显式事务 + version
9. 批次 7: /health 拆分
10. 批次 8: MySQL 客户端超时
11. 批次 9-10: audit + behavior_log
12. 批次 11: 凭据清理
13. 验证 (T8)
14. 切回非只读 (T9)
