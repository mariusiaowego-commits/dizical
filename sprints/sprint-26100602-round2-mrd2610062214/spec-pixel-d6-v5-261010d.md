---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# spec-pixel-d6-v5-261010d · D6 微调（落地）+ 744 布局对照卡（新建）

    owner        pixel
    上游         plan-261010d.md §D6-1 ｜ brief-pixel-d6-v5-261010d.md
    日期         2026-10-10
    口径         只碰 docs/demos/ · 不加依赖 · 不 commit / 不 push · 色值只走 --dash-*
    门禁         verify-demos.py OK · token-contrast.py 不合格 0 · --dash-* 名集合 70 个 0 差异

---

## 0 一句话结论

D6 两行（刻度行 / 时长行）已按 dad 要求贴近 dash 并换细体：**可见净距 9.57 → 5.07 / 7.33 → 4.86 px**，字重 800 → 400，不压线不裁切，三档 × 两皮肤全绿，负控 4 条红。

744 布局另交一张独立对照卡 `metronome-01-v5.html`（49,264 B / 1,150 行），按 dad 同一份规格做 pixel 自己的解读：中枢栏 `1fr auto 1fr` 贯通卡顶、双栏 `42fr : 58fr`（实测 42.00 / 58.00）、步进键到旋钮 18px、到主按钮 29.55px、4 粒灯单行 y 极差 0、灯组偏心 0.02px、药丸 h32、音色下啦与主按钮等高 50、命中区实测 46×46 / 60×46。**13 条断言 × 6 组合全绿，负控 84 条红。**

---

## 1 任务 1 · D6-1 落地（改 `practice-duration-card-01-v3.html`）

### 1.1 改了什么（两处 CSS + 一处自检）

    .time-ticks-row     bottom: calc(50% + 8px)  →  calc(50% + 3.5px)
                        font-weight: 800          →  400
    .rail-duration-row  top:    calc(50% + 8px)  →  calc(50% + 5.5px)
                        font-weight: 800          →  400
    字号                9px 保持不变（brief 允许 8.5～9；9px 是两行唯一可读下限，故不降）
    自检                B3 段重写（见 1.3），并把改前基线值写进审计输出 d61Before

### 1.2 为什么两行给的偏移量不一样（3.5 / 5.5），却都叫「净距 5px」

这两行的「8px」是 CSS 盒偏移，不是眼睛看到的距离。眼睛看到的是**字墨迹到 dash 可见笔画**的距离，而两行字形内容不同：

    canvas 真实字体度量（SF Mono / ui-monospace，9px，line-height 1）
      刻度行 "07:15"（纯数字）  墨迹底 = 行盒底 − 2.37px   （数字只有 cap 高，下方留空）
      时长行 "42 分钟"（含 CJK）墨迹顶 = 行盒顶 + 0.13px   （汉字撑满字身）
    dash 可见笔画               线在 viewBox y=2、stroke-width 1.6 → 笔画占 1.2..2.8（非缩放描边）

要让两行**看起来**都是 5px，盒偏移必须不同：刻度行 3.5px、时长行 5.5px。若两行都写 5.5px，刻度行的可见净距会变成 7.1px（还是「远」），若都写 3.5px，时长行只剩 2.8px（压线）。故按字形分别对齐，并在自检里断言**可见净距**而不是 CSS 值。

### 1.3 自检断言怎么量的（关键：不用行盒当墨迹）

    inkMetrics(el) = canvas.measureText 取 actualBoundingBoxAscent/Descent + fontBoundingBox*
                     → 基线 = 行盒顶 + (lineHeight − (fbAsc+fbDesc))/2 + fbAsc
                     → 墨迹上下沿 = 基线 ∓ actualBoundingBox*
    净距          = dash 可见笔画边 − 墨迹边
    断言          B3：两行净距 ∈ [4,6] px ｜ 字重 = 400 ｜ 字号 ∈ [8.5,9] px
                  不压线：行盒到线盒间隙 ≥ 1px ｜ 不裁切：scrollWidth ≤ clientWidth+1

