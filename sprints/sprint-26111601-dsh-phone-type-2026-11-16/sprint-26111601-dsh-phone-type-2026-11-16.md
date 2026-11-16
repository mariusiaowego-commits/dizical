---
type: sprint
sprint: "26111601"
topic: dsh-phone-type
date: 2026-11-16
status: 已完成
branch: feat/practice-dsh-phone-type-v353
base: main@3844727 (v3.52)
---

# 26111601 · 练习助手手机端字号二次抬档（v3.53）

## 背景

v3.52（PR #406）已把手机仪表盘内部字号抬过一档（`.stand-btn` 12.5、
`.pill button` 15、`.diag-*` 12.5、`#bpmRead` 13）。dad 2026-11-16 仍在真机上
反馈「字太小」，走查定位到剩余未被覆盖的三类文本：

1. 画布顶栏：`.pk-brand` 13px、`.pk-pill` 11px、`.pk-ver` 9px、`.pk-mid` 11.5px。
2. 票夹露出条与弹层：`.pk-exposed-chip` **8px**、`.pk-exposed-title` 11.5px、
   `.pk-exposed-tag` 11.5px、`.pk-exposed-expand-hint` 9px。
3. 卡片模块内：mini 记录卡 11px、D 卡刻度 8.5px、S 卡术语 11px、
   B 卡预设芯片 12.5px、Q 卡标题 15px、R 卡空态 13px。

## 根因（实测）

- 手机走 440 设计宽 + feed，不是 1133 等比缩进。
- 缩放系数 k = stageW / 440：440 档 **0.9273**、393 档 **0.8205**、390 档 **0.8136**。
- 8px 芯片在 440 上视觉 7.4px，在 390 上 6.5px；11px 药丸在 390 上 9.0px。
- 结论：主因是手机断点写死的 8/9/11px，不是缩放算法。

## 方案

只改手机断点字号，**不动** `syncCanvasHeight()` 的 `k`，**不动** v3.48 的
`@container qcard (max-width:468px/348px)` 与 `.s2-*` 基线。

| 档 | CSS（440 设计宽） | 440 视觉 | 390 视觉 | 角色 |
|---|---|---|---|---|
| title | 18 | 16.7 | 14.6 | 品牌、卡头 |
| body | 16 | 14.8 | 13.0 | 科目、开始、快选、空态 |
| label | 14 | 13.0 | 11.4 | 顶栏药丸、谱架、时长胶囊 |
| caption | 12 | 11.1 | 9.8 | 版本、序号、刻度 |

断点归属：

- 画布文档：`@media (max-width:480px)` / `(max-width:600px)`（画布 440 命中，iPad 744 不命中）。
- 模块文档：新增 `html.cz-vp440`，由 `applyModuleState` 在 `vpEff === '440'` 时打上。

## 验收

- 440 / 393 / 390 三档：品牌 18、芯片 12、药丸 14；k 保持 0.9273 / 0.8205 / 0.8136。
- 390 上科目与「开始」视觉 ≥ 13px。
- 三档 `overflowX = false`，顶栏与票夹条不裁切。
- iPad 744：品牌仍 13.5、芯片仍 8.5，qcard 两档 token 不变。
- `pytest tests/test_practice_dsh.py tests/test_practice_dsh_save.py tests/test_practice_dsh_popout_data.py` 全绿。
- R 卡 `s2-step-*` 四列无真数据时不判 passed，记 `skipped`。

## 红线

- 不改缩放基准与 `canvasFitBaseH`。
- 不引入新 hex；字号沿用现有 px 体系。
- 不跨仓库改 dizical-minip（纯 CSS/JS，无 API 变化）。


## 发布

- PR #408 squash → `main` `c8d8da9`。基线当时等于 `origin/main` `3844727`。开放 PR 只剩无关的 #230。
- CloudRun `dizical-prod-163`：Status `normal`，FlowRatio `100`，162 已降为 0。BuildId `2612858672`，RunId `multi_tenant_1xSmmTKeFn0wAG`。创建 2026-11-16 10:49:18，流量切完 10:55:51 CST。
- `/health/live` 200 `alive`；`/health/ready` 200，database ok，lesson_count 37，cos_ok true。
- `/practice-dsh` 302 到登录，`X-Dsh-Build` 未取到，记 skipped。
- 本机 8765 未重启。
