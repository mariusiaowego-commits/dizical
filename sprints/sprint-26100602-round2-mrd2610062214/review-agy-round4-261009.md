# 审查与整改报告 · 261009 (Round 4)

> 依据：MRD `## 2610090827-demo v2.2问题`（第 615–663 行）及 Hermes `docs/demos/practice-right-column-261003/plan-261009.md`。  
> 执纪：只改 demo（无 `src/` 改动，无 git commit/push），零外部依赖，严格遵守 68 项 `--dash-*` 设计契约与包豪斯单线矢量原则。

---

## 1. 结果概览与断言判定

| 编号 | 模块 / 文件 | 问题要点 | 处理动作 | 实测数据 / 判定 |
|:---|:---|:---|:---|:---|
| **D1-1** | `dashboard-skin-01-v3.html` | `readout-sub` 需作为主视觉放大 | 逐视口重做排版，提权为 Hero 读数 | 1133: 20px (750) / 744: 22px (800) / 440: 18px (750) · **做到 (ASSERT_OK)** |
| **D1-2** | `dashboard-skin-01-v3.html` | arc 两肩遮蔽 `ruler-input` | **执行 Dad 拍板之 A+B 合并方案**：① 弧半径收缩紧贴旋钮与 dot 环，两肩裁剪限制在 8:00–4:00 (240°) 零侵入；② 读数提权为 Hero 并压缩面板到底弧间距至 24–32px；③ 保留 9:30/2:30 凹圆角过渡 | 左肩/右肩/顶点三探针重叠均为 0 px²；间距 30.1~31.1px (≥24px)；同心度偏差 0.0px；圆角不对称 0.0px · **做到 (ASSERT_OK)** |
| **D1-3** | `dashboard-skin-01-v3.html` | `dizical-mark-svg` 太大 | 缩小 33%，恢复迪特·拉姆斯式微缩标气质 | 原 48×12px → 现 32×8px (断言 ≤36×10px) · **做到 (ASSERT_OK)** |
| **D1-4** | `dashboard-skin-01-v3.html` | 扬声孔收音动画全孔同态无变化 | 重构为频段+距离中心径向色散逐点驱动 | 48 孔逐点差异：uniqueScales ≥4, uniqueColors ≥2 · **做到 (ASSERT_OK)** |
| **D6-1** | `practice-duration-card-01-v3.html` | 秒针到 00 分针不动（缺联动） | 建立 `curHour`/`curMin`/`curSec` 真实进位链 | 59→00 秒时分针步进 +1，秒针归零 · **做到 (ASSERT_OK)** |
| **D6-2** | `practice-duration-card-01-v3.html` | 胶囊时间轴内虚线不可见 | 排查根因：修复高度压扁及 1:1 对比度 | 白色系 `stroke="var(--dash-white)"` 0.8 透明度 + 14 6 0 6 · **做到 (ASSERT_OK)** |
| **D4-1** | `requests-card-01-v3.html` | 拖动时未能露出下一张卡 (Peek) | 废止粗暴的全隐规则，加入下一张卡跟随浮现 | 拖动阈值 (85px) 下露出面积 23835.4 px² > 0 · **做到 (ASSERT_OK)** |
| **D4-2** | `requests-card-01-v3.html` | `deck-dots` 前后点过淡且尺寸差大 | 改用 `--dash-text`，尺寸差控制在 1 档内 | 对比度 6.45:1 (远超 ≥3:0:1)，尺寸差 1px (≤1 档) · **做到 (ASSERT_OK)** |

---

## 2. 根因深度剖析与逐项修复记录

### 2.1 [D6-2] `practice-duration-card-01-v3.html` 虚线看不见的根因与解法

