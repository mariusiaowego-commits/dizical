# sprint-26091401 · F1 生产验收 4 项修复

- **状态**: 代码完成 + 全量回归全绿 + PR 已提（**PR #328**）／待 dad 拍 merge
- **日期**: 2026-09-14
- **分支**: `feat/sprint-26091401-f1-card-modal-fix`（commit `aef6620`）
- **触发**: dad 在**生产**验收 B6 图鉴接线（PR #327 / deploy #125）后提的 4 条视觉问题
- **分工**: 方案 A —— agy（视觉：`badge-ccg.css` + 46 条文案）＋ hermes（后端字段/迁移/载荷、前端接线、独立闸门、全量回归、PR）

## 4 条问题 → 修复

| # | 现象（dad 原话） | 根因 | 修法 |
|---|------------------|------|------|
| 1 | `/achievements` 列表卡变「胶囊」 | `.ccg-stage-mount` 无 CSS ⇒ `--card-w: min(160px,100%)` 百分比自引用 = 0px ⇒ 卡 0×0 | mount 给宽（`width:100%; display:flex; justify-content:center`）+ 列表档 `min(160px, 44vw)` |
| 2 | `/badges` 卡片屏面没有卡 | 同 #1（`.badge-card` 同样 flex+column+center） | 同上，选择器显式含 `.b-card`/`.badge-card` |
| 3 | modal 典故太长（最长 501 字） | 卡背与 modal 共读 `description` | 新字段 `achievements.story_short`（≤60 字 / 46 条）+ 4 处载荷 + 卡背接线，modal 右侧仍读长典故 |
| 4 | modal 太小，3D 区不够震撼 | `min(920px,100%)` / `92dvh` / 卡区 `min(240px,46vh)` | `min(1240px,96vw)` / `94dvh` / 卡区 `min(400px,52vh)` / 右列 `flex:1 1 38%` |

**Q1 与 Q2 是同一个 bug**，不是两个问题。

## 验收数据（独立探针，非自报）

| 指标 | 修前 | 修后 |
|------|------|------|
| `.ccg-stage` | 0 × 0 | 160 × 240 |
| 卡片外壳 | 337 × 36（胶囊） | 191 / 224 / 317 × 276 |
| `--pointer-x / y` | `NaN%` | `85% / 20%` |
| `.ccg-rotator` 3D | 无 | `matrix3d(0.964, 0.0606, -0.2585…)` |
| modal（MBP 1728） | 920 上限 | **1240 × 672**，3D 卡 **400 × 600** |

## 全量回归（本 sprint 最大收获）

```
修前: 648 passed / 8 skipped / 119 errors / 261.40s
修后: 768 passed / 8 skipped / 0 failed / 0 error / 32.08s
基线: main b96a945 = 749 passed（768 = 749 + 19 个新测试）
```

`seed_story_short()` 0 行变更时不 commit ⇒ 隐式 BEGIN 留 RESERVED 锁 ⇒ 同进程建表 `database is locked`。**生产同害**，已修 + 加回归测试。

## 待办

- [ ] dad review + merge PR #328
- [ ] （merge 后）deploy ⇒ MCP 只读复核云端 `story_short` 行数，为 0 再走 MCP 补种
- [ ] 视觉终验交 dad 真机
- [ ] 环境清理（8766 / 8791 / 8793 / Chrome 9447）待 dad 拍
