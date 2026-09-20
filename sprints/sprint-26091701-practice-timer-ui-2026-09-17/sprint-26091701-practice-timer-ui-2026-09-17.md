---
id: 26091701
type: sprint
version: 1.0.0
start_date: 2026-09-17
end_date: 2026-09-17
status: 进行中
priority: 高
summary: "practice 页计时器模块（dial knob + 倒计时 + 按钮组 + 补录 knob）样式与交互优化 — 方案评审阶段"
tags: [sprint, dizical, practice, timer, ui]
---

# Sprint 26091701 · practice 计时器模块样式与交互优化

## 1. 背景与触发

dad 2026-09-17 拍板：开 worktree 做 practice 页计时器（dial knob + 运行倒计时 + 按钮组 + 补录 knob）的样式与交互优化；做法先由 agy（Claude Opus 4.6 Thinking）出 thinking 方案，不先动码。

## 2. 团队分工

- **方案 (thinking)**：`dizical-agy`（Claude Opus 4.6 Thinking，pane `w10:p6`）
- **调度 / 融合 / 前端实现**：`dizical-hermes`（coder profile，pane `w10:p1`）
- **git / 测试 / 机械活**：`dizical-minimax`（MiniMax-M3，pane `w10:p2`）
- **审计 / 验收**：`dizical-warden`（pane `w10:p3`）
- **拍板**：dad

## 3. 工作区

- worktree：`/Users/mt16/.herdr/worktrees/dizical/timer-260917`
- 分支：`feat/practice-timer-ui-260917`（base `origin/main`）
- 生产 8765 从主 checkout 跑，本 sprint 所有改动只落 worktree

## 4. 任务清单

- [x] 方案产出（agy，thinking）→ `plan-practice-timer-ui-2026-09-17.md`：现状盘点 9 节 / 问题 17 条（样式 5 + 交互 4 + 动效 3 + 可访问性 2 + 性能 1）/ 方案 A·B·C / 推荐 A
- [x] 可点变体对照 demo → `docs/demos/timer-variants-demo-2026-09-17.html`（三面板 A/B/C 并排，复用 practice.html 真代码：dial knob CSS L157-214 + `createDialKnob()` L2753-2848；带 ×60 演示倍速开关；demo 内把 `SNAP_RADIUS` 0.8 → 1.5 解问题 I1）
- [x] dad 定运行态 = 方案 B「极简数字」，已实装进 worktree `practice.html`（开始收 picker → 56px 大字 mm:ss + 4px 横条；暂停压暗；归零 bounce；提前结束/打卡/重置统一还原）；修掉本人引入的「暂停/提前结束 点不动」叠加层 bug
- [x] 选择时间态 v2 方案 + demo（knob + wheel 对齐 / 一体化胶囊座舱）→ **已被 v3 方向取代**，文件留作历史：`plan-select-state-v2-2026-09-18.md`、`docs/demos/timer-select-v2-demo-2026-09-18.html`
- [x] **v3 方向（dad 拍）** → `docs/demos/timer-counter-v3-demo-2026-09-18.html`：数字滚轮移植 Rare UI AnimatedCounter（11 面/列 + 1.5em mask 窗口 + 方向感知弹簧 + sizer），金额→MM:SS；底部进度条可拖拽增减时长（步进 1 分钟）；保留 开始/暂停/提前结束；计时中沉浸式且**正计时**
- [ ] v3 落地真实 practice.html（worktree）→ 移除 knob/activity-wheel 相关代码或保留给补录 tab（待 agy 评审结论）
- [ ] 验收（warden）+ PR

## 5. 参考材料

- `src/kid_app/templates/practice.html`（自包含：页内 CSS + JS，~3075 行）
- `src/kid_app/static/style.css`（`.timer-display` / `.timer-btns` / `.timer-btn`）
- `docs/demos/dial-knob-demo.html`（617 行，旋钮交互原始 demo）
- `PRDs/PRD-timer-layout-prototype.html`、`PRDs/PRD-计时器模块重构-260511.md`、`PRDs/AI-PRD-练习计时细分内容-260727.md`、`docs/tech-spec/practice-v3.1.md`

## 6. 硬约束

不改 timer protect modal / page-leave guard / pause-resume 语义；不引新依赖；不改 DESIGN.md token；440×956 / 744×1133 / 1133×744 / 1728×1117 四档都要过。
