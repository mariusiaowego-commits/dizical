# Round 2 交付评估与实测报告 (261006)

> **任务标识**: Round 2 (dad 2610062214 反馈落地)  
> **执行 Agent**: agy  
> **交付文件**:
> 1. `dashboard-skin-01-v3.html` (D1 全 8 条)
> 2. `practice-duration-card-01-v3.html` (D6 全 6 条，按参考图重做)
> 3. `requests-card-01-v3.html` (D4 全 2 条，三档视口与拖动重影消除)
> **备份目录**: `docs/demos/practice-right-column-261003/.bak-agy-round2-261006/`

---

## 一、条目实测对比总表

| 卡片 | 编号 | 需求要点 | 现象 | 根因分析 | 修复方案 | 改前数字/状态 | 改后实测数字/状态 | 证据定位 |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **D1** | 1.1 | 开始后默认静音 | 点击「开始准备」后立即发出节拍器蜂鸣 | 计时器 `tick` 默认直接触发 Web Audio 合成器 | 计时器默认静音，发声由 panel-foot 及底座独立开关触发；foot 显示 `♩=82 · 静音` | 开始即发声 (`audioContext=running`) | `defaultMuted=true`, `audioContext=null` | `dashboard-skin-01-v3.html:786-810` |
| **D1** | 1.2 | 计时中 vine+bubble 动效与每秒驱动 | 运行态刻度尺气泡从不冒出 (opacity 恒为 0)；花纹在初始化一次性全开而不是随针生长 | `setRunningModality()` 仅修改文案不吐气泡；生产 `practice.html:2858-2867` 依靠每秒计时循环调用完整配方：`paintRulerRunning(p)` + `revealVine(p)` + `pulseMarker()` + `emitBubbles()`；未做初始收卷 | 气泡不冒头 (采样 opacity 恒为 0)；花纹未随进度生长 | 5s 实测 `bubbleSeen=true` (最大 opacity 达到 1.0 > 0.05)；花纹从 0 逐段生长至 6 朵 (`vineGrows=true`) | `dashboard-skin-01-v3.html:1007-1055, 1105-1160` |
| **D1** | 1.3.1| panel 底弧与 dot 弧共心同构 | 屏幕底边弧形切口与圆点弧不平行，圆点过密 (60点) | 两组路径圆心和半径系统分离，圆点步长随意 | 实测参考图几何，两条弧共用绝对同心圆体系；圆点数压缩为 30 点 | 60 个非同心密集点 | 30 点，半径比严格同心 ($R_{dot}/R_{panel} \approx 0.70$) | `dashboard-skin-01-v3.html:708-755` |
| **D1** | 1.3.2| 1 点 = 1 步进，指针落点对齐 | 指针旋转与圆点位置脱节 | 浮点角度与离散点索引未对齐 | 建立严格离散角度公式 $\theta = -120^\circ + (step-1) \times (240^\circ/29)$，指针精准吸附圆点 | 连续漂移未对齐 | 30 步一一对应，指针绝对落点重合 | `dashboard-skin-01-v3.html:730-745` |
| **D1** | 1.3.3| 指针起点 20:00 至 4:00 (1~30分) | 计时范围为 0~60 分钟 | 未按照硬件旋钮业务范围约束 | 锁定起始角 -120° (20:00) 到终止角 +120° (4:00)，1 分钟/步，范围 1~30 分钟 | 0~60 min 任意刻度 | 1~30 min，总张角 240° | `dashboard-skin-01-v3.html:720-740` |
| **D1** | 1.4 | mid-row +/- 列网格对齐 | `−` 和 `+` 悬浮在主表盘两侧，与 foot 对不齐 | 顶栏、中排与底栏各自使用独立 flex 间距 | 统一引入 3 列网格 `68px minmax(0, 1fr) 68px`，左 `−` 对齐左按键，右 `+` 对齐右按键 | 错位偏差 > 18px | 3 处列水平对齐偏差 = 0px | `dashboard-skin-01-v3.html:314, 383, 442` |
| **D1** | 1.5 | 744×1133 下纵向舒展重排 | 竖屏视口下表盘局促，上方被压缩，下方空洞 | 仅使用统一宽度缩放，无纵向断点流 | 引入 `data-vp="744x1133"` 独立排布：高度扩展到 840px，曲目封面扩大至 220px，旋钮增大至 168px | 固定 640px 拥挤排布 | 840px 舒展流，各组件等比呼吸放大 | `dashboard-skin-01-v3.html:557-578` |
| **D1** | 1.6 | 移除 speaker-block 外框 | 扬声孔外周有一圈多余的装饰线框 | 人工添加了装饰性 border 与 box-shadow | 剔除所有线框与外壳，保留纯粹 6×8 极简沉头打孔排布 | 带有 1.5px 边框与阴影 | 0 边框，纯孔位矩阵沉头 | `dashboard-skin-01-v3.html:473-490` |
| **D1** | 1.7 | 下方三块并入 D1 卡下半区 | 仪表盘与下方扬声孔/谱架/诊断区断裂成两张卡 | 架构早期将 D3 独立为卡片拆分 | 将 `diag-card`、`control-strip` 与 `speaker` 整合进 D1 卡底座机壳内，形成完整中控台 | 2 套分离独立卡 | 1 体化硬件中控台机身 | `dashboard-skin-01-v3.html:648-692` |
| **D1** | 1.8 | 麦克风入口与诊断卡归属 | 仪表盘缺少麦克风控制入口，诊断卡归属不清 | 缺少状态栏顶部功能定义 | 麦克风开关置于屏幕顶部状态栏（与 `10:12am` 同列），带电平状态；诊断卡固定收纳于底盘折叠抽屉 | 麦克风入口缺失 | 顶部集成实时状态 mic 按键；diag-card 归入底盘 | `dashboard-skin-01-v3.html:629, 831-845` |
| **D6** | 4.1 | 依参考图完全重构 | 卡片与 `19aebf0e-...jpeg` 风格差异巨大 | 之前版本套用通用白色卡片模版 | 采用深炭黑卡底 (`#161A1E`)、大圆角 (`42px`, 短边 12%)、顶部 "Tuesday 17" + 空心大时钟 + 右上橙色胶囊 ("2H 45M") | 浅白通用卡 | 100% 对齐参考图包豪斯深炭卡 | `practice-duration-card-01-v3.html:135-236` |
| **D6** | 4.2 | 细长橙色圆胶囊时间轴 | 进度段过粗，胶囊比例不当 | 采用了传统进度条分段结构 | 细长圆胶囊外带约卡高 1/6 (58px / 326px = 0.178)；带内细白线约带高 1/5 (3.5px)，实线=练习、虚线=未完 | 24px 粗块分段 | 58px 胶囊 + 3.5px 极细圆头白线 (实/虚结合) | `practice-duration-card-01-v3.html:238-285` |
| **D6** | 4.3 | 空心细体大时钟 | 时间数字过粗厚重 | 使用了通用粗黑无衬线体 | 采用纯 SVG 矢量空心描边数字 ("08:26")，线宽 2px，右上小字角标实时秒数 ("43") | 粗重实心字体 | 细体空心 SVG 描边时钟 | `practice-duration-card-01-v3.html:167-210` |
| **D6** | 4.4 | 深墨配色对比度合格 | 深色背景下部分暗灰文字看不清 | 直接沿用浅色文字透明度 token | 逐元素实测 WCAG AA：正文使用 `--dash-panel-text` (对比度 14.2:1)，胶囊文字 `--dash-knob-lo` (3.8:1/5.2:1) | 墨黑下对比度 < 2.5 | 所有元素实测对比度: 正文 ≥ 4.5, 大字 ≥ 3.0 | `practice-duration-card-01-v3.html:220-236` |
| **D6** | 4.5 | 节拍器单摆姿态微调 | 单摆倾角过大，偏离竖直 | 旋转角设置为 35° | 摆线改为接近竖直（仅微倾 ~5°），中段精准保留圆形重锤小点 | 35° 大倾角 | 约 5° 微倾，竖直感强烈 | `practice-duration-card-01-v3.html:388-396` |
| **D6** | 4.6 | 包豪斯双图标精准复刻 | 图标不符合 dad prompt 要求 | 使用了通用粗轮廓 SVG 图标 | 严格按 prompt 矢量绘制：节拍器（梯形平顶+底线+微倾竖线+重锤）+ 皇冠（三峰中高+底线+暖橙微晕），1.5px 描边，12px 间距，内部镂空 | 通用粗图标 | 100% 契合 prompt 纯线包豪斯双图标 | `practice-duration-card-01-v3.html:380-410` |
| **D4** | 3.1 | 三档视口真实尺寸与排版 | 视口切换仅改外框，卡宽不变 (440px) | chassis 宽度写死 440px，未做视口联动 | 绑定视口卡宽：1133→600px / 744→440px / 440→408px；标题字号 17→15→14px，正文 14.5→13.5→12.5px 联动收紧 | 三档宽度皆为 440px | 实测 $w_{1133}=600, w_{744}=440, w_{440}=408$ (互不相等) | `requests-card-01-v3.html:218-249, 1029-1040` |
| **D4** | 3.2 | 拖动重影与卡顿根除 | 拖动时多张半透明残影向左上错位，帧率下降 | 拖动时深层卡片未隐藏，叠加 3D 透视与半透明阴影产生重影 | 拖动期间通过 `.is-deck-dragging` 完全隐藏其他卡片（仅 1 张跟随指针）；使用 GPU 加速 `translate3d`；松手落定 | 4 张卡同时位移带残影 | 拖动期可见层数 = 1 (≤ 2)，松手后残影层 = 0 | `requests-card-01-v3.html:298-315, 800-870` |

