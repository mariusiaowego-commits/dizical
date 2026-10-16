# spec-pixel-d2-primary-261010 — D2 节拍器卡「主按钮重设计 + 音色胶囊右挂」规格

日期 2026-10-10 · 作者 hermes `pixel` profile · 目标文件 `docs/demos/practice-right-column-261003/metronome-01-v3.html`（实施 = hermes）
对照页（可点）`docs/demos/practice-right-column-261003/d2-primary-probe-pixel.html`
上游 plan：`plan-261010b.md` §A3

---

## 0 一句话结论

主按钮从「5 字 + 200px 宽」压到 **图标 + 2 字 + 128×52**，音色入口从参数区搬成 **104×44 胶囊挂在主按钮右侧**（同一排）；
两件都落在 A 甲板已有的高度阶梯上（52 / 44 / 32 / 24），全甲板**只留 1 层投影**（只在主按钮），命中区全 ≥44px，两皮肤对比度最低 4.89:1。

推荐组合 = **布点 A（同排居中） + 文案档 AB（开始 / 暂停）**。

---

## 1 改前诊断（在 `metronome-01-v3.html` 上实测，不是转述）

| # | 现象 | 实测证据 | 判为「丑」的根因 |
|:--|:--|:--|:--|
| 1 | 主按钮文案太长 | `.primary-toggle-btn` `min-width:200px`，文案 `启动节拍器`/`暂停节拍器` = **5 字**（v3 L747 / L1046 / L1059） | 5 字把按钮撑成一块 200×52 的珊瑚砖；字号 15px 下这 5 字的墨迹宽 ≈ 75px，两侧各留 62px 空底 |
| 2 | 音色入口与主按钮抢层级 | `.timbre-fold`（44px，`--dash-ink-a04`）+ `.btn-preview`（44px，r22 胶囊）自成一行 `.timbre-bar`（v3 L507–543） | 音色行与主按钮**同高 44/52、同为圆角矩形/胶囊**，形态维度只差底色；且「音色」这个参数项占了一整行 |
| 3 | 甲板行数虚高 | `.bottom-ops` 现有 4 行：主按钮行 / 音色行 / 预设行 / 状态行（v3 L739–775） | 行数多 → 每行都要靠底色分，dad 说的「都像圆角矩形、糊成一片」 |

---

## 2 推荐方案（布点 A + 文案档 AB）

### 2.1 主按钮 `.primary-toggle-btn`（改）

| 项 | 值 | 说明 |
|:--|:--|:--|
| 尺寸 | **128 × 52**（`min-width:128px` / `height:52px` / `padding:0 22px` / `gap:8px`） | 52 = A 甲板主级，与 dad 已拍的「沉头圆角矩形 h52 那层」同源；128 由 `图标 18 + gap 8 + 2 字 31 = 57` + 两侧 22px 内边距得出（实测余量 71px，见 §7 ⑥） |
| 圆角 | **14px**（布点 C 用 12px，同心规则 16−4） | 与音色胶囊 999 / 抽屉项 8 / 预设 6 都不同 |
| 图标 | **矢量 SVG 18×18**，`fill:currentColor`，`aria-hidden="true"`；play = 三角形 `polygon 7 4 21 12 7 20`，pause = 两条 `rect 4.5×16 rx1.2` | 沿用 v3 已有图形，只把 16px 提到 18px（2 字后按钮变小，图标要补回存在感）。**不用 emoji**，不用字形 ▶ / ⏸ |
| 文案 | **2 字**：空转 `开始` / 运行 `暂停` | 见 §3 文案档 |
| 字号 | 15px / 800 / `letter-spacing:.5px` | **不动字阶**：15 是 A 甲板已拍的主级字号，本轮改形态不改字号 |
| 空转底色 | `--dash-coral-solid` `#CC3B3B`，字 `--dash-white` | 白字压底 4.93:1（≥4.5） |
| 运行底色 | `--dash-panel`（浅银 `#1C1E21` / 深墨 `#14181C`），字 `--dash-white` | 16.71 / 17.84:1 |
| 投影 | 空转 `0 4px 12px var(--dash-coral-glow)`；hover `0 6px 16px var(--dash-coral-glow)`；运行 `0 2px 8px var(--dash-shell-shadow)` | **每态都是单层**，且全甲板只有这一件有投影 |
| 命中区 | **52px**（无 `::before` 扩展） | ≥44 ✓ |
| 交互 | `:hover` 抬投影；`:active` `transform:scale(.98)`；`white-space:nowrap` | 补 `nowrap`：2 字也不许折行 |

```css
.primary-toggle-btn {
  position: relative; border: 0; cursor: pointer; font-family: inherit;
  display: inline-flex; align-items: center; justify-content: center;
  height: 52px; min-width: 128px; padding: 0 22px; gap: 8px;
  border-radius: 14px; background: var(--dash-coral-solid); color: var(--dash-white);
  white-space: nowrap; font-size: 15px; font-weight: 800; letter-spacing: .5px;
  box-shadow: 0 4px 12px var(--dash-coral-glow);
  transition: background-color 150ms ease-out, box-shadow 150ms ease-out, transform 120ms ease-out;
}
.primary-toggle-btn:hover { box-shadow: 0 6px 16px var(--dash-coral-glow); }
.primary-toggle-btn:active { transform: scale(.98); }
.primary-toggle-btn.running { background: var(--dash-panel); color: var(--dash-white); box-shadow: 0 2px 8px var(--dash-shell-shadow); }
.primary-toggle-btn .tg-icon { display: inline-flex; align-items: center; }
.primary-toggle-btn .tg-pause { display: none; }
.primary-toggle-btn.running .tg-play { display: none; }
.primary-toggle-btn.running .tg-pause { display: inline-flex; }
```