**为什么不用 `getClientRects()`**：它给的是行盒（含字身上下空白），刻度行会把净距报成 7.00、时长行 5.00 —— 数字「看着合格」，但和眼睛看到的（11 / 8）差 3px；换细体后更会误判。用 canvas 字体度量拿到的是真墨迹，且**随实际字体自适应**（dad 机器上字体变化也会自动反映到数字里）。

### 1.4 实测（三档视口 × 两皮肤）

    ┌──────────┬──────────┬──────────┬────────┬────────┬────────┬────────┐
    │ 视口宽   │ 皮肤     │ 刻度净距 │ 时长净距│ 字重×2 │ 刻度盒隙│ 时长盒隙│
    ├──────────┼──────────┼──────────┼────────┼────────┼────────┼────────┤
    │ 480      │ 浅白     │ 5.07     │ 4.86   │ 400    │ 1.50   │ 3.50   │
    │ 480      │ 深墨     │ 5.07     │ 4.86   │ 400    │ 1.50   │ 3.50   │
    │ 380      │ 浅白     │ 5.07     │ 4.86   │ 400    │ 1.50   │ 3.50   │
    │ 380      │ 深墨     │ 5.07     │ 4.86   │ 400    │ 1.50   │ 3.50   │
    │ 340      │ 浅白     │ 5.07     │ 4.86   │ 400    │ 1.50   │ 3.50   │
    │ 340      │ 深墨     │ 5.07     │ 4.86   │ 400    │ 1.50   │ 3.50   │
    └──────────┴──────────┴──────────┴────────┴────────┴────────┴────────┘
    裁切 0/0 · 字/胶囊底对比 5.99:1（深墨）/ 5.01:1（浅白）
    六格数值完全一致：rail 几何与字体度量与卡宽、皮肤无关（皮肤只换色，不动尺寸）

**改前 vs 改后**

    刻度行   CSS 偏移 8px → 3.5px   墨迹净距 9.57 → 5.07 px   字重 800 → 400
    时长行   CSS 偏移 8px → 5.5px   墨迹净距 7.33 → 4.86 px   字重 800 → 400
    盒间隙   6.00 → 1.50 / 3.50 px（都 ≥1，不压线）

**像素级交叉验证**（headless 截图逐行扫描，只作为量法互证，不作判定）：

    线笔画占第 294–295 行
    刻度墨迹行 277..283（改前）→ 281..287（改后）   可见净距 11 → 7
    时长墨迹行 303..310（改前）→ 300..307（改后）   可见净距 8  → 5
    阈值法把细字（400）的淡边像素漏掉，系统性偏大 ≈2px；canvas 度量法（1.3）才是判定口径

### 1.5 负控（改回旧值必须红）

    第 1 遍 注入副本（.time-ticks-row / .rail-duration-row 回到 8px + 800）
            → ASSERT_FAIL，4 条红：
              B3 fail: 刻度行墨迹净距 want 4..6px got 9.57px
              B3 fail: 时长行墨迹净距 want 4..6px got 7.33px
              B3 fail: 刻度行字重 want 400 got 800
              B3 fail: 时长行字重 want 400 got 800
    第 2 遍 原值 → ASSERT_OK（failures []）
    第 3 遍 原值 → ASSERT_OK（failures []）

    注：负控红出的 9.57 / 7.33 与审计输出里的 d61Before 完全一致 —— 说明「改前基线」不是手抄的，是同一套量法当场量出来的。

---

## 2 任务 2 · `metronome-01-v5.html`（744 布局 · pixel 独立解读版）

### 2.1 交付物是什么

一张**独立对照卡**：同一份 dad 规格，pixel 的实现版本，供 dad 与 agy 在 `metronome-01-v3.html` 的主实现二选一。
打开即 744 档（`data-vp="pad"`），顶栏可切 1133 / 440、浅白 / 深墨、跑动演示；页内常驻「量值面板」把本节所有数字实时打出来；`?audit=1` 出完整断言结果。

不引 gsap（本卡动效全走 CSS transition），自带 `prefers-reduced-motion` 降级；不读任何外部文件。

### 2.2 三层结构规格（数值即实现值）

