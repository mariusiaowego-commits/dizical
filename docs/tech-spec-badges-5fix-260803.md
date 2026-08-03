# Sprint 04 — Badges 5 Bug Fix Tech Spec (260803)

> **AI 标注:** 本 tech spec 由 coder agent 生成, 镜像到 Obsidian `tqob/05-Coding/project-dizical/sprints/sprint-04-badges-5fix-2026-08-03/tech-spec-badges-5fix-2026-08-03.md`.

## 修复方案

### 1. 加练狂魔 (double) — `_has_double_practice` + `_double_first_achieved_at`

**问题根因**: `daily_practices.date` 是 UNIQUE 约束, 同日第二次练习走 UPDATE 合并 items (database.py:807-816), 数据库里**永远**不会有 `COUNT(*) >= 2 GROUP BY date` 的记录.

**修法**: 利用 `behavior_log` JSON 数组里的 `session_id` 字段. 一次保存 = 一个 session. 同日 distinct session_id ≥2 即"加练".

```python
# src/achievement_definitions.py

def _double_first_achieved_at(conn: sqlite3.Connection) -> str | None:
    """史上首次同日 ≥2 个 distinct session 的最早日期.

    daily_practices.date UNIQUE 约束导致同日第二次练习走 UPDATE 合并 items,
    永远不会出现 ≥2 条记录. 真正的"加练"语义看 behavior_log 里 distinct session_id 数.
    """
    cur = _exec(conn,
        "SELECT date, behavior_log FROM daily_practices "
        "WHERE behavior_log IS NOT NULL AND behavior_log != '[]' "
        "ORDER BY date"
    )
    import json as _json
    for date_str, log_str in cur.fetchall():
        try:
            entries = _json.loads(log_str)
        except (ValueError, TypeError):
            continue
        sessions = {e["session_id"] for e in entries if e.get("session_id") is not None}
        if len(sessions) >= 2:
            return date_str
    return None
```

历史数据: 2026-07-27 是首次达成日 (4 sessions).

### 2. streak_N / recovery_N 进度展示 — `_calc_milestone`

**a. streak 系列**: 未解锁时展示 "当前连续 X 天, 还差 N-X 天"

```python
if aid.startswith("streak_") and aid[7:].isdigit():
    n = int(aid.split("_")[1])
    first_at = _streak_first_achieved_at(conn, n)
    achieved = first_at is not None
    if achieved:
        cond = f"你在 {first_at} 第一次连着打卡 {n} 天"
    else:
        cur_streak_val = streak  # 全局 _get_consecutive_streak(dates, today)
        gap = max(0, n - cur_streak_val)
        cond = f"连着打卡 {n} 天就能拿到（当前连续 {cur_streak_val} 天，还差 {gap} 天）"
    return CalcResult(achieved, n if achieved else streak, None, first_at, cond)
```

**b. recovery 系列**: 加 `_recovery_current_streak` helper, 过滤 injury_date 之后的日期

```python
def _recovery_current_streak(conn, injury_date, today):
    """烫伤后当前连续天数 (从 today 往前数, 必须 >= injury_date).

    today 没练时 fallback yesterday (跟 _get_consecutive_streak 一致).
    """
    cur = _exec(conn,
        "SELECT DISTINCT date FROM daily_practices "
        "WHERE total_minutes > 0 AND date >= ? AND date <= ? ORDER BY date DESC",
        (injury_date, today.isoformat()),
    )
    dates = [r[0] for r in cur.fetchall()]
    if not dates:
        return 0
    dset = set(dates)
    start = today if today.isoformat() in dset else today - timedelta(days=1)
    streak = 0
    check = start
    while check.isoformat() in dset and check.isoformat() >= injury_date:
        streak += 1
        check -= timedelta(days=1)
    return streak
```

**c. `_get_consecutive_streak` 算法改进**: today 没练时 fallback yesterday

```python
def _get_consecutive_streak(dates, today, min_mins=10):
    if not dates:
        return 0
    dset = set(dates)
    start = today if today.isoformat() in dset else today - timedelta(days=1)
    streak = 0
    check = start
    while check.isoformat() in dset:
        streak += 1
        check -= timedelta(days=1)
    return streak
```

**d. `_calc_milestone` 加 today 参数**: `_recovery_current_streak` 需要 today.

```python
def _calc_milestone(conn, aid, stats, streak, total_mins,
                    top_items, has_all_items, all_items_achieved_at,
                    has_double, today):  # 新增 today
    ...
```

调用方 `calc_all` 同步加 today 参数.

**e. Modal 渲染优先级**: calc `cond` (含进度) > `cond_text` (用户/AI 填的友好描述) > `desc` (zh_story)

```js
// src/kid_app/templates/badges.html
document.getElementById('modal-cond').textContent =
  card.dataset.cond || card.dataset.condText || card.dataset.desc;
```

### 3. 考级 tab — `badges_page` + `badges.html`

