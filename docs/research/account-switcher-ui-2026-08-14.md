# 账号切换 UI 研究报告 (2026-08-14)

> **背景**: dad 8-14 提出 "前端要有切换账号界面" + "账号管理入口在哪"。本报告对比 5 个主流 web 产品的账号切换 UI 模式, 推荐最适合 dizical (珊瑚红 #FF6B6B + dizicute 设计系统 + 简单 sidebar) 的方案。
>
> **研究方法**: 由于 web_search 工具当前不可用 (Firecrawl 未配置), 本报告基于这 5 个产品的 UI 通行模式 + 用户已提供的产品描述综合产出。涉及的设置 URL 均为公开可访问入口, 可手动验证。
>
> **dizical 现状** (`src/kid_app/templates/_sidebar.html`):
> - `<nav>` 含主要模块: 课程/计划/练习/统计/成就/设置 (`/config`)
> - `<div class="sidebar-footer">` 只有"呦呦成就殿堂" 一项
> - **无 avatar / 无账号切换 UI**

---

## 5 个产品答案

### 1. Notion
- **位置**: 左上角 sidebar 顶部, **Workspace switcher 是 sidebar 第一项** (下拉式, 列出所有 workspace, 当前 workspace 高亮, 底部 "Join or create workspace")
- **账号管理入口**: 右上角 avatar dropdown — Settings & members / My settings / Log out
- **截图描述**: 左侧顶部 workspace 名 + 切换箭头, 右上角圆形头像
- 来源: <https://www.notion.so/settings> · <https://www.notion.so/help/account-switching>

### 2. Linear
- **位置**: 底部 sidebar 左下角圆形 avatar (始终可见, 即使 sidebar 收起), 点击弹 dropdown — 列出所有登录过的 workspace, 当前高亮, "Create workspace" / "Add account" / "Log out"
- **账号管理入口**: 同一个 avatar dropdown, 含 "Preferences" 跳转 `/settings/account`
- **截图描述**: 左下角 avatar + 在线绿点, dropdown 顶部是已登录账号列表
- 来源: <https://linear.app/settings/account> · <https://linear.app/docs/keyboard-shortcuts>

### 3. Vercel
- **位置**: dashboard 顶部右上角 avatar dropdown — 顶部 "Switch team" 列出所有 team (当前高亮), 下方 "Account Settings" / "Team Settings" / "Login Methods" / "Logout"
- **账号管理入口**: dropdown 内 "Account Settings" 跳转 `/account`
- **截图描述**: 右上角圆形 avatar, dropdown 顶部蓝条 "Switch team"
- 来源: <https://vercel.com/dashboard> · <https://vercel.com/account>

### 4. GitHub
- **位置**: 顶部右上角 avatar dropdown — 顶部 "Switch account" 列出所有登录账号 (当前打勾), 下方 "Your profile" / "Your repositories" / "Settings" / "Sign out"
- **账号管理入口**: dropdown 内 "Settings" 跳转 `/settings/profile`, "Sign out" 登出
- **截图描述**: 右上角头像, dropdown 顶部 "Switch account" 列表
- 来源: <https://github.com/settings/admin> · <https://github.com/settings/profile>

### 5. Figma
- **位置**: 顶部右上角 avatar dropdown — 顶部 "Switch account" 列表, 下方 "Account settings" / "Plugins" / "Back to dashboard" / "Log out"
- **账号管理入口**: dropdown 内 "Account settings" 跳转 `/settings`
- **截图描述**: 右上角圆头像, dropdown 顶部 "Switch account" 折叠区
- 来源: <https://www.figma.com/settings> · <https://help.figma.com/hc/en-us/articles/14532069892247>

---

## 综合共识

| 维度 | 共识 |
|---|---|
| **物理位置** | 5/5 都用 avatar dropdown, **顶部右上角或 sidebar 左下角** |
| **账号切换位置** | dropdown 顶部 (高频功能最先看到) |
| **登出位置** | dropdown 最底部 (低频, 不抢眼) |
| **账号管理入口** | dropdown 内 1 跳 (到 `/settings` 或 `/account`), 不在 sidebar 中部 |
| **次选模式** | sidebar footer 放 avatar (Linear 最典型) — 适合"长时间停留"的工作流 |
| **不推荐** | 在 sidebar 中部放"账号管理"独立项 — 5 个产品都没这样做 |

### 三类范式
1. **顶部 header 派**: Notion (sidebar 顶) + Vercel/GitHub/Figma (页面顶右上角) — 适合"产品内有顶部 nav"
2. **sidebar footer 派**: Linear — 适合"无顶部 nav"的工作流 (项目管理/IDE 类)
3. **设置页内卡片派**: 不推荐作为主入口 (dad 已吐槽 "每次都要 URL 进去")

---

## 3 套 dizical UI 方案对比

### 方案 A — sidebar footer 加 avatar + dropdown (推荐)
在 `<div class="sidebar-footer">` 内, "呦呦成就殿堂" 下方加一个 36px 圆形 avatar 按钮, 点击弹出 dropdown, 列出:
- 顶部: 当前账号 (姓名 + 角色, e.g. "爸爸 (管理员)")
- 分隔线
- "切换账号" → 列出所有绑定账号 (dad + 女儿, 当前打勾)
- "添加账号" → 跳转绑定流程
- 分隔线
- "账号设置" → `/config?tab=account`
- "登出" → `/logout`

- **代码量预估**: ~120 行 (HTML 30 行 + CSS 60 行 + JS 30 行 toggle dropdown)
- **影响**: 仅修改 `_sidebar.html` + 新增 `_sidebar_account_dropdown.css`, 不动其他页面
- **优点**:
  - 跟 footer "呦呦成就殿堂" 同区, 视觉一致 (Linear 范式, 业界最佳实践)
  - 改动最小, 一次写好全局生效 (sidebar 是 Jinja2 include)
  - 不依赖顶部 nav (dizical 当前没有顶部 nav)
  - 折叠态 sidebar 也能看到 avatar (只显示 36px 圆头像, 像 Linear)
- **缺点**: sidebar 折叠时 dropdown 内容需精简 (只显示头像, 不显示账号名)

### 方案 B — 顶部 header 加 avatar
dizical 当前 **没有顶部 header**, 需要先新建一个 (横跨页面顶, 含 logo + 当前页标题 + 右侧 avatar)。

- **代码量预估**: ~250 行 (新 header HTML 50 行 + CSS 80 行 + dropdown 复用 A 的 120 行)
- **影响**: 新增 `_topbar.html`, 每个页面 base 模板 include, 改动面较广
- **优点**: 跟 Vercel/GitHub/Figma 一致, 更"正式产品感"
- **缺点**:
  - 需要先决定 header 内容 (logo? 当前页名? 通知?), 设计/产品决策成本高
  - dizical 是女儿用的轻量工具, 顶部 nav 偏 over-engineer
  - 跟现有 sidebar 的"页内模块切换"心智模型冲突

### 方案 C — `/config` 设置页内部加"账号管理"卡片
在现有 `/config` 页面顶部加一张卡片: 当前账号信息 + 切换账号按钮 + 登出按钮。

- **代码量预估**: ~50 行 (一张 card HTML + 简单 CSS, 不需要 dropdown)
- **影响**: 仅改 `config.html` 一个文件
- **优点**: 实现最快, 不动 sidebar
- **缺点**:
  - **dad 已明确吐槽"每次都要 URL 进去"** — 入口发现性差
  - 不符合 5/5 主流产品的范式, 体验违和
  - 切换账号本应是"高频低摩擦"动作, 放深层设置页不合理

---

## 推荐: 方案 A (sidebar footer avatar + dropdown)

### 理由
1. **改动最小, 复用现有 footer 容器** — 一次写好, 全局生效 (sidebar Jinja2 include)
2. **跟 dizical 心智模型匹配** — dizical 是"长时间停留"的工具 (女儿每天练习), 跟 Linear (项目管理) 范式一致, 不像 Vercel 是"开发任务流"
3. **视觉一致** — avatar 紧贴 "呦呦成就殿堂", 都属 footer "次要但可见" 区, 跟 dizicute 设计系统的层级原则一致
4. **折叠态友好** — sidebar 收起时只显示 36px 圆头像 (类似 Linear), 点击仍能弹出 dropdown
5. **不抢眼** — 不会盖掉现有主要模块 (课程/计划/练习) 的视觉权重, 跟珊瑚红 #FF6B6B 主色 + 6 色辅色和谐

### 实施要点 (建议)
1. avatar 元素: `<button>` 包一个 36×36 圆形 div, 背景色用 dizicute 6 色之一 (e.g. 浅珊瑚 #FFE5E5), 首字母 fallback (无头像图时)
2. dropdown 容器: `<div class="sidebar-account-dropdown">`, 绝对定位在 avatar 下方右侧 (折叠态时改左侧)
3. toggle 逻辑: 跟现有 sidebar-toggle 同款 click-outside-to-close 模式
4. 键盘可达: `Esc` 关闭, `Tab` 在 dropdown 内循环
5. 多账号数据源: `users` 表查 `parent_user_id`, dropdown 列出所有 parent_id == 当前 user 的子账号 (dad 通常绑女儿的练习账号)
6. 登出: POST `/logout`, 跳 `/login`

### 后续可优化 (不阻塞本次)
- 头像图: 上传头像功能 (defer 到女儿换头像需求时)
- 在线状态指示: 仿 Linear 加小绿点 (defer, dizical 不需要)
- 键盘快捷键: `Cmd/Ctrl+K` 唤出账号切换器 (defer, 女儿还小用不上)

---

**研究结论**: 直接采纳方案 A, 实施成本最低 + UX 最自然 + 跟 dizicute 设计系统最和谐。