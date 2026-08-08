---
id: 26080801
type: prd
version: 1.0.0
date: 2026-08-08
status: active
related_sprint: "[[sprint-26080801-stage-print-ipad-pdf-2026-08-08]]"
related_plan: "[[plan-stage-print-ipad-pdf-2026-08-08]]"
tags: [sprint-26080801, stage-print, ipad, pdf]
---

# PRD — stage-print iPad 适配 + iPad Safari PDF 完整输出

## 1. 用户故事

作为 **dizical 老师 (dad)**，在 iPad Safari 横屏上打开 `/report/stage-print?stage_order=16` 全选 6 天，点击"打印 / PDF"时，期望：

1. 屏上能看清 6 天的科目×日期矩阵，列宽合理
2. 导出 PDF 包含完整 6 天 + 页脚 "数据: practice_sessions · 展示 6/6 天"
3. Mac 浏览器对照同页面，行为不退化

## 2. 验收（EARS 形式）

- **E1 (屏上可读)**：iPad Safari 横屏 (`max-width: 1180px`) 屏上 paper 不再被压到 colgroup 短列 < 5mm；矩阵外层可横滚
- **E2 (PDF 完整)**：iPad Safari 导出 PDF 包含全选 N 天的全部矩阵，页脚完整
- **E3 (Mac 兼容)**：Mac Chrome 同页面 PDF 仍 1 页完整（sprint 26080103 baseline）
- **E4 (不破坏 sprint 26080103)**：sprint 26080103 的 min-width 8mm、break-inside: avoid、table-layout: auto 全部保留
- **E5 (列对齐)**：打印上下文 `table-layout: fixed` 强制列按比例等比，不被 flex 压

## 3. 用户场景

### 场景 A: 老师在 iPad mini 导出 7 天明细

1. iPad Safari 打开 `/report/stage-print?stage_order=16`
2. 工具条选择 Stage 16，点击"表格"视图
3. day-filter 默认全选 6 天，点击"确认展示"
4. 屏上看到 6 天矩阵，列宽 5-8mm，可横滑
5. 点击"打印 / PDF" → 状态条显示"已选 6 天 · 屏上可横滑 · 打印按内容自动分页"
6. iOS 打印对话框选"存储到文件" → 输出 1 或 2 页 PDF
7. 用 `pdftotext` 验证 6 天 + 页脚全在

### 场景 B: 老师在 Mac Chrome 验证同页面不退化

1. Mac Chrome 打开同 URL
2. 屏上 6 天矩阵完整
3. 打印 → 1 页 PDF
4. `pdftotext` 验证 6 天 + 页脚全在（跟 sprint 26080103 baseline 一致）

## 4. 不在范围

- iPad 之外 (iPhone 拒绝服务)
- 老师/家长分享流程
- 其他页面 (`/report` 主体) PDF
- 多人多 stage 批量导出
- 设计系统调整

## 5. 度量

| 指标 | 修前 (baseline) | 修后 (target) |
|---|---|---|
| iPad Safari 屏上列宽 ≥ 5mm | 部分列 < 5mm | 全列 ≥ 5mm |
| iPad Safari PDF 包含天数 | 4/6 天 | 6/6 天 |
| iPad Safari PDF 页脚完整 | 否 (被截) | 是 |
| Mac Chrome PDF 包含天数 | 6/6 天 | 6/6 天（不退化） |
| 单测数 | 0 stage-print test | ≥5 stage-print test |

## 6. 风险

- R1: 屏上 paper 自适应后 colgroup 短列在 iPad mini 1133px viewport 上变 5-7mm，可能仍偏小
  - 缓解: colgroup 短列比例 2% → 2.4% / 2.6% / 2.8% 三档
- R2: iPad Safari `@page A3 landscape` 实际可用面积 < 420×297mm
  - 缓解: `--print-zoom` floor 0.95 + 必要时 fallback A4 横向
- R3: sprint 26080103 的 0.65 floor 改 0.95 后 Mac 7 天可能分 2 页
  - 接受: dad 反馈重点是"全选一周导出 PDF 不全"，分 2 页 > 内容不全
