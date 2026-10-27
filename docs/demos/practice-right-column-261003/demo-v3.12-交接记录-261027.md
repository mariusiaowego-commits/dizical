---
source: ai-agent
date: "2026-10-27"
doc_type:
  - handoff
tags: [dizical, practice, demo-v3.12, handoff, s22]
project:
  - dizical
is_done: false
---

# HANDOFF · dizical practice 右栏 demo v3.12（写于 2026-10-27）

    写入人   codex（本线程独立收口）
    工作目录 /Users/mt16/dev/dizical · 分支 feat/practice-ui-iter-260920
    demo 服务 http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html（PID 97410，curl 200，本轮未重启）

---

## 1 · 现在到哪了

```
demo 版本   v3.12（2026-10-27 盖章，24 页徽章 + VERSIONS.md 已重写 + 历史补 v3.11 / v3.12 两轮）
本轮范围     S22 收尾：agy 只读复核的 P0/P1 全部修完 + 新增回归护栏
commit      HEAD = 073e8c8（v3.11 S22）；本轮改动 → 新 commit（dad 授权「只 commit，不开 PR / 不 merge / 不 push / 不打 tag」）
门禁        verify.js --strict 15/15 PASS · sync-demo-templates --check 6/6 字节级一致 · CSS [data-vp] 0 处
待办        dad 肉眼验收 v3.12；遗留 P1（外层 #czPresets 541–660px 溢出）等 dad 拍板
```

## 2 · dad 本轮三条需求（原文要点）+ 落点

| dad 需求 | 落点 | 状态 |
|---|---|---|
| 1. 标注问题解决 | v3.10 已做（卡槽插入卡改主题色 + 去透明度），本轮无新增 | ✅ |
| 2.1 票夹空态（首次打开无选择 → 科目/内容置空等选择） | v3.11 已做，本轮保留 | ✅ |
| 2.2 选满两项立即变形为黑色窄条（不等点「开始」） | v3.11 已做，**本轮把变形动画从「瞬间跳变」修成真实插值** | ✅ |
| 2.3 窄条上加「重新选择」，变回票夹且保留选择 | v3.11 已做，**本轮把反向变形也修成插值** | ✅ |
| 2.4 计时期间「重新选择」置灰 | v3.11 已做，本轮保留 | ✅ |
| 3. BUG：拖 dashboard ruler 改时长，左侧票夹不联动 | v3.11 修了一半（ruler→票面/窄条），**本轮补齐票面→ruler 反向** | ✅ |
| 前端设计交给 agy（herdr `w45:p1`） | agy 只读复核已交付（`20261027-172047-s22-v311-folio-bar-review`），本轮按其 P0/P1/P2 逐条处理 | ✅ |

## 3 · agy 复核结论与本轮处置

agy 原文 verdict = 「P0 变形动效完全失效并瞬间跳变 + P1 440 窄条内容裁切 + P1 时长联动单向遗漏」建议修完再交付 dad；核心架构（`.stage-bar` 独立解耦 / 状态机分离 / 15 项护栏）评价为方向正确。

| agy 结论 | 严重度 | 根因 | 本轮处置 |
|---|---|---|---|
| 选满两项变形动效完全失效、瞬间跳变 | **P0** | `.stage-bar` 用 `!important` 锁死几何（`width:50px !important` / `#pkTicketCard display:none !important`），GSAP 补间写的是内联 style（非 !important）→ **样式表 !important 直接压掉内联插值**，票夹在第 1 帧就跳到 50px | 新增过渡态 `.stage-morphing`：只负责「把窄条显示出来」，不锁几何；动画结束才切回 `.stage-bar` 稳态。注入 CSS 里 `#pkLeftCol` / `#pkTicketCard` 的 `height:auto!important` / `width:100%!important` 规则加 `:not(.stage-morphing)` |
| 440 视口横条内容被挤成 1 个字 | **P1** | 440 横条 408px 内塞了 科目 70 + 剩余 96 + BPM 71 + 重选 76，内容区只剩 4.2px | ≤600 断点：窄条内冗余 BPM 隐藏（BPM 在下方 Card A/B 常驻大字号）、标签「本次内容」→「本次」、压缩内边距与按钮 padding |
| 直接调 `ttStepMin` / 点票面时长卡推不到仪表盘 | **P1** | 总线只监听了 `#pkTicketDurUp/Down` 的指针事件；`ttSetDuration` 包装层只改票面与窄条，没有派发 `api.duration()` | `window.ttSetDuration` 包装层补 `bus.duration(duration, 'left_ticket')`（回环由 `leftDur()` 值比较挡住，不自激） |
| 1133 竖条剩余时间 11px 偏小 | P2 | 远视距可读性 | **不采纳**：11px 实测宽 33px，50px 窄条内放大到 14px 会溢出；可读性靠横排而非字号解决 |
| 空态下 Slot 4「检票·开始」按钮的认知冲突 | P2 | 空态按钮 disabled，选满两项后自动收窄条，该按钮随即消失 | **不采纳**：它是 Slot 4 占位 CTA，dad 的新流程里主操作在 Card A「开始」；保留占位反而说明「中间栏还有这一格」 |
| `--cz-bar-h` 视口切换后不重算 | **P2** | 高度只在 morph 时算一次 | 新增 `refreshBarHeight()` 挂 `resize`：临时撤 `.stage-bar` 量票卡自然高度再写回 `--cz-bar-h` |

