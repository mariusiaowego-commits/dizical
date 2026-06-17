# Badge V2.1 工作流 6 个 Bug 修复 Plan

> **For Hermes:** 用户在 2026-06-15 走完一次完整 badge 工作流, 发现 6 个 bug, 要求一次性全部修干净并重新 commit `assign_pal` 验证。issue: `/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/issues/生成badge工作流问题.md`

## Goal
修复用户提的全部 6 个 badge workflow bug, 重新 commit `assign_pal` 走通端到端验证, 1 个 PR 收尾。

## 当前状态 (实查)
- 走通过一次: STEP 1 填 meta → STEP 2 hermes chat 多轮 (v1 蒙正好少年 → v2 批改小帮手) → STEP 3 commit
- draft `2026-06-15_assign_pal_517548` 状态 `committed`
- DB 状态: `achievements` 行有, `achievement_stats.achieved='N'`, `achievement_badges.url='/static/badges/assign_pal_v1.png'`
- 实际文件: `src/kid_app/static/badges/assign_pal_v1.png` 存在 (1.5MB, "蒙正好少年"), `assign_pal_v2.png` 不存在 (404)
- `.tmp/2026-06-15_assign_pal_517548_v2.png` 仍存在 (1.6MB, "批改小帮手") — cleanup 没用对 version, v2 残骸没清

## 6 个 Bug 根因 (已实查代码确认)

### Bug 1 — 显示的图是错的 (你以为 404, 实际 200 但版本错)
**真凶**: `routes/badge_workflow.py:148` `move_tmp_to_static(req.draft_id, draft.version)` 用了**顶层 `version`**, 但用户在 hermes chat 多轮对话时 hermes agent **直接编辑 draft.json** 写 `image_regenerated_v2` event + 改 `image.version=2`, 没走 `badge_draft.update_draft_image()` 函数, 所以顶层 `version` 没同步 (还是 1)。
**后果**: commit 复制 v1.png 到 static, achievement_badges.url 写 `_v1.png`, 前端加载到 v1 ("蒙正好少年") 而不是用户期望的 v2 ("批改小帮手")。

### Bug 2 — milestone 仍 locked
**真凶**: 设计如此。achievements 表**没** `is_locked` 列。locked 由 `achievement_stats.achieved='N'` + 前端 CSS 灰化判定。新 commit 的 stats row `achieved='N'` + `src/achievement_definitions.py` 里**没有** `assign_pal` calc 规则 → 永远 locked。**V2.1 plan 拍板 calc 跟生图解耦, calc 走 git apply + `/calc-apply` skill 单独提 PR**。
**本次不修 calc, 但要修 UI 文案误导** ("自动解锁" 实际是 "calc 接入后解锁")。

### Bug 3 — 灰底 (去背景差)
**真凶**: skill `badge-image` 文档 step 7 写 "PIL alpha 验证", 实际只检测 alpha 通道<128 比例, **没去背景**。模型生成 "isolated on a clean white background" — 输出是 1024x1024 整张**白底** PNG, 不是透明 PNG。前端 div 米色 + 白底图 = 灰方框感。
**超出本次 PR scope** (需装 rembg 或调 bria-rmbg 模型, 跨依赖), **记录 issue 不修代码**。

### Bug 4 — modal-desc 显示 "无"
**真凶**: `routes/badge_workflow.py:155-156` `meta_for_db.setdefault("description", "无")` + `setdefault("stat_logic", "无")` — V2 meta schema 不收这俩字段, 直接落 "无"。前端 `achievements.html:614` 读 `card.dataset.desc` 拿到 "无" → 显示 "无"。
**修法**: commit 写库时把 `meta["zh_story"]` 映射到 `description` (zh_story 实际就是典故小故事, 业务语义跟 description 一致), `stat_logic` 改落空字符串 `""` (calc 不靠它, 留 "无" 是历史包袱)。

### Bug 5 — modal-cond 显示空白 (注意: 跟 Bug 4 根因不同)
**根因 (实查)**: `modal-cond` 读 `data-cond` 来自 `CalcResult.condition` (calc 计算返回), 不是 `achievements.description`。
- `app.py:509` `_build_milestone_card(... ach["description"] ... condition="")` 第 9 个参数
- `app.py:1461` `badges` 路由 `"condition": res.condition` 取 calc 返回
- `achievement_definitions.py:375` `_calc_milestone` fallthrough `return CalcResult(False, 0, None, None, "")` — 空字符串
- `assign_pal` 没 calc 规则 → `condition=""` → modal 显示空 (而不是"无")
- `curl /badges` 实查 (2026-06-15): `assign_pal 批改小帮手 achieved=False cond=` (空字符串)

**修法 (本期跟 Bug 4 一起, 前端 JS 1 行 fallback)**:
- `src/kid_app/templates/badges.html:600` (跟 achievements.html 同样位置) `card.dataset.cond` 读 → 改为 `card.dataset.cond || card.dataset.desc` (cond 空时复用 desc = zh_story)
- 同样改 `achievements.html:600`
- 业务理由: 没 calc 规则的 badge 暂时用 zh_story 兜底, calc 接入后 condition 字段自动覆盖

