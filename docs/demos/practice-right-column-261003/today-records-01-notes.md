# D5 今日练习记录 — 实现说明

文件：`docs/demos/practice-right-column-261003/today-records-01.html`

视觉数值沿用 `--dash-*`（与 `dashboard-skin-01-v2.html` 同一套名字）。浅银是 `:root`，深墨是 `:root[data-skin="ink"]`。没有新 token。agy 的配色稿还没接。

## 和需求书不一致的地方

- **相比昨日的绿色**用已有的 `--dash-mic-on`（浅银 `#10B981`，深墨 `#34D399`）。多出来的红色用 `--dash-coral`。没有另造一个绿色 token。
- **总时长**读 mock 的 `span_minutes`（自然时间，接口还没有）。**练习时长**和**相比昨日**不读 summary 里的预计算字段，用 sessions 的 `duration_seconds` 之和，再减去 `yesterday_seconds`。
- 分钟显示用 `Math.round(秒 / 60)`。这组 mock 都能整除，57 分和 +27 分是算出来的。
- 科目行的「单次」列是这次科目的 session 条数（`N 次`）。单次时长写在展开后的 session 行上。科目行的「明细」是「—」。
- 科目行的「速度」：各 session 的 `tempo_bpm` 相同就写一个数，不同就写 `低–高`。
- 占比只加在科目行上，按科目秒数 / 全部科目秒数，最大余数法，合计 100。session 行的占比是「—」，不重复计入。
- 参考图右侧的折线没有对应列，3.4 的六列里没有这项，所以没画。
- 参考图是深色控制台。这里按 3.1 改成浅底扁平，深色只作为 `data-skin="ink"` 的另一套皮肤。

## 模糊

dad 选定方案 2。`gsap.ticker` 逐帧算行到滚动容器上下边缘的距离，带 32px，上限 5px。离开边缘用 gsap 在 0.12s 内收回 `blur(0px)`，结束后清掉内联 style。`prefers-reduced-motion: reduce` 时不算模糊。滚到底（下面没有剩余内容）时目标模糊为 0，方便各行回到清晰。

## 文字色

正文不再用 `--dash-ink` / `--dash-muted`。改用会随皮肤翻转的 `--dash-text`、`--dash-text-soft`。多/少的数字用 `--dash-delta-up` / `--dash-delta-down`。填充色仍用原来的 `--dash-ink` 和 `--dash-coral`。

## 行为

- 「折叠 / 展开」是一组两态按钮。折叠只渲染科目行，展开在科目行下挂 session 行。
- `?expand=1` 打开就是展开。
- `?audit=1` 在页面底部写 `<pre id="audit">`。先一行 `ASSERT_OK` 或 `ASSERT_FAIL …`，再一段 JSON：折叠行数、展开行数、三个 heroic、占比合计。
- 断言和显示分开。符号断言看的是「练习秒是否大于昨日秒」，不看 `signedDelta` 自己。所以把比较方向写反时，断言会红，而不是跟着一起错。
- 9 条 session，3 个科目，其中萨丽哈有一条 `is_extra: 1`，明细前标「补录」。
- 744 宽隐藏「明细」列。440 宽改成三层卡片网格，不横向滚动。
