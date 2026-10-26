# demo v38 · Codex 架构方案（待与 agy 方案核对）

> 定位：本文件是 **Codex 的独立判断**，用于和 `PLAN-v38-agy方案.md` 逐条对照。
> 事实依据：`PLAN-v38-取证与架构.md`（1~5 节，全部为 Playwright 实测）。
> 原则：先解决「为什么会反复改坏」，再解决「这一版哪里不好看」。

---

## 一、先把病因说清楚（这是关键，不修这个，下一轮还会坏）

### 病因 1：双份实现 + 无同步机制（**最根本**）

每张卡存在两份代码：

| 真源 | 镜像 |
|---|---|
| `canvas-01.html` 里的 `<template id="tpl-A">`（运行时唯一生效） | `dashboard-skin-01-v3.html`（没人加载，已过期） |

- 实测证明：`wantBelow` 只存在于 canvas-01.html，`dashboard-skin-01-v3.html` 里还是旧算法。
- 后果：任何人（包括 agy）打开 `dashboard-skin-01-v3.html` 都会看到「正确的」旧代码，改它 → 无效果 → 再改内联 → 又改坏。**这就是「改来改去没改对」的机械原因。**
- 更糟：正确基准 `dashboard-skin-01.html` 从未被内联回来，导致内联副本越修越偏。

### 病因 2：布局模式绑定在「视口」上，而不是「卡片模式」上

现有 CSS 大量使用 `data-vp="1133x744"|"744x1133"|"440x956"`。
但卡片在 iframe 里，卡片实际宽度是 360 / 430 / 460 / 712 / 408 —— **和视口号没有稳定对应**。
于是同一张卡在 1133 画布里只有 360px 宽，却命中 1133 的样式分支 → 所有字号/间距都按错的宽度算。

→ 组合爆炸：6 卡 × 3 视口 × 3 组合 × 2 皮肤 = 108 个分支要维护，必然出错。

### 病因 3：几何靠 JS 打补丁，且补丁被 `!important` 静默废掉

`layoutArc()` 里 `midEl.style.marginTop = -70.2px`，
但注入样式 `html.cz-fill .mid { margin-top: 16px !important }` 覆盖它。
computed 仍是 16px，`dy=80px`，`fx_offset=sqrt(82²-96²)=0` → 圆弧退化成直线 → **面板缺口消失**。
**没有任何断言发现这件事**，所以这个 bug 存活了很多轮。

### 病因 4：组合定义有三份互相矛盾的数据源

`PRESETS` / `COMBO_MODS` / `COMBO_DEFS` 各写各的。
结果：文案说「③ 全右栏六卡」，实际渲染 4 张，S 和 Q **连 DOM 节点都不存在**。

### 病因 5：没有回归守卫

每轮靠肉眼 + agy 自报 PASS。agy 两次自报 PASS 都被我实测推翻（`.c-detail` 被删、card 压面板 29866px²、1133 叠字）。

---

## 二、目标架构

### 2.1 核心：**只有两种卡片模式**（用户的原话，作为唯一标准）

```
html.cz-expand   —— 横向扩展模式：卡片是横向轨道里的一列
                    宽度固定（按卡型），高度 = 票卡全高，内容必须撑满，禁止内部滚动
html.cz-feed     —— 纵向 feed 模式：卡片是纵向流里的一段
                    宽度 = 容器全宽，高度 = 内容自然高，随页面滚动，禁止内部滚动
```

**模式由外层画布显式下发**（画布知道轨道方向是 row 还是 column），不让卡片自己猜：

```js
// canvas 侧，唯一判定点
var mode = railDirection === 'row' ? 'expand' : 'feed';
iframe.contentDocument.documentElement.classList.toggle('cz-expand', mode==='expand');
iframe.contentDocument.documentElement.classList.toggle('cz-feed',   mode==='feed');
```

**硬规则：卡片 CSS 里禁止出现 `data-vp`、`@media (max-width:1023px)` 这类「按视口」的分支。**
只允许 `.cz-expand` / `.cz-feed` 两个选择器。这一条写进 lint 检查。
→ 分支数从 108 降到 **12**（6 卡 × 2 模式），这就是用户说的「不论什么视口、什么组合都和谐」的可实现形式。

### 2.2 每张卡的两种模式规格（12 份）

