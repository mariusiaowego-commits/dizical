# demo v38 · 审美、两模式架构与单一真源方案（agy 总体方案 · 终审版）

> **作者**：agy（审美、架构与复杂思考）  
> **复核/取证输入**：Codex 取证档案（`PLAN-v38-取证与架构.md` 含第二轮 5.1~5.8 追加取证）  
> **基准参考**：`科目卡片参考-04.jpg`（4096×4096 原始审美标杆）、`dashboard-skin-01.html`（早期表扬基准版）  
> **服务运行环境**：Chromium / http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html（PID 43307 持续在线）  
> **状态**：方案编制完成（**严禁动任何代码**，等待 Codex 交叉复核与 dad 最终拍板后进入实施）

---

## 目录

1. [仪表盘审美规格：同心几何、浮空按钮与极细下标](#1-仪表盘审美规格同心几何浮空按钮与极细下标)
2. [组合架构治理与统一 Schema（应对 5.1 六卡失踪与 5.2 乱序）](#2-组合架构治理与统一-schema应对-51-六卡失踪与-52-乱序)
3. [两模式布局架构：横向扩展卡片 vs 纵向无限 Feed 流（6 卡 × 2 模式 = 12 份规格）](#3-两模式布局架构横向扩展卡片-vs-纵向无限-feed-流)
4. [单一真源方案：消灭模板漂移与闭环防回归](#4-单一真源方案消灭模板漂移与闭环防回归)
5. [对 Codex 取证档案根因判定的审查与补全（含 5.4、5.5、5.7 真实定位）](#5-对-codex-取证档案根因判定的审查与补全)
6. [动效时序方案：严格串行插卡（针对 5.8 重叠）与从槽抽卡物理动效](#6-动效时序方案严格串行插卡针对-58-重叠与从槽抽卡物理动效)
7. [分阶段实施计划与验收红线](#7-分阶段实施计划与验收红线)

---

## 1. 仪表盘审美规格：同心几何、浮空按钮与极细下标

用户在图像 1 及补充意见中明确指出：
1. **± 加减号位置又不对了**：之前表扬过那一版样式，要"更凸显阴影、像叠在黑色空间上面"。
2. **上面的 arc 被搞没了**：为什么乱改。
3. **knob 本来和上面的 arc 有圆弧关系**：以 `科目卡片参考-04.jpg` 为准。
4. **title-col 里"分钟"下标字太粗太大**：要求极细字体、缩小、按下标做。

### 1.1 同心几何公式（替换失效的 `wantBelow` JS 补丁）

#### 为什么当前的 `wantBelow` JS 补丁必崩？
当前代码在 `layoutArc()`（`canvas-01.html:7814`）试图用 JS 读取 DOM 盒坐标，计算 `delta = (kcy - pr.bottom) - wantBelow`，再给 `#mid` 赋内联样式 `marginTop`。然而：
1. `html.cz-fill .mid { margin-top: 16px !important; }`（第 16311 行）是带 `!important` 的全局注入，JS 内联样式直接被样式表碾压。
2. 导致旋钮圆心比面板底边下沉了 80px（`dy = 80px`），使得切线偏移 `fx_offset = sqrt(max(0, (R+r)² - (dy+r)²))` 负溢出归零，SVG `clip-path` 的圆弧凹口退化成一条横直线。
3. 动态 JS 计算 `maskImage: radial-gradient(circle at 50% 283px)` 的圆心打在面板高 203px 之外，挖孔完全打空。

#### 纯 CSS 声明式同心几何公式（彻底抛弃 JS 补丁）
在视觉物理上，面板缺口圆心、刻度点弧圆心、大旋钮圆心必须在空间上**三心合一**，固定在**面板盒的底边缘中点** $(x = 50\%, y = 100\%)$。

```
                    ┌───────────────────────────────┐
                    │  Panel (Dark Space, Masked)   │
                    │                               │
                    │   R_notch = 110px (挖孔半径)   │
           ─────────┴─────────┐           ┌─────────┴─────────  y = Panel Bottom
                              │  R_arc=96 │
                      ░░░░░░░░│           │░░░░░░░░   (同心刻度点弧)
                    ░░         ▼         ▼         ░░
                   ░   ╭───────────────────────╮     ░
      [ − ] Button │   │  Knob (R_knob = 84px) │     │  [ + ] Button
    (58px Obsidian)│   │                       │     │ (58px Obsidian)
      (同水平轴)   ░   ╰───────────────────────╯     ░    (同水平轴)
                    ░░                             ░░
                      ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

**几何参数比例定义**：
- **宽视口 / 宽栏**（卡宽 $\ge 380\text{px}$）：
  - 旋钮半径：$R_{\text{knob}} = 84\text{px}$（直角直径 $168\text{px}$）
  - 刻度点弧半径：$R_{\text{arc}} = R_{\text{knob}} + 12\text{px} = 96\text{px}$（刻度点直径 $5\text{px}$，环绕角度 $-120^\circ \sim +120^\circ$）
  - 面板底部挖孔半径：$R_{\text{notch}} = R_{\text{arc}} + 14\text{px} = 110\text{px}$（留出 14px 纯净暗腔气口）
  - 倒角过渡平滑半径：$r_{\text{fillet}} = 16\text{px}$
- **紧凑视口 / 窄栏**（卡宽 $< 380\text{px}$）：
  - 旋钮半径：$R_{\text{knob}} = 68\text{px}$（直径 $136\text{px}$）
  - 刻度点弧半径：$R_{\text{arc}} = 78\text{px}$
  - 面板底部挖孔半径：$R_{\text{notch}} = 90\text{px}$
  - 倒角过渡平滑半径：$r_{\text{fillet}} = 12\text{px}$

#### 具体 CSS 变量与结构实现（无需 JS 介入位置计算）

```css
/* 1. 变量驱动同心体系 */
:root {
  --dash-knob-r: 84px;
  --dash-arc-r: 96px;
  --dash-notch-r: 110px;
}
@container (max-width: 379px) {
  :root {
    --dash-knob-r: 68px;
    --dash-arc-r: 78px;
    --dash-notch-r: 90px;
  }
}

/* 2. 面板底边圆形缺口：永远以 50% 100%（底边中点）为圆心，零漂移 */
.panel {
  position: relative;
  z-index: 1;
  /* 移除所有 JS 动态注入的 clipPath 补丁，采用原生 CSS 渐变 mask */
  -webkit-mask-image: radial-gradient(
    circle var(--dash-notch-r) at 50% 100%,
    transparent calc(var(--dash-notch-r) - 1.5px),
    black var(--dash-notch-r)
  );
  mask-image: radial-gradient(
    circle var(--dash-notch-r) at 50% 100%,
    transparent calc(var(--dash-notch-r) - 1.5px),
    black var(--dash-notch-r)
  );
}

/* 3. 中轴旋钮行：负 margin 严格等于旋钮半径，把旋钮物理圆心精确拉上面板底边 */
.mid {
  position: relative;
  z-index: 2;
  margin-top: calc(-1 * var(--dash-knob-r)) !important; /* 强制覆盖掉错误的 16px !important */
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: visible !important;
}

/* 4. 刻度点弧：绝对定位，圆心锁死在旋钮圆心 */
.arc {
  position: absolute;
  left: 50%;
  top: var(--dash-knob-r); /* 即 mid-row 旋钮的竖向中心 */
  width: 0;
  height: 0;
  pointer-events: none;
}
.arc i {
  position: absolute;
  width: 5px;
  height: 5px;
  margin: -2.5px 0 0 -2.5px;
  border-radius: 50%;
  background: var(--dash-dot);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4);
}
.arc i.is-on {
  background: #FFFFFF;
  box-shadow: 0 0 6px rgba(255, 255, 255, 0.85);
}
```

*JS 瘦身说明*：彻底删除 `canvas-01.html:7814-7920` 那些算 `wantBelow`、`delta`、`clipPath` 字符串拼接的脏逻辑；JS 只保留纯数学计算给 `.arc i` 算角度 $\theta_i$ 并通过 `transform: translate(cos*R, sin*R)` 摆点，点数固定 27 个。

---

### 1.2 ± 按钮恢复：深色黑曜石浮空圆盘与复合阴影

当前被改坏的样式是：44px 扁平白底弱阴影圆纽，被推到面板下方 80px 孤立放置。  
**恢复标准**：严格对齐 dad 认可的原始表扬版（`dashboard-skin-01.html:258-270`），并增强"悬浮在黑色空间之上"的双层投射光影。

#### 规格参数
- **尺寸**：直径 $58\text{px}$（紧凑视口 $48\text{px}$），正圆 `border-radius: 50%`。
- **与旋钮的轴心关系**：与旋钮处于同一水平中心线，`gap: clamp(18px, 4cqw, 48px)`。
- **盘体色彩（两层微渐变）**：
  - 浅色/深色模式统一深黑曜石微弧面：`linear-gradient(180deg, #2A3036 0%, #101316 100%)`。
  - 顶圈极细高光内边框：`1px solid rgba(255, 255, 255, 0.18)`。
- **符标 Glyph**：
  - 极细极简 `+` 与 `−`，字号 $26\text{px}$（紧凑 $22\text{px}$），字重 `font-weight: 350`，色彩采用暖象牙白 `#FFF8F0`。
- **浮空核心：复合多层漫反射阴影（Composite Shadow）**：
  不仅有外投射，还有内凹槽反射，营造悬浮质感：
  ```css
  .round {
    flex: 0 0 auto;
    width: 58px;
    height: 58px;
    border-radius: 50%;
    border: 1px solid rgba(255, 255, 255, 0.18);
    background: linear-gradient(180deg, #2A3036 0%, #101316 100%);
    color: #FFF8F0;
    font-size: 26px;
    font-weight: 350;
    line-height: 1;
    display: grid;
    place-items: center;
    cursor: pointer;
    touch-action: manipulation;
    user-select: none;
    /* 复合四重阴影：内高光 + 内底深阴影 + 接触小硬影 + 悬浮大漫反射 */
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.25),
      inset 0 -2px 4px rgba(0, 0, 0, 0.40),
      0 4px 8px rgba(16, 20, 24, 0.35),
      0 12px 24px -2px rgba(16, 20, 24, 0.45);
    transition: transform 120ms ease, box-shadow 120ms ease;
  }
  .round:active:not(:disabled) {
    transform: scale(0.95) translateY(2px);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.15),
      inset 0 -1px 2px rgba(0, 0, 0, 0.30),
      0 2px 4px rgba(16, 20, 24, 0.30),
      0 6px 12px -1px rgba(16, 20, 24, 0.35);
  }
  ```

---

### 1.3 `title-col` 的"分钟"下标规格（回应 Codex 5.4 取证）

**Codex 5.4 实测取证量化**：
- 节点：`#readoutUnit`（`canvas-01.html:7500`）
- 现状数值：字号 26px，字重 700，宽 53px，占大数字高度的 50%。
- **核心矛盾**：左侧大数字 `#readoutDigits` 是 SVG 空心单线数字（stroke 1.4~1.8px），视觉线宽极细；而"分钟"用 700 实心粗体，笔画厚度达到 4~5px，**视觉线宽比高达 1:6，是数字主体的 6 倍重**！彻底喧宾夺主。

**规格重构**：
- **字重**：极细（`font-weight: 250`，绝对禁止 700 粗体），笔画视觉厚度降至 1~1.5px，与空心数字线宽比降为约 1:1.2。
- **字号**：降为 **`13px`**（大数字高度的 1/4）。
- **基线对齐**：标准下标沉降（`vertical-align: sub`），下边缘与大数字数字基线平齐，留白 $6\text{px}$。
- **色彩与不透明度**：颜色用中性面板浅字带微透明度 `rgba(255, 248, 240, 0.65)`。
- **CSS 落地**：
  ```css
  .readout-line {
    display: inline-flex !important;
    align-items: baseline !important;
    position: relative !important;
  }
  .readout-unit,
  html.cz-fill .readout-unit {
    position: relative !important;
    left: auto !important;
    bottom: 0 !important;
    margin-left: 6px !important;
    font-size: 13px !important;
    font-weight: 250 !important;
    letter-spacing: 0.04em !important;
    color: rgba(255, 248, 240, 0.65) !important;
    line-height: 1 !important;
    transform: translateY(2px) !important; /* 下标微下沉 */
    pointer-events: none !important;
  }
  ```

---

### 1.4 浅色（Light / 暖白银灰）与深色（Ink / 深墨黑金）两套 Token 对齐表

| Token 名称 | 浅色皮肤（Light） | 深墨皮肤（Ink） | 审美作用 |
|---|---|---|---|
| `--dash-panel` | `#1C1E21`（深碳色，保持专业声学仪表底） | `#14181C`（极深墨底） | 仪表盘中央深色屏幕区 |
| `--dash-panel-text` | `#F7F4EF`（象牙白，对比度 14:1） | `#FFF8F0`（暖白） | 屏幕区主数字、主文字 |
| `--dash-panel-dim` | `rgba(247, 244, 239, 0.55)` | `rgba(255, 248, 240, 0.55)` | "分钟"下标、副标题、刻度线底轨 |
| `--dash-btn-face-hi` | `#3A3E44` | `#2A3036` | ± 悬浮按钮顶面微光 |
| `--dash-btn-face-lo` | `#14171A` | `#101316` | ± 悬浮按钮底面深阴影 |
| `--dash-btn-glyph` | `#F7F4EF` | `#FFF8F0` | ± 符号极细线 |
| `--dash-btn-shadow` | `rgba(20, 24, 28, 0.35)` | `rgba(0, 0, 0, 0.65)` | 悬浮外投射漫反射阴影 |
| `--dash-knob-hi` | `#4A5058` | `#3A4148` | 大旋钮拉丝顶光 |
| `--dash-knob-lo` | `#121417` | `#0E1114` | 大旋钮底面暗区 |
| `--dash-dot` | `rgba(255, 255, 255, 0.32)` | `rgba(255, 248, 240, 0.28)` | 点弧静止点点阵 |
| `--dash-dot-on` | `#FFFFFF`（带 0 0 6px 辉光） | `#FFFFFF`（带 0 0 8px 辉光） | 点弧激活点 |

---

## 2. 组合架构治理与统一 Schema（应对 5.1 六卡失踪与 5.2 乱序）

Codex 在第 5 节追加取证中揭露了两个极其严重的架构隐患：
- **5.1 组合定义与渲染不一致**：预设 ③ 宣称是"全右栏六卡"（`PRESETS['3'] = ['A','B','S','D','R','Q']`），但实际渲染时 `COMBO_MODS['3']` 只有 4 张卡，**S 和 Q 根本没有 DOM 节点**！
- **5.2 纵向 Feed 模式视觉顺序错乱**：在 744/440 下，DOM 顺序明明是 A $\to$ B $\to$ D $\to$ R，但屏幕视觉渲染出来的顺序却是 A $\to$ D $\to$ R $\to$ **B（B 被甩到了最后）**！

### 2.1 根因剖析
1. **六卡失踪根因**：`canvas-01.html` 里存在 3 套互相割裂的数据定义：
   - 顶栏按钮文案（259 行）写"全右栏六卡"；
   - `PRESETS`（16086 行）写 `['A','B','S','D','R','Q']`；
   - `COMBO_MODS` 与 `COMBO_DEFS`（16629 行）却写死了树只有 4 张卡。**没有单一真源，导致六卡承诺从未兑现**。
2. **视觉顺序错乱根因**：第 16584~16590 行有一段暴力硬编码的 CSS：
   ```css
   .cz-mod[data-mod="A"] { order: 2; }
   .cz-mod[data-mod="S"] { order: 3; }
   .cz-mod[data-mod="D"] { order: 4; }
   .cz-mod[data-mod="R"] { order: 5; }
   .cz-mod[data-mod="Q"] { order: 6; }
   .cz-mod[data-mod="B"] { order: 7; } /* B 卡被强制赋予最大 order！ */
   ```
   在窄屏 flex-direction: column 布局下，CSS `order: 7` 强行将全功能节拍器 B 踢到了全页面最底部，破坏了音乐人先看仪表、再看节拍器、后看时长和记录的自然认知流！

### 2.2 解决方案：单一声明式组合架构（Single Declarative Combo Schema）

彻底废除分散的 `PRESETS`、`COMBO_MODS`、`COMBO_DEFS`，统一收拢为单一配置对象 `COMBO_SCHEMA`：

```javascript
const COMBO_SCHEMA = {
  '1': {
    code: 'COMBO_1_COMPACT_BASE',
    label: '① 仪表盘 + 竖条节拍器 + 记录小卡',
    mods: ['A', 'S', 'D', 'R'],
    // 宽屏横向扩展树
    expandTree: {
      kind: 'row', gap: 16,
      kids: [
        { kind: 'astack', w: 440, kids: [
          { kind: 'row', gap: 12, kids: [{ kind: 'mod', k: 'D', w: 214 }, { kind: 'mini', w: 214 }] }
        ]},
        { kind: 'mod', k: 'S', w: 140 } // 坚决保底 140px
      ]
    },
    // 纵向 Feed 流顺序：A (主仪表) -> S (横条 Ribbon) -> D (时长) -> R (记录)
    feedOrder: ['A', 'S', 'D', 'R']
  },
  '2': {
    code: 'COMBO_2_DR_COLUMN',
    label: '② 仪表盘 + 竖条节拍器 + 复合全列 + 要求',
    mods: ['A', 'S', 'D', 'R', 'Q'],
    expandTree: {
      kind: 'row', gap: 16,
      kids: [
        { kind: 'astack', w: 420 },
        { kind: 'mod', k: 'S', w: 140 }, // 坚决保底 140px
        { kind: 'comp', w: 360, kids: [{ kind: 'mod', k: 'D' }, { kind: 'mod', k: 'Q' }] }
      ]
    },
    feedOrder: ['A', 'S', 'D', 'Q', 'R']
  },
  '3': {
    code: 'COMBO_3_FULL_SIX',
    label: '③ 全右栏六卡（真·全量模式）',
    mods: ['A', 'B', 'S', 'D', 'R', 'Q'], // 真正全部包含 6 张卡！
    expandTree: {
      kind: 'row', gap: 16,
      kids: [
        { kind: 'astack', w: 420 },
        { kind: 'mod', k: 'B', w: 340 },
        { kind: 'mod', k: 'S', w: 140 },
        { kind: 'comp', w: 360, kids: [
          { kind: 'mod', k: 'D' },
          { kind: 'mod', k: 'R' },
          { kind: 'mod', k: 'Q' }
        ]}
      ]
    },
    // 纵向 Feed 流权威顺序：严禁乱序甩到最后！
    feedOrder: ['A', 'S', 'B', 'D', 'R', 'Q']
  }
};
```

#### 实施硬约束
1. **彻底删除第 16584~16590 行那些静态 `order: 2~7` 的 CSS 规则**。
2. 纵向 Feed 模式下，直接由 `buildCombo()` 按照当前组合的 `feedOrder` 数组来确定 DOM 插入顺序，实现：
   **`DOM 顺序 == 视觉渲染顺序 == 键盘无障碍 Tab 导航顺序`**。
3. **自动化测试强断言**：在 Playwright 脚本中增加断言：
   `expect(renderedCards.length).toBe(COMBO_SCHEMA[currentCombo].mods.length)`，一旦出现"组合声明了六卡但只渲染四张"立即阻断！

---

## 3. 两模式布局架构：横向扩展卡片 vs 纵向无限 Feed 流

dad 在架构判断中给出根本原则：
> "前期做了太多不同视口的适配工作。其实应该做好的就是每张卡片在**横向扩展卡片模式**与**纵向无限 feed 流模式**两种模式下，针对不同设备宽度高度做好可读性佳、适配不同设备的卡片样式。这样不论什么视口、什么卡片互相组合，都能比较美观与和谐。"

### 3.1 模式判定机制：宿主传导 + 卡片内生响应双闭环

为彻底消灭以往"在外部硬写 1133/744/440 断点导致内部样式到处写死"的弊端，采用 **架构级双闭环**：

```
[ 宿主外层 (Canvas) ] ── 依据布局容器宽度 (列排 vs 行滑)
         │
         ▼ 传导标记
  [ .cz-mod data-layout="expand" | "feed" ]
         │
         ▼ 注入 iframe 根节点
  [ html[data-layout="expand" | "feed"] ]
         │
         ▼ 卡片内部内生裁决
  [ @container (min-width: 350px) / (min-height: 480px) ]
```

1. **内生判定规则**（卡片自身自主裁决）：
   - 卡片根容器统一设定：`container-type: inline-size; container-name: moduleCard;`。
   - 当 `inline-size >= 350px` 且外层允许拉伸时，卡片自动激活 **`Expand`（横向扩展）** 的双栏/多列空间。
   - 当 `inline-size < 350px` 时，卡片内部自动无缝降级为 **`Feed`（流式/紧凑）** 垂直流动。
2. **宿主上下文标记**：
   - 当视口处于宽屏多列组合（如 1133 模式的组合 1/2/3）时，宿主给 iframe 注入 `data-layout="expand"`。
   - 当视口处于纵向堆叠（如 744 竖屏、440 手机单列滚动）时，宿主给 iframe 注入 `data-layout="feed"`。

---

### 3.2 6 张卡 × 2 模式 = 12 份精准布局规格

#### 卡 1：A 仪表盘（Dashboard）
| 模式 | 宽度与高度策略 | 网格与排布 | 字号与视觉阶梯 | 溢出/滚动策略 |
|---|---|---|---|---|
| **Expand 模式** | 宽 $420\text{px} \sim 480\text{px}$，高锁死 $540\text{px} \sim 620\text{px}$（与左侧票夹等高对齐） | 三列屏幕区：`[Cover 92px] [Center 读数+标尺 240px] [Right 老师要求/词句 120px]`；底区同心旋钮 $168\text{px}$ + 悬浮 ± 按钮 $58\text{px}$ + 底部 48 孔喇叭孔阵 | 主数字 60px 镂空细体；下标 13px 极细；说明字 11px；BPM 读数 15px monospace | 面板内部溢出剪裁（圆形缺口 mask）；旋钮与 ± 悬浮突出区 `overflow: visible`；无滚动条 |
| **Feed 模式**（响应 5.3 节奏断裂） | 宽 $100\%$（满宽），高自适应内容（约 $380\text{px} \sim 400\text{px}$，避免 666px 过高挤压） | 单列纵向居中：顶栏状态 -> 封面居左/小数字居右 -> 中轴标尺 -> 紧凑同心旋钮 $136\text{px}$ + ± 按钮 $48\text{px}$ -> 精简 24 孔喇叭孔阵 | 主数字 44px；下标 12px；旋钮等比缩放；喇叭孔阵减行 | `overflow: visible`；整卡随流滚动，卡内零内部滚动条 |

#### 卡 2：S 竖条节拍器（Metronome Strip）—— 响应图像 2、图像 4 及 Codex 5.6
| 模式 | 宽度与高度策略 | 网格与排布 | 字号与视觉阶梯 | 溢出/滚动策略 |
|---|---|---|---|---|
| **Expand 模式**（宽屏组合 2/3 竖排） | 宽度**严格保底 $140\text{px} \sim 160\text{px}$**，**严禁被压扁成 76px**！高度通高对齐票夹（$560\text{px} \sim 620\text{px}$） | 优雅竖排舱：`[顶区 4 拍 LED 阵列 14px]` $\to$ `[垂直居中 48px Tabular 大 BPM 数字]` $\to$ `[速度术语 Allegro 13px，对比度 5.2:1]` $\to$ `[竖排微调按纽 36px]` $\to$ `[底部大圆胶囊主开关 120×48px]` | BPM 48px 加粗数字，高对比可读；术语横排字间距 0.06em；按纽带深色微凸起；补全 DOM 内缺失的 ± 按纽 | 纯竖向静态排布，绝对不挤压，可读性极佳；零溢出 |
| **Feed 模式**（纵向流横向 Ribbon 条） | 宽 $100\%$ 满宽，高度锁定紧凑横条带 **$88\text{px} \sim 96\text{px}$**（严禁膨胀） | 单行横向流：左侧 `[4 拍 LED + 36px BPM]` $\to$ 中间 `[速度术语 + 音色]` $\to$ 右侧 `[− 按钮 + 108px 胶囊开关 + + 按钮]` | BPM 36px；术语 12px；操作按纽 36px 圆形 | 设置面板改为**向下滑动展开抽屉（Drawer）**，**严禁采用绝对定位浮层盖住 `+` 加号按纽**（彻底消除图像 4 缺陷） |

#### 卡 3：B 全功能节拍器卡（Metronome Full）
| 模式 | 宽度与高度策略 | 网格与排布 | 字号与视觉阶梯 | 溢出/滚动策略 |
|---|---|---|---|---|
| **Expand 模式** | 宽 $380\text{px} \sim 420\text{px}$，高与中轴列等高 | 上半区大表盘刻度（直径 $236\text{px}$ SVG）+ 环形点；下半区拍号（2/4、3/4、4/4）+ 节拍细分选择器 | 刻度盘 BPM 52px；术语 14px；拍号胶囊 13px | 静态全景展示，无溢出 |
| **Feed 模式**（响应 5.3 节奏断裂） | 宽 $100\%$，高度控制在 **$260\text{px} \sim 280\text{px}$**（严禁 768px 撑爆整屏） | 表盘等比收敛至 $160\text{px}$，参数切换按钮折为 2×2 网格并排，使与前后的 D、R 卡高度过渡自然 | 表盘 BPM 36px；按纽高度 36px 适合拇指触控 | 自适应内容高度，整卡随流自然滚动 |

#### 卡 4：D 今日练习时长卡（Bauhaus Widget）—— 响应图像 5、补充 5 与 Codex 5.5
| 模式 | 宽度与高度策略 | 网格与排布 | 字号与视觉阶梯 | 溢出/滚动策略 |
|---|---|---|---|---|
| **Expand 模式**（彻底解决 61% 空白） | 宽 $360\text{px} \sim 440\text{px}$，**高度不拉伸，限定内容高 $220\text{px} \sim 250\text{px}$** | **重构为平衡双栏**：<br>• 左栏（核心计时）：日期 $\to$ 空心细体大时钟 `08:26:43` $\to$ 胶囊总时长 `2H 45M`<br>• 右栏（可视化分布）：7 日练习微柱状分布点阵 + 橙色胶囊时间轴线 + 包豪斯双图标 | 空心时钟高 44px 单线镂空；秒数下标 20px；胶囊文字 12px 粗体 | 彻底终结 285px（61%）大白地；卡片高度自适应内容，底边距稳定在 16px |
| **Feed 模式** | 宽 $100\%$，高度紧凑 $150\text{px} \sim 170\text{px}$ | 纵向微模块：第一行日期与总时长；第二行空心时钟单行居中；第三行橙色细虚线时间轴 | 时钟 38px；时间轴高度 24px | 纯紧凑卡片，零多余空白 |

#### 卡 5：R 今日练习记录（Today's Records）
| 模式 | 宽度与高度策略 | 网格与排布 | 字号与视觉阶梯 | 溢出/滚动策略 |
|---|---|---|---|---|
| **Expand 模式** | 宽 $360\text{px} \sim 460\text{px}$，若嵌入复合列则为紧凑 Mini 卡（高约 $140\text{px}$），若独立全列则为大表格 | Mini 态：左侧今日总分钟数（40px 粗体大字），右侧完成科目数徽章，底侧"查看明细"药丸按钮（点击呼出 Popout 弹窗） | 核心大数字 40px；单位 16px；说明 12px | Mini 卡无滚动；点击后在宿主中心呼出带毛玻璃背景的明细弹窗（保证 12 条记录全部 display:block 且无截断） |
| **Feed 模式** | 宽 $100\%$，高度约 $110\text{px} \sim 130\text{px}$ | 横向通栏摘要：左侧日期与累计时长，右侧绿色已完成打勾与"明细清单 >"按钮 | 大数字 32px，单位 14px | 纯触发条，交互与 Expand 一致，弹出大明细弹窗 |

#### 卡 6：Q 老师要求（Teacher Requests）
| 模式 | 宽度与高度策略 | 网格与排布 | 字号与视觉阶梯 | 溢出/滚动策略 |
|---|---|---|---|---|
| **Expand 模式** | 宽 $380\text{px} \sim 440\text{px}$，高约 $320\text{px} \sim 360\text{px}$ | 3D 纸牌堆叠效果（Deck 视角，层叠展示前 3 课，带微旋转与层次阴影，可手势/点击划走翻牌） | 课次标题 16px 粗体；作业要求 13px 书卷体排版 | 卡片自身保持 3D 透视，内部文字超长采用淡出渐变 |
| **Feed 模式** | 宽 $100\%$，高自适应（约 $200\text{px}$） | 扁平折叠卡片（手风琴展开），当前课次高亮置顶，附带语音留言微播放条 | 标题 15px；内容 13px；行高 1.6 | 垂直自然折叠，不搞复杂 3D 视角以防挤压可读性 |

---

## 4. 单一真源方案：消灭模板漂移与闭环防回归

### 4.1 现状病灶深度剖析
Codex 在取证档案中精准揭示了混乱之源：
- 运行时真正被加载执行的代码，全部内联在 `canvas-01.html` 的 `<template id="tpl-A">`、`tpl-B`、`tpl-S`、`tpl-D`、`tpl-R`、`tpl-Q` 内部（行数在 6611 ~ 15800 之间）；
- 而目录中的独立文件 `dashboard-skin-01-v3.html`、`metronome-02-strip.html` 等**全部是历史残存的过期镜像**；
- 当开发者修改独立文件时，demo 没有任何变化；当开发者直接去改 `canvas-01.html` 几千行的内联字符串时，由于缺乏单测和格式化，改动极易失控，且很容易把早期正确的逻辑冲掉。

### 4.2 落地决策：抽取权威公共源 + 构建时自动注入（推荐最佳实践）

```
[ 权威单一源源码目录 ]
docs/demos/practice-right-column-261003/cards/
  ├── card-a-dashboard.html        (仪表盘权威源)
  ├── card-s-metronome-strip.html  (竖条节拍器权威源)
  ├── card-b-metronome-full.html   (全功能节拍器权威源)
  ├── card-d-duration.html         (今日时长权威源)
  ├── card-r-records.html          (练习记录权威源)
  └── card-q-requests.html         (老师要求权威源)
                 │
                 ▼ python3 tools/sync-demo-templates.py
[ 运行时演示总装文件 ]
docs/demos/practice-right-column-261003/canvas-01.html
  ├── <template id="tpl-A"> <!-- AUTO-INJECTED FROM card-a-dashboard.html (SHA256: ...) -->
  ├── <template id="tpl-S"> <!-- AUTO-INJECTED ... -->
  └── ...
```

#### 具体执行机制
1. **源码抽取**：
   在 `docs/demos/practice-right-column-261003/cards/` 建立 6 个独立的单卡 HTML 文件。
   - `card-a-dashboard.html` 直接以最完美的 `dashboard-skin-01.html` 为蓝本回填，补齐同心几何与悬浮 ± 按钮；
   - 彻底废弃并归档旧的 `*-v3.html` 等混淆性文件。
2. **构建注入脚本 (`tools/sync-demo-templates.py`)**：
   - 编写一段轻量 Python 脚本，读取 `cards/card-*.html` 的内容；
   - 寻找 `canvas-01.html` 中各 `<template id="tpl-X">` 的占位标签，进行确定性替换注入；
   - 注入时生成唯一的 SHA256 校验指纹注释，格式如：`<!-- SOT-HASH: card-a-dashboard.html a1b2c3... -->`。
3. **闭环防回归校验脚本（CI / Playwright 前置检查）**：
   - 在所有的自动化测试脚本（如 `verify-demos.py`）中增加前置校验：
     计算 `cards/*.html` 的哈希值，与 `canvas-01.html` 模板内部声明的哈希值做比对。
   - 若检测到有人手动篡改 `canvas-01.html` 内联模板导致哈希不一致，测试直接红灯阻断，并提示：`"检测到内联模板与权威源不同步！请修改 cards/ 下的文件并运行 python3 tools/sync-demo-templates.py"`。

---

## 5. 对 Codex 取证档案根因判定的审查与补全

我对 Codex 在 `PLAN-v38-取证与架构.md` 中的取证事实表示充分认可，结合第二轮追加的实测数据（5.4~5.7），现将具体根因与解决架构完全定型：

### 5.1 审查点 A：边角阴影真实定位（用户图像 3 & Codex 5.7）
- **Codex 5.7 精确定位事实**：
  1. `DIV#pkSlotCavity.pk-slot-cavity`（rect `{x:407, y:61, w:434, h:16}`）：内部带 `rgba(0,0,0,0.95) 0 6px 14px inset` 阴影，被整整三层父容器硬裁切：
     - `DIV.pk-punch-slot-wrap.cz-punch-slot.dash-integrated-slot`（`overflow: hidden`）
     - `DIV.cz-astack-crown.dash-top-rim`（`overflow: hidden`）
     - `DIV.cz-combo`（`overflow: auto`）
  2. `DIV#czRecordsMini.card-records-mini`（rect `{x:630, y:652, w:224, h:220}`）：外投射阴影 `0 12px 28px rgba(44,62,80,.18)` 被 `.cz-node.cz-mod` / `.cz-node.cz-brow` 的 `overflow: hidden` 裁掉下半部。
  3. **Iframe 矩形物理窗口阻断（致命关键）**：每个卡片运行在 iframe 内，卡片自身有 `border-radius: 24px`，但 iframe 作为系统级窗口是**无圆角的锐角矩形**！当卡片外投射漫反射阴影扩散到 iframe 边框时，直接被截断成一条垂直灰直线！
- **agy 架构解法（阴影外提 + 解除硬裁切）**：
  - **外提阴影至宿主卡托**：把各卡片最外层的高斯漫反射（`box-shadow: 0 12px 28px ...`）挂载到宿主文档的 `.cz-node.cz-mod` 上，而不是在 iframe 内部画！让 iframe 内部保持纯净无溢出；
  - **解除三层父容器不合理的 `overflow: hidden`**：`.cz-astack-crown`、`.dash-integrated-slot`、`.cz-brow` 统一设为 `overflow: visible`；
  - **Iframe 外框圆角化**：宿主对 `.cz-mod > iframe` 声明 `border-radius: 24px; overflow: hidden;`，杜绝任何直角灰色边框露底！

### 5.2 审查点 B：D 卡 61% 面积空白（Codex 5.5 取证确认）
- 实测确认：在 1133 组合 1 下，D 卡容器高 469px，内容只排到 y=184px，**底部空白高达 285px（占比 61%）**。
- 确认按照 3.2 节的"平衡双栏"规格重构，将时钟与时间轴并列展开，限高 220px，多余垂直空间由网格自然释放。

### 5.3 审查点 C：S 节拍器 76px 挤压与 3.2:1 低对比度（Codex 5.6 取证确认）
- 实测确认：76px 宽度使 28px 数字边距只剩 19px，灰色 `#666` 对比度 3.2:1 低于标准。
- 确认在 `COMBO_SCHEMA` 中全量推行 `w: 140px` 保底，术语文字提亮至高对比 `#F7F4EF`（墨底）/ `#2C3E50`（浅底），对比度确保 $\ge 5.0:1$。

---

## 6. 动效时序方案：严格串行插卡（针对 5.8 重叠）与从槽抽卡物理动效

### 6.1 严格串行插卡时序编排（回应 Codex 5.8 实测数据）

#### Codex 5.8 实测暴露的硬重叠
实测数据显示：
- `ms = 0`：票夹 h=742，rail op=0.39，卡槽卡 op=0；
- `ms = 80`：票夹开始收，**卡槽卡在 80ms 时就以 op=0.34 提前冒头**；
- `ms = 280`：**卡槽里的卡已经 100% 出现（op=1.00），而此时票夹还在半空中收缩（h=114px）**！  
这就导致人眼看到的不是"把票收好再插卡"，而是"新卡突然在右边变出来，同时左边在乱闪"。

#### 串行时序重构方案（消除重叠窗口，两段式接力）

```
[ 0ms ] ────── (Phase 1: 票夹完全收缩入轨) ────── [ 280ms ] ── (Phase 2: 机械插卡) ── [ 520ms ]
票夹内容瞬淡: 0ms - 100ms (opacity: 1 -> 0, y: -6px)
票夹物理收拢: 0ms - 280ms (宽 360 -> 50px / 高 742 -> 52px, power3.inOut)
卡槽插卡透明度: 保持 0 ! 保持 0 ! 保持 0 ! ──────► [ 260ms 释放 ]
                                                      │
                                                      ▼ 机械插入动效
                                            卡槽暗腔张开: 260ms - 340ms (高 0 -> 18px)
                                            票卡头部插入: 280ms - 480ms (y: -36px -> 0, back.out(1.15))
                                            触点绿灯点亮: 480ms - 520ms (呼吸微闪)
```

**关键指标承诺**：
- **在 `ms = 0 ~ 260ms` 之间，卡槽卡片的 opacity 严格恒等于 0**！
- 只有当票夹收缩完成度达到 $90\%$ 以上时，卡槽插卡才被触发启动；
- 彻底终结"票夹还在收、卡已插好"的倒反天罡现象。

---

### 6.2 计时态展开卡片：从卡槽暗腔抽出的物理动效（From-Slot Draw-Out）

#### 现状缺陷
用户在计时态点击仪表盘顶部的露出条想看科目详情时，当前实现直接 `overlay.style.display = 'flex'`，粗暴弹出一个全屏居中弹窗，没有任何位置线索，毫无"卡片从刚才插入的打卡机槽里抽出来查看"的物理解释。

#### 物理抽卡动效设计（From-Slot Spatial Morphing）

```
                     ┌──────────────────┐
                     │   Screen Center  │
                     │                  │
                     │  Expanded Card   │  <── 终态：完整大卡片居中
                     │   (600 × 520px)  │      (清晰展现科目名、名画、要求)
                     └────────▲─────────┘
                              │
                              │ 向上平滑抽出 + 放大形变
                              │ (360ms, cubic-bezier(0.16, 1, 0.3, 1))
                              │
                    ┌─────────┴─────────┐
                    │ █ Slot Cavity █   │  <── 起点：卡槽物理坐标
                    └───────────────────┘      (rect: x, y, width, 18px)
```

#### 实现技术算法
1. **获取起点物理坐标**：
   在点击露出条瞬间，通过 `slotRect = punchSlotCavity.getBoundingClientRect()` 精确捕获卡槽在视口中的绝对位置 $(x_0, y_0, w_0, h_0)$。
2. **初始化弹窗位置（Ghost Proxy）**：
   浮层弹窗 `#czCardPopup` 初始位置直接钉在 $(x_0, y_0)$，尺寸为 $(w_0, h_0)$，卡片内容被 `clip-path: inset(0 0 85% 0)` 裁切（仅露出顶端 15% 仿造槽内卡头）。
3. **空间插值动画（FLIP 思想）**：
   - 目标终态：视口中心 `left: 50%`, `top: 50%`, `transform: translate(-50%, -50%)`, 尺寸 `min(600px, 90vw) × min(520px, 80vh)`，`clip-path: inset(0 0 0% 0)`。
   - 动画时间：$360\text{ms}$。
   - 缓动曲线：`cubic-bezier(0.16, 1, 0.3, 1)`（苹果风格超平滑流体阻尼，先由槽内迅速拔出，随后优雅减速展开至全屏）。
   - 背景毛玻璃蒙层：`opacity: 0 -> 1`（时长 260ms）。
4. **收回反向动效（Stow Back）**：
   点击"收回槽内"或蒙层时，弹窗沿原轨迹平滑缩小、下沉插回卡槽暗腔内，最终隐去。给孩子极其拟真的卡片抽插交互快感！

---

## 7. 分阶段实施计划与验收红线

### 阶段 1：仪表盘审美规格彻底修复（耗时预估：1.5h）
- **改动范围**：
  - 清理 `canvas-01.html:16311` 等处针对 `.mid`、`.round` 的破坏性 `!important` 覆盖；
  - 面板 `-webkit-mask-image` 恢复为纯 CSS `50% 100%` 径向缺口，`.mid` 恢复 `margin-top: calc(-1 * var(--dash-knob-r))`；
  - 恢复 ± 悬浮按钮为 58px 深黑曜石双层高光阴影盘；
  - 修正 `.readout-unit` 为 13px、字重 250 的极细下标（线宽比降为 1:1.2）。
- **量化验收标准**：
  - [ ] 面板底部缺口与刻度点弧、大旋钮圆心完全重合（误差 $< 0.5\text{px}$）；
  - [ ] ± 按钮具有明显的浮空投影，与旋钮处于同一水平中轴；
  - [ ] "分钟"文字字重 $\le 300$，字号 $13\text{px}$，按下标对齐。

### 阶段 2：边角阴影与宿主容器裁切彻底治理（耗时预估：1h）
- **改动范围**：
  - 解决 5.7 取证指出的 3 处裁切祖先（解除 `pkSlotCavity`、`czRecordsMini` 上的 `overflow: hidden`）；
  - 宿主 `.cz-mod > iframe` 设定 `border-radius: 24px`，大漫反射外提至宿主卡托；
  - 宿主 `.pk-stage-wrap` 增加 16px 呼吸衬垫。
- **量化验收标准**：
  - [ ] 9 个视口组合下，票夹及右侧所有卡片的四个圆角弧线与边框阴影清晰完整呈现，零直角硬切缝；
  - [ ] Playwright 采样：卡槽与卡片边角无 straight-edge clipping 直线裁切。

### 阶段 3：组合 Schema 统一与两模式 12 份规格落地（耗时预估：2.5h）
- **改动范围**：
  - 废除 16584 行恶意 `order: 7`，解决 5.2 节 B 卡被甩到最后的乱序问题；
  - 落地 `COMBO_SCHEMA`，解决 5.1 节组合 3 缺少 S/Q 节点的假六卡缺陷；
  - **S 卡**：在 Expand 宽屏模式下宽度保底 140px，术语对比度 $\ge 5:1$；Feed 模式为 88px 横条带，抽屉向下展开；
  - **D 卡**：Expand 模式落地平衡双栏，将底部 285px（61%）空白彻底清零；
  - 完成 A、B、D、R、Q、S 共 12 份模式规格的代码对齐。
- **量化验收标准**：
  - [ ] 预设 ③ 下真实渲染出 6 个卡片节点（A, B, S, D, R, Q 均存在且可见）；
  - [ ] 744/440 Feed 流下视觉顺序与 DOM 顺序完全一致（A $\to$ S $\to$ B $\to$ D $\to$ R $\to$ Q）；
  - [ ] 1133 组合 2 下，S 节拍器竖条宽度 $\ge 140\text{px}$，可读性优秀；
  - [ ] D 卡在任何横向扩展视口下，卡片底部空白高度 $\le 24\text{px}$。

### 阶段 4：严格串行插卡动效与抽卡物理动效（耗时预估：2h）
- **改动范围**：
  - 重写 `enterRun()` GSAP 时间轴：票夹 0~280ms 收拢阶段，卡槽卡片 opacity 严格锁死为 0；260~500ms 机械插卡接入；
  - 实现 `openCardOverlay()` 与 `closeCardOverlay()` 的物理抽卡动画（基于卡槽实际物理坐标的 FLIP 放大与收回）。
- **量化验收标准**：
  - [ ] 逐 20ms 采样证实：0~240ms 期间卡槽卡片 opacity 均为 0，彻底消除重叠；
  - [ ] 展开卡片时，肉眼清晰可见卡片由打卡机槽口向上滑出并放大居中。

### 阶段 5：单一真源工程化固化与全量防回归（耗时预估：1.5h）
- **改动范围**：
  - 将调优后的 6 张卡抽取至 `cards/card-*.html`；
  - 编写 `tools/sync-demo-templates.py` 注入脚本；
  - 编写自动化校验钩子，确保 `canvas-01.html` 内联模板与权威源 SHA256 绝对一致；
  - 归档过期文件。
- **量化验收标准**：
  - [ ] 运行 `python3 tools/verify-demos.py` 全绿通过；
  - [ ] 篡改测试：手动修改内联字符串，测试必须精准报红阻断。

---

### 回归红线（严防死守、一步不退）
在上述重构实施全过程中，前序版本已通过的硬指标必须 100% 保持，任何一项打破立即回滚：
1. **黑色读数区零重叠**：卡片/卡槽 vs 仪表盘黑色读数区（panel、knob、transport、diagCard）重叠面积 **必须保持 0.0 px²**。
2. **露出比例**：三档视口 1133 / 744 / 440 露出比例 **稳定在 19.5% ~ 20.5%**。
3. **记录弹窗明细**：12 条 `.c-detail` 全部真实可见、文本完整、无截断（`scrollWidth == clientWidth`）。
4. **状态流转无空窗**：`enterRun` 与 `exitRun` 形变过程连续，空窗帧数 $= 0$。

---
*终审方案已就绪，静待 Codex 交叉复核与 dad 批示执行。*
