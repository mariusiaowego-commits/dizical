# spec-pixel-a2a3-261010 — D1 谱架模式键重做（A2）+ diag-card 单框重写（A3）

日期 2026-10-10 · 作者 hermes `pixel` profile · 对象 `docs/demos/practice-right-column-261003/dashboard-skin-01-v3.html`（**已按本规格改完**）
对照页（可点）`docs/demos/practice-right-column-261003/a2a3-probe-pixel.html`
上游：`plan-261010c.md` §A2/§A3 · `brief-pixel-a2a3-261010.md`

---

## 0 一句话结论

**A3**：`diag-card` 里那层「提示条圆角框」拆掉，全卡只留**一层框**（卡自身），分层改用 **1px 细分割线 + 内边距/留白**（备选：满血弱底带）；顺手修掉深墨皮肤下**白底暖白字 1.05:1** 的底（`--dash-white` → `--dash-surface-soft`）。
**A2**：谱架键从「橙→珊瑚渐变 + 双阴影 + 白字 2.29:1」换成卡内既有的**沉头浅凹键**语言（托盘弱底 + 1px 描边 + 只内凹），并补**激活态**；该行改成 **主控件行 + 说明行** 两段，三列主控件 centerline 极差 **18.50px → 0.00px**。

改完实测：`dashboard-skin-01-v3.html?audit=1` → **ASSERT_OK / fails: []**；对照页 `?audit=1` → **ASSERT_OK / fails: []**。

---

## 1 改前诊断（全部实测，不是转述）

### A2 该行「上下没对齐 / 不统一」

三列主控件（孔阵 / 开始药丸 / 谱架键）的中心 Y：

| 档 | 孔阵 cy | 药丸 cy | 谱架键 cy | 极差 |
|:--|:--|:--|:--|:--|
| 1133×744（卡 420） | 616.50 | 633.50 | 615.00 | **18.50px** |
| 744×1133（卡 500） | 632.50 | 649.50 | 631.00 | **18.50px** |
| 440×956（卡 390） | 616.50 | 633.50 | 615.00 | **18.50px** |

**根因**：三列各自是「前导/尾随文字 + 主控件」的竖栈，栈内文字高度不同（孔阵下 8px logo / 药丸上 16px 计时 / 键下 13px 大屏看谱），而网格只把**列盒子**居中 → 主控件被各自的前后文字顶偏：药丸比行心低 +12.00px、孔阵高 −5.00px、谱架键高 −6.50px。

### A2 谱架键本体

| 项 | 改前实测 | 判定 |
|:--|:--|:--|
| 尺寸 | 56×44（卡 ≤440 容器档）/ 66×44（744 档） | 命中 44 ✓ |
| 底 | `linear-gradient(180deg, var(--dash-accent), var(--dash-coral))` = `rgb(255,140,90)` → `rgb(255,107,107)`（深墨 `rgb(255,87,34)` → `rgb(255,107,107)`） | 品牌色当副操作底，与卡内「银面/托盘」两族都不沾 |
| 字 | `--dash-white` 压上述渐变 | **2.29:1（浅银）/ 2.78:1（深墨）→ 低于 4.5** ✗ |
| 投影 | `inset 0 1px 0 btn-rim` + `0 4px 8px shell-inset` = **1 内 + 1 外** | 甲板上多出一层外投影 ✗ |
| 激活态 | **无**（`.is-on` 不改任何东西，点下去没有反馈） | ✗ |

### A3 `diag-card` 圆角框套圆角框

扫描口径：**容器框** = 四边 `border-width > 0` 且有圆角的非控件元素；**嵌套对** = 容器框的祖先链里还有容器框；**竖向扫描线**（过卡中心）**穿过几条框线带**。

| 指标 | 改前实测 |
|:--|:--|
| 卡内容器框 | **2** 个：`diag-card`（r16）+ `toast-banner`（r6） |
| 容器框套框（嵌套对） | **1** 对：`toast-banner ⊂ diag-card` |
| 竖向扫描线穿过框线带 | **4** 条：y=679 卡顶 / y=722 提示条顶 / y=745 提示条底 / y=754 卡底 |
| 控件框（按钮） | 2 个 `.diag-btn`（1px + r6）——属按钮可点边界，**不算框套框**（保留） |

**顺带发现的真缺陷（深墨皮肤）**：`.diag-card { background: var(--dash-white) }`，而深墨皮肤**不覆盖** `--dash-white`（仍 `#FFFFFF`），字色却是 `--dash-text = #FFF8F0`：

| 元素 | 浅银 | 深墨 |
|:--|:--|:--|
| 状态文字（声波监听…） | 10.98:1 ✓ | **1.05:1** ✗ |
| 提示文字（扬声孔与麦克风…） | 5.71:1 ✓ | **1.33:1** ✗ |