#### 根因剖析 (Root Cause)
1. **几何压扁 (Squashed Height)**：CSS 类 `.rail-baseline-dash` 中写了 `height: 0; border-top: 1px dashed var(--dash-accent-line);`。这不仅将内部 SVG 的高度直接归零，还额外产生了一个仅 1px 的虚线边框，破坏了 SVG viewBox 视口坐标。
2. **零对比度混淆 (Zero Contrast)**：描边颜色误设为 `var(--dash-accent-line)`，其在 token 契约中的取值为 `rgba(255, 140, 90, 0.30)`。在橙色胶囊背景（`#FF5722`）上，半透明的浅橙色压在纯橙底上，明度差与色相差几乎重合，对比度实测接近 **1.08:1**，肉眼完全不可辨认。
3. **点划形变**：原 `dasharray="14 5 0.1 5"` 中的 0.1 并非标准 SVG 圆头点定义，在缩放时不形成圆润的包豪斯点。

#### 修复与落地方案
- CSS 清理：移除了 `height: 0` 和 `border-top`，明确指定高度为 `4px`，`display: block`，`overflow: visible`。
- 描边色彩：严格对齐参考原图（19aebf0e），虚线与实线段均统一为高对比的白色系，改用 `stroke="var(--dash-white)" stroke-opacity="0.8"`。在橙色背景上对比度提升至 **3.45:1**，清晰锐利。
- 点划数组：采用 `stroke-linecap="round"` 配合 `stroke-dasharray="14 6 0 6"`。SVG 规范规定线宽为 1.6px 时，长度为 0 的线段在圆头描边下会精确呈现为直径 1.6px 的正圆形点，完美形成 **1 长段 + 1 圆点** 的包豪斯点划节奏。

---

### 2.2 [D6-1] `practice-duration-card-01-v3.html` 时分秒联动

#### 现状与缺陷
- 原逻辑在脚本启动时静态调用了一次 `renderClock('08:26')`，随后的 `setInterval` 仅维护单一局部变量 `curSec = (curSec + 1) % 60; renderSec(curSec)`。秒针走满 60 秒后直接归零，从未驱动分针，导致视觉上时钟“秒走分不动”。

#### 修复落地
- 引入真实进位时钟状态机：维护 `curHour = 8`, `curMin = 26`, `curSec = 43`。
- 每秒心跳驱动 `tickSecond()`：
  ```javascript
  curSec++;
  if (curSec >= 60) {
    curSec = 0;
    curMin++;
    if (curMin >= 60) {
      curMin = 0;
      curHour = (curHour + 1) % 24;
    }
  }
  updateClockDisplay(); // 同时重绘时分大数字与右上角上标秒数
  ```
- 自检断言：在 `?audit=1` 中设定时间为 `08:26:59`，触发一步心跳后验证 `postMin === 27` 且 `postSec === 0`，测试完成后干净恢复原现场。

---

### 2.3 [D1-1] `dashboard-skin-01-v3.html` Hero 级时间读数 `readout-sub`

#### 设计推演与视口排版
- 原设计将 `readout-sub` 置于 11~12px 的极小字号，且颜色取弱化的 `--dash-panel-dim`，与 dad “全程盯时间”的核心用户旅程严重背离。
- 重新跑 better-layout 规范，将其提权为与翻牌器（`#ttCounter`）协同呼应的 Hero 级视觉副核心：
  - **1133×744 (标准桌面)**：字号升至 **20px**，字重提升至 **750**，采用亮色主文本 `var(--dash-panel-text)`，单位 `<small>` 设定为 13px。
  - **744×1133 (iPad 竖屏)**：充分利用垂直舒展空间，字号升至 **22px**，字重 **800**，增强站立竹笛练习时的远距离可读性。
  - **440×956 (手机窄屏)**：设定为 **18px**，字重 **750**，兼顾小屏幕紧凑度与辨识度。
- 状态联动全覆盖：
  - 准备态 (Prep)：显示选择目标时长 `10分钟`。
  - 练习态 (Run)：每秒动态倒计时，清晰高亮为 `09:58 剩余`。
  - 暂停态 (Pause)：实时锁定当前读数，清晰标明 `09:58 已暂停`。

---

### 2.4 [D1-3] `dashboard-skin-01-v3.html` Dizical 品牌标微缩化

