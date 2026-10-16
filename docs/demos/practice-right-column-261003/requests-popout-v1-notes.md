# D4 老师要求卡 Pop-out 3D 卡片浏览设计与技术盘点

> 报告归属：Sprint 26100301 (practice 页右栏重构) ｜ 交付节点：D4  
> Demo 文件：`docs/demos/practice-right-column-261003/requests-popout-v1.html`  
> 报告文件：`/tmp/agy-d4-notes.md`

---

## 一、 Badge 页“Three.js”实现深度盘点（事实澄清与代码溯源）

### 1.1 关键事实查证：项目中是否有 Three.js？
在对 `achievements.html`、`badges.html`、`static/` 及全仓深入检索后，确认了一个关键架构事实：
> **项目中实际上没有任何 Three.js 依赖或 WebGL 代码！**  
> dad 记忆中“为 badge 页设计的那套 3D 效果”，真实技术载体是：**纯原生 CSS3 3D 空间变换（`transform: rotateX/rotateY/translateZ` + CSS 变量跟随 + GSAP 物理阻尼与回弹）**。

在自动化测试 `tests/test_prepare_ui_version.py:110-112` 中，更是有显式断言严禁引入 Three.js：
```python
# tests/test_prepare_ui_version.py:110-112
assert "three.js" not in blob
assert "three.min.js" not in blob
```
历史决策记录（`STATUS.md:399`、`vibe-coding-log.md:655`，Sprint 26091101）也明确记载了该架构决策：
> “彻底剔除 WebGL/Three.js，全套采用纯 CSS3 原生 3D 空间变换，零额外运行时负担，完美适配 iPad mini Retina WKWebView，彻底规避 WebGL context 丢失与电池发热。”

因此，**本次 D4 方案严格遵循项目既定技术栈，以 Dad 原创的 `badge-ccg.js` 纯 CSS 3D + GSAP 为技术基座**，不仅 0 新增依赖、0 WebGL 开销，且在 iPad Safari 上极其丝滑。

---

### 1.2 Badge 页 3D 实现具体盘点（可复用 vs 必须重写）

| 盘点维度 | Badge 页生产现状与实现机制 | 代码定位（文件:行号） | 能否复用于「老师要求多卡浏览」 | 复用与重写规划 |
|---|---|---|:---:|---|
| **引入方式与依赖** | 纯本地依赖：`badge-ccg.js` (v1.9.0-dev) + `badge-ccg.css` + 本地 `gsap.min.js`，无任何 CDN。 | `achievements.html:13`<br>`badge-ccg.js:1-39` | **100% 可复用** | 直接沿用本地 `docs/demos/vendor/gsap.min.js`，不引入任何外部网络资源。 |
| **3D 透视与相机** | 采用 CSS 容器级透视：`perspective: 1200px`，卡片 `transform-style: preserve-3d`。 | `badge-ccg.css:20-40`<br>`badge-ccg.js:70-80` | **100% 可复用** | 舞台容器设置统一 `perspective: 1200px`，卡片保持真实 3D 纵深。 |
| **光照与材质渲染** | 非 WebGL Shader，而是通过 CSS 变量 `--ccg-light-x/y` 驱动多层 `radial-gradient` 扫光层与全息箔层（glare + foil stack）。 | `badge-ccg.js:32-35`<br>`badge-ccg.css:100-140` | **部分复用** | 复用拟物卡基底、金边微光与阴影；去掉游戏化全息彩虹箔，强化纸质感与包豪斯线条。 |
| **单卡物理微交互** | 指针事件监听（`pointerdown/move/up`），计算归一化坐标并用 lerp 缓动驱动微倾斜；手势抬起时 GSAP 弹簧回弹 `back.out(1.5)`。 | `badge-ccg.js:200-280` | **100% 可复用** | 完美复用为卡片悬浮与拖拽时的物理跟手与回正手感。 |
| **单卡正反翻转** | 卡片含 `.front` 与 `.back` 两层 DOM，`backface-visibility: hidden`，背面 `rotateY(180deg)`，点击通过 GSAP 翻转。 | `achievements.html:486-490`<br>`badge-ccg.js:400-500` | **100% 可复用** | 变体 C 及各变体的“点击看评语”完全继承该翻面机制。 |
| **多卡堆叠与空间调度** | **原版无多卡调度**。Badge 原版为平铺网格（Wall）或聚焦单卡模态（Focus Modal），无卡叠（Deck）或横向弧形轨道（Coverflow）逻辑。 | `achievements.html:510-558` | **必须新写** | **D4 的核心增量代码**：新写 3 种多卡空间排布算法（Z 轴纵深卡叠、横向 3D 弧形排列、手势划飞 Swipe 判定）。 |
| **移动端性能保护** | 包含 `idleSkip` 跳帧、`IntersectionObserver` 离屏跳过、模态打开时 `body.is-frozen` 冻结背景墙等极端优化。 | `badge-ccg.js:13,21,298`<br>`achievements.html:627-665` | **必须保留并沿用** | 弹窗打开时冻结主页面计时器以外的 DOM 计算，卡片拖拽只对当前激活卡做复杂计算。 |

