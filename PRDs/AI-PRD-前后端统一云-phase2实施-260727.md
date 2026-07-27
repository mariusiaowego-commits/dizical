# AI-PRD-前后端统一云-phase2实施-260727

> 📌 父 PRD: `Obsidian/tqob/05-Coding/project-dizical/PRDs/AI-PRD-前后端统一云-260717.md` (4 阶段方案)
> 📌 本 PRD = 阶段 1 实施明细 (PR-1)
> 📌 触发: dad 7-27 拍 Q1=A / Q2=手动激活 / Q3=A / Q4=A / Q5=A(等前提) / Q6=A / Q7=A / Q8=C(暂缓)

**日期**: 2026-07-27
**分支**: `feat/p4-phase2-web-mac-to-cloud` (基于 main, 不基于 staging)
**状态**: ⏳ 进行中 (PR-1 待提交)
**范围**: 1 PR (cherry-pick + schema 迁移 + 数据同步 + 切云 + 验证)

---

## 🎯 目标

将 dizical 主仓 **web + mac 端**后端从**本地 SQLite 单后端**切到 **DATABASE_URL env 驱动的双后端** (默认 SQLite, 有 env 走云 MySQL).
阶段 1 不停用本地 SQLite, web 端 `8765` 服务启动时读 `~/.zshrc` 的 `DATABASE_URL`, 写入走云 MySQL, 读出也走云 MySQL.

**dad 7-17 红线** (AGENTS.md §"数据策略红线"):
- 本地 SQLite **永不删** (本 PRD 也遵守)
- 沙盒期本地与云分裂, **接受**
- 退出沙盒条件 = 4 前提满足 (见 Q5)

**关键架构发现 (dad 7-27 Q11)**:
- mac app 在主仓 `channels/mac-app/Sources/DizicalMac/DizicalMacApp.swift` 里
- `DIZICAL_URL = "http://127.0.0.1:8765"` (line 18) — mac app 是 WKWebView 容器, **所有业务请求打本地 kid_app**
- **切云 = mac app 不用改 1 行代码** (业务走 kid_app, kid_app 切云)
- Q6=A "mac app 跟 web 同 PR 走 A 路径" = **同 PR 切云, 但 mac app 实际无代码改动** (只需确认 menu bar 启 kid_app 仍能拉起云)

---

## 📋 PR-1 6 步清单 (Q7=A 1 PR 全部完成)

| # | 任务 | 输出 | 验证 |
|---|------|------|------|
| 1 | ✅ 本地 SQLite 备份 | `data/backups/phase2-pre-cloud-20260727-154911/` 684K, integrity_check=ok | sqlite3 PRAGMA |
| 2 | 写云端 schema 迁移脚本 `scripts/migrate_cloud_schema.py` | 13 表补齐, 含 7-27 新加的 `practice_sessions` + `practice_items.last_tempo_note/bpm` | mcp 云端 DESCRIBE 全表 |
| 3 | 写本地→云一次性数据同步脚本 `scripts/sync_local_to_cloud_phase2.py` | 13 表 INSERT IGNORE, 全量, 跑前 mcp DESCRIBE 云端 + 跑后 diff 行数 (含 dad 7-27 提的"小程序测试数据 1 条不删, 后续手动删") | 同步前/后行数 diff + 测试数据行仍在 |
| 4 | cherry-pick `feat/p4-phase1b-staging` 2 个 mysql fix 到 phase2 | commit `c46557c` (kwargs) + `0af13d6` (behavior_log) | git log --oneline |
| 5 | mac kid_app 加 `DATABASE_URL` env + 验证 web 录入 → 云 MySQL 有新行 + mac app 仍能拉起 kid_app | `~/.zshrc` 写 export, `start-prod.sh` 重启服务, web 录入一次, pymysql 查云, mac app 菜单栏 "打开" 验证 | curl + pymysql + mac app launchctl |
| 6 | 写 `scripts/cloud_backup.sh` (Q2: dad 手动激活, 不进 cron) | mysqldump 拉云 → `~/.dizical/backups/manual/` | dad 手跑验证 |

---

## 🏗 架构决策 (dad 7-27 拍板 6 个)

### Q1 (cherry-pick vs merge): A — cherry-pick 2 个 fix 到 phase2

**理由**: staging 上 2 个 fix (commit c46557c/0af13d6) 解决 MySQL REPLACE INTO bug, 不带进 phase2 = 写入 500. merge staging 全部 11 commit 会混进 verify-pin / dockerfile 撤回等不属于 phase2 的内容.

### Q2 (定期备份方向): dad 手动激活, 不进 cron

