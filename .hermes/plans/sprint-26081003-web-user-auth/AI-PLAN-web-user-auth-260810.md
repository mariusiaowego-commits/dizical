---
id: 26081003
type: sprint
version: 2.0.0
start_date: 2026-08-10
end_date: TBD
status: 待启动
priority: 高
summary: web 用户体系 (B 方案本地化) — dad 后台建账号 + 首次改密 + config 管理权限
related: ["[[AI-PRD-前后端统一云-phase2实施-260727]]", "[[API-CHANGELOG]]"]
tags: [sprint, dizical, auth, user-system, web, password]
---

# Sprint 26081003 — Web 用户体系 (B 方案本地化)

**分支**: `feat/web-user-auth-260810` (已 checkout, 跟 main 同 hash, 空状态待动)
**触发**: dad "目前 web 端裸奔, 任何用户在公网拿到 url 就能开界面+录数据"

---

## 1. 背景 / 现状 (跟原 plan 一致)

### 1.1 鉴权现状（裸奔）
- **唯一鉴权端点** `POST /api/verify-pin` (app.py:2810), 比 settings.dad_pin (现=0905)
- **所有 GET 页面路由 + 大部分 API 完全无鉴权** (40 个路由中39 个无鉴权)
- 公网 URL 拿到就能进 + 录数据
- 抽屉 `_sidebar.html:215-220` 硬编码 `女儿 / 学习者`

### 1.2 历史 Phase B 残留 (PR #189, 7-28)
- minip 已有 `dad_whitelist` (openid 列表) + `pending_whitelist` + admin-whitelist.html (孤儿)
- 本次 web 端**完全不复用** (dad 8-10 拍板: 多密码本地, 不走 mp whitelist 体系)

### 1.3 dad 角色诉求（8-10 拍板）

| 角色 | 数量 | 看 | 录练习 | config / praise / admin |
|------|------|----|--------|------------------------|
| **dad (root)** | 1 | 全 | ✓ | ✓ PIN |
| **女儿** | 1 | 自己的练习 + 报告 | ✓ | ✗ |
| **家人** | N (待定) | 报告 + 成就 | ✗ | ✗ |
| **老师** | 1 (待定) | 全 | 待定 | ✗ |
| **访客 (guest)** | **本期砍掉** | - | - | - |

**重要变更**: dad 8-10 否决了方案 A (invite link) 和 A' (微信扫码)：
- A 否决理由: invite link 走 GitHub 模式, 家里很多人**网络不通** (翻墙/防火墙), 拿到 link 没法点
- A' 否决理由: 微信扫码要**自备已备案域名** + 个体户/企业主体, dad 用的是**腾讯送的 run.tcloudbase.com 子域名**, **无法备案**, 也不愿意再走资质

**dad 最终拍板**: **多密码账号体系, 全本地**, dad 在 config 后台手动建账号 + 分配角色权限。

---

## 2. 砍掉 vs 保留 (变更点)

| 原 plan 元素 | 8-10 拍板 |
|------------|----------|
| ❌ Invite Token | 砍 (网络不通) |
| ❌ 公开 Share Link | 砍 (走 GitHub 模式网络有问题) |
| ❌ 微信扫码登录 | 砍 (没自备域名) |
| ❌ 自助注册 | 砍 (dad 不开放注册, 账号全 dad 手动开) |
| ✅ 多密码账号体系 | **保留** (dad 拍板) |
| ✅ dad 后台建账号 | **新增** (dad 拍板: "用户首次注册就是我通过给额度的方式开放注册") |
| ✅ 用户名 + 密码登录 | **新增** (dad 拍板) |
| ✅ dad config 后台管理用户 + 权限 | **新增** (dad 拍板) |
| ✅ 首次登录强制改密 | **新增** (安全基线) |
| ✅ dad (root) 走原 PIN 模式 | **保留** (沿用 0905) |
| ✅ 抽屉 UI 动态化 | **保留** |

