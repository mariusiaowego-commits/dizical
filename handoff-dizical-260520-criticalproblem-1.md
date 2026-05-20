# handoff-dizical-260520-criticalproblem-1
**创建时间**: 2026-05-20
**标签**: dizical-260520-criticalproblem-1
**优先级**: P0
**状态**: 已修复（commit dfc18fb）

---

## 问题1: 连续练习天数统计逻辑错误（连续天数显示为0）

### 现象
achievements 页面"已连续练习"看板显示0天，但实际从5/7到5/19每天都有练习记录。

### 根因
`streak_days()` 函数从今天倒查，遇到 `total_minutes=0` 的日期立即中断返回。当前 DB 中5/5和5/6存在"病假"记录（`total_minutes=0`），导致函数在5/6处中断，返回0。

但代码中已有正确的 `_calc_max_consecutive_streak()` 函数（从历史数据中找最长连续段，返回58），`achievements_page` 之前错误地调用了 `streak_days()` 而非 `_calc_max_consecutive_streak()`。

### 已修复（commit a9427ef）
`achievements_page` 已改用 `_calc_max_consecutive_streak()`，当前显示58天。

### 待确认
用户反馈：`_calc_max_consecutive_streak()` 的逻辑是否正确？
- 该函数扫描从最早数据到今天的所有日期，total_minutes>0则累加，=0则归零重新计
- 5/5 total_minutes=0 会中断当时的 streak，但不影响之后新开始的 streak 的历史最大值
- 需要用户确认这个逻辑是否符合业务预期（即"病假"是否算作"断练"）

---

## 问题2: daily_practices.items 中 item_id 数据污染 ✅ 已修复

### 根因
`addExtraMins`（is_extra=True）时，后端直接用 `max_id+1` 分配 item_id，不 fuzzy match。
且 `submitPractice`/`submitQuickLog` 等前端打卡只传 item name 不传 item_id。

### 修复（commit dfc18fb）

**前端**：`submitPractice`/`submitQuickLog`/`addExtraMins` payload 全部加 `item_id: selectedItemId`

**后端 `api_log`**：
- 前端已传 item_id → 直接用
- 前端未传 item_id → fuzzy match 回填
- 前端传了 item_id 但无效 → `db.validate_item_id()` fuzzy match 修复

**新增 `db.validate_item_id(item_id, item_name)`**：
- 验证 item_id 是否在 practice_items 表存在且 is_archived=0
- 无效则 fuzzy match 修复，返回真实 ID

**`save_daily_practice`**：
- 对已有的 item_id 也做合法性验证，无效则 fuzzy match 修复

### DB 数据修复
2026-05-18 和 2026-05-19 的 items JSON 已手工修正为真实 item_id：
- 1034=吸气长音, 1004=回娘家, 1341=唱萨利哈, 1340=萨丽哈, 1026=采茶扑蝶

### 验证结果
```
昨日(5/19): [('萨丽哈', 13), ('吸气长音', 9)]
本周(5/18~5/19): [('吸气长音', 18), ('萨丽哈', 13)]
本月(5月): [('吸气长音', 97), ('采茶扑蝶', 58)]
```

---

## 问题概述

dizical 项目存在两类严重数据质量问题，必须在下一个 sprint 优先修复。

---

## 问题1: 连续练习天数统计逻辑错误（连续天数显示为0）

### 现象
achievements 页面"已连续练习"看板显示0天，但实际从5/7到5/19每天都有练习记录。

### 根因
`streak_days()` 函数从今天倒查，遇到 `total_minutes=0` 的日期立即中断返回。当前 DB 中5/5和5/6存在"病假"记录（`total_minutes=0`），导致函数在5/6处中断，返回0。

但代码中已有正确的 `_calc_max_consecutive_streak()` 函数（从历史数据中找最长连续段，返回58），`achievements_page` 之前错误地调用了 `streak_days()` 而非 `_calc_max_consecutive_streak()`。

### 已修复（commit a9427ef）
`achievements_page` 已改用 `_calc_max_consecutive_streak()`，当前显示58天。

