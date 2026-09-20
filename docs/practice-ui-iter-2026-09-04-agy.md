# Practice 页面独立诊断与改造方案 (agy 视角)

> 作者: dizical-agy @ w9:pM  
> 受众: dizical-hermes @ w9:pC & peer agents  
> 目标文件: `src/kid_app/templates/practice.html` (3068 行) + `src/kid_app/app.py:2531-2640`  
> 约束: 未查阅 Hermes 方案，基于代码静态审计、dizicute 规范与真实练笛场景独立产出。

---

## 1. 视野限制

1. **无真机视觉渲染帧率与截图**: 属于纯代码静态审查，无法精确采样 iPad mini / WebKit 下 GSAP 动效与 pointermove 的实际渲染 FPS。
2. **触控摩擦力靠推理**: Dial Knob 的角度阻尼手感只能从 `delta * sensitivity` 推导，无法获得手指真机滑动评测。
3. **WebKit 限制黑盒**: iOS Safari 的后台挂起与 AudioContext 用户交互解锁限制依赖历史真机开发常识，需真机复核。

---

## 2. 现状盘 (Surface Area & 架构视角)

1. **3068 行单文件巨石**: 920 行 CSS + 240 行 HTML + 1850 行 JS + 尾部补丁 CSS。所有逻辑全塞在一处，缺乏模块边界。
2. **全局状态无序蔓延**: 20+ 个松散全局变量 (`selectedItem`, `duration`, `elapsed`, `timerRunning`, `paused`, `finishPending`, `submitting` 等) 随意读写，缺少统一状态机。
3. **输入组件功能重叠割裂**: 同时挂载了 `createDialKnob` (圆盘旋钮) 和 `createActivityWheel` (垂直弧形轮盘)，两者互相双向监听同步，结构冗余。
4. **设计系统 (dizicute) 严重漂移**: DESIGN.md 规定了 6 个标准色，但代码中充斥 30+ 个生硬 Hex 色值 (`#5D4037`, `#8B6914`, `#F0D060` 等暗金/泥棕杂色)，严重破坏了 Coral-red 的清爽感。

---

## 3. 诊断问题清单 (P0 / P1 / P2)

### [P0] 严重可用性与数据安全缺陷

#### P0-1: `setInterval` 节流漂移 + 屏幕无常亮保护 (WakeLock 缺失)
- **位置**: `practice.html:1981-2001`, 全局无 `wakeLock` API
- **现状**: 7:15 早读练笛需双手持笛看乐谱。iPad 默认 2 分钟自动锁屏，锁屏后 WebKit 冻结或将 `setInterval` 节流至 1 分钟/tick。10 分钟练习可能耗时 25 分钟才报鸣，甚至铃声被 WebKit 后台音频策略拦截静音。
- **修法**: 
  1. 计时改用挂钟时间差算值: `elapsed = Math.floor((Date.now() - startTime) / 1000)`。
  2. 计时开始时请求屏幕常亮: `navigator.wakeLock?.request('screen')`，停止/离开时 release。
- **验收**: iPad 设置 1 分钟锁屏，启动 5 分钟计时后不碰屏幕，全程不灭屏且 5 分钟准点响铃。

#### P0-2: 练习内容强制校验阻塞，导致开始按钮“假死”
- **位置**: `practice.html:1820-1828` (`updateStartBtnState`), `1840-1842` (`selectItem`)
- **现状**: 每次点选科目会自动清空 `sessionContentInput`。若该科目没有配置 tags，在输入框有字之前“开始”按钮始终 disabled，且**无任何文字提示告知为何不可点**。早晨赶时间的孩子会误以为页面崩溃。
- **修法**: 
  1. 移除强阻塞，提供兜底默认内容（如自动填充“常规练习”或老师要求的第一条）。
  2. 若仍保留校验，在点击置灰按钮时触发微动效与 Tooltip 提示“请选择本次练习重点”，禁止静默置灰。
- **验收**: 选任意科目后，“开始”按钮立即可点（自带默认重点），或点击未就绪按钮有明确操作反馈。

#### P0-3: 零本地草稿保护 + 静默网络错误吞没
- **位置**: `practice.html:2118-2169`, `2190`, `2226`
- **现状**: 全程无 `localStorage` 备份。打卡瞬间若家庭局域网或 Wi-Fi 抖动，仅抛出原生 `alert('网络错误')`。孩子一旦刷新或关闭标签页，30 分钟辛苦练笛记录彻底丢失；`addExtraMins` 更是直接 `catch(e) {}` 静默吞没。
- **修法**: 
  1. 计时过程及结束态实时同步到 `localStorage.setItem('dizical_active_session', ...)`。
  2. 打卡失败自动写入离线待重试队列，UI 弹出非阻塞轻量 Toast 并允许“重试”。
- **验收**: 断网状态下点击打卡，记录保存在本地待重试栏，联网后点重试能成功入库。

---

### [P1] 交互效率与设计规范缺陷

#### P1-1: Dial Knob 旋钮与 Activity Wheel 交互繁琐且反直觉
- **位置**: `practice.html:1040-1051`, `2738-2930`
- **现状**: 7-15 岁儿童双手持笛，手指在 148px-180px 的触屏圆环上绕圈极易滑脱且手指会挡住正中数字。同时并存旋钮与轮盘，造成认知过载。竹笛练习时间高度标准化 (5 / 10 / 15 / 20 / 30 分钟)，无需精细到每 1 分钟连续拨盘。
- **修法**: 彻底剔除复杂 rotary SVG 旋钮与 wheel，改为 **dizicute 风格预设药丸 (5 / 10 / 15 / 20 / 30m) + 微调步进器 (±1m)**，单次点击即完成选择。
- **验收**: 设定时间只需点击一次药丸按钮，手指不再遮挡数字，交互耗时降至 1 秒以内。

