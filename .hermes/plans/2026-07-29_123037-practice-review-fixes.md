# Plan: Practice 修复（Phase 0–5 ＋ 未来扩展）

> **For Hermes / dad:** 一次性修完 PR #190-#196 引入的 5 个真实回归与 4 个一致性缺口，并把未来小程序/config 历史扩展的架构落地。
>
> **范围:** dizical 后端 + Web practice。本次不动 dizical-minip 任何代码，但保持发布版兼容。
>
> **执行者:** 后续 subagent（plan 评审通过后用 subagent-driven-development 派发）。
>
> **YAGNI:** 不引入 AbstractBackend 基类全局改写、不引 stored procedure、不换前端框架、不加 API gateway。加固以“最小修改 + 一致性保护”落地。

---

## 0. 已核实事实（不靠印象）

| 编号 | 事实 | 证据 |
|---|---|---|
| F1 | Web 快速补录把 tempo_note/tempo_bpm/content 放在 `body.session_detail`，后端只读顶层 | `src/kid_app/templates/practice.html:1980-1983` vs `src/kid_app/app.py:1203-1208` |
| F2 | `app.py:1225-1226` 与 `1248-1250` 都在 `save_practice_session_and_daily_summary`（内部已 append behavior_log）后再次 `append_behavior_log` | `app.py:1225-1226,1248-1250` vs `database.py:1383-1390` / `database_mysql.py:963-981` |
| F3 | MySQL 缺 `update_practice_session` 与 `delete_practice_session` | `database_mysql.py` 全文无定义；`app.py:1019,1040` 直接调 |
| F4 | Web submit 缺 `practice_at` | `practice.html:1876-1889` body |
| F5 | `selectArchivedItem` 缺 V4 状态机 5 个调用（访问已删 DOM） | `practice.html:1415-1444` |
| F6 | `renderTodayRecords` 把 name/content 直接拼进 `innerHTML` | `practice.html:2186,2194-2197` |
| F7 | UTC vs CST `isToday` 比较 bug | `practice.html:2135` |
| F8 | MySQL 运行时 DDL `id INT`，`schema_mysql.sql` 写 `id BIGINT` | `database_mysql.py:771` vs `schema_mysql.sql:128` |
| F9 | `behavior_log` 跨端语义不一致：SQLite 事务内 `INSERT INTO …` 走日志表 + JSON 追加，MySQL 用 `JSON_ARRAY() \|\| %s` 拼接 | `database.py:1383-1390` vs `database_mysql.py:538-547,963-981` |
| F10 | 小程序 POST `/config/api/records` 用顶层 `tempo_note/tempo_bpm/content/content_source`（兼容） | `dizical-minip/src/utils/api.ts:308-309`、 `practice.vue:901-904` |
| F11 | `tests/test_practice_sessions.py` 仅覆盖 SQLite；MySQL session CRUD 全无测试 | 已 grep 确认 |

---

## 1. 目标 / 非目标

### Goals

- G1 修 5 个真实回归（F1/F2/F3/F4/F5）
- G2 修 2 个一致性缺口（F6/F7）
- G3 加固：MySQL↔SQLite session CRUD 对等 + `behavior_log` 跨端原子追加 + `AbstractBackend` 防再遗漏
- G4 输入校验统一改 Pydantic 减少 `body.get()` 类型 bug
- G5 文档/API-CHANGELOG/双 vault 同步
- G6 本次不破坏 dizical-minip 发布版

### Non-Goals

- 不做 config UI 历史编辑 UI（仅设计架构 + 留接口）
- 不做小程序新功能或字段升级
- 不动 `daily_practices.items` JSON 数据结构
- 不引入新依赖（沿用 FastAPI + Pydantic v2 + 原生 JS）
- 不加 AbstractBackend 抽象基类以外的“大重构”

---

## 2. 数据不变量（commit-or-rollback 必查）

