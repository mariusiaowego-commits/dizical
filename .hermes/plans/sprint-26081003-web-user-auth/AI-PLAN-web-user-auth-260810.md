---
id: 26081003
type: sprint
version: 1.0.0
start_date: 2026-08-10
end_date: TBD
status: 待启动
priority: 高
summary: web 端用户体系 — 角色定义 / 会话鉴权 / 路由守卫 / 抽屉 UI 动态化 / 邀请流
related: ["[[AI-PRD-前后端统一云-phase2实施-260727]]", "[[API-CHANGELOG]]"]
tags: [sprint, dizical, auth, user-system, web]
---

# Sprint 26081003 — Web 端用户体系

**分支**: `feat/web-user-auth-260810` (已 checkout, 跟 main 同 hash, 空状态待动)
**触发**: dad "目前 web 端裸奔, 任何用户在公网拿到 url 就能开界面+录数据"

---

## 1. 背景 / 现状

### 1.1 鉴权现状（裸奔）
- **唯一鉴权端点** `POST /api/verify-pin` (app.py:2810), 只比 settings.dad_pin (现=0905). 不是用户体系, 是「应用密码」
- **所有 GET 页面路由 + 大部分 API 完全无鉴权** (lsof 已验 8765 LISTEN, app.py 全量 @app.get/post 已 grep, 共 40 个路由只有 verify-pin 跟它/permission 内部有 PIN 提示)
- 公网 URL `https://dizical-prod-*.run.tcloudbase.com/...` 谁拿到就能进, 还能 POST `/api/log` 录练习
- 抽屉 `_sidebar.html:215-220` 当前硬编码 `女儿 / 学习者`, 纯展示未注入用户身份

### 1.2 历史 Phase B 残留 (PR #189, 7-28)
- minip 已有完整用户体系: `dad_whitelist` (active openid 列表) + `pending_whitelist` (待审批) + apply-access + approve/deny/remove
- 但全是 wechat openid 模型, 不适用于 web 端浏览器
- `admin-whitelist.html` 模板**孤儿**: app.py 没注册 `/admin/whitelist` 路由 (仅 `config_router` + `badge_workflow_router` + `minip_router`), 页面存在但不可达

### 1.3 dad 角色诉求（本次 sprint 重做）

| 角色 | 数量 | 看 | 录练习 | config / praise / admin |
|------|------|----|--------|------------------------|
| **dad (root)** | 1 | 全 | ✓ | ✓ |
| **女儿** | 1 | 自己的练习 + 报告 | ✓ | ✗ |
| **家人** | N (待定) | 报告 + 成就 | ✗ | ✗ |
| **老师** | 1 (待定) | 全 | ✗ | ✗ (录练习权限未明, 待定) |
| **访客 (guest)** | N (公开 share link) | 仅 report 页 | ✗ | ✗ PDF 禁下载 |

**关键约束**: 不引 SaaS (Auth0/Clerk/Supabase), 不引第三方托管身份. 家庭场景, 全部自托管.

---

## 2. 调研 (X / GitHub / 主流 SaaS 做法)

| 方案 | 来源 | 适用度 | 评 |
|------|------|--------|-----|
| **共享应用 PIN** (现有模式) | dizical 现状 | ❌ | 1 个 PIN 全家共用, 谁录的不可区分, 无法做家人"只看女儿练习" |
| **JWT + 密码** | FastAPI 官方 tutorial | ⚠️ | 适合多用户 SaaS, 但家庭场景过度 (5-10 人无需注册密码) |
| **Magic Link / Passkey** | Clerk, Supabase, supertokens | ⚠️ | 适合邮箱体系, 家庭场景无统一邮箱, 老师/家人不一定有 |
| **Invite Token / One-time link** | GitHub org invite, VS Live Share, Ardine (self-hosted) | ✅ | dad 一键生成 link → 家人点 link 自动建账号 (无密码). 跟"家庭内邀请"语义完全吻合 |
| **Shareable read-only token (公开 link + 限权限)** | GitHub repo public/private, Figma view link | ✅ | 访客公开 link 只能看 report, 跟 dad "访客人数未知, 只看 report 不下 PDF" 完全吻合 |
| **Cookie-based session + 短 token (itsdangerous)** | Flask/Django 默认 | ✅✅ | 自托管, 零依赖, 不引加密库. 跟 PIN-style 演进平滑, 适合 5-10 人家庭 |

