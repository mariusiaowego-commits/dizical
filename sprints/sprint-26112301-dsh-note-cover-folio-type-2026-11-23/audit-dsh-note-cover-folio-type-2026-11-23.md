---
type: sprint
sprint: "26112301"
doc: audit
date: 2026-11-23
---

# 复审汇总

## agy（Antigravity CLI，w56:p1）三轮只读复审

| 轮次 | Verdict | 主要问题 | 处理 |
|---|---|---|---|
| R1 | `BLOCK` | 3 P1 + 4 P2 + 2 P3：feed 短卡回退断链、连点状态机/兜底、横排头部滚动丢失、mask 糊边、resize 不复位、cursor 过宽、测试表演型 | 全部修复 |
| R2 | `BLOCK` | 新回归 P1-A（resize 未过滤纯高度变化，短卡回退展开自毁）、P1-B（半途重开用半途高算 `room`/锁高，顶出底栏）、P2-1（`transitioncancel` 异步误命中新监听）、P3-1（DESIGN.md 过时） | 全部修复 |
| R3 | **`APPROVE`** | 仅 1 条可选 P3：复位快照 `noteResetFeed` 初始化时机早于宿主挂 `cz-feed` | 已在 `setupTeacherNotes()` 末尾同步快照 |

R3 独立复跑：`tests/test_practice_dsh.py` 38 passed、`test_practice_dsh*.py` 67 passed、内联 script 13 段 0 fails、`grep transitioncancel` 0 命中。

## pixel（hermes -p pixel，w56:p2）视觉复审

- 首轮 `NEEDS WORK`：P1 去便签自身 mask 渐隐、P2 标题 18px、P3 `.pk-stub-more-btn` 补样式 + cursor 收窄。
- 落地后转 `PASS`（本轮改动均按 pixel 方案实现）。

## 自查

- 全量 `pytest`：1242 passed / 2 基线 failed / 8 skipped（3 条沙箱限制单列）。
- 真实浏览器复测 440 / 1133 / 390 三档，含收起半途重开。
