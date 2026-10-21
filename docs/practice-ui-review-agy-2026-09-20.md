---
source: ai-agent
type: review
project: dizical
date: 2026-09-20
base_commit: 44fe6c1
target: src/kid_app/templates/practice.html (3706 行, 刻度尺版)
author: dizical-agy (Antigravity pane w25:p2)
reviewer: dizical-hermes (w25:p1)
status: 评审输入 · 非方案定稿
tags: [dizical, practice, ui-review, layout, 2026-09-20]
---

# practice 页前端 UI & Layout 评审（agy）+ Hermes 复核

> 评审对象：**当前 main（44fe6c1）**，即时间选择已改成「滚轮数字 + 刻度尺 + ±1 步进」的那一版。
> 触发：dad 2026-09-20 拍板「旧的 260904 方案全部作废，重新做 practice UI 重构」→ 先让 agy 出前端 UI / layout 评审。
> 本文正文是 agy 的评审报告（逐字），后面两节是 Hermes 的复核把关与补录拆除影响面盘点。
> 旧方案已归档：`sprints/_archived-2026-09/README.md`。

---

## 正文 · agy 评审报告

# dizical practice 页前端 UI & Layout 评审报告

## 1. 总判断
当前页面是**“两套交互模式（滚轮刻度尺 vs 旋钮转盘）与两套产品形态（计时 vs 补录）的生硬缝合”**：废弃补录系统未剥离导致双模冗余，信息面板（科目摘要、黑底仪表盘、session 参数）三重重叠；主操作流（选科目→定时间→开始）被撕裂为跨视口的非闭环点触，严重违背 7 岁儿童早读双手持笛一臂距离的使用场景。

---

## 2. 布局 / 结构问题

### [P0] 废弃补录模块（Tab + Dial Knob + Activity Wheel + Dashboard Extra）占据大面积层级与代码负担
- **代码位置**: `practice.html:1128-1132` (`.v4-tab-header`), `practice.html:1195-1245` (`#tabExtra`), `practice.html:264-424` (CSS), `practice.html:2846-3160` (JS)
- **问题分析**: 补录使用率为零，却常驻一级卡片内部 Tab。内部维护了基于极坐标算法的 Dial Knob 和惯性滚动的 Activity Wheel，并完整复制了一套 `#dashCardInlineExtra`。给 7 岁孩子带来严重误触风险与心理负荷。
- **建议改法**: 彻底移除 `.v4-tab-header` (L1128-1132) 与 `#tabExtra` (L1195-1245)；将 `#tabTimer` 解构为直接的单卡；清理 17 个关联函数与对应 CSS。
- **牵连清理清单**:
  - **DOM ID**: `#tabExtra`, `#dashCardInlineExtra`, `#dciNameExtra`, `#dciIdExtra`, `#dciTempoExtra`, `#dciContentExtra`, `#dciExtraCount`, `#extraSection`, `#extraWheel`, `#extraKnobEl`, `#extraTicks`, `#extraValue`, `#addExtraBtn`, `#extraLogList`, `#extraSessionPanel`, `#extraCurrentItem`, `#extraBpmDisplay`, `#extraBpmInput`, `#extraContentTags`, `#extraContentInput`
  - **JS 函数**: `createDialKnob`, `createActivityWheel`, `updateWheel`, `addExtraFromPicker`, `addExtraMins`, `deleteExtraRecord`, `refreshExtraSection`, `setExtraNote`, `setExtraBpmValue`, `stepExtraBpm`, `renderExtraContentTags`, `fillExtraDefaults`, `renderExtraItemGrid`, `selectExtraItem`, `updateDashboardExtra`, `_pulseUpdateExtra`, `updateExtraBtnState`
  - **CSS 类**: `.dial-knob`, `.dial-disc`, `.dial-ticks`, `.dial-face`, `.dial-value`, `.dial-unit`, `.activity-wheel`, `.wheel-item`, `.wheel-pill`, `.wheel-icon`, `.wheel-indicator`, `.extra-log-item`, `.extra-mins`, `.extra-del`, `.extra-item-select`, `.extra-current-item`, `.v4-tab-header`, `.extra-tab`