### 待确认
用户反馈：`_calc_max_consecutive_streak()` 的逻辑是否正确？
- 该函数扫描从最早数据到今天的所有日期，total_minutes>0则累加，=0则归零重新计
- 5/5 total_minutes=0 会中断当时的 streak，但不影响之后新开始的 streak 的历史最大值
- 需要用户确认这个逻辑是否符合业务预期（即"病假"是否算作"断练"）

---

## 问题2: daily_practices.items 中 item_id 数据污染

### 现象
achievements 页面格5（昨日TOP）、格6（本周TOP）显示"暂无"，但格7（本月TOP）正常。

### 根因
`_calc_top_items()` SQL JOIN 逻辑：
```sql
JOIN practice_items pi ON pi.item_id = json_extract(je.value, '$.item_id')
WHERE pi.is_archived = 0
```

部分历史 daily_practices 记录的 items JSON 中使用了**前端临时占位 item_id**（1,2,3,4...），而非从 practice_items 表查询的真实 ID。

**受影响的数据**：
- `2026-05-18`: `item_id: 1, 2, 3, 4`（实际应为 `1034, 1004, 1341, 1341`）
- `2026-05-19`: `item_id: 1, 2, 3`（实际应为 `1034, 1340, 1026`）

practice_items 表中 ID 1=基本功（已归档, is_archived=1）、ID 2=单吐（已归档），被 JOIN 条件过滤掉，导致这些记录无法匹配。

### 数据样本

**正常的 items 记录（格7有数据）**：
```json
2026-05-15: [{"item": "吸气长音", "minutes": 10, "item_id": 1034}, ...]
```

**被污染的 items 记录（格5/6无数据）**：
```json
2026-05-18: [{"item_id": 1, "item": "回娘家", ...}, {"item_id": 2, "item": "唱萨利哈", ...}]
2026-05-19: [{"item_id": 1, "item": "萨丽哈", ...}, {"item_id": 3, "item": "采茶扑蝶", ...}]
```

### 影响范围
- 格5（昨日TOP）：2026-05-19 记录污染
- 格6（本周TOP）：2026-05-18 记录污染
- 格7（本月TOP）：正常（因为本月有5/1-5/15的正常数据）

### 修复方案（待定）
需要决定：
1. **数据修复**：修正 items JSON 中的 item_id 映射（根据 item 名称匹配真实 ID）
2. **代码加固**：前端录入时禁止使用占位 ID，practice 录入 API 必须验证 item_id 合法性
3. **容错**：`_calc_top_items` 增加 fallback —— 当 JOIN 失败时，按 item 名称模糊匹配

---

## 涉及文件

- `src/kid_app/app.py`
  - `streak_days()` — 问题1相关（已确认返回0的根因）
  - `_calc_max_consecutive_streak()` — 问题1相关（正确实现）
  - `_calc_top_items()` — 问题2相关（JOIN 失败）
  - `achievements_page()` — 调用以上函数

- `data/dizi.db`
  - `daily_practices` 表 — items JSON 数据污染
  - `practice_items` 表 — 真实科目定义
  - `weekly_assignments` 表 — 周期定义（stage_start/stage_end/stage_order）

---

## 验证 SQL

```sql
-- 查看被污染的记录
SELECT date, items FROM daily_practices
WHERE date >= '2026-05-01'
AND items LIKE '%item_id": 1%' OR items LIKE '%item_id": 2%' OR items LIKE '%item_id": 3%';

-- 查看 practice_items ID 1-5 的实际情况
SELECT item_id, name, is_archived FROM practice_items WHERE item_id <= 5;

-- 验证连续天数计算（期望58）
SELECT COUNT(*) FROM daily_practices
WHERE total_minutes > 0
AND date >= '2025-09-27'  -- 最早数据日
AND date <= '2026-05-19';
```

---

## 下一步

1. 用户确认 `_calc_max_consecutive_streak()` 逻辑是否符合业务预期
2. 决定问题2的修复方案（数据修复 / 代码加固 / 容错）
3. 实施修复并验证