### 2.2 音色胶囊 `.timbre-capsule`（新，取代 `.timbre-fold`）

| 项 | 值 | 说明 |
|:--|:--|:--|
| 尺寸 | **104 × 44**（`min-width:104px` / `height:44px` / `padding:0 14px` / `gap:6px`） | 44 = A 甲板第二级；104 覆盖最长音色名「808 低鼓」「清脆 blip」（实测无省略号、无撑破，见 §7 ⑥/P11） |
| 圆角 | **999px**（胶囊） | 全页**唯一**一个胶囊，只在「音色入口」上；旧的 `试听 h44 r22` 胶囊已退场（见 §5） |
| 内容 | `音色名`（13px / 650，`max-width:96px`，`nowrap`）+ **caret SVG 12×12**（`polyline 6 9 12 15 18 9`，`stroke:currentColor` 2.6px，`aria-hidden`） | caret 只在展开时转 180°，其余态不动 |
| 空转底色 | `--dash-surface-soft`（浅银 `#FFFDFB` / 深墨 `#1A1E22`）+ `1px solid var(--dash-ink-a12)` 描边，字 `--dash-text` | **用不透明底**，不随卡片壳渐变漂移：10.82 / 15.92:1 |
| hover | 底 `--dash-shell-hi`（浅银 `#F3F4F6` / 深墨 `#5C6770`） | 9.98 / 5.49:1；沿用预设 chip 的既有 hover 语言 |
| 展开态 `.open` | 底 `--dash-text`、字 `--dash-page`（**反白**）+ caret 转 180° | 10.43:1 两皮肤都成立；复用抽屉内「音色项·选中」的反白语言 |
| 投影 | **无** | 甲板只留主按钮 1 层投影 |
| 命中区 | **44px** | ✓ |
| 无障碍 | `aria-haspopup="true"` + `aria-expanded` 跟随抽屉 + `aria-label="音色：<当前音色>"` | 可见文案只有 2 字音色名，语义靠 aria 补全 |

```css
.timbre-capsule {
  position: relative; flex: none; cursor: pointer; font-family: inherit;
  display: inline-flex; align-items: center; justify-content: center;
  height: 44px; min-width: 104px; padding: 0 14px; gap: 6px;
  border: 1px solid var(--dash-ink-a12); border-radius: 999px;
  background: var(--dash-surface-soft); color: var(--dash-text);
  font-size: 13px; font-weight: 650; white-space: nowrap;
  transition: background-color 120ms ease-out, color 120ms ease-out, transform 120ms ease-out;
}
.timbre-capsule:hover { background: var(--dash-shell-hi); }
.timbre-capsule:active { transform: translateY(1px); }
.timbre-capsule.open { background: var(--dash-text); color: var(--dash-page); }
.timbre-capsule .tc-name { max-width: 96px; overflow: hidden; text-overflow: ellipsis; }
.timbre-capsule .tc-caret { transition: transform 150ms ease-out; }
.timbre-capsule.open .tc-caret { transform: rotate(180deg); }
```

> **持久态禁用半透明底的规则**（本轮新立的硬约束）：胶囊这类「带字的持久态控件」不许拿 `--dash-ink-a12` 当底。
> 实测：`a12` 压在深墨卡片壳**亮端** `#5C6770` 上 → 字对比度 **4.43:1**（低于 4.5）；压暗端 `#3E474E` 才有 6.80。
> `a12` 只允许出现在 `:hover` / `:active` 这类瞬态选择器里。probe 的 P13 断言机器检查这一条。

### 2.3 展开的抽屉（改：从「音色行 + 抽屉」变成「胶囊 + 抽屉」）

| 项 | 值 |
|:--|:--|
| 位置 | `position:absolute; left:0; right:0; top:calc(100% + 8px)`，挂在 `.deck`（`position:relative`）上 → 铺在**整块甲板外面**，不盖主按钮 / 胶囊 / 预设行 / 状态行（实测相交 0，见 §7 ⑤） |
| 底板 | `--dash-shell-hi` **不透明** + `1px solid var(--dash-ink-a16)`，`border-radius:12px`，`padding:6px`，`gap:6px`，`flex-wrap:wrap` |
| 音色项 | `36px` 高 / `border-radius:8px` / `padding:0 10px` / 12.5px / 650；`::before{inset:-4px 0}` → 命中 **44px**；未选透明底 + `--dash-text`；**选中反白**（底 `--dash-text` / 字 `--dash-page`，10.43:1） |
| 试听 | `44px` 高 / `border-radius:8px` / `padding:0 16px` / `1px solid var(--dash-ink-a16)` / 底 `--dash-surface-2` / 字 `--dash-text`（9.62 / 9.00:1）；命中 44px |
| 关法 | 再点胶囊 / 点抽屉外 / `Esc`（沿用 v3 现有行为） |

---

## 3 文案档（三档都做了可点切换）

| 档 | 空转 / 运行 | 字数 | 按钮宽 | `aria-label` | 评价 |
|:--|:--|:--|:--|:--|:--|
| **AB（推荐）** | `开始` / `暂停` | 2 / 2 | 128px | 开始节拍器 / 暂停节拍器 | 「开始」是孩子嘴里的词，「暂停」是播放器通用对；两字都无歧义 |
| ST | `启动` / `停止` | 2 / 2 | 128px | 启动节拍器 / 停止节拍器 | 同样合规；偏机器语（「启动」多用于设备），且「停止」比「暂停」语义更硬（实际行为是可恢复的暂停） |
| IC | 纯图标 | 0 | 128px（内容仅 18px 图标） | 开始节拍器 / 暂停节拍器 | 最省空间，但儿童用户认三角/双杠要靠猜；**仅当 dad 想更极简时才选**，且必须保留 `aria-label` |

