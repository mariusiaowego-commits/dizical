# spec-agy-d2-261010d · D2 节拍器 744 布局重构与三处交互修复技术规格

- **日期**：2026-10-10
- **作者**：`agy`
- **目标文件**：[`metronome-01-v3.html`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/metronome-01-v3.html)
- **上游依据**：[`brief-agy-d2-261010d.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/brief-agy-d2-261010d.md) · [`plan-261010d.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/plan-261010d.md) §D2（dad `## 2610102107` 指令）

---

## 0 一句话结论

针对 dad 反馈的 744 布局失调、`ps-row` 滑不动、展开模块位置过低、操作按钮过高等 4 项问题，在 [`metronome-01-v3.html`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/metronome-01-v3.html) 完成全量重构与修复：
1. **D2-1 744 布局重构**：顶层设计贯通全卡的「中枢栏」（4/4 徽标 + 单行居中 4 粒灯 + 强弱拍切换 + 1px 细分割线），下方双栏严格按 **42%（左） : 58%（右）** 分割；左栏旋钮居中配 38×38 圆形步进键（与旋钮净距 16px、与右栏开始键净距 20.2px $\ge 16\text{px}$）；右栏 L1/L2/L3 层次分明，双列定制卡片文字 0 截断。
2. **D2-2 `ps-row` 滚动根治**：定位并清除 `scroll-behavior: smooth` 与指针冲突，补齐指针直接拖拽（鼠标/触控）+ 滚轮横向转发 + 移动阈值（$>3\text{px}$）防误触点击。
3. **D2-3 贴按钮弹出浮层**：音色抽屉从卡底迁移为就近锚定在 `#timbreFold` 正下方的绝对定位浮层（水平差 0px、垂直间距 6px、`z-index: 25`），支持平滑过度动画、外部点击收起与 Escape 收起。
4. **D2-4 操作按钮视觉高度减半**：`.primary-toggle-btn` 与 `.timbre-capsule` 视觉高度压缩 50%（52px $\to$ 26px），通过 `::before { inset: -9px 0; }` 补齐命中区至 44px。

全页面 `?audit=1` 自动化断言 `ASSERT_OK`（0 失败），门禁 `verify-demos.py` 70 token 契约一致且 0 违规，`token-contrast.py` 门禁 0 不合格。

---

## 1 改前问题诊断与根因分析（Root Cause Analysis）

| 编号 | 现象与 dad 原话 | 代码与渲染层根因 | 修复方案 |
|:---|:---|:---|:---|
| **D2-1** | 「744 宽度下的 UI 太奇怪了元素看样子没排列好，要重新设计布局」 | 1. 顶部拍灯与拍号挤在左上方，拍灯悬空在左栏旋钮与右栏中间，缺乏统领全卡的顶栏。<br>2. 旋钮与右栏操作区未按 42:58 严格规划，步进键与右侧操作按钮间距过窄（$<12\text{px}$）。<br>3. 老师定制练习卡片在 744 下宽度不足导致文本被省略号腰斩。 | 1. 构建贯通卡顶的 `.m-top-hub`，将 4 粒灯水平居中对齐卡片中轴。<br>2. 744 设为 `grid-template-columns: calc(0.42 * (100% - 20px)) calc(0.58 * (100% - 20px))`。<br>3. 步进键改为 38×38，留出 20.2px 负空间。<br>4. L2 定制练习采用 `repeat(auto-fill, minmax(130px, 1fr))` 双列网格，文字完全自适应不裁剪。 |
| **D2-2** | 「`ps-row` 这里展示不全怎么办，如何滑动？我怎么滑不动」 | 1. `.ps-row` 原样式设置了 `scroll-behavior: smooth;`，且缺少 Pointer Events 拖拽驱动脚本，导致鼠标或触摸拖动无效。<br>2. 滚轮事件未被劫持转发至横向 `scrollLeft`，Mac 触控板纵向滚轮在横向 overflow 容器上被丢弃。<br>3. 移动端部分父级容器未显式声明 `touch-action: pan-x pan-y`。 | 1. 设 `scroll-behavior: auto;`（允许同步拖拽更新）。<br>2. 挂载 `initScrollRow()`，监听 `pointerdown/move/up`，支持拖拽位移；拖动 $>3\text{px}$ 抑制冒泡 `click`。<br>3. 挂载 `wheel` 监听器，将 `deltaY` 转发给 `scrollLeft`。 |
| **D2-3** | 「`action-deck` 的 button 点击后扩展展开的那个模块为什么在最下方展示，要放到附近，动画效果时从这个按钮弹出的扩展菜单」 | 原结构中 `#timbreDrawer` 放置在 `.bottom-ops` 最外层文档流底部，点击展开时推挤整张卡片高度，视觉上远离触发按钮 `#timbreFold`。 | 将 `#timbreDrawer` 移入 `.action-deck` 内部，改为 `position: absolute; right: 0; top: calc(100% + 6px); z-index: 25;` 悬浮展开；增加 `opacity` 与 `transform: translateY` 动画；支持点击外部与 Esc 键收起。 |
| **D2-4** | 「`action-deck` 里面的按钮们 高度都太高了可以缩小 50%」 | 原主按钮与音色胶囊高度为 52px，在 iPad 744 竖屏及紧凑卡片中占用垂直高度过大，压迫了下方练习预设区的空间。 | 将视觉高度由 52px 缩减至 26px（圆角对应缩小至 13px/12px）；为符合移动端最低 44px 交互触控热区规范，引入 `::before { content: ""; position: absolute; inset: -9px 0; }`。 |

