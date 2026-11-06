# `/practice-dsh` MRD 3.2.5 架构设计文档（ARCH-MRD325）

> **状态**：Segment A 架构设计产出（待用户拍板 §4 三个交互方案后进入 Segment B–F 实现）
> **基线提交**：`769ae65`（`DSH_VERSION = "20260417c"`，`src/kid_app/app.py:42`）
> **目标源码**：`src/kid_app/templates/practice-dsh.html`、`src/kid_app/app.py`
> **关联规范**：`docs/practice-dsh/DESIGN.md`（§1–§11 既有规范及 §10 八条红线）

---

## 0. 变更总览与 Sprint 编号索引（V1–V4 / C1–C24 / §2.3.2.1）

本文档完整覆盖 MRD 3.2.5 的 24 项编号需求与 `mic-status-btn` vs `diag-status` 架构判定，按四大核心章节组织：

| 章节 | 覆盖编号 | 对应后续实现分段 | 核心架构目标 |
|---|---|---|---|
| **§1 多视口固定布局** | `V1`、`V2`、`V3`、`V4` | Segment E | 确立 `pc-layout` / `ipad-h` / `ipad-s` / `phone-layout` 4 档视口体系与既有 `data-vp="1133\|744\|440"` + `COMBO_SCHEMA` 的双层映射关系；宽>高单屏 ≤2 卡 + 底部聚光灯换屏；高>宽纵向等宽瀑布流 |
| **§2 卡槽 3 态状态机** | `C10`、`C11`、`C12`、`C13`、`C14`、`C15` | Segment C | 确立选择态（`select`）/ 准备态（`prep`，含计时暂停）/ 计时态（`run`）三态迁移表、槽口下移与露出高度几何公式、上拔露出前 3 个 session 标签微交互与插入锁定 |
| **§3 票夹瘦身与元素归属表** | `C1`–`C9`、`C17`–`C24`、`§2.3.2.1` | Segment B / D / F | 完整定义 `pk-ticket` 瘦身后的去向、全屏今日记录弹窗、Dashboard 浅色 `dizicute` 主题化、双扬声器对称布局、`mic-status-btn` 与 `diag-status` 合一方案及前后端边界 |
| **§4 三个待拍板交互方案** | `C7`、`C16`、`C19`（联动 `C18`） | Segment C / D | 提供科目累计练习记录 pop-out（`C7`+`C18`）、换科目卡片动画（`C16`）、音符节奏与 BPM 全局小弹窗（`C19`）的精确尺寸、时序、缓动曲线与跨 iframe 通信协议 |

---

## 1. 多视口固定布局（V1–V4）

### 1.1 现状锚点与核心矛盾

1. **外层视口落档函数**：`applyCanvasViewport()`（`src/kid_app/templates/practice-dsh.html:23148-23163`）目前仅按宽度和纵横比写入 `state.vp = '1133' | '744' | '440'`（定义于 `:19176`），并在 `applyModuleState()`（`:22792-22793`）把 `data-vp` 写入 `#canvasBody` 及单卡预览容器。
2. **卡内组件耦合**：6 张卡片内联模板（`tpl-A`、`:10540` `tpl-B`、`:12582` `tpl-D`、`:13878` `tpl-S`、`:15892` `tpl-Q`、`:16622` `tpl-R`）大量使用 `body[data-vp="440"]` 与 `body[data-vp="744"]` 选择器控制卡内字号、内边距和栅格列数，并由 `broadcast()`（`:23539`）把 `vp: state.vp` 广播到各卡片 iframe。
3. **Combo 宽度契约**：`COMBO_SCHEMA`（`:19066-19126`）目前以 `1133` 为画布设计宽度基准（`designW: 1133 | 1244 | 1332`），且 `fitWideCombo()`（`:21315-21349`）在桌面横屏下会把 3 卡组合（如 Combo 3 `ASR`、Combo 4 `AST`、Combo 5 `ABQT`）横向压缩塞入同一屏，违反 `V2`「单屏最多呈现 2 张卡片」。
4. **流式瀑布判定**：`canvasIsFeed()`（`:22619-22625`）目前硬编码 `window.matchMedia('(max-width: 1023px)').matches`，未能严格按 `宽 > 高` vs `高 > 宽` 区分 `ipad-h` 与 `ipad-s`。

### 1.2 架构裁决：4 档布局类与 `data-vp` / `COMBO_SCHEMA` 双层共存映射

**明确结论**：采用**「外层 4 档语义布局类（Layout Tier）主导排布 + 底层 `data-vp`（Component Size Token）确定性派生 + `COMBO_SCHEMA` 保留组卡定义但剥离超 2 卡同屏挤压」**的双层共存架构，既满足 MRD 3.2.5 四视口固定样式，又零破坏 6 张卡片内联 CSS 的 `[data-vp]` 选择器与 `DESIGN.md §10.4` 宽度契约。

* **第一层（外层布局档位 `state.layoutTier`）**：在 `document.body`、`#canvasArea`（`:19136`）及 `#canvasBody`（`:4781`）上同步设置类名 `.pc-layout | .ipad-h | .ipad-s | .phone-layout` 与属性 `data-layout-tier="pc-layout|ipad-h|ipad-s|phone-layout"`。
* **第二层（卡内尺寸档位 `state.vp`）**：由 `state.layoutTier` 确定性映射生成 `state.vp`（`pc-layout` → `'1133'`，`ipad-h` → `'1133'`，`ipad-s` → `'744'`，`phone-layout` → `'440'`），继续通过 `broadcast()`（`:23539`）下发给子卡 iframe。

### 1.3 四档视口完整规格表（V1 / V2 / V4）

| 档位类名 (`data-layout-tier`) | 派生 `data-vp` | 设计基准尺寸 (`designW × designH`) | 精确 `@media` 触发条件（CSS 与 `applyCanvasViewport` 同源） | 宽高关系与滚动模式 | 单屏卡片上限 | 卡槽舞台宽度 (`--cz-a-w`) 与关键样式差异 |
|---|---|---|---|---|---|---|
| **`pc-layout`** | `'1133'` | `1440px × 900px`（兼容 MBP 16 `1728×1117`；Combo 舞台基准宽 `1133px`） | `@media (orientation: landscape) and (min-width: 1180px)` | **宽 > 高**（横向分页卡带模式，`overflow-x: auto; scroll-snap-type: x mandatory`） | **≤ 2 张顶层卡片/屏**（超出卡片流入第 2 屏，底部显示进度聚光灯 `V3`） | `--cz-a-w: 440px`（`COMBO_SCHEMA[2]` 为 `520px`）；舞台两侧留白充裕，`.cz-stage-wrap` 最大宽度 `1280px`，卡片间距 `gap: 16px`，底部 `.cz-spotlight-bar` 高度 `36px` |
| **`ipad-h`** | `'1133'` | `1133px × 744px`（兼容 iPad `1024×768`） | `@media (orientation: landscape) and (max-width: 1179px)` | **宽 > 高**（横向分页卡带模式，`overflow-x: auto; scroll-snap-type: x mandatory`） | **≤ 2 张顶层卡片/屏**（超出卡片流入第 2 屏，底部显示进度聚光灯 `V3`） | `--cz-a-w: 420px`；外围 `.cz-canvas-body` 左右内边距收紧为 `12px`，卡片间距 `gap: 12px`，通过 `syncCanvasHeight()`（`:23036`）锁定整屏高度不出现纵向滚动条 |
| **`ipad-s`** | `'744'` | `744px × 1133px`（兼容 iPad `768×1024`） | `@media (orientation: portrait) and (min-width: 600px)` | **高 > 宽**（纵向无限下拉瀑布流，`flex-direction: column; overflow-y: auto`） | **单列纵向排列**（每行 1 张顶层卡片，宽度 `100%`，自然向下生长） | 容器最大宽度 `max-width: 744px`（居中），水平内边距 `16px`，卡片间距 `gap: 16px`；子卡收到 `data-vp="744"`，卡内保持平板双栏/宽屏信息密度，但外层容器严格单列纵向堆叠 |
| **`phone-layout`** | `'440'` | `440px × 956px`（兼容 iPhone `375px–440px`） | `@media (orientation: portrait) and (max-width: 599px)` | **高 > 宽**（纵向无限下拉瀑布流，`flex-direction: column; overflow-y: auto`） | **单列纵向排列**（每行 1 张顶层卡片，宽度 `100%`，自然向下生长） | 容器最大宽度 `max-width: 440px`（居中），水平内边距 `10px`，卡片间距 `gap: 12px`；子卡收到 `data-vp="440"`，卡内切换为手机紧凑单栏布局，顶部胶囊栏 `#pkTop` 字号与间距紧凑化 |

> **关键实现落点**：
> 1. `applyCanvasViewport()`（`src/kid_app/templates/practice-dsh.html:23148-23163`）重写为按 `w > h`（landscape）与 `h >= w`（portrait）先判定横竖，再以 `1180px`（横屏分界）与 `600px`（竖屏分界）确定 `layoutTier`。
> 2. `canvasIsFeed()`（`:22619-22625`）改为：
>    ```javascript
>    function canvasIsFeed() {
>      if (state.mode !== 'canvas') return false;
>      return state.layoutTier === 'ipad-s' || state.layoutTier === 'phone-layout';
>    }
>    ```
> 3. CSS 媒体查询（原 `:19655` `@media (max-width: 1023px)` 与 `:19887`）统一替换为机身属性选择器 `.cz-canvas-body[data-layout-tier="ipad-s"], .cz-canvas-body[data-layout-tier="phone-layout"]`，确保 JS 判定与 CSS 样式 100% 同步，消除 `1024×768`（iPad 横屏）与 `744×1133`（iPad 竖屏）在 `1023px` 临界点上的错位。

### 1.4 宽 > 高模式（`pc-layout` / `ipad-h`）：单屏 ≤ 2 卡与横向扩展机制（V2）

在 `pc-layout` 与 `ipad-h` 下，针对 `COMBO_SCHEMA`（`:19066-19126`）与 `buildCombo()`（`:20091-20161`）执行以下改造：

1. **顶层卡片分页单元定义**：
   * 在 `buildCombo()`（`:20091-20161`）中，顶层视觉列（Column Unit）定义为 `#czAStack.cz-astack`（内含票夹卡槽与 Card A Dashboard）、独立的 `.cz-tcard`（如 Card B、Card D、Card Q）或纵向堆叠子组 `.cz-substack`（如 Combo 1 中的 `B+S` 纵向栈，占 1 个顶层列宽）。
   * 注意：根据 `C1`，今日记录 `R` 改为顶部「练习记录」按钮触发的全屏模态窗，不再作为常驻桌面卡列占用横向屏宽；当组合含超过 2 个顶层卡片列（例如 `A + B + S` 拆列、Combo 4 `A + S + D`、Combo 5 `A + B + Q + D` 或自定义多选 `off`）时，每 **2 个顶层卡片列** 封装为一个 `.cz-stage-page`（或按每页 2 卡计算分页步长）。
