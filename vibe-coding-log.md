# dizical vibe coding log

## 2026-05-24 — 每日打卡盲盒功能

### 功能设计
- 基于stage周期的7天动态徽章系统，用"随机性"对抗每日打卡疲劳
- 每天展示当天的盲盒badge（220x220大图），打卡后解锁彩色版，未打卡显示灰化版
- 7张OK哥赶海主题badge（河豚→螃蟹→章鱼→海螺→宝箱→魔鬼鱼→神龙）
- 根据打卡天数触发不同强度的GSAP动效和confetti特效

### 技术实现
- `app.py`: 新增 `_daily_blindbox_html()` 函数，基于stage_start/stage_end计算
- `achievement_definitions.py`: 修改daily类型计算逻辑，支持stage周期
- `achievements.html`: 新增卡片区域+CSS样式+JS动效
- 图片: 7张badge图存放在 `static/badges/daily_checkin_1-7.png`

### MRD来源
- 文档: `/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/PRDs/mrd-每日打卡盲盒.md`
- 技术方案: `/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/PRDs/tech-spec-每日打卡盲盒.md`

### Git
- 分支: `feat/badge-design-dev`
- commit: `90ab086`
- 已推送到GitHub

---

## 2026-05-24 — 练习记录数据修正

### 变更
- 删除误记到 2026-05-24 的错误记录（含未知科目 1338）
- 修正 2026-05-23：原 1337:45 → 正确 1338:45（回课）

### 发现的问题
- `dizical practice log` 记录时过滤已归档科目(is_archived=1)，导致归档科目显示为 "?"，但数据库有正确记录——bug 待修

---

## 2026-05-22 — 表扬页改为配置台入口

### 变更
- `/praise` 路由重定向到 `/config`
- 底部导航栏「表扬」改为「配置」（achievements/practice/report 三页）
- 配置台入口现在位于底部导航栏最后一个位置

### commit
- `da6174e` - refactor: 表扬页改为配置台入口

---

## 2026-05-22 — 练习科目配置管理台 Phase 1 MVP

### 需求
将 CLI TUI 的 practice_config 功能迁移到 Web 界面，家长在 iPad/Mac 上直接操作练习科目配置。

### 架构设计
- **页面路由**: `/config` 配置主页 + `/config/practice` 练习科目配置页
- **API 命名空间**: `/config/api/practice/*`，可扩展到通知配置、缴费配置
- **UI 布局**: Master-Detail（左侧大科目列表 260px + 右侧小科目列表自适应）
- **PIN 验证**: 复用现有 `/api/verify-pin` 端点

### 文件清单
- `src/kid_app/routes/config.py` - 配置路由模块（14KB，API + 页面路由）
- `src/kid_app/templates/config.html` - 配置主页模板（11KB，卡片列表 + PIN 验证）
- `src/kid_app/templates/config-practice.html` - 练习科目配置页模板（37KB，Master-Detail 布局）

### API 端点
- `GET /config/api/practice/categories` - 获取所有大科目（含统计）
- `POST /config/api/practice/categories` - 新增大科目
- `PUT /config/api/practice/categories/{id}` - 改名/排序
- `DELETE /config/api/practice/categories/{id}` - 删除大科目（清空归属）
- `PUT /config/api/practice/categories/order` - 批量排序
- `GET /config/api/practice/items` - 获取所有小科目
- `POST /config/api/practice/items` - 新增小科目
- `PUT /config/api/practice/items/{id}/rename` - 改名小科目
- `DELETE /config/api/practice/items/{id}` - 删除小科目
- `PUT /config/api/practice/items/{id}/category` - 设置归属
- `POST /config/api/practice/items/{id}/archive` - 归档
- `POST /config/api/practice/items/{id}/unarchive` - 取消归档

### UI 特性
- GSAP 入场动画（back.out 刹车感 + stagger）
- 下拉菜单选择归属（点击外部自动关闭）
- 行内编辑科目名称（blur/Enter 保存，Escape 取消）
- 搜索过滤（实时过滤 + 自动展开匹配分组）
- Toast 提示（成功/错误反馈）

### 可扩展性设计
- 配置主页预留通知配置、缴费配置模块入口
- API 命名空间 `/config/api/*` 可扩展
- 组件可复用（手风琴、行内编辑、下拉选择）

### 测试结果
- `/config` 页面 200 OK
- `/config/practice` 页面 200 OK
- 大科目选择功能正常
- 搜索过滤功能正常
- 归属变更功能正常

### commit
- 待提交

---
## 2026-05-22 — 三栏布局 grid overflow 修复 + box-shadow

### Bug
- `grid-template-columns: 22% 44% 34%` + `gap: 8px` 溢出 16px，右栏被切
- 根因：CSS Grid 百分比不含 gap 计算，`100% + gap` 总宽超容器

