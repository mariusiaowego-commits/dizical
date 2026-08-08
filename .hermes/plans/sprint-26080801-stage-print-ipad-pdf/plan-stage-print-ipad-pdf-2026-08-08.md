---
id: 26080801
type: sprint
version: 1.0.0
start_date: 2026-08-08
end_date: 2026-08-08
status: 进行中
priority: 高
summary: /report/stage-print 表格视图 iPad 横屏可读 + iPad Safari PDF 不再截内容
tags: [sprint, dizical, stage-print, ipad, pdf]
---

# Sprint 26080801 — stage-print iPad 适配 + iPad Safari PDF 完整输出

## 1. Goal

修复 `/report/stage-print` 表格视图在 iPad 横屏 (`landscape`) 屏上不可读、且 iPad Safari 导出 PDF 内容被截断的 P0 bug。Mac 浏览器对照同页面已能完整显示 6 天矩阵并 1 页完整输出 PDF；iPad Safari 同页面只能看到 4 天，PDF 只输出 1 页且缺 7/31、8/1 两列。

**Acceptance criteria**：
- [ ] iPad Safari 横屏 (`1024×768` landscape 物理 2266×1488) 表格视图屏上预览可读，6 天全显示
- [ ] iPad Safari 导出 PDF 包含完整 6 天矩阵，页脚 "数据: practice_sessions · 展示 6/6 天" 完整出现
- [ ] Mac Safari/Chrome 导出 PDF 仍 1 页完整（baseline 不退化）
- [ ] 矩阵列宽在两个设备上视觉一致，不出现一边被压一边被拉
- [ ] 屏上不分页、不裁剪，PDF 多页时分页处不出现"半行"或"半列"

## 2. 根因分析（已有证据）

### 证据

| 证据 | 来源 | 结论 |
|---|---|---|
| Mac PDF 1 页 = 6 天完整 | `/Users/mt16/Downloads/竹笛练习明细 · Stage 16 · 表格2.pdf` (228K) `pdftotext` 验证 | 同一 DOM + `@page` A3 landscape 下 Mac 浏览器完整 |
| iPad PDF 1 页 = 4 天（缺 7/31, 8/1） | `/Users/mt16/Downloads/竹笛练习明细 · Stage 16 · 表格.pdf` (158K) `pdftotext` 验证 | 同一 DOM + `@page` A3 landscape 下 iPad Safari 截断 |
| 矩阵 colgroup 用百分比 | `stage-print.html:894-905` `shortW = 2 ~ 5%`, `itemW = 7 ~ 10%` | iPad Safari 在 `@page` A3 上下文里 flex/auto 压到 2% 一格 < 6mm |
| `preparePrintZoom` 写在 paper 的 `zoom` 上 | `stage-print.html:1130-1156` | iPad Safari 的 `zoom` 在 print 上下文里**部分支持**，无法保证 paper 缩到 A3 范围 |
| `paper-scale { transform: none }` 屏上禁止缩放 | `stage-print.html:432-435` | 屏上 iPad 真不知道 paper 是 420mm，只能看到 ~794px (A4)，colgroup 2% 折算 16px 直接吞字 |
| `updatePreviewStatus` 只算 paper 自身高度 | `stage-print.html:744-762` | 不算 paper 在视口里的有效宽度，所以 iPad 真把 420mm 渲到 1133px viewport 时，colgroup 2% = 22px |

### 根因（双层）

1. **屏上 iPad 看不懂 paper 是 420mm**：`paper` 元素 CSS 宽度 `420mm` (A3 横向) 在 iPad 1133px viewport 上渲染为 ~1588px（按 1mm=3.78px），已经超过视口 1133px，paper 被 flex 父容器压回 1133px；colgroup 短列 2% 折算 22px ≈ 5mm，iPad 上 5mm 字读不清。
2. **iPad Safari 打印上下文不响应 paper.zoom**：Mac Chrome 完整支持 `paper.zoom` 缩放，输出 PDF 时 paper 真正被缩到 A3；iPad Safari 走自己的 `WKWebView` 打印路径，对 `zoom` CSS 属性的支持不完整或不应用到 `@page` 上下文，paper 仍是 420mm 物理像素，但打印纸只有 A3 实际可用面积（420mm），导致矩阵被裁。

## 3. 修复方案

### 3.1 屏上：双布局

