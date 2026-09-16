---
id: 26091604
type: sprint
version: 1.0.0
start_date: 2026-09-16
end_date: 2026-09-16
status: 已完成
priority: 高
summary: "CCG 前端生命周期边角治理：全局单一 Resize 监听、成就页截断显式 Unmount、lostpointercapture 防抖、切卡锁保持与 --nx/--ny 冻结清零 (PR #335 MERGED, CloudRun Deploy #130 已上线)"
tags: [sprint, dizical, ccg, lifecycle, safari]
---

# Sprint 26091604 · CCG 前端生命周期边角治理

## 1. 背景与触发

Dad 在 iPad mini 真实生产环境完成 Sprint 26091603 验收（3D 动效卡顿彻底消除，WebP 3MB 秒开通过），并指示正式启动由 Grok 审查把关提出的 5 项前端生命周期边角优化：
1. **Window `resize` 监听收敛与成就页截断显式 Unmount**：消除 44 个独立 resize 监听，收敛为模块级单一监听；成就页 DOM 裁剪时显式调用 `unmount()`，防止内存泄漏。
2. **`lostpointercapture` 防抖与对称注销**：避免 pointerup 后补发 lostpointercapture 导致 `springHome()` 重复触发打断 GSAP，并在 `destroy()` 中对称注销。
3. **Modal 切卡过程保持 `is-frozen`**：详情弹窗换卡时维持冻结锁，避免背景卡墙解冻闪烁 1 帧。
4. **CSS 冻结规则补全 `--nx/--ny`**：`.is-frozen` 压制投影偏移变量，确保投影与卡面完全平整静止。
5. **动态 `pointer: coarse` / `fine` 响应**：监听媒体查询变化，支持 iPad 外接键鼠与触屏动态切换。

## 2. 团队分工矩阵

- **总指挥 / 多模态视觉把关**：`dizical-agy` (Antigravity)
- **核心前端主力**：`dizical-ds-flash` (DeepSeek-V4.1-Flash, `w19:pD`)
- **架构顾问与终局 Review**：`dizical-grok` (Grok 4.6, `w19:p7`)
- **部署工兵**：`dizical-minimax-m3` (MiniMax-M3, `w19:p6`)
- **最终拍板**：Dad

## 3. 核心任务清单

- [x] **任务 1（全局 Resize 监听收敛）**：`badge-ccg.js` 移除每卡单独的 `window.addEventListener("resize")`，改为模块级单一 `window.addEventListener("resize")`（支持 `visualViewport`），批量重置所有已挂载卡的 `cachedRect`。
- [x] **任务 2（成就页截断显式 Unmount）**：`achievements.html` 在 `unlocked.slice(5).forEach(...)` 中先调用 `DizicalCCG.unmount(c)` 再 `c.remove()`。
- [x] **任务 3（lostpointercapture 防抖与注销）**：`badge-ccg.js` 中 `onLostPointerCapture` 在 `pointerId == null` 时直接返回；`destroy()` 中显式 `removeEventListener("lostpointercapture")`。
- [x] **任务 4（切卡保持 is-frozen）**：`badge-ccg.js` 中 Modal 换卡先锁定再卸载挂载，消除 1 帧解冻缝隙。
- [x] **任务 5（CSS 补全 --nx/--ny 归零）**：`badge-ccg.css` 在 `.is-frozen .ccg-stage:not([data-mode="focus"])` 中加入 `--nx: 0 !important; --ny: 0 !important;`。
- [x] **任务 6（动态 coarse 响应）**：`badge-ccg.js` 监听 `window.matchMedia("(pointer: coarse)")` 的 `change` 事件动态更新 `coarse`。
- [x] **任务 7（版本号升级）**：资源引用升级为 `?v=26091605`。

## 4. 产出与验证结果

- **PR**: [#335](https://github.com/mariusiaowego-commits/dizical/pull/335) squash merge → `main` commit `7318a2b`。
- **Grok 终审**: PASS（全票通过）。
- **门禁测试**: Headless Chrome 7 项生命周期自动化断言全绿，全量 813 项 pytest 全部通过。
- **生产部署**: Cloud Run DeployId **#130**（Image `dizical-prod-130-20260916221538`），FlowRatio 100%，`badge-ccg.js` 81,732 字节 byte-for-byte 校验一致。

