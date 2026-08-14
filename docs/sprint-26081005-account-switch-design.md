# Sprint 26081005 — 账号切换 + 账号管理入口 3 套实施方案

> **目标**：把 `/config/users`（dad 后台用户管理）接入 sidebar，并提供"账号切换"功能，让女儿/爸爸/妈妈/老师能在网页端快速换人。
> **设计系统**：dizicute（`#FF6B6B` 珊瑚红 + 36px 圆角头像 + 14px 字号 + 240ms 缓动）。
> **前置事实**（来自 A1 现状盘点）：
> - sidebar 现有 5 个 nav + 1 个 footer (呦呦成就殿堂)，**未接** `/config/users` 入口。
> - `/config/users` 路由已在 `src/kid_app/routes/config_users.py:78` 注册并 `app.py:2982` include。
> - 出 API：`POST /api/auth/logout` (`auth_web.py:100`) + `GET /api/auth/me` (`auth_web.py:142`)。
> - 模板里有登出按钮的 CSS（`_sidebar.html:210-227`）和 JS（`_sidebar.html:360-367`），但 **DOM 里没渲染按钮 DOM** — 这是已知小 bug，见各方案风险点。
> - **现有 sidebar 顶部就是页面 header**（没有独立 topbar），方案 D 涉及新增 topbar 模板。
> - sprint 26081004 隐私清理：占位符 = "公开通用 fallback, no real values"，不混真实路径 / 真实 chat_id。
>
> **A2 共识**：主流用 avatar dropdown，但 dizical 现有 sidebar 是"页内模块切换"风格，所以下文把 dropdown 改造量列入"前端 JS 复杂度"对比。

---

## 方案 A — sidebar 顶部加"账号"区（avatar + dropdown）

### 1. 设计描述

把现有 sidebar 顶部那块"硬编码 Y/女儿/学习者"（`_sidebar.html:240-246`）升级为**可点击的 avatar 按钮**，click 后弹出 dropdown，3 个选项：

```
┌─ Sidebar (240px 展开态) ──────────────────┐
│ [≡] toggle                                 │
│ ┌───────────────────────────────────────┐ │
│ │ (●)  女儿  ▼                          │ │ ← 整块可点击
│ │      学习者                          │ │
│ └───────────────────────────────────────┘ │
│ ──── dropdown (展开时) ────               │
│   🔁  切换账号                             │
│   👥  账号管理        (仅 dad 可见)        │
│   ───────────                             │
│   🚪  登出                                │
│ ────────────────────────────────────────  │
│  [🏠] 准备                                 │
│  [✏️] 练习                                 │
│  [📊] 报告                                 │
│  [🏆] 成就                                 │
│  [⚙️] 设置                                 │
│ ────────────────────────────────────────  │
│  [⭐] 呦呦成就殿堂                          │
└───────────────────────────────────────────┘
```

收起态（64px）整块**只有 36×36 avatar 圆**，click 同样弹出 dropdown（iPad 触屏友好）。

### 2. 改动文件清单

| 文件 | 改什么 | 行数 |
|------|--------|------|
| `src/kid_app/templates/_sidebar.html` | 240-246 avatar 区域包一层 `<button>` + dropdown 容器；JS 加 toggle/open/close；新增 CSS（dropdown 定位、hover、阴影） | ~80 行 |
| `src/kid_app/routes/config_users.py` | (无) 路由已就绪 | 0 |
| `src/kid_app/auth.py` | (无) `get_current_user` 已有 | 0 |
| `src/kid_app/static/icons/` | 新增 `user-switch.svg` + `logout.svg` (或沿用已有) | 0 |
| `static/icons/` 同名复用 | 已有 stroke 风格 SVG 可直接用 | 0 |

### 3. 代码量预估

- HTML 模板：~25 行（avatar 按钮 + 3 项 dropdown 内容）
- CSS：~40 行（dropdown 定位 absolute + 阴影 + 圆角 12px + 240ms 缓动）
- JS：~25 行（click outside 关闭 / ESC 关闭 / dad 角色过滤）
- **总计**：约 **90 行** （含 iPad 触屏 tap）

### 4. 验收

```bash
# 1. curl 测 /api/auth/me 没问题
curl -s http://localhost:8765/api/auth/me -b "dizical_session=..." | jq .user.username

# 2. 浏览器: 展开 sidebar → 点 avatar → dropdown 弹出 (3 项, dad 多 1 项)
# 3. 点击"切换账号" → 跳 /login (注: 跟登出合一, 清 cookie 后回 login 页)
# 4. 浏览器: dad 登录 → 看到"账号管理"→ 跳 /config/users (现有 404 风险, 待 A1 确认)
# 5. 收起态 64px: 只剩 36×36 圆 avatar, click 同样弹 dropdown
```

