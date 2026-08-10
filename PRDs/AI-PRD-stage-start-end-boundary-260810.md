---
id: 26081002-stage-start-end-boundary-prd-main
type: prd
version: 1.0.0
sprint: "[[sprint-26081002-2026-08-10]]"
date: 2026-08-10
author: dizical-agent
tags: [prd, dizical, stage-print, db-migrate]
---

# AI-PRD-stage-start-end-boundary-260810 — stage_start/end 边界修复

> Obsidian 镜像: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/PRDs/AI-PRD-stage-start-end-boundary-260810.md` (8-12 双写规则)

## 1. 背景

承接 sprint 26081001 验收, dad 浏览器实测发现 Stage 17 只有 8-01 一天, Stage 18 只有 8-08 一天, 但 `/api/practices/{date}` 显示 8-02~8-09 都有 40-71 min 练习数据. dad 反馈"一个 stage 里面只有一天 那也太错了".

## 2. 目标

G1. **stage 范围正确**: `/api/practices/stage-detail?stage_order=17` 返 7 天 (8-02~8-08), `?stage_order=18` 返 1 天 (8-09)
G2. **数据库一致**: 云端 2 行 weekly_assignments stage_start/end 跟 lessons 表下一节对齐
G3. **migrate 脚本 idempotent**: 多次跑 diff=0, 出错回滚

## 3. 用户故事

**As a** 家长  
**I want** 选 Stage 17 时能看到 8-02~8-08 共 7 天的练习明细 (含 8-01 当天 71 min + 8-02~8-07 共 6 天)  
**So that** 老师布置的"这个 stage 练了什么"不会因为 stage 边界错只看到 1 天, 影响我对女儿练习进度的判断

## 4. 验收标准

- AC1: `curl /api/practices/stage-detail?stage_order=17` 返 7 天 (8-02~8-08)
- AC2: `curl /api/practices/stage-detail?stage_order=18` 返 1 天 (8-09)
- AC3: prod `/report/stage-print` 选 Stage 17 显示 7 天内容, 选 Stage 18 显示 1 天内容
- AC4: 其他 stage (1-16, -1 到 -12) 不动
- AC5: 云端 `SELECT COUNT(*) FROM weekly_assignments WHERE stage_start = lesson_date` = 0
- AC6: 全套 pytest 0 新增 regression
- AC7: dad 浏览器实测 ok

## 5. 非目标

- ❌ 不修 save_weekly_assignment (PR #256 已修, 不会再产生新异常行)
- ❌ 不动其他 weekly_assignments 行
- ❌ 不改前端 stage-print.html
- ❌ 不写前端单测

## 6. 风险

| ID | 风险 | 等级 | 应对 |
|----|------|------|------|
| R1 | 反推算法错 | 中 | migrate 跑前 SELECT 验证 lessons 表 next lesson |
| R2 | 8-15 是 scheduled, 算法 future[0] 包括 attended + scheduled | 低 | 合理, 8-15 是 next stage_end |
| R3 | 云端 migrate 锁/权限/超时 | 中 | dump 备份, 失败立刻回滚 |

## 7. 修法

### 7.1 算法 (跟 SQLite `database.py:710-740` + PR #256 一致)
```python
def compute_new_boundary(lesson_date, all_lessons):
    stage_start = (lesson_date + timedelta(days=1)).isoformat()
    future = [d for d in all_lessons if d > lesson_date]
    stage_end = future[0].isoformat() if future else (lesson_date + timedelta(days=7)).isoformat()
    return stage_start, stage_end
```

### 7.2 修 2 行 (id=78, 79)
- id=78 (lesson=2026-08-01): stage_start 2026-08-01→**2026-08-02**, stage_end 2026-08-01→**2026-08-08**
- id=79 (lesson=2026-08-08): stage_start 2026-08-08→**2026-08-09**, stage_end 2026-08-08→**2026-08-15**

### 7.3 新 src/migrate_fix_stage_start_end_260810.py (跟 sprint 26081001 同款)
- `--target=local|cloud` 双模式
- DATABASE_URL 优先 + MYSQL_* 5 件套 fallback
- 备份到 `data/backups/stage-start-end-260810-{local,cloud}-pre-*.txt`
- 事务包裹
- 打印前后 diff
- idempotent (多次跑 diff=0)

## 8. 验证 (prod API)

```
/api/practices/stage-detail?stage_order=17:
  lesson_date: 2026-08-01
  stage_start: 2026-08-02  ✓
  stage_end: 2026-08-08   ✓
  days: 7 (8-02~8-08)     ✓
  total: 367 min

/api/practices/stage-detail?stage_order=18:
  lesson_date: 2026-08-08
  stage_start: 2026-08-09  ✓
  stage_end: 2026-08-15   ✓
  days: 1 (8-09)          ✓
  total: 56 min
```

## 9. 关联

- 关联 sprint: 26081001 (PR #256, #257, 修 stage_order)
- 起源: sprint 26080601 (切云) MySQL 老 fallback bug
- PR: #258 (MERGED)
- Obsidian sprint: `tqob/05-Coding/project-dizical/sprints/sprint-26081002-stage-start-end-boundary/`
- 主仓: `src/migrate_fix_stage_start_end_260810.py`
