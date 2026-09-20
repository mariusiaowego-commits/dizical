---
id: 26091701-plan-v2
type: plan
version: 2.0.0
date: 2026-09-18
sprint: 26091701
status: 待 dad 拍板
summary: "选择时间态 v2：14px 垂直错位根因(底部按钮 46px 拉偏) / 一体化胶囊座舱 / 单数点选 44px 热区 / 四档 gap 常量"
tags: [sprint, dizical, practice, timer, plan, geometry]
source: ai-agent
author: dizical-agy (Claude Opus 4.6 Thinking)
---

# 计时器选择时间状态与运行过渡优化方案 (v2)

> **范围**: 仅限计时器选择时间（idle）状态的几何、布局、结构依存与步进交互，以及向方案 B「极简数字」运行态的动效交接。  
> **硬性边界**: 运行态已定方案 B（旋钮缩小收起 + 56px 倒计时 + 4px 进度条），不重开 A/B/C 方案选择；不改动后端 API、数据库、老师要求栏及安全守卫语义。  
> **日期**: 2026-09-18

---

## 1. 现状实测几何 (含 file:line + px 算术)

### 1.1 现有 DOM 结构与层级

在 [practice.html:1039-1061](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1039-L1061) 中，主计时器区域的层级结构如下：

```html
.timer-block                                <!-- L122: flex-direction: row; gap: 10px; align-items: stretch -->
  └── .picker-card                          <!-- L136-144: flex; align-items: center; gap: 0; padding: 4px 0 -->
        ├── .activity-wheel#timerWheel      <!-- L217-226: width: 80px; height: 200px; -->
        └── .picker-col                     <!-- L145-151: flex column; align-items: center; gap: 6px; margin: 0 auto -->
              ├── .picker-label             <!-- L152-155: font-size: 13px; font-weight: 600; "主计时" -->
              ├── .dial-knob#timerKnobEl    <!-- L158-166: width/height: var(--knob-size); -->
              ├── #timer-display            <!-- L348: display: none (已隐藏) -->
              ├── .action-btns              <!-- L320: flex; gap: 10px; margin-top: 8px; -->
              │     ├── #startBtn           <!-- L321-329: padding: 10px 20px; font-size: 15px; -->
              │     └── #finishEarlyBtn     <!-- L330: 提前结束 (初始 display: none) -->
              └── .confirm-area#confirmArea <!-- L351: display: none (未打卡时隐藏) -->
```

### 1.2 各元素实际渲染高度 (CSS 算术分解)

#### (1) `.activity-wheel` 内部几何
- 容器尺寸：固定 `width: 80px; height: 200px;`（[practice.html:219-220](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L219-L220)）。
- 选中项定位计算：在 [practice.html:2871](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L2871) 中，`el.style.top = 'calc(50% + ' + (-17 + arcY) + 'px)'`。
  - 对于当前选中项（`offset === 0`），弧线偏移量 `arcY = 0`。
  - `.wheel-item` 自身高度为 `34px`（[practice.html:230](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L230)），其自身半高即 `17px`。
  - 选中项顶部位置：`50% - 17px` = `100px - 17px = 83px`。
  - **选中项中心线（数字中心）**：`83px + 17px = 100px`，即**严格坐落在 `.activity-wheel` 自身高度的中线（距 wheel 顶边 100px 处）**。

#### (2) `.picker-col` 内部纵向堆叠高度
`.picker-col` 是 `flex-direction: column; gap: 6px;`（[practice.html:145-151](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L145-L151)），其内部自上而下包含：
1. **`.picker-label`**: `font-size: 13px; font-weight: 600;` 实际渲染盒模型高度为 **18px**（line-height 约 1.38）。
2. **flex gap**: **6px**。
3. **`.dial-knob`**（高度即 `--knob-size`）：
   - Mac MBP (默认): `--knob-size: 180px`（[practice.html:159](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L159)）
   - iPad mini 竖屏 (640px-1099px): `--knob-size: 168px`（[practice.html:872](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L872)）
   - iPhone (≤639px): `--knob-size: 148px`（[practice.html:852](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L852)）
