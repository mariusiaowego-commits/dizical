---
source: ai-agent
project: dizical
sprint: demo-v3.7-S17-S18
date: 2026-10-26
---

# demo v3.7 · S17 + S18 轮验收记录（2026-10-26）

分支 `feat/practice-ui-iter-260920`（起点 HEAD `f330bac` = tag `demo-v3.5`；本轮改动已 commit，**未开 PR / 未 merge**）。
服务：`http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html`（PID 97410）。

## dad 批注 → 修复

1. **槽孔被改没了，只剩一块黑屏**（x22.2% y15.6%）
   - 根因：S16 把整个槽体填成全宽黑金属块，卡槽从「孔」退化成「挡板」。
   - 修：槽体改回透明，只在底缘画一条比黑区窄的缝。`#pkPunchSlotWrap[data-hole="1"]::before`（z46，下半孔，`bottom:0`，高 = 孔高/2，左右 `--pk-hole-inset` 28px）+ `::after`（z42，上半孔，垫在卡后）；下半孔加 `inset 0 1px 0 rgba(255,255,255,.16)` 顶边高光做「沉进去」的边缘感。
   - 实测：横排孔宽 380 / 350 < 黑区 416 / 386；卡宽 < 孔宽；孔所有状态常驻。

2. **dashboard 黑色区域头部元素被遮盖**（x46.2% y15.8%）
   - 根因 A：`updateCardSlotGeometry()` 里 `cardInset` 在声明前使用 → `cardW=NaN` → 卡片宽度失效。
   - 根因 B：面板让位用了「露出高度」`exposedH` 而不是槽体总高 → MIC 被上压 12px。
   - 修：几何输入全部提到函数顶部先算；`--cz-panel-pt = slotFullH + slotSafeGap`。
   - 实测：mic.t 149–152 ≥ 槽底 +8（9 组合全 PASS）。

3. **今日 42分 / BPM 60 位置还是太上面**（x23.7% y49.9%）
   - 修：`.panel-foot` 三处（卡内 `.grid-3col` / canvas `cz-fill` / `cz-feed`）统一 `position:absolute; top: var(--cz-foot-top); bottom:auto`；`layoutArc()` 按圆点弧顶边实时写 `--cz-foot-top = dotTop - pr.top - 10`。视口黑区高度变化时状态行自动跟到拱肩。
   - 实测：今日中心与弧顶差 ≤2px；与可见刻度墨迹重叠 0.0px²。

4. **仪表盘标题与票夹不联动**
   - 修：新增 `syncDashCover()`（canvas 顶层文档查 `.cz-mod[data-mod="A"] > iframe` → iframe 内 `#dashCoverName`），挂 `syncRunMeta()`（变更时）+ `syncAll()`（重建/初始时）。
   - 实测：dash="吸气长音" == 票夹"吸气长音"（54 组合态全 PASS）。

## 门禁

- `node tools/verify.js --strict` → 9 组合 × 11 项核心指标全 PASS（exit 0）
- `python3 tools/sync-demo-templates.py --check` → 6 模板字节级一致
- `python3 tools/check-layout-modes.py` → CSS `[data-vp]` 选择器 = 0
- 自写量化探针 `/private/tmp/check-s18.js` → 3 视口 × 3 组合 × 2 态 = **54 项断言全 PASS**（槽孔存在且窄于黑区 / 头部不遮盖 / 今日落拱肩 / 不压刻度 / 标题联动）

## 截图

- A 卡整卡：`/private/tmp/s19/panel-{1133,744,440}-{prep,run}.png`（6 张）
- 全页：`/private/tmp/s19/vp{1133,744,440}-c{1,2,3}-{prep,run}.png`（18 张）

## 事故与恢复（必读）

- 我误用 `apply_patch` 的 `Move to:`（同路径）删除了**未提交**的 `canvas-01.html`。
- 恢复：从 `~/.codex/sessions/2026/10/{21..26}/*.jsonl` 提取 114 个原始 patch，脚本重放 42 个重建（`/private/tmp/canvas-recover/`）；`cards/*.html` 权威源当时完好，sync 后补齐 A 卡 CSS/HTML。
- 判定无损的依据：sync --check 字节级一致 + verify 11 项全绿 + 54 项探针全 PASS。
- 教训：未提交的大文件没有 git 兜底，动 demo 主体前先 `cp` 备份到 /private/tmp。

