---
source: ai-agent
date: "2026-10-27"
doc_type:
  - handoff
tags: [dizical, practice, demo-v3.11, handoff, s22]
project:
  - dizical
is_done: false
---

# HANDOFF · dizical practice 右栏 demo v3.11（写于 2026-10-27）

    写入人   codex（本线程独立收口）
    工作目录 /Users/mt16/dev/dizical · 分支 feat/practice-ui-iter-260920
    demo 服务 http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html（PID 97410，在线 200）

---

## 1 · 现在到哪了

```
demo 版本   v3.11（2026-10-27 盖章，24 页徽章 + VERSIONS.md 已重写）
本轮范围     S22：票夹空态 + 选满两项即变形窄条 + 「重新选择」+ ruler↔窄条时长联动 + 两个自测出来的回归
commit      HEAD = 8889873（v3.10）；本轮改动在工作区（dad 授权「只 commit，不开 PR / 不 merge / 不 push / 不打 tag」）
门禁        verify.js --strict 15/15 PASS · sync-demo-templates --check 6/6 字节级一致 · CSS [data-vp] 0 处
待办        dad 肉眼验收 v3.11；agy 只读复核在跑（见 §7）
```

## 2 · dad 本轮四条需求（原文要点）

1. 标注问题解决 → 上一轮 v3.10 已做（卡槽插入卡改主题色 + 去透明度）。
2. 票夹准备态改制：
   - 2.1 首次打开（没有任何选择）出现**空态**：科目、本次练习内容都置空，等待首次选择。
   - 2.2 用户填完这两项后**立即**激活「变形为黑色窄条 bar」，替换原来「点仪表盘开始才变形」的策略。
   - 2.3 窄条 bar 上增加同 UI 规范的「重新选择」按钮；点击后从窄条变形回票夹 UI，**选择保留**最近一次。
   - 2.4 「重新选择」在计时期间置灰不可点。
3. BUG：拖 dashboard 刻度尺 ruler 改练习时长时，左侧票夹时长不联动。
4. 前端设计交给 herdr 里的 agy（`w45:p1`，cwd `/Users/mt16/dev/dizical`）。

## 3 · 改了什么（全在 `docs/demos/practice-right-column-261003/`）

### 3.1 空态（agy 交付，我复核）
- `canvas-01.html:~5383` `let cur = null`（不再预选第一项）；`canvas-01.html:5626` `renderEmptyTicket()`。
- 空态文案：科目名「未选择科目」、副标「点击打开票夹选择练习曲目」；内容区 `.pk-empty-hint`「请先在上方选择练习科目」。
- `#pkStartBtn` 走 `syncStartState()`：两项不齐即 `disabled`。
- 实测三视口：`subj="未选择科目"`、`startDisabled=true`、`bar=false`。

### 3.2 选满两项即变形（**我重写了 agy 的实现**）
agy 原版用 `.stage-running` 承载窄条 → 一选完两项仪表盘就进计时态（卡片提前插进卡槽、chip「进行中」、`prep-only` 全隐藏）。
我改成独立类：

| 位置 | 内容 |
|---|---|
| `canvas-01.html:451-453` | `stage-bar` 下 `.run-only / .run-only-block` 强制 `display:none`（保留 prep 语义） |
| `canvas-01.html:2120-2175` | `.stage-bar` 几何：横排 `#pkLeftCol` 50px 竖条 / feed 视口 100%×52px 横条；`.pk-run-rail` 显示 |
| `canvas-01.html:17456-17465`（注入 CSS） | feed 视口 `stage-bar #pkLeftCol` 52px 横条；并把 `height:auto !important` 的 prep 规则**排除 `.stage-bar`** |
| `canvas-01.html:~6240` | `morphTicketToBar()` 只加 `stage-bar`（删掉 `stage-running` / `cz-ticket-live` / `cz-ticket-enter` / lockOverlay / insertedHead 那套） |
| `canvas-01.html:~6400` | `expandBarToFolio()` / `resetToPrepClean()` 撤 `stage-bar` + 清 `--cz-bar-h` |
| `canvas-01.html:~6597` | `enterRun()` 的 `isBarDeformed` 分支补齐计时态（`stage-running` + `cz-ticket-live` + lockOverlay + `syncSlotMode()` + `pkTick()`），不重播变形 |
| `canvas-01.html:~6666` | `exitRun()` 回「窄条准备态」（`stage-prep` + 保留 `stage-bar`），只有点「重新选择」才展开 |