4. **flex gap**: **6px**。
5. **`.action-btns`**:
   - `margin-top: 8px`（[practice.html:320](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L320)）。
   - 内部按钮 `.btn`：`padding: 10px 20px; font-size: 15px;`，行高约 18px，总高度 `10 + 18 + 10 = 38px`（[practice.html:321-324](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L321-L324)）。
   - 底部按钮行总占用高度：`8px (margin-top) + 38px (button) = 46px`。

因此，`.picker-col` 在 idle 状态下的总高度 $H_{\text{col}}$ 为：
$$\text{Mac}: 18 + 6 + 180 + 6 + 46 = 256\text{px}$$
$$\text{iPad mini}: 18 + 6 + 168 + 6 + 46 = 244\text{px}$$
$$\text{iPhone}: 18 + 6 + 148 + 6 + 46 = 224\text{px}$$

#### (3) 关键：旋钮圆心在 `.picker-col` 中的垂直位置
`.dial-knob` 是正圆形，圆心位于旋钮半高处。圆心距离 `.picker-col` 顶边的距离 $Y_{\text{knob-center}}$：
$$Y_{\text{knob-center}} = \text{Label}(18\text{px}) + \text{gap}(6\text{px}) + \frac{\text{KnobSize}}{2}$$
- **Mac (180px 旋钮)**: $18 + 6 + 90 = \mathbf{114\text{px}}$
- **iPad mini (168px 旋钮)**: $18 + 6 + 84 = \mathbf{108\text{px}}$
- **iPhone (148px 旋钮)**: $18 + 6 + 74 = \mathbf{98\text{px}}$

---

## 2. C1 / C2 / C3 的根因分析

### 2.1 C1 垂直错位根因（为什么 wheel 感觉太低了？）

`.picker-card` 是 flex 容器，其样式为：
```css
.picker-card {
  display: flex;
  align-items: center; /* 交叉轴居中 */
  gap: 0;
  padding: 4px 0;
}
```
因为设置了 `align-items: center`，浏览器会将左侧的 `.activity-wheel`（高 200px）与右侧的整个 `.picker-col`（高 244px~256px）进行**整体垂直中心对齐**。

此时，`.activity-wheel` 的顶部距离 `.picker-card` 顶部的偏移为：
$$\text{Top}_{\text{wheel}} = \frac{H_{\text{col}} - 200}{2}$$
而由于选中项位于 wheel 自身高度的 100px（中点），因此**wheel 选中项中心距离 card 顶部的距离**就是：
$$Y_{\text{wheel-center}} = \text{Top}_{\text{wheel}} + 100 = \frac{H_{\text{col}}}{2}$$

**实测对比数值（算术对比）**：

| 设备 | $H_{\text{col}}$ | Wheel 选中项中心 $Y_{\text{wheel-center}}$ | 旋钮圆心 $Y_{\text{knob-center}}$ | 垂直偏差 $\Delta Y$ (Wheel 偏下量) |
|---|---|---|---|---|
| **iPad mini 竖屏 (744px)** | 244px | 122px | 108px | **+14px (偏下)** |
| **Mac (1728px)** | 256px | 128px | 114px | **+14px (偏下)** |
| **iPhone (440px)** | 224px | 112px | 98px | **+14px (偏下)** |

**根因结论**:  
因为 `.picker-col` 的底部挂载了 `.action-btns`（占高 46px），而顶部只有 `.picker-label`（占高 18px）。底部的按钮造成了上下不对称（底部比顶部重 $46 - 18 = 28\text{px}$）。在 `align-items: center` 作用下，这 28px 的不平衡恰好将 wheel 的中心向下拉低了：
$$\frac{28\text{px}}{2} = \mathbf{14\text{px}}$$
**这正是 Dad 肉眼感知到“wheel 偏下、两边数字没有上下居中”的根本数学原因！**

