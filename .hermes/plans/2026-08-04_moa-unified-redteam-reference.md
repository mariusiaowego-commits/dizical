# dizical 云 MySQL 切云 · MOA 统一对抗性 Reference (2026-08-04)

> **作者**：主 agent (coder profile)  
> **来源**：4 份 red-team 报告（3 份 MOA 真多模型 + 1 份主 agent 整合前 subagent 报告，已在 MOA 中交叉验证）  
> **状态**：已交叉验证，未单方面吸收 subagent 结论  
> **范围**：read-only，不动文件 / 不动云

---

## 0. 来源与可信度

| 报告 | 来源 | 类型 | 状态 |
|------|------|------|------|
| 2026-08-04_cloud-mysql-cutover-redteam.md | MOA 真路径（custom:ark → minimax aggregator） | 数据库/分布式 | 真 |
| 2026-08-04_cloud-cutover-sre-redteam-review.md | subagent（同 provider） | SRE/灾备 | 已并入 v2 |
| 2026-08-04_cloud-cutover-sre-redteam-review-v2.md | MOA 真路径 | SRE/灾备 v2 | 真 |
| 2026-08-04_cloud-mysql-primary-multiclient-cutover-review.md | subagent（同 provider） | 全栈 QA | 待用 |
| 2026-08-04_cloud-mysql-cutover-concurrency-research.md | subagent（同 provider） | 并发研究 | 已部分吸收 |

主 agent 抽查确认的 file:line 证据：
- `database.py:636-700` ON CONFLICT 单行 JSON 确认
- `database_mysql.py:384-410` DELETE+逐 item INSERT 确认
- `app.py:405-408` json_extract / json_each SQLite 专有 确认
- DBUtils SteadyDBConnection methods 不含 `.execute()` 确认
- 17 处裸 conn.execute / ? 占位符命中确认

---

## 1. P0 必崩项（不修切云必 500 / 必丢数据）

| # | 描述 | 证据 file:line | 修法 |
|---|------|----------------|------|
| P0-1 | **17 处裸 `conn.execute()` + `?` 占位符** | app.py:199, 356, 363, 384, 405, 426, 546, 799, 824, 833, 2243, 2252, 2367；config.py:1018, 1052, 1071, 1083 | 全部改 `db_adapter.execute()` 或 `conn.cursor().execute()`，占位符改 `%s` |
| P0-2 | **app.py `_calc_top_items` 用 SQLite 专有 `json_extract` + `json_each`** | app.py:405-408 | 改 MySQL `JSON_TABLE` 或抽到 backend 抽象 |
| P0-3 | **`weekly_assignments` 两后端 schema 异构** | SQLite database.py:636-700 ON CONFLICT 单行 JSON vs MySQL database_mysql.py:384-410 DELETE+逐 item INSERT | MySQL 端改 `INSERT ... ON DUPLICATE KEY UPDATE` 单行 JSON 存储；schema_mysql.sql 加 `UNIQUE(lesson_date)` 约束 |
| P0-4 | **MySQL 缺 4 个方法** | list_stages / get_stage_by_order / get_stage_containing_date / get_practice_sessions_in_range | MySQLBackend 补 4 个方法（byte-equivalent） |
| P0-5 | **容器本地 FS 写** uploads/reports/badges | config.py:1113 写 data/uploads；app.py:1326 写 data/reports；badge_generator.py 写 static/badges | 迁移到 CloudBase 存储桶；DB 改存对象 key |
| P0-6 | **CloudRun 缺 hermes CLI** | Dockerfile 无 hermes；app.py:1280 / config.py:1270 `subprocess.run('hermes chat ...')` | 选项 A：build image 装 hermes；B：HTTP API 直调 LLM；C：生图功能灰掉 |
| P0-7 | **测试文件硬编码云连接串 + 明文密码** | tests/test_save_daily_practice_mysql.py:96-97 包含 dizical 账号明文 | 删硬编码 → env 读；轮换密码；清 git 历史 |
| P0-8 | **Dockerfile 注释泄露旧 host:port** | Dockerfile:28 | 删旧注释 |
| P0-9 | **`save_practice_session_and_daily_summary` 仍是 read-modify-write** | database_mysql.py:1135-1138 普通 SELECT，无 FOR UPDATE | 显式事务 + `SELECT FOR UPDATE` + `version` 列 |
| P0-10 | **5s 进程内 dedup 多实例失效** | app.py:29-54 `_dedup_cache: Dict` 进程级 | MySQL 唯一索引 + request_id 幂等表 |
| P0-11 | **request_id 缺失，minip 必双发** | api.ts:236-240 无 requestId；callContainer 8s race 后 wx.request fallback | 客户端生成 UUID + 服务端幂等表 |
| P0-12 | **practice_sessions 无 version/updated_at** | database_mysql.py:933-1091 update/delete 无版本条件 | 加 version BIGINT DEFAULT 1 + updated_at，UPDATE/DELETE 带 WHERE version=? |
| P0-13 | **MySQL `save_weekly_assignment` 写不存在的列** | database_mysql.py:384-410 INSERT item_id, target_minutes（schema_mysql.sql:169-178 没这两列） | 跟 P0-3 一起重写 |
| P0-14 | **MySQL 缺 whitelist / pin_fail_count 专用表** | settings K-V 表 `INSERT OR REPLACE` 整条覆盖，并发不安全 | 拆 `dad_whitelist_members` + `pin_fail_count` 独立表 |
| P0-15 | **/health 数据库挂也返 200** | app.py:82-105 只查 get_all_lessons | 拆 `/health/live`（仅进程存活）+ `/health/ready`（DB 真正可用） |
| P0-16 | **MySQL 客户端无 connect_timeout/read_timeout/write_timeout** | database_mysql.py:36-66 | 加超时参数 + ping(reconnect=True) |
| P0-17 | **mac app 启动 uvicorn 不传 DATABASE_URL** | DizicalMacApp.swift:218-221 | 显式注入 DATABASE_URL 到 launchctl plist |
| P0-18 | **cloudrun.yaml 时空配置漂移** | cloudrun.yaml:20 写 SQLite，端口 80（线上 8080） | 改 MySQL 或删除 yaml 让 MCP 控制 |
| P0-19 | **JWT_SECRET 明文** | cloudrun.yaml:21 + spike-deploy.sh:61 | 改 Secret 注入 |
| P0-20 | **mac 0 写保护 + 个人版回档未确认** | CloudBase MySQL 个人版 | 改套餐或接受手动备份策略 |
| P0-21 | **`save_daily_practice` 缺行为 JSON 字段** | behavior_log 第 2 轮 SELECT-UPDATE 独立，窗口 | 合并为单次 SELECT FOR UPDATE |
| P0-22 | **audit log 两后端时机不一致** | SQLite conn.commit 在 audit 之前 vs MySQL audit 在事务内 | SQLite audit 移入事务 |
| P0-23 | **5s 进程内 dedup 在 CloudRun 多实例下完全失效** | app.py:32 进程 dict | 单实例强制 + 切云前完成 idempotency 表 |
| P0-24 | **myiqldump→SQLite 备份缺 JSON/时区/类型校验** | 并发研究 §5.2 | Python mysql-connector → sqlite3 转换器 + json_valid + 行数对账阈值 0 |

