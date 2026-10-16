---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# fix-pixel-canvas-261011e · 复验剩余两条（owner: pixel）

依据：`review-agy-canvas-261011.md` **§6 复验（v2）**（agy 真窗口定案，34209 B，2026-10-11 15:40）
复现命令（agy 给的，本地可点）：`docs/demos/practice-right-column-261003/scripts/verify-real-window-261011.py`

## P0-1 已判「真修好」，不用再动
宽屏 1280 / 1133 三预设 `modColBottom = ticketBottom = 686.0`（越界 0.0px）；窄屏纵向流式。✓

## 只剩两条

### ① P0-2 判词「只修了真窗口那一路」→ 补脚手架联动
agy 实测：
```
真 744 窗口   railFlexDir column · railClientW/ScrollW 580/580 · 行数=模块数(2/3/6) ✓ 堆叠
真 440 窗口   column · 408/408 · 行数=模块数 ✓ 堆叠
真 1280/1133  row · 878 / 751 · 行数 1 ✓ 宽屏单行横滑
hermes 场景   窗口 1265 + 点顶栏 #czVp「744」→ docClientW 仍 1265 · row · 863/2516 · 行数 1 ✗ 未堆叠
```
根因（agy 定位）：顶栏 `#czVp` 的 `setVp('744')` **只改了卡片 iframe 的 `data-vp`，没有改画布 iframe 自身的宽度** → 画布 iframe 仍 1265 宽，`@media (max-width:1023px)`（注入在画布文档里）自然不生效。
要改：`setVp(w)` **同时把画布 iframe 的宽度设为该档**（或给它挂 `data-vp` 让注入 CSS 用容器/属性选择器判定），使得在桌面窗口里点 744 / 440 时，画布文档宽度真的变成 744 / 440 并且模块轨切换为 `column`。
断言补一条：**在 1265 宽的外层窗口里，点 `#czVp=744` 后实测画布 `docClientW === 744` 且轨 `flex-direction === 'column'`、`scrollW === clientW`**（把这两行实测数打进结果）。三条负控（窄屏强撑单行）保留。

### ② P2-1 判词「没修好」→ 兜底窗口太窄，改 FALLBACK_MS
agy 实测（真时钟）：
```
空载无干扰前台    onfinish 289.7ms  vs 兜底 321.4ms  → 胜出 onfinish ✓
轻度主线程抖动 50ms  onfinish 338.2ms（被推迟） vs 兜底 320.1ms → 胜出 fallback ✗
```
根因：声明 280ms 与兜底 320ms 之间**只有 40ms 缓冲**（<2.5 帧）；主线程抖动 35–50ms 就会被兜底抢跑，而 `land()` 里 `getAnimations().forEach(a=>a.cancel())` 一执行，`onfinish` **永远没机会**。
要改：`FALLBACK_MS` 320 → **500**（agy 建议 500 或 600）。声明时长 280ms 与 `cubic-bezier(0.34,1.56,0.64,1)` 保持不动。
自检要求：
- 真时钟空载 → `landedBy === 'onfinish'`
- **造一次抖动**（例如触发时并行跑一段 50–80ms 的主线程负载）→ 仍应 `onfinish`；把负载毫秒数、`onfinish` 时延、兜底到期时刻三个数一起打进结果
- `observedMs` 的口径写清楚（agy 已拆穿它是「兜底 + waitAnim + 硬编码 420ms 等待」的采样点，不是动画时长）—— 要么改成分离字段 `animDurationMs` / `measureSpanMs`，要么在结果里显式标注它是采样跨度

## 纪律
只碰 `canvas-01.html` / `compose-03.html` / 你的 spec；画布源文件零改动（sha256 `e86d4bc56163218d`）；不 commit / 不 push / 不加依赖。
汇报一行：`①setVp 联动后 docClientW/railFlexDir 实测` + `②抖动下 landedBy + onfinish/兜底两个时刻`。
