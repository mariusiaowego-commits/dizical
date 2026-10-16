# spec-pixel-d2-bottom-261009 — D2 节拍器卡「底部操作区」重设计规格

> 作者：hermes `pixel`。依据 `brief-pixel-d2-261009.md`。
> 只做设计，不碰实现文件（`metronome-01-v3.html` / `-v4.html` / `compose-02.html` 一字未改）。
> 号码来源：`metronome-01-v3.html`（自读核实，非转述）、`token-spec.md`、`card-contract.md`。

---

## 0 根因（1 句 + 可核对证据）

**根因：底部 5 类控件全落在同一条样式带上——「白底 / 胶囊或 8px 圆角 / 32–44px 两档高 / 只有选中态换填色」——
层级只由颜色承担，形态本身零区分，于是 presets 与上方音色轨在「底色 + 高度 + 三角圆角」上无法区分。**

自读 `metronome-01-v3.html` 实测值（行号为据）：

| 控件 | 位置 | 高 | 圆角 | 底色 | 描边 | 阴影 |
|------|------|----|------|------|------|------|
| `.primary-toggle-btn` | 502–535 | `min-height:44` | `999px` | `--dash-coral-solid` | 无 | `0 2px 8px --dash-coral-glow` |
| `.timbre-seg` | 476–479 | 32+6=38 | `999px` | `--dash-white` | 无 | 无 |
| `.timbre-seg button` | 480–485 | `min-height:32` | `999px` | `transparent` | 无 | 无 |
| `.btn-preview` | 488–493 | `min-height:32` | `999px` | `--dash-white` | `1px --dash-ink-a16` | 无 |
| `.preset-chip` | 542–570 | `min-height:44` | `8px` | `--dash-white` | `1px --dash-shell-inset` | 无 |
| `.metro-card` 卡体 | 212–226 | — | `28px` | shell 渐变 | `1px --dash-shell-inset` | 3 层（glint/inset/drop） |

读表结论：**3 个胶囊（主按钮 / 音色轨 / 试听）+ 1 个白块（预设）**，高度只有 32 / 44 两档。
dad 说「按钮和标签 bar 都是圆角矩形没有作出区分」「preset 和上面很像」——**准确，不是错觉**：
preset 与音色轨的差别只有 `8px vs 999px` 圆角，底色同为 `--dash-white`，高度同为 44。
`bottom-ops` 现有 `gap:10px`，与卡体 `gap:14px` 差 4px，分组也读不出来。

---

## 1 四层权重（从上到下，权重 = 面积 × 底饱和 × 投影 × 描边）

```
① 主操作      启动/停止        唯一「实心品牌色 + 唯一投影 + 唯一大圆角」→ 一眼锁定
② 次级操作    试听             与音色轨同高，实心中性弱底 + 描边，无投影 → 是「按钮」但不是主角
③ 参数选择    音色 / 预设      无底或弱底、无投影、最小圆角 → 是「参数」不是「按钮」
                 · 选中态永远高于同族未选态
④ 状态标签    当前 BPM/调式/音色摘要   纯文字，无底无框无投影 → 只读信息
```

**权重排序（显式）：① > ② > ③选中 > ③未选 > ④。**
判据：同一屏里，`主按钮净视觉面积 ≥ 次级 ≈ 参数轨`，而「带投影的层只有 1 个」= ①。
②③ 的分野不靠高度（同高 44/48），靠**填充**：② 是实心弱底（`--dash-surface-2` + 1px 描边），
③ 是**凹槽/底线**（无自身高度感）。

> 命中区硬约束（brief #6）与 dad「preset 太高」的冲突解法：
> **视觉高 ≠ 命中区**。所有 < 44px 的控件用 `::before { position:absolute; inset:-Npx 0 }` 把命中区抬到 44px，
> 视觉高度按层级阶梯走。命中区 = `offsetHeight + |top| + |bottom|`（可被 `getComputedStyle(el,'::before')` 读出并断言）。

---

## 2 形态区分表（推荐 = 变体 A「甲板分级」）

单位 px。`命中区` 列：`—` = 自身已 ≥44，无需扩展。

