---
id: 26091801
type: sprint
version: 1.0.0
start_date: 2026-09-18
end_date: 2026-09-18
status: 进行中
priority: 高
summary: "Sprint 26091801 PLAN — 计时器生产落地：demo 设计替换生产 picker + 倒计时 overlay，前后端契约对齐，单测 + warden 审计 + MCP 部署"
tags: [sprint, dizical, plan, timer]
---

# Sprint 26091801 — practice 计时器生产落地 PLAN

## Goal

把 sprint 26091701 定稿的计时器设计（选择态：滚轮数字 MM:SS + 刻度尺 + 步进按钮；运行态：沉浸式**正**计时 + 细线下生长的圆弧花纹与花朵 + 红色刻度顶端的音符气泡）落地到生产页 `practice`，**替换**现有两套 UI：旧的 `dial knob + activity-wheel` 选择器、以及上一轮未提交的「方案 B」倒计时 overlay。
验收：练习页计时器与 demo 视觉/交互一致；打卡链路（`POST /api/log`）行为与现状完全一致（毫秒不差的时间语义、practice_at、速度/内容必填、正常结束/提前结束弹窗、chime/confetti/CCG 钩子）；前端契约有 pytest 覆盖。

## Blocking Questions（0–3，均给默认建议）

- **Q1 数字字体**：demo 用 JetBrains Mono（jsDelivr fontsource CDN）。生产用哪个？
  — **recommend: 系统等宽栈** `ui-monospace, SFMono-Regular, Menlo, monospace`（0 字节、无 CDN、无新 token）。理由：`~/dev/designrepo` 目录已不存在，仓库规矩「先回 designrepo 加 typography token」**当前无法执行**；系统等宽在 iPad/Mac 上都有 SF Mono/Menlo。若 dad 要 JetBrains Mono 外观，后续加 3KB 子集自托管（需他拍 + 补 DESIGN.md token）。
- **Q2 GSAP 来源**：生产页现在从 cdnjs 拉 gsap 3.12.5（`canvas-confetti` 同理）。
  — **recommend: GSAP 改为本地自托管（`static/vendor/gsap.min.js`，72KB）并保留 CDN 兜底**。理由：实测本机 CDN 间歇 `ERR_CONNECTION_CLOSED`，一旦失败整页动效全死（含本次新增的花纹/气泡）。
- **Q3 旧 UI 去留**：旧的 `dial knob + activity-wheel` 与「方案 B」倒计时 overlay 是否删除？
  — **recommend: 全删**。demo 已用刻度尺替代选择器、用正计时替代倒计时，dad 已验收；留着会与新手势/事件冲突（旧 knob 透明后仍吃指针，历史上出过 bug）。

## Assumptions

1. **Data**：练习时长 1–30 分钟整数（现 `duration` 变量 + `MIN_MIN/MAX_MIN`），打卡分钟数 `Math.max(1, Math.ceil(elapsed/60))`（提前结束）或 `duration`（正常结束）——本次不改变该语义。
2. **Failure**：`/api/log` 失败 → 保持现有 `alert` + `submitting` 防重放逻辑；GSAP 缺失（CDN 挂）→ 计时核心功能必须仍可用（动画降级为直接赋值）。
3. **Boundaries**：只改 practice 页（模板 + 该页内联 JS/CSS）；不动 `/api/*` 后端签名；不动 practice 页的其它模块（session panel / 补录 / 额外练习 / CCG 三面）。
4. **State**：`started / paused / timerRunning / finishPending / elapsed / duration` 六个变量语义保持不变，新 UI 只作为它们的视图层。
5. **Environment**：iPad mini Safari（744×1133 CSS）+ iPhone Safari（440×956）+ Mac Safari；窄屏（≤1099）无左侧 rail 的布局下也要正常。
6. **Scope**：包含 demo 归档进仓 + GSAP vendor；不包含 cloudrun 部署（那是 sprint 末尾 minimax 的活）、不包含字体子集（等 Q1 拍板）。
7. **Testing**：新增 pytest 断言前端契约（practice.html 含新元素 id、旧 UI 元素已移除、`practice_at` 传参仍在、`/api/log` 调用未被改动）；跑现有全量 pytest 确认零回归。

## Plan

1. **Demo 归档**（先落，供 warden 对拍）
   - `docs/demos/timer-counter-v3.1-demo-2026-09-18.html`（定稿 demo）
   - `docs/demos/vendor/gsap.min.js`（本地 GSAP，sha256 记录在报告里）
   - 删 `docs/demos/timer-select-v2-demo-2026-09-18.html` 之外的临时文件？—— 保留 v3/v3.1 两个 demo，删 v2/variants 以防混淆（待定，倾向保留全部，仓库 docs/demos 已存在同类归档）
2. **模板改造** `src/kid_app/templates/practice.html`
   - 删：`.picker-card` 内 dial knob / activity-wheel 相关 DOM + CSS + JS（`updateWheel`/`updateVisual`/picker 实例化）
   - 删：「方案 B」`.timer-countdown` overlay 的 DOM/CSS/JS（`enterRunningUI`/`exitRunningUI`/`dimRunningUI`/`bounceRunningValue`/`updateRunningProgress`）
   - 增：新计时器卡片 DOM（滚轮数字 + 刻度尺 + 步进按钮 + 状态胶囊 + 花纹 SVG 层 + 气泡层 + 按钮排）
   - 增：对应 CSS（沿用 demo 的 token：#FF6B6B primary / #E8D8B0 底轨 / #D9C79A 花纹 / #2C3E50 数字）
   - 增：对应 JS（`makeCounter/renderCounter`、`buildRuler/placeNeedleAt/paintRulerSelect/paintRulerRunning`、`buildVine/revealVine/retractVine/bloomFlowersUpTo`、`buildBubbles/emitBubbles`、`VINE_FLOWERS` 六款花 + `hash01` 花种取值、调参常量 `VINE_CFG` 按 dad 定稿 0.90/19/16/1.00/1.5）
   - 改：状态机接线 —— `toggleTimer()` / `startTickInterval()` / `finishEarly()` / `resetTimer()` / `abortFinishEarly()` / `cancelFinishEarly()` 改为驱动新 UI（保持 `elapsed`/`duration` 变量与打卡链路不变）
   - 新增：`setDuration(v)` 代替旧 picker 的 setValue；刻度尺拖拽 → 改 `duration`；步进按钮 ±1 分钟
   - 保留：`submitPractice()` 全链路（`practice_at`、`behavior_log`、`tempo_note/tempo_bpm/content` 必填校验）、两个 finish modal、`playChime()`、`fireConfetti()`、`DizicalCCG.checkUnclaimed()`、`loadTodayRecords()`
3. **GSAP 自托管**：`src/kid_app/static/vendor/gsap.min.js` + 模板改为本地优先、CDN 兜底
4. **单测**：`tests/test_practice_timer_frontend.py`（新）+ 全量 `pytest`
5. **PR**：feature branch `feat/practice-timer-integration-260918`（或复用 `feat/practice-timer-ui-260917`，见下）→ review packet → warden 审计 → dad 拍 merge

**Alternative considered and rejected**：把 demo 的整段 JS 原样内联进 practice.html（含调参台）—— 拒绝，因为调参台是 demo 调试件、生产页不需要，且会触发「页面含调试控件」类审计问题；改为把 demo 的参数固化成常量。