**已知副作用**: modal-cond 跟 modal-desc 内容暂时相同, 用户体验 ok; calc 接入后两边会自动分 (condition 走 calc, desc 走 zh_story)。

### Bug 6 — 字段 tooltip
**真凶**: `config-badge.html` 的 v21-section / v21-advanced 字段 label 没 tooltip, 新用户看不懂。
**修法**: 给 v21-section 跟 v21-advanced 所有 `<label>` 旁加 `?` 图标, hover 弹 GSAP fade-in tooltip, 大白话 1-2 句解释每个字段。

## 修复策略

### 1. Bug 1 (commit 用 image.version 不用顶层 version) — 核心
`src/kid_app/routes/badge_workflow.py:148, 161-166, 173, 181` — commit handler 全程用 `draft.image["version"]`, 顶层 `version` 同步更新(为单数据源)。

具体改动:
- `move_tmp_to_static(req.draft_id, draft.version)` → `move_tmp_to_static(req.draft_id, image_version)`
- `badge_db.insert_badge_row(... version=draft.version)` → `version=image_version`
- `badge_draft.cleanup_tmp(req.draft_id, draft.version)` → `cleanup_tmp(req.draft_id, image_version)`
- 返回 url `f"/static/badges/{badge_id}_v{draft.version}.png"` → `_v{image_version}.png`
- 修完后调用 `mark_draft_status` 前 `draft.version = image_version; save_draft(draft)` (顶层同步, 让 draft 状态自洽)

### 2. Bug 4+5 (description 取 zh_story)
`src/kid_app/routes/badge_workflow.py:155-156`:
- `meta_for_db.setdefault("description", "无")` → `meta_for_db["description"] = meta_for_db.get("zh_story") or "无"`
- `meta_for_db.setdefault("stat_logic", "无")` → `meta_for_db["stat_logic"] = ""`

### 3. Bug 2 (UI 文案误导) — 局部
`src/kid_app/templates/config-badge.html` — 找 "milestone (里程碑, 写三表 + 自动解锁)" 文案, 改为 "milestone (里程碑, 写三表 + 等 calc 接入后解锁)"。

### 4. Bug 6 (tooltip)
`src/kid_app/templates/config-badge.html` — 给 v21-section / v21-advanced 字段 label 旁加 `?` 图标 span, hover 用 GSAP fade-in 弹 tooltip div。**大白话文案**:
- `name`: "Badge 的中文名, 孩子能叫出来的"
- `type`: "突破 / 坚持 / 季节 - 决定这枚 badge 怎么算达成"
- `category`: "milestone = 永久勋章 / seasonal = 节日/季节限定"
- `placeholder`: "英文描述想画的画面, 喂给 AI 生图模型"
- `zh_story`: "中文典故 + 鼓励小故事, 弹窗里给孩子看"
- `display_format`: "前端展示格式, achieved_flag = 完成型"
- `sort_order`: "展示顺序, 数字小的在前"

### 5. Bug 3 (去背景) — 记录不动
在本 plan 末尾加 "followup issues" 一节, 提示用户/未来 agent:
- "badge 去背景" issue 单独建, 需评估 rembg / bria-rmbg / 提示工程三种方案
- 短期 workaround: 前端 div `background: transparent` (现在是 `#fffdf8` 米色, 改成跟白底同色或透明, 视觉差缓解)

不修代码, 但**短期缓解** (改前端背景色) 可放本次 PR 末尾 (1 行 CSS)。

## 测试策略

### 新增/改 pytest
1. `tests/test_badge_commit_version_sync.py` (新) — 测 commit handler:
   - test 1: draft 顶层 version=1, image.version=2 → commit 后 achievement_badges.url 必须是 `_v2.png`
   - test 2: draft 顶层 version=2, image.version=2 → commit 后 url 是 `_v2.png` (回归)
   - test 3: commit 后 draft.json 顶层 version 跟 image.version 同步
   - test 4: commit 后 .tmp/{id}_v{image_version}.png 被清理
2. `tests/test_badge_commit_meta_mapping.py` (新) — 测 meta 映射:
   - test 1: meta.zh_story 存在 → achievements.description = zh_story
   - test 2: meta.zh_story 缺 → achievements.description = "无"
   - test 3: achievements.stat_logic = "" (不是 "无")
3. `tests/test_badge_workflow_routes.py` 已有 → 加 1 case 验 stat_logic 空字符串

### 验证步骤
```
cd /Users/mt16/dev/dizical
/usr/local/bin/python3 -m pytest tests/test_badge_commit_version_sync.py tests/test_badge_commit_meta_mapping.py -v
# 期望 7+ passed

/usr/local/bin/python3 -m pytest tests/ -q
# 期望 250+ passed (含 PR #97 的 245 + 新增 5+)
```

## 端到端验证 (recommit `assign_pal`)

