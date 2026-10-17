---
id: 26101701
type: sprint
version: 1.0.0
start_date: 2026-10-17
end_date:
status: 进行中
priority: 高
summary: "修复生产 badge commit 因运行时代码依赖被排除 scripts/ 而无法派生 WebP 的 P0"
tags: [sprint, dizical, badge, webp, p0]
plan: "[[plan-badge-webp-ship-2026-10-17]]"
---

# Sprint 26101701 · Badge WebP 运行时依赖修复

## 触发

2026-10-17 生产 `/config/badge` 确认 badge 报错：`/app/scripts/generate_badge_webp.py` 不存在。`.tcbignore` 排除 `scripts/`，而 `badge_draft` 运行时按文件路径从该目录动态加载 WebP 编码实现；Storage First 因而在入库前失败，commit 与 replace-image 都受影响。

## 范围

- 运行时 WebP 实现移至 `src/kid_app/badge_webp.py`。
- `badge_draft` 改为包导入；`scripts/generate_badge_webp.py` 保留 CLI 兼容壳。
- 增加回归守卫，保持双档规格与 Storage First 失败语义。
- 不改 main、不碰 `data/`、不改 `.tcbignore`；不修设计 demo 服务脚本调用。
- 不执行真实生产 badge commit。草稿 id `grade_5_excellent` 与“二级考级优秀”的等级含义疑点需 dad 决定。

## 基线与分支

- Worktree：`.worktrees/badge-webp-ship-261017`
- Branch：`fix/badge-webp-import-from-pkg-261017`
- Base：`origin/main` @ `85ea81b`

## 进度

- [x] 接收并核对交接 brief 与 WIP 范围
- [x] 建立 sprint plan / 验收 / 决策记录
- [x] 复跑 8 条守卫测试 + badge COS/route 安全回归（60 passed, 5 warnings）；全量测试因既有 data/ 写路径未运行
- [x] 两轮独立 review：round 1 的 P2 已修，round 2 无新增问题
- [x] commit `ad9edf9` + push feature branch + PR #371 opened; 6-question review packet in PR body
- [ ] dad review / 拍板；之后 merge、CloudRun deploy、只读上线验证

## PR

- URL：`https://github.com/mariusiaowego-commits/dizical/pull/371`
- Head：`ad9edf9356a9ce4444e1708f8ad23da0a148ba31`
- GitHub checks：当前无 checks 报告
- Merge / deploy / 真实 badge commit：未执行，等 dad review 与 ID/等级决定。
- [ ] 真实 badge commit（需先解决草稿 id 业务疑点并单独确认）

## 状态

进行中。代码仍是接手前 WIP；本 sprint 当前不执行合并、部署或生产数据写入。
