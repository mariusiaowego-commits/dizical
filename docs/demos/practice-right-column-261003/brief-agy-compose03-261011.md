# brief-agy-compose03-261011 · 组合选择页（owner: agy）

新建：`docs/demos/practice-right-column-261003/compose-03.html`（**你独家 owner**）
先读：`plan-merge-261010f.md`（并入计划）+ `compose-02.html`（现有组合页，可复用其 iframe 装载与等高做法）

## dad 原话
> 在整体的布局中给一些选项，比如让我选展示 左栏票卡+右栏仪表盘+竖条节拍器；左栏票卡+右栏仪表盘+下方两个卡片（今日练习卡+老师要求卡）在 demo 里让我看整体不同组合的效果，以后我也是可以自选展示哪些的组合。记住在一屏里展示，如果样式塞不进去就往右可以滑动查看

## 模块清单（都用 iframe 现成页，不许重画）
| 代号 | 模块 | 源文件 |
|---|---|---|
| L | 左栏票卡 | `../practice-ticket-v4-260920.html` |
| A | 右栏仪表盘 | `dashboard-skin-01-v3.html` |
| B | 节拍器卡 | `metronome-01-v3.html` |
| S | 竖条节拍器 | `metronome-02-strip.html` |
| D | 今日练习时长卡 | `practice-duration-card-01-v3.html` |
| R | 今日记录 | `today-records-01.html` |
| Q | 老师要求卡 | `requests-card-01-v3.html` |
| X | 底部块 | `dashboard-bottom-blocks-01-v2.html` |

## 要做什么
1. **预设按钮**（点一下切组合，dad 一眼比效果）：
   - ① `L + A + S`（左栏票卡 + 仪表盘 + 竖条节拍器）
   - ② `L + A + D + Q`（左栏票卡 + 仪表盘 + 今日练习时长卡 + 老师要求卡，下方两卡）
   - ③ `L + A + B + S + R + Q`（全右栏 + 左栏）
   - ④ 全部 8 个
   - ⑤ 仅右栏六卡（现状对照）
2. **自由勾选**：每个模块一个 checkbox，任意组合；选择写 `localStorage`（以后 dad 自选还能记住）
3. **一屏 + 右滑**（dad 的硬要求）：
   - **只允许一行**：所有选中模块横排，**不许换到第二行**（断言：布局行数 = 1）
   - 塞不下 → **横向滚动**（`overflow-x: auto`，滚动条可见，并在右下角给一个非 emoji 的「右滑」指示：用项目自身几何语言，例如一条细线 + 直角小三角）
   - 模块宽：每张声明 min/默认/max（左栏票卡也要给三档），默认按 max 展示，窄视口按 min
4. **等高**：一行内所有模块等高（同 compose-02 口径，打实测高）
5. **换肤**：沿用现有皮肤开关（浅银 / 深墨），所有模块同时翻转
6. 配色只走 `--dash-*`（撞色族 = 朱橙 `--dash-vermilion*`），不新增依赖，**不 commit / 不 push**

## 自检（`?audit=1` 必须 `ASSERT_OK`，全部打实测值）
对**每个预设**逐条输出：
- `modules`（选了哪些）、`rows`（**必须 1**）、`eachWidth`、`rowHeight`、`containerW`、`contentW`、`hasScrollX`（contentW > containerW 时就该 true）、`clipped`（必须 false）
- 横滑可用性：能滚（`scrollLeft` 后 > 0）+ 松手后仍在同一行
- 模块顺序：按清单顺序排列（L 在最左）
- 断言「一屏」：`rows === 1` 且 `clipped === false`
**负控**：把 `overflow-x` 关掉（或强制 `flex-wrap: wrap`）时必须在预设 ③ 报红，红行要出现两端原文（content 总宽 vs 容器宽 / 行数 1 vs 2）。

## 产物
`spec-agy-compose03-261011.md`：改了什么 + 5 个预设的实测表（模块 / 行数 / 各宽 / 总宽 / 是否可横滑）+ 负控结果 + 遗留。
