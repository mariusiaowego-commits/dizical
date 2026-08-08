---
date: 2026-08-08
status: active
sprint: 26080801
related: stage-print-ipadmini-and-image-export-2026-08-01.md
tags: [stage-print, ipad-safari, pdf, beforeprint, waza]
---

# stage-print iPad Safari PDF 完整输出 (sprint 26080801)

## 1. 根因：iPad Safari WKWebView 忽略 `@page` 尺寸

**症状**: `/report/stage-print` 表格视图 iPad Safari 横屏屏上不可读，iPad Safari 导出 PDF 内容不全 (1 页只剩 4/6 天 + 长 URL 残片)。

**修前证据** (pdftotext + pymupdf 抽取 `/tmp/ipad-stage16-before.pdf` 和 `/tmp/mac-stage16-before.pdf`):

| 维度 | iPad PDF | Mac PDF |
|---|---|---|
| 页面尺寸 (rect) | **595×841 (A4 portrait)** | **1191×841 (A3 landscape)** |
| 含月日标签 | 0 个 (CJK 字体映射丢失) | 6 个 (7/27-8/1) |
| "数据: 展示6/6 天" | y=418 (中段) | y=580 (页底) |
| 长 URL 残片 (`dizical-prod-283401`) | **1 次** | 0 次 |

**关键发现**: iPad Safari 输出的 PDF 是 **A4 portrait 595×841**, 不是 `stage-print.html` 里设的 `@page { size: A3 landscape; margin: 0 }`。iOS Safari 的打印走自己的 `UIPrintInteractionController`, 对 `@page` CSS 属性的支持不完整或不应用到打印上下文。

**验证法**:
```python
import pymupdf
doc = pymupdf.open('/path/to/exported.pdf')
print(doc[0].rect)  # 595.2755737304688, 841.8897705078125 = A4 portrait
#                     1191.1199951171875, 841.9199829101562 = A3 landscape
```

## 2. 修法：beforeprint 兜底改 paper 元素尺寸

CSS `@page` 在 iOS Safari 上不可靠, 必须用 JS `beforeprint` 事件直接改 paper 元素尺寸:

```javascript
function applyPrintPaperFix() {
  if (viewMode !== 'table') return;
  var isLs = true;
  var wMm = isLs ? 420 : 210;
  var hMm = 297;
  paper.style.width = wMm + 'mm';
  paper.style.minHeight = hMm + 'mm';
  paper.style.maxWidth = 'none';
  paper.style.maxHeight = 'none';
  paper.style.margin = '0';
  paper.style.overflow = 'visible';
  var t = paper.querySelector('table.matrix');
  if (t) {
    t.style.tableLayout = 'fixed';
    t.style.width = '100%';
  }
}
function clearPrintPaperFix() {
  paper.style.width = '';
  paper.style.minHeight = '';
  // ... 还原
}
if (window.matchMedia) {
  window.addEventListener('beforeprint', applyPrintPaperFix);
  window.addEventListener('afterprint', clearPrintPaperFix);
}
```

## 3. 屏上 iPad 横屏 viewport ≤ 1180px 自适应

iPad 横屏 viewport 1133px (CSS px), paper CSS 宽度 420mm ≈ 1588px, paper 被父容器压回 1133px; colgroup 短列 2% 折算 22px ≈ 5mm 不可读.

**修法**: `@media (max-width: 1180px) { .paper.is-table.is-landscape { width: 100% } }` + `.view-table-wrap { overflow-x: auto }` 让矩阵外层可横滚. Mac Chrome (viewport > 1180px) 仍走 420mm 完整布局, 零退化.

## 4. `preparePrintZoom` floor 0.95 (从 0.65 改)

iPad Safari 上 `paper.zoom` 在 print 上下文支持不完整, 之前的 `floor = 0.65` 让 iPad Safari 把内容压到 65% 不可读. 改 `floor = 0.95` 后"宁可不缩也别压", 长 stage 自然分 2 页. Mac Chrome 不受影响 (zoom 支持完整, scale 通常 = 1).

## 5. 跟 sprint 26080103 的关系

- sprint 26080103: 关 `table-layout: fixed` + 加 min-width 8mm + 不限高 (针对 iPad mini 屏上不可读 + 表格自然撑高)
- sprint 26080801: iPad Safari 打印 `@page A3 landscape` 失效兜底 + 屏上 viewport 自适应 (针对 iPad Safari PDF 截断)
- 两个 sprint 叠加, 不冲突. sprint 26080103 的 min-width 8mm / break-inside: avoid 全部保留

## 6. 沉淀

- 新 reference: `references/stage-print-ipad-safari-pdf-2026-08-08.md` (本文件)
- 新单测: `tests/test_stage_print_pdf.py` (10 个, 含 beforeprint 兜底验证)
- 决策日志: 写入 tqob `sprints/decision-log.md` "iPad Safari WKWebView 忽略 @page, 必须 beforeprint 兜底"

## 7. 验收 Checklist (给 dad 真机验证)

- [ ] iPad Safari 横屏打开 `http://<mac-ip>:8765/report/stage-print?stage_order=16&view=table`
- [ ] 屏上 6 天矩阵完整, 列宽 ≥ 5mm, 可横滑
- [ ] 点 "打印 / PDF" → iOS 打印对话框 → 存储到文件 → 把 PDF 拿到 Mac
- [ ] Mac 跑 `python3 /tmp/extract_pdf_blocks.py /path/to/ipad-after.pdf`
  - page size 应接近 **1191×841 (A3 landscape)** 而不是 595×841 (A4 portrait)
  - 含月日 6 个 (7/27-8/1)
  - "数据: 展示 6/6 天" 在 y=580 附近 (页底)
  - 没有长 URL 残片
- [ ] Mac Chrome 同 URL 走一遍, PDF 仍是 A3 landscape 1191×841 (零退化)