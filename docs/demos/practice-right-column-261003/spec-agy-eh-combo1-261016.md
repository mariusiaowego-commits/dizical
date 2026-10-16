# spec-agy-eh-combo1-261016 · 组合 1 有限高下 A 卡内部重排规格

> **文档归属**：Sprint 26100301 (practice 页右栏重构) ｜ 核心规范  
> **制定责任人**：agy ｜ 日期：2026-10-16  
> **上游依据**：
> - Dad 反馈文档：`tqob/PRDs/2610160819-demov3.4问题.md`（第 1 条、第 6.1 条、第 7.1 条）
> - 现场实测根因：`docs/demos/practice-right-column-261003/PLAN-demov34问题-261016.md`（组合 1 A 卡 460×331 宽扁比 1.39，内部三段硬挤错位）

---

## 1. 现象根因与两套比例形态定义（Item 1 & 6.1）

### 1.1 现状严重错位根因
在组合 1 中，为了与左栏等高闭环，A 仪表盘的高度被限制在 **$331\text{px}$**，宽度为 **$460\text{px}$**（宽/高比 $\approx 1.39 \ge 1.3$，属于典型的**宽扁矮盒**）。  
**原代码严重错误**：仍然机械地沿用组合 3 高瘦盒（430×586，宽/高比 0.73）的**自上而下纵向三大段堆叠逻辑**：
- 顶部黑区 `#panel`（高 140px）
- 中间旋钮与弧点 `#mid`（高 130px）
- 底部控制甲板 `#transport`（高 130px）
- 总需高度：$140 + 130 + 130 = 400\text{px} > 331\text{px}$！

**导致的视觉崩塌现象**（Dad 现场直斥）：
1. **黑色主屏未居中**：在 flex-shrink 挤压下 `#panel` 左右偏移，中轴偏离；
2. **Knob 旋钮严重错位**：纵向空间不够，旋钮被强行往上推，直接撞进黑区下边缘；
3. **旋钮上叠了一层奇怪东西**：为了修补缩放，代码加入了绝对定位的兜底层，产生了一个 `pointer-events: none` 的阴影/浮层半遮盖了旋钮；
4. **弧点 `#arc` 严重走形**：圆弧半径与旋钮物理圆心脱节，弧点甚至落到了旋钮背后或错位到一旁。

---

## 2. 容器查询阈值与两套形态规则

A 卡必须通过容器查询（Container Query）在“宽扁紧凑形态”与“近方舒展形态”之间进行彻底的结构重构：

```css
.dash-card-container {
  container-type: size;
  container-name: dashCard;
  width: 100%;
  height: 100%;
}
```

### 2.1 判定阈值定义
- **形态 A · 宽扁紧凑形态（Compact Landscape）**：
  $$\text{aspect-ratio} \ge 1.25 \quad \text{或} \quad \text{height} \le 380\text{px}$$
  （典型场景：组合 1 宽 460×高 331px、宽屏半高仪表盘）。
- **形态 B · 近方舒展形态（Standard Portrait）**：
  $$\text{aspect-ratio} < 1.25 \quad \text{且} \quad \text{height} > 380\text{px}$$
  （典型场景：组合 2/3 宽 430×高 586px、独立通高仪表盘）。

---

## 3. 宽扁紧凑形态（组合 1）内部分区与重排方案

在高度仅 $331\text{px}$ 的宽扁盒内，**坚决废除纵向三段堆叠**，改为**上屏（黑屏）+ 下操纵台（左右横排 3 栏）**的紧凑结构：

```
┌────────────────────────────────────────────────────────┐ 460px 宽
│ [内嵌卡槽 Inset Slot]   382px × 36px                    │
│ ┌────────────────────────────────────────────────────┐ │
│ │  #panel 黑色主屏 (高度 120px，水平严格居中)         │ │
│ │  [萨丽哈头像 36px]   [空心数字 08:26]   [BPM 82]    │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 下操纵台 (横向 3 栏并排，高度 130px)                │ │
│ │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │ │
│ │ │ 左栏: 孔阵   │ │ 中栏: 旋钮   │ │ 右栏: 主按纽 │ │ │
│ │ │ #speaker-    │ │ #knob (56px) │ │ [开始/检票]  │ │ │
│ │ │  Grille 56px │ │ #arc 同心圆弧│ │ 谱架按键     │ │ │
│ │ └──────────────┘ └──────────────┘ └──────────────┘ │ │
│ └────────────────────────────────────────────────────┘ │
│ 诊断行: 极简点状状态灯 (高 20px，无白底，紧贴底衬)     │
└────────────────────────────────────────────────────────┘ 总高 331px
```

