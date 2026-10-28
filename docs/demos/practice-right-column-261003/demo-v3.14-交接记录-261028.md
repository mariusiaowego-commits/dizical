---
source: ai-agent
date: "2026-10-28"
doc_type:
  - handoff
tags: [dizical, practice, demo-v3.14, handoff, s22]
project:
  - dizical
is_done: false
---

# HANDOFF · dizical practice 右栏 demo v3.14（写于 2026-10-28）

    写入人   codex（本线程独立收口）
    工作目录 /Users/mt16/dev/dizical · 分支 feat/practice-ui-iter-260920
    demo 服务 http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html（PID 97410，curl 200，本轮未重启）

---

## 1 · 现在到哪了

```
demo 版本   v3.14（2026-10-28 盖章，24 页徽章 + VERSIONS.md 已重写；历史补 v3.14 条目）
本轮范围     S22 续轮：就绪引导 —— 票夹没选齐时点仪表盘「开始」，引导用户去补缺的那一项
commit      HEAD = 4d38318（v3.13）；本轮改动 → 新 commit（沿用 dad 授权：只 commit，不开 PR / 不 merge / 不 push / 不打 tag）
门禁        verify.js --strict 17/17 PASS · sync-demo-templates --check 6/6 字节级一致 · CSS [data-vp] 0 处
待办        dad 肉眼验收 v3.14；遗留 P1（外层 #czPresets 541–660px 溢出）等 dad 拍板
```

## 2 · dad 本轮要求（原文要点）+ 落点

| dad 原文 | 落点 | 状态 |
|---|---|---|
| 「增加一个 onboarding 提示，只在用户在置灰状态下点击计时开始时出现」 | 引导只由置灰「开始」的 click 触发，选齐后自动收起，不主动弹出 | ✅ |
| 「引导用户去先选择科目或者练习内容」 | 引导落在票夹上，聚光框圈住该补的控件，CTA 直接打开对应入口 | ✅ |
| 「只提醒一个，优先级按科目 > 练习内容 > bpm，哪个没选择就提醒哪个，每次点击只提醒一个（优先级最高的那一个）」 | `missingField()` 按 subject → content → bpm 取第一个缺失项，一次只渲染一条 | ✅ |
| 「设计一个引导样式」 | coach mark：聚光框 + 带箭头的引导卡，浅银/深墨两套皮肤共用 token | ✅ |
| 「744、440 视口下视觉 focus 在下面第二屏的 dashboard，出一个提示在上面票夹也看不到」 | 引导弹出时先把票夹目标**滚回浏览器视口**（实测 744 scrollY 742→0、440 922→143），1133 不动 | ✅ |

## 3 · 改了什么

### 3.1 仪表盘卡（`cards/card-a-dashboard.html`，权威源）

| 位置 | 内容 |
|---|---|
| `~720-725` | `.pill button.is-locked`：置灰视觉（opacity .38 / 去实心底 / 灰字），替代原来的真 `disabled` |
| `~1976-1985` | `syncPrimaryEnabled()` 不再写 `disabled`，改 `aria-disabled` + `is-locked` |
| `~2100-2116` | btnPrimary click：未就绪时先 `parent.__czGuideShow()` 拉起引导，再 return，不产生计时 |

**为什么去掉真 `disabled`**：浏览器不给 `disabled` 按钮派发 click，引导根本接不到点击。
`aria-disabled` 保留屏幕阅读器语义，视觉上仍然置灰。

### 3.2 画布层引导（`canvas-01.html`，宿主注入，画布源零改动）

| 位置 | 内容 |
|---|---|
| `__CZ_CSS` 末尾 | `.cz-guide` / `.cz-guide-spot` / `.cz-guide-arrow` 样式（238×128，浅银白底 + 深墨黑底，箭头三角） |
| `~18750` | `__CZ_GUIDE_SRC`：注入画布文档执行的引导逻辑 |
| `injectCanvas()` | 新增第 ⑥ 步：注入 `#czGuideLib` 脚本 |

