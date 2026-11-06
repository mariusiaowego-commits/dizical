# practice-dsh 设计规范（练习助手 · 拟物仪表盘）

> 版本：v3.25 · 2026-11-06 · 对应代码 `src/kid_app/templates/practice-dsh.html`（25035 行，单文件）
> 上一版合并提交：`8da6ffe`（PR #392，v3.24）· 本版在 `practice-frontend` 分支，待合并
> 镜像：`/Users/mt16/dev/uiux-asset-library/design-system/practice-dsh/`

## 0. 这份文档是什么

`practice-dsh` 是 dizical kid-app 里「练习助手」标签页的完整前端实现 —— 一个**拟物仪表盘 + 展票**界面：左侧是练习票夹（选科目 / 练习内容 / 速度 / 时长），右侧是仪表盘与可组合的卡片横排。

本文是它的**产品层设计规范**：布局系统、token、组件、动效、交互契约、多视口验收清单。
品牌层（珊瑚红 / 朱橙 / 苹方 / 圆角 / 间距）以 `dizicute` 为准，见 `DESIGN.md`（仓根）与 `uiux-asset-library/design-system/dizicute/DESIGN.md`。

**权威顺序**：本文件 > 代码现状 > 旧 demo。若代码与本文件冲突，说明代码跑偏了，改代码。
本文所有行号对应 `8da6ffe`；改动模板后请同步更新行号与 `DSH_VERSION`。

---

## 1. 设计理念

1. **拟物但克制**：仪表盘是深色面板 + 凹拱 + 金属旋钮 + 玻璃读数；但只有两个强调色（珊瑚 `#FF6B6B` = 人的关系，朱橙 `#FF5722` = 能量度量），不堆装饰。
2. **票 → 槽 → 仪表**：练习选择是一条叙事线。票夹（准备态）→ 黑色窄条 bar（已选）→ 卡片插入仪表盘的卡槽（计时态）。三者必须始终同源，绝不允许各显示各的。
3. **一张画布两种排布**：横排（右展，多卡并排，看全局）↔ 纵向 feed（单列长卡，看细节）。同一批卡片在两种排布下都要可读，**任何卡片在 feed 下都不许锁死高度**。
4. **一屏优先**：桌面横屏一屏放下；放不下时靠缩放（`scale`）而不是靠裁切。
5. **深浅双皮肤**：整套 practice 页全局切换，不只在「练习助手」标签里。

---

## 2. 代码地图

| 区域 | 位置 | 说明 |
|---|---|---|
| 宿主页 | `practice-dsh.html:287–346` | `#czBar` 调试条 / `#czStage > iframe#czCanvas` / `#czHint` / `template#tpl-canvas` |
| 画布（真 UI） | `practice-dsh.html:349–8473` | 顶栏、舞台、票夹、黑条、弹窗、抽屉；`loadCanvas()` 写入 iframe srcdoc（`:19679`） |
| 卡模板 | `tpl-A` 仪表盘 `:8475–12098` / `tpl-B` 节拍器卡 `:12099–14517` / `tpl-S` 竖条节拍器 `:14518–15486` / `tpl-D` 今日时长 `:15487–16590` / `tpl-R` 今日记录 `:16591–17347` / `tpl-Q` 老师要求 `:17348–19026` | 全部内联在同文件，不是独立文件 |
| 宿主脚本 | `:19028–25001` | 组合、布局、缩放、联动、审计自检 |
| 状态记忆 | 运行时主键常量 `STORE_KEY`（`:19043`）；顶层初始化另有对字面量 `dizical_practice_dsh_state` 的向后兼容读取（`:11`）；皮肤另存 `dizical_skin`（`:23199`） | 组合 / 视口 / 皮肤；`?audit=1` 不写用户上次选择（`:21551`） |

关键函数（宿主侧）：`applyCanvasViewport()` `:23148`、`syncCanvasHeight()` `:23036`、`applyLayoutMode()` `:22752`、`canvasIsFeed()` `:22619`、`setCombo()` `:21538`、`buildCombo()` `:20091`、`morphTicketToBar()` `:7123`、`expandBarToFolio()` `:7303`、`wireBuildBadge()` `:23818`。

> 折叠方向的函数实名是 **`morphTicketToBar`**（票夹→黑条）—— 代码里没有 `collapseFolioToBar` 这个函数；文档、注释、提交信息都按实名写，别再造一个不存在的名字。

---

## 3. 布局系统

### 3.1 DOM 骨架

