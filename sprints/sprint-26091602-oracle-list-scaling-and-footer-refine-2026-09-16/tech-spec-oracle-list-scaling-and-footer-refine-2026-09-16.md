# tech-spec · sprint-26091602 · Oracle 典藏卡列表缩放与页脚细节

> 6 个前端生产文件，累计 +456 / −70。后端零改动。
> 三个 commit：`4496757`（首轮）→ `248bf43`（二轮）→ `3daf66f`（三轮）→ squash 为 main `5ef98fa`。

## 1. 列表态缩放（首轮）

`.oracle-card` 已启用 Container Queries（`container-type: inline-size; container-name: oraclecard`，见 sprint-26091601），故所有内部尺寸可用 `cqw` 按卡宽等比缩放。本轮把列表态的**名牌 / 胸针 / 印章 / 头像**收紧：

```css
/* 名牌：收紧高度、内边距、字号 */
.oracle-nameplate { padding: …cqw; }
.oracle-nameplate .oracle-name { font-size: clamp(…cqw…); }

/* 装饰件：按卡宽等比 */
.oracle-pin    { width: …cqw; height: …cqw; }
.oracle-seal   { … }
.oracle-avatar { … }
```

机制：列表卡宽远小于 Modal 卡宽，若装饰件用固定 px 则相对显得臃肿；改用 `cqw` 后同一套 CSS 在两种尺寸下比例一致。

## 2. 类别 → 单字映射（首轮）

`badge-ccg.js` 侧按 tag 白名单映射为单字，替换 hardcode 头像/文字：

```
突破 → 破    巅峰 → 极    执着 → 韧    段位 → 阶
晋级 → 跃    神秘 → 秘    主题 → 典
```

与 sprint-26091601 的 `artToneFromTag()` 同一套 7 键白名单（突破/巅峰/执着/晋级/神秘/段位/主题），保证**印章 / 底板 / 页脚单字三者同源**，不会出现映射错配。

## 3. 去双层白框（首轮）

### 3.1 badges.html · `.badge-card`

```css
.badge-card {
  padding: 0; background: transparent; border: none;
  transition: transform 0.15s;              /* 去掉 box-shadow 过渡 */
}
.badge-card:hover { transform: translateY(-4px); box-shadow: none; }
.badge-card.unlocked::before { display: none; }   /* 去金色光晕块 */
.badge-card.locked { background: transparent; border: none; filter: none; }
.badge-card.locked:hover { filter: none; }
```

保留 `.badge-card:active { transform: scale(0.97) }`（点击反馈，与白框无关）。

### 3.2 achievements.html · `.b-card`

全部规则加 `:not(#card-daily-blindbox .b-card)` 排除盲盒：

```css
.b-card:not(#card-daily-blindbox .b-card) {
  padding: 0; border-radius: 16px;
  overflow: visible;                    /* 原 hidden 会裁掉 CCG 卡面外溢 */
  background: transparent; border: none; box-shadow: none;
  transition: transform 0.2s;
}
.b-card.unlocked:not(#card-daily-blindbox .b-card) { background: transparent; border: none; box-shadow: none; }
.b-card.unlocked:not(#card-daily-blindbox .b-card)::before { display: none; }
.b-card.unlocked:not(#card-daily-blindbox .b-card):hover { box-shadow: none; transform: translateY(-2px); }
.b-card.locked:not(#card-daily-blindbox .b-card) { background: transparent; border: none; }
```

`overflow: hidden → visible` 是关键：CCG 卡面的 3D 层会溢出原 `.b-card` 盒，`hidden` 会把它裁掉。

## 4. Modal 锁标隐藏（首轮）

沿用 `badge-ccg.css:2259-2265` 的既有规则（focus 态隐藏锁标）：

```css
.ccg-stage[data-mode="focus"].is-locked::after,
.ccg-claim-stage .ccg-stage.is-locked::after,
#ach-detail-stage .ccg-stage.is-locked::after,
#bd-detail-stage .ccg-stage.is-locked::after { display: none !important; }
```