### [P0] iPad mini 竖屏 (744px) 视口断裂：计时器与参数面板纵向堆叠导致“开始”与必填项倒置
- **代码位置**: `practice.html:972-974` (`@media (min-width: 640px) and (max-width: 1099px) { .timer-block { flex-direction: column; align-items: center; } }`) & `practice.html:1142-1192`
- **问题分析**: 在主要设备 744px 竖屏下，`.timer-block` 被强制转为 column。左侧 `#timerCard`（含开始按钮）排在上面，右侧 `#sessionPanel`（含必填内容标签与输入框）折到下面。孩子选完科目，上方的“开始”按钮因下方内容为空直接置灰，孩子看不见原因。
- **建议改法**: 在 iPad mini 竖屏 744px 下，保持计时卡片与参数区的紧凑横向排布（744px 足够容纳 400px 计时器 + 280px 参数区），或将参数标签作为下挂托盘嵌于计时器正下方一体化展示。

### [P0] 三重信息面板垂直堆叠：收拢摘要、黑底 Dashboard 与 Session 面板严重重复
- **代码位置**: `practice.html:1092-1109` (`#selectedSummary`), `practice.html:1137-1141` (`#dashCardInline`), `practice.html:1169-1191` (`#sessionPanel`)
- **问题分析**: 选完科目后，屏幕上依次出现：(1) `#selectedSummary`（科目名、ID、老师要求、AI流式心情）；(2) `#dashCardInline`（黑底背景，再次显示科目名、ID、速度、老师要求）；(3) `#sessionPanel`（速度、BPM、练习内容）。一屏内同一条要求显示 3 次，首屏严重挤爆。
- **建议改法**: 删除黑底 `#dashCardInline` (L1137-1141)；将科目名与老师要求精简收拢在顶部单行条（高度 ≤ 50px），移除流式心情/故事 DOM。

### [P1] 今日练习统计四处分散冲突
- **代码位置**: `practice.html:77-83, 1082-1085` (`.top-bar`), `practice.html:1035-1037` (`#mobileTopbarAside`), `practice.html:588-611, 1254-1263` (`#todaySummaryBar`), `practice.html:968, 980` (`top-bar display: none`)
- **问题分析**: 顶部有 `.top-bar`（在 ≤1099px 下被 media query 粗暴隐藏），抽屉里有aside数字，底部又有一个大号珊瑚红渐变 `#todaySummaryBar`。iPad mini 竖屏进入页面时顶部无统计，必须滑到底部才能看到总时长。
- **建议改法**: 统一收敛为顶部 Header 内的一个简洁胶囊（`今日 15 分钟`），彻底删除顶部旧 `.top-bar` 与底部多余的 `#todaySummaryBar` 大卡片。

### [P2] 幽灵重新选择按钮与功能重叠
- **代码位置**: `practice.html:1026-1028, 1122` (`#reselectFloat`), `practice.html:1099` (`.resel-btn`)
- **问题分析**: L1122 定义了 `<button class="reselect-float" id="reselectFloat" ... style="display:none">`，没有任何 JS 代码解除其 `display:none`，系未完成遗留代码；而 L1099 在 summary 里已有一个重新选择按钮。
- **建议改法**: 删除 L1122 的 `#reselectFloat` 节点及 L1026-1028 的 CSS。

---

## 3. 视觉 / 密度问题

### [P0] 违背 dizicute 设计系统：黑底科技渐变与未授权青绿色系侵入
- **代码位置**: `practice.html:992-1004` (`.dash-card-inline` linear-gradient `#2C3E50` 至 `#34495E`, `.dci-tempo` `#FFD93D`, `.dci-assign-label` `#FF8C5A`)；`practice.html:31, 48, 64, 81, 435, 438, 933` (青绿色 `#4ECDC4` / `#44B8AC`)
- **问题分析**: `DESIGN.md:20-31` 明确要求 6 核心色，且 `accent #FF8C5A` 仅限 praise 页。练习页内出现黑底发光科技仪表盘、青绿打卡按钮，整页出现 110 个独立 Hex（CSS 内 91 个），色盘完全失控。
- **建议改法**: 删除黑底仪表盘；青绿按钮与高光统一替换为主色珊瑚红 `#FF6B6B` 或柔和暖色，全面对齐 dizicute 设计规范。

### [P1] 媒体查询断点过度碎片化 (8 个断点)
- **代码位置**: `practice.html:155` (520px), `L529` (800px), `L606` (600px), `L689` (744px), `L695` (440px), `L767` (767px), `L951` (639px), `L972` (640-1099px)
- **问题分析**: iPad mini 竖屏 (744px) 处于 744、767、800、640-1099 四重断点交叉口，不同区域以不同步调变异，布局稳定性极差。
- **建议改法**: 精简为 2 个标准断点：手机竖屏 (`max-width: 639px`) 与 平板/抽屉模式 (`max-width: 1099px`)。