```
body（宿主页）
├ #czBar.cz-bar[hidden]        组合 / 视口 / 皮肤 调试条
├ #czStage.cz-stage
│  └ iframe#czCanvas            srcdoc = template#tpl-canvas
└ #czHint.cz-hint

画布文档（iframe 内）
#practiceStage.stage-prep | .stage-bar | .stage-running
├ header#pkTop.pk-top                       高 44px
├ main#stageWrap.pk-stage-wrap              flex, gap 24px, max-width 1280px
│ ├ aside#pkLeftCol.pk-left-col             宽 380px（1024–1199 → 360px）
│ │ ├ article#pkTicketCard.pk-ticket        票夹展开态
│ │ └ aside#pkRunRail.pk-run-rail           计时黑条
│ └ div#pkMainCol.pk-main-col               flex:1 1 0%, gap 14px
│   └ #czCombo.cz-combo / .cz-rail          卡片轨道（横排或 feed）
└ .cz-pagedots                              分页点（宽屏 --dots-h: 21px）
```

### 3.2 两种排布

| | 横排右展 `cz-expand` | 纵向 feed `cz-feed` |
|---|---|---|
| 触发 | 轨道 `flex-direction: row`（画布 ≥1024px） | `flex-direction: column`（<1024px，`:19655`） |
| 舞台 | `flex-direction: row` | `flex-direction: column`，gap 收到 8px（`:19890`） |
| 卡片宽 | 固定（COMBO_SCHEMA） | `display: contents` + `order` 排序：A1 B2 S3 D4 R5 Q6；T 拆成 D7 / R8（`:19887–19911`） |
| 缩放 | `k = min(1, kW, kH)` | `k = min(1, kW)`，**不压高度**，允许滚动 |
| 票夹 | 左侧竖列 380px | 顶部横条，高 52px（`:19899`） |

判定读的是 `getComputedStyle().flexDirection`，**不是像素宽** —— 手机是把 1133 画布等比缩进去，`clientWidth` 仍可能 ≥1024（`canvasIsFeed()` `:22622`）。

### 3.3 视口三档（嵌入练习页时）

`applyCanvasViewport()` `:23146`：

| 可用宽 | 设计宽 | 落档 |
|---|---|---|
| > 1133 | 可用宽（1728/1920/2560 撑满） | 横排 |
| ≥ 793 | 1133（793 = 1133×0.7，仍可读，保住横排） | 横排 |
| 520–792 | 744 | feed |
| < 520 | 440 | feed |

卡内视口字符串 `1133x744` / `744x1133` / `440x956`；窄屏堆叠时 `applyModuleState` `:22832` 按卡宽再降档（≥1023→1133，≥560 或 vp=744→744，否则 440）。

### 3.4 缩放算法（最容易改坏的地方）

`syncCanvasHeight()` `:23020`：

- 只在「嵌入 + 宿主高 > 240」时缩放；独立打开时清 transform，高度按内容自然底，下限 420px。
- `kW = #czStage.clientWidth / iframe.dataset.vpApplied`。**必须用宿主宽**，用 iframe 自身宽会得到 `kW=1` 并裁掉右边（`:23049`）。
- 高度基准 `canvasFitBaseH`：同一 `fitKey = round(hostW)@round(hostH)@round(designW)` 下取见过的**最大自然高**（准备态）。
  换档时 `canvasFitBaseH = 0` 重置（`:23012`）。
  这是「点开始后整页突然放大」的根因防线：计时态黑条变矮，若基准跟着变矮，`kH` 变大 → 整页被放大。**基准必须锁在准备态**。
- `k < 0.9999` 才写 `transform: scale(k)`，`transform-origin: top left`；舞台高 `round(nat*k)`，水平 `marginLeft` 居中。

### 3.5 断点一览（画布 CSS `:801–1469`）

| 条件 | 改什么 |
|---|---|
| `max-width:1199px and min-width:1024px` | 顶栏/舞台 `max-width:100%`，gap 16px，票夹 360px |
| `min-width:1024px and max-height:800px` | body `padding:3px 6px`，顶栏高 38px，舞台 gap 12px |
| `min-width:1200px and min-height:850px` | 一屏锁定：`html,body` 100vh + `overflow-y:hidden`，舞台高 `calc(100vh - 68px - var(--dots-h))` |
| `min-width:1200px and min-height:1000px` | hero 338px，大数字 64px |
| `max-width:1023px` | 单列，顶栏 `margin:0 auto 10px`，舞台 gap 16px |
| `max-width:480px` | 顶栏 `flex-wrap`，`.pk-grow` 换行，`.pk-run-stat` 隐藏，`.pk-ver` 9px，`.pk-pill` 11px |
| `max-height:590px` | 折叠区切到「今日」单行 |
| `prefers-reduced-motion: reduce` | 动画/过渡压到 `0.01ms` |

---

## 4. Token

### 4.1 颜色（两套皮肤）

浅色（默认，**通过去掉 `data-skin` 表达，不是 `data-skin="light"`**）：

