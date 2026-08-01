# MOA 跨模型评审: Practice 修复计划

> 基于代码审查 (app.py:1184-1279 + database.py:1136-1419 + database_mysql.py:760-1004 + practice.html:1415-2263) 的证据驱动评审.

---

## 1. 规范请求-响应合同 (Canonical API Contract)

**POST /api/log** | 两路径共存, 签名统一:

| 字段 | 必填 | 新 session 路径 | 旧兼容路径 |
|------|------|----------------|-----------|
| date, item, item_id, minutes | ✅ | ✓ | ✓ |
| tempo_note, tempo_bpm, content | ① | 有 → session 写入 | 无 → save_daily_practice 兼容 |
| practice_at | ② | 必传 CST ISO, 不传则 started_at=NULL | 传则新建行写入, 已有行不动 |
| behavior_log | ③ | 前端不再发(session 事务已写), 发的则降级 | 兼容 |

> ① `all(k in body for k in ("tempo_note","tempo_bpm","content"))` 决定路径路由
> ② practice.html:1877 **未传 practice_at** — 证据: submitPractice body 不含该字段
> ③ save_practice_session_and_daily_summary 事务内 (database.py:1367-1390) 已 append behavior_log + practice_audit_log, 外部 (app.py:1248-1250) 又追加 → **double-write bug**

**响应统一**: `{ok, total, session?}` — session 对象含 id/tempo_note/tempo_bpm/content/duration_minutes

---

## 2. SQLite/MySQL 对等 CRUD 与审计不变量

### 缺失 (Blocking)

| 方法 | SQLite (database.py) | MySQL (database_mysql.py) |
|------|---------------------|---------------------------|
| delete_practice_session | ✅ line 1136 | ❌ **缺失** |
| update_practice_session | ✅ line 1195 | ❌ **缺失** |
| _ALLOWED_TEMPO_NOTES / _BPM_MIN/_MAX | ✅ | ❌ 硬编码 |

**影响**: 在 MySQL 环境 (dizical-minip + CloudRun), app.py:1019 `db.delete_practice_session()` → **AttributeError 500**. 生产级阻塞.

### 审计不变量 (两地一致, 已验证):
- save_practice_session_and_daily_summary: INSERT session → 更新 daily items → append behavior_log → INSERT practice_audit_log → 更新 practice_items 冗余列 — **整事务**
- behavior_log 是 session 的 audit 副本, 不是事实源
- practice_audit_log 不可绕过的写操作追踪

---

## 3. 实施顺序 (RED-GREEN-HTTP/DB 验证)

```
Phase 1 — 阻塞级 (MySQL 不崩溃)
  RED:   测试预计 AttributeError (NoMethodError)
  GREEN: 给 MySQLBackend 加 delete_practice_session + update_practice_session
  HTTP:   用 curl PUT/DELETE /api/practice-sessions/{id} 验证 200
  DB:     MySQL 行确认 deleted / updated

Phase 2 — 数据正确 (不丢/不重)
  RED:   behavior_log 写入后 count=1 (当前 double-write)
  GREEN: has_session_detail 时跳过外部 append_behavior_log (app.py:1248-1250 加条件)
  HTTP:   POST /api/log 带 tempo_note/tempo_bpm/content → GET /api/practices/{date} 校验 sessions[].behavior_log 不重复
  DB:     behavior_log JSON 数组长度 = session 数 (不是 2x)

Phase 3 — practice_at 补全
  RED:   practice.html submitPractice body 缺 practice_at → session.started_at = NULL
  GREEN: submitPractice() 加 practice_at: nowCstLocal() (与 config-practice-log.html:898 对齐)
  HTTP:   打卡后 GET /api/practice-sessions/{id} 确认 started_at 非空

Phase 4 — 归档状态机统一
  RED:   archived 科目选后 fillSessionDefaults/renderBpmPresets/renderContentTags 不执行
  GREEN: selectArchivedItem 补上缺失的 5 个调用 (practice.html:1445+) 
  VISUAL: 真机确认归档科目速度默认值与正常科目一致
```

---

## 4. 未来小程序改动清单 (本次不实施, 🟡 部分兼容)

| 项 | 原因 | 可暂不改 |
|----|------|---------|
| mp POST /config/api/records 传 session 字段 | 腾读取 minip #24 | 后端现有 has_session_detail 路由兼容 |
| mp 读 sessions[] 渲染 | 老渲染仍 work | 但 mp 用户看不到速度/内容细节 |
| mp 编辑/删除 session | 后端新 API 已存在 | mp 不做 UI 入口即可 |
| mp behavior_log 不再发 | 后端接收并 append, 多一条 | 无害, 只是冗余 |
| practice_at 传 CST | 不传则 started_at=NULL | 回退用 created_at 显示 |