### 2.2 C2 水平过窄根因（为什么 wheel 太靠近右边圆弧？）

- 在 [practice.html:139](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L139) 中，`.picker-card` 声明了 `gap: 0;`。
- `.activity-wheel`（宽 80px）内部的项目 `.wheel-item` 采用绝对定位 `left: 0; right: 0;`（[practice.html:229](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L229)），其右侧指示器 `.wheel-indicator`（宽 8px）和药丸 `.wheel-pill` 一直贴到 wheel 的最右边界（距离仅 `padding: 0 10px`）。
- 右侧的 `.picker-col` 也是 `margin: 0 auto;`，`.dial-knob` 的外圆环直接从 col 的左边缘开始渲染。
- **物理间距实测为 0px~4px**，没有呼吸留白，视觉上 wheel 的数字与旋钮的刻度环相互碰撞挤压。

### 2.3 C3 缺乏结构依存根因（为什么不像一个整体 UI？）

- `.activity-wheel` 与 `.picker-col` 是平铺在 transparent 卡片上的两个独立 DOM 节点（[practice.html:140-142](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L140-L142) 清除了 background/border-radius/box-shadow）。
- 左侧是一个悬浮的半透渐变滚轮列表，右侧是一个拟物的表盘和底部的实体按钮。
- 两个控件没有共同的包裹底板（backing plate）、没有边界框（bounding box）、没有凹槽（recessed bay）结构，导致它们像是在页面上偶然挨在一起的两个插件，缺乏仪表级（instrument-grade）的整体感。

---

## 3. 对齐方案 (C1 数学对齐 + C2 间距常量)

### 3.1 C1 零误差对齐：结构分层法（解耦按钮影响）

为了彻底解决 14px 的偏下问题，**绝对不能使用 `margin-top: -14px` 这种脆弱的魔术数字**（一旦按钮文本、字号或 padding 微调，就会再次错位）。

**根本解法：重构 `.picker-card` 内部的对齐层级**。
将“滚轮 + 旋钮”封装为一个纯粹的交互对齐行 `.timer-dial-row`，而将 `.picker-label` 和 `.action-btns` 移出此对齐行：

```html
<!-- 重构后的结构 -->
<div class="picker-card">
  <!-- 顶部标题统一居中 -->
  <div class="picker-label"><span class="icon-inline">...</span> 主计时</div>
  
  <!-- 核心交互区：仅包含 wheel 和 dial-knob，保证纯粹的圆心对齐 -->
  <div class="timer-dial-row">
    <div class="activity-wheel" id="timerWheel">...</div>
    <div class="dial-knob" id="timerKnobEl">...</div>
  </div>
  
  <!-- 底部操作按钮 -->
  <div class="action-btns">
    <button class="btn btn-primary" id="startBtn" onclick="toggleTimer()">开始</button>
    <button class="btn btn-danger" id="finishEarlyBtn" style="display:none">提前结束</button>
  </div>
  
  <!-- 占位与完成提示 -->
  <div class="timer-display" id="timer-display" style="display:none">00:00</div>
  <div class="confirm-area" id="confirmArea">...</div>
</div>
```

**数学对齐验证**:
- `.timer-dial-row` 样式：
  ```css
  .timer-dial-row {
    display: flex;
    flex-direction: row;
    align-items: center; /* 严格中心对齐 */
    justify-content: center;
  }
  ```
- `.activity-wheel` 高度调整为与当前旋钮高度匹配或保持对称（例如固定高度 180px 或 200px）。
  - 当 `.activity-wheel` 高度为 $H_{\text{wheel}}$ 时，选中项中线位于 $\frac{H_{\text{wheel}}}{2}$。
  - `.dial-knob` 是正圆形，圆心位于 $\frac{H_{\text{knob}}}{2}$。
  - 在 `align-items: center` 容器中，两者的中心线完全重合！