**实现**: `scripts/cloud_backup.sh` 一键脚本 (mysqldump + sqlite3 .restore), dad 想说"备份"就 `bash scripts/cloud_backup.sh`. 不写 crontab. **违反常规运维**但符合 dad "不要双写架构" + "手动控制"偏好.

### Q3 (迁移前同步最新数据): A — 本地 → 云 一次性 INSERT IGNORE

**理由**: web/mac 仍本地权威, 切云后云 = 沙盒副本. 13 表全量同步, 但**只跑一次** (PR-1 内). 后续日常运维靠"切云后云端是权威, 本地 cron 拉云" (Q2 脚本, dad 手动激活).

**风险**: 同步后本地继续写, 云端不感知 = 7-17 数据策略红线第 2 条 "沙盒期分裂, 接受". PR-1 切云后**所有写入走云**, 本地 SQLite 立即**无新数据**. 后续 dad 想恢复本地时用 Q2 脚本拉一次即可.

### Q4 (PRD 双写): A — 2 个 Obsidian 子目录镜像

**路径**:
- 主仓: `PRDs/AI-PRD-前后端统一云-phase2实施-260727.md` (本文件)
- Obsidian: `tqob/05-Coding/project-dizical/PRDs/AI-PRD-前后端统一云-phase2实施-260727.md`
- Obsidian (minip 镜像): `tqob/05-Coding/project-dizical-minip/PRDs/AI-PRD-前后端统一云-phase2实施-260727.md`

**双写校验**: `md5 -q <主仓路径> <镜像路径>` 必须一致.

### Q5 (切云后本地关系): A — 停用本地 SQLite, 但 **必须 4 前提全满足**

**进入条件** (all must be true):
1. ❌ 小程序提审通过 + 上架 (dad 没动, 7-17 至今)
2. ⚠️ 云 MySQL 完整可用 (PR-1 第 2 步完成 = 满足)
3. ✅ 小程序录入练习正常写库 — **dad 7-27 14:51 反馈已验证**: 在小程序做了测试录入, 云端有 1 条测试数据 (dad 拍"可以后续删除, 今天就在做测试")
4. ❌ 小程序含 dizical 最新功能 (minip 完全没对接 practice_sessions, minip `submitRecord` 字段缺 `tempo_note/bpm/content`)

**当前状态**: 4 前提 2/4 满足 (前提 3 新满足). **PR-1 不动"停用本地"** (留待阶段 C).

**dad 7-27 14:51 关键事实** (PR-1 同步脚本设计要遵守):
- 在没迁移好之前, **所有新数据从本地 SQLite 更新** (web/mac 8765 服务持续写入本地)
- 小程序里有 1 条测试数据在云端, **不删** (dad 后续手动删, agent 不动)
- 同步脚本用 INSERT IGNORE, **不覆盖** 云端已有 (含那条测试数据)

**PR-1 切云后** = **"双写架构雏形"**:
- 写入走云 (DATABASE_URL env)
- 本地 SQLite **保留可读** (kid_app 启动时不删, dad 想 fallback 时 `unset DATABASE_URL` 重启即可)
- 本地不再有新数据 (无写入)
- 这违反 dad "不要双写" 历史偏好, 但**不**违反"停用本地"红线, 阶段 C 才真停

### Q6 (mac app 切云是否同 PR): A — 同一个 PR, 但**走 A 路径**

**含义**: Q6 字面 "同一个 PR" + "走 A 路径" = PR-1 同时改 `mac-app/.../config.js` URL 改云端?

**实际架构 (dad 7-27 Q11 摸清)**:
- mac app 在主仓 `channels/mac-app/Sources/DizicalMac/DizicalMacApp.swift` (line 18)
- `DIZICAL_URL = "http://127.0.0.1:8765"` — mac app 是 WKWebView 容器, 所有请求打本地 kid_app
- **切云 = mac app 不需要改任何代码** — kid_app 自己切云, mac app 仍是壳
- 验证: mac app 菜单栏 "打开" → 触发 kid_app (uvicorn) → kid_app 读 DATABASE_URL 走云

**Q6=A 实际意义**: PR-1 同时确认 mac app 仍能拉起 kid_app (且 kid_app 已切云), 不改 mac app 任何代码. **PRD 6 步不变, 不变 6+1 步**.

### Q7 (PR 范围): A — 1 PR 全部 6 步

**优势**: 1 PR = 1 review, 1 deploy, 1 验证回滚链. dad 偏好 "做好一个我满意一个 commit 一个" 但**这次是跨架构改动, 不能拆**, 拆了等于 web 切云后 mac app 仍指本地 = 数据分裂.