| Token | 值 | 用途 |
|---|---|---|
| `--dash-page` | `#FFF8F0` | 页面底（暖白） |
| `--dash-white` | `#FFFFFF` | 卡片面 |
| `--dash-panel` | `#1C1E21` | 仪表盘黑面板 |
| `--dash-panel-text` | `#F7F4EF` | 面板文字 |
| `--dash-text` / `--dash-text-soft` | `#2C3E50` / `#666666` | 正文 / 次级 |
| `--dash-coral` / `--dash-coral-solid` | `#FF6B6B` / `#CC3B3B` | 珊瑚：品牌与行动 |
| `--dash-vermilion` / `--dash-vermilion-solid` | `#FF5722` / `#B8531F` | 朱橙：能量度量 |

深墨 `data-skin="ink"`（`:114–195`）：页面 `#1C2127`、卡面 `#232931`、面板 `#14181C`、文字 `#DED7CD`、次级 `#A8A29A`；阴影从蓝灰改纯黑，票面高光从白 0.9 降到 0.08（`:469–476`）。

**不变**：珊瑚 / 朱橙两套皮肤共用；深墨下选中 pill 用珊瑚底 + 页底色字。

### 4.2 圆角

票卡 18 / 黑条竖 22（横 14，计时态横条 16）/ 面板 24 / 仪表盘外壳 24 / 节拍器卡 28 / 竖条节拍器 22 / 今日时长卡 42 / 老师要求机身 28、叠卡 20 / 抽屉 `18px 0 0 18px` / pill 一律 9999px。

### 4.3 间距

舞台 gap：24（宽）→ 16（中）→ 12（矮）→ 10（≤480）。黑条与下方卡片 `margin-bottom: 4px`。仪表盘 foot 左右内缩 12px。卡槽上抬 `--cz-card-rise` 默认 20px。

内边距：票卡 `12px 14px 14px`（≤480 `10px 10px 12px`）；面板 `10px 14px 6px`；仪表盘壳 `14px 16px`；今日时长卡 `26px 24px 22px`；换曲目盒 `22px 24px`；结束确认盒 `20px 20px 16px`；引导卡 `10px 12px`。

### 4.4 字体

- 正文：`-apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei"`，14px / 行高 1.5
- 衬线 `--font-serif`：`"Songti SC", "STSong", Georgia, "Times New Roman"` —— 票面铭文 12/600、科目名 26/700/1.2、黑条竖排内容 11/700
- 等宽 `--font-mono`：`ui-monospace, SFMono-Regular, Menlo` —— 票面大数字 30/700、黑条剩余 13/800、BPM 18/800
- **所有数字必须同时具备** mono 家族 + `tabular-nums`（票面大数字、仪表盘 `.clock`、BPM、节拍器 bpm）
- 例外：结束弹窗时长 `.pk-finish-dur-val`（`:4292`）**没有显式写 mono 家族**，靠继承 + `tabular-nums` 等宽排布；要彻底收敛到 mono 需另开重构，别在这条规则下假装它已经统一
- 上下标不是 `<sup>`：D 卡主时钟 SVG 高 68px、秒 SVG 高 30px + `margin-top:4px`，顶对齐；仪表盘「分钟」用 `.readout-unit`，字号 `calc(var(--readout-digits-h,60px)/2)`，与数字 `align-items:flex-end`

### 4.5 动效时长

| Token | 值 | 用途 |
|---|---|---|
| `--s6-enter-ticket-dur` | 0.28s | 票夹入场 |
| `--s6-enter-slot-delay` | 0.78s | 插卡延迟（票夹变形结束后再插） |
| `--s6-enter-slot-dur` | 0.7s | 插卡时长 |
| `--s6-exit-slot-dur` | 0.26s | 退卡 |
| `--s6-exit-ticket-delay` | 0.18s | 退票夹延迟 |
| `--s6-exit-ticket-dur` | 0.28s | 退票夹时长 |

缓动：`cubic-bezier(0.16,1,0.3,1)`（插卡、抽屉）、`cubic-bezier(.55,0,.86,.35)`（退卡）、`cubic-bezier(0.2,0.8,0.2,1)`（knob）、`cubic-bezier(0.23,1,0.32,1)`（弹出）、`cubic-bezier(.16,.84,.24,1)`（引导卡）。

---

## 5. 组件规范

### 5.1 票夹（准备态）`article.pk-ticket` `:4786`

展开态：左栏 380px（1024–1199 → 360px），票卡圆角 18px，`min-height: 520px`。
结构：抬头行 / 打孔 / 票面主图 / 科目块（标题 26px + 副 11px）/ 大数字网格（mono 30/700）/ 齿孔线 / 本次内容槽 + 标签 pill 组。

**依赖契约**：科目、练习内容（session）、速度、时长四项都选齐，票夹才允许变形。缺哪一项，「开始」时按 **科目 > 练习内容 > BPM > 时长** 的优先级只提醒一项（`missingField()` `:21610`）。

### 5.2 黑色窄条 bar（已选 / 计时）`aside.pk-run-rail` `:5061`

