# verify-hermes-261015-round1 · grok 10:56 版上台复算（7 条）

    真会话：本地浏览器（非无头），卡内视口三档按钮 1133 / 744 / 440
    对象：canvas-01.html 780,537 B @10:56（前一版 755,110 B @10-13 13:38）
    画布本体：sha256 e86d4bc56163218d 未变

## 逐条判决（before → after）

| # | 判据 | 实测 | 判决 |
|---|---|---|---|
| 1.1+1.2 | A 卡内不溢出、无滚动条 | `#frame`/`#dash` 现在撑满卡片 = 0,0 **430×584**（旧：#frame 固定 429 高挂 y=32）；卡内 body `scrollHeight 584 == clientHeight 584`、`overflow-y: hidden`、溢出 **0px**（旧 467>441，溢出 26px） | ✅ |
| 3 | 仪表盘黑区右下 BPM 联动 | 左 60→62 ⇒ A 卡 `#bpmRead`「BPM 82 · 静音」→**「BPM 84 · 静音」** ✓；B 卡 `#bpmHeroText` 82→84 ✓；反向点 B 卡 + ⇒ 左 64→65、A 卡→85 ✓；组合1↔组合3 切换后仍通 ✓；总线 `ready:true / pending:false / dash:85 / red:false`、log 逐步含 `readBack` + `dashSync.stuck:false` | ✅ |
| 3（负控） | `?negctl=bus` 必须红 | 左 60→62 而 A 卡仍 82；`red:true`，verdict「R2-D1 fail [联动1 左→右] 右栏 82 没跟着变（左栏 62）」 | ✅ |
| 4 | 未计时 readout 不再是小数字 | `.ac-root`/`#ttCounter` 现在 **72×60**（font-size 48px）且有内层 SVG（72×54，1 path + 2 g），不再是 0×0；旧的小字兜底 `#metaVal` 已 `display:none` | ✅ |
| 5 | 孔阵灵敏度 +20% | 代码 `var GAIN = 4.8;`（旧为字面量 4.0）＋ `NOISE_FLOOR 0.012` | ✅（振幅真机归 dad） |
| 6 | toast 不常显 + diag-card 撤白底 | `.toast-banner` 默认 `display:none`，仅 `.diag-card.is-toast` 时 `display:flex`（长按走 `pointerdown` + `HOLD_MS` + `window.__czToast`）✓；`.diag-card` 背景 = **rgba(0,0,0,0) 透明** + 1px 发丝顶线（`rgba(44,62,80,0.12)`）、无阴影 ✓ | ✅ |
| 11 | 老师要求卡两边不被裁 | Q 卡 404×780：叶节点 `scrollWidth > clientWidth` 命中 **0**；文本完整读出「… 1 / 6 萨丽哈 **2026-09-14** ♩=72 指定速度 中板抒情 · ♩=68 …」（旧截图里是「2026-0」被切） | ✅ |
| 14 | 744/440 不压叠 | 三组合 × {744,440} = 6 组：两两相交 **0**；票卡 78–858 居首、模块依序 944 → 1106 → 1268 → 1445（单列）；doc 高 744 档 1462~1631 / 440 档 1462~1631（旧 2486~3285） | ✅ |
| 12/13 | 卡内改容器驱动（本轮只落了 A 卡） | A 卡 `#dash`/`#frame` 已吃满容器（不再写死高）；其余卡（B/D/R/Q）待第二轮按 agy 规格统一 | 部分 |

## 残留（第二轮要收的）

```
R1 票卡在窄档没跟着缩：1133/744/440 三档票卡都是 780 高（agy spec-agy-container-bp 要求 744 档 460~500、440 档 420~450）
R2 440 档整页 doc 高 1631px（组合1/3），agy 判据 ≤1450（744 档 1631 ≤1650 ✓ 达标）
R3 空闲 readout 形态：容器与 SVG 都在（72×60 + path），但看不到文字层（空心数字是 path 绘制）→ 空闲时是否"一片空白"要 dad 真机看一眼
R4 组合切换瞬间总线会短暂 ready:false/pending:true（随后自愈）→ 是否要加"切换期不判红/自动重试"由 grok 定
R5 B/D/R/Q 卡内部仍是各自原设计尺寸（item 13 容器查询纪律还没全覆盖）
```

## 未做（等第二轮）
```
item 7  B 通高（组合3 改 A | B | [D 上 + R 下]）— 按 spec-agy-eh-fix
item 8  卡槽嵌进仪表盘顶边 — 按 spec-agy-slot-combo1
item 9/10 R 卡 = D 风格同族 + D/R 上下 + 点击 popout — 按 spec-agy-records-card
item 12 组合1 内部重排 — 按 spec-agy-slot-combo1
item 2  dad 文档该条正文空白，待补
```