### 修复
- fr 单位 `0.656fr 1.316fr 1.014fr`，自动扣 gap
- 三栏加 `box-shadow: 0 2px 8px rgba(0,0,0,0.10)`

### 另记
- SSH proxy `127.0.0.1:6789` 挂了导致 `git push origin` 失败，改 pushurl HTTPS 绕过
- git remote set-url 对已有 remote 的 pushurl 不生效，需 `git config --local remote.origin.pushurl`

## 2026-05-21 PM — timer submitPractice double-click bug 修复

### Bug 现象
提前结束（finishEarly）或自然结束点打卡后没记录，两次快速点击导致打卡没成功。

### Root Cause
1. `submitPractice()` 无防重放标志，两次快速点击时两个 fetch 并发
2. `save_daily_practice` 用 `INSERT OR REPLACE`，第二个请求的 `items=[]` 覆盖第一个的记录

### Fix
1. `practice.html` — `submitPractice` 加 `submitting` 标志（global bool），首次点击设 true，fetch 返回后设 false，期间所有调用 return
2. `database.py` — `append_behavior_log` 的 `ON CONFLICT` 注释修正

### Commit
- `c303e5b` → branch `fix/timer-submit-race` → **已合并 main**

### 教训
打卡类写操作必须有防重放 guard。

## 2026-05-21 PM — badges页图片URL补漏

### `BADGE_FILES` 漏了 3 个 badge
- **Bug**: `badges_page()` 的 `BADGE_FILES` 漏了 `total_60`/`week_champ`/`full_month`，导致这 3 个 badge 在 badges 页 fallback 到 `medal_badge.png`
- **根因**: 两处 badge URL 映射（achievements页 BADGE_URLS / badges页 BADGE_FILES）需同步维护，添加新 badge 时容易漏掉其中一处
- **修复**: `app.py` 第1046行补入 3 个 key，`6e6ba14` push to main
- **教训**: 添加新 badge 时同步检查两处映射字典，下次加 badge 记得：`/achievements` 的 `BADGE_URLS` + `/badges` 的 `BADGE_FILES`
- **服务进程陷阱**: kill 旧进程后需 `lsof -i :8765` 确认新进程（服务跑在 Python 3.12）

## 2026-05-21 (Thu) — modal-box 重构 + badges页空白Bug修复

### modal-box 优化（iPad mini 7 横屏）
- **宽度**：310px → 420px → 580px（用户要求更宽）
- **图片**：156px → 200px
- **文字**：modal-desc 16px → 19px
- **关闭按钮**：恢复右上角圆形（用户不喜欢底部半圆悬挂样式）
- **iPad landscape 适配**：`overflow: auto` + `padding: 16px` + 图片 200px，总高度控制在 420px 以内

### badges.html 页面空白 Bug
- **现象**：Chrome DevTools Elements 面板 `<body>` 无子元素，页面只有背景色
- **根因**：`</style>` 标签丢失，导致后续所有 HTML 内容被浏览器当成 CSS 文本渲染
- **错误过程**：多次 patch 改 HTML 时，每次 patch 追加到文件而不是覆盖，产生多个 `<style>` 块、`</style>` 跑到 body 内、重复 CSS 规则
- **修复**：重写 badges.html 的 CSS/HTML 边界部分，确保 `</style>` 在 `</head>` 前
- **教训**：HTML 模板结构乱了，curl 验证正确但浏览器显示空白，难以调试

### achievements.html 同样 </style> 丢失
- **根因**：`</style>` 缺失导致 openModal 变成 CSS 文本，JS 解析出错
- **修复**：补上 `</style>` 闭合标签

### 调试方法
- `grep -n "<style\|</style\|</head>\|<body>" file.html` — 定位标签顺序
- `curl | grep -n "modal-overlay\|</head>\|<body>"` — 验证服务端渲染 HTML
- `browser_console` 执行 `document.body.innerHTML.length` — 确认 body 有无内容
- `browser_console` 执行 `typeof openModal` — 确认 JS 函数是否定义

### commit
- 未 push

## 2026-05-21 (Thu) — badges页tab分离 + grade名称description更新 + workflow修复

### 本次完成
- **页签分离**: badges页 milestone/seasonal 双tab，按已解锁排序
- **locked蒙版**: saturate 0.25→0.3, brightness 0.9→0.95（更透明）
- **type字段Bug**: 入库脚本 `add_badge_early.py` 把 `type` 写成 `'achievement'`，应为 `'突破'`
- **DB修正**: 3个新badge type='突破'；10个grade name+description全更新
- **Workflow修复**: `docs/badge-workflow.md` 步骤1+步骤4加字段含义注释
- `312cd38` push to main

