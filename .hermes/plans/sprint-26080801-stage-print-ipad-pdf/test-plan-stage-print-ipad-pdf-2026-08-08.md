---
id: 26080801
type: test-plan
version: 1.0.0
date: 2026-08-08
status: active
related_sprint: "[[sprint-26080801-stage-print-ipad-pdf-2026-08-08]]"
tags: [sprint-26080801, stage-print, ipad, pdf, test]
---

# Test Plan — stage-print iPad 适配 + iPad Safari PDF 完整输出

## 1. 单测（6 个，文件 `tests/test_stage_print_pdf.py`）

| ID | 名称 | 验证 | 失败模式 |
|---|---|---|---|
| T1 | `test_paper_css_responsive_max_1180` | `@media (max-width: 1180px) .paper.is-table.is-landscape { width: 100% }` 存在 | iPad 横屏 paper 仍 420mm 硬限 |
| T2 | `test_paper_css_print_max_width_420` | `@media print .paper.is-landscape { max-width: 420mm }` 存在 | 打印上下文 paper 越界 |
| T3 | `test_matrix_print_fixed_layout` | `@media print table.matrix { table-layout: fixed !important }` 存在 | 打印上下文列被 flex 压 |
| T4 | `test_colgroup_short_w_2_8_for_6_days` | `shortW = ... 2.8 : 2.4` 字面量 | 6 天矩阵短列 2% → iPad 上 < 5mm |
| T5 | `test_prepare_print_zoom_floor_0_95` | `if (scale < 0.95) scale = 0.95;` 字面量 | zoom 压内容到 65% 不可读 |
| T6 | `test_sync_paper_mode_hint_text` | "屏上可横滑 · 打印按内容自动分页" 文案 | 状态条误导 |

## 2. 集成验证（手测 / dad 真机）

### 2.1 Mac Chrome

```
URL: http://localhost:8765/report/stage-print?stage_order=16
操作: 工具条选 Stage 16 → 表格视图 → 全选 6 天 → 确认展示
屏上验证: 6 天矩阵完整, 矩阵行高 8mm, 列宽合理
打印操作: Cmd+P → 保存 PDF 到 /tmp/mac-stage16-after.pdf
PDF 验证: pdftotext /tmp/mac-stage16-after.pdf 应含 6 个日期 (7/27 7/28 7/29 7/30 7/31 8/1) + 页脚 "展示 6/6 天"
```

### 2.2 iPad Safari

```
URL: http://<mac-ip>:8765/report/stage-print?stage_order=16 (LAN) 或 http://<tailscale>:8765/...
操作: 同 Mac, 选 6 天 → 打印 → 存储到文件
iPad 屏上验证: paper 占满 viewport, 矩阵外层可横滑
iPad PDF 验证: 通过 Tailscale file cp 或微信传文件把 PDF 拿到 Mac, pdftotext 验证 6 天 + 页脚
```

### 2.3 对比证据

| 证据 | 修前 | 修后 |
|---|---|---|
| Mac PDF | /Users/mt16/Downloads/竹笛练习明细 · Stage 16 · 表格2.pdf (228K, 6/6 天) | /tmp/mac-stage16-after.pdf |
| iPad PDF | /Users/mt16/Downloads/竹笛练习明细 · Stage 16 · 表格.pdf (158K, 4/6 天) | /tmp/ipad-stage16-after.pdf |
| pdftotext 第 1 页 | Mac: 6 天完整 / iPad: 4 天 + 长 URL 残片 | 都 6 天完整 + 页脚 |

## 3. 回归验证

- [ ] sprint 26080103 min-width 8mm 保留: `grep -n "min-width: 8mm" src/kid_app/templates/stage-print.html` 仍 ≥ 1 处
- [ ] sprint 26080103 break-inside avoid 保留: `grep -n "break-inside: avoid" src/kid_app/templates/stage-print.html` 仍 ≥ 2 处
- [ ] sprint 26080103 table-layout: auto 屏上保留: `grep -n "table-layout: auto" src/kid_app/templates/stage-print.html` 仍 ≥ 1 处
- [ ] 全量 pytest `pytest -q --tb=no 2>&1 | tail -3` 净零回归（基线 0 failed）

## 4. 验证脚本（不直接跑，列在 plan 阶段）

- 单测: `uv run --project /Users/mt16/dev/dizical pytest tests/test_stage_print_pdf.py -q`
- 重启: `./scripts/stop-prod.sh && ./scripts/start-prod.sh && lsof -nP -iTCP:8765 -sTCP:LISTEN`
- 屏上: 浏览器打开 `/report/stage-print?stage_order=16`
- PDF: Mac Cmd+P / iPad Safari 分享 → 存储到文件 → pdftotext

## 5. 失败标准

任何 1 项不通过:
- T1-T6 任一失败 → 修代码 + 重跑
- Mac PDF 退化（缺天 / 缺页脚）→ 修 + 重打
- iPad PDF 仍 4/6 天 → 修 `@media print` CSS + `--print-zoom` 算式
- pytest 净零失败数变化 → 修 regression