### 5. 风险点

| 风险 | 降级 |
|------|------|
| `/config/users` 路由已注册但模板可能还没渲染（**待 A1 确认** A1 任务做的 `/config/users` 路由测试结果） | 切换前先 `curl -I http://localhost:8765/config/users?pin=0905` 确认 200 |
| 现有 sidebar 顶部 CSS `sidebar-header` 已用 36px 圆，加 dropdown 后展开态 topbar 高度从 56px → 约 220px (dropdown 展开)，可能挤压 nav | 限高：`max-height: 240px + overflow-y: auto` |
| 女儿误触"账号管理"（虽然默认隐藏） | dad role 才渲染，client-side 隐藏，server-side 守门已有 (`_check_dad_or_401`) |
| 现有登出按钮 CSS 已写但 DOM 没渲染（_sidebar.html:360-367 引用 `#sidebarLogoutBtn` 但模板没这个 id） | 顺手在 footer 真实加上 `<button id="sidebarLogoutBtn">` 修这个遗留 bug |
| 隐私占位符：dropdown 不要展示真实 chat_id / iCloud 路径 | dropdown 只展示 `display_name + role_label`，跟 `/api/auth/me` 字段一致 |

### 6. 工作量

**半天**（4-5 小时，含首屏视觉 polish + 现有登出按钮 bug 修复）

### 7. 设计系统一致性 / 移动适配

- **颜色**：avatar 用 `var(--primary, #FF6B6B)` 背景 + 白字，跟现有 sidebar 头像一致；dropdown hover 跟 nav 一样用 `rgba(255,107,107,0.06)`。
- **icon**：复用心相印 / 切换 / 退出 3 个 Lucide-style 24×24 SVG（stroke 1.75）跟现有 nav 同款。
- **spacing**：dropdown 距顶 56px（avatar 高），距左 64px（avatar 中心 + 4px），圆角 12px（跟 `.card` 风格统一）。
- **iPad 触屏**：click outside 用 `pointerdown` 而不是 `mousedown`，iPad Safari 不会误触。
- **mobile (≤1023px)**：sidebar 已经在 mobile 模式下 transform 隐藏，dropdown 跟随 sidebar 一起滑出。

### 8. 跟 sprint 26081004 隐私清理关系

- dropdown 字段完全来自 `/api/auth/me`（返回 `_user_to_public` 公开字段），无密码 hash / 无真实路径 / 无 chat_id，符合隐私占位符规范。
- 不需要在 sidebar 模板里写任何"占位符 fallback"。

### 9. 跟 dashboard 父级 URL 设计

- `/config/users` 路径仍沿用（已有路由 + 共享 `_sidebar` 上下文）。
- 不建议改 `/admin/account`，因为现有 `/admin/whitelist` UI 已被 sprint 26081004 删（改成 JSON API），如果将来要"父级 URL"统一管理，应该先做 `/admin` 整体 rename 一并处理。

---

## 方案 B — sidebar 底部加 3 项（账号管理 / 切换 / 登出）

### 1. 设计描述

把 sidebar 底部现有"呦呦成就殿堂"（`/badges`）那个 footer 升级为**账号条目区**，按从上到下排列：

```
┌─ Sidebar footer (240px 展开态) ────────────┐
│ ────────────────────────────────────────  │
│  [👥] 账号管理        (仅 dad 可见)       │ ← 第 1 项
│  [🔁] 切换账号                              │ ← 第 2 项
│  [🚪] 登出                                  │ ← 第 3 项
│ ────────────────────────────────────────  │
│  [⭐] 呦呦成就殿堂                          │ ← 保留原 footer
└───────────────────────────────────────────┘
```

收起态（64px）下，3 项都是 36×36 圆，**跟 nav item 视觉一致**（圆 + 居中 icon）。

切换账号 = 调 `/api/auth/logout` + 跳 `/login`（不暴露真正"切换意图"，符合隐私）。dad 看到"账号管理 → /config/users"。

### 2. 改动文件清单

| 文件 | 改什么 | 行数 |
|------|--------|------|
| `src/kid_app/templates/_sidebar.html` | 305-314 footer 区域加 3 项 `<a>` + 修 `#sidebarLogoutBtn` 真实按钮（修遗留 bug）；JS 现成 (360-367) | ~30 行 |
| `src/kid_app/routes/config_users.py` | (无) | 0 |
| `static/icons/` | 复用现有 user/settings/logout class 风格 stroke SVG | 0 |

