# Practice Session Detail — API 变更

**日期**: 2026-07-29
**分支**: fix/practice-bugs-20260729
**类型**: 🔴 不兼容

## 变更

### 1. POST /api/log — content 必填

`content` 字段从可选变为必填 (前端+后端双重校验). 传空字符串 `""` 或缺失返回 400.

---

**日期**: 2026-07-27
**分支**: feat/practice-session-detail
**类型**: 🟡 部分兼容

## 变更

### 1. POST /api/log — 新增可选字段

```json
{
  "tempo_note": "♪ | ♩",   // 新增, 可选
  "tempo_bpm": 40-150,       // 新增, 可选
  "content": "练习内容"      // 新增, 可选
}
```

有 content 时走 `save_practice_session_and_daily_summary` (创建 session)，否则走旧 `save_daily_practice` (完全兼容)。

### 2. GET /api/practices/{date} — 返回新增 sessions[]

响应新增 `"sessions": [...]` 字段，每条含 `id, item_name, tempo_note, tempo_bpm, content, duration_minutes, started_at`。

### 3. 新增 GET /api/practice-sessions/{date}

返回某日全部 session，可选 `?item_id=` 过滤。

### 4. 新增 GET /api/practice-sessions/latest

返回某 item 最近一次 tempo 信息 (用于前端 Q1=B 默认值填充)。

### 5. 新增 GET /api/assignments/latest

返回某 item 最近 assignment 的 metronome 字段 (Q1=B fallback)。

### 6. 新增 DELETE /api/practice-sessions/{id}

删单条 session + 事务内重算 daily 汇总。

---

# Practice V3.1 UI — content_options 配置

**日期**: 2026-07-28
**分支**: feat/practice-v3.1-ui
**类型**: 🟡 部分兼容（新增字段/端点，旧客户端忽略即可）
**minip**: 无需改（字段可选，未用则默认标签）
**上线**: 待 merge

## 变更

### 1. practice_items.content_options 字段

- SQLite / MySQL 新增 `content_options TEXT`（逗号分隔字符串）
- 迁移: `src/migrate_add_content_options.py`（幂等）
- 空 = 练习页用全局默认标签

### 2. PUT /config/api/practice/items/{item_id}/content-options （新增）

```json
// request
{ "content_options": "第一分句\n第二分句" }  // 或逗号分隔 / string[]

// response
{ "ok": true, "content_options": "第一分句,第二分句", "options": ["第一分句","第二分句"] }
```

校验: 每项 ≤50 字, 最多 20 项, 去重保序。

### 3. GET /api/items / GET /config/api/practice/items

返回的 item 对象新增可选字段 `content_options`（字符串）。

### 4. 前端

- practice 页: 选科目后渲染预置标签；BPM 步进器；卡片合并 2:8
- config/practice: 科目行「内容」按钮编辑预置选项