```
∀ date, ∀ item_id:
  daily_practices.total_minutes = SUM(practice_sessions.duration_minutes WHERE practice_date=date AND item_id=item_id) + legacy_offset
  # legacy_offset = daily.items[item].minutes - sessions_sum (旧数据无 session, 一次迁移后归 0)
  # 迁移后 invariant: legacy_offset = 0
  # (本次不强制重写历史 daily, 容忍 legacy_offset 存留, 但新建数据必须满足 sessions_sum == daily.items[item].minutes)

∀ POST /api/log with session_detail:
  behavior_log[].length after commit == 1 (而不是 2)  # F2 修复目标
  practice_sessions.started_at == body.practice_at (CST ISO)  # F4 修复目标
  practice_audit_log 增 1 条, channel=internal, method=save_session  # 已实现, 不动

∀ PUT /api/practice-sessions/{id}:
  practice_items.last_tempo_note/bpm 同步更新 (与 save 行为一致)
  daily.items[item_id].minutes 增量为 (new_duration - old_duration)
  daily.items[item_id].minutes >= 0  (clamp, 已实现 database.py:1251)

∀ DELETE /api/practice-sessions/{id}:
  daily.items[item_id].minutes 减 deleted.duration_minutes
  若减后 == 0, 该 item 行从 items 移除
  total_minutes 同步更新
```

---

## 3. API 合同（最终态）

### POST /api/log  （web 端，dizical-minip 不调用）

请求 schema（Pydantic 校验，错误返 422）：
```json
{
  "date": "YYYY-MM-DD",
  "item": "string",
  "item_id": "int",
  "minutes": "int>0",
  "is_extra": "bool=false",
  "log": "string?",
  "practice_at": "string?  CST ISO 'YYYY-MM-DD HH:MM:SS[.fff]'",
  "behavior_log": "[{enter_time,item,minutes}]?  deprecated, 仅兼容旧前端",

  "tempo_note": "♪|♩|♬ ?",       // 三个全在 → session 路径
  "tempo_bpm": "40-150 ?",
  "content": "string 1..200 ?",
  "content_source": "manual|legacy|backfill ?=manual",

  "session_detail": "{ tempo_note, tempo_bpm, content, content_source }?  // 嵌套 alias, 接受但 merge 到顶层
}
```

响应：
```json
{ "ok": true, "total": 49, "session": { id, practice_date, item_id, item_name, duration_minutes, tempo_note, tempo_bpm, content, content_source, is_extra, started_at, created_at } }
```

### POST /config/api/records  （dizical-minip 当前调用，不动）

`api_save_record` 在 `src/kid_app/routes/config.py:550-612`。本次为它加和 `/api/log` 一致的 Pydantic 校验，但**不改变字段**，不破坏 minip。

### GET /api/practice-sessions/{date}  （minip 7-27 已用，本次保持）

### GET /api/practice-sessions/latest  （minip 7-27 已用，本次保持）

### PUT /api/practice-sessions/{id}  （web 7-28 已用，本次 MySQL 补齐 + 校验统一）

### DELETE /api/practice-sessions/{id}  （web 7-28 已用，本次 MySQL 补齐）

### 未来：GET /api/practice-sessions/range?from=YYYY-MM-DD&to=YYYY-MM-DD  （config 历史页用，本次只写 stub doc，不实现）

---

## 4. 实施顺序（每段 2-5 分钟任务；先 RED 再 GREEN 再真实 HTTP/DB 验证）

### Phase 0 — 契约与架构骨架

**Task 0.1** 新增 `src/kid_app/schemas.py`，写 `PracticeLogRequest` Pydantic model（包含顶层 4 字段 + 嵌套 `session_detail` merge）
- RED: `pytest tests/test_schemas_practice_log.py -q` 期望 Pydantic 422（空 body）
- GREEN: 实现 Pydantic，含 `session_detail` 字段 + validator 合并
- Verify: `pytest tests/test_schemas_practice_log.py -q` 4 case PASS（顶层 / 嵌套 / 缺 content / 空 body）

**Task 0.2** `src/database.py` 新增 `class BaseBackend(ABC)`，定义抽象方法 `_create_practice_session / _update_practice_session / _delete_practice_session / _save_session_and_daily_summary`，让 SQLite/MySQL 都显式继承
- RED: `pytest tests/test_base_backend_contract.py -q` 期望继承类实现全部抽象方法
- GREEN: SQLite 已有方法加 `@override`；MySQL 同样继承
- Verify: 2 PASS

**Task 0.3** `src/database_mysql.py` MySQL DDL 改 `BIGINT` 与 `schema_mysql.sql:128` 对齐；同时统一日期字段类型为 `DATE NOT NULL`（`schema_mysql.sql:131` 已正确）
- RED: `DESCRIBE practice_sessions` 后断言 `id` 字段类型为 `bigint`
- GREEN: 改 DDL；保持 `idx_practice_sessions_date` SKIP 注释（业务按日期扫但 MySQL 5.7 限制）
- Verify: `mcp cloudbase` 拉表结构确认

