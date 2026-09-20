---
id: 26091701-plan
type: plan
version: 1.0.0
date: 2026-09-17
sprint: 26091701
status: 待 dad 拍板
summary: "practice 计时器样式+交互优化方案：17 项问题，A/B/C 三变体，推荐 A 呼吸弧"
tags: [sprint, dizical, practice, timer, plan]
source: ai-agent
author: dizical-agy (Claude Opus 4.6 Thinking)
---

# 计时器模块样式与交互优化方案

> **范围**: practice.html 计时器区域 — dial knob + 倒计时显示 + 按钮组 + 补录 knob
> **不在范围**: 老师要求栏、badge 页、config 页、后端 API、DB
> **日期**: 2026-09-17

---

## 1. 现状盘点

### 1.1 整体结构

计时器模块位于 `.vertical-stack > .floor.floor-pickers` 卡片内（[practice.html:1024](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1024)），通过 V4 Tab header 切换「计时练习」和「快速补录」两个面板（[practice.html:1026-1029](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1026-L1029)）。

卡片背景 `#FFFDF5`，边框 `2px solid #F0D060`（[practice.html:119](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L119)）。

### 1.2 Dial Knob（主计时旋钮）

- **容器**: `.dial-knob`，`--knob-size: 180px`（[practice.html:158-166](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L158-L166)）
- **外盘**: `.dial-disc`，渐变 `#FFFDF8 → #F0E8D0`，多层 box-shadow 模拟凸起（[practice.html:167-177](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L167-L177)）
- **刻度 SVG**: `.dial-ticks`，80ms ease-out transition，拖动时 transition: none（[practice.html:178-184](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L178-L184)）
- **内面板**: `.dial-face`，inset 18%，渐变 `#FFFFFF → #FFF8F0`（[practice.html:185-201](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L185-L201)）
- **中央数值**: `.dial-value`，36px/900 weight/`#2C3E50`/letter-spacing -1px（[practice.html:202-208](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L202-L208)）
- **单位标签**: `.dial-unit`，12px/600 weight/`#999`（[practice.html:209-214](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L209-L214)）
- **HTML 锚点**: `#timerKnobEl`（[practice.html:1044-1051](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1044-L1051)）

