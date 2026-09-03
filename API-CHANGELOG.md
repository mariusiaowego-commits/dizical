# dinghy 微信跳转录入 URL Link — API 变更

**日期**: 2026-08-07
**分支**: feat/miniprogram-url-link
**类型**: 🟡 部分兼容（新增端点，现有逻辑零改动）

## 变更

### POST `/api/minip/url-link`（新）

生成小程序 URL Link（微信内点击直达小程序页面并带参数）。dinghy bot 调用，实现"微信点链接 → 呦助预填录入"（配合 dizical-minip PR #33 前端预填）。

- body: `{path, query}`；path 仅允许 `/pages/practice/practice`（白名单）
- 需要环境变量：`WX_APPID` / `WX_SECRET`（CloudBase 配置，不进 git）
- 可选鉴权：`DINGHY_URL_LINK_KEY` 设置后需带 header `X-Dinghy-Key` 匹配，否则 403
- 返回 `{ok: true, url_link}`；30 天临时链接（is_expire=1, expire_type=1）
- access_token 进程内缓存（7000s），避免每次请求拉 token
- minip 前端无需改动

---

# Backend 切换 — API 变更

**日期**: 2026-08-29 (待 PR)
**分支**: feat/config-set-password
**类型**: 🟡 部分兼容（新增端点, 现有 API 签名基本不变, dizical-minip 无改动）

## 变更

### 1.1 POST `/config/api/users/{user_id}/set-password` — 设置指定密码 (dad 后台)

- 背景: dad 想"看到当前密码"以便微信/电话告知家人, 但密码是 scrypt 单向哈希, 原明文无法回看. Sprint 26082901 dad 拍板方案①: dad 自己设一个新密码 (他知道的), 当场返回明文 1 次
- Body: `{pin, new_password}`; 守门 `_check_dad_or_401` (PIN 或 dad role session, 同 reset-password)
- 行为: 设新 scrypt hash; 校验 >= MIN_PASSWORD_LEN (6); **不强制 must_change_password** (dad 设的就是用户该用的密码); 不 bump session
- 返明文 `new_password` 1 次 (设完即忘, 不存明文)
- **影响**: 新增端点, dizical-minip 无调用, 无需改动. 同 sprint 前端 config-users.html 加 [设置密码] 按钮 + modal

### 1.2 PIN 残留 URL 修复 — POST `/config/users/verify` + pin_ok cookie (dad 报)

- **问题**: 之前用 PIN 进 `/config/users` 时 PIN 留 URL (`?pin=0905`), 历史记录/共享链接泄露
- **新增** `POST /config/users/verify`: body `{pin}` → 验 PIN, 通过种 `dizical_pin_ok` cookie (HttpOnly 签名, 2h), 返 `{ok:True}`
  - 安全: Origin/Referer 校验 (CSRF) + IP 限流 5 次/5min (防 4 位 PIN 爆破)
  - cookie 存**已验证签名** (非 PIN 明文), 窃 cookie 只能短时访问本网关, 不能解出 PIN
- **GET** `/config/users?pin=` (老链接/curl) → 校验通过后 **303 + 种 cookie + 清 URL** 重定向
- **升级** `_check_dad_or_401` 第三轨: dad session OR body/header PIN OR pin_ok cookie
- **兼容**: `/config/api/invites/list` 从 query pin 改三轨守门 (老 `?pin=` 仍兼容); `/api/verify-pin` (mp) + `dizical_session` + minip `X-Dad-Pin` 均不动
- **影响**: 前端 config-users.html submitPin 改 POST + invites/list 去 URL pin. dizical-minip 不调这些 HTML/API 端点, **无需改动**

---

# Backend 切换 — API 变更