2. **废除超 2 卡同屏挤压**：
   * 修改 `fitWideCombo()`（`:21315-21349`）：当顶层卡片列数 `<= 2` 时，计算单屏宽度适配；当顶层卡片列数 `> 2` 时，**禁止**将第 3、4 张卡片缩小挤压进第 1 屏，而是固定前 2 张卡片占满第 1 屏（宽度 = `comboAvailWidth(stageWrap)` `:21292`，减去 `gap`），第 3 张及后续卡片按相同单卡宽度向右自然排列在第 2 屏及后续屏（`.cz-stage-wrap` 启用 `overflow-x: auto; scroll-snap-type: x mandatory`）。

### 1.5 宽 > 高模式：底部进度聚光灯区域设计（V3）

**明确结论**：**就地升级替换**现有的 `.cz-pagedots`（CSS 位于 `:19730-19739`，DOM 挂载与逻辑位于 `syncComboPager()` `:21409-21460`、`paintStageDots()` `:21353-21365`、`stageGoPage()` `:21378-21390`），将其升级为支持「点击跳页 + 指针拖拽滑动（Scrubbing）+ 聚光灯光晕指示」的 `.cz-spotlight-bar`，不新建第二套平行分页 DOM。

1. **DOM 结构（挂载于 `#czStageHost` 底部，替换原 `.cz-pagedots`）**：
   ```html
   <div class="cz-pagedots cz-spotlight-bar" role="slider" aria-label="画布屏幕切换聚光灯"
        aria-valuemin="0" aria-valuemax="1" aria-valuenow="0" tabindex="0">
     <div class="cz-spotlight-track">
       <div class="cz-spotlight-beam"></div>
       <button type="button" class="cz-page-dot is-on" data-page="0" aria-label="第 1 屏"></button>
       <button type="button" class="cz-page-dot" data-page="1" aria-label="第 2 屏"></button>
     </div>
   </div>
   ```
2. **几何尺寸与视觉样式（严格使用既有 token）**：
   * 外层容器 `.cz-spotlight-bar`：高度固定 `--dots-h: 36px`（原 `:19650` `26px` 增至 `36px`），宽度 `100%`，居中对齐。
   * 轨道 `.cz-spotlight-track`：高 `22px`，内边距 `0 10px`，圆角 `999px`，背景 `color-mix(in srgb, var(--ink) 8%, var(--paper))`，边框 `1px solid var(--line)`，内部 `.cz-page-dot` 间距 `10px`。
   * 聚光灯光束 `.cz-spotlight-beam`：绝对定位滑块，高 `16px`，宽 `44px`，圆角 `999px`，背景 `var(--coral)`，发光阴影 `0 0 14px color-mix(in srgb, var(--coral) 55%, transparent)`，随 `stageWrap.scrollLeft / maxScroll` 实时映射 `transform: translate3d(Xpx, 0, 0)`。
   * 显隐规则：当总屏数 `pageCount <= 1` 或处于 `ipad-s` / `phone-layout` 纵向流式模式时，`.cz-spotlight-bar` 设为 `display: none` 且 `--dots-h: 0px`。
3. **三种换屏交互协议**：
   * **在聚光灯轨道上左右拖拽/滑动**：在 `.cz-spotlight-track` 上绑定 `pointerdown` / `pointermove` / `pointerup`（带 `setPointerCapture`）。拖拽期间根据指针在轨道内的归一化横坐标 `ratio = clamp((clientX - trackRect.left) / trackRect.width, 0, 1)` 实时驱动 `stageWrap.scrollLeft = ratio * maxScroll`；松手（`pointerup`）时按最近页码调用 `stageGoPage(stageWrap, Math.round(ratio * (pageCount - 1)))`（平滑吸附 `behavior: 'smooth'`）。
   * **点击节点跳页**：点击任一 `.cz-page-dot[data-page]` 直接调用 `stageGoPage(stageWrap, idx)`（`:21378`）。
   * **卡片画布区横向手势/触控板滑动**：保留并复用 `forwardStageGesture()`（`:22700-22738`）与原生 `scroll-snap-type: x mandatory`，滚动事件通过 `requestAnimationFrame` 反向同步 `.cz-spotlight-beam` 位移与 `aria-valuenow`。

### 1.6 高 > 宽模式（`ipad-s` / `phone-layout`）：纵向无限下拉瀑布流（V4）

1. **展平嵌套容器并保持严格卡片顺序**：
   * 沿用并固化 `:19900-19912` 的 `display: contents` 方案：在 `.cz-canvas-body[data-layout-tier="ipad-s"]` 与 `.cz-canvas-body[data-layout-tier="phone-layout"]` 下，`.cz-combo`、`.cz-astack`、`.cz-substack`、`.cz-tcard` 全部设为 `display: contents`，使 `#czTicketStage` 与所有 `.cz-card` 成为 `.cz-stage` 的直接 Flex 子项（`flex-direction: column; align-items: stretch; gap: 16px` / `12px`）。
   * 显式 `order` 排序（`:19903-19910`）：`#czTicketStage { order: 1 }` → `.cz-card-A { order: 2 }` → `.cz-card-B { order: 3 }` → `.cz-card-S { order: 4 }` → `.cz-card-D { order: 5 }` → `.cz-card-Q { order: 7 }`。
   * **插槽紧密衔接特例**：在 `ipad-s` 与 `phone-layout` 下，`#czTicketStage`（`order: 1`）与 `.cz-card-A`（`order: 2`）之间需要保持卡槽插入的视觉连接感，因此 `.cz-card-A` 设置 `margin-top: calc(-1 * var(--cz-feed-gap))` 使其顶部紧贴 `#czTicketStage` 的 `#pkSlotCavity`。
2. **等宽与自适应高度（零重叠保障）**：
   * 所有卡片容器 `.cz-card` 及 `#czTicketStage` 强制 `width: 100% !important; max-width: 100% !important; flex: 0 0 auto !important;`。
   * 卡片高度由 `sizeFeedCard()`（`:21061-21195`）与 `measureCardContent()`（`:20949-21050`）根据子卡内容真实高度设置 `card.style.height = targetH + 'px'`，并在子卡内部高度变化（如折叠面板展开、曲谱缩放）时通过 `ResizeObserver` 重新触发 `sizeFeedCard()`，杜绝绝对定位导致的卡片重叠。

### 1.7 缩放基准锁定 `canvasFitBaseH` 在 4 档视口下的重置与锁定策略

1. **现状锚点**：`syncCanvasHeight()`（`src/kid_app/templates/practice-dsh.html:23036-23089`）使用 `canvasFitBaseH` 与 `canvasFitBaseKey`（`:23029-23030`）锁定非计时态的缩放分母，遵守 `DESIGN.md §10.1` 红线。
2. **4 档适配规则**：
   * **仅对宽 > 高档位启用整屏缩放**：当 `state.layoutTier === 'ipad-s' || state.layoutTier === 'phone-layout'` 时，`syncCanvasHeight()` 走 `:23038-23045` 分支，清空 `--cz-fit-scale`、`width`、`height`，并将 `canvasFitBaseH = 0; canvasFitBaseKey = ''`，交由纵向自然滚动。
   * **基准 Key 纳入 `layoutTier`**：在 `pc-layout` 与 `ipad-h` 下，`fitKey`（`:23062`）扩展为：
     `var fitKey = Math.round(hostW) + '@' + Math.round(hostH) + '@' + Math.round(designW) + '@' + state.layoutTier;`
   * **锁定时机**：在**选择态（`select`）**与**准备态（`prep`）**下，首次渲染或 `fitKey` 变更时捕获 `naturalH` 写入 `canvasFitBaseH`；一旦 `canvasFitBaseH > 0` 且 `fitKey === canvasFitBaseKey`，即使后续用户在选择态/准备态与计时态（`run`）之间切换引起卡槽露出高度变化，分母始终锁定为 `canvasFitBaseH`，禁止整屏二次跳缩。
   * **重置时机**：当发生 (a) 窗口 resize 跨过 4 档阈值导致 `state.layoutTier` 改变、(b) 设备横竖屏翻转、(c) 切换顶部 Combo 预设（`applySelection()` `:22572`）时，`fitKey` 变化自动触发 `canvasFitBaseH` 重新采样。

---

## 2. 卡槽 3 态状态机（C10–C15）

### 2.1 三态精确定义与现有类名/数据集映射表（C12）

MRD 3.2.5 将卡槽与卡片的生命周期收敛为 **选择态（`select`）**、**准备态（`prep`）**、**计时态（`run`）** 三态。其与现有 `#practiceStage`（`:4780`）、`#pkPunchSlotWrap`（`:5098`）及 Card A `dash.dataset.mode`（`:23234-23238`）的映射关系如下：

| 3 态名称 (`data-slot-state`) | 业务判定谓词（基于 `practice-dsh.html` 状态变量） | `#practiceStage` 类名组合（`:4780`） | `#pkPunchSlotWrap` 属性（`:5098`） | Card A `dash.dataset.mode`（`:9453` / `:23234`） | 物理隐喻与卡片位置 |
|---|---|---|---|---|---|
| **选择态 (`select`)** | `!cur \|\| !String(content \|\| '').trim()`（科目未选，或科目已选但未选定具体练习内容 session） | `.practice-stage.stage-prep.stage-bar.slot-state-select`（注：淘汰旧版整屏大票夹展开态，首屏即进入卡槽悬停态） | `data-slot-state="select"` | `'prep'` | 卡片处于卡槽上方**高露出上拔位**（`C13`），露出卡片头部、重选按钮及该科目**前 3 个 session 快捷标签**（若已选科目）或「点击选择科目」引导 |
| **准备态 (`prep`)** | `Boolean(cur && String(content \|\| '').trim()) && (!started \|\| paused \|\| !timerRunning)`<br>⚠️ **含两类子场景**：<br>① 初始选妥科目+session 尚未点开始（`!started`）<br>② **从计时态点击暂停（`started && paused && !timerRunning`）** | ① 初始准备：`.practice-stage.stage-prep.stage-bar.slot-state-prep`<br>② 暂停准备：`.practice-stage.stage-prep.stage-bar.slot-state-prep.is-paused`（移除 `.stage-running`） | `data-slot-state="prep"`<br>`data-slot-substate="ready \| paused"` | ① 初始：`'prep'`<br>② 暂停：`'pause'`（`cardAMode()` `:23236`） | 卡片从槽内**向上缓缓拔出少许**（`C13` 加减速微动画），露出卡片头部、累计记录入口（`C7`）、`重新选择` 按钮（`C15`）及**前 3 个 session 快捷标签** |
| **计时态 (`run`)** | `Boolean(cur && String(content \|\| '').trim() && started && timerRunning && !paused)` | `.practice-stage.stage-running.slot-state-run` | `data-slot-state="run"` | `'run'` | 卡片**向下插入卡槽深处**（`C14`），仅露出顶部紧凑状态带 `#pkCardExposedBar`（显示曲目名 + 脉冲绿点 + 实时计时 `#pkExposedTimer`），**卡面不可点击**（`pointer-events: none`） |