- 桌面：左栏收到 **50px 宽 × 票夹原高**，黑条竖排（科目竖排 11/700、剩余 13/800、BPM 18/800、今日 11、进度条、重新选择按钮）。
- 窄屏（≤1023）：改成**顶部横条，高 52px，圆角 14px**。
- 「重新选择」按钮：计时期间置灰不可点；点击后 bar 变回票夹，**保留最近一次选择**。
- 票夹不再固定在左侧，随页面一起滚。

### 5.3 仪表盘 A `article.dash` `:9453`

外壳宽 `min(100%,420px)`，圆角 24px，内边距 `14px 16px`，gap 8px。
内部：`section.panel`（深面板，圆角 24px，内边距 `10px 14px 6px`，底部 mask 凹拱半径 85px / 深 24px，`data-depth="32"` 变 32px）。
子元素：卡槽（画布层 `.cz-punch-slot`，卡片外壳 `.cz-mod` 圆角 24px）、`knob` 144px + rotor + mark、`arc > i` 6px 点（20 点档 4.5px）、`ruler-wrap / ruler / ruler-vine / vine-flower`、± 钮 58px、`mic-status-btn`、`battery / bat / bat-fill / bat-pct`、读数 SVG 60px（feed 66px）+ `.readout-unit`「分钟」。

**只保留 mic 指示灯**；时间与电池元素已删除（2026-10 决定）。

### 5.4 卡槽与插卡

卡槽是仪表盘的组件 —— 仪表盘隐藏时卡槽必须一起隐藏。
卡片从卡槽穿出的效果 = 卡槽分上下两层，上半在下、卡在中间、下半在最上；卡片比孔槽略窄，插入后盖住上半，并在下缘被下半遮罩遮住。
插卡动画 `pkCardToSlot` / `pkCardToSlotFeed` `:2656`：`translate(-50%,-44px)` → 30% opacity .72 → 72% 归位 → 85% `translate(-50%,-2px)` → 100% 归位，时长 `--s6-enter-slot-dur`（0.7s）、缓动 `cubic-bezier(0.16,1,0.3,1)`、**delay `--s6-enter-slot-delay`（0.78s，必须等票夹变形结束）**。
退卡 `pkCardFromSlot` `:2712`：`0.20s cubic-bezier(.55,0,.86,.35)`；feed 版位移用 `var(--cz-feed-travel, 90px)`。

### 5.5 节拍器

- S 竖条 `.strip` 140×468 圆角 22px；feed 档变横条 92px 高 / 圆角 20px。子：`name`、`leds .led` 14px、`nudge` ± 36px、`.bpm` 48/800、`unit`、`go`。
- B 卡 `.metro-card` 圆角 28px 内边距 `14px 16px 12px`。子：`m-sig-badge`、`led-row .led-bulb` 18px、`m-accent-toggle`、`rotary-knob` **168px**、`dial-outer-ring` 220px、`step-btn` 44px、`bpm-hero-val` 42/900、`primary-toggle-btn`、`timbre-capsule`、`preset-chip`。
- 长按 ± 必须**加速但能停**：按住自动加速连续加减，松开立即停；长按要抑制浏览器右键菜单（`contextmenu` preventDefault）。
- 节拍器音色：多音色胶囊（自然生态鼓点 + Nikko 风格），默认音量要响。

### 5.6 老师要求卡 Q `.req-card-chassis` `:18215`

宽随视口 1133→600 / 744→440 / 440→408。子：`m-title`、`m-meta-chip`（stage / date / latest）、`m-counter-badge`（历史张数 `1/2`）、`req-deck-stage`（`.deck-card` 圆角 20px）、`deck-dots`、`deck-btn`。

排版规则（2026-11 定案）：
- 只用**两套字号**：标题 17px/800，正文 / 日期 / 分段 / 要点 14px/500。不要大小混排，不要彩色底块。（例外：计数徽标 `--counter-sz` 13px、落款 `--sig-sz` 12px `:17439`，属装饰性元信息，不算正文级）
- 标题与正文要有明确间距；标题左上角不许被圆角裁掉；`1/2` 这类计数不许换行把标题顶上去。
- 卡片高度要吃满：feed 档可以长卡纵向发展，不锁高。
- 底部「下一张」按钮在深色下不许被遮盖（padding-bottom 要留够）。
- 内容取数：按 **stage** 聚合，从最近到最远，每张卡展示一次老师要求；占位文案禁止写「李老师」之类。

### 5.7 今日时长 D / 今日记录 R / 合并卡 T

- D `.card-wrap` 圆角 **42px**，内边距 `26px 24px 22px`，默认宽 380。子：`date-row`、`clock-display`、`pill-duration`、`timeline-rail-capsule` 高 51px、`recent-subject`。
- R 独立模板 `tpl-R`。
- T 不是独立模板：D+R 去外框拼进一个壳，宽 360；feed 档壳 `display:contents`，D / R 各成一行。
- 配色：R 的底色与 D 保持一致（浅色主题也必须有浅色版），不另造红绿。

