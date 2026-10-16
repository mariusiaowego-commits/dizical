# spec-agy-container-bp-261015 · 容器查询纪律与 744/440 断点单列退化规格

> **文档归属**：Sprint 26100301 (practice 页右栏重构) ｜ 核心修复规格  
> **制定责任人**：agy ｜ 日期：2026-10-15  
> **上游依据**：
> - Dad 反馈文档：`PRDs/2610150930-demov3.3问题.md`（第 13 条、第 14 条）
> - 现场实测根因定位：`docs/demos/practice-right-column-261003/PLAN-demov33问题-261015.md`
>   - 744 档实测：票卡 `82,78 580×780` 与 A 仪表盘 `84,78 576×780` **严重压叠**（同顶同左）
>   - 440 档实测：票卡 `16,78 397×780` 与 A 仪表盘 `18,78 393×780` **严重压叠**（同顶同左）
>   - 三组合 ⨯ 744/440 全部压叠，页面总高度飙升至 2486px ~ 3285px！

---

## 1. 核心根因与前端架构纪律革新（Item 13 解决）

### 1.1 现状死板布局根因分析
Dad 第 13 条一针见血指出：
> *“记住：卡片如果按组合排布的，不要出现一个卡片固定宽高后里面进行移动，这样设计前端 layout 是不对的。”*

**现场实测代码死穴**：
1. **外层死锁固定高**：无论屏幕是 1133px、744px 还是 440px，脚本无差别给每张卡片硬套 `height: 780px`，导致窄屏下多张 780px 巨物相互重叠碰撞；
2. **定位机制崩溃**：外层容器在窄屏媒体查询下，右栏轨道与票卡没有切回普通文档流，依然使用绝对定位或固化 Grid 区域，导致票卡与右栏第一张卡（A 仪表盘）具有几乎完全相同的 `left` 与 `top`（$t=78\text{px}, l \approx 82\text{px}$）；
3. **卡内元素写死绝对坐标**：卡片内部为了应付组合，通过 `top: 32px; left: 44px;` 等硬编码位移生搬硬套，一旦外框尺寸变化，内容立即破框溢出。

### 1.2 现代 CSS 容器查询（@container）与流式排版纪律
从根本上重塑组件设计，**彻底禁止“固定盒 + 内部绝对定位挪移”**，强制推行以下三大纪律：

1. **容器查询化声明**：
   每个模块卡片外壳声明为尺寸查询容器：
   ```css
   .cz-card-shell {
     container-type: inline-size;
     container-name: moduleCard;
     width: 100%;
     box-sizing: border-box;
   }
   ```
2. **卡内布局一律采用 Flexbox 与 Grid 流式布局**：
   - 内部纵向排布一律采用：`display: flex; flex-direction: column; justify-content: space-between;`
   - 内部元素尺寸一律使用百分比、`flex: 1` 或 `clamp(min, val, max)`，禁止写死 `width: 409px; height: 405px`；
3. **响应式尺寸降级采用 `@container` 查询**：
   当卡片被放置在紧凑网格（如组合 1 卧排宽度仅 224px）时，由容器自身尺寸触发规则，而非全局媒体查询：
   ```css
   @container moduleCard (max-width: 280px) {
     .card-title { font-size: 13px; }
     .hero-metric { font-size: 32px; }
     .hide-on-compact { display: none; }
   }
   ```

---

## 2. 744 与 440 断点单列退化规则（Item 14 解决）

在移动端与平板竖屏视口下，彻底摒弃横向等高硬锁定，转为标准的**垂直单列流式（Vertical Single-Column Flow）**。

### 2.1 视口断点与布局形态划分

| 视口档位 | 代表设备 | 容器布局模式 | 票卡与模块排布关系 | 卡片高度策略 |
|---|---|---|---|---|
| **> 1024px** | iPad 横屏 (1133) / 桌面 Mac (1280) | **双栏等高横排** | 左栏票卡 + 右栏横向滚动/紧凑轨道 | 严格闭合等于票卡高 $H = 780\text{px}$ |
| **≤ 1024px**<br>(重点 744 档) | iPad mini / iPad 竖屏 (744×1133) | **垂直单列流动** | **票卡居首，右栏模块垂直顺延** | **内容自适应高（严禁 780px！）** |
| **≤ 480px**<br>(重点 440 档) | iPhone 17 / 手机竖屏 (440×956) | **极窄单列流动** | **票卡居首，右栏模块垂直顺延** | **紧凑自适应高（严禁 780px！）** |

---

### 2.2 744 档（iPad 竖屏 744×1133）具体几何规范