> **关于「准备态包含从计时态点击暂停」的关键架构改造点**：
> * 现状：`pauseToggle()`（`:7731-7747`）在点击暂停时仅切换 `paused = true; timerRunning = false`，但 `#practiceStage` 仍保留 `.stage-running` 类（`:7702` 添加后直到 `finish()` `:7849` 才移除），导致暂停时卡片依然锁死在计时态槽底。
> * 改造后：在 `pauseToggle()`（`:7731-7747`）与 `bridgeCardA()`（`:23443-23446`）中，当切换为 `paused = true` 时，同步调用 `syncSlotState()`：将 `#practiceStage` 的 `.stage-running` 替换为 `.stage-prep.stage-bar.slot-state-prep.is-paused`，并将 `#pkPunchSlotWrap.dataset.slotState = 'prep'`。此时卡片执行 `C13` 上拔动画回到准备态位置，允许用户查看累计记录、切换前 3 个 session 标签或点击 `重新选择`；当再次点击开始/继续（`paused = false; timerRunning = true`）时，重新切回 `.stage-running.slot-state-run`，卡片执行 `C14` 下插动画。

### 2.2 状态迁移完整真值表（7 大触发事件）

| 序号 | 触发事件 | 入口函数与源码锚点 | 源状态 → 目标状态 | 守卫条件 (Guard) | 触发的视觉/DOM 动作与微动画 |
|---|---|---|---|---|---|
| **E1** | **页面初始化 / 选定科目** | `selectItem(id)`（`:6638-6662`） | `select` → `select`（若尚未选 session）或 `select/prep` → `prep`（若同时选定 session） | `items.find(x => x.id === id)` 存在 | 若从已有科目切换至另一科目，触发 **`C16` 换卡片动画**（旧卡拔出退场 → 新卡落入准备态上拔位）；渲染该科目前 3 个 session 快捷标签（`C13`）与昨日练习时长（`C18`） |
| **E2** | **选定练习内容 (session)** | 卡面快捷标签点击（`C13`）或 `.pk-folio-box` 内标签点击（`C6`/`C24`，`renderSessionPills` `:6135`） | `select` → `prep`（或 `prep` → `prep`） | `Boolean(cur && content.trim())` | 更新 `#pkExposedSub` / `#dashCoverName` 副标题；高亮选中标签；`#pkPunchSlotWrap` 设为 `data-slot-state="prep"`；激活 Card A 主控大圆钮 `#mainTrigger` 为可开始状态 |
| **E3** | **点击开始计时** | `startPractice()`（`:7681-7729`）← Card A `#mainTrigger`（`:10282`）经 `bridgeCardA()`（`:23443`）调用 | `prep` → `run`<br>（若在 `select` 态点击，先弹出 `openFolio()` `:6664` 拦截） | `cur && content.trim() && mins >= 1` | 触发 **`C14` 卡片插入卡槽动画**：卡片向下滑入槽口 `translateY(var(--cz-card-run-y))`，收起前 3 个 session 标签区，`#czTicketStage` 设置 `pointer-events: none`，`#pkExposedDot` 切换为呼吸绿点 |
| **E4** | **计时中点击暂停** | `pauseToggle()`（`:7731-7747`）← Card A `#mainTrigger` 触发 | `run` → `prep`（`substate="paused"`） | `started && !paused` | 停止 `tickTimer`；`#practiceStage` 移除 `.stage-running` 并加上 `.stage-prep.stage-bar.slot-state-prep.is-paused`；触发 **`C13` 卡片上拔微动画**：卡片从槽口向上缓缓拔出 `28px`，恢复卡面按钮点击（`C7` 统计入口、`C15` `重新选择`、前 3 个 session 标签） |
| **E5** | **暂停态点击继续** | `pauseToggle()`（`:7731-7747`）← Card A `#mainTrigger` 触发 | `prep`（`paused`） → `run` | `started && paused` | 恢复 `lastTickAt = Date.now()` 与 `tickTimer`；`#practiceStage` 恢复 `.stage-running.slot-state-run`；再次触发 **`C14` 卡片插入卡槽动画**并锁定卡面点击 |
| **E6** | **提前结束 / 倒计时归零完成** | `confirmEarlyFinish()`（`:7807-7838`）或 `finish()`（`:7840-7924`） | `run` 或 `prep(paused)` → `prep`（重置 `started = false`） | `started === true` | POST `/api/log` 保存记录并触发 `openPraise()` / 刷新今日记录弹窗数据；卡片从槽底升回 `prep` 上拔位（`C13`），保留当前 `cur` 与 `content` 供下一轮练习 |
| **E7** | **点击「重新选择」或点封面换科目** | `.pk-exposed-expand-hint`（`C8`/`C15`）或 Card A `.cover-frame` / `#dashCoverName`（`C9`）调用 `openFolio()`（`:6664`） | `select` 或 `prep` → 打开 `#pkFolioModal`（`:5261`） | `slotState !== 'run'` | 弹出加宽版 `.pk-folio-box`（含科目列表 + 每个科目下的 session 标签组 `C6`/`C24`）；用户在弹窗内点选新科目与 session 后关闭弹窗，触发 **E1 + E2 + `C16` 换卡动画** |

### 2.3 卡槽几何重构：卡片露出增高、槽口下移与 Dashboard 内元素下移（C10 / C11 / C13 / C14）

`updateCardSlotGeometry()`（`src/kid_app/templates/practice-dsh.html:20164-20385`）是控制卡槽与 Card A 顶部衔接的唯一几何中心。MRD 3.2.5 对其几何参数做如下精确调整：

1. **三态露出高度与位移参数表（写入 `#czAStack` CSS 变量）**：

   | 几何参数 / CSS 变量 | 旧值（`:20201-20272`） | MRD 3.2.5 新值（**选择态 `select` / 准备态 `prep`**） | MRD 3.2.5 新值（**计时态 `run`**） | 作用目标与源码锚点 |
   |---|---|---|---|---|
   | **卡片露出可见高度 `exposedH`** | `min(max(aH*0.18, 86), 124)`（约 `86px–118px`） | **`136px`**（`clamp(128px, aH * 0.24, 148px)`）：容纳顶部状态行（`44px`）+ 科目累计记录胶囊（`28px`）+ 前 3 个 session 标签行（`44px`）+ 内边距（`20px`） | **`88px`**（`clamp(82px, aH * 0.15, 96px)`）：仅露出顶部紧凑状态带 `#pkCardExposedBar`（曲目名 + 绿点 + 计时器） | `updateCardSlotGeometry()` `:20201` |
   | **卡片上拔位移 `--cz-card-pull-y`** | 固定 `cardRise = 26px` | **`-28px`**（向上拔出 `28px`，`C13`） | **`0px`**（完全插入卡槽基准位，`C14`） | 作用在 `#pkPunchSlotWrap`（`:5098`）的 `transform: translate3d(0, var(--cz-card-pull-y), 0)` |
   | **卡槽凹口位置 `#pkSlotCavity`** | `bottom: 0; height: 22px`（`:19776`） | **向下移动 `22px`**：槽口唇边高度 `slotLipH = 24px`，通过 `--cz-slot-overlap` 将槽口压入 Card A `section.panel` 顶部区域更深处（overlap 从 `38px` 增至 **`60px`**） | 同左（槽口物理位置固定在面板上沿下移后的基准线上，不随卡片拔插而乱跳，确保物理插槽锚定感） | `#pkSlotCavity` `:5117`、`:19776`；`updateCardSlotGeometry()` `:20210-20225` |
   | **Dashboard `section.panel` 顶部内边距 `--cz-panel-pt`** | `slotOverlap + 10`（约 `48px`） | **`74px`**（`slotOverlap(60px) + 14px`） | **`74px`**（保持固定，防止切换开始/暂停时 Card A 内部封面、数显、标尺发生垂直跳动） | `updateCardSlotGeometry()` `:20272` → 写入 Card A `section.panel { padding-top: var(--cz-panel-pt) }`（`:19327`） |

2. **Dashboard `section.panel` 内部元素联动下移（C11）**：
   * 由于 `--cz-panel-pt` 从 `~48px` 增加到 **`74px`**（下移 `26px`），为保证 Card A 总高不变且不撑破单屏基准高 `canvasFitBaseH`：
     * `section.panel`（`:9455`）内部纵向间距 `gap` 从 `10px` 收紧为 **`7px`**（`:8621` / `:19328`）；
     * `.panel-head`（`:9456`）移除 `#panelMicBtn`（迁往底部 `diag-card`，见 §3.5），使 `.cover-frame`（`:9465`）与 `#dashCoverName`（`:9469`）整体随 `--cz-panel-pt: 74px` 自然下移 `26px`，彻底让出上方加高后的卡槽与卡片露出区；
     * `.readout` 大数显字号在 `aH < 640px` 时自适应收紧 `4px`，保证 `.panel-foot`（`:9491`）不触底溢出。

3. **C13 上拔微动画与 C14 下插锁定动效参数**：
   * **C13（进入选择态 / 准备态 / 计时暂停时向上拔出）**：
     * 触发属性：`#pkPunchSlotWrap[data-slot-state="select"]`、`#pkPunchSlotWrap[data-slot-state="prep"]`
     * 位移与缓动：`transform: translate3d(0, -28px, 0)`，过渡时长 **`360ms`**，加减速缓动曲线 **`cubic-bezier(0.22, 1, 0.36, 1)`**（先快速克服卡槽阻尼启动，后柔和减速停靠在悬停位）。
     * 前 3 个 session 标签区 `.pk-exposed-quick-sessions`：`opacity: 0 -> 1`、`transform: translateY(6px) -> translateY(0)`，过渡时长 **`260ms`**，延迟 **`80ms`**，缓动 **`cubic-bezier(0.22, 1, 0.36, 1)`**。
   * **C14（进入计时态时向下插入卡槽并禁用点击）**：
     * 触发属性：`#pkPunchSlotWrap[data-slot-state="run"]`
     * 位移与缓动：`transform: translate3d(0, 0px, 0)`，过渡时长 **`300ms`**，缓动曲线 **`cubic-bezier(0.32, 0.72, 0, 1)`**（模拟磁吸落槽，末端带轻微机械落位感）。
     * 点击禁用规则：在 `.practice-stage.slot-state-run #czTicketStage` 上设置 **`pointer-events: none !important; cursor: default !important;`**，同时隐藏 `.pk-exposed-expand-hint`（`opacity: 0; visibility: hidden`）与 `.pk-exposed-quick-sessions`（`max-height: 0; opacity: 0; pointer-events: none`）。

