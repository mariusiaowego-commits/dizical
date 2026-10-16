# spec-agy-binding-261012 · 左右栏双向联动总线规格（映射表 · 事件 · 状态机）

> **文档归属**：Sprint 26100301 (practice 页右栏重构) ｜ 交付物 D  
> **上游 MRD**：`tqob/05-Coding/project-dizical/PRDs/MRD-左右栏组合问题.md`（标题 `## 2610120839-demo v3.2` 第 4.1 / 4.2 条）  
> **参考图基线**：`docs/demos/practice-right-column-261003/参考图文字基线-261012.md`（dad image20/21/24 逐图读数）  
> **任务 Brief**：`docs/demos/practice-right-column-261003/brief-agy-combos-261012.md` §D  
> **设计责任人**：agy ｜ 状态：正式设计规格（已按参考图基线校正）

---

## 1. 架构总览：统一练习状态总线（Practice Sync Bus）

左栏练习票卡（`practice-ticket-v4-260920.html`）与右栏模块列（仪表盘、节拍器、时长卡）存在于同宿主跨 iframe（或多组件协同）环境中。为消除以往各模块各自为政、状态割裂的问题，设计轻量级**单一真理源（Single Source of Truth, SSOT）事件总线**：`DizicalPracticeBus`。

### 1.1 核心状态数据模型 (State Interface)
```typescript
interface PracticeSyncState {
  // 1. 节拍速度与大拍子 (BPM & Note)
  bpm: number;              // 范围: 30 ~ 240，默认 80
  beatNote: string;         // '♩' (四分音符) | '♪' (八分音符) | '𝅘𝅥𝅯' (十六分音符)
  
  // 2. 计划练习时长 (Duration)
  durationMin: number;      // 范围: 1 ~ 30 分钟，默认 10

  // 3. 当前选中的 Session 练习科目
  sessionTitle: string;     // 如 "吸气长音", "全按作5 音阶练习"
  sessionId: string;        // 如 "session-longtone-1"

  // 4. 练习全生命周期状态机 (Lifecycle Mode)
  stageMode: 'prep' | 'running' | 'paused'; // 'prep' (准备态) | 'running' (计时态)
}
```

---

## 2. 核心联动映射矩阵表（Master Binding Matrix）