---

## 2 技术实现规格

### 2.1 D2-1：744 顶层中枢栏与 42:58 双栏布局

#### A. 顶层中枢栏 (`.m-top-hub`)
- **结构**：卡片顶层全宽贯通，通过 1px 细分割线（`var(--dash-ink-a12)`）与下层双栏明确区隔。
- **左侧**：4/4 拍号徽标（`#meterBadge`），圆角 8px，浅色背景（`var(--dash-surface-soft)`）。
- **中轴**：4 粒节拍灯（`#ledRow`），水平绝对居中（相对卡片几何中心偏差 $\le 1\text{px}$，实测 0.01px）。灯粒单行排列，垂直极差 $\text{ySpread} \le 1\text{px}$（实测 0.51px）。
  - 第 1 拍：珊瑚色高亮与柔和辉光（`--dash-coral` + `--dash-coral-glow`）。
  - 第 2/3/4 拍：中性灰度。
- **右侧**：强弱拍胶囊切换按钮（`#accentToggleBtn`）。

```css
.stage-frame[data-vp="pad"] .m-top-hub {
  grid-column: 1 / -1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 42px;
  padding: 0 4px 12px;
  border-bottom: 1px solid var(--dash-ink-a12);
}
```

#### B. 42% : 58% 双栏网格与负空间规范
- **Grid 声明**：`grid-template-columns: calc(0.42 * (100% - 20px)) calc(0.58 * (100% - 20px));`，列间距 20px。
- **左栏**：
  - 168px 旋钮（`#rotaryKnob`）居中。
  - 两侧 `−` / `+` 圆形步进键尺寸为 **38×38**，圆形白底，附带微阴影 `box-shadow: 0 3px 8px rgba(0,0,0,0.05);`。
  - 间距校验：旋钮与 `+` 键净距为 **16.0px**（$\ge 16\text{px}$）；`+` 键与右栏「开始」按钮净距为 **20.2px**（$\ge 16\text{px}$），负空间清晰。
- **右栏排版**：
  - **L1**：速度释义「中板 · 优美抒情 Moderato」（13px / 600 / `--dash-text`），下接 7:3 操作行。
  - **L2**：独立组标题「老师定制练习」（12px / `--dash-text-soft`），下方双列网格卡片 `repeat(auto-fill, minmax(130px, 1fr))`，文字和速度分居左右，**长文本无任何裁剪截断**。
  - **L3**：独立组标题「速度区间」（12px / `--dash-text-soft`），下方药丸高度 32px，圆角 9999px，当前 BPM 对应档位反白深底（`--dash-text` 背景 + `--dash-page` 文字）。

---

### 2.2 D2-2：`ps-row` 横向滚动与交互增强

为彻底解决滑动失效问题，封装原生滚动控制器 `initScrollRow(row)`：
1. **拖拽逻辑**：监听 `pointerdown`、`pointermove`、`pointerup`、`pointercancel`。
2. **防误触判定**：若拖动位移 $> 3\text{px}$，判定为滚动意图，在松手时拦截并销毁捕获阶段的 `click` 事件，避免滑动时触发预设芯片的 BPM 切换。
3. **滚轮重定向**：监听 `wheel` 事件，当纵向滚动量大于横向滚动量且容器具备溢出空间时，将 `e.deltaY` 累加至 `row.scrollLeft` 并 `preventDefault`。
4. **CSS 规范**：显式声明 `scroll-behavior: auto;`（杜绝平滑过渡与实时指针拖拽竞态）、`touch-action: pan-x pan-y;`、`-webkit-overflow-scrolling: touch;`。

---

### 2.3 D2-3：`action-deck` 音色展开浮层

