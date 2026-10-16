# review — grok 第 2 轮（2610062214）

页面目标：这是一屏会拿去上线的练习页，左栏放计时和尺子，右栏是按契约宽度向右延伸的卡片轨道，页面自己往下滚。

```
1133 / 744
┌ 计时 460 ┬─ 轨道横向延伸 ─────────────────────►
│ 尺子     │ 节拍器 420 │ 要求 440 │ 记录 460 │ 时长 380 │ 下方 400
└──────────┴─ 每卡高度 = 内容 scrollHeight，不裁切

440（窗宽 ≤520 自动，按钮也可切）
计时 → 节拍器 → 要求 → 记录 → 时长 → 下方
单列，卡宽 100%（实测 408），页面纵向滚动
```

未改 `src/`、未改 `shared/ruler-production.*`、未改 agy 的三份 v3。v2 原件留在 `.bak-grok-round2-261006/`。

## 条目

| 条目 | 现象 | 根因 | 修法 | 改前 → 改后 | 证据 |
|---|---|---|---|---|---|
| A1 计时卡高度 | `card-practice-timer` 只有一条 | compose-01 轨道 `overflow-y: hidden`，槽 `overflow: hidden`，iframe 没撑到内容高 | compose-02 按 iframe 内 `scrollHeight` 设高，并去掉 `.dash` 的 `max-height` | iframe 高 **158 → 482**。尺子在卡内，底边 y=189，卡高 482 | `?audit=1` `clipped: false`，`contentH: 482` |
| A2 组合页目标 | 六张卡横排成画廊，矮的被裁 | 同一条固定高轨道里用 iframe 画廊 | 重做成左栏计时 + 右栏轨道。1133/744 用契约宽 460/420/440/460/380/400。440 改单列 | 1133 六卡宽 **460/420/440/460/380/400**，高 482/516/563/545/430/416，全部 `clipped: false`。744 同宽，页溢出 0。440 卡宽 **408**，页高超出一屏，溢出 0 | 三档 `pageOverflowX: 0`，每卡 `innerOverflow: 0` |
| A3 节拍器里的尺子 | `metro-card` 里有 60 根刻度 | v2 页自己嵌了 `ruler-wrap` 并调用共享件。共享件选择器没作用域，hermes 在修 | **不改 shared/**。v3 去掉尺子 markup 和共享件引用。compose 载入 v3，并断言 `.tick` 与 `.ruler-wrap` 为 0 | v2：**ticks 60 / ruler-wrap 1**。v3 与 compose：**0 / 0** | `metronome-01-v3.html?audit=1` 与 compose 的 `ticks` |
| A4 变体选择器 | 下方区块仍让人选孔阵/按钮/谱架 | 已选值只是默认，选择器还在 | compose 里固化并藏起选择器：孔阵金属沉头、按钮扁平胶囊、谱架胶囊钮 | 选择器可见 → `chooserHidden: true`。三类标记都在：`variant-countersink` / `pill-flat` / `stand-btn-pill` | compose `frozen` |
| A5 chassis 相叠 | 舞台里三块看起来叠在一起 | 槽把卡裁成一截；舞台宽被 1133 档撑开。三块本身是 `position: static` | 舞台宽锁在卡内，chassis 三块强制 `position: static`，卡高给足 | 相交面积 **0**（三块都在） | `overlapArea: 0` |
| A6 今日记录折叠 | 点折叠/展开没反应 | 组合页靠 `?expand=1`，iframe 高度不跟内容走 | src 固定 `today-records-01.html`（无 expand）。点卡内 `#btnOpen` / `#btnFold`，随后重算高度 | 行数 **3 → 12 → 3** | `records.before/expanded/folded` |
| B 五种音色 | 拍声只有闷的木鱼 | v2 只有 `scheduleWoodblock` | `metronome-01-v3.html`：木鱼 / 电子滴答 / 808 低鼓 / 鼓边 / 清脆 blip。Web Audio，无新依赖。包络 5ms 起、80ms 落。第 1 拍更高更响。默认木鱼，`localStorage` 键 `dizical.metro.timbre` | 5 个按钮都在。切到 click 后 `currentTimbre=click`，快照仍是 `{bpm:82, timbre:wood}`。试听 `oscCreated` **0 → 1** | `?audit=1` `ASSERT_OK` |

v2 节拍器页里的尺子还在（60 根）。那是共享件作用域的事，按简报留给 hermes，本轮没有改 `shared/`。

D4 拖动重影不在这轮交付里：简报写明不碰 `requests-card-01-v3.html`。

## 门禁

```
python3 scripts/verify-demos.py compose-02.html metronome-01-v3.html
```

两页 OK。`一致（68 个）`。metronome 有写死超宽值警告 `1133`（舞台档宽，带 `max-width: 100%`），不计 NG。

```
python3 scripts/token-contrast.py
```

门禁不合格合计 **0**。OPEN 的品牌色压白底仍是原先那三项，不计门禁。

## 三档

| 视口 | 页横向溢出 | 卡内横向溢出 | 裁切 | 备注 |
|---|---|---|---|---|
| 1133×744 | 0 | 0 | 无 | 契约宽度，计时高 482 |
| 744×1133 | 0 | 0 | 无 | 同上，右轨道自己横滑 |
| 440×956 | 0 | 0 | 无 | 单列，卡宽 408，页向下滚 |
