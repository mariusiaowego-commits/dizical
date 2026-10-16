# 卡片契约 v1（26100401）

> 用途：向右延伸的卡片 dashboard 的**唯一接口**。每张卡自己声明宽/高约束，dashboard 只负责间距、吸附、切换。
> 拍板依据：dad MRD `2610041201` + Q1/Q2/Q3 答案（Q2「按你建议走」→ 本文件即建议落地）。
> 改这个文件 = 改契约。改卡内部实现不用动本文件。

## 1 卡片清单

| # | 沟通用名 | 文件 | min 宽 | 默认宽 | max 宽 | 内容形态 | 状态 |
|---|----------|------|--------|--------|--------|----------|------|
| 1 | `card-practice-timer` | `dashboard-skin-01-v2.html` | 380 | 460 | 620 | 计时 + 刻度尺 + 节拍取值 | W1 修正中 |
| 2 | `card-metronome` | `metronome-01-v2.html` | 340 | 420 | 560 | 4 粒拍灯 + knob + 拍声引擎 | W3 修正中 |
| 3 | `card-transport-blocks` | `dashboard-bottom-blocks-01-v2.html` | 320 | 400 | 520 | 按钮组 / 扬声孔 / 谱架 | W2 修正中 |
| 4 | `card-requests` | `requests-card-01.html`（新，从 D4 拆） | 340 | 440 | 600 | 老师要求（独立卡，练习中可看） | 等 D4 变体拍板 |
| 5 | `card-today-records` | `today-records-01.html` | 380 | 460 | 620 | 今日记录（折叠/展开 + 滚动模糊） | 已交付 |
| 6 | `card-practice-duration` | `practice-duration-card-01.html` | 300 | 380 | 480 | 今日练习时长 | W4 新做，排位后定 |

宽档都是 **v1 建议值，dad 可调**；调宽度只改本表，不改卡内代码。

## 2 布局规则（dashboard 一侧负责，卡一侧不操心）

- 横向排列、向右延伸；卡间距 `16px`；轨道左右内边距 `16px`
- `scroll-snap-type: x mandatory` + 每卡 `snap-align: start` → 松手自动吸附对齐
- 触屏：原生横向滑动；鼠标：`shift+滚轮` 或直接拖轨道
- 键盘：`←/→` 上一张/下一张，`Home/End` 首/末张，`Esc` 关闭（在弹窗内时）；焦点在卡内输入控件时不抢键
- 高度预算：`min(卡内容高, 视口高 − 顶部 .nav 53px − 上下 padding 24px)`；卡内部超高自己在卡内滚
- 窄屏（≤1099，含 iPhone 440）：**不再横向滚动**，卡宽 100%、上到下一个一个往下排（Q1 答案）
- 卡片首帧全部懒渲染，只有进入视口 ±1 张的卡才初始化（节拍器/计时器不许后台跑）—— **待实现，登记为 P2 项**

## 3 「独立命名 / 保留 / 可迭代」的落地方式（Q3 授权我方定）

dad 原话「每个卡片都可以单独设计优化迭代，保留这些卡片的 branch，合理命名，确保不要被删除」。
我方口径（**不用 5 条 git 分支**，避免并行分支合并地狱）：

1. **独立命名** → 上表「沟通用名」固定，讨论/派活/文档一律用这个名字
2. **保留** → 卡片文件固定在 `docs/demos/practice-right-column-261003/`，不在任何迭代里删除或改名
3. **可迭代可回溯** → 每张卡每次大改前，把当前版**冻结副本**放 `versions/<卡名>-vN.html`（不参与运行，只作对照/回滚）
4. **统一迭代分支** → `feat/practice-ui-iter-260920` 一直迭代、永不删；开工前先 `pull` 最新 main（用 merge，不 rebase）
5. **卡不单开分支** → 卡之间靠「文件所有权切块」隔离（一个 lane 一个文件），不靠分支隔离

## 4 每张卡必须自带的检查（契约级，dashboard 不管）

- 顶部视口切换：`1133×744 / 744×1133 / 440×956`
- 皮肤切换：`浅银 / 深墨`（`data-skin="ink"`）
- `?audit=1` 自报实测 JSON（宽高、溢出、关键对比度、交互断言），断言要能被负控弄红
- 颜色只走 `--dash-*`；六（七）文件 token 名集合一致（由 `scripts/verify-demos.py` 守）
- 文字对比度：正文 ≥4.5 / 大字号 ≥3.0（由 `scripts/token-contrast.py` 守）

## 5 刻度尺：必须用共享件，不许自己重造

dad 要求「用我生产上的那套 ruler-wrap」+「计时开始后 notes-bubbles 跳动 + ruler-vine 花开生长」。
生产那套已抽成共享件，**逐行切片**自 `src/kid_app/templates/practice.html`：

```
shared/ruler-production.css   ← practice.html:580-637（几何/尺寸/过渡/@keyframes 一字未改）
                                颜色字面量提成 --ruler-* 变量（默认值=生产值），末尾带深墨覆盖块
shared/ruler-production.js    ← practice.html:3993-4021 / 4028-4038 / 4060-4078 / 4229-4500 逐行切片
                                （气泡池、卷草纹几何、开花、红针、开关态、拖拽）
tools/gen-ruler-shared.py     ← 切片生成器；生产改了先改 practice.html 再重跑它
ruler-shared-check.html       ← 接入自检页（?audit=1 出 ASSERT_OK/FAIL）
```

