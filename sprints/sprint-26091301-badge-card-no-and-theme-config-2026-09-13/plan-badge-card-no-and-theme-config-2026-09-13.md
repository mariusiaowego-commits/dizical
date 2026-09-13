---
id: 26091301-plan
type: plan
version: 0.1.0
date: 2026-09-13
status: 进行中
tags: [plan, dizical, badge, card-no, theme]
---

# PLAN — 徽章卡编号 + 主题设计期入口

## 1. 输入

- 清单：`docs/AI-PLAN-ccg-backlog-260913.md` B1 / B2
- 方案：`docs/AI-PRD-徽章卡编号-260912.md`（§3 落地细节、§5 验收）
- 现状实测：`achievements` 46 行；主键 TEXT `id`；无任何编号列；`sort_order` 36 行为 0
- 相关列已就绪：`card_theme`（上一 sprint）、`card_stars`（上一 sprint）

## 2. 任务分解（顺序执行）

| # | 任务 | 落点 | 依赖 |
|---|------|------|------|
| 1 | 幂等迁移 `ensure_card_no_column`（双后端） | `src/kid_app/badge_db.py` | — |
| 2 | 幂等回填 `backfill_card_no`（只填 NULL，可重跑） | `src/kid_app/badge_db.py` | 1 |
| 3 | 启动 hook 追加 ensure + backfill | `src/kid_app/app.py` | 1,2 |
| 4 | 新建卡写入 `MAX+1`（同事务） | `src/kid_app/badge_db.py` | 1 |
| 5 | `GET /api/badge/unclaimed` 加 `card_no` | `src/kid_app/routes/badge_claim.py` | 1 |
| 6 | `GET /api/achievements` 加 `card_no` | `src/kid_app/routes/minip_api.py` | 1 |
| 7 | 前端 `No.%03d` / `—` + 日期中文化 | `src/kid_app/static/js/badge-ccg.js` | 5 |
| 8 | 测试：5 处建表补列 + 新增 `test_achievements_card_no.py` | `tests/` | 1–7 |
| 9 | B2 config 卡片主题下拉（8 套） | config 路由 + 模板 | 独立 |
| 10 | 文档：`API-CHANGELOG.md` / STATUS / DEVELOPMENT_PLAN / vibe log / vault | — | 5,6,9 |

## 3. 风险与对策

| 风险 | 对策 |
|------|------|
| 测试自建表缺列 → 大批测试红（上个 sprint 踩过：27 红） | 5 处建表 SQL 与生产列**同步**补 `card_no`，写完跑全量而非子集 |
| 云端 MySQL 掉连接导致迁移静默失败 | 迁移失败只 warning（读页面不能 500），但**回填必须可重跑**；启动 hook 同一 try |
| 并发建卡跳号 | 编号在同一写事务内 `MAX+1`（`badge_write_tx`） |
| 编号被排序改动带跑 | 编号与 `sort_order` 完全解耦，回填只写一次 |

## 4. 里程碑

- M1 B1 代码 + 全量 pytest 绿 → PR（等 dad review）
- M2 B2 下拉 + 测试 → 同分支叠加或单独 PR（dad 定）
- M3 收尾：文档 + vault 镜像 + STATUS 更新
