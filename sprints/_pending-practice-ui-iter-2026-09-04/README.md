---
status: index                # README, 不会被 sprint 引用, 但保持元数据一致
sprint: pending
date: 2026-09-04
---

# practice-ui-iter — Pending Sprint 包

> ⚠️ **这是 _pending_ 状态**，不是正式 sprint。
> 启动条件: dad 拍板 `integrated-draft.md` §5 的 4 个决策点（dial-knob / dashboard 暖白 / token 收敛 / 女儿账号）。

## 文件清单

| 文件 | 作者 | 角色 |
|---|---|---|
| `hermes-draft.md` | Hermes (w9:pC) | Hermes 独立诊断（11 个问题） |
| `agy-draft.md` | dizical-agy (w9:pM) | agy 独立诊断（9 个问题，含儿童物理场景视角） |
| `integrated-draft.md` | Hermes (integrator) | **dad 拍板的入口文档**（12 个问题，4 sprint 拆分） |

三份文档都加了 YAML frontmatter：
- `status: process-draft` — 明确不是 final，supersedes 关系在 integrated 的 supersedes 字段
- `sprint: pending` — 启动后改 sprint-id
- `activation_rule` — 5 步启动 SOP

## 启动 SOP（启动 sprint 时执行）

```bash
# 1. 拍板 integrated-draft §5 的 4 个决策点

# 2. mv 文件夹（去掉 _pending 前缀，加 sprint-id 后缀）
cd /Users/mt16/dev/dizical/sprints
mv _pending-practice-ui-iter-2026-09-04 sprint-<id>-practice-ui-iter
cd sprint-<id>-practice-ui-iter

# 3. 重命名 draft → v1 baseline
mv hermes-draft.md hermes-v1.md
mv agy-draft.md agy-v1.md
mv integrated-draft.md integrated-v1.md

# 4. 写正式 sprint.md（参考 STATUS.md 2026-09-03 sprint-26090903 模板）

# 5. 更新 v1 文件的 YAML:
#    - status: superseded
#    - sprint: <sprint-id>
#    - superseded_by: sprint.md
#    - 移除 note 里的 "启动时" 段，改成 "已 superseded by sprint.md @ <date>"
```

## 为什么放 sprints/ 而不是 docs/

3 份方案都直接对应未来一个 sprint 的执行输入。放 sprints/_pending-practice-ui-iter-2026-09-04/ 跟现有 sprint 习惯对齐（参考 sprints/sprint-26090903-stage-print-responsive/ 命名）。_pending 前缀让 sprint 启动前的诊断稿不会跟正式 sprint 混淆。

docs/ 那 3 份原稿（hermes/agy/integrated）**保留**，作为"立项前的思考过程"存档 — 跟 process-draft 状态一致。YAML 也加了 `superseded_by: null` 字段，启动后填。

## 历史归档

- docs/practice-ui-iter-2026-09-04-{hermes,agy,integrated}.md ← 原始 3 份（立项前稿）
- sprints/_pending-practice-ui-iter-2026-09-04/ ← 本文件夹（启动前的 _pending 副本）

启动后:
- sprints/_pending-practice-ui-iter-2026-09-04/ → sprints/sprint-<id>-practice-ui-iter/
- 文件重命名 -draft → -v1
- 写 sprint.md

不要删 docs/ 原稿，那是有意识保留的过程存档。