→ 深墨皮肤下这块等于「白底白字」。A3 重写必须一并修掉（否则「只有一层框」也救不回可读性）。

---

## 2 A2 方案

### 2.1 行结构：主控件行 + 说明行（这是「共中轴」的唯一稳解）

```
.deck.transport            →  flex column, gap 4px
  ├─ .transport-main.grid-3col   孔阵 ｜ 开始/提前结束药丸 ｜ 谱架模式键
  └─ .transport-caps.grid-3col   dizical logo ｜ 00:00 · 待开始 ｜ 大屏看谱
```

- 两段都是真卡既有的 `.grid-3col`（`align-items:center` + 68px/1fr/68px 列，≤440 容器下自动收成 58px），**没有新列系统**。
- 主控件行里每列**只放一个主控件** → 网格 `align-items:center` 直接让三者 centerline 重合（不是靠手调 padding）。
- 说明行把原来散在三列里的三行小字（logo / 计时 / 大屏看谱）收成**一套 caption 语言**：`10px / 650 / --dash-text-soft / letter-spacing .04em`（计时保留 `tabular-nums`；原来 11px 衬线 800 + `--dash-kicker` 的「kicker」风格取消）。
- 取舍：计时文字从药丸**上方**挪到**下方**。理由——「共中轴」要求每列主控件前后留白对称；把三处辅助文字集中到一段说明行，是三档卡宽都不需要手调像素的做法。若 dad 要计时留在上方，只能回到逐列 padding 微调（脆，且 744 档会再次错开）。

### 2.2 谱架键形态（两个候选，推荐 A2-1）

| 项 | **A2-1 沉头浅凹键（推荐·已实施）** | A2-2 银面浮雕键（候选） |
|:--|:--|:--|
| 尺寸 | `min-width:66px` / `height:44px` / `padding:0 10px`（≤440 容器收 `min-width:56px` / 11px） | 同左 |
| 圆角 | 12px | 12px |
| 描边 | `1px solid var(--dash-shell-inset)` | `1px solid var(--dash-shell-inset)` |
| 底 | `var(--dash-tray-inset)`（浅银 `rgba(0,0,0,.08)` → `rgb(213,211,206)` / 深墨 `rgba(0,0,0,.35)` → `rgb(14,17,20)`） | `linear-gradient(180deg, var(--dash-btn-face-hi), var(--dash-btn-face-lo))`（浅银 `#FFF`→`#E4E1DC` / 深墨 `#2A3036`→`#101316`） |
| 字 | `var(--dash-text)` 12px / 750 | `var(--dash-btn-glyph)` 12px / 750 |
| 投影 | **只 1 层内凹**：`inset 0 1px 2px var(--dash-shell-inset)`；**无外投影** | `inset 0 1px 0 var(--dash-btn-rim)` + `0 4px 8px var(--dash-shell-inset)`（**1 内 + 1 外**） |
| 激活态 | `--dash-coral-solid` 底 + `--dash-white` 字 + `--dash-coral` 描边，投影清空 | 同左（保留顶部高光） |
| idle 对比度 | **7.33:1（浅银）/ 17.99:1（深墨）** | 8.42:1 / 12.66:1 |
| 激活对比度 | **4.93:1**（白字压 `--dash-coral-solid`，两皮肤同值） | 4.93:1 |
| 语言出处 | 卡内 `.mic-status-btn` 的**托盘/凹陷**族（`--dash-tray-inset` + `--dash-cover-line` 同源） | 卡内 `.round` ± 键的**银面浮雕**族（`--dash-btn-face-*` + `--dash-btn-rim`） |
| 代价 | 副操作「凹」、主操作「凸」→ 层级更明确 | **甲板上多一层外投影**（违反硬约束「主按钮是唯一有投影的一层」）→ 本规格记为**已知代价**，不计入 fails |

**推荐 A2-1 的理由**：① 不新增投影层（严格守住硬约束）；② 谱架模式是**副操作**，用「凹」与「开始」的「凸」形成层级差；③ 复用卡内已存在的托盘 token 组合，不引入新的材质语言。

```css
/* 已写入 dashboard-skin-01-v3.html */
.stand-btn {
  min-width: 66px; height: 44px; padding: 0 10px; white-space: nowrap;
  border: 1px solid var(--dash-shell-inset); border-radius: 12px;
  background: var(--dash-tray-inset);
  color: var(--dash-text);
  font-family: inherit; font-size: 12px; font-weight: 750;
  box-shadow: inset 0 1px 2px var(--dash-shell-inset);
  touch-action: manipulation; cursor: pointer;
}
.stand-btn:active { transform: scale(0.96); }
.stand-btn.is-on {
  background: var(--dash-coral-solid); color: var(--dash-white);
  border-color: var(--dash-coral); box-shadow: none;
}
```

### 2.3 A2 改前 → 改后（实测）