### 3. 代码量预估

- HTML：~15 行（3 个 `<a>` + 翻修 logout 按钮）
- CSS：~5 行（复用现有 `.sidebar-item` 样式，只加 hover/icon spacing 微调）
- JS：~5 行（logout 按钮 id 改名 + onClick handler）— **大量复用现有 sidebar 脚本**
- **总计**：约 **25 行**

### 4. 验收

```bash
# 1. curl 测 logout
curl -X POST http://localhost:8765/api/auth/logout -b "dizical_session=..." -i

# 2. 浏览器: 展开 sidebar → 滚到底 → 看到 3 项 (女儿无"账号管理"; dad 有)
# 3. 切换账号 → 跳 /login
# 4. 登出 → 跳 /login
# 5. 收起态 64px: 3 项都是 36×36 圆 icon-only
```

### 5. 风险点

| 风险 | 降级 |
|------|------|
| 底部密集 4 项可能视觉拥挤 | 跟"呦呦成就殿堂"统一灰色，hover 微微红，分组用 1px border-top 分割 |
| 女儿误触"账号管理"虽然 dad-only 隐藏 | server-side `_check_dad_or_401` 已守门 |
| 隐私：女儿误触"切换账号"频繁换用户 | 视觉上跟"登出"用同色（普通灰），无差异化，切换和登出走同一路径 |
| iPad 触屏 36px 圆刚好满足 44px 最小点击区（差 8px）| 沿用现有 nav 36×36 圆（dizical 现有规范，不破坏） |
| 跟现有 footer 视觉风格冲突 | 复用现有 `.sidebar-footer a` 样式不动 |

### 6. 工作量

**1 小时**（极轻量改动）

### 7. 设计系统一致性 / 移动适配

- **颜色**：完全沿用 `.sidebar-footer a` 灰色 + hover 浅红，跟"呦呦成就殿堂"同组。
- **icon**：复用 stroke 1.75 / 24×24 SVG，跟 5 个 nav 完全一致。
- **spacing**：3 项 + 呦呦成就殿堂 = 4×36 = 144px 高度差，footer 之前 0%。
- **iPad**：跟 nav 同样 36×36 圆，触屏友好。
- **mobile**：跟 sidebar 一起 transform。

### 8. 跟 sprint 26081004 隐私清理关系

- 完全不涉及敏感字段，匿名处理。
- 不需要占位符。

### 9. 跟 dashboard 父级 URL 设计

- 维持 `/config/users` 路径不动。
- 跟方案 A 同样建议：暂时不引入 `/admin/account` 重命名。

---

## 方案 D — 全局顶部 header 加 avatar + dropdown

### 1. 设计描述

新建一个**全局 topbar 模板** `_topbar.html`，在所有页面（sidebar 顶部 toggle 之上）增加一条 56px 横条：

```
┌──────────────────────────────────────────────────────────────┐
│ 🍃 dizical                  [搜索框]    女儿 (●)  ▼           │ ← 56px topbar (新增)
├──────────────────────────────────────────────────────────────┤
│ [≡] [●] 女儿                              │                  │
│  │       │                                 │  page content   │
│  │  5 个 nav                                │                  │
│  │                                         │                  │
│  │  footer: 呦呦成就殿堂                     │                  │
└──────────────────────────────────────────────────────────────┘
```

dropdown 内容跟方案 A 一样（切换账号 / 账号管理 / 登出），但 avatar 是**页面顶部右上**，全局位置。

需要新建 `_topbar.html` + 改动 `base` layout（**待 A1 确认** dizical 是否有 `base.html` 共享模板；从 grep 结果看每个页面是独立模板 + include `_sidebar.html`，没有 base.html，所以要全量改 9 个模板 include topbar）。

### 2. 改动文件清单

| 文件 | 改什么 | 行数 |
|------|--------|------|
| `src/kid_app/templates/_topbar.html` | **新建**：topbar 模板 + avatar + dropdown + CSS + JS | ~120 行 |
| `src/kid_app/templates/_sidebar.html` | 顶部 toggle 跟 topbar 留 56px 空间（margin-top: 56px） | ~5 行 |
| `src/kid_app/templates/config.html` `practice.html` `prepare.html` `report.html` `achievements.html` `badges.html` `config-users.html` `change-password.html` `accept-invite.html` (9 个) | 在 `{% include "_sidebar.html" %}` 之前加 `{% include "_topbar.html" %}` | ~9 行 |
| `src/kid_app/static/dizicute.css` (如果存在) 或各模板 inline | 主页内容 padding-top +56px 避免被遮 | ~10 行 |
| `routes/config_users.py` | (无) | 0 |

