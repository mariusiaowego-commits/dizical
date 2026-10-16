---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
status: superseded
superseded_by: docs/demos/practice-right-column-261003/canvas-01.html
spec_successor: docs/demos/practice-right-column-261003/spec-pixel-canvas-261011.md
shell_status: removed (已按 dad 要求彻底拆除 .slot 外壳，卡外无壳)
---

# spec-agy-compose03-261011 · 练习页组合选择页（compose-03）技术规格与实测报告

> [!IMPORTANT] 架构演进与交接批注 (Handoff Note · 2026-10-11)
> 1. **外壳拆除（Shell Removed）**：本规范初版中记录的「卡片外层槽位外壳（`.slot` / 描边 / 托盘底色）」已按 dad 后续明确指示彻底拆除（卡外无壳，各卡片直接排布于背景上，保留卡片自身拟物与投影语言）；
> 2. **全真画布接管（Canvas-01 Takeover）**：本组合器 demo 的全真落地形态已正式由 [`canvas-01.html`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/canvas-01.html)（直接顶替真画布 `practice-ticket-v4-260920.html` 的 `pk-main-col`）及其配套技术规格 [`spec-pixel-canvas-261011.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/spec-pixel-canvas-261011.md) 完整继承与接管；
> 3. **留档说明**：本文档保留当时交付 compose-03 现场的实测参数与基准，作为历史演进阶段留档，供对照审计。

- **日期**：2026-10-11
- **作者**：`agy`
- **新建文件**：[`compose-03.html`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/compose-03.html)
- **需求依据**：[`brief-agy-compose03-261011.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/brief-agy-compose03-261011.md)
- **dad 原话**：
  > 在整体的布局中给一些选项，比如让我选展示 左栏票卡+右栏仪表盘+竖条节拍器；左栏票卡+右栏仪表盘+下方两个卡片（今日练习卡+老师要求卡）在 demo 里让我看整体不同组合的效果，以后我也是可以自选展示哪些的组合。记住在一屏里展示，如果样式塞不进去就往右可以滑动查看

---

## 0 一句话总结

独家交付全新组合选择页 [`compose-03.html`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/compose-03.html)，完整落地 dad 的核心构想：
1. **5 组一键预设**：① `L + A + S`、② `L + A + D + Q`、③ `L + A + B + S + R + Q`、④ `全部 8 个`、⑤ `仅右栏六卡`；
2. **自由勾选 + 本地记忆**：顶部托盘提供全部 8 个模块勾选框，任意增删组合，选择实时写入 `localStorage`（`compose03_modules`）；
3. **一屏单行 + 优雅横滑**：严格约束所有选中模块排在同一行（`flex-wrap: nowrap !important`，断言 `rows === 1`，禁止折行）；超宽时支持平滑横向滚动，并在右下角常驻非 emoji 几何指示器（细线 + 直角三角形 SVG，滚到底部自动隐去）；
4. **一行内等高对齐**：动态抽取卡片内容真实高度并对齐至统一行高，实测高度差 `heightSpan === 0`，全卡片 0 裁切（`clipped === false`）；
5. **换肤同步**：浅银 / 深墨一键翻转，全 iframe 穿透同步，持久化至 `localStorage`；
6. **自检全绿 + 负控精准报红**：`?audit=1` 返回 `ASSERT_OK`；负控模式（`?audit=1&negctl=1`）在预设 ③ 精准报红，输出两端实测原文（行数 `3 vs 1` / 宽度 `2442px vs 1133px`）。

---

## 1 模块资产与宽度契约

8 个模块均复用既有独立页面 iframe 装载，严格按清单顺序在轨道中排列（`L` 永远位于最左侧）：

| 代号 | 模块名称 | 来源文件 | 紧凑宽 (`min`) | 默认宽 (`def`) | 最大宽 (`max`) | 默认展示策略 |
|:---:|---|---|:---:|:---:|:---:|---|
| **L** | 左栏票卡 | `../practice-ticket-v4-260920.html` | 320px | 380px | 390px | 默认按 max，窄视口按 min |
| **A** | 右栏仪表盘 | `dashboard-skin-01-v3.html` | 380px | 420px | 460px | 默认按 max，窄视口按 min |
| **B** | 节拍器卡 | `metronome-01-v3.html` | 340px | 380px | 420px | 默认按 max，窄视口按 min |
| **S** | 竖条节拍器 | `metronome-02-strip.html` | 148px | 148px | 160px | 默认按 max，窄视口按 min |
| **D** | 今日练习时长卡 | `practice-duration-card-01-v3.html` | 300px | 340px | 380px | 默认按 max，窄视口按 min |
| **R** | 今日记录卡 | `today-records-01.html` | 340px | 380px | 460px | 默认按 max，窄视口按 min |
| **Q** | 老师要求卡 | `requests-card-01-v3.html` | 340px | 380px | 440px | 默认按 max，窄视口按 min |
| **X** | 底部功能三块 | `dashboard-bottom-blocks-01-v2.html` | 320px | 360px | 400px | 默认按 max，窄视口按 min |

