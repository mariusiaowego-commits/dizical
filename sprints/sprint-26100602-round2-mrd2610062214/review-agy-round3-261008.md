# Round 3 交付评估与实测报告 (261008 / dad 2610081651 反馈落地)

> **任务来源**: MRD `## 2610081651`（第 570–611 行）及 `plan-261008b.md`  
> **执行 Agent**: agy  
> **交付文件**:
> 1. `practice-duration-card-01-v3.html` (D6: B1 虚线间隔段 + B2 全套 0-9 细体数字 + B3 细体秒上标，定稿深色基准)
> 2. `dashboard-skin-01-v3.html` (D1: A1.1 拱交错与呼吸带 + A1.2 紧贴点环 + A1.3 居中对齐/去SPEAKER/Dizical矢量标 + A1.4 真实麦克风电平/金属沉头 + A1.5 增量开花 + A1.6 深色对齐 D6)  
> **规范保证**: 不改 `src/`、不 commit、68 名 `--dash-*` token 契约一致、WCAG 对比度门禁 0 NG、无 emoji。

---

## 一、条目实测对比总表

| 卡片 | 编号 | dad 原话要点 | 现象/改前状态 | 修复方案与实现机制 | 改前实测数字 | 改后实测数字 | 验收判定 | 证据定位 |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **D6** | **B1** | 练习间隔要用虚线（1 长线段 + 1 dot），区间实线区分 | 间隔与练习段混合，底线为粗糙虚线，无点划节奏 | SVG `<line class="session-gap-dash">` 采用 `stroke-dasharray="14 5 0.1 5"` 与圆头端点，练习段保持白色实线 | 单一虚线无点循环 | 段类型 = 2；间隔含长段(14)与圆点(0.1) | **做到** | `practice-duration-card-01-v3.html:393-397` |
| **D6** | **B2** | 细体数字 0/8 满意，2 与 6 偏短，画全 0–9 | 仅实现 0, 8, 2, 6，字高极差 > 3px，缺 1/3/4/5/7/9 | 建立 `HOLLOW_DIGITS` 完整 0–9 几何字库，所有字符高度严格对齐 y=2~50 (高 48px)，1.8px 线宽 | 缺 6 个数字，字高差 3.2px | **10 个数字齐全，高度极差 0.63px (≤ 1.0px)** | **做到** | `practice-duration-card-01-v3.html:426-448` |
| **D6** | **B3** | 秒上标没用细体字 | 秒数采用普通 HTML 文本与系统字体 | `#secSvg` 接入 `renderSec(curSec)`，复用 `HOLLOW_DIGITS` 矢量中空字形 | 系统字体文本 | **同款 SVG Monoline 细体字族** | **做到** | `practice-duration-card-01-v3.html:360-362, 461-468` |
| **D1** | **A1.1** | arc 上半圆遮蔽 ruler，重建凹凸拱交错与呼吸带 | ruler 底边到 arc 顶边仅 6px，无拱交错，两端无圆角 | 暗面板底边凹拱 + 银底盘凸拱 (`.chassis-dome`) 包裹旋钮上半 + 9:30/2:30 内凹圆角 (`.panel-arch-fillet-*`)，压缩点环与旋钮边距 | 呼吸间距 **6.0px**；相交侵入 20px | **呼吸间距 50.4px (≥ 24px)；相交面积 0.0；fillet 对称差 0.0px** | **做到** | `dashboard-skin-01-v3.html:378-420, 755-763` |
| **D1** | **A1.2** | 点环离 knob rotor 太远，需紧贴旋钮 | 点环半径 108px，距旋钮边缘 43px | 点环半径调整为 `knobRadius + 7px`，点内缘距旋钮仅 4px；四向严格同心 | 间距 43px，且大屏下漂移 | **间距 4.0px (≤ 22.5px 为原值一半)；四向极差 0.0px (≤ 2px)** | **做到** | `dashboard-skin-01-v3.html:420-435, 995-1010` |
| **D1** | **A1.3** | speaker 与 cover-col 中线对齐；删 SPEAKER；字母拼 Dizical | speaker 较 cover-col 偏左 25px；有 SPEAKER 文本；节拍器带 `♩` 符号 | `alignSpeakerWithCover` 消除中线差；删文字；自绘包豪斯单线矢量 Dizical 标识；删 `♩` 改为 BPM | 偏离 **25.0px**；含 SPEAKER；含 `♩` | **中线偏差 0.0px (≤ 1px)；无 SPEAKER；页面 0 emoji** | **做到** | `dashboard-skin-01-v3.html:778-795, 975-987` |
| **D1** | **A1.4** | 收音计时随麦克风声音律动；恢复 D3 金属沉头 | 无音频分析节点；无麦克风时假装在动；孔阵无外沉头环 | 接入 `getUserMedia` + `AnalyserNode` 实时提取分贝电平驱动孔阵缩放；无权限诚实显示“未授权/无设备”；恢复 `.variant-countersink` | 无 Analyser；纯假动画 | **真实 AnalyserNode 联动；无设备诚实报 unavailable；含金属沉头变体** | **做到** | `dashboard-skin-01-v3.html:450-465, 1025-1095` |
| **D1** | **A1.5** | 拖动 ruler 时，已开过的花不重走开花动画 | 每次刻度变动销毁重绘，导致所有花重新弹跳 | `RulerProduction.revealVine` 增量化包装：记录 `lastRevealP`，标记 `bloomAnimCount`，单花动画仅播 1 次 | 来回拖拽重复弹跳动画 5 次 | **来回拖拽 5 次，每朵花动画次数 ≤ 1；单调推进动画数 = 露出花数** | **做到** | `dashboard-skin-01-v3.html:1098-1155` |
| **D1** | **A1.6** | 深色部分完全参考 D6 改一版 | D1 深色 `--dash-accent` 为 `#FF8C5A`，与 D6 (`#FF5722`) 不一致 | D1 的 `:root[data-skin="ink"]` 逐项对齐 D6，同名 token 值全等 | 存在 1 处 token 差异 | **同名 68 项 token 100% 全等比对一致** | **做到** | `dashboard-skin-01-v3.html:81-147` |

