---
id: 26080405
type: sprint
version: 1.0.0
start_date: 2026-08-04
end_date: 2026-08-04
status: 进行中
priority: 高
summary: 切云前必崩 parity 修复 — 17 处裸 SQL + weekly_assignments schema + 4 个 MySQL 缺方法 + 容器本地 FS + 凭据 + 只读模式部署
tags: [sprint, dizical, parity-fix, cutover]
---

# Sprint 08 — Cutover Parity Fix (2026-08-04) Sprint 记录

## Goal

2026-08-04 14:00 女儿 web 录入前，修完 MOA red-team 找到的所有切云前 P0 阻断。部署只读模式 → 修复 → 验证 → 恢复非只读。

## 拍板记录 (Phase 1)

- 完整 MOA 8-04 跑完（3 路真 MOA，4 份 red-team 报告）
- dad 拍板 8 项（Q1=A Q2=B Q3=A Q4=A Q5=A Q6=A Q7=A Q8=A）
- 11:00 sprint 启动（无拍板题，沿用 8-04 共识）

## 任务状态

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 0 | git tag 备份 | ✅ | pre-cutover-parity-2026-08-04 @ 18de13794d |
| 0.5 | 本地 SQLite 备份 | ✅ | dizi-20260804-105520.db SHA256 32e5864d3... |
| 1 | 切 feat/cutover-parity-fix-2026-08-04 分支 | ✅ | |
| 2 | MOA 统一 reference | ✅ | 24 P0 + 20 P1 + 失败场景 F1~F10 |
| 3 | 写 MAINTENANCE_MODE middleware | ⏳ | |
| 4 | 部署只读 + 验证 | ⏳ | |
| 5 | Telegram 通知 dad | ⏳ | |
| 6 | dad 出门 | ⏳ | 11:25 |
| 7 | 批次 1: 17 处裸 SQL | ⏳ | |
| 8 | 批次 2: json_extract/json_each | ⏳ | |
| 9 | 批次 3: weekly_assignments schema | ⏳ | |
| 10 | 批次 4: 4 个 MySQL 方法 | ⏳ | |
| 11 | 批次 5-6: 显式事务 + version | ⏳ | |
| 12 | 批次 7: /health 拆分 | ⏳ | |
| 13 | 批次 8: MySQL 客户端超时 | ⏳ | |
| 14 | 批次 9-10: audit + behavior_log | ⏳ | |
| 15 | 批次 11: 凭据清理 | ⏳ | |
| 16 | 本地 DATABASE_URL=mysql+... 起 kid_app 验证 | ⏳ | |
| 17 | 53 写端点 smoke | ⏳ | |
| 18 | pytest 已有 | ⏳ | |
| 19 | 切回非只读 | ⏳ | 13:00 |
| 20 | Telegram 解禁通知 | ⏳ | |
| 21 | 女儿下午录入 | ⏳ | 14:00-15:00 |

## Sprint 回顾 (待 closeout 时填)

- **学到了什么**：
- **哪些下次会避免**：
- **文档/工具改进**：

## Commit

- 本次全部 commit 在 feat/cutover-parity-fix-2026-08-04 分支
- commit 列表：(待 closeout 填)

## PR

- (待 closeout 填)

## 链接

- Plan: [[plan-cutover-parity-fix-2026-08-04]]
- PRD: [[prd-cutover-parity-fix-2026-08-04]]
- Tech Spec: [[tech-spec-cutover-parity-fix-2026-08-04]]
- Test Plan: [[test-plan-cutover-parity-fix-2026-08-04]]
- MOA Reference: [[../moa-unified-redteam-reference-2026-08-04]]
- 父 plan: [[../../../../dizical/.hermes/plans/2026-08-04_cloud-mysql-primary-multiclient-cutover]]
- 备份点: git tag `pre-cutover-parity-2026-08-04` @ 18de13794d
- 本地 SQLite 备份: `~/.dizical/backups/manual/dizi-20260804-105520.db`