**Task 0.4** `src/database_mysql.py` 重写 `append_behavior_log` 使用 `JSON_ARRAY_APPEND(COALESCE(behavior_log, JSON_ARRAY()), '$', CAST(%s AS JSON))`
- RED: 测写入后 JSON 数组长度 = 1（不是覆盖）
- GREEN: 重写
- Verify: `pytest tests/test_behavior_log_mysql.py`（subprocess 隔离）

### Phase 1 — 阻塞级（MySQL 不崩 + 双写去重）

**Task 1.1** `src/database_mysql.py` 实现 `update_practice_session` 与 `delete_practice_session`
- RED: `pytest tests/test_update_delete_session_mysql.py`（subprocess 隔离）期望 `AttributeError`（缺方法）
- GREEN: 从 SQLite 移植，整事务 + 重算 daily + 写 audit
- Verify: pytest 6 case PASS（基本更新 / 改 duration 触发 daily 重算 / delete 重算 / 删最后一条 / 删中间 / 部分更新）

**Task 1.2** `src/kid_app/app.py:1203-1257` 把 `behavior_entries` 处理改为：仅 `not has_session_detail` 时 `append_behavior_log`（让 session 路径只写一次）
- RED: 测 POST /api/log 带 session 4 字段后，behavior_log 数组长度 == 1
- GREEN: 加 `if behavior_entries and not has_session_detail:` 条件
- Verify: 真实 HTTP POST + sqlite3 WAL checkpoint + JSON 数组长度

**Task 1.3** `src/kid_app/routes/config.py:550-612` 的 `api_save_record` 也加同样的 dedup
- RED: 同上，minip 路径测 1 条
- GREEN: 同样条件
- Verify: 真实 HTTP POST（minip 模拟）

**Task 1.4** `src/kid_app/app.py:1182-1279` 改用 Pydantic `PracticeLogRequest` 校验 body
- RED: 缺 `date` 返 422（不是 500）
- GREEN: 用 Pydantic；`practice_detail` validator merge 顶层
- Verify: pytest + 真实 curl

### Phase 2 — 数据正确性（web 端修复）

**Task 2.1** `src/kid_app/templates/practice.html:1863-1895` `submitPractice` body 加 `practice_at: nowCstLocal()`；`addExtraMins` 同样
- RED: pytest jsdom 模拟 + 抓 fetch body 断言含 `practice_at`
- GREEN: 改两处 fetch
- Verify: 真实浏览器手动打卡 → sqlite3 查 `started_at` 非空

**Task 2.2** `src/kid_app/templates/practice.html:1415-1444` `selectArchivedItem` 复用 `selectItem` 状态机（fillSessionDefaults / renderBpmPresets / renderContentTags / updateStartBtnState / updateExtraBtnState / updateDashboard / compact 收拢 / 移除已删 DOM 操作）
- RED: 单元测（test harness 加 jsdom）：选 archived 后 `bpmPresets` 内有 1 个 .bpm-preset
- GREEN: 删 `selectArchivedItem` 函数本体，把 `onclick` 直接走 `selectItem(name, id, btn, event)`
- Verify: 浏览器手动选 archived 科目，dashboard 显示默认值 + BPM 预设出现

**Task 2.3** `practice.html:2135` 改 `isToday` 用 CST 本地日期
- RED: jsdom mock `new Date('2026-07-29T00:30:00+08:00')` 时 isToday 应为 true
- GREEN: 用与 `nowCstLocal` 同源的 `todayDate`（服务端 Jinja 注入）或前端用 `getFullYear/getMonth/getDate` 拼 CST
- Verify: pytest 4 边界（00:00 / 04:00 / 16:00 / 23:59 CST）

**Task 2.4** `practice.html:2186,2194-2197` 改 `innerHTML` 为 `textContent`/`createElement`（消 XSS 风险）
- RED: jsdom 测 `<img onerror=...>` content 不会执行
- GREEN: 用 `document.createElement('span')` + `textContent =`，保留速度/分钟加 `<span class="...">`
- Verify: pytest + 浏览器视觉对比

### Phase 3 — 架构加固（一致性与可观察性）