### 3. 代码量预估

- 新 `_topbar.html`：~120 行（HTML 25 + CSS 50 + JS 45）
- 9 个模板 include：~9 行
- sidebar margin 调整：~5 行
- 内容 padding 调整：~10 行
- **总计**：约 **145 行**

### 4. 验收

```bash
# 1. curl 测 /api/auth/me
curl -s http://localhost:8765/api/auth/me -b "dizical_session=..." | jq .user.role

# 2. 浏览器: 9 个页面打开 → 顶部 56px 横条都有 → avatar + dropdown
# 3. dad 登录 → dropdown 有"账号管理"→ 跳 /config/users
# 4. 切换账号 → /login
# 5. iPad 触屏 → 顶部 56px 可点 + sidebar 仍可独立折叠
```

### 5. 风险点

| 风险 | 降级 |
|------|------|
| 9 个页面都要包 topbar，遗漏一个页面就有视觉不一致 | 写一个 `tests/test_topbar_present.py` 走遍所有 GET 路由，断言 HTML 含 `_topbar` 标记 |
| 现有 sidebar 顶部 toggle 跟 topbar 视觉冲突（双重 header 错觉） | topbar 只放 avatar，不放 nav；sidebar 仍管页面模块切换，分工清晰 |
| 给女儿学习者造成 double header 干扰 | topbar 文字极简（"dizical" 站名 + 头像就好），不抢戏 |
| 顶部 56px + sidebar 64px = 120px 垂直空间挤压 iPad 横屏 | topbar 缩到 48px，内容 padding-top 48px |
| 现有登出遗留 bug 仍未修 | 顺手在 topbar dropdown 中有一个真正的 logout 按钮 |
| 隐私：topbar 显示 `display_name`，多人共用 iPad 时身份可见 | 跟现在 sidebar 一样显示，无需额外处理 |
| 隐私：topbar 不展示敏感字段 | 严格只读 `/api/auth/me` 字段 |

### 6. 工作量

**1 天**（8 小时，含 9 个页面验证 + iPad 实测 + 视觉 polish）

### 7. 设计系统一致性 / 移动适配

- **颜色**：topbar 背景 `var(--surface, #FFFFFF)` + 底 border `rgba(0,0,0,0.05)`，跟 sidebar 1px 分割风格统一。
- **icon**：复用 stroke 1.75 SVG，跟 sidebar 完全一致。
- **spacing**：topbar 56px 高 + 16px padding，跟 `.sidebar-toggle` 36px 圆 + 16px margin 视觉对齐。
- **iPad 触屏**：56px 横条点击区大 + dropdown relative 定位正确闭合。
- **mobile (≤1023px)**：topbar 仍保留（不跟 sidebar 一起隐藏），因为 avatar 切账号是移动端核心功能。

### 8. 跟 sprint 26081004 隐私清理关系

- topbar 字段完全来自 `/api/auth/me` 公开字段，零敏感。
- 9 个模板 include hardcoded，**无任何占位符需求**。

### 9. 跟 dashboard 父级 URL 设计

- 维持 `/config/users`。
- 顶部 topbar 未来可扩展"显示通知 / 搜索框 / 全局设置"，所以独立模板比 sidebar 顶部块更利于长期演进。

---

## 推荐方案

**推荐方案 A**，理由如下：

1. **最小视觉冲击**：现有 sidebar 顶部 avatar 区域（`_sidebar.html:240-246`）已经预留位置，加 dropdown 即可，不需要新增 topbar 模板（避免 9 个页面 include + 隐私/视觉/test 重复工作）。
2. **跟现有"sprint 26081003 登出按钮 CSS 已写但 DOM 没渲染"自然融合**：方案 A 顺手可以把 logout 按钮 + dropdown 一起补全，把这个遗留 bug 修掉。
3. **dad 角色天然隐藏"账号管理"**：dropdown 用 Jinja2 `{% if current_user.role == 'dad' %}` 渲染，server-side `_check_dad_or_401` 兜底，**双层守门**。
4. **dashboard URL 演进灵活**：未来如果要把 `/config/users` 改名 `/admin/account`，只需改一处路由 + dropdown 链接，不影响 9 个页面。
5. **iPad 触屏体验统一**：dropdown 跟着 sidebar 滑出，不挤占顶部 56px 高度差。

**方案 B 是兜底**：如果 dad 拍板"sidebar 底部 footer 才是账号管理体系"（跟"呦呦成就殿堂"一起作为"次要导航"），方案 B 1 小时搞定，无 dropdown JS 复杂度。

