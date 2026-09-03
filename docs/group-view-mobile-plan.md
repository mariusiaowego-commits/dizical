# Group View 移动端布局深化方案

## 问题
当前 group view（view=group）在手机端（390px）仅做了基础限宽（.paper width:100%），但：
- assign-grid 没有独立响应式（沿用 `.paper.is-table .assign-grid`，仅在 table 视图生效）
- 卡片内部排版未针对小屏优化（padding/font-size 固定）
- 日块（.day-block）在窄屏下未优化间距

## 方案概要
保留桌面 A4 竖向 210mm 居中布局，手机端（≤768px）改用 fluid + 卡片网格自适应，iPad（768-1180）轻微压缩间距。

## 关键决策
1. assign-grid 在 group view 下独立响应式：桌面 4 列 → iPad 3 列 → 手机 2 列
2. 手机端 .paper 限宽 100% + box-shadow none（已做，6eab012）
3. 卡片 padding/font-size 在手机端缩小（不改变 JS）
4. 日块间距在手机端压缩（gap 缩小）
5. 不改 renderBodyGroup()，纯 CSS 方案

## CSS 改动草案

```css
/* 手机端 ≤768: group view 卡片网格 2 列 */
@media screen and (max-width: 768px) {
  .paper:not(.is-table) .assign-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 2mm 3mm;
  }
  .paper:not(.is-table) .assign-card {
    padding: 1.5mm 2mm;
    margin-bottom: 2mm;
  }
  .paper:not(.is-table) .assign-card h2 {
    font-size: 7.5pt;
  }
  .paper:not(.is-table) .assign-item {
    font-size: 7pt;
    padding: 0.5mm 0.6mm;
  }
  .paper:not(.is-table) .day-block {
    margin-bottom: 1.2mm;
  }
}

/* iPad 768-1180: 3 列 */
@media screen and (min-width: 769px) and (max-width: 1180px) {
  .paper:not(.is-table) .assign-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 1mm 1.5mm;
  }
}
```

## 验证清单
- [ ] 手机端 390px：group view 卡片 2 列，无横向滚动
- [ ] iPad 768px：3 列，间距适中
- [ ] 桌面 1440px：4 列，210mm 居中
- [ ] pytest test_stage_print_pdf.py 16/16 仍绿
- [ ] 打印预览 A4 竖向不受影响

## 改动范围
- 仅 CSS（stage-print.html <style> 块）
- 不改 JS、不改 API、不改 DESIGN.md