| 联动条目 | 左栏控件与选择器 | 右栏卡片及控件选择器 | 字段与类型 | 同步方向 | 正向表现（左 → 右） | 反向表现（右 → 左） |
|---|---|---|---|:---:|---|---|
| **联动 1：节拍与速度** (MRD 4.1) | `#pkBpmVal`<br>`#pkBpmDown` / `#pkBpmUp`<br>`#pkBeatNoteBtn` | **节拍器卡片** (`metronome-02-strip.html` / `metronome-01-v5.html`):<br>`.strip .bpm`<br>`#btnPlus` / `#btnMinus`<br>`#metroSoundToggle` | `bpm`: `number`<br>`beatNote`: `string` | **双向**<br>(Bi-dir) | 左栏调 BPM 或选四分音符（大拍子）$\to$ 右侧节拍器 BPM 数字与速度实时跟随变更，音频引擎无缝调整间隔。在组合 2 中兼容文字竖排模式。 | 右侧节拍器调整 BPM $\to$ 左栏票卡大数字 `#pkBpmVal` 瞬时同步，音符符号与大拍子指示保持一致。 |
| **联动 2：练习时长** (MRD 4.1) | `#pkTicketDurVal`<br>`#pkTicketDurDown`<br>`#pkTicketDurUp` | **仪表盘 Card A** (`dashboard-skin-01-v3.html`):<br>`#rulerInput`<br>`#readoutDigits`<br>`#ruler` (刻度指针) | `durationMin`: `number` (1~30) | **双向**<br>(Bi-dir) | 左栏加减时长（如选 10 分钟）$\to$ **右侧仪表盘表现得像用户平滑拖拽了 ruler 指针到 10 分钟刻度**，数字与藤蔓花朵开花进度同步按比例更新。 | 右侧拖拽刻度尺尺身或滑动 input $\to$ 左栏票卡大数字 `#pkTicketDurVal` 同步刷新。 |
| **联动 3：Session 科目标签** (MRD 4.1) | `#pkTicketCard .pss-bar`<br>`#pssList .pss-item` (选中项) | **仪表盘 Card A 顶栏**:<br>`#panel .status`<br>原 `.clock` (时间文本)<br>新 `.session-tag-pill` | `sessionTitle`: `string` | **单向**<br>(左 → 右) | 左栏切换 Session 科目 $\to$ **右栏仪表盘黑色区块内 `clock` 区域时间彻底隐藏（时间不要了），替换为高保真展示该科目标签胶囊**。 | 无反向修改（Session 选项目录权在左栏票夹）。 |
| **联动 4：准备态/计时态** (MRD 4.2) | `#practiceStage`<br>`#pkLeftCol`<br>(准备态宽 380px<br>计时态收窄至 220px) | **仪表盘 Card A 控件**:<br>`#btnPrimary` (开始键)<br>`#btnSecondary` (结束/暂停键)<br>`#dash[data-mode]`<br>**打卡机卡槽** `.cz-punch-slot` | `stageMode`:<br>`'prep'` \| `'running'` | **双向**<br>(Bi-dir) | 左栏触发检票进入计时 $\to$ 右侧仪表盘进入 `run` 态，打卡机卡槽呈现咬合插入，刻度尺开始走字，`.readout-unit`（分钟）隐藏。撕裂虚线平滑收拢保持整段结束。 | **仪表盘点击「开始」= 进入计时态（左栏收窄为竖向单列）；点击「结束」= 回到准备态（左栏平滑复原为 380px）**。 |

---

## 3. 逐条详细技术实现规格与实测判据

### 3.1 联动 1：BPM 速度与音符双向联动

#### 事件定义
* **事件名**：`SYNC_METRO_TEMPO`
* **Payload**：`{ bpm: 80, beatNote: '♩', source: 'left_ticket' | 'right_metro' }`

#### 表现细节与交互反馈（已按 image24 竖排校正）
1. **左 $\to$ 右**：
   - 用户在左栏点击 `#pkBpmUp` 或 `#pkBpmDown`，或点击 `#pkBeatNoteBtn` 切换拍号；
   - 广播 `SYNC_METRO_TEMPO`；
   - 右侧节拍器（无论是常规宽度的 `metronome-02-strip`，还是组合 2 中 **极窄 76px 文字竖排** 的节拍器）立即将内部 state 的 `bpm` 变更为目标值；
   - 在文字竖排（`writing-mode: vertical-rl`）形态下，BPM 数字与拍号标签按垂直单字流紧凑呈现，数值与左栏严格同步；
   - 若节拍器当前处于跑动状态（Running），调用内部 `AudioContext` 节拍引擎无缝重算 `interval = 60 / bpm`，下一拍立即生效，不得停顿爆音；
   - 仪表盘 Card A 底部状态栏的微型读数 `#bpmRead` 同步刷新为 `BPM 80`。
2. **右 $\to$ 左**：
   - 用户在右侧节拍器上点击微调步进键、长按快调或旋转旋钮；
   - 广播 `SYNC_METRO_TEMPO`；
   - 左栏 `#pkBpmVal` 实时响应并更新文字（`element.textContent = bpm`），且附带极轻微的 150ms 字体颜色轻微高亮（反馈数据已接收）。

#### 实测验收判据 (Test Assertion)
```javascript
// 控制台实测执行：左改右随
document.querySelector('#pkBpmUp').click(); // 假设从 80 加到 81
var rightBpm = metroDoc().querySelector('.bpm').textContent.trim();
assert(rightBpm === '81', '右栏 BPM 未随左栏加键同步');

// 右改左随
metroDoc().querySelector('.nudge.plus').click(); // 右栏从 81 加到 82
var leftBpm = document.querySelector('#pkBpmVal').textContent.trim();
assert(leftBpm === '82', '左栏 BPM 未随右栏加键同步');
```

