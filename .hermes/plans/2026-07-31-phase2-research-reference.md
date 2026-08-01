# Phase2 重新规划 — 双仓库 Research Reference (2026-07-31)

> 触发: dad "三端统一云数据库 + CRUD 加锁防多端重复添加" 重新 plan 前的 research
> 方法: 2 个并行 subagent 只读审查 dizical 后端 + dizical-minip, 全部证据 file:line 可溯
> 状态: 调研完成, 待 dad 拍板后据此重写 phase2 plan

---

## 1. 双后端架构 (dizical 后端)

- **工厂**: `src/database.py:1537-1545` — 模块加载时看 `os.environ["DATABASE_URL"]` 是否以 `mysql` 开头, 是 → `MySQLBackend`, 否 → SQLite `Database`
- **三文件分工**:
  - `src/database.py` = SQLite 后端 + 工厂
  - `src/database_mysql.py` = MySQL 后端 (连接池 PooledDB max 10, `:46-57`), 镜像 53 方法
  - `src/database_base.py` = ABC 基类, 强制 session CRUD 4 方法签名 (`:21-66`)
  - `src/db_adapter.py` = 占位符兼容层 (`?`↔`%s`), achievement/calc 等非 db 单例代码用
- **当前本地 8765 跑 SQLite**: `~/.zshrc` 无 DATABASE_URL, 服务 PID 93481 实际 SQLite
- **CloudRun 配置层仍是 SQLite**: `cloudrun.yaml:20` = `sqlite:////tmp/dizical.db`, 注释 "Phase 1 改 MySQL" — **实际云端跑什么库待 mcp 验证** (7-17 部署时手工注入过 DATABASE_URL)

## 2. 写路径并发审计 (核心)

| 路径 | SQLite | MySQL | 并发结论 |
|---|---|---|---|
| save_daily_practice | `BEGIN IMMEDIATE` 写锁 (`:764`) | **无锁**, SELECT→merge→写 (`:473-525`) | MySQL lost-update |
| save_practice_session_and_daily_summary | `BEGIN IMMEDIATE` 事务 (`:1415`) | pymysql 事务但**无行锁** (`:1118`) | 同 (date,item) 并发追加会丢 |
| append_behavior_log | BEGIN IMMEDIATE + SELECT→append | **JSON_ARRAY_APPEND 原子** (`:539-557`) | ✅ 唯一 DB 级原子写 |
| add_lesson | 纯 INSERT, **无唯一约束** (`:34-47`) | 同 | check-then-insert 竞态 (lesson_manager.py:124-127) |
| achievements | badge_write_tx 事务 (`:25-43`) | ON DUPLICATE KEY (`:643-661`) 疑似死代码 (badge_db 用 sqlite3 语法) | MySQL 路径可能不可用 |
| weekly_assignments | INSERT OR REPLACE + UNIQUE | **DELETE 旧行+逐条 INSERT** 非原子 (`:388-402`), 列名与 DDL 不一致 | ⚠️ 漂移 |
| set_setting | INSERT OR REPLACE (`:402`) | ON DUPLICATE KEY (`:263`) | ✅ 幂等 |

**现有去重机制 (全仓仅 3 种)**:
1. **5s 进程内内存 dedup** (`app.py:29-54`) — key=(date,item_id,minutes), **单实例有效**, CloudRun 多实例即失效
2. 唯一键: daily_practices.date UNIQUE / practice_items.name / practice_categories.name / settings.key
3. INSERT OR IGNORE / ON DUPLICATE KEY (仅部分表)

**全仓无**: SELECT FOR UPDATE、retry-on-conflict、version 乐观锁、幂等键。父 PRD 只"建议"过 `updated_at + WHERE updated_at=?` (`AI-PRD-前后端统一云-260717.md:142-148`), 从未实施。

## 3. 两后端行为漂移 (切云前必修)

1. MySQL save_daily_practice **会覆盖 practice_at** (SQLite 保留首次, `:502-507` vs `:797-803`)
2. MySQL 旧路径 **不写 audit log** (`:446` kwargs 只取 practice_at)
3. weekly_assignments MySQL 写 schema 与建表 DDL 列名不一致
4. badge_db.py 写路径用 sqlite3 命名参数 SQL, MySQL 连接上不可执行
5. 跨库类型: practice_at (SQLite TEXT CST / MySQL DATETIME)、behavior_log (空串 vs '[]')