### 根因分析
- 入库脚本照着 workflow 模板写，模板第3个值硬编码 `'achievement'`（SQL关键字），入库脚本没改直接用
- 教训：workflow 模板里硬编码占位符容易被直接复制粘贴使用，需加注释警示
- 字段含义混淆：`type`=前端中文标签，`category`=数据类型(milestone/seasonal)

## 2026-05-20 (Wed) PM — 闻鸡起舞系列 badge × 3 新增

### 本次完成
- **新增 3 个 seasonal badge**：
  - `early_riser` 闻鸡起舞：当月首次打卡早于 20:00
  - `little_chick_commander` 小鸡指挥官：当月首次打卡早于 17:00
  - `first_to_act` 先声夺人：当月首次打卡早于 12:00
- **计算逻辑**：`achievement_definitions.py` `_calc_seasonal()` 新增分支，用 created_at 时间戳判断
- **badge URL 映射**：app.py 两处 BADGE_URLS 更新
- **入库**：achievements + achievement_badges 表，sort_order 29/30/31
- **图片**：early_bird_A/B/C.png，FAL 生图 + PIL 去背（threshold=200）
- **docs**：badge-prompts.md 新增闻鸡起舞系列，已同步 Obsidian
- **FAL CDN 下载速度极慢**（~2-3KB/s），用户手动下载解决

### 验证结果
- early_riser: achieved=True（首次打卡 14:07 < 20:00）✓
- little_chick_commander: achieved=True（14:07 < 17:00）✓
- first_to_act: achieved=False（14:07 ≥ 12:00）✓
- 三张图片 200 OK，RGBA 白像素=0 ✓

### commit
待推送

### 本次完成
- **连续练习天数**：新增 `_calc_current_streak()` 从昨天倒查（今天没练不影响），当前=13天（5/7起）
- **本月练习环比**：改用上月同一时间段，文案"比4月少3天"，`_ring_diff()` 新增 `ref_period` 参数
- **本周练习环比**：改用 `weekly_assignments.stage_start/stage_end`（stage_order 定位），替代错误的自然周上上周逻辑；当前=2天 vs 上周8天→"比上周少6天"
- **格5/6 TOP无数据**：items JSON 中 item_id 用占位数字(1,2,3...)导致 SQL JOIN 失败，handoff-dizical-260520-criticalproblem-1.md 已记录
- commit: `8c523c2`, `d6dff83`, `a9427ef` 已推送 main

### 根因分析
- `_ring_diff` 硬编码"上周"，月份对比无法动态传入月份名 → 新增 `ref_period` 参数
- `week_days_prev` 用自然周上上周而非 actual 上周（stage周期）→ 改用 stage_order 定位
- 格5/6: items 录入时用占位 item_id(1,2,3...) 而非查询真实 ID，JOIN `is_archived=0` 行失败

## 2026-05-18 (Mon) AM — item_id fuzzy match bug + practice_query requirements 字段

### 本次完成
- **Bug 1**: `save_daily_practice` else 分支（新建记录）跳过 fuzzy match，`item_id` 错写为顺序号；修复：else 分支也先调 `_match_practice_item_id`；修正 6 条历史错配记录（05-12 ~ 05-17）
- **Bug 2**: `practice_query.py` 作业渲染读 `requirement` 而非 `requirements`（复数），本周作业要求显示空白；修复两处
- commit: `05d3e1f` + `d97cac8`，已推送 main

### 根因分析
- `save_daily_practice` 的 else 分支（无 existing 记录）原设计：为不在 `practice_items` 表的自由科目分配顺序号，但漏掉了「先 fuzzy match 再 fallback」逻辑
- `practice_query.py` 字段名 `requirements`（复数）是历史设计，`requirement`（单数）是拼写错误

## 2026-05-14 (Thu) PM — behavior_log + report UI

### 本次完成
- **4.1 后端**: append_behavior_log() + POST /api/log 接收 + /api/practices/{date} 返回
- **4.2 前端**: 今日跳过前日对比；练习轨迹时间线；逐科目前日对比（总时长+每科+顺序+新科目）
- **practice**: enterTime 进入时刻记录，三个打卡 fetch 带上 behavior_log
- **日历选择 UI**: today 青绿圆点角标；选中淡黄背景+橙色数字+左侧竖条；back.out 弹入动效
- **migrate_behavior_log.py**: DB migration 脚本
- **PR #29**: feat/behavior-log-and-report-ui → main，9 files

