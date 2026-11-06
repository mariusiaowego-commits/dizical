# practice-dsh UI 文案定案表（MRD 3.2.5）

> 归属项目：dizical · 练习助手（practice-dsh）  
> 对应版本：MRD 3.2.5 · Sprint 26110603 · 段 B1 + 段 B2-A 文案定案  
> 权威规范：`AGENTS.md` · `docs/practice-dsh/DESIGN.md` §5.9  

---

## 1. 文案变更定案表（本次与后续改造覆盖）

| 编号 | 场景 / 业务功能 | 现状文案 | 定案文案 | DOM 位置 / 元素 ID | 状态 / 阶段 | 决策依据与处理说明 |
|---|---|---|---|---|---|---|
| C1 | 顶栏记录入口 Pill | `今日记录 — ▾`<br>（真实数据：`今日记录 X分 · N次 ▾`） | **`练习记录 — ▾`**<br>（真实数据：**`练习记录 X分 · N次 ▾`**） | `header#pkTop > #pkRecords` | 段 B1 本次实现 | MRD §2.1 要求顶栏设练习记录 pill 入口。采纳**改造并复用既有 `#pkRecords`** 方案，不新增冗余按钮；避免顶栏元素过多导致 ≤480px 极窄屏换行崩坏；保持现有事件绑定、云端数据回灌及打开全屏记录弹窗逻辑连贯。 |
| C2 | 全屏练习记录弹窗 | 标题：`今日练习记录`<br>徽标：`今日`<br>按钮：`关闭` | 标题：**`今日练习记录`**<br>徽标：**`今日`**<br>按钮：**`关闭`** | `.pk-drawer`<br>`#pkDrawerClose` | 段 B1 本次实现 | 保持页面内容区 UI 与文案完全不变，弹窗形态由右侧抽屉升级为全屏弹窗（宽高撑满可视带，内容居中最大宽 720px）。关闭按钮文案保持「关闭」。 |
| C3 | 谱架模式按钮 | `谱架模式`（含 SVG 图标） | **`谱架模式`** | `section.diag-card .diag-actions > #standBtn` | 段 B1 本次实现 | 从原 `transport-main .c-right` 迁移至下方监视条 `section.diag-card` 的 `.diag-actions` 操作区；样式对齐 `.diag-btn` 监视条按钮风格；点击切换 `aria-pressed` 与激活高亮。 |
| C4 | 谱架模式辅助提示 | `大屏看谱` | **并入按钮 title**（`title="谱架模式 · 大屏看谱"`） | `#standBtn[title]` | 段 B1 本次实现 | 原独立提示标签 `.stand-badge-tip#standTip` 随 `transport-caps` 整行删除；将「大屏看谱」作为辅助说明注入 `#standBtn` 的 `title` 属性，既保持监视条精简克制，又无损保留儿童/家长操作指引。 |
| C5 | 仪表盘计时文字 | `00:00 · 待开始`<br>`XX:XX · 练习中`<br>`待选择票夹科目与时长` | **由主读数与刻度尺全面承接**<br>（DOM 保留无障碍辅助节点） | `#opsTimerText`<br>（主视觉已由 `#readoutDigits` 覆盖） | 段 B1 本次实现 | 原 `transport-caps .ops-kicker#opsTimerText` 视觉展示行整块移除（MRD §2.3.5）。功能论证：准备态目标时长已由中心空心数字显式展示，计时态运行读数（`MM:SS`）由 `#readoutDigits` / `#metaVal` 每秒实时渲染，进度由 `.ruler` 刻度指针与卷草纹生长呈现，未准备就绪由开始按钮就绪门禁与 spotlight 引导承接；DOM 保留 `#opsTimerText` 作为辅助状态节点，防止既有脚本空指针。 |
| C6 | 底栏补充说明行 | `Dizical` 品牌 Logo<br>`00:00 · 待开始`<br>`大屏看谱` | **整块删除** | `.transport-caps.grid-3col` | 段 B1 本次实现 | MRD §2.3.5 明确定案：deck 区域的所有底部的补充说明文字（`transport-caps grid-3col`）全部移除，让仪表盘更加简洁聚焦。原 Dizical logo、计时文字行、大屏看谱独立标签全部下线。 |
| C7 | 麦克风监听与收音 | 面板顶部：`MIC 关` / `MIC 开`<br>监视条左侧：`监听关` / `监听中`<br>监视条右侧：`收音` | **合并至监视条**<br>文案：`MIC 关` / `MIC 开`（带呼吸点与激活状态） | `section.diag-card .diag-status > #panelMicBtn` | 段 B2-A 本次实现 | MRD §2.3.2.1 第一分支定案：将面板顶部 `.panel-head` 的 `#panelMicBtn` 移除，合并迁移至下方监视条 `section.diag-card` 的 `.diag-status` 内，与 `#micToggleBtn` 逻辑整合为单按钮操作与状态反馈。保留隐藏 `#diagMicStatus`/`#diagMicDot`/`#micToggleBtn` 兼容测试。 |
| C8 | 仪表盘底部 c-left 昨日时长 | 现状：`今日 42分`（`#todayTotal`） | 准备态未选科目：**无文案**<br>选中科目后：**`昨天练了 x.x分`**（点击打开科目累计弹窗） | `panel-foot .c-left > #yesterdaySubjBtn` | 段 B2-A 本次实现 | MRD §2.3.3.1 与 2026-11-06 拍板（ARCH §4.0 C7）：c-left 作为科目累计记录弹窗（`#pkSubjectStatsModal`）唯一触发入口。未选科目时无文案，选中后展示「昨天练了 x.x分」（昨日秒数 ÷ 60，保留 1 位小数）。保留隐藏 `#todayTotal` 兼容测试。 |
| C9 | 仪表盘底部 c-right 音符节奏 | 现状：`BPM 60 · 静音`（`#bpmRead`） | 展示：**`♩=96`** 或 **`♪=192`**（单读数）<br>点击：打开全局音符节奏弹窗（`#pkTempoModal`） | `panel-foot .c-right > #bpmToggleBtn` | 段 B2-A 本次实现 | MRD §2.3.3.2 与 2026-11-06 拍板（ARCH §4.0 C19）：废弃双读数并列方案，采用单读数聚焦展示。点击唤起全局 `#pkTempoModal`，支持四分音符/八分音符分段选择、40–200 BPM 步进与 60/80/96/108/120 常用预设，取消与确认更新。 |
| C10 | 票夹去重瘦身 | 票夹内存在 BPM 调节网格、时长调节网格、打开票夹按钮等 | **整块删除**<br>（保留票头编号与 Hero 封面，删除重复的 BPM/时长调节网格） | `#pkTicketCard`<br>（删除 `.pk-ticket-digits-grid`、`#pkFolioBtn`） | 段 B2-A 本次实现 | MRD §2.3.1 / C4 定案：票夹内与仪表盘重复的 BPM 调节（`#pkBpmVal`, `#pkBpmDown`, `#pkBpmUp`, `#pkTicketNoteBtn`）和时长调节（`#pkTicketDurVal` 等）整块移除，彻底精简为纯粹票卡外观，避免双重输入混淆。相关 JS 引用平滑重构。 |
| C11 | 科目选择入口迁移 | 票夹内多处点击打开票夹弹窗 | **仪表盘封面作为唯一入口**（`title="点击更换科目"`） | `tpl-A .cover-frame > #dashCoverFrame` / `#dashCoverImg` | 段 B2-A 本次实现 | MRD §2.3.1 / C5 / C9 定案：收敛科目选择入口至仪表盘封面 `.cover-frame`，点击呼出 `#pkFolioModal`，移除票夹内 `#pkFolioBtn` 与 `#pkTicketHeroFrame` 的点击打开逻辑。 |
| C12 | 科目弹窗承接 Session 标签 | 仅在票夹附券展示 session pills | **科目弹窗各科目内展示全部 session 药丸网格** | `#pkFolioModal .pk-folio-item > .pk-folio-item-sessions` | 段 B2-A 本次实现 | MRD §2.3.1 / C6 + C24 定案：将 session 标签选择前置到 `#pkFolioModal`，弹窗升级为大尺寸沉浸视窗，每个科目卡片展开展示其全部 session 药丸，点击药丸一键选中科目与目标 session 并完成数据绑定。 |