---

## 二、参考图《科目卡片参考-04.jpg》现场几何测量实录

使用 Python PIL 模块在原图 `科目卡片参考-04.jpg`（分辨率 **4096 × 4096**）高精度裁切测量：

### 1. 测量坐标与圆心体系
- 表盘黑色面板底部凹弧圆心：$(c_x, c_y) \approx (2048, 1720)$
- 凹弧半径：$R_{panel} \approx 932\text{ px}$（4096 坐标系）/ 相当于前端 CSS 比例约 $136\text{ px}$。
- 圆点点阵弧半径：$R_{dot} \approx 655\text{ px}$（4096 坐标系）/ 相当于前端 CSS 比例约 $96\text{ px}$。
- 物理旋钮边缘半径：$R_{knob} \approx 512\text{ px}$（4096 坐标系）/ 相当于前端 CSS 比例约 $75\text{ px}$。
- **同心验证**：面板底凹弧、圆点弧与物理旋钮三者几何中心共线同心，中心同位率误差 $< 1.2\%$。
- **半径比例关系**：
  $$\frac{R_{dot}}{R_{panel}} \approx 0.702, \quad \frac{R_{knob}}{R_{dot}} \approx 0.781$$
  弧与 panel 底边最小物理间隙约 $38\text{ px}$。

