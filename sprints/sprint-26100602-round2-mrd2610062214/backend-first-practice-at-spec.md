# 后端方案 · `daily_practices.first_practice_at`（D5/D6 总时长跨度缺的字段）

作者：hermes（架构/后端） · 日期：2026-10-06 · 状态：**待 dad 批准后落 `src/`**（本轮只改 demo，故先只给方案 + patch 文本）

## 1 现象 → 根因

**现象**：D5「今日练习记录」卡片与 D6「今日时长卡」要表现的是**一天自然跨度**（例：19:10 开始 → 20:07 结束，中间 9 段练习 + 8 段休息），
所以需要「**当天第一次开始练习的时刻**」+ 每次的起止。

**根因**：`daily_practices` 只有单值 `practice_at`，语义是「该日**首次创建**记录时的练习时间」（AGENTS.md 明确：UPDATE 永不覆盖）。
它既不是「当天最早开始」，也无法表达多段的时间轴 —— 前端要画跨度只能靠猜。

## 2 三个方案对比

| 方案 | 做法 | 优点 | 缺点 | 结论 |
|:--|:--|:--|:--|:--|
| **A 加列** | `daily_practices.first_practice_at`（当天最早的练习时刻） | 可索引、读写都便宜、语义直白 | 需要 DDL + 回填 | ✅ **推荐** |
| B 读时聚合 | 读接口 `MIN(behavior_log[].enter_time)` | 零 DDL | 每次读都要 JSON 解析，无索引；旧行 `behavior_log` 可能为空 | 作为 A 的**回填来源** |
| C 审计表聚合 | 读 `practice_audit_log` 首条 | 已有表 | 审计表是写操作台账（含补录/删除），不等于练习语义 | ❌ |

**采用 A，并用 B 做历史回填**（`behavior_log` 里第一条 `enter_time` 比 `practice_at` 更准）。

## 3 语义（写清楚，避免以后混）

- `first_practice_at` = **当天所有练习记录里最早的练习时刻**（CST ISO `'YYYY-MM-DD HH:MM:SS[.fff]'`，不带 Z 后缀 —— 与 `practice_at` 同格式，同 AGENTS.md 的 practice 写入路径约定）。
- 与 `practice_at` 的关系：`practice_at` 保留「首次写入时间」语义不变（**不动已有行为**）；`first_practice_at` 是**单调取早**：
  - 新建行 → = 传入的 `practice_at`
  - 更新行 → `MIN(已有 first_practice_at, 本次 practice_at)`（补录一个更早的时间，要能把它拉早）
- `created_at` 仍是 DB 写入时间（UTC），不参与。

## 4 DDL（两个后端都要，写法沿用项目既有风格）

### 4.1 SQLite —— `src/database.py`（`daily_practices` 的 ensure-schema 块，与 `practice_at` 那段并列）

```python
# 2026-10-06: 当天最早练习时刻（D5/D6 总时长跨度用）。AGENTS.md practice 写入路径约定同 practice_at。
cursor.execute("SELECT name FROM pragma_table_info('daily_practices') WHERE name='first_practice_at'")
if not cursor.fetchone():
    cursor.execute("ALTER TABLE daily_practices ADD COLUMN first_practice_at DATETIME")
```
（与 line 360–372 的 `ALTER TABLE daily_practices ADD COLUMN ...` 同一块，幂等：列已存在则跳过。）

### 4.2 MySQL —— `schema_mysql.sql` + `.cloudrun-deploy/src/database_mysql.py`

```sql
ALTER TABLE daily_practices ADD COLUMN first_practice_at DATETIME NULL COMMENT '当天最早的练习时刻(CST)';
```
（MySQL 侧同样用「查 information_schema → 缺才加」的幂等写法，与现有 ALTER 一致。）

## 5 写路径 patch

`src/database.py::save_daily_practice`（约 979 行起；`.cloudrun-deploy/src/database_mysql.py` 约 666 行起同改）：

```python
# INSERT 路径（新行）
INSERT INTO daily_practices (date, items, total_minutes, total_seconds, log, practiced, practice_at, first_practice_at)
VALUES (?,?,?,?,?,?,?,?)
# 参数尾部补 practice_at 同一值

# UPDATE 路径（已有行）—— practice_at 仍不覆盖；first_practice_at 单调取早
UPDATE daily_practices
   SET items=?, total_minutes=?, total_seconds=?, log=?, practiced=?,
       first_practice_at = CASE
         WHEN ? IS NULL THEN first_practice_at
         WHEN first_practice_at IS NULL THEN ?
         WHEN ? < first_practice_at THEN ?
         ELSE first_practice_at END
 WHERE date=?
```

## 6 读路径

- 记录读接口（`/config/api/records/*` 与 kid-app 用的读接口）**新增两个字段**（不删不改老字段，向后兼容 = 🟡 部分兼容，按 `API-CHANGELOG.md` 登记）：
  - `first_practice_at`：当天最早练习时刻（无则回退 `practice_at`）
  - `span_seconds`：当天跨度秒数 = `max(段落结束) - min(段落开始)`（由 items/behavior_log 算，前端只展示）
- 老客户端不读新字段不受影响（✅ 不破坏）。

## 7 回填（历史行）

一次性脚本 `scripts/backfill_first_practice_at_2609xx.py`（**由 agent 执行并留审计**，符合「云 DB 走 MCP / 本地走脚本 + 审计」约束）：

```sql
-- 优先用 behavior_log 首条 enter_time；没有就退回 practice_at
UPDATE daily_practices
   SET first_practice_at = COALESCE(
         json_extract(json_extract(behavior_log, '$[0]'), '$.enter_time'),
         practice_at)
 WHERE first_practice_at IS NULL;
```
- 只填 `IS NULL` 的行，**不覆盖**已有值；跑完打印影响行数 + 抽样 10 行前后对比，写 `practice_audit_log`（channel=`backfill`）。

## 8 测试计划（pytest，落在 `tests/`）

| # | 用例 | 断言 |
|:--|:--|:--|
| 1 | 新建记录的当天行 | `first_practice_at` = 传入 `practice_at` |
| 2 | 同日第二次写入（更晚） | `first_practice_at` **不变**（仍是更早那次） |
| 3 | 同日补录一个更早的时刻 | `first_practice_at` **被拉早**（单调取早） |
| 4 | 老行（无该列值）+ 回填脚本 | 值 = `behavior_log` 首条 `enter_time`；空则 = `practice_at` |
| 5 | 幂等 DDL | 连跑两次 ensure-schema 不报错、列只有一个 |
| 6 | `span_seconds` 计算 | 9 段样本 → 跨度 = 末段结束 − 首段开始 |

## 9 落地顺序（等 dad ack）

1. 我改 `src/database.py` + `schema_mysql.sql` + `.cloudrun-deploy/src/database_mysql.py`（幂等 DDL）
2. 我改 `save_daily_practice` 两处（写路径）
3. 我加 6 条 pytest 并跑全量（确认无回归）
4. 回填脚本 → 先本地库 dry-run 打印，dad 确认后执行生产
5. `API-CHANGELOG.md` 登记（🟡 部分兼容）+ CloudRun 部署
6. 前端（D5/D6）接真字段替换样本数据

> **为什么要 dad ack**：本轮口径是「只改 demo」，而这份方案会动 `src/` 与生产库 schema —— 按规矩「改已有代码先列 diff 等 ack」。