### 5.8 弹层

| 弹层 | 遮罩 | 盒 |
|---|---|---|
| 换曲目 `.pk-folio-box` | `rgba(44,62,80,.45)` | `min(540px,92vw)` × `min(620px,85vh)`，圆角 20px，内边距 `22px 24px` |
| 提前结束 `.pk-finish-box` | 38% + `blur(3px)` | `min(420px,100%)`，圆角 22px，内边距 `20px 20px 16px`，时长 40px tabular |
| 全文阅读 `.pk-reader` | — | `min(860px,94vw)`，圆角 20px，内边距 `28px 32px` |
| 右抽屉 `.pk-drawer` | `opacity .28s ease` | 宽 `min(340px,100vw)`，圆角 `18px 0 0 18px`，`transform .28s cubic-bezier(0.16,1,0.3,1)` |
| 引导 `.cz-guide` | 无（spotlight 描边） | 238px，圆角 15px，内边距 `10px 12px`；`.cz-guide-spot` 2px 朱橙描边 + `czGuidePulse` 1.9s |

**浅色 + 深色两套弹窗 UI 都要有**，不能只有黑色。

### 5.9 Pills

`.pk-pill` 圆角 9999px / `padding 6px 14px` / 高 ≥36px / 13px；`.mini` 高 28 / 字 11.5px；`.mini.busy` `opacity .55; pointer-events:none`。
实例：`#pkStateToggle`「切到练习态」、`#pkRelayoutBtn`「刷新布局」、`#pkRecords`「今日记录 — ▾」。
卡片组��切换 `.cz-seg / .cz-btn`（`data-combo` off/1–5）；皮肤切换 `[data-skin]`。

**定案文案不许改**：`检票 · 开始练习`、`收回槽内 ✕`、`展开卡片 ▾`、`重新选择`、`提前结束`、`切到练习态`、`刷新布局`。

### 5.10 版本角标（2026-11 新增）

顶栏最右 `#pkVerWrap > button#pkVer + #pkVerPop`：平时只显示 `v3.25`（10px / opacity .5 / tabular-nums）；悬停或点一下弹出 5 行构建信息（版本 / 分支 / 提交 / 构建时间 / 来源 checkout）。
- **按设备能力分流**：`hover:hover` 设备走 mouseenter/mouseleave（160ms 延时收起），点击不再 toggle；触屏只认点击 —— 触屏 tap 会合成 mouseenter 再 click，共用一个开关会「先开再关」＝永远打不开。
- 弹层必须按画布宽度夹取（窄屏顶栏换行时 `right:0` 会跑出屏幕）。
- 数据来自 `/static/build-info.json`（部署打包时落盘，镜像无 `.git`）；版本常量唯一手改点 `DSH_VERSION` `:19071`。

---

## 6. 动效时序（准备 → 计时 → 结束）

### 6.1 票夹 ⇄ 黑条（GSAP，`morphTicketToBar` `:7123` / `expandBarToFolio` `:7303`）

变形期间 `stage-morphing` 禁 CSS transition（`:2374`）。

> **delay 口径**：下表的 delay 是 **GSAP timeline 内的绝对插入位置（秒）**，不是相对前一段的累加。改动画按绝对位置填，别把相对 delay 串起来（会越串越长）。

| 方向 | 动作 | 时长 / 缓动 | delay |
|---|---|---|---|
| 票夹→黑条 | 左栏宽 → 50px | 0.28s `power3.inOut` | 0 |
| | 票卡 opacity 1→0 + scale 1→0.96 | 0.26s `power2.in` | 0 |
| | 黑条 opacity 0→1 | 0.26s `power2.out` | 0 |
| | `prep-only` opacity 0 / y −4 | 0.14s `power2.in` | 0 |
| 黑条→票夹 | 左栏宽/高复原 | 0.34s `power3.inOut` | 0.05s |
| | 票卡淡入 | 0.30s `power1.out` | 0.06s |
| | 黑条淡出 | 0.26s `power1.inOut` | **0.22s**（先让票卡出来） |
| | `prep-only` 回归 | 0.26s `power2.out` | 0.14s |

**动画不许露出穿帮**：回弹期间卡片下缘不得从卡槽下半露出来。

### 6.2 启动时序（硬规则）

1. 票夹选中四项 → 触发「变形为黑色窄条 bar」（不再等点开始）。
2. 点开始 → **黑条变形动画先执行**，计时同时开始。
3. 黑条变形结束 → 卡片插入卡槽。实现口径是 `--s6-enter-slot-delay`（**0.78s**）+ `--s6-enter-slot-dur`（**0.7s**），缓动 `cubic-bezier(0.16,1,0.3,1)`；需求原话是「变形结束后延迟约 0.5s、比原动画慢 30%」，落到代码就是这组 token —— **改时序改 token，不要把 0.5s / 30% 写死进 CSS**。
4. 计时态展开卡片 = 卡片从卡槽里出来，不是蒙层直接弹全屏。