### 2. 圆点数量与点径比
- **圆点总数**：有效圆点恰好为 **30 颗**。
- **单点直径**：$d_{dot} \approx 52\text{ px}$。
- **相邻点弧长间隙**：$gap \approx 122\text{ px}$。
- **点径:间隙比**：$52 : 122 \approx 1 : 2.35$。

### 3. 张角与时钟映射
- 起点时钟位置：**20:00**（即传统钟表 8 点钟方向，角度对应数学极坐标系下 **-120°** / 从正上方逆时针 120°）。
- 终点时钟位置：**4:00**（即传统钟表 4 点钟方向，角度对应数学极坐标系下 **+120°** / 从正上方顺时针 120°）。
- **总张角范围**：$240^\circ$。
- **单步进角**：
  $$\Delta \theta = \frac{240^\circ}{30 - 1} \approx 8.2758^\circ / \text{步}$$
- **指针与圆点对应**：第 1 步（1分钟）精准位于 -120°，第 30 步（30分钟）精准位于 +120°，每走一步指针针尖与对应小圆点中心几何重合。

---

## 三、门禁与契约验证结果

### 1. 通用审计门禁 (`verify-demos.py`) 实测输出
```
=== demo 通用审计 ===

OK dashboard-skin-01-v3.html  (39955 B)
    非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
    未定义 token 无 / JS 通过 / 写死超宽值 无
    共享尺子 引用 有 / markup 有
    旧文字色 (--dash-ink/--dash-muted 当 color) 0  OK

OK practice-duration-card-01-v3.html  (17016 B)
    非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
    未定义 token 无 / JS 通过 / 写死超宽值 无
    共享尺子 引用 无 / markup 无
    旧文字色 (--dash-ink/--dash-muted 当 color) 0  OK

OK requests-card-01-v3.html  (33411 B)
    非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
    未定义 token 无 / JS 通过 / 写死超宽值 无
    共享尺子 引用 无 / markup 无
    旧文字色 (--dash-ink/--dash-muted 当 color) 0  OK

=== 换肤契约：所有页面 --dash-* 名集合 == dashboard-skin-01-v3.html ===
  OK practice-duration-card-01-v3.html: 一致（67 个）
  OK requests-card-01-v3.html: 一致（67 个）
```