规则：
- 可见文案 **≤2 字**（或 0 字纯图标），超过 2 字机器判失败（P8）。
- `aria-label` 跟随所选档位写全（`开始节拍器` / `暂停节拍器`），并用 `aria-pressed` 表达开合状态。
- 若将来引入「已暂停 → 继续」的第三态，第三态用 `继续`（2 字），仍守 ≤2 字。
- **不用 emoji**：图标一律矢量 SVG（P9 机器扫 emoji 码位）。

---

## 4 三个布点候选（胶囊都在主按钮右侧，差别只在「怎么排」）

| 布点 | 规则 | 实测几何（卡内容宽 386） | 拿到什么 | 代价 |
|:--|:--|:--|:--|:--|
| **A 同排居中（推荐）** | `.deck-row{justify-content:center}`，主按钮 `min-width:128`，胶囊 `flex:none` | 主按钮 128×52，胶囊 104×44，整排 242 宽居中，胶囊右端距卡内边 **73px** | 与上方旋钮 / 灯排 / 状态行**共用同一条中轴**；层级靠尺寸差（52 vs 44）分；改动最小（只是把音色行换成胶囊挪进这一排） | 主按钮不再是甲板里最宽的一件（宽度让给「成对」的构图） |
| B 主条拉伸 + 胶囊右挂 | 主按钮 `flex:1 1 auto`，胶囊 `flex:none` | 主按钮 **272**×52，胶囊 104×44，胶囊右端距卡内边 **1px** | 主按钮变成一条横贯甲板的「启动条」，胶囊像挂在右端的模块；操控感最强 | 2 字文案内容只 57px，**余 215px 全摊成珊瑚空底**；且这一排脱离卡体中轴（旋钮/灯排仍居中），构图断成两截 |
| C 共用凹槽底盘 | `.deck-row{padding:4px; border-radius:16px; background:var(--dash-ink-a04)}`，主按钮 `flex:1 1 auto; border-radius:12px` | 主行高 **60**，主按钮 264×52，胶囊 104×44，胶囊右端距卡内边 5px | 最像收音机面板的「槽内按键」；两件被一层凹槽收成一个整体 | 多一层形态（凹槽 r16 + 主按钮 r12 同心）；甲板高 **+8px**；凹槽只能用底色差表达（不许 inset 投影，否则破「只 1 层投影」） |

三视口（1133 / 744 / 440）**同一套几何**，都不需要重排：卡内容宽三档实测都是 386，A 的整排 242 余量充足（0 横溢 / 0 折行）。

---

## 5 试听的去向（本轮顺带的层级收益）

现状 `试听` 是甲板上一个 `h44 / r22` 的**胶囊**（v3 L535–543），与音色入口同高同形 → 这是「按钮与标签都是圆角矩形」的另一半来源。
本规格把 `试听` 移进**音色抽屉内**（`h44 / r8 / surface-2`，与抽屉里的音色项同族）：它是「音色」这个决定的附属动作，放抽屉里语义也更对。
收益：甲板从 4 行降到 3 行（主行 / 预设行 / 状态行），且**全页只剩一个胶囊**（= 音色入口），胶囊这个形态本身就变成「音色」的识别符。
若 dad 要 `试听` 留在甲板上：备选形态 = 行末一个 44×44 的纯图标方钮（喇叭图形，无文字），但那会破坏「主按钮 + 胶囊」两件成对的构图，故不推荐。

---

## 6 A 甲板阶梯（本轮之后）

| 层 | 件 | 高 | 圆角 | 底 | 字 | 投影 | 命中 |
|:--|:--|:--|:--|:--|:--|:--|:--|
| 主操作 | 主按钮 | **52** | 14（C:12） | `--dash-coral-solid` / 运行 `--dash-panel` | `--dash-white` 15/800 | **1 层** coral-glow / 运行 shell-shadow | 52 |
| 次操作 | 音色胶囊 | **44** | 999 | `--dash-surface-soft` + `ink-a12` 描边 / 展开反白 | `--dash-text` 13/650 | 无 | 44 |
| 参数 | 预设 chip（不动） | **32** | 6 | `--dash-surface-soft` + `ink-a12` 描边 / 选中 `--dash-accent-solid` | `--dash-text-soft` 11.5/700 | 无 | 44（`::before inset:-6px 0`） |
| 状态 | 状态行（不动） | **24** | — | 透明 | `--dash-text` 11/700 | 无 | 24 |
| 抽屉内 | 音色项 | 36 | 8 | 透明 / 选中反白 | `--dash-text` 12.5/650 | 无 | 44（`::before inset:-4px 0`） |
| 抽屉内 | 试听 | 44 | 8 | `--dash-surface-2` + `ink-a16` 描边 | `--dash-text` 13/700 | 无 | 44 |

阶梯四值 `52 / 44 / 32 / 24` 互不相同（P6）；圆角集 `14 / 999 / 8 / 6 / 0` 互不相同（P2/P6）。
**不动**：旋钮、灯排、状态行、预设行、抽屉的不透明底板与关闭行为。

---

## 7 机器可验 + 实测（`d2-primary-probe-pixel.html?audit=1`，headless Chrome 1400×813）

### 7.1 断言清单

