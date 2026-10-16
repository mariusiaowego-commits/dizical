# plan — Sprint 26100301 practice 页右栏重构

> 版本 v0.1.0-draft ｜ 2026-10-03 ｜ 未拍板项集中在本文件 §4
> 需求原文（dad `2610011327`）在 §0，按原文条目编号保留，便于逐条对账。

## §0 需求还原（原文条目）

右栏是**上下结构**：上 = 仪表盘卡（计时 + 当前科目信息 + 练习进度），下 = 今日练习记录；老师要求卡从一级页面移出，改 pop-out。

### A. 仪表盘卡

- **1.0** 参考 `/Users/mt16/Downloads/dizical-uiux-reference/科目卡片参考-04.jpg`：**逐帧 copy 整体 UI 样式与 layout 排列**，在此基础上 copy + 创新。整体风格拟物；**要做成后续可替换仪表盘样式的模式**（这只是第一个默认皮肤）。
- **1.1** `timer-block` 的「圆角矩形黄色背景 + 橙色细边框」**不要了**，重新设计背景/边框；里面 `timerCard` 的元素都很好，保留。
- **1.2** 仪表盘 = 整体外框金属银色，内分多个**不规则图形**区域。最上面是不规则图形（超圆角 top dark panel）。参考里这块放了：封面图 / 歌曲名 / 播放进度条 / 歌词 / 最上通栏 bar（左麦克风提示 icon、时间、电池）/ 下方 volume(左) 与 track(右)。**这块 screen 可以 copy，但内容要重新思考**：
  - **1.2.1** 「专辑封面」（status bar 下方左侧）→ 改放 `pk-ticket-hero-frame` 里那张「每科目不同」的图，裁切成**正方形**，样式 = 圆角矩形边框 + 外围一圈**浅灰色细线圆角矩形**边框；图片下方显示当前练习科目名（如「萨丽哈」）。
  - **1.2.2** 歌曲名位 → 放 `练习计时`（`time-card` 里的 `readout`）；进度条位 → 放 `ruler`。
  - **1.2.3** 右侧「歌词」位 → 放 session 标签（小标题）+ 正文放该科目的**老师要求**（`assignments`）；小标题不动，正文**滚动播放**，**点击可暂停/恢复**滚动。
  - **1.2.4** 「volume」位 → 放**速度 bpm 要求**；「track」位 → 放**今日累计练习时长**。
  - **1.2.5** 左下角改成的 bpm 速度显示要与 silver-control-area 的 large rotary knob **联动**；显示值 = 当前设置的练习 bpm。
- **1.3** 银色控制面板区（`silver-control-area`）：`+`/`-` 号保留但**位置对调（+ 在右）**；功能 = 准备态下增减练习时长设置；**同一套 ± UI 同时应用到 top dark panel 进度条两侧（右 `+`、左 `-`），替换掉 `timerCard` 里现有的 ±**。
- **1.4** 当中 Large Rotary Knob = **全新单独开发**的「节拍器」调 BPM 旋钮：旋转左小右大，旋转联动上方 bpm 显示；**练习进行时要调用系统音响，像真节拍器一样按 bpm 打拍**（实现要 research 市面节拍器 APP，**最好不要自己造轮子**）。
  - **1.4.1** 参考 `bauhaus_metronome_ui_design_guide.md`（**重要**：其中很多 UI 元素带 feature，需评估哪些可做成对应功能）+ `节拍器ui.PNG`。
- **1.5** 银色面板区下方分左中右三块：
  - **1.5.1** 左 = 扬声孔：随麦克风捕获的声音/节奏做**跟随节奏的震动动效**。
  - **1.5.2** 中 = 操作按钮区：**保留现有按钮的逻辑与状态**，UI 改成符合本仪表的风格。参考 `2609260044-button-reference-01.jpg`、`button-reference-02-2609261128.jpg`。
  - **1.5.3** 右 = 谱架模式入口按钮（设计按钮 UI 样式）。
  - **1.5.4** **本期不做功能**：谱架模式点击无效果，只出 UI 样式。**谱架模式正式 UI（整体三栏 → 谱架卡片 + 仪表卡缩窄成长条）单独出 plan + 单独 demo，dad 最终确定后再开工**；仪表卡缩小宽度的样式与排版也要单独 demo 决策。

### B. 老师要求卡

