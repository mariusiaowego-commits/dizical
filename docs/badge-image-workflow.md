# Badge 图片生成工作流 (V2.5, 2026-06-16)

> dizical badge 图生成的**完整**流程 + 验收清单 + 排错指南 + 表彰型徽章设计.
> 沉淀自 2026-06-16 用户反馈"批改小帮手 灰方框" + "assign_pal UI locked" + "表彰型徽章字段" 三次调查, 防止下次重蹈覆辙.

---

## 1. 流程全景 (5 步)

```
STEP 1 表单填 meta       →  STEP 2 草稿         →  STEP 3 生图       →  STEP 4 去白底 (PIL + rembg)  →  STEP 5 commit
/config/badge 填字段       /api/badge/draft     /badge-image skill    skill step 7 (V2.4)               /api/badge/commit-from-draft
                                                                 ├─ 主路: PIL 阈值 245
                                                                 └─ 兜底: 透明<28% → rembg U2-Net

每步**强验收点** (不通过不能进下一步):
- STEP 1 验收: 表单**cond_text 必填**, **unlock_strategy 选 (calc/immediate)**, **纪念章**填 achieved_at_override
- STEP 2 验收: draft.json 写到 `data/lib/badge_data/{draft_id}.json`, status=`draft_created`
- STEP 3 验收: 图存 `.tmp/{draft_id}_v{n}.png`, 文件 > 500KB
- **STEP 4 验收 (关键)**: 4 角 alpha=0 **AND** 4 角 RGB 不画"软灰" + 真透明比例 ≥ 28%
- STEP 5 验收: /badges 页面 4 角干净 + modal 弹典故 + 状态跟 unlock_strategy 一致

---

## 2. 字段体系 (V2.5 通用设计)

### 2.1 表单字段 (`src/kid_app/templates/config-badge.html`)

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `id` | ✓ | str | badge 唯一 ID, e.g. `assign_pal` |
| `name` | ✓ | str | 中文名, e.g. "批改小帮手" |
| `type` | ✓ | str | 标签: 突破/巅峰/执着/段位/晋级/神秘 |
| `category` | ✓ | str | `milestone` 永久 / `seasonal` 季节 |
| `placeholder` | ✓ | str | AI 生图 prompt |
| `zh_story` | ✓ | str | 典故 (弹窗 modal-desc) |
| **`cond_text`** | **✓** | str | **条件文案 (弹窗 modal-cond, 手填/AI 生成, 必填)** |
| `unlock_strategy` | - | enum | `calc` (走计算, 默认) / `immediate` (立即解锁, 纪念章) |
| **`achieved_at_override`** | - | date | **解锁时间 (通用字段, 跟 grade 无关)**. 3 种用法: 1) 一次性事件 (考级/获奖/表彰) — 填日期, 立即 unlocked; 2) 纪念章场景 — 跟 `immediate` 配合; 3) 留空走 calc |
| `display_format` | - | str | `achieved_flag` / `top_items` / `days` / `minutes` / `time_hours_minutes` |
| `threshold` | - | int | 阈值 (calc 用) |
| `sort_order` | - | int | 展示顺序 |

### 2.2 **表彰型 / 纪念章型 徽章 (V2.6 新增)**

**场景**: badge **不走 calc** (跟练习无关), 一上线就解锁. 例:
- 纪念章 (assign_pal "批改小帮手" — 任何一次批改任务都触发)
- 考出时间 (grade_1 "小笛芽" — 2026-07-01 考出, 一次性 unlocked)
- 表彰时刻 (e.g. "六一儿童节当天练习" lucky_61 系列虽然走 calc, 但模式类似)

**3 种机制并存** (按优先级):

| 字段 | 优先级 | 触发 | 弹窗显示 |
|---|---|---|---|
| **`achieved_at_override` (新)** | **1 (最高)** | 通用: 表单填日期, 路由直接 unlocked | modal-cond: "考出时间: YYYY-MM-DD" |
| `unlock_strategy='immediate'` (PR #101) | 2 | 纪念章场景, commit 时直接 achieved=Y | modal-cond: "立即解锁" |
| `unlock_strategy='calc'` (默认) | 3 | 跟练习相关, 走 calc_all() | modal-cond: calc 返回 |

**实现路径** (`src/kid_app/app.py` 路由):
1. 检测 `is_commemorative = (unlock_strategy == "immediate" OR achieved_at_override 非 NULL)`
2. 如果 commemorative: **跳过 calc**, 直接读 achievement_stats.achieved='Y' 或用 achieved_at_override 时间
3. 返回 `CalcResult(achieved=True, achieved_at=override, condition="考出时间: ..." 或 "立即解锁")`

**commit handler** (`src/kid_app/routes/badge_workflow.py`):
- 用户填 `achieved_at_override` → 写 db (TEXT, nullable) + stats.achieved='Y' + stats.achieved_at=override+' 00:00:00'

### 2.3 数据库迁移

```bash
/usr/local/bin/python3 src/migrate_add_cond_text.py        # PR #100 加 cond_text
/usr/local/bin/python3 src/migrate_add_unlock_strategy.py   # PR #101 加 unlock_strategy
/usr/local/bin/python3 src/migrate_add_achieved_at_override.py  # V2.6 加 achieved_at_override
```

3 个 migration 都**幂等**, 重复跑无副作用.

### 2.4 适用场景判断 (设计决策树)

```
新 badge 设计?
│
├─ 跟练习相关 (e.g. streak/total_X/first_log)?
│   └─ → unlock_strategy='calc', 写 stat_logic, calc_all() 评估
│
├─ 一次性事件 (考级/获奖/表彰/生日)?
│   └─ → `achieved_at_override='YYYY-MM-DD'` (+ `unlock_strategy='calc'` 或 `'immediate'`)
│       (表单填日期, 一上线 unlocked, modal-cond 显示"考出时间: YYYY-MM-DD")
│       任何 badge 类型 (不限于 grade 1-10) 都能用此字段
│
└─ 任何时候都解锁 (纪念章/特殊)?
    └─ → unlock_strategy='immediate'
        (commit 时直接 achieved=Y, modal-cond 显示"立即解锁")