---

## 二、两张卡机器自检实测输出 (`?audit=1`)

### 1. D6 `practice-duration-card-01-v3.html?audit=1`
通过 Playwright 驱动无头 Chromium 测得真实 DOM 数据：
```json
ASSERT_OK
{
  "card": "card-practice-duration-v3",
  "railHeight": 34,
  "cardHeight": 284,
  "railRatio": 0.12,
  "whiteSegs": 3,
  "gapDashPattern": "14 5 0.1 5",
  "digitGlyphCount": 10,
  "digitHeightSpread": 0.63,
  "superscriptIsSvg": true,
  "bauhausIcons": 2,
  "iconGap": 12,
  "skinResponsive": true,
  "viewports": [
    480,
    380,
    340
  ],
  "noHOverflow": true,
  "fails": [],
  "verdict": "ASSERT_OK"
}
```

### 2. D1 `dashboard-skin-01-v3.html?audit=1`
通过 Playwright 驱动无头 Chromium（经 5.1s 真实自然计时走时监测）测得真实 DOM 数据：
```json
ASSERT_OK
{
  "card": "card-practice-timer-v3",
  "dotsCount": 30,
  "defaultMuted": true,
  "audioRunning": "none",
  "centerOffset": 0,
  "footAlignDiff": {
    "left": 0,
    "right": 0
  },
  "breathingBand": {
    "gap": 50.4,
    "intersectArea": 0
  },
  "filletAsymmetry": 0,
  "dotRingGap": {
    "min": 4,
    "max": 4,
    "spread": 0
  },
  "speakerCoverAlign": 0,
  "noSpeakerText": true,
  "noEmoji": true,
  "countersinkPresent": true,
  "maxFlowerBloomPlays": 1,
  "noHOverflow": true,
  "liveRun5sNatural": {
    "bubbleSeen": true,
    "maxBubbleOpacity": 1,
    "initialBloomed": 0,
    "finalBloomed": 1,
    "vineGrows": true
  },
  "fails": [],
  "verdict": "ASSERT_OK"
}
```

---

## 三、双门禁运行实测

### 1. 通用审计门禁 (`python3 scripts/verify-demos.py`)
```
=== demo 通用审计 ===

OK index.html  (20532 B)
OK dashboard-skin-01-v3.html  (61811 B)
OK metronome-01-v3.html  (49674 B)
OK dashboard-bottom-blocks-01-v2.html  (36722 B)
OK requests-card-01-v3.html  (33868 B)
OK today-records-01.html  (29018 B)
OK practice-duration-card-01-v3.html  (24031 B)
OK compose-02.html  (22575 B)
OK card-dashboard-skeleton-01.html  (20622 B)
OK ruler-shared-check.html  (13723 B)
OK dashboard-skin-01-v2.html  (39056 B)
OK metronome-01-v2.html  (42357 B)
OK requests-popout-v1-v2.html  (38415 B)
OK d5-design-probe.html  (42791 B)

=== 换肤契约：所有页面 --dash-* 名集合 == dashboard-skin-01-v3.html ===
  OK metronome-01-v3.html: 一致（68 个）
  OK dashboard-bottom-blocks-01-v2.html: 一致（68 个）
  OK requests-card-01-v3.html: 一致（68 个）
  OK today-records-01.html: 一致（68 个）
  OK practice-duration-card-01-v3.html: 一致（68 个）
  OK compose-02.html: 一致（68 个）
  OK card-dashboard-skeleton-01.html: 一致（68 个）
  OK ruler-shared-check.html: 一致（68 个）
  OK dashboard-skin-01-v2.html: 一致（68 个）
  OK metronome-01-v2.html: 一致（68 个）
  OK requests-popout-v1-v2.html: 一致（68 个）
  OK d5-design-probe.html: 一致（68 个）
```

### 2. 对比度门禁 (`python3 scripts/token-contrast.py`)
```
=== dashboard-skin-01-v2.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
... (全部 6 个测试页面检查)
→ 门禁不合格合计：0
```

---

## 四、关于 dad 拍板事项的汇报

1. **itshover.com 字母 icon 调查结论**:
   实测抓取该站点（https://itshover.com），确认为动效交互图标库（如 heart, rocket, star, sparkles 等操作符号），**不包含拼写单词所需的单字母 A–Z 矢量字形**。如实汇报后，退路采用纯包豪斯几何单线（1.2px 线宽，圆与直角几何拓扑）自绘了微型 `Dizical` monoline 矢量标识，置于孔阵下方，严守“0 emoji、0 位图、无渐变纯二维”约束。
2. **麦克风真机交互特性**:
   代码已接入标准的 `getUserMedia({ audio: true })` 与 `AudioContext.createAnalyser()`。在真实浏览器授权麦克风后，每帧通过 `getByteFrequencyData` 获取分贝电平实时调制 48 枚扬声孔缩放与高光。若在无麦克风或未授权环境下，诚实显示“未授权/无设备 (不可用)”，坚决杜绝“无输入假装在动”的伪交互。
3. **深墨基准与全等对齐**:
   已将 D6 作为全仓库唯一深墨源头，D1 的 `:root[data-skin="ink"]` 与 D6 同名 68 项 token 经 Python 脚本逐行比对完全一致。