---

## 5. 未来 config 历史 CRUD 架构

```
config-practice-log 扩展为历史管理页:

┌─ 今日补录 (当前) ──────────────────────────┐
│  日期选择器 + 科目/时间/分钟/tempo/content   │
└────────────────────────────────────────────┘
┌─ 历史记录 (新增) ───────────────────────────┐
│  日期选择 → 加载当日 sessions[]             │
│  每行: 科目 | tempo=80 | 内容 | 5min | ✎ ✕  │
│  编辑弹窗: 复用 editSessionModal 逻辑        │
│  删除弹窗: "删除后不可恢复" 二次确认         │
└────────────────────────────────────────────┘

API 复用: GET /api/practice-sessions/{date}
          PUT /api/practice-sessions/{id}
          DELETE /api/practice-sessions/{id}

事实表 = practice_sessions,  汇总 = daily_practices.items (自动重算)
```

---

## 6. 边界 + 反向论证 (5+)

1. **双后端 race condition**: is_extra 路径无 save_daily_practice (app.py:1230-1237) — 旧路径不防重放, 快速点两次 → 2 条 session. 应在 app.py 加 minutes 去重窗口 (5s 内同 item_id+minutes 拒).
2. **负分钟漏洞**: update_practice_session duration_minutes 从 5→3 时, delta = -2, daily.items[].minutes 会被减到负数 → 封 max(0, ...) 已在 database.py:1251.
3. **content 转义**: renderTodayRecords (practice.html:2188-2198) 直接 innerHTML 拼接 name/content. 虽数据来自后端 (本系统), 但 content 含 `&<>` 会破渲染. 应 `textContent` or `.createTextNode()`.
4. **归档 sql injection**: toggleArchived line 1175 `it.name.replace(/'/g, "\\'")` 防单引号但不防 `</script>` 等. 同上 innerHTML 风险.
5. **session 非今日可编辑**: renderTodayRecords line 2135 用 `isToday` 控制编辑按钮. 但后端 API 对任何日期都允许 PUT/DELETE. 前端 gate 不够 — 历史 session 应需要二次确认.
6. **事务超时**: MySQLBackend 无 BEGIN/COMMIT (auto-commit pool). save_practice_session_and_daily_summary 用 with conn: 但异常时外层的 conn.commit() 在事务外部. 检查 MySQL 版本是否真正原子.
7. **practice_at vs enter_time**: submitPractice 缺 practice_at 只传 behavior_log.enter_time. 但 save_practice_session_and_daily_summary 写 started_at=practice_at=NULL. 此时 enter_time 有值但 started_at 无值 → 时间戳分裂.

---

## 7. 应接受 / 拒绝的过度设计

### ✅ 接受
- **统一 AbstractBackend 基类** — 声明 delete/update_session 抽象方法, 防止今后再遗漏 MySQL 实现 (当前语法不报错, 运行时炸)
- **POST /api/log body 验证层** — 用 Pydantic model 代替手写 `body.get()`, 减少类型转换 bug
- **session 创建时间戳去重** — 5s 窗口防双击

### ❌ 拒绝
- **behavior_log 彻底移除** — 小程序和旧数据依赖 behavior_log. 降级为 "有 session 不再写" 即可
- **MySQL session CRUD 重构为 stored procedure** — 额外运维成本, Python 事务足够
- **前端迁移到 Vue/React** — innerHTML 问题可用 `textContent` 解决, 新框架不必要
- **统一 API gateway** — 当前双路由够用, 加层增加延迟

---

## 8. Ship / Hold 判定

```
Phase 1 (MySQL CRUD 补齐)     → SHIP NOW — 生产阻塞, 5 行代码
Phase 2 (behavior_log dedup) → SHIP NOW — 数据正确性, 3 行代码
Phase 3 (practice_at 补全)   → SHIP NOW — 1 行代码
Phase 4 (归档状态机统一)      → SHIP NOW — 5 行调用, 无副作用

综合: 阻塞级 BUG (Phase 1) 先修, 剩下的顺序在本 sprint 内 ship.
      Phase 5 (历史 config CRUD) → 下一迭代.
```

*证据索引: app.py L1215-1227 (is_extra double-write), app.py L1248-1250 (normal double-write), database.py L1383-1390 (internal behavior_log write), database_mysql.py L760-1004 (无 delete/update), practice.html L1415-1444 (selectArchivedItem 缺失调用), practice.html L1876-1893 (缺 practice_at), practice.html L2130-2202 (innerHTML 拼接), database.py L1251 (负分钟 clamp)*
