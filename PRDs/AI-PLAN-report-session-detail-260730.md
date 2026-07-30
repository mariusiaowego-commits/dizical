---
title: AI-PLAN report 练习明细展示
date: 2026-07-30
source: ai-agent
tags:
  - dizical
  - plan
  - report
  - practice-sessions
status: ready-to-execute
aliases:
  - report session detail plan
---

# Plan: Report 页练习明细（科目下 sessions）

> **For Hermes / dad:** report 页把 `practice_sessions` 明细接到两处展示入口：竹笛 modal（`modal-content` / `seg-item` 下方）+ 日历点击后的当日卡片。前端为主，API 已就绪。
>
> **范围:** `src/kid_app/templates/report.html` 为主；不改 practice 写入路径、不改小程序、不改月累计/柱图聚合语义。
>
> **执行者:** 本会话直接落地（plan 写完即开分支实现）。
>
> **YAGNI:** 不新增后端 endpoint；不重做竹笛视觉；不在 hover tooltip 里塞全量 session（空间不够）。

---

## 0. 已核实事实（不靠印象）

| 编号 | 事实 | 证据 |
|---|---|---|
| F1 | 练习明细真相表是 `practice_sessions`：`duration_minutes` + `tempo_note`/`tempo_bpm` + `content` + `item_name`/`item_id` | `data/dizi.db` schema + 2026-07-29 行（吸气长音 10+2、西藏舞曲 8 条分句等） |
| F2 | `daily_practices.items` 只是科目汇总，无细节 | 2026-07-29 items 合计 55 分，无 content |
| F3 | `GET /api/practices/{date}` **已返回** `sessions[]`（按时间升序） | `src/kid_app/app.py:972-995` |
| F4 | report modal `openDiziModal` 只渲染 `items` → 横向 `seg-item`，**不读 sessions** | `report.html:690-716` |
| F5 | 日历点击已有 `#dayDetail`，但 body 只写「总时长 vs 昨日」+ `behavior_log` 轨迹，**没有科目组成、没有 session 明细** | `report.html:792-839` |
| F6 | practice 页已有成熟分组 UI：`record-group` / `record-session`（科目头 + 行：速度/内容/分钟） | `practice.html:486-492, 2106-2220` |
| F7 | 柱图 bar 点击 → `openDiziModal(date)`；日历点击 → `#dayDetail`（两条入口独立） | `report.html:635-638, 767-859` |
| F8 | `#dayDetail` 目前在整张大 card（含月图/月累计/stage）**之后**，不是日历正下方 | `report.html:212-248` |
| F9 | 目标设备：iPad mini 横屏 ~1024×768 + Mac 浏览器；modal 现 `max-width:760px; width:94%`，无 `max-height`/滚动 | `report.html:103-110` |

### 练习明细是什么（给 UI 文案对齐）

一次计时 = 一条 session，展示格式对齐 practice 页：

```
科目名                         N 分钟
  ♪=60   正常长音练习            10min
  ♪=60   正常长音练习             2min
```

- **速度**: `{tempo_note}={tempo_bpm}`（如 `♪=80`、`♩=70`）
- **内容**: `content`；空则显示「未填写练习内容」（与 practice 一致）
- **分钟**: `duration_minutes`
- **额外**: `is_extra=1` 可加小标签「额外」（可选，V1 可先不做以免拥挤）
- **旧数据**: 有 `items` 分钟但 sessions 未覆盖时，补「历史汇总」伪行（复用 practice 页 legacy 逻辑）

示例（2026-07-29 总 55 分）:

| 科目 | 汇总 | 明细 |
|---|---|---|
| 吸气长音 | 12 | 10 正常长音练习 ♪=60；2 同 |
| 单吐tuku | 5 | 2 ku ♩=70；3 tu ♩=80 |
| 西藏舞曲 | 16 | 第1–5句各 2 + 24拍第一句 2(extra) + 2/4拍第2/3句各 2 |
| 萨丽哈 | 9 | 3 低音/中音拆练；6 背全曲 |
| 单吐练习 | 3 | 3 全曲 ♩=92 |
| 回娘家 | 5 | 5 加速、背谱 ♪=88 |
| 采茶扑蝶 | 5 | 5 2/4拍一整句 ♪=112 |

---

## 1. 目标 / 非目标

### Goals

- **G1** 竹笛 modal（`#diziModal .modal-content`）在科目（seg）概览下方展示该日 **按科目分组的 session 明细**，往下展开、可滚动
- **G2** 点击日历日期后，在日历**正下方**出现/刷新一张卡片，展示该日总分钟 + **组成**（科目汇总 → 其下 session 明细）
- **G3** 适配 1024×768（iPad mini 横屏）与 Mac：modal 可放大但有 max-height + 内部滚动，不撑破视口
- **G4** 抽出共享 `renderSessionGroups(items, sessions)`，modal 与 dayDetail 共用，避免两套文案/结构漂移
- **G5** report 内其它「科目练习情况」入口 review 清楚：该展示明细的展示，聚合视图不硬塞

