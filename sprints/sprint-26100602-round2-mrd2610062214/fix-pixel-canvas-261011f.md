---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# fix-pixel-canvas-261011f · P2-1 审计仍红（owner: pixel）

我在**普通浏览器会话**里跑你自己交付的 `canvas-01.html?audit=1`（不是 Playwright 脚本），结果：

```
verdict: ASSERT_FAIL · failures 1
P2-1 fail [插入卡槽] 真时钟下真出口应为 onfinish，实测 fallback
        （landedAt 502ms · 兜底到期 500ms · 抖动负载 0ms）
insert.after.landedBy: 'fallback'
```
同时我这条会话里 `clockProbe.advanced === true`（真时钟在推进）、`jitterMs = 0`（没造负载）。
即：**在你新加的那条自洽断言下，我这边真时钟 + 零抖动仍然判红**，而你的 Playwright 跑（空载 290.9 / 抖 60ms 323.6 / 抖 80ms 356.3）全绿。

## 我判断的两个可能（你来定案，别猜）
1. **审计自己的采样时机问题**：`runAudit()` 跑插入测试时，模块列/卡槽/票卡可能不在「已渲染且可见」状态（隐藏容器、离屏、或正被别的组合切换覆盖）→ WAAPI 动画在无渲染上下文时会被推迟甚至不开始 → `onfinish` 永不触发，兜底必然胜出。你的 Playwright 直跑（元素可见）才会 290ms 落定。
2. **真脆性**：兜底 500ms 对重度节流（后台标签页 / 主线程长阻塞）仍不够。

**先测再判**：在这次插入测试的同一时刻，把「元素是否 rendered/visible（offsetParent/checkVisibility）· 动画 playState/currentTime 是否推进 · 动画是否被 cancel」这三个数打进结果，据此区分 1 还是 2。

## 修（按定案结果二选一或都做）
- 若是 1：**把插入测试的采样条件改成「元素确实渲染可见」**（必要时先把该模块列切到可见态再测，测完还原）；断言保留「真出口应为 onfinish」不变。
- 若是 2 或两者兼有：**兜底不能按死时长盲抢** —— 兜底到点时先看动画时钟有没有推进：推进中 → 继续等 `onfinish`（给一个够宽的上限），并**不要 cancel()**（cancel 会让 onfinish 永久失去机会）；时钟冻结 → 才 `land('fallback')`。
- 断言口径写死在结果里（原话）：`clockProbe.advanced === true` ⇒ 必须 `onfinish`；`=== false`（无头冻结）⇒ 允许 `fallback` 并记 `p21Note`。此刻这条断言就是红的根源，修完它必须**在我的普通浏览器会话里也绿**。

## 验收（缺一不算）
1. 普通浏览器会话（不是脚本）打开 `canvas-01.html?audit=1` → `verdict: ASSERT_OK` / `failures: []`，并把当次 JSON 的 `insert` 块原文贴进 spec
2. agy 的 `scripts/verify-real-window-261011.py` 重跑一遍（三档窗口 + direct_race + jitter_race），把它的输出摘要附上
3. 三条窄屏负控 + 加壳 + 待命自循环（132 / 66 / 71 / 1）仍真红不变
4. 若最终结论是「审计环境里注定走兜底」，**不许把它写成绿**：如实标 `SKIPPED` + 原因 + 真窗口实测数

只碰 `canvas-01.html` / 你的 spec；画布 sha256 保持 `e86d4bc56163218d`；不 commit / 不 push / 不加依赖。
