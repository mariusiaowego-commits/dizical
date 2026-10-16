# spec-agy-records-card-261015 · 今日练习记录小卡与 Popout 弹窗规格

> **文档归属**：Sprint 26100301 (practice 页右栏重构) ｜ 核心修复规格  
> **制定责任人**：agy ｜ 日期：2026-10-15  
> **上游依据**：
> - Dad 反馈文档：`PRDs/2610150930-demov3.3问题.md`（第 9 条、第 10 条）
> - 现场实测根因定位：`docs/demos/practice-right-column-261003/PLAN-demov33问题-261015.md`
> - 既有参考：`docs/demos/practice-right-column-261003/practice-duration-card-01-v3.html`、`docs/demos/practice-right-column-261003/requests-popout-v1-v2.html`

---

## 1. 核心定位与设计同族继承（Item 9 & 10 解决）

### 1.1 核心定位革新
原今日练习记录卡试图在紧凑的右栏中强行塞入完整的历史记录列表与折叠交互，导致展开后卡片破框、下方出现大面积毛玻璃模糊遮罩（`.records-blur-mask`），严重遮挡其他功能模块且无法阅读。  
根据 Dad 第 9、10 条明确指示：
1. **取消原长列表卡片形态**，严禁在卡片内就地展开；
2. **彻底废除下方模糊层（Blur Mask）**；
3. **今日记录卡（R）本体降维为精炼的“小卡片”**，仅做今日成果数据摘要与点击触发器；
4. **点击小卡后通过 Popout 浮层弹窗展示完整练习记录**；
5. **R 小卡的视觉 UI 完整继承今日时长卡 D（`practice-duration-card-01-v3`）的包豪斯拟物同族风格**。

### 1.2 同族设计 Token 继承清单
R 卡不再使用孤立的简陋白底或突兀的第三方样式，必须与 D 时长卡共享同一套设计语言和视觉资产：

| 设计要素 | 继承自 D 卡 (`practice-duration-card-01-v3`) 的 Token | 具体取值与实现 |
|---|---|---|
| **外壳背景** | `--dash-shell-lo` / `--dash-panel` | 浅色外包壳 `#E8E5E0` 内嵌深炭黑表盘 `#161A1E`，或一体化高质感深炭底色 |
| **主边框与圆角** | `--dash-radius` / `--dash-cover-line` | 圆角 `border-radius: 24px`，外带 1px 细发丝边框 `rgba(255, 255, 255, 0.12)` |
| **文字排版系统** | `--font-base` / `--font-mono` | 标题为标准无衬线屏显字体，数字为等宽排版（`font-variant-numeric: tabular-nums`） |
| **主读数展现** | 巨大数字居中 + 附标标签 | 大号完成数字（`font-size: 36px ~ 42px`，大字重 800）+ 灰色单位标注 |
| **品牌强调色** | `--dash-coral` / `--dash-vermilion` | 辅以 dizicute 经典珊瑚红 `#FF6B6B` 作为高光点缀、已完成绿标 `#2ECC71` |
| **交互胶囊** | Bauhaus Pill Button | 底部配有同族的圆角拟物胶囊按纽 `[ 查看练习明细 ↗ ]` |

---

## 2. 复合列布局与高度分配规范

### 2.1 组合 2 与 3：D + R 上下复合列结构（宽度 360px）
在组合 2、组合 3 中，时长卡 D 与记录卡 R 垂直合体，共同占据第 3 列（宽 360px），二者之和严格等于基准高度 $H = 780\text{px}$：

```
┌───────────────────────────────────────────┐
│ D 今日练习时长卡 (上部主卡)               │
│ 360px × 460px (约 59% H)                  │
│                                           │
│ [ 01:15 ] 练习时长 · 今日达成 80%         │
│ [ 进度胶囊条 / 目标 90m ]                 │
└───────────────────────────────────────────┘
  ▲ 垂直间距 gap = 12px
┌───────────────────────────────────────────┐
│ R 今日练习记录小卡 (下部小卡)             │
│ 360px × 308px (约 39.5% H)                │
│                                           │
│ [ 3 / 4 ] 项曲目已完成                    │
│ [ 药丸按钮: 查看记录明细 ↗ ] (点击弹窗)    │
└───────────────────────────────────────────┘
[ 复合列总高度: 460 + 12 + 308 = 780px ≡ H ]
```

- **高度闭合方程**：
  $$h(D) + \text{gap}(12\text{px}) + h(R) \equiv H = 780\text{px}$$
- **定位对齐**：
  - D 卡顶边与票卡顶边平齐：$t(D) = t(\text{ticket})$；
  - R 卡底边与票卡底边平齐：$b(R) = b(\text{ticket})$，相对票卡底差 $\Delta b \equiv 0$。

