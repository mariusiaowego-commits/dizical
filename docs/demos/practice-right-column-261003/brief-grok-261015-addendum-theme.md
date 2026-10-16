# brief-grok-261015-增补 · 画布缺 `data-theme="dizicute"`（item 2 根因，已现场验证修法）

dad item 2.1 原话：「和 practice-ticket-v4-260920.html 中的差距还有，主要是可撕虚线（pk-perforation-line），
原来 ticket-v4 的样式和你这次展示的不同，**左右虚线都超过半圆了**」→ 我查到了确切根因（不用 agy/grok 查了），
并且**在真会话里把修法验过**，你照做即可。

## 根因（实测）
```
两边 CSS 与 markup 逐字相同：
  .pk-perf-notch-left/right { background: var(--surface-page); ... }   ← 半圆咬口用"页面底色"挖掉虚线两端
源 ticket-v4：票卡 6→386 / 虚线 7→385 / 咬口 l6 w11（6–17）与 375–386 正好盖住虚线两端 → 观感正确
canvas-01  ：票卡 6→366 / 虚线 7→365 / 咬口位置一样，但 **computed background = rgba(0,0,0,0)（透明）**
             → 咬口不生效 → 虚线两端露出来 → 就是 dad 说的"超过半圆"

为什么透明：
  --surface-page: var(--c-tertiary)  只定义在 [data-theme="dizicute"] 选择器里
  源页面 <html lang="zh-CN" data-theme="dizicute"> 带着这个属性
  canvas-01 构造 srcdoc 时用的是自拼 head：
     canvasIframe.srcdoc = '<!DOCTYPE html><head><base ...><meta charset></head>' + t...
  → 画布原本的 <html data-theme="dizicute"> 落不到 iframe 文档上 ⇒ iframe 内 documentElement 没有 data-theme
  ⇒ 实测：canvas 文档里 [data-theme="dizicute"] 定义的 **61 个 token 全部为空**
     （--surface-page / --surface-card / --text-main / --border-card / --shadow-card / --pk-req-* …）
     凡是 var() 没写 fallback 的地方一律失效（背景透明 / 无阴影 / 无边框色）→ 这就是"差距还有"的整类根因
```

## 修法（我已现场验证有效，选一个）
```
方案 A（最小、推荐）：画布 iframe 文档就绪后补属性
  canvasIframe.addEventListener('load', () => { canvasIframe.contentDocument.documentElement.setAttribute('data-theme','dizicute'); ... })
  或在既有"运行时把模块列挂进 pk-main-col"的那段里一起做（同一处，别再加一段 listener）

方案 B：把 <html lang="zh-CN" data-theme="dizicute"> 原样保留进 srcdoc（拼 head 时别把画布开标签吃掉）

现场验证（我做的，方案 A 等价动作）：
  before: themeAttr null | notchBg rgba(0,0,0,0) | --surface-page ""（空）
  setAttribute('data-theme','dizicute') 后：
  after : themeAttr dizicute | notchBg **rgb(255,248,240)** | --surface-page #FFF8F0 | --surface-card #FFFFFF | --text-main #2C3E50 | --shadow-card 0 1px 3px …
  ⇒ 咬口恢复、虚线不再超过半圆
```

## 要你做的
```
1 落修法（A 或 B），并确认 title/其它依赖 data-theme 的东西不受影响
2 自检（真会话）：
   ① canvas 文档 documentElement.getAttribute('data-theme') === 'dizicute'
   ② .pk-perf-notch-left/right 的 computed backgroundColor === rgb(255,248,240)（不再 transparent）
   ③ [data-theme="dizicute"] 里定义的 token 缺失数 = 0（我在台上也会复算）
   ④ 虚线两端与咬口关系：虚线左端(7) 落在左咬口(6–17) 内、右端落在右咬口内（按源票卡同款相对关系）
3 顺带自查：这 61 个 token 回来后，别的地方有没有因此改变观感（尤其 D/R/Q/S 卡与组合布局）——
   有变化要在汇报里列出来（这是"恢复应有样式"，但要让人知道差异面）
```
红线不变：只改 canvas-01.html；画布本体零改动；不 commit / 不 push / 不加依赖。
