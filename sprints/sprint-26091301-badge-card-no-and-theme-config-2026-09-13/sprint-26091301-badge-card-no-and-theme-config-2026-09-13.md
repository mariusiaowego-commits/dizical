---
id: 26091301
type: sprint
version: 0.1.0
start_date: 2026-09-13
end_date: —
status: 进行中
priority: 高
summary: "徽章卡编号 (achievements.card_no) + 主题的设计期入口 (config 下拉)。承接 PR #323 合并后的 backlog B1/B2。"
tags: [sprint, dizical, badge, card-no, theme]
---

# SPRINT 26091301 — 徽章卡编号 + 主题设计期入口

## 0. 来源

1. dad 2026-09-13 原话：**「323 merge skill别瘦身 继续开发 我记得完整plan里有很多项目要做的」**
2. 前置已完成：**PR #323 已 merge**（squash 进 main，tip = `440eb5c`，2026-09-13T02:47:21Z）
3. 清单来源：`docs/AI-PLAN-ccg-backlog-260913.md`（B1–B5）、`docs/AI-PRD-徽章卡编号-260912.md`
4. 承接规则：B1/B2 属 backlog，本 sprint 单独立项，不与 CCG 视觉同 PR

## 1. Goal

- **B1 徽章卡编号**：`achievements.card_no`（图鉴编号，一卡一号、永久不变）
  - 幂等迁移（双后端）+ 现有 46 张一次性回填 + 新徽章 `MAX+1`（建卡事务内）
  - 两条 API 加**可选**字段 `card_no`：`GET /api/badge/unclaimed`、`GET /api/achievements`
  - 前端：卡面 `No.%03d` 取真值，无值显示 `—`（禁止再兜底假号 `001`）
  - 前端顺带：卡面日期 `achieved_at` → `2026年6月16日`
- **B2 主题设计期入口**：config 侧加「卡片主题」下拉（8 套），写 `achievements.card_theme`
  - ⚠️ 定位（dad 原话）：主题是**设计期材料**，不是用户功能 ⇒ **不做**用户侧主题选择器

## 2. 范围外

- 7 日盲盒主题卡编号（独立体系 `THEMES` dict，另立方案）
- 卡片视觉改动（dad：其它不要动了）、`sort_order` 语义清理
- 小程序改代码（Q4=A：只给 API 加可选字段，展示择期）
- B3 防伪档位定档 / B4 金框 1px 底座去留 —— 等 dad 眼验后拍

## 3. 决策记录（PRD §4 已由 dad 拍）

| 问 | 结论 |
|----|------|
| Q1 编号语义 | **A** 图鉴编号（稳定、永久） |
| Q2 编排方式 | **A** 按「类别 → 现有 sort_order（0 的按 created_at）→ id」自动排 001–046 |
| Q3 星级来源 | **A** `achievements.card_stars` 列（上一 sprint 已上线，本 sprint 不再动） |
| Q4 小程序 | **A** 本轮只加 API 可选字段，展示择期 |

## 4. 验收标准

1. 现有 46 张卡 `card_no` 唯一且连续；重复跑回填不改任何已有编号（幂等）
2. 领取弹窗 / `/badges` / 演示页三处编号一致；无值显示 `—` 而非 `001`
3. 改 `sort_order`（或 `sort_order_override`）后编号**不变**
4. 新建卡拿到 `MAX+1`，不跳号不重号
5. 全量 `pytest tests/` 绿（基线 **732 passed / 8 skipped / 0 failed**）
6. 小程序老包不报错（新字段可选）

## 5. 执行方式与产物位置

- 分支：`feat/sprint-26091301-badge-card-no`（基于 `440eb5c`）
- 流程：local → test → feature → PR（dad review + merge）
- 文档：本目录 4 份（sprint / plan / tech-spec / test-plan），仓库与 Obsidian vault 两侧逐文件 md5 一致

## 6. 进度

- [x] PR #323 merge 进 main（`440eb5c`）
- [x] 分支 + sprint 文档（本目录）
- [ ] B1 代码落地（迁移 / 回填 / 写入路径 / 两条 API / 前端格式化 / 测试）
- [ ] B1 全量 pytest 绿 + PR
- [ ] B2 config 主题下拉 + 测试 + PR
- [ ] 收尾：STATUS.md / DEVELOPMENT_PLAN.md / vibe log / API-CHANGELOG / vault 镜像

## 7. 待 dad 一句话

1. B4 金框最外 1px 暗掐丝底座：留 / 去（对比页第 ② 段）
2. B3 防伪强度档位：弱 ×1 / 中 ×1.6 / 强 ×2.4（对比页第 ③ 段）
3. B2 落地形态确认：config 下拉写入 `card_theme` 即够，还是也要「新建卡时选主题」的入口