### 2.1 推荐三套方案 (供 dad 拍板 Q1)

#### 方案 A — Invite Token + 公开 Read-only Token (推荐)
- **核心**: 区分两类身份:
  - **白名单用户** (家人/女儿/老师): dad 在 web admin 一键生成 `invite_link` (一次性 token, 30 天有效), 点 link 自动建账号 + Cookie session
  - **公开访客**: dad 生成 `share_link` (只读 token, 长期有效), 拿到 link 的人只能看 `/report`, 不能看其他页, 不能下 PDF
- **会话**: itsdangerous 签名 Cookie (Flask 默认同款), 不引 JWT
- **dad (root)**: 保留现有 PIN 模式 (config/praise 走 dad_pin 二次验证) + invite 自己
- **优点**:
  - 跟现有 minip 白名单 (`dad_whitelist` openid) 模式同源, 不引新概念
  - 家庭场景零密码, 老人/小孩友好
  - 公开 link 可随时撤销
  - 不引第三方 SaaS, 自托管
- **缺点**:
  - 要写 invite 邮件/分享 UI (但家庭场景可走"dad 复制 link 微信发给家人")
  - 公开 link 一旦泄露不可控, 但语义就跟 GitHub public repo 一样 (默认信任发放范围)

#### 方案 B — 多用户密码体系 (传统 SaaS 模式)
- **核心**: 传统 username + bcrypt 密码, web 注册, dad 审批
- **会话**: JWT 或 session cookie
- **优点**: 标准, 成熟, GitHub/Notion 同款
- **缺点**:
  - 家庭场景 over-engineered (5-10 人不需要"忘记密码")
  - 老人/小孩记密码痛
  - 跟现有 minip whitelist 双轨
  - dad 要多一个注册 UI + 密码重置流程

#### 方案 C — PIN 矩阵 (现有模式扩展, 最小改动)
- **核心**: 不引入"用户"概念, 沿用 PIN 矩阵 (每角色一个 PIN):
  - dad_pin (现有 0905) = 全权限
  - student_pin = 看 + 录练习
  - family_pin = 只看
  - guest_pin = 公开 link 等同
- **优点**: 改动最小, 1 sprint 内可完工
- **缺点**:
  - 不可识别"谁录的" (审计 log 失效)
  - 家人多 PIN 易混
  - 扩展性差 (加角色要加 PIN)
  - 跟 minip whitelist 不可对齐 (minip 是 openid, web 是 PIN, 两套)

**推荐**: **方案 A** (跟 minip whitelist 同源, 跟家庭场景语义最吻合, 公开 link 解 dad "访客人数未知" 的焦虑)

---

## 3. 目标

### 3.1 目标 (Goal)
给 web 端建一套**白名单用户 + 公开只读访客**的双轨用户体系, 替代当前"裸奔+1 个全局 PIN" 模式.

### 3.2 验收标准 (Acceptance Criteria)
1. **路由守卫**: 所有 `/prepare` `/practice` `/achievements` `/badges` `/config` `/report` + 所有写操作 API (`/api/log` 等) 必须有"未登录或权限不足"守卫 → 重定向到 `/login`
2. **5 个角色** 可识别, 各自走权限矩阵 (见 §4)
3. **invite 流**: dad 在 `/admin/users` 一键生成 invite link (含 role + 过期时间) → 家人点 link 自动建账号 + Cookie session
4. **公开 share link**: dad 生成 `guest` 角色的只读 link, 任何人点 link 都能进 `/report`, 但看不到 `/practice` `/config` 等, 且 report 页 PDF 下载按钮 disabled
5. **抽屉 UI 动态化**: 当前硬编码 `女儿/学习者` 改为读 cookie session 显示真实用户头像/角色
6. **dad PIN 沿用**: 现有 `dad_pin=0905` + `/api/verify-pin` 路径保留, dad (root) 走 PIN 二次验证
7. **minip 兼容**: 现有 minip whitelist (`dad_whitelist` openid) 不破坏, mp 提审路径不变
8. **回滚**: 单 PR 可 revert, 回滚后 = 当前裸奔状态