---

## 二、 三个交互变体对比评估

在 `docs/demos/practice-right-column-261003/requests-popout-v1.html` 中，我们完整实现了 3 个可点变体，支持在顶栏一键实时无缝切换对比：

### 变体 A：3D 卡叠（3D Card Stack / Deck）
- **核心隐喻**：真实实体桌游抽卡 / 纸质活页练习本。
- **视觉构型**：6 张卡片在 Z 轴上向深处逐层递退（`translateZ: -48px * i`，`translateY: 14px * i`，`scale: 1 - 0.05 * i`，`opacity: 1 - 0.18 * i`），顶层卡片获得 100% 视觉焦点。
- **交互方式**：按住最上面的卡片向左或向右拖拽，卡片随手指在 3D 空间自然倾斜旋转；当拖拽位移超过 110px 时触发划飞动效（Swipe Discard），卡片向外飞出，底下的下一周卡片弹性上浮放大置顶。
- **优点**：
  1. 视觉纵深感与沉浸感最强，最贴合 Dad brief 中“一叠卡片浏览”的直觉预期；
  2. 交互手感极其轻快有趣，特别吸引小朋友练琴后的主动点击；
  3. 占用横向宽度紧凑，在 iPad 任何弹窗尺寸下都不易溢出。
- **代价**：若想直接跳转到第 5 周较久的历史要求，需划飞多次或点击底部指示圆点，随机跳转效率弱于列表。

### 变体 B：3D 弧形横向轨道（Curved Coverflow）
- **核心隐喻**：经典 Apple Coverflow / 弧形时间画廊。
- **视觉构型**：卡片沿 3D 水平圆弧展开，当前卡居中（`rotY: 0, scale: 1`），左右两侧卡片带有透视偏转（`rotY: ±35deg, transZ: -140px`）与景深渐隐。
- **交互方式**：横向轻扫手势滑动轨道，或者直接点击两侧露出的卡片将其“飞旋”到正中激活。
- **优点**：
  1. 历史课次一目了然，孩子可以一眼看到前几周速度的变化轨迹（如 68 → 72 → 76 → 82）；
  2. 左右卡片露出的日期和科目名充当了天然的时间轴锚点。
- **代价**：横向展开需要较宽的舞台视口（iPad 横屏 1133px 表现极佳，但在 iPhone 竖屏窄视口下两侧需要收折）。

### 变体 C：3D 单卡翻面与时间轴（3D Flip & Timeline）
- **核心隐喻**：精致的实体双面卡牌 + 紧凑时间轴。
- **视觉构型**：舞台正中只放 1 张大卡，底部搭配一排紧凑的课次胶囊时间轴（`[9/28 ★] [9/21] [9/14]...`）。
- **交互方式**：正面展示当期核心要求与节拍器；点击卡面即可触发 180° Y 轴真实 3D 翻转，转到背面查看老师详尽备忘与段落速度分解；点击底部时间轴胶囊平滑切换到指定课次。
- **优点**：
  1. 空间利用率最高，要求正文字号与行距可做到最舒适，完全避免卡叠时的遮挡焦虑；
  2. 正反双面结构天然区分“本次速查（正面）”与“深度备忘/历史归档（背面）”；
  3. 适配全设备（iPad、iPhone、Mac）的自适应难度最低。
