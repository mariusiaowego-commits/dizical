# 节拍器第 3 轮 — 经典滴答、深墨对齐、卡面收起、竖条（2026-10-08）

demo v2.2。改的是 `metronome-01-v4.html` 和 `shared/beat-engine.js`，新文件 `metronome-02-strip.html`。`compose-02.html` 在计时卡右侧加了竖条挂载槽。`metronome-01-v3.html` 和 `practice-duration-card-01-v3.html` 没改。

数字来自 headless Chrome（`--autoplay-policy=no-user-gesture-required`）打开页面自己的 `?audit=1`。

## 改前 → 改后

| | 上一轮 v4（v2.1） | 这一轮 |
|---|---|---|
| 音色 | 4：木鱼、电子滴答、牛铃、鼓槌 | 5，多了 `classic`（经典）。空的存储默认经典。旧值 `click` / `sub808` / `rim` / `blip` 仍落到木鱼 |
| 经典滴答 | 没有 | 双正弦 1046.5Hz 与 2825.55Hz（1:2.7），高通噪声 3500Hz，起 0.5ms、落 12ms，峰值 0.42 |
| 实测峰值 | 鼓槌最高 0.28 | classic 0.42 > 鼓槌 0.28 > 木鱼 0.26 > 牛铃 0.20 > 电子滴答 0.16 |
| 第 1 拍 | `accentFlags: 0`，频率差 0，峰值差 0 | 仍是 0 / 0 / 0。四拍同一配方 |
| 灯声同步（120 BPM，32 拍，电子滴答） | 覆盖 100%，中位 3.33ms，最小 0.67ms，最大 6ms，`setTimeout` 0 | 覆盖 100%（32/32），中位 6ms，最小 3.33ms，最大 8.67ms，`setTimeout` 0 |
| 深墨 token 对 D6 | 同名值不相等（页底、强调色、外壳高低和若干只在浅色里的名字） | 同名 65 个值全等，`inkMismatch: 0` |
| 深墨卡面文字对比度 | 未按 D6 深墨量 | 最低 5.99（启动钮），拍灯标签和速度词 7.97，BPM 与音色名 15.92。全部 ≥ 4.5 |
| 卡面设置 | 旋钮、±、启停、4 个音色钮、试听、5 个预设都在卡面上 | 卡面 4 项：减、加、启停、音色名。滑杆、旋钮、音色列表、拍号、预设在弹窗里 |
| 弹窗 | 没有 | 点音色名打开，点关闭收回。`opened: true`，`closed: true` |
| 竖条 | 没有 | `metronome-02-strip.html`。宽 140，对照尺 420，比 0.333。高 468 > 宽。1133 与 440 页面横向溢出都是 0 |
| 组合页 | 左栏只有 460 宽的计时卡 | 计时卡右侧多一个 148 宽的竖条槽。1133 / 744 / 440 页面横向溢出都是 0，槽内竖条比仍是 0.333 |

开始时的快照还在：审计里按下启动时是木鱼 / 82，随后切到电子滴答，快照对象不变。

## A2.1 经典滴答

选择器 5 项：`classic`、`wood`、`beep`、`cowbell`、`sticks`。

`BeatEngine.preview('classic')` 记下的就是 `hit()` 排进去的那一声：峰值 0.42，两个正弦，频率比 2.7，`accent: false`。这一声新增 2 个振荡器。另外四种的预览也都是 `accent: false`。

32 拍同步仍打在电子滴答上，好跟上一轮比。`freqSpan: 0`，`peakSpan: 0`，`accentFlags: 0`。灯没有用过 `accent-lit`。

竖条自己又跑了 4 拍经典，`accentFlags: 0`，四拍频率差和峰值差都是 0。

## A2.2 深墨

深色基准是 `practice-duration-card-01-v3.html` 的 `:root[data-skin="ink"]`。v4 和竖条的同名声明与它对过，差 0 个。`--dash-*` 名字仍是 68 个，没有加名、没有减名。浅色板没有改成 D6 的浅色值。

深墨下卡面改成 D6 的 `--dash-surface-soft`。启动钮在深墨里是 `--dash-page` 字配 `--dash-accent` 底，测到 5.99。暂停态是 `--dash-text` 配 `--dash-panel`。

## A2.3 卡面与弹窗

卡面只留 4 粒拍灯、BPM 数字、速度词、±、启停、音色名。拍灯和数字是读数，不是设置。弹窗关着时，带 `face-setting` 且有布局盒的元素是 4 个。

弹窗里有 BPM 滑杆、旋钮、5 个音色、试听、预设和「4/4」「四拍同声」。`hidden` 配合 `.pop[hidden] { display: none !important }`，关掉之后这些设置不再占位。

## A2.4 竖条

竖条自己的版式：顶上是音色名和 4 粒灯，中间是加、BPM、减，底下是启停。滑杆、音色列表和拍号在同一套弹窗里。皮肤用的是和 v4 同一份 token，深墨与 D6 全等。对比度最低同样是 5.99。

宽度对的是页内一根 420px 的仪表盘尺（仪表盘 `.dash` 的 `min(100%, 420px)`），不是会随窗口变的槽宽。140 / 420 = 0.333。组合页在 1133、744、440 里量到的槽内竖条也是 0.333，高大于宽，卡本身没有横向溢出。

440 宽时组合页改成上下叠，槽宽变成 408，竖条卡仍是 140，不跟槽一起拉宽。

## 门禁

`python3 scripts/verify-demos.py`：自动名单里的页全部 OK。契约 68 名。

`python3 scripts/verify-demos.py metronome-01-v3.html metronome-01-v4.html metronome-02-strip.html compose-02.html`：四页 OK，68 名一致。v4 的写死超宽值警告仍是 `1133`（舞台档，带 `max-width: 100%`），不计 NG。竖条和组合页没有这条警告。共享尺子引用无。

`python3 scripts/token-contrast.py`：门禁不合格合计 0。OPEN 的白底品牌色仍低于 3，不进门禁，色值没改。

## 没做到 / 故意没做

- 经典滴答按方案的双正弦、高通噪声和短包络做了，机器只量到峰值、频率比和振荡器个数。好不好听要 dad 用耳朵定。
- 这一轮的 32 拍中位是 6ms，上一轮是 3.33ms。两次都在 10ms 以内，覆盖都是 100%。差来自这次 headless 的帧间隔，不是时钟改回了 `setTimeout`。
- 仪表盘 v3 的发声开关没有接这套引擎。
- `verify-demos.py` 的自动名单还没有 v4 和竖条。点名跑过，68 名是齐的。名单归台账那一侧。
- 「±」长按仍用 `setTimeout`。同步那 32 拍里的 `setTimeout` 次数是 0。