---

## 3. 目标 (Goal)

给 web 端建一套**dad 后台手动开账号 + 用户名密码登录 + config 管理权限**的传统多用户体系, 替代当前"裸奔+1 个全局 PIN" 模式。**mp 微信端完全不动** (沿用现有 openid 白名单机制)。

### 3.1 验收标准 (Acceptance Criteria)

#### Web 端 (本次实施范围)
1. **dad 唯一路径**: dad 在 `/config/users` 后台**手动**建账号 (输用户名 + 自动生成初始密码 + 选角色), 把初始密码微信手发给家人
2. **家人登录**: 浏览器打开 url → 重定向 `/login` → 输用户名 + 初始密码 → 强制改密 → 进权限范围内的页面
3. **权限矩阵**: 5 角色 × 资源矩阵严格执行, 越权返 403
4. **首次改密**: 初始密码登录后强制跳 `/change-password`, 改完才能进主站
5. **30 天 cookie 记住登录** (dad 8-10 拍板): 默认勾选, 关浏览器 30 天内自动登录, dad 在 `/config/users` 可强制踢出某用户所有设备
6. **dad (root)**: 走原 `/api/verify-pin` (PIN=0905), **不**走新密码体系, 配置修改/审批用户都走 PIN 守门

#### mp 微信端 (本次完全不动, 显式声明)
7. **mp 端 0 改动**: 沿用现有 7-28 PR #189 机制 — `wx.login` 静默拿 openid → 后端比 `dad_whitelist` → 首次自动加白名单 → 进入
8. **mp 端流程不变**: PIN + openid 白名单, 无需密码 (微信生态天然身份绑定)

#### 兼容性 + 回滚
9. **mp 兼容**: minip 现有 `dad_whitelist` + openid 路径 **零改动**
10. **回滚**: 单 PR revert, 回滚后 = 当前裸奔状态

---

## 4. 权限矩阵 (Design, 跟原 plan 一致)

| 资源 | dad (root) | 女儿 | 家人 | 老师 | 访客 |
|------|-----------|------|------|------|------|
| `/` 落地 | `/practice` | `/practice` | `/report` | `/practice` | - (本期砍) |
| `/prepare` `/practice` `/achievements` `/badges` | ✓ | ✓ | ✗ | ✓ | - |
| `/report` (PDF 下载) | ✓ | ✓ | ✓ | ✓ | - |
| `/config` `/praise` | ✓ (PIN) | ✗ | ✗ | ✗ | - |
| `/config/users` (用户管理) | ✓ (PIN) | ✗ | ✗ | ✗ | - |
| `POST /api/log` | ✓ | ✓ | ✗ | ✗ | - |
| `PUT/DELETE` 写操作 | ✓ | ✗ | ✗ | ✗ | - |

**老师能否录练习**: dad 拍板过 A = "全看 + 不录", 跟家人同只读 + 老师专属视图 (后续 sprint 加)。

**访客 (guest)**: 本期砍掉, 后续如需要 (公开 share report) 再走单独 sprint。

---

## 5. 数据模型

### 5.1 新表 `web_users` (结构化, 替代 settings JSON)
```sql
CREATE TABLE web_users (
  user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  username       VARCHAR(64) UNIQUE NOT NULL,        -- 登录名 (e.g. 'yoyo', 'dad')
  display_name   VARCHAR(64) NOT NULL,                -- UI 显示 (e.g. '女儿', '爸爸')
  password_hash  VARCHAR(256) NOT NULL,               -- argon2 hash
  role           VARCHAR(16) NOT NULL,                -- dad / student / family / teacher
  avatar_letter  VARCHAR(1),                           -- 单字母头像 (e.g. 'Y', 'D')
  must_change_password BOOLEAN DEFAULT 1,             -- 1=登录后强制改密
  created_by     INTEGER,                             -- 哪个 user_id 创建 (dad=NULL 允许)
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_login_at  DATETIME NULL,
  revoked        BOOLEAN DEFAULT 0                    -- 软删 (dad 后台操作)
);
```