- **2** 改为 pop-out，**不在一级页面**；入口放到最上面的 `pk-top` 区域。
- **2.1** pop-out 弹窗重新设计 UI，**单独出 demo 等 dad 决策**；默认展示本周最新要求，可查看历史要求。
- **2.1.2** UI 使用 dad 为 badge 页设计的 **three.js 3D 效果**；每一次要求 = 一张卡片；卡片浏览的 UI 与交互 **copy 指定的 reference** —— ⚠️ **原文这两处 reference 是空的（``），缺件，见 §4 Q1**。

### C. 今日练习记录

- **3.1** 展开态样式 copy `/Users/mt16/Downloads/dizical-uiux-reference/2609252147-reference-01.png`（high-resolution console 风）：**不 copy 黑色配色**，换本项目主题配色；**扁平化，不要特别拟物**。
- **3.2** 头部通栏右侧保留「折叠 / 展开」双态按钮：折叠 → 列表只有**科目级**；展开 → 到科目下的 **session 级**。
- **3.3** 通栏下 3 个 heroic 区（左→右）：**总时长**（从今日第一个科目 session 开始到现在的自然时间，单位分钟 `mm`）、**练习时长**（今日所有科目练习时长总和，`mm`）、**相比昨日**（多 = 红色 `+mm`，少 = 绿色 `-mm`）。
- **3.4** 列表列：科目 / 总时长 / 速度 / 单次（单次时长）/ 明细（session）/ 占比（本科目练习时长 ÷ 截至目前累计时长，`x%`）。
- **3.5** modal（pop-out）滚到卡片下方要有**渐进模糊**效果，用 GSAP（或评估后更合适的方案）：向下滚动时边缘信息模糊，离开边缘快速变清晰。

## §1 现状盘点（生产）

- `src/kid_app/templates/practice.html`（4693 行）：右栏现有 `#timerCard`（ruler + 圆盘 picker）、`.session-panel`（科目/速度/内容）、`#extraSection`、`.today-records` + `.today-summary-bar`、`.today-stat`（`今日已练习: {{ today_text }}`）
- 老师要求：`GET /api/assignments/latest?item_id=` → BPM 预设与要求正文（前端已有 3 处调用）
- 数据表：`practice_sessions(practice_date, item_id, item_name, duration_minutes, tempo_note, tempo_bpm, content, content_source, is_extra, started_at, reps, duration_seconds)`；`daily_practices(date, items JSON, total_minutes, log, practiced, behavior_log, practice_at, total_seconds)`
- 已可推导：总时长 = `now − MIN(started_at)`（今日）；练习时长 = `Σ duration_seconds`；占比 = 本科目 ÷ 合计；速度 = `tempo_bpm`；单次 = `duration_seconds`；明细 = sessions 行
- 待确认（派 grok 盘点）：今日记录的现读接口与字段、`pk-top` 现有结构、`pk-ticket-hero-frame` 的图源与取法、按钮组现有状态机、`timerCard` ± 现有实现
- **无 DDL 预期**：`tempo_bpm` / `started_at` / `duration_seconds` 均已存在；若 3.3「相比昨日」需要昨日值 → 由 `daily_practices`/`practice_sessions` 按日期查询即可
- 约定：**不新增依赖**（节拍器音频实现如需引库必须先拍板，见 §4 Q2）

## §1b 生产现状盘点结论（grok 只读实测，2026-10-03）

**① 生产页没有右栏。** `src/kid_app/templates/practice.html`（4693 行）是**单列**：`.top-bar` → 选科目 → `.vertical-stack`（`#timerCard` + `#extraSection`）→ `.today-records`。`pk-top` / `pk-ticket-hero-frame` / 三栏舞台**只在 demo** `docs/demos/practice-ticket-v4-260920.html`，从未挂进生产模板。
→ **结论**：本期 demo 阶段的承载 = 以 demo `practice-ticket-v4-260920.html` 的三栏舞台为底，**整块替换其右栏**；左栏不动、生产模板不碰。

**② 3.3「总时长」缺正确的字段（写入侧缺口）。** `started_at` 的语义是**打卡提交时刻**（`practice.html:3066-3068` 打卡时才 `practice_at: nowCstLocal()`，后端写入 `started_at`）；进行中的会话 DB 里没有行；历史行还有 NULL。`now − MIN(started_at)` 会得到打卡瞬间而非「按下开始」。
→ 本期 demo 用 mock 数据；**生产移植时要新增「首次开始计时时刻」的写入**（新列或复用 `behavior_log`），记进 §4b 待定。

