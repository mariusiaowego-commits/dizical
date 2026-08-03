# Sprint 04 — Badges 5 Bug Fix Test Plan (260803)

> **AI 标注:** 本 test plan 由 coder agent 生成, 镜像到 Obsidian `tqob/05-Coding/project-dizical/sprints/sprint-04-badges-5fix-2026-08-03/test-plan-badges-5fix-2026-08-03.md`.

## 测试策略

每个修复点对应独立测试文件, 用 in-memory SQLite 隔离. 真实 db 集成测试通过 `curl /badges` 拿 data_json 验证.

## test_double_practice_badge.py (5 cases)

验证加练狂魔 (double) 的核心语义.

1. **test_double_unlocks_when_two_sessions_same_day**
   - 同日 2 个 distinct session_id → `achieved=True`, first_at = 当日
   - 验证: 加练狂魔历史首次达成 = 2026-07-27 (4 sessions)

2. **test_double_locked_when_single_session**
   - 同日多条但都同 session_id → `achieved=False`
   - 边界: 多次保存是同一 session (重复点击保存)

3. **test_double_locked_for_legacy_entries_no_session_id**
   - 老 entries (无 session_id 字段) → `achieved=False`
   - 不算"加练" (没区分 session)

4. **test_double_earliest_date_when_multiple_days**
   - 多个日期都达成 → 返最早那一天
   - 例: 7-27 + 7-28 + 7-29 都达成 → first_at = 2026-07-27

5. **test_double_empty_db**
   - 无数据 → False / None

## test_streak_recovery_progress.py (8 cases)

验证 streak_N / recovery_N 进度展示 + `_get_consecutive_streak` 算法.

1. **test_streak_unlocked_shows_achieved_date**
   - 7 天连续 → `achieved=True`, cond = "你在 YYYY-MM-DD 第一次连着打卡 7 天"

2. **test_streak_locked_shows_progress**
   - 当前 9 天连续, streak_100 未达成 → cond 含 "当前连续 9 天, 还差 91 天"

3. **test_streak_locked_zero_progress**
   - today 跟 yesterday 都没练 → cond 含 "当前连续 0 天, 还差 N 天"

4. **test_recovery_unlocked**
   - 烫伤日 2026-07-08, 7-08..7-14 连续 7 天 → recovery_first_practice_7 达成

5. **test_recovery_locked_with_progress**
   - 当前 9 天, recovery_first_practice_21 未达成 → cond 含 "自2026-07-08起累计打卡 21 天（当前 9/21, 还差 12 天）"

6. **test_recovery_excludes_practice_before_injury**
   - 烫伤前有练习 (6-27..7-04 共 8 天), 不算 recovery streak
   - `_recovery_current_streak` 应只算 7-25..8-02 (9 天)

7. **test_recovery_streak_zero_when_today_not_practiced**
   - today 没练 + today+yesterday 都没练 → recovery streak = 0

8. **test_get_consecutive_streak_basic**
   - `_get_consecutive_streak` 基本场景 (today 在/不在, fallback yesterday)

## test_seasonal_dispatch.py (6 cases)

验证 `_calc_seasonal` dispatch bug 修复.

1. **test_week_champ_returns_correct_cond**
   - week_champ 不再返 "月累计 60 分钟" fallback
   - 应展示 "本周 X > 上周 Y, 阶段 N vs M"

2. **test_top1_returns_correct_cond**
   - top1 不再返 fallback (mock _get_top_items 避免 pre-existing SQL bug)

3. **test_full_month_returns_correct_cond**
   - full_month 不再返 fallback, 应展示 "本月 X 分钟 > 上月 Y 分钟"

4. **test_early_riser_returns_correct_cond**
   - early_riser 按小时判断, 不再返 fallback, 应展示 "首次达成 ... (需早于 20:00)"

5. **test_total_60_still_fallback**
   - total_60 本身就是月度 60 分钟, cond 应该是 fallback 文本 (允许)

6. **test_unknown_monthly_falls_back_to_60min**
   - 未知 monthly aid → 走 fallback 60 分钟 (default 行为保留)

## test_night_owl_calc.py 兼容

老测试调 `_calc_milestone` 没传 today 参数. 修复后必传. 改 3 处调用加 `today=date(2026, 6, 13)`, 加 `from datetime import date` import. 行为不变, 仅调用签名变化.

## 集成验证 (curl /badges)

重启服务后:

```bash
curl -s http://localhost:8765/badges | python3 -c "
import sys, re, json
html = sys.stdin.read()
m = re.search(r'const DATA = (\[.*?\]);', html, re.DOTALL)
data = json.loads(m.group(1))
for b in data:
    if b['id'] in ('double', 'streak_7', 'streak_100', 'recovery_first_practice_21', 'week_champ', 'top1', 'full_month'):
        print(f\"{b['id']}: {b['condition']}\")
"
```

期望:

- `double: 2026-07-27 同日 ≥2 次打卡` (解锁, achieved=True)
- `streak_7: 你在 2025-10-03 第一次连着打卡 7 天` (解锁)
- `streak_100: 连着打卡 100 天就能拿到 (当前连续 9 天, 还差 91 天)` (未解锁 + 进度)
- `recovery_first_practice_21: 自2026-07-08起累计打卡 21 天 (当前 9/21, 还差 12 天)` (未解锁 + 进度)
- `week_champ: 本周 X > 上周 Y, 阶段 N vs M` (而非 fallback)
- `top1: 当月第1: 科目名 (N 分钟)` (而非 fallback)
- `full_month: 本月 X 分钟 > 上月 Y 分钟` (而非 fallback)

## 浏览器验证 (dad 走)

```
1. http://localhost:8765/badges (Cmd+Shift+R 强刷)
2. 顶部 tab: 🏆 成就 / 🎵 考级 / 🌟 赛季 (3 个, SVG icon)
3. 点 🎵 考级 → 10 个 grade_1..10
4. 回到 🏆 成就 → 点 "周冠军" → 火焰主题图
5. 点 "百日传奇" → modal 显示进度
6. 点 "病愈连练21天" → modal 显示进度
7. 点 🌟 赛季 → 7 个 badge 各有不同 cond
```