### 5.2 哈希方案
- 用现有依赖 **`argon2-cffi`** (pyproject 已有, 不引新)
- 格式: `argon2$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>`
- 算法参数: 默认 OWASP 推荐 (memory 64MB, iterations 3, parallelism 4)

### 5.3 Cookie 设计 (30 天记住登录, dad 8-10 拍板)

**核心思路**: 不存密码明文到 cookie, 而是用 **itsdangerous 签名 Cookie** (现有依赖) 存 {user_id, expires_at, sig}。

| 选项 | 行为 | 业界对照 |
|------|------|----------|
| **A 30 天 Cookie** (默认) | 关浏览器 30 天内自动登录 | GitHub / Notion / Slack web |
| B 7 天 Cookie | 短一些, 安全性高 | 部分银行 web |
| C session Cookie (关浏览器即失效) | 每次重输 | 早年 jira / 老旧 OA |
| D 30 天默认 + checkbox | 用户可关 | Google / Facebook |

**实现细节 (Q3=A 路径)**:
- Cookie 名: `dizical_session`
- Cookie 内容: `itsdangerous.URLSafeTimedSerializer(app_secret).dumps({user_id, role})`
- Cookie 参数: `HttpOnly=True, Secure=True, SameSite=Lax, max_age=30*24*3600`
- 登录响应: `Set-Cookie: dizical_session=...; Max-Age=2592000; HttpOnly; Secure`
- 默认 remember=true (登录页 checkbox 已勾选, 用户可手动取消)

**登出策略**:
- 用户主动 logout → 清当前 cookie (前端 `Set-Cookie: Max-Age=0`)
- dad "踢出所有设备" → 重置 `SECRET_KEY` 或加 `web_users.session_version` 列 (递增), 老 cookie 签名对不上自动失效

### 5.4 兼容性 (重要)
- 现有 `settings.dad_pin=0905` **不动** (dad root 二次验证沿用)
- 现有 `settings.dad_whitelist` (mp openid) **不动** (mp 路径 100% 不变)
- 现有 `settings.pending_whitelist` 不动
- `web_users` 是**全新表**, 不破坏任何东西

### 5.5 初始化迁移
- `src/migrate_add_web_users.py` (新):
  - `CREATE TABLE IF NOT EXISTS web_users (...)` 幂等
  - **不自动建 dad 账号** (dad 走 PIN 模式不走 web_users)
  - 跑完输出 "表已就绪, 请去 /config/users 手动建账号"

---

## 6. API 端点 (新增)

| Method | Path | 角色 | 用途 |
|--------|------|------|------|
| POST | `/api/auth/login` | 任何人 | 提交 {username, password, remember=true} → 设 cookie + 返 user 对象 |
| POST | `/api/auth/logout` | 已登录 | 清 cookie (当前设备) |
| POST | `/api/auth/change-password` | 已登录 (must_change=1) | 改密 + 清 must_change 标志 |
| GET | `/api/auth/me` | 已登录 | 返 {user_id, username, display_name, role, avatar_letter, must_change} |
| GET | `/config/users` | dad (PIN) | 用户管理页 (列出 + 增/删/改/撤销 + 踢出所有设备) |
| POST | `/config/api/users/create` | dad (PIN) | 建账号 (username, display_name, role, avatar_letter) → 生成初始密码 + 返明文一次 (dad 复制发给家人) |
| POST | `/config/api/users/{user_id}/reset-password` | dad (PIN) | 重置密码 → 返新明文一次 + must_change=1 |
| POST | `/config/api/users/{user_id}/role` | dad (PIN) | 改 role |
| POST | `/config/api/users/{user_id}/revoke` | dad (PIN) | 软删 (revoked=1) |
| POST | `/config/api/users/{user_id}/logout-all` | dad (PIN) | 踢出该用户所有设备 (重置 cookie 签名密钥) |