| ID | 断言 |
|:--|:--|
| P1 | 主按钮高 = 52（与 A 甲板主级一致） |
| P2 | 主按钮圆角 ∈ {12,14}；胶囊圆角 ≥100（胶囊）；三者与预设 r6 互不相同 |
| P3 | 音色胶囊高 = 44（A 甲板第二级） |
| P4 | 命中区 ≥44：主按钮 / 胶囊 / 预设 chip / 抽屉音色项 / 抽屉试听（含 `::before` 扩展） |
| P5 | 全甲板投影**只 1 层、只落在主按钮**，且该投影值本身是**单层**（逗号拆层） |
| P6 | 高度阶梯 distinct ≥4：`[52,44,32,24]` |
| P7 | 主按钮与胶囊**同排垂直居中**，中心差 ≤1px |
| P8 | 可见文案 ≤2 字；纯图标态 0 字且 `aria-label` 非空 |
| P9 | 主按钮 / 胶囊 文案与 SVG 内**无 emoji 码位** |
| P10 | 三视口 × 三布点：0 折行、0 横向溢出、全部 `nowrap` |
| P11 | 胶囊宽 ≥104 且内容不溢出（覆盖最长音色名） |
| P12 | 对比度 ≥4.5：**全部从真渲染元素取值**（元素色本身来自 `--dash-*`），两皮肤 |
| P13 | 持久态（选择器不含 `:hover/:active/:focus`）**不许把 `--dash-ink-a12` 当底** |
| P14 | 抽屉打开时与主按钮 / 胶囊 / 预设行 / 状态行**相交面积 = 0**，且不横溢 |
| P15 | 布点作用域内 `data-skin="ink"` 覆盖条数 = 0（两皮肤只靠 `:root` token 块翻转） |

### 7.2 断言原始输出（未删节）

