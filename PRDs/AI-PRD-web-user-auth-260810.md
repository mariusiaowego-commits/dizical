# AI-PRD-web-user-auth-260810 (v2 — B方案本地化)

> dizical web 端用户体系 PRD v2 — dad 8-10 拍板: 多密码账号体系全本地
> 分支: `feat/web-user-auth-260810` (已 checkout 空状态)
> Sprint: 26081003 (待启动, 待 dad Q1=A 拍板)
> 主文档: `.hermes/plans/sprint-26081003-web-user-auth/AI-PLAN-web-user-auth-260810.md`
> 本文档 = PRD 镜像, 用于 Obsidian 索引

## 摘要

web 端 (iPad Safari + Mac Safari/Chrome + Mac app WKWebView) 当前所有 GET 页面路由 + 大部分写操作 API 裸奔, 公网 URL 拿到就能开界面+录数据. dad 8-10 反馈要做用户体系.

## dad 8-10 拍板变更

**否决**:
- ❌ 方案 A Invite Token (GitHub 模式) — 家里人**网络不通** (GitHub 翻墙问题)
- ❌ 方案 A' 微信扫码 — 要**自备已备案域名** + 个体户/企业主体, dad 用的是**腾讯送的 run.tcloudbase.com 子域名**, **无法备案**

**拍板**:
- ✅ **多密码账号体系, 全本地**
- ✅ dad 在 config 后台**手动建账号** (输用户名 + 自动生成初始密码 + 选角色)
- ✅ 微信手发初始密码给家人, 首次登录强制改密
- ✅ dad 在 config 后台**管理用户 + 权限分配**
- ✅ **30 天 cookie 记住登录** (dad 反馈"每次都输很烦") — 默认勾选, dad 可手动踢出某用户所有设备

**mp 微信端**:
- ✅ **完全不动** — 沿用现有 7-28 PR #189 机制 (wx.login 静默拿 openid → 比对 dad_whitelist → 自动加白)
- 微信生态天然身份绑定, **无需密码**

## 砍掉 vs 保留

| 砍 | 留 |
|----|----|
| Invite Token / 公开 Share Link / 微信扫码 | 多密码账号体系 |
| 自助注册 (dad 不开放) | dad 后台手动建账号 |
| 访客 (guest) 场景 | 用户名 + 密码登录 |
| | 首次登录强制改密 |
| | dad (root) 走原 PIN=0905 |
| | 抽屉 UI 动态化 |

## 权限矩阵 (5 角色, 访客本期砍)

| 资源 | dad | 女儿 | 家人 | 老师 |
|------|-----|------|------|------|
| `/prepare` `/practice` `/achievements` `/badges` | ✓ | ✓ | ✗ | ✓ |
| `/report` (PDF 下载) | ✓ | ✓ | ✓ | ✓ |
| `/config` `/praise` `/config/users` | ✓ PIN | ✗ | ✗ | ✗ |
| `POST /api/log` | ✓ | ✓ | ✗ | ✗ |

## 拍板题 (Q1-Q3, dad 必答字母回)

| # | 问题 | A | B | C/D | 推荐 |
|---|------|---|---|-----|------|
| Q1 | 拍 B 方案本地化 (本期 plan) | 推荐 | 等域名再做扫码 | invite 自建代理 | **A** |
| Q2 | 访客场景 | 本期砍 | 单独 sprint | 一起做 | **A** |
| **Q3 (新)** | **web cookie 记住登录** | **30 天 (默认勾选)** | 7 天 / session (每次重输) / checkbox 自选 | | **A** |

**推荐默认全 A**, dad "开始吧 / 按你的计划走" = 全选 A.

**Q3=A 关键点**: 不存密码明文到 cookie, 用 itsdangerous 签名 cookie 存 {user_id, role}, HttpOnly+Secure+SameSite=Lax. dad 在 `/config/users` 给某用户点 "踢出所有设备" 可强制重登.

## 风险 (8 条)

1. dad 把初始密码微信发错人 → 重置密码按钮 + must_change 强制
2. dad PIN 失效全家无法访问 → 保留 verify-pin + 紧急逃生
3. argon2 hash 在弱机器慢 → 现代设备 <100ms, 老设备 200-500ms 可接受
4. Cookie XSS → HttpOnly + Secure + PIN 二次验证
5. mac app WKWebView cookie → 验证同源, 不行时单独跳 PIN
6. minip whitelist 破坏 → web_users 是新表, mp 100% 不变
7. 老师权限待定 → dad 拍过 A "全看不录", 后续加专属视图
8. CloudRun SECRET_KEY 跨容器 → 环境变量统一

## Sprint 拆分

- **26081003-A (本期, 3-5 天)**: 数据模型 + auth.py + login/change-password + 4 页守卫 + 抽屉动态化 + /config/users (dad 后台)
- **26081003-B (后续, 待定)**: mac app cookie 兼容深修 / 老师专属视图

## 关联

- 历史: PR #189 (7-28) Phase B admin-whitelist (mp 端, 仅参考 UI 风格)
- 历史: `templates/admin-whitelist.html` (孤儿 UI, 风格参考)
- pyproject 依赖已含: `argon2-cffi` + `itsdangerous` + `Werkzeug` → **不引新依赖**
- settings 表 5 个 key (dad_pin/dad_whitelist/active_blindbox_theme/yoyo_portrait_prompt/pin_fail_count:*) → **全不动**
- 50+ config 路由按功能拆 (/config/blindbox 等) → /config/users 同款新模板