### 技术细节
- save_daily_practice 的 INSERT OR REPLACE 会覆盖 behavior_log → 改为打卡后追加 append_behavior_log
- cal-sel-ring 用 transform 导致位置乱跳 → 改用 CSS .selected class + .sel-bar span + GSAP scaleY 动画
- today::after 角标方案替代背景色（避免被 practice level 背景覆盖）
- **Bug**: 竖条 stuck 不消失 — GSAP inline transform 覆盖 CSS → 修复：killTweensOf + 手动设 scaleY(0)

### 收尾
- STATUS.md 更新时间 + 阶段描述
- handoff-2026-05-14-PM.md 更新
- **勋章数据库文档**: `tqob/05-Coding/project-dizical/勋章数据库/勋章墙数据库.md`
  - 表结构 + 28 枚勋章（sort_order 排序）+ `![]|120x120` 图片引用 + 表头字段名
  - grade 段位表含 `unlocked_template` / `locked_template` 列（统一模板在表下方）
  - badge_attachments/ 46 个图片附件
  - 待补：18 枚非 grade 勋章的 placeholder 描述

### Git Log（本次 session）
|| Commit | 内容 |
|--------|------|
| `2da33a3` | fix: achievements locked card overlay - SVG b-lock sizing + grey mask; badges GSAP entrance; practice items JSON robustness |
| `2159932` | fix: use CSS filter grayscale for locked badges instead of overlay pseudo-element |
| `3a4083a` | docs: update STATUS.md 2026-05-14 |
| `6ea730b` | fix: all_items.png white background made transparent via PIL threshold conversion |

### 当前状态
- git main clean，所有 commit 已 push
- 服务正常运行
- P0: 无（本次迭代计划事项全部完成）
- P2 历史遗留: 勋章幽默描述优化 / iPad 响应式双测

---

## 2026-05-13 (Wed) — 勋章墙 v4 重构 + 成就体系完善

### 本次完成
- **勋章墙 v4 重构**（音乐之旅成就）
  - 页面改名：勋章墙 → 音乐之旅成就
  - 卡片精简：只保留图片（100×100px居中）+ 名字（18px）+ 分类标签（14px）
  - 弹窗详情：放大高清图 + 获取条件 + 获取时间 + 一句话描述
  - 弹窗 GSAP 动效：从点击位置弹出，内容快速依次淡入（总时长 ~0.3s）
  - 列表排序：已解锁/未解锁分段，同类按最新获取时间降序

- **分类标签 UI**
  - 突破：淡红背景 + 细边框
  - 段位：淡金背景 + 细边框
  - 巅峰：淡紫背景 + 细边框
  - 执着：淡蓝背景 + 细边框
  - 晋级：淡绿背景 + 细边框
  - 神秘：淡灰背景 + 细边框
  - 统一：细体 11px + 中性灰文字 + 胶囊圆角

- **TOP 成就动态 condition**
  - top1/2/3 按未归档科目（is_archived=0）统计练习时长
  - top1 展示第1名科目 + 时长
  - top2 展示第2名科目 + 时长
  - top3 展示第3名科目 + 时长
  - condition 示例：`累计时长第 1：单吐(66分钟)`

- **Bug 修复**
  - `badges_page()` 末尾 `conn.close()` 关闭共享连接导致其他页面 500
  - grade 图去白底：PIL threshold=200，白色像素变透明，保存 RGBA

### Git Log（本次 session）
| Commit | 内容 |
|--------|------|
| `c9d6c09` | feat: 勋章墙重构 - 音乐之旅成就/弹窗详情/克制标签/简化卡片/解锁排序 |
| `b8c11dd` | fix: top2只展示第2名科目/top3只展示第3名科目 |
| `3e0e7f2` | feat: 勋章墙标签样式/段位金/巅峰紫/突破红/执着蓝/晋级绿细体胶囊 |
| `93a2d9c` | feat: top成就按未归档科目统计/弹窗condition直接展示科目名+时长 |
| `3e0e7f2` | 标签样式：淡彩色胶囊 + 细体中性文字 |

---

## 2026-05-13 (Wed) — achievements 重构 + badge 文件损坏修复

### 本次完成
- **README 更新**：badge 列表 + kid_app 架构说明，补 PR #27 漏掉的文档
- **milestone 俏皮描述**：5个 milestone 描述改为得瑟语气（"笛子都认识你了"/"时间管理大师"等）
- **achievements 卡片重构**：单列左右结构 + 120×120 圆形 badge + GSAP hover弹跳/click缩放动画 + 金色 spotlight 样式


- **PNG 文件损坏 + 修复**：`PR #27 squash merge` 导致 22 个 badge PNG blob 损坏存成旧丑版；从 `feat/achievements-badge-refresh` 分支 `2fe5a94` 强制覆盖修复；commit `8fadc8a`
- **prompt 文档化**：`docs/badge-prompts.md` 记录 22 条 prompt（ID + CDN URL + placeholder）
- **PNG 三地备份**：dev/ + iCloud TQ目录/ + iCloud Obsidian tqob/00-Artifacts/

