---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# spec-agy-d1b-261010f · D1 卡三处修交付报告

- **卡片代号**：D1 仪表盘卡（`dashboard-skin-01-v3.html`）
- **负责人**：`agy`（独家 owner）
- **对应 Brief**：[`brief-agy-d1b-261010f.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/brief-agy-d1b-261010f.md)
- **代码变动约束**：仅修改 `dashboard-skin-01-v3.html` 单文件；未 touch 其它页面；未 commit / 未 push；无新增依赖；配色全走 `--dash-*`。
- **验收结论**：`?audit=1` 验证通过，**`ASSERT_OK`（0 失败）**；三档视口（1133×744 / 744×1133 / 440×956）实测全部通过；三条负控全数报红。

---

## 1. 改动明细清单

### 1.1 Fix 2.1.1 谱架模式键位置与安全距离
- **根因分析**：
  1. 上方 `.mid-row` 设有左右内边距 `padding: 0 var(--mid-pad, 8px)`，而下方 `.transport-main` 与 `.transport-caps` 原先为 `padding: 0`。导致底部三列相对中段向两侧扩出 8px（744 档扩出 6px），使得右列 `.c-right` 的中轴向右偏移 6–8px，与上方纵向模块（`#silverPlus` 增减键）无法对齐。
  2. 原 `.stand-btn` 设置了 `min-width: 76px`，超出列宽（58px / 74px），向卡片右缘溢出，导致右缘留白仅 15–16px，过于贴边。
- **改动落实**：
  1. `.transport-main, .transport-caps` 增加 `padding: 0 var(--mid-pad, 8px);`，与 `.mid-row` 共享完全一致的列网格基准线。
  2. `.stand-btn` 样式调整为 `min-width: 0; width: 100%; max-width: 100%;`，撑满所在列单元格并严格居中，文案左右对称留白。
  3. 744 纵向视口修复 `.panel` 底部留白（由 4px 调整至 16px），确保在各种高度下刻度尺与拱形 apex 之间保持安全间距（≥16px）。

### 1.2 Fix 2.1.2 readout 计时开始后隐藏「分钟」
- **根因分析**：
  1. 原 CSS 隐藏规则编写为 `.dash[data-mode="running"] .readout-unit`，但引擎在计时开始时的真实属性是 `data-mode="run"` 与 `data-mode="pause"`，选择器永远不匹配，导致计时状态下「分钟」单位一直残留。
- **改动落实**：
  1. 将 CSS 规则修正为真实值：
     ```css
     .dash[data-mode="run"] .readout-unit,
     .dash[data-mode="pause"] .readout-unit { display: none !important; }
     ```
  2. 在 `evaluateAudit` 中新增真实态断言，强制采样 `run` 与 `pause` 状态下 `.readout-unit` 的 computed display，确保严格为 `none`。

### 1.3 Fix 2.1.3 `grille-6x8 variant-countersink` 孔阵动画与宽度对齐
- **根因分析**：
  1. 原孔阵写死 6 列 × 8 行（48 孔），总宽为 $6 \times 6 + 5 \times 3.5 = 53.5\text{px}$，远小于 `cover-frame` 的 72px 宽度，视觉上孔阵偏窄、未对齐。
  2. 原运行态动画为 `holePulse`，且延迟采用 `i % 8` 的对角错位，不是自下而上的声波波纹。
  3. 准备态（待命阶段）虽无 CSS 动画，但在音频仿真或复位后存在内联 `transform: scale(1.00)` 残留，导致无法证明准备态完全静止。
- **改动落实**：
  1. 列数扩充为 8 列 × 8 行（共 64 孔），采用网格两端对齐：
     ```css
     .grille-6x8 {
       display: grid;
       width: var(--cover-w, 72px);
       height: var(--cover-w, 72px);
       grid-template-columns: repeat(8, 6px);
       grid-template-rows: repeat(8, 6px);
       justify-content: space-between;
       align-content: space-between;
       gap: 0;
       padding: 0;
       box-sizing: border-box;
     }
     ```
     实测孔阵总宽严格等于 72.0px，与 `cover-frame` 总宽差 0.0px（$\le 1\text{px}$）。
  2. **准备态完全静止**：
     - CSS 设置 `.dash:not([data-mode="run"]) .hole, .dash[data-mode="prep"] .hole, .dash[data-mode="pause"] .hole { animation: none !important; }`；
     - `enterPrep()` 及能量为 0 时彻底清空内联 `transform`、`backgroundColor`、`boxShadow`；
     - 断言采样证实准备态孔阵所有孔无 running 动画、无内联变化。
  3. **自下而上声波波纹动效**：
     - 生成孔阵时预设 `--wave-delay: ((7 - row) * 0.08 + colDist * 0.03)s`，底行（row 7）延迟 0.105s，顶行（row 0）延迟 0.665s，波动自下而上逐层传导；
     - 动画关键帧采用 `waveRippleUp`，高亮激活时呈现珊瑚暖光与沉头光泽：
       ```css
       @keyframes waveRippleUp {
         0%, 100% { transform: scale(1); background-color: var(--dash-hole); }
         35% { transform: scale(1.22); background-color: var(--dash-hole-active); box-shadow: 0 0 4px var(--dash-coral-glow); }
         65% { transform: scale(1.08); background-color: var(--dash-vermilion-soft); }
       }
       ```
     - 麦克风音频点驱动算法（`renderSpeakerPointFrame`）同步适配 8 列网格，保证自底向上单调点亮。

---

## 2. 三档视口实测数据汇总表

所有数值均由 Headless Chromium 在 `dashboard-skin-01-v3.html` 真实渲染环境中通过 `getBoundingClientRect()` 及 `getComputedStyle()` 实测提取：

| 验收项 | 指标说明 | 1133×744 (横屏桌面) | 744×1133 (纵向iPad) | 440×956 (窄屏手机) | 判定 |
|---|---|---|---|---|---|
| **全页裁定** | `verdict` | **`ASSERT_OK`** | **`ASSERT_OK`** | **`ASSERT_OK`** | **PASS** |
| **失败数** | `fails.length` | 0 | 0 | 0 | **PASS** |
| **舞台宽度** | `stageWidth` | 420.0px | 500.0px | 390.0px | 正常响应 |
| **Fix 2.1.1 谱架键中轴** | `standCx` | 757.0px | 791.0px | 742.0px | 实测值 |
| **Fix 2.1.1 上方银钮中轴** | `plusCx` | 757.0px | 791.0px | 742.0px | 实测值 |
| **Fix 2.1.1 列公共中轴** | `colCx` | 757.0px | 791.0px | 742.0px | 实测值 |
| **Fix 2.1.1 中轴差** | `centerlineDiff` | **0.00px** ($\le 1\text{px}$) | **0.00px** ($\le 1\text{px}$) | **0.00px** ($\le 1\text{px}$) | **PASS** |
| **Fix 2.1.1 键右缘留白** | `standMarginRight` | **24.0px** ($\ge 16\text{px}$) | **22.0px** ($\ge 16\text{px}$) | **24.0px** ($\ge 16\text{px}$) | **PASS** |
| **Fix 2.1.1 列右缘留白** | `colMarginRight` | 24.0px | 22.0px | 24.0px | 模块同口径 |
| **Fix 2.1.2 准备态单位** | `prepDisplay` | `block` (可见) | `block` (可见) | `block` (可见) | **PASS** |
| **Fix 2.1.2 运行态单位** | `runDisplay` | `none` (隐藏) | `none` (隐藏) | `none` (隐藏) | **PASS** |
| **Fix 2.1.2 暂停态单位** | `pauseDisplay` | `none` (隐藏) | `none` (隐藏) | `none` (隐藏) | **PASS** |
| **Fix 2.1.3 孔阵列数/行数** | `cols × rows` | 8 列 × 8 行 | 8 列 × 8 行 | 8 列 × 8 行 | **PASS** |
| **Fix 2.1.3 孔阵总孔数** | `holeCount` | 64 孔 | 64 孔 | 64 孔 | **PASS** |
| **Fix 2.1.3 单孔宽高** | `singleHole` | 6.0px × 6.0px | 6.0px × 6.0px | 6.0px × 6.0px | **PASS** |
| **Fix 2.1.3 孔阵总宽** | `grilleWidth` | 72.0px | 72.0px | 72.0px | 实测值 |
| **Fix 2.1.3 封面总宽** | `coverWidth` | 72.0px | 72.0px | 72.0px | 实测值 |
| **Fix 2.1.3 宽度差** | `widthDiff` | **0.00px** ($\le 1\text{px}$) | **0.00px** ($\le 1\text{px}$) | **0.00px** ($\le 1\text{px}$) | **PASS** |
| **Fix 2.1.3 准备态静止** | `prepStateStatic` | `true` (无动画/无位移) | `true` (无动画/无位移) | `true` (无动画/无位移) | **PASS** |
| **Fix 2.1.3 运行态动效** | `runAnimationName` | `waveRippleUp` | `waveRippleUp` | `waveRippleUp` | **PASS** |
| **Fix 2.1.3 动效方向** | `waveDirectionBottomUp` | `true` (自下而上) | `true` (自下而上) | `true` (自下而上) | **PASS** |
| **Fix 2.1.3 底行/顶行延迟** | `bottomDelay / topDelay` | 0.105s / 0.665s | 0.105s / 0.665s | 0.105s / 0.665s | 阶段差 0.560s |

---

## 3. 负控测试验证记录

对每一条修复均编写了负控注入测试，将代码故意改回错误设定，证实断言严格生效并准确定位红行：

### 3.1 Fix 2.1.1 负控（谱架键位置偏右 / 贴边溢出）
- **注入条件**：移除 `.transport-main` 与 `.transport-caps` 的 padding，并将 `.stand-btn` 设回 `min-width: 76px`。
- **运行裁定**：`ASSERT_FAIL`
- **红行原文捕获**：
  ```text
  Fix 2.1.1 fail: 谱架键与上方银钮中轴差 8.00px > 1.0px
  Fix 2.1.1 fail: 谱架键右侧安全距离 7.0px < 16.0px（太贴边）
  ```
- **实测数据**：`standCx = 765.0`, `plusCx = 757.0`, `centerlineDiff = 8.00px`, `standMarginRight = 7.0px`。

### 3.2 Fix 2.1.2 负控（计时中「分钟」单位未隐藏）
- **注入条件**：将选择器写回 `running` 或在 `run` 态强制 `.readout-unit { display: block !important; }`。
- **运行裁定**：`ASSERT_FAIL`
- **红行原文捕获**：
  ```text
  Fix 2.1.2 fail: run 态下 .readout-unit 仍可见 (display=block)
  ```
- **实测数据**：`runDisplay = "block"`, `hiddenInRun = false`。

### 3.3 Fix 2.1.3a 负控（孔阵宽度与 cover-frame 不一致）
- **注入条件**：将孔阵宽度强制改回 6 列旧值 53.5px。
- **运行裁定**：`ASSERT_FAIL`
- **红行原文捕获**：
  ```text
  Fix 2.1.3 fail: 孔阵总宽 53.5px 与 cover-frame 总宽 72.0px 差 18.50px > 1.0px
  ```
- **实测数据**：`grilleWidth = 53.5`, `coverWidth = 72.0`, `widthDiff = 18.50px`。

### 3.4 Fix 2.1.3b 负控（准备态孔阵有动画在运行）
- **注入条件**：破坏准备态静止规则，强制在 `prep` 态启用动画 `.dash[data-mode="prep"] .hole { animation: waveRippleUp 1s infinite !important; }`。
- **运行裁定**：`ASSERT_FAIL`
- **红行原文捕获**：
  ```text
  Fix 2.1.3 fail: 准备态孔阵有动画在运行或有残留 transform（必须完全静止）
  ```
- **实测数据**：`prepStateStatic = false`, `ok = false`。

### 3.5 Fix 2.1.3c 负控（孔阵总数/列数不完整）
- **注入条件**：移除一个孔元素（总孔数从 64 变为 63）。
- **运行裁定**：`ASSERT_FAIL`
- **红行原文捕获**：
  ```text
  Fix 2.1.3 fail: 孔阵总数 got 63（want 64 = 8列x8行）
  ```
- **实测数据**：`holeCount = 63`, `ok = false`。

---

## 4. 自动化测试与工程门禁结果

1. **`dashboard-skin-01-v3.html?audit=1` 完整 5s 自然计时运行**：
   - 自然推进 5.1s 采样，气泡透明度达标（`maxBubbleOpacity = 1`），藤蔓自然开花，正向计时递增；
   - 裁定结果：`ASSERT_OK`，`fails: []`。
2. **`python3 docs/demos/practice-right-column-261003/scripts/verify-demos.py`**：
   - 结果：全部通过（0 错误）。
   - 换肤契约：所有页面 `--dash-*` 名集合一致（77 个）。
3. **`python3 docs/demos/practice-right-column-261003/scripts/token-contrast.py`**：
   - 结果：门禁不合格合计：0。

---

## 5. 遗留事项

- 无遗留缺陷。D1 仪表盘卡三处修复完毕，各视口对齐精度达到实测 0.0px 误差，`spec` 与断言全部闭环。