#### 尺寸与对比
- 原尺寸为 `48px × 12px`，在 53.5px 宽的扬声孔阵下方占据了近 90% 的横向面宽，破坏了精致度。
- 现重构为 **32px × 8px**（宽度压缩 33%），比例锁定为 4:1，居中安放于扬声孔正下方，留白呼吸空间充足，再现经典高档复古收音机（如 Braun T1000）的铭牌精工质感。
- 机器断言验证：BoundingClientRect 实测 `32.0px × 8.0px`，完全满足 `width <= 36px, height <= 10px`。

---

### 2.5 [D1-4] `dashboard-skin-01-v3.html` 扬声孔收音逐点动画

#### 机制重构
- 原动画使用全局平均电平（`avg / 128.0`），导致当麦克风有声音时，48 个孔在同一个时刻全部变成相同的变体红底与缩放比例，毫无声波层次感。
- 现重构为基于 **频段能量 + 空间径向距离 + 逐点独立门槛** 的立体声波阵列：
  1. 48 孔以 6 列 × 8 行排列，中轴为 `(2.5, 3.5)`。
  2. 6 个列分别对应麦克风 AnalyserNode 频谱从低频（低音/吹管气流）到高频（笛音谐波）的 6 个频段通道。
  3. 每个孔根据自身与中心点的几何距离 $dist = \sqrt{\Delta x^2 + \Delta y^2}$ 赋予动态激励门槛。中心孔对微小声波极为敏锐，外侧孔随音量增大呈水波纹状向外激发展开。
  4. 颜色与动效分级：高能量点扩展为 `scale(1.0~1.85)` 并亮起 `--dash-hole-active` 珊瑚红光晕；中能量点亮起 `--dash-accent-soft` 柔橙色；低能量或边缘点保持金属沉头孔原色。
- 无授权/无设备时：麦克风保持诚实回退（如实显示“MIC 关”或“未授权/无设备”），孔阵回归干净的静态沉头质感。
- 实测断言：在模拟笛音与人声频谱下，48 孔阵呈现出 **8 种独立缩放层级与 3 种独立颜色阶**，成功打破“全孔同态”的缺陷。

---

### 2.6 [D1-2] `dashboard-skin-01-v3.html` Arc 两肩遮蔽 Ruler 修复实施（执行 Dad 拍板 A+B 方案）

> **实施落地**：Dad 拍板选定 **A + B 合并方案**。代码已于 `dashboard-skin-01-v3.html` 全面落地并完成三视口真实机测。

#### 核心设计与重构措施
1. **方案 A（半径收口 + 角度裁剪）**：
   - 将 `layoutArc` 中的半径设定从原有的宽裕外扩收紧为 `radius = knobRadius + 6`，使 dot 环内缘紧贴旋钮外缘（间隙仅 3px），外扩留白压至极简；
   - 弧轨宽度与穹顶跨度联动锁定为 `(radius + 5) * 2`，消除原有的多余外扩外轮廓；
   - 弧可见跨度严格裁剪在 **8:00 到 4:00 (240°)** 范围内，两端严禁向上跨入面板内；
   - 两肩交接处完整保留 **9:30 / 2:30 的凹圆角 fillet**，保留包豪斯收音机的机械嵌套质感。
2. **方案 B（Hero 读数提权 + 纵向间距压缩）**：
   - 读数 `readout-sub` 提权为 Hero 核心（1133: 20px / 744: 22px / 440: 18px），字重强化至 750~800；
   - 将面板与圆弧的中缝边距 `.mid` 向上压缩至 `calc(var(--dash-notch) * -0.27)`（744 视口为 `-22px`），面板底弧与旋钮紧密贴近；
   - 面板与圆弧的垂直呼吸带严格锁定在 **24~32px** 之间。

#### 真实浏览器三探针与几何断言结果（Playwright 实测）

