---
id: 26101701
type: sprint
version: 1.0.0
start_date: 2026-10-17
end_date:
status: 已完成（已部署 #144 + 徽章上架）
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
- [x] Warden 独立审计：`W_VERDICT=PASS`、`W_BLOCKERS=none`（P2 两条非阻塞）
- [x] dad 授权后 merge：PR #371 merged，merge commit `f4e9df477ebd2179af6711fc72f1d7a9ca8a9df2`
- [x] CloudRun deploy #144（镜像 `dizical-prod-144-20261017221827`，`Status=normal` / `FlowRatio=100` / `HasTraffic=true`）；build log 见 `inflating: src/kid_app/badge_webp.py`（22:18:58）与 `Image pushed successfully`（22:22:00），镜像内 `scripts/` 命中 0；`/health/live` 与 `/login` 均 200
- [x] 真实 badge commit 一次：`grade_2_excellent`「二级考级优秀」（dad 拍板 id）→ 生产三表写入并复查
- [x] 重复徽章去重：删 `grade_5_excellent` 三表行 + 旧草稿 + 旧 COS 对象
- [x] 收尾：已合分支与临时 worktree 清理

## PR

- URL：`https://github.com/mariusiaowego-commits/dizical/pull/371`
- 实现 commit：`ad9edf9356a9ce4444e1708f8ad23da0a148ba31`；docs follow-up：`e13376c5c734d1b74158c67d12d607cd14965a81`（head `956492d`）。
- 合并结果：`merged=true`、`state=closed`、`merged_at=2026-10-17T06:41:55Z`；merge commit `f4e9df477ebd2179af6711fc72f1d7a9ca8a9df2`；仓库 `delete_branch_on_merge=false`，feature 分支保留。
- 合并树与 PR head 树相同（`git diff 956492d f4e9df4` 为空）。
- deploy：已完成 —— CloudRun `dizical-prod` deploy #144（2026-10-17 22:18→22:23），源码取自 `origin/main` @ `bd90527` 的干净 worktree；部署前 `src/kid_app/badge_webp.py`、`src/kid_app/badge_draft.py` 双侧 md5 一致；未传 `envParams`，未动 DB/COS/.env。
- 回滚路径：控制台切回 deploy #143（镜像 `dizical-prod-143-20261016131126`）。

## 徽章上架（同日，dad 授权）

- id 决策：草稿原 id `grade_5_excellent` 与 name/`cond_text` 的「二级考级」不一致 → 改为 `grade_2_excellent`（现有 `grade_1`..`grade_10` 对应 1..10 级）。
- 执行：新建草稿 `2026-10-17_grade_2_excellent_6fcd77`（COS）→ `POST /config/api/badge/draft/{id}/image` 推 1024×1024 RGBA PNG（sha256 `24ecca7970d1f6ae1d57a2ba2ab3ccd456c1e5e6532f8a3096193f2fc24faeb1`，1857894 B）→ `POST /config/api/badge/commit-from-draft`。
- 写入（生产 MySQL 实测）：`achievements` `grade_2_excellent`「二级考级优秀」card_no 48 / sort_order 41 / display_on_achievements 1 / achieved_at_override 2026-10-31 / unlock_strategy immediate；`achievement_badges` url `…/badges/grade_2_excellent_v1.png` version 1 is_current 1 is_locked 0；`achievement_stats` achieved=Y。
- 去重：22:41:10 页面「待确认」把旧草稿提交成 `grade_5_excellent`（card_no 49，同名同图）→ 页面上出现两张相同卡。dad 拍板保留 `grade_2_excellent`；已删三表 `grade_5_excellent` 行（MCP `runStatement` 留审计）、`DELETE /config/api/badge/draft/2026-10-17_grade_5_excellent_137a5b`、`manageStorage delete badges/grade_5_excellent_v1.png`。
- 复查：dup 计数全 0 / keep 计数各 1；achievements 总数 48；旧 COS key 404、新 key 200（1857894 B）；旧草稿 404、新草稿 200。
- 未做：容器内真实 commit 的 traceback 复验（懒加载路径不在启动时执行）；线上 UI 渲染需 dad 浏览器确认（`/achievements` 匿名访问 302 到 PIN 页）。

## 状态

已完成。代码在 `main`：PR #371 merge commit `f4e9df4`、docs PR #373 merge commit `bd90527`。生产已部署 deploy #144（2026-10-17 22:18→22:23），镜像内 `src/kid_app/badge_webp.py` 存在、`scripts/` 不存在。同日完成一次真实 badge commit（`grade_2_excellent`「二级考级优秀」）与重复徽章去重，均在生产 MySQL / COS 复查通过。