### 2.4 `#pkCardExposedBar` 结构升级与三态显隐清单（C7 / C8 / C13 / C14 / C15）

将 `#pkCardExposedBar`（`src/kid_app/templates/practice-dsh.html:5121-5129`）从原本只有单行标题的窄条，升级为支持 3 态切换的双层露出卡头：

```html
<!-- 替换 src/kid_app/templates/practice-dsh.html:5121-5129 -->
<div class="pk-card-exposed-bar" id="pkCardExposedBar" aria-live="polite">
  <!-- 上部区域：左侧科目累计记录入口 (C7) + 右侧计时数字 (run态) -->
  <div class="pk-exposed-top-row">
    <button type="button" class="pk-exposed-stats-chip" id="pkExposedStatsTrigger"
            aria-label="查看科目累计练习记录">
      <span class="pk-exposed-dot" id="pkExposedDot" aria-hidden="true"></span>
      <span class="pk-exposed-stats-text" id="pkExposedStatsText">累计 0 次 · 0 分钟</span>
      <span class="pk-exposed-stats-caret" aria-hidden="true">↗</span>
    </button>
    <span class="pk-exposed-timer" id="pkExposedTimer">00:00</span>
  </div>

  <!-- 中部主行：左侧当前科目与选中 session 标题 + 右侧「重新选择」独立按钮 (C8 / C15) -->
  <div class="pk-exposed-main-row">
    <div class="pk-exposed-title-group">
      <span class="pk-exposed-title" id="pkExposedTitle">未选曲目</span>
      <span class="pk-exposed-sub" id="pkExposedSub">点右侧重新选择科目与内容</span>
    </div>
    <button type="button" class="pk-exposed-expand-hint" id="pkExposedReselectBtn"
            aria-label="重新选择练习科目与内容">重新选择</button>
  </div>

  <!-- 下部区域：选择态/准备态上拔露出的前 3 个 session 快捷标签 (C13) -->
  <div class="pk-exposed-quick-sessions" id="pkExposedQuickSessions" role="group" aria-label="快捷练习内容选择">
    <!-- 由 renderExposedQuickSessions() 动态渲染当前科目的前 3 个 session pill -->
  </div>
</div>
```

**三态下 `#pkCardExposedBar` 内部子元素显隐与交互真值表**：

| 子元素 ID / 类名 | 选择态 (`select`) | 准备态 (`prep`，含暂停) | 计时态 (`run`) |
|---|---|---|---|
| `#pkExposedStatsTrigger`（`C7` 上部累计记录入口） | 若 `cur` 已选：显示 `累计 N 次 · M 分钟`，可点击打开 `C7` 弹窗；若 `!cur`：显示 `待选择练习科目`，不可点击 | **显示且可点击**：点击打开 `C7` 科目累计练习记录 pop-out | **隐藏文案箭头，仅保留 `#pkExposedDot` 呼吸绿点**，不可点击 |
| `#pkExposedTimer`（实时倒计时/正计时） | `display: none` | 若 `substate === 'paused'`：显示当前暂停读数（琥珀色闪烁）；若未开始：`display: none` | **显示**（`font-variant-numeric: tabular-nums`，实时跳秒） |
| `#pkExposedTitle` + `#pkExposedSub` | 显示科目名（或「请选择练习科目」）+「请选择下方练习内容」 | 显示科目名 + 当前选中的 session 名称 | 显示科目名 + 当前选中的 session 名称 |
| `#pkExposedReselectBtn`（`.pk-exposed-expand-hint`，`C8`/`C15`） | **显示文案 `重新选择`**；仅该按钮本身响应点击（`stopPropagation`），点击调用 `openFolio()` 打开 `.pk-folio-box` | **显示文案 `重新选择`**；仅该按钮本身响应点击，点击调用 `openFolio()` 打开 `.pk-folio-box` | **`display: none`**（且整卡 `pointer-events: none`） |
| `#pkExposedQuickSessions`（`C13` 前 3 个 session 快捷标签） | 若 `cur` 已选：**展开显示前 3 个 session pill**（点击任一 pill 立即选中并切入 `prep` 态）；若 `!cur`：显示 1 个虚线引导胶囊 `＋ 点此选择科目与内容` | **展开显示前 3 个 session pill**（当前选中项高亮 `is-active`，可一键切换至另外 2 个常用 session） | **收起隐藏**（`max-height: 0; opacity: 0; pointer-events: none`） |

> **C8 点击热区收敛落实点**：
> 删除 `initRunRailCard()`（`src/kid_app/templates/practice-dsh.html:7047-7062`）中绑定在整个 `stageCard`（`#czTicketStage`）上的 `click` 与 `keydown` 监听器（原逻辑点击整张卡任意空白处均会触发 `expandToTicket()`）。改为**仅**在 `#pkExposedReselectBtn`（即 `.pk-exposed-expand-hint`）上绑定 `click` → `openFolio()`，在 `#pkExposedStatsTrigger` 上绑定 `click` → `openSubjectStatsPopout('card')`（`C7`），在 `#pkExposedQuickSessions` 内前 3 个 `.pk-quick-session-pill` 上绑定 `click` → `selectQuickSession(tag)`。卡面其余背景区域不绑定任何跳转或展开事件。

---

## 3. 票夹瘦身后的元素归属表（C1–C9, C17–C24, §2.3.2.1）

### 3.1 `pk-ticket`、`#pkRunRail` 与 Dashboard `tpl-A` 全量元素去向总表

下表逐一列出 `src/kid_app/templates/practice-dsh.html` 中原票夹 `article#pkTicketCard.pk-ticket`（`:4786-5059`）、运行轨 `#pkRunRail`（`:5061-5095`）、露出卡头 `#pkCardExposedBar`（`:5121-5129`）及 Dashboard `tpl-A`（`:9453-9589`）全部子元素的处置动作与新归属位置：

