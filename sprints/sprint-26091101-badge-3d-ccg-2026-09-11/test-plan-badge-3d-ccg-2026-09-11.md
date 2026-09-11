---
id: 26091101-test-plan
type: test-plan
version: 1.0.0
date: 2026-09-11
status: 进行中
tags: [test-plan, dizical, badge, 3d, ccg]
---

# TEST-PLAN - 徽章集卡化 3D CCG 改造测试计划

## 1. 自动化测试 (`tests/test_badge_claim.py`)
- **Case 1: 迁移后未领取状态查询**
  - 设置某徽章 `achieved='Y', claimed_at=NULL`，调用 `GET /api/badge/unclaimed`，应返回该徽章且 `unclaimed_count >= 1`。
- **Case 2: 领取操作成功**
  - 调用 `POST /api/badge/claim`，入参 `{"badge_id": "xxx"}`，返回 200 且 `claimed_at` 具有有效时间戳。再次查询 `GET /api/badge/unclaimed` 该徽章消失。
- **Case 3: 幂等性防护**
  - 对已领取的徽章再次发送 `POST /api/badge/claim`，应返回 200 `{ "status": "ok", "already_claimed": true }`，不报 409 或 500。
- **Case 4: 审计日志验证**
  - 检查 `practice_audit_log` 是否存在一条 `method='badge_claim'` 的写入记录。
- **Case 5: 未解锁徽章不可领取**
  - 对 `achieved='N'` 的徽章尝试调用 claim，应拒绝并返回相应错误。

## 2. 前端与真机交互验收 (iPad mini + Mac)
- **Demo 把玩对比 (`/static/badge-ccg-demo.html`)**：
  - [ ] 方案一（纯 CSS 全息光影）在触控拖拽时流畅反光跟随，松手平滑回正。
  - [ ] 方案二（纯 CSS 3D 分层视差）在倾斜时呈现清晰的 Z 轴图层错落感。
  - [ ] 触屏拖拽卡面时，背景页面不发生滚动穿透（`touch-action: none` 生效）。
  - [ ] iPad mini 横屏（744px）无溢出，自适应左右排版。
- **全局拦截弹窗链路**：
  - [ ] 造一条未领取徽章测试数据，打开 `/prepare` 或 `/practice`，能够自动弹出全屏高光 3D 卡牌弹窗。
  - [ ] 点击“领取入库”，金色粒子雨爆发，卡牌缩小飞入左侧成就殿堂图标。
  - [ ] 弹窗关闭后，刷新页面不再重复弹出。