**① 顶层中枢栏（贯通卡顶，底部 1px 分割线）**

    容器        display:grid; grid-template-columns: 1fr auto 1fr; align-items:center
                grid-column: 1 / -1（贯通双栏）; padding 2px 0 10px
                border-bottom: 1px solid var(--dash-ink-a12)
    左 · 节拍号  h30（padding 5px 10px · r8 · 12px/700 · bg --dash-surface-soft · 1px --dash-shell-inset）
    中 · 4 粒灯  单行 flex · gap 14 · 灯 17×17 · 编号 10px/650
                第 1 拍 = --dash-coral + 3px --dash-coral-a25 光晕；2/3/4 = --dash-shell-lo + 1px --dash-ink-a16
                跑动时当前拍 → --dash-accent + --dash-accent-glow 光晕；第 1 拍跑动 → 4px coral 光晕
    右 · 强弱拍  胶囊 h32 r9999（padding 0 12 · 12px/650）
                关：bg --dash-surface-soft + 1px --dash-ink-a12 + 字 --dash-text-soft
                开：bg --dash-coral-solid + 字 --dash-white（珊瑚实心，与「第 1 拍珊瑚高亮」语义同族）

  **为什么中列用 `auto` 而不是 `justify-self`**：写 `1fr auto 1fr` 时中列宽度=灯组内容宽、左右两列各占剩余一半 → 灯组中心天然等于卡中心（实测偏心 0.02px）。若写 `auto 1fr auto`（把 1fr 给中列），中列会被两侧不等宽内容挤偏 —— 负控实测偏 28.08px。

**② 左栏 · 旋钮 + 两侧 − / +**

    栏宽        42fr（744 档实测 285.6px）
    旋钮        160×160 盒；刻度环 60 格（每 5 格加长 2px）· 已走过部分 --dash-coral，未走 --dash-ink-a16/a25
                转子 inset 15px · radial-gradient(--dash-knob-hi → --dash-knob-lo)
                中心数字 font-size: var(--dash-num)=52px/800/--dash-mark + 单位 BPM 11px/750/--dash-coral
                拖动上下调速（4px / BPM），范围 40–208
    步进键      38×38 圆形 · bg --dash-white（深墨 --dash-surface-2）· 1px --dash-ink-a12
                单层微阴影 0 2px 6px --dash-shell-shadow · 17px 字
                命中区 46×46（::after inset −5px；实测射线 23.5/22.5/23.5/22.5）
    与旋钮净距  18px（flex gap；断言 ≥16）
    为什么不把旋钮做更大：160 + 38×2 + 18×2 = 272 ≤ 285.6，留 13.6px 余量；再大就会把「键不贴旋钮」的 16px 挤掉

**③ 右栏三层**

    L1 释义     13px/600/--dash-text（中文）+ 12px/650/--dash-text-soft（意大利语术语）
     L1 操作行  display:grid; grid-template-columns: 7fr 3fr; gap 10px
                开始：h50 r14 · bg --dash-coral-solid · 字 --dash-white 15px/800 · 图标 16px
                      单层投影 0 4px 12px --dash-coral-glow；hover 0 6px 16px；active scale(.98)
                      运行态：bg --dash-panel · 字 --dash-panel-text · 投影 0 2px 8px --dash-shell-shadow
                      文案 2 字「开始 / 暂停」+ aria-label「开始节拍器 / 暂停节拍器」+ aria-pressed
                音色：h50 r9999 胶囊（浅灰 --dash-surface-soft + 1px --dash-ink-a12，与主按钮等高）
                      内容「木鱼」13px/650 + caret 10px；展开时反白（bg --dash-text / 字 --dash-page）+ caret 转 180°
                      展开超时逐项 listbox（role=listbox / option + aria-selected），外点收起
    L2 组标题   12px/650 · 见 2.5（颜色有取舍）
    L2 卡片     grid repeat(auto-fill, minmax(130px, 1fr)) gap 8
                单卡 grid 1fr auto · 左「练习名」12px/650 --dash-text · 右「速度」11px/700 --dash-text-soft
                min-height 38 · r8 · bg --dash-surface-soft · 1px --dash-ink-a12
                长文本 white-space:normal + overflow-wrap:anywhere（**不截断**，改行）
                744 档 = 2 列 × 2 行（列宽 191.45px）；1133 档 = 3 列（166.7px）
    L3 药丸      h32 r9999 padding 0 14 · 12px/650
                闲：bg --dash-surface-soft + 1px --dash-ink-a12 + 字 --dash-text
                活：bg --dash-text + 字 --dash-page（浅白档=深底白字；深墨档随皮肤反白）
                命中区 46 高（::after 上下 −8px，左右不扩 → 相邻药丸不抢命中）

