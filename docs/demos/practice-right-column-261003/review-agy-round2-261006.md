# Round 2 交付评估与实测报告 (261006 / 261008 更新)

> **任务标识**: Round 2 (dad 2610062214 反馈落地 + grok/hermes 独立复核项闭环)  
> **执行 Agent**: agy  
> **交付文件**:
> 1. `dashboard-skin-01-v3.html` (D1 全 8 条 + P0 步进单位 + P1 同心与列对齐 + P1e 自然计时开花实测 + P2 移除 emoji)
> 2. `practice-duration-card-01-v3.html` (D6 全 6 条 + 34px 细胶囊发丝轨 + 包豪斯双图标单线重画 + 真实深浅换肤与三档宽 + 时钟字体现状说明)
> 3. `requests-card-01-v3.html` (D4 全 2 条，三档卡宽真实互不相等 + 拖动单层无重影)
> **备份目录**: `docs/demos/practice-right-column-261003/.bak-agy-round2-261006/`

---

## 一、条目实测对比总表（含 Grok 复核项闭环）

| 卡片 | 编号 | 需求要点 | 现象 | 根因分析 | 修复方案 | 改前数字/状态 | 改后实测数字/状态 | 证据定位 |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **D1** | **P0** | 步进单位修正与标签同步 | 点一次「−」，分钟标签不动，内部时长跳到 30 | `applyDuration` 将 `nextMin * 60` (秒) 送进 `RulerProduction.setDuration`，触发 `MAX_MIN=30` 夹紧；且 `metaVal` 读数层被旧状态覆盖 | 统一以分钟为单位送入 `setDuration(nextMin)` 并比对 `duration !== nextMin`，在调用后统一更新 `metaVal` 与滚轮 | 点一次 − 内部变成 30，屏幕仍显 10 分钟 | **点一次 − 精确由 10 变为 9 分钟** (`meta=9分钟`, `rulerDur=9`)；两端对称平滑夹紧 1 与 30 | `dashboard-skin-01-v3.html:992-1008` |
| **D1** | 1.1 | 开始后默认静音 | 点击「开始准备」后立即发出节拍器蜂鸣 | 计时器 `tick` 默认直接触发 Web Audio 合成器 | 计时器默认静音，发声由 panel-foot 独立开关触发；foot 显示 `♩=82 · 静音` | 开始即发声 (`audioRunning=running`) | `defaultMuted=true`, `audioRunning=none` | `dashboard-skin-01-v3.html:790-820` |
| **D1** | 1.2 / P1e | 运行态气泡与自然生花实测 | 运行态刻度尺气泡从不冒出；花纹未随进度生长；旧 audit 自行拨进度造假 | `setRunningModality` 仅改文案；生产依赖每秒计时循环驱动 `paintRulerRunning` + `revealVine` + `emitBubbles`；旧断言手动调 `revealVine(0.35)` | 对齐生产 1000ms 计时循环全套驱动；audit 采用纯自然 5 秒走时，不手动设置进度 | 气泡 opacity 恒为 0；audit 靠人工拨进度测 6 朵花 | **5s 自然计时实测**：气泡真实冒出 (max opacity = 1.0 > 0.05)，花朵由 0 朵自然生长至 2 朵 (`vineGrows=true`) | `dashboard-skin-01-v3.html:1100-1145, 1260-1280` |
| **D1** | 1.3.1 / P1a | panel 底缺口与 dot 弧绝对同心 | 缺口弧度与点弧不平行，两圆心存在物理偏移 | 面板遮罩缺口 Y 轴中心写死偏移量，未绑定旋钮真实中心 | 动态计算 `--notch-center-y: ${kcy - pRect.top}px`，两弧严格共用绝对同心圆体系 | 1133 视口圆心差 **49px**，744 视口差 **32px** | **同心偏离度 = 0.0px** (两圆心绝对重合) | `dashboard-skin-01-v3.html:915-923, 1212-1226` |
| **D1** | 1.3.2 | 1 点 = 1 步进，指针落点对齐 | 指针旋转与圆点位置脱节 | 浮点角度与离散点索引未对齐 | 锁定离散角度公式 $\theta = -120^\circ + (step-1) \times (240^\circ/29)$，指针精准对准对应圆点 | 连续漂移未对齐 | 30 步一一对应，指针绝对落点重合 | `dashboard-skin-01-v3.html:928-938` |
| **D1** | 1.3.3 | 指针起点 20:00 至 4:00 (1~30分) | 计时范围为 0~60 分钟 | 未按照硬件旋钮业务范围约束 | 锁定起始角 -120° (20:00) 到终止角 +120° (4:00)，1 分钟/步，范围 1~30 分钟 | 0~60 min 任意刻度 | 1~30 min，总张角 240°，30 点 | `dashboard-skin-01-v3.html:890-935` |
| **D1** | 1.4 / P1b | mid-row +/- 外缘对齐 | `−` 和 `+` 悬浮在两侧，与 panel-foot 外缘错位 | 顶栏、中排与底栏各自使用独立 flex 间距 | 为 `.mid-row` 引入补偿边距 `--mid-pad: 8px` (744下 6px)，对齐 44px 按钮与底栏 | 1133 错位 **8px**，744 错位 **6px** | **左侧外缘差 = 0.0px，右侧外缘差 = 0.0px** | `dashboard-skin-01-v3.html:362-375, 1228-1240` |
| **D1** | 1.5 / P1c | 744×1133 下纵向舒展重排 | 竖屏视口下表盘局促，上方被压缩，下方空洞 | 仅使用统一宽度缩放，无纵向断点流 | 引入 `data-vp="744x1133"` 深度纵向重排：压缩顶部 (`cover: 68px, ac-root: 44px, gap: 10px`)，将空间让渡给旋钮 (176px)、弧线 (290px)、按钮 (50px) | panel-main 仅增高 24px，中间极空 | 独立重排流，空间重点交予旋钮与交互区 | `dashboard-skin-01-v3.html:565-600` |
| **D1** | 1.6 | 移除 speaker-block 外框 | 扬声孔外周有一圈多余的装饰线框 | 人工添加了装饰性 border 与 box-shadow | 剔除所有线框与外壳，保留纯粹 6×8 极简沉头打孔排布 | 带有 1.5px 边框与阴影 | 0 边框，纯孔位矩阵沉头 | `dashboard-skin-01-v3.html:473-490` |
| **D1** | 1.7 | 下方三块并入 D1 卡下半区 | 仪表盘与下方扬声孔/谱架/诊断区断裂成两张卡 | 架构早期将 D3 独立为卡片拆分 | 将 `diag-card`、`control-strip` 与 `speaker` 整合进 D1 卡底座机壳内，形成完整中控台 | 2 套分离独立卡 | 1 体化硬件中控台机身 | `dashboard-skin-01-v3.html:648-692` |
| **D1** | 1.8 / P1d | 麦克风入口真实采集与诚实占位 | 缺少麦克风控制入口；或声称采集中实际未调 API | 缺少状态栏定义；API 调用未真实连接 | 顶部状态栏增加 MIC 按钮；调用真实 `getUserMedia`；若失败诚实显示「未接麦克风 (示意占位)」 | 无入口 / 虚假采集文案 | 真实麦克风接入 + 诚实占位回退 | `dashboard-skin-01-v3.html:940-989` |
| **D1** | **P2** | 移除 diag toast 内闪电符号 | 诊断浮层提示带有一枚 emoji 闪电 | 使用了 `⚡` emoji 字符 | 替换为纯文字标签 `<span class="toast-tag">提示:</span>` | 包含 `⚡` emoji | 0 emoji，纯语义文字 | `dashboard-skin-01-v3.html:538, 770-776` |
| **D6** | 4.1 / P2-3 | 真实深墨与浅银换肤响应 | 浅银按钮点击后卡片背景色不变，仍为深黑色 | `:root` 与 `[data-skin="ink"]` 下 `--dash-panel` 均写死深炭色 | `.card-wrap` 采用 `--dash-surface-soft` (深墨 `#1A1E22`，浅银 `#FFFDFB`)，文字/图标采用 `currentColor` | 点击浅银背景不变 (恒为黑) | **深墨 rgb(26,30,34) ↔ 浅银 rgb(255,253,251) 真实切换** (`skinResponsive=true`) | `practice-duration-card-01-v3.html:176-184, 435-442` |
| **D6** | 4.2 / P1-6 | 34px 细长圆胶囊时间轴与发丝线 | 进度轨高度过大 (58px / 17.8%)，与参考图细胶囊不符 | 沿用了通用进度条分段排布，容器过高 | 重构为 **34px 全圆角胶囊** (`border-radius: 999px`, 占卡高 12%)；内嵌 **2px 发丝细白线** (`.session-seg-white`) 与 1px 虚线基准线 | 轨高 58px (17.8% 卡高) | **轨高 34px (12.0% 卡高)**，细长胶囊 | `practice-duration-card-01-v3.html:240-285` |
| **D6** | 4.3 / P1-7 | 空心细体时钟与字体情况说明 | 时钟为描边 SVG 而非原生细体字 | 生产无三方 webfont 依赖；原生字体无特定几何字形 | 采用零依赖 SVG Monoline 高精度复刻原图字形（斜穿 0、双环 8、几何 2、单线 6）；如实说明原生字体局限 | 粗重字体 / 缺少说明 | 高精度矢量中空时钟 + 规范说明（见第二节） | `practice-duration-card-01-v3.html:348-370` |
| **D6** | 4.4 | 逐元素深墨与浅银对比度合格 | 深色背景下部分暗灰文字看不清 | 直接沿用浅色文字透明度 token | 逐元素实测 WCAG AA：正文使用 `--dash-text` (对比度 16.5:1)，浅银下 11.2:1；门禁 0 违规 | 墨黑下对比度 < 2.5 | 所有元素实测对比度: 正文 ≥ 4.5, 大字 ≥ 3.0 (门禁 0 NG) | `practice-duration-card-01-v3.html:70-145` |
| **D6** | 4.6 / P1-8 | 包豪斯单线矢量双图标重画 | 图标形体偏简，皇冠带有发光阴影违背 prompt | 使用了带有 `filter: drop-shadow` 的通用图案 | 严格依 prompt 纯线重画：平顶等腰梯形+水平底线+纯竖直单摆+摆心小圆点；皇冠平底+锐角三峰（中峰略高）；无任何发光渐变；1.5px 线宽，12px 间距 | 带发光阴影，单摆倾角过大 | **纯二维 monoline 矢量**，1.5px 线宽，间距严格 12px (`iconGap=12`) | `practice-duration-card-01-v3.html:393-412` |
| **D6** | **P2-3** | 三档设备宽度真实切换 | 无论点击哪档按钮，卡宽一直写死 380px | 未向卡片派发不同视口宽度 | 支持 1133 大屏 (480px)、744 契约 (380px)、440 手机 (340px) 真实切换 | 三档宽度均为 380px | **实测宽度: 480px / 380px / 340px 真实变化** | `practice-duration-card-01-v3.html:426-433, 482-493` |
| **D4** | 3.1 | 三档视口真实尺寸与排版 | 视口切换仅改外框，卡宽不变 (440px) | chassis 宽度写死 440px，未做视口联动 | 绑定视口卡宽：1133→600px / 744→440px / 440→408px；标题字号 17→15→14px，正文 14.5→13.5→12.5px 联动收紧 | 三档宽度皆为 440px | 实测 $w_{1133}=600, w_{744}=440, w_{440}=408$ (互不相等) | `requests-card-01-v3.html:218-249, 1029-1040` |
| **D4** | 3.2 | 拖动重影与卡顿根除 | 拖动时多张半透明残影向左上错位，帧率下降 | 拖动时深层卡片未隐藏，叠加 3D 透视与半透明阴影产生重影 | 拖动期间通过 `.is-deck-dragging` 完全隐藏其他卡片（仅 1 张跟随指针）；使用 GPU 加速 `translate3d`；松手落定 | 4 张卡同时位移带残影 | 拖动期可见层数 = 1 (≤ 2)，松手后残影层 = 0 | `requests-card-01-v3.html:298-315, 800-870` |