```text
=== d2-primary-probe-pixel · ?audit=1 ===
probe: D2 主按钮 + 音色胶囊 布点 A/B/C   窗口: 1400×726
约束: 文案≤2字 / 与A甲板同源 h52 / 胶囊置主按钮右侧 / 只1层投影 / 命中≥44 / 无emoji / 现有 --dash-* token

--- ① 视口扫描（3 视口 × 3 布点：主行宽 / 主按钮宽 / 胶囊宽 / 尾端余量 / 溢出 / 折行）---
  v1133 布点A  卡内容宽 386  主行高 52  主按钮 128×52  胶囊 104×44  胶囊右端距卡内边 73  横溢=false  折行=none
  v1133 布点B  卡内容宽 386  主行高 52  主按钮 272×52  胶囊 104×44  胶囊右端距卡内边 1  横溢=false  折行=none
  v1133 布点C  卡内容宽 386  主行高 60  主按钮 264×52  胶囊 104×44  胶囊右端距卡内边 5  横溢=false  折行=none
  v744 布点A  卡内容宽 386  主行高 52  主按钮 128×52  胶囊 104×44  胶囊右端距卡内边 73  横溢=false  折行=none
  v744 布点B  卡内容宽 386  主行高 52  主按钮 272×52  胶囊 104×44  胶囊右端距卡内边 1  横溢=false  折行=none
  v744 布点C  卡内容宽 386  主行高 60  主按钮 264×52  胶囊 104×44  胶囊右端距卡内边 5  横溢=false  折行=none
  v440 布点A  卡内容宽 386  主行高 52  主按钮 128×52  胶囊 104×44  胶囊右端距卡内边 73  横溢=false  折行=none
  v440 布点B  卡内容宽 386  主行高 52  主按钮 272×52  胶囊 104×44  胶囊右端距卡内边 1  横溢=false  折行=none
  v440 布点C  卡内容宽 386  主行高 60  主按钮 264×52  胶囊 104×44  胶囊右端距卡内边 5  横溢=false  折行=none

--- ② 尺寸 / 形态 / 命中区 / 阶梯（两皮肤 × 3 布点）---
  [light] 布点A  主行高 52  主行底=rgba(0, 0, 0, 0) 主行圆角=0
    主按钮·idle  h=52 命中=52(扩0) w=128 圆角= 14 字=15 bg=rgb(204, 59, 59) color=rgb(255, 255, 255) 投影=1层
    主按钮·run     h=52 bg=rgb(28, 30, 33) 投影=1层 rgba(44, 62, 80, 0.18) 0px 2px 8px 0px
    音色胶囊    h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(255, 253, 251) color=rgb(44, 62, 80) 投影=0层
    胶囊·open   h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(44, 62, 80) color=rgb(255, 248, 240) 投影=0层
    预设chip   h=32 命中=44(扩12) w= 71 圆角=  6 字=11.5 bg=rgb(255, 253, 251) color=rgb(102, 102, 102) 投影=0层
    状态行      h=24 命中=24(扩0) w=386 圆角=  0 字=11 bg=rgba(0, 0, 0, 0) color=rgb(44, 62, 80) 投影=0层
    抽屉音色项  h=36 命中=44(扩8) w= 70 圆角=  8 字=12.5 bg=rgba(0, 0, 0, 0) color=rgb(44, 62, 80) 投影=0层
    抽屉试听    h=44 命中=44(扩0) w= 60 圆角=  8 字=13 bg=rgb(244, 239, 235) color=rgb(44, 62, 80) 投影=0层
    同排中心差 0.0px   高度集 [52,44,32,24]   圆角集 [14,999,8,6,0]   投影层落点 [主按钮×1]
    asserts: P1–P11 all ok
  [light] 布点B  主行高 52  主行底=rgba(0, 0, 0, 0) 主行圆角=0
    主按钮·idle  h=52 命中=52(扩0) w=272 圆角= 14 字=15 bg=rgb(204, 59, 59) color=rgb(255, 255, 255) 投影=1层
    主按钮·run     h=52 bg=rgb(28, 30, 33) 投影=1层 rgba(44, 62, 80, 0.18) 0px 2px 8px 0px
    音色胶囊    h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(255, 253, 251) color=rgb(44, 62, 80) 投影=0层
    胶囊·open   h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(44, 62, 80) color=rgb(255, 248, 240) 投影=0层
    预设chip   h=32 命中=44(扩12) w= 71 圆角=  6 字=11.5 bg=rgb(255, 253, 251) color=rgb(102, 102, 102) 投影=0层
    状态行      h=24 命中=24(扩0) w=386 圆角=  0 字=11 bg=rgba(0, 0, 0, 0) color=rgb(44, 62, 80) 投影=0层
    抽屉音色项  h=36 命中=44(扩8) w= 70 圆角=  8 字=12.5 bg=rgba(0, 0, 0, 0) color=rgb(44, 62, 80) 投影=0层
    抽屉试听    h=44 命中=44(扩0) w= 60 圆角=  8 字=13 bg=rgb(244, 239, 235) color=rgb(44, 62, 80) 投影=0层
    同排中心差 0.0px   高度集 [52,44,32,24]   圆角集 [14,999,8,6,0]   投影层落点 [主按钮×1]
    asserts: P1–P11 all ok
  [light] 布点C  主行高 60  主行底=rgba(44, 62, 80, 0.04) 主行圆角=16
    主按钮·idle  h=52 命中=52(扩0) w=264 圆角= 12 字=15 bg=rgb(204, 59, 59) color=rgb(255, 255, 255) 投影=1层
    主按钮·run     h=52 bg=rgb(28, 30, 33) 投影=1层 rgba(44, 62, 80, 0.18) 0px 2px 8px 0px
    音色胶囊    h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(255, 253, 251) color=rgb(44, 62, 80) 投影=0层
    胶囊·open   h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(44, 62, 80) color=rgb(255, 248, 240) 投影=0层
    预设chip   h=32 命中=44(扩12) w= 71 圆角=  6 字=11.5 bg=rgb(255, 253, 251) color=rgb(102, 102, 102) 投影=0层
    状态行      h=24 命中=24(扩0) w=386 圆角=  0 字=11 bg=rgba(0, 0, 0, 0) color=rgb(44, 62, 80) 投影=0层
    抽屉音色项  h=36 命中=44(扩8) w= 70 圆角=  8 字=12.5 bg=rgba(0, 0, 0, 0) color=rgb(44, 62, 80) 投影=0层
    抽屉试听    h=44 命中=44(扩0) w= 60 圆角=  8 字=13 bg=rgb(244, 239, 235) color=rgb(44, 62, 80) 投影=0层
    同排中心差 0.0px   高度集 [52,44,32,24]   圆角集 [12,999,8,6,0]   投影层落点 [主按钮×1]
    asserts: P1–P11 all ok
  [ink] 布点A  主行高 52  主行底=rgba(0, 0, 0, 0) 主行圆角=0
    主按钮·idle  h=52 命中=52(扩0) w=128 圆角= 14 字=15 bg=rgb(204, 59, 59) color=rgb(255, 255, 255) 投影=1层
    主按钮·run     h=52 bg=rgb(20, 24, 28) 投影=1层 rgba(44, 62, 80, 0.35) 0px 2px 8px 0px
    音色胶囊    h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(26, 30, 34) color=rgb(255, 248, 240) 投影=0层
    胶囊·open   h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(255, 248, 240) color=rgb(44, 62, 80) 投影=0层
    预设chip   h=32 命中=44(扩12) w= 71 圆角=  6 字=11.5 bg=rgb(26, 30, 34) color=rgba(255, 248, 240, 0.68) 投影=0层
    状态行      h=24 命中=24(扩0) w=386 圆角=  0 字=11 bg=rgba(0, 0, 0, 0) color=rgb(255, 248, 240) 投影=0层
    抽屉音色项  h=36 命中=44(扩8) w= 70 圆角=  8 字=12.5 bg=rgba(0, 0, 0, 0) color=rgb(255, 248, 240) 投影=0层
    抽屉试听    h=44 命中=44(扩0) w= 60 圆角=  8 字=13 bg=rgb(62, 71, 78) color=rgb(255, 248, 240) 投影=0层
    同排中心差 0.0px   高度集 [52,44,32,24]   圆角集 [14,999,8,6,0]   投影层落点 [主按钮×1]
    asserts: P1–P11 all ok
  [ink] 布点B  主行高 52  主行底=rgba(0, 0, 0, 0) 主行圆角=0
    主按钮·idle  h=52 命中=52(扩0) w=272 圆角= 14 字=15 bg=rgb(204, 59, 59) color=rgb(255, 255, 255) 投影=1层
    主按钮·run     h=52 bg=rgb(20, 24, 28) 投影=1层 rgba(44, 62, 80, 0.35) 0px 2px 8px 0px
    音色胶囊    h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(26, 30, 34) color=rgb(255, 248, 240) 投影=0层
    胶囊·open   h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(255, 248, 240) color=rgb(44, 62, 80) 投影=0层
    预设chip   h=32 命中=44(扩12) w= 71 圆角=  6 字=11.5 bg=rgb(26, 30, 34) color=rgba(255, 248, 240, 0.68) 投影=0层
    状态行      h=24 命中=24(扩0) w=386 圆角=  0 字=11 bg=rgba(0, 0, 0, 0) color=rgb(255, 248, 240) 投影=0层
    抽屉音色项  h=36 命中=44(扩8) w= 70 圆角=  8 字=12.5 bg=rgba(0, 0, 0, 0) color=rgb(255, 248, 240) 投影=0层
    抽屉试听    h=44 命中=44(扩0) w= 60 圆角=  8 字=13 bg=rgb(62, 71, 78) color=rgb(255, 248, 240) 投影=0层
    同排中心差 0.0px   高度集 [52,44,32,24]   圆角集 [14,999,8,6,0]   投影层落点 [主按钮×1]
    asserts: P1–P11 all ok
  [ink] 布点C  主行高 60  主行底=rgba(255, 248, 240, 0.04) 主行圆角=16
    主按钮·idle  h=52 命中=52(扩0) w=264 圆角= 12 字=15 bg=rgb(204, 59, 59) color=rgb(255, 255, 255) 投影=1层
    主按钮·run     h=52 bg=rgb(20, 24, 28) 投影=1层 rgba(44, 62, 80, 0.35) 0px 2px 8px 0px
    音色胶囊    h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(26, 30, 34) color=rgb(255, 248, 240) 投影=0层
    胶囊·open   h=44 命中=44(扩0) w=104 圆角=999 字=13 bg=rgb(255, 248, 240) color=rgb(44, 62, 80) 投影=0层
    预设chip   h=32 命中=44(扩12) w= 71 圆角=  6 字=11.5 bg=rgb(26, 30, 34) color=rgba(255, 248, 240, 0.68) 投影=0层
    状态行      h=24 命中=24(扩0) w=386 圆角=  0 字=11 bg=rgba(0, 0, 0, 0) color=rgb(255, 248, 240) 投影=0层
    抽屉音色项  h=36 命中=44(扩8) w= 70 圆角=  8 字=12.5 bg=rgba(0, 0, 0, 0) color=rgb(255, 248, 240) 投影=0层
    抽屉试听    h=44 命中=44(扩0) w= 60 圆角=  8 字=13 bg=rgb(62, 71, 78) color=rgb(255, 248, 240) 投影=0层
    同排中心差 0.0px   高度集 [52,44,32,24]   圆角集 [12,999,8,6,0]   投影层落点 [主按钮×1]
    asserts: P1–P11 all ok

--- ③ 状态（主按钮两态 + 胶囊三态；hover 从 CSS 声明解析，JS 触发不了 :hover）---
  [light] 主按钮 idle  bg=rgb(204, 59, 59)  投影=1层  rgba(255, 107, 107, 0.45) 0px 4px 12px 0px
  [light] 主按钮 run   bg=rgb(28, 30, 33)  投影=1层  rgba(44, 62, 80, 0.18) 0px 2px 8px 0px
  [light] 胶囊   idle  bg=rgb(255, 253, 251)  color=rgb(44, 62, 80)  投影=0层  描边=rgba(44, 62, 80, 0.12)
  [light] 胶囊   hover 声明 var(--dash-shell-hi) → bg=#F3F4F6
  [light] 胶囊   open  bg=rgb(44, 62, 80)  color=rgb(255, 248, 240)（声明 var(--dash-page)）  caret 旋转 180°
  [light] P13 持久态把 --dash-ink-a12 当底色的条数 = 0（a12 只允许出现在 :hover / :active）
  [ink] 主按钮 idle  bg=rgb(204, 59, 59)  投影=1层  rgba(255, 107, 107, 0.45) 0px 4px 12px 0px
  [ink] 主按钮 run   bg=rgb(20, 24, 28)  投影=1层  rgba(44, 62, 80, 0.35) 0px 2px 8px 0px
  [ink] 胶囊   idle  bg=rgb(26, 30, 34)  color=rgb(255, 248, 240)  投影=0层  描边=rgba(255, 248, 240, 0.1)
  [ink] 胶囊   hover 声明 var(--dash-shell-hi) → bg=#5C6770
  [ink] 胶囊   open  bg=rgb(255, 248, 240)  color=rgb(44, 62, 80)（声明 var(--dash-page)）  caret 旋转 180°
  [ink] P13 持久态把 --dash-ink-a12 当底色的条数 = 0（a12 只允许出现在 :hover / :active）

--- ④ 对比度（WCAG 自算，阈值 4.5:1；token 由页面自身 getComputedStyle 解析）---
  [light]  主按钮 idle 字/自身底=4.93  |  主按钮 running 字/自身底=16.71  |  胶囊 idle 字/自身底⨯壳亮端=10.82  |  胶囊 idle 字/自身底⨯壳暗端=10.82  |  胶囊 hover 字/声明底⨯壳亮端=9.98  |  胶囊 hover 字/声明底⨯壳暗端=9.98  |  胶囊 open 字/自身底=10.43  |  抽屉底板 字/plate 底=9.98  |  抽屉音色项·选中 字/自身底=10.43  |  抽屉试听 字/自身底=9.62  |  预设·选中 字/自身底=4.89  |  预设·未选 字/自身底⨯壳亮端=5.66  |  预设·未选 字/自身底⨯壳暗端=5.66  |  状态行 字/壳亮端=9.98  |  状态行 字/壳暗端=7.69
  [light]  min = 4.89:1
  [ink]  主按钮 idle 字/自身底=4.93  |  主按钮 running 字/自身底=17.84  |  胶囊 idle 字/自身底⨯壳亮端=15.92  |  胶囊 idle 字/自身底⨯壳暗端=15.92  |  胶囊 hover 字/声明底⨯壳亮端=5.49  |  胶囊 hover 字/声明底⨯壳暗端=5.49  |  胶囊 open 字/自身底=10.43  |  抽屉底板 字/plate 底=5.49  |  抽屉音色项·选中 字/自身底=10.43  |  抽屉试听 字/自身底=9.00  |  预设·选中 字/自身底=4.89  |  预设·未选 字/自身底⨯壳亮端=15.92  |  预设·未选 字/自身底⨯壳暗端=15.92  |  状态行 字/壳亮端=5.49  |  状态行 字/壳暗端=9.00
  [ink]  min = 4.89:1

--- ⑤ 抽屉打开：与主按钮/胶囊/预设行 相交面积 = 0、卡片增高、不横溢 ---
  布点A  抽屉盒 386×100  相交 主按钮=0 胶囊=0 预设行=0 状态行=0  卡片高 606→606（+0）  横溢=false  抽屉底板 rgb(243, 244, 246)
  布点B  抽屉盒 386×100  相交 主按钮=0 胶囊=0 预设行=0 状态行=0  卡片高 606→606（+0）  横溢=false  抽屉底板 rgb(243, 244, 246)
  布点C  抽屉盒 386×100  相交 主按钮=0 胶囊=0 预设行=0 状态行=0  卡片高 631→631（+0）  横溢=false  抽屉底板 rgb(243, 244, 246)

--- ⑥ 文案档：可见字数 / 按钮宽 / aria-label（≤2 字，纯图标 0 字）---
  档AB 布点A  可见 "开始" 2 字  按钮 128×52  内容 图标 18 + 字 31 = 57px（余 71px 摊在两侧内边距）  aria-label "开始节拍器"
  档AB 布点B  可见 "开始" 2 字  按钮 272×52  内容 图标 18 + 字 31 = 57px（余 215px 摊在两侧内边距）  aria-label "开始节拍器"
  档AB 布点C  可见 "开始" 2 字  按钮 264×52  内容 图标 18 + 字 31 = 57px（余 207px 摊在两侧内边距）  aria-label "开始节拍器"
  档ST 布点A  可见 "启动" 2 字  按钮 128×52  内容 图标 18 + 字 31 = 57px（余 71px 摊在两侧内边距）  aria-label "启动节拍器"
  档ST 布点B  可见 "启动" 2 字  按钮 272×52  内容 图标 18 + 字 31 = 57px（余 215px 摊在两侧内边距）  aria-label "启动节拍器"
  档ST 布点C  可见 "启动" 2 字  按钮 264×52  内容 图标 18 + 字 31 = 57px（余 207px 摊在两侧内边距）  aria-label "启动节拍器"
  档IC 布点A  可见 "" 0 字  按钮 128×52  内容 图标 18 + 字 0 = 18px（余 110px 摊在两侧内边距）  aria-label "开始节拍器"
  档IC 布点B  可见 "" 0 字  按钮 272×52  内容 图标 18 + 字 0 = 18px（余 254px 摊在两侧内边距）  aria-label "开始节拍器"
  档IC 布点C  可见 "" 0 字  按钮 264×52  内容 图标 18 + 字 0 = 18px（余 246px 摊在两侧内边距）  aria-label "开始节拍器"

--- ⑦ 零皮肤专属覆盖 / 无 emoji ---
  布点作用域内 data-skin="ink" 覆盖条数 = 0（仅 :root token 块翻转，合规）
  主按钮/胶囊 内含 emoji 的元素数 = 0

fails[] = []
verdict = ASSERT_OK
```