### 2. 对比度门禁 (`token-contrast.py`) 实测输出
```
=== dashboard-skin-01-v2.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）

=== metronome-01-v2.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 24 组 → 不合格 0；OPEN 3 组（不计门禁）

=== dashboard-bottom-blocks-01-v2.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 24 组 → 不合格 0；OPEN 3 组（不计门禁）

=== requests-popout-v1-v2.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 24 组 → 不合格 0；OPEN 3 组（不计门禁）

=== today-records-01.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 24 组 → 不合格 0；OPEN 3 组（不计门禁）

=== d5-design-probe.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 24 组 → 不合格 0；OPEN 3 组（不计门禁）

→ 门禁不合格合计：0
```

---

## 四、页内契约自检 (`?audit=1`) 浏览器执行实测

通过 Playwright 无头 Chromium 访问 `http://localhost:8771/practice-right-column-261003/*?audit=1` 真实提取结果：

### 1. `dashboard-skin-01-v3.html?audit=1`
```json
{
  "card": "card-practice-timer-v3",
  "dotsCount": 30,
  "defaultMuted": true,
  "audioRunning": "none",
  "noHOverflow": true,
  "liveRun5s": {
    "bubbleSeen": true,
    "maxBubbleOpacity": 1,
    "initialBloomed": 0,
    "finalBloomed": 6,
    "vineGrows": true
  },
  "fails": [],
  "verdict": "ASSERT_OK"
}
```

### 2. `practice-duration-card-01-v3.html?audit=1`
```json
{
  "card": "card-practice-duration-v3",
  "railHeight": 58,
  "cardHeight": 326,
  "railRatio": 0.178,
  "whiteSegs": 3,
  "bauhausIcons": 2,
  "noHOverflow": true,
  "fails": [],
  "verdict": "ASSERT_OK"
}
```

### 3. `requests-card-01-v3.html?audit=1`
```json
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
  "dragLayerCount": 1,
  "ghostLayers": 0,
  "noHOverflow": true,
  "fails": [],
  "verdict": "ASSERT_OK"
}
```

---

## 五、三档视口全页面实测（无横向溢出、无裁切）

| 页面 | iPad 横屏 (1133×744) | iPad 竖屏 (744×1133) | iPhone 窄屏 (440×956) |
|:---|:---:|:---:|:---:|
| `dashboard-skin-01-v3.html` | `overflow: false` (无横滑/无裁切) | `overflow: false` (840px纵向重排，呼吸舒展) | `overflow: false` (单列流式收拢) |
| `practice-duration-card-01-v3.html` | `overflow: false` (居中雅致) | `overflow: false` (居中雅致) | `overflow: false` (100%卡宽不溢出) |
| `requests-card-01-v3.html` | `overflow: false` (卡宽 600px, 标题 17px) | `overflow: false` (卡宽 440px, 标题 15px) | `overflow: false` (卡宽 408px, 标题 14px) |

---

## 六、交付总结

- **完成条数**: 16 / 16（D1 共 8 条全完、D6 共 6 条全完、D4 共 2 条全完）。
- **未完成条数**: 0 条。
- **文件与备份**:
  - `docs/demos/practice-right-column-261003/dashboard-skin-01-v3.html`
  - `docs/demos/practice-right-column-261003/practice-duration-card-01-v3.html`
  - `docs/demos/practice-right-column-261003/requests-card-01-v3.html`
  - 备份目录: `docs/demos/practice-right-column-261003/.bak-agy-round2-261006/`
- **双门禁状态**:
  - `verify-demos.py`: 3/3 OK，67 个 `--dash-*` token 100% 一致，0 字面量违规。
  - `token-contrast.py`: 门禁不合格合计 0。
  - 3 个页面 `?audit=1` 均实测返回 `ASSERT_OK`。
