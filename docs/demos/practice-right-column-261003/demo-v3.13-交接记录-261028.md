---
source: ai-agent
date: "2026-10-28"
doc_type:
  - handoff
tags: [dizical, practice, demo-v3.13, handoff, s22]
project:
  - dizical
is_done: false
---

# HANDOFF · dizical practice 右栏 demo v3.13（写于 2026-10-28）

    写入人   codex（本线程独立收口）
    工作目录 /Users/mt16/dev/dizical · 分支 feat/practice-ui-iter-260920
    demo 服务 http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html（PID 97410，curl 200，本轮未重启）

---

## 1 · 现在到哪了

```
demo 版本   v3.13（2026-10-28 盖章，24 页徽章 + VERSIONS.md 已重写；历史补 v3.13 条目）
本轮范围     S22 续轮：开始计时的「就绪门禁」—— 票夹选齐才允许开始，计时时长以票夹为真源
commit      HEAD = 4be845f（v3.12）；本轮改动 → 新 commit（沿用 dad 授权：只 commit，不开 PR / 不 merge / 不 push / 不打 tag）
门禁        verify.js --strict 16/16 PASS · sync-demo-templates --check 6/6 字节级一致 · CSS [data-vp] 0 处
待办        dad 肉眼验收 v3.13；遗留 P1（外层 #czPresets 541–660px 溢出）等 dad 拍板
```

## 2 · dad 本轮三条要求（原文要点）+ 落点

| dad 原文 | 落点 | 状态 |
|---|---|---|
| 「左边票夹还没选择科目或没选择全的时候，右边计时器点击开始就能计时」 | 仪表盘 A 卡「开始」在票夹未选齐时 `disabled`，点击无任何反应；读数行与按钮 title 给出原因 | ✅ |
| 「这个记录的是什么时？计时器记录的应该是票夹选择好的时间」 | 计时时长取票夹真源：票夹 18 分 → A 卡 ruler 18 → 计时 18，窄条剩余 18:00 | ✅ |
| 「目前只是前端 demo UI，后续正式开发时还需要后端一起连调，做好后端逻辑的交互」 | 见 §5 前后端契约（demo 用总线 ready 通道模拟，正式版落到接口与落库口径） | ✅（契约已写，未动后端代码） |

## 3 · 改了什么

### 3.1 票夹侧（唯一真源）

| 文件 | 位置 | 内容 |
|---|---|---|
| `canvas-01.html` | `~6096-6136` | 新增 `window.__czPracticeReady()`：汇总 `subjectId / subjectName / content / durationMin` 与 `ready / reason`（原因文案：先科目 → 再内容 → 再时长） |
| `canvas-01.html` | `~6138-6148` | 新增 `pushPracticeReady()`：把就绪状态经总线推给仪表盘卡 |
| `canvas-01.html` | `syncStartState()` 末尾 | 每次选择变化都推一次就绪状态（与票夹「开始」按钮同一份判据） |
| `canvas-01.html` | `enterRun()` | **删掉自动补选**（原先会替用户挑科目 + 内容），改为未就绪就 toast 原因并返回；就绪则把票夹时长推给仪表盘后再进计时态 |

### 3.2 总线（画布 ↔ 卡片）

| 文件 | 位置 | 内容 |
|---|---|---|
| `canvas-01.html` | `onReady()` / `pullReady()` / `syncReadyFromCanvas()` | 新增 **ready 通道**：`DizicalPracticeBus.ready(flag, reason)` → A 卡 `setPracticeReady()`；卡载入/重挂时 `settleAfterReady()` 重新推送（否则 A 卡还停在默认可用） |
| `canvas-01.html` | `S` 状态 | 新增 `ready / readyReason` 字段，`api.read()` 可读 |

### 3.3 仪表盘卡（`cards/card-a-dashboard.html`，权威源）

| 位置 | 内容 |
|---|---|
| `~1968-1994` | `practiceReady / practiceReadyReason` + `syncPrimaryEnabled()` + `window.setPracticeReady(flag, reason)` + `window.getPracticeReady()` |
| `enterRun / enterPause / enterPrep` | 每次切态都重算按钮可用性（只有准备态会被拦；计时中的「暂停」永远可点） |
| `enterPrep` | 读数行文案按就绪状态切换：`00:00 · 待开始` ↔ 未就绪原因 |
| `btnPrimary` click | 未就绪时直接 return，不产生任何计时 |

## 4 · 实测证据（探针 `/private/tmp/s73.js`，1133 + 440）

| 阶段 | A 卡「开始」 | 读数行 | 仪表盘状态 | 票夹 |
|---|---|---|---|---|
| 空态（未选） | `disabled=true`，title「请先在左侧票夹选择练习科目」 | 同左文案 | `prep` | 未选 |
| 空态点「开始」 | 仍 `disabled=true` | 不变 | 仍 `prep`（**没有开始计时**） | 未选 |
| 只选科目 | `disabled=true`，title「请先在左侧票夹选择本次练习内容」 | 同左 | `prep` | 科目已选 |
| 选满两项 | `disabled=false` | `00:00 · 待开始` | `prep` | 科目 + 内容 |
| 票夹时长改 18 | `disabled=false` | — | A 卡 ruler = **18** | 票面 18 |
| 点「开始」 | — | `00:00 · 练习中` | `run`，卡内 duration = **18** | 票面 18 / 窄条 18:00 |

