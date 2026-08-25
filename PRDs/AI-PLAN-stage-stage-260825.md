# Sprint PLAN — stage 跟随 assignment，课程取消也能建 stage 承接练习

> dad 拍板方向（2026-08-25）：stage 跟随 assignment 生成，assignment 两种来源（老师上课布置 / 家长自己布置），课程取消（cancelled）也建 assignment → stage 自然生成，其它都不用改。
> 本 PLAN 是执行设计，先拍板再动代码。

## Goal

修复 `/report/stage-print` 报告页 stage 下拉停留在 Stage 18（08-16 后练习无 stage 承接）的问题，并让「课程取消但本周仍练习」的场景有正确 stage 承接。

**验收标准：**
1. 08-16 课（attended）产生 Stage 19，范围 08-16 ~ 下一节课日（08-22 或按新语义）
2. 08-22/08-29 若取消但有作业/练习 → 也有对应 stage（连续编号），list_stages 正常显示
3. 云端 stage 下拉看到 Stage 19+；练习数据（daily_practices）不丢失、正确归到对应 stage
4. 代码防复发：weekly_assignments 不再重复行、stage_order 不会因课程状态变化而遗漏回填

## Blocking Questions

- **Q1: 取消课（cancelled）也纳入 stage_order 连续编号吗？** — **推荐 A**（because dad 已拍板"跟正常课一样连续编号"）
  - A. 是：lessons 有课（attended/scheduled/cancelled 任一）就编号
  - B. 否：只有 attended 编号（会重复当前 bug）
- **Q2: 非 attended 课（scheduled/cancelled 但有作业）要出现在 stage 下拉吗？** — **推荐 A**
  - A. 要：取消/未上但有 dad 布置作业 → 显示（否则练习无承接）
  - B. 不要：只有 attended 课出 stage
- **Q3: stage_end 语义保持「下一节 scheduled 课日期」吗？** — **推荐 A**（dad 已拍板）
  - A. 保持：用下一节 scheduled 课日（含取消的）
  - B. 改固定 7 天
- **Q4: 本次要不要顺手把 08-22 标 cancelled + 给 08-22 建作业？** — **推荐 A**
  - A. 要：一次到位，让 08-22 之后到今天练习有 stage
  - B. 不要：只修代码机制，数据 prob dad 自己录

## Assumptions

1. **Data**: weekly_assignments 一张表存所有 stage（师授/家长补同构），lesson_date 唯一（已建 UNIQUE 索引）
2. **Data**: lessons 表已有 CANCELLED 状态枚举 + `send_lesson_cancelled` 通知，取消课程流程存在
3. **Data**: 08-22 是 scheduled（未决），08-29 是 scheduled；08-16 已 attended
4. **Failure**: stage_order 计算失败时写 NULL（跟现在一致），但加了唯一索引后不会再产生重复行
5. **Boundaries**: 只改 weekly_assignments 写入/stage 生成逻辑，不动 list_stages 的过滤（保留 NULL/0 过滤是刻意设计）
6. **Environment**: 双后端（SQLite database.py + MySQL database_mysql.py）同步改；云端 prod 数据已修一半（合并+建索引 done, stage_order 回填用到新语义）
7. **Scope**: 不改业务/成就/盲盒逻辑（agy 发现的那些影响面本轮不做，另开 sprint）

## Plan

### 改动点（核心 2 处写逻辑 + 测试）

> **agY review 修正**：stage_order 算法不能用「lessons 全表序号」——历史有 3 节 cancelled 无作业课（04-04/06-06/06-27）会插队占号，让历史 Stage 1-18 整体右移。改为用 **weekly_assignments 自身连续序列** 编号，历史编号不漂移（已本地验证：17 个历史 stage 用新算法全绿 OK）。

1. **`src/database.py` SQLite `save_weekly_assignment` (行 ~729)**
   - stage_order 算法改为：统计 `weekly_assignments` 中 `lesson_date >= '2026-03-14' AND lesson_date < 当前课日` 的 DISTINCT lesson_date 数 + 1
   - 即「stage_order = 该课之前已录作业的周数 + 1」
   - 只要某课（attended/scheduled/cancelled 任一）录了 assignment → 拿到下一个连续编号；没录作业的课不占号 → 历史编号不漂移
   - `get_weekly_assignments_in_range` / `list_stages` 不动

2. **`src/database_mysql.py` MySQL `save_weekly_assignment` (行 ~455)**
   - 同步改 stage_order 算法（对齐 SQLite 的 COUNT + 1 语义）
   - `ON DUPLICATE KEY UPDATE` 加回 stage_order（已做，补完）

3. **`schema_mysql.sql` + SQLite 迁移**
   - MySQL 加 `UNIQUE(lesson_date)`（已加）
   - SQLite 已有 unique，无需

4. **测试**
   - 新增 `tests/test_weekly_assignment_stage_order.py`：
     - 历史 17 个 stage 用新算法编号不变（不漂移）
     - cancelled 课录作业 → 分配到下一个连续 stage_order
     - scheduled 提前录作业 → 立即编号
   - `tests/test_list_stages_filter.py` 保持：确认有作业的 stage 正常显示

5. **数据修复（MCP prod）**
   - 08-22 标 cancelled
   - **给 08-22 录入 assignment（生成 Stage 20）**——agy 指出：若不录，今天 08-25 是 Stage 19 第 9 天，盲盒打卡（MAX(stage_order) 定位）仍失效；录了 Stage 20 盲盒立即恢复
   - 08-29 scheduled 待 dad 确认是否需要提前录

### 顺序
先代码 → 本地 SQLite 测试（验证历史编号不漂移）→ 数据修复 prod → 提 PR

**Alternative rejected**: 
- A1 不动数据只改查询（让 list_stages 显示 stage_order=NULL 的 stage）——rejected because 让 stage_order 失去排序/连续性意义，每次特判易漏
- A2 用 lessons 全表序号排 stage_order——rejected because 历史 cancelled 无作业课插队占号，破坏 Stage 1-18 编号（agy 致命盲点）

---

## agy review 整合记录

| # | agy 提出 | 采纳 | PLAN 改在哪 |
|---|---|---|---|
| 1 | ⚠️致命: lessons 全表序号会破坏历史 Stage 1-18 | ✅ | 改用 weekly_assignments 自身序列 + 1 (改动点 1) |
| 2 | scheduled 课提前录作业即编号, 不会空 stage (list_stages 数据源是 weekly_assignments) | ✅ | 改动点 1 算法说明 |
| 3 | 必须录 08-22 生成 Stage 20, 否则盲盒打卡(MAX stage_order 今天超期) 仍失效 | ✅ | 数据修复 (改动点 5) |
| 4 | achievement/盲盒/海报下游无需改代码, 只要 stage_order 单调递增 | ✅ | 不动 (已确认) |

**本地验证**：17 个历史 stage 用「COUNT(较早日期的 assignment)+1」编号全绿 OK，无漂移。