# Plan — /config/practice-log 选中科目后展示 session 细节 + 默认速度

**Sprint**: 26080101 (2026-08-01 第 1 个)
**类型**: UI 增强 (录入辅助)
**Appetite**: 半天

---

## 目标

`/config/practice-log` "录入练习" Tab 选科目后，跟 `/practice` 页一样:
1. 自动填默认速度 (♪/♩ + BPM), tempo hint 显示来源 ("老师要求" / "上次" / "默认")
2. 自动渲染 BPM 预设按钮 (从该科目最新老师要求的 BPM, fallback 60/80/100/120)
3. 自动渲染 content 预设标签 (从 `practice_items.content_options` 拆), 点击 → 填入 content 输入框
4. **触发时机**: 加"应用默认"按钮, 用户点才填 (怕覆盖用户手填的内容) — **Q4=C 拍板**

## 拍板 (Q1-Q4)

| # | 问题 | 选项 | dad 拍板 |
|---|------|------|----------|
| Q1 | BPM 控件长什么样 | A 完全复用 practice 的 bpm-stepper (-/+) + presets / B 继续 mini number input | **A** |
| Q2 | content 预设标签点击行为 | A 替换 / B 追加 / C 多选 | **A** |
| Q3 | 默认速度来源优先级 | A 老师要求 → 上次 → ♪=80 / B 只上次 / C 只默认 | **A** |
| Q4 | 触发时机 | A 自动生效 / B 第一次 / C 加按钮 | **C** |

## 改动范围

**只动 1 个文件**: `src/kid_app/templates/config-practice-log.html`

| 行 | 现状 | 改成 |
|----|------|------|
| CSS ~502-520 (`.log-tempo-row` block) | 1 个 number input | 加 bpm-stepper (-/+) + presets 容器 + tags 容器样式 |
| JS ~793-866 (`renderLogEntries`) | mini 控件 + 3 个事件 | 加 "应用默认" 按钮 + 调 `fillEntryDefaults(idx)` + presets + tags 渲染 |
| 新增 JS | - | `fillEntryDefaults(idx)`: 复用 practice 的 3 fetch 链 → applyTempo → renderBpmPresets → renderContentTags |
| 新增 JS | - | `renderEntryBpmPresets(idx, itemId)`, `renderEntryContentTags(idx, itemId)` (从 practice copy + 微调多行支持) |

**不动**:
- 后端 API (全部已有: `/api/assignments/latest`, `/api/practice-sessions/latest`, `practice_items.content_options`)
- 提交逻辑 (`submitLogBtn`)
- 其他 2 个 tab

## 与 practice 页的复用原则

practice 的 `fillSessionDefaults` / `renderBpmPresets` / `renderContentTags` 操作单 panel 元素 (`#sessionPanel` / `#tempoNoteQuaver` 等), 不直接复用。
**做法**: copy 3 个函数 → 重命名为 `fillEntryDefaults(idx)` / `renderEntryBpmPresets(idx, itemId)` / `renderEntryContentTags(idx, itemId)`, 把 `#sessionPanel` 单例 DOM 改为 `.log-entry-row[data-idx="${idx}"]` 子元素查询。

## 风险

- **R1**: 多行同时存在时, presets/tags 渲染要按 idx 隔离, 不能串到别的行 (用 data-idx selector)
- **R2**: 多次切科目频繁 fetch, 加 `__entryDefaultsLoaded[itemId]` cache (跟 practice `_defaultTempoLoaded` 同模式)
- **R3**: practice.html V4 紧凑模式在窄屏缩小 stepper, practice-log 不用 (录入页是 PC 优先, 不用压窄)
- **R4**: "应用默认" 按钮点击前用户已经手填了 BPM/content, 提示 "将覆盖你已填的值, 继续?" (可选确认)

## 验证

- [ ] 选中已有老师要求的科目 → 点 "应用默认" → BPM 跟老师要求一致, hint 显示 "老师要求"
- [ ] 选无老师要求但有历史的科目 → BPM = 上次, hint 显示 "上次"
- [ ] 选全新科目 → BPM = 80, hint 显示 "默认"
- [ ] BPM 预设按钮可点击, 数值落入输入
- [ ] content 预设标签可点击, 内容填入输入框
- [ ] 切换不同科目行互不干扰
- [ ] 用户已手填 content → 点 "应用默认" 提示确认

## 非目标

- 录入学时/补录 (`/practice` tabTimer/tabExtra) — 不动
- `/api/log` 提交逻辑 — 不动
- 老师要求录入 tab — 不动
- 历史回放 (回填到 session 输入) — 不动 (本期只覆盖"录入"tab 的新建)