## 4 · 改了什么（全在 `docs/demos/practice-right-column-261003/`）

| 文件 | 位置 | 内容 |
|---|---|---|
| `canvas-01.html` | `2172-2186` | 新增 `.stage-morphing` 过渡态 CSS（桌面竖排方向 + 只显示窄条，不锁几何） |
| `canvas-01.html` | `17396-17401`（注入 CSS） | `#pkLeftCol` / `#pkTicketCard` 的 prep 规则加 `:not(.stage-morphing)`，另加 morphing 态专用的 flex/width/align-self 规则 |
| `canvas-01.html` | `17600-17601`（注入 CSS） | feed 断点同理加 `:not(.stage-morphing)` |
| `canvas-01.html` | `2979-3026` | 新增 `@media (max-width:600px)` 窄条排版（BPM 隐藏 / 标签「本次」/ 内边距压缩） |
| `canvas-01.html` | `6334-6460` | `morphTicketToBar()`：桌面态把左栏高度钉成票夹高度；动画期用 `.stage-morphing`，`onComplete` 换回 `.stage-bar` |
| `canvas-01.html` | `6508-6640` | `expandBarToFolio()`：先撤 `.stage-bar` 再钉几何（宽 50 / 高 52 / 票卡 0 宽 0 高），反向变形不再闪一下弹回整列 |
| `canvas-01.html` | `7077-7096` | `ttSetDuration` 包装层补 `bus.duration(duration,'left_ticket')` |
| `canvas-01.html` | `6313-6332` | 新增 `refreshBarHeight()` + `resize` 监听 |
| `tools/verify.js` | 项 14 Part 2b | 新增断言：点 `#pkTicketDurBtn` → 票面 21 且仪表盘 ruler 21 |
| `tools/verify.js` | 项 15 | 新增断言：`morphMidSteps ≥ 3`（变形中间值档数，护栏 P0）、`contentWidth ≥ 40 且不裁切`（护栏 P1，窄屏） |
| `tools/stamp-demo-version.py` | `DEMO_VERSION` + 历史 | v3.12 盖章；历史补 v3.11 / v3.12 两轮条目 |

## 5 · 实测证据

### 5.1 P0 变形动画（探针 `/private/tmp/s71.js`、`/private/tmp/s72.js`）

| 视口 | 变形过程采样 | 判定 |
|---|---|---|
| 1133（横排，宽度轴） | 360 → 341 → 165 → 56 → 50（5 档） | 插值，非跳变 ✅ |
| 744（feed，高度轴） | 791 → 728 → 279 → 61 → 52（6 档） | ✅ |
| 440（feed，高度轴） | 666 → 639 → 342 → 72 → 52（5 档） | ✅ |
| 反向「重新选择」（1133，宽度轴） | 50 → 60 → 196 → 347 → 360（15 档） | ✅ |
| 窄条淡入 | opacity 0.18 → 0.68 → 0.92 → 0.995 → 1 | ✅ |

### 5.2 P1 440 横条内容（`/private/tmp/s70.js`）

```
440 视口：内容「正常长音练习」实测宽 71.3px（scrollWidth 71 ≤ clientWidth，无裁切）
         窄条内 BPM display=none（腾位给内容）；重选按钮 60px，右侧留白 11px
```

### 5.3 P1 时长双向（`/private/tmp/s70.js`）

```
点票面时长卡片按钮 → 票面 11 · 仪表盘 #rulerInput 11 · 窄条剩余 11:00（三处一致）
```

### 5.4 P2 窄条高度重算（`/private/tmp/s72.js`）

```
1133 窄条 --cz-bar-h = 651px，左栏高 651px
切到 440 后 --cz-bar-h = 650px（已重算），feed 窄条高 52px
```

## 6 · 门禁证据

```
python3 tools/sync-demo-templates.py --check  → PASS（6 模板字节级一致）
python3 tools/check-layout-modes.py          → PASS（CSS [data-vp] 0 处）
node tools/verify.js --strict                → 15/15 PASS
  项 14 ruler↔票夹双向 + 窄条 18:00 + 票面时长键回灌 ruler   ✅ 9/9
  项 15 空态 / 满项变形（morphMidSteps≥3）/ 窄条不塌 / 时间横排 / 内容不裁切 / 重选保留 / 计时禁用  ✅ 3/3
```

## 7 · 红线

- 画布源 `docs/demos/practice-ticket-v4-260920.html` **零改动**（sha256 前 16 = `e86d4bc56163218d`）。
- 权威源唯一 `cards/card-*.html`；改完必须 `python3 tools/sync-demo-templates.py`（本轮已 stamp → sync → check PASS）。
- CSS 禁 `[data-vp]`；不引新 hex，一律 `--dash-*`。
- 探针与截图统一放 `/private/tmp`，不进仓库。
- 未 push / 未开 PR / 未 merge / 未打 tag。

## 8 · 交接给下一个 session

1. 先读本文件 + `VERSIONS.md`，再从 §1 的 commit 继续。
2. dad 验收重点看：① 首次打开的**空态**票夹；② 选满两项的**变形动画是否连贯**（不再瞬间跳变）；③ 窄条上的**「重新选择」**（点了变回票夹、选择保留、计时中置灰）；④ **拖 dashboard ruler 时左侧票夹时长是否同步**。
3. 遗留 P1（挂起，等 dad 拍板）：外层 `#czPresets` 在 541–660px 宽度区间溢出（只影响 demo 调试壳）。