| 卡 | expand（横向列） | feed（纵向流） |
|---|---|---|
| **A 仪表盘** | 宽 430-460 固定；高 = 票卡高；notch=96px；旋钮 144px；± 58px | 宽=容器；高=自然（面板 200 + 旋钮 150 + deck）；notch=78px；旋钮 120px；± 52px |
| **B 节拍器** | 宽 340；高 = 票卡高 | 宽=容器；高=自然；删除固定高度 |
| **S 竖条** | 宽 76-130（竖排 writing-mode）；字号按竖排单独规格 | **横向 bar**（不是竖条）：宽=容器，高≈96px，内容横排 |
| **D 今日时长** | 宽 224-380；**内容只有 184px 高就限高 320px，不拉伸** | 宽=容器；高=自然；去掉 61% 空白 |
| **R 今日记录** | 宽 224-460；内部表格可滚 | 宽=容器；高=自然；表格换 3 行堆叠 |
| **Q 老师要求** | 宽 440；文本内滚 | 宽=容器；高=自然 |

> S 卡在 feed 模式必须换成「横向 bar」——这一条用户在上一轮就提过（「纵向排列的视口下票夹也应该是横向 bar」），至今没实现。这是**功能缺失**，不是样式问题。

### 2.3 单一真源

推荐 **抽取 + 构建注入**：

```
cards/
  a-dashboard.html     ← 唯一真源，可单独用浏览器打开
  b-metronome.html
  s-strip.html
  d-duration.html
  r-records.html
  q-requests.html
tools/build-canvas.py  ← 把 cards/*.html 注入 canvas-01.html 的 <template> 区
tools/check-canvas.py  ← --check：不一致就 exit 1
```

好处（除了防漂移）：
1. **每张卡可以单独在任意宽度打开验证** —— 这是「两模式」能落地的前提，不需要跑整个画布；
2. agy 改一张卡只碰一个 200-400 行的文件，不会再在 880KB 文件里误伤别的卡；
3. 单文件体积从 880KB 降到外壳 + 6 卡；
4. `check-canvas.py` 让「文件不一致」变成硬失败，而不是靠人记得。

（备选：直接删掉 6 个镜像 .html，只保留内联。省事但没有 1、2 两个好处，不推荐。）

### 2.4 组合定义收敛为一张表

```js
var COMBOS = {
  '1': { label:'组合 1', cards:['A','D','R','S'], wide:[...], layout:'astack+s' },
  '2': { label:'组合 2', cards:['A','S','D','R'], ... },
  '3': { label:'组合 3', cards:['A','B','S','D','R','Q'], ... }  // ← 需 dad 确认
};
```
`PRESETS` / `COMBO_MODS` / `COMBOS` 树全部由它派生，删掉重复定义。
加断言：`渲染节点数 === cards.length`（缺一即红）。

> ⚠️ **需要 dad 拍板**：组合 3 到底要 4 张（现状 A/B/D/R）还是 6 张（文案承诺）？
> 我倾向 **6 张**（按文案），因为「全右栏六卡」是用户能看到的名字。

### 2.5 几何：回到参考图，用公式而不是补丁

不再用 JS 调 margin。改成**纯 CSS 几何**（原版 `dashboard-skin-01.html` 的写法），因为 notch 永远贴面板底边：

```css
.panel {
  mask-image: radial-gradient(circle var(--notch) at 50% calc(100% + 6px),
              transparent 97%, black 100%);
}
.mid { margin-top: calc(var(--notch) * -0.62); }   /* 旋钮圆心≈面板底边 */
.round { width:58px; height:58px; font-size:26px; color:#FFF8F0;
         background:linear-gradient(180deg,#2A3036,#101316);
         box-shadow: inset 0 1px 0 rgba(255,255,255,.10), 0 6px 12px rgba(44,62,80,.45); }
```
点弧半径 = notch 半径（同心），这是「knob 与 arc 是一个整体」的定义式。

**加运行时断言（这条是这次最重要的新增）：**
```
|knobCenterY - panelBottom| <= 1.5px
|dotRadius - notchRadius| <= 1.0px
面板 clip-path 中弧段的弦长 > 40px      ← 防止再次退化成直线
```
任一条不满足 → 画布顶部红条报错，并且 `verify.py` 失败。

### 2.6 动效时序（串行，用户明确要求）