### 6.3 仪表盘内部

- knob 旋转 `transform .2s cubic-bezier(0.2,0.8,0.2,1)`，拖动中 `transition:none`。
- 弧点同曲线 .24s，点亮 `scale(1.15)`。
- 花（ruler 藤蔓）无 keyframes，用 GSAP 按 `data-sp` 播一次：berry `back.out(2)` stagger 0.06/0.04 共 0.35s；`elastic.out(1,0.6)` 0.45s；`scaleY 0→1` `power3.out` 0.4s；`rotation −90→0` `back.out(2)` 0.5s。刻度 clip `width .35s power2.out`。
- 节拍器 B 旋钮 `transform .05s linear`；LED 余晖 `background .04s ease-out, box-shadow .32s cubic-bezier(0.1,0.8,0.2,1)`。
- 老师要求卡划卡：`x ±550 / rotationZ ±20 / opacity 0` `0.22s power2.in`，回弹 `0.22s power3.out`。
- 负控提示环 `negctlWaveLoop`：`scale 1 → 1.24 → 1`，0.75s ease-in-out infinite。

---

## 7. 卡片组合

`MODS` `:19050`：A 仪表盘 460 / B 节拍器 420 / S 竖条节拍器 160 / D 今日时长 380（自定义档 288）/ R 今日记录 460 / Q 老师要求 440 / T 合并卡 360。

`COMBO_SCHEMA` `:19066`，`GAP_H=16`、`GAP_V=12`：

| key | 组合 | 布局 |
|---|---|---|
| 1 | AB | astack 460 + B 420 |
| 2 | AS | astack 460 + S 140（**默认**） |
| 3 | ASR | astack 460 + S 140(tate) + R 460 |
| 4 | AST | astack 460 + S 140(tate) + tcard 360（T 上段 D 高 220px，R 下限 160px） |
| 5 | ABQT | astack 430 + B 340 + Q 360 + tcard 360 |
| off | 自定义 | 勾选决定 |

初始状态 `{mods: PRESETS['2'], vp:'1133', skin:'light', combo:'2'}` `:19176`；组合、视口、皮肤全部记进 `localStorage`，**下次打开记住上次选择**，不回落默认。

---

## 8. 交互状态机与数据契约

```
票夹(准备态)  ──选齐 科目/内容/速度/时长──▶  黑条态
      │                                        │
      │点开始(缺项只提醒一个: 科目>内容>BPM)      │计时开始
      ▼                                        ▼
   stage-prep ───────────────────────────▶ stage-running
                                              │
                              ┌───────────────┴──────────────┐
                        提前结束(二次确认)                  正常结束
                              ▼                               ▼
                        结束确认弹窗 → 入库 daily_practices（+ practice_at CST）
```

**必须同源**：票夹选中的科目 / 练习内容 / 速度 / 时长 → 卡片插入后显示的内容 → 仪表盘联动显示的内容。三个地方任一处显示「吸气长音」这类默认值就是 bug。
练习时长（ruler 拖出来的时间）**不入库**，它只是本次计时的目标时长。

---

## 9. 多视口验收清单（改完必跑）

视口：1728×1117 / 1440×900 / 1133×744（iPad mini 横屏）/ 1024×768（iPad mini 竖屏）/ 744×1133（iPad 竖屏）/ 440×956（iPhone 17 Pro Max）/ 393×852（iPhone）。

每个视口检查：

- [ ] 无裁切、无元素重叠、无压顶栏、无压黑条
- [ ] 票夹与黑条在准备态 / 计时态都完整可见（横排右展、feed 顶部横条两种形态）
- [ ] 卡槽在**所有状态**都在（不只在计时态出现）
- [ ] 卡片插入位置真的在孔槽中部穿出，下缘被遮罩盖住
- [ ] 卡片头部没有被容器遮罩切掉
- [ ] 老师要求卡：标题不裁、计数不换行、底部按钮不遮盖、feed 档可长卡
- [ ] 节拍器元素不叠、旋钮指针不错位
- [ ] 月历等网格：上下间距 = 左右间距
- [ ] 深色皮肤下同样全部通过
- [ ] 缩放后点开始**整页宽度/高度不得变化**（锁定 `canvasFitBaseH`）

验收口径用 headless Chrome 取 `getBoundingClientRect` / `getComputedStyle` 实测值，不靠肉眼。

---

## 10. 改动红线