440 视口结果一致（`btnDisabled` true → false → run，`cardDuration=18`，`railRemain=18:00`）。

## 5 · 前后端联调契约（正式开发照这个来）

### 5.1 前端真源与判据（demo 已实现，接口名换成后端字段）

```
票夹 = 真源：
  subject_id     practice_items.id          （必填）
  content        本次练习内容（胶囊/输入）   （必填）
  duration_min   练习时长（1..30）           （必填）
  tempo_bpm      练习速度（票夹 BPM）         （可选，缺省用 subject 的 last_tempo_bpm）

就绪判据 = 三项齐 → 可开始；否则按钮 disabled + 原因（reason 文案前端本地生成，后端返回同款文案覆盖）
```
demo 落点：`canvas-01.html` 的 `window.__czPracticeReady()` 就是这个判据的唯一实现；
正式版建议把同一判据放到后端，前端只做乐观禁用（避免前后端两套判据漂移）。

### 5.2 接口建议（沿用现有 `practice-sessions` 体系）

1. **开始前读票夹快照**：`GET /api/practice-sessions/latest?item_id={subject_id}` 拿默认速度；
   另需一个「今日练习内容选项」来源（`practice_items.content_options` 或老师要求 `weekly_assignments`）。
2. **开始/结束落库**：走 `save_practice_session_and_daily_summary`（`src/kid_app/app.py:2116` 一带），
   每条 session 的 `items` JSON 记 `{item_id, minutes, content, tempo}`，
   其中 `minutes` **必须取票夹的 `duration_min`**，不允许用卡片默认值。
3. **后端兜底校验**：开始请求缺 `item_id` / `duration_min` → `409 {"ok": false, "code": "NOT_READY", "reason": "..."}`；
   前端收到 `NOT_READY` → 禁用「开始」并展示 `reason`（与 demo 的提示文案一致）。
4. **并发**：`PUT /api/practice-sessions/{session_id}` 已有 `If-Match` 乐观锁 + `409 VERSION_CONFLICT`
   （`src/kid_app/app.py:1804`），开始/结束沿用即可，不需要新机制。
5. **时间口径**：`daily_practices.practice_at` 仍是 CST ISO 字符串（生产真件口径，不改）。

### 5.3 demo 侧与正式版的差异（明写，避免误当已接后端）

- demo 的 ready 通道是 **iframe 内存态**（`DizicalPracticeBus.ready`），刷新即失效，**没有落库、没有调后端**。
- demo 调试壳 `window.__cz.setCanvasStage('run')` 仍会**代选**科目/内容（那是壳的调试行为，不是产品行为），
  产品路径（用户点仪表盘「开始」）已完全走门禁。
- demo 的 A 卡 `duration` 与票夹 `duration` 通过总线双向同步；正式版单一真源在后端快照，前端不再各存一份。

## 6 · 门禁证据

```
python3 tools/sync-demo-templates.py --check  → PASS（6 模板字节级一致）
python3 tools/check-layout-modes.py          → PASS（CSS [data-vp] 0 处）
node tools/verify.js --strict                → 16/16 PASS
  项 14 ruler↔票夹时长双向 + 窄条 18:00 + 票面时长键回灌 ruler   ✅ 9/9
  项 15 选完两项即变形 + 重新选择                              ✅ 3/3
  项 16 开始计时就绪门禁（未选齐点不动 / 选齐后计时时长=票夹时长） ✅ 3/3
```

`verify.js` 本轮新增：项 16（`tools/verify.js` 的 `startGate` 段）——覆盖「空态点开始无效」「只选科目仍禁用」
「选齐后可点」「票夹 18 → 卡内计时 18」四段。

## 7 · 红线

- 画布源 `docs/demos/practice-ticket-v4-260920.html` **零改动**（sha256 前 16 = `e86d4bc56163218d`）。
- 权威源唯一 `cards/card-*.html`；改完必须 `python3 tools/sync-demo-templates.py`（本轮已 stamp → sync → check PASS）。
- CSS 禁 `[data-vp]`；不引新 hex，一律 `--dash-*`。
- **本轮没有改任何后端代码**（`src/` 零改动）；后端只在 §5 写成契约，等 dad 点头再联调。
- 探针与截图统一放 `/private/tmp`，不进仓库。
- 未 push / 未开 PR / 未 merge / 未打 tag。

## 8 · 交接给下一个 session

1. 先读本文件 + `VERSIONS.md`，再从 §1 的 commit 继续。
2. dad 验收重点：① 空态下仪表盘「开始」点不动且提示清楚；② 选齐科目 + 内容后按钮恢复；③ 拖票夹时长到 18 再开始，计时就是 18 分钟；④ 停止后回到准备态，按钮状态与就绪判据一致。
3. 下一步若 dad 点头做后端联调：先做 §5.2 的 `NOT_READY` 契约（后端兜底 + 前端提示对齐），再做落库字段对齐。