### Git Log（本次 session）
| Commit | 内容 |
|--------|------|
| `47ff64c` | docs: update STATUS.md |
| `5ff33d6` | docs: add handoff-2026-05-13 |
| `8fffcd8` | docs: add enamel badge prompts v2 |
| `c47365e` | feat(kid-ui): achievements milestone redesign |
| `8fadc8a` | fix(kid-ui): restore enamel badge PNGs from PR branch |
| `c253c24` | docs: update README badge list + kid_app architecture |

### 下次待办
- **transparency**：badge PNG 白底去背（PIL 去背，白→透明 RGBA）— 图片现在还是有白底
- **勋章可配置化**：praise tab 勋章配置功能

---

### 本次完成
- **FAL 生图修复**: Nous Portal 登录成功 + pip install fal_client，image_generate 工具恢复
- **badge prompt 模板建立**: PRD 文档 `tqob/05-Coding/project-dizical/PRDs/勋章墙设计-生图prompt.md`，统一 Enamel Pin 风格
- **20张 badge 全部重新生成**: 统一 Enamel Pin 3D 珐琅金属徽章风格（gold border + glossy enamel fills + 居中图标）
- **prompt 记录规范化**: image-gen.md 记录 v1 废弃链 + v2 placeholder prompt + CDN URL + 本地路径
- **PR #27 合并**: 22 files changed（20 PNG + image-gen.md 记录）

### PR #27 内容
1. `1261353` — SQLite并发修复 + achievements布局重构
2. `2fe5a94` — 勋章墙 v2 Enamel Pin 风格全量替换（20 badge PNG）

### 下次待办
- 勋章可配置化（praise tab 勋章配置功能）
- milestone 幽默描述优化
- README 更新（badge 图床路径说明）

---

## 2026-05-12 (Mon) — achievements 重构 + badge 生图

### 本次完成

#### SQLite 并发修复
- **问题**: `unable to open database file` — macOS 多线程并发 connect() WAL 数据库
- **修复**: `_get_connection()` 改为单连接复用 `self._conn`，去掉 WAL journal mode
- **服务启动**: `uvicorn --workers 1`（单进程避免并发）

#### achievements 布局重构
- 去掉 2 列 grid → 单列全宽卡片（与 practice/prepare/report 一致）
- 本周目标 `goal = 5` → `goal = 7`（用户指出周应该7天）

#### Badge 生图（20张）
- 全部通过 Hermes Nous subscription 生成，存至 `src/kid_app/static/badges/`
- 覆盖 20 个 badge ID：streak_1/3/7/14/30/100, total_60/300/600/1000, first_log, double, week_champ, full_month, all_items, night_owl, one_breath, comeback, song_end, top1/2/3

#### 前端接入 badge 图片
- `_milestone_html()`: emoji → `<img>` 标签
- `badges_page` `render_badge_item()`: emoji → `<img>`
- achievements more-card: emoji → 真实 badge 图片

#### badges.html 网格优化
- 手机 2 列，平板 3 列，大屏 4 列，gap 加大
### 待办
- 勋章可配置化（praise tab 勋章配置功能）
- milestone 幽默描述优化
- Git 提交 + PR

---

## 2026-05-11 (Sun) — fuzzy match 重写 + prepare 新样式 + Kid UI Phase 3

---

## 2026-05-09 (Sat) — assign-phase1b + P0 备份全面收尾

### assign-phase1b 图片存储
- `weekly_assignments` 表新增 `images TEXT` 列（迁移兼容）
- `save_weekly_assignment` 支持 `images` 增量合并追加，不覆盖已有图片
- CLI `--image/-i` 可多次指定配图路径，录入后显示「📷 N 张已保存」
- 查询显示「📷 N 张配图」
- `.gitignore` 加入 `data/assignment_images/`
- 修复 iter 双重消费 bug：`img_list = list(img)` 避免确认消息计数错误
- subagent 验收：schema ✅ / 49 tests ✅ / E2E ✅
- Commit: `4f62e66` → `fc72a9e` (含 docs 更新)

### P0 数据备份全面完成
- `backup.py` DATA_DIR 路径修复：优先查 `data/dizi.db`，fallback 到 `/Users/mt16/data`（已清空）
- Payment reminder 措辞统一：`待缴余额` → `累计待缴金额`（11处）
- Cron 精简：只保留 `dizi-payment`，删 `dizi-monthly`/`dizi-weekly`/`dizi-reminders-sync`
- iCloud 同步验证：`/Users/mt16/Documents/TQ/01-Personal/0101-Family/010101-YoYo/dizical-backups/` ✅
- 废弃 `dizical.db` 空库 + `/Users/mt16/data/` 旧目录已清理

