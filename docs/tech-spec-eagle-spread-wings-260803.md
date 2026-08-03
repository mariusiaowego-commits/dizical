# Sprint 05 — 雄鹰展翅 Tech Spec (260803)

> **AI 标注:** 本 tech spec 由 coder agent 生成, 镜像到 Obsidian `tqob/05-Coding/project-dizical/sprints/sprint-05-eagle-spread-wings-2026-08-03/tech-spec-eagle-spread-wings-2026-08-03.md`.

## DB INSERT

```sql
INSERT INTO achievements (id, name, type, category, stat_logic, description,
                          display_format, threshold, unlocked_template, placeholder,
                          sort_order, seasonal_type, cond_text, unlock_strategy,
                          achieved_at_override, display_on_achievements, created_at)
VALUES ('eagle_spread_wings', '雄鹰展翅', '突破', 'milestone',
        'never_unlock_(achieved_at_override)',
        '草原上, 哈萨克女孩萨丽哈学雄鹰展翅飞, 不做温室一枝花. 你把整首《萨丽哈最听毛主席的话》背出来 — 这是你的羽翼. 雪山再高, 雄鹰也能飞过.\n\n背歌时忘了词没关系, 再来一遍就是. 一遍一遍练到顺口的耐心, 都是翅膀.',
        'achieved_flag', NULL, NULL,
        'an elegant chibi girl in traditional Kazakh attire holding a soaring golden eagle above her head with both arms, the eagle\'s wings spread wide forming a triumphant halo, with a bamboo dizi flute in one hand and a Kazakh traditional ornamental ribbon trailing behind, set against a bright sunflower field under a golden sunrise',
        37, 'monthly',
        '把《萨丽哈》整首背出来, 你的笛声像草原的雄鹰一样响亮啦!',
        'immediate', '2026-08-03', 1, CURRENT_TIMESTAMP);

INSERT INTO achievement_badges (achievement_id, url, is_locked, version, is_current)
VALUES ('eagle_spread_wings', '/static/badges/eagle_spread_wings.png', 0, 1, 1);
```

## PNG

- 源: `data/lib/badge_data/.tmp/eagle_spread_wings_v1.png`
- 落盘到: `src/kid_app/static/badges/eagle_spread_wings.png`
- 处理: PIL 阈值 245 去 RGB>245 像素 + rembg U2-Net 兜底 (用 /usr/local/bin/python3)
- 验证: RGBA, 47% 透明, 4 角 alpha=0

## 服务重启

`./scripts/stop-prod.sh && ./scripts/start-prod.sh` (AGENTS 红区: V1 era badge workflow 改动后必须重启)

## 计算路径

`sprint 04 PR #218` 已修复 calc 流程 (app.py:badges_page line 569-576):

```python
is_commemorative = (ach.get("unlock_strategy") == "immediate" or ach.get("achieved_at_override"))
if is_commemorative:
    cur.execute("SELECT achieved, achieved_at FROM achievement_stats WHERE achievement_id=?", (aid,))
    row = cur.fetchone()
    override_at = ach.get("achieved_at_override")
    if override_at:
        res = CalcResult(True, 1, None, override_at, f"考出时间: {override_at}")
    elif row and row[0] == 'Y':
        res = CalcResult(True, 1, None, row[1] or None, "立即解锁")
```

`eagle_spread_wings` 走 `override_at` 分支, 返 `CalcResult(True, 1, None, '2026-08-03', '考出时间: 2026-08-03')`.

## 不需要新 calc 分支

`_calc_milestone` 不知道 `immediate`, 但 `badges_page` 在循环外 layer 了一层 `is_commemorative` 判断, 直接 override `res`. 这是设计意图, sprint 04 验证过.

## 数据迁移

db 改动**不入 commit** (db 不在 git 里). commit 只包含 1 个 PNG 文件. db 改动在生产环境由运维工具或手动执行.

## 风险

- 无. immediate 模式已经 sprint 04 验证过, db INSERT 是 INSERT-only 不会破坏现有数据