---

## 2. DESIGN.md §5.9 定案文案不许改清单（7 条逐条核对）

按照项目设计规范 `docs/practice-dsh/DESIGN.md` §5.9，以下 7 条文案为不可变更的既定契约。本次段 B1 改动已完成逐条代码审查，确认全部严格遵守，无任何改动或覆盖：

| 规范条目 | 契约文案 | 规范所属组件 / 场景 | 本次段 B1 审查结论 |
|---|---|---|---|
| 1 | **`检票 · 开始练习`** | 票夹展开态准备就绪行动按钮 | ✅ **未改动**（属于票夹主体，本批不碰） |
| 2 | **`收回槽内 ✕`** | 卡片展开层返回卡槽按钮 | ✅ **未改动** |
| 3 | **`展开卡片 ▾`** | 卡槽露出条 `pk-exposed-expand-hint` | ✅ **未改动**（MRD C15 更换为「重新选择」属于段 B2，本批严格未碰） |
| 4 | **`重新选择`** | 计时态窄条 `ticketBarVert` / `ticketBarHoriz` | ✅ **未改动** |
| 5 | **`提前结束`** | 仪表盘操作药丸副操作按钮 `#btnEarly` | ✅ **未改动**（保留在 `#btnEarly`） |
| 6 | **`切到练习态`** | 顶栏调试切换按钮 `#pkStateToggle` | ✅ **未改动**（顶栏保留该按钮与文案） |
| 7 | **`刷新布局`** | 顶栏重排按钮 `#pkRelayoutBtn` | ✅ **未改动**（顶栏保留该按钮与文案） |

