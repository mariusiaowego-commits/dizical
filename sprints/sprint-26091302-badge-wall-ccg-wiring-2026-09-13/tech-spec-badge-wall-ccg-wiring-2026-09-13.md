---
id: 26091302-tech-spec
type: tech-spec
version: 0.1.0
date: 2026-09-13
status: 进行中
tags: [tech-spec, dizical, badge, ccg, wiring]
---

# TECH-SPEC — 图鉴接线（B6）

## 1. 现状基线（实测，非推测）

| 项 | 事实 | 出处 |
|----|------|------|
| CCG 渲染器 | `DizicalCCG`（IIFE，挂在 `window`） | `static/js/badge-ccg.js:660-673` |
| 导出 API | `BADGE / mountCard / unmountAll / claim / openClaim / closeClaim / checkUnclaimed / startFps / setMaxTilt / setHoloGain / flipAll` | 同上 |
| 挂载签名 | `mountCard(stage, scheme, data)`：设 `ccg-stage ccg-<scheme>` + `data-ccg-theme = d.card_theme \|\| d.theme \|\| "azure"`，`innerHTML = cardMarkup(...)`，`bindReady()`，再注册进 `cards` 并常驻 rAF | `badge-ccg.js:223-410` / rAF `:623` |
| 数据 shape | `{id, name, tag, image, cond, story, date, stars, no, card_theme}` | `badge-ccg.js:18-29` + `normalize()` `:553` |
| 卡面 DOM | `frontMarkup()` 出 `.ccg-foil-stack`(z1 背景箔) / `.ccg-art-frame > .ccg-art-window` / `.ccg-foil-stack.ccg-foil-over`(z6 扫光) / `.ccg-frame` / `.ccg-holo-head` / `.ccg-info-bar` / `.ccg-plate` | `badge-ccg.js:152-192` |
| 唯一已接线真实流程 | 领取弹窗 `_badge_claim_modal.html`（35 行） | `_sidebar.html:758` + `:763`；`practice.html:2141,2230` |
| 我的成就页 | 961 行，grep `ccg` = 0；卡墙 `.b-card/.b-img-wrap/.b-img`；点开 `openModal()` 读 `dataset`（img/name/tag/cond/date/desc/locked） | `templates/achievements.html:745-800`；弹窗 markup `:617-637` |
| 成就殿堂页 | 507 行；卡墙模板字符串 `data-img="${esc(d.badge_url)}"`；自带 `#modal-*` | `templates/badges.html:331`、`:287`、CSS `:164-260` |
| 两页 gsap | 已从 CDN 引入（无需新增依赖） | `achievements.html:9` / `badges.html:8` |
| 样式版本 | `badge-ccg.css` v1.5.0（1410 行）+ `badge-ccg-themes.css` | 文件头注 |

## 2. 设计（三个新契约）

### 2.1 `mountCard(stage, scheme, data, opts)` — 第 4 参 `opts`

- `opts.static === true`：只出 markup + 一次性 `paint()`（静止态：`px=50, py=IDLE_Y, lit=IDLE_LIT`），
  —— **不绑 pointer、不 push `cards`、不进 rAF**；stage 加 `is-static` 类（CSS 关过渡/关 hover 抬升）
- `opts.locked === true`：stage 加 `is-locked` 类 → CSS 灰度 + 压暗 + 锁标（纯前端，不生成灰度图）
- **省略 `opts` 时行为与现在完全一致** ⇒ 领取弹窗零回归

### 2.2 列表卡（两个图鉴页）

- 每张卡的外层 `.b-card`（网格/筛选/CSS 依赖）**保留**，只把内部的 `.b-img-wrap + img` 换成
  `<div class="ccg-stage" data-...></div>` 并 `mountCard(el, 'holo', data, {static:true, locked})`
- 数据源不变：仍走各页现有 `data-*` / JSON payload（含 `card_no` → `no`、`card_theme` → `theme`）
- 点击行为不变：仍调原 `openModal(card)`

### 2.3 详情弹窗

- 旧 `#modal-box` 内部换为领取弹窗同款双栏：左 `.ccg-claim-stage`（挂**交互**卡 `mountCard(el,'holo',data)`）+ 右文案区
- 打开时挂载、关闭时 `unmountAll(overlay)` 释放（防 rAF/监听泄漏）
- 保留旧字段语义：名称 / tag / 条件 / 日期 / 故事；locked 时提示语沿用现文案

## 3. 版本号与冻结纪律

- 本次改动触及卡面呈现（新增静态/锁定两态）⇒ `badge-ccg.js` / `badge-ccg.css` / demo 页 chip
  同步升 **v1.6.0-dev**（未验收不带 `-dev` 之外的号；dad 说「定了」才 freeze）
- `static/demo-archive/**` **只读**，本次不 freeze、不覆盖

## 4. 不做

- 后端 / API / DB 一律不动（本次无 API 变更 ⇒ API-CHANGELOG 不新增节）
- 盲盒区、页面外壳、B3/B4 定档、用户端主题选择器
