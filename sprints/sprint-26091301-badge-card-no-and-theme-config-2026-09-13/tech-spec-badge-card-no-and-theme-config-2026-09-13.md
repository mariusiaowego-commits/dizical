---
id: 26091301-tech-spec
type: tech-spec
version: 0.1.0
date: 2026-09-13
status: 进行中
tags: [tech-spec, dizical, badge, card-no, theme]
---

# TECH-SPEC — 徽章卡编号 + 主题设计期入口

## 1. 现状基线（实测，非推测）

| 项 | 事实 | 出处 |
|----|------|------|
| 卡面编号 | `no: d.no \|\| "001"` → 真实链路上永远是 `001` | `static/js/badge-ccg.js:537` |
| 领取弹窗数据源 | `/api/badge/unclaimed` 返回无编号字段 | `routes/badge_claim.py` |
| DB | `achievements` 46 行，主键 TEXT，无编号列 | 线上 `/api/achievements` 46 行 |
| 排序 | `sort_order` 36 行为 0，另有 `sort_order_override` | `badge_db.py` |
| 星级 | `card_stars` 列已上线（上一 sprint Q3） | `badge_db.py:120` |
| 迁移模式 | `ensure_card_theme_column` / `ensure_card_stars_column` 双后端幂等 | `badge_db.py:42-138` |
| 启动 hook | `@app.on_event("startup")` 已调两个 ensure | `app.py:35-53` |
| 双后端 SQL | 必须走 `src/db_adapter.execute()`（PR #287） | `src/db_adapter.py` |

## 2. DDL（幂等）

```sql
ALTER TABLE achievements ADD COLUMN card_no INTEGER NULL;
-- SQLite 无 IF NOT EXISTS：先 PRAGMA table_info / SHOW COLUMNS 判存在
-- MySQL 侧不建唯一索引（云 DB 走信息架构查询判断），本地幂等函数负责防重
```

- 可空：不设 NOT NULL，避免迁移瞬间炸写入路径
- 唯一性由回填逻辑 + 写入路径 `MAX+1` 保证；校验用 `count(*) = count(distinct card_no)`

## 3. 回填规则（M1）

1. 候选集：`card_no IS NULL` 的行（**已有编号的行绝不改动** ⇒ 可重复运行）
2. 排序：`category` → `sort_order`（0 的用 `created_at`）→ `id`
3. 起始值：`COALESCE(MAX(card_no), 0) + 1`
4. 结果：现有 46 张连续编号；dad 若要手排，只改这一次回填顺序

## 4. 写入路径

- `badge_db.py` 新增 `fetch_max_card_no()`
- `insert_achievement_row` 增加 `card_no` 列：调用方给值则用，否则 `MAX+1`
- 与 INSERT 同一事务（`badge_write_tx`），避免并发跳号
- draft JSON 契约加**可选**字段 `card_no`（不填走 `MAX+1`），`schema_version` 不升版

## 5. 展示（三处一致）

| 位置 | 改动 |
|------|------|
| `badge-ccg.js normalize()` | `no` 取 `d.card_no` → `No.%03d`；无值显示 `—` |
| 卡面日期 | `achieved_at` `YYYY-MM-DD` → `2026年6月16日`（纯前端） |
| `routes/badge_claim.py` | `unclaimed` 返回体加可选 `card_no` |
| `routes/minip_api.py` | `/api/achievements` 返回体加可选 `card_no` |

## 6. B2 主题设计期入口

- 定位：**设计期**改主题（config），不做用户端选择器
- 落点：config 页新增「卡片主题」下拉，8 套主题（深 5：azure / bamboo / coral / imperial / frost；淡 3：pearl / mint / sakura）
- 写入：`achievements.card_theme`（列已存在，只做写入口）
- 不改：`badge_theme.py` 的 `TYPE_THEME_MAP` 兜底逻辑（无值仍走 type 映射）

## 7. 不做（本轮）

- 盲盒主题编号、卡面视觉、`sort_order` 重构、小程序改代码、B3/B4 定档
