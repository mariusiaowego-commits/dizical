# Practice Session Detail — API 变更

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

## minip 影响

| 端点 | 变更 | 影响 |
|------|------|------|
| POST /api/log | 可选新字段 | ✅ 完全兼容 (不传字段 = 旧行为) |
| GET /api/practices/{date} | 新增 sessions[] | ✅ 完全兼容 (minip 忽略新字段) |

**minip 无需同步改动**。
