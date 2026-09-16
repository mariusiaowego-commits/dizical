# tech-spec · sprint-26091601 · Oracle 典藏卡体系重构

> 6 个前端生产文件，+817 / −85。后端零改动。

## 1. 细金掐丝边（badge-ccg.css）

金框由 `.ccg-frame` 承载。原 6px 粗重多层的 box-shadow 收敛为双层细描边：

```css
/* 修后 */
.ccg-frame {
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.45),
    inset 0 0 0 1.5px rgba(212, 160, 23, 0.35);
}
```

机制：原配方是多层叠加（1px 深褐 + 5px 金 + 6px 白）形成「实心厚边」。改为 1px 白边 + 1.5px 低透明度金属，金属只作为「掐丝」高光线存在，不再形成面状的视觉重量，中央原画的相对亮度占比随之上升。

圆角体系沿用既有变量链（`--ccg-card-r` / `--ccg-rim-inner-r` / `--ccg-art-inset`），不改弧线同心关系。

## 2. 矢量水墨泼墨名牌（badge-ccg.js + badge-ccg.css）

新增页面级一次性注入的 SVG 母版 `INK_SVG_HTML`（`ensureInkSvg()`，幂等，通过 `getElementById("oracle-ink-splash-graphic")` 判重）：

```
<filter id="oracle-ink-bleed">
  <feTurbulence type="fractalNoise" baseFrequency="0.04 0.018" numOctaves="3" result="noise"/>
  <feDisplacementMap in="SourceGraphic" in2="noise" scale="3.0"
                     xChannelSelector="R" yChannelSelector="G"/>
</filter>
```

- `feTurbulence` 生成分形噪声 → `feDisplacementMap` 让边缘产生宣纸渗墨的自然毛边
- 飞白丝缕：多条细长 `<path>` 叠加 `opacity 0.82–0.96`
- 墨星迸溅：约 90 个 `<ellipse>`，各自带独立 `rotate` + `opacity 0.47–0.97`
- 渐变 `oracle-ink-flow`（`#fff9f6 → #ffede8 → #fedacf`）提供墨迹浓淡层次

替代原 `clip-path: polygon()` 硬切割名牌。

**注入位置**：`document.body.firstChild` 之前，`position:absolute; visibility:hidden`，不参与布局。

## 3. 7 系分类底板与专属印章

### 3.1 分类判定（白名单，不可注入）

```js
function artToneFromTag(tag) {
  var t = String(tag || "");
  var keys = ["突破", "巅峰", "执着", "晋级", "神秘", "段位", "主题"];
  for (var i = 0; i < keys.length; i++) {
    if (t.indexOf(keys[i]) !== -1) return keys[i];
  }
  return "主题";   // 未命中回落
}
```

返回值恒为 7 个白名单常量之一 —— 该值后续既用于 `ORACLE_SEALS[key]` 查表，也用于拼 `aria-label`，白名单保证无注入面。

`stage.setAttribute("data-art-tone", artToneFromTag(d.tag))` 挂到 `.ccg-stage`。

### 3.2 底板 token（badge-ccg-themes.css）

```css
[data-art-tone="突破"] .oracle-art {
  --oracle-art-tone: linear-gradient(160deg, #2a114f 0%, #461f70 45%, #183e2b 100%);
}
/* …共 7 条：突破 / 巅峰 / 执着 / 晋级 / 神秘 / 段位 / 主题 */
```

消费点：`badge-ccg.css:1687` 的 `.oracle-art { background: var(--oracle-art-tone); }`。经核查 CSS 定义与 JS 白名单 **7 键完全对齐，无死代码**。

### 3.3 印章

同 `artToneFromTag()` 结果做 `ORACLE_SEALS[key]` 白名单查表，内联 SVG 精铸金章，附 `role="img"` + `aria-label="<key> · 精铸金章"`。

## 4. 3D 刚性整卡翻转舞台

### 4.1 结构分层

```
.ccg-claim-overlay            position: fixed; 点击空白退出
└ .ccg-claim-dialog           role=dialog aria-modal
  └ .ccg-claim-layout         flex column, align/justify center（copy 区隐藏后不留网格洞）
    ├ .ccg-claim-stage        → mountCard(mode: "focus")
    └ .ccg-claim-copy[hidden]
```

`.ccg-claim-layout` 由 grid 改为 `flex-direction: column; align-items: center`，配合 `.ccg-claim-copy` 加 `hidden`，避免双栏布局在单卡模式下留出空列。

### 4.2 翻转与倾斜

- 翻转：`.ccg-card-flipper` 上的 `--flip` 变量 0 ↔ 180deg；GSAP 驱动，无 GSAP 时回落 CSS 过渡（`.ccg-stage.ccg-no-gsap`）
- 倾斜：pointer 事件驱动 `rotateX/rotateY`，`springHome()` 平滑归零
- 轻点判定：位移 `< 6px` 视为 tap → 触发翻转，避免拖动误触

### 4.3 无按钮化关闭

| 通道 | 实现 |
|------|------|
| 模板 | `_badge_claim_modal.html` / `achievements.html` / `badges.html` 中 `.ccg-claim-close` 按钮已删除 |
| 兜底 | `bindModal()` 对 `closer` 做 null 守卫（`if (closer) closer.addEventListener(...)`），按钮缺失不报错 |
| 点空白 | `ov.addEventListener("click", e => { if (e.target === ov) closeClaim(); })` |
| 详情弹窗 | `achievements.html:739` / `badges.html:434` 各自的 `keydown Escape → closeModal()` |
| claim 弹窗 | `badge-ccg.js:1223` 全局 ESC → `closeStoryTray()` + `closeClaim()` + `resetAllFlips()` |

### 4.4 幂等绑定

`bindModal()` 用 `data-ccg-bound` 属性做守卫，重复调用不会重复挂监听器。

## 5. 已知技术债 / 兼容性说明

| 项 | 说明 |
|----|------|
| `cqw` 容器查询 | `.oracle-card` 使用 `container-type: inline-size` + 10 条 `clamp(…cqw…)` 规则，**无 px 兜底、无 `@supports` 守卫**。iOS 16 以下 `clamp()` 整条失效 → 回落继承 16px → 复现「文字撑爆卡面」 |
| `clip-path` 前缀 | 3 处无 `-webkit-` 前缀（iOS 13+ 已支持无前缀，风险低） |
| `touch-action: none` | 位于 `.ccg-stage`，**pre-existing**（main:194/230/1397），非本 sprint 引入 |
| 字段插值转义 | 6 处 `innerHTML` 拼接 `d.name` / `d.cond` / `story` 未转义，**pre-existing 模式**（main:218 已存在），本 sprint 新增 4 个 sink |
| 卡墙 hover tilt | 卡墙路径（`badge-ccg.js:631-637`）在非 focus 态直接写 `state` 并 `paint()`，故卡墙仍 hover tilt（`maxTilt` 默认 22）—— 沿用前一 sprint F5 决定，本 sprint 未变更 |
| 未移除的监听器 | `destroy()` 移除 5 个 pointer 监听器，`lostpointercapture`（匿名 handler）无法移除；节点随 DOM 移除被 GC，非真实泄漏 |
