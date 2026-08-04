---
id: 26080402
type: prd
sprint: sprint-08-cutover-parity-fix-2026-08-04
project: dizical
date: 2026-08-04
status: 进行中
priority: 高
related:
  - "[[plan-cutover-parity-fix-2026-08-04]]"
  - "[[../moa-unified-redteam-reference-2026-08-04]]"
tags: [prd, sprint-08, dizical, parity-fix]
---

# Sprint 08 — Cutover Parity Fix PRD

## User Story

**US-1**: dad 11:25 出门，14:00 回来后女儿可在 web 端练的且数据成功持久化。
**US-2**: 修复期间（11:30-13:00）任何写操作不会破坏数据完整性。
**US-3**: 修复后 kid_app 仍能在 SQLite + MySQL 双后端正确工作，DATABASE_URL=mysql+... 启得起。
**US-4**: 切云前所有 P0 阻断修完，下次切云不 500。

## Acceptance Criteria

### AC-1 只读模式可工作
- [ ] 写操作返 503 + `MAINTENANCE_READONLY` 错误
- [ ] 读操作继续返回数据
- [ ] /api/__maintenance__ 返当前模式
- [ ] dad Telegram 收到通知

### AC-2 P0-1 17 处裸 SQL 全部收口
- [ ] `grep "conn\.execute" src/` 0 命中
- [ ] `grep "json_each\|json_extract" src/` 0 命中
- [ ] `grep "\\?" src/kid_app/routes/config.py` SQL 字符串内 0 命中
- [ ] 所有写路径用 db_adapter 或 cursor.execute

### AC-3 P0-3/P0-13 weekly_assignments 一致
- [ ] MySQL `save_weekly_assignment` 用 `INSERT ... ON DUPLICATE KEY UPDATE`
- [ ] `schema_mysql.sql` 有 `UNIQUE(lesson_date)` 约束
- [ ] `get_weekly_assignment_for_week` 查询方向对齐

### AC-4 P0-4 MySQL 4 方法补齐
- [ ] `list_stages` byte-equivalent to SQLite
- [ ] `get_stage_by_order` byte-equivalent
- [ ] `get_stage_containing_date` byte-equivalent
- [ ] `get_practice_sessions_in_range` byte-equivalent

### AC-5 P0-9 显式事务
- [ ] `save_practice_session_and_daily_summary` 显式 BEGIN
- [ ] `SELECT ... FOR UPDATE` 加锁 daily row
- [ ] behavior_log 合并到同一 SELECT

### AC-6 P0-12 version/updated_at
- [ ] `practice_sessions` DDL 加 `version BIGINT DEFAULT 1`
- [ ] `practice_sessions` DDL 加 `updated_at DATETIME(3)`
- [ ] update_practice_session WHERE version=? 校验
- [ ] delete_practice_session WHERE version=? 校验

### AC-7 P0-15 /health 拆分
- [ ] `/health/live` 仅检查进程存活
- [ ] `/health/ready` 真正查 DB，失败返 503
- [ ] CloudRun readiness 路径文档化

### AC-8 P0-16 MySQL 客户端超时
- [ ] `connect_timeout=5`
- [ ] `read_timeout=10`
- [ ] `write_timeout=10`
- [ ] `ping(reconnect=True)`

### AC-9 P0-22 audit log 一致
- [ ] SQLite 端 audit 移入事务（在 commit 之前）

### AC-10 P0-7/P0-8 凭据清理
- [ ] `tests/test_save_daily_practice_mysql.py:96-97` 不含明文密码
- [ ] `Dockerfile:28` 不含旧 host:port

### AC-11 验证
- [ ] 本地 `DATABASE_URL=mysql+...` 起 kid_app 成功
- [ ] curl /health 返 database=ok
- [ ] curl 53 写端点 smoke 全过
- [ ] pytest 已有不新增 fail
- [ ] 女儿下午录入测试

## Non-Goals

- 不切换 DATABASE_URL
- 不动云 MySQL 数据
- 不部署 CloudRun 新版本
- 不实现 timer lease（下次 sprint）
- 不实现 request_id 幂等表（下次 sprint）
- 不迁移到对象存储（下次 sprint）
- 不补 dad_whitelist / pin_fail_count 专用表（下次 sprint）
- 不修 mac app（不变）
- 不实施 schema_mysql.sql 全表 CHECK（按需）

## Open Questions

- 13:00 切回非只读后，是否需要保留 MAINTENANCE_MODE middleware 代码？**建议：保留，下次切云直接用**
- /health/ready 路径同步到 CloudRun 控制台：dad 手动 / 后续 sprint？
- 本次改动是否需要 PR review？**建议：自己审查 + 通知 dad，因为时间紧**
