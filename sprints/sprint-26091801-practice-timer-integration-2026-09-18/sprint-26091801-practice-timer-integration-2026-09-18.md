---
id: 26091801
type: sprint
version: 1.0.0
start_date: 2026-09-18
end_date: 2026-09-18
status: 已完成
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
| 审计 | w10:t2 / w10:p7 dizical-warden-audit（**另开新 tab**，read-only） | 三轮独立审计：分支一轮「需改」→ 二轮「可 merge」→ PR 级「可 merge」 |
| 部署 | w10:t3 dizical-minimax（另开新 tab） | MCP CloudRun 部署 |

## 3. 交付物

| # | 交付物 | 落点 / 证据 |
|---|---|---|
| 1 | 生产页计时器模块替换（选择态 + 运行态） | `src/kid_app/templates/practice.html`（+731/−80） |
| 2 | demo 归档 + 本地 GSAP vendor | `docs/demos/`（3 个 demo + vendor gsap 72,214B sha256 `28033e449a31ebcc…`） |
| 3 | 单测 29 条 + 全量回归 | `tests/test_practice_timer_frontend.py`；全量 0 失败 |
| 4 | PR + review packet | PR #338（已 merge，squash → `69a81c1`） |
| 5 | 独立审计报告 ×3 轮 | `/tmp/sprint-26091801-warden-review.md`、`-round2.md`、`/tmp/sprint-26091801-pr-audit.md` |
| 6 | minimax MCP 部署记录 | 见 STATUS.md 与本 sprint §6 |

## 4. 状态

- [x] Phase 1 PLAN + 拍板（vault + 主仓双写）
- [x] Phase 2 实现 + 单测 + PR #338
- [x] warden 审计（三轮，末轮 PR 级 可 merge / 无阻塞）
- [x] dad 拍 merge → squash merge `69a81c1`
- [x] Phase 3 收尾（checklist 见 §7；#7 shipped 清单等 dad 拍）
- [ ] minimax MCP deploy

## 5. Sprint 回顾

| 项 | 值 |
|---|---|
| 预计 vs 实际 | 当天完成：定稿 demo → 生产移植 → 29 条单测 → 三轮审计 → merge。实际耗时主要在「审计→修复→复审」两轮往返，值得 |
| 学到 | ① **定稿 demo 的尺寸不能指望容器给**：demo 卡片宽度来自它自己的 grid 舞台，搬进生产 flex 行后塌成 216px、60 格尺子格距 1.8px 挤成一团 —— 移植时必须把尺寸写成显式约束（`width:520px; max-width:100%`）。② **布局类缺陷必须量尺寸/格距，不能只验元素存在性** —— orchestrator 首轮探针全是 DOM/数值断言，全绿却漏了这个，是审计方补上的。③ **视觉层整段移植 + 只读状态桥**（getter/setter 指向生产 `duration/elapsed/timerRunning`）比重写稳：26 个函数 20 个逐字一致，漂移可控。④ **CDN 是单点**：GSAP 从 CDN 拉不到会让整页动效全死 → 本地自托管 + CDN 兜底 |
| 风险点 | 真机手感未验（dad 目视）；`#timerCard` 520px 让桌面/横屏 session-panel 变窄（~293px，需 dad 目视）；既有 12 处未判空 gsap（含 1 处影响正常结束响铃）留 follow-up 小 PR |

## 6. 提交记录

| commit | 内容 |
|---|---|
| `b6cd369` | demo 归档 + demo 侧 GSAP vendor |
| `9d8db77` | 计时器生产落地主体（+721/−73） |
| `dad9895` | 卡片宽度 520px（审计阻塞项） |
| `b6a96bb` | 审计 P1/P2 修复（gsap 判空 / 暂停态锁控件 / 清死代码） |
| `69a81c1` | squash merge 进 main（PR #338） |

## 7. 收尾 checklist

- [x] 1 sprint doc 更新（status 已完成 / end_date / commit 记录 / 回顾表）
- [x] 2 closeout 3-1-1（`verify-2026-09-18.md`）
- [x] 3 decision log 追加（`sprints/decision-log.md` 6 行）
- [ ] 4 STATUS.md 新 sprint 段（本地 gitignored + Obsidian 镜像）
- [x] 5 git tag `sprint-26091801-timer-complete` + push
- [x] 6 Obsidian 双写（md5 一致）
- [ ] 7 shipped 交付清单（**等 dad 拍 closeout 后再写**）