| 控件 | 层 | 视觉高 | 命中区 | 圆角 | 底色 | 文字色 | 字重/字号 | 阴影 | 描边 | 块边距 |
|------|----|--------|--------|------|------|--------|-----------|------|------|--------|
| `.primary-toggle-btn` | ① 主操作 | **52** | 52 | **14** | `--dash-coral-solid` 实心；`.running` → `--dash-panel` | `--dash-white` | 800 / 15 | `0 4px 12px --dash-coral-glow`（**全页唯一投影**） | 无 | 下 14 |
| `.btn-preview`（试听） | ② 次级操作 | **44** | 44 | **22**（半高胶囊） | `--dash-surface-2` 实心弱底 | `--dash-text` | 700 / 13 | none | `1px --dash-ink-a16` | 左 10 |
| `.timbre-seg`（音色轨） | ③ 参数-槽 | **44** | — | **12** | `--dash-ink-a04`（凹槽，半透明，非实心） | — | — | none | 无（靠底色差，不靠框） | 轨内 pad 4 |
| `.timbre-seg button` 未选 | ③ 参数 | **36** | **44**（`inset:-4px 0`） | **8** | `transparent` | `--dash-text` | 650 / 12.5 | none | 无 | 项间 2 |
| `.timbre-seg button.is-on` | ③ 参数-选中 | 36 | 44 | 8 | `--dash-text` 实心（= 墨块） | `--dash-page` | 700 / 12.5 | none | 无 | — |
| `.preset-row` | ③ 参数群 | 32 | — | — | 透明 | — | — | none | 无 | 项间 8 |
| `.preset-chip` 未选 | ③ 参数 | **32** | **44**（`inset:-6px 0`） | **6** | `--dash-surface-soft` | `--dash-text-soft` | 700 / 11.5 | none | `1px --dash-ink-a12` | — |
| `.preset-chip.active` | ③ 参数-选中 | 32 | 44 | 6 | `--dash-accent-solid` 实心 | `--dash-white` | 700 / 11.5 | none | `1px --dash-accent` | — |
| `.bottom-status`（状态标签） | ④ 状态 | **24**（行） | — | **0** | 无底 | `--dash-text` | 700 / 11，`letter-spacing:.06em` | none | 无（**不用分隔墨线**） | 上 12 |

### 2.1 维度互异计数（≥3 项要求 → 实得 6 项）

| 维度 | A 变体的取值集合 | 互异数 |
|------|------------------|--------|
| 视觉高 | 52 / 44 / 36 / 32 / 24 | **5** |
| 圆角 | 22 / 14 / 12 / 8 / 6 / 0 | **6** |
| 底色类型 | 品牌实心 / 中性实心弱底 / 半透明凹槽 / 词牌弱底 / 无底 | **5** |
| 投影 | 仅 ① 有，其余 4 类 `none` | **2** |
| 连接方式 | 凹槽连线（音色）/ 独立 chip（预设）/ 单行文字（状态） | **3** |
| 文字阶梯 | 15 / 13 / 12.5 / 11.5 / 11 | **5** |

---

## 3 尺寸阶梯（4px 网格，禁止挤在 40–48）

**A（推荐）**：`13U / 11U / 9U / 8U / 6U` = `52 / 44 / 36 / 32 / 24`（U = 4px）
`主 ÷ 预设 = 52 ÷ 32 = 1.625`；相邻档差 8 / 8 / 4 / 8，无同档相邻。

**B**：`14U / 12U / 10U / 9U / 7U` = `56 / 48 / 40 / 36 / 28`（主 ÷ 预设 = 1.556）
**C**：`12U / 11U / 9U / 8U / 5.5U` = `48 / 44 / 36 / 32 / 22`（主 ÷ 预设 = 1.50）

字号阶梯（A）：`15 / 13 / 12.5 / 11.5 / 11`，步长 2 / 0.5 / 1 / 0.5 —— 与高度阶梯同序、不同步长，
**禁止把字号也压成两档**（现状只有 12 / 13 两档，是「没有层级」的另一半原因）。

---

## 4 底色与阴影分配

| 分配 | 谁 | 规则 |
|------|----|------|
| 实心**品牌**底 | ① 主操作（`--dash-coral-solid`）、③ 预设选中（`--dash-accent-solid`） | 只给「按下会改变全局状态」的控件 |
| 实心**中性**底 | ② 次级操作（`--dash-surface-2`）、③ 音色选中（`--dash-text` 墨块） | 给「局部生效」的控件 |
| 半透明**凹槽**底 | ③ 音色轨（`--dash-ink-a04`） | 只 1 处，用来把「一组选项」框成一个槽，不是按钮 |
| 弱底 | ③ 预设未选（`--dash-surface-soft`） | 预设是「可换的档位」，给最小可辨认底 |
| 纯文字（无底） | ④ 状态标签 | 只读信息，永不参与交互，因此永不给底/框/投影 |
| **投影** | **只有 ①** | 「不许每层都投影」= 4 层里只有 1 层有 `box-shadow`，其余 computed 必须 `none` |

