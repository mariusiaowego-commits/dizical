---
sprint: sprint-26092003-secret-scrub
date: 2026-09-20
status: 已完成
branch: fix/e2e-cred-scrub-260920 (已 squash merge → main 6b969ba)
base: origin/main @ 2aee3fb → 6b969ba
worktree: 未建独立 worktree, 直接在主 checkout /Users/mt16/dev/dizical 完成
commit:
  - 0cf2d6d fix(security) 5 files +72/-8 (PR #342)
  - 6b969ba squash merge of #342
pr:
  - 342: fix(security): 洗 e2e 脚本明文 dad 密码 + 防回潮契约 — MERGED 2026-09-20T05:11:51Z
tag: (无独立 tag, 随 sprint 26092002 cleanup tag 一并结)
author: orchestrator pane w10:pA (deepseek-v4.1-flash, 接单后执行) — 发现方 = minimax pane w10:pB (deepseek-v4.1-flash, 历史遗留 review)
reviewers: dad (改密 + 终审 merge) + warden pane w10:pD (MiniMax-M3, PR-level audit W_VERDICT=MERGE)
---

# sprint-26092003-secret-scrub — 洗 e2e 脚本明文 dad 密码 + 防回潮契约

## 触发

2026-09-20 上午, minimax pane 在「历史遗留 review」中扫出 P0: `scripts/e2e_sprint_26091901/` 4 文件含 **dad 账号明文密码 7 处**, 且已随 commit `2aee3fb` (PR #340, sprint 26091901) 进入 main 并推到远端。READM 里自承「PR merge 后由 dad 改密」, 但 merge 后未改。

dad 2026-09-20 拍板: **本人亲走改密** (agent 不碰凭据), 洗脚本走独立 PR。

## 范围

| # | 文件 | 改动 |
|---|------|------|
| 1 | `scripts/e2e_sprint_26091901/e2e_dom_state.py` | `os.environ.get("PASSWORD", "<明文>")` → `os.environ["PASSWORD"]` |
| 2 | `scripts/e2e_sprint_26091901/e2e_interactions.py` | 同上 |
| 3 | `scripts/e2e_sprint_26091901/e2e_touch_action.py` | 同上 |
| 4 | `scripts/e2e_sprint_26091901/README.md` | 删 3 处明文, 改 `<your-password-here>` 占位 + 必填说明 |
| 5 | `tests/test_e2e_secret_scrub.py` | **新增** 3 条契约 (防回潮) |

## 关键修法

**3 个 .py → 强制 env 读取**: `PASSWORD = os.environ["PASSWORD"]`
- KeyError 是**预期行为**: 运维忘传 `PASSWORD` 时脚本立刻报错, 而不是静默用错密码登录
- 形态上杜绝「不留神又把默认值写回去」——`os.environ.get("PASSWORD", <字面量>)` 这种写法本身就没了

**README**: 删明文示例, 改占位符 + 明示「必填, 不要 commit 明文」。

**3 条契约** (`tests/test_e2e_secret_scrub.py`):
| 契约 | 断言 |
|------|------|
| `test_no_plaintext_password_in_e2e_scripts` | 4 目标文件全文 grep 旧明文 = 0 命中 |
| `test_e2e_scripts_force_password_env` | 3 个 .py 必须含 `os.environ["PASSWORD"]`, 且**不得**出现 `os.environ.get("PASSWORD", ...)` 形态 |
| `test_e2e_readme_has_password_required_hint` | README 明示必填 + 不含明文 |

**负控 (三遍)**: 注水把明文塞回 `e2e_dom_state.py` → 2 条断言红 (红线含两端原文) → 改回 → 重跑绿。3 passed。

## 测试与验收

- 局部: `python3 -m pytest tests/test_e2e_secret_scrub.py -v` → **3 passed** (warden 独立复跑同样 3 passed)
- 语法: 3 个 .py `ast.parse` 通过
- 明文复扫: `grep -rn <旧明文> scripts/e2e_sprint_26091901/*.py *.md` → **0 命中**
- 唯一残留: `tests/test_e2e_secret_scrub.py` 内的哨兵常量 + 注释 (刻意保留 —— 要断言「旧值永不再入仓」必须写出该字面量; 若 dad 要求连这处也不留, 改为片段拼接即可, 非阻断)
- PR-level audit: warden `W_VERDICT=MERGE`, 5 项 PASS, ITEM_TEST_REPLAY 3/3

## 不该变什么 (已核)

- 0 产品代码改动 (`git diff main..HEAD -- src/` = 0; 仅新增 1 个测试文件)
- 0 push origin/main (走 feature branch + PR)
- 未碰 AGENTS.md / SOUL.md / config.yaml (dad 8-30 红线)
- 未重启服务 / 未动 daemon / 未调 mcp__cloudbase

## 风险与已知遗留

| 风险 | 状态 |
|------|------|
| 历史 commit (`2aee3fb` 及更早) 仍含明文 | **不可消除** (除非 `git filter-repo` 改写全部 sha, 影响所有 PR + 远端 ref); PR body 已自承, 不做 |
| e2e 脚本今后跑需传 env | 预期行为: `export PASSWORD=<新密>` 后才跑; 不传即 KeyError (这是防御, 不是 bug) |
| dad 改密完成情况 | dad 2026-09-20 自报已完成改密 (agent 未参与、未验证、未持有凭据) |
| `/tmp/e2e_check.py` (含同一明文) | 已随 closeout 的 `/tmp/trash-26092002/` 清除 (2026-09-20) |

## 关联

- PR: https://github.com/mariusiaowego-commits/dizical/pull/342 (MERGED)
- squash sha: `6b969ba`
- warden PR-level audit: `/tmp/warden-audit-cleanup-260920.md` (含 PR #341 + #342)
- 上游 review (发现方): `/tmp/dizical-cleanup-review-260920.md` §P0
- 姊妹 sprint: `sprint-26092002-cleanup-repo` (历史遗留收尾, 同批 PR)
- 主仓 sprint dir: `/Users/mt16/dev/dizical/sprints/sprint-26092003-secret-scrub-2026-09-20/`
- Obsidian 镜像: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/sprints/sprint-26092003-secret-scrub-2026-09-20/`