### 2.2 组合 1：D + R 卧排结构（宽度 460px）
在组合 1 中，D 与 R 卧排在 A 仪表盘下方：
- D 在左，R 在右，各占 $224\text{px}$ 宽度；
- 高度均为 $328\text{px}$；
- 横向闭合：$224 + 12 + 224 = 460\text{px} \equiv w(A)$。

---

## 3. R 小卡内部信息架构与 Popout 弹窗规格

### 3.1 R 小卡卡面内容（严禁出现滚动列表）
R 卡内仅保留 3 个视觉层级，确保信息一目了然：
1. **Header 行（32px）**：
   - 音符图章小徽标 +「今日练习记录」字样（14px，淡金/高亮白）；
2. **Body 数据块（垂直居中弹性吃满）**：
   - 巨大状态读数：如「**3** <span style="font-size:16px;color:#8E9CAE">/ 4 首</span>」；
   - 状态副标：「已完成 75% 今日计划」；
   - 成果点缀：3 颗金色实心星（已打卡评分）。
3. **Footer 操作区（48px）**：
   - 交互胶囊按钮：
     ```html
     <button class="pill-popout-btn" id="openRecordsPopoutBtn">
       <span>查看记录明细</span>
       <svg class="icon-arrow" width="14" height="14" viewBox="0 0 24 24">...</svg>
     </button>
     ```
   - 按钮自带微 3D 按压反馈，光标 hover 时呈现轻微上浮光晕。

### 3.2 全局 Popout 弹窗规格（沿用既有 popout 形态）
当用户点击 R 卡上的任意区域或 `pill-popout-btn` 时，触发模态浮层：

1. **背景遮罩（Backdrop Overlay）**：
   - `position: fixed; inset: 0; z-index: 9999;`
   - `background: rgba(15, 18, 22, 0.65);`
   - `backdrop-filter: blur(12px);`
2. **弹窗主体（Modal Sheet Container）**：
   - 几何尺寸：`width: min(600px, 92vw); max-height: 82vh;`
   - 居中定位：`position: fixed; left: 50%; top: 50%; transform: translate(-50%, -50%);`
   - 质感：`background: #1D2228; border-radius: 28px; border: 1px solid rgba(255, 255, 255, 0.16); box-shadow: 0 24px 64px rgba(0, 0, 0, 0.6);`
3. **弹窗内部分区**：
   - **Header（固定顶栏）**：
     - 左侧：标题「今日练习记录详情」+ 日期「2026-10-15」；
     - 右侧：圆形关闭按钮 `×`（40×40px，按压回弹）；
   - **Body（可平滑滚动列表区）**：
     - 每一条练习科目列表项：
       - 科目名称（如「基本功 · 低音长音吹奏」）；
       - 录制时长（如「15 分钟」）；
       - 演奏时 BPM（如「82 BPM」）；
       - 麦克风平稳度得分（波形图标 + 95分）；
     - 条目之间以半透明细线分界。
   - **Footer（固定底栏）**：
     - 累计总时长与今日完成度总评；
     - 「关闭」主操作按纽。
4. **关闭与退出机制**：
   - 点击右上角关闭按纽 `×`；
   - 点击外部遮罩区域（Click Outside）；
   - 键盘按下 `Escape` 键；
   - 退出动画采用 0.2s 缓动缩放淡出（`transform: scale(0.96); opacity: 0;`）。

---

## 4. 可量判据（Price-Tag Verification Criteria）

1. **模糊层与破框 0 容忍**：
   - 页面 DOM 中彻底不存在 `.records-blur-mask` 或任何生效的 `filter: blur(...)` 遮挡层；
   - R 卡本体内部无任何原生纵向滚动条：`scrollHeight <= clientHeight`。
2. **复合列垂直闭合精度**：
   - 组合 2 与组合 3 中：
     $$h(D) + 12 + h(R) = 780\text{px} \pm 1\text{px}$$
     $$t(R) - b(D) = 12\text{px} \pm 0.5\text{px}$$
     $$b(R) = b(\text{ticket}) \pm 1\text{px}$$
3. **Popout 弹窗交互响应**：
   - 点击 `#openRecordsPopoutBtn` 后：
     - 模态弹窗容器可见：`modal.style.display !== 'none'`；
     - `backdrop-filter` 计算值包含 `blur`；
     - 弹窗居中：`abs(left + width/2 - window.innerWidth/2) <= 1px`；
   - 点击关闭后：模态完全销毁或隐藏，不残留遮罩阻挡主屏操作。
