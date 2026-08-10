# AI-PRD-web-user-auth-260810

> dizical web 端用户体系 PRD — 替代当前"裸奔+1 个全局 PIN" 模式
> 分支: `feat/web-user-auth-260810` (已 checkout 空状态)
> Sprint: 26081003 (待启动, 待 dad Q1-Q4 拍板)
> 主文档: `.hermes/plans/sprint-26081003-web-user-auth/AI-PLAN-web-user-auth-260810.md`
> 本文档 = PRD 镜像, 用于 Obsidian 索引

## 摘要

web 端 (iPad Safari + Mac Safari/Chrome + Mac app WKWebView) 当前所有 GET 页面路由 + 大部分写操作 API 裸奔, 公网 URL 拿到就能开界面+录数据. dad 8-10 反馈要做用户体系.

## 调研结论 (3 套方案对比)

| 方案 | 来源 | 评 |
|------|------|-----|
| **A Invite Token + 公开 Read-only Token** | GitHub org invite, VS Live Share, Ardine | 推荐 |
| B 多用户密码体系 | FastAPI 官方 | 家庭场景 over-engineered |
| C PIN 矩阵扩展 | dizical 现状扩展 | 改动最小但扩展性差 |

## 推荐: 方案 A

**核心**: 区分两类身份
- 白名单用户 (家人/女儿/老师): dad 一键生成 invite link, 点 link 自动建账号 + 签名 Cookie
- 公开访客: share link 拿到的任何人都能进 `/report`, PDF 下载禁用

## 权限矩阵 (5 角色)

| 资源 | dad | 女儿 | 家人 | 老师 | 访客 |
|------|-----|------|------|------|------|
| `/prepare` `/practice` `/achievements` `/badges` | ✓ | ✓ | ✗ | ✓ | ✗ |
| `/report` | ✓ | ✓ | ✓ | ✓ | ✓ (PDF 禁) |
| `/config` `/praise` `/admin/users` | ✓ PIN | ✗ | ✗ | ✗ | ✗ |
| `POST /api/log` | ✓ | ✓ | ✗ | 待定 | ✗ |

## Sprint 拆分

- **Sprint 26081003-A** (3-5 天): 数据模型 + auth.py (签名 Cookie) + login-invite + 4 页守卫 + 抽屉动态化
- **Sprint 26081003-B** (3 天): 公开 share link + /admin/users + PDF 禁下 + config 守卫
- **Sprint 26081003-C** (待定): 老师角色完善

## 拍板题 (Q1-Q4, dad 必答字母回)

- Q1: A Invite Token / B 多用户密码 / C PIN 矩阵 — **推荐 A**
- Q2: 只做 A sprint / A+B 一起 / A+B+C 全做 — **推荐 只做 A**
- Q3: 老师 = 全看+不录 / 全看+录 / 本期不做 — **推荐 全看+不录**
- Q4: 公开 share link 形态 (30 天过期+微信分享 / 永久 / 扫码 / 不开放) — **推荐 30 天过期+微信分享**

## 风险 (5 类)

1. dad PIN 失效全家无法访问 → 保留 verify-pin 路径 + 紧急逃生 (settings 表手动改)
2. 公开 link 泄露陌生人看报告 → 默认 30 天过期 + revoke 按钮
3. Cookie XSS 偷 → HttpOnly + Secure + PIN 二次验证
4. mac app WKWebView 拿不到 cookie → 验证同源策略
5. minip whitelist 破坏 → 双轨运行, mp 路径 100% 不变

## 关联

- 历史: PR #189 (7-28) Phase B admin-whitelist (mp 端, 本次 web 端复用思路)
- 历史: `src/migrate_add_dad_whitelist.py` (settings JSON 白名单模式)
- 历史: `templates/admin-whitelist.html` (孤儿 UI, 风格可参考)
- 历史: `.hermes/plans/sprint-26080802-stage-print-polish/plan-*.md` (PRD 范式)