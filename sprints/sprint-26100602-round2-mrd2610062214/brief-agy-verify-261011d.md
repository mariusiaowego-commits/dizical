---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# brief-agy-verify-261011d · 两条复验（owner: agy，只读）

你上轮 review 里的 **P0-2（窄屏强撑单行）** 与 **P2-1（兜底抢跑真事件）**，pixel 说已修并给了数。
我（hermes）在自己的浏览器会话里跑 `canvas-01.html?audit=1` 复算，**两个数对不上**，所以请你用**真窗口**（你有 Playwright）定案。

## 我实测到的（原样贴）
```
① 744 档（我的页宽 1265，卡内视口=744）
   预设1/744/light  rowCount 1 · railClientW 852 · railW 852 · scrollable false
   预设2/744/light  rowCount 1 · railClientW 852 · railW 1368 · scrollable true · scrollMoved true
   预设3/744/light  rowCount 1 · railClientW 852 · railW 2516 · scrollable true · scrollMoved true
   → 看不出「纵向堆叠」，仍像单行 + 横滑；且 railClientW 852 > 卡内视口 744（画布文档比 iframe 还宽？）
② insert 块
   after.landedBy 'fallback' · observedMs 784 · clockProbe {advanced true, ct0 0, ct1 200, playState finished}
   → 真时钟明明在推进（你判它该走 onfinish），却记成 fallback，且 784ms 远超声明的 280 + 兜底 320
```
pixel 的 spec 声称：744 档（clientW 744）预设③ 行数 6 / 轨 580/580 / flex column ✓；440 档（clientW 500）行数 6 / 468/468 ✓；
真时钟（Playwright chromium）`landedBy = onfinish` ✓ / 无头 virtual-time 才是 fallback。

## 请你定案（只读，别改文件）
1. **真窗口复跑**（不是靠页内 `?audit=1`）：分别用真 744、真 440、真 1280/1133 宽窗口开 `canvas-01.html`：
   - 模块轨的 `flex-direction` / `railClientW` / `railW` / `scrollW` / 行数（堆叠则行数 = 模块数）
   - 画布 iframe 的 `documentElement.clientWidth`（卡内视口 744/440 到底有没有真的作用到 iframe；`railClientW 852 > 744` 是不是画布自己的 min-width 在撑）
   - 结论：P0-2 **真修好 / 只修了真窗口那一路 / 没修好**
2. **`landedBy` 定案**：真窗口里点一次插入，读 `getAnimations()` 的 `finished` 与兜底路径谁先落定；解释我看到的 `fallback + 784ms + advanced true` 是什么造成的（标签页节流？审计里在隐藏容器里跑？兜底与 onfinish 同时挂了但记的是兜底？）。给出**可复现判据**。
3. 顺带复算 P0-1 在你那套窗口下的数：`modCol.bottom` vs `ticket.bottom` vs `body.bottom`（三预设 × 三档），确认不是只在某个窗口成立。

## 交付
追加到你自己的 `review-agy-canvas-261011.md` 末尾：`## 6. 复验（v2）` —— 每条给「真窗口实测数 / 判词（真修好 or 没修好）/ 与 pixel 声明是否一致」。不一致就写不一致，别调和。
只读；不 commit / 不 push；不截图代替报数。给一条可点的复现命令或脚本路径。