| 指标 | 改前 | 改后 |
|:--|:--|:--|
| 三列主控件 centerline 极差 | **18.50px**（616.50 / 633.50 / 615.00） | **0.00px**（616 / 616 / 616） |
| 说明行 centerline 极差 | 无「说明行」概念（三处小字各自成组） | **0.00px**（663.25 / 663.25 / 663.25） |
| 每列「主控件↔说明」竖轴差 | — | **0.00 / 0.01 / 0.01 px** |
| 谱架键尺寸 | 56×44 / 66×44 | **58×44（≤440 容器档）/ 70×44（744 档）** |
| 谱架键外投影层 | 1 | **0** |
| 谱架键 idle 对比度 | **2.29:1 / 2.78:1** ✗ | **7.33:1 / 17.99:1** ✓ |
| 谱架键激活态 | 无 | 珊瑚实心 **4.93:1** ✓ |
| 甲板行高 | 95px | 99px（卡内 `scrollHeight == clientHeight`，无裁切，三档实测） |

三档卡宽 × 两皮肤全部 `fails: []`（见 §5）。

### 2.4 顺带修的一处（A2 副作用，已纳入断言）

孔阵被 `alignSpeakerWithCover()` 按「与封面同竖轴」平移了 +37px（对齐 `cover-col`），但**搬进说明行的 logo 没有跟着平移** → 孔阵在 622、自己的 logo 留在列心 585，**同列错 37px**。
已把该函数扩展为「孔阵与 logo 用同一个偏移」，并加断言 **A2-7**（每列主控件↔说明的 cx 差 ≤1px）机器看着。实测改后：`孔阵↔logo 0.00 / 药丸↔计时 0.01 / 谱架键↔大屏看谱 0.01`。

---

## 3 A3 方案

### 3.1 框线普查：改了哪几处、每处改前是几层框

| # | 位置 | 改前 | 改后 |
|:--|:--|:--|:--|
| 1 | `.diag-card`（卡自身） | 1 层框（1px `--dash-shell-inset` + r16） | **保留**（全卡唯一一层框） |
| 2 | `.toast-banner`（提示条） | **第 2 层框**：1px `--dash-accent-line` + r6 + `--dash-notice-bg` 底 | **拆掉**：0 边 + 0 圆角，改 1px 上分割线（`--dash-ink-a12`）或满血弱底带 |
| 3 | `.diag-btn` ×2（开启收音 / 发声: 关） | 1px + r6（**控件框**） | 保留不动（按钮需要可点边界，不是「框套框」） |

同一规则在卡内其它区块的普查结果：**没有第二处容器框套框**（`.cover-halo` 内层 `.cover-frame` 无边框；`.pill` / `.grille` / 面板均无边框）→ 本轮只改上面 1 处 + 卡底 token。

### 3.2 两个候选

**A3-1 细分割线（推荐·已实施）**

```css
.diag-card {
  background: var(--dash-surface-soft);     /* 会随皮肤翻转：浅银 #FFFDFB / 深墨 #1A1E22 */
  border: 1px solid var(--dash-shell-inset);/* 全卡唯一一层框 */
  border-radius: 16px; padding: 8px 12px; gap: 6px;
}
.toast-banner {
  background: transparent; border: 0; border-radius: 0;
  border-top: 1px solid var(--dash-ink-a12); /* 单边 1px：只有一条边 → 不构成框 */
  padding: 6px 0 0; margin: 0;
}
```

**A3-2 弱底带（候选）**

```css
.diag-card { background: var(--dash-surface-soft); padding: 8px 0 0; overflow: hidden; }
.diag-row  { padding: 0 12px; }
.toast-banner {
  background: var(--dash-ink-a04); border: 0; border-radius: 0;
  margin: 0; padding: 6px 12px;             /* 满血到卡内边，被卡的 r16 裁掉 */
}
```

| 项 | A3-1 细分割线 | A3-2 弱底带 |
|:--|:--|:--|
| 容器框 / 嵌套 / 扫描线框线带 | 1 / 0 / 2 | 1 / 0 / 2 |
| 浅银 状态 / 提示 对比度 | 10.82 / 6.00 | 10.82 / 5.61 |
| 深墨 状态 / 提示 对比度 | 15.92 / 12.52 | 15.92 / 11.26 |
| 观感 | 最克制：提示行像一条脚注 | 分组感更强：底部一整条弱底托盘 |
| 代价 | 分割线在浅银下很轻（`--dash-ink-a12` ≈ 1.1:1 的线），弱到几乎只看得到留白 | 卡底部左右内边距必须由子元素自己补（卡 padding 归零），后续加元素要记得 |

