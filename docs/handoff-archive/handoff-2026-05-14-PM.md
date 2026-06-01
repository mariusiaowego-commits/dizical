# Handoff — 2026-05-14 PM

## PR #29
`feat/behavior-log-and-report-ui` → main，commit `0f3eb6d`

## 已合并到 main

### behavior_log 后端
- `src/database.py`: `append_behavior_log(date, entry)` — 插入或追加 behavior_log JSON 数组
- `src/kid_app/app.py`: `POST /api/log` — 接收 `behavior_log` 字段，追加到当天记录
- `src/kid_app/app.py`: `/api/practices/{date}` — 返回 `behavior_log`
- `src/migrate_behavior_log.py`: DB migration（添加 `behavior_log` TEXT 列到 `daily_practices`）

### practice 前端
- `enterTime` = `new Date().toISOString()` 记录页面进入时刻
- 三个 POST body（quick/practice/addExtra）都带上 `behavior_log: [{enter_time, item, minutes}]`

### report 前端
- 今日无数据 → "今天还没过完，明天来看"
- 今日有数据 → 只显示记录和轨迹，无对比
- 历史日期 → 练习轨迹（📍时间线）+ 逐科目前日对比（📊总时长+每科+顺序+新科目+前日有今无）
- `detailBehaviorLog` / `detailComparison` — kid-app 卡片风格（白底+轻阴影+无粗体标题）

### 日历选择 UI
- today：右上角青绿圆点 `::after { top:4px; right:4px; border-radius:50%; background:#00695C }`
- 选中：`background:#FFFDE7` + `color:#E65100 bold` + 左侧竖条 `.sel-bar { scaleY:0→1, back.out(2.2) }`
- `.sel-bar` 是每个格子内的 `<span class="sel-bar"></span>`，由 Python render 时注入
- `cal-sel-ring` 已删除，改用纯 CSS `.selected` class

## 技术细节
- save_daily_practice 的 INSERT OR REPLACE 会覆盖 behavior_log → 改为打卡后追加 append_behavior_log
- cal-sel-ring 用 transform 导致位置乱跳 → 改用 CSS .selected class + .sel-bar span + GSAP scaleY 动画
- today::after 圆点用 absolute 右上角，::before 竖条用 absolute 左侧，z-index 10 不冲突
- selection 竖条 GSAP 动效：scaleY(0→1) + back.out(2.2)，旧 bar 要手动 kill + 清除 inline transform
- report.html 已移除旧 cal-sel-ring 元素
- today 被选中时：青绿角标 + 桃红竖条 + 淡黄背景 + 橙色加粗数字，四层叠加

## 2026-05-14 下午场 — 勋章数据库文档

### 新建文档
- `tqob/05-Coding/project-dizical/勋章数据库/勋章墙数据库.md`
  - 表结构（achievements + achievement_badges）+ 字段说明
  - 28 枚勋章按 sort_order 分组，含 `![]|120x120` 图片引用
  - 表头含数据库字段名（括号内）
  - grade 段位表含 `unlocked_template` / `locked_template` 列（统一模板在表下方 blockquote）
  - display_format 说明 / 勋章总数 / 附件清单
- `tqob/05-Coding/project-dizical/勋章数据库/badge_attachments/` — 46 个 badge 图片附件

### 待办
- 其他 18 枚非 grade 勋章（streak/total/top/first_log/all_items/double）的 placeholder 生图描述待补录
  - DB 中这三个字段目前均为 NULL，非 AI 生成，手工设计所以无 prompt

## 服务状态
- 服务运行在 `localhost:8765`
- 启动命令：`cd /Users/mt16/dev/dizical && python3.14 -m src.kid_app.app`
