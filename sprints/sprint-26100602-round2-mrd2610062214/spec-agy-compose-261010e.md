---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# spec-agy-compose-261010e · compose-02 组合1 窄槽降级技术规格与实测报告

- **日期**：2026-10-10
- **作者**：`agy`
- **目标文件**：[`compose-02.html`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/compose-02.html)
- **上游依据**：[`brief-agy-compose-261010e.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/brief-agy-compose-261010e.md) · dad 追加指令（`## 2610102107` 第 4 条）

---

## 0 一句话结论

针对 dad 反馈的「`compose-02.html` 组合1 在 460、620 窄宽度下底排 2 张卡片无法展示全、要求放不下就降级为一行一张卡片」指令，在 [`compose-02.html`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/compose-02.html) 完成动态判定与降级重构：
1. **摒弃写死断点魔法数**：严格按卡片契约最小宽度计算两卡并排阈值 $\text{neededW} = \text{minW}_{\text{duration}}(300) + \text{minW}_{\text{requests}}(340) + \text{gap}(16) = \mathbf{656px}$。
2. **820 档保持并排**：容器内容宽 788px $\ge$ 656px，两卡等分各得 386px，双栏并排对齐，文字无裁剪；
3. **620 / 460 档优雅降级**：容器内容宽分别为 588px 与 428px（均 $< 656\text{px}$），自动降级为「一行一张卡片」（三行纵向堆叠），底排两卡各占 100% 满宽，内部元素 0 裁切、无横向滚动条；
4. **断言完美兼容**：并排时校验「上宽 == 下两张宽 + 间距」，降级堆叠时校验「上宽 == 每张卡片宽」；
5. **门禁与自动化自检全绿**：`?audit=1&combo=1` 返回 `ASSERT_OK`（0 失败）；负控 `forceSide=1` 准确报红拦截并输出两端实测原文（460 档：`container width 428px < needed width 656px`；620 档：`588px < 656px`）。

---

## 1 改前问题诊断与实测根因

### 1.1 容器宽度与卡片分配算术

组合1 容器在 `.board` 上设置了左右各 16px 的 `padding`（总计 32px 内边距），卡片间距 `gap = 16px`。
在改前强制 50% 等分（`flex: 1 1 0`）时，下排两张卡分配到的物理宽度实测如下：

| 行宽开关档位 | 容器外宽 | 容器内容宽 (`containerInnerW`) | 改前下排每张卡分配宽 (`durW` / `reqW`) | 契约最小宽需求 (`minW`) | 判定结果 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **820** | 820px | $820 - 32 = \mathbf{788px}$ | $(788 - 16) / 2 = \mathbf{386px}$ | 时长 300 / 要求 340 | **充足**（可并排） |
| **620** | 620px | $620 - 32 = \mathbf{588px}$ | $(588 - 16) / 2 = \mathbf{286px}$ | 时长 300 / 要求 340 | **严重不足**（放不下） |
| **460** | 460px | $460 - 32 = \mathbf{428px}$ | $(428 - 16) / 2 = \mathbf{206px}$ | 时长 300 / 要求 340 | **极度挤压**（严重破碎） |

### 1.2 卡片内部渲染实测证据（Headless Chromium 像素级抓取）

在改前强制并排状态下，卡片内部 iframe 实际渲染的 `scrollWidth` 与溢出量：
- **在 206px 宽度下（460 档强行并排）**：
  - `card-requests`：内容 `scrollWidth = 250px` > 容器 `206px` $\implies$ **溢出 44px（出现横滑/裁切）**。
  - `card-practice-duration`：内容 `scrollWidth = 293px` > 容器 `206px` $\implies$ **溢出 87px（右侧刻度与仪表严重截断）**。
- **在 286px 宽度下（620 档强行并排）**：
  - `card-practice-duration`：内容 `scrollWidth = 333px` > 容器 `286px` $\implies$ **溢出 47px（时长卡文字与刻度压线超界）**。

事实证明 dad 指令「碰 到 460、620 宽度 则下面 2 个卡片都无法展示全了」判断完全精准！

---

## 2 窄槽降级技术实现规格

### 2.1 卡片契约申明与动态宽度计算

在 DOM 结构中补齐各卡片的契约最小宽度：
```html
<div class="slot" data-card="card-practice-timer" data-combo="1" data-w="460" data-min-w="380">...</div>
<div class="slot" data-card="card-requests" data-combo="1" data-w="440" data-min-w="340">...</div>
<div class="slot" data-card="card-practice-duration" data-combo="1" data-w="380" data-min-w="300">...</div>
```

在 JS 控制器中动态提取并计算并排阈值：
```javascript
var CARD_MIN_W = {
  'card-practice-timer': 380,
  'card-metronome-strip': 148,
  'card-metronome': 340,
  'card-requests': 340,
  'card-today-records': 380,
  'card-practice-duration': 300
};

function getComboInnerWidth() {
  var padL = parseFloat(getComputedStyle(board).paddingLeft) || 16;
  var padR = parseFloat(getComputedStyle(board).paddingRight) || 16;
  return board.clientWidth - padL - padR;
}

function updateComboLayout() {
  if (!board.classList.contains('is-combo')) return { stacked: false, innerW: 0, neededW: 0 };
  var innerW = getComboInnerWidth();
  var minDur = CARD_MIN_W['card-practice-duration'] || 300;
  var minReq = CARD_MIN_W['card-requests'] || 340;
  var gap = parseFloat(getComputedStyle(board).gap) || 16;
  // 必须满足两卡最小宽度之和 + 间距才允许并排
  var neededW = minDur + minReq + gap; // 656px
  var forceSide = qs.get('forceSide') === '1' || !!window.__forceSideBySide;
  var shouldStack = (innerW < neededW) && !forceSide;
  
  board.classList.toggle('is-combo-stacked', shouldStack);
  board.classList.toggle('force-side', forceSide);
  board.dataset.comboLayout = shouldStack ? 'stacked' : 'side-by-side';
  return { innerW: Math.round(innerW), neededW: Math.round(neededW), stacked: shouldStack, forceSide: forceSide };
}
```

### 2.2 响应式样式与排版降级规则

```css
/* 默认并排态：第二行两张卡等分 (50% - gap/2) */
.board.is-combo .slot[data-card="card-practice-duration"] { flex: 1 1 0; order: 2; }
.board.is-combo .slot[data-card="card-requests"] { flex: 1 1 0; order: 3; }

/* 窄槽降级态：放不下时一行一张，各占整行 100% 满宽 */
.board.is-combo.is-combo-stacked .slot[data-card="card-practice-duration"],
.board.is-combo.is-combo-stacked .slot[data-card="card-requests"] {
  flex: 0 0 100% !important;
  width: 100% !important;
}

/* 负控强制并排重写类 */
.board.is-combo.force-side .slot[data-card="card-practice-duration"],
.board.is-combo.force-side .slot[data-card="card-requests"] {
  flex: 1 1 0 !important;
  width: auto !important;
}
```

### 2.3 高度自适应规则

- **并排态（820 档）**：执行 `maxH` 计算，将底排两张卡高度同步为较大者（均为 608px），保持横向底边完美齐平；
- **堆叠态（620 / 460 档）**：底排两卡各自独立成行，取消强制等高，每张卡调用 `fit(iframe)` 取自身内容自然高度，避免在纵排中产生无意义的留白推挤。

### 2.4 断言兼容口径（双模态校验）

- **并排态（2 行）**：
  - 校验 `botTop >= slotTop.bottom - 1`（下排顶边在首行底边下方）；
  - 校验 `bottomRowW == slotTop.width`（误差 $\le 2\text{px}$）；
  - 校验下排两卡宽度相同、高度相同。
- **堆叠态（3 行）**：
  - 校验三行纵向有序递增：$\text{Timer.bottom} \le \text{Duration.top} \le \text{Duration.bottom} \le \text{Requests.top}$；
  - 校验每张卡宽度均占满整行且与上卡宽一致：$|\text{Duration.width} - \text{Timer.width}| \le 2\text{px}$ 且 $|\text{Requests.width} - \text{Timer.width}| \le 2\text{px}$；
  - 校验所有卡片 `scrollWidth <= clientWidth + 1`，0 横滑 0 裁切。

---

## 3 三档行宽 × 两皮肤全量实测数据表

在 Chromium 驱动下实时抓取渲染层测量值：

| 皮肤 | 行宽档位 | 容器外宽 (px) | 容器内容宽 (px) | 契约所需宽 (px) | 实际布局 | 总行数 | 计时卡宽 (px) | 时长卡宽 (px) | 要求卡宽 (px) | 时长卡 Top (px) | 要求卡 Top (px) | 容器横滑 (px) | 卡片内溢出 |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **浅银** | **820** | 820 | 788 | 656 | **side-by-side** | **2** | 788 | 386 | 386 | 727 | 727 | **0** | **无 (0)** |
| **浅银** | **620** | 620 | 588 | 656 | **stacked** | **3** | 588 | 588 | 588 | 727 | 1351 | **0** | **无 (0)** |
| **浅银** | **460** | 460 | 428 | 656 | **stacked** | **3** | 428 | 428 | 428 | 727 | 1351 | **0** | **无 (0)** |
| **深墨** | **820** | 820 | 788 | 656 | **side-by-side** | **2** | 788 | 386 | 386 | 727 | 727 | **0** | **无 (0)** |
| **深墨** | **620** | 620 | 588 | 656 | **stacked** | **3** | 588 | 588 | 588 | 727 | 1351 | **0** | **无 (0)** |
| **深墨** | **460** | 460 | 428 | 656 | **stacked** | **3** | 428 | 428 | 428 | 727 | 1351 | **0** | **无 (0)** |

实测结论：
1. **820 档**：两张底卡 `durTop = 727`、`reqTop = 727`，处于同一水平行，宽度均为 386px，两卡合计宽 $386 \times 2 + 16 = 788\text{px}$，与计时卡宽 788px 绝对对齐；
2. **620 档**：两张底卡 `durTop = 727`、`reqTop = 1351`，处于不同行（有序纵排），宽度均占满 588px，内部元素无裁剪；
3. **460 档**：两张底卡 `durTop = 727`、`reqTop = 1351`，处于不同行，宽度均占满 428px，内部元素无裁剪。

---

## 4 自动化负控测试验证（Negative Controls）

在访问 `compose-02.html?combo=1&forceSide=1`（关掉降级判定、强制并排）时，自动化断言立即报红拦截：

```json
{
  "verdict": "ASSERT_FAIL",
  "failures": [
    "narrow slot 620 forced side-by-side: container width 588px < needed width 656px (min 300+340+16); bottom cards cannot fit",
    "narrow slot 460 forced side-by-side: container width 428px < needed width 656px (min 300+340+16); bottom cards cannot fit"
  ]
}
```

- **两端原文比对**：
  - 460 档：容器宽 `428px` vs 需要宽 `656px`；
  - 620 档：容器宽 `588px` vs 需要宽 `656px`；
- 负控测试完全验证了门禁对窄槽放不下场景的拦截有效性。

---

## 5 质量门禁与契约验证状态

1. **页面内自动化断言**：
   - `compose-02.html?audit=1&combo=1` $\implies$ **`ASSERT_OK`，`failures: []`**；
   - `compose-02.html?audit=1`（全部卡片轨道视图） $\implies$ **`ASSERT_OK`，`failures: []`**。
2. **Demo 通用审计 (`verify-demos.py`)**：
   ```bash
   python3 docs/demos/practice-right-column-261003/scripts/verify-demos.py compose-02.html
   # 输出：
   # OK compose-02.html  (38228 B)
   #     非中性色字面量 0 / transition:all 0 / ink True / 括号差 0 / audit模式 有
   #     未定义 token 无 / JS 通过 / 写死超宽值 无
   #     旧文字色 0  OK
   ```
3. **颜色合规检查**：全页无任何非中性色写死字面量，所有色彩全部基于 `--dash-*` token（包括 `--dash-accent` 系列）；
4. **交付规范遵守**：仅修改 [`compose-02.html`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/compose-02.html)，产出报告 [`spec-agy-compose-261010e.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/spec-agy-compose-261010e.md)，无 git commit、无 git push、未引入任何第三方依赖。
