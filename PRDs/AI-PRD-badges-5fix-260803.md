# Sprint 04 — Badges 5 Bug Fix PRD (260803)

> **AI 标注:** 本 PRD 由 coder agent 生成, YAML `source: ai-agent`, 镜像到 Obsidian `tqob/05-Coding/project-dizical/sprints/sprint-04-badges-5fix-2026-08-03/prd-badges-5fix-2026-08-03.md`.

## 背景

`/badges` 勋章墙页面有 5 个独立 badge bug, 都是显示/计算错误, dad 在浏览器逐个发现:

1. **加练狂魔** (double) — 应点亮但没亮. 历史首次达成 2026-07-27 (当日 4 sessions)
2. **streak_N** — 未解锁时 modal 应该告诉用户"还差多少天", 当前只显示静态条件
3. **考级 tab** — grade_1..10 (10 个考级 badge) 跟其他 milestone 混在一起, dad 要求独立 tab
4. **streak_7 图加载不出** — 浏览器 404
5. **seasonal 全 "当月累计 ≥ 60 分钟"** — 7 个 seasonal badge 都显示同一行, 实际语义完全不同

## 目标

5 个 bug 一次性修完, 每个 bug 都对应一个用户可感知的修复.

## 验收标准

### 1. 加练狂魔 calc
- 2026-07-27 起 (史上首次同日 ≥2 distinct session), double badge 应显示已解锁
- 未达成时 modal 显示 "同日 ≥ 2 次打卡" (跟现状一致)
- 历史数据 daily_practices 里 7 天有 ≥2 sessions (7-27..8-02)

### 2. streak_N / recovery_N 进度展示
- streak_100 (未解锁): modal "条件" 应显示 `连着打卡 100 天就能拿到（当前连续 9 天，还差 91 天）`
- streak_7 (已解锁): modal "条件" 应显示 `你在 2025-10-03 第一次连着打卡 7 天`
- recovery_first_practice_21 (未解锁): modal "条件" 应显示 `自2026-07-08起累计打卡 21 天（当前 9/21，还差 12 天）`
- recovery_first_practice_14 (已解锁): modal "条件" 应显示 `你在 2026-07-23 烫伤后连着打卡 14 天`

### 3. 考级 tab
- `/badges` 顶部 tab bar 应有 3 个: 成就 / 考级 / 赛季
- 点 "考级" 应只显示 grade_1..grade_10 共 10 个 badge
- grade_1 (小笛芽) 已解锁金色, grade_2..10 未解锁灰锁

### 4. streak_7 图
- db `achievement_badges` streak_7 is_current=1 行 url 应 = `/static/badges/streak_7.png`
- `static/badges/streak_7.png` 存在且 200 OK
- 视觉: 火焰主题, 跟 streak_3 (小火焰) / streak_14 (双周传说) 同一系列 (chibi 女孩 + 火焰 + 7 数字 + 笛子)
- 透明 PNG: 4 角 alpha=0, RGBA 模式

### 5. seasonal 7 个独立 cond
- 7 个 seasonal badge modal "条件" 各不相同 (当前都返同一行 "当月累计 ≥ 60 分钟"):
  - total_60 (小水滴) → 当月累计 ≥ 60 分钟
  - week_champ (绕梁七日) → 本周 X > 上周 Y, 阶段 N vs M
  - full_month (刮目相看) → 本月 X 分钟 > 上月 Y 分钟
  - top1 (情有独钟) → 当月第1: 科目名 (N 分钟)
  - early_riser (闻鸡起舞) → 首次达成 YYYY-MM-DD HH:MM (需早于 20:00)
  - little_chick_commander (小鸡指挥官) → 首次达成 ... (需早于 17:00)
  - first_to_act (先声夺人) → 首次达成 ... (需早于 12:00)

### 6. 附: tab icon 用 SVG
- 3 个 tab 都不用 emoji, 用 koboyo.com 手绘 SVG (trophy / treble-clef / star)
- `fill="currentColor"` 跟随主题色

## 非目标

- 不改其他 badge 的 calc 规则
- 不动 achievement_badges 表结构
- 不动 practice_items 表
- 不重写 /badges 整体 UI (只加 tab icon + 改 buildTab 过滤逻辑)

## 关联

- Sprint doc: [[sprint-04-badges-5fix-2026-08-03]]
- Tech spec: [[tech-spec-badges-5fix-2026-08-03]]
- Test plan: [[test-plan-badges-5fix-2026-08-03]]
- Verify: [[verify-2026-08-03]]
- PR #218