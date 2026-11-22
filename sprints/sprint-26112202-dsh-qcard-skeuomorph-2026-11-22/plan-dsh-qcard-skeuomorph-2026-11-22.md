---
type: sprint
sprint: "26112202"
doc: plan
date: 2026-11-22
---

# 实施计划

1. **宿主摘壳**：`practice-dsh.html` 的 `CANVAS_SCOPE` 给 `.cz-mod[data-mod="Q"]` 去圆角/投影/裁剪；`sizeBox()` 对 Q 放行 `overflow: visible`；清理重复的 `.cz-mod > iframe` 声明。
2. **嵌入桥接解绑**：`MODULE_SCOPE` 里 `cz-expand` 下 Q 的 `.stage-frame` / `.req-card-chassis` 解除裁剪；`html.cz-fill.cz-feed .deck-card` 宽改 `100%`，加 `margin-bottom: 14px` 给落影留位。
3. **tpl-Q 结构**：`createCardMarkup()` 输出 `.qc-shell > .qc-sheet > (.qc-paper-body + .deck-footer-bar)`；空态不渲染底栏；背景叠卡渲染无 id 的静态底栏壳。
4. **tpl-Q 样式**：
   - 删 `.deck-card::before` 描边、静态 `preserve-3d` / `backface-visibility` / `overflow: hidden` / `container-type`、`.req-card-chassis` 的 28px 裁切、`.qc-bay`、`.qc-idx` 灰底。
   - 加 `.qc-shell`（实体 1px 边 + 2px 纸厚切面 + 落影）、`.qc-sheet`（19px 内圆角裁剪 + `container: qcard / inline-size` + `padding-inline: 18px`）。
   - `.qc-paper-body::before` 8px 内印线；速度章 `-2°`；「最新」墨灰细印框；撕口便签；卡底登记带。
   - 双皮肤 token（浅色 / 深墨）。
5. **叠卡与动效**：`renderDeck()` 静态顶卡 `transform: none`，底层卡 2D `translateY + scale`；`bindCardDrag()` / `navTo()` 去 `translateZ`，`will-change` 只在拖拽/翻页期挂。
6. **测量链**：`measureCardContent()` 的 feed 解锁数组补 `.qc-shell` / `.qc-sheet` / `.qc-paper-body`。
7. **版本与文档**：`DSH_VERSION` → `v3.55`；`docs/practice-dsh/DESIGN.md` §13.3 更新；token 按 §10.2 登记。
8. **验证与交付**：`node --check`、`pytest`、8765 上 Playwright 四角像素 + 多视口 + 双皮肤 + 翻页复测，PR + 独立 audit。

## 不做

- 不加 `feTurbulence` 纸纹。
- 不改 dots 为纯非交互。
- 不动 T 卡与 A/B/R 卡。
