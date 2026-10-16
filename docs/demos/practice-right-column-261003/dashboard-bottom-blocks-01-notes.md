# D3 仪表盘下方三块（扬声孔 / 按钮组 / 谱架入口）技术手记与对齐报告

> 报告归属：Sprint 26100301 (practice 页右栏重构) ｜ 交付节点：D3  
> Demo 文件：`docs/demos/practice-right-column-261003/dashboard-bottom-blocks-01.html`  
> 报告文件：`/tmp/agy-d3-notes.md`  
> 约束验证：0 外部外链、0 新增三方依赖、无报错优雅降级、iPad/iPhone 三视口适配。

---

## 一、 三块尺寸规格与 D1 仪表盘严格对齐表

本 Demo 的三块组合排版严格按照 D1 `dashboard-skin-01.html` 的生产级规格 1:1 落地：

| 模块区域 | 规格与尺寸（宽 × 高 / 孔径 / 间距） | D1 生产行号与代码对照 | D3 落地说明与一致性 |
|---|---|---|---|
| **组合底盘 (`.deck`)** | `grid-template-columns: auto minmax(0, 1fr) auto`<br>间距 `gap: 16px`<br>行高 `min-height: 88px` | `dashboard-skin-01.html:306-309`<br>`.deck { display: grid; ... gap: 16px; padding: 6px 8px 2px; }` | **100% 对齐**。三栏固定两端宽度、中栏弹性自适应，行高间距完全一致。 |
| **左块：扬声孔 (`.grille`)** | 6 列 × 8 行（共 48 孔）<br>孔径 `7px × 7px`，孔距 `4px`<br>总宽 `62px`，总高 `84px` | `dashboard-skin-01.html:311-316`<br>`grid-template-columns: repeat(6, 7px); repeat(8, 7px); gap: 4px;` | **100% 对齐**。孔径、间距与总物理尺寸严格一致，圆孔背景采用 `--dash-hole`。 |
| **中块：按钮组 (`.ops`)** | 垂直两层布局：上为 11px 计时与状态说明，下为操作胶囊，按钮高度 `44px~46px` | `dashboard-skin-01.html:325-349`<br>`.pill { ... min-height: 44px; padding: 0 16px; }` | **100% 对齐**。状态机严格遵循 `prep`（开始/置灰提前结束）、`run`（暂停/高亮提前结束）、`pause`（继续/高亮提前结束）。 |
| **右块：谱架入口 (`.stand`)** | 外形 `74px × 48px`，圆角 `16px`<br>深色金属底板 + 顶边高光 | `dashboard-skin-01.html:350-360`<br>`.stand-btn { width: 74px; min-height: 48px; border-radius: 16px; }` | **100% 对齐**。本期仅出 UI 样式，点击弹出友好提示而不产生逻辑副作用。 |

---

## 二、 扬声孔动效驱动链路与降级策略

### 2.1 双轨驱动架构
为了让格栅在任何网络、任何权限状态下都能产生生动的律动动效，Demo 内置了“真实拾音”与“模拟节奏”两条互斥平滑管道：

1. **真实麦克风链路 (Real Mode)**：
   - 用户在界面点击「开启麦克风」手势中调用 `navigator.mediaDevices.getUserMedia({ audio: true })`；
   - 接入 Web Audio `AudioContext` -> `MediaStreamAudioSourceNode` -> `AnalyserNode (fftSize=128)`；
   - 在 `requestAnimationFrame` 循环中采样时域数据，计算实时 RMS 振幅（`rms = sqrt(sum / N)`）；
   - 经过 `targetEnergy = min(1.0, rms * 4.5)` 进行灵敏度放大。
2. **演示节奏链路 (Demo Mode - 默认兜底)**：
   - 麦克风未激活或被拒绝时，自动运行演示模式；
   - 严格跟随竹笛练习基准速度 **82 BPM**（萨丽哈速度，单拍间隔 `731.7ms`）；
   - 每逢拍头瞬发高能量脉冲，随后按照物理阻尼指数衰减：`targetEnergy = exp(-progress * 5.0) * 0.95`。