#### P1-2: 30+ 违背 dizicute 的非标颜色与泥金色杂乱堆叠
- **位置**: `practice.html:119-120`, `2762`, 头部 style 区
- **现状**: 大量硬编码 `#5D4037`, `#8B6914`, `#F0D060`, `#c8860a`, `#4ECDC4`。与 DESIGN.md 定义的 6 色暖白+珊瑚红原则冲突，视觉风格像工程测试板。
- **修法**: 收敛至 dizicute CSS 变量：Primary (`#FF6B6B`), Secondary (`#2C3E50`), Tertiary (`#FFF8F0`), Muted (`#666666`)。
- **验收**: 页面所有 CSS 无外部未知十六进制色值，完全符合 DESIGN.md 规范。

#### P1-3: 弹窗 A11y 缺失与键盘无响应
- **位置**: `practice.html:938-976` (三个弹窗), `1264-1269`
- **现状**: 弹窗无 `role="dialog"` 和焦点捕获；`Escape` 键未绑定关闭弹窗；外接键盘/Mac app 下无法使用 `Space` 空格键起停计时器。
- **修法**: 补充 ARIA 属性；支持 `Space` 键切换开始/暂停，`Esc` 键返回关闭弹窗。
- **验收**: 纯键盘能够无障碍完成选择、计时、暂停与放弃操作。

---

### [P2] 架构维护性与代码整洁度缺陷

#### P2-1: 后端拼接 HTML 污染与国际化硬编码
- **位置**: `app.py:2577-2607` (`items_html` 拼接), `practice.html:1037`
- **现状**: 后端 Python 动态拼装大段 HTML 字符串并注入前端，出现 `No practice items. Ask dad...` 英文硬编码。前端缺少统一文案字典。
- **修法**: 后端只返纯 JSON 数组，交由前端渲染；文案统一定义。
- **验收**: `app.py` 中移除所有 HTML 拼接。

#### P2-2: 巨石文件拆分
- **位置**: `src/kid_app/templates/practice.html`
- **现状**: 3068 行全部堆在一个 HTML 文件中。
- **修法**: 拆离出 `static/css/practice.css` 与 `static/js/practice.js`。
- **验收**: 模板文件行数控制在 400 行以内。

---

## 4. 改造建议 (增量 Sprint)

拒绝一次性大重写，分三期平滑升级：

1. **Sprint 1 (核心安全与防呆 - 0.5天)**:
   - 修复 P0-1: 挂钟时间差 + WakeLock 屏幕常亮。
   - 修复 P0-2: 解除内容未填禁止开始的死锁，加入默认填充。
   - 修复 P0-3: 加入 `localStorage` 临时防丢草稿机制。
2. **Sprint 2 (交互重构与 Dizicute 对齐 - 1天)**:
   - 修复 P1-1: 拔除 Dial Knob / Wheel，上线 dizicute 快捷时间药丸组。
   - 修复 P1-2: 色彩全面回炉至 6 个 design token。
   - 修复 P1-3: 补全键盘 Space/Esc 交互与 A11y 焦点管理。
3. **Sprint 3 (架构瘦身 - 0.5天)**:
   - 修复 P2-1 & P2-2: 后端 HTML 拼接彻底数据化，静态资源物理分文件。

---

## 5. 风险 + 验证方案

1. **iOS WebKit AudioContext 自动播放拦截**:
   - *风险*: 计时到点播放 chime，若中途没有任何触碰，iOS 可能会阻止 `Audio.play()`。
   - *对策*: 在用户点击“开始”按钮时，预先 `load()` 或静音播放 1ms 音频以激活 Audio 上下文。
2. **WakeLock 兼容性与降级**:
   - *风险*: 部分旧版 Safari 或非 HTTPS 环境下 `navigator.wakeLock` 为 undefined。
   - *对策*: 采用 `if ('wakeLock' in navigator)` 严格守卫，降级时静默忽略，不阻塞核心计时。
3. **本地草稿版本兼容**:
   - *风险*: 缓存结构变动引起旧版本解析崩溃。
   - *对策*: LocalStorage Key 带上当前版本与日期命名空间 (`dizical_draft_v1_${today}`)。

---

## 6. 跟 Hermes 的对接清单 (我认为 Hermes 容易漏看的点)

1. **竹笛真实物理场景的“双手与视线占用”**:
   - Hermes 可能聚焦在布局像素、DOM 结构与视觉层次。
   - 我更强调**物理情境**: 吹笛子双手没空、离 iPad 有一臂距离、清晨容易锁屏。因此 **WakeLock 屏幕常亮** 和 **挂钟时间对齐** 必须是第一优先级。
2. **Dial-Knob 的存废立场**:
   - Hermes 可能会尝试微调 Knob 的半径、阻尼或样式。
   - 我的观点明确：**旋钮在儿童练习场景是个伪需求**。应彻底废弃 Knob/Wheel，直接改用 5/10/15/20/30 分钟的 дизаcute 快捷药丸。
3. **数据断网灾备与心理保护**:
   - Hermes 可能认为 API 是 localhost 很少挂。
   - 但实践中 iPad 走局域网/Tailscale 极易丢包，打卡失败弹 alert 会给练完吹笛的小孩极大挫败感。**本地草稿暂存**是刚需。
4. **开始按钮的隐性死锁**:
   - `updateStartBtnState` 强制依赖 `sessionContentInput`，若不选 tag 根本点不了开始，这是典型的开发者防呆过度变成“防用户”的暗坑。

---
指纹: agy-tower-2026-0904-herdr
