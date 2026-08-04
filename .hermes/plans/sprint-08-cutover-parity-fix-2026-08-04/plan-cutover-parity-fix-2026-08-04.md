---
id: 26080401
type: plan
sprint: sprint-08-cutover-parity-fix-2026-08-04
project: dizical
date: 2026-08-04
status: 进行中
priority: 高
related:
  - "[[moa-unified-redteam-reference-2026-08-04]]"
  - "[[../moa-unified-redteam-reference-2026-08-04]]"
tags: [plan, sprint-08, dizical, parity-fix, cutover]
---

# Sprint 08 — Cutover Parity Fix (2026-08-04) PLAN

## Goal

2026-08-04 14:00-15:00 女儿 web 录入前，修完 MOA red-team 找到的所有切云前 P0 阻断：
- 17 处裸 `conn.execute()` + `?` 占位符 + SQLite 专有 `json_extract`/`json_each`
- weekly_assignments 两后端 schema 异构
- MySQL 缺 4 个方法
- 容器本地 FS 写 + 缺 hermes CLI
- 凭据泄露

部署只读模式 → 修复 → 验证 → 恢复非只读。

## Blocking Questions

无（已基于 8-04 完整 MOA 拍板 P0-1~P0-24）

## Assumptions

1. **本地 SQLite 完整且未变**：backup 15 表 716800 bytes SHA256 32e5864d3...
2. **云 MySQL 完整且未变**：当前 15 表约 1,700+ 行，dizical 账号已建
3. **当前 kid_app (PID 11366) 跑 main 分支，DATABASE_URL 未设，走 SQLite 路径**
4. **MAINTENANCE_MODE 当前不存在**：要在 kid_app 加 env-driven middleware
5. **CloudRun 生产端不在本仓库控制范围**：只读验证不直接动 CloudRun env
6. **dad 11:25 出门前需切到只读**
7. **dad 14:00 回来后女儿可能 web 录入 1-2 条**：必须 T9 13:00 切回非只读
8. **修复期间所有改动只走 feat/cutover-parity-fix-2026-08-04 分支**
9. **本 sprint 不写云，不切 DATABASE_URL，不动生产 CloudRun**

## Plan

### T0 备份 (10:55) ✅
- `git tag -a pre-cutover-parity-2026-08-04` @ 18de13794d
- `bash scripts/backup_local_sqlite.sh` → `dizi-20260804-105520.db` (716800 bytes)

### T1 分支 (10:55) ✅
- `git checkout -b feat/cutover-parity-fix-2026-08-04`

### T2 MOA Reference (10:58) ✅
- `.hermes/plans/2026-08-04_moa-unified-redteam-reference.md` (24 P0 + 20 P1 + 失败场景 F1~F10 + 37 项 checkpoint)
- tqob 双写（本次补做）

### T3 MAINTENANCE_MODE middleware (11:00)
- 写 `src/kid_app/maintenance.py`
- env: `MAINTENANCE_MODE=readonly|off|maintenance`
- 行为：
  - off: 正常读写
  - readonly: 写操作 503 + `{"error": "MAINTENANCE_READONLY", "message": "系统升级中，预计 13:00 恢复"}`
  - maintenance: 所有请求 503 + 维护页
- /api/__maintenance__ 端点：返当前模式 + 升级状态

### T4 部署只读 (11:10)
- `bash scripts/stop-prod.sh`
- `MAINTENANCE_MODE=readonly bash scripts/start-prod.sh`
- curl /api/__maintenance__ 验证

### T5 通知 (11:20)
- `hermes send --to telegram "系统进入只读，预计 13:00 恢复"`

### T6 dad 出门 (11:25)

### T7 Phase 2 修复 (11:30-12:50)

按 11 个批次顺序执行（详细见 PRD/TECH-SPEC）：
1. 17 处裸 SQL 收口 (P0-1)
2. json_extract/json_each 适配 (P0-2)
3. weekly_assignments schema 对齐 (P0-3 + P0-13)
4. MySQL 补 4 个方法 (P0-4)
5. save_practice_session_and_daily_summary 显式事务 (P0-9)
6. practice_sessions version/updated_at (P0-12)
7. /health 拆分 (P0-15)
8. MySQL 客户端超时 (P0-16)
9. audit log 事务对齐 (P0-22)
10. behavior_log 合并 SELECT (P0-21)
11. 凭据清理 (P0-7 + P0-8)