### 7.3 负控（证明断言会咬人，3 遍）

副本注入（只在副本上，不进交付文件）：

```css
.timbre-capsule { height: 30px; background: var(--dash-ink-a12); }
.deck[data-v="A"] .primary-toggle-btn { min-width: 200px; box-shadow: 0 4px 12px var(--dash-coral-glow), 0 1px 0 rgba(255, 255, 255, 0.2); }
.deck[data-v="A"] .preset-chip { height: 46px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.30); }
```

第 1 遍（红，节选；两端原文都在行里）：

```text
asserts: FAIL → P3  h_capsule 30 !== 44 | P4  hit 胶囊 30 | P5  投影层落点 [主按钮,预设chip] | P5  主按钮 idle 投影 2 层 rgba(255, 107, 107, 0.45) 0px 4px 12px 0px, rgba(255, 255, 255, 0.2) 0px 1px 0px 0px | P5  主按钮 running 投影 2 层 rgba(255, 107, 107, 0.45) 0px 4px 12px 0px, rgba(255, 255, 255, 0.2) 0px 1px 0px 0px
fails[] = ["[light][A] P3  h_capsule 30 !== 44","[light][A] P4  hit 胶囊 30","[light][A] P5  投影层落点 [主按钮,预设chip]","[light][A] P5  主按钮 idle 投影 2 层 rgba(255, 107, 107, 0.45) 0px 4px 12px 0px, rgba(255, 255, 255, 0.2) 0px 1px 0px 0px","[light][A] P5  主按钮 running 投影 2 层 rgba(255, 107, 107, 0.45) 0px 4px 12px 0px, rgba(255, 255, 255, 0.2) 0px 1px 0px 0px","[light][B] P3  h_capsule 30 !== 44","[light][B] P4  hit 胶囊 30","[light][C] P3  h_capsule 30 !== 44","[light][C] P4  hit 胶囊 30","[ink][A] P3  h_capsule 30 !== 44","[ink][A] P4  hit 胶囊 30","[ink][A] P5  投影层落点 [主按钮,预设chip]","[ink][A] P5  主按钮 idle 投影 2 层 rgba(255, 107, 107, 0.45) 0px 4px 12px 0px, rgba(255, 255, 255, 0.2) 0px 1px 0px 0px","[ink][A] P5  主按钮 running 投影 2 层 rgba(255, 107, 107, 0.45) 0px 4px 12px 0px, rgba(255, 255, 255, 0.2) 0px 1px 0px 0px","[ink][B] P3  h_capsule 30 !== 44","[ink][B] P4  hit 胶囊 30","[ink][C] P3  h_capsule 30 !== 44","[ink][C] P4  hit 胶囊 30","P13 [light] 持久态拿 a12 当底: .timbre-capsule → var(--dash-ink-a12)","P13 [ink] 持久态拿 a12 当底: .timbre-capsule → var(--dash-ink-a12)","P12 [ink] 胶囊 idle 字/自身底⨯壳亮端 = 4.43:1"]
verdict = ASSERT_FAIL
```

