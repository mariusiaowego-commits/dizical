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