---

## 二、专项几何与设计说明

### 1. 《科目卡片参考-04.jpg》现场几何测量实录
使用 Python PIL 模块在原图 `科目卡片参考-04.jpg`（**4096 × 4096**）高精度裁切测量：
- **圆心体系**：表盘黑色面板底部凹弧圆心与物理旋钮中心重合于 $(2048, 1720)$。
- **半径体系**：面板凹弧半径 $R_{panel} \approx 932\text{ px}$（前端映射约 $136\text{ px}$）；圆点弧半径 $R_{dot} \approx 655\text{ px}$（映射约 $96\text{ px}$）；物理旋钮半径 $R_{knob} \approx 512\text{ px}$（映射约 $75\text{ px}$）。
- **比例关系**：$R_{dot} / R_{panel} \approx 0.702$，$R_{knob} / R_{dot} \approx 0.781$。
- **圆点数量与张角**：有效圆点恰为 **30 颗**；起点 **20:00**（-120°），终点 **4:00**（+120°），总张角 **240°**，单步进角 $\Delta\theta = 240^\circ / 29 \approx 8.2758^\circ$。
- **同心验证结论**：在前端通过动态计算 `--notch-center-y: ${kcy - pRect.top}px`，实测圆心距差从 49px 降至 **0.0px**。

