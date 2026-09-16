# TEST-PLAN · CCG 移动端 3D 动效零卡顿治理与 WebP 缩略图分流管线 (Sprint 26091603)

## 1. 测试策略与门禁

本次测试包含三层验证：
1. **自动化回归测试**：768 pytest 全量通过，确保后端路由与数据契约 0 破坏；
2. **多模态资产审计**：44 张生成的 WebP 图片 Alpha 透明通道肉眼抽检；
3. **渲染性能与交互验收**：本地 8765 端口真机与无头浏览器性能指标对比。

## 2. 核心测试用例

| # | 测试模块 | 测试操作与输入 | 预期结果 |
|---|---|---|---|
| TC-01 | 全量后端回归 | 运行 `pytest -q --ignore=tests/config_ui_fixes` | 768 passed, 0 failed |
| TC-02 | WebP 资产衍生完整性 | 运行 `python3 scripts/generate_badge_webp.py` | 44 张 PNG 成功衍生对应 44 张 thumbs 与 44 张 full WebP |
| TC-03 | WebP 透明度与画质 | AGY 视力抽检 `eagle_spread_wings.webp`, `assign_pal_v2.webp` 等 | 背景纯透明无白边噪点，金色掐丝边缘清晰锐利 |
| TC-04 | 资产体积压缩比 | `du -sh` 统计 thumbs 总包与单图体积 | thumbs 单张在 15-30KB，44 张总和在 1.2MB 左右，比原 PNG 压缩 95%+ |
| TC-05 | 弹窗背景冻结 | 打开任意卡片 Modal | 背景网格所有卡片立即停止 tick，无 3D 旋转计算，全屏 blur 流畅不掉帧 |
| TC-06 | 弹窗关闭解冻 | 关闭 Modal 返回列表 | 背景卡恢复正常状态，DOM 样式无残留 |
| TC-07 | 触屏列表静止 | 模拟 touch / iPad 触屏环境访问 | 列表态卡片静止无自动微倾（idle drift），滑动丝滑维持 60fps |
| TC-08 | 触摸跟随响应 | 在 Modal 中触摸拖动卡牌 | 旋转倾角即时跟随，视觉无 500ms 拖手延迟，松手平滑回弹 |
| TC-09 | 列表缩略图加载 | 查看网络请求面板 | 列表态卡片请求 `/thumbs/*.webp`，未产生 1024px PNG 请求；进入 Modal 才按需请求对应高清图 |