### [P2] 3D 按钮伪元素重投影与网格间距过大
- **代码位置**: `practice.html:731` (`gap: 16px 10px`), `practice.html:745-783` (`transform: translate3d(0, 0.6em, -1em)`, box-shadow `0 3px 0 #9E9E9E` / `#B45309`)
- **问题分析**: 违背 `AGENTS.md` “3D btn depth ≤0.6em”、“极简 ≤2 颜色灰/金”的要求，视觉重心过于下沉，按钮看起来厚重杂乱。
- **建议改法**: 将深度削减至 `0.25em` 或改用轻量扁平卡片，网格统一为 `gap: 12px`，突出科目文字。

### [P2] 6 个 Modal 弹窗各立门派、缺乏公用体系
- **代码位置**: `practice.html:23-32` (`.modal-box`), `L40-68` (`.finish-modal-box`), `L616-622` (`.edit-modal-box`), `L643-653` (`.video-modal-box`), `L3649`, `L3675`
- **问题分析**: 每个弹窗单独定义背景、圆角、padding、按钮样式，甚至在文件底部 L3680-3682 还残留补丁 CSS。
- **建议改法**: 统一抽象为 `.dizi-modal` 基础结构，共享 16px 圆角和 dizicute 按钮标准。

---

## 4. 交互 / 可达性问题

### [P0] 选科目后“开始”按钮静默置灰，核心流程严重受阻
- **代码位置**: `practice.html:1700-1708` (`updateStartBtnState`), `practice.html:1717` (`sessionContentInput.value = ''`), `practice.html:1162` (`#startBtn disabled`)
- **问题分析**: `selectItem` 会将内容输入框重置为空，`updateStartBtnState` 检查到 `!content` 立即禁用“开始”按钮。界面没有任何关于“为什么不能开始”的提示。一臂距离外的 7 岁儿童无法感知需要先去下方点选标签。
- **建议改法**:
  1. 选中科目后，**默认自动选定第一个内容 Tag**（如“长音练习”）并填入内容框，使“开始”按钮立即可用；
  2. 若未填内容，按钮不作静默置灰，点击时震动提示并引导高亮“选一下练什么”。

### [P1] 滥用 15 处原生阻塞式 alert() / confirm()
- **代码位置**: `practice.html:2201, 2271, 2275, 2423, 2431, 2438, 2458, 2470, 2749, 2765, 2767, 2777, 2784, 2790, 2801`
- **问题分析**: 原生弹窗在 Safari/WKWebView 中完全阻塞 UI，文字微小不易点按，儿童体验极差。
- **建议改法**: 砍掉补录直接消灭 5 处（L2423, 2431, 2438, 2458, 2470）；打卡内容校验改为输入框微动效+Toast；删除确认使用轻量确认浮层。

### [P1] 步进按钮热区低于 44px 标准，刻度尺可访问性弱
- **代码位置**: `practice.html:185-194` (`.step-btn` 宽高 `38px × 32px`), `practice.html:214-219` (`.ruler-input tabindex="-1" opacity:0`)
- **问题分析**: 步进按钮高度 32px 低于 Apple HIG 推荐的 44×44pt 触控标准，儿童手持笛子单手微调容易按空；尺子透明 input 设为 `tabindex="-1"` 导致辅助焦点完全失效。
- **建议改法**: 将 `.step-btn` 触控热区扩展至 44×44px；恢复原生 input 的 aria 状态绑定与轮廓控制。

### [P2] 后端拼 HTML 包含英文硬编码且违背组件化
- **代码位置**: `app.py:2713` (`items_html = "<p style='color:#7F8C8D;text-align:center;'>No practice items. Ask dad to add via dizical practice config</p>"`)
- **问题分析**: 在中文儿童产品中出现全英文硬编码；且 L2684-2710 在 Python 内部拼写 HTML 字符串。
- **建议改法**: 改为中文（如“还没有练习科目哦，请爸爸在配置页添加”），后续迁移至 Jinja2 模板。

---

## 5. 重构骨架建议

### 一屏内黄金视口空间划分 (iPad mini 744 × 1133 px)
目标：**不滚动视口直接完成“选科目 → 定时间 → 点开始”闭环**。