```
0ms    ── 票夹开始收拢（expand: leftW 360→50 共 320ms / feed: height→52）
320ms  ── 票夹到位，rail 完全接管
320ms  ── 卡槽插卡开始（opacity 0→1 + translateY -8→0，共 240ms）
560ms  ── 完成，进入 live
```
退出严格反向：`560→320` 抽卡，`320→0` 票夹展开。
点击露出条查看完整卡：FLIP —— 从卡槽矩形插值放大到弹窗矩形（240ms），**不是直接出蒙层**。

### 2.7 边角阴影

- `#pkSlotCavity` 的 inset 阴影被三层 `overflow:hidden` 裁切 → 改为在 `.cz-astack-crown` 上用 `::after` 画阴影（同层，不跨裁切边界）。
- `#czRecordsMini` 阴影被 `.cz-node` 裁掉 → `.cz-node` 改 `overflow:visible`，圆角移到内层。
- 卡片 iframe 本身无圆角 → `.cz-mod > iframe { border-radius: 20px; overflow: hidden }`，让阴影投在 `.cz-mod` 上（iframe 外）。
- **验收**：采样卡片外 2px 环带的像素，要求「没有 1px 硬直边」（亮度梯度连续）。

### 2.8 回归守卫（这是最能防「下次又坏」的东西）

`tools/verify.py`，一次跑完：

```
3 视口 × 3 组合 × 2 皮肤 × 2 模式 全矩阵，断言：
 1. 卡片/卡槽 vs 面板/旋钮/按键 重叠 == 0 px²
 2. 露出比例 20% ±1.5%
 3. 露出条内任意两可见元素重叠 == 0 px²（防止 1133 叠字复发）
 4. 记录弹窗 .c-detail display:block 且 sw<=cw
 5. enter/exit 逐 20ms：空窗帧数 == 0，且无「两套文字同时≥30%」
 6. 组合渲染节点数 == 定义数（防止六卡变四卡）
 7. feed 模式视觉顺序 == 定义顺序
 8. 卡片 CSS 里 data-vp 出现次数 == 0（lint）
 9. 几何断言（2.5）
10. D 卡底部空白 / 卡高 <= 30%
```

任何一条失败 → 非 0 退出。以后每轮改完先跑它，agy 的「我修好了」不再作为依据。

---

## 三、实施顺序（每步可独立验收）

| 阶段 | 内容 | 收益 | 风险 |
|---|---|---|---|
| **S0** | 建立 `verify.py` + 把现状跑成基线（记录 10 条真/假） | 后面每步都有护栏 | 低 |
| **S1** | 抽 `cards/*.html` + `build/check` 脚本；内联改为生成 | 根治双源漂移 | 中（构建脚本要正确） |
| **S2** | 模式改造：卡片 CSS 去掉 `data-vp`，只留 `.cz-expand/.cz-feed`；画布下发模式 | 分支 108→12 | 中（要逐卡迁移） |
| **S3** | 仪表盘几何回归参考图（notch/弧/±）+ 断言 | 修用户 3 条批注 | 低 |
| **S4** | 组合表收敛 + 补 S/Q + feed 顺序 | 修「六卡变四卡」和顺序错乱 | 中 |
| **S5** | D 卡限宽 / S 卡 feed 横 bar / R 卡 feed 堆叠 / Q 卡 | 修 5 条批注 | 中 |
| **S6** | 动效串行 + 出槽 FLIP | 修 2 条批注 | 中 |
| **S7** | 阴影 3 处 | 修「好几轮没解决」 | 低 |
| **S8** | 全矩阵 verify + 三档截图 + 升版本号 | 交付 | 低 |

建议 **S0→S1→S2 先做**（这三步是「以后不再反复」的地基），确认地基没问题再做 S3-S7 的视觉修复。

---

## 四、我需要和 agy 对齐的分歧点（待它方案回来后逐条比）

1. **两模式的判定点**：我主张由画布下发 class（显式、无歧义）；agy 可能主张 container query（纯 CSS）。倾向我的，因为 container query 无法知道「轨道方向」。
2. **单一真源**：我主张抽文件 + 构建；agy 可能主张删镜像只留内联。需要比「可单独验证」这个收益值不值得引入构建步骤。
3. **组合 3 是 4 张还是 6 张**：这是产品决策，需 dad 确认。
4. **S 卡 feed 模式**：必须换成横 bar（功能缺失），不能只调字号。
5. **仪表盘几何**：我主张纯 CSS + 断言；如果 agy 坚持 JS 计算，必须去掉 `!important` 冲突并加断言。