**6 步清单** (Q11 摸清后修正):
1. ✅ 本地 SQLite 备份 (684K, integrity_check=ok)
2. 写云端 schema 迁移脚本 `scripts/migrate_cloud_schema.py`
3. 写本地→云一次性数据同步脚本 `scripts/sync_local_to_cloud_phase2.py`
4. cherry-pick `feat/p4-phase1b-staging` 2 个 mysql fix (c46557c/0af13d6) 到 phase2
5. mac kid_app 加 `DATABASE_URL` env + 验证 web 录入 → 云 MySQL 有新行 + mac app 仍能拉起 kid_app
6. 写 `scripts/cloud_backup.sh` (Q2: dad 手动激活, 不进 cron)

**mac app 无需改 1 行代码** (WKWebView 容器壳, 业务走 kid_app).

### Q8 (minip 端谁写): C — 暂缓

**minip 端要加的改动** (Q5 前提 4):
- `submitRecord` 增加 `tempo_note/bpm/content` 字段
- 新增 UI 录入"速度 + 内容" 输入项
- 调 5 个新 API: GET `/api/practice-sessions/{date}`, GET `/api/practice-sessions/latest`, GET `/api/assignments/latest`, DELETE `/api/practice-sessions/{id}`

**当前**: minip 仓 `fix/records-item-name` 分支有 dad 自己改的 PR in-flight (`425f251 submitRecord + submitSupplement 加 item 字段`). 跟 PR-1 冲突, 暂缓.

**PR-1 跟 minip 端无代码耦合** (主仓是后端 + kid_app, minip 端独立). PR-1 切云后 minip 端继续写云 = 无需 minip 改 1 行.

---

## 📌 阶段 1 完成 ≠ 阶段 C 入口

阶段 1 切云后, dad Q5 的"停用本地 SQLite"**不能立刻做**. 4 前提 (提审/云完整/录入正常/含新功能) 必须全部满足.

| 阶段 | 范围 | 当前状态 | 进入条件 |
|------|------|----------|----------|
| **PR-1 (阶段 A)** | kid_app 切云 + mac app URL 改云 + 备份脚本 | ⏳ 进行中 | Q1-Q7 答案收齐 |
| **PR-2 (阶段 B)** | minip 端加 practice_sessions 录入 | ⏸ 暂缓 | Q8=C, dad 拍 |
| **PR-3 (阶段 C)** | 停用本地 SQLite (kid_app 不再有 SQLite fallback) | ⏸ 远期 | Q5 4 前提满足 |

---

## 🚦 风险矩阵 (PR-1 专项)

| 风险 | 概率 | 缓解 |
|------|------|------|
| **云端 schema 缺表** (7-27 practice_sessions + 冗余列) | 🟡 中 | 写迁移脚本前先 `DESCRIBE` 全表, 列 diff, 补全 |
| **同步冲突** (云端已有数据, INSERT IGNORE 不冲突, 但行 ID 可能乱) | 🟢 低 | 用 `INSERT IGNORE`, 不用 `REPLACE INTO` (避免覆盖) |
| **mac kid_app 切云后 iPad 不可用** (iPad 走 tailscale → mac kid_app) | 🟢 低 | 切云后 iPad 也走云 (kid_app 已被云代理), 反向路径更短 |
| **mac app config.js 改云后 WebView 缓存** (WKWebView 缓存老 config.js) | 🟡 中 | mac app 内加 fallback: 云端 5xx 时 fallback 到 localhost:8765 (本地 SQLite) |
| **DATABASE_URL 密码含 @ 字符** | 🟢 低 | URL encode 成 `%40`, 7-17 已处理 (commit 47f5307 撤回明文, 02cf4d6 改 env) |
| **mac 断网** | 🟡 中 | 暂时不实现离线兜底, dad 拍 "mac 断网 = 不录入" 可接受 |

---

## 🔄 回滚 SOP (PR-1 失败时)

```bash
# 1. 停 kid_app
bash scripts/stop-prod.sh

# 2. 撤 DATABASE_URL env
unset DATABASE_URL
# 或从 ~/.zshrc 删 export DATABASE_URL=...

# 3. 启 kid_app (fallback 本地 SQLite)
bash scripts/start-prod.sh

# 4. 验证本地 8765 仍可用
curl http://localhost:8765/health

# 5. 回滚代码 (git revert)
cd ~/dev/dizical
git checkout main
git branch -D feat/p4-phase2-web-mac-to-cloud

# 6. 云端数据保留 (不要删, dad 红线)
# dad 手动决定是否跑 scripts/cloud_backup.sh 拉回本地
```

