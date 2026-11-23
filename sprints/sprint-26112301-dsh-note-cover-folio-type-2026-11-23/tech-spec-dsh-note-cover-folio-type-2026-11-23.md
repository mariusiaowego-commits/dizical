---
type: sprint
sprint: "26112301"
doc: tech-spec
date: 2026-11-23
---

# 技术方案

## 1. 两种展开形态

| 档位 | 判定 | 便签定位 | 目标高 | 卡高 |
|---|---|---|---|---|
| 竖排 feed（overlay） | `isFeedDeck() && wrap.offsetTop + baseH - 48 >= 180` | `absolute; bottom:0`，向上长 | `min(max(startH, need), room, 320)`，`room = wrap.offsetTop + baseH - 48` | 不变（`.ctn-wrap` 锁 `baseH`，`.is-expanded` 排除 `height:auto !important`） |
| 横排 1133（in-flow） | 其余 | `static` | `max(startH, min(need, inlineH))`，`inlineH = max(120, min(260, paper.clientHeight - 120))` | 不变（`.card-req-body` 收缩到 `min-height:96px`） |

`need = headH + body.scrollHeight + 18`。

## 2. 状态机

- 方向：`open = note.dataset.open !== '1'`（点击即翻转，不等动画结束）。
- 稳定折叠高：`baseH = note.classList.contains('is-open') ? +(wrap.dataset.collapsedH || startH) : startH`。
  收起动画半途重开时 `offsetHeight` 是半途值，锁高与可用空间必须用 `baseH`，否则会把半途高度写回 `wrap`，顶出底栏。
- overlay 判定保留 `wrap.classList.contains('is-expanded')`：已展开的卡收起过程中仍是浮层语义。
- 过期回调：`dataset.seq` 递增，`settle()` 首行比对，不等则丢弃。
- 收口：`transitionend`（只认 `propertyName === 'height'`）+ `setTimeout(settle, 240/180 + 120)`。
  **不监听 `transitioncancel`**：连点改写 `height` 会取消旧过渡，浏览器异步派发的旧 `transitioncancel` 会命中新绑定的 `onEnd`，导致新过渡 0ms 瞬断。
- 监听器只保留一份：`note.__noteEnd`，重入前先移除。

## 3. 复位

```
if (w === noteResetW && feed === noteResetFeed) return;
```

iframe 量高改自身高度也会派发 `resize`（`innerWidth` 不变、`isFeedDeck()` 不变），不加过滤会把刚展开的浮层瞬间弹回。复位时清 `wrap.dataset.collapsedH`，若有节点被复位且 `feed` 为真，再 `pokeFeedReflow()` 收掉多余高度。

## 4. 视觉

- 便签是压在纸上的实物：1px 内棕线 `inset 0 1px 0 rgba(160,66,23,.30)` + `drop-shadow(0 -1px 2px var(--qc-note-shadow-near))`。
- 不做自身 mask 渐隐：6px 遮不住 24.75px 行高，反而把纸边糊掉。
- `.ctn-head` 整条可点（`cursor:pointer`，只在 `.is-clampable` 上），粗指针下 44px。

## 5. 票夹手机档

`@media (max-width:480px)` 覆盖：

| 元素 | 1133 | ≤480 |
|---|---|---|
| 弹窗标题 | 16 | 18 |
| 曲目名 | 14 | 16 |
| 副行（档案编号） | 12 | 13 |
| 环节 pill | 12 | 13.5 / 36 高 |
| BPM 徽标 | 11.5 | 12.5 / 30 高 |
| 分类 pill | 12 | 12.5 / 32 高 |
| 归档展开按钮 | — | 14 / 44 高 |

`.pk-stub-more-btn` 原先全仓无样式，本次补齐。

## 风险与回滚

- 纯模板/样式改动，无 schema、无 API、无依赖变化；回滚即 revert 该 PR。
- 唯一行为风险是展开高度受宿主量高影响，已有 440/1133 实测与状态机单测覆盖。
