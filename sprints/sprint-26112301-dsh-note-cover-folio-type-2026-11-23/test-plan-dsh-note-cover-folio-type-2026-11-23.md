---
type: sprint
sprint: "26112301"
doc: test-plan
date: 2026-11-23
---

# 测试计划

## 1. 静态

- `qcard_nodecheck.py`：模板内联 `<script>` 逐段 `node --check`，要求 `fails: 0`。

## 2. 单测

- `tests/test_practice_dsh.py::test_teacher_note_toggle_behaviour`（Node 驱动）：
  - 浮层锁高：展开后 `wrap.style.height` 保持折叠值；
  - 短卡回退：`room < 180` 走 in-flow，`is-expanded` 不挂，settle 后触发 `pokeFeedReflow`；
  - 连点方向：收起中途重开 `dataset.open` 回到 `1`、`is-closing` 被清；
  - 半途重开：mock `offsetHeight = 190`，断言 `wrap.style.height === '100px'`、目标高 ≤ `room`；
  - 不绑 `transitioncancel`；`transitionend` 监听只有 1 个；
  - `prefers-reduced-motion` 瞬时落定且清掉兜底定时器。
- 版本契约：`DSH_VERSION = 'v3.57'`。
- 全量 `pytest tests/ --ignore=tests/config_ui_fixes`，与基线比对。

## 3. UI（8765 + Playwright，DSF=2）

| 用例 | 判据 |
|---|---|
| 440 展开 | 便签高 > 折叠高 ×2；`.ctn-wrap` 高度不变（±1px）；`.deck-card` 高度不变（±1px）；`coversReq: true`；`position: absolute` |
| 440 滚到底 | `.ctn-head` top 与便签 top 差值 < 10px（头部钉住）；`body.scrollTop > 0` |
| 440 收起 | 回到折叠高（±1px），`is-open` 消失，按钮文案「展开全文」 |
| 440 半途重开 | 收起 70ms 后重开：`is-closing === false`，`wrap.style.height` 仍是折叠值，`footerClipped === false` |
| 1133 展开 | 卡高 744 不变；`coversReq: false`；`position: static`；正文区 `overflow-y: auto` |
| 1133 半途重开 | 卡高不变、底栏未被裁 |
| 375 + 深墨 | 展开正常，截图无糊边 |
| 票夹 390 | `docOverflowX <= 0`；标题 18、曲目名 16、pill 13.5/36、mini 12.5/30、分类行 32 |

## 4. 失败模式

- 未跑 / 环境不允许的项标 `skipped` 并写原因，不记 `passed`。
