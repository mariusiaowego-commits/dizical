---
title: AI-PLAN Stage 维 Session 明细打印页
date: 2026-07-30
source: ai-agent
tags:
  - dizical
  - plan
  - stage
  - practice-sessions
  - print
  - A4
status: implementing
aliases:
  - stage session print
  - 阶段练习明细打印
---

# Plan: Stage 维 Session 明细展示（A4 打印 HTML）

> **For Hermes / dad:** 把每次 **session**（`practice_sessions` 一行 = 一次科目计时）按 **stage**（课次周期 `stage_start`→`stage_end`）聚合，输出可打印 A4 的 HTML 页，给观摩者看清「这个阶段每天/每科练了什么、多久」。
>
> **范围:** 只读聚合 + 打印向 HTML；不改写入路径、不改小程序。
>
> **分支:** `feat/stage-session-print-report`
>
> **YAGNI:** 不做 PDF 导出服务、不做 AI 摘要、不做「一天 N 场」分段；打印先浏览器 Ctrl/Cmd+P。

---

## 1. 术语表（以后交流用这个）

| 代称（交流用） | 代码 / 表 | 中文 UI 可用 | 是什么 |
|---|---|---|---|
| **session** | `practice_sessions` 一行 | **练习明细 / 一次计时** | 选科目 → 计时提交的 **1 次**；含 `duration_minutes`、`tempo_note`+`tempo_bpm`、`content`、`started_at`、`is_extra` |
| **item** | `practice_items` / session 的 `item_id` | **科目** | 如「西藏舞曲」「吸气长音」 |
| **daily 汇总** | `daily_practices.items[]` | **当日科目合计** | 同一天同科目多条 session **分钟之和**；**无** content/速度细节 |
| **stage** | `weekly_assignments.stage_*` | **阶段 / Stage N** | 一节课后到下一节课前的练习周期：`stage_start` = 上课日+1，`stage_end` = 下一节课日（含），`stage_order` = 序号 |
| **assignment** | `weekly_assignments.items[]` | **老师要求 / 作业** | 本 stage 科目清单 + `requirements` + `metronome`（观摩对照用） |
| **behavior_log** | `daily_practices.behavior_log` | （审计轨迹，一般不打印） | 审计用，**不是**明细真相；打印以 **session** 为准 |

### 推荐说法（对 dad / agent）

- 说「**session**」或「**练习明细**」= 单次计时细节（本需求的原子行）
- 说「**item** / 科目」= 科目维度
- 说「**stage 维聚合**」= 把 `[stage_start, stage_end]` 内所有 session 汇总成一页
- **不要**说「场次」指 session（6-22 MRD 里「一天 N 场」是另一概念，V2 未做）

```
stage (课次周期)
 └─ day (自然日)
     └─ item (科目)
         └─ session × N  (每次计时: 时长 + 速度 + content)
```

**示例（Stage 15: 2026-07-19 → 2026-07-25）**  
西藏舞曲 6 sessions / 43 min；吸气长音 5 sessions / 42 min …  
其中某日：西藏舞曲 第1句 2min ♪=80 · 第2句 2min ♪=80 …

---

## 2. 目标 / 非目标

### Goals

- **G1** 选定一个 stage，生成 **一页 A4（竖向优先；内容过多可自动续页）** 可打印 HTML
- **G2** 精确到每条 **session**：科目、时长、速度、内容、日期/时间、是否额外
- **G3** stage 维度总览：总分钟、练习天数、session 数、按科目小计
- **G4** 可选对照：**老师要求**（本 stage assignment 的 requirements / metronome）
- **G5** 入口：report 页或独立路由（如 `/report/stage-print?stage=15` 或 `?date=2026-07-29` 解析所属 stage）
- **G6** 文档双写（本 plan + 实现后 handoff）

### Non-Goals（本版不做）

- 服务端生成 PDF / 云打印
- 改 practice 录入 / session 写入
- 小程序同步
- AI 周报文案
- 月维度（month）打印（可 V1.1 复用同一模板）

