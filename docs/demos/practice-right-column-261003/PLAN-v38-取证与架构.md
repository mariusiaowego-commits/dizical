# demo v38 · 取证档案与架构决策输入（Codex 出具，2026-10-23）

> 用途：把「实测取证」交给 agy 做审美/架构方案；agy 的方案回来后由 Codex 复核、合并、再执行。
> 取证环境：真实无头 Chromium（Playwright），http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html，PID 43307。
> 本档案只记录**已测量的事实**与**根因判定**；审美与架构方案由 agy 出。

---

## 0. 一句话根因

**运行时的卡片全部内联在 `canvas-01.html` 的 `<template>` 里；同目录的 `dashboard-skin-01-v3.html` 等独立文件是过期镜像，改它们对 demo 无效。**
仪表盘被改坏，是因为**内联副本被改成了另一套算法**，而**参考基准（`dashboard-skin-01.html` 原始版）里那套是对的**。

| 角色 | 位置 | 状态 |
|---|---|---|
| 运行时仪表盘（真正生效） | `canvas-01.html` `<template id="tpl-A">`（第 6611 行起） | 被改坏 |
| 同目录仪表盘文件 | `dashboard-skin-01-v3.html` | **过期镜像**（其 `layoutArc` 还是旧算法 `R = dy + depth`） |
| 最早参考版本（用户表扬的那版） | `dashboard-skin-01.html`（第 258 行 `.round`、第 161-172 行缺口 mask） | ✅ 正确，但**从未被内联回来** |

其它卡片同理：`tpl-B`(9910) / `tpl-S`(12433) / `tpl-D`(13244) / `tpl-R`(14144) / `tpl-Q`(14791)；
对应文件 `metronome-01-v3.html`、`metronome-02-strip.html`、`practice-duration-card-01-v3.html`、`today-records-01.html`、`requests-card-01-v3.html` 同为镜像。

---

## 1. 仪表盘：旋钮 / 弧 / ± 按钮（用户图像 1 的 3 条批注）

### 1.1 参考图 `科目卡片参考-04.jpg` 的正确几何

- 深色面板**底部挖出圆形缺口**，缺口圆心 = 旋钮圆心；
- 大旋钮从缺口探出，旋钮外套一圈**刻度点弧**（半径与缺口同心）；
- ± 是**深色圆盘**，带**明显投影**，浮在浅底上，与旋钮同一水平轴；
- 面板底边的缺口弧线与旋钮点弧**同心连续**，三者是一个整体。

### 1.2 原始版 `dashboard-skin-01.html` 就是这么实现的（可直接回填）

```css
--dash-notch: 96px;                     /* 72/78 随视口 */
.panel{
  -webkit-mask-image: radial-gradient(circle var(--notch) at 50% calc(100% + 6px), transparent 97%, black 100%);
  mask-image:        radial-gradient(circle var(--notch) at 50% calc(100% + 6px), transparent 97%, black 100%);
}
.mid { margin-top: calc(var(--dash-notch) * -0.72); }   /* 把旋钮圆心拉到面板底边上 */
.round {                                                   /* ± 按钮 */
  flex: 0 0 auto; width: 58px; height: 58px; border-radius: 50%;
  background: linear-gradient(180deg, var(--dash-btn-face-hi), var(--dash-btn-face-lo));  /* 深色 #2A3036→#101316 */
  color: var(--dash-btn-glyph);                            /* 浅色字 #FFF8F0 */
  box-shadow: inset 0 1px 0 var(--dash-btn-rim), 0 6px 10px var(--dash-shell-inset);  /* 强投影 */
  font-size: 26px;
}
```

### 1.3 当前内联副本为什么坏（实测数值）

**（a）缺口弧塌缩 —— arc 消失的直接原因**

内联 `tpl-A` 的 `layoutArc()`（canvas-01.html 第 7814 行起）改成 JS 调整：
```js
var wantBelow = 0;                       // 期望：旋钮圆心落在面板底边
var delta = (kcy - pr.bottom) - wantBelow;
midEl.style.marginTop = ...              // 想把 .mid 往上拉
```
但注入样式里有：
```css
html.cz-fill .mid { margin-top: 16px !important; }   /* canvas-01.html:16311 —— !important 直接废掉 JS 修正 */
```
实测：`mid` 的 inline style 确实是 `margin-top: -70.2px`，**computed 仍是 16px**（被 !important 覆盖），
于是 `dy = 旋钮圆心 - 面板底边 = 80px`（期望 0）。