### 今日 commit（7个）
| Commit | 内容 |
|--------|------|
| `4f62e66` | feat: 每周作业配图存储 (assign-phase1b) |
| `fc72a9e` | docs: 更新 STATUS.md 和 DEVELOPMENT_PLAN.md |
| `65d863e` | docs: 更新STATUS.md和vibe coding log，收尾开发 |
| `5d33c74` | docs: 更新README - kid-ui底部Tab/归档/CLI逗号分隔 |
| `ced8c4c` | feat(cli): practice log 支持逗号分隔多条记录 |
| `4b47107` | fix(database): save_daily_practice 改为追加合并 |
| `673b36e` | fix(cli): practice log 默认日期改为今天 |

### 本次 Session（第二段）— P0验证 + dizical-report skill + Kid UI Phase3 plan
- P0 验证通过：practice log ✅ / backup run ✅ / assign配图录入查询 ✅
- dizical-report skill 创建：`~/.hermes/profiles/coder/skills/life-automation/dizical-report/SKILL.md`
  - 生图阻断：Nous subscription FAL gateway 未开通 gpt-image-2，需用户自行配置
- Kid UI Phase 3 plan：`dizical/.hermes/plans/kid-ui-phase3-ux-refresh.md`
  - P0: prepare页面完善
  - P1: achievements增强 + praise重建
  - P2: practice项目分组 + style.css统一
- Handoff: `.hermes/plans/kid-ui-phases-handoff.md`

---

## 2026-05-08 (Fri) — Kid UI Phase 2

### 本次完成（Phase 2）
- **底部Tab导航**：5个页面全部改为 position:fixed bottom，适合 iPad 单手操作
- **practice_config TUI 重构**：子菜单 while True 自循环，q 逐层返回，消灭死角
- **practice_config 归档菜单**：进菜单显示已归档清单，unarchive 行为修正
- **kid-ui 归档逻辑**：已归档小科目默认隐藏，底部归档区按钮点击后弹窗选择
- **practice log 逗号分隔**：支持 `单吐:7，回娘家:4` 中英文逗号多种格式
- **practice log 默认日期**：从"昨天"改为"今天"，与 practice today 一致
- **save_daily_practice 追加修复**：同日期多次 log 改为合并而非覆盖
- **归档 q 键无效 bug**：_archive_choose 两次 input() 导致第二次读空字符串
- **_category_sort 排序验证**：增加重复 ID 检查 + 完整性覆盖检查
- **代码审查**：subagent 审查发现归档 q 键 bug
- **数据库修复**：05-07 数据被 INSERT OR REPLACE 覆盖，补回 17 分钟记录

### 今日 commit（14个）
| Commit | 内容 |
|--------|------|
| `5d33c74` | docs: 更新README - kid-ui底部Tab/归档/CLI逗号分隔 |
| `ced8c4c` | feat(cli): practice log 支持逗号分隔多条记录 |
| `4b47107` | fix(database): save_daily_practice 改为追加合并而非整体替换 |
| `673b36e` | fix(cli): practice log 默认日期改为今天 |
| `585697e` | fix: _do_archive调用_archive_choose而非已删除的_archive_toggle |
| `290b6a1` | fix(practice-config): 修复归档q键无效+排序验证缺失 |
| `9eeeb01` | refactor(practice-config): 全面重构TUI交互规范 |
| `f546d00` | feat(kid-ui): 固定底部Tab导航 + practice_config归档管理 |

---

## 2026-05-08 (Fri) — Timer Bug

### Timer Bug 修复 (`a90e6f6`)
- **现象**: 选5分钟练习，计时300秒后打卡，记录成300分钟
- **根因**: `elapsed` 是秒，`submitPractice()` 和 `finishEarly()` 直接当分钟用
- **修复**: `submitPractice` 传 `Math.floor(elapsed/60)`，`finishEarly` 显示也转分钟

---

## 2026-05-07 (Thu)

### 每周老师要求导入
- 命令: `dizical practice import-assignments data/imports/import-assignments.csv`
- 结果: ✅ 17 周全部导入成功
- CSV 格式: `WeekStart,Item,Requirement,Notes`（日期格式 `YYYY/M/D`）

### 修复 thisweek TypeError bug
- **现象**: `dizical practice thisweek` 报错 `TypeError: string indices must be integers`
- **根因**: `daily_practices.items` 字段存了旧格式 `["单吐练习", "回娘家", ...]` 而非标准格式 `[{item: '单吐练习', minutes: N}, ...]`
- **修复**: `database.py` 新增 `_normalize_items()` 辅助方法，读取时自动 normalize

