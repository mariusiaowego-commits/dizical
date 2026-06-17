# Badge V2.3: unlock_strategy 字段 + skill prompt 改 (RGBA 通用工作流) 实施 Plan

> **For Hermes:** 用户 2026-06-16 拍板. 1 大 PR. 解决 2 个问题:
> 1. unlock_strategy 字段 (commit 时立即解锁 vs 走 calc 评估)
> 2. skill prompt 改 (gpt-image-2 默认输出 RGBA 透明, 通用工作流, 不再手动去背)
>
> plan: `.hermes/plans/2026-06-16_093000-feat-badge-unlock-strategy-and-rgba.md`

## Goal
设计新 badge 时, 用户选 1 种解锁策略 (immediate/calc) + skill 默认生 RGBA 透明 PNG. 两者正交.

## 验收标准
1. ✅ meta 增 `unlock_strategy` enum 字段 (`immediate` / `calc`, 默认 `calc` 跟现状一致)
2. ✅ commit handler 走 immediate 时直接 `achieved='Y' + achieved_at=now` (设计时立刻解锁, 纪念章场景)
3. ✅ 老 badge 数据 (没 unlock_strategy) 默认 `calc`, 行为不变
4. ✅ skill prompt 改: 删 `isolated on a clean white background`, 改 `isolated object, transparent PNG background`
5. ✅ PIL step 7 加真去白底逻辑 (兜底, prompt 偶尔产出白底也自动转透明)
6. ✅ assign_pal 这张图用新方法重生 RGBA 透明版替换 (父 PR 完成后, 单独 agent 跑)

## 调研结论 (实查)
- **unlock_strategy 必须新字段**: category (milestone/seasonal) 跟 unlock_strategy (immediate/calc) 是正交维度
- **其他 badge 为什么 RGBA**: 同一模型 `fal-ai/gpt-image-2` 输出, 区别在 prompt — 不写白底默认输出透明 PNG
- **assign_pal v2.png RGB 原因**: skill prompt 写了 "isolated on a clean white background", 模型就给白底
- **PIL step 7 升级**: 原只检测 "alpha < 128 红色像素", 改: 检测 "RGB > 245 白底像素 → alpha=0"

## 设计

### unlock_strategy 字段
- meta 增 `unlock_strategy: 'immediate' | 'calc'` (默认 `calc`)
- DB `achievements` 加 `unlock_strategy TEXT DEFAULT 'calc'`
- 表单 v21 基础信息 select (跟 category 同级), 默认 `calc`
- tooltip: "解锁策略. immediate = 立即解锁 (纪念章, 跟练习无关). calc = 走 calc 评估 (跟练习相关, 需 calc 接入)"

### commit handler 改 (routes/badge_workflow.py)
```python
if draft.meta.get("unlock_strategy") == "immediate":
    # 直接 achieved='Y' + achieved_at=now
    badge_db.insert_achievement_stats_row(conn, badge_id, achieved='Y', achieved_at=now_iso())
else:
    # 老路径, calc 接入后由 calc_all 评估
    badge_db.insert_achievement_stats_row(conn, badge_id)
```
**前提**: `insert_achievement_stats_row` 接受 achieved + achieved_at 参数 (当前只接受 badge_id)

### skill prompt 改 (~/.hermes/profiles/dizical/skills/badge-image/SKILL.md)
```diff
- ...Orthographic, straight-on view, high quality, isolated on a clean white background.
+ ...Orthographic, straight-on view, high quality, isolated object, transparent PNG background.
```

### skill step 7 PIL 去白底 (新)
```python
from PIL import Image
img = Image.open(f"{TMP_DIR}/{draft_id}_v{n}.png")
if img.mode != "RGBA":
    img = img.convert("RGBA")
# 去白底: 任何 RGB > 245 的像素 → alpha=0
pixels = img.load()
w, h = img.size
for y in range(h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        if r > 245 and g > 245 and b > 245:
            pixels[x, y] = (r, g, b, 0)
img.save(f"{TMP_DIR}/{draft_id}_v{n}.png", optimize=True)
# 验证: alpha 通道 < 128 像素比例 > 20% (跟其他 badge 一致 30-60%)
```

**性能**: 1024x1024 = 1M 像素, Python loop ~5-10s. 接受 (反正生图已经 30-60s).

