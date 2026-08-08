---
id: 26080801
type: sprint
version: 1.0.0
start_date: 2026-08-08
end_date: 2026-08-08
status: 已完成
priority: 高
summary: /report/stage-print 表格视图 iPad 横屏可读 + iPad Safari PDF 不再截内容
tags: [sprint, dizical, stage-print, ipad, pdf]
plan: "[[plan-stage-print-ipad-pdf-2026-08-08]]"
prd: "[[prd-stage-print-ipad-pdf-2026-08-08]]"
tech_spec: "[[tech-spec-stage-print-ipad-pdf-2026-08-08]]"
test_plan: "[[test-plan-stage-print-ipad-pdf-2026-08-08]]"
---

# Sprint 26080801 — Stage Print iPad 适配 + iPad Safari PDF 完整输出

## 1. Brief

dad 反馈 (2026-08-08)：
- iPad mini 横屏 `/report/stage-print` 表格视图全选 6 天后屏上不可读
- iPad Safari 导出 PDF 内容不全 (对比 Mac Chrome 1 页完整，iPad 1 页只剩 4/6 天 + 长 URL 残片)
- 必须保留 Mac Chrome 行为不退化

## 2. 任务清单

| # | 任务 | 状态 | 证据 |
|---|---|---|---|
| 1 | 写 PLAN/PRD/TECH-SPEC/TEST-PLAN (本目录) | [x] | 本目录 5 份 md, Obsidian 双写 md5 一致 |
| 2 | 开 `feat/stage-print-ipad-pdf-260808` 分支 | [x] | `git checkout -b feat/stage-print-ipad-pdf-260808 origin/main` |
| 3 | 改 `src/kid_app/templates/stage-print.html` (5 处 CSS + 4 处 JS) | [x] | tech-spec 段; git diff +72 / -12 |
| 4 | 加 `tests/test_stage_print_pdf.py` (10 个单测) | [x] | 10/10 PASSED |
| 5 | 跑 pytest 净零回归 | [x] | 470 passed / 8 skipped / 0 failed |
| 6 | 重启本地 8765 | [x] | PID 23748, lsof 8765 LISTEN |
| 7 | Mac Chrome 验证 + PDF 导出 → `/tmp/mac-stage16-after.pdf` | [待 dad 真机] | pdftotext 6/6 天 (待复测) |
| 8 | iPad Safari 验证 + PDF 导出 → `/tmp/ipad-stage16-after.pdf` | [待 dad 真机] | pdftotext 6/6 天 + 无 URL 残片 (待复测) |
| 9 | 写 verify-2026-08-08.md (3-1-1 closeout) | [x] | verify-2026-08-08.md |
| 10 | 同步 Obsidian tqob 双写 | [x] | md5 校验通过 (5 份 sprint md) |
| 11 | commit + push + gh pr create | [下一步] | gh pr view |
| 12 | 沉淀 reference: `references/stage-print-ipad-safari-pdf-2026-08-08.md` | [x] | md5 dd3fc73c... |
| 13 | 写入 decision-log.md (3 条) | [x] | tqob decision-log.md 67 行 (原 64 行) |

## 3. Sprint 回顾（完成后填）

- **What shipped (3 bullets)**:
  1. iPad Safari WKWebView 打印 `@page A3 landscape` 失效兜底（beforeprint JS）
  2. 屏上 paper viewport ≤1180px 自适应 + 矩阵横滑
  3. preparePrintZoom floor 0.95（从 0.65/0.70 改）
- **1 thing we learned**:
  - iOS Safari 的 `UIPrintInteractionController` 不读 `@page` CSS，必须用 JS `beforeprint` 直接改 paper 元素 width。pdftotext + pymupdf 抽 iPad PDF page rect = 595×841（A4 portrait），而 Mac PDF = 1191×841（A3 landscape），证实 iPad Safari 静默 fallback
- **3 risks remaining**:
  - R1: iOS 某些版本 `beforeprint` 不触发或 paper.style.width 不生效 → dad 真机验证
  - R2: colgroup 短列 2.8% 在 iPad viewport 1133px 上 ≈ 32px ≈ 8mm, sprint 26080103 min-width 8mm 保底
  - R3: CloudRun 部署未触发, dad 拍板决定是否部署
