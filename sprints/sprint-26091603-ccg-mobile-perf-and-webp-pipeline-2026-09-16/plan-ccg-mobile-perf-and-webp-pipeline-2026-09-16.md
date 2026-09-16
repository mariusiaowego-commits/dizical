# PLAN · CCG 移动端 3D 动效零卡顿治理与 WebP 缩略图分流管线 (Sprint 26091603)

## 1. 目标与范围

针对 iPad mini 生产环境（#128）实测录屏中的 3D 顿挫掉帧与 70MB 首屏加载慢，进行 P0（前端性能止血）与 P1（WebP 缩略图管线）的双轨治理。

## 2. 核心架构设计

### 2.1 P0 前端性能止血 (实施者: `dizical-ds-flash`)
1. **Modal 弹窗全网格挂起**：
   - 暴露 `DizicalCCG.setPaused(paused: boolean)`。
   - `openClaim()` / 详情弹窗打开时调用 `setPaused(true)`，关闭时调用 `setPaused(false)`。
   - 暂停态下：
     - 非 focus 的卡片 `tick(t)` 立即 `return`。
     - 卡墙父容器或卡片添加 `.is-frozen` 类，设置 `transform: none !important; animation: none !important;`。
     - 解除 WebKit 对背景 18 张连续 3D 变换图层进行实时 `backdrop-filter: blur(14px)` 计算的算力灾难。
2. **列表态剥离 SVG 分形滤镜**：
   - 列表卡片 `.ccg-stage[data-mode="wall"]` 彻底移除 `filter: url(#oracle-ink-bleed)`。
   - 保留纯静态矢量渐变水墨。
   - 动态分形滤镜仅在聚焦单卡 `[data-mode="focus"]` 时挂载。
3. **移动触屏端列表态去 Idle Drift**：
   - 在触屏设备（`pointer: coarse`）下，列表态卡片静止展示（无自动正弦波微倾角晃动），呈现高保真印刷品质感；仅在弹窗聚焦把玩时开启 3D 姿态与高光跟随。
4. **触摸交互即时响应**：
   - 缓存卡片 `getBoundingClientRect()`，避免 `pointermove` 过程中高频触发强迫同步布局。
   - 提升缓动跟随响应，消除 500ms 滞后感。
5. **前端图源支持缩略图**：
   - 列表态卡片优先取 `image_thumb` 或 `badges/thumbs/*.webp`，Modal 挂载时渐进切入 `badges/full/*.webp`。

### 2.2 P1 WebP 缩略图自动化衍生管线 (实施者: `dizical-minimax-m3`)
1. **转码脚本** `scripts/generate_badge_webp.py`：
   - 遍历 `src/kid_app/static/badges/*.png`。
   - 生成 `src/kid_app/static/badges/thumbs/*.webp`（320×320 @2x，保持 Alpha 透明通道，质量 80%）。
   - 生成 `src/kid_app/static/badges/full/*.webp`（1024×1024，保持 Alpha 透明通道，质量 90%）。
   - 保持原生 PNG 原位不动，老旧环境透明 Fallback。
2. **构建与测试**：
   - 确保转码后首屏资源从 70MB 降至约 1.1MB，显存占用从 176MB 降至 18MB。
   - 768 pytest 全量通过。

### 2.3 终局审查与多模态把关 (实施者: `dizical-grok` + `dizical-agy`)
1. Grok 审查最终 diff，杜绝 WebKit 边界坑。
2. AGY 抽检 WebP 透明通道纯净度，抓取本地 8765 渲染截图对比。
3. 产出 Review Packet 供 Dad 拍板。
