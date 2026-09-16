---
id: 26091603
type: sprint
version: 1.0.0
start_date: 2026-09-16
end_date: 2026-09-16
status: 进行中
priority: 高
summary: "iPad mini 移动端 3D 动效零卡顿治理与 WebP 缩略图分流管线 (P0+P1)"
tags: [sprint, dizical, perf, ccg, webp]
---

# Sprint 26091603 · CCG 移动端 3D 动效零卡顿治理与 WebP 缩略图分流管线

## 1. 背景与触发

Dad 在 iPad mini（Retina 2266×1488 物理屏）的 Safari 真实环境中体验生产部署（#128）时，录制了 12.8 秒的屏幕录屏（`/Users/mt16/Downloads/ScreenRecording_09-16-2026 16.MP4`）。
经 AGY 逐帧提取与差分分析，暴露出两大影响体验的严重问题：
1. **3D 动效卡顿严重**：列表态 18 张卡并发 RAF 3D 变换；名牌 SVG `feTurbulence` 滤镜触发 WebKit 强制 CPU 重绘；弹窗打开时背景未冻结，叠加 `backdrop-filter: blur(14px)` 导致 GPU 过载；触摸跟手缓动 `k=0.08` 导致 500ms 滞后。
2. **首次打开加载极慢**：44 张卡片全部使用 1024×1024 未压缩 PNG，单张 1.2–2.0MB，首屏总流量高达 70MB+，占用 176MB 显存。

Dad 拍板方案 A：**P0（前端渲染性能止血）+ P1（WebP 缩略图分流与体积暴降）组合拳一次性搞定**。

## 2. 团队分工矩阵

- **总指挥 / 多模态视觉把关**：`dizical-agy` (Antigravity)
- **核心前端主力**：`dizical-ds-flash` (DeepSeek-V4.1-Flash, `w19:pD`)
- **资产管线与回归工兵**：`dizical-minimax-m3` (MiniMax-M3, `w19:p6`)
- **首席架构顾问与终局 Review**：`dizical-grok` (Grok 4.6, `w19:p7`)
- **最终拍板**：Dad

## 3. 核心任务清单

### P0 · 架构级零卡顿治理 (`ds-flash`)
- [ ] **Modal 冻结机制**：弹窗打开时设置 `DizicalCCG.setPaused(true)`，非 focus 卡片跳过 `tick()`，背景网格添加 `.is-frozen`（`transform: none`，停用一切后台重绘与混合渲染）。
- [ ] **列表态剥离重滤镜**：`.ccg-stage[data-mode="wall"]` 彻底移除 SVG `#oracle-ink-bleed`，静态水墨渐变兜底；动态分形滤镜仅在 Modal 聚焦单卡时启用。
- [ ] **触屏端去自动晃动**：`@media (pointer: coarse)` 或 `coarse` 状态下，列表态禁用 idle drift，卡片保持精致印刷品质感。
- [ ] **触摸跟手直接响应**：缓存 `getBoundingClientRect()` 避免 `pointermove` 中的 layout thrashing；跟手缓动大幅提速（延迟 < 20ms）。
- [ ] **前端响应式图源接入**：列表优先加载 `thumbs/` 缩略图，Modal 渐进无缝换为 `full/` 高清图。

### P1 · 资产现代化转码与缩略图分流 (`minimax-m3`)
- [ ] **转码自动化脚本**：编写 `scripts/generate_badge_webp.py`，遍历现存 44 张 PNG 生成：
  - `src/kid_app/static/badges/thumbs/*.webp`（320×320 @2x，透明 WebP，15–30KB）
  - `src/kid_app/static/badges/full/*.webp`（1024×1024，透明 WebP，80–120KB）
- [ ] **无缝兼容 Fallback**：原 PNG 保持原位不动，作为老旧浏览器兜底。
- [ ] **构建产物防膨胀**：校验构建包体积，确保 `.cloudrun-deploy` 在合理范围。

### Audit & 把关 (`agy` + `grok`)
- [ ] **Grok 终局 Code Review**：审查 `git diff`，查验 WebKit / Safari 极端边缘情况。
- [ ] **AGY 多模态资产核验**：肉眼抽检 WebP 透明通道纯净度（无黑边/无白边）。
- [ ] **全量回归测试**：768 pytest 0 回归。
- [ ] **本地 8765 验证**：无头浏览器截帧与性能对比。
- [ ] **Review Packet 呈报 Dad**：拍板后部署生产。