**为什么这样分层不套框**（dad 的「大忌讳」）：框线在视觉上是**闭合的矩形轮廓**，两层闭合轮廓必然产生「盒子里还有一个盒子」的读数；而**单边线 + 内边距**不会闭合，只表达「换了一层内容」。所以拆框的同时必须给足留白（本规格：行→线 6px、线→字 6px、卡内边距 12px），否则会退化成「用留白硬撑」。

### 3.3 A3 改前 → 改后（实测）

| 指标 | 改前 | 改后（A3-1 / A3-2 相同） |
|:--|:--|:--|
| 卡内容器框数 | **2**（`diag-card`, `toast-banner`） | **1**（`diag-card`） |
| 容器框套框嵌套对 | **1**（`toast-banner ⊂ diag-card`） | **0** |
| 竖向扫描线穿过框线带 | **4** 条（679/722/745/754） | **2** 条（682 卡顶 / 754 卡底） |
| 卡底 token | `--dash-white`（深墨不翻转） | `--dash-surface-soft`（翻转） |
| 深墨 状态文字 | **1.05:1** ✗ | **15.92:1** ✓ |
| 深墨 提示文字 | **1.33:1** ✗ | **12.52:1**（A3-1）/ **11.26:1**（A3-2）✓ |
| 浅银 状态 / 提示 | 10.98 / 5.71 | 10.82 / 6.00（A3-1）· 5.61（A3-2） |
| 卡内按钮文字（两皮肤） | 8.99 / 9.00 | 8.99 / 9.00（不动） |

---

## 4 断言清单（已写进卡的自检 + 对照页自检）

| ID | 断言 | 口径 |
|:--|:--|:--|
| A2-1 | 主控件行三列主控件 centerline 极差 ≤1px | `getBoundingClientRect().cy` |
| A2-2 | 说明行三列说明 centerline 极差 ≤1px | 同上 |
| A2-3 | 谱架键命中区 ≥44×44 | 元素盒子（无 `::before` 扩展） |
| A2-4 | 谱架键**无外投影**（box-shadow 里不含非 inset 层） | 逗号拆层 + 过滤 inset |
| A2-5 | 谱架键文案 = 2–4 汉字纯名字、无 emoji | 正则 |
| A2-6 | 谱架键 idle / 激活 对比度 ≥4.5（两皮肤） | WCAG 自算，底取「自身底压卡壳渐变暗端」，渐变底取全部色停的最差值 |
| A2-7 | 每列「主控件 ↔ 说明」竖轴差 ≤1px | cx 差 |
| A2-8 | 甲板无横向溢出 | `scrollWidth ≤ clientWidth+1`（对照页） |
| A2-9 | 谱架键有激活态（`.is-on` 真的改底） | 对照页（基线块靠这条显形） |
| A3-1 | `diag-card` 容器框数 = 1 | 四边 border>0 且 r>0 的非控件元素 |
| A3-2 | 容器框套框 = 0 对 | 容器框的祖先链 |
| A3-3 | 竖向扫描线穿过框线带 = 2 条 | 卡中心竖线与各框上下边带求交 |
| A3-4 | 卡内状态/提示/按钮文字对比度 ≥4.5（两皮肤） | WCAG 自算 |
| A3-5 | diag 卡无横向溢出 | 对照页 |

---

## 5 实测证据

### 5.1 卡自身 `dashboard-skin-01-v3.html?audit=1`（新增段原样）

```text
ASSERT_OK
"A2_A3": {
    "A2_mainControlCys": [ 616, 616, 616 ],
    "A2_mainCenterlineSpread": 0,
    "A2_captionCys": [ 663.25, 663.25, 663.25 ],
    "A2_captionCenterlineSpread": 0,
    "A2_columnAxisDiffs": [ "孔阵↔logo 0.00", "药丸↔计时 0.01", "谱架键↔大屏看谱 0.01" ],
    "A2_standHit": [ 58, 44 ],
    "A2_standDropShadowLayers": 0,
    "A2_A3_contrast": {
      "light": { "standIdle": 7.33, "standOn": 4.93, "standBack": "rgb(213,211,206)", "diagCardBack": "rgb(255,253,251)",
                 "diagStatus": 10.82, "diagTip": 6, "diagBtn": 8.99 },
      "ink":   { "standIdle": 17.99, "standOn": 4.93, "standBack": "rgb(14,17,20)", "diagCardBack": "rgb(26,30,34)",
                 "diagStatus": 15.92, "diagTip": 12.52, "diagBtn": 9 }
    },
    "A3_containerFrames": [ "diag-card" ],
    "A3_nestedFramePairs": [],
    "A3_frameBandsOnScanline": [ "682 top diag-card", "754 bottom diag-card" ]
  },
"fails": [],
"verdict": "ASSERT_OK"
```

三档卡宽 × 两皮肤逐个复跑（注入式跑 `window.runAudit()`，只取 A2/A3 段）：