---

## 4. 权限矩阵 (Design)

| 资源 | dad (root) | 女儿 | 家人 | 老师 | 访客 (guest) |
|------|-----------|------|------|------|--------------|
| `/` 落地 (重定向) | `/practice` (或 dashboard) | `/practice` | `/report` | `/practice` | `/report` |
| `/prepare` (准备页) | ✓ | ✓ | ✗ → /report | ✓ | ✗ |
| `/practice` (练习页) | ✓ | ✓ | ✗ | ✓ | ✗ |
| `/report` (报告) | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/report` PDF 下载 | ✓ | ✓ | ✓ | ✓ | ✗ disabled |
| `/achievements` (成就) | ✓ | ✓ | ✓ | ✓ | ✗ |
| `/badges` (殿堂) | ✓ | ✓ | ✓ | ✓ | ✗ |
| `/config` (设置) | ✓ (PIN 二次验证) | ✗ | ✗ | ✗ | ✗ |
| `/praise` | ✓ (PIN 二次验证) | ✗ | ✗ | ✗ | ✗ |
| `/admin/users` (用户管理) | ✓ (PIN 二次验证) | ✗ | ✗ | ✗ | ✗ |
| `POST /api/log` | ✓ | ✓ | ✗ | ✗ (待定) | ✗ |
| `POST /api/items/{}/archive` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `DELETE /api/practice-sessions/{}` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `PUT /api/items/order` | ✓ | ✗ | ✗ | ✗ | ✗ |

**未明**: 老师是否能录练习? **待 Q3 拍板**.

---

## 5. 数据模型

### 5.1 新表 `web_users` (settings 表升级)
当前 dad_whitelist 是 settings JSON 数组 (openid). web 端需要结构化:

```sql
CREATE TABLE web_users (
  user_id        VARCHAR(64) PRIMARY KEY,     -- nanoid (无 openid 概念)
  role           VARCHAR(16) NOT NULL,        -- dad / student / family / teacher / guest
  display_name   VARCHAR(64) NOT NULL,
  avatar_letter  VARCHAR(1),                  -- 单字母头像 (current 女儿 Y)
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by     VARCHAR(64),                 -- 哪个 user_id 邀请的 (guest = NULL)
  expires_at     DATETIME NULL,               -- guest 公开 link 可设过期 (NULL = 永不过)
  revoked        BOOLEAN DEFAULT 0,
  notes          TEXT
);
```

### 5.2 新表 `web_sessions` (可选, 不引 redis)
- 简单做法: 用 itsdangerous 签名 Cookie (加密+过期+role+user_id), 不存 DB
- 撤销 = 调 `/api/auth/logout` 清 cookie, 或改 dad_pin 强制全员下线
- 高级做法: 加 sessions 表做 server-side revoke, **第一期不做**

### 5.3 新表 `web_invites` (邀请 link 用)
```sql
CREATE TABLE web_invites (
  invite_id      VARCHAR(64) PRIMARY KEY,    -- nanoid
  role           VARCHAR(16) NOT NULL,
  expires_at     DATETIME NOT NULL,         -- 默认 30 天
  used_at        DATETIME NULL,
  used_by_user_id VARCHAR(64) NULL,
  created_by     VARCHAR(64) NOT NULL,      -- dad
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  revoked        BOOLEAN DEFAULT 0
);
```

### 5.4 兼容性
- 现有 `settings.dad_whitelist` (minip openid 列表) **不动**, mp 端继续用
- 现有 `settings.dad_pin` 不动, dad (root) PIN 二次验证沿用
- 现有 `settings.pending_whitelist` 不动
- `web_users` / `web_invites` 是**新增**, 不破坏 mp 路径

### 5.5 迁移
- 新增 `src/migrate_add_web_user_auth.py`:
  - `CREATE TABLE IF NOT EXISTS web_users (...)`
  - `CREATE TABLE IF NOT EXISTS web_invites (...)`
  - 幂等, 跑 1 次
  - 初始化 1 个 dad 用户 (display_name="爸爸", user_id="u_root")

---

## 6. API 端点 (新增)

| Method | Path | 角色 | 用途 |
|--------|------|------|------|
| POST | `/api/auth/login-invite` | 任何人 | 点 invite link 后, 提交 display_name + avatar_letter → 建账号 + Cookie |
| POST | `/api/auth/logout` | 已登录 | 清 Cookie |
| GET | `/api/auth/me` | 已登录 | 返回 {user_id, role, display_name, avatar_letter} (前端抽屉用) |
| GET | `/admin/users` | dad | 列出 web_users + web_invites |
| POST | `/admin/users/invite` | dad (PIN) | 生成 invite link, 返回完整 URL |
| POST | `/admin/users/{user_id}/revoke` | dad (PIN) | 撤销用户 (revoked=1, 强制下次请求重登) |
| POST | `/admin/users/{user_id}/role` | dad (PIN) | 改 role |
| GET | `/share/{share_token}` | 任何人 | 公开访客 link 入口, 设 cookie `role=guest`, redirect 到 `/report` |

**改动现有**:
- `POST /api/verify-pin` (app.py:2810): 保留, 但加注 "=dad (root) 二次验证, 普通登录走 /api/auth/login-invite"
- 所有 GET 页面路由: 加 `Depends(get_current_user)` 守门
- 所有写操作 API: 加 `Depends(require_role(...))` 守门

---

## 7. UI 改动

### 7.1 抽屉 UI (`_sidebar.html`)
- 当前硬编码 `Y / 女儿 / 学习者` 改为 Jinja 模板变量 `{{ user.display_name }}` / `{{ user.role_label }}`
- 角色 label: dad=「管理员」/ student=「学习者」/ family=「家人」/ teacher=「老师」/ guest=「访客」
- 登出按钮 (右下角 footer 新增, 仅已登录显示)

### 7.2 `/login` 页 (新建 `templates/login.html`)
- 邀请 link 自动跳转 (带 invite_token query)
- 公开 share link 自动跳转
- 错误页: invite 失效 → 友好提示 + 申请入口 ("跟 dad 微信说一声")

### 7.3 `/admin/users` 页 (新建 `templates/admin-users.html`)
- 仿 `admin-whitelist.html` 风格 (但用主站色, 不是 dizical-prod-* 那套旧模板)
- 列出当前 web_users + 各自 invite 状态
- dad 一键生成 invite link (弹 modal: 选角色 + 选过期时间 → 生成完整 URL → 复制按钮)
- 撤销 / 改 role 按钮

### 7.4 守门未登录 (middleware)
- 新增 `src/kid_app/auth.py`:
  - `get_current_user(request) -> Optional[User]`: 解 Cookie → 验证签名 → 返回 user 对象
  - `require_role(*roles)` FastAPI Dependency: 未登录 → 302 /login, role 不符 → 403
  - 应用范围: 所有 @app.get("/prepare"/"achievements"/"badges"/"report") + 所有 POST/PUT/DELETE
- 注意 `/` (首页) 行为: 根据 role 重定向到不同落地页 (student/family/teacher → /practice or /report)

---

## 8. 风险清单 (必读)

| 风险 | 等级 | 描述 | 缓解 |
|------|------|------|------|
| **R1**: 现有 dad PIN 失效 = 全家无法访问 | 高 | dad_pin=0905 是当前唯一登录, 一旦改坏 dad 自己也进不来 | (a) 改造完保留 verify-pin 路径不变 (b) dad 走 web_users 表 + 自己的 invite link 重登, PIN 仅二次验证 (c) 紧急逃生: settings 表手动重置 dad_pin |
| **R2**: 公开 share link 泄露 = 陌生人看报告 | 中 | dad 在微信/朋友圈分享, 拿到 link 的人都能看 | (a) 默认 30 天过期 (b) 撤销按钮 + revoke table (d) report 不含敏感信息 (PDF 含个人练习, 禁下) |
| **R3**: Cookie 被 XSS 偷 = 拿到 role | 中 | itsdangerous 签名 Cookie 防篡改, 但不能防 XSS 读 | (a) HttpOnly + Secure cookie (b) 报告页纯静态, 无 user-generated HTML (c) 关键操作 (config/praise) PIN 二次验证 |
| **R4**: mac app WKWebView 拿不到 cookie | 中 | WKWebView 同源策略, web cookies 应该可共享 | (a) 验证 mac app 启动后能继承 web 登录 (b) 必要时 mac app 单独走 PIN 模式 |
| **R5**: minip whitelist 破坏 | 高 | web_users 表改动影响 mp verify-pin 路径 | (a) web_users 是新表, 不动 dad_whitelist (b) 双轨运行, 验证 mp 提审路径 100% 不变 |
| **R6**: 老师角色权限待定 (Q3) | 中 | 老师能否录练习 / 改 config 决定 UI 行为 | dad 拍板 Q3, 再写角色 enum |
| **R7**: 撤销 = 强制所有人下线 | 低 | revoke user → 旧 cookie 仍有效, 要等过期 | 接受 24h 过期延迟; 或加 sessions 表 (本期不做) |
| **R8**: CloudRun 部署 Cookie 跨域 | 中 | itsdangerous SECRET_KEY 跨容器不一致 = 全部 401 | CloudRun 环境变量统一 SECRET_KEY (跟 dad_pin 同策略, 已有 dotenv 管理) |

---

## 9. 回滚方案 (3 类)

1. **代码回滚**: 单 PR revert, 不动 DB. web_users 表留着, 不影响
2. **DB 回滚**: `DROP TABLE web_users, web_invites` (幂等). 不影响 settings 表
3. **逃生通道**: dad 在 settings 表手动改 `dad_pin` = 任意值 → 走原 verify-pin 路径绕过新体系 (临时)

---

## 10. 验证 (Verification)

### 10.1 自动化测试
- `tests/test_auth_web.py` (新): 30 个 case
  - invite link 生成/使用/过期/撤销
  - role 守卫矩阵 (5 角色 × 6 资源 = 30 组合)
  - cookie 签名/篡改/过期
  - dad PIN 二次验证
- `tests/test_routes_admin_users.py` (新): admin 端点 + PIN 守门
- 现有 `tests/test_practice_sessions.py` + 全部 pytest 必须绿 (基线 ~270 passed)

### 10.2 手动验证
1. 重启 8765, curl `/` → 302 → `/login`
2. curl `/login?invite_token=xxx` → 200 (显示建账号表单)
3. 提交 display_name → cookie 设上 → 跳 `/practice` (或 /report)
4. 抽屉显示真实用户名/角色
5. 访问未授权页 → 403
6. dad 走 PIN 0905 → 解锁 `/admin/users` → 生成 invite link
7. 复制 invite link 浏览器隐身模式打开 → 能用
8. 公开 share link 打开 → 只能看 /report, 其他全 403, PDF 下载 disabled

### 10.3 部署验证
- CloudRun 部署后, 公网 url `/` 302 → `/login`
- dad 在 admin 生成 link → 微信发给自己 → 链接能用
- minip 小程序继续能进 (settings.dad_whitelist 路径 100% 不变)

---

## 11. 改动文件清单 (预估)

| 文件 | 改动 | 行数 |
|------|------|------|
| `src/kid_app/auth.py` (新) | get_current_user / require_role / 签名 Cookie | ~200 |
| `src/kid_app/routes/auth_web.py` (新) | /api/auth/login-invite, logout, me, /admin/users 端点 | ~350 |
| `src/kid_app/app.py` | 所有 GET/POST 路由加 Depends 守卫 | ~150 |
| `src/kid_app/templates/_sidebar.html` | 抽屉 UI 动态化 + 登出按钮 | ~80 |
| `src/kid_app/templates/login.html` (新) | 登录页 | ~150 |
| `src/kid_app/templates/admin-users.html` (新) | 用户管理页 | ~250 |
| `src/migrate_add_web_user_auth.py` (新) | 建表迁移 | ~80 |
| `src/kid_app/routes/admin_users.py` (新) | /admin/users 路由 | ~150 |
| `tests/test_auth_web.py` (新) | 30 case | ~400 |
| `tests/test_routes_admin_users.py` (新) | admin 端点 | ~150 |
| **总计** | 10 文件 | **~1960** |

---

## 12. Sprint 拆分建议

大改动建议拆 2-3 个 sprint (各 ≤ 5 天 appetite), 避免一个 PR 太重:

### Sprint 26081003-A: 用户体系核心 (推荐第一期)
- 数据模型 + auth.py (签名 Cookie) + /api/auth/login-invite + /login 页
- 守卫只挂在 `/prepare` `/practice` `/achievements` `/badges` (4 页)
- `_sidebar.html` 动态化
- **不动**: /report (公开), /config (仍走 dad_pin), /admin/users (admin)
- **验收**: dad + 女儿 + 家人 invite 流通, 但访客/admin 还没接
- **估**: 3-5 天

### Sprint 26081003-B: 公开访客 + admin
- /share/{token} 公开 link → role=guest → 落地 /report
- /admin/users 页 (dad 一键生成 invite + revoke + 改 role)
- /report PDF 下载对 guest 禁用
- /config 改走新守卫 (保留 dad_pin 二次验证)
- **估**: 3 天

### Sprint 26081003-C: 老师 + 完善 (待 Q3 拍板)
- 老师角色权限确定
- 老师 UI (可选: 专门 dashboard)
- 撤销策略 (sessions 表可选)

---

## 13. 拍板题 (Q1-Q4, dad 必答)

### Q1: 鉴权方案 (核心)
- A — **方案 A** Invite Token + 公开 Read-only Token (推荐)
- B — 方案 B 多用户密码体系
- C — 方案 C PIN 矩阵扩展 (最小改动)

**推荐 A**: 跟现有 minip whitelist 同源, 家庭场景语义吻合, 公开 link 解访客焦虑

### Q2: 落地路径 (第一期 sprint 范围)
- A — **只做 Sprint 26081003-A** (核心 4 页守卫 + invite 流), 后续 sprint 再做 B/C
- B — A+B 一起做 (一个 PR, ~8 天 appetite, 风险更高)
- C — A+B+C 全做完 (≥10 天, 太重不推荐)

**推荐 A**: 一期一清, 拍板后再启动下一期

### Q3: 老师权限
- A — 老师 = "全看, 不录练习, 不改 config" (跟家人一样的只读 + 老师专属科目视图)
- B — 老师 = "全看 + 录练习" (能代女儿录)
- D — **本期不做老师角色**, 后续 sprint 加

**推荐 A**: 老师场景是观察, 不是改数据; 跟家人同只读权限足够, UI 后面单独加老师专属视图

### Q4: 公开访客 share link 形态
- A — **dad 在 `/admin/users` 一键生成 share link, 微信手发给访客** (默认 30 天过期)
- B — 永久 link (不设过期)
- C — 扫码 (二维码分享)
- D — 不开放公开访客, 全部走 invite

**推荐 A**: 跟 GitHub public repo + Figma view link 同款, 默认 30 天过期, dad 微信分享

---

## 14. 计划执行顺序 (Q 拍板后)

```
Phase 1 (Brief + 拍板) ─── 现在 ──── done with this doc
       │
       ▼ Q1-Q4 拍板
       │
