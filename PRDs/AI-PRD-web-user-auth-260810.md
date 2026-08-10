# AI-PRD-web-user-auth-260810

> dizical web 端用户体系 PRD — 替代当前"裸奔+1 个全局 PIN" 模式
> 分支: `feat/web-user-auth-260810` (已 checkout 空状态)
> Sprint: 26081003 (待启动, 待 dad Q1-Q5 拍板)
> 主文档: `.hermes/plans/sprint-26081003-web-user-auth/AI-PLAN-web-user-auth-260810.md`
> 本文档 = PRD 镜像, 用于 Obsidian 索引

## 摘要

web 端 (iPad Safari + Mac Safari/Chrome + Mac app WKWebView) 当前所有 GET 页面路由 + 大部分写操作 API 裸奔, 公网 URL 拿到就能开界面+录数据. dad 8-10 反馈要做用户体系.

## 调研四套方案

| 方案 | 来源 | 评 |
|------|------|-----|
| **A Invite Token + 公开 Read-only Token** | GitHub org invite, VS Live Share, Ardine | 推荐 (本期 sprint) |
| **A' 微信扫码登录 (cloudbase wx_open)** | 微信开放平台网站应用 OAuth2.0 | 推荐追加 (后续 sprint) |
| B 多用户密码体系 | FastAPI 官方 | 家庭场景 over-engineered |
| C PIN 矩阵扩展 | dizical 现状扩展 | 改动最小但扩展性差 |

## 推荐: A+A' 混合

**本期 sprint 26081003-A**: 全权 agent 跑 A (Invite Token, ~1960 行)
**后续 sprint 26081004**: dad 申请开放平台资质, cloudbase 开 wx_open, agent 集成 A' (~800 行)
**渐进增强**: A' 上线后 invite link 走"微信扫码 + 邀请绑定"双通道, 不破坏 A

## A vs A' (核心决策)

| 维度 | A (Invite Token) | A' (微信扫码) |
|------|-------------------|----------------|
| 实施工作量 | ~1960 行 | ~800 行 (cloudbase 封装大头) |
| dad 工作量 | 0 | 资质审核 5-15 工作日 + 控制台 5 分钟 |
| 家人注册体验 | 点 invite link | 微信扫码 (丝滑) |
| 访客 (guest) | ✓ share link | ✗ 不支持 |
| 审核员 | ✓ PIN 1104 | ✗ 审核员无微信账号 |
| mp/web 账号互通 | ❌ 两套 | ✅ unionid 互通 |

**A' 前置硬门槛**:
- 微信开放平台账号 + 网站应用审核 (5-15 工作日)
- 主体要求: 个体户/企业 (个人不通过)
- 域名要求: HTTPS + ICP 备案 (dizical-prod-* 已备案 ✓)
- unionid 互通: mp + 网站应用绑同一开放平台账号 (否则拿不到 unionid)
- cloudbase 控制台开 wx_open 登录方式 (5 分钟)

**cloudbase 实查 (8-10, mcp queryAppAuth getLoginConfig)**:
- envId `cloud1-d4gfwyvsk1435e2e4`
- 当前登录方式: `usernamePassword: true, email/anonymous/phone: false`, **wx_open 未开**

## 权限矩阵 (5 角色)

| 资源 | dad | 女儿 | 家人 | 老师 | 访客 |
|------|-----|------|------|------|------|
| `/prepare` `/practice` `/achievements` `/badges` | ✓ | ✓ | ✗ | ✓ | ✗ |
| `/report` | ✓ | ✓ | ✓ | ✓ | ✓ (PDF 禁) |
| `/config` `/praise` `/admin/users` | ✓ PIN | ✗ | ✗ | ✗ | ✗ |
| `POST /api/log` | ✓ | ✓ | ✗ | 待定 | ✗ |

## Sprint 拆分 (4 块)

- **26081003-A (3-5 天)**: 数据模型 + auth.py (签名 Cookie) + login-invite + 4 页守卫 + 抽屉动态化
- **26081003-B (3 天)**: 公开 share link + /admin/users + PDF 禁下 + config 守卫
- **26081004 (1-2 周, 等开放平台资质)**: A' 微信扫码 + unionid 互通
- **26081003-C (待定)**: 老师角色完善

## 拍板题 (Q1-Q5, dad 必答字母回)

| # | 问题 | A | B | C/D | 推荐 |
|---|------|---|---|-----|------|
| Q1 | 鉴权方案 | Invite Token + 公开只读 | 多用户密码 | PIN 矩阵 | **A** |
| Q2 | 落地路径 | 只做 Sprint A | A+B 一起 | A+B+C 全做 | **A** |
| Q3 | 老师权限 | 全看不录 | 全看+录 | 本期不做 | **A** |
| Q4 | 公开 link 形态 | 30 天过期+微信分享 | 永久 / 扫码 / 不开放 | | **A** |
| **Q5 (新)** | **微信扫码登录** | **A+A' 混合** | 只做 A | 跳过 A 做 A' | **A** |

**推荐默认全 A**, dad "开始吧 / 按你的计划走" = 全选 A.

**Q5=A 后续 dad 动作**: 立即去 https://open.weixin.qq.com 注册开发者账号 + 创建「网站应用」+ 提交审核 (5-15 工作日跑着, 不卡本期 sprint).

## 风险 (5 + 3 类)

### 本期 sprint (A 路径)
1. dad PIN 失效全家无法访问 → 保留 verify-pin + 紧急逃生 (settings 表手动改)
2. 公开 link 泄露 → 默认 30 天过期 + revoke 按钮
3. Cookie XSS → HttpOnly + Secure + PIN 二次验证
4. mac app WKWebView cookie → 验证同源
5. minip whitelist 破坏 → 双轨运行, mp 路径 100% 不变

### A' 路径独有 (后续 sprint)
6. dad 没开放平台账号 → A' sprint 卡住 (但 A 不受影响)
7. 个人主体拒绝审核 → 需升级个体户/企业资质
8. unionid 不互通 → 重做 mp 端 wx.login 拿 unionid 字段

## 关联

- 历史: PR #189 (7-28) Phase B admin-whitelist (mp 端)
- 历史: `src/migrate_add_dad_whitelist.py`
- 历史: `templates/admin-whitelist.html` (孤儿 UI, 风格参考)
- 历史: `.hermes/plans/sprint-26080802-stage-print-polish/plan-*.md` (PRD 范式)
- cloudbase: `cloud1-d4gfwyvsk1435e2e4` envId, wx_open 未开 (8-10 实查)
- 微信开放平台: https://open.weixin.qq.com (Q5=A' 必访问)
- cloudbase wx_open 文档: https://docs.cloudbase.net/authentication-v2/method/wechat-login
- 微信开放平台 OAuth2.0: https://developers.weixin.qq.com/doc/oplatform/developers/dev/auth/web.html