---
id: 26081003
type: sprint
version: 3.0.0
start_date: 2026-08-10
end_date: 2026-08-12
status: 进行中
priority: 高
summary: web 用户体系 (B 方案本地化) — dad 后台建账号 + 首次改密 + 30 天 cookie + config 管理权限
related: ["[[.hermes/plans/sprint-26081003-web-user-auth/AI-PLAN-web-user-auth-260810]]", "[[PRDs/AI-PRD-web-user-auth-260810]]"]
tags: [sprint, dizical, auth, user-system, web, password]
---

# Sprint 26081003 — Web 用户体系

**分支**: `feat/web-user-auth-260810`
**拍板**: dad 8-10 全选 — Q1=A Q2=A Q3=A
**周期**: 2026-08-10 → 2026-08-12 (3 天 appetite)

## 任务进度

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| 1 | plan v3 拍板 (Q1/Q2/Q3 全 A) | ✅ | commit `4784883` |
| 2 | PRD/TECH-SPEC/TEST-PLAN 写完 | ✅ | 本 sprint doc |
| 3 | 建表迁移 src/migrate_add_web_users.py | ⏳ | 进行中 |
| 4 | src/kid_app/auth.py (签名 cookie + 守卫) | ⏳ | 进行中 |
| 5 | src/kid_app/routes/auth_web.py (login/logout/change-pw/me) | ⏳ | |
| 6 | src/kid_app/routes/config_users.py (dad 后台) | ⏳ | |
| 7 | 路由守卫 app.py 全量 | ⏳ | 4 页 + 写操作 API |
| 8 | templates/login.html + change-password.html | ⏳ | |
| 9 | templates/_sidebar.html 动态化 | ⏳ | |
| 10 | templates/config-users.html (dad 后台) | ⏳ | |
| 11 | tests/test_auth_web.py + test_config_users.py | ⏳ | 30+ case |
| 12 | 本地验证 (dad 手动走流程) | ⏳ | |
| 13 | PR + 6 问题 review packet | ⏳ | |
| 14 | merge + CloudRun deploy | ⏳ | |
| 15 | closeout (3-1-1) + Obsidian Base 更新 | ⏳ | |

## Sprint 回顾 (完成后填)
- 实际耗时:
- 关键踩坑:
- 1 件事学到的:

## Commit + PR
- Commit: TBD
- PR: TBD