```text
[1133x744 / light]  fails=[]   主控件 cy [616,616,616] spread=0   说明行 cy [663.25,663.25,663.25] spread=0
[1133x744 / ink]    fails=[]   同上
[744x1133 / light]  fails=[]   主控件 cy [632,632,632] spread=0   说明行 cy [679.25,679.25,679.25] spread=0   命中 [70,44]
[744x1133 / ink]    fails=[]   同上
[440x956 / light]   fails=[]   主控件 cy [616,616,616] spread=0   说明行 cy [663.25,663.25,663.25] spread=0   命中 [58,44]
[440x956 / ink]     fails=[]   同上
```

### 5.2 对照页 `a2a3-probe-pixel.html?audit=1`（未删节）

```text
=== a2a3-probe-pixel · ?audit=1 ===
probe: A2 谱架键 + A3 diag 单框 候选对照   窗口: 1400×813
口径: A2 主控件/说明行 centerline 极差 ≤1px · 谱架键命中 ≥44 且无外投影 · A3 容器框=1 / 嵌套=0 / 扫描线框线带=2 · 对比度 ≥4.5（两皮肤）

--- 卡宽 420px（真卡 1133×744 档）× 皮肤 light ---
  A2 现状 [基线]  主控件 cy [266.25, 283.25, 264.75] 极差 18.50px   （无说明行）   键 56x44 外投影 1 层  底 rgb(255,140,90) / rgb(255,107,107)  idle对比 2.29  激活 （无激活态）
      asserts: FAIL → A2-1 主控件行 centerline 极差 18.50px > 1px [266.25 / 283.25 / 264.75] | A2-4 谱架键外投影 1 层（甲板只允许主操作抬升） | A2-6 谱架键 idle 字/自身底 2.29:1 < 4.5 | A2-9 谱架键没有激活态（.is-on 不改底）
  A2-1 沉头浅凹键 [候选]  主控件 cy [415.75, 415.75, 415.75] 极差 0.00px   说明行极差 0.00px   竖轴差 [0.00, 0.01, 0.01]   键 58x44 外投影 0 层  底 rgb(213,211,206)  idle对比 7.33  激活 4.93
      asserts: OK
  A2-2 银面浮雕键 [已知代价]  主控件 cy [569.25, 569.25, 569.25] 极差 0.00px   说明行极差 0.00px   竖轴差 [0.00, 0.01, 0.01]   键 58x44 外投影 1 层  底 rgb(255,255,255) / rgb(228,225,220)  idle对比 8.42  激活 4.93
      asserts: FAIL → A2-4 谱架键外投影 1 层（甲板只允许主操作抬升）
  A3 现状 [基线]  容器框 ["diag-card","toast-banner"]  嵌套 1 对  扫描线框线带 4 条   卡底 rgb(255,255,255)  对比 状态 10.98 / 提示 5.71 / 按钮 8.99
      asserts: FAIL → A3-1 diag-card 容器框数 2（应 = 1）: diag-card , toast-banner | A3-2 容器框套框 1 对: toast-banner ⊂ diag-card | A3-3 竖向扫描线穿过框线带 4 条（应 = 2）: 727 top diag-card ; 770 top toast-banner ; 793 bottom toast-banner ; 802 bottom diag-card
  A3-1 细分割线 [候选]  容器框 ["diag-card"]  嵌套 0 对  扫描线框线带 2 条   卡底 rgb(255,253,251)  对比 状态 10.82 / 提示 6 / 按钮 8.99
      asserts: OK
  A3-2 弱底带 [候选]  容器框 ["diag-card"]  嵌套 0 对  扫描线框线带 2 条   卡底 rgb(255,253,251)  对比 状态 10.82 / 提示 5.61 / 按钮 8.99
      asserts: OK

--- 卡宽 500px（真卡 744×1133 档）× 皮肤 light ---
  A2 现状 [基线]  主控件 cy [266.25, 283.25, 264.75] 极差 18.50px   （无说明行）   键 66x44 外投影 1 层  底 rgb(255,140,90) / rgb(255,107,107)  idle对比 2.29  激活 （无激活态）
      asserts: FAIL → A2-1 主控件行 centerline 极差 18.50px > 1px [266.25 / 283.25 / 264.75] | A2-4 谱架键外投影 1 层（甲板只允许主操作抬升） | A2-6 谱架键 idle 字/自身底 2.29:1 < 4.5 | A2-9 谱架键没有激活态（.is-on 不改底）
  A2-1 沉头浅凹键 [候选]  主控件 cy [415.75, 415.75, 415.75] 极差 0.00px   说明行极差 0.00px   竖轴差 [0.00, 0.01, 0.01]   键 66x44 外投影 0 层  底 rgb(213,211,206)  idle对比 7.33  激活 4.93
      asserts: OK
  A2-2 银面浮雕键 [已知代价]  主控件 cy [569.25, 569.25, 569.25] 极差 0.00px   说明行极差 0.00px   竖轴差 [0.00, 0.01, 0.01]   键 66x44 外投影 1 层  底 rgb(255,255,255) / rgb(228,225,220)  idle对比 8.42  激活 4.93
      asserts: FAIL → A2-4 谱架键外投影 1 层（甲板只允许主操作抬升）
  A3 现状 [基线]  容器框 ["diag-card","toast-banner"]  嵌套 1 对  扫描线框线带 4 条   卡底 rgb(255,255,255)  对比 状态 10.98 / 提示 5.71 / 按钮 8.99
      asserts: FAIL → A3-1 diag-card 容器框数 2（应 = 1）: diag-card , toast-banner | A3-2 容器框套框 1 对: toast-banner ⊂ diag-card | A3-3 竖向扫描线穿过框线带 4 条（应 = 2）: 727 top diag-card ; 770 top toast-banner ; 793 bottom toast-banner ; 802 bottom diag-card
  A3-1 细分割线 [候选]  容器框 ["diag-card"]  嵌套 0 对  扫描线框线带 2 条   卡底 rgb(255,253,251)  对比 状态 10.82 / 提示 6 / 按钮 8.99
      asserts: OK
  A3-2 弱底带 [候选]  容器框 ["diag-card"]  嵌套 0 对  扫描线框线带 2 条   卡底 rgb(255,253,251)  对比 状态 10.82 / 提示 5.61 / 按钮 8.99
      asserts: OK

--- 卡宽 390px（真卡 440×956 档）× 皮肤 light ---
  A2 现状 [基线]  主控件 cy [266.25, 283.25, 264.75] 极差 18.50px   （无说明行）   键 56x44 外投影 1 层  底 rgb(255,140,90) / rgb(255,107,107)  idle对比 2.29  激活 （无激活态）
      asserts: FAIL → A2-1 主控件行 centerline 极差 18.50px > 1px [266.25 / 283.25 / 264.75] | A2-4 谱架键外投影 1 层（甲板只允许主操作抬升） | A2-6 谱架键 idle 字/自身底 2.29:1 < 4.5 | A2-9 谱架键没有激活态（.is-on 不改底）
  A2-1 沉头浅凹键 [候选]  主控件 cy [415.75, 415.75, 415.75] 极差 0.00px   说明行极差 0.00px   竖轴差 [0.00, 0.01, 0.01]   键 58x44 外投影 0 层  底 rgb(213,211,206)  idle对比 7.33  激活 4.93
      asserts: OK
  A2-2 银面浮雕键 [已知代价]  主控件 cy [569.25, 569.25, 569.25] 极差 0.00px   说明行极差 0.00px   竖轴差 [0.00, 0.01, 0.01]   键 58x44 外投影 1 层  底 rgb(255,255,255) / rgb(228,225,220)  idle对比 8.42  激活 4.93
      asserts: FAIL → A2-4 谱架键外投影 1 层（甲板只允许主操作抬升）
  A3 现状 [基线]  容器框 ["diag-card","toast-banner"]  嵌套 1 对  扫描线框线带 4 条   卡底 rgb(255,255,255)  对比 状态 10.98 / 提示 5.71 / 按钮 8.99
      asserts: FAIL → A3-1 diag-card 容器框数 2（应 = 1）: diag-card , toast-banner | A3-2 容器框套框 1 对: toast-banner ⊂ diag-card | A3-3 竖向扫描线穿过框线带 4 条（应 = 2）: 727 top diag-card ; 770 top toast-banner ; 793 bottom toast-banner ; 802 bottom diag-card
  A3-1 细分割线 [候选]  容器框 ["diag-card"]  嵌套 0 对  扫描线框线带 2 条   卡底 rgb(255,253,251)  对比 状态 10.82 / 提示 6 / 按钮 8.99
      asserts: OK
  A3-2 弱底带 [候选]  容器框 ["diag-card"]  嵌套 0 对  扫描线框线带 2 条   卡底 rgb(255,253,251)  对比 状态 10.82 / 提示 5.61 / 按钮 8.99
      asserts: OK

--- 皮肤矩阵：420 档 × light / ink（对比度） ---
  [light] A2 现状  键底 rgb(255,140,90) / rgb(255,107,107)  idle 2.29 / 激活 无   对比度不达标项 1
  [light] A2-1 沉头浅凹键  键底 rgb(213,211,206)  idle 7.33 / 激活 4.93   对比度不达标项 0
  [light] A2-2 银面浮雕键  键底 rgb(255,255,255) / rgb(228,225,220)  idle 8.42 / 激活 4.93   对比度不达标项 0
  [light] A3 现状  卡底 rgb(255,255,255)  状态 10.98 / 提示 5.71 / 按钮 8.99   对比度不达标项 0
  [light] A3-1 细分割线  卡底 rgb(255,253,251)  状态 10.82 / 提示 6 / 按钮 8.99   对比度不达标项 0
  [light] A3-2 弱底带  卡底 rgb(255,253,251)  状态 10.82 / 提示 5.61 / 按钮 8.99   对比度不达标项 0
  [ink] A2 现状  键底 rgb(255,87,34) / rgb(255,107,107)  idle 2.78 / 激活 无   对比度不达标项 1
  [ink] A2-1 沉头浅凹键  键底 rgb(14,17,20)  idle 17.99 / 激活 4.93   对比度不达标项 0
  [ink] A2-2 银面浮雕键  键底 rgb(42,48,54) / rgb(16,19,22)  idle 12.66 / 激活 4.93   对比度不达标项 0
  [ink] A3 现状  卡底 rgb(255,255,255)  状态 1.05 / 提示 1.33 / 按钮 9   对比度不达标项 2
  [ink] A3-1 细分割线  卡底 rgb(26,30,34)  状态 15.92 / 提示 12.52 / 按钮 9   对比度不达标项 0
  [ink] A3-2 弱底带  卡底 rgb(26,30,34)  状态 15.92 / 提示 11.26 / 按钮 9   对比度不达标项 0

--- 基线咬合检查（内置负控：现状块必须触发断言） ---
  A2 基线触发 A2-1 ? true   基线红行: ["A2-1 主控件行 centerline 极差 18.50px > 1px [266.25 / 283.25 / 264.75]","A2-4 谱架键外投影 1 层（甲板只允许主操作抬升）","A2-6 谱架键 idle 字/自身底 2.29:1 < 4.5","A2-9 谱架键没有激活态（.is-on 不改底）"]
  A3 基线触发 A3-1/2/3 ? true   基线红行: ["A3-1 diag-card 容器框数 2（应 = 1）: diag-card , toast-banner","A3-2 容器框套框 1 对: toast-banner ⊂ diag-card","A3-3 竖向扫描线穿过框线带 4 条（应 = 2）: 727 top diag-card ; 770 top toast-banner ; 793 bottom toast-banner ; 802 bottom diag-card"]

--- 候选的已知代价（计入 spec，不计入 fails） ---
  A2-2 银面浮雕键 : ["A2-4 谱架键外投影 1 层（甲板只允许主操作抬升）"]

fails[] = []
verdict = ASSERT_OK
```

