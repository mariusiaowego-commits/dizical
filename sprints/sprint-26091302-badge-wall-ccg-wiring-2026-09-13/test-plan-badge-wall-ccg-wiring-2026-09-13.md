---
id: 26091302-test-plan
type: test-plan
version: 0.1.0
date: 2026-09-13
status: 进行中
tags: [test-plan, dizical, badge, ccg, wiring]
---

# TEST-PLAN — B6 图鉴接线

## 验收标准（可判定）
1. `/achievements`（我的成就）与 `/badges`（成就殿堂）两页，**列表每张卡是 CCG 卡面**，且列表内**无 3D 交互**（鼠标移上去不 tilt、不出现跟随光）。
2. 点开任意一张卡 → **详情弹窗是 CCG 双栏**（左卡右文，字段齐全），弹窗内的卡**可全量交互**（tilt / holo / 翻面）。
3. 未解锁（locked）卡：列表与弹窗均表现为灰化 + 锁定标记，**不存在灰度 PNG 资源依赖**。
4. 页面外壳与改动前一致：页头标题栏、筛选 tab、底部导航、整页背景、网格与统计数字无视觉变化。
5. 领取徽章弹窗（`_badge_claim_modal.html`）行为与改动前**完全一致**（默认参数路径未变）。

## agent 侧证据（必须贴原始输出）
| 项 | 命令 | 期望 |
|---|------|------|
| JS 语法 | `node --check src/kid_app/static/js/badge-ccg.js` | exit 0 |
| 模板解析 | `.venv/bin/python` TestClient GET 两页 | 200 |
| 接线存在 | `grep -c ccg` 两模板 | 非 0 |
| 旧弹窗已清 | `grep -n 'id="modal-img"'` 两模板 | 无输出 |
| 契约默认路径 | 领取弹窗相关测试 | 不回归 |
| 全量回归 | `.venv/bin/python -m pytest tests/ -q` | **732 passed / 8 skipped / 0 failed**（main 基线） |
| 性能契约 | 列表 mount 调用点带 `static` 断言 | 列表无 rAF / 无 pointer 绑定 |

## 数值探针（agent 可做）
- 列表态：CDP 下对列表卡 `getComputedStyle` 检查 `is-static` class 存在；监听 5s 内 `requestAnimationFrame` 调用次数 ≈ 0（列表页）
- 弹窗态：打开后同探针，rAF 有调用；`transform` 随 pointer 变化
- locked：`getComputedStyle(filter)` 含 `grayscale`

## 视觉验收（归 dad，agent 不自证）
- Mac Safari + iPad mini 竖屏/横屏 各看一遍：列表静止观感、点开交互手感、locked 灰化程度
- 环境：合并 B1+B2+B6 的测试分支（本地 SQLite 副本），端口 8766

## 回归清单
- [ ] 领取徽章弹窗（有未领取徽章时自动弹）不受影响
- [ ] 筛选 tab / 统计数字 / 「显示全部 →」
- [ ] 我的成就 与 成就殿堂 两页互相跳转正常
- [ ] 移动端（iPhone Safari 440px）不横向溢出
- [ ] `demo-archive/v1.5.0/` 未被改动（`git status` 无变化）