```
+-------------------------------------------------------------+
| Header: [ 练习打卡 ]                      [ 今日已练 15 分 ] | (高 44px)
+-------------------------------------------------------------+
| 1. 科目区 (高约 180px 展开 / 52px 选中收拢)                 |
|    - 展开态: 2-3 列大圆角科目卡 (仅科目名 + 老师要求金标)    |
|    - 选中收拢: [ 吸气长音 | 老师要求: 连音均匀 ]  [ 换科目 ] |
+-------------------------------------------------------------+
| 2. 练习控制台 (首屏核心, 高约 380px)                        |
|   +--------------------------+  +-------------------------+ |
|   | 时间控制 (左)            |  | 参数与内容 (右)         | |
|   |                          |  |                         | |
|   |        [ 10:00 ]         |  | 速度: [ ♪ | ♩ ] = [ 80 ]| |
|   |        (大字号 72px)     |  |                         | |
|   | [-] |--|--|--|--|--| [+] |  | 练什么:                | |
|   |   (刻度尺拖拽 + 步进)    |  | [长音] [吐音] [连吐] (高亮)|
|   |                          |  | [ 自定义输入框        ] | |
|   |     [ ★ 开始练习 ★ ]     |  |                         | |
|   |   (48px 高珊瑚红大按钮)  |  |                         | |
|   +--------------------------+  +-------------------------+ |
+-------------------------------------------------------------+
| 3. 次屏滚动区 (向下轻滑可见)                                |
|    - 今日 Session 记录折叠卡片 (查看/编辑/删除)             |
|    - 底部励志文案                                           |
+-------------------------------------------------------------+
```

### 优先级排序草案
1. **首屏绝对优先级**:
   - 科目选择与收拢条
   - 时间选择与大字倒计时（滚轮数字 + 刻度尺 + 步进）
   - 开始 / 提前结束 / 打卡按钮
   - 速度与练什么快捷标签（自动默认选中第一项）
2. **彻底删除**:
   - 快速补录模块（Tab、Dial Knob、Activity Wheel）
   - 黑底渐变 Dashboard (`.dash-card-inline`)
   - Gemini 流式练习心情/故事文本占位
   - 幽灵按钮 `#reselectFloat`
   - 4 个零引用死函数: animateReqText (practice.html:1567), setPickerTime (practice.html:1974), glitchAnimateDigit (practice.html:2040), rulerWidth (practice.html:3510)
3. **降级至次屏**:
   - 今日打卡历史列表与详情卡片

---

## 6. 不要动清单

1. **打卡链路契约**:
   - 必须保持 `POST /api/log` 接口及入参结构（`date`, `item`, `item_id`, `minutes`, `tempo_note`, `tempo_bpm`, `content`, `practice_at`）。
   - `practice_at` 严格生成本地 CST 字符串，不得带 `Z`，UPDATE 保留首次时间。
   - 速度（音符+BPM）与练习内容（content）后端必填校验保持不变。
2. **单一路由规则**: 练习页必须保持单一路由 `/practice`，不可拆分为多个分步 URL。
3. **品牌资产与徽章体系**: 盲盒与徽章的 enamel pin 掐丝厚金边风格不得改动，不得引入新 hex 混淆主题。
4. **计时底层机制**: 刻度尺 60 格拖拽联动、Web Worker 防后台休眠保活、server-clock 校验不可破坏。

---

## 7. 取舍与风险

| 改动项 | 代价与改动面 | 回归风险 | 验证重点 |
|---|---|---|---|
| **彻底移除快速补录** | 删 HTML ~150 行、CSS ~180 行、JS ~450 行 | 极低（补录无业务依赖） | 确认去掉外层 Tab 后，主计时卡片在 744px 竖屏与 1133px 横屏正常自适应居中 |
| **移除黑底 Dashboard 与多余信息层** | 删 HTML ~20 行、CSS ~30 行、JS `updateDashboard` | 极低（纯视觉冗余） | 确认收拢态单行条能完整容纳老师要求与示范视频 Chip |
| **“练什么”标签自动预选** | JS `selectItem` 增加默认第一项填入并触发 `updateStartBtnState` | 低（利好儿童体验） | 无预设标签、无老师要求的冷启动科目，默认兜底内容测试 |
| **断点收敛至 639 / 1099** | 重构媒体查询，废除 520 / 600 / 744 / 767 / 800 | 中（样式层需真机回归） | iPad mini (744×1133) 与 iPhone (440×956) 下的字号与间距自适应 |
| **原生 alert/confirm 降级为 Toast/Modal** | 替换 10 处剩余阻塞调用为自定义轻量 UI | 低 | 验证断网异常与快速连续点击下的表单保护 |


---