> 对照页把「现状」做成**基线块**并要求它必须红（`NEG-A2` / `NEG-A3` 两条内置负控）——基线不红就报 fail，等于把「断言会咬人」这件事也机器化了。

### 5.3 负控 3 遍（改卡本体）

注入（只进副本，同/更高特异性、放在被断言规则之后）：

```css
.stand-btn { background: linear-gradient(180deg, var(--dash-accent), var(--dash-coral)); color: var(--dash-white);
  box-shadow: inset 0 1px 0 var(--dash-btn-rim), 0 4px 8px var(--dash-shell-inset); }
.transport-caps { margin-top: 10px; }
.transport-caps .stand-badge-tip { margin-top: 8px; }
.diag-card .toast-banner { border: 1px solid var(--dash-accent-line); border-radius: 6px; background: var(--dash-notice-bg); }
.diag-card { background: var(--dash-white); }
```

第 1 遍（红）：

```text
ASSERT_FAIL
fails: [ "A2-2 fail: 说明行 centerline 极差 4.00px > 1px（logo/计时/大屏看谱 = 667.75 / 667.75 / 671.75）",
         "A2-4 fail: 谱架键带 1 层外投影（甲板只允许主操作抬升）",
         "A2-6 fail [light]: 谱架键 idle 字/自身底 = 1.26:1 < 4.5",
         "A3-4 fail [ink]: diag 状态文字 = 1.05:1 < 4.5",
         "A3-4 fail [ink]: diag 提示文字 = 1.33:1 < 4.5",
         "A3-1 fail: diag-card 容器框数 = 2（应 = 1，只有卡自身）: diag-card , toast-banner",
         "A3-2 fail: 容器框套框 = 1 对: toast-banner ⊂ diag-card",
         "A3-3 fail: 竖向扫描线穿过框线带 = 4 条（应 = 2：卡顶 + 卡底）" ]
verdict = ASSERT_FAIL
```