**日期**: 2026-08-25 (数据修复已上线, 代码待 PR)
**分支**: feat/report-stage-computation-check (PR #289)
**类型**: ✅ 完全兼容（内部 weekly_assignments 写逻辑修复, API 端点签名全不变, dizical-minip 无需改动）

## 变更

### 1. MySQL weekly_assignments 写入修复 (内部逻辑, 无 API 签名变化)

- 修复云端 MySQL `save_weekly_assignment` 不再回填 `stage_order` / 产生重复行
- 原因: MySQL 表缺 `UNIQUE(lesson_date)` 索引 + UPSERT 排除 stage_order → 08-16 课作业 stage_order=NULL → stage 列表停在第 18
- 变更:
  1. `save_weekly_assignment` 每次保存重算 stage_start/end/order (对齐 SQLite), `ON DUPLICATE KEY UPDATE` 加回 stage_order
  2. `schema_mysql.sql` 加 `UNIQUE KEY idx_assignments_lesson_unique (lesson_date)`
- **数据已修**: 合并重复行 + 回填 stage_order=19，云端 stage 下拉现显示 Stage 19
- **影响**: 后端写逻辑优化, API 无变化。minip 盲盒打卡受 stage_order 影响 (此前 MAX(stage_order) 停 18 → 打卡范围错), 数据修复后恢复. 无需代码改动

---

# Backend 切换 — API 变更

**日期**: 2026-08-18 (CloudRun DeployId 100 已上线)
**分支**: feat/config-refactor-260817 (PR #283) + feat/mobile-polish-260818 (PR #284)
**类型**: ✅ 完全兼容（HTML 入口弃用, API 端点全保留, dizical-minip 无需改动）

## 变更

### 1. GET `/config/records` — HTML 入口弃用 (302 redirect)

- 之前: 渲染 config-records.html (练习记录管理台, 4 tab: calendar/add/edit/stats)
- 现在: `302 → /config/practice-log?tab=stats` (UI 并入 practice-log 的「练习统计」tab)
- 后端 `/config/api/records/*` 端点**全保留**, 签名未变 (供 dizical-minip / 旧客户端 / 旧 handoff 继续调用)
- app.py middleware PUBLIC 白名单加 `/config/records` (1 行) — deprecated redirect 跳过 auth
- **影响**: minip 走 `/config/api/records` 路由, 不受 HTML 入口弃用影响, **无需改动**
- 验证: curl /config/records → 302 → /config/practice-log?tab=stats ✓ (3 个 pytest 保护: test_config_records_redirect)

### 2. dizical-test-env 测试环境 (非 API, 附注)

- 新 skill `dizical-test-env` + setup-test-env.sh 一键脚本: worktree 验前端直接复制主 checkout db + 建 dad/test_root 密码 000000 + 起 8766
- dad 不用记命令, 见 dizical-development skill §6

---

# Backend 切换 — API 变更

**日期**: 2026-08-09
**分支**: feat/s3-assignment-history3 (PR 待建)
**类型**: 🟡 部分兼容（新增只读端点, minip 不调用无需改）

## 变更

### 1. GET `/config/api/assignments/by-item`（新）

查询某科目最近 N 次老师要求（默认 3 次）。参数: `item_id` 或 `item`（科目名）, `limit`。
返回 `{history: [{lesson_date, metronome, requirements}]}` 倒序。
按 item_id 优先, 其次科目名匹配（兼容历史 item_id 为 null 的记录）。
minip 不调用。

---

# Backend 切换 — API 变更

**日期**: 2026-08-09
**分支**: fix/picker-active-only-s1 (PR #244)
**类型**: ✅ 完全兼容（新增校验/格式拦截, minip 无需改动）

## 变更

### 1. POST `/config/api/assignments/upload` — 格式白名单收紧

- 之前: 接受 jpg/jpeg/png/heic/heif (heic 依赖 macOS sips 转换, CloudRun Linux 无 sips 导致 heic 原样存 COS, Chrome 无法预览)
- 现在: 只接受 jpg/jpeg/png; heic/heif 返 400 + 中文提示 (请先转为 jpg 或 png)
- 影响: 业务上 heic 上传本来 Chrome 就看不了, 实际无损失. minip 不调用此端点.

---

# Backend 切换 — API 变更

**日期**: 2026-08-05
**分支**: feat/sprint-09-cloud-cutover
**类型**: 🟡 部分兼容（新增只读/写端点，minip 无需改）

## 变更

### 1. GET `/config/api/backend`（新）

读当前后端模式 + 云端 URL。返回 `{mode: 'cloud'|'local', dizical_url: str}`。
默认 `local`（settings 表无记录时）。minip 不调用。

### 2. PUT `/config/api/backend`（新）

写后端模式。body: `{mode: 'cloud'|'local', dizical_url?: str, pin?: str}`。
- `mode` 非法 → 400
- `dad_pin` 已设置且 pin 不匹配 → 403
- 写 settings 表 `backend_mode` + `dizical_url`（仅 cloud 模式写 URL）
minip 不调用。mac app 的 DIZICAL_URL 切换在 mac 项目（不在本仓）。

---

# Stage 维 Session 明细打印 — API 变更

**日期**: 2026-07-30
**分支**: feat/stage-session-print-report
**类型**: 🟡 部分兼容（新增只读端点，minip 无需改）

## 变更

### 1. GET `/api/practices/stages`（新）

历史 stage 列表，供打印页切换历史阶段。

### 2. GET `/api/practices/stage-detail`（新）

Query: `stage_order` 或 `date`（所属 stage）。  
返回按日→科目→session 的聚合 + assignment 老师要求全文 + summary。  
minip 不调用。

### 3. GET `/report/stage-print`（新 HTML）

A4 单页打印预览；可查历史 stage。

---

# Practice Session Detail — API 变更

**日期**: 2026-07-29
**分支**: fix/practice-bugs-20260729
**类型**: 🔴 不兼容

## 变更

### 1. POST /api/log — content 必填

`content` 字段从可选变为必填 (前端+后端双重校验). 传空字符串 `""` 或缺失返回 400.

---

# Practice V3.1+ — API 变更 (PR-A/B/C/D, 2026-07-29)

**日期**: 2026-07-29
**分支**: fix/practice-pr-a (合并前); PR-A / PR-B / PR-C / PR-D 4 个独立 PR
**类型**: 🟡 部分兼容 (mp 端无需改)

## 变更

### 1. POST /api/log — Pydantic 校验 (PR-B)

替换手写 `body.get()` 类型转换, 用 `PracticeLogRequest` Pydantic model 校验.
校验失败返 422 + details (Pydantic 错误结构).
- 缺 `date` / `item` / `item_id` / `minutes` → 422
- `tempo_bpm` 越界 (40-150) → 422
- `content` 仅空白 → 422 (session 路径下)
- `tempo_note` 非 ♪/♩/♬ → 422

### 2. POST /api/log — `session_detail` 嵌套 alias (PR-B)

Web 快速补录实际把 tempo_note/tempo_bpm/content 嵌套在 `body.session_detail`, 后端 schema 自动合并到顶层. 兼容旧 / 新两种调用方式.

### 3. POST /api/log — `behavior_log` dedup (PR-B)

`save_practice_session_and_daily_summary()` 事务内已 append 1 条 behavior_log.
旧路由在事务后再次 `append_behavior_log` 造成双写. PR-B 在 session 路径下移除外部 append.
- 旧路径 (无 session 字段): 继续 `append_behavior_log` 兼容旧前端
- session 路径: 事务内 1 条, 外部不再写

### 4. POST /api/log — 5s dedup 防重 (PR-D)

同 `(item_id, minutes)` 5s 内重复请求 → 返回首次响应缓存, 不再写 session/daily.
- 进程级 dict, 5s 后自动清理
- 进程重启失效 (无副作用)

### 5. PUT /api/log — MySQL session CRUD 补齐 (PR-B)

`update_practice_session` / `delete_practice_session` 之前仅 SQLite 端实现 (PR #190-#196 漏).
PR-B 移植到 MySQLBackend, 整事务 + 重算 daily + 写 audit + 同步冗余列.
- 7-28 CloudRun PUT/DELETE 必 500 → 修复
- MySQL DDL 字段类型与 `schema_mysql.sql` 对齐 (BIGINT)

### 6. GET /api/practice-sessions/{date} 兼容

字段不变, 但 `practice_sessions.started_at` 之前常为 NULL. PR-C 前端 `submitPractice` / `addExtraMins` body 加 `practice_at: nowCstLocal()` (CST ISO 无 Z), session.started_at 写入新值.

## 数据库

`src/database_base.py` 新增 `BaseBackend(ABC)` 抽象基类, 4 个 session 方法 (create/update/delete/save) 强制所有 backend 实现. 防止 7-28 那种"漏方法导致运行时 500"再发生.

`src/database_mysql.py` 修复 `append_behavior_log` 用 `JSON_ARRAY_APPEND` 原子追加 (旧 `|| %s` 字符串拼接破坏 JSON 结构).

## minip 端

无变化. mp 端 `submitRecord` 已使用顶层 `tempo_note/tempo_bpm/content` 字段, 走 `/config/api/records` 路由, 与本次 `/api/log` 改动无关.

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