**Task 3.1** `src/database.py` 与 `src/database_mysql.py` 把 save 路径中 behavior_log 写入逻辑挪到事务外
- 决策：保留事务内写（防止回滚时 audit 丢失），加注释说明语义
- RED: 故意让事务内 SQL 失败，断言 audit 也未写（要么全成功要么全不写）
- GREEN: 不改实现（已正确），只加注释
- Verify: pytest 1 case（手动 raise）

**Task 3.2** 双后端 race condition：API 加 5s 防重窗口（同 item_id+minutes+enter_time 5s 内拒）
- RED: 同一分钟连发 2 次，第二条返 409 或 200 with dedup_message
- GREEN: 路由层加 dedup 字典（`{item_id, minutes, second_window}`），TTL 5s
- Verify: pytest + 真实 HTTP

**Task 3.3** `src/kid_app/app.py` / `src/kid_app/routes/config.py` 增加 `start_time` 计时埋点（loguru 或 print）
- 不上 Prometheus，先 print 打 request_id + ms 耗时
- RED: N/A（观测类）
- GREEN: 加 4 个埋点
- Verify: 看日志

### Phase 4 — 文档与跨端同步

**Task 4.1** `API-CHANGELOG.md` 加本次条目（🟡 部分兼容）
- 内容：内容必填（已有）+ 双写去重 + MySQL 补齐 + practice_at 推荐 + session_detail alias 兼容 + Pydantic 422 错误
- 类型：🟡 部分兼容（小程序不需改）

**Task 4.2** `PRDs/AI-PRD-练习修复-260729.md` 写问题描述 + 修复方向 + 验收标准（独立文档，方便 dad 审）

**Task 4.3** `docs/practice-session-detail.md` 写技术 spec：AbstractBackend 模式、Pydantic 校验、跨后端 audit 不变量

**Task 4.4** Obsidian 镜像双写 + `md5 -q` 校验

**Task 4.5** `STATUS.md` + `vibe-coding-log.md` 更新（gitignored 文档，只本机）

### Phase 5 — 未来扩展（本次仅设计，不实施）

- **5.1** `config-practice-log.html` 顶部新增 tab「历史记录」，复用 editSessionModal
- **5.2** GET `/api/practice-sessions/range` 端点设计（不实现，只写 schema）
- **5.3** 数据库层 `move_session_to_item(session_id, new_item_id, new_date)` 设计（事务：删旧 + 写新 + 重算新旧两天 daily）
- **5.4** dizical-minip 未来改造：minip 端 sessions[] UI 渲染 + 编辑弹窗（本次不实施，只在 `PRDs/AI-PRD-练习修复-260729.md` 留接口）

---

## 5. 测试矩阵

| 层 | 文件 | 覆盖 |
|---|---|---|
| 单元 | `tests/test_practice_sessions.py` (扩) | SQLite session CRUD 加 content 空校验 / 负 minutes / 字段更新 delta |
| 单元 | `tests/test_update_delete_session_mysql.py` (新) | subprocess 隔离 MySQL update/delete（5 case） |
| 单元 | `tests/test_behavior_log_mysql.py` (新) | subprocess 隔离 MySQL append 原子性（3 case） |
| 单元 | `tests/test_schemas_practice_log.py` (新) | Pydantic 校验（4 case） |
| 单元 | `tests/test_base_backend_contract.py` (新) | ABC 强制实现（2 case） |
| 单元 | `tests/test_api_log_extra_detail.py` (新) | 嵌套 `session_detail` merge + dedup（3 case） |
| 集成 | `tests/test_dual_backend_parity.py` (新) | SQLite vs MySQL 同一组请求 diff（参考 achievements_mysql 模式） |
| 数据不变式 | `tests/test_audit_invariants.py` (新) | sessions_sum == daily.items[item].minutes + behavior_log.length == 1 |
| 时区 | `tests/test_today_window.py` (新) | mock datetime 跨 CST 00:00 / 04:00 / 16:00 / 23:59 |
| XSS | `tests/test_html_injection.py` (新) | content 含 `<img onerror>` → 渲染不执行 |
| 防重 | `tests/test_dedup_window.py` (新) | 同 item+minutes 5s 内拒 |

总计：约 35 case。

---

## 6. 验证策略（每 Phase 跑完必走）