---

### 3.2 联动 2：练习时长联动（模拟拖动 Ruler 指针）

#### 事件定义
* **事件名**：`SYNC_PRACTICE_DURATION`
* **Payload**：`{ durationMin: 15, source: 'left_ticket' | 'right_dash' }`

#### 表现细节与交互反馈
1. **核心视觉体验（Dad 显式要求）**：
   > “左栏 `pk-ticket-num-col` 选择了练习时长 x 分钟，右边的仪表盘内也要动态变化（类似模仿用户拖拽了 ruler 指针到 10 分钟）”
2. **仪表盘联动驱动机制**：
   - 收到左栏变更信号后，仪表盘**不仅修改隐藏输入框的数值**，必须执行真实指针滑动模拟：
     ```javascript
     function applyDurationFromLeft(durMin) {
       var input = document.getElementById('rulerInput');
       var readoutDigits = document.getElementById('readoutDigits');
       input.value = durMin;
       
       // 1. 触发原生 input 事件，驱动刻度尺内部的 offset 计算与红针滑动
       input.dispatchEvent(new Event('input', { bubbles: true }));
       
       // 2. 调用生产级藤蔓生长渲染器，让红针与绿藤按比例瞬间定位到目标刻度
       if (window.RulerProduction && RulerProduction.revealVine) {
         var progress = (durMin - 1) / (30 - 1); // 归一化比例
         RulerProduction.revealVine(progress, false);
       }
       
       // 3. 驱动空心 SVG monoline 数字重绘为目标数值
       updateHollowDigits(readoutDigits, String(durMin));
     }
     ```
3. **反向联动**：
   - 用户在右栏仪表盘上拖拽 `#ruler` 刻度尺或滚动齿轮，`input` 发生变化；
   - 广播 `SYNC_PRACTICE_DURATION`，左栏票卡时长大字 `#pkTicketDurVal` 实时跟随刷新为整数。

#### 实测验收判据 (Test Assertion)
```javascript
// 左栏改时长为 15 分钟
setLeftDuration(15);
var rulerVal = dashDoc().getElementById('rulerInput').value;
var svgText = dashDoc().getElementById('readoutDigits').getAttribute('aria-label');
assert(rulerVal === '15', '仪表盘 rulerInput 游标未滑至 15');
assert(svgText === '15', '仪表盘 readoutDigits 大数字未渲染为 15');
```

---

### 3.3 联动 3：Session 练习科目与仪表盘顶栏黑区 Clock 替换联动

#### 事件定义
* **事件名**：`SYNC_SESSION_SUBJECT`
* **Payload**：`{ title: '全按作5 音阶练习', id: 's-scale-5' }`

#### 表现细节与交互反馈
1. **黑色区块改造规约（Dad 显式要求）**：
   > “左栏 `pss-bar` 选择了一个练习科目的 session，右边仪表盘中目前没有位置可以放 session 的标签名称，我建议在右栏仪表盘中的黑色区块内的 `clock` 区域中时间替换为展示这个标签，时间不要了。”
2. **DOM 改造与样式实现**：
   - 仪表盘顶栏原 DOM 结构：
     ```html
     <!-- 旧结构 -->
     <div class="status">
       <button class="mic-status-btn">...</button>
       <span class="clock">10:12am</span> <!-- 彻底移除 -->
       <div class="battery">...</div>
     </div>
     ```
   - **重构后结构**：
     ```html
     <!-- 新结构 -->
     <div class="status">
       <button class="mic-status-btn">...</button>
       <!-- 替换为精细科目标签胶囊 -->
       <div class="session-tag-pill" id="panelSessionTag" title="当前练习科目">
         <span class="session-dot"></span>
         <span class="session-title-text" id="panelSessionText">吸气长音</span>
       </div>
       <div class="battery">...</div>
     </div>
     ```
