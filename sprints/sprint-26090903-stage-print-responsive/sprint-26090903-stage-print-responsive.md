---
id: 26090903
type: sprint
version: 1.0.0
start_date: 2026-09-03
end_date: 2026-09-03
status: 已完成
priority: 高
summary: stage-print 响应式深化（桌面表格 + group view 移动端 + 键盘无障碍）
tags: [sprint, dizical, stage-print]
---

# Sprint 26090903 — stage-print 响应式深化

**Sprint Goal**: 让 `/report/stage-print` 在桌面/手机/iPad 三档设备上都有可用布局，并提供键盘无障碍支持。

**触发**: dad 说"修完两个 issue + 深化"

## 决策记录

| 维度 | 决策 | 拍板人 |
|------|------|--------|
| 桌面响应式 | fluid + max-width:420mm + sticky 科目列 + `@media screen` 隔离 | dad 9-03 |
| 三档断点 | ≤768 / 768-1180 / ≥1180 | dad 9-03 |
| 策略采纳 | grok 方案（@media screen 隔离 + sticky + JS 去 overflow:visible）| dad 9-03 |
| 分工 | agy 方案设计 + 2轮review，grok 实施 + 2轮patch | dad 9-03 |
| 键盘无障碍 | ←→ 横滑 200px + Home/End + focus-visible + aria-live | dad 9-03 |

## Sprint 子任务

### S1 — PR #305 桌面 1440px 响应式表格
- [x] `.paper.is-table` fluid + max-width:420mm（桌面不 210mm 硬限）
- [x] sticky 科目列（`:has()` + JS fallback）
- [x] 三档断点（768 / 1180）
- [x] `fillMatrixToPaper()` 去 `overflow='visible'`
- [x] `@media print` 完整保留
- [x] **PR #305 Merged**（commit `581e6fb` + `886bf7a` + `6eab012`）

### S2 — PR #306 Group view 移动端 + 键盘无障碍
- [x] assign-grid 手机端 2 列 + iPad 3 列 + 桌面 4 列
- [x] 卡片紧凑排版（padding / font-size / gap）
- [x] 日块间距压缩
- [x] `bindKeyboardA11y()` ← → 横滑 + Home/End
- [x] `:focus-visible` 焦点环（2px accent outline）
- [x] aria-live region 提示当前科目
- [x] **PR #306 Merged**（commit `a24a4ba`）

## 测试
- `tests/test_stage_print_pdf.py` 16/16 PASSED
- 全量 pytest baseline 36 failed（预先存在，patch 未引入新回归）

## Review
- agy (Claude Opus 4.6 Thinking) 2轮独立 review：初始方案 + P1/P2 review + 最终确认
- grok (Grok 4.6) 实施 + 自验 + PASS 确认
- P0 阻断性：无
- P1 体验级：4 处已在合入前修完

## 交付
- **PR #305**: https://github.com/mariusiaowego-commits/dizical/pull/305 (Merged)
- **PR #306**: https://github.com/mariusiaowego-commits/dizical/pull/306 (Merged)
- **main commit**: `a24a4ba`
