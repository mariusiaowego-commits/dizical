---
status: process-draft        # NOT authoritative. 过程稿, 启动 sprint 时 supersedes
sprint: pending              # 等 dad 拍板 sprint-id 后改为 sprint-<id>-practice-ui-iter
date: 2026-09-04
author: Hermes (dizical-hermes @ w9:pC) — integrator
peer_reviewers:
  - dizical-agy (dizical-agy @ w9:pM) — independent diagnostic
note: |
  整合稿 (Hermes + agy 双 agent 独立诊断 → Hermes 整合). 这是 dad 拍板的入口文档.
  启动 sprint 时:
  1. dad 拍板 integrated-draft §5 的 4 个决策点 (dial-knob / dashboard 暖白 / token 收敛 / 女儿账号)
  2. mv ../_pending-practice-ui-iter-2026-09-04 ../sprint-<id>-practice-ui-iter
  3. mv *-draft.md *-v1.md (去掉 -draft 后缀, 标记 v1 baseline)
  4. 写正式 sprint.md (按 STATUS.md 2026-09-03 sprint 模板)
  5. 启动时在本文件 supersedes 字段补 sprint.md 路径, status 改 superseded
supersedes:
  - hermes-draft.md
  - agy-draft.md
superseded_by: null
activation_rule: see `note:` above
---

# Practice 页 UI/UX 优化迭代方案 — 整合版 (Hermes + agy)

