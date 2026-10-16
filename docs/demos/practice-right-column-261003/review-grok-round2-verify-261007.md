# 独立复核 — 第 2 轮 vs dad 2610062214

只读。浏览器实测（Chrome headless + CDP，1133×744 / 744×1133 / 440×956）。不采用 `交付台账-261007.md` 和 `review-agy-round2-261006.md` 的结论；对得上才写 match。

判据是 MRD `## 2610062214` 的原话。D1 第 3 条含 3.1–3.3，表里合成一条，完成度按最弱的子项。

## A. 逐条对照

| # | dad 原话（保留限定词） | 落点 | 判定 | 实测 | 完成度 |
|---|---|---|---|---|---|
| D1.1 | 点击开始后，为什么会直接出现节拍器声音 | `dashboard-skin-01-v3.html:749` `metroMuted`；`#bpmRead` `#btnPrimary` | match | 不按发声，连续跑 32 秒：`createOscillator` 次数 **0**，屏上一直是 `♩=82 · 静音`，模式 `run`，倒计时走到 `09:28 · 练习中`。页内 audit `defaultMuted:true` `audioRunning:"none"`，与这次独立计数一致 | 好。开始不再出声 |
| D1.2 | 计时条走动时要有 `ruler-vine` 生花和 `notes-bubbles`；现在只有手动拖时长才有 | `:1014` `driveRulerRunning`；`.notes-bubbles .tt-bubble` `.ruler-vine .vine-flower` | partial | 32 秒、每秒一帧：气泡节点 22 个，**每一秒都有 1–4 个 opacity>0.08**（序列 1,2,2,2,2,1,2,3,3,2,4…）。花：前 16 秒 **0** 朵 `data-bloomed=1`，第 17 秒起一直是 **1** 朵。藤蔓盒宽全程 **266px 不变**。页内 audit 写 `finalBloomed:6 / vineGrows:true`，那是审计函数自己调用了 `revealVine(0.35)`（约 `:1166`），不是这 5 秒自然长出来的 | 一般。计时中气泡是有的，花在 32 秒里只开了 1 朵。台账把「6 朵」当成自然生长，和实测不符 |
| D1.3 | arc 要和 panel 底弧平行、点不要密；一点一步、首末点对准指针；起点 20:00、终点 4:00，1 分钟一步，1–30 分 | `#arc i` `:859`；`#silverMinus` `:919` `applyDuration` | partial | 点 **30** 个。第 1 点方位角 **150°**（8 点 / 20:00），第 15 点 **-94°**（12 点方向），末点 **30°**（4 点）。这是经 12 点的上弧，不是经 6 点的短弧。panel 缺口圆和点所在圆**不同心**：1133 档圆心距 **49px**，半径差 **12.9px**；744 档圆心距 **32px**，半径差 **12.5px**。点一次「−」：屏上仍是 `10分钟`，`window.duration` 变成 **30**。内部步长和标签脱节 | 一般偏下。疏密和 8 点→12 点→4 点的走向对了；两条弧不是同一条；加减一次并不等于走 1 分钟 |
| D1.4 | 左 − 对齐 `panel-foot` 左边，右 + 对齐右边 | `.panel-foot .c-left/.c-right` 对 `#silverMinus` `#silverPlus` | partial | 1133：左缘差 **-8px**，右缘差 **+8px**。744：**-6px / +6px**。两边都在同一套 3 列网格里，但按钮外缘没有贴上 foot 的外缘 | 一般。方向对，差大约一粒小按钮的边 |
| D1.5 | 744×1133 时 `panel-main` 很空，应压缩上面、把空间让给指针 / arc / 按钮 / speaker | `.dash[data-vp="744x1133"]` `:214`；`.panel-main` | partial | 744：dash **500×584**，`panel-main` 高 **128**，内容底到 `panel-main` 底的空档 **0**。1133：dash **420×520**，`panel-main` 高 **104**。744 只把主区加高了 24px，不是把上面压下去 | 一般。没有明显的「上面空一大块」了，也没有按原话把上区压短 |
| D1.6 | `speaker-block` 不要自作聪明加线框外框 | `#speakerGrille` `:438` | match | 计算样式 `border: 0px none`，`box-shadow: none`，背景透明，孔 **48**。截图上是一排沉头孔，没有矩形外框 | 好。外框没了 |
| D1.7 | 下方三块不该拆成另一套 UI，应放进仪表盘 | `#diagCard` `#transport` 都在 `#dash` 内 | match | `.speaker-block` 只有 **1** 个，且在 dash 里。diag、开始/提前结束、谱架都在同一张卡内。`diagInsideDash: true` | 好。仪表盘底下就是这三块，不再是卡外的第二套 |
| D1.8 | 麦克风开关的 UI 在哪；仪表盘里有没有能点的入口；`diag-card` 是不是单独一张卡 | `#panelMicBtn` `#micToggleBtn` | partial | 两个钮都在卡内。点面板 MIC：文案 `MIC 关 → MIC 开`，diag 变成「采集中」。再点 diag 的「开启收音」回到关。全程 `getUserMedia` 调用 **0** 次 | 一般。入口在了，但是假开关，没有真正开麦克风 |
| D2.1 | 声音太闷，多设计一些，前端要有 UI 选择；附带的参考链接 | `metronome-01-v3.html` `#timbreSeg` `#btnPreview` | match | 五个钮：木鱼 / 电子滴答 / 808 低鼓 / 鼓边 / 清脆 blip。点 blip 后 `currentTimbre=blip`，试听让 `oscCreated` 从 1 增到 **2**。开始时快照停在 `{bpm:82, timbre:wood}`，随后切音色不改快照。卡内 `.tick` **0**、`.ruler-wrap` **0**、没有 `ruler-production` 的 link/script。参考链接打不开，没有和那条声音对听 | 好（相对「要有几种声音和选择器」）。和那条参考音是不是像，这次无法证明 |
| D4.1 | 三个视口点了标签，宽度和整体都没有变化，是不是做一样的 | `#reqChassis` `setViewport` | match | 独立量，不看页内数字：1133 档宽 **600**，744 档 **440**，440 档 **408**。页内 audit 的 `widths` 与此相同。六次（3 视口 × 2 皮肤）页溢出都是 0 | 好。三档宽度互不相等 |
| D4.2 | 按住拖动有时很卡，有重影，卡住 | `.deck-card` 拖动手势 | match | 用真实鼠标事件（不是审计里手动加 class）：拖到 +60px 时，另外两张 `opacity:0`，只有一张 `is-dragging` 且 `translate3d(60px, 1.2px, 0)`。松开后 `is-dragging` 数量 **0**。没量到帧时间，不能证明「不卡」 | 一般偏上。重影按「其余层藏起来」处理掉了；顺不顺手没有帧数 |
| D6.1 | 和参考图还有很大差距，重给 `19aebf0e…jpeg` | `practice-duration-card-01-v3.html` `.card` / 截图 | partial | 结构同图：深炭圆角卡、Tuesday 17、空心 08:26、秒、Practice、橙 pill、橙条、Piano 45m 20s、右下两枚图标。差在橙条偏厚、白段是 4px 实心条、图标比参考小一号且更简 | 一般。一眼能认成那张图，还不是那张图 |
| D6.2 | `rail` 里 `seg` 太高，要参考图那种高度很小的细长圆胶囊 | `#railCapsule` `.session-seg-white` `.rail-track-line` | partial | 卡高 **326**，rail 高 **58**，占比 **0.178**（台账 0.178 这个数对）。内轨线高 **6px**，是 rail 的 **0.103**，不是「线约带宽 1/5」。三段白条高都是 **4px**。圆角 16px | 差一截。58px 的橙条仍然是一块，不是细胶囊。台账把 0.178 判成已经符合「细长」，过宽 |
| D6.3 | 时间的细体字没有采用？还是没有这种字体 | `#dateText` `.hollow-digits-svg` | partial | 日期是系统无衬线 **15px / 字重 600**。时钟是描边 SVG（`stroke #FFF8F0`），不是一款细体字 | 一般。做成了空心几何数字，没有换细体字体 |
| D6.4 | 深墨下字和背景变成同一个颜色，看不清 | `#dateText` `#subjectText` 对卡面背景 | match | 默认深炭卡 `rgb(22,26,30)`。日期和科目都是 `rgb(255,248,240)`，对比度 **16.61**。点「浅银」后卡面背景不变，仍是这块深炭。只量了这两处正文，没有重扫台账说的 18 个元素 | 好。这两处不再融进背景。台账的「18 处最低 5.99」我没有逐条复算 |
| D6.5 | `ic-metronome` 的单摆太靠旁边，可以稍微斜，不能摆太过 | `.bauhaus-ic line` | match | 摆线 `x1=12 y1=6.5` → `x2=12 y2=20`，竖直线，在 24 视口宽的正中 | 好。不再偏到一边 |
| D6.6 | 完全复刻两枚 icon：间距 12px、`#F5F5F5`、线宽 1.5px；节拍器三角+竖摆+点，皇冠三峰 | `.bauhaus-ic` | partial | 间距 **12px**，摆线 stroke **#F5F5F5**、`stroke-width 1.5`，这两项对上 prompt。截图里两枚图标很小、比参考图简，皇冠和节拍器的形体没有参考图那么清楚 | 一般。数字规格对了，形体还没复刻到位 |
| C.1 | 组合时 `card-practice-timer` 高度太小，内容出不来 | `compose-02.html` 左栏 iframe | match | 1133：计时卡高 **482**，`clipped:false`。上一版同一条轨道里这张卡的 iframe 只有 **158**，槽 `overflow:hidden` | 好。就「高度给出来」这一条，够了 |
| C.2 | 一团乱、每张卡都不全；如果这是会上线的，组合视图错得离谱 | `compose-02.html` 六个 iframe 的 `src` | partial | 布局已是左计时、右轨道；1133/744 宽度 460/420/440/460/380/400，440 单列宽 408；三档页溢出 0，卡内溢出 0。但计时嵌的是 **`dashboard-skin-01-v2.html`**，老师要求是 **`requests-card-01.html`**，今日时长是 **`practice-duration-card-01.html`**，下方块是 **v2**。本轮的 v3 卡没有进这张组合页 | 一般。架子对了，里面还是旧卡。台账写成「真实布局已落地」时没写这一点 |
| C.3 | `metro-card` 里不该有尺子 | compose 里 metronome iframe；`metronome-01-v3.html` | match | 组合页 `ticks:0` `rulerWraps:0`。v3 页同样是 0，且 stylesheet/script 列表里没有 `ruler-production` | 好。这张卡里没有尺子 |
| C.4 | `control-strip` 还在让选扬声孔，记得已经选好了 | compose 注入后的下方块 iframe | match | `chooserHidden:true`。固化结果 `grille/ops/stand` 都是 true（金属沉头 / 扁平胶囊 / 谱架胶囊） | 好。选择器不在了 |
| C.5 | `dash-simulation-chassis` 里元素叠在一起、互相遮盖 | 同一 iframe 里 `.speaker-block` `.ops-block` `.stand-block` | match | 三块相交面积 **0**（1133 / 744 / 440 三次 audit 都是 0） | 好。不再叠 |
| C.6 | `card-today-records` 折叠/展开怎么点都看不到下面 | 卡内 `#btnOpen` `#btnFold`，src 无 `expand=1` | match | src 是 `today-records-01.html`。行数 **3 → 12 → 3** | 好。点卡内的钮就展开、再折回去 |
| 骨架 | 设计没问题，吸附保留，左右切卡也 ok | `card-dashboard-skeleton-01.html` 本轮不在五页交付里 | match | 没有改这个文件。按原话记保留。这次没有重测吸附手感 | 好（保留，不是新做） |