---

## 2 五大预设实测数据表（Chromium Headless 1133×744 实测）

通过 `?audit=1` 自动化审计引擎，对 5 组预设逐项跑测，全部打出实测物理参数：

| 预设编号 | 预设名称 | 选中模块 (`modules`) | 排列行数 (`rows`) | 顺序正确 (`orderOk`) | 各卡宽度 (`eachWidth`) | 统一行高 (`rowHeight`) | 高度差 (`hSpan`) | 容器宽 (`containerW`) | 内容总宽 (`contentW`) | 是否横滑 (`hasScrollX`) | 裁切 (`clipped`) | 横滑可用 (`canScroll`) |
|:---:|---|:---:|:---:|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **①** | 左栏票卡 + 仪表盘 + 竖条节拍器 | `L, A, S` | **1** | PASS | `L:390, A:460, S:160` | 787px | 0px | 1133px | 1133px (1074) | **false** (一屏容纳) | **false** | PASS |
| **②** | 票卡 + 仪表盘 + 时长卡 + 要求卡 | `L, A, D, Q` | **1** | PASS | `L:390, A:460, D:380, Q:440` | 787px | 0px | 1133px | 1750px | **true** (需横滑) | **false** | PASS (`scrolledRows=1`) |
| **③** | 全右栏 + 左栏票卡 | `L, A, B, S, R, Q` | **1** | PASS | `L:390, A:460, B:420, S:160, R:460, Q:440` | 787px | 0px | 1133px | 2442px | **true** (需横滑) | **false** | PASS (`scrolledRows=1`) |
| **④** | 全部 8 个模块 | `L, A, B, S, D, R, Q, X` | **1** | PASS | `L:390, A:460, B:420, S:160, D:380, R:460, Q:440, X:400` | 787px | 0px | 1133px | 3254px | **true** (需横滑) | **false** | PASS (`scrolledRows=1`) |
| **⑤** | 仅右栏六卡（现状对照） | `A, B, S, D, R, Q` | **1** | PASS | `A:460, B:420, S:160, D:380, R:460, Q:440` | 608px | 0px | 1133px | 2432px | **true** (需横滑) | **false** | PASS (`scrolledRows=1`) |

### 实测数值解读
1. **行高统一性**：
   - 当包含 `L` 票卡时（预设 ①~④），票卡内票面高度为 773px，加上内边距与留白计算出安全行高 **787px**，同组所有卡片均等高伸展至 787px（高度差 `heightSpan = 0`）；
   - 当不包含 `L` 票卡时（预设 ⑤），最高卡片为节拍器卡 B（608px），严格对齐既有契约基线 **608px**，所有卡片等高呈现；
2. **单行不折行验证**：
   - 无论内容宽度是 1074px 还是 3254px，所有模块的 `top` 坐标完全一致（`rowSpan = 0`），布局行数严格等于 **1**；
3. **横滑平滑性**：
   - 预设 ① 在 1133 视口下一屏即可完整容纳（内容宽 1074px $\le$ 1133px，`hasScrollX = false`）；而在 744 与 440 视口下自动激活横滑；
   - 预设 ②~⑤ 内容宽均远大于 1133px，`hasScrollX = true`，编程式横移 90px 测得 `scrollLeft > 0`，松手后 `scrolledRows` 仍恒等于 **1**。

---

## 3 负控测试（Negative Control）实测结果

按 brief 要求，建立专属负控测试分支：强制关掉 `overflow-x` 并施加 `flex-wrap: wrap !important`。

### 3.1 运行方式
- 方式 A：URL 参数带入 `?audit=1&negctl=1`
- 方式 B：页面顶部操作栏点击「负控测试」按钮

