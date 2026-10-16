# 节拍器 v4 — 四种音色与灯声同步（2026-10-08）

demo v2.1，卡 v4。新文件 `metronome-01-v4.html`，`metronome-01-v3.html` 未改。引擎在 `shared/beat-engine.js`。`compose-02.html` 的节拍器 iframe 改为 v4。

dad 在方案上改了一条：不要重拍。没有重拍音色，第 1 拍也不升音高。四拍音高和增益相同。其余按 `plan-metronome-timbre-261008.md`。

## 音色（只用非重拍那一行）

| 钮 | id | 做法 | 频率 | 峰值 | 包络 | 时长 |
|---|---|---|---|---|---|---|
| 木鱼 | `wood` | 正弦下滑 + 短噪声（带通 800Hz，Q 1.2，增益为正弦的 0.25） | 720Hz → 200Hz | 0.26 | 起 2ms，落 55ms | 80ms |
| 电子滴答 | `beep` | 正弦，不下滑 | 2093Hz | 0.16 | 起 1ms，落 28ms | 40ms |
| 牛铃 | `cowbell` | 两个方波 540Hz + 780Hz，带通 1400Hz，Q 4 | 540Hz（记录值） | 0.20 | 起 1ms，落 160ms | 220ms |
| 鼓槌 | `sticks` | 只有噪声：高通 2200Hz，再加一层带通 4000Hz | 2200Hz（高通，没有音高） | 0.28 | 起 0.5ms，落 16ms | 30ms |

808 和 blip 已从选择器去掉。旧的 `localStorage` 值 `click` / `sub808` / `rim` / `blip` 读出来落到木鱼。

四拍走同一行。`?audit=1` 在 120 BPM 的电子滴答上量了 32 拍：`freqSpan: 0`，`peakSpan: 0`，`accentFlags: 0`。第 1 拍和第 2 拍的频率、峰值相等。

## 同步

声音 `start(audioTime)`。灯在 `requestAnimationFrame` 里读 `currentTime`，第一次 `now >= audioTime` 时点亮，并记下这个 `currentTime` 为 `visualTime`。余晖是同一帧里的比较（`now < audioTime + glow`），没有 `setTimeout`。填队列也在这个 rAF 里，预读 150ms。不再用 `setInterval` 当节拍时钟。

验收跑在页面自己的 `?audit=1` 上，真实 `AudioContext`，120 BPM，32 拍：

| | 目标 | 实测 |
|---|---|---|
| 拍数 | 32 | 32 |
| `visualTime - audioTime` | 0–20ms 覆盖 ≥ 95% | **100%**（32/32） |
| 中位数 | ≤ 10ms | **3.33ms** |
| 最小 / 最大 | | 0.67ms / 6ms |
| 同步期间 `setTimeout` 次数 | 0 | **0** |
| 驱动 | `raf` | `raf` |

这 32 拍的振荡器加上试听的一声，`oscCreated` 是 33（试听 1 声电子滴答 + 32 拍各 1 个正弦）。

另外不带 `?audit=1` 直接点「启动」，默认木鱼、82 BPM，看了约 10 秒：

- 0.96s 时已有 2 个振荡器，9.99s 时是 14 个。中间 9.03 秒新增 12 个。82 BPM 在 9.03 秒里应有约 12.4 拍，对得上（木鱼每拍 1 个正弦）。
- 灯亮着的时候，亮的是第几粒，就等于音频时钟上当前拍的 `beat`。采样里 `lit` 为 1 时 `beat` 为 1，`lit` 为 0 时 `beat` 为 0，没有灯时 `beat` 是空。
- 采样里的 `dt`（173ms、259ms 这类）是这盏灯已经亮了多久，不是点亮的那一帧晚了多久。点亮时刻以审计的 `visualTime - audioTime` 为准，中位数 3.33ms。

## 改前 → 改后

| | v3 | v4 |
|---|---|---|
| 音色 | 木鱼、电子滴答、808、鼓边、blip | 木鱼、电子滴答、牛铃、鼓槌 |
| 第 1 拍 | 更高、更响；开关打开时灯用 `accent-lit` | 与另外三拍同一频率、同一增益 |
| 节拍时钟 | `setInterval` 25ms 去填 100ms 队列 | rAF 填 150ms 队列 |
| 点灯 | `setTimeout(time - currentTime)` | 同一帧的 `currentTime` |
| 灯声差 | 没有机器测量 | 32 拍，中位 3.33ms，最大 6ms |
| 组合页 | iframe `metronome-01-v3.html` | iframe `metronome-01-v4.html` |

开始时的 `{bpm, timbre}` 快照还在。审计里开始时是木鱼 / 82，随后切到电子滴答，快照对象不变。

## 门禁

`python3 scripts/verify-demos.py metronome-01-v4.html compose-02.html`

两页 OK。契约 68 名一致。共享尺子引用无。v4 仍有写死超宽值警告 `1133`（舞台档，带 `max-width: 100%`），不计 NG。

`python3 scripts/token-contrast.py` → 门禁不合格合计 0。

## 没做到 / 故意没做

- 仪表盘 v3 的「发声」仍走它自己的调度，没有接这个引擎。方案里这一轮就不接。
- 鼓槌没有振荡器，只有噪声。`oscCreated` 在鼓槌上不增加。试听计数的审计用的是电子滴答。
- 「±」长按仍用 `setTimeout`，那是按钮连发，不是点灯。同步那 32 拍里 `setTimeout` 次数是 0。
- 原来的「强弱拍」开关改成了一枚不能点的「四拍同声」，避免看起来还能打开重拍。