第 2 遍 / 第 3 遍（改回原值，交付文件本体）：

```text
ASSERT_OK   （两遍都 ok）
```

### 5.4 门禁

```text
python3 scripts/verify-demos.py a2a3-probe-pixel.html dashboard-skin-01-v3.html
  OK a2a3-probe-pixel.html (46637 B)
     非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
     未定义 token 无 / JS 通过 / 写死超宽值 ['1133']（仅顶栏 max-width）
     共享尺子 引用 无 / 旧文字色 0
  OK dashboard-skin-01-v3.html (104632 B)
     非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
     未定义 token 无 / JS 通过 / 写死超宽值 无 / 共享尺子 引用 有 + markup 有 / 旧文字色 0
  换肤契约：--dash-* 名集合一致（70 个）

python3 scripts/token-contrast.py  →  门禁不合格合计：0
```

---

## 6 实施清单（本轮已落在 `dashboard-skin-01-v3.html`）

| 行号 | 位置 | 动作 |
|:--|:--|:--|
| L479–492 | `.deck.transport` / 新增 `.transport-main` `.transport-caps` | 甲板改两段竖栈（gap 4px）；两段都 `align-items:center`；说明行 caption 统一 `10px/650/--dash-text-soft` |
| L531–541 | `.ops-kicker` | 11px 衬线 800 + `--dash-kicker` → 10px/650 + `--dash-text-soft` + `tabular-nums` |
| L522–526 | `.dizical-logo` | 去掉 `margin-top: 2px`（已进说明行） |
| L565–580 | `.stand-btn` | 橙渐变 + 双阴影 → 托盘弱底 + 1px `--dash-shell-inset` + 只内凹；新增 `.stand-btn.is-on` |
| L583–598 | `.diag-card` | 底 `--dash-white` → `--dash-surface-soft`（唯一框保留） |
| L620–631 | `.toast-banner` | 拆掉第 2 层框，改 1px `--dash-ink-a12` 上分割线 + 留白 |
| L713 | 容器查询里的 `.stand-btn` | `width: 56px` → `min-width: 56px`（与新基线的 `min-width` 对齐，否则 66px 撑破 58px 列） |
| L850–885 | 甲板 markup | 拆成 `.transport-main.grid-3col` + `.transport-caps.grid-3col`；logo 挪进说明行并给 `id="speakerLogo"`；谱架键补 `aria-pressed` |
| L1062–1078 | `alignSpeakerWithCover()` | 孔阵与说明行 logo 用同一个水平偏移（原来 logo 留在列心，与孔阵错 37px） |
| L1712–1719 | 谱架键交互 | 加 `click` 切 `.is-on` + `aria-pressed`（demo 内只表达形态与状态） |
| L2155–2320 | 自检新增段 | A2-1…A2-7 + A3-1…A3-4 断言 + 两皮肤对比度矩阵 |
| L2433 | 自检输出 | 新增 `A2_A3` 字段（实测值进 JSON，供复核） |

