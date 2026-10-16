---
date: "2026-10-15"
doc_type:
  - plan
tags: [dizical, practice, demo-v3.3, fix-plan]
description: demo v3.3 十四条问题的根因定位 + 分工
project: dizical
is_done:
---

# AI-PLAN · demo v3.3 问题（2026-10-15）

    来源  dad 文档 tqob/PRDs/2610150930-demov3.3问题.md（14 条）+ 4 张截图（已逐张 vision 读出）
    对象  docs/demos/practice-right-column-261003/canvas-01.html（747→750KB，未 commit）
    红线  画布本体 practice-ticket-v4-260920.html 零改动（sha256 e86d4bc56163218d）· 不新增依赖 · 不 commit

## 我这轮在真会话（1133 档）量到的现场（每条根因的证据）

```
① 仪表盘内部
   A 卡 iframe：396×441（组合1 460 宽 / 组合3 430 宽）
   A 卡内 body: scrollHeight 467 > clientHeight 441  ← 溢出 26px，这就是滚动条（item 1.2 实测根因）
   溢出来源：#frame 高 429 固定在 y=32 → 32+429=461 > 441（frame 高度没跟着卡片高度缩）
   A 卡内 #dash 409×405 @y44；#panel 377×115 @y58
   .ac-root(#ttCounter) computed font-size 48px 但 box = 0×0  ← 空心数字容器是空的（item 4 根因）
   实际可见的是 .readout-sub #metaVal「10分钟」font-size 16px  ← 这就是 dad 看到的"小数字"
   #legacy-readout display:none（旧的兜底在，但没显示）
② 联动
   A 卡内有 #bpmRead（显示「BPM 82 · 静音」）和 #bpmToggleBtn
   画布把原画布块搬进了隐藏宿主 #czStubHost{display:none!important}（画布自己的 JS 仍按 id 找得到它们）
   → 画布 JS 的 setBpmRead() 写的是隐藏宿主那份；A 卡里这份是副本 ⇒ 不联动（item 3 根因）
③ 卡槽
   .pk-punch-slot-wrap.cz-punch-slot = 460×48 @(394,21)，底边 69；仪表盘顶 76 ⇒ seam 7px
   它是仪表盘【上方独立一条】，自身带文案「打卡机入卡槽 · 点击下方「检票·开始练习」自动插入票卡 / 待命入槽 / 吸气长音」
   → dad 要的是"槽开在仪表盘上"（拟物嵌入），不是上面单独一条（item 8 根因）
④ 孔阵
   .grille-6x8.variant-countersink 72×72（744 档 56×56）
   麦克风映射：level = Math.min(1.0, (rms - NOISE_FLOOR) * 4.0)（canvas-01 内联）← 灵敏度就在这里（item 5）
⑤ toast / diag
   .toast-banner 47,405 351×21，display:flex / opacity:1 → 静态常显（item 6）
   .diag-card 34,362 377×73（白底）→ dad 要撤白底、直接贴大背景
⑥ B 高度
   组合3：B=340×520 + 12 + D=340×248 = 780 = H ⇒ B 自身不是 H（它跟 D 同列分高）—— item 7 要的口径
⑦ 窄档（744/440，页面上有「卡内视口」三档按钮，已复现）
   744：票卡 82,78 580×780；A 84,78 576×780 ⇒ 票卡×A 压叠
   440：票卡 16,78 397×780；A 18,78 393×780 ⇒ 票卡×A 压叠
   三组合 × 两档 全部「票卡×A」压叠（doc 高 2486~3285，一屏 780 一卡地竖排）
   → item 14 根因：≤744 时右栏没切成单列（模块列与票卡同 t=78 同 l≈18，父容器没换布局），且每卡仍按 780 高
⑧ 老师要求卡（Q）
   截图3 实测：卡内「2026-0…」日期被截断；卡内元素是定宽设计直接塞进窄槽（item 11）
```

## 十四条 → 根因 → 改法 → 归属