Phase 2A (核心 Sprint)
  ├─ 1. 建 PR-26081003-A 分支 (feat/web-user-auth-260810 已有, 不再开)
  ├─ 2. 写 PRD/TECH-SPEC/TEST-PLAN
  ├─ 3. 实现 + 单测
  ├─ 4. PR + 6 问题 review packet
  └─ 5. dad merge → CloudRun deploy
       │
       ▼ Q 拍是否继续
       │
Phase 2B (公开访客 + admin Sprint)
  └─ 同 Phase 2A 流程
```

---

## 15. 关联文档

- 历史: `PRDs/AI-PRD-前后端统一云-phase2实施-260727.md` (云端 MySQL 切流, 已有 schema)
- 历史: PR #189 Phase B admin whitelist (mp 端雏形, 本次 web 端复用思路)
- 历史: `src/migrate_add_dad_whitelist.py` (settings 表白名单 JSON 模式)
- 历史: `templates/admin-whitelist.html` (孤儿 UI, 风格可参考)
- 历史: `.hermes/plans/sprint-26080802-stage-print-polish/plan-*.md` (PRD 范式参考)
- AGENTS.md § 数据策略红线 / § 跨项目协作规范 / § Sprint 收尾 Checklist

---

**状态**: 待启动
**下一步**: dad 答 Q1-Q4 (字母回) → 启动 Sprint 26081003-A