### 2. 《19aebf0e...jpeg》时间轴与时钟字体说明
- **橙色时间轴胶囊实测**：
  原图（1024×1024）中卡片高度 667px，橙色区域高 123px，内部白线位于 y=625，厚度约 4~5px。在前端 284px~320px 高度卡片中，我们将胶囊高度压缩为 **34px**（卡高的 12.0%），内嵌 **2px 发丝细白线** 与 1px 虚线，完全符合 dad 指示的「高度很小的细长圆胶囊」。
- **时钟字体情况如实说明**：
  参考图使用的是专用包豪斯中空线框字体（含对角线穿通 0、双环 8、几何拱顶 2）。在 Web 前端**不引入外部三方 webfont** 的硬约束下，系统原生字体（即便是 SF Pro Display Ultralight）无法原生提供这种特殊的几何字形拓扑。本方案采用高精度的 **SVG Monoline 矢量绘制** 忠实重现参考图外观，并将其文字描边与填充绑定至 `currentColor`，随深墨/浅银皮肤自适应翻转；若未来引入专用 woff2，代码结构已做好同级替换准备。

---

## 三、门禁实测输出

### 1. 通用审计门禁 (`verify-demos.py`)
```
=== demo 通用审计 ===

OK dashboard-skin-01-v3.html  (47340 B)
    非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
    未定义 token 无 / JS 通过 / 写死超宽值 无
    共享尺子 引用 有 / markup 有
    旧文字色 (--dash-ink/--dash-muted 当 color) 0  OK

OK practice-duration-card-01-v3.html  (18819 B)
    非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
    未定义 token 无 / JS 通过 / 写死超宽值 无
    共享尺子 引用 无 / markup 无
    旧文字色 (--dash-ink/--dash-muted 当 color) 0  OK

OK requests-card-01-v3.html  (33396 B)
    非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
    未定义 token 无 / JS 通过 / 写死超宽值 无
    共享尺子 引用 无 / markup 无
    旧文字色 (--dash-ink/--dash-muted 当 color) 0  OK

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
  （跳过无 token 页：index.html）
```