第 2 遍 / 第 3 遍（改回原值，交付文件本体）：

```text
fails[] = []
verdict = ASSERT_OK
```

注：注入的 `a12` 底在**浅银**皮肤下不报错（8.15:1），只在**深墨**壳亮端报 4.43:1 —— 这正是 §2.2 那条「持久态禁用 a12 底」的由来。

### 7.4 门禁

```text
python3 scripts/verify-demos.py d2-primary-probe-pixel.html metronome-01-v3.html
  OK d2-primary-probe-pixel.html (57583 B)
     非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
     未定义 token 无 / JS 通过 / 写死超宽值 ['1133'] / 共享尺子 无 / 旧文字色 0
  OK metronome-01-v3.html
  换肤契约：--dash-* 名集合一致（70 个）

python3 scripts/token-contrast.py  →  门禁不合格合计：0
```

---

## 8 实施清单（hermes，只改 `metronome-01-v3.html`）

| 位置 | 动作 |
|:--|:--|
| L507–514（`.timbre-bar` / `.timbre-fold`） | 删 `.timbre-bar`、`.timbre-fold`；新增 `.deck-row` 与 `.timbre-capsule`（§2.2 的 CSS） |
| L516–519（`.timbre-drawer`） | 保留绝对定位 + `top:calc(100% + 8px)`，容器改成 `.deck`（`.deck{position:relative}`）；底板换 `.timbre-plate`（§2.3） |
| L520–534（`.timbre-seg`） | 去掉内层 `--dash-ink-a04` 槽底（改透明，压在不透明 plate 上）；项 36/8、`::before inset:-4px 0`、选中反白不变 |
| L535–543（`.btn-preview`） | 圆角 22 → **8**，其余（44 高 / surface-2 底 / ink-a16 描边）保留；从甲板移进抽屉 |
| L545–546（`.bottom-ops` / `.bo-params`） | `.bottom-ops{position:relative}`；`.bo-params` 只留 `.preset-row`（音色行撤掉） |
| L548–567（`.primary-toggle-btn`） | 按 §2.1 换：`min-width 200→128`、`padding 0 24→0 22`、补 `white-space:nowrap`；`.running` 与图标切换逻辑保留 |
| L569–582（`.preset-row` / `.preset-chip`） | **不动** |
| L739–775（甲板 markup） | 改成 `.deck > [.deck-row(主按钮 + 胶囊 + 抽屉) , .preset-row , .bottom-status]`；主按钮图标 16→18px；文案 span 改 2 字；胶囊加 `aria-haspopup/aria-expanded/aria-label`；抽屉里加「音色项 ×5 + 试听」 |
| L976–1002（`applyTimbre`） | `timbreFoldName` → 胶囊内的音色名节点；同时更新胶囊 `aria-label` |
| L1029–1063（`toggleMetronome`） | L1046 `'暂停节拍器'` → `'暂停'`，L1059 `'启动节拍器'` → `'开始'`；同时写 `aria-label`（`暂停节拍器` / `开始节拍器`）与 `aria-pressed` |
| L1381–1390 / L1823–1844（抽屉开合与 Esc/外点） | 触发器 `timbreFold` → 胶囊；行为不变 |
| 自检块（L1397–1416 的 measure 清单 / L1509–1534 / L1636–1660） | 选择器更新：`.timbre-fold` → `.timbre-capsule`、`.timbre-seg` 槽底断言按新结构改；新增 P1–P15（照 §7.1 抄） |

