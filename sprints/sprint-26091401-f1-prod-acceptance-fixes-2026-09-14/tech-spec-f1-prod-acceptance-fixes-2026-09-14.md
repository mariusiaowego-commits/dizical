# tech-spec · sprint-26091401 · F1 生产验收 4 项修复

## 1. 几何：百分比自引用 0px

```css
/* 修前 */
.ccg-stage { /* --card-w: min(160px, 100%) 由 .ccg-grid-cell .ccg-stage 覆盖 */ }
/* .ccg-stage-mount 在 CSS 里没有任何规则 */

/* 修后 */
.ccg-stage-mount { width: 100%; display: flex; justify-content: center; }
.ccg-grid-cell .ccg-stage,
.badge-grid .ccg-stage,
.b-card .ccg-stage,
.badge-card .ccg-stage { --card-w: min(160px, 44vw); }
```

机制：`--card-w` 参与 `width: var(--card-w)` 与 `height: calc(var(--card-w) * 1.5)`。父容器没有确定宽度时，`100%` 对自身求解 ⇒ 0px ⇒ 宽高同时塌成 0，只剩 `.b-card` 的 padding（337×36 的「胶囊」）。改用 `vw` 绝对长度 + 给 mount 明确宽度，两页列表卡稳定 160×240。

`.b-card` / `.badge-card` 从「依赖 `.ccg-grid-cell` 包裹类」改为**显式列在选择器里**，避免模板换壳时再次踩空。

## 2. `story_short` 数据链路

```
achievements.story_short VARCHAR(255) NULL
  ↑ database.py      幂等 ALTER（与 card_no / card_theme 同模式）
  ↑ badge_db.ensure_story_short_column()   SQLite + MySQL 双后端幂等；_invalidate_columns_cache()
  ↑ badge_db.seed_story_short()            读 badge_story_short.json（46 条），幂等 UPDATE，**无条件 commit**
  ↓ app._ach_optional_cols(conn, *names)   SELECT 列按表实际列动态拼（缺列不引用 ⇒ 迁移未完也不 500）
  ↓ 载荷四处：app.py ×2 页面/接口 + app._build_milestone_card() + routes/minip_api.py 独立 API
  ↓ 前端：achievements.html / badges.html 卡背；badge-ccg.js normalize storyShort
  ↓ 回落链：d.story_short || d.storyShort || d.story
```

- `_ach_optional_cols()` 顺带修掉老 bug：`has_card_no` 判的列没进 SELECT ⇒ 恒 False ⇒ 图鉴编号全显「—」。
- `minip_api.py` 是**第 4 处独立载荷**（key 用 `typ`/`group` 而非页面 payload），由新测试 `test_achievements_page_payload_includes_story_short` 暴露。

## 3. 锁泄漏（全量回归暴露的真 bug）

```python
# 修前 —— 0 行匹配时不 commit
if changed:
    conn.commit()

# 修后 —— 无条件 commit
conn.commit()   # 46 条 UPDATE 即使 0 行匹配也已隐式 BEGIN，不提交就留着 RESERVED 锁
```

后果链：启动播种（0 行变更）⇒ 隐式写事务不结束 ⇒ SQLite RESERVED 锁常驻 ⇒ 同进程/同库其它连接 `CREATE TABLE` 立即 `database is locked`。生产等价害处（MySQL 事务不释放）。

## 4. modal 几何

| 位置 | 修前 | 修后 |
|------|------|------|
| dialog 宽 | `min(920px, 100%)` | `min(1240px, 96vw)` |
| dialog 高 | `92dvh` | `94dvh` |
| 横屏 3D 卡区 | `min(240px, 46vh)` | `min(400px, 52vh)` |
| 右细节列 | `flex: 1 1 42%` | `flex: 1 1 38%` |

左右结构不变；窄屏（≤ 某断点）仍回落单列竖排。

## 5. 卡背排版

字号/间距从固定 px 改为 `calc(var(--card-w) * k)` 配 `clamp()` 上下限：列表 160px 卡自动用小字，modal 400px 卡自动放大（标题 26px）。`.ccg-back-val` 列表态 `-webkit-line-clamp: 4`，`.ccg-claim-overlay` 内 `unset`（modal 卡背短文全显）。

## 6. 兼容性

- 新增列可空、幂等迁移 ⇒ 老部署/回滚版本读到多余列无影响。
- `story_short` 为空的旧数据前端自动回落长 `description` ⇒ 不会出现空卡背。
