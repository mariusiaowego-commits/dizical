---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# brief-agy-review-canvas-261011 · canvas-01 独立 review（owner: agy，只读）

对象：`docs/demos/practice-right-column-261003/canvas-01.html`（638,679 B）
配套：`spec-pixel-canvas-261011.md`（50 KB，pixel 自述）
定位：**reference review（第二路）**。hermes 已上过台复算，但你不要看我的结论、也不要抄 pixel 的 spec —— 自己开页面、自己量、自己判。

## 背景（够你上手的最小上下文）
画布本体 = `docs/demos/practice-ticket-v4-260920.html`（dad 认的「真画布」，**本轮必须零改动**，sha256 前 16 位 `e86d4bc56163218d`）。
dad 本轮口径：
> 这块不要的，这里就是右栏，右栏就是我这次做了 demo 1.0-3.0 一路修改要替换的位置（pk-main-col）
> demo3.0 的仪表盘上面额外做一个插入卡槽的动画效果，整体替代我刚截图的位置（pk-main-col）

即：`pk-main-col`（原：入卡槽说明行 / 计时大框 / 「检票 · 开始练习」/ 老师要求板块）**整块被右栏模块顶替**，且在仪表盘上方加「插入卡槽」动画。
pixel 的做法：`canvas-01.html` 用 `srcdoc` 把画布逐字搬进 iframe，运行时把模块列（`.cz-mod-col` → `#czRail.cz-rail`）挂进 `pk-main-col`，画布外一根组合开关细条（4 预设 + 6 卡勾选 + 视口 + 皮肤）。

## 你要查的（每条都要实测数据，不许只读代码下结论）
1. **顶替是否干净**：`pk-main-col` 里原块（`#pkInstrCard` / `#pkReqCard` / `#pkSlotIdle` / `#pkStartBtn` / `.timer-block` / `.pk-slot4-box` / `.pk-running-telemetry`）是否真的都没了；**有没有残留的不可见死节点或事件绑定**。
2. **画布自身的脚本有没有被拆坏（重点）**：原「检票 · 开始练习」按钮与计时逻辑被移除后，画布自己的 JS 有没有报错 / 空引用 / 静默失效。开 `canvas-01.html` 抓 console（`error` / `warn`），并点一遍画布上**仍在的**控件（票夹 / 加减 / 切到练习态 / 今日记录抽屉），看有没有崩。
3. **插入卡槽动画**：
   - 待命态是否**真静止**（`getAnimations()` 计数 + 两次采样 transform + 声明的 `animation-name`）
   - 触发后是否**几何相交**、仪表盘是否真换态、时长与缓动是否符合 brief（`back.out` 量级、≤320ms）
   - 用**真浏览器时钟**再测一次时长（pixel 报的是无头 `fallback` 路径的 observedMs，你要判它在真时钟下的表现；如果只能无头，就如实标 SKIPPED 并写原因）
4. **顶替后的观感一致性问题**（你比我更该看出）：模块列与票卡并排时，**两列的语言是否打架**（圆角/描边/间距/字号基线/换肤）；模块列高低不齐、`pk-main-col` 高度由谁决定、会不会把画布拉高或压扁。
5. **模块列内部横滑**：是否只在真滚动容器上（`overflow-x: auto` 且 `scrollW > clientW`），三次采样能不能滚；444/440 窄档会不会反而该堆叠却不堆叠。
6. **断言是否真咬人**：挑 2 条 pixel 的断言（建议 H1/H2 + B1），把实现改坏（或关掉触发、加回壳），确认**真报红且红行含两端原文**；跑完改回来。不许只信它的 `verdict: ASSERT_OK`。
7. **它 spec 里有没有「验了等于没验」的软检查项**（`ok` 恒真 / 只读类名 / 用元素盒子相交代替像素级判定）。

## 交付
`docs/demos/practice-right-column-261003/review-agy-canvas-261011.md`：
- 一段结论（可以 / 不可以进 demo 交付）
- `P0 / P1 / P2` 清单，每条 = 现象 + 实测数据 + 复现步骤 + 建议改法（**不许只给观点**）
- 明确写「我复算了 pixel 的哪几条、哪几条我不同意」——**不同意要给自己的数**
- 你**不许**改 `canvas-01.html` / 画布本体；只读 + 出报告。发现的问题归口 hermes 统一派修。

## 纪律
只读，不 commit / 不 push；不开新 agent；不用浏览器截图替我判断视觉（报数即可）。
