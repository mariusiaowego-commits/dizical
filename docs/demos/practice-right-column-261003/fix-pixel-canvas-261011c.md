# fix-pixel-canvas-261011c · 按 agy review 修缮（owner: pixel）

依据：`docs/demos/practice-right-column-261003/review-agy-canvas-261011.md`（agy 交，25KB，2026-10-11）
dad 口径：这 6 点**由 agy 判定**，你按判决实施；不另开判断，不要改动判决内容。
目标：修完自跑审计，把红条数 → 0 的原文贴出来。

## 必做（按 review 的 P0/P1/P2 逐条落）

### P0-1 模块列高击穿画布底线（agy 实测：模块列 717 / 736 / 750px vs 票卡与 wrapper 654px，溢出 61–96px）
- `.cz-insert` 现在占 102px（82px 舞台 + 上下 padding）→ 压缩冗余上下 padding
- 给 `.cz-rail` 加 `max-height` 约束，令 **`.cz-insert` + `.cz-rail` + gap ≤ 票卡高（实测 654px）**；超出部分在轨内纵向/横向自理，不许把卡片顶出画布底边
- 断言（写实测值）：三预设各自 `modCol.bottom ≤ ticket.bottom`，并把两者的 bottom 实测数打进结果

### P0-2 窄屏强撑单行横滑（440/744 档：画布已纵向堆叠，轨却死守 2516px 单行）
- 追加 `@media (max-width: 1023px) { .cz-rail { flex-direction: column; align-items: stretch; overflow-x: visible; } }`（agy 指定值）
- **改断言口径**：`A1 单行` 只在 `docClientW ≥ 1024` 时断言 `rowCount === 1`；`< 1024` 豁免单行，改断言「纵向堆叠且无横向溢出」（`scrollW === clientW`）
- 严禁用 `transform: scale()` 凑一屏（agy 已否，理由：亚像素模糊 + 点击坐标错位）

### P1-1 插卡触发与画布状态机脱节（agy 实测：点插卡 → Card A 走字，但左侧真实票卡仍 380px 待命态，两边撕裂）
- `runInsert()` 落定回调里调 `canvasDoc().defaultView.enterRun()`；若画布内容标签未选（`content === ""`）先兜底取 `cur.content_options[0]`
- 监听画布内 `#pkStateToggle`：切练习态 → 联动 `runInsert()`；切回准备态 → 联动 `resetInsert()`
- Card A 暂停/结束时向父级广播，同步顶栏文案

### P1-2 深墨换肤割裂（画布无 ink 皮肤 → 黑块浮在米白纸上）
- **不许改画布源文件**（sha256 `e86d4bc56163218d` 必须保持）
- 走运行时注入：在 `CANVAS_SCOPE` 里追加 `:root[data-skin="ink"]` 对 `#practiceStage`（底色 `#14181C`）/ `.pk-ticket`（`#1E242B` + 文字 `#FFF8F0`）/ `.pk-top`（`#1A1E22`）的覆盖；`setSkin()` 里同步给 `canvasDoc().documentElement` 挂/摘 `data-skin="ink"`
- 断言改写：`C1 皮肤同翻` 现在只查 iframe 内属性（agy 判「验了等于没验」）→ 改成**实测画布 `#practiceStage` 与 `.pk-ticket` 的 computedStyle 背景色**在浅银/深墨两态下不同（贴两组 rgb 原文）

### P2-1 兜底计时器误伤真事件（agy 实测：Chromium WAAPI `onfinish` 在 287ms 触发，被 `setTimeout(280)` 抢跑）
- 兜底改 `setTimeout(..., 320)`；**声明时长 280ms 与 `cubic-bezier(0.34,1.56,0.64,1)` 保持不动**
- 断言里如实记录 `landedBy`（真出口应是 `onfinish`，不再是 `fallback`）

### P2-2 多卡并排高度不一 → 矮卡底部留白空洞
- 按 review §2 P2-2 的改法处理；若 review 未给具体数值，就给一条明确规则（例如轨内 `align-items: flex-start` + 每卡自撑高，或统一拉伸），并写进 spec 说明选了哪条、为什么

## 纪律
- 只碰 `canvas-01.html` / `compose-03.html` / 你的 spec；画布源文件零改动
- 不 commit / 不 push / 不加依赖；配色只走 `--dash-*`
- 保留上轮已绿的全部断言（挂载链命中 pk-main-col / 无壳 / 真横滑容器 / 脚手架已隐 / E1 票卡分档 / E2 基线公式自洽）
- 自跑：3 视口（1133 / 744 / 440）× 4 预设 × 2 皮肤 + 三条负控（加壳 / 待命自循环 / 单行断言在 440 档），把 `verdict` 与 `failures` **原文**贴进 spec
- 汇报一行：`红 <n> → <m>` + P0-1 的 `modCol.bottom` vs `ticket.bottom` 实测 + 插入动画 `landedBy` 实测