> 日期: 2026-09-04
> 目标页: `/practice` (https://dizical-prod-283401-10-1454535414.sh.run.tcloudbase.com/practice)
> 出品: Hermes (dizical-hermes @ w9:pC) + agy (dizical-agy @ w9:pM) 双 agent 独立诊断 → Hermes 整合
> 设计系统: dizicute (DESIGN.md + designrepo)
> 状态: **等 dad 拍板，尚未动手**

---

## 0. 前置说明

### 0.1 视野限制
两份诊断都是**纯静态源码分析**（未登录无法访问云端 prod 截图，本地 8765 未起，browser-harness daemon 没运行）。结论以代码为准，**上线前必须真机复核**（iPhone 17 Pro Max + iPad mini 竖屏 + Mac 浏览器）。

### 0.2 诊断输入
- Hermes 版 (16106 字节): `docs/practice-ui-iter-2026-09-04-hermes.md`
- agy 版 (9405 字节): `docs/practice-ui-iter-2026-09-04-agy.md`
- 代码: `src/kid_app/templates/practice.html` (3067 行 单文件 CSS+HTML+JS) + `src/kid_app/app.py:2531-2640` (`practice_page`)
- 历史上下文: `docs/practice-uiux-audit-2026-05-26.md` (V1 排查) + `docs/tech-spec/practice-v3.1.md` (V3.1 PR #188)

### 0.3 两份方案的核心差异（dad 拍板重点看）
| 维度 | Hermes | agy | 整合判断 |
|---|---|---|---|
| dial-knob | 调参数（灵敏度 0.25→0.5、加步进） | **彻底废除**，改 5/10/15/20/30 药丸 | **听 agy** — 儿童双手持笛场景拨旋钮是伪需求，但要保留 knob 给 dad 精确微调（1-30 分钟自由值）|
| 女儿真实物理场景 | 略 | **WakeLock + 挂钟时间对齐** 是 P0 | **听 agy**，列为本次 P0-1 |
| 数据灾备 | 略 | **LocalStorage 离线草稿** 是 P0 | **听 agy**，列为本次 P0-3 |
| dashboard 黑底 | 改暖白 | 改 dizicute 6 色 token | **听 agy 的色板策略，Hermes 的暖白基调** |
| 设计 token 漂移 | 列了若干 hex | **30+ hex 全面收敛** | **听 agy**，作为 P1-2 独立 sprint |
| ARIA / 键盘 | 略 | Space/Esc 绑定 | **听 agy**，作为 P1-3 |
| agy 漏看的 | — | — | Hermes 提的：P0-4 timer 启动后 knob 仍转 + P1-1 reselect 双入口 + P2-1 modals 不统一 + P2-3 footer 隐藏 + P2-4 _defaultTempoLoaded bug 可疑 |
| 共同漏看 | — | — | 后端 `app.py:2577-2607` Python 拼 HTML（hermes 看 app.py 提及，agy 单列 P2-1） |

---

## 1. 现状盘

### 1.1 文件规模
- **3067 行单一模板**: inline `<style>` ≈900 行 + inline `<script>` ≈1900 行 + DOM ≈170 行
- 50+ JS 函数；20+ 全局变量（无状态机）

### 1.2 路由 + 数据依赖
- `GET /practice` 一个路由拼整页 HTML（含 `items_html` Python 字符串拼接 — `app.py:2577-2607`）
- API: `/api/practices/{date}` `/api/practice-sessions/{date}` `/api/practice-sessions/latest` 等

### 1.3 现有布局（V3.1 + V4 多轮迭代后）
```
┌─ 顶部状态栏 (今日分钟 + server clock) ─────────────┐
├─ item-section card ───────────────────────────────┤
│  h2 选择练习项目                                    │
│  selected-summary (选中后收拢展示)                  │
│  selection-area (搜索 + 分类网格)                   │
├─ reselect-float (浮动按钮) ────────────────────────┤  ← P1-1 跟 summary 内按钮重复
├─ vertical-stack ───────────────────────────────────┤
│  floor-pickers                                     │
│    v4-tab-header [计时练习 | 快速补录]              │
│    tabTimer:                                       │
│      dash-card-inline (黑底 dashboard)             │  ← P0-1 暖白化
│      timer-block                                   │
│        picker-card (wheel | dial-knob 180px)       │  ← P0-3 / P1-1
│        session-panel (速度 + 内容)               │
│    tabExtra:                                       │
│      dash-card-inline Extra                       │
│      timer-block (wheel | dial-knob + session)    │
├─ card today-records ────────────────────────────────┤
│  today-summary-bar (今日总时长 + 科目数 + session) │
│  recordsList                                       │
├─ practice-footer (Gemini 鼓励文案但没 hookup) ─────┤  ← P2-3
└─ 3 个 modal: timerProtectModal / finishEarlyModal / finishNormalModal (+imagePreview +video +edit 共 6 个, 样式不统一)
```

---

## 2. 诊断 — 12 个真问题（按严重度整合）

### 🔴 P0 — 必须改（4 项）

#### P0-1. WakeLock 缺失 + 计时用 setInterval 漂移（agy 提出，Hermes 漏）
- **位置**: `practice.html:1981-2001` setInterval 计时 + 全局无 `navigator.wakeLock`
- **场景**: 7:15 早读，iPad 双手持笛看乐谱，默认 2 分钟锁屏 → WebKit 冻结 setInterval（实测可能 1 分钟/tick）+ AudioContext 静音 + 屏幕熄屏 → 10 分钟练习实际跑 25 分钟甚至不响铃
- **修法**:
  1. 计时改挂钟时间差：`elapsed = Math.floor((Date.now() - startTime) / 1000)`
  2. 计时开始请求 `navigator.wakeLock?.request('screen')`，停止/release
  3. 启动按钮触发时预激活 AudioContext（静音 1ms play 解锁）
- **验收**: iPad 设 1 分钟锁屏，启动 5 分钟计时后不碰屏幕，全程不灭屏且 5 分钟准点响铃

#### P0-2. dashboard 黑底破坏品牌 + accent 色错位（Hermes 提，agy 同意 token 漂移视角）
- **位置**: `.dash-card-inline` 行 888-900 + `.dci-tempo #FFD93D` `.dci-assign-label #FF8C5A`
- **症状**: dizicute 暖白页面里切到 `#2C3E50 → #34495E` 渐变黑底 + 红/橙/金高饱和色块；`#FF8C5A` (accent) 错位到 practice 页（DESIGN.md §"暖橙 — praise 页 only"）
- **影响**: 计时器卡片最显眼元素，每次进入 practice 页都看到，破坏统一感；AGENTS.md §UI "弱化 CTA / ≤2 颜色灰/金 / 极简"
- **修法**:
  1. dashboard 改暖白底 `#FFFDF5` 跟楼层一致
  2. `.dci-name` 用 `#FF6B6B` (primary)
  3. `.dci-tempo` 改 `#5D4037` (muted dark) 或 `#666666` (muted)
  4. `.dci-assign-label` 删 `#FF8C5A` accent，改为 muted 灰
  5. dashboard 退化为 1 行 chip（科目名 + 速度 + 老师要求），3 个信息不分行（Hermes P1-5）
- **验收**: 截屏对比前后；grep `#FF8C5A|#FFD93D|#2C3E50` 在 practice.html ≤ 2 处（仅设计 token 定义）

#### P0-3. dial-knob 180px + pointer-events 灵敏度 0.25 + SVG reflow（Hermes 提，agy 主张废除）
- **位置**: `.dial-knob --knob-size:180px` 行 158，`sensitivity:0.25` 行 2743，`updateVisual` 行 2785-2811 每帧 `removeAll .active-dot + 重建 + arcPath d 属性重写`
- **症状**:
  - 灵敏度 0.25 = 拖 1440° 走完 30 分钟 range（手指实际操作慢）
  - **每帧 SVG reflow**，触屏拖动 60fps 撑不住
  - 双手持笛时手指画圆易滑脱，且遮挡中央数字（agy）
- **影响**: 女儿真实场景拨 5 分钟 = 一次痛苦经历
- **修法** (Hermes + agy 折中，**dad 拍板**):
  - **方案 A (Hermes 温和版)**: 灵敏度 0.25 → 0.5；SVG `<g>` 预渲染 rotate 替代 reflow；缩小 180→144 mobile / 168 tablet；加 ±5/±10 quick step 按钮
  - **方案 B (agy 激进版)**: 彻底废除 dial-knob + activity-wheel，主路径改 **5/10/15/20/30 dizicute pill 秒选**；旋钮移到 settings 给 dad 精确微调 (1-30 分钟)
- **推荐**: **B**（agy 视角更符合儿童物理场景），但保留 dial-knob 作为"自定义"二级入口
- **验收**: 设定时间 < 1 秒（点 1 次药丸），手指不再遮挡数字，AGENTS.md §UI "极简" 合规

#### P0-4. 开始按钮隐性死锁 — 内容未填就静默置灰（agy 提出，Hermes 没看到）
- **位置**: `practice.html:1820-1828` `updateStartBtnState`，`1840-1842` `selectItem` 自动清空 `sessionContentInput`
- **症状**: 选科目 → 清空 session content input → 若科目没配 content_options tags，"开始"按钮 disabled，**无任何文字提示为何不可点**
- **影响**: 早上赶时间的孩子误以为页面崩溃，按几次无反应，挫败感
- **修法**:
  1. **首选**: 移除强制内容校验，提供兜底默认内容（"常规练习" 或老师要求第一条）
  2. **次选**: 保留校验，但点击置灰按钮时触发微动效 + tooltip "请先写这次练什么"
- **验收**: 选任意科目后 "开始" 立即可点（或点击置灰按钮有明确反馈）

### 🟡 P1 — 强烈建议（5 项）

#### P1-1. reselect 双入口混乱（Hermes 提）
- **位置**: `.resel-btn` 行 996 + `.reselect-float` 行 1019 — 完全重复功能
- **修法**: 删 `.reselect-float`，只留 summary 内按钮（或反过来）
- **验收**: 选中科目后只看到 1 个 "重新选择" 入口

#### P1-2. 30+ 非标 hex 全面收敛到 dizicute token（agy 提）
- **位置**: 全文 `#5D4037` `#8B6914` `#F0D060` `#c8860a` `#4ECDC4` 等
- **症状**: DESIGN.md 6 色 token，实践却 30+ 杂色（暗金/泥棕/赭石） — 视觉风格像工程测试板
- **修法**: grep 出所有非 token hex → 映射到 6 色 → 替换；引入 CSS variable `--primary --secondary --tertiary --neutral --muted --accent`
- **验收**: `grep -oE '#[0-9A-Fa-f]{6}' practice.html | sort -u | wc -l ≤ 6`（允许设计 token 定义本身）

#### P1-3. ARIA / 键盘 Space-Esc 无绑定（agy 提，Hermes 漏）
- **位置**: 3 个 modal 行 938-976 + 计时器全局
- **症状**: modal 无 `role="dialog"` 无焦点捕获；`Escape` 不绑关闭；`Space` 不能起停计时
- **修法**: 补 ARIA 属性；`Space` 切换开始/暂停，`Esc` 关 modal；`Tab` 焦点环 visible
- **验收**: 纯键盘可完成：选科目 → 开始 → 暂停 → 完成 → 打卡；dad 配外接键盘可用

#### P1-4. _defaultTempoLoaded 删除逻辑疑似 bug（Hermes 提）
- **位置**: 行 1843 `if (selectedItemId !== id) { delete _defaultTempoLoaded[id]; }`
- **症状**: 永远是 falsy 条件（`selectedItemId !== id` 不会 delete），意图可能是"切走清缓存"但代码写成"切回才清"
- **修法**: 先读 fillSessionDefaults 调用链确认意图；若是 bug 改单行；若是 cache 策略加注释
- **验收**: 切科目时 tempo 默认值来源 (latest session vs DB D 列) 行为符合预期

#### P1-5. activity-wheel 80×200 + 8 条目边缘点中率低（Hermes 提）
- **位置**: 行 217-296，wheel-item height:34px
- **症状**: 80px 宽边缘 + 34px 高，触屏命中率 < 60%
- **修法**: 跟 P0-3 方案 B 联动 — 彻底改 pill 秒选，wheel 仅作辅
- **验收**: 见 P0-3

### 🟢 P2 — Nice-to-have（3 项）

#### P2-1. 后端 Python 拼 HTML + 6 个 modal 样式不统一（Hermes + agy 共同提）
- **位置**: `app.py:2577-2607` `items_html` 字符串拼接 + `practice.html:938-976` 等 6 个 modal 各自 max-width 不同
- **修法**:
  1. 后端只返纯 JSON，前端渲染（移除 "No practice items. Ask dad..." 英文硬编码）
  2. 抽 1 套 `.modal-overlay` + `.modal-box`，6 个 modal 共用
- **验收**: `grep -n 'items_html += ' app.py` 为 0；6 个 modal DOM 都有 `class="modal-box"`

#### P2-2. 巨石文件拆分 CSS + JS（agy 提）
- **修法**: `static/css/practice.css` + `static/js/practice.js`（拆模块 picker / timer / records / modal / state）
- **验收**: 模板 ≤ 400 行

#### P2-3. practice-footer 文案没 hookup + server-clock 信息冗余（Hermes 提）
- **位置**: 行 1161 + 行 1521 `streamMood` 仅在选科目末尾触发一次
- **修法**:
  1. footer 移到 today-records 下面，加小图标 + 选中/完成计时后刷新
  2. server-clock 改成 "今日目标进度" (本周目标 vs 已练分钟)，或删
- **验收**: footer 文案可见且触发 2 次以上（选 + 完成）

---

## 3. 改造建议（增量 sprint）

### Sprint 0 — 拍板 (半天)
- [ ] dad 看 P0-3 dial-knob 方案 A vs B 选哪个
- [ ] dad 看 P0-2 dashboard 暖白化 mock 是否接受
- [ ] dad 看 Sprint 1-3 时间分配

### Sprint 1 (1d) — 数据安全 + 防呆 (agy P0 全部)
- [ ] **P0-1** WakeLock + 挂钟时间对齐 + AudioContext 预激活
- [ ] **P0-4** 开始按钮解除强校验 + 默认填充
- [ ] P0-3 阶段 1: dial-knob SVG reflow 修复（若 dad 选 A 方案）

### Sprint 2 (1d) — 品牌合规 + 设计 token
- [ ] **P0-2** dashboard 暖白化 + 1 行 chip
- [ ] **P1-2** 30+ hex → 6 色 dizicute token + CSS var
- [ ] **P1-1** 删 reselect-float 双入口

### Sprint 3 (1.5d) — 交互重构（视 Sprint 0 拍板）
- [ ] **P0-3** 阶段 2: dial-knob 方案 A（灵敏度 + 步进）或方案 B（pill 秒选 + knob 仅自定义）
- [ ] **P1-3** ARIA + 键盘 Space/Esc
- [ ] **P1-4** _defaultTempoLoaded bug 排查
- [ ] **P1-5** activity-wheel 配合 dial-knob 改造

### Sprint 4 (1d) — 架构瘦身
- [ ] **P2-1** 后端只返 JSON，前端渲染；6 modal 统一
- [ ] **P2-2** 拆分 CSS/JS
- [ ] **P2-3** footer + server-clock 优化

### 总计 ≈ 4.5d（dad 拍板 + 4 sprint），可拆 feature branch 分 4 个 PR 走

---

## 4. 风险 + 验证

### 4.1 风险
| 风险 | 影响 | 对策 |
|---|---|---|
| **WakeLock 不支持** (iOS < 16.4 / 非 HTTPS) | 女儿依然锁屏 | `if ('wakeLock' in navigator)` 守卫；降级到 `requestAnimationFrame` + visibleState 监听 |
| **AudioContext 自动播放拦截** | 计时到点静音 | 启动按钮 click 时静音 1ms 解锁 + 用户首次手势必须先于计时 |
| **LocalStorage 跨版本缓存** | 老缓存解析崩溃 | key 带版本 `dizical_draft_v1_${today}` |
| **dashboard 黑底改暖白** | dad 之前推过黑底对比视觉强调 | **先 mock 给 dad 看再改**（出 iPad 截图） |
| **dial-knob 方案 B 激进废除** | dad 之前 V3.1 / V4 强视觉签名 | **保留 knob 作为自定义二级入口**，主路径 pill 秒选 |
| **modal 统一** | SSR 兼容性 + 显示依赖 `display:flex` + `.open` | 抽公共 class 前先 mock |
| **P0-3 灵敏度改大** | 女儿可能更频繁误触 | Sprint 1 先灰度 1 周看反馈 |

### 4.2 验收指标
- [ ] 真机 iPhone 17 Pro Max (440×956) 截图前后对比
- [ ] 真机 iPad mini 竖屏 (744×1133) 同上
- [ ] 真机 iPad mini 横屏 (1133×744) 同上
- [ ] 女儿 5 分钟计时流程 ≤ 5 秒可达（点 pill → 开始）
- [ ] pytest 268+ passed（不能引入新 fail）
- [ ] 设计 token 一致性扫描：grep hex ≤ 6 处
- [ ] WakeLock 真机锁屏测试：5 分钟不灭屏 + 准点响铃
- [ ] 离线草稿：断网下打卡 → localStorage 保存 → 联网重试入库
- [ ] 纯键盘走完选科目 → 计时 → 完成 → 打卡

### 4.3 不验收指标
- ❌ LCP / FID — 性能没问题（数据量小）
- ❌ SEO — 内部工具页面
- ❌ 国际化 — 当前中文不变
- ❌ 后端 API 形状 — 本次不动

---

## 5. dad 必看决策点（4 个）

1. **dial-knob 存废**：保留调参 (A) / 彻底废除改 pill 秒选 (B)
2. **dashboard 黑底 vs 暖白**：当前黑底强调视觉 / 暖白回归 dizicute
3. **设计 token 全面收敛**（30+ hex → 6 色）：是否同意做这个 sprint
4. **女儿账号分离**（dad 当前代女儿登录）：是否纳入下个 sprint（涉及 auth 子系统，本方案未列入）

---

## 6. 元信息
- 出品: Hermes (dizical-hermes @ w9:pC) + agy (dizical-agy @ w9:pM)
- workspace: w9 (HERDR_WORKSPACE_ID)
- 诊断方式: 静态源码 + 设计系统规范 + agy 的"儿童双手持笛物理场景"视角
- 限制: 无 prod 截图
- 信心度: 8/10（结构性问题高置信；细微交互 + 真机性能需 dad 复核）
- 下一动作: dad 拍板 §5 的 4 个决策 → 写 PR → 拆 sprint 实施