---

## 2026-04-28 (Mon)

### 状态检查
- 分支: `hermes/hermes-f001fa86` (worktree 模式)
- main 与 worktree 分支完全同步，均指向 `72b8e7f`
- remote `origin/main` 也是 `72b8e7f`，无落后
- 工作树干净，Git 层无任何遗留问题

### 已完成 PR (chronological)
| # | Commit | 内容 |
|---|--------|------|
| #10 | `72b8e7f` | fix: remove duplicate entry_points from setup.py |
| #9 | `6b23ec8` | feat: 批量导入进展log和每周老师要求 |
| #8 | `f809335` | fix: add cyan to _RICH_TAG regex for calendar alignment |
| #7 | `42ab1cd` | fix: 练习日历+独立显示、db_path绝对路径、图例格式统一 |

---

## 2026-01-28 (已归档数据)

| 项目 | 金额 |
|-----|------:|
| 节拍器 | 147 |
| lingokids | 545 |
| 很久以前羊肉串 | 549 |
| 竹笛考级 | 284 |
| 洗车会员费 | 6820 |
| 海南租车 | 2533 |
| 萨莉亚+弹珠 | 207 |
| 元旦云南土菜吃饭 | 853 |
| **合计** | **12,079** |

## 2026-05-11 (Mon) — kid_app 删除按钮 Bug 修复

### 根因
前端 `practice.html:774` 的 `onclick="deleteRecord('${it.item_id}')"` 传了字符串 `"1"`，后端 `app.py:152` 用 `body.get("id")` 取值（也是字符串），传给 `remove_daily_practice_record_by_id(date, item_id)` 后，与 DB 中的 `item_id`（int）比较 `1 != "1"` → 过滤永远失败 → 记录删不掉。

### 修复
| 文件 | 行 | 改动 |
|------|----|------|
| `practice.html` | 774 | `deleteRecord('${it.item_id}')` → `deleteRecord(${it.item_id})` |
| `app.py` | 152 | `body.get("id")` → `int(body.get("id", 0))` |

### 验证
- `DELETE /api/log {"id": 1}` (int) → `total_minutes` 从 20→10 ✅
- `DELETE /api/log {"id": "1"}` (str) → 同样有效（后端强转） ✅
- pytest 49/49 ✅

### 待修复（P0 未完成）
- P0: fuzzy match 包含关系权重过高
- P1: Kid UI Phase3 未启动
- 遗留: `_normalize_items` 在 `remove_daily_practice_record_by_id` 中实际未使用（被 `get_daily_practice` 替代）

### Git 状态
- main `73aacf6`，工作区 dirty（app.py + practice.html 未 commit）

---

## 2026-05-10 (Sun) — commit收尾 + handoff

### 本次完成
- **commit `ffee6c3`**：assignments 交互 TUI + fuzzy 显示 item_id + practice_query 作业查询逻辑修正（查「今天或之前最近」而非「本周周一」）+ dizical-kid 命令修复
- **commit `7778d98`**：`vibe coding log.md` → `vibe-coding-log.md`（连字符命名），更新所有 skill 文档引用

### 教训
- 上次 session 声称「都 commit 了」但未实际验证，导致 dirty 文件漏到新 session
- 今后：先报告结果 → 用户确认 → 再 git 验证 → 收尾，顺序不能反

### 遗留问题
- P1: fuzzy match 包含关系权重过高
- P2: Kid UI Phase3 未启动

### Git 状态
- main 与 origin/main 同步，工作区干净

---

## 2026-05-11 (Mon) — kid-app UI/UX 规范文档 + Phase3 全部收尾

### 本次完成
- **UIUX_STYLE.md 生成**：完整审查 5 个前端页面（prepare/practice/achievements/report/praise），覆盖配色/字体/布局/组件/动画/依赖，写入项目根目录
- **Push `82a50bb`**：docs: 添加 kid-app UI/UX 样式规范文档
- **同步 vault**：复制到 `tqob/05-Coding/project-dizical/docs/UIUX_STYLE.md`
- **Handoff**：`2026-05-11-1400-handoff.md`
- **Phase3 全部完成**：
  - fuzzy match 修复（pytest 49/49）
  - prepare 鼓励语 date-seeded
  - achievements 本周目标进度条 + 徽章距离提示
  - praise 页重构
  - practice 三栏布局重构（计时器/老师要求/额外练习）
  - 底部导航 `!important` 统一
  - 计时器 finishEarly + 自然结束 bug 修复
  - 额外练习自定义输入 + 删除确认
  - 计时器保护弹窗
  - 选择练习项目移到三栏上方

### 已知问题（不再处理）
- **宽屏右边界**：`.panel-extra` 负 margin 在 iPad Safari 不稳定，已放弃