清旧数据 → 走 STEP 1-3 → 检查文件 + DB + 前端 200 + 图对。

```bash
# 1. 清旧 commit 残留
sqlite3 data/dizi.db "DELETE FROM achievement_stats WHERE achievement_id='assign_pal';"
sqlite3 data/dizi.db "DELETE FROM achievement_badges WHERE achievement_id='assign_pal';"
sqlite3 data/dizi.db "DELETE FROM achievements WHERE id='assign_pal';"
rm -f src/kid_app/static/badges/assign_pal_v1.png src/kid_app/static/badges/assign_pal_v2.png
rm -f data/lib/badge_data/.tmp/2026-06-15_assign_pal_517548_*.png

# 2. 重 commit: 走 commit-from-draft 端点 (draft 还在, status=committed, 但我们要重置到 draft_awaiting_confirm)
# 实际做法: 把 draft.json 状态从 committed 改回 draft_awaiting_confirm
python3 -c "
import json
from pathlib import Path
p = Path('data/lib/badge_data/2026-06-15_assign_pal_517548.json')
d = json.loads(p.read_text())
d['status'] = 'draft_awaiting_confirm'
d['history'].append({'at': '2026-06-15T08:00:00Z', 'from': 'committed', 'to': 'draft_awaiting_confirm', 'by': 'agent', 'event': 'reset_for_recommit'})
p.write_text(json.dumps(d, ensure_ascii=False, indent=2))
"
# 但 commit handler 检查 status == 'draft_awaiting_confirm', 改 status 后调 commit-from-draft
# 注意: badge_exists() 检查会冲突, 旧数据已 DELETE, 不会冲突

# 3. 调 commit
curl -s -X POST http://localhost:8765/config/api/badge/commit-from-draft \
  -H "Content-Type: application/json" \
  -d '{"draft_id": "2026-06-15_assign_pal_517548"}' | python3 -m json.tool
# 期望 ok: True, image_url: /static/badges/assign_pal_v2.png

# 4. 验文件
ls -la src/kid_app/static/badges/assign_pal_v2.png
curl -sI http://localhost:8765/static/badges/assign_pal_v2.png | head -3
# 期望 200

# 5. 验 DB
sqlite3 data/dizi.db "SELECT * FROM achievement_badges WHERE achievement_id='assign_pal';"
sqlite3 data/dizi.db "SELECT id, name, description, stat_logic FROM achievements WHERE id='assign_pal';"
# 期望 description = zh_story 全文, stat_logic = ''

# 6. .tmp 清理
ls data/lib/badge_data/.tmp/
# 期望空 (v2.png 也被清)

# 7. 浏览器 sanity check
open http://localhost:8765/badges
# 看图是不是 "批改小帮手", 点开 modal 看 desc/cond 是不是 zh_story 全文
```

## 文件清单

| 文件 | 改动 |
|---|---|
| `src/kid_app/routes/badge_workflow.py` | 改 4 处 (commit handler 用 image.version, description=zh_story, stat_logic="") |
| `src/kid_app/templates/config-badge.html` | UI 文案误导修 + 加 tooltip `?` 图标 + GSAP fade-in + 改背景色 (Bug 3 短期缓解) |
| `tests/test_badge_commit_version_sync.py` | 新文件, 4 test cases |
| `tests/test_badge_commit_meta_mapping.py` | 新文件, 3 test cases |
| `docs/badge-workflow.md` | 补 "已知问题" 一节, 记 6 个 bug 状态 (Bug 3 未修, calc 单独提 PR) |

## PR 拆分 (按 dizical-feature-workflow-pr-sanity-checklist skill)
1. **PR 1 - fix**: 改 routes/badge_workflow.py + 新增 7 pytest → core bug fix
2. **PR 2 - ui**: 改 config-badge.html (tooltip + 文案 + 背景色) → UX 改善
3. **PR 3 - docs**: 改 docs/badge-workflow.md → 知识沉淀

每 PR 独立 branch, 独立 pytest, dad 手动 merge。

## 风险
- 改动 `commit-from-draft` 行为是 hot path, 需保证**回归测试**完整 (旧 commit 流程不动, 只在顶层/image.version 不一致时切换到 image.version)
- draft `2026-06-15_assign_pal_517548` 顶层 version=1, image.version=2 这种"不一致"是 bug 临时态, 修完后所有 draft 一致, 老 user 之前已 commit 的 badge 不受影响 (走 achievement_badges 表 url, 不读 draft)

## 已知不修 (followup issues)
- **Bug 3** (去背景差): 需评估 rembg / bria-rmbg / 提示工程三种方案, 单独提 issue
- **Bug 2 calc 接入**: `assign_pal` 没 calc 规则, locked 是预期。`/calc-apply` skill 走单独 PR 提 calc 逻辑

## 收尾
- recommit 完验过后, 更新 issue 文档标 6 个 bug 全部关闭
- `docs/badge-workflow.md` 补 "已知问题 + 修复历史" 一节
- Obsidian 镜像双写 plan + 后续修复后双写 issue 关闭记录