### Non-Goals

- 不改 `/api/practices/{date}` 合同（已够用）
- 不改 practice 写入、config 补录、小程序
- 不在月累计 bar / 柱图 hover tooltip 里列 session（空间与语义都是聚合）
- 不重做竹笛背景/横向 seg 视觉（只在下方加明细区）
- 不做 dayDetail 内编辑/删除 session（只读；编辑在 practice 页）

---

## 2. Report 全页 review：哪些位置要展示明细

| 位置 | 当前展示 | 是否加 session 明细 | 决策理由 |
|---|---|---|---|
| **A. `#diziModal`（柱图 bar 点击）** | 竹笛图 + 横向 seg-item（科目名+分钟） | **必须** | 用户明确要求；科目日级详情入口 |
| **B. `#dayDetail`（日历日期点击）** | 总时长 vs 昨日 + behavior_log 轨迹 | **必须** | 用户明确要求「55 分怎么组成」 |
| **C. 柱图 bar hover tooltip** | 单科目当日分钟 + vs 昨日 | 否 | tooltip 空间极小；点击已进 modal |
| **D. 月科目累计 `#monthSummaryCard`** | 全月科目合计横条 | 否 | 月聚合，无「单日 session」语义 |
| **E. Stage 周图 legend** | 科目色点 | 否 | 图例 |
| **F. 日历格子本身** | 热力色 / 分钟角标 | 否 | 格子信息密度已满 |
| **G. 练习轨迹 `renderTrail`** | behavior_log 时间线 | **保留为次要** | 有时序价值；明细以 sessions 为主；V1 放在科目明细下方，不删除 |

> **结论:** 只有 **A + B** 需要加 session 明细；C–F 保持聚合；G 保留轨迹，位置调整到明细之后。

---

## 3. UI / 布局方案

### 3.1 共享明细块（科目分组）

结构（对齐 practice，report 只读、无编辑按钮）:

```html
<div class="rp-session-list">
  <div class="rp-group">
    <div class="rp-group-header">
      <span class="rp-g-name">西藏舞曲</span>
      <span class="rp-g-mins">16 分钟</span>
    </div>
    <div class="rp-session">
      <span class="rp-tempo">♪=80</span>
      <span class="rp-content">第1句</span>
      <span class="rp-mins">2min</span>
    </div>
    <!-- ... -->
  </div>
</div>
```

分组规则（与 practice `renderTodayRecords` 一致）:

1. 以 `items[]` 科目顺序为主序（报告「组成」与汇总一致）
2. 将该 `item_id` 的 sessions 挂到组下
3. 若 `items.minutes > sum(sessions)`，补一条伪 session：`content='历史汇总'`、无 tempo、不可点
4. 仅有 session、items 缺席的（理论少见）按 session 出现顺序追加

### 3.2 Modal（A）

```
┌─ modal-content (max-width ~860px, max-height ~min(88vh,720px), overflow-y auto) ─┐
│  日期 + 总练习 N 分钟                                                    [×]   │
│  [竹笛图]                                                                     │
│  [横向 seg-item 条 — 保留]                                                    │
│  ── 练习明细 ──                                                               │
│  科目A  12分钟                                                                │
│    ♪=60  正常长音练习                                              10min      │
│    ♪=60  正常长音练习                                               2min      │
│  科目B  ...                                                                   │
│  footer                                                                       │
└───────────────────────────────────────────────────────────────────────────────┘
```

- `#segmentsContainer` 保持 absolute 横向；**不要**把 session 塞进每个 absolute `seg-item`（窄宽百分比下会挤爆）
- 明细区 `#modalSessionDetail` 放在 `segmentsContainer` **下方**，视觉上「跟在科目段落后面往下展」
- iPad 768 高：header+竹笛+seg 约占上半，明细区滚动

### 3.3 日历当日卡（B）

- **DOM 位置调整:** `#dayDetail` 移到 `.cal-grid` **正下方**（月图/月累计之前），满足「正下方」
- 卡片内容顺序:
  1. 标题：`7月29日 · 练习 55 分钟`（可读中文日期更好，可保留 `YYYY-MM-DD` 副标）
  2. 总时长行 + vs 昨日 diff（保留现有）
  3. **科目组成 + session 明细**（新，主内容）
  4. 练习轨迹（可选保留）
- 点另一天：原地刷新；切月：清空/隐藏（现有逻辑保留）
- Stage 周图仍可在下方继续加载（不挡明细）

