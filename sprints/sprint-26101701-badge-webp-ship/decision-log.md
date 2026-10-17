---
source: ai-agent
project: dizical
sprint: sprint-26101701-badge-webp-ship
updated: 2026-10-17
version: 1.0
---

# Sprint 26101701 决策记录

| 日期 | 决策 | 为什么 |
|---|---|---|
| 2026-10-17 | 把 WebP 编码实现放在 `src/kid_app/badge_webp.py`；`scripts/generate_badge_webp.py` 只保留 CLI 壳 | `.tcbignore` 整目录排除 `scripts/`；运行时模块必须随 `src/` 进入 CloudRun 镜像，避免再次出现容器内 FileNotFoundError |
| 2026-10-17 | 不改 `.tcbignore`，不迁移 `config.py` 的设计 demo shell 调用 | 修复线上 badge commit P0 的最小边界；demo 脚本是低危本地工具且与本次提交链无关 |
| 2026-10-17 | 不执行真实生产 badge commit | brief 指出 `grade_5_excellent` 与“二级考级优秀”疑似不一致；写生产三表前需 dad 决定业务 ID/等级 |
| 2026-10-17 | 坏图测试精确断言 `PIL.UnidentifiedImageError` | round-1 review 指出 `pytest.raises(Exception)` 可能掩盖无关错误；精确异常锁定非法图片字节的真实失败行为 |
| 2026-10-17 | GH API EOF / 临时 token-invalid 按网络抖动处理，重试 2–3 次；必要时用 `HTTPS_PROXY=http://127.0.0.1:7897` | dad 说明 token 仍有效；git push 走本地 gh credential helper，不与 API 请求共用网络路径 |
| 2026-10-17 | 部署源码取 `origin/main` 干净 worktree（`bd90527`），rsync 到 `.cloudrun-deploy/`，不传 `envParams` | practice checkout 有未评审内容，直接拿它的 `src/` 会把无关改动送上线；不传 env 避免覆盖远端 DATABASE_URL/COS_* |
| 2026-10-17 | 徽章 id 由 `grade_5_excellent` 改为 `grade_2_excellent` | 草稿 name/`cond_text` 都是「二级考级」，现有 `grade_1`..`grade_10` 对应 1..10 级；id 与业务语义必须一致，否则后续 calc 会挂错级别 |
| 2026-10-17 | 重复徽章保留 `grade_2_excellent`，删 `grade_5_excellent` | 页面「待确认」提交旧草稿产生第二条同名同图记录；id 语义正确的那条才是 canonical，另一条留三表会造成重复展示与统计污染 |
| 2026-10-17 | 去重时三表删除走 MCP `runStatement`，COS 对象走 `manageStorage delete`，草稿走 API DELETE | 生产写操作全部留审计；本地无 COS 凭据且不应读取，避免为删一个对象把密钥拉进上下文 |
| 2026-10-17 | 已合分支（`fix/badge-webp-import-from-pkg-261017`、`docs/badge-webp-closeout-261017`）与 4 个临时 worktree 在 dad 授权后清理 | 工作已进 `main`（`bd90527`），回滚靠 main 历史 + CloudRun #143；长期挂着的临时 worktree 会干扰后续会话的分支判断 |