Demo 版本（[dial-knob-demo.html:46-102](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/docs/demos/dial-knob-demo.html#L46-L102)）的 knob 是 220px、`.dial-value` 44px/-2px letter-spacing，与生产代码存在尺寸差异。

### 1.3 Activity Wheel（纵向滚轮）

- **容器**: `.activity-wheel`，80×200px（[practice.html:217-226](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L217-L226)）
- **每项**: `.wheel-item`，34px 高，280ms `cubic-bezier(0.34, 1.56, 0.64, 1)` 过渡（[practice.html:227-238](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L227-L238)）
- **选中指示器**: `.wheel-indicator`，8px 宽横条，`#2C3E50`（[practice.html:288-300](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L288-L300)）
- **上下渐变遮罩**: `::before` / `::after`，30px 高（[practice.html:301-317](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L301-L317)）
- Demo 版（[dial-knob-demo.html:104-221](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/docs/demos/dial-knob-demo.html#L104-L221)）wheel 是 220×260px，差距显著。

### 1.4 计时显示

- **`#timer-display`**: style.css 定义 64px/bold/`var(--primary)`（[style.css:136-142](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/static/style.css#L136-L142)），但 practice.html 内联 `.timer-display { display: none; }`（[practice.html:348](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L348)）将其永久隐藏。
- **实际显示位置**: 计时开始后，`.dial-value`（中央 36px 数值）从分钟数切换为 `mm:ss` 格式（[practice.html:1966-1979](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1966-L1979)）。
- **Glitch 动效**: 首次 start 调 `renderTimerDisplay(true)` → GSAP `fromTo`（opacity 0→1, scale 1.1→1, 0.3s power2.out）（[practice.html:1975-1977](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1975-L1977)）。存在一个未使用的 `glitchAnimateDigit()` 函数（[practice.html:1941-1963](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1941-L1963)），有 red/cyan text-shadow + elastic.out 弹性效果，但**从未被调用**。

### 1.5 按钮组

- **容器**: `.action-btns`，flex/gap 10px/center/wrap/margin-top 8px（[practice.html:320](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L320)）
- **通用 `.btn`**: 10px 20px padding, 20px 圆角, 15px 字号（[practice.html:321-328](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L321-L328)）
- **开始按钮**: `.btn.btn-primary`，渐变 `#4ECDC4 → #44B8AC`（[practice.html:329](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L329)）— 注意: 这里是**青绿色**不是珊瑚红
- **提前结束**: `.btn.btn-danger`，`#FF6B6B`（[practice.html:330](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L330)）
- **补录按钮**: `.btn.btn-ghost`，透明底 + `#4ECDC4` 2px 边框（[practice.html:332](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L332)）

style.css 中还定义了 `.timer-btns`（flex/center/gap 10/wrap）和 `.timer-btn`（12px 20px/30px 圆角/18px 字号，[style.css:143-158](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/static/style.css#L143-L158)），但这些**未被当前 practice.html 使用**（属于旧三栏原型残留）。

### 1.6 补录 Knob

- **`#extraKnobEl`**（[practice.html:1101-1108](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1101-L1108)）：结构与主 knob 完全相同，默认值 5 分钟。
- 补录按钮 `.btn.btn-ghost` `#addExtraBtn`（[practice.html:1110](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1110)）。

### 1.7 Timer-block 布局

- `.timer-block`: `flex-direction: row; gap: 10px`（[practice.html:122](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L122)）— 横向排列 picker-card + session-panel
- iPad 竖屏/手机: 切为 `flex-direction: column; align-items: center`（[practice.html:850, 870](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L850)）
- 手机 knob 缩到 148px（[practice.html:852](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L852)），iPad 竖屏 168px（[practice.html:872](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L872)）

### 1.8 安全语义（不触碰）

- **timerProtectModal**: 计时中离开页面弹窗（[practice.html:14-29, 938-947](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L14-L29)）
- **page-leave guard**: `beforeunload` / sidebar nav 拦截（由 `timerRunning` 变量守护，[practice.html:1336](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1336)）
- **pause 保留 elapsed**: `toggleTimer()` 暂停时 `paused = true`，不清零（[practice.html:1904-1912](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1904-L1912)）
- **finish-early cancel 恢复 elapsed**: `cancelFinishEarly()` 从 `finishSavedElapsed` 恢复（[practice.html:2046-2060](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L2046-L2060)）
- **正常结束弹窗确认**: 不自动提交（[practice.html:1992-1998](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1992-L1998)）

### 1.9 PRD 与代码差异

| 差异点 | PRD 描述 | 代码实际 |
|--------|----------|----------|
| 布局结构 | PRD-260511 写三栏 grid `25% 45% 30%` | 代码已改为垂直 `.vertical-stack` + Tab 切换（V4 重构） |
| 计时器显示 | PRD-260511 写 72px 大字倒计时 | 代码用 dial-face 内 36px 中央值显示正计时 mm:ss |
| 时间选择 | PRD-260511 写 5/10/15/20/30 按钮行 | 代码用 dial-knob 旋钮 + activity-wheel |
| `.timer-display` | style.css 写 64px/bold 计时器显示 | practice.html 内联 `display: none` 永久隐藏 |
| glitch 动效 | `glitchAnimateDigit()` 完整实现 | 函数存在但未被调用，实际只用简单 fromTo |
| knob 阻力 | PRD-260727 §11.7 要求 5/10/15/20/25/30 吸附 | demo 代码有 `snapValue()` 但生产代码的 `SNAP_RADIUS=0.8` 吸附力极弱 |

---

## 2. 问题清单

### 2.1 样式 (5)

| # | 现象 | 根因 | 影响设备 |
|---|------|------|----------|
| S1 | dial-value 36px 在计时 mm:ss 模式下偏小，5 位字符 `00:00` 挤在 dial-face 64% 区域内（face inset 18%），iPad 上可读性差 | 从 demo 的 44px 缩到 36px 时未调整 face 比例 ([practice.html:203](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L203) vs [dial-knob-demo.html:90](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/docs/demos/dial-knob-demo.html#L90)) | iPad / iPhone |
| S2 | activity-wheel 80×200px 远小于 demo 的 220×260px，每行 34px 触摸目标偏小（demo 38px），wheel-pill 文字 13px（demo 14px）辨识度低 | 从 demo 移植时大幅缩尺以适应旧三栏布局，改为垂直布局后未放大 ([practice.html:219-220](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L219-L220)) | iPad / iPhone |
| S3 | 开始按钮用青绿渐变 `#4ECDC4→#44B8AC`，提前结束用珊瑚红 `#FF6B6B`，色彩语义反直觉（红=停止，但这里红=提前结束；绿=开始，但用的是 secondary 而非 primary） | 历史沿用 practice 页以 `#4ECDC4` 作主色（UIUX_STYLE.md 第 43 行），但 DESIGN.md token 里 `colors.primary=#FF6B6B`，两套体系冲突 | 全设备 |
| S4 | 按钮 `.btn` padding 10px 20px、圆角 20px、字号 15px 偏小，与 style.css `.timer-btn` (12px 20px / 30px 圆角 / 18px) 和 PRD (13px 28px / 24px 圆角 / 18px) 三处不统一 | 多代重构留下的重复定义 ([practice.html:321-323](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L321-L323) vs [style.css:149-157](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/static/style.css#L149-L157)) | 全设备 |
| S5 | `.confirm-area` 成功打卡区背景 `#EDF7F0` + 边框 `#A0D8A8` 与计时器卡片 `#FFFDF5` + `#F0D060` 色调不搭（冷绿 vs 暖黄），视觉跳跃 | 成功区直接复用了旧原型的颜色 ([practice.html:351-358](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L351-L358)) | 全设备 |

### 2.2 交互 (4)

| # | 现象 | 根因 | 影响设备 |
|---|------|------|----------|
| I1 | 旋钮拖到特定数字(5/10/15/20)很困难，没有明显的吸附/阻力感 | `SNAP_RADIUS = 0.8`（demo [dial-knob-demo.html:339](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/docs/demos/dial-knob-demo.html#L339)）配合 `sensitivity=0.25`，实际吸附窗口小于 1 度，手指几乎感知不到 | iPad / iPhone 触摸 |
| I2 | 计时中 dial-knob 仍然可以拖动（改变 duration 值），但不影响正在跑的 elapsed，语义矛盾 | `toggleTimer()` 只在首次 start 时读 `duration`，之后 knob 拖动更新 `duration` 但 `startTickInterval()` 已用旧的 `duration*60` 做比较 ([practice.html:1985](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1985)) | 全设备 |
| I3 | 从 idle 分钟数 → 计时 mm:ss → 结束回 idle 的状态切换没有过渡，数值跳变生硬 | `renderTimerDisplay(true)` 只做 0.3s opacity+scale，没有数值形态切换动画；`resetTimer()` 直接 `valueEl.textContent = '10'` 无过渡 ([practice.html:1885](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1885)) | 全设备 |
| I4 | `glitchAnimateDigit()` 函数（完整 red/cyan 故障风格动效）已实现但从未调用，每秒 tick 只做 textContent 覆写，浪费了已写好的动效投资 | `renderTimerDisplay()` 在非 forceRebuild 路径只做 `valueEl.textContent = timeStr`，没有调用 glitch ([practice.html:1972-1978](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1972-L1978)) | 全设备 |

### 2.3 动效 (3)

| # | 现象 | 根因 | 影响设备 |
|---|------|------|----------|
| M1 | 弹窗动效 `.finish-modal-box` GSAP `back.out(2)` 0.4-0.5s 与 dial-ticks 的 80ms `ease-out` 节奏不统一，弹窗慢拖沓 | 两处动效由不同迭代添加，缺乏统一 timing 规范 | 全设备 |
| M2 | 计时完成 chime 后弹窗出现延迟感：`playChime()` 同步调，但 `gsap.fromTo` 弹窗有 0.5s 延迟 | chime 与弹窗无协调（[practice.html:1997-1998](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1997-L1998)） | 全设备 |
| M3 | dial-ticks 80ms ease-out 过渡在快速拖动时肉眼可见滞后，但 `.dragging` class 切到 `transition: none` 时又太突兀 | 单一 transition 值无法兼顾跟手性与松手回弹感 ([practice.html:182-184](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L182-L184)) | iPad 触摸 |

### 2.4 可访问性 (2)

| # | 现象 | 根因 | 影响设备 |
|---|------|------|----------|
| A1 | dial-knob 无 ARIA role/label/valuetext，屏幕阅读器无法理解这是一个时间选择器 | 原始实现只考虑触摸交互 ([practice.html:1044](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1044)) | 全设备 |
| A2 | 计时运行中无视觉进度指示（只有中央数字变化），缺乏环形进度弧或色彩变化 | dial-knob 计时时 ticks/dots 保持静止，没有进度映射逻辑 | 全设备 |

### 2.5 性能 (1)

| # | 现象 | 根因 | 影响设备 |
|---|------|------|----------|
| P1 | 每秒 `renderTimerDisplay()` 直接覆写 `textContent`，触发 layout → paint；在低端 iPad 上叠加 dashboard 更新可能掉帧 | `setInterval` 1000ms 回调中做 DOM 写入 + 可能的 GSAP 动画 ([practice.html:1982-2001](file:///Users/mt16/.herdr/worktrees/dizical/timer-260917/src/kid_app/templates/practice.html#L1982-L2001)) | 旧 iPad |

---

## 3. 方案

### 方案 A: 「呼吸弧」— 环形进度 + 呼吸节奏

**视觉描述**: 计时运行时，dial-knob 外环的 SVG dots 从静态装饰变为**顺时针填充的进度弧**，颜色从 `#4ECDC4`（起步）渐变到 `#FF6B6B`（接近结束）。中央 `mm:ss` 放大到 28px（face 区域宽度的 55%），配合 1s 周期的微弱 scale 脉动（1.0 → 1.02 → 1.0，`ease: sine.inOut`）模拟呼吸感。idle 态恢复分钟数显示，带 0.25s crossfade。

**交互流程**:
1. idle: knob 可拖，中央显示分钟数 + "分钟"
2. 点开始: knob **锁定**（`pointer-events: none`），中央 crossfade 到 `mm:ss`，进度弧从 0 开始填充
3. 暂停: 弧停在当前位置，数字停止脉动，按钮文案「继续」
4. 继续: 弧从当前位继续，数字恢复脉动
5. 结束/提前结束: 弧闪烁 2 次 → 弹窗

**按钮**: 统一为 dizicute `colors.primary` (#FF6B6B) 作 CTA，idle 态按钮弱化（ghost 风格），运行态按钮反转（填充珊瑚红）。「提前结束」保持 ghost 灰。

**关键改动点**:

| 文件 | 锚点行 | 改动 |
|------|--------|------|
| practice.html | L158-166 | `.dial-knob` 新增 `.is-running` 修饰 class，running 时 `pointer-events: none` |
| practice.html | L202-208 | `.dial-value` 改 28px（running 态），idle 态保持 36px，通过 `.is-running .dial-value` 切换 |
| practice.html | L167-177 | `.dial-disc` running 态加微弱脉动 `animation: breathe 4s ease-in-out infinite` |
| practice.html | L1966-1978 | `renderTimerDisplay()` 重写为 crossfade 逻辑 |
| practice.html | L1924-1936 | `toggleTimer()` 首次 start 给 knob 加 `.is-running`，`resetTimer()` 移除 |
| practice.html | L319-332 | `.btn` 系列统一到 14px 24px padding, 24px 圆角, 16px 字号 |
| practice.html | createDialKnob 调用 | 进度弧逻辑：计时中每秒更新 `activeGroup` SVG 弧的 `d` 属性 |

**优点**:
- 进度弧复用 knob 已有的 SVG 基础设施（`activeGroup` + `arcPath`），改动量小
- 呼吸脉动符合练习场景（吹笛需呼吸节奏感）
- 锁定 knob 消除 I2 交互矛盾

**代价**:
- 每秒需更新 SVG path `d` 属性（+1 次 DOM 写入）
- 需要新增 `@keyframes breathe` + `.is-running` 两个 CSS 规则

---

### 方案 B: 「极简数字」— 大字倒计时 + knob 隐藏

**视觉描述**: 计时开始时 dial-knob 整体用 GSAP `scale(0.6) → opacity(0)` 缩小消失，原位展开一个**大字倒计时** `mm:ss`，字号 56px（与 finish-modal 的 `.finish-mins` 一致），颜色 `#2C3E50`（`colors.secondary`）。下方进度条为 4px 高的横条，从左到右填充，颜色 `#FF6B6B`。结束时数字 bounce 放大 → 弹窗。

**交互流程**:
1. idle: knob 正常显示
2. 点开始: knob 缩小消失（0.3s `back.in(2)`），大字数字淡入（0.3s `power2.out`），横条从 0% 开始
3. 暂停: 横条停止，数字保持
4. 结束: 数字 bounce → 弹窗

**按钮**: 与方案 A 相同。

**关键改动点**:

| 文件 | 锚点行 | 改动 |
|------|--------|------|
| practice.html | L1039-1060 | `.timer-block` 内新增 `.timer-countdown` 容器（绝对定位覆盖 knob 区域），内含 `.countdown-value` (56px) + `.countdown-bar` (4px 高) |
| practice.html | L348 | `.timer-display` 改名/复用为 `.countdown-value` |
| practice.html | L1924-1936 | start 时 GSAP 动画切换 knob → countdown |
| practice.html | L1876-1900 | resetTimer() 时反向动画 countdown → knob |
| practice.html | L158-166 | `.dial-knob` 新增 `.hidden-running` class |
| practice.html | L319-332 | 按钮统一（同 A） |

**优点**:
- 计时态视觉极简，大字号可读性最佳（56px vs 36px vs 28px）
- 横条进度直觉清晰
- 不修改 SVG 刻度代码

**代价**:
- knob 出/入动画增加 GSAP timeline 复杂度
- 新增 HTML 元素（`.timer-countdown` 容器）
- knob 消失时 activity-wheel 需同步隐藏或重定位，涉及 flex 布局调整

---

### 方案 C: 「双态 knob」— 复用 glitch + 环形倒计时

**视觉描述**: 保持 knob 始终可见。idle 态不变。计时态: dial-ticks 外环**倒转**（从满到空）模拟倒计时，active dots 从全亮逐个熄灭。中央数字使用**已有的 `glitchAnimateDigit()`**（red/cyan text-shadow + elastic.out），但限制只在分钟数变化时触发（每 60 秒一次），秒变化用普通 `textContent` 更新。整分钟到达时 knob 做一次 `scale(1.05)` bounce。

**交互流程**:
1. idle: knob 可拖，中央分钟数
2. 点开始: ticks 瞬间填充到 100%，开始倒转；中央切到 `mm:ss`；首次 glitch 动效
3. 每分钟: glitch 动效 + knob bounce
4. 暂停: ticks 停止，数字保持
5. 结束: ticks 归零 + 全屏 confetti

**按钮**: 与方案 A/B 相同。

**关键改动点**:

| 文件 | 锚点行 | 改动 |
|------|--------|------|
| practice.html | L1966-1978 | `renderTimerDisplay()` 加入每 60 秒调 `glitchAnimateDigit()` 逻辑 |
| practice.html | L383-416 (demo 参考) | `updateVisual()` 反向计算 ratio: `1 - elapsed/(duration*60)` |
| practice.html | L1941-1963 | `glitchAnimateDigit()` 终于被启用 |
| practice.html | L158-166 | knob running 态禁拖（同 A） |
| practice.html | L319-332 | 按钮统一（同 A/B） |

**优点**:
- 激活已实现但未使用的 `glitchAnimateDigit()`，ROI 最高（0 新代码直接启用）
- 环形倒转直觉清晰（看着 dots 一个个灭掉）
- 不新增 HTML 元素

**代价**:
- 每秒需重绘 SVG dots（`activeGroup` 内 circle 增删），比方案 A 的 arc path 更重
- glitch 动效（red/cyan shadow）风格偏赛博朋克，与 dizicute 暖白珊瑚红品牌调性有张力
- 分钟级 glitch 在长时间练习（20-30 分钟）中的累积感受需实机验证

---

## 4. 推荐

**推荐方案 A「呼吸弧」**。

理由: (1) 进度弧复用现有 SVG 基础设施，改动集中在 CSS + `renderTimerDisplay()` 一个函数；(2) 呼吸脉动与竹笛练习场景天然契合，不喧宾夺主；(3) 不新增 HTML 元素、不隐藏现有组件、不引入赛博风格动效，与 dizicute 暖白调性一致；(4) 按钮色彩统一到 `colors.primary` 解决 S3 语义冲突；(5) knob 锁定解决 I2 交互矛盾。

否决 B: 大字倒计时视觉冲击强但 knob 出入动画增加复杂度，且 wheel 重定位会触碰 flex 布局。否决 C: glitch 赛博风格与品牌调性冲突，每秒重绘 SVG circles 性能不如 arc path。

---

## 5. 落地清单

以下按执行顺序排列，预估一位工程师 1 天内可完成。

| # | 文件 | 锚点行 | 改动描述 |
|---|------|--------|----------|
| 1 | practice.html | L158-166 | `.dial-knob` 新增 `.dial-knob.is-running { pointer-events: none; }` |
| 2 | practice.html | L202-214 | `.is-running .dial-value` 改 `font-size: 28px; letter-spacing: -0.5px`；`.is-running .dial-unit` 改 `display: none` |
| 3 | practice.html | ~L215 (新增) | 新增 `@keyframes breathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.02); } }` 和 `.is-running .dial-disc { animation: breathe 4s ease-in-out infinite; }` |
| 4 | practice.html | L319-332 | `.btn` 统一 `padding: 14px 24px; border-radius: 24px; font-size: 16px`；`.btn-primary` 改 `background: #FF6B6B; color: white`（移除渐变）；`.btn-danger` 改 `background: #F0F0F0; color: #666`（弱化提前结束） |
| 5 | practice.html | L351-358 | `.confirm-area` 背景改 `#FFF8F0`，边框改 `2px solid #F0D060`（与卡片统一暖黄调） |
| 6 | practice.html | L1924-1936 | `toggleTimer()` 首次 start: 给 `#timerKnobEl` 加 class `is-running`；调 `startProgressArc()`（新函数） |
| 7 | practice.html | L1876-1900 | `resetTimer()`: 移除 `is-running` class；调 `resetProgressArc()` |
| 8 | practice.html | L1966-1978 | `renderTimerDisplay()` 重写: idle→running 时 crossfade（GSAP `fromTo` opacity 0.25s）；running 中 textContent 直接写 |
| 9 | practice.html | ~L1980 (新增) | 新增 `startProgressArc()` / `updateProgressArc()` / `resetProgressArc()` 三函数，操作 `activeGroup` 内 SVG arc `d` 属性，ratio = `elapsed / (duration*60)`，颜色插值 `#4ECDC4 → #FF6B6B` |
| 10 | practice.html | L1982-2001 | `startTickInterval()` 内每秒调 `updateProgressArc()` |
| 11 | practice.html | L2046-2060 | `cancelFinishEarly()` 恢复 arc 到 `elapsed/(duration*60)` 位置 |
| 12 | practice.html | L2063-2086 | `abortFinishEarly()` 调 `resetProgressArc()` |
| 13 | practice.html | L219-220 | `.activity-wheel` 宽度改 `100px`（从 80px 放大 25%），高度改 `220px`（从 200px）；`.wheel-item` 高度改 `38px`（从 34px） |
| 14 | practice.html | L246-256 | `.wheel-pill` font-size 改 `14px`（从 13px），min-width 改 `42px`（从 38px） |
| 15 | practice.html | L339 (demo snapValue 参考) | 生产代码 `createDialKnob` 调用参数加 `snapVals: [5,10,15,20,25,30]`，`SNAP_RADIUS` 加大到 `1.5`（从 0.8） |
| 16 | practice.html | L1044 | `#timerKnobEl` 加 `role="slider" aria-label="练习时长" aria-valuemin="5" aria-valuemax="30" aria-valuenow="10" aria-valuetext="10 分钟"` |
| 17 | practice.html | createDialKnob `updateVisual` | 每次值变化更新 `aria-valuenow` + `aria-valuetext` |
| 18 | practice.html | L848-878 | 手机媒体查询: `.is-running .dial-value { font-size: 24px; }`；iPad 竖屏: `.is-running .dial-value { font-size: 26px; }` |
| 19 | practice.html | L1941-1963 | 删除未使用的 `glitchAnimateDigit()` 函数（dead code 清理） |
| 20 | style.css | L136-158 | 删除未使用的 `.timer-display` / `.timer-btns` / `.timer-btn` 定义（dead code 清理） |

---

## 6. 验收标准

### iPhone (440×956)
- [ ] knob 148px，中央数值 idle 36px / running 24px 可读
- [ ] 440px 宽无横向溢出（检查 `.vertical-stack` margin 12px 生效）
- [ ] activity-wheel 100×220px 不超出卡片
- [ ] 按钮触摸区 ≥44px（padding 14px + font 16px ≈ 44px 高）

### iPad mini 竖屏 (744×1133) — 主设备
- [ ] knob 168px，中央数值 idle 36px / running 26px 可读
- [ ] 拖动 knob 数字跟随延迟 < 1 frame（`transition: none` on drag）
- [ ] 5/10/15/20/25/30 分钟位置有明显吸附感（`SNAP_RADIUS=1.5`）
- [ ] 计时中 knob 不可拖动（`pointer-events: none`）
- [ ] 进度弧从 12 点钟方向顺时针填充，颜色从青到红渐变
- [ ] 暂停时弧停止、数字停止脉动
- [ ] 继续后弧从暂停位恢复
- [ ] 提前结束 → 弹窗 → 取消 → 弧恢复到取消前位置
- [ ] 提前结束 → 弹窗 → 不练了 → 弧重置、knob 解锁

### iPad mini 横屏 (1133×744)
- [ ] `.timer-block` column 布局，knob 居中
- [ ] session-panel 100% 宽度不溢出

### Mac MBP (1728×1117)
- [ ] `.timer-block` row 布局，knob 左 + session-panel 右
- [ ] knob 180px，中央数值 idle 36px / running 28px
- [ ] 鼠标 wheel 事件正常选值

### 通用
- [ ] GSAP `back.out` 缓动用于弹窗动效（保持现有）
- [ ] 呼吸脉动 `scale(1.02)` 4s ease-in-out 肉眼可感但不刺眼
- [ ] 开始按钮珊瑚红 `#FF6B6B`，提前结束灰 `#F0F0F0`
- [ ] 不使用 emoji，图标均为 SVG
- [ ] 无新 hex 颜色（所有颜色在 DESIGN.md token 内或既有代码中）
- [ ] knob 具有 `role="slider"` + `aria-valuenow` + `aria-valuetext`
- [ ] `#timer-display` / `.timer-btns` / `.timer-btn` dead code 已清除
- [ ] `glitchAnimateDigit()` dead code 已清除

---

## 7. 风险与不做

### 风险

| 风险 | 概率 | 缓解 |
|------|------|------|
| 进度弧 SVG path 每秒重绘在旧 iPad mini 6 上掉帧 | 低 | 只更新一个 `d` 属性（不增删 circle），比当前 `textContent` 写入开销相当 |
| 呼吸脉动 `transform: scale(1.02)` 在 disc 上触发 GPU 合成层，内存增加 | 低 | disc 已有 `box-shadow` 触发合成层，`will-change: transform` 可选加 |
| `SNAP_RADIUS=1.5` 导致 1-4 分钟范围连续值难以选到 | 中 | 吸附点只设在 5/10/15/20/25/30，1-4 不在吸附列表中，不受影响 |
| 按钮颜色从青绿改珊瑚红后用户短期不适应 | 低 | 珊瑚红是项目 primary 色（品牌色），统一后长期更一致 |

### 明确不做

- **不改 timer protect modal / page-leave guard / pause-resume 语义** — 安全逻辑完全不触碰
- **不改 session-panel（速度/内容输入区）** — 不在范围
- **不改 activity-wheel 交互逻辑**（touch/wheel 事件） — 只调尺寸
- **不改弹窗内容/按钮**（finishEarlyModal / finishNormalModal） — 只在范围内
- **不改 submitPractice() / 后端 API** — 不在范围
- **不引新依赖** — 纯 CSS + 现有 GSAP
- **不改 DESIGN.md token** — 所有颜色在现有 palette 内
- **不改 tab 切换逻辑**（计时练习/快速补录） — 不在范围
- **不改 dashboard `.dash-card-inline`** — 不在范围
