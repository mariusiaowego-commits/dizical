---
type: sprint
sprint: "26112201"
topic: dsh-session-req-tcard
date: 2026-11-22
status: 已完成
branch: feat/practice-dsh-session-req-tcard
base: 0cd6874
---

# Sprint 26112201 · 练习助手环节化老师要求 + Q/T 卡重构（v3.54）

## 范围

- 老师要求按「练习环节（session）」结构化：名称 / BPM / 音符 / 环节要求，存 `practice_items.content_options`（JSON）与 `weekly_assignments.items[].sessions`。
- 每个环节的 BPM 联动节拍器、A 卡读数与练习记录载荷，消灭回落 `♪=80`。
- `/config/practice`（科目预置环节）与 `/config/practice-log` Tab2（老师要求）补齐录入 UI。
- Q 卡：第一条要求不再当大标题；环节分组；卡内隔离底栏；卡高与兄弟卡一致；圆角描边；按钮/指示点翻页动画。
- T 卡重构：原生 DOM 看板替代 D+R iframe 拼壳。

## 文档

- `prd-dsh-session-req-2026-11-22.md`
- `plan-dsh-session-req-2026-11-22.md`
- `tech-spec-dsh-session-req-2026-11-22.md`
- `test-plan-dsh-session-req-2026-11-22.md`
- `verify-dsh-session-req-2026-11-22.md`

## 状态

PR #410 squash merge → `e3c5f5d`（2026-11-23）。v3.56 增量（补充说明结构化 + 全站卡片统一外框 + 量高修正）随后经 PR #411 → `7ee4ab9` 落地，归入 sprint 26112202 收尾。