**③ 今日记录读接口**：`GET /api/practices/{date}` → `app.py:1688-1727`，返回 `items[]`（已 annotate `seconds`）/ `total_minutes` / `total_seconds` / `sessions[]`（含 `tempo_bpm` `duration_seconds` `content` `reps` `is_extra` `started_at`）/ `behavior_log[]`。
- 已有：练习时长（Σ秒）、科目、速度（按 session）、单次、session 明细、占比分子（前端 `subjectSeconds:3420` 已加总，未渲染）
- **需新增响应字段**：`yesterday_seconds`、`delta_seconds`；`span_minutes` 依赖上面 ② 的写入侧
- 建议形状（不实现）：`GET /api/practices/{date}/summary` → `{date, span_minutes, practice_seconds, yesterday_seconds, delta_seconds, subjects:[{item_id,item_name,seconds,share_pct,sessions:[…]}]}`

**④ 老师要求 + 历史要求接口都现成**（D4/2.1.1 可直接用）：
- `GET /api/assignments/latest?item_id=`（`app.py:1869`）→ 只回一条、窗口 8 周、解析失败即 `found:false`，**不能当历史列表**
- `GET /config/api/assignments/by-item?item_id=&limit=N`（`routes/config.py:1018`）→ 该科目最近 N 次，**不限 8 周**，含 `lesson_date` / `metronome` / `requirements` / `metronome_segments` ← 历史要求走这条
- `GET /config/api/assignments?weeks=8&item=`（`config.py:957`）→ 按周列表，最新在前

**⑤ 科目图缺口**：`practice_items` 无图片列（`database.py:174-181`）；`subject_info.get_subject_info` 只返回文案，无图 URL；demo 唯一一张图 `docs/demos/assets/practice-hero-ticket-260922.png`（768×1024）是全科目共用、JS 不换。→ 1.2.1 的「每科目不同图」**图源待 dad 定**。

**⑥ 换皮要清的硬编码**：`#F0D060`（金边，`practice.html:550` / `.floor-pickers:537`）、`#FFFDF5`（卡片底 `550`）、`#FFF0E8`（`#metaVal` 胶囊 `560`）都不在 DESIGN.md 的 6 token 里 —— 仪表盘改为 token 驱动时必须一并收编（呼应 dad 的换肤=仅配色 token）。

**⑦ 生产移植时的契约锁（不能破，本期 demo 阶段不受影响）**：`tests/test_practice_timer_frontend.py` 按**源码子串**锁 —— id（`ttCounter` `ruler` `rulerRow` `rulerInput` `ttStepMinus` `ttStepPlus` `startBtn` `finishEarlyBtn` `confirmArea` `confirmMins` `metaVal`）· 注释 `sprint 26091901: 自定义 Pointer Events — 整段尺子按下相对拖拽` · `if (started) return` 必须在 pointerdown 前 100 字 · `ttSetDuration(nextDur, true)` · `MIN_MIN=1`/`MAX_MIN=30`/`TICKS=60` · `touch-action:none` 留在 `.ruler-input` · 按钮文案 `开始`/`暂停`/`继续` · 打卡 body 字段子串（`fetch('/api/log'`、`practice_at: nowCstLocal()`、`behavior_log: [{enter_time: enterTime` …）· 主计时圆盘必须继续不存在、补录圆盘必须继续存在。

## §1c token 契约已统一（2026-10-03，我做的）

4 个 demo 原本各写各的 `--dash-*`，已统一成**一份契约**：`docs/demos/practice-right-column-261003/token-spec.md`

- **主表**：浅银（`:root`）49 项 + 深墨（`:root[data-skin="ink"]`）覆盖 45 项；尺寸/时间 token（`radius`/`notch`/`num`/`beat`）皮肤无关
- **四文件契约完全一致**（集合相同），换皮 = 加 `data-skin="ink"`；组件内禁止硬编码 hex
- **新增 8 个 token**（`coral-soft` / `mic-on` / `notice-bg` / `notice-ink` / `surface-2` / `surface-3` / `surface-soft` / `gold`），把 D2/D3/D4 的散落色值收编
- **D4 的 `--c-*` 命名空间**已改为指向 `--dash-*` 的别名（不动其内部 CSS）
- **硬编码 hex 收编**：D2 4 处、D3 6 处、D4 24 处 → 现在四文件外露 hex = 0；其中 28 处逐字节同值替换，6 处灰阶近似收敛（逐条记在 token-spec §6）
- **验证**：负控（改前备份跑同一审计）报出 4/6/24 处 → 证明审计会咬；改后外露 hex 0 / 未定义 `var()` 0 / 花括号平衡；内联 `<script>` 与改前逐字节一致（只动样式）
- 脚本 `/tmp/unify-dash-tokens.py`（逐条断言出现次数）、`/tmp/verify-dash-tokens.py`；改前备份 `.bak-before-token-unify/`
- ⚠️ **方法论坑（记一笔）**：跨文件比对 CSS token 时，**不能按「第 N 个块」取**（D1 把 `:root[data-skin="ink"]` 写在 `:root` 前面，D2/D3 相反）——必须**按选择器对齐**，否则会产出假冲突（我据此误报过两次）

