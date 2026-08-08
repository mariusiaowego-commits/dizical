---
id: 26080801
type: tech-spec
version: 1.0.0
date: 2026-08-08
status: active
related_sprint: "[[sprint-26080801-stage-print-ipad-pdf-2026-08-08]]"
tags: [sprint-26080801, stage-print, ipad, pdf, css, js]
---

# Tech Spec — stage-print iPad 适配 + iPad Safari PDF 完整输出

## 1. 改动文件清单

| 文件 | 行号区间 | 改动 |
|---|---|---|
| `src/kid_app/templates/stage-print.html` | 110-145 (paper CSS), 304-405 (matrix CSS), 415-460 (@media print), 1063-1084 (fillMatrixToPaper), 1099-1110 (fillMatrixForPrint), 1130-1156 (preparePrintZoom), 727-742 (syncPaperMode) | 5 处 CSS + 3 处 JS |

## 2. CSS 改动详解

### 2.1 屏上 paper 自适应

```css
/* 屏上: paper 不再 420mm 硬限, 按 viewport 自适应 */
.paper {
  width: 210mm;          /* A4 竖向 仍是默认 */
  min-height: 297mm;
  max-height: none;
  overflow: visible;
  background: var(--paper);
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  padding: 8mm 9mm 10mm;
  position: relative;
  zoom: 1 !important;
}

/* 表格视图 A3 横向 */
.paper.is-table.is-landscape {
  width: 420mm;          /* 保持 sprint 26080103 v2 设计 */
  min-height: 297mm;
  max-height: none;
  padding: 4mm 5mm 4mm;
  box-sizing: border-box;
  overflow: visible;
}

/* iPad 横屏 viewport ≤ 1180px: paper 不再 420mm 硬限 */
@media (max-width: 1180px) {
  .paper.is-table.is-landscape {
    width: 100%;
    min-width: 0;        /* 不强制 980px, 让 paper 完全跟 viewport */
  }
  .paper.is-table .view-table-wrap {
    overflow-x: auto;    /* 矩阵横滚 */
  }
}
```

### 2.2 打印上下文

```css
@media print {
  html, body { background: #fff !important; margin: 0 !important; padding: 0 !important; width: 100%; height: auto; }
  .no-print, .toolbar, .day-filter { display: none !important; }
  .stage-wrap { padding: 0 !important; margin: 0 !important; display: block !important; }
  .paper-scale { transform: none !important; margin: 0 !important; padding: 0 !important; }

  /* paper 强制按 100% 渲, 矩阵按 print-zoom 缩放 */
  .paper {
    box-shadow: none !important;
    margin: 0 auto !important;
    width: 100% !important;
    max-width: 420mm;    /* A3 横向物理上限 */
    zoom: var(--print-zoom, 1) !important;
  }
  .paper:not(.is-landscape) {
    width: 100% !important;
    max-width: 210mm;
    min-height: 297mm;
    padding: 5mm 6mm !important;
    overflow: visible !important;
  }
  .paper.is-landscape {
    width: 100% !important;
    max-width: 420mm;
    min-height: 297mm;
    padding: 3.5mm 4.5mm !important;
    overflow: visible !important;
  }

  /* 矩阵打印上下文: 锁列宽, 防 flex 压 */
  table.matrix {
    table-layout: fixed !important;
    width: 100% !important;
  }
  table.matrix col { width: auto !important; }   /* 清 colgroup 百分比, 按 CSS min-width 算 */
  table.matrix thead { display: table-header-group !important; }
  table.matrix tbody tr { break-inside: avoid !important; page-break-inside: avoid !important; }
  table.matrix tfoot { display: table-row-group !important; break-before: avoid !important; page-break-before: avoid !important; }
}
```

### 2.3 colgroup 短列比例

```js
// stage-print.html:894-895
// 修: 短列从 2% 起调, 6 天时短列 2.8% (iPad 1133px viewport -> 32px = 8mm)
var itemW = nDays <= 2 ? 10 : nDays <= 4 ? 8 : 7;
var shortW = nDays <= 1 ? 5 : nDays <= 2 ? 4 : nDays <= 4 ? 3 : nDays <= 6 ? 2.8 : 2.4;
var tempoW = shortW + 0.5;
```

## 3. JS 改动详解

### 3.1 `preparePrintZoom` 改 @page 区域比例

```js
// stage-print.html:1130-1156 替换
function preparePrintZoom() {
  var isLs = viewMode === 'table';
  // @page 物理区域: 表格 A3 横向 (420x297mm), 分组 A4 竖向 (210x297mm)
  var targetH = (isLs ? 297 : 297) - 8;   // 减 padding
  var targetW = (isLs ? 420 : 210) - 9;   // 减 padding
  // paper 物理大小 (px -> mm, 96dpi)
  var naturalW = paper.offsetWidth  / (96 / 25.4);
  var naturalH = paper.offsetHeight / (96 / 25.4);
  var scale = 1;
  if (naturalW > targetW) scale = Math.min(scale, targetW / naturalW);
  if (naturalH > targetH) scale = Math.min(scale, targetH / naturalH);
  // sprint 26080801: floor 0.95 (从 0.65 / 0.70 改), 不让 zoom 把内容压到看不清
  if (scale < 0.95) scale = 0.95;
  if (scale > 1) scale = 1;
  paper.style.setProperty('--print-zoom', String(scale.toFixed(4)));
  return scale;
}
```

