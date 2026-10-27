---
source: ai-agent
date: "2026-10-27"
doc_type:
  - handoff
tags: [dizical, practice, demo-v3.8, handoff, s19]
project:
  - dizical
is_done: false
---

# HANDOFF · dizical practice 右栏 demo v3.8（写于 2026-10-27）

    写入人   codex（本线程独立收口，agy 已休息）
    工作目录 /Users/mt16/dev/dizical · 分支 feat/practice-ui-iter-260920
    demo 服务 http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html（PID 97410）

---

## 1 · 现在到哪了

```
demo 版本   v3.8（2026-10-27 盖章，24 页徽章 + VERSIONS.md 已重写）
本轮范围     S19 全视口（1133/744/440）统一窄孔卡槽 + 440 视口 4 条批注修复（指示灯出黑区 / 卡槽不对称 / 读数靠中 / 按钮压喇叭孔）
commit      本轮全部改动已 commit 到 feat/practice-ui-iter-260920（版本锚点 commit，未开 PR / 未 merge / 未 push / 未打 tag）
门禁         verify.js --strict 11/11 PASS · sync-demo-templates --check 6 模板字节级一致 · CSS [data-vp] 0 处
待办         dad 肉眼验收 v3.8（见 §4）
```

## 2 · 本轮改了什么（附 path:line + 实测值）

### 2.1 根因复盘：440 刷新态 iframe 内 15px 滚动条引起指示灯出黑区 & 卡槽不对称（批注 1、2）
- **根因**：`localStorage` 存 `vp=440`（`canvas01_state`）刷新时，`syncAll()` 先执行 `syncModuleHeight()` 再 `mountSlot()`，量高时未带 `--cz-panel-pt`（57px），且 `measureCardContent()` 把 `.panel` 上内边距硬写 `10px 14px 6px`，导致 iframe 内 `scrollHeight 613 > clientHeight 612` 触发 15px 纵向滚动条，把 iframe 内 `#panel`（含电池）向左挤 15px，而外层 `.cz-astack-crown` 仍按无滚动条宽度定位 → 指示灯溢出黑区右缘、卡槽右缘压过电池右缘。
- **修复**：
  - `canvas-01.html:17329-17435` `updateCardSlotGeometry()`：三视口（1133/744/440）统一 `holeInset=28`、`cardInset=36`、露卡 `20%`（744/440 复刻 1133 窄孔设计）；读取 iframe 内 `#panel` 真实 `getBoundingClientRect()` 动态写 `.cz-astack-crown` 的 `left` / `right: auto` / `width`；写 `--pk-led-right = ((holeInset - 7) * 0.5) = 10.5px`。
  - `canvas-01.html:17110` + `17534`：`#pkPunchSlotWrap > .cz-slot-led { right: var(--pk-led-right, 10.5px) !important; }`，inline `led.style.right` 同步。
  - `canvas-01.html:16807-16808`：`MODULE_SCOPE` 中 `html.cz-fill.cz-feed` 及 `.page/.frame/.dash/...` 统一 `overflow: hidden !important`，杜绝 1px 抖动触发内部滚动条。
  - `canvas-01.html:17917-17924` `measureCardContent()`：`.panel` padding 改为 `var(--cz-panel-pt, 10px) 14px 64px`；`canvas-01.html:19214` `syncAll()` 量高前先调 `updateCardSlotGeometry(canvasDoc())`。
- **实测（Playwright 探针 `/private/tmp/probe-s33.js`，含 `localStorage` 440 刷新复现）**：

| 视口 | panel [L,R] | hole [L,R] | micL | batR | holeL−micL | holeR−batR | symDiff | led [L,R] | ledInPanel |
|---|---|---|---|---|---|---|---|---|---|
| 440 c=1 | [28, 412] | [56, 384] | 56.0 | 384.0 | 0.0px | 0.0px | 0.0px | [394.5, 401.5] | true |
| 744 c=1 | [28, 716] | [56, 688] | 56.0 | 688.0 | 0.0px | 0.0px | 0.0px | [698.5, 705.5] | true |
| 1133 c=1 | [406, 842] | [434, 814] | 434.0 | 814.0 | 0.0px | 0.0px | 0.0px | [824.5, 831.5] | true |

`innerScrollDiff = 0px`，三视口卡槽孔左右对称误差 `0.0px`，孔右缘与电池右缘对齐误差 `0.0px`，指示灯稳居右孔肩中心 `[394.5, 401.5] ⊂ panel [28, 412]`。

