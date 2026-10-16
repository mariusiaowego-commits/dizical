# brief-grok-261013 · 等高卡片网格 + 组合树落地（owner: grok / w31:p7）

你现在是本项目**前端主力**。目标文件：`docs/demos/practice-right-column-261003/canvas-01.html`（**本轮只有你改这个文件**）。

## dad 的原始反馈（2026-10-13，逐字）
> 如截图，高度还是不对，你看左边票卡高度 360*1024，右侧 `cz-fill` 里面的 dash 也就是仪表盘的高度不是 1024，
> 这样就导致看上去不是一样高了。**我的理解左侧票夹也是一个"卡片"，那么右侧仪表盘等卡片就是大家一样高度的。**

## 我（hermes）上台实测的现状（09:24 那版 · 1133 档 · 窗口宽度 1133）
```
画布 iframe 1133×593 · 画布文档 scrollHeight 593（仍与 iframe 高度相等 → 高度回环没根治）
左栏票卡 .pk-ticket   360×559  （computed min-height: 520px · flex 1 1 auto）
模块（全部 t=32，也就是仍在一行平铺，不是组合树；且 6 个全部可见，而 state.mods 只有 [A,S]）：
   A 472×559   ← 高度已等于票卡 559 ✓（唯一对的）
   B 432×620   ← 超出票卡高（底边 652 > 票卡底 591）
   S 172×480
   D 392×313
   R 158×38
   Q 452×606   ← 超出票卡高（底边 638 > 591）
.czd-fill：这版里已经查不到 .cz-fill 元素（dad 截图里那个是 09:19 版）
```

## 本轮要做（按 dad 的话就是一条硬规则 + 三条落地）
1. **等高硬规则**：右栏每一张卡片（仪表盘 A / 节拍器 B / 竖条 S / 今日时长 D / 记录小卡 R / 老师要求 Q）
   **都必须与左栏票卡等高**（视觉上"大家一样高"）。
   做法由 agy 的 `spec-agy-equalheight-261013.md` 定（等高分配：谁是顶格通高、谁在行内分高、超出部分内部滚动）；
   agy 产出前先按"全部 = 票卡高 H"实现，H 取**该视口档下画布的自然高度**（1133 档实测 559；744/440 档各量一次）。
2. **禁止高度回环**：iframe 高度**不得**由画布 `scrollHeight` 反推；模块高度也不得回灌 iframe 高度。
   断言：① combo=off 时 ticket.h == 该档自然高；② 挂满模块后 ticket.h 不变（±1px）；
   ③ `iframe.clientHeight` 与画布 `scrollHeight` 不再恒等（防回环）。
3. **组合树落地**（不是一行平铺）：按 `参考图文字基线-261012.md` 的 image23 / image24：
   ```
   组合1 = 中轴列（上：仪表盘【高 = 票卡高】；下：今日时长卡 + 记录小卡 并排卧底）| 最右：竖条节拍器【通高】
   组合2 = 一行并排 票卡 | 仪表盘 | 竖条节拍器（文字竖排）| 今日练习卡；等高顶底对齐；最右为一屏右界，超界靠右滑
   组合3 = 仪表盘 | 复合列（节拍器上 / 今日时长卡下）| 今日记录；按 spec-agy-combos §4
   断言：给出每块 rect(l/t/w/h) + 与票卡的顶差/高差；组合2 另给一屏右界 X 与超出量
   ```
4. **可见性/实例**：一个组合里每个模块只 1 个实例；只渲染勾选的模块（`state.mods` 与实际可见集合必须一致）。
   断言：`visibleMods.map(m=>m.dataset.mod)` == `state.mods`（顺序可不同）；`.cz-mod` 总数 == 定义数（无残留、无第二排游离）。

## 保持不动的（别回退）
- 弹窗遮罩实测是对的：`#pkFolioModal.open` → `position: fixed` / `z-index: 100` / `background rgba(44,62,80,0.45)` / 铺满画布 / `elementFromPoint` 命中的是它自己。
- 卡槽：按 `spec-agy-slot-261012.md §7` 实装 `.cz-punch-slot`（静态拟物、无 `.cz-mini`/`.cz-slot` 框、与仪表盘顶边 6~8px 接缝、**无插入动画**）。
- 联动：`DizicalPracticeBus` 已在画布里，但 `window.__cz.bus` 为空、我点左栏「减速」值没变 → 源画布那两个按钮挂的是 `attachLongPressStepper`（长按步进），监听要跟它同一条代码路径；正/反向各贴前后值 + 负控必须报红。

## 红线
只碰 `canvas-01.html`（+ 你自己新写的 spec/说明）；**画布源文件零改动**（`docs/demos/practice-ticket-v4-260920.html`，sha256 `e86d4bc56163218d`）；
不 commit、不 push、不加依赖；配色只走 `--dash-*` 与画布自带 token；
**汇报必须"价签式"：每条给实测数 + verdict 原文**；自检绿不算数，要在普通浏览器会话里也绿（我会上台复算）。

## 验收（我上台会量这些数）
```
ticket.h == H(档) ；所有可见模块 h == H（±1px）且 t 与票卡 t 对齐或明确在下方行内
visibleMods == state.mods ；.cz-mod 总数 == 定义数
iframe.clientHeight != 画布 scrollHeight（不再恒等）
组合1/2 的树结构 rect 与 image23/24 基线一致（逐块 l/t/w/h）
.cz-punch-slot 存在且无动画（runInsert/FALLBACK_MS 计数 0）
联动：左→右、右→左各一组前后值
```