---

## 3. 关键交互文案决策依据

### 3.1 顶栏入口：为什么复用改造 `#pkRecords` 而不是新增第二个 Pill？
1. **防止顶栏拥挤与溢出**：
   顶栏现存关键节点：`练习准备`（品牌）、`女儿竹笛早课`（标题）、`#pkStateToggle`（切到练习态）、`#pkRelayoutBtn`（刷新布局）、`#pkRecords`（记录入口）、`#pkRunStat`（今日累计）、`#pkVerWrap`（版本角标）。
   在 iPad 竖屏（744px）及手机视口（≤480px）下，空间极度紧凑。如果新增独立 pill，将出现「今日记录 X分·X次 ▾」与「练习记录」两个含义高度重合的入口，并导致 ≤480px 下次级行发生非预期三次换行折断。
2. **单一真源与事件迁移**：
   既有 `#pkRecords` 本身就绑定了 `openRecordsDrawer` 并接收 `__czApplyDay` 的云端数据回灌（`mins` 与 `sessions.length`）。将其文字定案为 `练习记录 — ▾`（有数据时为 `练习记录 X分 · N次 ▾`），既百分之百满足 MRD §2.1「在 pk-top 内增加一个练习记录 pill 作为入口」的业务初衷，又消除了双入口歧义，保证全站数据回灌链路平滑升级。

### 3.2 计时文字 `#opsTimerText` 移除后的功能承载
MRD §2.3.5.1 要求删除 `transport-caps` 说明文字行。原行中央的 `opsTimerText` 曾承载「00:00 · 待开始 / 练习中」文字。
本改造经过功能完整性评估，该信息并未丢失，而是由更高层级的组件以更好的视觉层次完全覆盖：
1. **练习时长与运行计时**：
   仪表盘中心的核心视标 `#readoutDigits`（采用 monoline hollow digits 引擎）在准备态显式指示目标分钟数（如 `10`），在练习中（run 模式）则直接每秒渲染实时 `MM:SS` 倒计时/正计时数值。
2. **进度感知**：
   仪表盘内置的 `.ruler` 刻度尺红针高亮跟随、卷草藤蔓渐进开花（vine bloom）提供直观的物理进度反馈。
3. **未就绪告警**：
   票夹未选齐科目与内容时，开始按钮触发的 ready guide（聚焦光斑引导）承担了明确的行为指引。
4. **无障碍兼顾**：
   在 DOM 中保留 `#opsTimerText` 节点作为隐藏的 `aria-live` 辅助节点，保证原有脚本逻辑不报错，屏幕朗读工具仍可获取状态变化。