### 关键组件调整细则：
1. **黑色主屏 `#panel` 绝对居中**：
   - 尺寸锁定：`width: 420px; height: 120px; margin: 6px auto;`
   - 居中规则：`align-self: center; margin-left: auto; margin-right: auto;`
   - 内容紧凑化：封面头像缩至 36×36px；空心大数字保持 32px 清晰可读；标尺 ruler 改为微型滑条或纯数字展示。
2. **下操纵台（横向 3 列流式排布）**：
   - 布局：`display: grid; grid-template-columns: 100px 1fr 120px; height: 130px; align-items: center;`
   - **左列**：`#speakerGrille` 孔阵紧凑化（$56\text{px} \times 56\text{px}$），居中排布；
   - **中列（旋钮同心区）**：
     - `#knob` 直径设为 **$56\text{px}$**；
     - `#arc` 弧点采用相对旋钮中心绝对定位：
       ```css
       .arc-track {
         position: absolute;
         top: 50%; left: 50%;
         transform: translate(-50%, -50%);
         width: 88px; height: 88px; /* 比 knob 大一圈，形成同心环 */
         pointer-events: none;
       }
       ```
     - **彻底消除旋钮上方的遮罩层**：检查并移除所有覆盖在 `#knob` 上的绝对定位 `.mask`、`.knob-overlay` 或调试残留层，保证旋钮视觉光洁、触控直接生效。
   - **右列**：放置主操作检票/开始胶囊按钮（高 40px）与谱架按键。
3. **底部诊断区 `#diagCard`**：
   - 高度固定为 $20\text{px}$，背景完全透明（`background: transparent`），仅保留绿/黄微型 LED 状态灯与极简文字。

---

## 4. 近方舒展形态（组合 3）内部分区规则

当高度 $> 380\text{px}$ 时，自动切回经典纵向舒展布局：
1. `#panel` 黑色主屏高度舒展为 $150\text{px} \sim 165\text{px}$，封面图与标尺尺标全量展示；
2. `#mid` 旋钮区垂直舒展（高度 $130\text{px} \sim 150\text{px}$），旋钮直径 $72\text{px}$，弧点同心环直径 $110\text{px}$，左右两侧配有时长加减圆钮；
3. `#transport` 底部甲板垂直向下顺延（高度 $140\text{px} \sim 160\text{px}$），孔阵全量 $72\text{px} \times 72\text{px}$；
4. 各模块垂直边距均匀呼吸，无任何重叠挤压。

---

## 5. 可量判据（Price-Tag Verification Criteria）

在宽扁形态（460×331px）下运行自动化测量，必须满足以下价签：

1. **黑色主屏水平绝对居中**：
   $$|\text{midX}(\text{panel}) - \text{midX}(\text{card})| \le 1.0\text{px}$$
2. **旋钮与弧点同心对齐**：
   $$|\text{midX}(\text{knob}) - \text{midX}(\text{arc})| \le 1.0\text{px}$$
   $$|\text{midY}(\text{knob}) - \text{midY}(\text{arc})| \le 1.0\text{px}$$
3. **旋钮无覆盖层铁证**：
   通过 `document.elementFromPoint(knob.midX, knob.midY)` 探测顶层元素，其返回值必须为 `#knob` 或其子节点 `.knob-rotor`，严禁命中任何 `.overlay` 或 `.mask`。
4. **卡内零溢出与零内滚**：
   $$\text{card.scrollHeight} \le \text{card.clientHeight} \quad (\text{绝对无纵向滚动条})$$
5. **最小字号保障**：
   卡内所有可见文本标签计算字号 $\ge 11\text{px}$，空心计时大字 $\ge 28\text{px}$。