## §1d v2 轮（2026-10-03，review → 一次性改完）

- **输入**：两轮实测 review —— grok 自检 + 互检 D1/D2/D3/D4，agy 自检 + 互检（原文 `docs/demos/practice-right-column-261003/review-grok.md` 14.8KB / `review-agy.md` 23.3KB）
- **交叉核对结果**：共性必改 **7** 条 / 单边复核接受 **5** 条 / 冲突 **1** 条（D2 旋钮量程，按业务判）/ 与需求书冲突 **3** 条（**不擅自改**，见下）
- **v2 修改**：**92 处**（D1 30 / D2 22 / D3 20 / D4 20），脚本 `scripts/fix-v2-d*.py` 逐条断言、不匹配整体失败、不写盘
- **三个 HIGH**：① D1 机身从 1109×678 拉到 `min(100%,420px)` → 实测 420×511 ② D1 `:root[data-skin="ink"]` 原来整段在注释里（换肤死）→ 解除 + 顶栏切换器，实测 `--dash-panel` `#1C1E21 → #14181C` ③ D4 正文滚动被卡片 3D 拖拽吞掉 → `touch-action: pan-y` + 拖拽让位
- **两条工程性错误**：D3「开始/提前结束」实测只隔 5px（误触级）→ 12px；D2 969 行 `cumulativeDriftMs` 写死 0 并断言「恒等于 0」（假证据，同日志实测 0.4535ms）→ 改为按末拍实测位置算真实偏移 + 判定由值算 + 标出探针 20 样本量化上限
- **审计规则升级（v2 起生效并脚本化）**：旧规则「整行没有 `--` 才判硬编码」漏掉混写行（`linear-gradient(180deg, #FF8282, var(--dash-coral))`）→ 新规则 **非中性色一律禁止字面量**；中性黑/白 alpha（投影、内阴影、高光）列入允许清单
- **换肤契约扩到 62 个 `--dash-*`**（新增 13 项「透明度阶梯」：`--dash-ink-a04/a12/a16/a25/a42`、`--dash-coral-glow/-a25`、`--dash-accent-soft/-wash/-line/-glow`、`--dash-gold-a35/-glow`）；深墨只覆盖 ink-a*（深底翻暖白），品牌 alpha 两套同值
- **验证**：`scripts/verify-v2b.py` 七项全 PASS（非中性色字面量 0 / `transition:all` 0 / ink 活体 / 花括号平衡 / 内联 JS 过 `node --check` / 引用 token 全有定义 / `--dash-*` 名集合四文件一致）；四页面真机加载 `js_errors = 0`
- **交付物**：`v2-changes.md`（92 处分组清单）、`token-spec.md`（由脚本读真值生成，浅银 64 项 / 深墨覆盖 50 项）、`scripts/`（7 个可复跑脚本）
- **与需求书冲突、v2 保持原样的 3 条**：银面 ± 保持调练习时长（需求 1.3）/ 老师要求保持滚动播放（1.2.3，只补静态状态字）/ 右下保持单个谱架按钮（1.5.3）
- ⚠️ **服务器坑（记一笔）**：`python3 -m http.server <port> --directory <demo 子目录>` 会让 `../vendor/gsap.min.js`、`../practice-skeleton-260920/real-timer-visual.js` 全部 404（上级路径跑出服务根），页面静默缺依赖并抛 `ttSetControlsEnabled is not defined`。**根目录必须设 `docs/demos`**。另：8770 被 mole-vibe 项目的 `web_server.py` 占着，别用。

## §2 分期

> **下一阶段 plan**：`plan-phase2-c-compose.md`（补 C 段 + 合成右栏 + 接真接口 + 写入侧维修）。