### T8 验证 (12:50-13:00)
- `DATABASE_URL=mysql+...` 起本地 kid_app
- curl /health 返 database=ok
- 53 写端点 smoke
- pytest 已有
- git commit + diff 干净

### T9 切回非只读 (13:00)
- `MAINTENANCE_MODE=off bash scripts/start-prod.sh`
- curl 验证读写
- `hermes send --to telegram "修复完成，解除只读"`

### T10 女儿练的 (14:00-15:00)

## Files Changed

### 新增
- `src/kid_app/maintenance.py` (~30 行)
- `src/database_mysql.py` (+120 行，4 个方法 + weekly_assignments 重写)
- `src/database.py` (~10 行修改，audit 移入事务)
- `schema_mysql.sql` (+1 行 UNIQUE 约束)
- `tests/` (暂不改，本地 smoke 够)

### 修改
- `src/kid_app/app.py` (~30 行，17 处 SQL 收口 + /health 拆分)
- `src/kid_app/routes/config.py` (~20 行，4 处 SQL 收口)
- `scripts/start-prod.sh` (+3 行，MAINTENANCE_MODE 透传)
- `tests/test_save_daily_practice_mysql.py` (删硬编码)
- `Dockerfile` (删旧注释)

### 不动
- `data/dizi.db` (红线)
- Cloud MySQL 数据
- CloudRun 生产配置
- 任何云资源

## Verification

### 静态
- `python3 -c "import ast; ast.parse(open('file.py').read())"` 全过
- `grep -n "conn\.execute\|json_each" src/` → 0 命中
- `grep -n "\?" src/kid_app/routes/config.py` SQL 字符串内 → 0 命中

### 数据
- 本地 SQLite `PRAGMA integrity_check = ok`
- 本地行数与 backup 一致

### 运行时
- `curl /health` database=ok
- `curl /api/practice/items` 返数据
- 53 写端点 smoke 全过
- pytest 已有不新增 fail

## Risks

- **回滚**：`git checkout main && bash scripts/start-prod.sh` → backup point
- **MAINTENANCE_MODE 误改 off**：写 503 → 影响女儿下午录入
- **P0-15 /health 拆分影响 CloudRun**：CloudRun 生产端用 /health，需同步改 readiness 路径或保留 /health 不变
- **数据库 schema 漂移**：只有 weekly_assignments 加 UNIQUE（DDL idempotent）
- **mysql ping 触发副作用**：MySQLBackend 加 ping(reconnect=True) 可能改变现有连接行为

## Alternative Considered and Rejected

- **完全停服模式**：拒绝 → 影响女儿下午录入，只读模式更友好
- **一次性大 PR**：拒绝 → 单批次改动 review 困难，失败回滚链路长
- **不动 kid_app 切云**：拒绝 → MOA 共识 P0-1/2/3 必崩
- **改云 MySQL 适配旧代码**：拒绝 → 跟原 PRD 倒挂，且云端数据已被使用

## Links

- 父 plan：`.hermes/plans/2026-08-04_cloud-mysql-primary-multiclient-cutover.md`
- MOA reference：`.hermes/plans/2026-08-04_moa-unified-redteam-reference.md`
- 并发研究：`~/dev/dizical-minip/.hermes/plans/2026-08-04-cloud-mysql-cutover-concurrency-research.md`
- 子 red-team 报告：
  - `.hermes/plans/2026-08-04_cloud-mysql-cutover-redteam.md` (data)
  - `.hermes/plans/2026-08-04_cloud-cutover-sre-redteam-review-v2.md` (sre v2)
  - `.hermes/plans/2026-08-04_cloud-mysql-primary-multiclient-cutover-review.md` (fullstack)
- 备份点：git tag `pre-cutover-parity-2026-08-04` @ 18de13794d
- 本地 SQLite 备份：`~/.dizical/backups/manual/dizi-20260804-105520.db`