### 3.2 `fillMatrixToPaper` 屏上准备

```js
// stage-print.html:1063-1084
// 修: 屏上也清空 paper.style.minHeight (避免 210mm 兜底占空间)
function fillMatrixToPaper() {
  if (viewMode !== 'table') return;
  var wrap = paper.querySelector('.view-table-wrap');
  var table = paper.querySelector('table.matrix');
  if (!wrap || !table) return;
  paper.style.height = '';
  paper.style.maxHeight = '';
  paper.style.minHeight = '';
  paper.style.overflow = 'visible';
  wrap.style.height = '';
  wrap.style.maxHeight = '';
  wrap.style.overflow = 'visible';
  wrap.style.flex = '';
  table.style.height = '';
  table.style.maxHeight = '';
  table.style.minHeight = '';
  var rows = table.querySelectorAll('tbody tr');
  rows.forEach(function (r) { r.style.height = ''; r.style.minHeight = '8mm'; });
}
```

### 3.3 `syncPaperMode` 状态文案

```js
// stage-print.html:727-742 改 toolbar 状态条
function syncPaperMode() {
  var isTable = viewMode === 'table';
  paper.classList.toggle('is-table', isTable);
  paper.classList.toggle('is-landscape', isTable);
  var rule = document.getElementById('printPageRule');
  if (rule) {
    rule.textContent = isTable
      ? '@page { size: A3 landscape; margin: 0; }'
      : '@page { size: A4 portrait; margin: 0; }';
  }
  // 修: 文案不再"打印一页约 X%"误导, 改为"屏上可横滑 · 打印按内容自动分页"
  var hint = document.querySelector('.toolbar .hint');
  if (hint) {
    hint.textContent = isTable
      ? '表格 · A3 横向 · 屏上可横滑 · 打印按内容自动分页'
      : '分组 · A4 竖向 · 可切换表格';
  }
}
```

### 3.4 `updatePreviewStatus` 屏上提示

```js
// stage-print.html:744-762
// 修: 屏上根据 paper.scrollWidth vs clientWidth 判断是否横滑
function updatePreviewStatus() {
  paper.style.setProperty('--print-zoom', '1');
  paperScale.style.transform = '';
  var a3px = a3PageHeightPx();
  var contentH = paper.scrollHeight;
  var modeLabel = viewMode === 'table' ? '表格·横向' : '分组·竖向';
  var nDays = (lastPayload && appliedDays) ? Object.keys(appliedDays).filter(function(k){return appliedDays[k];}).length : 0;
  var overflow = paper.scrollWidth > (paper.clientWidth + 4);
  if (overflow) {
    statusMsg.textContent = modeLabel + ' · 已选 ' + nDays + ' 天 · 屏上可横滑 · 打印按内容自动分页';
  } else if (contentH > a3px + 8) {
    var pct = Math.max(40, Math.min(100, Math.round((a3px / contentH) * 100)));
    statusMsg.textContent = modeLabel + ' · 预览 100% · 打印一页约 ' + pct + '%';
  } else {
    statusMsg.textContent = modeLabel + ' · 预览 100% · 已在一页内';
  }
}
```

## 4. 测试设计

### 4.1 `tests/test_stage_print_pdf.py`（新增）

| 测试 | 验证 |
|---|---|
| `test_paper_css_responsive_max_1180` | 解析 `stage-print.html`, 验证 `@media (max-width: 1180px) { .paper.is-table.is-landscape { width: 100% } }` 存在 |
| `test_paper_css_print_max_width_420` | 验证 `@media print { .paper.is-landscape { max-width: 420mm } }` 存在 |
| `test_matrix_print_fixed_layout` | 验证 `@media print { table.matrix { table-layout: fixed !important } }` 存在 |
| `test_colgroup_short_w_2_8_for_6_days` | 验证 `shortW = ... 2.8 : 2.4` 字面量（6 天时 2.8%） |
| `test_prepare_print_zoom_floor_0_95` | 验证 `if (scale < 0.95) scale = 0.95;` 字面量 |
| `test_sync_paper_mode_hint_text` | 验证 "屏上可横滑 · 打印按内容自动分页" 文案存在 |

### 4.2 父目录结构

```
tests/
  test_stage_print_pdf.py       # 6 个新单测
```

## 5. 兼容性

- Mac Chrome: sprint 26080103 baseline 保留（`width: 420mm` 在 Mac viewport > 1180px 时仍生效）
- Mac Safari: 同 Chrome
- iPad Safari: 本 sprint 修复（viewport ≤ 1180px 触发新 CSS）
- iPhone: 不服务（dizical 设计原则）
- CloudRun: 不需重新部署（前端 CSS/JS 改动，HTML 模板重新加载即生效；`start-prod.sh` 启本地 8765 后 dad 立刻可验）

## 6. 部署路径

- **本地 8765**: `stop-prod.sh` → `start-prod.sh` → `lsof -nP -iTCP:8765 -sTCP:LISTEN` 确认
- **CloudRun**: 本 sprint 完成后 PR 走通后, dad 拍板是否部署；本 sprint 优先本地 8765 验真, CloudRun 部署走 MCP（沿用 sprint 26080701 流程）

## 7. 沉淀

- 新 reference: `references/stage-print-ipad-safari-pdf-2026-08-08.md`
- 沉淀 sprint-workflow mini-plan 第 5 段"验证路径"实战经验