**后端**: 给每个 badge 计算 `display_group`:

```python
# src/kid_app/app.py:badges_page
"display_group": "grade" if aid.startswith("grade_") else ach["category"],
```

**前端**: TABS 加 grade, buildTab 用 display_group 过滤

```js
// src/kid_app/templates/badges.html
const TABS = [
  { key: 'milestone', label: '成就',  icon: '/static/img/tab-icons/trophy.svg' },
  { key: 'grade',     label: '考级',  icon: '/static/img/tab-icons/treble-clef.svg' },
  { key: 'seasonal',  label: '赛季',  icon: '/static/img/tab-icons/star.svg' },
];

function buildTab(group) {
  const unlocked = DATA.filter(d => (d.display_group || d.group) === group && d.achieved);
  const locked   = DATA.filter(d => (d.display_group || d.group) === group && !d.achieved);
  ...
}
```

### 4. streak_7 图 — db url + 重生 PNG

**a. db url 修复**:

```sql
UPDATE achievement_badges SET url='/static/badges/streak_7.png'
WHERE achievement_id='streak_7' AND is_current=1;
```

**b. 火焰主题图重做**: 走 image_gen + PIL 阈值 245 + rembg U2-Net 兜底

- Prompt: "An emoji-adjacent 3D enamel pin of a chibi girl with a medium-sized orange-red flame rising above her head, holding a bamboo flute (dizi)... a small subtle number '7' integrated into the flame shape..."
- PIL 阈值 245 透明化 RGB>245 像素
- rembg U2-Net 二次净化 (处理 PIL 没割掉的深灰 234 RGB)
- 落盘到 `data/lib/badge_data/.tmp/streak7_regen_v1.png`
- dad 拍板后覆盖 `src/kid_app/static/badges/streak_7.png`

### 5. `_calc_seasonal` dispatch bug

**根因**: db 里所有 seasonal badge 的 `seasonal_type` 都是 "monthly". `_calc_seasonal` 里 `if seasonal_type == "monthly":` 块**直接 return** 月度通用 fallback (line 717 旧版), 导致 aid-specific 分支 (week_champ / full_month / top1 / early_riser / total_60 / threshold_map) **写在块外永远走不到**.

**修法**: 把所有 aid-specific 分支移进 `if seasonal_type == "monthly":` 块, fallback 在最后

```python
if seasonal_type == "monthly":
    # 1. lucky_61_YYYY (节日限定)
    if aid.startswith("lucky_61_") and len(aid) == len("lucky_61_2026"):
        ...
        return CalcResult(...)
    
    # 2. threshold_map (早练类)
    threshold_map = {"early_riser": 20, "little_chick_commander": 17, "first_to_act": 12}
    if aid in threshold_map:
        ...
        return CalcResult(...)
    
    # 3. total_60
    if aid == "total_60":
        ...
        return CalcResult(...)
    
    # 4. week_champ
    if aid == "week_champ":
        ...
        return CalcResult(...)
    
    # 5. full_month
    if aid == "full_month":
        ...
        return CalcResult(...)
    
    # 6. top1
    if aid == "top1":
        ...
        return CalcResult(...)
    
    # fallback: 当月累计 ≥ 60 分钟
    month_start = date(now_year, now_month, 1)
    ...
    return CalcResult(achieved, month_mins, None, None, cond)
```

### 6. 附: `_get_top_items` SQL alias bug (pre-existing)

```python
# 旧 (有 bug):
where = " AND dp.date >= ? AND dp.date <= ? "
# 新 (修复):
where = " AND date >= ? AND date <= ? "
```

`from` 子句是 `daily_practices` (无 alias), where 不能用 `dp.date`. 之前 dispatch bug 让 top1 永远走不到, 修了 dispatch 才暴露这个 pre-existing bug.

### 7. 附: tab icon SVG

下载 koboyo.com 手绘 SVG, 落到 `src/kid_app/static/img/tab-icons/`:

- `trophy.svg` — 奖杯, fill="currentColor"
- `treble-clef.svg` — 高音谱号
- `star.svg` — 5 角星

CSS: `.tab-icon { width: 18px; height: 18px; fill: currentColor; }` 跟随父元素 color.

## 数据库变更

- `achievement_badges`: streak_7 is_current=1 url 字段更新 (`streak_7_v1.png` → `streak_7.png`)
- 备份: `data/backups/dizi-pre-streak7-url-fix-20260803-133306.db` + `dizi-pre-streak7-url-fix2-20260803-154553.db`

## 测试覆盖

- `tests/test_double_practice_badge.py` (5 cases)
- `tests/test_streak_recovery_progress.py` (8 cases)
- `tests/test_seasonal_dispatch.py` (6 cases)
- `tests/test_night_owl_calc.py` (兼容老测试, 3 处调用加 today 参数)

合计 26 个新测试. 全套 399 passed, 14 pre-existing failed (与本次改动无关).