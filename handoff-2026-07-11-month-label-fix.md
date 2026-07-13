# Handoff - 2026-07-11 PR #150 月图 X 轴 label 修复

**Session**: PR #150 - 月图 X 轴日期 label 不再与柱状图底部重叠 (1 行 fix, 5 分钟工作)
**Status**: ship-ready - PR merged, prod 8765 加载新代码
**Owner**: dad
**Last updated**: 2026-07-11

---

## TL;DR

PR #147 merge 后 dad 反馈: 月图 X 轴日期 label (07/01, 07/04...) 跟柱状图底部重叠 ~10px. 1 行 fix (labelY 180→192) → PR #150 → prod 重启.

**当前状态**:
- main: `d10f18b` (PR #150 squash merge)
- 生产服务: 8765 PID 2000 跑新代码, 4/4 URL curl 200
- 0 OPEN PR, 0 stale 分支
- pytest: 16 fail / 291 pass (净回归 0, pre-existing)
- DB: 未动

---

## 根因 (重要: SVG text y 行为)

SVG text 的 `y` 属性是 **baseline** (基线), 不是文本顶部. 文本顶部 = baseline - font_size.

原代码:
- 月图 CHART_H = 140
- bar 底 y = 40 + CHART_H = 180
- label baseline y = 180 (labelY = CHART_H + 40, 默认)
- label 顶 y = 180 - 10 (font_size) = 170
- bar 范围 y = 0~180 (CHART_H=140 高度)
- **label 顶 170 跟 bar 0~180 重叠 10px**

修法:
- labelY = 192 (CHART_H + 52, 显式传)
- label 顶 y = 192 - 10 = 182
- bar 底 180
- **gap 2px** ✅

---

## 改动

### `src/kid_app/templates/report.html` (1 行)

```js
function renderMonthChart(monthData) {
  // ...
  return renderStackedChart(monthData, {
    barW: barW, barGap: 6, chartH: 140, labelStride: 3, labelY: 192  // ← 新增 labelY: 192
  });
}
```

**不改动 renderStackedChart 默认值** — stage chart 完全不受影响 (它继续用默认 labelY=200).

---

## 验证

- 浏览器实测 (8770): 月图日期 label y=192, 跟 bar 底 y=180 gap 2px, 无重叠
- vision 确认: 月图无重叠 + 5-7px 间距 + X 轴清晰; stage chart 跟之前一致
- pytest 净回归 = 0 (双向 FAILED-set diff 一致, 16 fail 同一集合)
- prod 8765 curl: 4/4 URL 200 (/report + /report?month=2026-06 + /report?month=2026-05 + /api/practices/monthly)

## prod 状态

- **PID**: 2000, port 8765, main `d10f18b`
- **URL**: http://localhost:8765 / http://10.0.0.14:8765 / http://100.67.215.121:8765

## Notes for future session

1. **SVG text y 是 baseline, 不是 top**. 计算 label 跟其他元素间距时必须 baseline - font_size
2. **stage chart 之前为什么没报**: BAR_W=40 柱粗, label "07/05" 宽 28px < 柱 40px, label 在柱内部, 视觉不违和. 月图 BAR_W=21 < label 28px, label 伸出柱外, 视觉明显
3. **opts.labelY 显式传是干净的解法**: 不改 renderStackedChart 默认, 跟 stage chart 行为解耦
4. **§⑱ pytest 节奏**: commit/merge 前各跑一次, 中间不跑. 视觉工作 dad ack 之前不 commit