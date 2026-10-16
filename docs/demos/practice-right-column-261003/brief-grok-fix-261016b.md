# brief-grok-fix-261016b · 第二轮（照 pixel 走查 + agy 规格 修）

你 10:43 那版我上台复核：744/440 档卡高出现"一刀切"（两次交互状态分别量到 708×150 与 708×520，六卡同值）
⇒ 不是内容驱动，是又换了个写死值。dad 要的是**内容撑开**（见 agy spec §1.2）。

## 必读（都在 docs/demos/practice-right-column-261003/）
```
audit-pixel-261016.md          三档走查逐块 rect + 判据（pixel 真会话 headed 量的）
spec-agy-feed744-261016.md     feed 档高度总规则 + 逐卡目标高（744/440）
spec-agy-eh-combo1-261016.md   组合1 宽扁比例下 A 卡内部重排
spec-agy-slot-size-261016.md   卡槽尺寸/内嵌（现在只有 18px 高）
spec-agy-s-hbar-261016.md      S 竖条 → 744/440 横条
spec-agy-combo1-d-r-261016.md  组合1 里 D/R 元素取舍 + R 底色与 D 统一
```

## A · 先修 pixel 量的 P0（dad 痛感最高）
```
P0-1  1133 组合1 · A 卡：旋钮 #knob 130.5 比所在行 #mid 102.3 高 28.2px
      → 盖住「开始/提前结束」按钮顶 10.4px（相交 499.5 / 790.9 px²）；#knobRotor 压进黑区 23.9px
      判据：J3 同行元素相交 = 0；旋钮底 ≤ 所在行底
P0-2  1133 组合1 · A 卡：黑区 #panel 内部裁 54px（.cover-col 越出 18.1px、.cover-name 0×0 消失）、#mid 裁 55px
      判据：卡内所有块 clientHeight == scrollHeight（J1/J2/J6）
P0-3  744/440 · R 卡：卡内纵向滚动条（#scroller 内容 498/569 vs 可见 431/400 ⇒ 缺 67/169px）
      判据：卡内 overflowY 不得 auto/scroll；clientHeight == scrollHeight；高度随记录条数单调（agy §4.3）
```

## B · 再修 P1
```
P1-1  1133 组合1/组合3 · #arc 点环拟合圆心比旋钮圆心左偏 26.8 / 25.4px（744/440 差 0）；9 个点落在旋钮面上
      判据：点环圆心 == 旋钮圆心（|Δx| ≤ 1）
P1-2  744/440 · 卡高被票卡高钉死：D 卡 63%/62% 空白、S 卡是横盒但内部仍 top/mid/bot 竖排（#bpmFace 仅 64×43）
      判据：按 agy spec §2/§3 —— h(S) ≤ 120px（真横条）、h(D) ≤ 280px、六卡高度不得全部相同
P1-3  1133 · A 卡读数行右偏（#readout cx 比面板中轴 +55px / #ttCounter +41.8px）
      判据：按 spec-agy-eh-combo1 给的口径对齐
```

## C · 收 P2
```
P2-1  黑区缺口圆心 y 写死 242.5px → 组合1 缺口整块落在面板外（看不到弧）、组合3 咬进 47.4px（规格 --notch-depth 24px）
      判据：咬进深度 == --notch-depth；圆心 x == 面板中轴（已成立）
P2-2  组合1 · #readoutUnit「分钟」与 #bpmRead 重叠 336px²
P2-3  440 档 B 卡 #psAssignRow 卡内横滚 +205px；440 档 A 卡 #mid 裁 5px
P2-4  744/440 视觉序 = A→D→R→B→S→Q（窄档 CSS order）与勾选序 A,B,S,D,R,Q 不一致
      → 请按 agy feed 规格的 Order 1..6 重排（票卡 → A → S → D → R → Q）
```

## D · 另外三条（dad 原文）
```
D-1 item 5：卡片下的"淡色底层"—— `#pkRecordsDrawer` 已隐藏（我量到 display:none ✓），继续确认三档卡片下方/右侧 60px 内无非透明底层
D-2 item 3/4：记录弹窗明细已存在（#czPopFrame 里有 科目/总时长/速度/单次/明细/占比 表）
      → 请你给 744/440 档的弹窗尺寸/密度适配（窄档近全屏 + 表格可横滚），并把证据贴出来
D-3 组合3 挂载：pixel 走查时只挂到 A/B/D（R 未挂载），我这边量到 A/B/D/R 都在
      → 请你确认真实挂载逻辑，给"组合3 = A/B/D/R"的 DOM 证据（避免复现时又对不上）
```

## 红线 / 汇报
只改 canvas-01.html；画布本体零改动（sha256 e86d4bc56163218d）；不 commit / 不 push / 不加依赖。
汇报：A/B/C/D 每组逐条给"真会话实测数（before → after）+ verdict"；负控 `?negctl=bus` 跑一次（必须红 + 带数值）。
另外：**改成内容驱动后，请给六卡高度的"异构性"证据**（h(S) ≤ 120 / h(D) ≤ 280 / 六值不全等），这是 dad 7.2-7.4 的验收点。