**方案 D 暂不推荐**：除非 dad 想要"未来扩展顶栏（搜索 / 通知 / 全局设置）"，否则 145 行 + 9 个页面改动 = 1 天工作量不划算。**但如果 dad 后续要做"暗色模式 / 多语言切换 / 通知中心"等全局 widget，方案 D 是必要前置**。

---

## 风险总表（跨方案）

| 风险 | A | B | D | 缓解 |
|------|---|---|---|------|
| 现有 `_sidebar.html` 残留：登出按钮 CSS 已写但 DOM 没渲染（360-367 引用 `#sidebarLogoutBtn` 但模板没 id） | ✅ 顺手修 | ✅ 顺手修 | ✅ 顺手修 | 任何方案都加上 `<button id="sidebarLogoutBtn">` 一句修 bug |
| 女儿误触"账号管理" | ✅ Jinja 模板渲染 + server 守门 | ✅ Jinja 模板渲染 + server 守门 | ⚠️ topbar 全局可见，依赖 server 守门 | 双层守门 |
| 跟现有 dizicute 视觉系统冲突 | 🟢 复用现有 sidebar 样式 | 🟢 复用 footer 样式 | 🟡 顶部新组件需适配 dizicute 12px 圆角 | 实施前用 pencil 画一稿 mom-test |
| 隐私占位符（sprint 26081004 审计要求） | ✅ 仅读 `/api/auth/me` 公开字段 | ✅ 仅读 `/api/auth/me` 公开字段 | ✅ 仅读 `/api/auth/me` 公开字段 | 任何方案都做：`grep -E "chat_id|icloud|password" templates/` 验证 |
| 多个用户共用 iPad 时身份混淆 | 🟡 sidebar 收起态 avatar 太隐蔽 | 🟢 footer 文字明显 | 🟢 顶部 56px 文字明显 | 方案 B/D 文字暴露身份更显眼 |
| iPad 触屏 36px 圆 < 44px Apple HIG | 🟡 沿用现有规范 | 🟡 沿用现有规范 | 🟢 顶部 56px 横条 44px+ | dizical 现有规范已接受 36px |
| mobile (≤1023px) sidebar 隐藏后账号入口丢失 | 🟡 sidebar 隐藏后 avatar 跟着藏 | 🟡 同样随 sidebar 隐藏 | 🟢 topbar 始终可见 | 方案 D 移动端更友好 |
| dashboard URL 命名（`/config/users` vs `/admin/account`） | 不动 | 不动 | 不动 | 3 方案都沿用 `/config/users`，未来 rename 单独 sprint |
| 9 个页面遗漏改 | 不涉及 | 不涉及 | ⚠️ 高 | 写 `tests/test_topbar_present.py` 兜底 |
| 现有 sidebar 顶部的 toggle 按钮 vs topbar 双重 header | 不涉及 | 不涉及 | 🟡 视觉困惑 | 实施前用 mom-test 截图比对 |
| 工作量 | 半天 | 1 小时 | 1 天 | dad 拍板时一并选工作量 |
| 调试难度（前端 JS 状态） | 🟡 中（dropdown toggle） | 🟢 极低（无 JS） | 🟡 中（topbar 跨页沟通） | 方案 B 调试最简单 |

---

## 待 A1 确认

1. **`/config/users` 路由在 A1 现状盘点中是否已经过浏览器实测可访问？**（虽然 `config_users.py:78` 路由已注册，但 Jinja 模板 `config-users.html` 是否 200 OK 渲染？）
2. **dizical 是否有共享 `base.html` 模板？**（grep 9 个模板都各自 include `_sidebar.html`，未见 base.html — 这影响方案 D 的工作量预估）
3. **登出按钮 DOM 缺失是不是已知 bug？**（`_sidebar.html:360-367` 引用 `#sidebarLogoutBtn` 但没渲染 — 这是 A1 之后才出现，还是历史遗留？）
4. **当前 footer 跟顶部 avatar 区的设计意图是不是"站名 + 女儿信息"对未来用户体系占位？**（header `Y/女儿/学习者` 是硬编码的 — 是不是 dad 拍板决定"先用真实用户名 + 头像字母"还是保留匿名占位？）

---

**报告字数**：约 2,500 字（含 3 套方案 + 推荐 + 风险总表 + 待确认清单）
**输出位置**：`docs/sprint-26081005-account-switch-design.md`
**下一步**：等 dad 拍板方案 A / B / D，再走 sprint 26081005 实施。