## B. 质量抽检

### 1. 视觉完成度

对照 `科目卡片参考-04.jpg`：D1 v3 的黑屏、缺口、上弧圆点、左右 −/+、无框扬声孔、底部按钮，已经是那张图的结构。差在圆点和缺口不是同一个圆（圆心距 49px），扬声孔是 6×8 而不是参考图那种更密的阵列，右下角是「谱架模式」而不是参考图的 EQ/FX。

对照 `19aebf0e…jpeg`：D6 区块齐全，深炭和橙条对。橙条 58px 偏厚；白段 4px 高，参考图是发丝一样的线；时钟是描出来的 08:26，不是那一款细体。

### 2. 交互

| 页 | 点过的 | 结果 |
|---|---|---|
| D1 | 开始 | 变成「继续」的前态是暂停：按钮「继续」，提前结束可点，`mode=pause` |
| D1 | 提前结束 | 回到「开始」，提前结束再次 disabled，计时 `00:00 · 待开始` |
| D1 | MIC / 开启收音 | 文案来回切，`getUserMedia` 仍是 0 |
| D1 | 发声 | `♩=82 · 静音` → `♩=82 · 发声` |
| D1 | 谱架模式 | 提示仍是「大屏看谱」，没有第二态 |
| D1 | − 一次 | 标签停在 10 分钟，`window.duration` 变成 30 |
| D2 | 五个音色、试听、一枚预设 | 音色切到 blip，振荡器计数 +1，BPM 文本变成 60 |
| D4 | 下一张 | 「上一张」从禁用变成可点 |
| D4 | 真实鼠标拖 60px | 只剩一层在跟手，松手后拖动态消失 |
| D6 | 三档宽度钮、浅银 | 卡宽始终 380；浅银不改变卡面颜色 |
| compose | 展开/折叠 | 3 → 12 → 3 |

