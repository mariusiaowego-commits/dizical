---
id: 26092002
type: tech-spec
version: 0.1.0-stub
date: 2026-09-20
status: stub — 待 dad 拍板后写入仓库 + Obsidian 镜像
project: dizical
sprint: sprint-26092002-cleanup-repo
summary: "历史遗留收尾的技术实施切分 — 3 commit 单文件 add / gitignore 门 / worktree + 远端分支处置矩阵 / STATUS.md 回写"
tags: [dizical, cleanup, tech-spec, sprint-26092002]
---

# TECH-SPEC · sprint-26092002-cleanup-repo

> STUB 说明: 结构按仓内 tech-spec 惯例; 数据/命令均来自 9-20 实跑输出。

## 1. 实施切分 (3 commit, 1 PR)

| # | commit | sha | 文件数 | 内容 | 行数 |
|---|--------|-----|--------|------|------|
| 1 | `chore(sprint)` | 3e39953 | 15 | sprint 26091901 四件 + 26091701 四件 + `_pending` 四件 + 本 sprint 主记录+verify + `sprints/decision-log.md` (+6 行) | +2387 |
| 2 | `chore(docs)` | 75861c5 | 62 | `docs/screenshots/uiux-audit-2026-09-08/` 57 png (7.7M) + practice UI 素材 4 md + `docs/ai-inspire-plan-integration.md` | +1097 |
| 3 | `chore(dizical-ai)` | 6819931 | 10 | dizical-ai 源码 8 + `.dockerignore` (typo 修) + `.gitignore` (+1 行忽略 `dizical-ai/.cloudrun-deploy/`) | +2051 |
| — | 合计 | 6819931 | **87** | +5535 / -0 | — |

硬约束: 单文件 `git add`, 禁 `-A` / `.`; 每 commit 后 `git status --porcelain` 校验; 3 commit 后必须为空; 禁 push main; 不碰 `AGENTS.md` / `SOUL.md` / `config.yaml`。

## 2. 忽略门 (gitignore) — 本次的「边界」

| 路径 | 规则 | 处置 |
|------|------|------|
| `docs/handoff-archive/` | `.gitignore:49` | 归档件**本地留存**, 不入库 (不要 `-f`) |
| `STATUS.md` | `.gitignore:54` | L15/16 补丁只改工作区, 不入 commit |
| `dizical-ai/node_modules/` `.cloudrun-deploy/` `logs/` | `.gitignore:96/97` + 本次新增 | 黑名单, 永不入库 |
| `sprints/sprint-26092002-cleanup-repo-2026-09-20/` | 入 commit 1 | 本 sprint 文档 (空目录 git 不跟踪, 先写文件) |

## 3. STATUS.md 回写 (工作区补丁, 不入 git)

- 补丁文件: `/tmp/status-line15-16-fix.patch` (11 行, 1 hunk `@@ -13,6 +13,6 @@`; 已 `git apply --check` 通过)
- 删: 「CloudRun Deploy #132 触发中, MCP cloudbase auth 过期, 待 dad 重启设备码登录完成部署 …」
- 换: 「**CloudRun Deploy #132 已 9-19 12:20:40 全量切流** (BuildId 2605705748, 镜像 dizical-prod-132-20260919122049, FlowRatio 100, HasTraffic true) … 2026-09-20 复核 MCP cloudbase `auth_status: READY` … **无待 dad 部署动作**」
- 删: 「Deploy 阻塞需 dad 介入设备码登录.」 → 换「部署已于 9-19 12:20 完成」
- 现状 (9-20 12:30 实跑): 旧文案 0 命中 / 新文案 1 命中 → **已生效**

## 4. worktree + 分支处置矩阵

| 对象 | 现状证据 | verdict | 命令 |
|------|----------|---------|------|
| `/private/tmp/dizical-verify` | 目录不存在, 登记 prunable | **prune 已做** | `git worktree prune` |
| `hygiene-260917` (`chore/repo-hygiene-260917` 9293ebe) | `.gitignore` 与 main **逐字节相同**; 远端已 gone; 非 main 祖先 | **删 (需 ack)** | `git worktree remove <path>` + `git branch -D` (`-d` 会拒) |
| `timer-260917` (`fix/timer-ruler-drag-260919` 079d1e0) | `git diff --quiet main <branch>` → **TREES EQUAL** | **defer** | 等 dad 说「可以合了/关闭分支」 |
| `origin/docs/sprint-26091801-closeout` | cherry-pick 等价集空, 无 branch 独有文件 | 删 (需 ack) | `git push origin --delete …` |
| `origin/feat/practice-timer-ui-260917` | 无 branch 独有文件 (差异全是 main 后续新增) | 删 (需 ack) | `git push origin --delete …` |
| `origin/fix/timer-ruler-drag-260919` | TREES EQUAL | defer 同 timeout | — |
| `origin/feat/miniprogram-url-link` | 1 ahead / 105 behind; main 里 `url-link` 0 命中 → 未 merge, dad 已拍「不动」 | 保留 | — |

## 5. PR 路线

`branch chore/cleanup-repo-260920 → 1 PR 含 3 commit → 等 dad merge` (不直 push main; 不只本地 commit —— 会造成 local/main 与 origin 分叉)。
安全修复另开 1 PR: `fix/e2e-cred-scrub-260920` (0cf2d6d, 5 文件 +72/-8)。

## 6. 回滚

3 commit 互相独立: `git revert 6819931` / `75861c5` / `3e39953` 可分别回; PR #342 回滚 = `git revert 0cf2d6d` (会恢复明文, 不推荐)。

## 7. 不做 (红线)

不重启服务 / 不动 daemon / 不调 mcp__cloudbase / 不 force push / 不改 `AGENTS.md` `SOUL.md` `config.yaml` / 不进 git history 改写。