### 2.2 440 视口读数再往左、靠中间一点（批注 3）
- `cards/card-a-dashboard.html:1320-1348`（同步至 `canvas-01.html:8075-8103`）`alignReadoutWithCover()`：分别测量 `#digits` 与 `.unit` 宽度；当存在下标单位（如准备态「10 分钟」）时左移补偿 `shiftLeft = Math.max(18, unitW * 0.5 + 6)`，使主数字视觉中心向黑区中心靠拢；同时加左界夹紧 `minCx = leftBound + 14 + digitsW * 0.5`，防止计时态 4 位 `00:00` 左移过头压封面图；`enterRun()` / `enterPause()` / `enterPrep()`（`cards/card-a-dashboard.html:1957,2007,2022`）切换时触发 `requestAnimationFrame(alignReadoutWithCover)`。
- **实测（440 c=1）**：准备态主数字 `10` 中心从 `250.0px` 左移至 `215.7px`（黑区中心 `220.0px`，偏差仅 `-4.3px`）；计时态 `00:00` 与左侧封面图保持 `≥14px` 净距。

### 2.3 440 视口底部按钮与左边喇叭孔重叠修复（批注 4）
- `cards/card-a-dashboard.html:888-895,913-918` + `canvas-01.html:16895-16900`：440 档 `.grid-3col` 改为 `64px minmax(0, 1fr) 64px` + `column-gap: 8px`，`.grille-6x8` 缩至 `56×56px`，`.pill button` 左右内边距收至 `0 12px`。
- `cards/card-a-dashboard.html:1294-1318` `alignSpeakerWithCover()`：计算 `maxOffset = pillRect.left - 12 - sRect.right`，对喇叭孔右移偏移量做上限夹紧，保证喇叭孔与中央胶囊按钮至少留 `12px` 安全净距。
- **实测**：440 c=1 喇叭孔右缘到按钮左缘净距 `34.0px`（744 为 `155.0px`，1133 为 `32.0px`），重叠面积 `0.0px²`。

## 3 · 门禁证据（提交前跑过）

```
python3 docs/demos/practice-right-column-261003/tools/sync-demo-templates.py --check → PASS（6 模板字节级一致）
python3 docs/demos/practice-right-column-261003/tools/check-layout-modes.py         → PASS（CSS [data-vp] 0 处）
node docs/demos/practice-right-column-261003/tools/verify.js --strict               → 11/11 PASS（3 视口 × 3 组合）
git diff --check                                                                    → 无空白错误
```

## 4 · 待办与红线

- **待办**：dad 肉眼验收 `http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html`（v3.8）；确认无误后再决定是否开 PR / merge / 打 tag。
- **红线**：权威源唯一 `cards/card-*.html` + `sync-demo-templates.py`；CSS 禁 `[data-vp]`；画布源 `practice-ticket-v4-260920.html` 零改动；探针与截图统一放 `/private/tmp`。

## 5 · agy 独立前端验收结论（2026-10-27 13:49，只读）

任务 `20261027-134103-s19-v38-verify`（pane `w45:p1`），报告 `/private/tmp/herdr-dispatch/tasks/20261027-134103-s19-v38-verify/result.md`，verdict `ready_for_acceptance`，19 张截图 `/private/tmp/verify-*.png`。

**A. 批注验证 5 项全 PASS**

| 指标 | 实测值 | 判定 |
|---|---|---|
| A1 指示灯位置（440 prep/run） | `led=[394.50, 401.50]`，`panel.right=412.00` → 内缩 `10.50px`；`led.left=394.50 ≥ hole.right=384.00` | PASS |
| A2 卡槽左右对称（3 视口 × 2 态） | `symDiff=0.0px`（左 28.0 / 右 28.0）；`holeR − batR = 0.0px` | PASS |
| A3 读数靠中（440） | prep `#digits` 中心 `215.70px` vs 面板中心 `220.00px`（差 `-4.30px`）；run `00:00` 与封面净距 `25.09px` | PASS |
| A4 喇叭孔 vs 按钮（440） | 净距 `38.00px`，重叠 `0.0px²` | PASS |
| A5 露出比例（run） | 440 `19.8%` / 744 `20.1%` / 1133 `20.0%` | PASS |

另测：`localStorage` 带 `vp=440` 刷新后 `innerScrollDiff=0px`（15px 滚动条根因已除）；动画中卡片下缘 `bleed ≤ -0.23px`（回弹不穿帮）。

**B. 遗留问题（本轮不修，等 dad 拍板）**

- **[P1] 外层演练控制栏窄窗溢出**：`#czPresets`（4 组长文本预设按钮，总宽约 `654px`，`white-space: nowrap`）在浏览器宽度 `541–660px` 区间导致外层出现横向滚动条（`scrollWidth=668px > clientWidth`）。**只影响 demo 调试控制栏，内部画布不溢出**。复现截图 `/private/tmp/verify-overflow-541px.png`。建议修法：`@media (max-width: 668px) { .cz-bar / .cz-seg { flex-wrap: wrap; } }` 或收敛预设文案长度。
- **[P2] `.panel-foot` 父容器盒跨旋钮（误报）**：1133 下父容器盒覆盖中央旋钮，但实际文字子元素在旋钮两侧（今日 `73.8–129.4px`、BPM `343.0–424.6px`，旋钮 `172.0–300.0px`），视觉零重叠；自动化脚本改探叶子节点即可。
