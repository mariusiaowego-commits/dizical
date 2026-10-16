# brief-pixel-canvas-261011 · 右栏并进真画布（owner: pixel）

**新建主产**：`docs/demos/practice-right-column-261003/canvas-01.html`（你独家 owner）
**可改**：`docs/demos/practice-right-column-261003/compose-03.html`（只做“拆外框 + 指路”，别重造）

## dad 原话（第 3 条）
> 1. 为什么所有卡片外面都有一个 frame？这是 demo 还是所见即生产所得？如果是生产也有着的外 frame 这样是不对的，每个卡片本身就有卡片样式，再加一个外框很丑
> 2. 真正的画布是在这里，右栏所有的样式和组合样式都要在这里给我看 demo，而不是你自己做一套界面给我看组合起来的样子。`file:///Users/mt16/dev/dizical/docs/demos/practice-ticket-v4-260920.html`

## 要做什么

### A. 答“外框”问题（先看清事实）
`compose-03.html` 里每个模块被包在 `.slot` 里：
```
.slot { border: 1px solid var(--dash-ink-a12); border-radius: 20px; background: var(--dash-white); overflow: hidden; }
```
这是**demo 展示脚手架**（给并排比对用的凹槽），**不是卡片自带**，也**不进生产**。
但 dad 说丑 → **把 `.slot` 的描边/圆角/底色全去掉**（改成透明、无边框、无阴影），让**卡片自己的样式**成为唯一可见的框。

### B. 真画布并装（主产 `canvas-01.html`）
以 `practice-ticket-v4-260920.html` 为**底**（它就是 dad 认的真画布：左栏票根 + 主列），把右栏卡片按组合并进**同一页**，并给组合开关：
1. **底座**：直接把 `practice-ticket-v4-260920.html` 的内容作为画布主体（iframe 或整段搬入皆可，但**页面上呈现的必须是它本身**，不许另做一套壳）
2. **并进方式**：右栏卡片作为画布内的**模块列**接入（在票卡右侧/下方，按容器宽决定列数），**卡片自带框**，不许再包一层 frame/slot
3. **组合开关**（放在画布**外面**的细条上，别塞进卡片里）：
   - ① 左栏票卡 + 仪表盘 + 竖条节拍器
   - ② 左栏票卡 + 仪表盘 + 下方两卡（今日时长 + 老师要求）
   - ③ 左栏票卡 + 全右栏六卡
   - ④ 只左栏票卡（原画布）
   - 每个右栏卡另有勾选框，可自由组合；选择写 localStorage
4. **一屏 + 右滑**：单行允许横滑（dad 上一轮的硬要求保留）；断言 `rows === 1` + 不裁切
5. 换肤（浅银/深墨）所有模块同时翻转

### C. 自检（`?audit=1` 必须 ASSERT_OK，打实测值）
- 每个组合：模块清单 / 行数 / 各模块宽 / 总宽 / 是否可横滑 / 是否裁切
- **无多余外框**：断言页面内**不存在**给卡片再包一层带 `border-radius`/`border` 的展示壳（实测：卡片 iframe/容器的父级不得有可见描边），并把实测的父级样式打印出来
- 负控：把 slot 壳加回去 → 必须报红，红行含两端原文（父级 border/radius 实测值 vs 期望 none）
- 产物：`spec-pixel-canvas-261011.md`（做法 + 各组合实测表 + 负控 + 遗留）

## 纪律
- 只碰这两个文件 + 可新建 `canvas-01.html`；**不 commit / 不 push / 不新增依赖**；配色只走 `--dash-*`
- 不改 `practice-ticket-v4-260920.html` 本体（它是 dad 的现存画布，本轮先用引用/并装方式；若必须改，先只加“可被引用的容器”并写清改了什么）
- headless 无音频设备时音频相关断言标 SKIPPED + 写明原因