## 5. 成就页展示数量（首轮 3 张 → 三轮 5 张）

`achievements.html` tab 分组 JS：

```js
if (uCount) uCount.textContent = unlocked.length;      // ① 先写完整计数
if (tabCount) tabCount.textContent = unlocked.length;
if (unlocked.length > 5) {                             // ② 再裁剪 DOM
  unlocked.slice(5).forEach(c => c.remove());
}
```

**顺序不可颠倒** —— 先 remove 会让计数变成截断后的 5。`unlocked` 顺序依赖服务端「最新在前」。

## 6. 名牌左对齐 + 立绘重心（二轮）

```css
/* 名牌：两级容器对齐链全改为 flex-start */
.oracle-nameplate-wrap { align-items: flex-start !important; }
.oracle-nameplate      { text-align: left !important; }
.oracle-name           { align-self: flex-start !important; }   /* 或同级 .oracle-cat */

/* 立绘：重心下移 + 微调 */
.oracle-art img {
  object-position: center 26%;
  transform: translateY(2px);
}
.oracle-art { contain: layout style; }     /* 新增：隔离布局/样式计算 */
```

## 7. 卡墙网格自适应多列（二轮）

`badges.html`：

```css
@media (min-width: 480px) {
  .badge-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 18px;
  }
}
```

原为固定断点（手机 2 列 / ≥800px 4 列）。改为 `auto-fill + minmax(160px, 1fr)` 后，1506px 宽屏自动铺出更多列，避免右侧留白。

## 8. 懒加载与闲置降帧（二轮）

### 8.1 图片懒加载（`badge-ccg.js`）

```js
'<img alt="" width="512" height="512" loading="lazy" decoding="async" src="' + d.image + '">'
```

`width`/`height` 显式声明，避免懒加载导致的布局抖动（CLS）。

### 8.2 列表墙闲置降帧

```js
/* 列表墙默认 idleSkip=4（约 15fps 闲置漂移）；
   hover/interacting 走 setFromPoint 满帧；
   focus/modal 不传此值 → 0 → 跟全局 1，60fps lerp + 翻转。 */
if (!cardIdleSkip && mode === "wall") cardIdleSkip = 4;
```

配合既有 IntersectionObserver 视口护栏（视口外不 paint）+ 上一 sprint 的 `idleSkip` 机制，列表闲置时渲染开销进一步下降。

## 9. cache-buster

| 阶段 | 版本 |
|------|------|
| 首轮 | `?v=26091602` |
| 二轮 | **`?v=26091603`** |

4 个引用点：`badges.html` / `achievements.html` / `_badge_claim_modal.html` / `oracle_production_audit.html`。

## 10. 已知技术债 / 未处理项

| 项 | 说明 |
|----|------|
| milestone 未解锁卡白底残留 | `achievements.html:218-226` 的 `#tab-pane-milestone #locked-grid-milestone .b-card` 权重 **(2,1,0)** > 新版 `.b-card.locked:not(...)` 的 **(1,3,0)**（`:not()` 只贡献 1 个 ID）→ 仍绘制白渐变底 + 红虚线框。未改动（疑为刻意的「未解锁激励视觉」） |
| `openClaim` 第三参被忽略 | `badge-ccg.js:1115` 仅 `function openClaim(data, scheme)` 两个形参；第三参 `{ locked:true }` 被静默丢弃，内部 `mountCard(..., { mode:"focus", canFlip:true })` 未透传 `locked` → Modal 内 `locked` 语义（灰度保留）未生效 |
| 卡面图为 1MB+ PNG | 未做 WebP / `srcset` / 缩略图优化（性能专项 backlog） |
| 每卡 6 个 pointer 监听器 | 卡墙一次性挂载全部 `.ccg-stage`（性能专项 backlog） |
| 全局 rAF loop 常驻 | `badge-ccg.js:1221`（性能专项 backlog） |
