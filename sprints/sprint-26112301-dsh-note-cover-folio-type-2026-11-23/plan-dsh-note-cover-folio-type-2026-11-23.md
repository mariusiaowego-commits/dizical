---
type: sprint
sprint: "26112301"
doc: plan
date: 2026-11-23
---

# 实施计划

1. **CSS 锁高**：`FILL_CSS` 里 `html.cz-fill.cz-feed .ctn-wrap:not(.is-expanded)` 保留折叠高，排除注入的 `height:auto !important`；`.ctn-wrap.is-expanded` 下便签 `position:absolute; bottom:0`。
2. **两档统一结构**：`.card-teacher-note.is-open` 改 flex 列，`.ctn-head { flex:0 0 auto }` 钉顶，`.ctn-body { flex:1 1 auto; overflow-y:hidden }`，落定后加 `.is-scrollable` 才可滚。
3. **状态机**：`toggleTeacherNote()` 读 `dataset.open` 决定方向；`baseH`（`wrap.dataset.collapsedH`）算锁高与可用空间；`dataset.seq` 令牌丢弃过期回调；`transitionend` + 240/180+120ms 超时兜底；不监听 `transitioncancel`。
4. **复位**：`resize` 只在 `innerWidth` 或 `isFeedDeck()` 变化时复位，复位后清 `dataset.collapsedH` 并按需 `pokeFeedReflow()`。
5. **视觉**：去便签自身渐隐 mask，改 1px 内棕线 `inset 0 1px 0 rgba(160,66,23,.30)` + 收紧上投影。
6. **票夹字号**：`@media (max-width:480px)` 覆盖 `.pk-folio-*` 字号与 pill 高度；补 `.pk-stub-more-btn` 原有缺失样式。
7. **测试**：新增 `test_teacher_note_toggle_behaviour`（Node 驱动状态机，含半途重开）；更新版本契约到 v3.57。
8. **验证与交付**：`node --check`、`pytest`、8765 上 Playwright 复核 440/1133/390，PR + agy 独立 audit。

## 不做

- 不重写 `formatNoteBlocks()` 解析。
- 不改 Q 卡三层结构与宿主摘壳（v3.56 已定）。
