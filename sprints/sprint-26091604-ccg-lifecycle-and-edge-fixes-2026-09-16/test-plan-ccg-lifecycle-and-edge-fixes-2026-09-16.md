# Test Plan: CCG 前端生命周期边角治理 (Sprint 26091604)

## 1. 自动化回归测试
- 全量 `pytest` 运行（768 项测试 100% 保持通过）。

## 2. 前端生命周期自动化断言 (Chrome Headless)
- 断言 1：全局 `resize` 监听器数量在挂载 44 张卡后恒为 1，不随卡片挂载递增。
- 断言 2：`achievements.html` 截断后，`DizicalCCG.cards.length` 减小，被删除的卡已成功从数组注销。
- 断言 3：`lostpointercapture` 模拟触发时，未引发重复 `springHome` 调用。
- 断言 4：`.is-frozen` 生效时，`--nx` 与 `--ny` 计算样式均为 `0`。
- 断言 5：Modal 连续换卡过程中，`document.body.classList.contains('is-frozen')` 持续为 `true`。
