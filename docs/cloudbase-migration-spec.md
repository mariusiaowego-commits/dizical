# CloudBase 迁移技术 spec

## 项目背景

dizical 当前是单机 FastAPI + SQLite, 仅在本地 8765 端口运行. 多端 (小程序 / web / Mac app) 依赖本地 Mac 在跑, 离开 Mac 寸步难行.

本次迁移目标: **dizical 全量数据 + 业务逻辑搬到腾讯云开发 (CloudBase)**, 所有端直接调云函数, **不再依赖本地服务**.

## 决策

- ✅ **保留**: 数据模型 + 业务逻辑 (Python 翻译成 Node.js 云函数)
- ❌ **退役**: FastAPI 后端 + 本地 SQLite 写权限
- 🔄 **改造**: 本地 SQLite → 只读备份 (cron 全量拉云)

## 范围

### In scope

| 模块 | 数量 | 备注 |
|------|------|------|
| 云函数 | 67 个 | 跟现有 FastAPI endpoint 一一对应 |
| 云数据库集合 | 12 个 | NoSQL, 跟现有 SQLite 表对应 |
| CloudBase Storage | 1 个 bucket | 头像 + 证书 |
| 鉴权 | JWT (HS256, 30d) | web / Mac app 用 |
| 本地备份脚本 | 1 个 Python 脚本 | 全量拉云 → 本地 .json |
| Cron | 1 个 LaunchAgent | 凌晨 3 点 |

### Out of scope

| 项 | 原因 |
|----|------|
| FastAPI 框架升级 | 全迁云, FastAPI 不再使用 |
| WebSocket 推送 | CloudBase 提供但项目不需要 |
| 多 region 部署 | 个人项目单 region 够用 |
| 企业级高可用 | 个人项目用不到 |
| 现有 SQLite 数据迁移 | 由 `scripts/migrate_data_to_cloud.py` 一次性脚本处理 |

---

## 云数据库集合 schema

| 集合 | 字段 | 索引 |
|------|------|------|
| `students` | _id, name, pin_hash, avatar_url, created_at | name (unique) |
| `teachers` | _id, name, phone, notes, created_at | - |
| `lessons` | _id, student_id, teacher_id, date, status, notes | student_id+date |
| `records` | _id, student_id, date, duration_min, items[], notes | student_id+date |
| `assignments` | _id, student_id, date, item_id, target_min | student_id+date |
| `achievements` | _id, student_id, badge_id, unlocked_at | student_id+badge_id |
| `blindbox` | _id, student_id, week_start, days[7] | student_id+week_start |
| `streak` | _id, student_id, current_days, last_checkin | student_id (unique) |
| `bless_pool` | _id, message, weight, used_count | - |
| `payments` | _id, student_id, lesson_id, amount, status, paid_at | student_id+status |
| `categories` | _id, name, color, icon | name (unique) |
| `items` | _id, category_id, name, target_min_default | category_id |

**字段命名规则**:
- 主键用 `_id` (CloudBase 自动生成)
- 外键用 `_id` 后缀 (e.g. `student_id`, `teacher_id`)
- 时间戳用 ISO 8601 字符串 (e.g. `"2026-07-16T10:30:00Z"`)
- 不存 enum, 用字符串 (CloudBase 不支持 enum)

---

## 云函数命名 + 路径

```
cloudfunctions/
  auth/
    login/index.js
    verify-pin/index.js
    refresh/index.js
    logout/index.js
    change-pin/index.js
  records/
    submit/index.js
    list/index.js
    get-daily/index.js
    get-monthly/index.js
    update/index.js
    delete/index.js
    stats/index.js
    bless-pool/index.js
  ...
```

每个云函数独立文件夹, 独立 package.json, 独立 deploy.

---

## 鉴权设计

### 三层

| 层 | 范围 | 实现 |
|----|------|------|
| L1 | 小程序 | `wx.cloud.callFunction` (免鉴权) |
| L2 | web / Mac app | Bearer Token (JWT, 30d 过期) |
| L3 | 数据级 | 云函数内 `jwt.verify(token)` 后, 按 role 判断可访问范围 |

### Role

| Role | 可访问 |
|------|--------|
| `student` | 自己的 records / achievements / assignments |
| `parent` | 所有学生数据 + 全部 lessons / payments |
| `admin` | 全部 + config + admin API |

---

## 本地备份

| 类型 | 频率 | 路径 | 保留 |
|------|------|------|------|
| 日 | 凌晨 3 点 | `~/.dizical/backups/daily/dizical-YYYYMMDD.json` | 7 天滚动 |
| 月 | 1 号 4 点 | `~/.dizical/backups/monthly/dizical-YYYYMM.json` | 12 月 |
| 季度 | 1/1, 4/1, 7/1, 10/1 5 点 | `~/.dizical/backups/snapshot/dizical-YYYYQ.tar.gz` | 永久 |

---

## 实施

12 天分 9 个 Phase, 每个 Phase 独立 commit + 测试 + 可合并. 详见 `migration-plan.md` (Obsidian).

---

## Git 策略

```
dizical 仓库:
  main (保持当前 FastAPI 跑, 不动)
    └── feat/p4-cloudbase-migrate-backend (主分支)
          - Day 3-8: 加 backup 脚本 + 双跑过渡
          - Day 10: 退役 FastAPI commit
```

### Commit 模板

```
<type>(<scope>): <subject>

<body>

<footer>
```

type: feat / fix / docs / chore / refactor
scope: cloudbase / backup / auth / records / ...

---

## 验收

| 项 | 标准 |
|----|------|
| 67 云函数全部署 | CloudBase 控制台可见, 每函数状态"运行中" |
| 小程序提审通过 | 微信公众平台版本管理显示"已发布" |
| 多端可访问 | 小程序 / web / Mac app 都能调通任一端点 |
| 本地备份可用 | 备份文件可解析, 校验脚本 OK |
| 数据安全 | 误删测试: 删 1 条 records → 7 天内可从备份恢复 |

---

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| CloudBase 配额超限 | 低 | 小程序不可用 | 监控 + 提前告警 |
| 数据迁移丢失 | 中 | 历史数据没了 | 迁移前全量备份, 迁移后逐条校验 |
| 鉴权漏洞 | 中 | 数据泄漏 | 小程序 + JWT 双重, 云函数内 role 校验 |
| 备份脚本 bug | 低 | 备份失败 | 加 checksum + 校验 + 失败告警 |
| 审核被拒 | 中 | 上线延期 | 提前 1 周提交, 预留改时间 |

---

## 相关文档

- Obsidian: `hermes-base/projects/project-dizical-cloudbase/`
  - `architecture.md`
  - `functions-catalog.md`
  - `migration-plan.md`
  - `local-backup-strategy.md`
- 通用模式: `hermes-base/concepts/tencent-cloudbase-pattern.md`
- 小程序侧 spec: `dizical-minip/docs/cloudbase-spec.md` (待写)