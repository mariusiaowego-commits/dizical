# brief-pixel-d6-v5-261010d · D6 微调 + 744 对照卡（owner: pixel）

先读：`plan-261010d.md`（本轮总 plan）

## 任务 1（改已有文件）：`practice-duration-card-01-v3.html`
dad 原话：`rail-duration-row` `time-ticks-row` 都要比现在更接近当中的 dash，用细字体。

现状（实测）：
```
.rail-duration-row   top: calc(50% + 8px)     font-family: var(--font-mono)  font-size: 9px  font-weight: 800
.time-ticks-row      bottom: calc(50% + 8px)  font-family: var(--font-mono)  font-size: 9px  font-weight: 800
```
改法：两行到 dash 的净距 8px → **5px**；字重 **800 → 400**（细体）；字号按可读性微调（8.5～9px）。
**不许压线**：B3 的安全距离仍然成立 → 断言「两行到 dash 净距 ≥4 且 ≤6px」。
交付：更新文件自检（含新断言 + 负控：改回 8px / 800 应报红）、三档视口 × 两皮肤实测数字。

## 任务 2（新建对照卡）：`metronome-01-v5.html`
dad 说 744 宽度下布局乱，并给了一版**完整重构规格**。agy 会在 `metronome-01-v3.html` 落主实现；
**你另起一张独立对照卡 `metronome-01-v5.html`**，按同一份规格做**你自己的解读版本**，给 dad 二选一。

规格（dad 原文要点，色值走 `--dash-*`）：
```
顶层中枢栏贯通卡顶：4/4 徽标（左）· 4 粒灯单行居中（第 1 拍珊瑚高亮，2/3/4 灰）· 强弱拍胶囊（右）· 底部 1px 细分割线
双栏 42% : 58%
  左：旋钮居中 + 两侧 − / + 圆形白键 38×38 微阴影 + 与旋钮净距 ≥16px；旋钮中心大字 + 珊瑚 BPM 标签
  右 L1：释义 13px/600；7:3 操作行（开始 珊瑚实心 r14 h50 ＋ 音色下拉 浅灰等高 50）
  右 L2：「老师定制练习」12px 弱灰组标题 + Grid 双列 minmax(130px,1fr)，文字与速度分列两侧，长文本不截断
  右 L3：「速度区间」12px 弱灰组标题 + 药丸 h32 r9999，当前档激活深底白字
```
硬要求：
- 只碰 `docs/demos/`、**不新增依赖**、不 commit / 不 push
- 换肤只走 `--dash-*`；**禁用 `--dash-ink` / `--dash-muted` 当文字 `color`**
- 自带 `?audit=1` 自检，**必须 ASSERT_OK**，断言要打实测值：744 文字无裁切（scrollWidth ≤ clientWidth+1）、灯单行 y 极差 0、灯组相对卡中心 ≤1px、− / + 与主按钮净距 ≥16px、左 42% / 右 58%（±1%）、药丸 h32、下拉与主按钮等高
- 三档视口（1133 / 744 / 440）× 两皮肤全测；负控（改回旧布局/旧值应报红）
- 目录：`docs/demos/practice-right-column-261003/`
- 输出：`spec-pixel-d6-v5-261010d.md`（改了什么 + 实测表 + 负控结果 + 遗留问题）
