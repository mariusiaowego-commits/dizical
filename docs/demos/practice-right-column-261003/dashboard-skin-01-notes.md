# D1 仪表盘默认皮肤 — 设计说明

文件：`docs/demos/practice-right-column-261003/dashboard-skin-01.html`（745 行）

自包含单页。尺子与 4 位滚轮不重写，脚本用 `docs/demos/practice-skeleton-260920/real-timer-visual.js`（票卡 v4 同一份），GSAP 用 `docs/demos/vendor/gsap.min.js`。封面占位图是 `docs/demos/assets/practice-hero-ticket-260922.png`（768×1024，方框里 `object-fit: cover`）。未改 `src/`，未加依赖。

## 参考图 → 我们的元素（1.2.1–1.2.5）

| 编号 | 参考图 | 本 demo |
|---|---|---|
| 外壳 | 浅灰银金属机身，大圆角，顶边高光 | `.dash` 银渐变 + 内高光 + 内阴影，圆角 `--dash-radius` |
| 1.2.1 | 专辑封面，方图，浅灰细线圆角框，图下歌名 | `.cover-halo` 浅灰细线 + `.cover-frame` 正方形圆角图。图下「萨丽哈」 |
| 1.2.2 标题 | 歌名 | `#ttCounter` 四位滚轮 `mm:ss`。其下 `#metaVal`：准备态「N分钟」，计时中「总计 N分钟」，暂停「已暂停」 |
| 1.2.2 进度 | 细进度条 | `#ruler` / `#rulerRow` / `#rulerInput`。60 格、每分 2 格、红针。左右是同一套圆钮，左 `−` 右 `+` |
| 1.2.3 | 右侧歌词 | 小标题「老师要求」固定。正文占位句循环上滚，点一下暂停 / 再点继续 |
| 1.2.4 volume | 左下 Volume | `#bpmRead`，例 `♩ = 82`。跟旋钮联动，不跟 ± 联动 |
| 1.2.4 TRACK | 右下 TRACK | 「今日 42分」。写死的占位，没有接今日数据 |
| 1.2.5 | 旋钮联动音量 | `#knob` 旋转联动的是 BPM，不是分钟。分钟只由两处 ± 和尺子改 |
| 通栏 | 麦克风 / 时间 / 电池 | 左麦克风图标、中 `#clock`（12 小时制）、右 76% 电池形 |
| 中部 | 大旋钮、左右圆钮、弧形点 | 旋钮居中咬进深色面板的缺口。银面圆钮左 `−` 右 `+`。27 个弧点，亮到当前 BPM |
| 底部左 | 扬声孔 | `#grille` 6 列 × 8 行圆孔 |
| 底部中 | 文字 + 胶囊双钮 | 「练习 / 点按开始」。胶囊左键：开始 / 暂停 / 继续。右键：提前结束 |
| 底部右 | 两个叠放圆角方钮 | 「谱架」「模式」，合成谱架模式入口。点击无效果 |

顶上另有 demo 条：视口 `1133×744` / `744×1133` / `440×956`，以及「准备态 / 计时中」。

## `--dash-*` token

默认值在文件顶部 `:root`。组件规则里没有写死的 hex。

| 名字 | 值 | 用途 |
|---|---|---|
| `--dash-page` | `#FFF8F0` | 页底，对齐 tertiary |
| `--dash-shell-hi` / `--dash-shell-lo` | `#F3F4F6` / `#D5D8DE` | 银壳上下渐变 |
| `--dash-shell-inset` | `rgba(44, 62, 80, 0.16)` | 内阴影、圆钮投影 |
| `--dash-shell-shadow` | `rgba(44, 62, 80, 0.18)` | 机身外投影 |
| `--dash-glint` | `rgba(255, 255, 255, 0.85)` | 顶边内高光 |
| `--dash-panel` | `#1C1E21` | 深色 top panel |
| `--dash-panel-text` | `#F7F4EF` | 面板上的字和数字 |
| `--dash-panel-dim` | `rgba(247, 244, 239, 0.62)` | 时间、小标题、TRACK |
| `--dash-cover-line` | `rgba(255, 255, 255, 0.55)` | 封面外圈细线 |
| `--dash-coral` | `#FF6B6B` | 红针、开始/暂停/继续 |
| `--dash-accent` | `#FF8C5A` | 计时中的「提前结束」、下方「模式」 |
| `--dash-white` | `#FFFFFF` | 胶囊上的白字、点亮的弧点 |
| `--dash-ink` | `#2C3E50` | 页上文字、扬声孔、demo 条选中 |
| `--dash-muted` | `#666666` | 次要说明 |
| `--dash-tick-future` / `--dash-tick-past` / `--dash-tick-rail` | 暖白 28% / 78% / 34% | 刻度未到、已过、底轨 |
| `--dash-btn-face-hi` / `--dash-btn-face-lo` | `#3A3E44` / `#14171A` | 圆钮金属黑 |
| `--dash-btn-glyph` | `#F7F4EF` | ± 字形 |
| `--dash-btn-rim` | `rgba(255, 255, 255, 0.22)` | 圆钮上沿高光 |
| `--dash-knob-hi` / `--dash-knob-lo` | `#4A5058` / `#121417` | 旋钮 |
| `--dash-mark` | `#F7F4EF` | 旋钮白刻线 |
| `--dash-dot` / `--dash-dot-on` | 白 42% / `#FFFFFF` | 弧点 |
| `--dash-hole` | `#2C3E50` | 扬声孔 |
| `--dash-pill-track` | `#14171A` | 胶囊槽 |
| `--dash-pill-idle` | 暖白 55% | 未亮的「提前结束」 |
| `--dash-stand` / `--dash-stand-text` | `#16191C` / `#F7F4EF` | 「谱架」 |
| `--dash-battery` | `#7DCEA0` | 电池形。不在 dizicute 6 色里，只做状态条占位 |
| `--dash-kicker` | `rgba(44, 62, 80, 0.72)` | 「练习」字 |
| `--dash-num` | `52px` | 滚轮字号。窄/矮容器里改小 |
| `--dash-beat` | `0.73s` | 扬声孔一拍，由 BPM 改写 |
| `--dash-notch` | `96px` | 深色面板底部圆缺口 |
| `--dash-radius` | `36px` | 机身圆角 |