- **对齐误差**:
  $$|Y_{\text{wheel-selected-center}} - Y_{\text{dial-face-center}}| = \mathbf{0\text{px}}$$
  在所有屏幕尺寸、任何字体和按钮变化下，**永久保持 0 像素误差**。

### 3.2 C2 间距常量规范 (分设备数值)

消除贴脸感，在 `.timer-dial-row` 内部设置规范的 `gap`。基于 `DESIGN.md` 的间距 token（`sm=8px / md=16px / lg=24px`），针对 4 个目标设备定义明确间距：

| 设备分辨率与环境 | 旋钮尺寸 `--knob-size` | Wheel 宽度 | Wheel 与 Dial 间距 `gap` | 依据与触控舒适度 |
|---|---|---|---|---|
| **iPad mini 竖屏** (744×1133) *主设备* | 168px | 84px | **16px** (`gap: 16px`) | 符合 token `md=16`，手指拖拽旋钮边缘不会误触滚轮最右项 |
| **iPad mini 横屏** (1133×744) | 180px | 84px | **18px** | 宽屏视觉平衡，呼吸感强 |
| **Mac 桌面** (1728×1117) | 180px | 88px | **20px** | 鼠标交互与大视窗最佳视觉间距 |
| **iPhone Safari** (440×956) | 148px | 76px | **12px** | 窄屏防横向溢出，紧凑但不挤靠 |

---

## 4. 结构依存方案 (C3 结构设计)

为了让 activity-wheel 和 dial-knob 呈现出“**一体化时间输入仪表**（Cohesive Time Selector Instrument）”的专业质感，设计以下 3 种方案：

### 选项 1: 一体化胶囊座舱 (Unified Instrument Capsule) — 【推荐】

```
┌────────────────────────────────────────────────────────────┐
│                    ⏱️ 主 计 时                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │  ┌──────────────┐         ┌──────────────────────────┐ │ │
│ │  │   8  - - -   │         │       \   |   /          │ │ │
│ │  │   9  - - -   │   16px  │     -   .---.   -        │ │ │
│ │  │ [10] ======= │ ──────> │    |   ( 10  )   |       │ │ │
│ │  │  11  - - -   │  间距   │     -   '---'   -        │ │ │
│ │  │  12  - - -   │         │       /   |   \          │ │ │
│ │  └──────────────┘         └──────────────────────────┘ │ │
│ │   左侧凹槽滚轮轨              右侧拟物表盘旋钮           │ │
│ └────────────────────────────────────────────────────────┘ │
│                     [ 开始练习 ]                           │
└────────────────────────────────────────────────────────────┘
```

- **视觉描述**:
  - 在 `.timer-dial-row` 外层包裹 `.timer-instrument-pod` 胶囊容器。
  - **背景**: 采用 `linear-gradient(180deg, #FFFDF8 0%, #F5EDE0 100%)`，带极轻内阴影 `box-shadow: inset 0 1px 3px rgba(0,0,0,0.05)`，形成仪表座舱感。
  - **边框**: `1.5px solid #E8D8B0`，圆角 `24px`，padding `12px 16px`。
  - **左侧滚轮区**: 作为“凹槽输入舱（Recessed Bay）”，背景为微淡色 `#F9F4EB`，给滚轮一个明确的物理滑动轨道边框。
  - **右侧旋钮区**: 嵌在胶囊右侧，旋钮自带的 `box-shadow` 投影自然落在底板上。
- **优点**:
  - 最符合 Dad 提出的“整体 UI 结构依存”要求，一眼即知两部分同属于一个输入仪器。
  - 格式塔“共同区域原则（Common Region Principle）”，从心理学上消除拼凑感。
  - 样式仅需纯 CSS，结构极其稳定。