**接法（卡片里照抄这段，路径不要再写 `../shared/`）**

```html
<link rel="stylesheet" href="shared/ruler-production.css">
<script src="../vendor/gsap.min.js"></script>
<script src="shared/ruler-production.js"></script>
<!-- 生产同名 markup：.ruler-wrap > .ruler#ruler > .ruler-row#rulerRow + .notes-bubbles + .ruler-input#rulerInput -->
<script>
  RulerProduction.mount({ minutes: 10 });
  RulerProduction.onDurationChange = sec => { /* 卡片自己的计时读数更新 */ };
  // 计时中：RulerProduction.setStarted(true) → 拖拽被守卫；prompt 取值走「开始那一刻快照」
</script>
```

**共享件已提供的 API**：`mount / step(±1) / setDuration / setStarted / emitBubbles / buildVine /
bloomFlowersUpTo / revealVine / retractVine / celebrateVine / paintRulerSelect / paintRulerRunning /
setMarker / pulseMarker / buildVineDebounced / tickCount / duration / onDurationChange`。

**边界（切片没搬、留给卡片）**：计时数字滚轮（`makeCounter/rollCol/ttRenderDigits` 那套）与秒位闪烁 ——
数字渲染走 `onDurationChange` 回调；`#metaVal` 不存在时共享件会补隐藏占位，保证尺子不被读数层拖死。

### 5.1 作用域加固（2026-10-06，踩坑后加的，必读）

**踩过的坑**：节拍器卡引了这两个文件却不想放尺子 → `.tick / .ruler` 样式洒进去，dad 在组合页看到
「节拍器卡里长出一把刻度尺」。

**规矩**：
1. **不托管尺子的页面，一个字符都不要引** `shared/ruler-production.{css,js}`（引了就会命中页面里任何 `.tick`）。
2. `mount` 现在支持**作用域根**：`RulerProduction.mount({ root: 容器元素, minutes: 10 })`；
   不传 = 整页（生产页单实例行为不变）。共享件内部的 DOM 查询（`#ruler / #rulerInput / #metaVal /
   .notes-bubbles / .tick.cur`）全部走这个根，不再全局命中。
3. 契约测试有守卫：**引了共享尺子的页面必须含 `.ruler-wrap` + `id="ruler"`**，否则 `scripts/verify-demos.py` 判 NG。
4. `setRunningModality(true)` 必须在**计时进入运行态时**调用（否则计时中看不到花开 + 音符气泡），
   对应 `setRunningModality(false)` 在待命/结束时调用。

### 5.2 运行态动画的**完整配方**（2026-10-06 补：这条不写清就会漏）

**踩过的坑**：D1 v3 只在开始/结束时切了「模式」，计时中**看不到音符气泡、花纹也不长**。
查生产 `practice.html` 才发现：`setRunningModality()` **自己不会吐气泡**（它只写 `#metaVal` 文案 + hint），
气泡/花纹是靠**计时循环每秒驱动**的。逐字对齐生产 `startTickInterval()`（`practice.html:2858-2867`）：

```js
// 每 1000ms，运行态（含暂停后继续）：
elapsed++;                                   // 已练秒数
paintRulerRunning(Math.min(1, elapsed / (duration * 60)));   // 尺子变进度器
revealVine(p);                               // 花纹跟红针生长（不是一次性全开）
pulseMarker();                               // 当前格自身脉冲
emitBubbles();                               // 红针顶端随机冒音符
// 选择态（待命）：paintRulerSelect(duration)；数字 = 所选时长
```

**自查口径**（dad 会这样验）：计时中盯 5 秒 → 应能看到气泡冒头（`emitBubbles` 每秒一次，单枚动画 1.2s），
花纹随进度增长（不是一开始就满开），红针随进度走。

## 6 深色基准 = `practice-duration-card-01-v3.html`（2026-10-08 dad 拍板）

dad 在 `## 2610081651` 对 D1 与 D2 各写一条「**深色部分完全参考 `practice-duration-card-01-v3.html` 改一版**」。
→ 该卡的深墨皮肤是**全站唯一深色基准**：

- 其它卡片的深墨，取值必须与 D6 同名 `--dash-*` token **逐名相等**（脚本可比对，见门禁）。
- 改深色的**唯一入口是 D6 卡**；先改 D6 定稿，再让其它卡对齐。**顺序不能反**。
- 这条同时是防漂移措施：以前各卡各自调深色，dad 一眼就看出「不是一个体系」。

## 7 挂件槽位（2026-10-08 新增）

dad 要的「节拍器最常用形态」= 宽 **仪表盘 1/3**、竖长条卡，挂在仪表盘**右侧**当长条挂件。

- 实现：`metronome-02-strip.html`，宽度比 = 0.333 ± 0.01（对照 = 仪表盘 `.dash` 的 420px 基准，不是随窗口变的槽宽）。
- 组合页 `compose-02.html` 里必须在计时卡右侧留出**挂载槽**演示这个挂件（当前 148px 槽 + 槽内竖条仍是 0.333）。
- 挂件内部元素/按钮 layout 由设计决定，但皮肤接 §6 的 D6 基准。
- 竖条卡自身不许横向溢出，速占（1133 / 744 / 440）三档都要过。