> **主 agent 修正**：SRE v2 的 P0-NEW-1/2/3/4/5 与全栈 QA 的 P0-NEW-1/2/3 高度重合（17 处 conn.execute、weekly_assignments schema 异构、4 个缺方法、容器本地 FS、缺 hermes CLI），已合并去重。测试文件硬编码凭据是真正新发现，列入 P0-7。

---

## 2. P1 切云后一周内必修

| # | 描述 | 证据 |
|---|------|------|
| P1-1 | `migrate_data.py:32-46` TABLES_ORDER 缺 `practice_sessions` | TABLES_ORDER 列表 |
| P1-2 | `practice_items` content_options 写并发 last-write-wins | database_mysql.py:358-366 |
| P1-3 | 53 写端点中方案只覆盖 12（23%），盲盒/白名单/课节/缴费/报告/badge 裸奔 | config.py:132-1138 + badge_workflow.py:92-540 |
| P1-4 | launchd 备份目录若在仓库内（data/backups/）不在 AGENTS 红线范围 | 当前方案未指定 |
| P1-5 | `settings` 表拆专用表缺事务边界 + 切云过渡期双写 | database.py:414-421 |
| P1-6 | /health 拆 /health/ready 时不更新 CloudRun 配置 | app.py:82-105 |
| P1-7 | 容器 init script 不传 DATABASE_URL | 缺 |
| P1-8 | CloudRun `/health/ready` 必须 503 时才能阻止流量 | 缺 |
| P1-9 | RPO/RTO 数字承诺未明 | 方案缺 |
| P1-10 | launchd 在 Mac 睡眠/断网下行为 | 需测试 |
| P1-11 | 告警机制 | 缺 |
| P1-12 | 部署回滚 vs 数据回滚 分离 | 缺 |
| P1-13 | 测试矩阵空，0 基线 | 720+ 用例 0 个 |
| P1-14 | audit_mode mock 边界未声明 | minip_api.py:211 返 mock 全量 |
| P1-15 | CORS allow_origins=["*"] 切公网后安全风险 | app.py:75 |
| P1-16 | /api/praise 已 410 Gone 但路由仍注册 | app.py:1875 |
| P1-17 | apply-access 死端点 | minip_api.py:619 定义，mp 端 0 调用 |
| P1-18 | 课程 cancel/confirm/reschedule/fee-paid 无幂等 | config.py:688-811 |
| P1-19 | blindbox/theme 未入 inventory | config.py:847-868 |
| P1-20 | PIN 宽模式自动加白 | minip_api.py:155-163 |