| 期 | 交付 | 出口条件 |
|---|---|---|
| P1 | 仪表盘默认皮肤 + 今日记录重做 + 老师要求 pop-out 骨架 | 对应 demo 经 dad 拍板 + warden 验收 |
| P2 | 节拍器旋钮 + 拍声 | 调研报告 + 实现路线拍板 |
| P3 | 谱架模式（谱架卡片 + 仪表缩窄态） | **独立 plan + 独立 demo，dad 定后才开工** |

## §3 demo 清单（全部落 `docs/demos/practice-right-column-261003/`，可点变体对照页）

| ID | 内容 | 归属 |
|---|---|---|
| D1 | 仪表盘默认皮肤（top panel 内容映射 + ruler + ± 镜像 + 银色框架） | agy 设计 / grok 实现 |
| D2 | 节拍器旋钮 + bauhaus guide 元素功能评估（拍号/术语/beat 灯/ACCENT/TAP/Slider） | agy |
| D3 | 三块功能区（扬声孔震动动效 / 按钮组 / 谱架入口按钮） | grok |
| D4 | 老师要求卡 pop-out（three.js 3D 卡片浏览；缺 reference） | agy 设计 / grok 实现 |
| D5 | 今日记录（折叠/展开两态 + 3 heroic + 列表 + 渐进模糊） | grok |
| D6 | 谱架模式 + 仪表缩窄态（单独 plan） | 待 dad |

## §4 拍板记录（dad 2026-10-03）

- **A1（原 Q1）老师要求卡 3D 卡片浏览的 reference**：dad **暂未想好**；dizical 里目前唯一用 three.js 的就是 **badge 页** → D4 以「badge 页 three.js 实现」为技术基座，**卡片浏览的交互由我们出 2–3 个可点变体方案供 dad 选**，不照抄外部 reference。
- **A2（原 Q3）换肤粒度 = ① 仅配色 token** —— 「可替换仪表盘样式」= 一套 CSS 变量（`--dash-*`），不含质感/布局变体。实现要点：仪表盘所有颜色只走 token，禁止硬编码 hex；皮肤 = 一份 token 映射。
- **A3（原 Q4）推进方式 = 先 demo（只碰 `docs/demos/`）→ dad 拍板 → 再移植生产**。本期第一阶段**不改** `src/kid_app/templates/practice.html`。
- **A4（原 Q5）3.3「相比昨日」昨日无练习数据时显示 `--`**（无对比对象）。
- **A5（原 Q2）节拍器拍声路线 = 采纳 A：纯 Web Audio API + Lookahead 调度器，零依赖**（agy 报告对比：A 0 KB/0 漂移；B Tone.js 336.9 KB min/76.6 KB gzip 且底层同原理；C 老旧孤儿库不推荐）。配套必做：`navigator.audioSession.type='playback'` 破静音开关（iOS 16.4+）、首次手势 `resume()` 解锁、`wakeLock` 防息屏 + `visibilitychange` 回前台重置 `nextNoteTime`、woodblock 合成音色（强拍 1200→400Hz/25ms、弱拍 600→250Hz/15ms）、`OfflineAudioContext` 精度验证（实测 0.0000ms）。
- **A6 科目 hero 图 = 先用全科目共用占位图推进 demo**，图源（生成 or dad 上传）后定。
- **A7 bauhaus 元素范围 = 本期做 4 粒 beat 灯 + 主启停 + ±1 微调**；拍号 4/4 / `ACCENT: BEAT 1` / TAP 测速 / BPM Slider 下期（Slider 与 ruler 撞车暂缓）；`Allegro` 改中文民乐术语（如「快板」）。

## §4b 仍待定

- 科目 hero 图源（生成管线 or dad 上传）
- 3.3「总时长」写入侧：「首次开始计时时刻」用新列还是复用 `behavior_log`
- D4：卡片浏览交互（3 个变体已交 agy 出，等 dad 选）
- 是否把旋钮改动后的 BPM 持久化回 session

## §5 分派

- **agy**（Gemini 3.8 Flash）：节拍器市面实现调研 + D2/D4 设计；负责审美判断
- **grok**（Grok 4.6）：生产右栏盘点（DOM/JS/数据契约）+ D1/D3/D5 实现
- **warden**（MiniMax-M3，profile=warden，独立 tab）：每轮 demo 独立验收（只读、自跑负控）
- **hermes（我）**：调度 + 基线把关 + 生产接线 + 方案文档 + 契约测试