### Git 状态
- main `82a50bb`，干净
- 服务器：uvicorn port 8765（proc `proc_eb43175f407c`, PID 27224）

## 2026-05-11 (Mon) PM — prepare tab GSAP ScrollTrigger 动画（失败回退）

### 本次完成
- **全部回退**：`practice.html` 和 `app.py` 恢复到 HEAD 状态
- **原因**：尝试在 `practice.html` 恢复 GSAP 弹入动画（ScrollTrigger 方案），Mac 浏览器始终看不到动画；点击练习科目后无法正确移动到计时器模块
- **服务器重启**：恢复正常

### 失败记录
- `practice.html` ScrollTrigger 动画：尝试了 `gsap.set()` → `gsap.to()`、`window.load` 延迟、`DOMContentLoaded` 保护等方案，均无效
- 根因未定位：可能是 Mac Chrome 对 `browser_console` 多行 JS 表达式有 "Object reference chain is too long" 限制，导致无法调试
- **经验**：下次改用 CSS `transition` / `animation` 做入场动画，不依赖 GSAP

### 未完成（handoff）
- prepare tab GSAP ScrollTrigger 动画流程（用户原始需求，**未开始**）
- "开始行动"按钮去下划线（未确认是否有）

### 文件
- Handoff：`260511-handoff.md`

## 2026-05-11 (Mon) — prepare 新样式 + tap-scroll 完成

### 完成
- **新配色**：cream/sage绿/rose粉渐变/lavender紫，maximatherapy 风格
- **GSAP ScrollTrigger**：hero 渐次淡入、step cards 滚动触发、CTA 弹性按钮
- **全局点击滚一屏**：逐屏 hero→steps→assignment→CTA（修正：DOM id `hero` 非 `heroSection`）
- **floatingTap**：右下角浮动提示，steps 区域显示，CTA 后消失
- **后端可配置**：BLESS_POOL(12条)/PREPARE_STEPS/CTA 文案
- **toggleStep**：点击勾选 + localStorage 每日重置
- **DB 修复**：weekly_assignments id=56，stage_end 2026-03-14→2026-05-17
- PR #26 merged，Commit 8eae04a

### 踩坑
- `SECTIONS` 数组中 `heroSection` 与实际 DOM id `hero` 不符，导致第一屏点击跳到最后
- GH API 网络 EOF，重试后成功
- merge 冲突：`--ours` 直接保留新版样式

### 遗留
- practice.html 入场动画（CSS transition 替代 GSAP，P2）

---

## 2026-05-11 (Mon) — kid-app 端口僵死 + `dizical status` 监控命令

### 本次完成
- **故障排查**：kid-app PID 35631 僵死未退出，持续占用端口 8765，导致重启失败
  - 现象：`curl /prepare` 返回 `Connection reset by peer`
  - 解决：`kill 35631` → 重启 uvicorn
- **`dizical status` 命令**：curses TUI dashboard
  - 监控：进程/PID、端口监听、HTTP /prepare 响应码+耗时
  - 显示：iPad 访问地址、最近练习记录
  - 交互：Q/Esc 退出，R 手动刷新，3秒自动刷新
  - 入口：`dizical status`

### 踩坑
- `subprocess.socket` → 正确：`import socket; socket.socket()`

---

## 2026-05-12 accumulate | 合并不完整 + 文档不同步

### 完成
- bless_pool扩至32条，替换7条push过强文案
- 随机刷新（每次打开页面换一条，不再按日期seed）
- praise页爸爸模式：增删祝福语（PIN验证）
- API: GET/PUT /api/bless-pool
- ~~feat/prepare-gsap-scrolltrigger~~（已删除）：半成品（215行模板），style与main不兼容，**决定舍弃**
- main 当前版本（8eae04a）无"步骤式检查逻辑"（三个准备工作→展示assignment→滚动）
- STATUS.md 未记录该分支存在，handoff 文件信息不准确
- egg-info 被 git track 导致工作区 dirty，两个 commit 未 push

### 今日处理
- git rm --cached dizical.egg-info/ + 加入 .gitignore → commit 0511075
- push a26c8b7 + 0511075 到 main
- STATUS.md 新增「历史遗留问题」段落记录未合并分支
- 工作区清理：删除 260511-handoff.md prepare-scroll-demo.html

### P0 待办
- prepare 步骤式检查逻辑：三个准备工作依次点完→展示本周assignment→流畅滚动到开始按钮

### 教训
1. 分支做完必须当天合并 main 或明确记录在 STATUS.md
2. PR 合入 main 后立即更新 STATUS.md + DEVELOPMENT_PLAN.md
3. handoff 文件要对照 git log 核实，不能凭记忆写