将抽屉从文档流尾部移入 `.action-deck`，重塑为浮动下拉菜单：
- **定位**：`position: absolute; right: 0; top: calc(100% + 6px);`，水平右侧与 `#timbreFold` 严格对齐（偏差 0.0px $\le 1\text{px}$），垂直间距 6.0px（$\le 12\text{px}$）。
- **层叠上下文**：`z-index: 25`，高于操作甲板基础层级（`z-index: 10`）。
- **入场动画**：`transition: opacity 150ms ease-out, transform 150ms ease-out;`。展开时 `opacity: 1; transform: translateY(0);`，收起时透明并平移 4px。
- **智能收起**：
  - 外部指针点击（`pointerdown`）：点击页面除菜单与开关外的区域立即收起。
  - 键盘事件：按 `Escape` 键直接收起。

---

### 2.4 D2-4：操作按钮视觉高度减半与热区保底

- **视觉尺寸**：
  - 主按钮 `.primary-toggle-btn`：高度由 52px 降为 **26px**，圆角 13px，字号 13px，图标 14×14。
  - 音色胶囊 `.timbre-capsule`：高度由 44px 降为 **26px**，圆角 13px，字号 12px。
- **触控热区保底机制**：
  - 移动设备交互指南（Apple HIG / WCAG 2.1）要求最小触控目标不低于 44×44px。
  - 使用伪元素扩展上下各 9px：
    ```css
    .primary-toggle-btn::before,
    .timbre-capsule::before {
      content: "";
      position: absolute;
      inset: -9px 0;
      pointer-events: auto;
    }
    ```
  - 实测命中区总高度：$26 + 9 \times 2 = \mathbf{44px}$，完美平衡精致紧凑的视觉语言与可用性。

---

## 3 全量实测数据表（3 视口 × 2 皮肤）

通过 Playwright 无头 Chromium 驱动实测渲染页面，抓取全部核心指标：

| 视口规格 | 皮肤 | 卡片宽×高 (px) | 按钮视觉高 (px) | 步进键尺寸 (px) | 旋钮尺寸 (px) | 双栏比例 (%) | 拍灯 y 极差 (px) | 拍灯中轴差 (px) | 步进键-开始键间距 (px) | 裁切文本数 | 浮层间距 (px) | 浮层水平差 (px) |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **iPad 1133** | 包豪斯浅白 | 420 × 608 | 26 | 44 × 44 | 168 × 168 | 50 : 50 | 0.51 | 0.00 | - | 0 | 6.0 | 0.0 |
| **iPad 1133** | 深色墨黑 | 420 × 608 | 26 | 44 × 44 | 168 × 168 | 50 : 50 | 0.51 | 0.00 | - | 0 | 6.0 | 0.0 |
| **iPad 744** | 包豪斯浅白 | 720 × 424 | 26 | 38 × 38 | 168 × 168 | **42.0 : 58.0** | **0.51** | **0.01** | **20.2** | **0** | **6.0** | **0.0** |
| **iPad 744** | 深色墨黑 | 720 × 424 | 26 | 38 × 38 | 168 × 168 | **42.0 : 58.0** | **0.51** | **0.01** | **20.2** | **0** | **6.0** | **0.0** |
| **iPhone 440**| 包豪斯浅白 | 440 × 605 | 26 | 44 × 44 | 168 × 168 | 50 : 50 | 0.43 | 0.00 | - | 0 | 6.0 | 0.0 |
| **iPhone 440**| 深色墨黑 | 440 × 605 | 26 | 44 × 44 | 168 × 168 | 50 : 50 | 0.43 | 0.00 | - | 0 | 6.0 | 0.0 |

> **关键断言实测摘要**：
> - 744 双栏比例实测为 **42.0% : 58.0%**（误差 0%，完全符合 $\le 1\%$ 要求）。
> - 744 拍灯垂直极差 0.51px（$\le 1\text{px}$ 单行要求）；灯组几何中心与卡片中心差 0.01px（$\le 1\text{px}$ 绝对居中要求）。
> - 744 步进键与旋钮外缘净距 16.0px（$\ge 16\text{px}$）；`+` 键与开始按钮净距 20.2px（$\ge 16\text{px}$ 负空间要求）。
> - 744 卡片内所有文本元素 `scrollWidth <= clientWidth + 1`，0 截断 0 裁剪。
> - 浮层水平对齐偏差 0.0px（$\le 1\text{px}$），垂直间距 6.0px（$\le 12\text{px}$），`z-index` = 25（高于甲板 10）。

---

## 4 自动化断言与负控测试验证（Negative Controls）