| 原所属区域 | 原元素 DOM 选择器与源码行号 | 原功能描述 | MRD 3.2.5 处置动作 | 新归属位置 / 替代组件与交互说明 | 关联编号 |
|---|---|---|---|---|---|
| **顶部导航栏 `#pkTop`** | `button#pkRecords.pk-top-pill`（`:4770`，绑定于 `:8250`，更新于 `:8378`） | 顶部右侧胶囊，原显示 `今日 · 0条` 并打开抽屉 `#pkRecordsDrawer` | **改名 + 改触发目标** | 按钮主文案固定为 **「练习记录」**（保留右侧今日条数角标或副文案）；点击不再打开旧抽屉，而是直接打开 **`C1` 全屏今日练习记录弹窗**（调用 `openRecordsPop()` `:20817`） | `C1`、`C2`、`C3` |
| **今日练习记录弹窗 `tpl-R` / `.popout-backdrop`** | `#czPopBackdrop.popout-backdrop`（`:19943-19961`，`buildPop()` `:20721-20764`）内嵌 `tpl-R`（`:16591-17347`） | 原为宽高受限的居中模态卡片（`max-width: 780px; max-height: 85vh`） | **升级为全屏弹窗** | `.popout-card[data-pop-card="R"]` 设为全屏尺寸（`width: min(100vw - 24px, 1280px); height: calc(var(--cz-band-h, 100vh) - 24px)`，窄屏下 `100vw × 100dvh`）；右上角 `#czPopClose`（`×`）、底部 `#czPopDone`（「完成」）及遮罩空白点击均调用 `closeRecordsPop()`（`:20835`），关闭后无损返回原浏览状态 | `C1`、`C2`、`C3` |
| **`pk-ticket` 头部** | `button#pkFolioBtn.pk-ticket-folio-btn`（`:4798`）+ `#pkTicketHeroFrame`（`:4802-4809`） | 票夹右上角「换曲目 ▾」按钮与票夹内曲目封面 | **从 `pk-ticket` 删除** | 曲目封面展示与换曲目入口统一收归：**① Card A Dashboard 顶部 `.cover-frame`（`:9465`）与 `#dashCoverName`（`:9469`）点击触发 `openFolio()`（`C9`）**；**② 卡槽露出区 `#pkExposedReselectBtn`（「重新选择」，`C8`/`C15`）点击触发 `openFolio()`** | `C4`、`C5`、`C8`、`C9`、`C15` |
| **`pk-ticket` 双列步进器** | `.pk-ticket-digits-grid`（`:4812-4843`）：左列 BPM（`#pkBpmMinus` / `#pkBpmBig` / `#pkBpmPlus` `:4814-4827`）+ 右列时长（`#pkDurMinus` / `#pkDurBig` / `#pkDurPlus` `:4830-4842`） | 票夹内调节速度 BPM 与目标练习时长 | **从 `pk-ticket` 整块删除** | **① BPM 与音符节奏调节**：收归 Card A `panel-foot .c-right` 点击弹出的 **`C19` 全局音符节奏小弹窗**（及 Card B 节拍器联动）；**② 目标时长调节**：收归 Card A 面板内 `250px` 宽的 **`#ruler` 拖拽标尺**（`:9483` / `C17`）与主大数显 `#minVal`（`:9474`） | `C4`、`C17`、`C19` |
| **`pk-ticket` Session 选择区** | `#pkSessionSlot.pk-session-slot.prep-only`（`:4854`）+ `.pk-session-tags-wrap.prep-only > #pkSessionTags`（`:4857-4864`） | 票夹内当前科目下的练习内容（session）胶囊网格与自定义输入 | **从 `pk-ticket` 迁移至 `.pk-folio-box` + 露出前 3 项** | **① 完整列表 + 自定义输入**：迁入加宽加高后的科目选择弹窗 **`#pkFolioModal > .pk-folio-box`**（`:5261-5280`）内每个科目项下方（`C6`、`C24`）；**② 快捷前 3 项**：在卡槽选择态/准备态上拔露出区 `#pkExposedQuickSessions` 展示前 3 个 session 标签（`C13`） | `C6`、`C13`、`C24` |
| **`pk-ticket` 科目累计统计卡** | `#pkSubjectInfoCard.pk-subject-info-card.prep-only`（`:4941-5035`）：含累计次数/总时长/近 7 天/日均（`:4950-4968`）、月度点阵 `#pkMonthDotsGrid`（`:4971-4978`）、历史 Session 芯片 `#pkSubjectSessionsList`（`:4981-4988`）、近 5 次记录 `#pkSubjectHistoryList`（`:4991-4998`）、曲目要点 `#pkRequireNote`（`:5002-5029`） | 票夹下半部常驻的科目多维统计信息 | **从 `pk-ticket` 剥离为独立 Pop-out 模态窗 (`C7`)** | 封装为独立弹窗 `#pkSubjectStatsModal`（复用 `ensureItemStats()` `:6426`、`renderSubjectStats()` `:6459`、`renderMonthDotMatrix()` `:6495` 渲染逻辑）。提供**双入口触发**：**① 卡槽露出区上部 `#pkExposedStatsTrigger`（`C7`）**；**② Card A `panel-foot .c-left` 的「昨天练了 x.x分」按钮（`C18`）** | `C7`、`C18` |
| **`pk-ticket` 底部主开始按钮与声音开关** | `.pk-ticket-actions`（`:4914-4938`）：`#pkStart`（「插入卡槽 · 开始练习」）+ `#pkSoundBtn` + `#pkMicBtn` | 旧版大票夹底部的开始按钮与音效/麦克风小图标 | **从 `pk-ticket` 隐藏/停用** | 开始/暂停统一由 **Card A 主控大圆钮 `#mainTrigger`（`:9530`）** 触发；麦克风开关统一由 **Card A 底部 `diag-card` 内的合并版麦克风按钮（`§2.3.2.1`）** 触发 | `C4`、`C12`、`§2.3.2.1` |
| **`#pkRunRail` 旧版横向运行条** | `aside#pkRunRail.pk-run-rail`（`:5061-5095`） | 早期版本遗留的顶部横向运行条（已在 `:2629` 设为 `display: none !important`） | **保持废弃隐藏** | 运行态与准备态展示完全由 `#pkPunchSlotWrap` 内的 `#pkCardExposedBar`（`:5121`）承担 | `C8`、`C12`–`C15` |
| **Card A `section.panel` 顶部麦克风按钮** | `button#panelMicBtn.mic-status-btn`（`:9457-9460`） | 面板左上角 `MIC ON / OFF` 胶囊按钮 | **从 `.panel-head` 移出，向下合并至 `section.diag-card`** | 移入 `section.diag-card`（`:9574-9583`）替换原 `.diag-status` 文字行与原 `#micToggleBtn`，消除同卡双麦克风按钮冗余（详见 §3.5） | `MRD §2.3.2.1` |
| **Card A `section.panel` 曲目封面与标题** | `.cover-frame`（`:9465-9467`）+ `#dashCoverName`（`:9469`） | 原仅作静态展示当前曲目封面与曲名 | **升级为可点击换科目触发器 (`C9`)** | 在选择态/准备态下赋予 `role="button" tabindex="0"` 与悬浮微缩放反馈；点击通过 `DizicalPracticeBus` 通知父文档调用 `openFolio()` 打开 `.pk-folio-box`（计时态下禁用点击） | `C5`、`C9` |
| **Card A `section.panel` 时间标尺** | `.ruler-wrap > #ruler.ruler`（`:9483-9489`，以及主文档镜像 `:5206-5215`） | 原宽度 `100%`（撑满 `section.panel` 内容区约 `376px`） | **宽度固定收窄为 `250px` (`C17`)** | `.ruler-wrap` 设置 `width: 250px; max-width: 100%; margin-inline: auto;`，标尺居中置于大数字读数下方，左右留出呼吸空间 | `C17` |
| **Card A `panel-foot` 左槽** | `.panel-foot.grid-3col .c-left > span#todayTotal`（`:9492-9494`） | 原静态显示 `今日已练 XXm` | **改造为科目昨日练习时长 + `C7` 弹窗入口 (`C18`)** | 改为 `<button type="button" id="yesterdaySubjBtn" class="panel-foot-link">`：<br>• 未选科目（`!cur`）：文案为空 `""`，`visibility: hidden`<br>• 已选科目（`cur`）：显示 **`昨天练了 x.x分`**（数据取自昨日该科目累计秒数 `/ 60` 保留 1 位小数），点击打开 `C7` 科目累计练习记录 pop-out | `C7`、`C18` |
| **Card A `panel-foot` 右槽** | `.panel-foot.grid-3col .c-right > button#bpmToggleBtn`（`:9496-9500`） | 原显示 `♪ 96 BPM` 并直接在本地循环切换预设档位 | **改造为音符节奏读数 + 全局小弹窗入口 (`C19`)** | 按钮文案格式改为 **`♩=xx ♪=xx`**（以高对比度高亮当前激活的拍号音符，另一音符按折算或记忆值弱化显示，见 §4.3）；点击通过 `DizicalPracticeBus` 呼出独立于卡片的 **`C19` 全局音符节奏小弹窗** | `C19` |
| **Card A `section.panel` 面板配色** | `section.panel`（`:9455`，CSS 变量定义于 `:8490-8530` 与 `:19705-19718`） | 原默认皮肤下 `--dash-panel` 为纯黑/深炭黑底色，视觉过于沉重 | **切换为 `dizicute` 暖色主题体系 (`C20`)** | 默认浅色皮肤下，`section.panel` 改用 `dizicute` 暖米白/珊瑚红设计 token（面板底色 `var(--cream)`、内凹槽 `var(--paper)`、主读数 `var(--ink)`、强调色 `var(--coral)` / `var(--vermilion)`、边框 `var(--line)`）；暗夜 `ink` 皮肤下同步映射为深暖炭底色（遵循 `DESIGN.md §10.2 & §10.5`） | `C20` |
| **Card A `transport-caps` 辅助文字行** | `div.transport-caps.grid-3col`（`:9546-9569`）：左 `#speakerLogo`（Dizical SVG）、中 `#opsTimerText`（「点击开始计时」）、右 `#standTip`（「立起设备自动进入」） | 运输控制区下方的三列辅助说明文字与 Logo | **整行内容全部移除 (`C21`)** | 清空 `#speakerLogo`、`#opsTimerText`、`#standTip` 三个节点（保留空置或隐藏 `.transport-caps` 容器并将高度释放给上下间距），保持控制区极简干净 | `C21` |
| **Card A `transport-main` 右槽 & `diag-card`** | 右槽 `button#standBtn.stand-btn`（`:9534-9544`）与左槽 `div#speakerBlock.speaker-block`（`:9525-9527`） | 左槽为 8×8 扬声器网孔，右槽为「谱架模式」方形大按钮 | **谱架按钮下移入 `diag-card` (`C22`) + 右槽复制对称扬声器 (`C23`)** | **① `C22`**：`#standBtn` 移入底部 `section.diag-card .diag-actions`（`:9579`），样式改为 `.diag-btn`（与「测试庆祝」按钮并列）；<br>**② `C23`**：将左槽 `#speakerBlock` 的 8×8 网孔结构（`:9750-9774`）完整复制到 `transport-main .c-right`（生成 `#speakerBlockRight > #speakerGrilleRight`），形成左右完全对称的双扬声器阵列（不含已移除的 Dizical Logo） | `C22`、`C23` |

### 3.2 `.pk-folio-box` 科目与 Session 一体化选择弹窗重构（C5 / C6 / C9 / C24）

1. **几何尺寸升级（C24）**：
   * 原尺寸（`:19932` & `DESIGN.md §5.8`）：`width: min(540px, 92vw); max-height: min(620px, calc(var(--cz-band-h, 100vh) - 28px));`
   * **MRD 3.2.5 新尺寸**：
     ```css
     #pkFolioModal > .pk-folio-box {
       width: min(680px, 94vw) !important;
       max-height: min(720px, calc(var(--cz-band-h, 100vh) - 24px)) !important;
       display: flex !important;
       flex-direction: column !important;
     }
     ```
2. **内部 DOM 结构与交互流（C6）**：
   * 改造 `renderFolioModal()`（`src/kid_app/templates/practice-dsh.html:6586-6636`）：
     * 列表 `#pkFolioList` 内每个科目卡片 `.pk-folio-item[data-item-id]` 分为上下两层：
       * **上层（科目头 `.pk-folio-item-head`）**：封面缩略图 `.pk-folio-thumb` + 科目名称 `.pk-folio-item-name` + 分类胶囊 `.pk-folio-item-cat` + 累计练习次数角标。点击科目头即选中该科目（高亮 `.is-selected` 并展开其下方的 session 面板）。
       * **下层（内嵌 Session 选择网格 `.pk-folio-item-sessions`）**：直接调用 `PracticeSessionSelector.parse(item.content_options)`（`:5803` / `:6142`）渲染该科目的全部预设 session 胶囊按钮 `.pk-session-pill`，并在末尾提供 `+ 自定义练习内容` 行内输入框 `.pk-folio-custom-session`。
     * **交互闭环**：
       * 用户点击某个科目下的任一 `.pk-session-pill`：立即同步设置 `cur = item` 与 `content = pillValue`，触发 `closeFolio()`（`:6674`），卡片执行 `C16` 换卡动画（若跨科目）并直接进入 **准备态（`prep`）**，同时更新卡面露出的前 3 个 session 标签（`C13`）。
       * 若某科目未配置预设 `content_options`，则提供默认胶囊 `常规练习`（一键即选）与自定义输入框。

### 3.3 昨日科目练习时长计算与展示规范（C18）

1. **数据源与拉取时机**：
   * 后端现成接口：`GET /api/practices/{practice_date}`（`src/kid_app/app.py:1916-1955`），返回指定日期（`YYYY-MM-DD`）的 `items: [{item_id, name, minutes, seconds, sessions: [...]}]`。
   * 在页面初始化 `load()`（`:7479`）时，根据当前业务日期 `practiceDate` 计算前一天日期字符串 `yesterdayStr`（CST 基准減 1 天），并发起一次轻量请求 `fetch('/api/practices/' + encodeURIComponent(yesterdayStr))`，将结果缓存于前端字典 `yesterdayMinutesByItemId: Record<number, number>`。
2. **精确汇总公式**：
   * 对于当前选中科目 `cur.id`：
     * 从昨日返回数据的 `items` 数组中过滤所有 `Number(entry.item_id) === Number(cur.id)` 的条目；
     * 若条目含 `seconds` 字段（精度更高），累加 `seconds / 60`；否则累加 `Number(entry.minutes || 0)`；
     * 结果保留 **1 位小数**：`const minsText = totalMins.toFixed(1)`（例如 `0.0`、`15.0`、`22.5`）。
