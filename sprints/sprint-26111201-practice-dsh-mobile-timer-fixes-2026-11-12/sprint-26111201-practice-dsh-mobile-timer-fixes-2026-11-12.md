---
id: 26111201
type: sprint
version: 1.0.0
start_date: 2026-11-12
end_date:
status: 已完成（PR #406 已合并 + 生产 deploy #162 已上线）
priority: 高
summary: "练习助手 dsh 手机端四修：字号抬档、计时中切布局二次确认、秒级时长、到点定格；并修 1 分钟时长选择失效"
tags: [sprint, dizical, practice-dsh, dsh, mobile, timer, v3.52]
---

# Sprint 26111201 · 练习助手 dsh 手机端四修 + 部署 #162

## 触发

dad 在手机端使用练习助手（`/practice-dsh`）时提出 4 个问题，随后追加「光 merge 没用，还要正式部署」：

1. 手机上仪表盘整体字太小，眼睛酸；
2. 计时过程中切换卡片布局会直接切断计时；
3. 计时不满 2 分钟（如 1 分 50 几秒）却被记成 2 分钟；
4. 需要逐项解释并做可验证测试：倒计时到点后是否自动结束计时并弹出提交确认弹窗。

## 范围

- 仅改 `src/kid_app/templates/practice-dsh.html`（DSH 版本 v3.51 → v3.52）+ 两个测试文件。
- 不改数据库 schema、不改公开 API、不改其他页面。

## 基线与分支

- Worktree：`/Users/mt16/.codex/worktrees/5eef/dizical`
- Branch：`feat/practice-dsh-mobile-timer-fixes`（head `ce25e67`）
- Base：`origin/main` @ `12abe15`（合并时为最新 main）

## 进度

- [x] 4 项需求逐条落地（字号 / 切布局拦截 / 秒级时长 / 到点定格）
- [x] 相关 pytest 6 文件 **130 passed**（`tests/test_practice_dsh.py`、`test_practice_dsh_edit_session.py`、`test_practice_dsh_popout_data.py`、`test_practice_dsh_save.py`、`test_practice_timer_frontend.py`、`test_config_practice_page.py`）
- [x] 13 处内联脚本 `node --check` 通过
- [x] 8765 本地端测：6 种布局组合 + A-only，60s 倒计时 → 弹窗 `01:00`、`curTick 59/60`；ticket `−` 路径与仪表盘银标 `−`/旋钮/ruler 三条路径均得 `canvasDur=1`
- [x] PR #406 squash-merge → `main` = `7b163aa`
- [x] 生产部署 CloudRun deploy **#162**：`Status=normal` / `FlowRatio=100` / `HasTraffic=true`，镜像 `dizical-prod-162-20261112101637`
- [x] 线上验收：`/health/live` 200；`/health/ready` `database=ok` `lesson_count=37` `cos_ok=true`；静态资产 `practice-dsh-assets/shared/ruler-production.js` 远端 sha256 与本地逐字节一致（25254 B）
- [ ] `X-Dsh-Build: v3.52` 响应头复核 —— **skipped**：线上 `/practice-dsh` 需登录，未获生产账号，未取到该头（见 verify 文档「未闭环项」）

## 改动清单（`src/kid_app/templates/practice-dsh.html`）

1. **手机字号抬档**（≤440px）：计时数字 11→12.5px，BPM 11→13px，今日时长 11.5→13px，pill 按钮 13→15px，站姿/节拍器 10.5→12.5px，诊断卡 12.5px。
2. **计时中禁止切布局**：`setCombo()` / `setMods()` → `layoutSwitchBlocked()` → `#czLayoutGuard` 二次确认；确认切换后用 `__czTicketElapsed()`（120/420/900ms 轮询）回填 Card A 读数，不丢已计时间。
3. **秒级时长**：统一走 `DizicalDur.fmt`，去掉 `Math.ceil`；110s 显示 `1分50秒`；R 卡科目分布改为「分钟 + 秒」两段相加。
4. **到点定格**：仪表盘单独计时结束时用 `finishDurationMin` 兜底；Card A 读数定格为 `MM:SS · 已暂停`，由 `__czSyncCardAElapsed` 同步。
5. **附加修复（`ce25e67`）**：仪表盘时长与 ticket 对齐 —— `leftDur()` 改读 `#rulerInput`，`onDuration('right_dash')` 改调 `ttSetDuration()`。此前代码去戳不存在的 `#pkTicketDurUp/Down`，导致「选 1 分钟」被硬编码的 10 覆盖（就是 dad 反馈的「选了 1 分钟到 1 分钟不停、进度条不达终点」的根因）。

## PR 与部署

- PR：`https://github.com/mariusiaowego-commits/dizical/pull/406`
- 合并：`7b163aa`（squash），合并前 base = 最新 `origin/main` @ `12abe15`
- 部署：CloudRun `dizical-prod` deploy **#162**（2026-11-12 10:16:29 起），镜像 `dizical-prod-162-20261112101637`
- 部署源：`.cloudrun-deploy`（`targetPath` 指向部署目录，非项目根）；部署前 `src/kid_app/templates/practice-dsh.html` 双侧 md5 一致（`f21b2256880846eb65a10fd8a09174e3`），根级 `.dockerignore` / `Dockerfile` / `schema_mysql.sql` 三份 md5 双侧一致，部署目录内无 `*.db`
- 回滚：控制台切回 deploy **#161**（镜像 `dizical-prod-161-20261111161743`）

## 未闭环项

- `X-Dsh-Build: v3.52` 响应头未取（需生产登录态）。镜像层证据已成立（构建日志含 `inflating: src/kid_app/templates/practice-dsh.html`，镜像 tag 与 deploy #162 绑定），但「模板字节内容」级的线上确认仍缺一条 authenticated curl。

