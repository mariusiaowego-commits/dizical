# tech-spec · sprint-26091402 · badge CCG 卡面+modal 微调

## 1. overlay 改 D 毛玻璃

```css
/* 修前（badge-ccg.css:1035-1052）*/
.ccg-claim-overlay {
  background: rgba(14, 10, 6, 0.52);
  backdrop-filter: blur(12px);
}

/* 修后 */
.ccg-claim-overlay {
  background: rgba(253, 250, 244, 0.55);
  backdrop-filter: blur(7px);
}
```

机制：`rgba(14,10,6,0.52)` 是「深夜里看屏幕」逻辑，对 3D 把玩舞台把画面压在底色后面；改亮色 55% 米白 + blur 7px 让 modal 看起来像「磨砂玻璃柜」，可读性回来、仍然有空间感。

## 2. 卡背故事区撑满 + 展开胶囊挪底部（CSS-only 方案）

```css
/* 修前（badge-ccg.css:915-960）*/
.ccg-back-val {
  -webkit-line-clamp: 4;        /* 写死行数 */
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ccg-back-story.is-expandable,
.ccg-back-story.is-expandable * { pointer-events: auto; }

/* 修后 */
.ccg-back-val {
  /* 删 -webkit-line-clamp: 4；改为容器即上限 */
  display: block;               /* 自然撑满 */
  -webkit-mask-image: linear-gradient(
    rgb(0,0,0) calc(100% - 24px),
    rgba(0,0,0,0) 100%
  );                             /* 仅 .has-overflow 时挂 */
}
.ccg-story-expand-btn {
  margin-top: auto;              /* 钉底 */
  align-self: flex-end;           /* 钉右 */
  pointer-events: auto;          /* 唯一可点 */
}
.ccg-back-story:not(.has-overflow) .ccg-story-expand-btn { display: none; }
.ccg-back-val,
.ccg-back-story > :not(.ccg-story-expand-btn) { pointer-events: none; }
```

JS 删 `isLong = storyVal.length > 50` 字数猜测；改用 `ResizeObserver` 监听 `.ccg-back-val` `scrollHeight > clientHeight` 真实溢出判定，加/移 `.has-overflow`。

为什么不走 JS 量高算整行 clamp：字体回退与 `document.fonts.ready` 异步会让首帧算错、iPad 横/竖屏切换会 layout thrashing、WebKit 动态 line-clamp 偶发半行残影 — 纯 CSS 方案零风险。

## 3. 光照层局部化（仅淡色主题作用域）

```css
/* 修前（badge-ccg-themes.css:180-225 pearl 段）*/
--theme-glare-stops: hsla(0,0%,100%,0.85) 0%,
                    hsla(48,82%,95%,0.40) 22%,
                    hsla(42,46%,88%,0.10) 45%;   /* 末端无 transparent */
--theme-foil-laser-blend: soft-light;             /* 整片软光冲淡 */
--theme-foil-spec-blend:   soft-light;
--theme-foil-op:           0.55;

/* 修后（仅 [data-ccg-theme="pearl|mint|sakura"] 内）*/
--theme-glare-stops: hsla(0,0%,100%,0.85) 0%,
                    hsla(48,82%,95%,0.40) 22%,
                    hsla(42,46%,88%,0.10) 45%,
                    hsla(42,46%,88%,0) 65%;       /* 末端归 transparent */
--theme-foil-laser-blend: color-dodge;
--theme-foil-spec-blend:   screen;
--theme-foil-op:           0.42;
```

机制：末端归 transparent 让光斑外圈不被「整片发白」覆盖；laser 回 color-dodge、spec 回 screen、foilOp 0.55→0.42 三重降亮；glare stops 跟随指针的椭圆渐变（CSS 已通过 `clamp(0%, var(--pointer-x,50%),100%)` 接入光标位置 — **不动**，4 处 clamp 是 brief 1 的禁区）。

**物理隔离**：所有改动严格限定在 `[data-ccg-theme="pearl|mint|sakura"]` 选择器作用域，**深色主题（azure/bamboo 等）CSS 一字节不改**。

## 4. 兼容性 / 兼容性回归

- 3D 几何参数硬边界（`maxTilt 22` / `ry=+nx*22` / `rx=-ny*22` / `state.lift 20` / `IDLE_Y=14%` / perspective 980px / origin 50% 48% / 四角 ±21.82°）逐字符未动
- 后端、`data/`、`badge_theme.py`、`badge_db.py`、`routes/badge_workflow.py` 不动
- `achievements.html` / `badges.html` 仅模板 literal 兜底（4 处 `azure→pearl`），不改结构
- 老 P1（badges.html `No.001` 回落）不动