---

## 3. P2 切云后两轮内补

- 单实例强制 vs 多实例扩容时机
- CloudBase 个人版回档能力确认
- 备份 iCloud 冗余
- idempotency 表分区（按月）
- 失败 UX 提示统一
- 客户端冲突 UI（"上次修改时间 + 来源 client"）
- mac 端离线兜底
- lesson_audit_log / payment_audit_log

---

## 4. 失败场景库（已发生或高概率触发）

| ID | 场景 | 触发条件 | 后果 |
|----|------|----------|------|
| F1 | 跨实例双发 | CloudRun 多实例 + minip 弱网 fallback | 累加 2x 写库 |
| F2 | mac + web 同时编辑 weekly_assignment | 两端同时改 | 一端覆盖另一端 |
| F3 | lease 心跳超时无清理 | 设备崩溃/断网 | 锁永久持有 |
| F4 | 切云前 SQLite 自增 ID 与云 MySQL AUTO_INCREMENT 漂移 | 迁移时 ID 不对齐 | INSERT 冲突 / 错位 |
| F5 | 软删除缺失 | DELETE practice_session | FK 引用断裂 |
| F6 | behavior_log 爆 65k | 长期积累 | 整条 JSON 超限 |
| F7 | 出差时区错位 | 非中国时区 | 日期偏 1 天 |
| F8 | 恢复演练误写覆盖 backup | 脚本误操作 | 备份被覆盖 |
| F9 | 切 DATABASE_URL 后任意写请求 | P0-1/2/3/13 触发 | 500 |
| F10 | 容器重启 | P0-5/6 触发 | uploads/reports/badges 丢；生图崩 |

---

## 5. Go/No-Go 结论

**结论：NO-GO**

理由：
- 17 处裸 conn.execute / ? 占位符 / json_extract 是物理阻断（切 DATABASE_URL=mysql 后 100% 500）
- weekly_assignments 两后端 schema 异构是功能阻断（assignment 不可用）
- MySQL 缺 4 个方法是 stage 报告阻断
- 容器本地 FS 写是容器重启阻断
- 缺 hermes CLI 是生图功能阻断
- 测试文件泄露生产凭据是安全阻断

**进入 Sprint 04 切云前必须修完 P0-1 ~ P0-24。**

---

## 6. 上线门禁（37 项 checkpoint，全部 ✅ 才允许 Sprint 04）

详见 `/Users/mt16/dev/dizical/.hermes/plans/2026-08-04_cloud-cutover-sre-redteam-review-v2.md` §11

- 7 项 schema/migration
- 6 项 idempotency/lock
- 4 项 timer lease
- 5 项 audit
- 4 项 backup
- 3 项 health/ready
- 4 项 secret/cred
- 4 项 smoke

---

## 7. 不可逆操作清单（仅 Sprint 04 执行，必须显式 go）

1. 云端清表 / 本地权威覆盖
2. 修改 CloudRun `DATABASE_URL`
3. 停止 SQLite 正常写入
4. 安装本地 `launchd` 任务
5. 轮换数据库凭据
6. 修改生产 CloudRun 配置
7. 执行恢复或回档
8. 删除任何云实例、表或本地文件

每项必须有：操作前备份 + dry-run + 影响清单 + 回滚方式 + 单独 go。

---

## 8. 修复时间表（与 sprint plan 一致）

```
10:55 tag + 备份
11:00 切 feat/cutover-parity-fix-2026-08-04 分支
11:05-11:15 写 MAINTENANCE_MODE middleware + 部署只读
11:20 Telegram 通知 dad
11:25 dad 出门
11:30-12:50 Phase 2 parity 修复 (17+4+2+1+1 处)
12:50-13:00 本地起 MySQL 后端 + curl 53 写端点
13:00 切回非只读 + Telegram 解禁通知
14:00-15:00 女儿练的
```

**当前 sprint plan 在 `/Users/mt16/dev/dizical/.hermes/plans/2026-08-04_parity-fix-sprint.md`，v1 已写。**
**v2 待写：v1 + 完整 P0-1~P0-24 + 失败场景 F1~F10 + 门禁 37 项。**