核心函数：

```
missingField()   优先级 subject > content > bpm，返回第一个缺失项
targetFor(field) subject → #pkTicketSubjectBlock；content → #pkSessionSlot .pss；bpm → #pkBpmVal
placeGuide()     引导卡锚在目标正下方，水平居中并夹进票夹内；箭头对准目标中心
                 目标下方空间 < 140px 时翻到目标上方（is-arrow-bottom）
__czGuideShow()  计算缺失项 → 渲染文案 → 定位 → 打开；选齐则收起
```

### 3.3 文案与 CTA

| 缺失项 | 标题 | CTA | CTA 动作 |
|---|---|---|---|
| 科目 | 先选择练习科目 | 打开票夹选科目 | 调 `openFolio()` |
| 练习内容 | 再选本次练习内容 | 选择练习内容 | 聚焦输入框并打开下拉 |
| 速度 | 再确认练习速度 | 去调速度 | 聚焦票面 BPM 数字 |

四步进度条（科目 / 内容 / 速度 / 时长）里已完成的项打勾，当前项高亮。

### 3.4 关闭与自动收起

- Esc、点引导外任意处 → 收起
- 用户补上缺失项后（`pushPracticeReady()` 里 `missingField()` 变了）→ 引导自动跟到下一项或收起
- 计时开始（`enterRun()`）→ 收起

### 3.5 跨屏回视野（v3.14b 补丁）

**问题**：744/440 是纵向流，票夹在第一屏、仪表盘在第二屏，两屏相隔 1300px+：

| 视口 | 票夹科目（外层页 y） | 仪表盘「开始」按钮（外层页 y） | 相距 |
|---|---|---|---|
| 744 | 302.7 | 1640.4 | 1337.7px |
| 440 | 423.2 | 1567.1 | 1143.9px |

用户点的是第二屏的按钮，引导却画在第一屏的票夹上 —— 等于没提示。

**解法**：`scrollTargetIntoView(el)` —— 引导弹出前先把目标滚进浏览器视口。
目标的外层绝对 y = 画布 iframe 顶 + 目标在画布内的 y + 外层 scrollY；
已经在视口里（含 96px 安全边距）就不动，否则
`scrollTo({ top: absY - vh * 0.28, behavior: 'smooth' })`。
画布 doc 自身不滚（内容全在 iframe 内），真正要滚的是外层页面，所以用 `win.top`。

**同时改的定位规则**：引导卡改为**水平居中于目标**（原来贴目标左边缘），再夹进票夹与视口范围；
箭头仍单独对准目标中心，两者解耦。原因：744 下贴左会让引导压住右侧的「10 分钟」数字
（截图实测），居中后不再压邻居。

## 4 · 实测证据

探针 `/private/tmp/s74.js`（1133 / 744 / 440 三视口一致）：

| 阶段 | 引导 | 字段 | 仪表盘状态 |
|---|---|---|---|
| 空态（未点） | 关闭 | — | `prep`，按钮 `is-locked` opacity .38 |
| 点置灰「开始」 | 打开，「先选择练习科目」 | subject | 仍 `prep`（没开始计时） |
| 选了科目 | 自动改指「再选本次练习内容」 | content | `prep` |
| 再点一次置灰开始 | 仍只提示内容（不叠加） | content | `prep` |
| 选了内容 | 自动收起 | — | `prep`，按钮解锁 opacity 1 |
| 点「开始」 | 保持关闭 | — | `run` |

几何（1133 实测）：引导卡 238×128，落在票夹内（票夹 6..366 × 64..714.5，引导 111.8..349.8 × 194.8..323.2）；聚光框覆盖目标面积 ≥ 60%；箭头中心对准目标中心（目标 cx 186，箭头 cx 187）。

