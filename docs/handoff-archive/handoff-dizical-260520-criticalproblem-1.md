# handoff-dizical-260520-criticalproblem-1
**创建时间**: 2026-05-20
**标签**: dizical-260520-criticalproblem-1
**优先级**: P0
**状态**: 全部已修复（commits dfc18fb + e9f36ad）

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

## 问题2: practice_config CLI 看不到已归档科目 ✅ 已修复（commit e9f36ad）

### 现象
`dizical practice config` 归档菜单（选项4）里看不到任何已归档科目。

### 根因
`practice_config.py` 所有菜单函数调用 `get_practice_items(active_only=False)` 时没传 `include_archived=True`，默认只返回活跃科目（is_archived=0），已归档科目（33条）全部被过滤。

DB 里有 44 条 practice_items：11条活跃 + 33条已归档。前端 `/api/items?include_archived=true` 能返回全量44条，但 CLI 菜单只看到11条。

### 修复（commit e9f36ad）
11处 `get_practice_items(active_only=False)` 全部加 `include_archived=True`：
- `_do_archive`、`_archive_choose`、`_relation_set`
- `_do_item`、`_item_delete`、`_item_rename`、`_item_add`、`_show_current`

### 验证
```bash
python3 -c "from src.practice_config import _do_archive; print('OK')"
```

---

## 涉及文件

- `src/kid_app/app.py` — `api_log` item_id 验证链 + payload 传 item_id
- `src/kid_app/templates/practice.html` — 3处 payload 加 `item_id: selectedItemId`
- `src/database.py` — `validate_item_id()` 新增 + `save_daily_practice` 验证
- `src/practice_config.py` — 11处 `include_archived=True`
- `data/dizi.db` — items JSON 修正（5/18、5/19）

---

## 涉及 commits

| Commit | 内容 |
|--------|------|
| `dfc18fb` | fix: 前端传item_id + 后端验证链 + fuzzy match |
| `e9f36ad` | fix: practice_config 11处加 include_archived=True |
| `c4c1637` | docs: 更新 README |
| `8c523c2` | fix: 连续天数/本周环比修正 |
| `d6dff83` | fix: 本周/上周对比改用 stage_order |
| `a9427ef` | fix: 连续天数改用历史最长 |