| # | dad 的原话要点 | 根因（实测） | 改法 | 归属 |
|---|---|---|---|---|
| 1.1 | 仪表盘为等高被拉高，内部元素没跟着重排 | `#frame` 固定 429 高 + 内部元素用固定 y | 卡片内部改**容器驱动**：帧/面板/底部诊断区按卡片高分配（flex/grid 分区），不写死 y | grok |
| 1.2 | 卡片出现纵向滚动条（拟物仪表盘不该滚） | body 467 > 441（`#frame` 429@y32 溢出 26px） | 同上：先消灭溢出（内容按可用高压缩/分区），再断言 `scrollHeight <= clientHeight`（写进页内自检） | grok |
| 2 | 票夹问题（2.1 **正文空白**） | — | **待 dad 补内容** | dad |
| 3 | 左栏速度与仪表盘黑区右下 BPM 不联动（竖条已联动） | 画布 JS 写的是隐藏宿主 `#czStubHost` 的 `#bpmRead`；A 卡副本没人写 | 总线把 A 卡（嵌套 iframe）的 `#bpmRead` 纳入绑定：就绪后 rebind + 每次变更跟随 + 负控真红 | grok |
| 4 | 未计时时 readout 是小数字，与 dashboard-skin-01-v3 不一致 | `.ac-root#ttCounter` box 0×0（空心数字没渲染），只剩 16px 的 `#metaVal` | 让卡片里 `#ttCounter` 真渲染（hollow-digits 初始化 + 尺寸）；无值时也显示大号 `--:--`/`00:00` 形态，不是小字 | grok |
| 5 | 孔阵声波幅度不够（很大力吹仍很小） | `level = min(1,(rms-NOISE_FLOOR)*4.0)` | 敏感度 +20%（4.0 → 4.8，或同幅度下调 NOISE_FLOOR），并给三条读数证据（静音=0 / 中/强） | grok |
| 6 | toast-banner 不要常显；diag-card 白底不要 | `.toast-banner` opacity 1 常显；`.diag-card` 有白底 | toast 改 hover / iPad 长按 `.diag-status` 才显示；`.diag-card` 白底透明化（只留发丝线分层） | grok |
| 7 | B 节拍器为什么没做同样高度 | 组合3 里 B 与 D 同列分高（520+12+248=780） | agy 出**等高口径**：哪些组合允许同列分高、B 单独出现时必须 = H | agy→grok |
| 8 | 卡槽样式奇怪，没嵌进仪表盘，彼此有距离 | 槽是仪表盘上方独立一条（seam 7px，自带文案） | agy 出**卡槽嵌进仪表盘顶边**的拟物规格（凹槽/缺口 + 票卡入槽的静态形态），grok 实装 | agy→grok |
| 9 | 今日记录卡展开后下面是模糊的；记录别做成卡片，点击小卡 popout 展示 | 旧实现"卡内展开" | R 卡改为「小卡（hover/点击）+ popout 弹窗」承载内容；删卡内展开（含模糊层） | agy→grok |
| 10 | 记录卡样式 copy 今日时长卡 D，与 D 上下结构（D 上 R 下），点击 R 弹 popout | 同 9 | R 卡 = D 风格同族（同一套内边距/字级/线），位置 = D 正下方；R 点击 → popout | agy→grok |
| 11 | 老师要求卡宽度不够、两边看不全 | 卡内定宽内容塞进窄槽 → 日期截断 | 卡内改流式（关键行 wrap/缩号），提供 ≥ 最小可读宽断言 | grok |
| 12 | 组合1 只是"放对位置"，元素没重排，撑满看不见 | 各卡内部仍按原始设计尺寸 | 组合1 = 仪表盘上 / 今日练习(D+R) 下左 / 竖条通高；各卡内部按**自己那一格**重排（这是 1.1 的同类根因） | agy 规格 → grok |
| 13 | 卡片按组合排布时，不要固定宽高后内部再挪（前端 layout 不对） | — 口径 | 全卡改**容器查询驱动**：`@container` + 内部只用 flex/grid/百分比；禁止"固定盒 + 内部绝对定位" | agy 规格 → grok |
| 14 | 卡内视口 744/440 时所有卡片压叠 | ≤744 右栏没切单列（票卡与模块列同 t/l），每卡仍 780 高 | 断点规则：≤744 票卡 → 模块列**顺序单列**（不重叠）+ 每卡高按内容/档位（不再固定 780）；三组合 × 2 档全部 0 重叠 | agy 规格 → grok |

## 分工（本轮）

```
grok (w31:p7)   实装 canvas-01.html：1.1 / 1.2 / 3 / 4 / 5 / 6 / 11 / 14（14 待 agy 规格）
agy  (w31:p4)   出 3 份规格（只写文档，不改 canvas-01）：
                  ① 等高口径（item 7：谁通高、谁同列分高、B 单独出现必须 = H）
                  ② 卡槽嵌进仪表盘（item 8）+ 组合1 内部重排（item 12）
                  ③ 今日记录卡 = D 风格同族 + D/R 上下结构 + 点击 popout（item 9/10）
                  ④ 容器查询纪律 + 744/440 断点单列规则（item 13/14）
pixel (w31:p6)  独立复量基线（当前 14 条的实测数）+ grok 交件后复量
hermes (我)     派单 / 上台复算 / 门禁 / 滚 v3.4 / 台账 / vault 同步
dad             补 item 2（正文空白）；拍 7/12/13 的口径分歧
```

## 交付顺序
1. agy 出规格（本人读规格时同步校对：等高 / 断点 / 卡槽 / 记录卡）
2. grok 实装 → 自检（含 `scrollHeight<=clientHeight`、窄档 0 重叠、总线双向 + 负控）
3. 我上台逐条复算（每条给"实测数 + 判决原文"）→ 门禁 → 滚 demo v3.4
4. pixel 独立复量 → 交 dad 真机
