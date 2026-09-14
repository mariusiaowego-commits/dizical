# plan · sprint-26091401 · F1 生产验收 4 项修复

## 为什么开这个 sprint

dad 在**生产环境**（deploy #125 之后）逐页验收 B6 图鉴接线时，发现 4 条视觉缺陷。这 4 条都在「dad 已认可的 demo 标准」与「生产实际呈现」之间：demo 页一切正常，生产两页的列表卡全塌。

## 拆解与归属（方案 A）

| 任务 | 归属 | 交付物 |
|------|------|--------|
| T1 几何修复（Q1+Q2，同根因） | agy | `badge-ccg.css`：`.ccg-stage-mount` 给宽 + 列表档绝对长度 |
| T2 modal 放大（Q4） | agy | `badge-ccg.css`：dialog / 卡区 / 右列三个数 |
| T3 卡背排版随卡缩放 | agy | `badge-ccg.css`：卡背字号/间距改 `calc/clamp(var(--card-w)…)` + 列表 `line-clamp 4` |
| T4 46 条「典故·短板」文案 | agy | `badge_story_short.json`（≤60 字、id 与 card_no 对齐） |
| T5 `story_short` 列 + 迁移 + 播种 | hermes | `database.py` / `badge_db.py` |
| T6 载荷接线（4 处）+ 前端卡背 | hermes | `app.py` / `minip_api.py` / 两个模板 / `badge-ccg.js` |
| T7 独立闸门（几何 / modal / 卡背） | hermes | `/tmp/ccgprobe/*` 探针实测 |
| T8 全量回归 + PR | hermes | 768 passed / 0 error ⇒ PR #328 |

## 关键决策

1. **Q1/Q2 合并处理**：先做根因侦查（复现台 `0×0` 实测）再动手，避免两处打补丁。复现台证明「几何一修，卡 + hover 3D 动画一起回来」，所以 3D 参数**一个都没改**。
2. **卡背文案走后端字段而非前端截断**：前端截断会在 60 字处截半句话；后端 `story_short` 由人写（面向 9 岁女孩），语义完整。回落链 `d.story_short || d.story` 保证未播种时卡背不空。
3. **不采信子 agent 自报**：agy 给的每个数都用 hermes 自己的探针复算（`.ccg-rotator` 矩阵、dialog 几何、卡背 clamp）。
4. **全量回归必须整跑**：子集一直绿，整跑才暴露 `database is locked` 的锁泄漏 —— 若按子集放行，这个 bug 会跟着 deploy 上生产。

## 风险与回退

- 回退面：仅 `badge-ccg.css`（视觉）+ `story_short` 新列（幂等、可空）。旧代码读到多余列不影响。
- `demo-archive/v1.5.0/` 自带 CSS 副本与线上不同源 ⇒ dad 认可的 3D 标准逐字节冻结，本 sprint 不动 demo。