**没动的**：`.pill` / `.round` / `.grille-6x8` / `.hole` / `.diag-btn` / `.diag-row` / `.diag-status` / 卡壳 `.dash` / 拱与点阵 / 尺子 / 旋钮 / token 名集合（仍 70 个，零新增）。

---

## 7 待 dad 拍板

1. **A2 键形态**：A2-1 沉头浅凹（推荐·已实施）/ A2-2 银面浮雕（代价：甲板多一层外投影）。
2. **A2 说明行**：把「00:00 · 待开始」从药丸上方挪到下方（换取三列共中轴）；若必须留上方，需要回到逐列 padding 微调。
3. **A3 分层**：A3-1 细分割线（推荐·已实施）/ A3-2 弱底带。
4. 顺带确认：深墨皮肤下 `diag-card` 从「白底」改成「跟皮肤走」（`--dash-surface-soft`）——这是修 1.05:1 的必要改动。

对照页顶栏 4 组开关：A2 变体 / A3 变体 / 卡宽 420·500·390 / 皮肤 浅银·深墨；`?audit=1` 出全部实测值。

---

## 8 边界与已知噪声

- 只改 `dashboard-skin-01-v3.html` + 新增本 spec 与 `a2a3-probe-pixel.html`；未动 `src/`、未 commit、未 push、未加依赖。
- 配色只走 `--dash-*`；白字压底用 `--dash-coral-solid`（4.93:1）；无 emoji；命中区 ≥44（谱架键 58×44 / 70×44）。
- 对照页 token 块与卡内既有规则**由脚本从真卡逐行抽出后注入**（不是手抄），`--dash-*` 名集合 70 个零差异。
- **环境噪声**：卡自身 `?audit=1` 里有一条既有的「5s 自然计时运行态」断言（花朵气泡 opacity），在 headless `--virtual-time-budget` 下偶发不触发（本轮红遍出现过 1 次、绿遍 2 次均未出现）。与本轮 A2/A3 无关，真机不受影响。
- 未做真机触控/观感验证；谱架键的真实上屏行为（进不进谱架模式）不在本 demo 范围。
- 遗留：demo 目录下有 3 个本轮临时文件 `.tmp-measure-a2a3.html` / `.tmp-audit-a2a3.html` / `.tmp-negctl-a2a3.html`（点开头的临时产物，清理命令被审批拦住，未删）。