- 表格视图在 iPad 横屏 viewport (`max-width: 1180px` 上下) 时，**屏上**也走"屏幕小，矩阵按内容可横滚"分支，**不再**把 paper 渲到 420mm 强行压。
- 引入 `.paper.is-table.is-landscape.is-screen-fit`（屏上）与 `.paper.is-table.is-landscape.is-print-fit`（打印）两套模式：
  - 屏上：去掉 `width: 420mm` 硬限，改 `width: 100%; min-width: 980px`（按 6 天计算），外层 `view-table-wrap` 加 `overflow-x: auto` 让 iPad 横屏可横滑。
  - 打印：恢复 `width: 420mm` + `zoom: var(--print-zoom)`，并把 `--print-zoom` 计算从 paper 整体改为 paper 与 A3 可用区域**双向取 min**（之前已经做）+ **强制下限 0.95**（不让 zoom 把 6 天内容缩到看不清）。
- 屏上 toolbar 状态条：根据 `paper.scrollWidth > clientWidth` 显示"横向滚动查看 6 天"提示。

### 3.2 打印：iPad 友好的 4 件套

- `@page` 强制 `A3 landscape`（已实现，但 iPad Safari 需补 `mark: 0;` 防页边距干扰）。
- `.paper.is-landscape` 在 `@media print` 内加 `width: 100% !important; max-width: 420mm; margin: 0 auto;`（不再依赖 paper 元素的 `width: 420mm`）。
- 矩阵 `table.matrix` 强制 `width: 100% !important; table-layout: fixed;` 打印上下文（屏上仍是 `table-layout: auto`），保证列按 CSS 比例被等比缩放，不被 flex 压。
- `--print-zoom` 计算从 `paper.scrollHeight/Width` 改为 `@page` 区域比例：
  ```js
  var targetW = 420 - 9;   // mm 减去 padding
  var targetH = 297 - 8;
  var naturalW = paper.offsetWidth  / 3.78;  // px -> mm
  var naturalH = paper.offsetHeight / 3.78;
  var scale = Math.min(targetW / naturalW, targetH / naturalH, 1);
  if (scale < 0.95) scale = 0.95;  // 不到溢出 1 页就不缩
  ```
- 之前 Mac 端 0.65 floor 在 iPad 上仍然溢出 → 改 `0.95` 之后，Mac/iPad 都不会把内容压到 65%；6 天矩阵若 0.95 仍溢出，自然分 2 页。

### 3.3 屏上打印按钮 status 文案

- iPad 屏上 100% 可读，按钮状态条改成"已选中 N 天 · 屏上可横滑 · 打印按内容自动分页"，不再出现"打印 100% · A4 横向 1 页"误导（iPad A3 横向本来就是 1 页，但屏上是 1133px 视口，会让 dad 误以为屏上就是 A3 1 页）。

## 4. 改动的文件

| 文件 | 改动 | 原因 |
|---|---|---|
| `src/kid_app/templates/stage-print.html` | (1) 屏上 paper 不再 420mm 硬限，按 viewport 自适应 + 矩阵外层 `overflow-x: auto` (2) `@media print` 改 `width: 100% !important; max-width: 420mm` (3) `preparePrintZoom` 改 @page 区域比例 + floor 0.95 (4) 矩阵打印上下文 `table-layout: fixed` 锁列 (5) `--print-zoom` 状态条文案 | 主修 |
| `src/kid_app/app.py` | **不动**（数据接口已含 stage 全量，sprint 26080103 已加 SSE API） | — |
| `tests/test_stage_print_pdf.py`（新增） | 5 个 PyTest 单测：① 屏上 viewport ≤1180px 时 paper.scrollWidth ≥ 980px ② 屏上 viewport 自由时 paper 可滚 ③ `--print-zoom` 计算结果区间 ④ `@media print` CSS 存在 `width: 100%` 强制 ⑤ 矩阵在 print 上下文有 `table-layout: fixed` | 防回归 |
| `docs/sprint-26080801-stage-print-ipad-pdf-2026-08-08.md`（新增） | sprint 完整文档 | dad 后续查阅 |

**不动**：
- 后端 API、数据库、其他模板、CSS 主题 token、设计系统。

## 5. 验证路径（按 sprint-workflow 强制 4 问）

1. **改动落在哪个分支**：`feat/stage-print-ipad-pdf-260808`（在 main checkout 直接开，不 worktree — 沿用 sprint 26080701 后 dad 偏好）
2. **dad 怎么立刻看**：本地 8765 (`http://localhost:8765/report/stage-print?stage_order=16`) 重启后用 Mac Chrome 验证屏上 + PDF，再用 iPad Safari (Tailscale 或 LAN) 验证屏上 + PDF
3. **真后端 smoke**：本地 8765 跑 prod DB（自动连云 MySQL，跟 CloudRun 同源），不需要额外 smoke
4. **cloud-only 步骤**：无（纯前端 + 1 个新 test 文件，本地 8765 跟 CloudRun 同源）