**回滚时间预估**: 5 分钟 (停服务 + unset + 启动 + 验证). **不会丢任何数据** (本地 SQLite 红线 + 云端保留).

---

## 📁 文件清单 (PR-1 预期产出)

### 新增
- `scripts/migrate_cloud_schema.py` (~150 行) — 云端 schema 迁移
- `scripts/sync_local_to_cloud_phase2.py` (~120 行) — 本地→云一次性同步
- `scripts/cloud_backup.sh` (~50 行) — dad 手动激活, mysqldump 拉云→本地
- `data/backups/phase2-pre-cloud-20260727-154911/` (684K, 已存在)
- `handoff-2026-07-27-p4-phase2.md` (~8K) — 完整 handoff 记录

### 修改
- `~/.zshrc` — 1 行 `export DATABASE_URL='mysql+pymysql://...'` (不在 git, 爸爸手改)
- `src/database_mysql.py` — cherry-pick 2 commit (c46557c/0af13d6)
- `src/database.py` — 不动 (factory 已存在)
- `channels/mac-app/...` — **不动** (WKWebView 壳, 业务走 kid_app, kid_app 切云后 mac app 自动跟着切云)

### 不动
- `src/kid_app/app.py` — 不动
- `src/kid_app/routes/*.py` — 不动
- `dizi.db` — 切云后只读, 不删, 永久保留
- `data/backups/phase2-pre-cloud-20260727-154911/` — 永久保留

---

## 🗓 时间预估

| 步骤 | 预估工时 | 风险 |
|------|----------|------|
| 备份 (已完成) | 5 分钟 | ✅ 0 |
| 写迁移脚本 + 测 | 1-2 小时 | 🟡 schema diff 可能漏表 |
| 写同步脚本 + 测 | 1 小时 | 🟢 INSERT IGNORE 安全 |
| cherry-pick 2 fix | 10 分钟 | 🟢 conflict 小 |
| mac 切云 + 验证 web 录入 + mac app 拉起 | 30 分钟 | 🟡 mac 服务重启 + DB URL 注入 |
| (mac app 无代码改动) | 0 分钟 | 🟢 WKWebView 壳, 0 风险 |
| 写 handoff + 收尾 | 30 分钟 | ✅ 0 |
| **总计** | **4-5 小时 (1 工作日)** | |

---

## 🤔 关键决策记录 (跟父 PRD 的取舍)

| # | 决策 | 取舍 |
|---|------|------|
| 1 | PR-1 不动"停用本地" | 遵守 Q5 拍板 (4 前提才进) |
| 2 | 不写 cron 备份 | 遵守 Q2 拍板 (dad 手动激活) |
| 3 | mac app 跟 web 同 PR 切云 | 遵守 Q6 拍板 (走 A 路径) |
| 4 | minip 端暂缓 | 遵守 Q8=C 拍板 (dad 拍) |
| 5 | 主仓基于 main, 不基于 staging | 避免 staging 11 commit 混进 phase2, 仅 cherry-pick 2 fix |
| 6 | 同步用 INSERT IGNORE, 不用 REPLACE | 避免云端已有数据被覆盖 (含 dad 7-27 提的 1 条小程序测试数据, 不可破坏) |
| 7 | 切云后本地 dizi.db 保留可读 | 阶段 C 前的安全网, 紧急回滚 5 分钟内恢复 |
| 8 | dad 7-27 14:51: PR-1 切云前本地持续写, 同步后云端是 1:1 副本 + dad 测试数据 1 条保留 | 同步脚本 INSERT IGNORE + 跑前/后 DESCRIBE diff, dad 后续手删测试数据 |
| 9 | mac app 不动 1 行代码 (Q11 摸清: WKWebView 壳) | 简化 PR-1 6 步, 不再 6+1 步; mac app 切云 = 验证菜单栏能拉起 kid_app (uvicorn 走云) |

---

## 🔗 关联文档

- **父 PRD**: `Obsidian/tqob/05-Coding/project-dizical/PRDs/AI-PRD-前后端统一云-260717.md` (4 阶段方案)
- **数据策略红线**: `AGENTS.md` §"数据策略红线" (5 条红线)
- **dual-backend 参考**: `~/.hermes/profiles/coder/skills/projects/dizical-development/SKILL.md` (跨后端 SQLite↔MySQL 适配层模式, 2026-07-24)
- **schema 同步参考**: `references/schema-sync-local-to-cloud-mysql-2026-07-27.md`
- **handoff**: `handoff-2026-07-27-p4-phase2.md` (待写)
- **PR-1 关联**: `feat/p4-phase2-web-mac-to-cloud` (本分支)

---

**拍板就开干?**