### 3. 动画（连续 32 秒，不是页内那 5 秒）

不带 `?audit=1`，以免页内审计自己把计时停掉。每秒记录：

- 气泡：32/32 秒都有可见气泡，同时可见 1–4 个。
- 花：0 朵维持到第 16 秒，之后停在 1 朵。没有第二条生长曲线。
- 藤蔓盒宽：266, 266, …, 266。
- 振荡器：0。倒计时从 10:00 走到 09:28。

所以「计时中有音符」成立；「花随进度长出来」在半分钟尺度上几乎看不出来。页内 `finalBloomed:6` 不能当作这 5 秒的自然结果。

### 4. 三视口 × 两皮肤

页横向溢出：

| 页 | 1133 浅/深 | 744 浅/深 | 440 浅/深 |
|---|---|---|---|
| D1 dash | 0 / 0，卡 420×520 | 0 / 0，卡 500×584 | 0 / 0，卡 390×520 |
| D4 机身 | 0 / 0，宽 600 | 0 / 0，宽 440 | 0 / 0，宽 408 |
| D6 | 三档页溢出 0，卡宽都是 380。浅银不改卡色 | 同左 | 同左 |
| D2 卡 | 1133 浅和深，卡宽 480，溢出 0 | 744 浅，卡宽 480，溢出 0 | 440 深，卡宽 416，溢出 0 |
| compose | 溢出 0 | 溢出 0 | 溢出 0；深墨再量一次仍是 0 |