3. **两态文案规则（`panel-foot .c-left > #yesterdaySubjBtn`）**：
   * **状态 1（未选科目 `!cur`）**：按钮文本置空 `""`，设置 `visibility: hidden; pointer-events: none;`。
   * **状态 2（已选科目 `Boolean(cur)`）**：按钮文本设为 **`昨天练了 ${minsText}分`**（例如 `昨天练了 15.0分` 或 `昨天练了 0.0分`），设置 `visibility: visible; pointer-events: auto; cursor: pointer;`；点击该按钮通过 `DizicalPracticeBus` 触发 `openSubjectStatsPopout('panel-foot')` 打开 `C7` 科目累计练习记录 pop-out。

### 3.4 Dashboard `section.panel` 切换为 `dizicute` 主题配色映射表（C20）

现状 `tpl-A`（`src/kid_app/templates/practice-dsh.html:8490-8530` 与主文档 `:19705-19718`）将 `section.panel` 写死为深黑底色。根据 `C20` 与 `DESIGN.md §10.2 & §10.5`（不引入新 hex，严格使用 `dizicute` 既有 token，且同步维护浅色默认皮肤与 `ink` 暗夜皮肤），Token 重映射如下：

| `section.panel` 样式变量 / 选择器 | 源码位置 | 旧值（深黑面板） | MRD 3.2.5 默认浅色皮肤（`dizicute` 暖色主题） | MRD 3.2.5 暗夜皮肤（`[data-skin="ink"]`） |
|---|---|---|---|---|
| `--dash-panel`（面板主背景） | `:8496` / `:19705` | 深炭黑底色 | `var(--cream)`（搭配顶部柔光渐变 `linear-gradient(180deg, var(--paper) 0%, var(--cream) 100%)`） | `var(--dash-card)`（深暖炭底色，与暗夜卡面协调） |
| `--dash-panel-2` / `--dash-well`（标尺槽与内凹窗背景） | `:8497-8498` / `:19706` | 纯黑内凹色 | `var(--paper)`（内阴影 `inset 0 1px 3px color-mix(in srgb, var(--ink) 8%, transparent)`） | `color-mix(in srgb, var(--ink) 88%, var(--paper))` |
| `--dash-line`（面板边框与分隔线） | `:8502` / `:19707` | 暗灰透明线 | `var(--line)`（暖米灰描边） | `color-mix(in srgb, var(--paper) 14%, transparent)` |
| `.readout` 大数字读数颜色 | `:8695` | 白色发光字 | `var(--ink)`（准备态）/ `var(--vermilion)`（计时态高亮） | `var(--paper)`（准备态）/ `var(--coral)`（计时态高亮） |
| `.panel-head` 曲目名 `#dashCoverName` | `:8660` | 浅灰白字 | `var(--ink)`（字重 `800`） | `var(--paper)` |
| `.panel-foot` 左右入口胶囊（`#yesterdaySubjBtn` / `#bpmToggleBtn`） | `:8760` | 暗底灰字 | 背景 `color-mix(in srgb, var(--coral) 10%, var(--paper))`，文字 `var(--vermilion)`，边框 `1px solid color-mix(in srgb, var(--coral) 28%, var(--line))` | 背景 `color-mix(in srgb, var(--coral) 18%, transparent)`，文字 `var(--coral)` |

### 3.5 `MRD §2.3.2.1` 专项判定：`mic-status-btn` 与 `diag-status` 关系及合一方案

1. **源码级取证（`src/kid_app/templates/practice-dsh.html`）**：
   * **组件 A**：`button#panelMicBtn.mic-status-btn`（位于 `section.panel > .panel-head`，`:9457-9460`），内含 `.dot#panelMicDot` 与 `#panelMicLabel`（显示 `MIC 关` / `MIC 开`）。
   * **组件 B**：`div.diag-status`（位于底部 `section.diag-card`，`:9575-9578`，内含 `.mic-indicator-dot#diagMicDot` 与 `#diagMicStatus`，显示 `监听关` / `监听中`）+ 右侧 `button#micToggleBtn.diag-btn`（`:9580`，显示 `收音` / `收音关`）。
   * **状态源与事件绑定核查**：在 `tpl-A` 脚本 `:10002-10009` 获取上述 DOM，在 `:10410-10411` 中：
     ```javascript
     micToggleBtn.addEventListener('click', toggleMic);
     panelMicBtn.addEventListener('click', toggleMic);
     ```
     在 `toggleMic()`（`:10206-10274`）中，`#panelMicDot` 与 `#diagMicDot` 同步切换 `.on` / `.active` 类，`#panelMicLabel`、`#diagMicStatus`、`#micToggleBtn` 同步由同一个布尔变量 `micActive`（`:10023`）和同一个 Web Audio `AudioContext + AnalyserNode` 实例驱动。
2. **明确结论**：
   * **两者完全表达同一个运行时状态（`micActive`），功能与点击行为 100% 重复**。
   * **合一改造方案**：
     1. 从 `section.panel > .panel-head`（`:9457-9460`）中**移除** `#panelMicBtn`（同时释放 `.panel-head` 顶部空间，配合 `C11` 面板元素下移与 `C9` 封面点击换曲目）。
     2. 将 `mic-status-btn` 移入底部 `section.diag-card`（`:9574-9583`）左侧，**替代**原有的纯文本 `.diag-status` 与原 `#micToggleBtn` 按钮，使 `section.diag-card` 简化为「左侧：可点击的 `#panelMicBtn.mic-status-btn`（兼作状态指示点 + 开关按钮，显示 `MIC 关 · 点击开启` / `MIC 开 · 监听中`） + 右侧：`.diag-actions`（内含 `C22` 迁入的 `#standBtn`「谱架模式」与既有 `#micToggleBtn` 合并后的 `#standBtn` 之外的 `#btnCelebrate`「测试庆祝」——**该按钮当前模板中不存在，方案落地时须删除此行或改为既有元素**）」：
        ```html
        <!-- 改造后的 section.diag-card (替换 src/kid_app/templates/practice-dsh.html:9574-9583) -->
        <section class="diag-card" aria-label="麦克风与辅助工具">
          <button class="mic-status-btn" id="panelMicBtn" type="button" aria-pressed="false">
            <span class="dot" id="panelMicDot"></span>
            <span id="panelMicLabel">MIC 关 · 开启麦克风</span>
          </button>
          <div class="diag-actions">
            <button class="diag-btn" id="standBtn" type="button" aria-pressed="false">谱架模式</button>
            <button class="diag-btn primary" id="btnCelebrate" type="button">测试庆祝</button>
          </div>
        </section>
        ```

### 3.6 前后端改动边界判定

**明确结论**：MRD 3.2.5 全部 24 项改动（`V1–V4`、`C1–C24` 及 `§2.3.2.1`）均为 **`src/kid_app/templates/practice-dsh.html` 纯前端架构与样式交互改造**，**后端 `src/kid_app/app.py` 与 SQLite 数据库 Schema 零改动**（无需变更 `API-CHANGELOG.md`，无需同步 `dizical-minip`）。现有后端接口完全满足数据需求：

| 业务需求 | 复用的现有后端 API | `src/kid_app/app.py` 源码锚点 |
|---|---|---|
| 科目列表与预设 Session 选项（`C5`、`C6`、`C13`、`C24`） | `GET /api/items`（返回 `id, name, category, content_options, require_note, cover_url`） | `app.py:1395-1460` |
| 科目累计练习统计、月度点阵、近 5 次历史（`C7`） | `GET /api/practices/item-stats?date=YYYY-MM-DD` | `app.py:1834-1913` |
| 今日练习记录全屏弹窗与昨日科目练习时长（`C1`–`C3`、`C18`） | `GET /api/practices/{practice_date}` | `app.py:1916-1955` |
| 练习完成/提前结束写入与自定义 Session 持久化 | `POST /api/log`、`PUT /api/items/{item_id}/content-options` | `app.py:1958-2120`、`app.py:1525-1565` |

---

## 4. 三个待用户拍板的交互方案（C7 / C16 / C19）

> **拍板说明**：以下三个交互方案已补齐全部精确尺寸、配色 token、缓动曲线与跨组件协议，请用户审阅拍板后进入代码实现分段（Segment C / D）。

### 4.0 拍板结论（2026-11-06，用户确认）

| 编号 | 结论 | 对本文档的修正 |
|---|---|---|
| **C19** | **不做双读数**。`panel-foot .c-right` 只显示单个「音符 = BPM」，如 `♩=96` 或 `♪=192`。音符（♩ / ♪）与 BPM（正整数）都由弹窗选择，左侧选音符、右侧选速度。BPM 沿用仪表盘既有 `BPM_MIN = 40 / BPM_MAX = 200`（`practice-dsh.html:9654`）。 | 覆盖 §4.3 的「♩=xx ♪=xx 双音符并列」与 A/B 选项讨论；`#bpmRead` 改为单值格式化 `formatTempo(note, bpm)`，同一时刻只高亮一个音符 |
| **C7** | **单入口**。科目累计练习记录 pop-out 只从 `panel-foot .c-left` 呼出：未选科目时无文案，选中后显示「昨天练了 x.x分」。取消 §4.1 的入口 A（`pk-card-exposed-bar` 顶部胶囊）。 | §4.1 双入口表只保留入口 B，`transform-origin` 固定为入口 B 的 `35% 42%` |
| **C16** | 采纳 540ms 双段换卡动画（220ms 抽离 + 320ms 落槽）。 | 与 §4.2 一致，无需改动 |

---

### 4.1 方案一：科目累计练习记录 Pop-out 入口与微交互设计（C7 + C18 联动）

#### 1. 双入口外观与尺寸规格

`C7` 科目累计练习记录弹窗支持从 **卡槽露出区上部（入口 A）** 与 **Dashboard 面板底栏左槽（入口 B，`C18`）** 两个位置呼出，共享同一个弹窗实例 `#pkSubjectStatsModal`：

