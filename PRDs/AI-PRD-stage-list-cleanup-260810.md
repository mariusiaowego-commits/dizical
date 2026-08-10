---
id: 26081001-stage-list-cleanup-prd-main
type: prd
version: 1.0.0
sprint: "[[sprint-26081001-2026-08-10]]"
date: 2026-08-10
author: dizical-agent
tags: [prd, dizical, stage-print, db-migrate]
---

# AI-PRD-stage-list-cleanup-260810 — Stage 列表过滤 + stage_order 回填

> Obsidian 镜像: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/PRDs/AI-PRD-stage-list-cleanup-260810.md` (8-12 双写规则)

## 1. 背景

`/report/stage-print` 打印页 stage 选择器下拉里, dad 8-10 反馈出现 3 类问题:
1. **Stage 0** (8-08 新录入, lesson=2026-08-08, 应得 stage_order=18, 实际写 0)
2. **12 个 Stage null** (老 schema 数据, id 27-38, lesson 2025-11-08 ~ 2026-03-07)
3. **缺最新 Stage 18** (实际应有 Stage 18 — 7-26=16, 8-01=17, 8-08=18)

## 2. 目标 (3 个)

G1. **下拉干净**: `/api/practices/stages` 返 30 行 (1-18 + -1 到 -12), 无 NULL/0
G2. **新录入正确**: MySQL 路径 `save_weekly_assignment` 写入 stage_order 跟 SQLite 算法一致
G3. **老数据回填**: 14 行 stage_order 修复 (12 NULL + 2 zero, 含 issue 漏的 8-01)

## 3. 用户故事

**As a** 家长  
**I want** 在 `/report/stage-print` stage 下拉里看到所有有练习数据的 stage (1-18 连续), 没有 "Stage 0" 或 "Stage null" 噪音  
**So that** 老师要求录入后我能看到最新 stage 的练习明细, 选择历史 stage 时不会被老 schema 数据干扰

## 4. 验收标准

- AC1: `curl /api/practices/stages` 返回 `count=30, stages[].stage_order=1..18 + -1..-12` 全部为正/负整数
- AC2: 浏览器下拉里看到 "Stage 17 · 2026-08-02 ~ 2026-08-08 (课 2026-08-01)" 和 "Stage 18 · 2026-08-09 ~ 2026-08-15 (课 2026-08-08)"
- AC3: 浏览器下拉里无 "Stage 0" 或 "Stage null" 选项
- AC4: `SELECT COUNT(*) FROM weekly_assignments WHERE stage_order IS NULL OR stage_order <= 0` = 0
- AC5: pytest 5/5 新单测 + 全套 0 新增 regression
- AC6: PR MERGED + CloudRun 部署 + 双后端 migrate 完成

## 5. 非目标

- ❌ 不修 lessons 表 attended 状态 (假设正确)
- ❌ 不动 stage_order 已有正确值 (1-16) 的行
- ❌ 不改前端 stage-print.html (SQL 过滤后 option 列表干净)
- ❌ 不重构 save_weekly_assignment 整体逻辑

## 6. 风险

| ID | 风险 | 等级 | 应对 |
|----|------|------|------|
| R1 | MySQL BIGINT 拒绝浮点 (静默 rowsAffected=0) | 高 | 改用 P1 负数 -1 到 -12 (INT 安全) |
| R2 | SQLite 单例锁死 (sprint 250 教训) | 高 | migrate 完成后立即重启 8765 + curl 实测 |
| R3 | 12 个老 NULL 算 stage_order 算不到 (lessons 表没老 lesson) | 中 | 拍板 P1 用负数 -1 到 -12 (按 lesson_date 升序倒号) |
| R4 | 云端 migrate 锁/权限/超时 | 中 | 用 dump 备份, 失败立刻回滚 |
| R5 | 已有 row 不会自动修 (sprint 08 语义) | 中 | 独立 migrate 修老 fallback 写入的异常行 |

## 7. 修法 (最终 P1 负数方案)

### 7.1 SQL 过滤
```sql
-- src/database.py:1204 + src/database_mysql.py:1002
SELECT ... FROM weekly_assignments
WHERE stage_start IS NOT NULL
  AND stage_order IS NOT NULL
  AND stage_order != 0
ORDER BY stage_order DESC, id DESC
```

### 7.2 MySQL 路径 stage_order 算法 (跟 SQLite 7-13 一致)
```python
# src/database_mysql.py:425 旧代码 → 新代码
if row:
    # 已有 row: 保留 stage_* (sprint 08 语义)
    stage_start = row.get("stage_start")
    stage_end = row.get("stage_end")
    stage_order = row.get("stage_order")
else:
    # 新 row: 跟 SQLite 一致算法
    cur.execute("SELECT date FROM lessons WHERE status = 'attended' ORDER BY date")
    attended_dates = [...]
    cur.execute("SELECT date FROM lessons ORDER BY date")
    all_lessons = [...]
    stage_start = (lesson_date + timedelta(days=1)).isoformat()
    future = [d for d in all_lessons if d > lesson_date]
    stage_end = future[0].isoformat() if future else (lesson_date + timedelta(days=7)).isoformat()
    if lesson_date_str in attended_dates:
        stage_order = attended_dates.index(lesson_date_str) + 1
    else:
        stage_order = None  # P1: 不再写 0, 跟 SQLite 一致写 None
```

### 7.3 4 处 int(stage_order) 兼容 (浮点/负数)
```python
# database.py:1243 + database_mysql.py:1081 + app.py:1297/1326
# 改前: int(stage_order)  →  改后: 直接传 stage_order (让 SQL 处理)
```

### 7.4 P1 负数算法 (sprint 26081001 migrate)
```python
# src/migrate_fix_stage_order_260810.py:67-87
# 老 lesson (lessons 表没, 不在 attended 列表) → 负数 -1 到 -12
# 12 个老 NULL 行按 lesson_date 升序倒号:
#   2025-11-08 → -1, 2025-11-15 → -2, ..., 2026-03-07 → -12
if ld_str in attended_strs:
    new_so = attended_strs.index(ld_str) + 1  # 小课 1-18
else:
    offset = null_ids_ordered.index(rid)
    new_so = -(offset + 1)  # 早期大课 -1 到 -12
```

## 8. 验证 (prod API)

```
/api/practices/stages: count=30
  Stage 18 · 2026-08-09 ~ 2026-08-15 (课 2026-08-08)  ← 8-08 录入
  Stage 17 · 2026-08-02 ~ 2026-08-08 (课 2026-08-01)  ← 8-01 录入
  Stage 16 · 2026-07-27 ~ 2026-08-01 (课 2026-07-26)
  ...
  Stage -1 · 2025-11-09 ~ 2026-03-14 (课 2025-11-08)  ← 早期大课
  ...
  Stage -12 · 2026-03-08 ~ 2026-03-14 (课 2026-03-07)
```

## 9. 关联

- Issue: https://github.com/mariusiaowego-commits/dizical/issues/255
- PR: #256, #257
- 关联 sprint: 26081002 (PR #258, 修 stage_start/end 边界)
- Obsidian sprint: `tqob/05-Coding/project-dizical/sprints/sprint-26081001-stage-list-cleanup/`
- 主仓: `src/database.py`, `src/database_mysql.py`, `src/migrate_fix_stage_order_260810.py`