### 2. 对比度门禁 (`token-contrast.py`)
```
=== dashboard-skin-01-v3.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）

=== practice-duration-card-01-v3.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）

=== requests-card-01-v3.html ===
  [light] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）
  [ink] 门禁 25 组 → 不合格 0；OPEN 3 组（不计门禁）

→ 门禁不合格合计：0
```

---

## 四、页内契约自检 (`?audit=1`) 浏览器执行实测

### 1. `dashboard-skin-01-v3.html?audit=1`
```json
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
  "noHOverflow": true,
  "liveRun5sNatural": {
    "bubbleSeen": true,
    "maxBubbleOpacity": 1,
    "initialBloomed": 0,
    "finalBloomed": 2,
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
  "railHeight": 34,
  "cardHeight": 284,
  "railRatio": 0.12,
  "whiteSegs": 3,
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
| `dashboard-skin-01-v3.html` | `overflow: false` (对齐 0px 偏差) | `overflow: false` (空间聚焦表盘与中控) | `overflow: false` (单列流式收拢) |
| `practice-duration-card-01-v3.html` | `overflow: false` (宽 480px) | `overflow: false` (宽 380px 契约) | `overflow: false` (宽 340px 手机无横溢) |
| `requests-card-01-v3.html` | `overflow: false` (宽 600px, 标题 17px) | `overflow: false` (宽 440px, 标题 15px) | `overflow: false` (宽 408px, 标题 14px) |

---

## 六、交付总结

- **完成条数**: 16 / 16 项全部达成并实测通过（含 Grok 复核指出的 P0 步进单位、P1 同心度、P1 列对齐、P1 自然计时断言、P2 闪电符号清除，以及 D6 细长胶囊重构、包豪斯双图标单线重画、真实双色换肤与三档卡宽）。
- **未完成条数**: 0 条。
- **双门禁状态**:
  - `verify-demos.py`: 全部 demo 页 OK，68 个 `--dash-*` token 100% 一致，0 字面量违规。
  - `token-contrast.py`: 门禁不合格合计 **0**。
  - 3 个页面 `?audit=1` 均实测返回 `ASSERT_OK`。