| 维度 | 入口 A：卡槽露出区上部 `#pkExposedStatsTrigger`（`C7`） | 入口 B：Dashboard `panel-foot .c-left > #yesterdaySubjBtn`（`C18`） |
|---|---|---|
| **挂载位置** | `#pkCardExposedBar > .pk-exposed-top-row` 左上角（`:5121`） | `tpl-A` `section.panel > .panel-foot.grid-3col > .c-left`（`:9492-9494`） |
| **几何尺寸** | 高 `26px`，内边距 `0 10px`，圆角 `999px`（胶囊形），字号 `11.5px`，字重 `700`，最大宽度 `220px`（超出省略号） | 高 `26px`，内边距 `0 10px`，圆角 `999px`（胶囊形），字号 `11.5px`，字重 `700` |
| **展示内容** | `[呼吸圆点 6×6px]` + `累计 {total_sessions} 次 · {total_minutes} 分钟` + 右侧微箭头 `↗` | • 未选科目：`""`（隐藏）<br>• 已选科目：`昨天练了 {x.x}分`（如 `昨天练了 15.0分`） |
| **默认态样式** | 背景 `color-mix(in srgb, var(--amber) 14%, var(--paper))`；文字 `var(--ink)`；边框 `1px solid color-mix(in srgb, var(--amber) 32%, var(--line))` | 背景 `color-mix(in srgb, var(--coral) 10%, var(--paper))`；文字 `var(--vermilion)`；边框 `1px solid color-mix(in srgb, var(--coral) 28%, var(--line))` |
| **Hover 态** | `transform: translateY(-1px)`；背景加深至 `color-mix(in srgb, var(--amber) 24%, var(--paper))`；微箭头 `↗` 位移 `translate(1px, -1px)`（时长 `160ms cubic-bezier(0.22, 1, 0.36, 1)`） | `transform: translateY(-1px)`；背景加深至 `color-mix(in srgb, var(--coral) 18%, var(--paper))`；阴影 `0 3px 8px color-mix(in srgb, var(--coral) 18%, transparent)` |
| **Active 按下态** | `transform: translateY(0) scale(0.97)`（时长 `90ms`） | `transform: translateY(0) scale(0.97)`（时长 `90ms`） |
| **可用状态** | 选择态（已选科目时）与准备态可点击；计时态（`run`）隐藏文字并禁用点击 | 选择态（已选科目时）、准备态、计时态均可点击查看 |

#### 2. Pop-out 模态窗（`#pkSubjectStatsModal`）尺寸、内容与微交互动效

1. **挂载层级与定位基准**：
   * 挂载于 `#canvasBody` 顶层（与 `#pkFolioModal` `:5261` 同级），遵循 `DESIGN.md §10.3` 红线，使用 `top: var(--cz-band-t, 0px); height: var(--cz-band-h, 100vh); z-index: 320;` 确保在任意缩放比下垂直居中于可视舞台带。
2. **弹窗卡片尺寸與结构**：
   * 卡片容器 `.pk-subject-stats-box`：`width: min(520px, 92vw)`，`max-height: min(640px, calc(var(--cz-band-h, 100vh) - 32px))`，圆角 `24px`，内边距 `22px`，背景 `var(--paper)`，边框 `1.5px solid var(--line)`，阴影 `0 24px 60px color-mix(in srgb, var(--ink) 22%, transparent)`。
   * 内部完整承接原 `#pkSubjectInfoCard`（`:4941-5035`）的 5 个模块：
     1. **弹窗头部**：科目封面缩略图（`40×40px`）+ 科目名称 + 分类标签 + 右上角关闭按钮 `#pkSubjectStatsClose`（`32×32px` 圆钮 `×`）。
     2. **4 宫格核心指标条**（`#pkStatSessions` 累计次数、`#pkStatMinutes` 累计分钟、`#pkStatWeek` 近 7 天、`#pkStatAvg` 日均时长）。
     3. **当月练习点阵日历**（`#pkMonthDotsGrid`，支持 `prev/next` 月份切换 `:6550`）。
     4. **练习内容分布芯片**（`#pkSubjectSessionsList`）与**近 5 次练习记录**（`#pkSubjectHistoryList`）。
     5. **本曲目练习要点便利贴**（`#pkRequireNote`，支持行内编辑保存）。
3. **打开/关闭缓动与原点展开动画**：
   * **打开动画（`280ms`）**：
     * 遮罩层 `.pk-subject-stats-backdrop`：`background: color-mix(in srgb, var(--ink) 38%, transparent)`，`backdrop-filter: blur(6px)`，`opacity: 0 -> 1`（`200ms ease-out`）。
     * 弹窗主体 `.pk-subject-stats-box`：根据触发源（入口 A 或入口 B）动态设置 `transform-origin`（入口 A 为 `50% 18%`，入口 B 为 `35% 42%`），从 ` opacity: 0; transform: translate3d(0, 14px, 0) scale(0.92)` 过渡至 `opacity: 1; transform: translate3d(0, 0, 0) scale(1)`，缓动曲线 **`cubic-bezier(0.22, 1, 0.36, 1)`**。
   * **关闭动画（`200ms`）**：
     * 点击右上角 `×`、点击遮罩空白处或按 `Escape` 键触发关闭；主体以 **`200ms cubic-bezier(0.55, 0, 0.86, 0.35)`** 收缩至 `opacity: 0; transform: translate3d(0, 8px, 0) scale(0.95)`，焦点自动归还至触发按钮。

---

### 4.2 方案二：切换科目时的换卡片动画方案（C16）

#### 1. 触发条件与物理隐喻

* **触发条件**：在 `selectItem(id)`（`src/kid_app/templates/practice-dsh.html:6638-6662`）中，当新选中的科目 ID `id` 与变更前的科目 ID `prevCurId` 不同（且 `prevCurId != null`）时触发 `playCardSwapAnimation(prevItem, nextItem, onMidpointSwap)`。
* **物理隐喻**：模拟实体打孔卡从卡槽中**「向上快速抽离旧卡 → 新卡从上方对准槽口垂直落下并停靠在准备态悬停位」**的双段式机械换卡动作。

#### 2. 双段式分步时序与精确参数（总时长 `540ms`）

| 阶段 | 时间窗口 | 动画作用对象 | CSS Transform & Opacity 关键帧 | 缓动曲线 (Easing) | 阶段内 DOM 同步动作 |
|---|---|---|---|---|---|
| **Phase 1：旧卡上拔抽离退场** | `0ms – 220ms`（时长 **`220ms`**） | `#pkPunchSlotWrap`（`:5098`） | 起点：`translate3d(0, -28px, 0) scale(1) rotate(0deg)`，`opacity: 1`<br>终点：`translate3d(0, -68px, 0) scale(0.96) rotate(-1.2deg)`，`opacity: 0` | **`cubic-bezier(0.55, 0, 0.86, 0.35)`**（加速向上抽出） | 为 `#pkPunchSlotWrap` 添加 `.is-swapping-out` 类；期间锁定卡面点击 |
| **Midpoint：卡面数据瞬时刷新** | `220ms`（帧切换点，耗时 **`0ms`**） | `#pkCardExposedBar` 及 Card A 封面/标题 | 瞬时将位置重置到入场起点：`translate3d(0, -76px, 0) scale(0.98) rotate(0.8deg)`，`opacity: 0` | `steps(1)` | 执行 `onMidpointSwap()`：更新 `#pkExposedTitle`、`#pkExposedSub`、`#pkExposedQuickSessions`（前 3 个 session 标签）、`#pkExposedStatsText`、Card A `#dashCoverImg` 与 `#dashCoverName`、昨日练习时长 `#yesterdaySubjBtn` |
| **Phase 2：新卡垂直落槽并回弹停靠** | `220ms – 540ms`（时长 **`320ms`**） | `#pkPunchSlotWrap`（`:5098`） | `220ms`：`translate3d(0, -76px, 0) scale(0.98)`，`opacity: 0`<br>`430ms`（微过冲压槽点）：`translate3d(0, -22px, 0) scale(1.0)`，`opacity: 1`<br>`540ms`（准备态悬停终点）：`translate3d(0, -28px, 0) scale(1.0)`，`opacity: 1` | **`cubic-bezier(0.16, 1, 0.3, 1)`**（快速落入后带轻微阻尼回弹停在 `-28px` 准备态上拔位） | 移除 `.is-swapping-out`，添加 `.is-swapping-in`；槽口光晕 `#pkSlotMouthGlow`（`:5118`）同步闪烁一次暖珊瑚色微光（`opacity: 0.35 -> 0.85 -> 0.35`，`320ms`）；`540ms` 结束时清理临时动画类 |

#### 3. 与 `C13`（上拔）、`C14`（插入）及 `DESIGN.md §10.8`（`--s6-enter-slot-delay`）的协调关系

1. **与 `C13` / `C14` 的衔接**：
   * `C16` 换卡动画仅在 `select` 或 `prep` 态下发生（`run` 计时态下禁止换科目）。
   * `C16` Phase 2 的终点坐标严格等于 `C13` 的准备态上拔坐标 `translate3d(0, -28px, 0)`，因此换卡动画结束的瞬间，卡片已经处于 `C13` 露出前 3 个 session 快捷标签的悬停位，无需二次跳动。
   * 当用户随后点击「开始练习」时，直接从 `-28px` 触发 `C14` 下插动画进入 `0px` 计时态。
2. **关于 `--s6-enter-slot-delay`（`0.78s`，`DESIGN.md §10.8`）的明确规则**：
   * 原 `--s6-enter-slot-delay: 0.78s`（定义于 `:2581` / `:2639`）是为旧版「整屏大票夹 `pk-ticket` 折叠变形为顶部窄条」预留的形态收敛等待时间。
   * 在 MRD 3.2.5 中，由于票夹已瘦身且卡片常驻卡槽，通过 `.pk-folio-box` 换科目时**不经过整屏大票夹折叠变形**，因此 **`C16` 换卡动画不叠加 `0.78s` 延迟**（弹窗关闭的同时立即启动 Phase 1 `220ms` 抽卡 + Phase 2 `320ms` 落卡，端到端 `540ms` 完成）；而原 `.stage-bar .pk-punch-slot-wrap` CSS 中的 `--s6-enter-slot-delay: 0.78s` 声明在源码中保留给初始化回退路径，不违背 `DESIGN.md §10.8`。

---

### 4.3 方案三：Dashboard `panel-foot .c-right` 音符节奏与 BPM 全局小弹窗方案（C19）

#### 1. `panel-foot .c-right` 入口按钮展示格式