---

## 3. 展示什么（打印页信息架构）— **先确认这块**

### 3.1 页眉（固定信息）

| 区块 | 内容 | 来源 |
|---|---|---|
| 标题 | 竹笛练习明细 · Stage {N} | `stage_order` |
| 周期 | {stage_start} ~ {stage_end}（共 D 天） | assignment |
| 上课日 | 本节课 {lesson_date} | assignment |
| 汇总一行 | 总练习 **T** 分钟 · 练习 **d** 天 · **s** 次明细 · **k** 个科目 | sessions 聚合 |
| 打印元信息 | 生成时间 CST（小字） | 客户端 now |

### 3.2 科目总览（半页上半或侧栏紧凑）

按 **item** 聚合本 stage：

| 列 | 说明 |
|---|---|
| 科目名 | `item_name` 快照 |
| 次数 | session 条数 |
| 合计分钟 | SUM(duration_minutes) |
| 占比 | / stage 总分钟 |
| 老师要求（可选一行摘要） | assignment 同 item 的 requirements 截断 1 行 |

用途：观摩者 10 秒内知道「这阶段时间砸在哪」。

### 3.3 明细主体（核心 · 观摩细节）

**推荐结构 A（默认）：按日 → 科目 → session**

```
## 7月29日 · 55 分钟 · 17 次明细
### 吸气长音 · 12 分钟
| 时间     | 时长 | 速度   | 内容           | 备注 |
| 17:03    | 10′  | ♪=60   | 正常长音练习   |      |
| 17:05    |  2′  | ♪=60   | 正常长音练习   |      |
### 西藏舞曲 · 16 分钟
| 17:26    | 2′   | ♪=80   | 第1句          |      |
| …        | …    | …      | …              | 额外 |
```

**结构 B（备选）：按科目 → 日 → session**  
适合「只盯一首曲子」的老师；V1 可做切换 `?group=item|day`，默认 **day**。

每条 session **必显**：

| 字段 | 显示 | 说明 |
|---|---|---|
| 日期 | 组头或列 | `practice_date` |
| 开始时间 | HH:MM | 从 `started_at` 解析 CST |
| 科目 | 组头 | `item_name` |
| 时长 | N′ 或 N 分钟 | `duration_minutes` |
| 速度 | ♪=80 / ♩=70 | `tempo_note`+`tempo_bpm`；legacy 无有效值可空 |
| 内容 | 全文 | `content`；空 →「（未填写）」 |
| 额外 | 小标「额外」 | `is_extra` |
| （可选）历史 | 「历史汇总」 | content_source=legacy 或伪行 |

**不打印：** behavior_log 审计串、内部 id（可 data 属性留给调试，不进可见区）。

### 3.4 页脚

- 小字：数据来源 practice_sessions · 仅供观摩/家校沟通
- 页码：`@page` CSS `counter(page)`（浏览器打印支持参差，可接受）

### 3.5 A4 版式约束

| 项 | 建议 |
|---|---|
| 纸张 | A4 竖向 `@page { size: A4; margin: 12mm 14mm; }` |
| 屏预览 | 固定宽 ~210mm 居中白纸阴影（屏幕像纸） |
| 字号 | 正文 9–10pt；表头 8pt；标题 14–16pt |
| 颜色 | 打印友好：灰/墨为主；科目色条可保留但对比够；避免浅粉底大面积 |
| 分页 | 日/科目组 `break-inside: avoid` 尽量不拆行；过长 stage 允许多页 |
| 操作 | 屏上「打印」按钮 → `window.print()`；隐藏 navbar/按钮 `@media print` |

### 3.6 示例数据量（真实）

| Stage | 区间 | sessions | 总分钟 | 观感 |
|---|---|---|---|---|
| 16 | 07-27→08-01 | 36 | 156 | 约 1–2 页 A4 |
| 15 | 07-19→07-25 | 34 | 176 | 约 1–2 页 |

密集分句日（如 7/29 西藏舞曲 8 条）表格行会变多 → **按日分页** 比硬塞一页更重要。