## 4. practice_sessions (7-28 已补齐, 不再是缺)

- 7-28 PR-B 补齐 MySQL 5 方法 (get_by_id/get_list/create/update/delete + save_session_and_daily_summary) (`database_mysql.py:830-1215`), ABC 强制
- **无唯一约束** → 双击/重传唯一防线 = 5s 路由 dedup
- SQLite 建表只在迁移脚本 `migrate_add_practice_sessions.py:47-61`, 不在 _init_tables

## 5. 待合 2 个 mysql fix (7-27, 仍在 phase1b 分支)

| commit | 修什么 |
|---|---|
| c46557c | save_daily_practice 收 practice_at kwargs + 列名 items_json→items (原来会 500) |
| 0af13d6 | REPLACE INTO 补 behavior_log 列 (NOT NULL 无默认值) |

## 6. dizical-minip 现状

- **生产 baseURL** = CloudRun 域名, ACTIVE_ENV=prod (`env.ts:27,36`), 已连云端
- **apiCall 双发竞态** (`api.ts:260-286`): callContainer 8s 超时 → 不取消原请求, 同 path/data 再发 wx.request → **同一 POST 可能后端收两次, 落两条**
- **payload**: date/items/total_minutes/tempo_note/tempo_bpm/content/content_source; **无 practice_at / behavior_log** (`practice.vue:1268-1277`)
- **认证**: 无用户系统, PIN 0905 + openid 白名单, openid 在 body 传 (不是 header), 伪 token 从不发送, 后续靠网关注入
- **防重**: submitting ref 防连点 ✅ (`practice.vue:1257,1260`), 但按钮没 disabled; 失败重提/超时双发/跨端无防护
- **提审**: 已发 f8c2712 (7-28 16:30), 等微信 1-3 工作日 (AGENTS.md:66-74)
- **minip 只读 practice_sessions**, 写由后端 POST /config/api/records 事务完成
- **数据红线** (AGENTS.md:236-252): 沙盒期 web/mac 不写云, 上线前删云重复制, 本地 SQLite 永不删
- **多端锁草稿已有**: AGENTS.md:307 "version + updated_at 乐观并发"

## 7. 云端现状待验证项

- [ ] mcp 查 CloudRun 服务实际 env (DATABASE_URL 是否真 MySQL)
- [ ] mcp DESCRIBE 云 MySQL 全表 schema vs 本地 (practice_sessions 是否存在, weekly_assignments 列名)
- [ ] 云端数据行数 vs 本地 (7-27 后本地有新增, lesson_count 17→24)

## 8. phase2 原计划 6 步 (7-27 暂缓, 全部未实施)

1. 本地备份 ✅ 唯一做完 (data/backups/phase2-pre-cloud-20260727-154911/)
2. migrate_cloud_schema.py — 补云端缺表 ❌
3. sync_local_to_cloud_phase2.py — INSERT IGNORE 全量 13 表 ❌
4. cherry-pick 2 个 mysql fix ❌
5. kid_app 加 DATABASE_URL 切云 + 验证 ❌
6. cloud_backup.sh 一键备份 ❌

---

## 结论: 重新 plan 必须覆盖的 3 个空白

1. **迁移策略**: 本地(权威, 1560+ 行, 7-27 后还在涨) → 云(793 行副本 + 测试数据)。INSERT IGNORE 只补缺 vs 以本地覆盖, 需 dad 拍
2. **三端同库架构**: 小程序已连云 ✅; web/mac = 本地 kid_app 加 DATABASE_URL 切云 (mac app 是 WKWebView 壳不改代码); CloudRun 配置层 SQLite 遗留要修
3. **并发锁**: 现状只有 5s 单实例 dedup。方案候选:
   - 幂等键 (客户端 requestId + 后端 idempotency 表) — 防双发/重提/连点
   - 乐观锁 version/updated_at — 防编辑 lost-update
   - MySQL 行锁 SELECT FOR UPDATE — 串行化读改写 (单家庭场景杀鸡用牛刀)
   - 父 PRD 已提乐观锁 (未实施), minip AGENTS.md:307 也倾向乐观锁