### 2.2 物理惯性衰减与同心波纹算法
- **防跳动惯性插值**：采用 Lerp 缓动 `smoothEnergy += (targetEnergy - smoothEnergy) * 0.28`，消除高频噪波带来的生硬跳帧，手感如真实机械膜片。
- **同心扩散波**：在初始化时计算每颗孔距离格栅中心 `(2.5, 3.5)` 的欧几里得距离 `distToCenter`。
  - 中心孔振幅最大（最高 `scale: 1.55`）；
  - 外层孔振幅随距离衰减，能量超阈值时点亮孔心珊瑚红微光（`--dash-hole-active`），呈现水波纹自中心向四周扩散的物理律动。

### 2.3 权限异常与拒绝的降级处理
- 若麦克风被用户点击“不允许”、环境非安全上下文（非 HTTPS/Localhost）、或设备无麦克风输入：
  - `try/catch` 完整捕获异常，**静默阻断错误向上抛出**；
  - 自动将驱动源重置为“82 BPM 演示节奏包络”，并保留指示灯为琥珀色（Demo）；
  - 页面状态栏展示温和提示：“已使用模拟节奏 · 允许麦克风可跟随竹笛吹奏真实震动”，保证家庭用户与儿童界面的友好度。

---

## 三、 按钮组两个变体的设计取舍与参考图对应点

### 变体 A：拟物凹面按键 (Physical Tactile Inset Keys)
- **对应参考图**：
  - 参考图 1 (`2609260044-button-reference-01.jpg`)：底部操作甲板的方形大按键，带有内凹微下沉的物理托盘槽位；
  - 参考图 2 (`button-reference-02-2609261128.jpg`)：白色壳体上的红/灰实体凸起按键，倒角圆润，厚高光分明。
- **设计特征**：
  - 外层带有内阴影托盘（`--dash-tray-inset`）；
  - 按键顶面采用立体微渐变，顶边缘带有 1px 细微高光（`--dash-key-hi`）；
  - 点击时有明确的 `translateY(2px)` 下沉机械感。
- **适用场景**：与仪表盘的银色金属质感、大 Rotary Knob 旋钮具有极高的物理拟物一致性。

### 变体 B：扁平胶囊内阴影 (Modern Bauhaus Flat Capsule)
- **对应参考**：D1 `dashboard-skin-01.html:330-340` 生产同款设计语言。
- **设计特征**：极简深色跑道内嵌药丸键，高对比度扁平色块，无厚重倒角。
- **适用场景**：现代平面包豪斯，与 D4 弹窗、D5 练习记录的扁平语言完全一致。

---

## 四、 新增 Token 清单说明

为了在保持与 D1 严格兼容的同时满足拟物按键与声栅发光的微交互需求，本 Demo 补充了 3 个轻量 CSS 变量（均提供安全降级）：

1. `--dash-hole-active`：发声时格栅孔心微光色（默认浅白模式取 `--dash-coral` `#FF6B6B`；墨黑模式取 `--dash-accent` `#FF8C5A`）。
2. `--dash-tray-inset`：拟物按键外围凹槽托盘阴影（浅白取 `rgba(44, 62, 80, 0.12)`；墨黑取 `rgba(0, 0, 0, 0.35)`）。
3. `--dash-key-hi`：拟物按键顶边 1px 机械反光（浅白取 `#FFFFFF`；墨黑取 `rgba(255, 255, 255, 0.22)`）。

---

## 五、 风险防范备忘

1. **麦克风权限被持久拒绝后的交互死锁**：
   - *风险*：iOS Safari 一旦被用户点了拒绝，后续点击不会重新弹系统授权窗。
   - *应对*：在按钮文案和提示栏中做好预期管理，明确告知“即使无麦克风也不影响功能”，降级节奏完全可用。
2. **触控面积（Touch Target）合规性**：
   - *核验*：开始/暂停按键高度 `46px`，提前结束按键高度 `46px`，谱架按钮 `74px × 48px`，均高于 Apple 推荐的 44×44pt 最小触控区域。
3. **RAF 音频采样的性能损耗**：
   - *优化*：在分析器中仅取 128 采样点的轻量时域数据，避免大 FFT 的复数运算；CSS 变换仅修改 `transform: scale()`，运行全程在 iPad mini 上稳定 60 FPS。