当视口宽度进入 `744px` 档位时：
1. **外层舞台样式**：
   ```css
   @media (max-width: 1024px) {
     .practice-stage-container {
       display: flex !important;
       flex-direction: column !important;
       width: 100% !important;
       padding: 24px 20px !important;
       gap: 20px !important;
       overflow-x: hidden !important;
       position: static !important;
     }
     .left-ticket-col, .right-module-col {
       position: static !important;
       width: 100% !important;
       max-width: 640px !important;
       margin: 0 auto !important;
     }
     .cz-rail, .cz-fill {
       display: flex !important;
       flex-direction: column !important;
       gap: 16px !important;
       width: 100% !important;
     }
   }
   ```
2. **顺序与高度动态分配（消灭 780px 虚胖）**：
   - **Order 1 · 票卡 `.pk-ticket`**：
     - 宽度：`100%`（居中，实测约 $580\text{px}$）；
     - 高度：按内容自然收敛，高度约为 **$460\text{px} \sim 500\text{px}$**；
   - **Order 2 · A 仪表盘**：
     - 位于票卡正下方（$\text{top}(A) = \text{bottom}(\text{ticket}) + 20\text{px}$）；
     - 高度：自适应紧凑高度 **$380\text{px} \sim 420\text{px}$**；
   - **Order 3 · D 时长卡**：
     - 位于 A 正下方，高度收敛为横幅条状 **$160\text{px} \sim 180\text{px}$**；
   - **Order 4 · R 记录小卡**：
     - 位于 D 正下方，高度 **$140\text{px} \sim 160\text{px}$**；
   - **Order 5 · S / B 节拍器**：
     - 位于 R 正下方，高度 **$200\text{px} \sim 240\text{px}$**；
3. **消除重叠判定**：
   所有模块 `left` 均对齐在舞台居中轨道（$l \approx 52\text{px} \sim 82\text{px}$），但每一个模块的 `top` 必须**严格大于上一个模块的 `bottom`**，重叠面积完全归零！

---

### 2.3 440 档（iPhone 竖屏 440×956）具体几何规范

当视口宽度进入 `440px` 档位时：
1. **外层舞台样式**：
   - 左右外边距紧凑化：`padding: 16px 12px`；
   - 宽度满铺：各卡片 `width: 100%`（计算宽度约 $416\text{px}$）；
2. **单列极简自适应高度分配**：
   - **票卡**：高约 **$420\text{px} \sim 450\text{px}$**；
   - **A 仪表盘**：孔阵与表盘进入单列居中紧凑模式，高约 **$320\text{px} \sim 350\text{px}$**；
   - **D 时长卡**：高约 **$140\text{px}$**；
   - **R 记录小卡**：高约 **$120\text{px}$**；
   - **S / B 节拍器**：高约 **$180\text{px}$**；
3. **页面总滚动高度收敛**：
   整页从头到底顺畅向下滚动，总文档高度控制在 $1200\text{px} \sim 1500\text{px}$，彻底杜绝之前 `docScrollHeight = 3285px` 的巨大虚空空白！

---

## 3. 可量判据（Price-Tag Verification Criteria）

在 744 与 440 视口下运行自动化测试，必须满足以下硬性物理价签：

1. **零重叠铁律（Zero-Collision Law）**：
   在 744×1133 与 440×956 视口下，对三套组合下的所有可见卡片集合 $\{C_1, C_2, \dots, C_n\}$（包含左栏票卡）：
   $$\forall i \ne j, \quad \text{Intersection}(\text{Rect}(C_i), \text{Rect}(C_j)) \equiv \emptyset \quad (\text{相交面积绝对为 } 0\text{px}^2)$$
   $$\text{即：} \quad \text{bottom}(C_i) + 12\text{px} \le \text{top}(C_{i+1})$$
2. **严格单列垂直次序（Strict Vertical Sequence）**：
   票卡顶边必须在最前，后续模块依序向下排列：
   $$t(\text{ticket}) < t(\text{mod}_1) < t(\text{mod}_2) < \dots < t(\text{mod}_n)$$
3. **消除虚空巨高（Doc Height Containment）**：
   - 744 档：整个页面 $\text{document.documentElement.scrollHeight} \le 1650\text{px}$（彻底消灭 3285px 异常）；
   - 440 档：整个页面 $\text{document.documentElement.scrollHeight} \le 1450\text{px}$（彻底消灭 2486px 异常）。
4. **单卡高度脱落 780px 铁证**：
   在 744 与 440 档位下，任意单张卡片计算高度必须满足：
   $$h(C_k) < 600\text{px} \quad (\text{严禁任何单卡在窄屏下被强行赋予 } 780\text{px})$$
