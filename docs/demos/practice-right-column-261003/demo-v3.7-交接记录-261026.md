---
source: ai-agent
date: "2026-10-26"
doc_type:
  - handoff
tags: [dizical, practice, demo-v3.7, handoff, s17, s18]
project:
  - dizical
is_done: false
---

# HANDOFF · dizical practice 右栏 demo v3.7（写于 2026-10-26）

    写入人   codex（herdr workspace w45 · pane w45:p1 之外的本线程）
    工作目录 /Users/mt16/dev/dizical · 分支 feat/practice-ui-iter-260920
    demo 服务 http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html（PID 97410）

---

## 1 · 现在到哪了

```
demo 版本   v3.7（2026-10-26 盖章，24 页徽章 + VERSIONS.md 已重写）
本轮范围     S17 卡槽窄孔化（agy 交付 + 我复核修尾）+ S18 边缘对齐 6 条（dad 261026 批注）
commit      本轮全部改动已 commit 到 feat/practice-ui-iter-260920（未开 PR / 未 merge / 未 push / 未打 tag）
门禁         verify.js --strict 11/11 PASS · sync-demo-templates --check 6 模板字节级一致 · CSS [data-vp] 0 处
待办         只剩 dad 肉眼验收（见 §4）
```

## 2 · 本轮改了什么（附 path:line + 实测值）

### 2.1 卡槽窄孔化（S17）
- `canvas-01.html:17078-17079`：`#pkPunchSlotWrap[data-hole="1"]::before`（z46，下半孔，bottom 0）与 `::after`（z42，上半孔）夹住卡片 → 卡片从窄孔中穿过；孔左右各留 28px 肩（`--pk-hole-inset`），卡比孔再窄 8px。
- `canvas-01.html:17305-17437` `updateCardSlotGeometry()`：`holeInset / cardInset / cardW` 全部提到函数顶部先算（此前 `cardInset` 先用后声明 → `cardW=NaN`）；`--cz-panel-pt = slotFullH + slotSafeGap`（此前按露出高度让位 → 压住 MIC）。
- `canvas-01.html:17086-17087` + `17494-17499`：`.cz-slot-led` 准备态/计时态同一孔肩位置；feed 流（`data-hole="0"`）无孔肩 → 隐藏。

### 2.2 插卡动画不穿帮（S18 批注 1）
- `canvas-01.html:2261-2301`：`pkCardToSlot` / `pkCardToSlotFeed` 全程 `translateY ≤ 0`（72% 归座 0px → 85% 回弹 −2px → 100% 落定 0px），卡底不再从下半孔下方露出。
- 实测（1133 C1，prep→run，152 帧逐帧采样）：越过孔底最大 `0.00px`；回弹期卡底留在下半孔遮罩内 `7.00px`。

### 2.3 MIC / 电池对齐卡槽孔缘（S18 批注 2、4 —— dad 明确「对齐卡槽孔边缘，不是插入卡片边缘」）
- `cards/card-a-dashboard.html:274` + `canvas-01.html:7029`：`.status` 改 `padding: 0 var(--cz-status-pad-x, 16px)`。
- 实测 1133 C1/C2/C3 × 准备态/计时态：`micLeftFromPanel = holeLeftFromPanel = 28.0px`、`batRightFromPanel = holeRightFromPanel = 28.0px`（误差 `0.0px`）。

### 2.4 读数与封面图上下居中（S18 批注 3）
- `cards/card-a-dashboard.html:1310-1329` + `canvas-01.html:8065`：新增 `alignReadoutWithCover()`，写 `--cz-readout-dx/dy`（纵向锁封面中心；水平取封面右缘↔右侧安全边界中点再左移 6px）。
- 实测 1133/744/440 两态：`digitsCoverCyDiff = 0.0px`；水平较可用区中点偏左 `−4.0px`。

### 2.5 页脚贴黑区下缘（S18 批注 5、6）
- `cards/card-a-dashboard.html:1439` + `canvas-01.html:8194`：`--cz-foot-top = panel 高 − 20px`（不再由圆点弧顶牵制）。
- 实测 1133/744/440 两态：「今日 xx分」距底 `4.0px`、「BPM xx」距底 `0–2px`。

### 2.6 feed 流修边
- `canvas-01.html:17316-17317`：`crownInset` 统一 12px（此前 feed 槽/卡右侧溢出 24px）；440 档旋钮 176→136px；feed 面板 `padding-bottom: 64px` + `justify-content: flex-start`。

## 3 · 门禁证据（提交前跑过）

```
node docs/demos/practice-right-column-261003/tools/verify.js --strict        → 11/11 PASS（3 视口 × 3 组合）
python3 docs/demos/practice-right-column-261003/tools/sync-demo-templates.py --check → 6 模板字节级一致
python3 docs/demos/practice-right-column-261003/tools/check-layout-modes.py → CSS [data-vp] 0 处
git diff --check                                                             → 无空白错误
```

已知的**非本轮引入**的遗留断言（`cards/card-a-dashboard.html?audit=1` 单卡独立预览 16 条 fail，与改动前备份逐条一致）：
`--notch-r/depth` 期望值过时 · ruler→arch 净距 · 读数 Hero 高度期望 60px（实际 54px）· A4 cover 同轴期望 1px（实际 15.6px）· 气泡动画 headless 无音频 · diag-card 框数断言过时。
**红线**：这些断言不许为了让报告变绿而改测试。

## 4 · 还需要 dad 拍板 / 验收的事

```
P0  ① 肉眼验收 S18 全部 6 条（MIC/电池对孔缘、读数与封面居中、页脚贴下缘、插卡回弹不露下缘、指示灯同位、feed 槽不溢出）
P0  ② 若上面还有不满意的点：给截图 + 坐标批注，我按批注继续改（同款流程：改 → Playwright 实测 → 出新截图）
P1  ③ 是否开 PR / merge / 打 tag（当前按 dad 指示「先 commit，不开 PR 不 merge」）
P2  ④ 「右栏并进生产模板 src/kid_app/templates/practice.html」是否提上日程（拍板 A3：先 demo 后移植）
```

## 5 · 红线与注意事项

- **右栏 6 张卡只改 `cards/` 目录下的权威源**（`cards/card-*.html`），改完必须跑 `python3 tools/sync-demo-templates.py` 同步进 `canvas-01.html`；**严禁直接改 `canvas-01.html` 的 `<template>` 内联块**。
- CSS 里**禁止出现 `[data-vp]` 选择器**（视口差异一律走 `html.cz-expand` / `html.cz-feed` / `html.cz-fill` 等类），`check-layout-modes.py` 门禁会拦。
- 画布源 `practice-ticket-v4-260920.html`（srcdoc 搬入）**全程零改动**。
- 探针脚本一律放 `/private/tmp`，不进仓库。
- 版本号只在 `tools/stamp-demo-version.py` 里改 `DEMO_VERSION / DEMO_DATE`，然后跑该脚本（自动改 24 页徽章 + 重写 `VERSIONS.md`），**再跑一次 `sync-demo-templates.py`**（卡片徽章会变）。