### 2.3 实测（三档 × 两皮肤，全部来自 `?audit=1` 的 `measurements`）

    ┌────────────┬──────┬──────┬──────┬────────┬────────┬────────┬────────┬──────────┬──────┬────────┐
    │ 组合       │ 卡宽 │ 左%  │ 右%  │ 灯y极差│ 灯偏心 │ 键-旋钮│ 键-主键│ 操作行比 │ 药丸 │ 最差对比│
    ├────────────┼──────┼──────┼──────┼────────┼────────┼────────┼────────┼──────────┼──────┼────────┤
    │ pad/浅白   │ 744  │ 42.00│ 58.00│ 0      │ 0.02   │ 18     │ 29.55  │ 68.2:29.2│ 32   │ 4.93   │
    │ pad/深墨   │ 744  │ 42.00│ 58.00│ 0      │ 0.02   │ 18     │ 29.55  │ 68.2:29.2│ 32   │ 4.93   │
    │ ipad/浅白  │ 960  │ 42.00│ 58.00│ 0      │ 0.02   │ 18     │ 74.91  │ 68.6:29.4│ 32   │ 4.93   │
    │ ipad/深墨  │ 960  │ 42.00│ 58.00│ 0      │ 0.02   │ 18     │ 74.91  │ 68.6:29.4│ 32   │ 4.93   │
    │ iphone/浅白│ 420  │ 单栏 │ 单栏 │ 0      │ 0      │ 18     │ 竖 44.0│ 68.2:29.2│ 32   │ 4.93   │
    │ iphone/深墨│ 420  │ 单栏 │ 单栏 │ 0      │ 0      │ 18     │ 竖 44.0│ 68.2:29.2│ 32   │ 4.93   │
    └────────────┴──────┴──────┴──────┴────────┴────────┴────────┴────────┴──────────┴──────┴────────┘
    命中区实测 步进键 46×46 · 药丸 60×46（六格相同）
    文字       32 个文本叶节点 × 6 格：裁切 0 · 越出卡外 0 · 药丸高全 32.00 · 组标题字号全 12
    定制练习   744/440 档 [2,2]（双列）· 1133 档 [3,1]（minmax(130px,1fr) 在 960 宽下自然出 3 列）
    色对比表   浅白最低 4.93（开始键 白字/--dash-coral-solid）· 深墨最低 4.93（同处）· 其余 5.66～15.92

### 2.4 断言清单（`?audit=1` → `verdict = ASSERT_OK`，`failures = []`）

    A0  744/1133 档双栏必须生效（容器查询命中）—— 防止布局塌了却静默跳过 A4/A7/A8
    A1  卡内所有文本：scrollWidth ≤ clientWidth+1（dad 指定）· 墨迹宽 ≤ clientWidth+1.2 · 越出卡外元素数 = 0
        （带命中区扩边的控件按扩边量豁免：Chrome 会把 ::after 的负 inset 计进 scrollWidth，38px 圆键量出 39）
    A2  4 粒灯 y 极差 = 0（单行）
    A3  灯组中心相对卡中心 ≤ 1px
    A4  双栏时「+ 键右沿 → 主按钮左沿」≥ 16px；单栏时「旋钮区底 → 主按钮顶」≥ 16px
    A5  步进键与旋钮外轮廓净距 ≥ 16px
    A6  步进键命中区实测 ≥ 44×44
    A7  左栏 = 42% ± 1
    A8  右栏 = 58% ± 1
    A9  音色胶囊高 = 主按钮高（±0.5）
    A10 四粒药丸高全部 = 32px（±0.5）
    A11 药丸命中区实测高 ≥ 44
    A12 组标题字号 = 12px
    A13 13 个探针元素的最低对比 ≥ 4.5（浅白 / 深墨各算一遍）