- **代价**:
  - 横向增加约 `24px` 的容器 padding，需确保在 iPhone 440px 宽下不溢出（经计算，440px 下 76px wheel + 12px gap + 148px knob + 24px pad = 260px，远小于 440px，安全无溢出）。

---

### 选项 2: 卫星同轴轨道拱桥 (Orbital Connector Bridge)

- **视觉描述**:
  - 不做大框包裹，而是在 activity-wheel 与 dial-knob 之间架设一条水平的“机械连桥（Bridge Plate）”。
  - 连桥高度等于选中项的高度（34px），从 wheel 的选中指示器（`.wheel-indicator`）水平延伸，与 dial-disc 的外边缘精确相切相接。
  - 连桥采用金属/掐丝金边材质 `linear-gradient(90deg, #E8D8B0, #D4AF37)`。
- **优点**:
  - 具有极强的机械联动感，直观传达“左侧当前项正是右侧表盘当前值”的物理连接关系。
- **代价**:
  - 视觉线条偏繁复，若设备缩放或有 1px 渲染抖动容易导致接缝瑕疵，开发维护成本较高。

---

### 选项 3: 共享刻度尺贯穿线 (Unified Datum Baseline)

- **视觉描述**:
  - 保持背景完全透明，但在 wheel 和 dial 的中线上绘制一条贯穿两者的细微金色基准线（Datum Baseline，`#E8D8B0`，1px dashed）。
  - wheel 的指示条与 dial 刻度的 9 点钟标记（-90deg）共线。
- **优点**:
  - 视觉最轻量，不增加任何背景层级。
- **代价**:
  - 结构依存感最弱，在儿童应用中缺乏玩具般的实体包裹感，无法彻底解决 Dad“看起来不像一个整体”的痛点。

---

### 结构方案推荐
**强烈推荐 选项 1（一体化胶囊座舱）**。  
*原因*: 它直接解决了 Dad 提出的“两个元素不像组成一个整体 UI”的核心诉求。通过底板的统一框定，将滚轮与旋钮组合成类似高端儿童学习机/专业音乐节拍器的“控制台”，既整洁、又稳固，完全符合 dizicute 暖白与圆润的品牌规范。

---

## 5. 精确步进交互方案 (C4: S1 vs S2 设计)

Dad 指出：“左侧有数字可以点击一次就增减1，这样更准确，同时也保留了拖动进度圆弧进行时间选择”。  
这包含两个层面的理解，我们分别设计并提供明确对比与结合方案：

### 5.1 方案 S1: 显式 +/-1 步进器按钮 (Explicit Micro Steppers)

- **形态**:
  - 在滚轮列的上方和下方，各增加一个轻量级的圆形步进微调按钮：上方为 `+1`（向上加 1 分钟），下方为 `−1`（向下减 1 分钟），或者位于滚轮指示器旁边。
  - 按钮尺寸：`28×28px`，背景 `#FFF8F0`，边框 `1px solid #E0D0A0`，文字 `#8B6914`，点击带 `scale(0.92)` 触控反馈。
- **逻辑**:
  - 点击 `+1`: `setValue(Math.min(max, currentValue + 1))`。
  - 点击 `−1`: `setValue(Math.max(min, currentValue - 1))`。
  - 触发两端同步更新（旋钮转动 + 滚轮滚动）。
- **优缺点**:
  - *优点*: 目标极明确，盲操不会点错数字。
  - *缺点*: 纵向增加了 2 个按钮，挤占了 wheel 的有效可视高度，在 200px 容器内显得局促。

---

### 5.2 方案 S2: 轮盘单数点选与行高触控放大 (Enhanced Wheel Direct-Tap) — 【推荐】

