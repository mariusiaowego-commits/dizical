---
source: ai-agent
date: "2026-10-27"
doc_type:
  - handoff
tags: [dizical, practice, demo-v3.9, handoff, s20]
project:
  - dizical
is_done: false
---

# HANDOFF · dizical practice 右栏 demo v3.9（写于 2026-10-27）

    写入人   codex（本线程独立收口）
    工作目录 /Users/mt16/dev/dizical · 分支 feat/practice-ui-iter-260920
    demo 服务 http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html（PID 97410，在线）

---

## 1 · 现在到哪了

```
demo 版本   v3.9（2026-10-27 盖章，24 页徽章 + VERSIONS.md 已重写）
本轮范围     S20 修轮：画布内 fixed 弹层锚到浏览器可视带（换曲目票夹 / 老师要求全文 / 今日记录明细 三层同时修）
commit      本轮改动已 commit 到 feat/practice-ui-iter-260920（版本锚点 commit，未开 PR / 未 merge / 未 push / 未打 tag）
门禁         verify.js --strict 12/12 PASS · sync-demo-templates --check 6 模板字节级一致 · CSS [data-vp] 0 处
待办         dad 肉眼验收 v3.9（见 §5）
```

## 2 · dad 报的现象与根因

**现象（dad 261027 截图）**：点票夹右上角「换曲目」→ 只出一片灰色蒙版，弹窗本体不见。

**根因**：画布 iframe 的高度 = 票卡带自然高（组合 3 = 3348px），而 iframe 内 `position: fixed` 的包含块是**整篇画布文档**（不是浏览器视口）。
`.pk-folio-modal { position:fixed; inset:0; display:flex; align-items:center }` 于是把弹窗居中到文档 y≈1673 处，
而浏览器视口只有 0–922 → 弹窗完全落在屏幕外；遮罩 `inset:0` 却铺满 3348px 画布 → 用户只看到一片灰。

**修复前实测（`/private/tmp/probe-s36-folio3.js`，744 档 + 组合 3）**：

```
outerViewportH: 922, frameTopInViewport: 167, frameH: 3348
.pk-folio-box  pageTop/pageBottom = 1531 / 2151     ← 完全在视口之外
```

## 3 · 怎么修的（画布源零改动）

**思路**：不改「画布自然底 + 画布 iframe 撑高」这个核心设计（dad 多次要求保留），而是让画布内的 fixed 弹层**以浏览器当前可视的那一截为参照**。

- `canvas-01.html:19353-19370` `canvasBand()` / `syncCanvasBand()`：算浏览器当前看得见的那一截（画布文档坐标）
  `top = max(0, -iframe.top)`、`bottom = min(画布高, innerHeight - iframe.top)`，写进画布文档根节点的
  `--cz-band-t` / `--cz-band-h` 两个 CSS 变量。
- `canvas-01.html:17216-17228`（注入画布文档的 `__CZ_CSS`）：
  - `.pk-folio-modal, .pk-overlay, .popout-backdrop, .cz-pop-mask { top: var(--cz-band-t); height: var(--cz-band-h); bottom: auto }`
    → 遮罩只压住可见区，弹层在可见带内居中。
  - `.pk-folio-box` 高 = `min(620px, 可视带高 − 40px)`；`.pk-reader` / `.popout-panel` 的 `max-height` 同样按可视带收口。
  - `.popout-panel` 垂直中心 = `var(--cz-band-t) + var(--cz-band-h)/2`（宽档原先是 50%/50% 居中到画布中段 → 屏幕外）。
- 刷新时机：`injectCanvas()`（`canvas-01.html:18909`）、`syncCanvasHeight()`（`19341`）、`resize`（`19748`）、
  `scroll`（`19750`，passive）、画布 iframe `load`（`19760`）。
- 窄档 `.popout-panel` 的 inline 定位（`placePopout()`，既有逻辑）保持不变，优先级更高，不受影响。

**画布源 `practice-ticket-v4-260920.html` 仍是零改动**（改动全在宿主 `canvas-01.html` 的注入层 + `__CZ_CSS`）。

## 4 · 实测证据

**修复后（`/private/tmp/probe-s39-band.js`，3 视口 × 3 组合 × 3 弹层 = 27 项，全 PASS）**

| 视口 | 组合 | 换曲目票夹 (page t~b) | 老师要求全文 | 记录明细 | 遮罩带 (page t~b) |
|---|---|---|---|---|---|
| 1133 | 1/2/3 | 207.5~827.5 | 411~624 | 207.5~827.5 | 113~922 |
| 744 | 1/2/3 | 234.5~854.5 | 422.3~666.8 | 175~914 | 167~922 |
| 440 | 1/2/3 | 277~897 | 449~725 | 260~914 | 252~922 |

- 修复前 744+组合3 的票夹弹窗在 `1531~2151`（不可见）；修复后同条件 `234.5~854.5`，**完全落在 922 高视口内**。
- 遮罩由「铺满 3348px 画布」变为「只压可见带」（1133 档 113~922）。

**截图**：`/private/tmp/s39-744-c3-folio.png`、`/private/tmp/s39-440-c3-folio.png`、`/private/tmp/s39-1133-c2-pop.png`

## 5 · 门禁证据

```
python3 tools/sync-demo-templates.py --check  → PASS（6 模板字节级一致）
python3 tools/check-layout-modes.py          → PASS（CSS [data-vp] 0 处）
node tools/verify.js --strict                → 12/12 PASS
  新增项 12：画布内 fixed 弹层落在浏览器视口内（换曲目/老师要求全文/记录明细 × 9 组合）✅ 27/27 可见
  1–11 项全部维持 PASS（重叠 0px² · 露出 19.8–20.1% · 条字重叠 0 · 记录明细 12 条 · 退场空窗 0 · 三心合一 R=78/64+14）
```

**新增回归断言**：`tools/verify.js:440-508`（项 12，`overlayViewport`），`--strict` 与非 strict 两条出口都纳入判定。

## 6 · 待办与红线

- **待办**：dad 肉眼验收 v3.9 → `http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html`
  （重点：组合 3 + 744/440 档点「换曲目」；老师要求全文；今日记录明细）。
- **遗留 P1（未处理，等 dad 拍板）**：外层 `#czPresets` 在 541–660px 宽度区间溢出。
- **红线**：权威源唯一 `cards/card-*.html` + `sync-demo-templates.py`；CSS 禁 `[data-vp]`；
  画布源 `practice-ticket-v4-260920.html` 零改动；探针与截图统一放 `/private/tmp`；不 push / 不开 PR / 不 merge / 不打 tag（除 dad 明确要求）。
