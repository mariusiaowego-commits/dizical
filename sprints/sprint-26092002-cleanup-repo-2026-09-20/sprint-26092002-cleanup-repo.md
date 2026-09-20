---
sprint: sprint-26092002-cleanup-repo
date: 2026-09-20
status: 进行中
branch: chore/cleanup-repo-260920
base: origin/main @ 2aee3fb
worktree: /Users/mt16/.herdr/worktrees/dizical/cleanup-260920 (待建)
author: orchestrator pane w10:pA (MiniMax-M3) + minimax pane w10:pB (deepseek-v4.1-flash, read-only review)
reviewers: dad (终审 + merge)
---

# sprint-26092002-cleanup-repo — 历史遗留收尾 + 主仓 dirty 入库

## 触发
dad 2026-09-20 上午让 orchestrator 检查 git 状态, 发现主仓 main `2aee3fb` 上有 11 条目 / 83 文件 dirty + 3 个 worktree 残留 + 4 个远端 orphan 分支 + /tmp 16 个 sprint 临时稿. 拍板 "全部走 deepseek review, 按 verdict 收干净, 走 sprint-workflow".

## 范围 (本次 sprint 做)
1. **主仓 dirty 11 条目 / 83 文件 → 3 commit 入库**:
   - `chore(sprint)` 13 文件: sprint 26091901 / 26091701 closeout 文档 + decision-log + _pending 草稿
   - `chore(docs)` 63 文件: UI/UX 审计截图 57 png + practice UI 迭代素材 6 md
   - `chore(dizical-ai)` 10 文件: dizical-ai 源码 8 文件 + .gitignore 1 行 + .dockerignore typo 修
2. **STATUS.md §0 第 15/16 行回写**: "deploy 阻塞 + MCP auth 过期" → "Deploy #132 已 9-19 12:20 全量切流"
3. **/tmp 清理**: 归档 9 (sprint-26091901 agy/warden 审计链) → `docs/handoff-archive/` (本地, 不入库); 删 19 (过程稿 + 本 pane 临时物) → `/tmp/trash-26092002/` (closeout 时一次清); 保留 10
4. **git worktree prune** `/private/tmp/dizical-verify` (detached HEAD, 目录已不存在, 仅清登记)

## 范围 (本次 sprint 不做, 等 dad 拍)
- ❌ **P0 密码洗脚本**: 单独走 sprint-26092003-secret-scrub 分支 (`fix/e2e-cred-scrub-260920`), dad 已自走改密, 我不碰凭据
- ❌ **destructive 操作** (本 PR 合后 dad 拍板再走): `hygiene-260917` worktree remove + 本地分支 -d + 远端 2 orphan 分支删 (`docs/sprint-26091801-closeout` / `feat/practice-timer-ui-260917`)
- ❌ **`timer-260917` worktree + 分支**: 按 handoff §六.3 defer (等 dad 明确说"可以合了/关闭分支"); review 已证 `git diff --quiet main origin/fix/timer-ruler-drag-260919` TREES EQUAL, 内容已零差异, 不急
- ❌ **`origin/feat/miniprogram-url-link`** (44 天未动, STATUS.md:55 dad 已拍"不动"): 保留
- ❌ **`origin/fix/timer-ruler-drag-260919`**: 按 §六.3 defer (与 timer-260917 同步)

## push 路线
`branch chore/cleanup-repo-260920 → 1 PR 含 3 commit → 等 dad review+merge`

不直 push main (sandbox 拦 force-push, 绕 review); 不只本地 commit (closeout 文档困本地, 之后必分叉).

## 硬约束
- 单文件 `git add`, 禁 `-A` / `.`; 禁 push (push 归 PR 步骤)
- 每个 commit 后跑 `git status --porcelain` 校验, 3 commit 后必须为空
- sprint doc / STATUS.md 改本地工作区, 不入 commit (被 .gitignore 忽略)
- 不碰 AGENTS.md / SOUL.md / config.yaml (dad 8-30 红线)
- 不重启服务 / 不动 daemon
- owner 拼写 `mariusiaowego-commits` (中段 o-w-e-g-o), 不可手打

## 进度
- [x] dad 拍板 (9-20 11:36)
- [x] minimax pane review (w10:pB, 18.5K 报告 + /tmp/status-line15-16-fix.patch)
- [x] vault stub 建 (主仓 + Obsidian 镜像, 空目录)
- [x] deepseek 3 份详情交付 (tmp 清单 / commit 拆分 / push 策略)
- [x] vault 主记录 + verify (本文件 + verify-2026-09-20.md)
- [ ] git checkout -b chore/cleanup-repo-260920 origin/main
- [ ] commit 1 chore(sprint) — 13 文件
- [ ] commit 2 chore(docs) — 63 文件
- [ ] commit 3 chore(dizical-ai) — 10 文件
- [ ] STATUS.md L15/16 补丁 (工作区, 不入 commit)
- [ ] /tmp 归档 9 + 删 19
- [ ] git worktree prune
- [ ] git push + gh pr create (含 6 问 review packet)
- [ ] 等 dad review+merge
- [ ] closeout: vault 补齐 7 doc (剩余 5 doc: prd / tech-spec / test-plan / handoff / decision-log 追加) + tag `sprint-26092002-cleanup-repo-complete`

## 关联
- review 报告: /tmp/dizical-cleanup-review-260920.md (18.5K)
- /tmp 清理清单: /tmp/tmp-cleanup-checklist-260920.md (6.9K)
- commit 拆分: /tmp/commit-plan-260920.md (6.6K)
- push 策略: /tmp/push-strategy-260920.md (6.5K)
- STATUS.md 补丁: /tmp/status-line15-16-fix.patch (2.4K, `git apply --check` 通过)
- 上一 sprint: handoff-2026-09-19-sprint-26091901-timer-ruler-drag.md (本仓本地, .gitignore 忽略)
- 主仓 sprint dir: /Users/mt16/dev/dizical/sprints/sprint-26092002-cleanup-repo-2026-09-20/
- Obsidian 镜像: ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/sprints/sprint-26092002-cleanup-repo-2026-09-20/