### milestone_html 渲染 + app.py
- `achievement_stats.achieved_at` 立即解锁的 badge 有值, 渲染时显示 "已解锁 [日期]"
- 老逻辑 `if achieved: ...` 不用改, achieved=True 就进 unlocked 区域

## 实施步骤

### Step 1: Worktree 隔离 (主仓 8765 不动)
- `git worktree add -b feat/badge-unlock-strategy /Users/mt16/dev/dizical-8770 main`

### Step 2: DB migration (achievements 加 unlock_strategy 列)
- `src/migrate_add_unlock_strategy.py` (新) — ALTER TABLE ADD COLUMN
- 跟 cond_text migration 同模式

### Step 3: TDD pytest
- `tests/test_unlock_strategy.py` (新, 5 cases):
  - 1. meta.unlock_strategy='immediate' → commit 后 achieved='Y' + achieved_at 非空
  - 2. meta.unlock_strategy='calc' (默认) → commit 后 achieved='N' + achieved_at NULL (老行为)
  - 3. meta 缺 unlock_strategy → 跟 case 2 一样 (老数据兼容)
  - 4. meta.unlock_strategy='invalid_value' → 验证拒绝 (400 错误)
  - 5. 老 achievement (没 unlock_strategy 列) 走 calc 默认, 行为不变

### Step 4: 改 routes/badge_workflow.py commit handler
- 检查 `unlock_strategy` enum 合法
- 走 immediate: 传 achieved='Y' + achieved_at 给 insert_achievement_stats_row
- 走 calc: 跟现状一样

### Step 5: 改 badge_db.insert_achievement_stats_row
- 接受 achieved + achieved_at 参数 (默认值 'N' + None)

### Step 6: 改 config-badge.html
- 加 select 字段 (跟 category 同级)
- tooltip 加 v21UnlockStrategy
- form data collect 加 unlock_strategy

### Step 7: 改 skill (~/.hermes/profiles/dizical/skills/badge-image/SKILL.md)
- prompt 改
- step 7 PIL 去白底代码

### Step 8: 全量 pytest
- 期望 268+ passed (原 263 + 5 新)

### Step 9: Worktree 启 8770 + e2e 验
- TestClient 调 commit-from-draft
- 验 immediate 路径: db.achieved='Y'
- 验 calc 路径: db.achieved='N'

### Step 10: commit + push + PR #101

## 文件清单
| 文件 | 改动 | 行数 |
|---|---|---|
| `src/migrate_add_unlock_strategy.py` | 新, migration | ~30 |
| `src/kid_app/badge_db.py` | 改 insert_achievement_stats_row 接受参数 | ~10 |
| `src/kid_app/routes/badge_workflow.py` | 改 commit handler 检查 unlock_strategy | ~15 |
| `src/kid_app/templates/config-badge.html` | 加 select + tooltip | ~30 |
| `tests/test_unlock_strategy.py` | 新, 5 cases | ~200 |
| `tests/conftest.py` | 加 unlock_strategy 列到创表 SQL | ~3 |
| `tests/test_badge_db.py` | 加 unlock_strategy 列 | ~3 |
| `~/.hermes/profiles/dizical/skills/badge-image/SKILL.md` | 改 prompt + step 7 | ~20 |

## 风险
- 老 milestone_data.achievement_stats 行的 `achieved` 跟 `achieved_at` 已存在, migration 不要重置
- skill 改 prompt 风险低 (只是描述变化), 不会破坏其他 badge 生成
- PIL 去白底兜底对全白图 (如 star_badge.svg 转 PNG) 会误判 → 但 skill 只处理 AI 生成图, 那些有 RGB 内容, 不会全白
- skill 部署 3 profile symlink 自动同步, 改 1 个 = 全部更新

## 已知不修 (followup)
- 老 RGB fallback 图 (fire_badge, medal_badge, star_badge, week_star_badge) — 单独 issue
- assign_pal_v2.png 这次重生 — 父 PR 合并后单独 agent 跑 (用新 skill prompt 重生 + PIL 去白底)
- calc 接入后 immediate 跟 calc 的边界 — 走 calc-apply skill 单独 PR

## 收尾
- PR #101 merge 后, 重启主仓 8765
- 单独起 agent 帮用户重新生成 assign_pal 图 (教学模式, 走 skill)