换肤：文件顶部有一段注释掉的 `:root[data-skin="ink"]`。打开注释并给 `<html data-skin="ink">` 即换成深色银壳。组件不用改。

## 和 DESIGN.md 6 token 的关系

直接复用：

- primary `#FF6B6B` → `--dash-coral`
- secondary `#2C3E50` → `--dash-ink`、`--dash-hole`
- tertiary `#FFF8F0` → `--dash-page`
- neutral `#FFFFFF` → `--dash-white`
- muted `#666666` → `--dash-muted`
- accent `#FF8C5A` → `--dash-accent`（这里用在提前结束和「模式」，不是 praise 页）

仪表盘专用、不在 6 token 里：银壳 `#F3F4F6` / `#D5D8DE`，深色面板 `#1C1E21`，旋钮和圆钮的黑，电池绿。这些只出现在 `:root`。

## 取舍

- 两处 ± 都改分钟（1–30），视觉是同一套黑圆钮。进度条两侧是 32px（窄屏 28px），银面两侧是 58px（窄屏 48px）。进度条行高只有 32px，放不下 58px 的钮。功能走同一个 `ttStepMin`。计时中和暂停时两处一起 `disabled`。
- 旋钮手感：没有惯性库。指针绕圆心的角度差，顺时针加大 BPM。系数 **0.42 bpm / 度**。范围 40–150。松手停住，不回弹。键盘左右也 ±1。弧点按这个比例点亮。
- 扬声孔：CSS `@keyframes holePulse`，周期 `--dash-beat = 60/bpm` 秒，8 列错开。假数据就是当前 BPM。准备态也在跳，方便看动效。`prefers-reduced-motion` 时停。
- 卷草纹和音符气泡是借来的脚本会画的，在深色面板上会挡尺子。本皮肤用 CSS 把 `.ruler-vine` 和 `.notes-bubbles` 藏掉。60 格、红针、拖拽、滚轮都还在。

## 未做

- 节拍器声音（D2）
- 谱架模式的功能，两个钮点击无效果
- 真实科目图、真实老师要求、真实今日时长。封面、正文、「今日 42分」都是占位
- 打卡提交、提前结束写库。按钮只切准备 / 计时 / 暂停三态的样子

## 验收

Chrome headless，CDP `Emulation.setDeviceMetricsOverride` 把布局视口设成精确尺寸，再量 `scrollWidth - clientWidth`。控制台错误用 `window.onerror` 收集。

| 视口 | 页面溢出 (x, y) | 卡片溢出 | 关键元素出界 | 控制台 |
|---|---|---|---|---|
| 1133×744 | 0, 0 | 0, 0 | 无。滚轮、尺子、两对 ±、旋钮、胶囊、谱架钮、封面名、歌词、格栅都在卡片内 | 空 |
| 744×1133 | 0, 0 | 0, 0 | 无 | 空 |
| 440×956 | 0, 0 | 0, 0 | 无。歌词换行。谱架两个钮完整 | 空 |

另外：60 个 `.tick`，4 个滚轮列。准备态主钮「开始」，提前结束 disabled。`?run=1` 进入计时中后主钮变成「暂停」，提前结束可用，两处 ± disabled。点「老师要求」正文可暂停滚动。