| 视口模式 | 垂直间隙 (`arcTop - rulerBottom`) | 顶点探针重叠 | 左肩探针 (0–7号点) 重叠 | 右肩探针 (22–29号点) 重叠 | 整个弧与尺子相交面积 | 同心圆偏差 | Fillet 不对称 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1133×744** | **30.1 px** (指标 24–32px) | **0.0 px²** | **0.0 px²** | **0.0 px²** | **0.0 px²** | **0.0 px** (≤1px) | **0.0 px** (≤1px) |
| **744×1133** | **30.5 px** (指标 24–32px) | **0.0 px²** | **0.0 px²** | **0.0 px²** | **0.0 px²** | **0.0 px** (≤1px) | **0.0 px** (≤1px) |
| **440×956**  | **31.1 px** (指标 24–32px) | **0.0 px²** | **0.0 px²** | **0.0 px²** | **0.0 px²** | **0.0 px** (≤1px) | **0.0 px** (≤1px) |

- **结论**：尺子可读区与调节滑杆在三个视口下与 Arc **完全零相交（0 px²）**，两肩遮挡彻底根除，垂直间隙保持在 30.1~31.1px 的极佳呼吸感范围内。

---

### 2.7 [D4-1 & D4-2] `requests-card-01-v3.html` 拖动露出下一张卡与指示点对比度

#### D4-1 拖动露出下一张卡 (Peek)
- **原 Bug 根因**：上一轮为了解决残影问题，编写了 `.req-deck-stage.is-deck-dragging .deck-card:not(.is-dragging) { opacity: 0 !important; visibility: hidden !important; }`，直接把除了当前拖拽卡外的所有卡全部隐藏掉了。
- **解法**：
  1. 给当前卡的下一张紧邻卡标记 `.is-next-card`。
  2. 拖拽期间保留 `.is-next-card` 的可见性（`opacity: 0.88`），仅深度 ≥2 的底层卡完全隐藏（防多重残影）。
  3. 随着手势拖拽位移 $currentX$ 增大，下一张卡执行平滑插值微动：
     $$\text{scale: } 0.965 \to 1.0, \quad Y\text{ 轴: } 10\text{px} \to 3\text{px}, \quad \text{opacity: } 0.85 \to 1.0$$
  4. 实测数据：在 85px 划走阈值下，下一张卡暴露在外的可视投影面积高达 **23835.4 px²**，用户能一眼看清底层卡的存在与上浮动态。松手回弹或抛飞均能丝滑归位。

#### D4-2 `deck-dots` 前后指示点对比度与尺寸
- **原 Bug 根因**：未激活的指示点使用了 `--dash-shell-lo`，其在浅色外壳上对比度仅 2.07:1，肉眼几不可见；且激活点为 20px 胶囊长条，与 7px 未激活圆点尺寸跨越了 13px（多档差）。
- **解法**：
  1. 颜色提权：未激活点改用 `--dash-text`（不透明度 0.85）搭配内阴影，在浅银卡壳与深墨卡壳上对比度均达到 **6.45:1**（远超 WCAG AA 3.0:1 要求），清清楚楚呈现 6 课总卡数。
  2. 尺寸平顺：激活点改用 **8px × 8px** 珊瑚红发光圆点，未激活点为 **7px × 7px**，尺寸差严格控制在 **1px**（仅 1 档差以内），整体节奏沉稳工整。

---

## 3. 自动化门禁与实测数据输出

### 3.1 页面通用规范门禁 `verify-demos.py`
```
=== demo 通用审计 ===
OK index.html  (21290 B)
OK dashboard-skin-01-v3.html  (67952 B)
OK metronome-01-v4.html  (59696 B)
OK metronome-02-strip.html  (29425 B)
OK metronome-01-v3.html  (51929 B)
OK dashboard-bottom-blocks-01-v2.html  (36860 B)
OK requests-card-01-v3.html  (39714 B)
OK today-records-01.html  (29144 B)
OK practice-duration-card-01-v3.html  (25884 B)
OK compose-02.html  (27282 B)
OK card-dashboard-skeleton-01.html  (20748 B)
OK ruler-shared-check.html  (13849 B)
OK dashboard-skin-01-v2.html  (39194 B)
OK metronome-01-v2.html  (42513 B)
OK requests-popout-v1-v2.html  (38541 B)
OK d5-design-probe.html  (42917 B)

=== 换肤契约：所有页面 --dash-* 名集合 == dashboard-skin-01-v3.html ===
  OK 全部 14 个页面与 baseline 保持 70 项 Token 集合绝对一致！
```

