# PR #323 独立审计 — minimax 原始报告 + hermes 逐条复核

- 审计对象: `feat/sprint-26091101-badge-3d-ccg` @ `dcb4868` vs `main`（28 commits / 84 files / +12,122 −17）
- 审计人: **minimax**（hermes subagent，只读命令，原始报告见 `audit-pr323-minimax-raw-2026-09-13.md`）
- 复核人: **hermes**（逐条反证，本节为准）
- 日期: 2026-09-13

## 一句话结论

**GO-with-nits → 修完 4 处小问题后 GO。** minimax 报 1×P0 + 3×P1；复核后：**真问题 4 处（无 P0，且都不是它报的 P0/P1 那条）**，误报 3 处。

## 一、真问题（已修，本 PR 内）

### 1. 测试 fixture 漂移：card_stars 列缺失 ⇒ 分支全量 **27 failed**（真 P1，minimax 报对了方向、报错了位置）

- 根因：`badge_db.insert_achievement_row` 的 INSERT 已扩到 **17 列**（含 `card_theme` + `card_stars`，`badge_db.py:299-310`），但测试自建表语句只补到 `card_theme`：
  - `tests/conftest.py:47`（共享 fixture）
  - `tests/test_badge_db.py:42`
  - `tests/test_badge_commit_version_sync.py:64`（`test_badge_commit_meta_mapping` / `test_cond_text_*` / `test_unlock_strategy` 全部复用此文件 helper）
  - `tests/test_achieved_at_override.py:42`
  - `tests/test_replace_image_endpoint.py:111`
- 现象：`sqlite3.OperationalError: table achievements has no column named card_stars`
- 取证（干净 worktree `git worktree add /tmp/dizical-headcheck dcb4868`）：
  - HEAD 全量 `pytest tests/ -q` ⇒ **27 failed, 705 passed, 8 skipped**
  - 修后全量 ⇒ **732 passed, 8 skipped, 0 failed**
- 修法：上述 5 处建表语句各补一行 `card_stars INTEGER`（纯测试文件，不动生产代码）。

### 2. `API-CHANGELOG.md:13` §1.1 主题映射与代码/线上不一致（真问题，但错在文档）

- 代码真值 `badge_theme.py:22-30`：突破→azure / **执着→bamboo** / 段位→bamboo / **巅峰→coral** / **晋级→coral** / 神秘→imperial
- 文档原文：执着→azure、晋级→azure、**漏了巅峰**
- 线上实测 `GET /api/achievements`（46 行）：azure 25 / bamboo 14 / coral 6 / imperial 1 —— 与代码一致，文档是错的
- 影响面：dizical-minip 按此文档同步主题，**必须修文档**
- 修法：改 `API-CHANGELOG.md:13` 三处（已改）

### 3. `badge_claim.py:246` 审计表 `session_id` 列被塞入 `badge_id`

- `practice_audit_log` 的 `session_id` 语义属练习 session；badge 领取无 session，原实现把 `badge_id` 同时写进 `session_id` 与 `detail`
- 修法：该位改 `None`（`detail` 已保留 badge_id）
- **未做**：历史脏行（`session_id = detail = badge_id`）清理 —— 审计表属合规源，等 dad 授权

### 4. `badge-ccg-themes.css:5` 头注释陈旧

- 注释写「4 个非默认主题块」，实际 7 块（深色 bamboo/coral/imperial/frost + 淡色 pearl/mint/sakura）
- 修法：改注释（已改）

## 二、误报（给出反证，勿按原报告处理）

| minimax 原结论 | 复核结果 | 反证 |
|---|---|---|
| P1-2：`ensure_card_stars_column` 可能没实现 ⇒ 生产 500 | **假** | `badge_db.py:120` 有实现体，`app.py:47` 启动 hook 已接线；相关测试 45 passed |
| P1-3：demo 下拉暴露的 pearl/mint/sakura「无 CSS 块、选了没反应」 | **假** | `badge-ccg-themes.css:153 / 222 / 289` 三块都在（仅头注释陈旧，见真问题 4） |
| ⑥-2：CHANGELOG 说 46 行、prod 只 44 行「数据漂移」 | **假** | 线上 `GET /api/achievements` 实测 **46 行**，分布 2★×25 / 3★×14 / 4★×3 / 5★×4 与 §1.4 完全一致 |
| P0-1 定级（主题映射不一致） | 方向对、层级偏高 | 不影响运行，属文档缺陷 ⇒ 归 P2 处理（已修） |

## 三、复核认定成立但**未修**（backlog，等 dad 拍）

1. `badge-ccg.js:638/654`：模块加载即启 rAF，`loop()` 每帧无条件重排，无停止出口；0 卡空转（单进程单循环，开销≈0）
2. `badge-ccg.css:1355-1362`：`prefers-reduced-motion` 块只关 `animation`，320ms opacity transition 未关（frame::after / spec / laser / security 4 处）
3. gsap 走 CDN（demo 页 + `_badge_claim_modal.html`），无本地兜底
4. 云 MySQL 断连无重试：2026-09-13 09:52 实测 `/api/achievements` 首次 **500**（`pymysql CR_SERVER_LOST: Lost connection to MySQL server during query`），重试即 200
5. audit 表历史脏行清理（真问题 3 的收尾）

## 四、审计纪律备注

- minimax 全程只读（git show / grep / sed / wc），未跑测试、未改文件、未重启服务，符合派活约束
- **subagent 报告 ≠ 事实**：本轮 4 条真问题中仅 2 条来自它（且位置/层级均有偏差），3 条为其误报 ⇒ 采纳前逐条反证是必要步骤
- 反证手段：干净 worktree 复现（`dcb4868`）+ 线上 API 实测 + 源码全量 grep（注意 `grep -rn "ensure_card_stars"` 只搜一处 pattern 会漏定义体，应按函数名全仓搜）