1. **demo 代码逐字复制**：认可过的 demo 版本不允许在投产页面上重画、重排。改就是改 demo。
2. **token 先注册再使用**：新色 / 新字号先回 `dizicute` 加 token，再同步本文件与代码。
3. **缩放基准**：改布局后必须 `canvasFitBaseH = 0` 重置并重新测量，否则整页缩放会错。
4. **feed 档不锁高度**：卡片在纵向流里要能纵向发展。
5. **两套皮肤同步**：任何新组件都要在 light / ink 下各做一遍。
6. **文案定案词不许改**：见 §5.9。
7. **数据不用假值**：D / R 卡走真实接口 `/api/practices/{今天}` 与 `/api/practices/{昨天}`，不用 `/api/today-stats`（服务端日期可能 UTC 会串到昨天）。
8. **改完必须**：`pytest tests/test_practice_dsh.py tests/test_practice_dsh_save.py` + 多视口实测 + 更新 `DSH_VERSION` + 重新打包部署。

---

## 11. 版本与发布

- `DSH_VERSION`（`:19071`）是唯一手改的版本号常量，当前 `v3.25`。
- 两处派生值都从 `DSH_VERSION` 自动派生，改版本号只需改模板这一处：
  - `X-Dsh-Build` 响应头 —— `app.py` 的 `dsh_version()` 解析模板常量
  - iframe 的 `?v=` 缓存绕过参数 —— `app.py` 的 `dsh_cache_bust()` 直接透出版本号（`v3.25` → `?v=v3.25`，`quote` 编码）。早期的「只留数字」派生（`v3.24` → `324`）已废弃：`v3.24` / `v3.24-beta` / `v3.2.4` 会撞成同一个 `324`，版本变了缓存不失效。
- 解析按 `(mtime_ns, ctime_ns, size)` 缓存，模板没改不重读 1MB 文件。`ctime` 必须一起进 key：保留 mtime 的换文件方式（拷贝/解包/同步工具）只改 ctime，少了它会把旧版本号读成新版本。
- 读文件失败不进缓存（`lru_cache` 不缓存异常），权限/IO 恢复后下一次请求即自愈；降级时 `X-Dsh-Build` 与 `?v=` 同为 `unknown`，不会出现 `?v=` 空参。
- 正则锚定行首 `^\s*var DSH_VERSION = '...'`，与 `scripts/_sync_cloudrun_deploy.py` 字节相同 —— 注释里的同名行不会污染响应头或打包出的 `build-info.json`。
- 模板内 22 处静态资源（CSS / JS / 图片）的 `?v=` 也走同一个值：写 `?v={{ dsh_v }}`，由 `/practice-dsh` 路由注入。早先是手写死的 `?v=315`，资源文件改过它也不变，浏览器启发式缓存下会看到旧样式。新增资源引用照此写，不要写死数字。
- 部署打包时 `scripts/_sync_cloudrun_deploy.py` 写 `src/kid_app/static/build-info.json`（version / branch / commit / source / dirty / built_at）。
- 改模板后**必须重跑该脚本再 deploy**，否则线上角标的 `commit` 是旧的。
- 线上验证：`curl -s https://dizical-prod-.../static/build-info.json`。

---

## 12. MRD 3.2.5 架构设计

> **完整架构规范**：详见 [`docs/practice-dsh/ARCH-MRD325.md`](ARCH-MRD325.md)（覆盖 `V1–V4`、`C1–C24` 及 `MRD §2.3.2.1`）。

### 12.1 多视口 4 档固定布局（`V1–V4`）
- **双层共存映射**：外层由 `applyCanvasViewport()`（`src/kid_app/templates/practice-dsh.html:23148`）写入 4 档布局类 `data-layout-tier="pc-layout | ipad-h | ipad-s | phone-layout"`；底层组件尺寸 `data-vp` 由 4 档确定性派生（`pc-layout` → `'1133'`、`ipad-h` → `'1133'`、`ipad-s` → `'744'`、`phone-layout` → `'440'`），兼容 6 张卡片内联 `[data-vp]` 选择器。
- **宽 > 高（`pc-layout`: `landscape and min-width: 1180px`；`ipad-h`: `landscape and max-width: 1179px`）**：横向扩展无限卡片模式，单屏最多呈现 **2 张顶层卡片**（`fitWideCombo` `:21315` 不再将 >2 卡挤压进同屏）；底部 `.cz-pagedots`（`:19730`）就地升级为 `.cz-spotlight-bar`（高 `36px`），支持点击跳页、轨道指针拖拽滑动（Scrubbing）与手势换屏（`V2`、`V3`）。
- **高 > 宽（`ipad-s`: `portrait and min-width: 600px`；`phone-layout`: `portrait and max-width: 599px`）**：`canvasIsFeed()`（`:22619`）判定为纵向瀑布流，卡片 `width: 100%` 等宽单列排列，高度由 `sizeFeedCard()`（`:21061`）按内容自然向下生长，零重叠（`V4`）。
- **缩放基准锁定**：`syncCanvasHeight()`（`:23036`）的 `fitKey` 纳入 `state.layoutTier`，在选择态/准备态锁定 `canvasFitBaseH`，跨 4 档阈值、横竖屏翻转或切换 Combo 时重置 `canvasFitBaseH = 0`。

