---
id: 26091801
type: sprint
version: 1.0.0
start_date: 2026-09-18
end_date: 2026-09-18
status: 进行中
priority: 高
summary: "practice 页计时器生产落地 — 把 demo 定稿的滚轮数字+刻度尺+花纹/音符+沉浸式正计时替换现有 picker 与倒计时 overlay，前后端契约对齐"
tags: [sprint, dizical, practice, timer, integration]
---

# Sprint 26091801 · practice 计时器生产落地

## 1. 背景与触发

dad 2026-09-18 拍板（附 demo 截图「ok了就是这个效果」）：

> 现在先把这个计时器替换掉原来计时器，然后所有对应前后端逻辑要对上。起 sprint 走 sprint-workflow，开发好以后自行单元测试，然后起一个新 tab 起 warden 进行 audit PR，过关后准备合并且 sprint-workflow 走完流程。最后起新 tab，minimax，让 minimax 连 mcp deploy。

前置：sprint 26091701（demo 迭代）已产出定稿 demo `docs/demos/timer-counter-v3.1-demo-2026-09-18.html`，dad 逐轮验收通过（滚轮数字 / 刻度尺 / 指针替换 / 过渡动效 / 圆弧花纹 / 六款花朵 / 音符气泡 / 调参台定稿参数）。

## 2. 团队分工

| 角色 | pane | 承担 |
|---|---|---|
| orchestrator | w10:p1 dizical-hermes | 计划、实现、单测、PR、融合与汇报 |
| 审计 | w10:p3 dizical-warden（另开新 tab） | PR 级独立审计（read-only） |
| 部署 | w10:p2 dizical-minimax（另开新 tab） | MCP CloudRun 部署 |

## 3. 交付物

1. 生产页 `src/kid_app/templates/practice.html` 计时器模块替换（选择态 + 运行态）
2. demo 归档进仓（`docs/demos/` + 本地 GSAP vendor）
3. 单测（pytest 前端契约 + 现有回归）
4. PR + review packet
5. warden 审计报告（read-only）
6. minimax MCP 部署记录

## 4. 状态

- [ ] Phase 1 PLAN + 拍板（本文件同期）
- [ ] Phase 2 实现 + 单测 + PR
- [ ] warden 审计
- [ ] dad 拍 merge
- [ ] Phase 3 收尾（7 项 checklist）
- [ ] minimax MCP deploy

## 5. Sprint 回顾（收尾时填）

| 项 | 值 |
|---|---|
| 预计 vs 实际 | 待填 |
| 学到 | 待填 |
| 风险点 | 待填 |
