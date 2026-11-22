---
type: sprint
sprint: "26112202"
doc: tech-spec
date: 2026-11-22
---

# 技术方案

## 根因

1. **横排 `cz-expand`**：20px 卡角的 1px 边带沿 45° 位于距角点 7.87–8.28px；宿主 `.cz-mod[data-mod="Q"]` 的 24px 裁弧在 9.94px，`.req-card-chassis` 的 28px 裁弧在 11.60px，两层 `overflow:hidden` 把边带 100% 切除，只剩直边。
2. **手机 `cz-feed`**：`.deck-card` 保留 `transform-style: preserve-3d`、`backface-visibility: hidden`，`#czCanvas` 再统一 `scale(k)`（k≈0.79–0.89）。透明 `::before` 1px 描边的外缘与父级圆角抗锯齿重叠，弧段有效 alpha 被二次采样吞到 < 0.04。

## 结构

```
.deck-card            位姿层：position / width / height / 2D transform / opacity
└─ .qc-shell          纸壳：border: 1px solid var(--qc-edge)；radius 20px；无 overflow
   └─ .qc-sheet       纸面：radius 19px；overflow: hidden；container: qcard / inline-size
      ├─ .qc-paper-body   内容：padding 18px；::before = 8px 内印线
      └─ .deck-footer-bar 登记带：dots + No./用时 + 上一张/下一张
```

一层只干一件事：动效不碰描边，描边不被裁剪，裁剪只发生在纸面层。

## 关键取值

| 项 | 浅色 | 深墨 |
| --- | --- | --- |
| `--qc-paper` | `#FEFCF7` | `#262D35` |
| `--qc-edge` | `#CFC9BE` | `#4E5864` |
| `--qc-edge-thick` | `#DFDAD1` | `#14181C` |
| `--qc-note` | `#FFF4E3` | `#313A44` |
| `--qc-foot` | `#F5F1E8` | `#202730` |
| 印泥字/框 | `#A04217` / `rgba(160,66,23,.45)` | `#FF9E7A` / `rgba(255,158,122,.42)` |

边色按 0.8× 45° 覆盖率（c≈0.55–0.65）反推：浅色 ΔY 由 28.8 提到 50.3，深墨由 24.9 提到 42.2。

## 约束与坑

1. `.qc-shell` 的 `inset` 纸棱会被不透明 `.qc-sheet` 盖死 → 纸厚用 `.qc-shell { padding-bottom: 2px; background: var(--qc-edge-thick) }` 真实露出；顶部受光移到 `.qc-sheet` 的 `inset 0 1px 0`。
2. 内印线不能写死底边偏移：`cz-fill` 下 `.deck-footer-bar { flex-wrap: wrap !important }`，窄档会折行。内印线挂 `.qc-paper-body::before`，底边天然落在登记带上沿；无底栏时 `:only-child` 四边闭合。
3. `@container qcard` 查 content-box。`.qc-sheet` 保留 `padding-inline: 18px`，现有 468 / 348 断点数值不变。
4. `runContractAudit` D4-2 要求未选 dot 对比度 ≥ 3.0:1（底 `chLum=0.89`）→ 孔底用 `rgba(44,62,80,.56)` / 深墨 `rgba(222,215,205,.55)`，命中垫放 `::before`。
5. `measureCardContent()` 的 `r.bottom` 不含 `box-shadow` → feed 档 `.deck-card` 加 `margin-bottom: 14px`，否则落影被 iframe 底边切平。
6. 静态顶卡不写 `transform`，`will-change` 只在拖拽/翻页期挂；否则 GPU 层被 canvas 二次采样发虚。

## 回滚

单文件改动（`practice-dsh.html`）+ 文档 + 测试。`git revert` 单个 squash commit 即回到 v3.54 视觉。
