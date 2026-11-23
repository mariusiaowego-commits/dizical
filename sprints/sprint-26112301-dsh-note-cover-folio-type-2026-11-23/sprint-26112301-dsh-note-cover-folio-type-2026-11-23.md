---
type: sprint
sprint: "26112301"
topic: dsh-note-cover-folio-type
date: 2026-11-23
status: 进行中
branch: feat/dsh-note-motion-folio-type
base: bb21318
---

# Sprint 26112301 · 补充说明覆盖式展开 + 微动效 + 票夹手机字号（v3.57）

## 范围

- 老师要求卡（Q 卡）底部「老师补充说明」点「展开全文」时要能展开更多；竖排 feed 允许遮住上方正文（此时重点是补充说明），但卡高与宿主 iframe 高度不变。
- 展开/收起补微动效，支持动画中途反向点击；`prefers-reduced-motion` 直接落定。
- 票夹弹窗（`.pk-folio-box`）在手机视口放大字号，克制且不破坏排版。

## 文档

- `prd-dsh-note-cover-folio-type-2026-11-23.md`
- `plan-dsh-note-cover-folio-type-2026-11-23.md`
- `tech-spec-dsh-note-cover-folio-type-2026-11-23.md`
- `test-plan-dsh-note-cover-folio-type-2026-11-23.md`
- `verify-dsh-note-cover-folio-type-2026-11-23.md`
- `audit-dsh-note-cover-folio-type-2026-11-23.md`（agy 三轮 + pixel 一轮汇总）

## 不做

- 不改 T 卡 Day Rail、A/B/R 卡结构。
- 不动补充说明的解析规则（`formatNoteBlocks` 沿用 v3.56）。
- 不引入新依赖、不改 schema / 公开 API。