## 6. 风险

- **R1**：屏上 paper 不再 420mm 硬限 → iPad 横屏 1133px 视口里 paper 自适应为 100%，colgroup 短列会变成 22px（5mm），需确认 iPad 真机上 5mm 可读。iPad mini 横屏物理 2266px (2x DPR)，CSS 1133px 5mm = 19px = 5mm 物理 ≈ 14.5pt 字号。可读但比 22mm 短列原始设计小。
  - **缓解**：colgroup 短列 2% 改 2.4% / 2.6% / 2.8% 三档（按天数），保证 6 天矩阵时短列 ≥ 6mm。
- **R2**：iPad Safari `@page A3 landscape` 实际可用面积可能比 420×297mm 略小（iOS 内部留 5mm 边距），需 fallback 到 A4 横向 + scale 0.85。
  - **缓解**：`--print-zoom` 计算后用 `Math.max(scale, 0.95)` 兜底，宁可分 2 页。
- **R3**：sprint 26080103 的"按 A3 横向装 7 天"在 iPad Safari 上不能直接复用，物理 7 天需要分 2 页。
  - **接受**：dad 反馈重点是"全选一周 6 天导出 PDF 不全"，6 天 iPad 上分 2 页 = 每页 3 天，比 1 页压到看不清强。

## 7. 验证脚本（plan 阶段定性，Phase 2 实施后跑）

```bash
# 单测
uv run --project /Users/mt16/dev/dizical pytest tests/test_stage_print_pdf.py -q

# 重启本地 8765
./scripts/stop-prod.sh && ./scripts/start-prod.sh
lsof -nP -iTCP:8765 -sTCP:LISTEN

# 屏上 + PDF 验证（Mac Chrome）
curl -s "http://localhost:8765/report/stage-print?stage_order=16" -o /tmp/stage-print.html
# 浏览器打开 /report/stage-print?stage_order=16&view=table 全选 6 天 → 打印 → 保存 PDF 到 /tmp/mac-stage16-after.pdf
# pdftotext 验证 6 天 + 页脚都在

# 屏上 + PDF 验证（iPad Safari）
# iPad Safari 打开 http://<mac-ip>:8765/report/stage-print?stage_order=16&view=table 全选 6 天 → 打印 → 保存 PDF
# 通过 Tailscale `tailscale file cp` / airdrop / 微信传文件助手把 PDF 拿回 Mac
# pdftotext 验证 6 天 + 页脚都在
```

证据归档：
- `/tmp/mac-stage16-before.pdf` (Mac 当前 PDF，已存)
- `/tmp/ipad-stage16-before.pdf` (iPad 当前 PDF，已存)
- `/tmp/mac-stage16-after.pdf` (本 sprint 修后 Mac PDF)
- `/tmp/ipad-stage16-after.pdf` (本 sprint 修后 iPad PDF)
- `pdftotext` 提取 4 个 PDF 第 1 页文本对比

## 8. 非目标

- 多人多 stage 批量 PDF 导出
- 其他页面 (`/report` 主体) PDF 适配
- 老师/家长分享流程
- iPad mini 之外的 iPad 型号（自适应 CSS 已覆盖）
- iPhone（dizical 不服务 iPhone）
- 设计系统 / dizicute token（仅调整 paper 宽度和 zoom 算式，色板不动）

## 9. 跟 sprint 26080103 的关系

- sprint 26080103 是"关 `table-layout: fixed` + 加 min-width + 不限高"路线，针对 iPad mini 屏上不可读
- 本 sprint 是"屏上 viewport 自适应 + 打印 `@page` 强制 + zoom 算式"路线，针对 iPad Safari PDF 截断
- 两个 sprint 不冲突，可叠加；本 sprint 不回退 sprint 26080103 的 min-width 改动
- 沉淀：`references/stage-print-ipadmini-and-image-export-2026-08-01.md` 已记录 sprint 26080103，本 sprint 单独写新 reference 写本 sprint 的发现

## 10. dad 拍板

- Q1 屏上 paper 宽度策略: **A** 屏上 100% 自适应 + 矩阵横滚
- Q2 打印 paper 缩放策略: **A** `@page` 区域 + floor 0.95
- Q3 矩阵打印上下文 table-layout: **A** 强制 `table-layout: fixed`
- Q4 验证方法: **A** Mac + iPad 各自导出 PDF + pdftotext 对比
