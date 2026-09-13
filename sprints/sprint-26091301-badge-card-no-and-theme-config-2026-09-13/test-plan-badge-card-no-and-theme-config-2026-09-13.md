---
id: 26091301-test-plan
type: test-plan
version: 0.1.0
date: 2026-09-13
status: 进行中
tags: [test-plan, dizical, badge, card-no]
---

# TEST-PLAN — 徽章卡编号 + 主题设计期入口

## 1. 基线

- 全量命令：`pytest tests/ -q`（在 `/Users/mt16/dev/dizical`）
- 合并前基线：**732 passed / 8 skipped / 0 failed**（PR #323 修复后）
- 纪律：**跑全量，不跑子集**——上个 sprint「45 passed」的子集跑没暴露 27 红

## 2. B1 用例

| # | 用例 | 期望 |
|---|------|------|
| 1 | 空表 → 新建 3 张卡 | 编号 1 / 2 / 3，连续 |
| 2 | 已有 3 张 + 回填重跑 | 编号不变，零写入（幂等） |
| 3 | 手工插入 `card_no IS NULL` 的老行 → 回填 | 只补 NULL 行，已有编号不动 |
| 4 | 回填后改 `sort_order` / `sort_order_override` | 编号**不变** |
| 5 | 回填后调 `insert_achievement_row` 不带 card_no | 新号 = `MAX+1`，不重号 |
| 6 | `count(*) = count(distinct card_no)` | 相等（唯一） |
| 7 | `GET /api/badge/unclaimed` | 响应含 `card_no` |
| 8 | `GET /api/achievements` | 响应含 `card_no`，老字段不变 |
| 9 | 前端 `normalize()` 无 `card_no` | 显示 `—` 而非 `001` |

## 3. B2 用例

| # | 用例 | 期望 |
|---|------|------|
| 1 | config 写 `card_theme = 'pearl'` | 落库成功，读回一致 |
| 2 | 写非法主题名 | 被拒（白名单校验 8 套） |
| 3 | 已有卡的 `card_theme` 为空 | 读取仍走 `TYPE_THEME_MAP` 兜底，不报错 |

## 4. 回归重点

- 5 处测试自建表 SQL 与生产列同步（`conftest.py` + 4 个测试文件）
- `card_theme` / `card_stars` 迁移路径不得被 card_no 改动破坏
- `badge_write_tx` 事务语义（回滚不留半行）

## 5. 生产验收（dad 侧，眼验）

1. `/badges` 页与领取弹窗编号一致且非 `001`
2. 改一次 DB `sort_order` → 编号不变
3. 新走一次建卡流程 → 号 = 现有最大值 +1