深墨（`data-skin="ink"`）验证：`--dash-ink-a04` → `rgba(255,248,240,.04)`、`--dash-ink-a12` → `.10`、
`--dash-ink-a16` → `.14`、`--dash-surface-soft` → `#1A1E22`、`--dash-accent-solid` / `--dash-coral-solid` 两肤同值
→ 上表**零皮肤专属覆盖**即可成立（v3 现存的 `:root[data-skin="ink"] .timbre-seg button { color: var(--dash-page) }` 可删）。
唯一例外：`--dash-surface-2` 深墨 = `#3E474E`，② 的弱点底在深墨下变成亮底，故 ② 文字色必须用 `--dash-text`
（深墨 = `#FFF8F0`），不得写死 `--dash-page`。

---

## 5 preset 区（dad 点名的重灾区）

1. **项高**：`44 → 32`（A）。命中区仍 44（`::before inset:-6px 0`），触控不降级。
2. **与上方主体的区分靠 4 个手段（不是 1 个）**：
   - 高度差：`32` vs 上方音色项 `36`、音色轨 `44`、主按钮 `52` → 最矮一档；
   - 底色差：`--dash-surface-soft`（弱底词牌）vs 音色轨 `--dash-ink-a04`（凹槽）vs 卡体 shell 渐变 → 3 种底；
   - 结构差：预设是**独立 chip（项间 8px）**，音色是**同一槽内的连线段（项间 2px）** → 一眼看出「一个是格子，一个是轨道」；
   - 高度感差：预设**无投影无内阴影**，卡体有 `inset glint + drop shadow` → 预设是「贴在板面上的纸片」，不与卡体争高低。
3. **选中态表达**：`--dash-accent-solid` 实心 + `--dash-white` 文字（对比 4.89:1）+ `1px --dash-accent` 描边。
   **不加投影、不加发光**（发光是 ① 的专属，避免选中态抢主按钮）。
4. **文字内容建议**（**需 dad 确认，属语义改动**）：chip 只留名称（`慢板 / 中板 / 萨丽哈★ / 小快板 / 双吐`），
   把 BPM 数值移到 ④ 状态标签（`当前 82 BPM · 萨丽哈 · 木鱼`）。
   依据：dad 既定 UI 偏好「按钮只放名字，ID 放选中摘要；选中后收拢」；副产品是 440 视口下 5 项不必缩字号。
   变体 C 不采纳这条，保留「82 萨丽哈★」双信息，供对照。

---

## 6 间距与分组

```
.bottom-ops  gap:14          簇间（① ↔ ③，③ ↔ ④）
.bo-params   gap:10          音色行 ↔ 预设行（组内）
.timbre-bar  gap:10          音色轨 ↔ 试听（同排，两种角色）
.timbre-seg  gap:2, pad:4    同一槽内的段（连续感）
.preset-row  gap:8           独立 chip（离散感）
.bottom-status 上 12         与预设行留白分开，不画线
```

**分组依据 = 角色，不是视觉相似**：① 一个簇（主操作）；③ 两个组但同一簇（参数）；
④ 一个簇（状态）。三簇之间 14px，簇内 ≤10px，且**簇内用底色差、簇间用留白差**——
现在 `bottom-ops` 全用 10px，所以 reading 上是「一坨」。

命中区扩展后的净空余量（防重叠，实测可查）：预设 chip 上下各外扩 6px，与预设行上/下相邻块余量 = 10−6 = 4px、12−6 = 6px，均 > 0。

---

## 7 三视口重排规则（数值全部为 probe `?audit=1` 实测值，可复核）

**不变量：三视口下卡内容宽恒为 386px。**
（1133 / 744：卡 `max-width:420` 含 2×1px 描边 → `clientWidth 418`；440：卡 `100%` → 416 含描边 → `clientWidth 414`，
卡内边距 16→14。两者减去 padding 都得 386。）
→ 结论：**断点在卡宽，不在视口**，所以三档重排规则一致；440 的唯一差别是卡不再有左右留白（`body` 侧距 12→0）与字号降一档。

