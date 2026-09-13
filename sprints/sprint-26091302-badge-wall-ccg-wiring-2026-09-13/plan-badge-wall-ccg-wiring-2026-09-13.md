---
id: 26091302-plan
type: plan
version: 0.1.0
date: 2026-09-13
status: 进行中
tags: [plan, dizical, badge, ccg, wiring]
---

# PLAN — B6 图鉴接线

## 目标
把已定稿的 CCG 卡面接进图鉴两页：列表静态卡、详情弹窗 3D 交互卡、locked 纯 CSS 灰度。页面外壳不动。

## 拆解（4 步）
| # | 内容 | 文件 | 判定 |
|---|------|------|------|
| 1 | `mountCard` 增 `opts {static, locked}`，默认行为不变 | `static/js/badge-ccg.js` | node --check + 领取弹窗回归 |
| 2 | 我的成就：卡墙换 CCG（静态）+ 详情弹窗换 CCG 双栏（交互） | `templates/achievements.html` | Jinja 解析 + 页面 200 |
| 3 | 成就殿堂：同上 | `templates/badges.html` | Jinja 解析 + 页面 200 |
| 4 | 列表静态卡尺寸 + locked 视觉（仅 CSS） | `static/css/badge-ccg.css` | grep 断言 + dad 真机 |

## 不做（范围外）
- 后端 / DB / API 一律不动（`card_no`、`card_theme` 由 B1/B2 负责）
- 页面外壳：页头、筛选 tab、底部导航、整页背景、网格与统计数字
- 用户端主题选择器（主题 = 设计期配置项）
- `demo-archive/` 冻结快照

## 分工
- 实施：minimax worker（pane `w19:p2`），brief `/tmp/b6_brief.md`
- 审计：hermes（本 session）—— diff 逐条核对契约、跑回归、出审计报告
- 视觉验收：dad 真机（agent 不做视觉自证）

## 依赖 / 风险
- 与 PR #324 / #325 无文件重叠（模板 + CCG 静态资源），可并行；验证环境需合并三者才看得到编号 + 主题 + 新卡
- 列表 44–46 张卡：静态态必须不绑 pointer、不进 rAF，否则手机上掉帧
- minimax 可能偏离契约 → 审计以 diff 为准，不采信自报

## 进度
- [x] sprint 文档 + vault 双写
- [x] 分支 `feat/sprint-26091302-badge-wall-ccg-wiring`（from main `440eb5c`）
- [x] brief 已派发 minimax
- [ ] 实施完成
- [ ] 审计（hermes）
- [ ] PR → 等 dad review/merge
- [ ] dad 真机验收