### 12.2 卡槽 3 态状态机与几何参数（`C10–C15`）
- **三态定义（`#pkPunchSlotWrap[data-slot-state]`）**：
  - `select`（选择态）：`!cur || !content.trim()`；
  - `prep`（准备态）：`cur && content.trim() && (!started || paused || !timerRunning)`，**显式包含从计时态点击暂停（`started && paused`）**；
  - `run`（计时态）：`cur && content.trim() && started && timerRunning && !paused`。
- **卡槽几何（`updateCardSlotGeometry` `:20164`）**：`select`/`prep` 露出高度 `136px`、上拔位移 `--cz-card-pull-y: -28px`（`360ms cubic-bezier(0.22, 1, 0.36, 1)`），露出上部累计记录胶囊（`C7`）、`重新选择` 按钮（`C15`）与**前 3 个 session 快捷标签**（`C13`）；`run` 露出高度 `88px`、下插位移 `0px`（`300ms cubic-bezier(0.32, 0.72, 0, 1)`）并设置 `#czTicketStage { pointer-events: none }`（`C14`）。`#pkSlotCavity` 下移 `22px`（`slotOverlap = 60px`），Card A `section.panel` 顶部内边距 `--cz-panel-pt` 增至 `74px`（`C10`、`C11`）。

### 12.3 票夹瘦身、Dashboard 改造与全屏记录弹窗（`C1–C9`、`C17–C24`、`§2.3.2.1`）
- **今日练习记录全屏化（`C1–C3`）**：顶部 `#pkRecords`（`:4770`）固定为「练习记录」按钮，点击打开全屏化 `.popout-backdrop`（`tpl-R` `:16591`），支持右上角关闭、底部完成与遮罩点击无损关闭。
- **票夹瘦身与 `.pk-folio-box` 扩容（`C4–C6`、`C8`、`C9`、`C24`）**：移除 `pk-ticket` 内科目选择器、BPM 步进器与时长步进器；`.pk-folio-box`（`:5262`）扩容至 `min(680px, 94vw) × min(720px, calc(var(--cz-band-h, 100vh) - 24px))`，内嵌各科目的 session 胶囊组与自定义输入；触发入口收敛至 Card A `.cover-frame` / `#dashCoverName`（`C9`）与卡槽 `.pk-exposed-expand-hint`（「重新选择」，`C8`/`C15`）。
- **Dashboard 面板与控制区改造（`C17`、`C20–C23`、`§2.3.2.1`）**：`#ruler` 宽度收窄为 `250px`（`C17`）；`section.panel` 默认皮肤切换为 `dizicute` 暖色 token（`var(--cream)` / `var(--paper)` / `var(--ink)` / `var(--coral)`），同步维护 `ink` 皮肤（`C20`）；清空 `transport-caps` 辅助文字与 Logo（`C21`）；`#standBtn` 移入 `diag-card`（`C22`），左扬声器 `#speakerBlock` 对称复制到 `transport-main .c-right`（`C23`）；`#panelMicBtn` 下移合并至 `diag-card` 替换原 `.diag-status` 与 `#micToggleBtn`（`§2.3.2.1`）。

### 12.4 三个待拍板交互方案摘要（`C7`、`C16`、`C19`）
- **`C7` + `C18` 科目累计练习记录 Pop-out**：双入口触发（`#pkCardExposedBar` 上部 `#pkExposedStatsTrigger` 与 `panel-foot .c-left` 的 `昨天练了 x.x分` 按钮 `#yesterdaySubjBtn`），共享挂载于 `#canvasBody`（`--cz-band-t` / `--cz-band-h`）的 `#pkSubjectStatsModal`（`width: min(520px, 92vw)`，打开 `280ms cubic-bezier(0.22, 1, 0.36, 1)`，关闭 `200ms cubic-bezier(0.55, 0, 0.86, 0.35)`）。
- **`C16` 换科目卡片动画**：跨科目切换时执行 `540ms` 双段式换卡动画 —— Phase 1 旧卡上拔退场（`220ms cubic-bezier(0.55, 0, 0.86, 0.35)`，`translateY(-28px -> -68px)`）→ Midpoint 刷新 DOM → Phase 2 新卡从上方落槽回弹停靠在 `-28px` 准备态悬停位（`320ms cubic-bezier(0.16, 1, 0.3, 1)`），不叠加 `0.78s` 折叠延迟。
- **`C19` 音符节奏与 BPM 全局小弹窗**：`panel-foot .c-right` 显示 `♩=xx ♪=xx`，点击通过 `DizicalPracticeBus` 呼出挂载在 `#canvasBody` 的全局小弹窗 `#pkTempoModal`（`width: min(340px, 90vw)`），内含 `♩ / ♪` 二选一分段胶囊、`40–200` BPM 长按步进器与快捷预设，确认后广播同步 Card A 与 Card B 节拍器。
