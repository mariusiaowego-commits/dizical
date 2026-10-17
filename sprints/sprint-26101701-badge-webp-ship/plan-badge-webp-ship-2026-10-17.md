---
source: ai-agent
project: dizical
sprint: sprint-26101701-badge-webp-ship
updated: 2026-10-17
version: 1.0
---

# Sprint 26101701 · Badge WebP 运行时依赖修复

## Goal

修复生产 `/config/badge` 提交与 replace-image 共用的 WebP 派生失败。运行时代码不再依赖 `.tcbignore` 排除的 `scripts/`；PNG 和两档 WebP 均成功后才允许继续写库，派生失败仍须 fail loud。范围仅限运行时 WebP 模块、CLI 兼容壳、回归测试和 sprint 文档；不改 main、不碰 `data/`、不改 `.tcbignore`。

验收：在 `scripts/` 不存在的部署形态下，运行时模块仍可 import 并派生两档 WebP；已有 badge commit 回归测试通过；全量测试无新增失败；独立 review 无未解决 P0/P1。生产部署和真实 badge commit 是后续门禁，不在本地测试中写生产数据。

## Blocking Questions (0–3)

无阻塞问题。用户已指定接手执行、沿用现有 worktree/分支、走 sprint-workflow，并明确禁止改 main 与触碰 `data/`。

## Assumptions

1. Data：本次不改数据库 schema、记录或 `data/` 文件；`tests/conftest.py` 把 badge 测试数据库重定向到 pytest 临时目录。
2. Failure：Storage First 契约不变；PNG 或任一 WebP 派生/上传失败时必须中止提交，不得先写三表或静默返回空内容。
3. Boundary：`.tcbignore` 的 `scripts/` 排除规则是既有部署约束；CLI 脚本可留在 `scripts/`，但运行时可导入实现必须在 `src/`。
4. State：`commit_image_from_draft()` 同时服务 commit 与 replace-image，两条路径继续共用同一派生 helper。
5. Environment：当前 worktree 基于 `origin/main` 的 `85ea81b`；生产 CloudRun 归档不会包含 `scripts/`。
6. Scope：`src/kid_app/routes/config.py` 中本地设计 demo 的 shell 脚本调用不属于本次 P0；不顺手改它。草稿 `grade_5_excellent` 与“二级考级优秀”的命名/等级疑点不属于代码修复范围，真实生产 commit 前须由 dad 决定。
7. Testing：先跑新增 WebP 守卫，再跑经确认不读写 `data/` 的 badge 回归；模拟 `scripts/` 缺失。因既有测试会直接读写 `data/`，不跑全量 pytest，明确报告未做 baseline 失败集对账；所有测试只在该 worktree 执行。

## Plan

1. Review WIP：核对 `src/kid_app/badge_webp.py` 是唯一实现，`badge_draft._webp_script()` 只 import 该包模块，CLI 壳仍导出兼容符号。
2. Validate tests：检查测试覆盖尺寸、RGBA/透明像素、小图不放大、坏输入报错、运行时模块路径、错误包装、静态守卫和 CLI identity；确认测试不访问 `data/`。
3. Verify：复跑新增守卫和 safe badge COS/route 子集；用隔离副本验证 `scripts/` 缺失；审计完整 diff 与未跟踪文件。跳过会访问或写入 `data/` 的测试。
4. Independent review：按 sprint 约定做两轮只读 review；记录每轮结论和闭环证据。
5. Ship：以显式文件清单 commit → push feature branch → 用 `gh-retry` 创建 PR；提交 PR review packet（6 问、变更清单、测试与双轮 review 结果）。等 dad review/拍板后再 merge/deploy；不触发真实生产 badge commit。

**Alternative considered and rejected**：在 `.tcbignore` 为 `scripts/` 加反向白名单。该目录是整体排除的本地工具链，反向规则语义未确认且会扩大部署包；将纯运行时实现搬入 `src/kid_app/`，保留 CLI 壳，是更小、更可靠的边界修复。
