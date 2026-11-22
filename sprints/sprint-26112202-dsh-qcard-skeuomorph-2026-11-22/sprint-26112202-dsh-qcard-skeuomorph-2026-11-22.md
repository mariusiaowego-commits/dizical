---
type: sprint
sprint: "26112202"
topic: dsh-qcard-skeuomorph
date: 2026-11-22
status: 进行中
branch: feat/qcard-skeuomorph
base: e3c5f5d
---

# Sprint 26112202 · Q 卡拟物重做与四角描边根治（v3.55）

## 范围

- 根治老师要求卡（Q 卡）四角圆弧无描边：摘除宿主 `.cz-mod[data-mod="Q"]` 的 24px 裁切与投影，卡内改三层结构。
- Q 卡拟物重做（琴房作业卡方向）：模切纸边 + 2px 纸厚 + 内印线 + 压印序号 + 印泥速度章 + 撕口便签 + 卡底登记带。
- 去掉静态 `preserve-3d` / `translateZ`，叠卡改 2D，翻页与拖拽动画保持。
- 保留 Day Rail（T 卡），本 sprint 不改 T 卡。

## 文档

- `prd-dsh-qcard-skeuomorph-2026-11-22.md`
- `plan-dsh-qcard-skeuomorph-2026-11-22.md`
- `tech-spec-dsh-qcard-skeuomorph-2026-11-22.md`
- `test-plan-dsh-qcard-skeuomorph-2026-11-22.md`
- `verify-dsh-qcard-skeuomorph-2026-11-22.md`

## 输入

- agy 架构方案：`/private/tmp/herdr-dispatch/tasks/20261122-210725-qcard-skeuomorph-arch/result.md`
- pixel UI 方案：`/private/tmp/herdr-dispatch/tasks/20261122-210725-qcard-skeuomorph-ui/result.md`
- agy review（`GO with fixes`）：`/private/tmp/herdr-dispatch/tasks/20261122-212653-qcard-skeuomorph-review/result.md`
- 综合方案（含 review 修正）：`/private/tmp/qcard-skeuomorph-plan.md`

## 状态

代码与本地验收完成，PR 待独立 audit 与合并授权。验收明细见 `verify-dsh-qcard-skeuomorph-2026-11-22.md`：
四角描边浅色 ΔY 37.8–52.5、深墨 37.7–49.0（440/375/1133），翻页后不变；
5 个 pytest 失败与基线一致。