**门禁口径不变**：`--dash-*` 名集合保持 70 个（本轮不新增 token，全部复用现有）；非中性色字面量 0；`transition:all` 0；深墨皮肤活体。

---

## 9 被否掉的选项（附实测/理由）

| 选项 | 否掉的理由 |
|:--|:--|
| 胶囊底用 `--dash-ink-a12`（现音色轨 hover 语言） | 深墨壳亮端 **4.43:1**（<4.5），且随卡片渐变漂移；改用不透明 `--dash-surface-soft`（15.92:1，且不漂移） |
| 保留 5 字文案 | 5 字墨迹 ≈75px + 200px 最小宽 → 与胶囊同排后 440 档拥挤，且空底占比更大 |
| 音色胶囊放参数区（现状位置） | dad 明确要求「胶囊置于主按钮右侧」；且留在参数区就仍与主按钮分属两行，层级照旧糊 |
| 胶囊 h52（与主按钮同高） | 同高 → 层级只剩颜色一个维度；且 A 甲板第二级本来就是 44，h52 会凭空多一级 |
| 布点 C 的凹槽加 inset 投影 | 会变成第 2 层投影，破「只 1 层投影」；凹槽只能用底色差表达 |

---

## 10 待 dad 拍板

1. **布点**：A 同排居中（推荐）/ B 主条拉伸 + 胶囊右挂 / C 共用凹槽底盘。
2. **文案档**：AB `开始·暂停`（推荐）/ ST `启动·停止` / IC 纯图标。
3. **试听去向**：进抽屉（推荐）/ 留甲板右端（44×44 纯图标方钮）。

三个问题都能在对照页上直接点出来看（顶栏 5 组 pill：布点 / 文案 / 状态 / 视口 / 皮肤）。

---

## 11 边界

- 只写两个新文件（本 spec + `d2-primary-probe-pixel.html`）；`metronome-01-v3.html`、`metronome-01-v4.html`、`compose-02.html` **一字未改**。
- 未 commit / 未 push / 未加依赖 / 未碰 `src/`。
- probe 页 token 块由脚本从 `metronome-01-v3.html` **逐行抽出**后注入（不是手抄），`--dash-*` 名集合 70 个零差异，已过 `verify-demos.py` 契约检查。
- probe 零外链（无 gsap、无 CDN）；`?audit=1` 自带自检；`?v=A|B|C · ?copy=AB|ST|IC · ?run=1 · ?skin=ink · ?vp=1133|744|440`。
- 未做真机听感 / 真机触控验证（demo 无音频设备），听感归 dad。
