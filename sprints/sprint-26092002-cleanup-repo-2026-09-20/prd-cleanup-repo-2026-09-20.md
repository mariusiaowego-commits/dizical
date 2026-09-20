---
id: 26092002
type: prd
version: 0.1.0-stub
date: 2026-09-20
status: stub — 待 dad 拍板后写入仓库 + Obsidian 镜像
project: dizical
sprint: sprint-26092002-cleanup-repo
summary: "历史遗留一次性收尾 — 主仓 83 个未跟踪文件入库 / 3 个 worktree 残留 / 4 个远端 orphan 分支 / /tmp 36 件临时稿 / STATUS.md 过期回写"
tags: [dizical, cleanup, repo-hygiene, sprint-26092002]
---

# PRD · 历史遗留收尾 (sprint-26092002-cleanup-repo)

> STUB 说明: 框架已按仓内 PRD 惯例 (id/type/version/date/status/project/sprint) 填好, 实质内容取自 2026-09-20 的 review 报告 + PR #341/#342 body; dad 可快速补/删。

## 1. 背景与触发

dad 2026-09-20 上午让 orchestrator 检查 git 状态, 发现四类历史遗留同时存在:

- 主仓 `main` @ `2aee3fb` 上有 **11 条目 / 83 文件** 未跟踪或改动 (sprint 文档、UI 素材、dizical-ai 源码、decision-log 改动)
- **3 个 worktree**: `/private/tmp/dizical-verify` (目录已不存在, 仅剩登记, prunable) + `hygiene-260917` + `timer-260917`
- **4 个远端 orphan 分支**: `docs/sprint-26091801-closeout` / `feat/practice-timer-ui-260917` / `fix/timer-ruler-drag-260919` / `feat/miniprogram-url-link`
- **/tmp 36 件** sprint 临时稿 (16 个 sprint-26091901-* + 20 个核查/过程物)
- 附加: `STATUS.md` §0 第 15/16 行仍在说「Deploy #132 触发中 / MCP auth 过期 / 待 dad 设备码登录」, 与事实相反 (9-19 12:20 已全量切流)

dad 拍板: 「全部走 deepseek review, 按 verdict 收干净, 走 sprint-workflow」。

## 2. 用户故事

> 作为唯一决策人, 我希望打开仓库时看到的是一个干净的工作区 —— 该入库的东西入库, 该忽略的忽略, 过期文档改对, 不留「不知道要不要删」的中间态, 这样下次改动不会在脏树上叠加。

## 3. 范围 (本次做)

1. 主仓 83 文件 → **3 commit** 入库 (sprint 文档 / UI 素材 / dizical-ai 源码)
2. `STATUS.md` L15/16 回写 (工作区改, 按 `.gitignore:54` 不入 commit)
3. /tmp 清理: 归档 9 (审计链) → `docs/handoff-archive/` (本地, 不入库); 删 19 → `/tmp/trash-26092002/` (closeout 一次清); 保留 10
4. `git worktree prune` 清 `/private/tmp/dizical-verify` 登记

## 4. 明确不做 (等 dad 拍)

| 不做项 | 理由 |
|--------|------|
| P0 密码洗脚本 | dad 已自走改密; 明文清洗另开 sprint 26092003 (`fix/e2e-cred-scrub-260920`), 不混进 chore PR |
| destructive 3 件 (worktree remove / 远端分支删) | PR 合后单独走, 需 dad 显式 ack |
| `timer-260917` + 其分支 | handoff §六.3: 等 dad 明确说「可以合了/关闭分支」 |
| `origin/feat/miniprogram-url-link` | STATUS.md:55 记 dad 已拍「不动」(PR #230 仍 OPEN) |
| 清 git history 里的旧明文 | 需 git filter-repo 改写所有 sha, 影响所有 PR; 不推荐 |

## 5. 验收标准

- [ ] `git status --porcelain` = 空
- [ ] `git diff main..HEAD -- src/ tests/` = 0 产品代码改动
- [ ] 3 commit 文件数 = 15 / 62 / 10, 总计 87 文件
- [ ] `grep -c "MCP cloudbase auth 过期" STATUS.md` = 0; 新版本文案命中 1
- [ ] `ls docs/handoff-archive/ | grep -c 26091901` = 9
- [ ] `git worktree list` = 2-3 条 (无 prunable)
- [ ] PR #341 / #342 均 MERGED; tag `sprint-26092002-cleanup-repo-complete` 已推

## 6. 关联

- review 报告: `/tmp/dizical-cleanup-review-260920.md`
- /tmp 清理清单: `/tmp/tmp-cleanup-checklist-260920.md`
- commit 拆分: `/tmp/commit-plan-260920.md`
- push 策略: `/tmp/push-strategy-260920.md`
- warden PR audit: `/tmp/warden-audit-cleanup-260920.md`
- 执行方复核: `/tmp/minimax-warden-review-260920.md`
- PR: [#341](https://github.com/mariusiaowego-commits/dizical/pull/341) (chore), [#342](https://github.com/mariusiaowego-commits/dizical/pull/342) (security)
