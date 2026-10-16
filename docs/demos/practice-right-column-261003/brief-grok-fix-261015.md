# brief-grok-fix-261015 · canvas-01 修 7 条（owner: grok / 只改 canvas-01.html）

先读：`docs/demos/practice-right-column-261003/PLAN-demov33问题-261015.md`（我逐条实测的根因与数）
红线：画布本体零改动（sha256 `e86d4bc56163218d`）· 不 commit / 不 push / 不加依赖 · 只有你能改 canvas-01.html

## 你现在就能做的 7 条（证据都是我在真会话 1133 档量的）

### ① item 1.1 + 1.2 · 仪表盘内部重排 + 消灭卡内滚动条
```
现状：A 卡 iframe 396×441；卡内 body scrollHeight 467 > clientHeight 441（溢出 26px = 那条滚动条）
      #frame 高 429 固定在 y=32 → 32+429=461 > 441；#dash 409×405@y44；#panel 377×115@y58
要求：卡内改成"高度驱动"分区（状态条 / 面板 / 主区 / 底部诊断区 按卡片高度分比例），任何高度下：
      ① body.scrollHeight <= clientHeight（写进页内自检，像 liveRun5sNatural 那样报数）
      ② 内部元素不越界、不被裁（关键元素 rect 全部落在卡片内）
      ③ 卡片高度变化（1133/744/440 三档 + 等高压缩）时都成立
```

### ② item 3 · 仪表盘黑区右下 BPM 联动（竖条已联动，A 卡没联动）
```
现状：A 卡内 #bpmRead 显示「BPM 82 · 静音」，左栏 #pkBpmVal 变它不变
      #bpmToggleBtn 也在 A 卡内
根因：画布 JS 的 setBpmRead() 写的是隐藏宿主 #czStubHost{display:none!important} 里那份；
      A 卡里这份是副本 → 没人写
要求：总线把 A 卡（.cz-mod[data-mod="A"] > iframe 内）的 #bpmRead / #bpmToggleBtn 纳入：
      左 → 右：点左 #pkBpmUp ×2 ⇒ A 卡 #bpmRead 里的数字 82→84（贴前后值）
      右 → 左：点 A 卡 #bpmToggleBtn 或卡内 +1 ⇒ 左栏跟着变（贴前后值）
      就绪后 rebind（卡 iframe load 后重算，不许在空文档上判 fail）
      负控 ?negctl=bus ⇒ 必须红，且 verdict 写明"右栏 X 没跟着变（左栏 Y）"
```

### ③ item 4 · readout 未计时时不能是小数字
```
现状：.ac-root(#ttCounter) computed font-size 48px 但 box = 0×0（空心数字没渲染）
      实际可见的是 .readout-sub #metaVal「10分钟」16px ← dad 说的"小数字"
对照：装成的 dashboard-skin-01-v3.html 里 .ac-root 是有尺寸的（[data-vp="1133x744"] 那套规则生效）
要求：卡片里 #ttCounter 真渲染（确认 hollow-digits 初始化 + 尺寸链）；未开始时显示大号占位（如 --:-- 或 00:00 的 48/60px 形态），
      与 dashboard-skin-01-v3.html 同档一致（给两边同档的实测 rect + font-size 对比）
```

### ④ item 5 · 孔阵灵敏度 +20%
```
现状：level = Math.min(1.0, (rms - NOISE_FLOOR) * 4.0)
要求：+20%（4.0 → 4.8，或等效下调 NOISE_FLOOR）；给三条读数：静音时 level=0（孔阵全静止）、中等、大声时的 level 值与孔阵振幅像素
      不许自循环动画（引擎仍是真收音驱动）
```

### ⑤ item 6 · toast-banner + diag-card
```
现状：.toast-banner 47,405 351×21 display:flex opacity:1（常显）；.diag-card 34,362 377×73 白底
要求：① toast 默认不显示 —— hover（桌面）/ iPad 长按 .diag-status 才弹出（CSS+JS 成对，见 coder-workflow CSS+JS Pair）
      ② 长按/点击区域 = .diag-status；给出手法（pointerdown 计时 350~500ms）+ 不遮挡其它控件的证明
      ③ .diag-card 白底透明化，只留发丝线分层（不构成"框套框"）
      ④ 卡内总高别因为撤白底而变（给撤前/撤后 body.scrollHeight）
```

### ⑥ item 11 · 老师要求卡（Q）宽度适配
```
现状：卡内定宽内容塞进窄槽 → 日期截断（dad 截图3 实测「2026-0…」被切）
要求：卡内改流式（时间/标签行 wrap 或按容器缩号），窄档（744/440）下关键信息完整可读
      给判据：Q 卡内所有文本节点 scrollWidth <= clientWidth（无横向截断）
```

### ⑦ item 14 · 744 / 440 档卡片压叠（页面上有「卡内视口 1133 / 744 / 440」按钮可复现）
```
现状（我量的）：744 → 票卡 82,78 580×780；A 84,78 576×780（压叠）；440 → 票卡 16,78 397×780；A 18,78 393×780（压叠）
                三组合 × 两档 全部「票卡×A」压叠；doc 高 2486~3285（每卡 780 高竖排）
要求：≤744 与 ≤440 时，票卡与模块列**顺序单列**（先票卡、再模块列），且每卡高度按该档内容算（不要再固定 780）
      判据：三组合 × {744,440} 共 6 组，两两相交 = 0；票卡底边 <= 模块列顶边
      （更完整的断点规则 agy 会交 spec-agy-container-bp-261015.md，交了你按它再校一遍）
```

## 不做（等 agy 规格，别抢）
```
item 7  等高口径（B 单独出现要不要 = H）→ 等 spec-agy-eh-fix-261015.md
item 8  卡槽嵌进仪表盘 → 等 spec-agy-slot-combo1-261015.md
item 9/10 今日记录卡改 D 风格 + popout → 等 spec-agy-records-card-261015.md
item 12 组合1 内部重排 → 等 spec-agy-slot-combo1-261015.md
```

## 汇报
每条：真会话实测数 + verdict 原文。改完在 pane 里贴 7 条的收口表（before → after）。
需自己核的负控：① 总线 ?negctl=bus 真红 ② 窄档压叠复现（先红后绿）