D1 六档 `dash.scrollHeight - clientHeight` 都是 0，但 dash 自己是 `overflow:hidden`，藏在里面的内容不会算进这个差。

### 5. 一致性

`card-contract.md` 默认宽：计时 460、节拍器 420、下方块 400、老师要求 440、今日记录 460、时长 380。

- compose 在 1133/744 用的就是这六个数。
- 节拍器**单页**卡宽是 **480**，不是契约 420。
- 老师要求单页 1133 档是 **600**（契约 max），不是默认 440。三档彼此不同，这是 dad 要的；和「默认宽」不是同一个数。
- D6 单页三档都是 380，和契约默认一致，也不随视口变。
- 时长卡的「Piano」、仪表盘的「萨丽哈」不是同一套科目名。参考图本身写的是 Piano。

### 6. 自检能不能被弄红

不改文件。在新文档脚本里改测量结果，再打开 `?audit=1`。

| 页 | 动手 | 结果 |
|---|---|---|
| D6 | `getBoundingClientRect` 把 `#railCapsule` 的高度谎报成 1 | **ASSERT_FAIL**，`railRatio got 0.003 want ~0.16` |
| D2 | `querySelectorAll('#timbreSeg button')` 返回空 | **ASSERT_FAIL**，`timbres got 0 want 5`，五个名字都报缺失 |

这两页的门不是焊死的绿。D1 的花开断言偏软：它自己把进度拨到 0.35 再数花，花少了才算失败，所以「计时中几乎不开花」仍可能是绿的。

## C. 还没到位

### P0

1. 组合页没有装上本轮的 v3 卡。现象：`compose-02.html` 的计时 / 老师要求 / 今日时长 / 下方块仍指向 v2 或 v1。落点：`compose-02.html` 四个 `iframe src`。建议：src 改到 `dashboard-skin-01-v3.html`、`requests-card-01-v3.html`、`practice-duration-card-01-v3.html`，再重测高度和溢出。约半天，含三档回归。
2. 仪表盘点一次「−」，分钟标签不动，内部时长变成 30。现象：一次 pointerdown 后 meta 仍是 `10分钟`，`window.duration === 30`。落点：`applyDuration` 把 `nextMin * 60` 送进 `RulerProduction.setDuration`，和尺子自己的单位拧在一起。建议：确认 setDuration 的单位，一次点击只走 1 分钟，标签和指针一起动。约 2 小时，含 1 和 30 两端。

