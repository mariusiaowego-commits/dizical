# spec-agy-records-card-261012 · 今日练习记录小卡与 Popout 弹窗规格

> **文档归属**：Sprint 26100301 (practice 页右栏重构) ｜ 交付物 C  
> **上游 MRD**：`tqob/05-Coding/project-dizical/PRDs/MRD-左右栏组合问题.md`（标题 `## 2610120839-demo v3.2` 第 5 条）  
> **参考图基线**：`docs/demos/practice-right-column-261003/参考图文字基线-261012.md`（dad image21 / image23 逐图读数）  
> **样式溯源**：`practice-duration-card-01-v3.html` (`card-practice-duration` Bauhaus Widget)  
> **任务 Brief**：`docs/demos/practice-right-column-261003/brief-agy-combos-261012.md` §C  
> **设计责任人**：agy ｜ 状态：正式设计规格（已按参考图基线校正）

---

## 1. 业务角色重塑与形态演进

### 1.1 Dad MRD 第 5 条原文
> “今日练习记录不用设计为卡片了，卡片的内容转成点击一个小卡片后popout弹窗来展示。今日练习记录copy `card-practice-duration`今日练习时长卡设计一个卡片样式。”

### 1.2 演进原因
旧版 `today-records-01.html` 是一个宽度 460px、高度 600px+ 的巨幅表格控制台（Console Table）。直接将庞大的表格塞在右栏常驻显示，既挤占了核心练习空间，又导致右栏极度拥挤、信噪比极低。

### 1.3 双层架构定义
本设计将「今日练习记录」重构为**两层协同体系**：
1. **常驻层：紧凑型小卡片（Mini Record Widget）**：
   - 样式 1:1 复刻 `card-practice-duration`（包豪斯高阶拟物质感）；
   - 负责高频、一瞥即知（Glanceable）的核心指标提炼（今日总练习遍数、完成科目数）；
   - 面积大幅缩减，完美支持与时长卡并排“卧”在仪表盘底部（如组合 1）。
2. **沉浸层：明细弹窗（Record Detail Popout Modal）**：
   - 用户点击小卡片即刻弹出；
   - 承载完整的多 Session 列表、遍数流水、时长趋势、各曲目手写批注及与昨日对比。

---

## 2. 今日练习记录小卡片视觉规格（常驻层）

小卡片（组件类名：`.card-records-mini`）深度继承 `practice-duration-card-01-v3.html` 的全部设计语言，确保与今日练习时长卡放置在一起时具备孪生般的视觉协调度。

```
┌────────────────────────────────────────────────────────────┐
│ .card-records-mini (深炭卡底/白瓷卡底 · 大圆角 R=26px)     │
│                                                            │
│  Today 17 (日期行)                     [ 4 Sessions 胶囊 ] │
│                                                            │
│  █ █  █ █ (空心线框 Monoline SVG 数字: "18" 遍)            │
│                                                            │
│  ────────── 极细刻度分割线 (var(--dash-ink-a12)) ─────────  │
│                                                            │
│  已练 3 科目 · 达成率 100%                 查看明细 ↗     │
└────────────────────────────────────────────────────────────┘
```

### 2.1 样式与材质规格（严格对齐 Token）

| 视觉属性 | 规格参数 | Token 映射与取值 |
|---|---|---|
| **外壳底色** | 深浅双皮自适应 | `var(--dash-surface-soft)`（浅银 `#FFFDFB` / 深墨 `#1A1E22`） |
| **外框边线** | 1px 细微光边 | `1px solid var(--dash-ink-a12)` |
| **圆角弧度** | 大圆角（适度缩放） | `border-radius: 26px;` |
| **立体投影** | 复合内凹与落阴影 | `box-shadow: 0 12px 28px var(--dash-shell-shadow), inset 0 1px 0 var(--dash-key-hi);` |
| **内边距** | 紧凑排布 | `padding: 16px 18px 14px;` |
| **光标交互** | 整体可点反馈 | `cursor: pointer;`，hover 时微上浮 `translateY(-2px)` 及边线提亮 |

### 2.2 尺寸分档定义（已按 image23 校正）
* **卧式尺寸（用于组合 1 仪表盘底部）**：
  - 宽度：`224px`；高度：`268px`；与今日练习时长卡并排无缝拼接，底线完全平齐（Y=654）。