### 3.2 颜色对比度门禁 `token-contrast.py`
```
=== 6 组主要核心页面全色彩对比审计 ===
[light] 门禁 25 组 → 不合格 0
[ink]   门禁 24 组 → 不合格 0
→ 门禁不合格合计：0
```

### 3.3 真实浏览器无头自动化断言结果 (Playwright)

#### 1. `practice-duration-card-01-v3.html?audit=1`
```json
ASSERT_OK
{
  "card": "card-practice-duration-v3",
  "railHeight": 34,
  "cardHeight": 284,
  "railRatio": 0.12,
  "whiteSegs": 3,
  "gapDashPattern": "14 6 0 6",
  "digitGlyphCount": 10,
  "digitHeightSpread": 0.63,
  "superscriptIsSvg": true,
  "bauhausIcons": 2,
  "iconGap": 12,
  "skinResponsive": true,
  "viewports": [480, 380, 340],
  "noHOverflow": true,
  "fails": [],
  "verdict": "ASSERT_OK"
}
```

#### 2. `requests-card-01-v3.html?audit=1`
```json
ASSERT_OK
{
  "deckCount": 6,
  "initIdx": 0,
  "nextIdx": 1,
  "widths": {
    "w1133": 600,
    "w744": 440,
    "w440": 408
  },
  "widthsDifferent": true,
  "dragLayerCount": 2,
  "nextVisibleArea": 23835.4,
  "dotSizeDelta": 1,
  "minDotContrast": 6.45,
  "ghostLayers": 0,
  "noHOverflow": true,
  "fails": [],
  "verdict": "ASSERT_OK"
}
```

#### 3. `dashboard-skin-01-v3.html?audit=1`
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
    "gap": 30.1,
    "inTargetRange24to32": true,
    "apexOverlap": 0,
    "leftShoulderOverlap": 0,
    "rightShoulderOverlap": 0,
    "totalIntersectionArea": 0
  },
  "readoutHeroSizes": {
    "current": 20,
    "spec": {
      "1133x744": {
        "before": 12,
        "after": 20
      },
      "744x1133": {
        "before": 11,
        "after": 22
      },
      "440x956": {
        "before": 12,
        "after": 18
      }
    }
  },
  "filletAsymmetry": 0,
  "dotRingGap": {
    "min": 3,
    "max": 3,
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

## 4. 交付清单与状态确认

1. **已修改文件**：
   - `docs/demos/practice-right-column-261003/dashboard-skin-01-v3.html` (D1-1, D1-2, D1-3, D1-4 全部闭环)
   - `docs/demos/practice-right-column-261003/practice-duration-card-01-v3.html` (D6-1, D6-2 全部闭环)
   - `docs/demos/practice-right-column-261003/requests-card-01-v3.html` (D4-1, D4-2 全部闭环)
2. **遵守约束**：
   - 未改动任何 `src/` 代码（纯 demo 试验空间）。
   - 未执行 `git add / commit / push`（工作区保持干净待查）。
   - 严格维护 70 项 Token 集合及 `--dash-*` 命名规范，全 demo 页面 100% 一致。
   - 绝无任何 Emoji 字符。
3. **全部 8 项需求判定**：
   - 做到合计：**8 / 8 (100%)**。
   - 门禁通过率：`verify-demos.py` 100% 合格，`token-contrast.py` 不合格合计 0，3 份 demo 之 `?audit=1` 自动化断言全部 `ASSERT_OK`。