3. **CSS 规格**：
   ```css
   .session-tag-pill {
     display: inline-flex;
     align-items: center;
     gap: 5px;
     height: 20px;
     padding: 0 8px;
     border-radius: 999px;
     background: var(--dash-vermilion-wash);
     border: 1px solid var(--dash-vermilion-line);
     color: var(--dash-panel-text);
     font-size: 11px;
     font-weight: 700;
     letter-spacing: 0.02em;
     max-width: 140px;
     white-space: nowrap;
     overflow: hidden;
     text-overflow: ellipsis;
   }
   .session-dot {
     width: 5px;
     height: 5px;
     border-radius: 50%;
     background: var(--dash-vermilion);
     box-shadow: 0 0 4px var(--dash-vermilion-glow);
   }
   ```
4. **联动行为**：
   - 左栏用户在 `pss-bar` 列表点击任意科目或录入新科目；
   - 广播 `SYNC_SESSION_SUBJECT`；
   - 右侧 `#panelSessionText` 立即平滑更新为对应科目名称；原 `10:12am` 时钟文本永久不再呈现。

#### 实测验收判据 (Test Assertion)
```javascript
// 验证时钟节点已退场
assert(dashDoc().querySelector('.status .clock') === null || 
       getComputedStyle(dashDoc().querySelector('.status .clock')).display === 'none', 
       '黑色区块内的旧 clock 区域必须被移除');

// 切换左栏 Session
selectSession('全按作5 音阶练习');
var tagText = dashDoc().getElementById('panelSessionText').textContent.trim();
assert(tagText === '全按作5 音阶练习', '仪表盘顶栏科目标签未同步替换');
```

---

### 3.4 联动 4：准备态/计时态状态机双向联动（左栏收窄与全链路切换）

#### 事件定义
* **事件名**：`TRANSITION_STAGE_MODE`
* **Payload**：`{ mode: 'prep' | 'running' | 'paused', trigger: 'dash_primary_btn' | 'ticket_start_btn' }`

#### 表现细节与交互反馈（已按 image20 虚线与 image21 遮罩校正）
1. **右侧驱动左栏核心闭环（Dad 显式要求）**：
   > “特别是仪表盘中的开始和结束，点击开始等于进入计时态，点击结束就等于回到准备态。（现状是点击后没有变化状态的）”
2. **正向：仪表盘点击「开始」($\to$ 进入计时态)**：
   - 用户点击仪表盘 Card A 的 `#btnPrimary`（开始练习，位于底部药丸内）；
   - 广播 `TRANSITION_STAGE_MODE: 'running'`；
   - **左栏票夹收窄联动**：
     - 左栏 `#practiceStage` 立即移除 `.stage-prep`，添加 `.stage-running`；
     - 左栏票夹宽度从展开态（`380px`）通过 CSS 容器平滑收窄为竖向小卡片（`220px`）；
     - 票根撕裂虚线自适应收缩至 220px，并通过 SVG/精确边距保持两端整段闭合（对照 image20）；
     - 左栏票夹隐藏所有准备态步进键（`.prep-only`），展示练习态读数（`.run-only`）；
   - **打卡机卡槽联动**：
     - 顶部卡槽从 `idle` 切换为 `engaged`，露出检票卡头；
   - **仪表盘自身**：
     - `#dash` 的 `data-mode` 切换为 `"run"`，`.readout-unit`（分钟小字）自动隐藏，刻度尺开始计时走字。
3. **反向：仪表盘点击「结束」($\to$ 回到准备态)**：
   - 用户点击仪表盘 Card A 的 `#btnSecondary`（结束练习）；
   - 广播 `TRANSITION_STAGE_MODE: 'prep'`；
   - **左栏票夹复原联动**：
     - 左栏 `#practiceStage` 恢复 `.stage-prep`，移除 `.stage-running`；
     - 左栏票夹宽度从 `220px` 平滑恢复回完整展开宽度（`380px`）；
   - **打卡机卡槽复位**：
     - 卡槽重置为空置待插狭缝（`idle`）；
   - **仪表盘自身**：
     - `#dash` 的 `data-mode` 恢复为 `"prep"`，显示 `.readout-unit`（分钟）。