| 视口 | 卡 `clientWidth` | 内容宽 | 主按钮 | 音色行（实测行数） | 预设行（实测项宽） | 状态行 |
|------|------------------|--------|--------|--------------------|--------------------|--------|
| 1133×744 | 418 | 386 | `min-width:200`，居中，不随视口变高 | A/B = **2 行**（音色轨一行、试听换行）；C = 1 行 | 5 等分一行，每项 **71px** | 一行 |
| 744×1133 | 418 | 386 | 同上 | 同上 | 同上 | 同上 |
| 440×956 | 414 | 386 | 同上（不缩高） | 同 1133（同宽 ⇒ 同行数） | 5 等分一行，每项 **71px** | 一行 |

预设 chip 净宽算式（实测 71px 对齐）：`(386 − 4×8) / 5 = 70.8 ≈ 71` → 减 `padding 0 6px` → 可用 **59px**。
最长标签「萨丽哈★」@11.5px（A）/ 12px（B）≈ 46 / 48px ✓ 余量 ≥11px；
变体 C 保留「82 萨丽哈★」@10.5px ≈ 55px，C 的 chip 用 `padding:0 4px` → 可用 63px ✓ 余量 8px。

**A/B 的音色行在三个视口都是 2 行**（轨 ≈318 + gap 10 + 试听 60 = 388 > 386）：这不是缺陷，是设计的一部分——
「试听」独占第二行，视觉上把它从音色参数里摘出来，正好服务 §1 的 ②/③ 分野。C 因字号小一档（12 vs 12.5/13）刚好 1 行。

**440 不做的事**：不缩主按钮高度（48 / 52 / 56 由变体定，不随视口变）；不把音色改成横向滚动
（`card-contract.md` 要求卡内不横滑，probe 实测 9 格 `横溢=false`）；不用 `transform: scale()` 假装适配。

---

## 8 状态与动效（每类都要有 5 态）

| 态 | 主操作 ① | 次级 ② | 音色项 ③ | 预设 chip ③ | 状态标签 ④ |
|----|----------|--------|-----------|--------------|-------------|
| default | coral 实心 + 投影 | `--dash-surface-2` + 描边 | 透明 + `--dash-text` | `--dash-surface-soft` + `--dash-text-soft` | `--dash-text` |
| hover | `box-shadow: 0 6px 16px --dash-coral-glow` | `background:--dash-ink-a04` | `background:--dash-ink-a04` | `background:--dash-shell-hi` | 无（不可交互） |
| active | `transform: scale(.98)` | `transform: translateY(1px)` | `translateY(1px)` | `translateY(1px)` | — |
| selected | `.running` → `--dash-panel` 底 + `--dash-white` 字（投影换 `--dash-shell-shadow`） | — | `--dash-text` 实心 + `--dash-page` 字 | `--dash-accent-solid` + `--dash-white` | — |
| focus-visible | 全部统一 `outline: 2px solid --dash-accent-text; outline-offset: 2px`（沿用 v3:620） | | | | — |
| disabled | `opacity:.45; cursor:not-allowed; pointer-events:none` | 同 | 同 | 同 | — |

动效：`transition: background-color 120ms ease-out, color 120ms ease-out, border-color 120ms ease-out`（① 用 150ms）；
**禁 `transition: all`**。主按钮 `▶/⏸` 图标沿用 v3 矢量字形（内联 SVG）。
`prefers-reduced-motion` 沿用 v3:625 的全局降级块。

---

## 9 机器可验清单（与 `d2-bottom-probe-pixel.html?audit=1` 断言 ID 一一对应）

| ID | 断言 | 判据 |
|----|------|------|
| A1 | `h_preset ≤ h_main × 0.8` | 44 → 32 ≤ 41.6 ✓（A/B/C 各自成立） |
| A2 | `h_preset < h_timbreItem` | 32 < 36 ✓ |
| A3 | `h_main ∈ [44, 64]` 且 `h_main` 为最大值 | 52 = max ✓ |
| A4 | 高度阶梯互异数 ≥ 4 | {52,44,36,32,24} → 5 ✓ |
| A5 | 圆角互异数 ≥ 3 | {22,14,12,8,6,0} → 6 ✓ |
| A6 | `radius_main ≠ radius_item ≠ radius_preset` | 14 ≠ 8 ≠ 6 ✓ |
| A7 | **投影唯一**：`box-shadow !== 'none'` 的控件数 == 1，且是主按钮 | 5 类控件里只有 ① ✓ |
| A8 | 底色类型互异数 ≥ 3（按 resolved 值去重） | 5 ✓ |
| A9 | 命中区：`h_main / h_preview / h_timbreItem / h_preset ≥ 44` | 52/44/44/44 ✓ |
| A10 | `h_preset ≥ 28`（不许为了矮而不可点） | 32 ✓ |
| A11 | 同排项高极差 = 0：预设 5 项、音色 5 项 `max−min === 0` | 0 ✓ |
| A12 | 无折行：每个 chip `scrollWidth ≤ clientWidth + 1`（`white-space:nowrap`） | ✓ |
| A13 | 无溢出：`card.scrollWidth ≤ card.clientWidth + 1`，三视口 × 3 变体全过 | ✓ |
| A14 | 对比度 ≥ 4.5：主按钮白字/`--dash-coral-solid`、预设选中白字/`--dash-accent-solid`、状态字/卡体亮端 `--dash-shell-hi`、音色未选字/凹槽合色、预设未选字/`--dash-surface-soft`（**两套皮肤各算一遍**） | 见 audit 原始输出 |
| A15 | 分组：`gap(簇间) > gap(组内)` → `14 > 10` ✓ | ✓ |
| A16 | 零皮肤专属色覆盖：A 变体下 `data-skin="ink"` 生效前后，`--dash-*` 命中集合不变 | ✓ |

