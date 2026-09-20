---
id: 26092002
type: test-plan
version: 0.1.0-stub
date: 2026-09-20
status: stub — 待 dad 拍板后写入仓库 + Obsidian 镜像
project: dizical
sprint: sprint-26092002-cleanup-repo
summary: "cleanup sprint 的验收门 — 无功能测试, 全部为 git/gitignore/worktree/镜像一致性校验 + PR 级审计 (warden)"
tags: [dizical, cleanup, test-plan, sprint-26092002]
---

# TEST-PLAN · sprint-26092002-cleanup-repo

> STUB 说明: 本 sprint 是仓库卫生 chore, **不含产品功能**, 因此测试面 = 一致性校验 + 审计, 不跑 pytest (无 `src/` 改动)。以下命令全部为 9-20 实跑过的形式。

## In scope

| 类别 | 校验点 | 命令 | 期望 |
|------|--------|------|------|
| 工作区干净 | 3 commit 后无残留 | `git status --porcelain` | 空 |
| commit 完整性 | 3 commit / 文件数 | `git log --oneline -3` + `git show --stat HEAD~2 HEAD~1 HEAD` | 15 / 62 / 10 文件 |
| 产品代码零改动 | src/ tests/ 不动 | `git diff main..HEAD -- src/ tests/` | 0 行 |
| 忽略门 | 归档 / STATUS / dizical-ai 黑名单不入库 | `git ls-files \| grep -cE "docs/handoff-archive/\|STATUS.md\|dizical-ai/(node_modules\|\.cloudrun-deploy\|logs)"` | 0 |
| 截图入库 | 目录全入库 | `git status --porcelain docs/screenshots/uiux-audit-2026-09-08` | 空 |
| STATUS 回写 | 旧文案消失 | `grep -c "MCP cloudbase auth 过期" STATUS.md` | 0 |
| STATUS 回写 | 新文案出现 | `grep -c "Deploy #132 已 9-19 12:20:40 全量切流" STATUS.md` | 1 |
| /tmp 归档 | 审计链归档 | `ls docs/handoff-archive/ \| grep -c 26091901` | 9 |
| /tmp 删除 | 过程稿进 trash | `ls /tmp/trash-26092002/ \| wc -l` | ≥19 (实际 22, 另 pane 补 3) |
| worktree | prunable 清掉 | `git worktree list --porcelain \| grep -c prunable` | 0 |
| 远端分支 | 未动 main | `git ls-remote origin refs/heads/main` | `2aee3fb…` |
| PR 状态 | 两个 PR 开到 main | `gh pr view 341 --json mergeable` / `342` | `MERGEABLE` |

## Out of scope

- **产品功能测试 (pytest)**: 本次 0 个 `src/` 改动 → 不跑; PR #342 的 3 条契约测试属 sprint 26092003, 单独跑 (`python3 -m pytest tests/test_e2e_secret_scrub.py -v`)
- **部署 / 服务重启**: 0 daemon 改动, 不需要 deploy; 不调 mcp__cloudbase
- **destructive 操作**: worktree remove / 远端分支删 → 在 PR 合后单独走, 每条需 dad ack (不在本 test-plan 门内)

## 验收门

1. **硬门**: `git status --porcelain` = 空 + `git diff main..HEAD -- src/ tests/` = 0
2. **审计门**: warden PR-level audit 5 项全 PASS (`/tmp/warden-audit-cleanup-260920.md`), 0 P0 / 0 P1
3. **执行方复核门**: minimax 独立重跑 5 项一致 (`/tmp/minimax-warden-review-260920.md`), 5 条补充已并入 closeout 清单
4. **镜像门**: 主仓 `sprints/sprint-26092002-cleanup-repo-2026-09-20/` 与 Obsidian 同名目录 **md5 逐对一致** (含 5 件新 doc + decision-log)

## 负控 (为什么这台"锁"是真咬)

本 sprint 的"锁"是校验命令, 不是断言, 所以用**反事实抽检**证明它们会红:

| 校验 | 抽检方式 | 期望表现 |
|------|----------|----------|
| `git ls-files \| grep docs/handoff-archive/` | 若有人误 `-f` 强加归档件 | 计数 > 0 → 立刻可见 (本次 = 0) |
| `git diff main..HEAD -- src/` | 任一 commit 若带上产品代码 | 非空 → 阻断 (本次 = 0) |
| `grep -c "MCP cloudbase auth 过期" STATUS.md` | 补丁未打时 | = 1 (本次 0 → 说明补丁生效) |
| `git merge-base --is-ancestor chore/repo-hygiene-260917 main` | 若我误用 `git branch -d` | 返回 NOT ancestor → `-d` 必拒 (已在 destructive 清单里改成 `-D`) |

## 已知残留风险 (不阻断, dad 知会)

1. git history 仍含旧明文密码 (2aee3fb 及之前) — 清洗脚本只在工作树生效; 要清历史需 git filter-repo (改写所有 sha), dad 拍
2. 仓库 +7.7M 截图 (`.git` 368M → ~376M) — 9-8 原始审计资料, 不可逆, 建议保留
3. PR #342 的回归哨兵里仍保留旧密码字符串常量 (要断言"它不再出现"就得写它); 若 dad 要求彻底不留, 改拼接写法 (1 行, 非阻断)
4. `timer-260917` + 其远端分支未清 (defer, 等 dad 说)