#### 实测验收判据 (Test Assertion)
```javascript
// 1. 点击仪表盘「开始」测试
dashDoc().getElementById('btnPrimary').click();
var leftCol = document.getElementById('pkLeftCol');
var stageCls = document.getElementById('practiceStage').className;
assert(stageCls.includes('stage-running'), '点击仪表盘开始后，左栏未进入 stage-running');
assert(leftCol.getBoundingClientRect().width <= 240, '左栏票卡未收窄至 220px~240px 范围');

// 2. 点击仪表盘「结束」测试
dashDoc().getElementById('btnSecondary').click();
var stageCls2 = document.getElementById('practiceStage').className;
var leftColWidth = leftCol.getBoundingClientRect().width;
assert(stageCls2.includes('stage-prep'), '点击仪表盘结束后，左栏未恢复 stage-prep');
assert(leftColWidth >= 360, '左栏票卡未恢复回 380px 展开宽度');
```

---

## 4. 异常隔离与安全边界保护

1. **防循环死锁（Loop Protection）**：
   在事件广播派发时，所有 payload 均携带 `source` 标识。任何模块在接收到自身广播出去的事件时直接 `return`，坚决杜绝 `A -> B -> A -> B` 的死循环震荡。
2. **数值边界夹紧（Value Clamping）**：
   - BPM 强制截断在 `[30, 240]` 之间；
   - 练习时长强制整型截断在 `[1, 30]` 分钟之间；
3. **静默降级（Graceful Degradation）**：
   若右栏中某个组件（如节拍器）未在当前组合中装载，总线监听器静默跳过该分支，主计时与左栏票卡运行丝毫不受影响。

---

## 5. 按参考图基线校正（image20 / image21 / image24 逐图校对结论）

根据 `docs/demos/practice-right-column-261003/参考图文字基线-261012.md` 中 dad image20/21/24 的视觉读数，本总线规格补强了以下三个关键交互细节：

1. **组合 2 极窄竖条下的竖排数据同步自洽（对照 image24）**：
   - *基线真值*：image24 表明组合 2 中的节拍器必须为极窄（76px）且文字竖排；
   - *总线适配*：`SYNC_METRO_TEMPO` 总线在分发 BPM 数值时，同时分发渲染模式标签；竖排节拍器在接收到 2 位或 3 位 BPM（如 80、120）时，在 UI 上采用字符纵向堆叠（Tate-chu-yoko / vertical stack）安全排布，避免文字横向挤压变形。
2. **曲目票夹浮层与全局层叠上下文联动加固（对照 image21）**：
   - *事故真相*：image21 呈现的浮层文字与背景混淆叠合，除缺少遮罩外，还因为左栏曲目弹窗与右栏各组件缺乏层级协同信号；
   - *总线加固*：新增 `MODAL_LAYER_STATE` 广播，当左栏展开 `.pk-folio-modal` 或右栏展开 Popout 时，通知宿主提升遮罩层级至 `z-index: 10000` 并强制应用 `rgba(14, 17, 20, 0.72)` 压暗背景，右栏各 iframe 内部暂停非必要渲染，彻底消除文字穿透。
3. **票卡宽度状态机收拢与撕裂线整段闭合（对照 image20）**：
   - *基线真值*：image20 读数证实撕裂线必须横向贯通且两端以整段实线结束；
   - *总线适配*：在准备态（380px）与计时态（220px）收窄切换时，由状态总线通知票卡重新计算虚线两端的 `dashoffset` 相位，确保票卡无论处于 380px 还是收窄至 220px，两端均保持完整线段截断，绝不出现残缺断点。