1. **pytest target**: `python3 -m pytest tests/test_practice_sessions.py tests/test_schemas_practice_log.py -q` 期望 12+N PASS
2. **pytest full**: `python3 -m pytest -q` 期望净回归 = 0（pre-existing fails 已知 13 个，PR #198 不会触碰）
3. **真实 HTTP**: 重启服务后 curl：
   - `curl -X POST http://localhost:8765/api/log -H 'content-type: application/json' -d '{...}'`
   - `curl http://localhost:8765/api/practice-sessions/2026-07-29`
   - 断言 response.status_code == 200 + JSON 字段齐
4. **DB 验证**: `sqlite3 data/dizi.db "PRAGMA wal_checkpoint(FULL); SELECT * FROM practice_sessions WHERE practice_date='2026-07-29';"` 确认 started_at 非空 + behavior_log JSON 长度正确
5. **浏览器视觉**: 选 archived 科目看 dashboard 默认值 / 选科目看 BPM 预设出现 / 选科目看 dci-assign 显示老师要求
6. **CloudRun parity** (如需)：mcp `queryCloudRun getDeployLog` 确认新代码已 deploy + `pymysql` 直连云端跑 1 次 session CRUD

---

## 7. 风险与反向论证

| 编号 | 风险 / 反例 | 缓解 |
|---|---|---|
| R1 | 旧前端发 `session_detail` 嵌套，新 Pydantic validator 漏 merge 兼容 | Task 0.1 测 4 case 含嵌套兼容；Task 1.4 真实 curl |
| R2 | MySQL DDL 改 `BIGINT` 触发 column 冲突 | 7-28 已是 `BIGINT`，运行时 DDL 跟 schema_mysql.sql 对齐 |
| R3 | `behavior_log` dedup 误删有效 entry | dedup 条件是 `not has_session_detail`，旧前端仍兼容；新前端不再发 |
| R4 | Pydantic v2 升级报错 | 检查 `pydantic_settings` `class Config` 弃用警告（已 1 warning）—— 改用 `model_config = ConfigDict(...)` |
| R5 | 5s dedup 误伤网络慢用户 | 仅同 item+minutes+second 重复才拒，跨科目或不同分钟不拒 |
| R6 | AbstractBackend 抽象基类引入回归 | 只覆盖 4 个 session 方法，不动其他方法；现有 268 passed 不应掉 |
| R7 | MySQL `JSON_ARRAY_APPEND` 写 NULL `behavior_log` | `COALESCE(behavior_log, JSON_ARRAY())` 已加；测试覆盖 |
| R8 | CST 时区判断用服务端注入 `todayDate` 与浏览器本地 漂移 | 用服务端 `today_date` Jinja 变量，前后端共用源 |
| R9 | 小程序 audit-mock 端点未通过新校验 | audit-mock 走 `/api/minip/audit-mock`（GET），与 `/api/log` 无关，零影响 |
| R10 | config-records.html 仍发旧字段 | 7-28 改过 content 必填（已 merge），其它字段不动 |

---

## 8. PR 拆分

| PR | 内容 | 文件 | 风险 |
|---|---|---|---|
| PR-A | Phase 0 契约 + 抽象基类 + Pydantic | schemas.py, database.py, database_mysql.py | 中（影响所有 save） |
| PR-B | Phase 1 MySQL CRUD + behavior_log dedup | database_mysql.py, app.py, config.py | 高（生产阻塞） |
| PR-C | Phase 2 web 修复（practice_at + archived + isToday + XSS） | practice.html | 低 |
| PR-D | Phase 3 防重 + 埋点 + 文档同步 | app.py, API-CHANGELOG, PRDs, Obsidian | 低 |

PR 顺序：A → B（必须先 B 修阻塞） → C → D，可并入 1 个 PR 但拆 4 commit。

---

## 9. 收尾 checklist

- [ ] pytest 全过
- [ ] curl 真实 HTTP 200
- [ ] sqlite3 + pymysql 双后端验证 started_at / behavior_log 长度
- [ ] 浏览器视觉 4 项 OK
- [ ] API-CHANGELOG + PRDs/AI-PRD-练习修复-260729.md + Obsidian 镜像三件同步
- [ ] md5 校验两仓一致
- [ ] STATUS.md / vibe-coding-log.md 更新（gitignored）
- [ ] backup `data/dizi.db` (无 destructive 写但仍按 dad 红线备份)

---

## 10. 拍板等待

请 dad 回复：
1. PR 顺序 A→B→C→D 合并还是 4 个独立 PR？
2. Phase 5 未来扩展是否单独出一份 `AI-PRD-config历史管理-260729.md`？
3. go 之后我开始 dispatch subagent 派发实施。