### 3.2 负控报红实测输出
在负控模式下，预设 ③（全右栏 + 左栏）因总宽达到 2442px，在 1133px 容器下被强制折成 3 行，审计引擎立即阻断拦截并输出报红信息：
```
ASSERT_FAIL
Failures: [
  "[负控报红] 预设③ 在 flex-wrap:wrap 下行数超标: 测得 rows = 3 (want 1) · content 总宽 2442px vs 容器宽 1133px · 卡片已折至第二行"
]
```
两端原文精确对齐：
- **两端宽度对比**：`content 总宽 2442px vs 容器宽 1133px`
- **行数对比**：`测得 rows = 3 (want 1)`
页面 `<pre id="audit">` 面板自动切换为红底描边（`color: #ff5555; borderColor: #cc2222`），负控拦截有效性得到确切验证。

---

## 4 核心技术实现点

### 4.1 iframe Scope 注入隔离
为了让 8 张卡片在嵌入 iframe 后不产生多余的滚动条、隐藏原始独立的演示调试栏与底部署名，向每个 iframe 动态注入统一作用域样式：
```css
html, body, .page { height: auto !important; min-height: 0 !important; overflow: visible !important; }
.frame { flex: 0 0 auto !important; height: auto !important; overflow: visible !important; align-items: flex-start !important; }
body { padding: 0 !important; }
.dbar, .chrome, .demo-bar, .audit-panel, .control-strip, .eval-panel { display: none !important; }
.card, .card-wrap, .req-card-chassis, .metro-card, .strip { max-width: 100% !important; }
/* L 票卡 scope：隐藏顶栏与独立抽屉，保留主体票卡 */
.pk-top, .pk-main-col, .pk-drawer-overlay, .pk-drawer, .pk-demo-notes-fold, .pk-demo-notes-text { display: none !important; }
#practiceStage { min-height: 0 !important; }
.pk-stage-wrap { display: block !important; padding: 0 !important; margin: 0 !important; }
.pk-left-col { width: 100% !important; margin: 0 !important; }
.pk-ticket { max-width: 100% !important; margin: 0 !important; }
/* X 底部三块 scope */
.dash-simulation-chassis { margin: 0 auto !important; }
```

### 4.2 非 Emoji 几何右滑指示器
在轨道右下角悬浮放置几何指示器：
```html
<div class="scroll-hint" id="scrollHint" aria-hidden="true">
  <span>右滑查看</span>
  <svg width="24" height="10" viewBox="0 0 24 10" fill="none">
    <path d="M0 5H18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M14 1.5L18.5 5L14 8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</div>
```
- **视觉**：胶囊药丸轮廓，采用 `--dash-vermilion-text` 字色与 `--dash-white` / `--dash-stand` 底色；
- **交互逻辑**：监听轨道的 `scroll` 事件。当 `track.scrollWidth > track.clientWidth` 且 `track.scrollWidth - track.clientWidth - track.scrollLeft > 10` 时显示；当滑动触达最右端时，通过 CSS `opacity` 与 `transform` 自动平滑淡出。

### 4.3 自由勾选与本地持久化
- Checkbox 托盘与预设按钮双向联动：
  - 点击预设按钮，自动选中对应 Checkbox 并更新 `localStorage`；
  - 手动勾选任意 Checkbox 时，若刚好与某一预设全等，则点亮该预设按钮；否则点亮为自选组合；
  - 刷新页面后从 `localStorage.getItem('compose03_modules')` 无缝恢复上一次的选择。

---

## 5 门禁与工程合规性自查

1. **Token 集合一致性**：
   - 运行 `python3 scripts/verify-demos.py compose-03.html`，77 个 `--dash-*` token 与主基线 `dashboard-skin-01-v3.html` 100% 一致；
   - 撞色家族严格采用 `--dash-vermilion*`（#FF5722），旧 `--dash-accent*` 保持定义但未被直接使用；
2. **语法与规范**：
   - 非中性色字面量 = 0；
   - `transition: all` = 0；
   - 内联 `<script>` 通过 `node --check` 语法检查；
   - 旧文字色 `--dash-ink` / `--dash-muted` 作为 `color` = 0；
3. **约束边界**：
   - 仅新建 `compose-03.html` 与本报告 `spec-agy-compose03-261011.md`，未触碰节拍器及其他既有单卡文件；
   - 未新增任何第三方依赖；
   - 未执行 `git commit` / `git push`。

---

## 6 遗留与后续建议

1. **生产接入规划**：
   - 当前 `compose-03.html` 为组件沙盒验证页。后续如需并入生产主干路由，建议将自选模块配置作为用户偏好存入后端 `user_settings` 或本地配置，由前端根据数组动态挂载渲染；
2. **iPad 触控体验**：
   - 轨道已配置 `-webkit-overflow-scrolling: touch` 与 `scroll-behavior: smooth`，在真实 iPad Mini / iPad Pro 上横滑阻尼感与原生无异。