**只有 A1 / A2 / A7 / A9 / A11 / A12 能真正咬人**（其余是护栏）；负控做法：把 `h_preset` 改回 44 → A1/A2 必红，
把投影加到 preset → A7 必红，去掉 `::before` → A9 必红。

---

## 10 变体 B / C（对照用，同一套硬约束）

| | A「甲板分级」（**推荐**） | B「刻度队形」 | C「紧凑分级」 |
|---|---|---|---|
| 主张 | 主按钮沉头圆角矩形，音色是凹槽轨，预设是纸片 chip | 全用项目刻度/沉头语言，圆角收到 2–8，预设靠「底线刻度」区分 | 主按钮只此一个胶囊，音色回深色收音机槽，预设回白块 |
| 高阶梯 | 52 / 44 / 36 / 32 / 24 | 56 / 48 / 40 / 36 / 28 | 48 / 44 / 36 / 32 / 22 |
| 圆角 | 22 / 14 / 12 / 8 / 6 / 0 | 24 / 8 / 4 / 2 / 6 / 0 | 999 / 22 / 10 / 6 / 4 / 0 |
| 音色轨底 | `--dash-ink-a04` 凹槽 | `--dash-white` + `1px --dash-shell-inset`（硬边槽） | `--dash-pill-track` 深槽（收音机语言） |
| 音色选中 | `--dash-text` 墨块 | `--dash-coral-solid` 珊瑚实心 + 白字 | `--dash-coral-solid` 珊瑚实心 + 白字 |
| 预设未选 | `--dash-surface-soft` + 描边 | 无底，只 `2px` 底线 `--dash-ink-a25` | `--dash-white` + `1px --dash-shell-inset` |
| 预设选中 | `--dash-accent-solid` 实心 | 底线 `--dash-accent-solid` + `--dash-accent-wash` 底 + `--dash-accent-text` 字 | `--dash-accent-solid` 实心 |
| 预设文字 | 名称 only | 名称 only | **「82 萨丽哈★」双信息**（现状语义） |
| 状态标签 | 纯文字 | 文字 + 8px `--dash-coral` 圆环锚 | 文字 + 2px `--dash-coral` 左刻度 tick |
| 取舍 | 层级最清、最像「面板上的三层甲板」；改动量中等 | 最贴项目几何语言；但底线刻度在深墨下发灰，需靠 `--dash-ink-a25`→`.22` 维持可见 | 改动最小（音色回深槽）；但主按钮成为唯一胶囊，与 will-be 生产页其它胶囊可能撞 |

三变体都满足 §9 全部断言（A1–A16），产出 `ASSERT_OK`（原始输出见 brief 的「pixel 交付」节）。

---

## 11 落地提示（给实现方，不属本次交付）

1. 只改 `metronome-01-v3.html` 的 `.bottom-ops` 段（502–570 行）与 `bottom-ops` markup（721–751 行）+ 新增 `.bottom-status` markup。
2. 现有 `:root[data-skin="ink"] .timbre-seg button { color: var(--dash-page) }`（487 行）按 §4 可删。
3. 新 token：**0 个**。全部走已存在 `--dash-*`（含 2026-10-09 新增的 `--dash-coral-solid` / `--dash-accent-solid`）。
4. 状态标签的值由现有 JS 已有变量拼（`currentBpm` / `TERM` / `currentTimbre` / `accentEnabled`），无需新状态。
5. 若采纳 §5.4 的文案搬移，`setBpm()` 与 `paintTimbre()` 各加一行写 `#bottomStatus`。