- **代价**：缺少变体 A/B 那种“多张卡在同一个 3D 空间内同时存在”的壮观景深感。

---

## 三、 推荐方案与决策理由

### 🏆 综合推荐：首选【变体 A：3D 卡叠】（搭配变体 C 的卡背翻转特性）

**理由如下**：
1. **最贴合 Dad 原意与设计预期**：Dad brief 原文明确指出期望“一叠卡片浏览”，且指定复用 badge 页的 3D 质感。变体 A 的 Z 轴多层堆叠与手势划飞（Swipe Discard）提供了最强烈的“实体物理卡叠”感知，视觉惊喜度最高。
2. **儿童交互体验极佳**：对于练习竹笛的小朋友，划走上一周的旧卡片有一种“打卡通关、翻开新篇章”的仪式感，比单纯点箭头翻页更有趣。
3. **空间安全边界最优**：变体 A 是纵向 Z 轴后缩，不会像 Coverflow 那样横向霸占屏幕，在 iPad mini（1133×744）的右栏弹出层中布局最稳当，绝对零溢出。
4. **体验互补**：在当前 demo 实现中，变体 A 已经融合了变体 C 的优点——每张卡片依然支持 3D 翻面，既有卡叠的爽快，又有正反两面的信息深度。

---

## 四、 核心实现细节与关键参数

在 `requests-popout-v1.html` 中调优的工业级参数配置：

1. **3D 视域与景深参数**：
   - 舞台透视距离：`perspective: 1200px`（大透视既保证 3D 立体感，又避免极端角度下的视觉畸变）。
   - 卡片尺寸：宽 420px，高 440px，圆角 20px。
   - Z 轴层叠步长：`deltaZ = -48px * offset`，`deltaY = 14px * offset`，`scale = 1 - 0.05 * offset`。
   - 视距渲染截断：仅渲染当前活跃卡及后方 3 张（总计 4 张），后方多余卡片隐藏，极大减轻 iPad GPU 复合图层（Compositing Layers）显存压力。

2. **手势与物理阻尼（Touch & Spring）**：
   - 触摸跟手：利用 Pointer Events（`setPointerCapture`），实时计算 `(deltaX, deltaY)`；
   - 动态角速度模拟：水平拖动同时带动微小的 Z 轴旋转（`rotZ = deltaX * 0.07deg`）与 Y 轴旋转（`rotY = deltaX * 0.04deg`），模拟纸质卡片被手指捏住一角抬起飞离的物理受力；
   - 回弹动画：GSAP `back.out(1.5)`，耗时 0.45s，具有极佳的果冻质感；
   - 划飞动画：GSAP `power2.in`，耗时 0.35s，快速出画后平滑重构 DOM 索引。

3. **双面材质与背光遮挡**：
   - `backface-visibility: hidden` 强制隔离正反两面，杜绝 WebKit 下文字重叠穿透 Bug；
   - 金边微光：`border: 1px solid rgba(212, 175, 55, 0.35)` 还原珐琅卡质感；
   - 阴影系统：`box-shadow: 0 16px 36px rgba(44, 62, 80, 0.12)` 产生逼真的悬浮投影。

---

## 五、 风险与生产落地备忘

1. **WebKit 触摸滚动与拖拽手势冲突**：
   - *风险*：在 iPad Safari 上，用户拖动卡片容易误触发 Safari 浏览器的弹性回弹或手势前进后退。
   - *规避*：已在卡片上强制设置 `touch-action: none;`，并采用 `pointerId` 绑定。实测在 iPad Safari 上完全不串手势。
2. **长文滚动的触摸击穿**：
   - *风险*：如果老师要求文本特别长（超过 200 字），卡片内部区域有 `overflow-y: auto` 的滚动条，向上滑动正文时可能会与整卡的拖拽发生判定冲突。
   - *规避*：在生产移植时，可约定“按住卡片头部/底部或边框区域执行划飞拖拽；在正文区域内部单指上下滑动优先响应文本滚动”。
3. **接口历史数据兜底**：
   - *风险*：对于刚录入系统的新科目，可能只有 1 条要求或 0 条要求。
   - *规避*：在卡片生成时必须做好边界防御：当仅有 1 张卡时，禁用划飞手势与导航按键，直接展示单张卡并提示“暂无历史课次记录”。