### 3.3 窄条上的「重新选择」
- 按钮 `#pkRailReselectBtn`（`canvas-01.html:4539`），样式 `2124-2325`；`updateReselectBtnState()` 在 `started/timerRunning` 时 `disabled`。
- 实测尺寸：1133 竖排 `32×65`（x25,y786）；744/440 横排 `66×28`。

### 3.4 ruler ↔ 票夹/窄条时长联动
- `cards/card-a-dashboard.html:1829` `applyDuration(nextMin, fromInput)` 回写 `#rulerInput.value` 并派发 `input`（`detail.fromApply` 防环）；新增 `rulerInput` 的 `input` 监听 + `window.applyDuration`。
- `canvas-01.html:6956` 包装 `window.ttSetDuration`：同步 `#pkTicketDurVal`，并调 `updateCollapsedProgress()` 让窄条 `#pkRailRemain` 跟着变（**这是 dad 第 3 条的正解**，agy 只做了票面没做窄条）。
- 实测：ruler 10→18 ⇒ 票面 18 且窄条 `10:00 → 18:00`；票面 +2 ⇒ ruler 20（三视口一致）。

### 3.5 我自测出来的两个回归（agy 没有覆盖）

**回归 A · 计时态被旧兜底打回准备态**
`setCanvasStage()` 的 520ms 收敛兜底定时器**没有代际令牌**：连点 prep → run 时，上一轮 `prep` 的定时器在 run 期间开火，
调 `forceCanvasStage('prep')` 把刚进的计时态打回准备态。而 S22 之后 `exitRun` 保留窄条（leftW=50），
旧判定「prep 必须 ≥300px」**永远不满足** → 这个旧定时器**必然**在 520ms 后开火。
- 修：`canvas-01.html:~19776` 新增 `var czStageSyncToken = 0`，每次 `setCanvasStage` 取 `myToken = ++czStageSyncToken`，
  `tick()` 每次进出都先比 token；收尾判定改为 `okW = want ? (w<=60) : (w>=300 || barNow)`。
- 证据：修复前 1133 C2/C3 在 2200ms 时 `stage="stage-bar stage-prep"`、`opacity=0`（卡片消失）；
  修复后 `stage="stage-bar stage-running cz-ticket-live"`、`opacity=1`。

**回归 B · 窄条塌成 0 高**
`.stage-bar` 下 `#pkTicketCard` 是 `display:none` → `#pkLeftCol` 塌成 0 高，`.pk-run-rail` 又是 `height:100%` → 整条只剩 2px 细边；
另外注入 CSS 里 `#pkLeftCol { height:auto !important }` 也会压扁它。
- 修：`canvas-01.html:6281` morph 时写 `--cz-bar-h = prepHeight`；`2133` 用 `height: var(--cz-bar-h)`；
  注入 CSS（`17266` / `17461`）把 `height:auto` 规则加 `:not(.stage-bar)`。
- 证据：修复前 1133 `leftH=0`、rail `2px`；修复后 `leftH=791`、rail `791`。

**回归 C · 剩余时间倒读**
`.pk-run-rail-remain-val` 原是 `writing-mode: vertical-rl; transform: rotate(180deg)` → 「10:00」被读成竖排倒字（视觉像 00:01）。
- 修：`canvas-01.html:2217` 改 `horizontal-tb` + `transform:none` + 11px（`10:00` 实测宽 32px，能进 50px 窄条）。