* **DOM 位置**：`tpl-A` 内 `section.panel > .panel-foot.grid-3col > .c-right > button#bpmToggleBtn`（`src/kid_app/templates/practice-dsh.html:9496-9500`）。
* **双音符并列读数格式（严格落实 MRD `♩=xx ♪=xx`）**：
  ```html
  <button class="bpm-read-btn" id="bpmToggleBtn" type="button"
          aria-haspopup="dialog" aria-label="设置节拍音符与BPM速度">
    <span class="bpm-note-pair" id="bpmRead">
      <span class="bpm-note-item is-active" id="bpmReadQuarter">♩=96</span>
      <span class="bpm-note-sep" aria-hidden="true"> </span>
      <span class="bpm-note-item" id="bpmReadEighth">♪=192</span>
    </span>
  </button>
  ```
  * **数值联动规则**：设当前一拍基准速度为 `bpm`（范围 `40–200`，默认 `96`），当前选定的拍号基准音符为 `beatNote`（`'quarter'` 代表以四分音符 `♩` 为一拍，`'eighth'` 代表以八分音符 `♪` 为一拍）：
    * 当 `beatNote === 'quarter'`（以 `♩` 为一拍，速度 `bpm`）时：`♩=${bpm}` 高亮显示（`font-weight: 800; color: var(--vermilion)`），右侧 `♪=${Math.min(400, bpm * 2)}`（或同值展示，见下述确认项）以 `opacity: 0.58` 弱化显示。
    * 当 `beatNote === 'eighth'`（以 `♪` 为一拍，速度 `bpm`）时：`♪=${bpm}` 高亮显示（`font-weight: 800; color: var(--vermilion)`），左侧 `♩=${Math.max(20, Math.round(bpm / 2))}` 以 `opacity: 0.58` 弱化显示。
    * **【需 orchestrator 确认】`♩=xx ♪=xx` 中非激活音符的数值语义**：
      * **推荐选项 A（乐理等效折算展示）**：激活音符显示当前设定的节拍器 BPM（如 `♩=96`），非激活音符显示同曲速下的等效时值速度（`♪=192`），直观体现四分音符与八分音符的 1:2 时值关系。
      * **备选选项 B（独立记忆/同值展示）**：分别为 `♩` 和 `♪` 记忆各自最后一次设定的 BPM（默认均为 `96`，显示 `♩=96 ♪=96`），点击切换哪个音符就以哪个音符的设定值驱动节拍器。
      * *架构兼容说明*：下方状态结构同时保存 `{ beatNote: 'quarter' | 'eighth', quarterBpm: 96, eighthBpm: 192 }`，无论拍板选项 A 或 B 仅需调整 1 行格式化函数 `formatTempoPair()`。

#### 2. 全局独立小弹窗（`#pkTempoModal`）挂载层级、尺寸与内部控件布局

1. **为什么挂载在父级 Canvas 文档而非 Card A iframe 内部**：
   * Card A 高度紧凑且受 `overflow: hidden` 裁切；根据 `C19`「做成独立于卡片的全局小弹窗」，弹窗 DOM `#pkTempoModal` 挂载在 `#canvasBody` 顶层（与 `#pkFolioModal` 同级，`z-index: 330`），通过 `top: var(--cz-band-t, 0px); height: var(--cz-band-h, 100vh)` 在全视口舞台中央弹出，完全不受 Card A 边界裁切。
2. **弹窗几何尺寸**：
   * 卡片主体 `.pk-tempo-box`：`width: min(340px, 90vw)`，圆角 `22px`，内边距 `20px`，背景 `var(--paper)`，边框 `1.5px solid var(--line)`，阴影 `0 20px 50px color-mix(in srgb, var(--ink) 22%, transparent)`。
   * 打开动画：`240ms cubic-bezier(0.22, 1, 0.36, 1)`（从 `scale(0.92) translateY(10px)` 弹出）；关闭动画：`180ms cubic-bezier(0.55, 0, 0.86, 0.35)`。
3. **内部 4 层控件结构**：
   ```
   ┌──────────────────────────────────────────────┐
   │  节拍与速度设置                          [×] │  ← 1. 标题栏 (高 28px)
   ├──────────────────────────────────────────────┤
   │  ┌───────────────────┬───────────────────┐   │
   │  │  ♩ 四分音符为一拍 │  ♪ 八分音符为一拍 │   │  ← 2. 音符基准分段选择器 (Segmented Pill, 高 42px)
   │  └───────────────────┴───────────────────┘   │
   │                                              │
   │        [ − ]      ♩ = 96       [ + ]         │  ← 3. 大字号 BPM 步进器 (复用 attachLongPressStepper :8132)
   │                   BPM (40–200)               │     按钮 44×44px，中央读数 36px tabular-nums
   │                                              │
   │   ( 60 )  ( 80 )  ( 96 )  ( 108 )  ( 120 )   │  ← 4. 常用速度快捷胶囊行 (高 30px)
   │                                              │
   │  [       取消       ]  [     确认应用     ]  │  ← 5. 底部操作栏 (高 40px)
   └──────────────────────────────────────────────┘
   ```
   * **控件 1（音符基准分段选择器 `#pkTempoNoteSeg`）**：二选一分段胶囊（`role="radiogroup"`），选项为 `♩ 四分音符为一拍`（`data-note="quarter"`）与 `♪ 八分音符为一拍`（`data-note="eighth"`）。选中项背景 `var(--coral)`，文字 `var(--paper)`。
   * **控件 2（BPM 步进调节区）**：左右为 `44×44px` 圆角步进按钮 `#pkTempoBpmMinus`（`−`）与 `#pkTempoBpmPlus`（`+`），直接复用现有的长按加速步进器 `attachLongPressStepper()`（`:8132-8162`，点按 `±1`，长按每 `70ms` `±2`），范围严格钳制在 `clampBpm(40, 200)`（`:5684`）。
   * **控件 3（常用 BPM 快捷预设胶囊）**：提供 `60`、`80`、`96`、`108`、`120` 五个一键预设胶囊，点击立即将数值填入中央读数。
   * **控件 4（确认/取消与遮罩关闭）**：点击「确认应用」或直接点击遮罩空白处提交修改并关闭弹窗；点击「取消」或右上角 `×` 恢复打开前的快照值并关闭弹窗。

#### 3. 跨 iframe 状态同步协议（Card A ↔ Canvas 主文档 ↔ Card B 节拍器 / Card S 曲谱）

现有的跨卡通信总线 consists of：
* 外层画布总线 `bus`（`src/kid_app/templates/practice-dsh.html:23515-23571`）
* 内层卡片 `DizicalPracticeBus`（`:21779-22265`，已具备 `tempo(bpm)` 方法 `:22254` 与 `state.bpm` `:21802`）

**C19 扩展协议（仅增量扩展 2 个字段，完全向后兼容）**：

1. **状态字段扩展**：
   * 在主文档 `state`（`:19175`）与 `DizicalPracticeBus` 的 `state`（`:21795`）中新增字段：
     `beatNote: 'quarter' | 'eighth'`（默认 `'quarter'`），持久化于 `localStorage.getItem('dsh_beat_note_v1')`。
2. **唤起弹窗消息（Card A → 主文档）**：
   * 用户在 Card A 点击 `#bpmToggleBtn`（`:9496`）时，Card A 调用：
     `window.parent.postMessage({ type: 'dsh:open-tempo-modal', bpm: currentBpm, beatNote: currentBeatNote }, '*')`
   * 主文档监听到 `dsh:open-tempo-modal`（或在同文档模式下由 `DizicalPracticeBus.openTempoModal()` 直接调用），打开 `#pkTempoModal` 并回填当前 `bpm` 与 `beatNote`。
3. **确认广播消息（主文档 `#pkTempoModal` → 所有卡片）**：
   * 用户在 `#pkTempoModal` 中确认后：
     1. 更新主文档 `bpm` 变量（`:5672`）与 `beatNote` 变量，写入 `localStorage`；
     2. 调用 `DizicalPracticeBus.tempo(bpm, beatNote)`（扩展 `:22254` 签名支持第二个参数 `beatNote`）；
     3. 调用外层 `bus.broadcast({ bpm: bpm, beatNote: beatNote })`（`:23539`）；
     4. **Card A** 收到广播后，调用 `renderBpmReadout(bpm, beatNote)` 更新 `.panel-foot .c-right #bpmRead` 的 `♩=xx ♪=xx` 展示；
     5. **Card B（节拍器卡，`tpl-B` `:11280`）** 收到广播后，同步更新节拍器 BPM 滑块/读数，并根据 `beatNote` 切换节拍器每拍音符细分图标。

---

## 5. `DESIGN.md §10` 八条红线合规性自检表

| 红线编号 | `DESIGN.md §10` 红线要求 | 本架构设计合规性验证 |
|---|---|---|
| **§10.1** | 缩放基准锁定（`canvasFitBaseH`） | **合规**：见 §1.7。`canvasFitBaseH` 在选择态/准备态首次渲染时锁定，切换至计时态绝不重新采样；仅在跨 4 档视口阈值、横竖屏翻转或切换 Combo 时重置。 |
| **§10.2** | 严禁硬编码颜色（走 `dizicute` / `--dash-*` token） | **合规**：见 §1.5、§3.4、§4.1–§4.3。全篇所有新增与改造样式 100% 引用 `var(--paper)`、`var(--cream)`、`var(--ink)`、`var(--coral)`、`var(--vermilion)`、`var(--amber)`、`var(--line)` 及 `--dash-*` 语义变量，零新增裸 hex。 |
| **§10.3** | 浮层定位用 `--cz-band-t` / `--cz-band-h` | **合规**：见 §3.1（`C1` 全屏记录弹窗）、§3.2（`C24` `.pk-folio-box`）、§4.1（`C7` `#pkSubjectStatsModal`）、§4.3（`C19` `#pkTempoModal`），全部绑定 `--cz-band-t` 与 `--cz-band-h`。 |
| **§10.4** | `COMBO_SCHEMA` 宽度契约 | **合规**：见 §1.2 与 §1.4。保留 `COMBO_SCHEMA` 组卡定义与 `1133px` 舞台基准宽，仅在顶层卡片列 `>2` 时改为每屏 2 卡横向分页，不篡改既有 `designW` 契约。 |
| **§10.5** | 默认浅色皮肤（同时维护 `ink` 皮肤） | **合规**：见 §3.4。`C20` 将 `section.panel` 默认皮肤切换为 `dizicute` 暖浅色体系，并同步给出了 `[data-skin="ink"]` 的暗夜映射。 |
| **§10.6** | 零外部字体/CDN 依赖 | **合规**：音符符号 `♩`（U+2669）与 `♪`（U+266A）及箭头均使用系统原生 Unicode 字符与内联 SVG，零外部字体或 CDN 引入。 |
| **§10.7** | 测试门禁（43 条 pytest） | **合规**：本设计保留所有自动化测试断言依赖的 DOM ID（如 `#pkTicketCard`、`#pkFolioModal`、`#pkCardExposedBar`、`#ruler`、`#mainTrigger`、`DSH_VERSION` 等）。 |
| **§10.8** | 保留 `--s6-enter-slot-delay` | **合规**：见 §4.2.3。CSS 变量 `--s6-enter-slot-delay: 0.78s` 保留在源码中不删除，`C16` 换卡动画通过独立的 `.is-swapping-out / .is-swapping-in` 类执行 `540ms` 双段动画。 |