Dad 的原话是：*“左侧有数字可以点击一次就增减1，这样更准确”*。在现有代码中，左侧滚轮正是数字列表（5..30），点击任意数字就已经能切换时间。现有体验的问题在于：
1. 当前 `.wheel-item` 触摸高度只有 **34px**（[practice.html:230](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L230)），低于 iOS 人机交互指南推荐的 **44px** 最小触控区域，手指容易点不准或误触相邻项。
2. 非选中项透明度较低，缺少明确的可点击提示感。

**S2 优化设计**:
- **触控区域扩充**:
  - `.wheel-item` 物理高度保持 36px，但通过 `::before` 伪元素将点击响应区域扩大至 **44px**（`top: -4px; bottom: -4px;`）。
- **单步可预测性**:
  - 选中项（如 10）的正上方是 9，正下方是 11。
  - 用户只需点击选中项上方的数字，立即精确减 1（触发 `updateWheel(true)` 弹性滚入）；点击下方数字，立即精确加 1。
  - 点击动画：增加 150ms 的轻微轻触高亮反馈。
- **步进精度保证**:
  - `values` 数组保持为连续整数 `[5, 6, 7, ... 30]`，不存在任何跳跃值。每一个整数都可以单次点击直达。

---

### 5.3 步进交互推荐与最终组合
**推荐采用「以 S2 为主，配合滚轮刻度点击」**。  
Dad 喜欢的正是“看着左侧的数字列表，直接点相邻数字就加减1”的直接映射感（Direct Manipulation）。无需在外部画蛇添足加 +/- 按钮，只需将 `.wheel-item` 的点击响应高度提升至 **44px**，并强化相邻项的视觉可点击性，即可完美兑现“点击一次增减1”的精准要求。

---

## 6. Idle -> Running (方案 B) 动效交接规格

Dad 已确认采用方案 B「极简数字」（旋钮缩小收起，中央展开 56px 大字倒计时 + 4px 横向进度条）。必须严格定义退场、入场及反向恢复的动画参数。

### 6.1 退场动效 (Idle Exit: 耗时 250ms)

当点击「开始」按钮（[practice.html:1924](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1924)）且校验通过时：

1. **`.activity-wheel` (左侧滚轮)**:
   - 动画：向左平移 `20px` 并淡出。
   - 参数：`gsap.to('#timerWheel', { opacity: 0, x: -20, duration: 0.22, ease: 'power2.in' })`。
2. **`#timerKnobEl` (右侧旋钮)**:
   - 动画：向中心缩小并淡出。
   - 参数：`gsap.to('#timerKnobEl', { opacity: 0, scale: 0.6, duration: 0.25, ease: 'back.in(1.4)' })`。
3. **`.timer-instrument-pod` (座舱容器)**:
   - 动画：高度平滑自适应，去除多余内边距。

### 6.2 入场动效 (Running Entrance: 耗时 320ms, 延迟 100ms 触发)

新展开运行态容器 `#timerRunningDisplay`（位于座舱内部中央）：

1. **倒计时大字 (56px)**:
   - 样式：`font-size: 56px; font-weight: 800; color: #2C3E50; letter-spacing: -1px; font-variant-numeric: tabular-nums;`
   - 动画：从 `scale(0.8)` 弹性放大至 `1.0`，透明度 0 变 1。
   - 参数：`gsap.fromTo('#runningCountdownText', { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.32, ease: 'back.out(1.7)', delay: 0.08 })`。
2. **横向进度条 (4px 槽)**:
   - 样式：底槽 `background: #E8D8B0; height: 4px; border-radius: 2px; width: 180px; margin: 8px auto 0; overflow: hidden;`
   - 填充条：`background: #FF6B6B; height: 100%; width: 0%; transition: width 0.3s linear;`
   - 参数：宽度根据 `(elapsed / (duration * 60)) * 100%` 实时更新。
3. **按钮态切换**:
   - `#startBtn` 文案变更为「暂停」，背景保持 `#4ECDC4`。
   - `#finishEarlyBtn` 平滑淡入显示（`display: inline-block; opacity: 1`）。

### 6.3 反向恢复动效 (Reverse Handoff: 结束/放弃/重置)