**改动现有**:
- `POST /api/verify-pin` (app.py:2810): **不动**, dad 走 PIN, 不走新密码体系
- 所有 GET 页面路由: 加 `Depends(get_current_user)` 守门
- 所有 POST/PUT/DELETE API: 加 `Depends(require_role(...))` 守门

---

## 7. UI 改动

### 7.1 抽屉 UI (`_sidebar.html`)
- 当前硬编码 `Y / 女儿 / 学习者` 改为 Jinja 模板变量 `{{ user.display_name }}` / `{{ user.role_label }}`
- 角色 label: dad=「管理员」/ student=「学习者」/ family=「家人」/ teacher=「老师」
- **登出按钮** (右下角 footer 新增, 仅已登录显示)

### 7.2 `/login` 页 (新建 `templates/login.html`)
- 极简: 用户名 + 密码 + 登录按钮 + 错误提示
- 链接到 `/change-password` (must_change=1 时强制)

### 7.3 `/change-password` 页 (新建 `templates/change-password.html`)
- 首次登录强制改密页
- 旧密码 + 新密码 + 确认新密码

### 7.4 `/config/users` 页 (新建 `templates/config-users.html`)
- 仿现有 `config.html` 主色 (#FF6B6B) + 跟 `/config/blindbox` 等同风格
- 列出当前 web_users 表格: 用户名 / 显示名 / 角色 / 创建时间 / 最后登录 / 状态
- 操作: 新建 / 重置密码 / 改角色 / 撤销
- 新建 modal: 输 username / display_name / 选 role / 自动生成初始密码 → 显示一次 → 复制按钮
- dad PIN 守门: 进入页面先输 0905 验证 (跟 `/config` 一致)

### 7.5 中间件 (`src/kid_app/auth.py`)
- `get_current_user(request) -> Optional[User]`: 解 Cookie → 验证签名 → 返 user 对象
- `require_role(*roles)` FastAPI Dependency: 未登录 → 302 /login, role 不符 → 403
- 守门范围: 所有 @app.get 页面路由 + 所有写操作 API

---

## 8. 风险清单 (8 条, 必读)

| 风险 | 等级 | 描述 | 缓解 |
|------|------|------|------|
| **R1**: dad 把初始密码微信发错人 | 高 | dad 复制初始密码时可能手抖, 发错群 | dad 后台展示"重置密码"按钮 + 强制 must_change=1 (收密码人首次登录必须改) |
| **R2**: dad PIN 失效 = 全家无法访问 | 高 | dad_pin=0905 唯一, dad 自己也进不来 | 保留 verify-pin 路径不变 + 紧急逃生 (settings 表手动改 dad_pin) |
| **R3**: argon2 hash 在弱机器慢 | 中 | iPad 老设备 CPU 慢, hash 计算 1s+ 用户感觉卡 | argon2 默认 m=65536,t=3,p=4 在 2020 后设备 <100ms, 老设备 200-500ms 可接受 |
| **R4**: Cookie 被 XSS 偷 = 拿到 role | 中 | itsdangerous 签名 Cookie 防篡改, 不能防 XSS 读 | HttpOnly + Secure cookie + config/praise 关键操作 PIN 二次验证 |
| **R5**: mac app WKWebView cookie | 中 | WKWebView 同源 cookie 共享, 验证 web 登录 mac app 能继承 | (a) mac app 启动后验 (b) 不行时 mac app 单独跳 PIN 模式 |
| **R6**: minip whitelist 破坏 | 高 | web_users 表改动影响 mp verify-pin 路径 | web_users 是新表, dad_whitelist 完全不动, 双轨 100% 兼容 |
| **R7**: 老师权限待定 | 低 | dad 8-10 已拍 Q3=A "全看不录", 跟家人同只读 | 接受当前实现, 后续 sprint 加老师专属视图 |
| **R8**: CloudRun 部署 SECRET_KEY 跨容器 | 中 | itsdangerous SECRET_KEY 不一致 = 全部 401 | CloudRun 环境变量统一 (跟 dad_pin 同策略) |

---

## 9. 回滚方案 (3 类)

1. **代码回滚**: 单 PR revert, 不动 DB. web_users 表留着
2. **DB 回滚**: `DROP TABLE web_users` (幂等), 不影响 settings
3. **逃生通道**: dad 在 settings 表手动改 `dad_pin` = 任意值 → 走原 verify-pin 路径绕过新体系 (临时)

---

## 10. 验证 (Verification)

### 10.1 自动化测试
- `tests/test_auth_web.py` (新): 30+ 个 case
  - login (正确密码 / 错密码 / 锁定 / must_change)
  - change-password (旧密码错 / 新密码一致 / 成功后 must_change 清零)
  - logout 清 cookie
  - 角色守卫矩阵 (5 角色 × 6 资源 = 30 组合)
  - cookie 签名/篡改/过期
  - dad PIN 二次验证 (config/users 端点)
- `tests/test_config_users.py` (新): admin 端点 + PIN 守门 + 建/重置/改 role/撤销
- 现有 pytest ~270 passed 必须全绿

### 10.2 手动验证 (dad 必走)
1. 重启 8765, curl `/` → 302 → `/login`
2. dad 输 0905 进 `/config/users`, 建女儿账号 (username=yoyo, role=student, 自动生成初始密码 abc123)
3. dad 复制 abc123 微信发女儿 (mac app / iPad)
4. 浏览器隐身模式打开 url → `/login` → 输 yoyo/abc123 → 强制跳 `/change-password` → 改密 → 进 `/practice`
5. 抽屉显示真实用户名/角色
7. 女儿访问 `/config` → 403
8. dad 走 PIN 0905 → 解锁 `/config/users` → 重置女儿密码 → 女儿下次必须再改密
9. mac app 启动, 验证是否继承 web cookie (大概率行, WKWebView 同源)

### 10.3 部署验证
- CloudRun 部署后, 公网 url `/` 302 → `/login`
- dad 在 `/config/users` 建 5 个测试账号 → 全能登录
- minip 小程序继续能进 (settings.dad_whitelist 100% 不变)

---

## 11. 改动文件清单 (预估)

| 文件 | 改动 | 行数 |
|------|------|------|
| `src/kid_app/auth.py` (新) | get_current_user / require_role / 签名 Cookie / argon2 hash | ~250 |
| `src/kid_app/routes/auth_web.py` (新) | login / logout / change-password / me | ~200 |
| `src/kid_app/routes/config_users.py` (新) | /config/users 端点 + PIN 守门 | ~250 |
| `src/kid_app/app.py` | 所有 GET 页面 + 写操作 API 加 Depends 守卫 | ~150 |
| `src/kid_app/templates/_sidebar.html` | 动态化 + 登出按钮 | ~80 |
| `src/kid_app/templates/login.html` (新) | 登录页 | ~150 |
| `src/kid_app/templates/change-password.html` (新) | 改密页 | ~120 |
| `src/kid_app/templates/config-users.html` (新) | 用户管理页 | ~300 |
| `src/migrate_add_web_users.py` (新) | 建表迁移 (幂等) | ~60 |
| `tests/test_auth_web.py` (新) | 30+ case | ~400 |
| `tests/test_config_users.py` (新) | admin 端点 | ~200 |
| **总计** | **11 文件** | **~2160** |

---

## 12. Sprint 拆分建议 (跟原 plan 一致)

- **Sprint 26081003-A (本期, 3-5 天)**: 数据模型 + auth.py + login/change-password + 4 页守卫 + 抽屉动态化 + /config/users (dad 后台)
- **Sprint 26081003-B (后续, 待定)**: mac app cookie 兼容性深修 / 老师专属视图 / 公开访客 (如有需要)

---

## 13. 拍板题 (Q1-Q3, dad 必答字母回)

### Q1: 拍板 B 方案本地化
- **A — 推荐**: dad 后台手动建账号 + 用户名密码 + 首次改密 + config 管理权限 (本期 plan)
- B — 等 dad 自备域名再走微信扫码 (永久不做)
- C — dad 想 invite link 走自己服务器代理 GitHub (网络问题不一定解决, 不推荐)

**推荐 A**: dad 8-10 已口头拍板, 这里只是 plan 确认. 直接 "Q1=A" 或 "按你的计划走" 启动 Sprint 26081003-A。

### Q2: 访客场景处理 (新增)
- A — **本期砍掉** (dad 8-10 未提访客, 默认不做)
- B — 单独做 (后续 sprint, 走"公开 share link" 或 "PIN 1104 复用")
- C — 本期一起做 (跟 A 一起, 但工作量 +500 行)

**推荐 A**: 访客人数未明 + 没强需求, 等 dad 真正需要时再单独 sprint。

### Q3 (新增 8-10): web 端 cookie 记住登录时长
- **A — 30 天 Cookie (推荐, 默认勾选)**: 关浏览器 30 天内自动登录, 跟 GitHub/Notion 同款
- B — 7 天 Cookie (短一些, 安全更高)
- C — Session Cookie (关浏览器立即失效, 每次都要重输)
- D — 默认 30 天 + checkbox 让用户选

**推荐 A 理由**:
- dad 8-10 反馈 "每次都要输密码会很烦", 30 天最贴近主流 SaaS 体验
- 默认开启, dad 也可手动 "踢出所有设备"
- 安全性可接受 (HttpOnly + Secure + 签名 cookie, 密码明文不入 cookie)

---

## 14. 计划执行顺序

```
Phase 1 (Brief + 拍板) ─── 现在 (Q1 拍板 = A) ─── done with this doc
       │
       ▼
Phase 2A (Sprint 26081003-A 实施)
  ├─ 1. 写 PRD/TECH-SPEC/TEST-PLAN
  ├─ 2. 实现 + 单测
  ├─ 3. PR + 6 问题 review packet
  └─ 4. dad merge → CloudRun deploy → dad 走手动验证 (建女儿账号流程)
       │
       ▼
Phase 2B (后续 sprint, 待 dad 拍)
```

---

## 15. 关联文档

### 历史 sprint 范式参考
- `PRDs/AI-PRD-前后端统一云-phase2实施-260727.md` (云端 MySQL 切流, 已有 schema)
- PR #189 Phase B admin whitelist (mp 端, 本次不复用, 仅参考 UI 风格)
- `.hermes/plans/sprint-26080802-stage-print-polish/plan-*.md` (PRD 范式参考)

### 现状关键事实 (8-10 实查)
- pyproject 依赖已含: `argon2-cffi 25.1.0` + `itsdangerous 2.2.0` + `Werkzeug 3.1.3` → **不引新依赖**
- settings 表 5 个 key: dad_pin / dad_whitelist / active_blindbox_theme / yoyo_portrait_prompt / pin_fail_count:* → **全不动**
- 50+ 个 config 路由已按功能拆 (/config/blindbox /config/practice 等) → `/config/users` 同款新模板

### AGENTS.md 红线
- § 数据策略红线 (云端 MySQL 唯一后端) — 本次 web_users 表新增, 不动现有云端数据
- § 跨项目协作规范 (mp 后端 API 变更同步) — 本次不动 mp API
- § Sprint 收尾 Checklist

---

**状态**: 待启动 (等 dad Q1 拍板 = A)
**下一步**: dad 答 "Q1=A" 或 "按你的计划走" → 启动 Sprint 26081003-A 实施