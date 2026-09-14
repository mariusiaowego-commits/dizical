# test-plan · sprint-26091401 · F1 生产验收 4 项修复

## 1. 自动化测试

| 套件 | 用例数 | 结果 |
|------|--------|------|
| `tests/test_badge_story_short.py`（本 sprint 新增） | 19 | passed |
| 全量 `pytest --ignore=tests/config_ui_fixes` | 768 passed / 8 skipped | **0 failed / 0 error / 32.08s** |
| 基线对照（main `b96a945`） | 749 passed / 8 skipped | 768 = 749 + 19 ✅ |

关键用例：
- `test_seed_leaves_no_open_transaction` —— 播种后断言 `conn.in_transaction is False`，并**另开一个连接执行 DDL** 作硬证据（不依赖实现细节）。这是本轮锁泄漏 bug 的回归锁。
- `test_achievements_page_payload_includes_story_short` —— 曾暴露 `minip_api.py` 第 4 处载荷缺口。

子集复验（二分定位用）：`test_assign_draft + test_auth_web` 修前 7 passed / 75 errors → 修后 **82 passed**。

## 2. 独立闸门（浏览器实测，非自报）

复现台：`/tmp/ccgprobe/`（本地静态服 **8793**，headless Chrome CDP **9447**），同一页面用 `?fix=on|off` 切换 CSS，做消融对照。

| 探针 | 脚本 | fix=off | fix=on |
|------|------|---------|--------|
| 列表几何 + 3D 载体 | `probe_gate.py`（`.ccg-rotator`） | `0×0` / `NaN%` | `160×240` / `85%/20%` / `matrix3d(0.964…)` |
| modal 几何（3 视口） | `probe_modal.py` + `modal_harness.html` | 920 上限 | `1240×672` / 卡 `400×600`；iPad 横屏 `1092×652`；竖屏单列 `300×450`；**无横向溢出** |
| 卡背短文 | `probe_back.py` | 截断 | `line-clamp 4` 生效、15 字短文全显 |

**探针口径教训**：3D 倾斜必须量 `.ccg-rotator`（3D 载体），量 `.ccg-card-flipper`（只管翻面）会得到「没动画」的错结论 —— 初版 `probe_hover.py` 就踩了这个坑，已重写为 `probe_gate.py`。

## 3. 未覆盖 / 交 dad

- **视觉终验交 dad 真机**：数值探针证明几何/矩阵/几何尺寸正确，但不替代人眼对「震撼感」的判断。
- **生产路径未跑**：本 PR 合并 + deploy 前，生产仍是旧 CSS/旧 app.py；deploy 后用 MCP **只读**复核云端 `story_short` 行数（期望 46），为 0 再走 MCP 补种（留审计）。
- `tests/config_ui_fixes`（缺 `bs4`，2 个 collection error）按 dad 指示**未动**。
- `badges.html` 两处 JS 兜底 `no: … || '001'`（P1 残留）本 sprint 未收口，另案。
