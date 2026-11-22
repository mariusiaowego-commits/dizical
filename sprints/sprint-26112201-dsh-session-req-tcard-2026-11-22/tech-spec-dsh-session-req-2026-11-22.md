---
type: sprint
sprint: "26112201"
doc: tech-spec
date: 2026-11-22
---

# 技术方案

## 数据契约（零 schema 变更）

- `practice_items.content_options`：JSON 数组 `[{name,bpm,note,requirement}]`；历史逗号/换行文本仍可解析。
- `weekly_assignments.items[]`：可选 `sessions` 同结构；落库时同步生成 `metronome`（`♩=60 / ♪=98`）与 `requirements` 文本，老消费者不改也能读。
- 合法范围：BPM 40–200（非法直接 400），note ∈ `♩/♪/♬`，名称 ≤50 字，要求 ≤200 字，最多 20 个环节。

## BPM 解析

- 先匹配 `[♩♪♬]\s*=\s*(\d{2,3})`；没有显式速度时取最后一个 40–200 的数字。
- 修复历史名称 `80乐段 ♪=90` 被前缀 80 抢走的问题（`src/practice.py:28`、`practice-dsh.html` 的 `extractBpm`）。

## API

- `PUT /config/api/practice/items/{id}/content-options`：接受 `sessions` 或 `content_options`；响应回 `sessions`。
- `GET /config/api/practice/items`、`GET /api/items`、`GET /config/api/assignments`、`GET /config/api/assignments/by-item`：补 `sessions`；assignment 优先记录内 sessions，否则按 item_id/名称回落科目预置。

## 练习助手

- `activeSessionList/getSessionByName/resolveSessionTempo/applySessionTempo` 统一速度真源；`pushTempoToFrames` 同步总线、广播、A 卡与露出条。
- `getSessionByName` 两侧都经 `cleanSessionText`，避免 `吹高音“6”` → `吹高音6` 的解析差异导致查不到环节。
- `buildPracticeLogBody` 直接读全局 `bpm/noteIdx/content`，不再自带默认速度。

## Q 卡

- 删 `.qc-item.is-hero`。
- `sessionBlocks` 三档：结构化 requirement → 名称归属（剥速度/引号后比核心名，多环节至少命中 2 个）→ 编号清单。
- `.deck-footer-bar` 在 `.deck-card` 内，`margin-top:auto` + 浅底 + 顶线；16 点时换行，按钮 `margin-left:auto` 右对齐；dot 固定 6px，active 用 `scale(1.25)`。
- 描边：`.deck-card{border:0;background-clip:padding-box}` + `::before` 1px（light `rgba(44,62,80,0.22)`；ink `rgba(222,215,205,0.28)`）；`.cz-mod[data-mod="Q"] > iframe{border-radius:0}`。
- 翻页：`navTo()` + `isAnimating` 门闩，按钮/指示点/拖拽共用。

## T 卡

- `buildTCard` 原生 DOM（`cz-t-head/hero/num/goal/list/row/foot`），无 iframe。
- `refreshTCard` 从 `pkRecords`、`.pk-drawer-item`、`pkCollapsedProgressVal` 反读；`applyDayToModules` 末尾重建后刷新。
- 高度 `lockCol(tcard, H)`；窄档 `.cz-tcard{display:flex;min-height:300px}`，不再 `display:contents`。
