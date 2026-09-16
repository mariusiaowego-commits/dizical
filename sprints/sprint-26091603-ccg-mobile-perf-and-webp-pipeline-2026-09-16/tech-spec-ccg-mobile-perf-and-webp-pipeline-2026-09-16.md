# TECH-SPEC · CCG 移动端 3D 动效零卡顿治理与 WebP 缩略图分流管线 (Sprint 26091603)

## 1. 架构总览

本次优化分为前端运行时架构优化（P0，由 `dizical-ds-flash` 实施）与离线资产流水线构建（P1，由 `dizical-minimax-m3` 实施）。

## 2. 前端技术实现设计 (P0)

### 2.1 全局挂起与背景墙冻结 (Freeze Loop)
- 在 `badge-ccg.js` 模块顶层声明 `var isPaused = false;`。
- 暴露 `window.DizicalCCG.setPaused = function(p) { isPaused = !!p; };`。
- 在 `loop(t)` 与 `tick(t)` 中：
  ```javascript
  if (isPaused && !isFocus) return;
  ```
- 在弹窗打开逻辑中：
  - `openClaim()` / 模态框展现时，调用 `DizicalCCG.setPaused(true)`，同时在卡墙容器添加 `.is-frozen`。
  - 弹窗关闭时，调用 `DizicalCCG.setPaused(false)`，移除 `.is-frozen`。
- 在 `badge-ccg.css` 中增加：
  ```css
  .is-frozen .ccg-stage:not([data-mode="focus"]) {
    transform: none !important;
    animation: none !important;
  }
  .is-frozen .ccg-stage:not([data-mode="focus"]) * {
    animation: none !important;
  }
  ```

### 2.2 列表态 SVG 滤镜剥离与分级
- 修改 `ensureInkSvg()` 或 `.oracle-ink-splash-graphic` 的引用方式：
- 在 `badge-ccg.css` 中：
  ```css
  /* 列表态仅保留静态矢量路径与渐变，禁用昂贵的 feTurbulence 滤镜 */
  .ccg-stage[data-mode="wall"] .oracle-nameplate use {
    filter: none !important;
  }
  /* 仅当处于 Modal 聚焦时才挂载该分形滤镜 */
  .ccg-stage[data-mode="focus"] .oracle-nameplate use {
    filter: url(#oracle-ink-bleed);
  }
  ```

### 2.3 触屏设备列表态禁用 Idle Drift
- 利用媒体查询与设备特征：
  ```javascript
  /* 在 coarse 指针（触屏）下，且非 focus 卡片，直接跳过 idle drift paint */
  if (coarse && !isFocus && !interacting) {
    return;
  }
  ```

### 2.4 触摸跟手即时响应优化
- 在 `onDown` 中调用一次 `r = stage.getBoundingClientRect()` 并缓存至实例；在 `onMove` 中直接复用，避免每一帧触碰引发 Layout Thrashing。
- 触摸跟随缓动更新：
  ```javascript
  var k = coarse ? 0.35 : 0.15; // 触屏大幅提速，消除 500ms 滞后
  ```

### 2.5 缩略图响应式渲染
- 卡片数据解析 `resolveCardImage(d, mode)`：
  - 若 `mode === 'wall'`，优先取 `image_thumb`，路径规则为 `/static/badges/thumbs/{name}.webp`；
  - 若未找到则 fallback 为原图 `/static/badges/{name}.png`；
  - 若 `mode === 'focus'`，展示 `image_full` `/static/badges/full/{name}.webp` 或原图。

## 3. 资产管线技术实现设计 (P1)

### 3.1 批处理脚本 `scripts/generate_badge_webp.py`
- 输入目录：`src/kid_app/static/badges/*.png`
- 输出目录：
  - `src/kid_app/static/badges/thumbs/*.webp`
  - `src/kid_app/static/badges/full/*.webp`
- 处理逻辑（Python Pillow）：
  - 自动保留 RGBA 透明通道（透明度不失真）；
  - `thumbs`：等比缩放至 `320×320`（Lanczos 重采样），WebP 格式，`quality=80, method=6`；
  - `full`：`1024×1024`，WebP 格式，`quality=90, method=6`；
  - 严格校验透明边缘，无白边噪点。
