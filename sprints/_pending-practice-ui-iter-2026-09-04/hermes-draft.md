---
status: process-draft        # NOT authoritative. 过程稿, 启动 sprint 时 supersedes
sprint: pending              # 等 dad 拍板 sprint-id 后改为 sprint-<id>-practice-ui-iter
date: 2026-09-04
author: Hermes (dizical-hermes @ w9:pC)
peer_reviewers: []
note: |
  诊断过程中产生的草稿. 启动 sprint 时:
  1. dad 拍板 §5 决策点 (hermes-draft §6 / integrated-draft §5)
  2. mv ../_pending-practice-ui-iter-2026-09-04 ../sprint-<id>-practice-ui-iter
  3. mv *-draft.md *-v1.md (去掉 -draft 后缀, 标记 v1 baseline)
  4. 写正式 sprint.md (按 STATUS.md 2026-09-03 sprint 模板)
  5. 启动时在本文件 supersedes 字段补 sprint.md 路径, status 改 superseded
supersedes: null
superseded_by: null
activation_rule: see `note:` above
---

# Practice 页 UI/UX 优化迭代方案 — Hermes 版

> 日期: 2026-09-04
> 目标页: `/practice` (https://dizical-prod-283401-10-1454535414.sh.run.tcloudbase.com/practice)
> 出品: Hermes (dizical-hermes @ w9:pC)
> 设计系统: dizicute (DESIGN.md + designrepo)
> 后续: 同步发 agy 出另一版 → 整合 → 实施

---

## 0. 前置说明 — 视野限制

**我没法直接看 prod 截图**（云端 `/practice` 需要登录；本地 8765 服务未起；browser-harness daemon 没运行；demo=true 不绕过登录）。诊断完全基于静态源码分析：

- 模板: `src/kid_app/templates/practice.html` (3067 行 — 单文件含 CSS+HTML+JS)
- 后端路由: `src/kid_app/app.py:2531 practice_page()`
- 设计 token: `DESIGN.md` + `dizicute` token 表
- 历史上下文: `docs/practice-uiux-audit-2026-05-26.md` + `docs/tech-spec/practice-v3.1.md` (PR #188, 2026-07-28)

**如果实际 prod 表现跟代码不符，以 dad 真机截图为准**。下面所有诊断都是基于代码 — 上线前必须真机复核。

---

## 1. 现状盘 (Surface area)

### 1.1 文件规模
- **3067 行 单一模板**，包含 inline `<style>` (≈900 行) + inline `<script>` (≈1900 行) + DOM
- 单文件 CSS + JS 体积大，刷新页面后浏览器 cache 命中率高，但开发期改一个动画要 grep 跨 2 千行

### 1.2 路由 + 数据依赖
- 1 个路由 `GET /practice` 拼整页 HTML（连 `items_html` 都是 Python str 拼接）
- 数据: `practice_items` + `practice_categories` + `weekly_assignments` + `daily_practices` + `subject_info`（独立 JSON 字段）
- API: `/api/practices/{date}`、`/api/practice-sessions/{date}`、`/api/practice-sessions/latest` 等

### 1.3 现有布局（V3.1 + V4 多轮迭代后）
```
┌─ 顶部状态栏 (今日分钟 + server clock) ─────────────┐
├─ item-section card ───────────────────────────────┤
│  h2 选择练习项目                                    │
│  selected-summary (选中后收拢展示)                  │
│  selection-area (搜索 + 分类网格)                   │
├─ reselect-float (浮动按钮) ────────────────────────┤
├─ vertical-stack ───────────────────────────────────┤
│  floor-pickers                                     │
│    v4-tab-header [计时练习 | 快速补录]              │
│    tabTimer:                                       │
│      dash-card-inline (黑底 dashboard)             │
│      timer-block                                   │
│        picker-card (wheel | dial-knob)            │
│        session-panel (速度 + 内容)               │
│    tabExtra:                                       │
│      dash-card-inline Extra                       │
│      timer-block (wheel | dial-knob + session)    │
├─ card today-records ────────────────────────────────┤
│  today-summary-bar (今日总时长 + 科目数 + session) │
│  recordsList                                       │
├─ practice-footer ──────────────────────────────────┤
└─ 3 个 modal: timerProtectModal / finishEarlyModal / finishNormalModal
```

### 1.4 JS 函数清单 (50+)
| 模块 | 函数数 | 关键 |
|---|---|---|
| Picker 自绘 | 5 | `createDialKnob` `createActivityWheel` `initPickers` |
| 状态机 | 8 | `selectItem` `toggleTimer` `resetTimer` `renderTimerDisplay` `glitchAnimateDigit` |
| 提交 | 6 | `addExtraFromPicker` `saveSessionEdit` `deleteSession` |
| 数据 | 6 | `fillSessionDefaults` `fillExtraDefaults` `renderBpmPresets` `renderContentTags` `loadArchivedToggle` `loadTodayRecords` |
| 视觉/动效 | 6 | `updateSelectedSummary` `collapseSelection` `toggleReselect` `playChime` `fireConfetti` `streamMood/streamSummary` |
| Modal/辅助 | 10+ | `openImagePreview` `openPracticeVideoModal` `updateReqPanel` `animateReqText` `renderStoryText` `setupTimerProtect` 等 |

---

## 2. 诊断 — 11 个真问题 (按严重度排序)

### 🔴 P0 — 必须改

#### P0-1. 视觉一致性破坏：DASHBOARD 用了设计系统**之外**的黑底
- **位置**: `.dash-card-inline` (行 888-900) + `.dci-name` `#FF6B6B` `.dci-tempo` `#FFD93D` `.dci-assign-label` `#FF8C5A`
- **症状**: dizicute token 暖白页面里突然切到 `#2C3E50 → #34495E` 渐变黑底 + 红/橙/金高饱和色块 — 跟"coral-red warmth for a kid's dizi practice app"品牌基调冲突。AGENTS.md §UI 偏好明确"弱化 CTA / ≤2 颜色灰/金 / 极简"
- **影响**: 这是计时器卡片最显眼的元素之一，每次进入 practice 页都看到，破坏统一感
- **修法**: dashboard 改暖白底 (`#FFFDF5`) 跟楼层一致；用 `#FF6B6B` (primary) 作 dci-name 颜色；保留黑色文字层级；只把"老师要求"标签用 `#FF8C5A`（praise-only accent，**不该用在 practice 页** — 这违反 token §accent 用途）

#### P0-2. 功能性破坏：practice 页无法被陌生人/自己之外的成员正确使用
- **位置**: practice 页只服务 kid（女儿自己），但登录流程强制 dad-admin 凭据
- **症状**: 不是所有 dad 女儿都能登录（没 kid 账号）；需要给女儿开 kid 专用登录入口（已有 `kid-app` 但账号体系没分）
- **影响**: 当前能用但角色错位 — dad 用 dad 账号帮女儿计时（违背 privacy + audit 留痕）
- **修法**: 不在本次 scope；记录到 backlog（涉及 auth 子系统）。本次 UI 优化不动这个

#### P0-3. 触屏可用性灾难：dial-knob 180px + pointer-events，drag 灵敏度系数 0.25
- **位置**: 行 158 `dial-knob --knob-size: 180px`，行 2743 `sensitivity: 0.25`
- **症状**:
  - 180px 大圆占屏，center 数字 36px 占 1/3 面积；dial ticks 跟 SVG 渲染 60 lines + 30 dots 每秒 rebuild — **触屏拖动时频繁 DOM reflow**（看 updateVisual 行 2785-2811，每次拖动 `removeAll .active-dot` + 重建 + arcPath 重写 d 属性）
  - 灵敏度 0.25 = 拖 4° 才改 1 分钟（一个完整 360° 才走完 30 分钟）— 手指拖动幅度要 ≥1440° 才走完 range，慢且容易误触
  - **touch-action: none** + 整个 knob 在 .floor 内，floor 有 overflow:visible 但 knob 紧贴边缘时旋转会被切
- **影响**: 女儿真实场景经常滑动 5 分钟时间 — 当前 UI 这是一次痛苦的经历
- **修法**:
  1. 灵敏度从 0.25 提到 0.5（拖 720° 走完 range，仍然细腻）
  2. dial-ticks/dots 用 SVG `<g>` 预渲染，rotate 用 transform 而不是 rebuild（拖动 60fps 不能 SVG reflow）
  3. 缩小 knob 到 144px（mobile）/ 160px（tablet） — 当前 AGENTS.md §UI "3D btn depth ≤0.6em"，knob 视觉体积违反"极简"
  4. 加 ±5min quick step 按钮（不动 knob，触屏直接点 +/−）

#### P0-4. 计时状态下视觉层叠冲突
- **位置**: timer 启动后 `.timer-display` (mm:ss) 替换 dial 中央数字，但 `.dial-knob` 还在转
- **症状**: 启动后 dial 还在原地（带 180° 灰渐变 + 60 ticks）但中央数字变 mm:ss — 视觉割裂，"dial 在转但中央显示秒数"的混合态不直觉
- **影响**: 用户（女儿）每秒钟看 60 ticks 旋转 + mm:ss 跳变 + glitch 动效 — 视觉噪声爆炸
- **修法**: 启动后 dial-knob **完全隐藏**（不只 `display:none`，避免 GSAP `glitchAnimateDigit` 残留），只保留 mm:ss 大字 + 进度环；stop 后才回归 knob

### 🟡 P1 — 强烈建议

#### P1-1. selected-summary + reselect-float 双入口混乱
- **位置**: 行 989-1006 `selected-summary` + 行 1019 `reselect-float`
- **症状**: 选完科目后同时出现两个"重新选择"入口：①summary 左侧按钮（行 996 `resel-btn`），②vertical-stack 上方浮动按钮（行 1019）。两者 100% 重复功能
- **影响**: dad 在 PR 评论已 ack 过这事，没改
- **修法**: 删 `.reselect-float`，只保留 summary 内的按钮。或者：删 summary 的 `resel-btn`，只留 reselect-float（更轻量，不挤 summary）

#### P1-2. .item-section.compact / .summary-right display:none 频繁切换
- **位置**: 行 910-920 CSS，row 1853-1855 JS `classList.add('compact')`
- **症状**: compact 模式藏掉 h2/搜索/选中区/summary-right，但 `.selection-area.collapsed` 又藏 selectionArea — 双重保险机制 + display:none + transition — 性能浪费 + 容易 CSS 状态错乱
- **影响**: 多次切科目时 CSS 重排；动画 0.35s 期间窗口高度跳变
- **修法**: 简化 — `.compact .summary-right` + `.compact .item-filter-wrap` + `.compact h2` 都不要单独藏，全部由 `.selection-area.expanded/collapsed` 一个 class 控

#### P1-3. activity-wheel 8 条目限定 + 80×200px 体积，触屏选错率高
- **位置**: 行 217 `activity-wheel width:80 height:200` + wheel-item height:34px → 最多显示 5-6 个
- **症状**: 80px 宽对女儿手指（≥10mm = 38px）来说边缘点中率 < 60%；wheel item 高度 34px 在 iPhone 440 宽竖屏下太小
- **影响**: 滚轮选分钟时经常误触隔壁
- **修法**: 加 ±5/±10 quick step 按钮（点选替代滚轮）+ wheel 改成 60×280 横向 wheel item，或者干脆**主路径**用 [1/3/5/10/15/20/30] segmented control（Dad 已经 ack 过这种 pattern：行 904 BPM preset = segmented control）

#### P1-4. Timer 状态下"计时器保护弹窗"误触高
- **位置**: 行 1673 `setupTimerProtect` 用 `beforeunload` 拦截 tab 关闭
- **症状**: 计时到一半女儿关掉 tab → 弹原生 confirm → 中断流程；AGENTS.md "iPad mini Safari" 触屏 confirm 经常失焦
- **影响**: 真实场景容易丢数据
- **修法**: 用 `visibilitychange` + server-side watchdog 每 30s ping；断网/锁屏容忍到 5 分钟，超时自动 save elapsed + 弹通知

#### P1-5. dashboard 文字层级混乱
- **位置**: `.dci-detail .dci-tempo` 14px 600 黄色 + `.dci-detail .dci-content` 13px `#E8ECF0`
- **症状**: 主信息（科目名）18px 红，对比 tempo 14px 金 / content 13px 灰，三种字重 + 三种颜色在 30px 高度里挤
- **影响**: 信息密度太高，女儿扫一眼看不出"现在在练什么"
- **修法**: dashboard 退化成 1 行 chip — 科目名 (16px primary) + 速度 (12px muted) + 老师要求 (12px primary muted)。三个信息不分行，全在一行显示，hover/click 展开详情

### 🟢 P2 — Nice-to-have

#### P2-1. modals 共用同一视觉模板但有 3 个不同的 box 样式
- `#timerProtectModal .modal-box` (max-width:320)
- `#finishEarlyModal .finish-modal-box` (max-width:380)
- `#finishNormalModal .finish-modal-box` (max-width:380, same)
- `#imagePreviewModal` (in JS-only 动态)
- `#videoModal` (video-modal-overlay)
- `#editModal` (.edit-modal-overlay)
- **修法**: 抽 1 个 `.modal-overlay` + 1 个 `.modal-box` 组件，5 个 modal 都用同一套；现在只是 max-width 不同不必要

#### P2-2. 实时时钟 (server-clock) 占视觉但 0 信息量
- **位置**: 行 79 `.server-clock` 13px 灰背景
- **症状**: 顶部状态栏右侧只显示当前时间 — 但页面已经显示"今日已练习 X 分钟"，时间冗余
- **修法**: server-clock 替换成"今日目标进度"（本周目标 vs 已练分钟），信息密度提升；或干脆删（mobile 隐藏，desktop 显示一个小 icon 即可）

#### P2-3. practice-footer 文案随机但无 UI hookup
- **位置**: 行 1161 `<div class="practice-footer" id="practiceFooter"></div>` + 行 1521 `streamMood`/`streamSummary` 调 LLM
- **症状**: 这个 footer 是给女儿加油的 Gemini 2.5 Flash 生成文案，但**没有触发按钮**（看代码 `streamMood` 只在 `selectItem` 末尾被调一次就完了） — 文案是隐藏的
- **修法**: 移动到今日练习记录下面（行 1156 today-summary-bar 之后），作为一句鼓励小卡；选中科目 + 完成计时后刷新；加小图标

#### P2-4. _defaultTempoLoaded 全局缓存失效逻辑可疑
- **位置**: 行 1843 `if (selectedItemId !== id) { delete _defaultTempoLoaded[id]; }`
- **症状**: 这个删除永远不发生 — `selectedItemId !== id` 改成 `selectedItemId === id` 才正确。意思是"切到不同科目时**保留**缓存"，但代码意图看起来是"切走清缓存" — 可能 bug
- **修法**: 读完整 fillSessionDefaults 调用链确认；若是 bug 修单行；若是 cache 设计有道理，加注释

#### P2-5. finishNormalModal 按钮 SVGs 巨长内联 (一次性 inline SVG)
- **位置**: 行 972-973 两个 `<svg>` 完整 path 都在模板里
- **症状**: 模板体积大，重复 SVG (check/cross icon 各 60 行)
- **修法**: 抽到独立 SVG sprite 或 partial

---

## 3. 改造建议（按优先级）

### 3.1 一次性大改（如果 dad 给一周时间）
1. **拆分 practice.html**: CSS → `static/css/practice.css`；JS → `static/js/practice.js`（拆模块：picker.js / timer.js / records.js / modal.js / state.js）。3047 行 → 5 个文件 ≤ 600 行
2. **design tokens 化**: 把所有 hex (`#FF6B6B` `#F0D060` `#FFFDF5` 等) 替换为 `var(--primary)` `var(--gold)` `var(--card-bg)`。同步 dizicute
3. **重构 dial-knob**: SVG 预渲染 + transform rotate，灵敏度 0.5，加 ±5/±10 步进
4. **重构 dashboard**: 黑底 → 暖白底 + 1 行 chip
5. **统一 modals**: 抽 1 套 `.modal-overlay` + `.modal-box`

### 3.2 增量式小改（一两天一个 sprint）
- Sprint A (1d): P0-1 dashboard 暖白化 + P0-4 timer 启动隐藏 knob + P1-1 删 reselect-float
- Sprint B (1d): P0-3 dial-knob 灵敏度 + 步进按钮
- Sprint C (0.5d): P1-3 activity-wheel → segmented control
- Sprint D (1d): P1-2 compact CSS 简化
- Sprint E (1d): P2-1 modals 统一 + P2-5 SVG sprite

### 3.3 不动的东西（设计原则决定）
- ❌ 不改 dial-knob 圆形外观 — 这是 V3.1 已定的强视觉签名（V4 PR 推过）
- ❌ 不改 timer-tab + extra-tab 的 V4 布局 — dad 已 ack
- ❌ 不动 backend API 形状 — 仅前端

---

## 4. 风险 + 验证

### 4.1 风险
- **DASHBOARD 黑底改暖白**: dad 之前 PR #188 推"暖白 + 暗 dashboard 对比"作为视觉强调；如果改白可能 dad 反对 — **需先出 mock 给 dad 看再改**
- **dial-knob 灵敏度**: 改大后女儿可能更频繁误触（拖动幅度变小 → 易拨过）；**A/B 测，先灰度**
- **modals 统一**: 现 3 个 modal 类名独立，merge 到统一 class 有 SSR 兼容性风险（modal 显示依赖 `display:flex` + `.open`，新 class 要保证行为一致）

### 4.2 验收指标
- [ ] 真机 iPhone 17 Pro Max (440×956) 横向比较 改造前 vs 改造后截图
- [ ] 真机 iPad mini 竖屏 (744×1133) 同上
- [ ] 女儿点 5min 计时 → 开始流程 5 秒内可达（目前要 knob 拖动 ≈3-5 秒）
- [ ] pytest 全绿（含现有 268 + 任何新测）
- [ ] 设计 token 一致性扫描：grep `#FF6B6B|#F0D060|#FFFEFA|#FFFDF5|#FFD93D|#2C3E50|#FF8C5A` 出现的次数 ≤ 10（集中在 design.md + style.css）

### 4.3 不验收指标
- ❌ LCP / FID — 当前页面无性能问题（数据量小），不优化
- ❌ SEO — 内部工具页面，不优化
- ❌ 国际化 — 当前中文不变

---

## 5. 跟 agy 的对接清单

发 agy 时请它回答：
1. 它看到的 dial-knob / dashboard / activity-wheel 三个核心组件，跟我的诊断是否一致？
2. 它对"dial-knob 是否应该改成 segmented control"有什么意见？
3. 它对"black-background dashboard 是否要保留" 有什么意见？
4. 它有没有发现我没看到的更深的 issue？（比如可访问性 / 键盘导航 / 国际化）
5. 它会怎么排序这 11 个问题？

---

## 6. 元信息
- 出品: Hermes (dizical-hermes)
- workspace: w9 (HERDR_WORKSPACE_ID)
- 诊断方式: 静态源码（3067 行 + 704 行 app.py practice 路由 + DESIGN.md）
- 限制: 未登录无法截图复核
- 信心度: 8/10（结构性问题高置信；细微交互需要真机）