### P1

1. arc 和 panel 缺口不同心（1133 差 49px，744 差 32px）。落点：`layoutArc` 的圆心对 `--notch-r/--notch-depth`。改成同一个圆心再量半径差。约 3 小时。
2. −/+ 外缘和 panel-foot 差 8px / 6px。落点：`.grid-3col` 的 68px 列和 44px 圆钮。约 1 小时。
3. 744 只把 dash 拉高到 584，`panel-main` 只多 24px。落点：`.dash[data-vp="744x1133"]`。要按原话重排，不是只加 max-height。约半天。
4. 麦克风钮不调用 `getUserMedia`。落点：`toggleMic`。要么接上授权，要么把文案改成「示意、未接麦克风」，别写「采集中」。约 2 小时。
5. 花在 32 秒里只开 1 朵，审计却报 6 朵。落点：audit 里的 `revealVine(0.35)`。自然计时的开花数要单独断言，不要自己把进度拨上去。约 2 小时。
6. 时长卡橙条仍是 58px（卡高的 17.8%）。落点：`.timeline-rail-capsule`。收到参考图那种细胶囊再量高度。约半天。
7. 时钟不是细体字，是描边 SVG。落点：`.hollow-digits-svg`。要就换细体，要就向 dad 说明没有那款字体、这是替代。约半天。
8. 两枚 icon 的线宽和间距对了，形体仍比 prompt 简。落点：`.bauhaus-ic`。按 prompt 的三角、竖摆、点、三峰重画。约半天。

### P2

1. diag 提示条里有一枚闪电符号。落点：`.toast-icon`。换成字。约 10 分钟。
2. 节拍器单页卡宽 480，契约默认 420。落点：`.metro-card` 的 max-width。约 30 分钟。
3. D6 的浅银按钮不改变卡色。三档设备宽度也不变（一直 380）。如果钮还留着，就让它真的切换，或者拿掉。约 1 小时。
4. 谱架钮点下去没有第二态。约 30 分钟，或明确写成只是入口。

## D. 结论

match **14** / partial **10** / miss **0**（按 MRD 的 24 条：D1 的第 3 条整条算 partial）。

这轮还不能直接给 dad 当「问题都对上了」来看：组合页仍嵌着旧卡，仪表盘的减号点一次就会把内部时长打到 30 而屏上还写着 10 分钟。先修这两条，再过目。

## E. fixed since review（2026-10-08）

只动了自己的两份：`compose-02.html`、`metronome-01-v3.html`。D1 减号那条 P0 在 `dashboard-skin-01-v3.html`，不在这两份里，没改。

下方三块的决定：从轨道里拿掉。v3 计时卡里已经有扬声孔、开始/提前结束、谱架。再放一张 v2 下方块就是 dad 说过的两套 UI。`dashboard-bottom-blocks-01-v2.html` 还在，页脚写明它只作对照、不进这条轨道。

| 项 | 改前 | 改后 |
|---|---|---|
| 计时 iframe | `dashboard-skin-01-v2.html`，高 482 | `dashboard-skin-01-v3.html`，1133 高 **546**，744 高 **610**，440 高 **546**。三档 `clipped: false` |
| 老师要求 | `requests-card-01.html`，高 563 | `requests-card-01-v3.html`，1133/744 高 **577**，440 高 **558**。机身宽 438 / 438 / 406，卡内溢出 0 |
| 今日时长 | `practice-duration-card-01.html`，高 430 | `practice-duration-card-01-v3.html`，高 **328**。卡内溢出 0 |
| 下方块槽 | v2，宽 400，高 416 | 槽删除。下方三块改在计时卡内量：speaker / 开始 / 谱架都在，相交面积 **0** |
| 节拍器单页卡宽 | **480** | **420**（`max-width: 420px`）。1133 页溢出 0，卡内溢出 0 |
| 三档页溢出 | 0 / 0 / 0 | 0 / 0 / 0 |
| 三档 `?audit=1` | ASSERT_OK | ASSERT_OK。`ticks: 0`，`chooserHidden: true`，`overlapArea: 0`，五张卡 `clipped: false` |

门禁再跑：`verify-demos.py compose-02.html metronome-01-v3.html` 两页 OK，契约仍是 68 名，共享尺子引用无。`token-contrast.py` 门禁不合格合计 0。

C.2 里「组合页嵌旧卡」这一差口合上了。D1 减号仍是 P0，不在本次改动里。