```

---

## 3. 5 步流程细节

### 3.1 STEP 1: 表单填 meta

路径: `http://localhost:8765/config/badge`

表单字段见 §2.1. 注意:
- `cond_text` **必填**, 留空 = 走 AI 按钮生成
- `unlock_strategy` 选 calc/immediate 决定是否走 calc
- `achieved_at_override` 纪念章场景填日期 (e.g. grade_1 填 `2026-07-01`)

### 3.2 STEP 2: 草稿

端点: `POST /api/badge/draft`

收 `meta` 字典 → 写 `data/lib/badge_data/{draft_id}.json`, status=`draft_created`.

### 3.3 STEP 3: 生图

走 `/badge-image` skill (跨 3 profile symlink 同步: dizical/coder/default).
**改过的 prompt** (V2.3 PR #101):
- ❌ 旧: "isolated on a clean white background"
- ✅ 新: "isolated object, transparent PNG background"

### 3.4 STEP 4: 去白底 (V2.4 双保险)

主路 PIL 阈值 245 + 兜底 rembg U2-Net (透明 <28% 触发).

**已知模型不稳定** (PR #102 调查):
- 同一 prompt 偶尔出 RGB(254) 真白 / RGB(237) 软灰 / AI 假装透明画棋盘
- 兜底机制必要, skill step 7 现在自动化

### 3.5 STEP 5: commit

端点: `POST /api/badge/commit-from-draft`

收 `draft_id`, 处理:
- description = zh_story (典故)
- cond_text = 用户/AI 填的 (条件文案)
- unlock_strategy + achieved_at_override (V2.6 通用字段)
- unlocked → 立即写 achievement_stats.achieved='Y'

---

## 4. 端到端验证清单

跑 5 步后**必须**逐项核查:

### 4.1 db 状态
```sql
SELECT id, name, description, cond_text, unlock_strategy, achieved_at_override
FROM achievements WHERE id='<new_badge_id>';

SELECT achievement_id, url, version, is_current
FROM achievement_badges WHERE achievement_id='<new_badge_id>';

SELECT achievement_id, achieved, achieved_at
FROM achievement_stats WHERE achievement_id='<new_badge_id>';
```

### 4.2 浏览器视觉
```bash
open http://localhost:8765/badges
open http://localhost:8765/achievements   # /achievements 路由 modal-box bg #fffdf8
```

**核查项**:
- [ ] badge 卡片显示 (不是"暂无勋章")
- [ ] 图真透明, 无"灰方框"
- [ ] 弹窗 modal-cond ≠ modal-desc (V2.2 PR #99)
- [ ] modal-cond 显示正确 (calc/立即解锁/考出时间 之一)
- [ ] unlocked 状态 badge 在 "已解锁" 区, locked 在 "未解锁"
- [ ] 长典故 modal-desc 可滚动 (V2.5 PR #108 max-height 60vh)

### 4.3 端到端 pytest
```bash
cd /Users/mt16/dev/dizical
/usr/local/bin/python3 -m pytest tests/ -q \
  --deselect tests/test_badge_batch.py::TestCommitBadgeBatchToDb::test_filter_not_ok_items \
  --deselect tests/test_lesson.py::TestPaymentManager::test_monthly_payment_status \
  --deselect tests/test_payment.py::TestPaymentManagerAdvanced::test_should_send_reminder
```

期望 ≥ 278 passed.

---

## 5. 排错指南

### 5.1 "暂无勋章" (db achievements 0 行)

**真凶**: `tests/conftest.py` V2.3 改造时 `DROP TABLE IF EXISTS` 没隔离 db.
**修法**: PR #104 用 `tmp_path_factory` 隔离, 不再碰 production.
**恢复**: 跑 `src/restore_achievements_v1.py` + `src/restore_achievement_badges_v1.py` (V2 完整复原).

### 5.2 "所有图显示同一张默认 medal_badge.png"

**真凶**: `achievement_badges` 表 0 行 + `get_badge_url()` fallback 默认图.
**修法**: 跑 `src/restore_achievement_badges_v1.py` (40 行 badge url) + grade_1~10 url 改 `grade_N-l.png`.
**立即生效**: 重启 service 清 60s `_BADGE_URL_CACHE`.

### 5.3 badge 显示 locked 但 db 是 Y

**真凶**: V2 era `badges_page` 路由走 `calc_all()`, 不读 `stats.achieved` for `unlock_strategy='immediate'`.
**修法** (V2.6 PR #110): 路由加 commemorative 分支, 检测 `unlock_strategy='immediate'` 或 `achieved_at_override` 非 NULL, 跳过 calc 直接 unlocked.

### 5.4 modal-cond 显示 desc 内容 (重复)

**真凶**: 前端 fallback `card.dataset.cond || card.dataset.desc` (V2.2 PR #99 修法, 但有些场景 fallback 复用).
**修法**: 走 V2.6 通用字段后, modal-cond 跟 modal-desc 自动分开 (3 级 fallback: calc > cond_text > desc).

### 5.5 /achievements 页面 modal 没背景

**真凶**: PR #98 Bug❸ 修法改 `background: transparent` 影响 `/badges` 跟 `/achievements` 两个模板.
**修法** (PR #106): `achievements.html` 单独改回 `#fffdf8` 跟 badges.html 一致.

### 5.6 modal-desc 太长, 弹窗超高

**真凶**: V2 era 长典故 (祖逖闻鸡起笛 407 字 / grade 典故 84-112 字) 没滚动.
**修法** (PR #108): `#modal-desc { max-height: 60vh; overflow-y: auto; }` 2 模板都加.

---

## 6. 视觉验证脚本

```python
from PIL import Image
import os
for f in sorted(os.listdir('src/kid_app/static/badges')):
    if not f.endswith('.png'): continue
    p = f'src/kid_app/static/badges/{f}'
    img = Image.open(p)
    w, h = img.size
    if img.mode == 'RGBA':
        trans = sum(1 for px in img.split()[-1].get_flattened_data() if px < 128)
        op = sum(1 for y in range(h) for x in range(w)
                 if img.getpixel((x,y))[3] >= 128 and img.getpixel((x,y))[0] > 200)
        print(f'{f:<35} RGBA 透明 {trans/(w*h)*100:>5.1f}% 灰白 {op/(w*h)*100:>5.1f}%')
    else:
        print(f'{f:<35} RGB  (无 alpha 通道, 老 fallback 图)')
```

浏览器实际视觉:
- `open http://127.0.0.1:8765/badges` 看 "批改小帮手" / "小笛芽" 等是否干净浮卡片
- `open http://127.0.0.1:8765/achievements` 验证 card-milestones 弹窗米色背景 + 长典故可滚动

---

## 7. 变更历史

| 版本 | 日期 | 变更 | 触发 |
|---|---|---|---|
| V1 | 2026-05-12 | PIL 去白底 (老 22 个 badge) | `docs/badge-prompts.md` |
| V2.1 | 2026-05-20 | workflow 文档初版 | `docs/badge-workflow.md` |
| V2.3 | 2026-06-16 | 改 prompt 删 "clean white background" | PR #101 |
| V2.4 | 2026-06-16 | PIL 阈值 + rembg 兜底 (双保险), 验收清单 | PR #103 (assign_pal 灰方框调查) |
| **V2.5** | **2026-06-16** | **+ V2.6 achieved_at_override 通用字段 + 表彰型徽章设计 + modal-desc 滚动 + /achievements modal bg 修复** | **PR #106-#111 沉淀** |