弧宽塌缩公式：`fx_offset = sqrt(max(0,(R+r)² - (dy+r)²))` = `sqrt(max(0,82² - 96²))` = **0**
→ clip-path 里那条 66px 圆弧退化成一条直线 → **面板底部没有缺口，弧点只剩一圈孤立的点环**。

**（b）mask 挖孔打空**

运行时 `#panel` 的 mask：`radial-gradient(66px at 50% 283px, transparent 98%, black 100%)`，
而面板本身只有 203px 高 → 挖孔圆心（局部 y=283）**整体落在面板盒子之外**，等于没生效。
（原始版的写法是 `at 50% calc(100% + 6px)`，永远贴着底边 —— 这点必须回填。）

**（c）± 按钮被改成白色弱阴影 44px**

| | 原始版（对） | 当前内联（错） |
|---|---|---|
| 尺寸 | 58px | 44px |
| 背景 | 深色盘 `#2A3036→#101316` | 白渐变 `linear-gradient(#fff,#E4E1DC)` |
| 投影 | `0 6px 10px rgba(44,62,80,.45)` | `0 4px 8px rgba(44,62,80,.14)` |
| 位置 | flex，与旋钮同轴 | grid `58px 302px 58px`，离面板 80px |

**（d）"knob 和 arc 不成一个整体"的量化**

- 面板底边 y=252，旋钮圆心 y=332（差 80px），刻度点环半径 62（点环在旋钮周围，不贴面板）；
- 原始版：旋钮圆心 y = 面板底边，点环半径 = 缺口半径 = 96 → 圆弧关系成立。

---

## 2. 其它已取证问题（交 agy 做方案，我负责复核）

| # | 用户批注 | 实测/定位结论 |
|---|---|---|
| A | 边角阴影「好几轮没解决」（图像 3） | 画布卡片阴影 token `--shadow-card`（canvas-01.html:342）= `0 1px 3px …, 0 8px 24px -4px …`；使用点 497 / 3561 / 3731。**症状是阴影被祖先 overflow 裁切后留下硬边直缝**，需要定位具体裁切祖先并改成「同层阴影」或去掉裁切。agy 需定位到具体元素与具体裁切祖先。 |
| B | `title-col` 的「分钟」下标太粗太大（补充 2） | 节点 `canvas-01.html:7500 <span class="readout-unit" id="readoutUnit">分钟</span>`，样式在 6940 附近 `.title-col`。要求：极细字重（≈200-300）、字号约为大数字的 1/3~1/2、基线右下沉、颜色降饱和。 |
| C | 竖条节拍器可读性差（图像 2，1133 组合2） | S 卡 = `tpl-S`（canvas-01.html:12433）。宽栏下被压成细竖条，字号/对比需按「竖排模式」单独规格。 |
| D | 横向拓展视口下「今日练习时长卡」大片空白（补充 5 / 图像 5） | D 卡 = `tpl-D`（canvas-01.html:13244）。宽栏下应**限宽并居中**（或改双栏信息），而不是拉伸到整宽。 |
| E | 纵向 feed 流布局元素没排布好（图像 4） | 已有 `html.cz-fill.cz-feed`（16176）等零散覆盖，但只是逐点打补丁，**没有每卡在 feed 模式下的规格**。图像 4 里 S 卡的「设置」浮层直接压住 `+` 按钮。 |
| F | 票夹变小与卡槽插卡动画没有先后顺序（补充 3） | 实测 enterRun：票夹收缩（左栏 360→50 / 高度 669→52）与卡槽插卡（卡片 opacity 0→1）**同步进行（0-400ms 同时）**，所以看不到插卡动作。要求串行：先收票夹 → 再插卡。 |
| G | 展开卡片要有「从卡槽出来」的动效（补充 4） | 现状 `cz-card-overlay` 直接 `display:flex` 全屏蒙层 + 弹窗，无出槽动效。 |

---

## 3. 用户对架构的总判断（原文要点，必须落到方案里）

> 「前期做了太多不同视口的适配工作。其实应该做好的就是**每张卡片在横向扩展卡片模式 与 纵向无限 feed 流模式 两种模式下**，针对不同设备宽度高度做好可读性佳、适配不同设备的卡片样式。这样不论什么视口、什么卡片互相组合，都能比较美观与和谐。」

因此方案要回答：