当用户点击「放弃」、弹窗取消或计时重置时（`resetTimer()` / `abortFinishEarly()`）：

1. **运行态大字与进度条**:
   - 动画：`gsap.to('#timerRunningDisplay', { opacity: 0, scale: 0.85, duration: 0.2, ease: 'power2.in', onComplete: () => hide() })`。
2. **滚轮与旋钮恢复 (弹出入场)**:
   - 旋钮：`gsap.fromTo('#timerKnobEl', { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.35, ease: 'back.out(1.7)' })`。
   - 滚轮：`gsap.fromTo('#timerWheel', { opacity: 0, x: -20 }, { opacity: 1, x: 0, duration: 0.3, ease: 'power2.out' })`。
   - 中央数值恢复默认分钟数显示。

### 6.4 绝对不触碰的安全语义清单 (DON'T TOUCH)

以下业务核心安全逻辑在动画重构中**严格保持原样，分毫不动**：
1. **`#timerProtectModal` 页面离开拦截**: `beforeunload` 与侧边栏路由跳转时的拦截弹窗（[practice.html:938-947](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L938-L947)）。
2. **`timerRunning` 运行态标记**: 变量作为全页面守卫开关，必须在动画开始第一帧同步置位（[practice.html:1336](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1336)）。
3. **暂停态保留 `elapsed`**: `paused = true` 时停止 interval 但绝不清零 `elapsed`（[practice.html:1905-1912](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1905-L1912)）。
4. **提前结束弹窗与取消恢复**: `cancelFinishEarly()` 从全局 `finishSavedElapsed` 恢复计秒（[practice.html:2045-2060](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L2045-L2060)）。
5. **正常结束防自动提交**: 计时到点必须弹窗等待用户确认（[practice.html:1992-1997](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1992-L1997)）。

---

## 7. 落地清单 (按执行顺序)

| 序号 | 文件 | 锚点行 | 具体改动内容 |
|---|---|---|---|
| **Step 1** | `practice.html` | L136-155 | 重写 `.picker-card` CSS：从单列混合改为两层布局，新增 `.timer-instrument-pod`（座舱背景、内阴影、圆角 24px、边框 `#E8D8B0`）。 |
| **Step 2** | `practice.html` | L1040-1060 | 调整 HTML DOM 结构：把 `.picker-label` 移到座舱上方居中；在座舱内创建 `.timer-dial-row`，把 `#timerWheel` 和 `#timerKnobEl` 并列放入其中；`.action-btns` 置于座舱下方。 |
| **Step 3** | `practice.html` | L217-226 | 调整 `.activity-wheel` CSS：高度设定为与旋钮视觉平衡的 `180px`（在 iPad 竖屏与 168px 旋钮高度相当），设置 `display: flex; align-items: center` 确保数学中线与旋钮圆心在同一水平基准线。 |
| **Step 4** | `practice.html` | L227-238 | 调整 `.wheel-item`：高度设为 36px，加 `::before` 扩充触控热区至 44px；优化文字字阶，让数字更清晰易读。 |
| **Step 5** | `practice.html` | L848-878 | 响应式断点更新：在媒体查询中定义 4 个设备的 `gap` 常量（iPad 16px、Mac 20px、iPhone 12px），确保手机端 440px 宽度无横向滚动条。 |
| **Step 6** | `practice.html` | L1052 | 在座舱内部增加方案 B 运行态容器 `#timerRunningDisplay`（含 56px 倒计时大字与 4px 进度条），默认 `display: none`。 |
| **Step 7** | `practice.html` | L1924-1937 | 在 `toggleTimer()` 首次开始中集成 GSAP 退场与入场动画：wheel/knob 缩小退场，展开 `#timerRunningDisplay`。 |
| **Step 8** | `practice.html` | L1876-1900 | 在 `resetTimer()` 中集成反向恢复动画：隐藏倒计时，wheel/knob 带 `back.out(1.7)` 弹性恢复展示。 |
| **Step 9** | `practice.html` | L2046-2086 | 在 `cancelFinishEarly()` 与 `abortFinishEarly()` 中处理对应状态恢复，确保数据与视觉一致。 |

