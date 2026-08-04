# 2026-08-04 — Cutover Parity Fix Sprint v2

> **v2 变更**：v1 + 完整 MOA 统一对抗性 reference (`.hermes/plans/2026-08-04_moa-unified-redteam-reference.md`) 24 项 P0 + 20 项 P1 + 失败场景 F1~F10 + 上线门禁 37 项
> **目标**：14:00 女儿 web 录入前把"切云前必崩"全部修完，部署只读 → 修复 → 验证 → 恢复
> **状态**：进行中

## 时间表

| 时间 | 阶段 | 动作 |
|------|------|------|
| 10:55 | T0 ✅ | git tag `pre-cutover-parity-2026-08-04` @ 18de13794d + 本地 SQLite 备份 `dizi-20260804-105520.db` SHA256 32e5864d3... |
| 10:55 | T1 ✅ | `git checkout -b feat/cutover-parity-fix-2026-08-04` |
| 10:58 | T2 ✅ | MOA 统一 reference 写入 `.hermes/plans/2026-08-04_moa-unified-redteam-reference.md` |
| 11:00 | T3 | 写 MAINTENANCE_MODE env-driven middleware + /api/__maintenance__ 端点 |
| 11:10 | T4 | 重启 kid_app，验证只读生效 |
| 11:20 | T5 | gateway Telegram 通知 dad |
| 11:25 | T6 | dad 出门 |
| 11:30 | T7 | Phase 2 parity 修复开始（按 P0 优先级） |
| 12:50 | T8 | 本地起 MySQL 后端 + 全端点 smoke |
| 13:00 | T9 | 切回非只读 + Telegram 解禁 |
| 14:00-15:00 | T10 | dad 回来女儿练的 |

## Phase 2 — Parity 修复（按 P0 优先级）

### 批次 1: P0-1 17 处裸 SQL (紧急)
- app.py 13 处：`conn.execute(...)` → `conn.cursor().execute(...)` 或 `db_adapter.execute()`
- config.py 4 处 assignments PUT/DELETE
- 占位符 `?` → `%s`
- 行：app.py:199, 356, 363, 384, 405, 426, 546, 799, 824, 833, 2243, 2252, 2367；config.py:1018, 1052, 1071, 1083

### 批次 2: P0-2 json_extract/json_each
- app.py:405-408 `_calc_top_items` 改 MySQL `JSON_TABLE` 或 backend 抽象
- 同步检查 824, 833

### 批次 3: P0-3 + P0-13 weekly_assignments schema 对齐
- database_mysql.py:384-410 改 `INSERT ... ON DUPLICATE KEY UPDATE` 单行 JSON
- database_mysql.py:414-420 查询方向修对
- schema_mysql.sql:169-178 加 `UNIQUE(lesson_date)`（DDL 幂等）

### 批次 4: P0-4 MySQL 补 4 个方法
- list_stages
- get_stage_by_order
- get_stage_containing_date
- get_practice_sessions_in_range

### 批次 5: P0-9 save_practice_session_and_daily_summary 显式事务 + FOR UPDATE
- database_mysql.py:1135-1138 SELECT 改 `FOR UPDATE`
- 显式 BEGIN/COMMIT

### 批次 6: P0-12 practice_sessions 加 version/updated_at
- database_mysql.py:780-797 DDL 加 version BIGINT DEFAULT 1 + updated_at DATETIME(3)
- update/delete 带 `WHERE id=? AND version=?`

### 批次 7: P0-15 /health 拆 /health/live + /health/ready
- app.py:82-105 拆分
- /health/ready 真查 DB 失败返 503

### 批次 8: P0-16 MySQL 客户端超时
- database_mysql.py:36-66 加 connect_timeout/read_timeout/write_timeout + ping(reconnect=True)

### 批次 9: P0-22 audit log 事务对齐
- database.py:837-841 SQLite 端 audit 移入事务

### 批次 10: P0-21 behavior_log 合并 SELECT
- database_mysql.py:1187-1194 与 1135-1138 合并为单次 SELECT FOR UPDATE

### 批次 11: 凭据 + Dockerfile
- P0-7 tests/test_save_daily_practice_mysql.py:96-97 删硬编码
- P0-8 Dockerfile:28 删旧注释

## 验证 gate（T8 必跑）

- [ ] 本地 `DATABASE_URL=mysql+...` 起 kid_app 成功
- [ ] curl /health 返 database=ok
- [ ] 53 写端点 smoke 全过 (按 MOA reference §1 P0 范围)
- [ ] 关键读端点不返 500
- [ ] pytest 已有测试全过（test_save_daily_practice_mysql.py 等）
- [ ] 没有任何 P0 未解决
- [ ] git commit + diff 干净

## 风险

- **回滚**：`git checkout main && bash scripts/start-prod.sh` 回 backup point
- **数据保护**：
  - 本地 SQLite 未动
  - 云 MySQL 未动
  - 修复期间只读模式不写云
- **dizical 女儿下午录入**：1-2 次/天，影响小
- **不可逆操作**：仅 DDL 加 UNIQUE 约束（idempotent），无 DROP/DELETE/TRUNCATE
- **不切 DATABASE_URL**：所有验证用 `DATABASE_URL=mysql+...` 启本地 kid_app

## 不可逆操作清单

- weekly_assignments 加 UNIQUE 约束（DDL idempotent）
- 没有 DROP / DELETE / TRUNCATE
- 没有切 DATABASE_URL（仅本地启停验证）
- 没有改 CloudRun 配置

## Gateway 通知文案

### T5 (11:20)
"系统进入只读模式，预计 13:00 恢复。14:00 后女儿练的可以正常录入。by Hermes cutover-parity-fix-2026-08-04"

### T9 (13:00)
"修复完成 + 53 写端点 smoke 通过。解除只读。生产可写。"

## sprint plan v1 → v2 diff

- 新增 MOA reference 引用
- P0 列表从 6 → 24 项
- P1 列表从 5 → 20 项
- 失败场景 F1~F10 显式列出
- 修复批次从 6 → 11
- 验证 gate 引用 37 项 checkpoint（待 SRE v2 详细展开）