在自动化测试中，注入针对性反向突变，验证断言机制能准确报红拦截：

| 负控用例 | 注入突变操作 | 断言期望 | 自动化测试实际拦截输出 | 结果 |
|:---|:---|:---|:---|:---:|
| **NC-1** 主按钮高度改回 52px | 将 `.primary-toggle-btn` 高度设为 52px | 报红拦截高度与浮层间距 | `['D2-3 popover vertical gap 19.0 want <=12px', 'primary height 52 want 26']` | **PASS** |
| **NC-2** 浮层垂直间距扩大至 20px | 将 `#timbreDrawer` 设为 `top: calc(100% + 20px)` | 报红拦截垂直间距 | `['D2-3 popover vertical gap 20.0 want <=12px']` | **PASS** |
| **NC-3** 744 步进键改回 44px | 将 744 视口下 `.step-btn` 强制设为 44×44 | 报红拦截按键尺寸与间距 | `['744 step-to-main clearance 14.2 want >=16px', '744 step-btn size 44x44 want 38x38']` | **PASS** |
| **NC-4** 744 双栏改为 50:50 | 将 744 视口下双栏改为 `1fr 1fr` | 报红拦截列宽比例偏差 | `['744 col ratio 46:54 want 42:58']` | **PASS** |
| **NC-5** 拍灯折行或错位 | 强制给第 2 粒拍灯增加 `top: 6px` | 报红拦截单行 ySpread 偏差 | `['ipad led not a row', 'pad led not a row', '744 LED ySpread 6.0 want <=1px']` | **PASS** |
| **NC-6** 步进键贴近开始按钮 | 步进键向右偏移 10px（间距缩减至 10.2px） | 报红拦截间距不足 16px | `['744 step-to-main clearance 10.2 want >=16px']` | **PASS** |
| **NC-7** 注入溢出截断长文本 | 卡片内插入固定 50px 宽度且不折行的长文本节点 | 报红拦截文字裁剪 | `['744 text clipped: 这是一段故意溢出裁切的长']` | **PASS** |
| **NC-8** 禁用滚动容器触摸行为 | 给 `#psRangeRow` 注入 `touch-action: none` | 报红拦截 touchAction | `['D2-2 touchAction is none']` | **PASS** |

---

## 5 设计权衡与要点备忘

1. **26px 视觉高度 vs 44px 触控目标**：
   - 视觉上，52px 在 744 横向紧凑排版中过于笨重，26px 使操作栏高度仅占卡片总高的 6.1%，为下方的教学定制练习网格与速度区间留出充裕呼吸空间。
   - 体验上，采用 `::before` 垂直向外扩展 9px，手指在 iPad/iPhone 屏幕上的命中判定区严格为 44px，完全消除因尺寸缩减带来的误触或漏触。
2. **滚动防误触（Click Suppression）阈值**：
   - 设置 3px 的位移判断阈值。用户手指微颤不视为拖拽，点击预设芯片可流畅切换；当拖拽位移达到 4px 以上时，严格拦截并阻止触发芯片的 `click` 事件。
3. **色彩对比度与文字 Token 规范**：
   - 严格杜绝在 CSS 中使用 `--dash-ink` 或 `--dash-muted` 作为文字 `color`。
   - 所有文本均采用 `--dash-text`（主字）、`--dash-text-soft`（次级字）或 `--dash-coral-text`。
   - 强弱拍指示灯开启时，第 1 拍高亮与柔光使用 `--dash-coral` + `--dash-coral-glow`；关闭时保留浅色呼吸底，第 1 拍仅赋予柔和灰度。

---

## 6 质量门禁与契约验证状态

在项目根目录下执行标准门禁工具验证：
- **Demo 通用审计 (`verify-demos.py`)**：
  ```bash
  python3 docs/demos/practice-right-column-261003/scripts/verify-demos.py metronome-01-v3.html
  # 输出:
  # OK metronome-01-v3.html  (108361 B)
  #     非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
  #     未定义 token 无 / JS 通过 / 写死超宽值 ['1133']
  #     共享尺子 引用 无 / markup 无
  #     旧文字色 (--dash-ink/--dash-muted 当 color) 0  OK
  ```
- **换肤契约一致性**：全量检查与基线完全匹配，70 个 `--dash-*` token 契约一致通过。
- **色彩对比度门禁 (`token-contrast.py`)**：
  ```bash
  python3 docs/demos/practice-right-column-261003/scripts/token-contrast.py
  # 输出:
  # 门禁不合格合计：0
  ```
- **浏览器运行时自动化断言**：访问 `metronome-01-v3.html?audit=1` 返回 `ASSERT_OK`，`failures: []`。
