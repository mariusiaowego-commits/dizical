# Badge V2.2: cond_text 字段 + AI 生成 (B 方案, 3 态 UX) 实施 Plan

> **For Hermes:** 用户 2026-06-15 提出新需求: modal-cond 跟 modal-desc 当前都用 zh_story (Bug ❺ 修法), 文案重复. 需要分开: cond = 条件一句话 / desc = 典故小故事. 用户选 B 方案: 手填 + AI 生成, AI 生成后可看可改可删可再生.

## Goal
**用户开发新 badge 时, 表单多 1 个 "条件文案 (一句话)" 字段, 可手填可 AI 生成. AI 生成的文案不锁死, 用户能改能删能再生. modal 弹窗里 modal-cond 显示条件文案, modal-desc 显示典故小故事, 两个独立.**

## 验收标准 (老话: 3 岁小孩能听懂)
1. ✅ 表单多 1 个字段 "条件文案", **留空 = 走 AI** (点 AI 按钮就生成)
2. ✅ AI 生成 → 填到 textarea → 不好可点一次再生 / 删掉手填 / 直接提交走 fallback
3. ✅ modal 弹窗里 **modal-cond ≠ modal-desc** (分开显示)
4. ✅ 留空提交 → 走 `cond_text || description` fallback (不破现状)
5. ✅ 老 badge 数据 (没 cond_text 列) 不报错, 走 calc / desc 兜底

## 当前状态 (实查)
- 2026-06-15 PR #98 已 merge (Bug ❶❷❸❹❺❻ 修) — main @ `604a08c`
- 服务 8765 跑新代码, 旧 7 bug 修代码生效
- modal-cond 走 `data-cond || data-desc` (Bug ❺ 修法)
- cond_text 字段**不存在** (需要新增)
- achievements 表**没 cond_text 列** (需要 migration)
- LLM 帮手 `subject_info._gemini_stream` 已有 (line 42, 流式 Gemini 2.5 Flash-Lite)

## 设计

### 字段
- **meta 增 `cond_text`** (可选) — 跟 `zh_story` 并列, 不进 required
- **DB `achievements` 加 `cond_text TEXT` 列** — migration 创
- **前端 dataset 多 `cond-text` 属性** — 从 achievements.cond_text 读

### 3 级 fallback 链
```
modal-cond 显示 =
  res.condition        ← calc 接入后 (最高)
  ?? user_cond_text    ← achievements.cond_text (用户/AI 填)
  ?? description       ← zh_story 兜底 (现状)
```

### 后端 1 个新端点
- `POST /config/api/badge/ai-cond` 收 `{name, placeholder, zh_story, type}` → 调 `_gemini_stream` 流式生成 → 返 `{ok: true, cond_text: "..."}`

### 前端 UI 改造
- `config-badge.html` 大白话 tooltip 体系加 1 条 "条件文案"
- 新增 1 个 textarea 字段 + 1 个 "✨ AI 生成" 按钮
- AI 按钮 loading/失败/成功 3 态

### 渲染 3 处改
- `badges.html:357` `dataset.cond || dataset.condText || dataset.desc`
- `achievements.html:600` 同上
- `_milestone_html` + `_badges_page` 后端拉 `cond_text` 进 dataset

## 实施步骤 (TDD 优先, 逐步验证)

### Step 1: Worktree 隔离 (主仓 8765 不动)
- `git worktree add -b feat/badge-cond-text /Users/mt16/dev/dizical-8769 main`
- 端口 8769 隔离, 跑测试不污染主仓

### Step 2: DB migration (achievements 加 cond_text 列)
- `src/migrate_add_cond_text.py` (新)
- 不可 DROP 表, 只 `ALTER TABLE achievements ADD COLUMN cond_text TEXT`
- 跑 worktree migration 测试 OK
- `tests/conftest.py` 加 `cond_text` 列 (worktree 创表同步)

### Step 3: draft meta schema 增 cond_text 字段 (Step 1 之前)
- `src/kid_app/badge_draft.py:133` required 字段不变 (cond_text 可选)
- `meta` dict 加 `cond_text` 字段自动落到 BadgeDraft
- 无代码改动, 仅 schema 文档说明

### Step 4: TDD 写 pytest
- `tests/test_cond_text_meta_mapping.py` (新, 4 cases)
  - test_cond_text_writes_to_db
  - test_missing_cond_text_writes_empty_string
  - test_empty_cond_text_writes_empty_string
  - test_existing_achievement_no_cond_text_no_error (老数据兼容)