* **独立轨道尺寸（用于单行展示）**：
  - 宽度：`340px ~ 380px`；高度：`220px ~ 260px`。

### 2.3 内容结构排布
1. **顶部日期与概览行 (`.mini-head-row`)**：
   - 左侧：日期小字 `Tuesday 17`（`font-size: 13px; font-weight: 600; color: var(--dash-text);`）；
   - 右侧：状态胶囊 `3 Sessions`（浅橙底朱红字，`background: var(--dash-vermilion-wash); color: var(--dash-vermilion-text);`）；
2. **核心英雄指标行 (`.mini-hero-row`)**：
   - 采用同款 SVG 空心线框字形（Monoline SVG Glyphs），高度 `44px`；
   - 醒目展现今日核心完成度：例如 `18`，右侧配底部对齐小字 `遍`（`font-size: 13px; font-weight: 700;`）；
3. **指标副标行 (`.mini-sub-row`)**：
   - 左右两列微型数据：`覆盖曲目: 4 首` ｜ `净练: 42 分钟`；
4. **底栏操作引导 (`.mini-foot-row`)**：
   - 右下角常驻醒目的微型展开标记：`查看明细 ↗`（带轻微悬停动效），明确传达该卡片具备深入下钻能力。

---

## 3. Popout 弹窗设计规格（明细层 · 针对 image21 缺陷加固）

用户点击小卡片任意位置，触发全局模态弹窗（类名：`.popout-records-modal`）。

### 3.1 遮罩层与定位基准（根治“叠在一起/无遮罩”事故）

根据 dad 参考图 image21 的现场复盘，弹窗“和后面内容叠在一起”的根本原因是**浮层缺乏压暗遮罩、缺乏物理抬升及背景未做彻底不透明处理**。本规格对此做出了刚性加固：

```css
/* 全局防穿透遮罩层：高层级、深度压暗、强模糊 */
.popout-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000; /* 必须高于所有卡片与 iframe 脚手架 */
  background: rgba(14, 17, 20, 0.72) !important; /* 强制深度压暗背景 */
  backdrop-filter: blur(12px) !important; /* 强高斯模糊，彻底消除背景字迹干扰 */
  -webkit-backdrop-filter: blur(12px) !important;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

/* 弹窗本体：强制 100% 不透明纯实色底 + 强投影 */
.popout-panel {
  width: 600px;
  max-width: calc(100vw - 32px);
  max-height: 82vh;
  background: var(--dash-surface-soft) !important; /* 严禁任何半透明！ */
  color: var(--dash-text);
  border: 1.5px solid var(--dash-ink-a16);
  border-radius: 32px;
  box-shadow: 
    0 28px 72px rgba(0, 0, 0, 0.45),
    0 4px 16px rgba(0, 0, 0, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.85); /* 强烈边缘抬升光 */
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  z-index: 10001;
}
```

### 3.2 内容分区架构

弹窗内部划分为三大视觉分区：

```
┌──────────────────────────────────────────────────────────────┐
│ [今日练习记录明细]                      Tuesday 17  [ × 关闭 ] │ ── 弹窗顶栏
├──────────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│ │  总时长 52分 │  │  练习 18 遍  │  │ 较昨日 +14分 (▲ 增)  │ │ ── 全景看板
│ └──────────────┘  └──────────────┘  └──────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│ 练习时间流水 (可纵向滚动区域 overflow-y: auto)               │
│                                                              │
│  [16:40] 全按作5 音阶练习 ────────────── 15分钟 · 6遍 · 80BPM │
│         分句：第 1-8 小节 · 舌音清晰                         │
│                                                              │
│  [17:05] 吸气长音 ───────────────────── 12分钟 · 4遍 · 60BPM │
│         风门稳定，尾音不飘                                   │
│                                                              │
│  [17:25] 姑苏行 慢板 ────────────────── 15分钟 · 8遍 · 72BPM │
│         历音连贯                                             │
├──────────────────────────────────────────────────────────────┤
│ 底部状态汇总：共 3 个 Session ｜ 净练 42分   [ 折叠明细按钮 ] │ ── 底部操作区
└──────────────────────────────────────────────────────────────┘
```

#### 分区 1：弹窗顶栏与全景看板（Today Overview Bar）
* **顶栏**：
  - 标题：`今日练习记录明细`（`font-size: 17px; font-weight: 750;`）；
  - 右侧关闭按钮：大触摸热区圆钮（`40×40px`，`border-radius: 50%`，浅底深色图标，居于视觉右上角）。