## 附录 A · Hermes 复核（逐条核过代码，2026-09-20）

### A.1 成立（已核对）

- **4 个死函数行号全对**：`animateReqText` L1567、`setPickerTime` L1974、`glitchAnimateDigit` L2040、`rulerWidth` L3510（全文零引用）
- **`.step-btn` 38×32 对**：`practice.html:186`
- **补录牵连清单里的 CSS 类全部存在**：`.wheel-icon` L375、`.extra-item-select` L546、`.extra-log-item` L558、`.extra-mins` L570、`.extra-del` L571、`.extra-current-item` L1010
- **`#reselectFloat` 确认是死节点**：唯一相关函数 `toggleReselect()`（L1756-1766）只切 `#selectionArea` / `#selectedSummary` 的 class，没有任何代码解除它的 `display:none`。所以不是"两个入口并存"，而是"一个活入口 + 一个幽灵节点"
- **6 个 modal 数目不对不上**：DOM 里是 timerProtect / finishEarly / finishNormal / editSession / imagePreview / videoPreview，与 agy 的判断一致

### A.2 需修正（3 处）

1. **"补录使用率为零"不准确。** 实测（`data/dizi.db` 只读）：`daily_practices.items` 里 `is_extra` 条目 **45 / 920 = 4.9%**，补录分钟合计 396，用过补录的天数 23，**最近一次补录 2026-06-13**（三个月前）。"砍掉"的结论不变，数字要准。
2. **"计时底层有 Web Worker 防后台休眠保活"不存在。** 全仓 `src/` 搜 `new Worker|Worker(` 零命中。真实情况：计时仍是 `timerInterval = setInterval(() => { elapsed++ })`（`practice.html:2085-2086`），无 `navigator.wakeLock`，无挂钟时间差。这条被 agy 写在"不要动清单"里，实际是**待修**项，不是待保项。
3. **行号一处偏差**：`updateStartBtnState` 在 `practice.html:1925`（agy 写 1700-1708）。

### A.3 一处定性补充

「开始按钮置灰」不是 bug：代码注释与 PRD 标明这是 **2026-07-27 dad 拍板的 Q3=A「内容必填」**（`PRDs/AI-PRD-练习计时细分内容-260727.md`）。准确表述是：**校验本身是既定产品决策，缺陷在于置灰不给原因**（屏外、无文案）。修法是补提示 / 预选默认内容，不是放宽校验 —— 这一点需 dad 确认后再动。

---

## 附录 B · 补录拆除影响面（Hermes 只读盘点）

| 层 | 内容 |
|---|---|
| DOM | `#tabExtra` 块 `L1195-1250`（56 行）+ tab 头 `L1129-1132` + 20 个 extra id（`extraItemGrid` / `extraItemFilter` / `extraCurrentItem` / `extraLogList` / `extraSessionPanel` …） |
| JS | 14 个 extra 函数：`addExtraMins` · `addExtraFromPicker` · `refreshExtraSection` · `deleteExtraRecord` · `fillExtraDefaults` · `renderExtraContentTags` · `renderExtraItemGrid` · `selectExtraItem` · `setExtraNote` · `setExtraBpmValue` · `stepExtraBpm` · `updateExtraBtnState` · `updateDashboardExtra` · `_pulseUpdateExtra` |
| JS 工厂 | `createDialKnob`（L2846）· `createActivityWheel`（L2950）· `initPickers` —— 只服务补录 |
| CSS | 旋钮族（`.dial-knob/.dial-disc/.dial-ticks/.dial-face/.dial-value/.dial-unit`）+ 滚轮族（`.activity-wheel/.wheel-item/.wheel-pill/.wheel-icon/.wheel-indicator`）+ extra 族（`.extra-log-item/.extra-mins/.extra-del/.extra-item-select/.extra-current-item`）+ `.v4-tab-header/.extra-tab` |
| 顺带 | 消灭 5 处 `alert`（L2423 / 2431 / 2438 / 2458 / 2470） |
| 后端 | **不动**：`/api/log` 的 `is_extra` 字段保留（历史 45 条数据 + 其他入口仍在用），只在 practice 页移除录入与展示 |
| 规模 | 估 HTML ~150 行 / CSS ~180 行 / JS ~450 行 |

---

## 附录 C · 数据支撑

`data/dizi.db` 只读统计（2026-09-20）：`items` 条目 920，其中 `is_extra` 45（4.9%）；补录分钟合计 396；用过补录的天数 23；最近一次补录 `practice_at = 2026-06-13 10:27:12`。