1. **两模式定义**：什么条件下进入「横向扩展卡片模式」、什么条件下进入「纵向 feed 流模式」？（判定必须在卡片自身内，不能只靠外层视口断点）
2. **每卡 × 每模式的布局规格**：A 仪表盘 / S 竖条节拍器 / B 节拍器 / D 今日时长 / R 今日记录 / Q 老师要求，6 张卡 × 2 模式 = 12 份规格，每份含：宽度策略、字号阶梯、网格、关键元素可见性优先级、溢出与滚动策略。
3. **单一真源**：消灭「内联模板 vs 独立文件」双份实现 —— 每张卡只留一份实现（agy 给方案：抽公共文件 + 构建注入，还是保留内联但消灭镜像文件并加同步校验）。
4. **不得回归**：以下已通过项必须保持 —— 卡片/卡槽与黑色读数区重叠 0 px²、露出比例 ≈20%、记录弹窗明细可见、enter/exit 形变空窗帧数 0。

---

## 4. 交付给 agy 的产出要求

1. **仪表盘审美规格**：按 `科目卡片参考-04.jpg` 给出旋钮/缺口/点弧/± 四者的同心几何公式（给出具体 CSS/JS 改法，替换掉现在失效的 `wantBelow` JS 补丁），以及浅/深两套皮肤下的 token 值。
2. **两模式布局架构**：给出 12 份卡片规格的实现方式（CSS 变量 / class 切换 / container query 的取舍），以及模式判定规则。
3. **对本文档根因判定的 review**：哪几条判定有误、哪一条还有遗漏（尤其 A 的边角阴影具体元素）。
4. **分阶段实施计划**：每阶段的改动范围、验收口径（可量化）、回归红线。
5. 方案文档写到 `docs/demos/practice-right-column-261003/PLAN-v38-agy方案.md`，截图放 `/tmp/v38-agy-*.png`。
6. **方案阶段不得改代码**（只出方案，等 Codex 与 dad 确认后再实施）。

---

## 5. 追加取证（第二轮，2026-10-23 晚）

### 5.1 🔴 严重：组合定义与渲染结果不一致（比用户描述的更严重）

| 入口 | 定义 | 实际渲染 | 差异 |
|---|---|---|---|
| `③ 全右栏六卡` 预设 | `PRESETS['3'] = ['A','B','S','D','R','Q']`（6 张） | **A,B,D,R（4 张）** | **S 和 Q 直接没有节点，不是隐藏** |
| 组合 1 | `COMBO_MODS['1'] = ['A','D','R','S']` | A,D,R,S | 一致（但「组合1」不该含 R/S，与预设②含义冲突） |
| 组合 2 | `COMBO_MODS['2'] = ['A','S','D','R']` | A,S,D,R | **不含 Q**，与预设②「仪表盘+时长+要求」矛盾 |
| 组合 3 | `COMBO_MODS['3'] = ['A','B','D','R']` | A,B,D,R | **不含 S、Q**，与「六卡」文案矛盾 |

根因：`canvas-01.html:16629` `COMBO_MODS` 只有三套四卡表，`COMBO_DEFS` 树里也只写了 A/D/R/S 或 A/B/D/R；
而工具栏文案（第 259 行）与预设（第 16089 行）承诺的是六卡。**两套数据源没有约束关系**。

> 这条必须由 agy 在架构层面解决：组合定义只允许一份数据（预设/组合/树由一个表派生），并加断言「渲染节点数 == 定义数」。

### 5.2 纵向 feed 模式下视觉顺序与 DOM 顺序不一致

实测（DOM 顺序 vs 屏幕上的 y 坐标排序）：

```
1133 c3  DOM=A,B,D,R   视觉=A→B→D→R   ✅
744  c3  DOM=A,B,D,R   视觉=A→D→R→B   ❌ B 被甩到最后
440  c3  DOM=A,B,D,R   视觉=A→D→R→B   ❌ 同上
```

原因：窄档（<1024）`.cz-combo` 变 `flex-direction: column`，但 B 卡在树里是 `.cz-mod`、D/R 在 `.cz-comp` 里，
而 `.cz-comp` 的 `flex` 顺序与 `.cz-mod` 不一致（`order` 未定义 + 负 margin/`.cz-astack-crown` 参与布局）。
**用户「纵向 feed 流布局元素没排好」的根因就在这里：不是间距问题，是顺序错乱。**

### 5.3 440 组合3 的 feed 页实际表现

全页截图 `/tmp/v38-440-c3-full.png`：A（666px）→ D（177px）→ R（162px）→ B（768px），
中间夹着大片空白（A 底部到 D 顶部之间 12px 正常，但 D/R 这两个矮卡与大卡混排后节奏断裂）。
且四张卡里有 **2 张不足 180px 高**，与 A/B 的 666/768 高差 4 倍以上 —— 这是「没有 feed 规格」的直接证据。