* **全景看板（三列卡片）**：
  - 列 1：今日总跨度（首个练习到当前，如 `52分`）；
  - 列 2：核心练习遍数（全部科目有效遍数累加，如 `18遍`）；
  - 列 3：相比昨日差异（朱橙 Tag `+14分`，带向上箭头图标）。

#### 分区 2：时间流记录列表（Timeline List View）
* **滚动体验**：采用原生极细滑轨（`scrollbar-width: thin`），弹性滚动。
* **卡片条目排布（Item Rows）**：
  - 每条记录呈现为一个独立的微型条目卡（`.record-entry-card`，背景 `var(--dash-surface-2)`，圆角 14px，padding 12px 14px）；
  - **首行**：左侧练习时分（`16:40`，Mono 字体）+ 曲目标题加粗；右侧时长、遍数胶囊、BPM 速度；
  - **次行**：科目标签（`.tag`，如 `吐音`、`音阶`）+ 教师批注/手写备注摘要。

#### 分区 3：底栏统计与操作（Modal Footer）
* 左侧显示今日打卡汇总徽标；
* 右侧提供显式的「完成 / 关闭」实体胶囊按键。

---

## 4. 交互模型与状态管理

### 4.1 打开通道（Open Trigger）
* 点击小卡片（`.card-records-mini`）的任何区域，向外广播 `OPEN_RECORDS_POPOUT` 事件；
* 遮罩层以 `120ms` 线性淡入，弹窗容器以 `200ms` `cubic-bezier(0.2, 0.8, 0.2, 1)` 从 `scale(0.96)` 微缩放大居中展开；
* 弹窗打开期间，主页面背景滚动被冻结（`document.body.style.overflow = 'hidden'`）。

### 4.2 三重关闭通道（Close Channels）
1. **通道 A（点击关闭按钮）**：点击右上角实体 `×` 按钮；
2. **通道 B（点击外部遮罩）**：点击弹窗主体以外的 `.popout-backdrop` 区域；
3. **通道 C（键盘无障碍）**：按键盘 `Escape` 键立即平滑关闭。

---

## 5. 验收断言标准

1. **小卡片规格断言**：
   - 小卡片类名必须为 `.card-records-mini`，外壳包含 `Tuesday 17` 日期标识与 SVG 空心大字；
   - 组合 1 状态下，小卡片宽度不得超过 `230px`，高度严格在 `260px ~ 270px` 之间，与时长卡底部绝对平齐；
2. **弹窗防穿透断言**：
   - 弹窗唤起后，`.popout-backdrop` 的 computed `background-color` 的 alpha 值必须 $\ge 0.65$；
   - `.popout-panel` 的 computed `background-color` 必须为不透明色（alpha 值为 1.0）；
   - `document.body.style.overflow === 'hidden'`；
3. **关闭逻辑断言**：
   - 触发关闭（Esc / 遮罩点击 / 关闭按钮）后，弹窗立即隐藏，`document.body.style.overflow` 恢复为空。

---

## 6. 按参考图基线校正（image21 / image23 逐图校对结论）

1. **小卡片高度与组合 1 底部平齐校正（对照 image23）**：
   - *原规格偏差*：原设定高度为 186px，与修正后的 370px 仪表盘组合后，总高（370+186=556px）未能填满 654px 包络线；
   - *基线校正*：小卡片高度随今日时长卡同步修正为 **268px**，两张小卡并排卧于仪表盘底部，顶距仪表盘 16px，底边与 Y=654 票卡底线精准吻合，严格契合 image23 的上下一体比例。
2. **根除 image21“无遮罩/文字重叠”严重视效事故**：
   - *事故真相*：image21 读数证实，旧版弹窗打开时由于缺失背景遮罩与清晰分界，导致弹窗文字与后方曲目列表完全重叠穿透，引发 dad 强烈质问；
   - *校正规约*：在规范中把 `.popout-backdrop` 的背景强制设定为 `rgba(14, 17, 20, 0.72) !important` + `backdrop-filter: blur(12px) !important`，层级钉死在 `z-index: 10000`；弹窗主体 `.popout-panel` 强制 100% 实体不透明白瓷/深墨底，并配备 `0 28px 72px rgba(0, 0, 0, 0.45)` 强立体阴影，确保弹窗与背景实现 100% 绝对物理隔离。