---

## 8. 机械化验收标准 (分设备)

每个验收条目均为客观可测量的指标：

### 1. 垂直对齐精度 (C1 验收)
- [ ] **所有设备**: 在 Chrome / Safari DevTools 下审查元素，`Math.abs(timerWheel.selectedItem.centerY - timerKnobEl.dialFace.centerY) <= 1px`（允许 1px 亚像素舍入误差，绝不允许出现 14px 的肉眼错位）。

### 2. 水平间距与防溢出 (C2 验收)
- [ ] **iPad mini 竖屏 (744×1133)**: `.activity-wheel` 右边界与 `.dial-knob` 左边界间距测得精确为 `16px ± 0.5px`。
- [ ] **Mac (1728×1117)**: 间距测得为 `20px ± 0.5px`。
- [ ] **iPhone (440×956)**: 间距测得为 `12px ± 0.5px`；检查 `document.documentElement.scrollWidth <= 440px`，无横向溢出。

### 3. 结构一体性 (C3 验收)
- [ ] `.timer-instrument-pod` 正常包裹 wheel 与 dial，呈现完整的座舱底板边框与圆角，视觉边界整齐闭合。

### 4. 精确步进操作 (C4 验收)
- [ ] 点击选中项正上方数字，当前时长立即精确减 1（例如 10 变为 9），旋钮刻度与中央数字无滞后同步变动。
- [ ] 点击选中项正下方数字，当前时长立即精确加 1（例如 10 变为 11）。
- [ ] `.wheel-item` 触控热区高度经测量 $\ge 44\text{px}$。
- [ ] 拖拽表盘弧线连续选值依然完全可用，松手即吸附。

### 5. 方案 B 动效与安全守卫 (C5 验收)
- [ ] 点击「开始」后，wheel 向左淡出（约 0.22s），knob 缩小消失（0.25s），大字 56px 倒计时弹入，横向进度条从 0% 顺畅前行。
- [ ] 计时中触发页面返回/离开，`#timerProtectModal` 依然可靠弹窗拦截。
- [ ] 暂停再继续，时间秒数与进度条准确衔接，无跳变或归零。
- [ ] 提前结束中点击「继续练」，倒计时大字与进度条立即恢复，`elapsed` 无损。

---

## 9. 不做清单与风险控制

### 9.1 明确不做清单 (Non-Goals)
1. **不做方案 A/C 的功能回滚**: 严格按照 Dad 选定的方案 B 推进，不保留环形呼吸进度弧或赛博 glitch 动效。
2. **不动 Session-Panel**: 速度（♪/♩、BPM）选择器与练习内容标签区域不在本期改动范围内。
3. **不动打卡与数据存储**: `submitPractice()` 接口与 CST ISO 时间戳逻辑完全保持原样。
4. **不引入新颜色或外部图标库**: 所有色值来自 `DESIGN.md`，图标全用项目现有的内联 SVG。

### 9.2 潜在风险与缓解对策

| 风险项 | 影响评估 | 缓解对策 |
|---|---|---|
| **iPhone 440px 宽度拥挤** | 中 | 保持旋钮 148px、wheel 76px、gap 12px，总占用 260px，并在必要时微调 padding，确保小屏安全。 |
| **GSAP 快速连击状态竞态** | 低 | 在动画执行期间对开始按钮做轻度节流（150ms 冷却），防双击导致 timeline 混乱。 |
| **触控滚动与点击冲突** | 低 | `createActivityWheel` 中已有移动阈值判断（$|dy| > 25\text{px}$ 才算滑动），点击判断由 click 触发，二者天然解耦。 |