### 5.4 title-col「分钟」下标（实测数值）

```
节点   #readoutUnit（canvas-01.html:7500）
字号   26px       ← 太大
字重   700        ← 太粗（用户要「极细」）
字距   0.52px
位置   x=269, y=123, w=53, h=26（大数字 #readoutDigits: x=196,y=101,w=69,h=52）
比例   字号 = 大数字高度的 50%，宽度占 53px
```

对比大数字：`#readoutDigits` 是 SVG 空心数字（`hollow-digits`），字重 560 但视觉是 1-2px 细线。
**「分钟」用的是 700 实心字重，视觉重量远大于大数字本身 —— 这就是「太粗」的量化原因。**

建议口径（供 agy 参考，最终由 agy 定）：字号 13-15px、字重 200-300、位置 `vertical-align: sub` 或 `translateY(0.35em)`。
（当前 26px/700 → 大数字视觉线宽比约 1:6，改成 14px/250 后约 1:2。）

### 5.5 今日练习时长卡（D）宽栏大片空白（实测）

1133 组合1：
```
D 卡 body: 360 × 469
内容最后元素底部 y = 184
底部空白 = 285px （占卡片高度 61%）
```

即 61% 的卡片面积是空的。这与用户「横向拓展视口下今日练习时长卡下面大片空白」完全对应。
**注意：这不是 padding 问题，是卡片按整宽拉伸但内容只有 184px 高。** 正确做法应是限宽/双栏/或改成横向条状，由 agy 给规格。

### 5.6 竖条节拍器（S）在 1133 组合2 的可读性（实测）

```
bpmFace  60    字号 28px  字重 800  颜色 rgb(44,62,80)
tempoTerm 慢板  字号 11px  字重 700  颜色 rgb(102,102,102)  ← 对比度不足
容器宽度 76px（COMBO_DEFS['2'] 里 w:76, tate:true）
```

`#bpmFace` 宽 38px 但字号 28px/800 → 在 76px 竖条里只剩 19px 边距；
`慢板` 11px/700 灰 #666 在浅银底上对比度约 3.2:1（低于 4.5:1）。
且实测 S 卡的 ± 按钮在 1133 组合2 下 **DOM 里不存在**（`plus: null, minus: null`）—— 竖条模式下按钮是另一套节点。

### 5.7 边角阴影（图像3）真实定位

实测所有带 `box-shadow` / `filter` 的元素，唯一「被祖先裁切」且会造成硬边直缝的是：

```
DIV#pkSlotCavity.pk-slot-cavity   rect {x:407,y:61,w:434,h:16}
  box-shadow: rgba(0,0,0,0.95) 0 6px 14px inset
  裁切祖先：
    1) DIV.pk-punch-slot-wrap.cz-punch-slot.dash-integrated-slot  overflow: hidden
    2) DIV.cz-astack-crown.dash-top-rim                          overflow: hidden
    3) DIV.cz-combo                                              overflow: auto
```

另外 `DIV#czRecordsMini.card-records-mini`（rect x:630,y:652,w:224,h:220）
box-shadow `0 12px 28px rgba(44,62,80,.18)` 被两层 `.cz-node.cz-mod` / `.cz-node.cz-brow` 的 `overflow:hidden` 裁掉下半部分阴影。

⚠️ 用户截图里的「灰色直角边缘」还可能是**卡片 iframe 的矩形边界本身**（iframe 无圆角，卡片圆角画在 iframe 内部），
需要在真机/iPad 上比对确认。这条请在方案里一并给出判断方法与修法（例如 iframe 加 `border-radius` + `overflow:hidden`，或把阴影画到 iframe 外层的 `.cz-mod` 上）。

### 5.8 动效时序（实测，供 agy 做时序方案）

enterRun（744，逐 20ms）：
```
ms=0    票夹 h=742   rail op=0.39   卡槽卡 op=0
ms=80   票夹 h=738   rail op=0.55   卡槽卡 op=0.34   ← 收缩和插卡同时开始
ms=160  票夹 h=625   rail op=0.88   卡槽卡 op=0.92
ms=280  票夹 h=114   rail op=1.00   卡槽卡 op=1.00   ← 票夹还在收，卡已完全出现
ms=360  票夹 h=53                              ← 票夹收尾
```
**结论：收缩（0-400ms）与插卡（0-240ms）完全重叠，插卡动作被票夹收缩掩盖。** 用户要求串行。