关闭行为（`/private/tmp/s74d.js`）：CTA「打开票夹选科目」→ 票夹弹窗 `display:flex` 且引导收起；Esc 收起；点引导外收起。

截图：`/private/tmp/g314-1133-light-subject.png`、`g314-440-ink-content.png` 等 8 张（浅银/深墨 × 1133/440 × 科目/内容）。

跨屏（`/private/tmp/s75b.js`，先滚到仪表盘那一屏，再点置灰开始）：

| 视口 | 外层 scrollY | 引导在浏览器视口内 | 票夹目标在视口内 | 聚光框贴目标 |
|---|---|---|---|---|
| 1133 | 30 → 30（不误滚） | ✅ | ✅ | ✅ |
| 744 | 742 → 0 | ✅ | ✅ | ✅ |
| 440 | 922 → 143 | ✅ | ✅ | ✅ |

横向越界复查（`/private/tmp/s75c.js`）：744 引导 x 253..491（票夹 16..728）、
440 引导 x 101..339（票夹 16..424），均未越出票夹。

截图：`/private/tmp/g314b-744-1-guide.png`、`g314b-440-1-guide.png`（纵向流下滚回票夹后的引导）。

## 5 · 门禁证据

```
python3 tools/sync-demo-templates.py --check  → PASS（6 模板字节级一致）
python3 tools/check-layout-modes.py          → PASS（CSS [data-vp] 0 处）
node tools/verify.js --strict                → 17/17 PASS
  项 16 开始计时就绪门禁（口径改为 aria-disabled + is-locked）  ✅ 3/3
  项 17 就绪引导（字段优先级 / 聚光覆盖 / 落在票夹内 / 选齐收起 / 计时后关闭 / 跨屏滚回视野） ✅ 3/3
```

**门禁口径修正两处**（都是把断言改成测实质，不是放宽）：

1. 项 16 的窄条剩余时间：`18:00` → 正则 `/^1[78]:\d\d$/`。
   原断言死盯 `18:00`，但倒计时是分钟级取整，第一秒 tick 后会显示 `17:59`，
   那是正确行为而不是缺陷。实质断言是「剩余落在 17~18 分钟区间」，
   同时仍要求 `cardDuration === 18 && ticketDur === 18`（时长确实取自票夹）。
2. 项 17 的跨屏用例**独立开一页**测：原来复用同一页，而那一页此前已进过 run 态，
   票夹已变形为窄条（位置全变），测到的不是「准备态空态点开始」这个真实场景。

## 6 · 红线

- 画布源 `docs/demos/practice-ticket-v4-260920.html` **零改动**（sha256 前 16 = `e86d4bc56163218d`）。
- 权威源唯一 `cards/card-*.html`；改完必须 `python3 tools/sync-demo-templates.py`（本轮已 stamp → sync → check PASS）。
- CSS 禁 `[data-vp]`；不引新 hex，一律 `--dash-*`（引导卡的白底/黑底走 `--dash-surface-soft` / `--dash-panel`）。
- **本轮没有改任何后端代码**（`src/` 零改动）。
- 探针与截图统一放 `/private/tmp`，不进仓库。
- 未 push / 未开 PR / 未 merge / 未打 tag。

## 7 · 交接给下一个 session

1. 先读本文件 + `VERSIONS.md`，再从 §1 的 commit 继续。
2. dad 验收重点：① 空态下点仪表盘「开始」弹出引导、指向票夹的科目区；② 选了科目后再点，引导改指练习内容输入框；③ 两项都选了，引导自动消失、按钮变实心可点；④ 深墨皮肤下引导底色跟着变深。
3. 已知取舍：置灰按钮不再是真 `disabled`（否则收不到点击），改 `aria-disabled`。键盘用户连按 Enter 也会触发引导，这是预期。
4. 下一步若 dad 点头做后端联调：仍按 v3.13 交接文档 §5 的 `NOT_READY` 契约（后端兜底 + 前端提示对齐），再做落库字段对齐。