### 3.4 响应式

| 视口 | modal | dayDetail |
|---|---|---|
| ≤1024 宽 / ~768 高 | `width: min(94vw, 860px)`；`max-height: 88vh`；内容 `overflow-y: auto`；seg 字号略缩 | card 全宽，session 行可换行 |
| Mac 大屏 | `max-width: 860px` 居中；明细更疏一点 padding | 同 |

---

## 4. 实现步骤

### 阶段 0：分支

```bash
git checkout main && git pull
git checkout -b feat/report-session-detail
```

### 阶段 1：共享渲染 + CSS

**Modify:** `src/kid_app/templates/report.html`

- 新增 CSS：`.rp-session-list` / `.rp-group` / `.rp-session` …（色系跟 modal 米黄 `#FFFDF8` / 金 `#8B6914` 与 dizicute 珊瑚点缀，弱化 CTA）
- 新增 JS：
  - `escapeHtml(s)`
  - `buildDisplaySessions(items, sessions)` — legacy 补齐
  - `renderSessionGroupsHtml(items, sessions)` → HTML 字符串
  - `formatCnDate(iso)` 可选

### 阶段 2：dayDetail

- 移动 HTML 节点到日历正下方
- 日历 click handler 在拿到 `data` 后插入 `renderSessionGroupsHtml(data.items, data.sessions)`
- 空数据文案保持；有 total 无 session 时仍展示科目汇总行

### 阶段 3：openDiziModal

- HTML 增加 `<div id="modalSessionDetail"></div>`（`#segmentsContainer` 与 footer 之间）
- fetch 后同时渲染 segs + session 明细
- CSS：`.modal-content` 加 max-height + overflow

### 阶段 4：验收

- 本机打开 `/report`，点 2026-07-29：
  - dayDetail 显示 55 分组成 + 西藏舞曲分句等
  - 点月图该日 bar → modal 有同样明细、可滚动
- 1024×768（浏览器 DevTools 或 iPad）不裁切、可关
- 无练习日：友好空态
- 不回归：月图、月累计、切月、Escape 关 modal

### 阶段 5：收尾

- 测通后 commit + PR
- 双写：本 plan 已在 vault；主仓 `PRDs/` 同步一份
- 按 AGENTS checklist 更新 `vibe-coding-log.md` / handoff（实现后）

---

## 5. 文件改动清单

| 文件 | 动作 |
|---|---|
| `src/kid_app/templates/report.html` | **主改动** CSS + HTML 结构 + JS |
| `PRDs/AI-PLAN-report-session-detail-260730.md` | 主仓镜像 plan |
| vault `project-dizical/PRDs/` 同名 | 本文件 |
| 后端 / API-CHANGELOG / minip | **不改**（✅ 完全兼容，无 API 变化） |

---

## 6. 风险与边界

| 风险 | 缓解 |
|---|---|
| 一日 session 很多（如西藏舞曲 8 条）modal 超高 | max-height + 内部滚动 |
| seg-item absolute 宽度极窄无法塞明细 | 明细独立列表，不塞进 absolute 节点 |
| XSS：content 用户输入 | `escapeHtml` / textContent 风格拼接 |
| items 与 sessions 分钟不一致 | legacy 伪行补差，与 practice 一致 |
| 今天未结束空态 | 保留「今天还没过完」逻辑 |

---

## 7. 验收标准（DoD）

- [ ] 日历点 7/29 → 正下方卡片：总 55 分 + 各科目 + 每条 session（速度/内容/分钟）
- [ ] 柱图点 7/29 → modal 有 seg 概览 + 下方同等明细，滚动不破 1024×768
- [ ] 无 session 旧日：至少显示科目汇总；有差量显示「历史汇总」
- [ ] 切月隐藏 dayDetail；Escape/遮罩关 modal
- [ ] 月累计/tooltip 行为不变
- [ ] feature 分支 + PR

---

## 8. 相关笔记

- [[AI-PRD-练习计时细分内容-260727]]
- [[AI-plan-练习计时细分内容-纯备注-260727]]
- [[AI-tech-spec-practice-v3.1-260728]]
- practice 页今日记录实现：`practice.html` `renderTodayRecords`

---

## 9. 执行记录

| 时间 | 事件 |
|---|---|
| 2026-07-30 | plan 写入 vault |
| 2026-07-30 | 分支 `feat/report-session-detail`；改 `report.html`：共享 `renderSessionGroupsHtml`、dayDetail 移日历正下方、modal 加 `#modalSessionDetail` + max-height 滚动 |
| 2026-07-30 | 验收：API 2026-07-29 = 55 分 / 7 items / 17 sessions；`/report` 200 已吐新 HTML |