- 跑 → **RED** (commit handler 还没改)

### Step 5: commit handler 改 — 写 cond_text 进 db
- `src/kid_app/routes/badge_workflow.py:155-156` 区域
- `meta_for_db["cond_text"] = meta_for_db.get("cond_text") or ""`
- 跟 description/stat_logic 一起处理
- 跑 → **GREEN**

### Step 6: 新端点 POST /config/api/badge/ai-cond
- `src/kid_app/routes/badge_workflow.py` 加路由
- 复用 `subject_info._gemini_stream` (已有)
- prompt: "Badge 名称: X, 类型: Y, 英文描述: Z, 中文典故: W. 生成一句话条件文案 (≤30 字, 解释孩子为什么能获得这个徽章)."
- 流式返回(可选)或简单返 text
- 失败返 500 + error

### Step 7: TDD 写 ai-cond 端点 pytest
- `tests/test_ai_cond_endpoint.py` (新, 3 cases, mock LLM)
  - test_ai_cond_returns_text
  - test_ai_cond_handles_llm_failure
  - test_ai_cond_validates_required_fields
- 跑 → **GREEN**

### Step 8: config-badge.html 加 UI
- 大白话 tooltip dict 加 `v21CondText: "弹窗里 '达成条件' 显示的一句话. 留空 = 走 AI / fallback 兜底"`
- 新增 `<textarea id="v21CondText" name="cond_text" rows="2" placeholder="例: 练习任意 1 天里包含 '批改' 关键词">`
- 旁边 `<button type="button" id="v21AiCondBtn">✨ AI 生成 (基于典故)</button>`
- JS 调 `/config/api/badge/ai-cond` → 填 textarea
- 3 态: idle ("✨ AI 生成") / loading ("⏳ AI 思考中...") / done ("✓ 已生成, 可改")

### Step 9: 渲染 3 处 — 3 级 fallback
- `badges.html:357` `card.dataset.cond || card.dataset.condText || card.dataset.desc`
- `achievements.html:600` 同上
- `app.py:1455 badges_page` 拉 `cond_text` 进 dataset
- `app.py:509 _build_milestone_card` 第 9 参 `cond` 改成 `user_cond_text or res.condition or desc`

### Step 10: 全量 pytest
- `pytest tests/ -q` → 期望 255+ passed (原 252 + 4 + 3 - 重复 case)

### Step 11: Worktree 启 8769 服务 + 端到端
- 启 8769 (uvicorn)
- 浏览器 `/config/badge` 测:
  - 填 placeholder + zh_story → 点 AI 按钮 → 看流式填入
  - 改文字 → 提交
  - 验 `/badges` modal: cond ≠ desc
- 留空提交 → 验 cond = desc fallback

### Step 12: commit + push + PR
- `git commit -m "feat(badge): cond_text 字段 + AI 生成 (modal-cond 跟 desc 分开)"`
- `gh pr create` 标题 `feat(badge): cond_text 字段 + AI 生成`

## 文件清单
| 文件 | 改动 | 行数 |
|---|---|---|
| `src/migrate_add_cond_text.py` | 新, migration | ~30 |
| `src/kid_app/routes/badge_workflow.py` | 改 commit handler + 新 ai-cond 端点 | ~50 |
| `src/kid_app/app.py` | 改 _milestone_html + badges_page 拉 cond_text | ~10 |
| `src/kid_app/templates/config-badge.html` | 加 textarea + AI 按钮 + tooltip | ~50 |
| `src/kid_app/templates/badges.html` | 3 级 fallback | ~2 |
| `src/kid_app/templates/achievements.html` | 3 级 fallback | ~2 |
| `tests/conftest.py` | 加 cond_text 列到创表 SQL | ~5 |
| `tests/test_cond_text_meta_mapping.py` | 新, 4 cases | ~150 |
| `tests/test_ai_cond_endpoint.py` | 新, 3 cases | ~100 |

## 风险
- ai-cond 端点调外部 LLM (Gemini 2.5 Flash-Lite), 失败要 graceful 兜底
- 老 achievement 数据无 cond_text 列 → migration 不可 DROP, 用 ALTER ADD (NOT NULL 风险要避免, 默认 NULL)
- 留空 vs 没填的语义不区分 (简单实现) → 用户说 "我没填" 还是 "忘了填" 都一样 fallback

## 已知不修 (followup)
- 流式 SSE 输出 (本期返非流式, 简单)
- AI 按钮 keyboard shortcut
- 历史 cond_text 备份 / 版本管理