### 2.5 实现中发现的真问题（顺手修掉，附证据）

1. **容器查询不能作用于容器自身**。第一版把 `container-type` 挂在 `.metro-card` 上、再在 `@container` 里改 `.metro-card` 的 `display:grid` → 规则被浏览器忽略，744 档静默退回单栏（实测 `leftPct = null`、键到主按钮 −491px）。改成把容器挂在 `.stage-frame` 上、`@container mstage (min-width:620px)` 改卡 → 双栏生效。
2. **渐变底不能取「最暗色停」算对比度，也不能取元素自身**。旋钮数字的承接面是**兄弟节点**（.knob-rotor 的径向渐变），祖先链走不到 → 第一版量出 1.3:1 的假数。修法：把 `.knob-face` 放进 `.knob-rotor` 里（结构上数字本来就在转子上），并按元素中心在渐变线上的投影取**局部**色。
3. **卡身渐变偏暗区里的弱灰不够 AA**。卡身是 `shell-hi → shell-lo` 渐变，组标题落在偏暗段：`--dash-text-soft`(#666) 实测 **4.02:1**、`--dash-kicker`(0.72) **3.93:1**，都 < 4.5。→ 组标题改用 `--dash-text`（局部实测 5.7～8.3:1），层级交给字号/字重（12px/650 对正文 13px/600）。**这与 dad 原话「12px 弱灰组标题」有出入，请拍板**。同类位置：v3 的 `.ps-header` 也用 --dash-text-soft，落在同一段渐变上（本轮不改 v3，仅报数）。
4. **命中区读 CSS 值会漏判**。第一版用 `getComputedStyle(el,'::after').top` 反推命中区：`content:none` 把扩边干掉时 CSS 数值仍在 → 断言照样绿。改为从控件中心沿 4 条射线打点、直到 `elementFromPoint` 不再命中该控件，量**真实**扩边（负控实测 38×38 才报红）。
5. **换肤取色要先把过渡冻住**。`.audit-nofx` 必须在**换肤之前**加、在整个 6 组合循环期间**一直挂着**；若在 `measure()` 内部加/摘，下一次换肤又会启动新过渡，读到上一皮肤的中间值（深墨档会量出浅色的 #FFFDFB）。

### 2.6 与 agy 版（`metronome-01-v3.html` 的 pad 段）的差异（供 dad 二选一）

    ┌──────────┬───────────────────────────────┬───────────────────────────────┐
    │ 项       │ agy · v3（主实现）            │ pixel · v5（本卡）            │
    ├──────────┼───────────────────────────────┼───────────────────────────────┤
    │ 双栏写法 │ calc(0.42*(100% − 20px)) / …  │ 42fr / 58fr + column-gap 24px │
    │ 卡宽     │ max-width 720px               │ 744 档 744px · 1133 档 960px  │
    │ 中枢栏   │ flex + 左右绝对定位 + margin auto │ grid 1fr auto 1fr（中列天然居中）│
    │ 灯       │ 灯 + 长标签（第1拍/弱拍2/…）  │ 灯 + 编号（1/2/3/4），10px    │
    │ 旋钮区   │ 240 viewBox 刻度环            │ 160 盒 60 格刻度环（已走过珊瑚）│
    │ 操作行   │ 主按钮 70% + 音色 30%         │ grid 7fr 3fr（实测 68.2:29.2）│
    │ 音色入口 │ 胶囊（沿用 D2 轮结论）        │ 胶囊 + 真下拉 listbox         │
    │ 定制练习 │ flex space-between + min-width:0 │ grid 1fr auto + anywhere   │
    │ 分类标题 │ --dash-text-soft              │ --dash-text（AA 取舍，见 2.5-3）│
    │ 命中区   │ 未断言                        │ 实测射线法断言 46×46 / 60×46  │
    └──────────┴───────────────────────────────┴───────────────────────────────┘

### 2.7 负控（改回旧布局 / 旧值必须红）

    第 1 遍 组合故障（副本 .tmp-negctl-v5.html：退回单栏、灯错位、键贴旋钮、命中区去掉、
            药丸 26px、下拉 40px、长文本 nowrap、42:58 改 30:70、组标题 14px + 低对比灰）
            → ASSERT_FAIL，84 条红：A0×4 A1×2 A10×24 A11×6 A12×6 A13×6 A2×6 A3×6 A5×6 A6×6 A7×4 A8×4 A9×4
    单点 a4（只 .m-actions margin-left −70px）→ ASSERT_FAIL，A4×4（-40.45px < 16）
    单点 a1（只 .ma-label nowrap + 22px）    → ASSERT_FAIL，A1×6（4 个元素越出卡右沿）
    单点 a3（只 .m-top-hub 改 auto 1fr auto）→ ASSERT_FAIL，A3×6（偏心 28.08px）
    第 2 遍 原值 → ASSERT_OK（failures []）
    第 3 遍 原值 → ASSERT_OK（failures []）
    说明：组合故障里 A0 的「退回单栏」会遮住 A4/A7/A8，故另做三个单点故障，保证每条断言都有单独咬人的证据。

---

## 3 门禁与复现

    python3 scripts/verify-demos.py metronome-01-v5.html dashboard-skin-01-v3.html practice-duration-card-01-v3.html
      → OK ×3 · 非中性色字面量 0 · transition:all 0 · 括号差 0 · 未定义 token 无 · JS 过 node --check
      → 换肤契约：--dash-* 名集合一致（70 个，0 差异）
      → 旧文字色（--dash-ink/--dash-muted 当 color）0
    python3 scripts/token-contrast.py metronome-01-v5.html practice-duration-card-01-v3.html
      → 门禁不合格合计 0（两份文件、两皮肤各自 24～25 组全过）

    单页自检：浏览器打开 <file>?audit=1 → <pre id="audit"> 首行 ASSERT_OK / failures []
    D6 卡：practice-duration-card-01-v3.html?audit=1（六格 480/380/340 × 浅白/深墨 由页内脚本循环）
    v5 卡：metronome-01-v5.html?audit=1（六格 744/1133/440 × 浅白/深墨 由页内脚本循环）

---

## 4 待 dad 拍板 / 遗留

    待拍板
      1 744 布局选哪版：agy 的 v3 主实现 / 本卡 v5（差异表见 2.6）—— 若选 v5，我出实施清单交 hermes 落 v3
      2 组标题颜色：dad 原话「12px 弱灰」，但卡身渐变偏暗区里弱灰只有 3.93～4.02:1（<AA）
        → 本卡取 --dash-text（5.7～8.3:1）。要「弱灰」就要接受低于 AA，或改卡身渐变
      3 灯编号：本卡用 1/2/3/4（10px），v3 用「第1拍/弱拍2/次强3/弱拍4」——要不要保留长标签
      4 音色入口：沿用 D2 轮结论做胶囊 + 真下拉（本卡）／只做胶囊不做下拉（v3 现状）

    遗留问题
      · 节拍号只做静态 4/4；2/4、3/4 切换要连灯数一起变，本轮不做
      · 跑动演示用 setInterval(60000/BPM)，切后台不补偿漂移；正式接入要换 AudioContext 时钟
      · 药丸命中区上下各扩 8px；当前三档都是一行，若以后换行（行距 8px）会与邻行命中区相叠，需改回左右也扩的写法
      · 深墨档 `.knob-rotor` 仍是深色渐变（物理旋钮的隐喻），故数字用 --dash-mark 而非 --dash-text，皮肤间不翻转
      · 未做真键盘焦点样式（Tab 可见环）：本轮断言未覆盖，若要走 a11y 门禁需补 :focus-visible

    本轮未碰
      metronome-01-v3.html（agy 的）、metronome-01-v4.html、dashboard-skin-01-v3.html、src/ 全部未动
      未 commit / 未 push / 未加依赖
