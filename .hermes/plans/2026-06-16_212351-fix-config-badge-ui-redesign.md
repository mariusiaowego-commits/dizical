# config-badge.html 改造 (portal 删 + UI 单列堆叠 sophon.at 风格)

> **For Hermes:** 用户 2026-06-16 21:08 ack.
> 两个独立改动, 1 个 PR, 不动 production db:
>
> 1. **Portal 状态卡 删** — `/config/api/portal/status` 端点不存在 (V2 era 旧接口不用了), JS 永远返红, 误报. 改前端 JS 删这段代码 + 删 HTML 卡.
> 2. **表单 UI 改 sophon.at 风格单列堆叠** — 当前 4 字段挤一行 (类型标签/Category/解锁策略/考出时间), 字段宽挤/label 截断. 改成大间距垂直堆叠.

## 安全约束

**绝不**:
- ❌ 不动 db (production `data/dizi.db`)
- ❌ 不动 achievement_stats / achievement_badges 表
- ❌ 不跑 `migrate_*.py` (无需要)
- ❌ 不动 `tests/conftest.py` schema (跟本 PR 无关)
- ❌ 不动任何其他 route (config.py / prepare.py / badge_workflow.py)
- ❌ 不动 achievement_definitions.py / badge_db.py

**只动**:
- ✅ `src/kid_app/templates/config-badge.html` (HTML + CSS + JS, 1 个文件)
- ✅ 重启 service (清 `_BADGE_URL_CACHE` 60s cache)

## 步骤

### Step 1: worktree 隔离 (预防 6-16 事故模式)
- 新 worktree `dizical-8771` 分支 `fix/config-badge-ui-redesign` 基于 `origin/main` (e2ae214e)
- 验证 production db 没动

### Step 2: 删 portal 状态卡
- 删 HTML: `<div class="portal-card..." id="portalCard">...</div>` (config-badge.html 第 857 行附近)
- 删 CSS: `.portal-card`, `.portal-light`, `.portal-card.status-ok/red/gray`, `.portal-light.green/red/yellow` 等
- 删 JS 函数: `loadPortalStatus()`, `updatePortalCard()`, `loadPortalProfiles()` + JS 启动时调用
- 删 JS 变量: `portalVerified`, `portalLight`, `portalCard`, `portalValue`, `portalDetail`, `portalError`, `portalProfiles`
- **不动** `/config/api/badge/discoveries` (用户已用)

### Step 3: 表单 UI 改 sophon.at 风格单列堆叠
- CSS 改 `.v21-row { display: block; }` (从 flex 改单列)
- CSS 加 `.v21-field { margin-bottom: 22px; }` (大间距)
- CSS input/select: `padding: 14px 16px; border-radius: 14px; font-size: 15px` (dizicute 大点击区)
- CSS label: `font-size: 15px; font-weight: 600` (大字号)
- CSS small (helper): `font-size: 13px; line-height: 1.5` (易读)
- HTML Row 1: `id` + `name` 改 2 行 (不再同行)
- HTML Row 2: `type` + `category` + `unlock_strategy` + `achieved_at_override` 改 4 行 (不再同行)
- HTML Row 3: `display_format` + `sort_order` 改 2 行 (不再同行)
- HTML Row 4: `placeholder` + `zh_story` 仍 v21-field-wide (单行, 不动)
- HTML Row 5: `cond_text` 单行 (不动)
- HTML Row 6: `unlocked_template` 等高级字段不动
- HTML Row seasonal (seasonal_type): 单行 (不动)

### Step 4: 视觉自查 (3 步)
- 浏览器 `http://localhost:8765/config/badge` 截图
- 对比 sophon.at 大间距 + 单列风格
- 没出现字段挤一行 / label 截断

### Step 5: 端到端功能自查 (确认没破)
- 访问 `/config/badge` 200 OK
- 表单填 "test_redesign_xyz" → 提交 → 应进 draft (跟之前一样)
- 浏览器 console 无 error
- service log 无 5xx

### Step 6: pytest 验证
- 全量 pytest 268+ passed (UI 改动不影响 backend, 但跑确认没破 schema test)

### Step 7: commit + push + PR
- 1 commit, 1 PR
- PR body 列改动 + 自查截图
- 等 dad review merge

### Step 8: merge 后 sync main

## 已知风险 + 缓解

| 风险 | 缓解 |
|---|---|
| worktree 跟 production db 共用 → 误清 db (6-16 事故模式) | 本 PR 不动 db; conftest 已隔离 (PR #104); 不跑 migrate / restore 脚本 |
| portal 卡删了, 别处还引用 `portalVerified` 变量 | grep 全 file, 验证 `portalVerified` 没被引用 |
| UI 单列改后, 必填字段 `<span class="v21-req">*</span>` 渲染异常 | 检查所有 label 结构 |
| modal/preview/draft 流程被破坏 | JS submit 函数 `v21SubmitDraft()` 不动 (它调 `/api/badge/draft`) |
| service restart 后 `_BADGE_URL_CACHE` 60s 旧缓存 | 按 AGENTS.md 重启流程 |

## 文件改动

| 文件 | 改动 |
|---|---|
| `src/kid_app/templates/config-badge.html` | 删 portal 卡 (~30 行 HTML + ~50 行 CSS + ~60 行 JS), 改 form layout (~40 行 CSS), 改 row 结构 (~30 行 HTML) |

## 验收

- 浏览器打开 `/config/badge` 视觉跟 sophon.at 一致 (大间距垂直堆叠)
- 没有"Portal 不可用"红色卡
- 字段不再挤一行 / label 不截断
- pytest 268+ passed
- production db achievement_stats 11 行不变 (不增不减)

执行:
    cd /Users/mt16/dev/dizical-8771
    # 改 config-badge.html
    # 重启 service 测试
    # pytest
    # commit + push + PR