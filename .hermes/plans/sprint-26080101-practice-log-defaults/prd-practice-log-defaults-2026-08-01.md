# PRD — /config/practice-log 选中科目后展示 session 细节 + 默认速度

**Sprint**: 26080101
**Date**: 2026-08-01
**Status**: 待开发

---

## 背景

dad 在 `/config/practice-log` "录入练习" Tab 录入练习时, 每个科目要重新填:
- 速度 (♪/♩ + BPM)
- 练什么 (自由文本)

但其实 `/practice` 页已经做了智能默认填充:
- 选中科目后从"老师要求" / "上次练习" / "默认" 取 BPM + 音符
- 渲染 BPM 预设按钮 (60/80/100/120 fallback)
- 渲染 content 预设标签 (`practice_items.content_options`, fallback 4 个通用)

practice-log 跟 practice 录入的是同一份数据 (`daily_practices` / `practice_sessions`), 但 UX 不一致, dad 抱怨"为什么 practice-log 没有像 practice 一样自动展示? 每次要手动填太烦了".

## 用户故事

> 作为 dad, 我在 `/config/practice-log` 录入补录练习时, 选完科目后点 "应用默认" 按钮,
> 系统自动显示该科目上次练习的速度/预设标签, 我可以一键点击填充, 不再需要回忆 + 手动键入.

## 功能需求

### F1. 速度默认值按钮
每条科目行右边加 "应用默认" 小按钮. 点击后:
- 拉 `/api/assignments/latest?item_id=X` → 有结果用它的 tempo_note + tempo_bpm, hint 显示 "老师要求"
- 否则拉 `/api/practice-sessions/latest?item_id=X` → 用它, hint 显示 "上次"
- 否则 ♪=80, hint 显示 "默认"

### F2. 速度控件升级
BPM 输入从 `<input type="number">` 升级为 stepper:
```
[−] 80 [+]
```
+ 下面一行 BPM 预设按钮 (从老师要求取 1 个 + fallback 60/80/100/120 合并, 去重, ≤5 个).

### F3. content 预设标签
content 输入框上方一行 chip-style 按钮:
- 从 `practice_items.content_options` (逗号分隔) 拆
- fallback: 长音 / 吐音 / 连吐 / 换气
- 点击 → 替换 content 输入框内容

### F4. 多行隔离
多条科目行同时存在时, presets/tags/hint 各自按 `data-idx` 隔离渲染, 不串行.

### F5. 防误覆盖
用户手填了 content 或 BPM 后, 再点 "应用默认" 弹 `confirm()` 确认覆盖 (避免手填丢失).

## 非功能需求

- 后端 0 改动 (所有 API 已存在)
- 仅 `src/kid_app/templates/config-practice-log.html` 1 个文件
- PC 优先 (dad 用 Mac, 不做 iPad 响应式特殊处理)
- 不改提交逻辑, 不改数据库结构

## 验收标准

| # | 场景 | 通过条件 |
|---|------|---------|
| 1 | 选 "西藏舞曲" (有老师要求 ♩=82) → 点应用默认 | BPM = 82, 音符 = ♩, hint = "老师要求", presets 含 82 |
| 2 | 选 "长音" (无要求但有历史 ♪=75) → 点应用默认 | BPM = 75, 音符 = ♪, hint = "上次", presets 含 75 |
| 3 | 选 "新科目" → 点应用默认 | BPM = 80, 音符 = ♪, hint = "默认", presets = [60,80,100,120] |
| 4 | content_options = "吐音,连吐,双吐" → 标签点击 "连吐" | content 输入框 = "连吐" |
| 5 | 同时录 2 科目, 各自点应用默认 | 行 1 速度 = 老师要求, 行 2 速度 = 上次, 互不串 |
| 6 | 已手填 "速度=90 内容=分句练习" → 点应用默认 | 弹 confirm "将覆盖已填值, 继续?", 取消则不动 |

## 不做

- 不动 `/practice` (主页面已经实现)
- 不动"老师要求" / "本周总览" 2 个 tab
- 不改 `/api/log` 提交逻辑
- 不加历史回放 (从已有 session 自动回填) — 那是下期

## 风险

| # | 风险 | 缓解 |
|---|------|------|
| 1 | 多行 selectors 串行 | 用 `[data-idx="X"]` 严格隔离 |
| 2 | 频繁切科目 N 次 fetch | `_entryDefaultsLoaded[itemId]` cache |
| 3 | 跟主仓练习同时混用同一 API | `_DEDUP_WINDOW_SECONDS = 5` 已保护, 不冲突 |