---

## 4. 数据与 API

### 4.1 已有

- `GET /api/practices/{date}` → 单日 `items` + `sessions[]`
- `GET /api/practices/stage/{date}` → 日×科目 **分钟矩阵**（**无** session 明细）→ 图表用，**不够打印**
- `weekly_assignments`：stage 边界 + 老师要求

### 4.2 新增（建议）

`GET /api/practices/stage-detail?date=YYYY-MM-DD`  
或 `?stage_order=N` / `?stage_start=&stage_end=`

响应草案：

```json
{
  "stage_order": 15,
  "lesson_date": "2026-07-18",
  "stage_start": "2026-07-19",
  "stage_end": "2026-07-25",
  "summary": {
    "total_minutes": 176,
    "practice_days": 6,
    "session_count": 34,
    "item_count": 6
  },
  "assignment_items": [
    {"item_id": 1346, "item": "西藏舞曲", "metronome": "♪=80", "requirements": "…"}
  ],
  "by_item": [
    {"item_id": 1346, "item_name": "西藏舞曲", "minutes": 43, "session_count": 6}
  ],
  "days": [
    {
      "date": "2026-07-29",
      "total_minutes": 55,
      "groups": [
        {
          "item_id": 1346,
          "item_name": "西藏舞曲",
          "minutes": 16,
          "sessions": [
            {
              "id": 1068,
              "started_at": "2026-07-29 17:26:04.909",
              "duration_minutes": 2,
              "tempo_note": "♪",
              "tempo_bpm": 80,
              "content": "第1句",
              "is_extra": false
            }
          ]
        }
      ]
    }
  ]
}
```

实现要点：

- 解析 date → 所属 stage（复用 stage chart 查询）
- `SELECT * FROM practice_sessions WHERE practice_date BETWEEN stage_start AND stage_end ORDER BY practice_date, started_at`
- 按日/item 分组；summary 与 by_item 一次扫完
- `lesson_date` 序列化 **必须 isoformat 字符串**（避 `/api/assignments/latest` 同类 500）

### 4.3 前端

- 新模板 `stage-print.html`（或 `report-stage-print.html`）
- 路由 `GET /report/stage-print` 返回页；JS fetch stage-detail 渲染
- report 页入口：dayDetail / stage 图旁「打印本阶段明细」链到当前 stage

---

## 5. 实现阶段

| 阶段 | 内容 | 验收 |
|---|---|---|
| **0** | 术语 + 本 plan 双写 + 分支 | 本文 + 主仓 `PRDs/` MD5 一致 |
| **1** | API `stage-detail` + 单测/手工 curl | 某 stage 总分钟 = SUM(sessions) |
| **2** | HTML 模板 + CSS 打印 A4 | 屏预览像纸；打印预览可读 |
| **3** | report 入口链接 | 一点即开对 stage |
| **4** | 文档收尾 + PR | changelog 若有 API：🟡 新增字段/端点 |

---

## 6. dad 拍板（2026-07-30）

| # | 决策 |
|---|---|
| 1 | 默认分组 **A：按日 → 科目 → session** |
| 2 | 老师要求 **全文**，**独立卡片**（页眉下） |
| 3 | 入口 **仅 report**；**新页**打开，可切换 **历史每个 stage** |
| 4 | **硬塞一页 A4**（紧凑字号 + 打印前缩放 fit） |

---

## 7. 相关

- [[AI-PRD-练习计时细分内容-260727]] — session 表定义
- [[AI-PLAN-report-session-detail-260730]] — report 日级 session 展示
- report stage chart：`GET /api/practices/stage/{date}`（仅矩阵，无 session）

---

## 8. 执行记录

| 时间 | 事件 |
|---|---|
| 2026-07-30 | 术语对齐 + plan 起草；分支 `feat/stage-session-print-report` |
| 2026-07-30 | dad 拍板 A/全文卡片/report 新页历史/单页；落地 API + stage-print.html + report 入口 |
