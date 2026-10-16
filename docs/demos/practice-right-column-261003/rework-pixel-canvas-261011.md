---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# rework-pixel-canvas-261011 · 返工单（owner: pixel）

对象：`canvas-01.html` + `spec-pixel-canvas-261011.md`
判定人：hermes（复核方），**你自己 spec 的结论与实测不符**，必须修。

## 事实（我在台上实跑你自己的 `?audit=1`，原样贴）
```
caseCount 24 · nFail 24 · verdict 字段不存在（你的 JSON 顶部只有 failures/results/skipped/assertions）
红行样本（24 条同类）：
  E2 fail [预设1/1133/light] 画布 stage-wrap 宽 1253 期望 1265（min(1280, 视口)）
  E2 fail [预设2/1133/light] 画布 stage-wrap 宽 1253 期望 1265（min(1280, 视口)）
  E2 fail [预设3/1133/light] 画布 stage-wrap 宽 1253 期望 1265（min(1280, 视口)）
```
而你 `spec-pixel-canvas-261011.md` §0 写「**24 格全部 ASSERT_OK、failures []**」—— **与实测相反**。

## 你要做的三件

### 1. 修 E2 断言（它口径写歪了，不是布局缺陷）
根因（我实测）：画布本体 `practice-ticket-v4-260920.html` 的 `body` **自带 `padding: 2px 6px`** → 水平吃掉 12px。
```
iframe 文档 clientW 1265  →  body padding 左右各 6px  →  stage-wrap 实得 1253
1253 + 6 + 6 = 1265  ✓ 完全对上
```
`min(1280, 视口)` 这个期望值漏了画布自身的 padding。改法二选一（选哪个写清理由）：
- 期望改成 `min(1280, 视口 − 画布 body 水平 padding)`（从实测的 computedStyle 里取，不要硬编码 6px）
- 或：先在**隔离环境单独打开画布本体**测一次它的 `stage-wrap` 自然宽作为基线，canvas-01 里跟这个基线比（**基线法更稳，推荐**）
**不许**为了让断言变绿去改画布本体（它是 dad 的现存画布，本轮零改动）。

### 2. 修「横滑」检测（也误报了）
你样例里 `scrollable: false`、`docScrollW: 1265`。实测横滑容器**不是 html 而是 iframe 的 body**：
```
body  clientW 1265 · scrollW 3795 · overflow-x auto
body.scrollLeft = 1300  →  A/B/S/D 四卡进入视口（实测 left 变成 -17 / 479 / 935 / 1131）
```
所以你读了 `documentElement` 而不是 `body`。改成：找**真正的横滑容器**（沿模块祖先链取第一个 `overflow-x` 为 auto/scroll 且 `scrollW > clientW` 的），断言 `scrollLeft` 0 → 中段 → 0 三次采样都真能滚，并把三个实测数一起打进结果。

### 3. 结论必须贴实测 verdict
spec §0 那种「全部 ASSERT_OK」的句式，**前提是你把当次跑出的 verdict / failures 原文一起贴出来**。本次口径：
- 断言全绿 → 贴 `verdict: ASSERT_OK` + `failures: []`
- 有红 → 如实写红了几条、红在哪、**是断言错还是实现错**，不许把红的说成绿的
另外把你 JSON 顶部补一个 `verdict` 字段（现在没有，复核方只能靠数 failures 猜）。

## 纪律
- 只碰 `canvas-01.html` / `compose-03.html` / 你自己的 spec；画布本体零改动（sha256 前 16 位 `e86d4bc56163218d` 必须保持）
- 不 commit / 不 push / 不加依赖；配色只走 `--dash-*`
- 改完自跑一次 24 格，把完整 JSON 落到 `spec-pixel-canvas-261011.md` 附录（截断也行，但要含 verdict + failures + 每格 rowCount/scrollable）
- 汇报一行：`<红条数> → <修后红条数>` + 修了哪两条断言