## 追加：S18 轮（2026-10-26 晚，dad 6 条批注）

dad 明确口径：**MIC 与电池对齐「卡槽孔边缘」，不是插入卡片边缘**。

1. **插卡减速+回弹时下缘穿帮**（x81.1% y13.3%）
   - 修：`canvas-01.html:2261-2301` `pkCardToSlot` / `pkCardToSlotFeed` 全程 `translateY ≤ 0`（72% 归座 0px → 85% 回弹 −2px → 100% 落定 0px）。
   - 实测：1133 C1 prep→run 逐帧 152 帧采样，卡底越过孔底最大 `0.00px`；回弹期卡底留在下半孔（z46，高 9px）遮罩内 `7.00px`。

2. **MIC 与卡槽左缘对齐**（x24.8% y17.2%）
   - 修：`cards/card-a-dashboard.html:274` + `canvas-01.html:7029` `.status` 改 `padding: 0 var(--cz-status-pad-x, 16px)`。
   - 实测 1133 C1/C2/C3 两态：`micLeftFromPanel = holeLeftFromPanel = 28.0px`（误差 `0.0px`）。

3. **时间数字与左侧封面图上下居中**（x59.1% y23%）
   - 修：`cards/card-a-dashboard.html:1310` + `canvas-01.html:8065` 新增 `alignReadoutWithCover()`，写 `--cz-readout-dx/dy`。
   - 实测 1133/744/440 两态：`digitsCoverCyDiff = 0.0px`；水平落在封面右缘与右侧安全边界中点偏左 6px（实测 −4.0px）。

4. **电池与卡槽右缘对齐**（x87.1% y16.7%）
   - 实测：`batRightFromPanel = holeRightFromPanel = 28.0px`（误差 `0.0px`）。

5. **「今日 xx分」下移贴近黑区下缘**（x29.7% y46.7%）
   - 修：`cards/card-a-dashboard.html:1439` + `canvas-01.html:8194` `--cz-foot-top = panel 高 − 20px`（不再由圆点弧顶牵制）。
   - 实测：「今日 xx分」距底 `4.0px`。

6. **「BPM xx」下移贴近黑区下缘**（x77.6% y46.9%）
   - 实测：「BPM xx」距底 `0–2px`。

附带修：卡槽指示灯 `.cz-slot-led` 准备态/计时态同位（`canvas-01.html:17086`、`:17494`），feed 流无孔肩则隐藏；feed 槽右侧溢出 24px 修掉（`crownInset` 统一 12px，`canvas-01.html:17316`）；440 档旋钮 176→136px。

## 门禁（盖章后复跑）

- `node tools/verify.js --strict` → 9 组合 × 11 项核心指标全 PASS（exit 0）
- `python3 tools/sync-demo-templates.py --check` → 6 模板字节级一致
- `python3 tools/check-layout-modes.py` → CSS `[data-vp]` 选择器 = 0
- 单卡 `cards/card-a-dashboard.html?audit=1` 的 16 条 fail 与改动前备份**逐条一致**（过时断言，非本轮引入；不许改测试掩盖）

## 版本与提交

- 页面版本已盖章 **demo v3.7（2026-10-26）**：`tools/stamp-demo-version.py` 改 `DEMO_VERSION/DEMO_DATE` + 补 6 张 `cards/` 权威源进 TABLE，跑完自动改 24 页徽章 + 重写 `VERSIONS.md`（含 v3.7 轮次条目）。
- 本轮全部改动已 commit 到 `feat/practice-ui-iter-260920`（**未开 PR / 未 merge / 未 push / 未打 tag**，按 dad 指示只做版本锚点）。
- 交接记录：`demo-v3.7-交接记录-261026.md`（Obsidian 镜像 `PRDs/handoff-2026-10-26-demo-v37-s18.md`）。