## 4 · 实测证据（`/private/tmp/s68.js`，3 视口 × 4 阶段）

| 视口 | 空态 | 只选科目 | 选满两项（窄条） | 点仪表盘「开始」 |
|---|---|---|---|---|
| 1133 | 未选择科目 / startDisabled / bar=false | bar=false | bar=true, timing=**false**, `stage-prep stage-bar`, 50×791, 剩余 10:00 横排, 卡槽 hidden | timing=true, 按钮「暂停」, dash=run, 卡槽 visible, 重选 disabled, chip 进行中, 剩余 09:58 |
| 744 | 同上 | bar=false | bar=true, timing=false, 712×52, 剩余 10:00, 卡槽 hidden | timing=true, dash=run, 卡槽 visible, 重选 disabled |
| 440 | 同上 | bar=false | bar=true, timing=false, 408×52, 剩余 10:00, 卡槽 hidden | timing=true, dash=run, 卡槽 visible, 重选 disabled |

- 结束计时：`bar=true, timing=false, stage="stage-bar stage-prep"`，票夹**不自动展开**（dad 2.3 语义）。
- 点「重新选择」：`bar=false, stage="stage-prep"`，科目「吸气长音」/ 内容「正常长音练习」**保留**。
- 计时中点「重新选择」：无效（`bar=true, timing=true`）。

**截图**：`/private/tmp/s68-{1133,744,440}-{A-empty,B-subj,C-bar,D-run}.png`（12 张）

## 5 · 门禁证据

```
python3 tools/sync-demo-templates.py --check  → PASS（6 模板字节级一致）
python3 tools/check-layout-modes.py          → PASS（CSS [data-vp] 0 处）
node tools/verify.js --strict                → 15/15 PASS
  项 13 卡槽卡主题色 + 实色不透明          ✅ 27/27
  项 14 ruler↔票夹时长双向 + 窄条 18:00     ✅ 9/9（本轮加宽：Part 3 断言窄条 railRemain）
  项 15 选完两项即变形 + 重新选择          ✅ 3/3（本轮加严：窄条不塌 railH、剩余时间横排可读 remainWM/remainFitsBar）
```

`verify.js` 本轮改动：`tools/verify.js:557-655`（项 14 Part 3）、`656-770`（项 15 新断言）、`800+`（打印口径）。

## 6 · 红线

- 画布源 `docs/demos/practice-ticket-v4-260920.html` **零改动**（sha256 前 16 = `e86d4bc56163218d`，本轮复验）。
- 权威源唯一 `cards/card-*.html`；改完必须 `python3 tools/sync-demo-templates.py`（本轮已跑，sync → check PASS）。
- CSS 禁 `[data-vp]`；不引新 hex，一律 `--dash-*`。
- 探针与截图统一放 `/private/tmp`，不进仓库。
- 未 push / 未开 PR / 未 merge / 未打 tag。

## 7 · agy 只读复核（进行中）

- 任务：`20261027-172047-s22-v311-folio-bar-review`（pane `w45:p1`，session `7aac699d-…`）
- brief：`/private/tmp/herdr-dispatch/tasks/20261027-172047-s22-v311-folio-bar-review/brief.md`
- result：同目录 `result.md`（截至本文件写入时 agy 仍在跑，`status=working`）
- 收到结果后要按「P0/P1/P2 + path:line + 证据」逐条处理，再决定是否进 v3.12。

## 8 · 交接给下一个 session

1. 先读本文件 + `VERSIONS.md`，再从 `HEAD = 8889873` + 工作区改动继续（本轮改动尚未 commit，见 §1）。
2. 待办顺序：agy 复核意见 → 修 → 复跑 `verify.js --strict` → 升 v3.12（如需要）→ dad 验收。
3. 遗留 P1（上一轮起挂起，未处理、等 dad 拍板）：外层 `#czPresets` 在 541–660px 宽度区间溢出。
