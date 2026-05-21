# Dizical Badge 工作流

> 添加新 badge 的完整流程
> 更新：2026-05-20

---

## Badge 类型

| 类型 | 计算方式 | 写入 achievement_stats | 示例 |
|------|----------|----------------------|------|
| `milestone` | 读 achievement_stats 字段 | ✅ 达成时写入 | streak_7, total_300, top1 |
| `seasonal` | 实时计算，不写 stats | ❌ | total_60, week_champ, full_month |

---

## 步骤概览

```
1. 设计阶段  →  2. 生图  →  3. 去背处理  →  4. 入库  →  5. 加计算逻辑  →  6. 验证
```

---

## 步骤 1：设计

确定：
- **badge id**：英文+下划线，如 `streak_7`、`total_300`
- **名称**：中文名
- **category**：`milestone` 还是 `seasonal`（数据类型，决定计算方式）
- **type（分类标签）**：突破 / 巅峰 / 段位 / 执着 / 晋级 / 神秘（决定前端 b-tag 颜色）
- **解锁条件**：一句话描述
- **计算逻辑**：基于哪些数据、阈值多少

> ⚠️ **字段含义**：`type` = 前端展示的中文标签，`category` = 数据类型。别混淆！
> ❌ 错误：`type='achievement'`（这是 SQL 关键字，不是有效标签）
> ✅ 正确：`type='突破'`，`category='seasonal'`

---

## 步骤 2：生成图片

用统一 prompt 模板（FAL Nous Portal / image_generate）：

```
An emoji-adjacent 3D enamel pin of [PLACEHOLDER]. Polished gold metal borders enclose flat, glossy enamel fills. The design is a centered, iconic illustration with a smooth, friendly silhouette and vibrant colors, matching a child's achievement badge style. Studio lighting reflects off the reflective enamel and raised gold metal edges. Orthographic, straight-on view, high quality, isolated on a clean white background.
```

**[PLACEHOLDER]** 替换为图片描述（英文，越具体越好）。

参考 `docs/badge-prompts.md` 已有的 placeholder 写法。

---

## 步骤 3：去白底处理

FAL 输出的 PNG 有白色背景，用 PIL 脚本去背：

```python
from PIL import Image
import os

src = "/Users/mt16/dev/dizical/src/kid_app/static/badges/<id>.png"
im = Image.open(src).convert("RGBA")
pixels = im.load()
for y in range(im.height):
    for x in range(im.width):
        r, g, b, a = pixels[x, y]
        if r > 220 and g > 220 and b > 220 and a > 200:
            pixels[x, y] = (r, g, b, 0)  # 纯白 → 透明
        # 抗锯齿 near-white + 低饱和 → 透明
        if r > 200 and g > 200 and b > 200:
            if max(r, g, b) - min(r, g, b) < 30:  # 低饱和度
                pixels[x, y] = (r, g, b, 0)

im.save(src)
```

文件路径：**`/Users/mt16/dev/dizical/src/kid_app/static/badges/<id>.png`**

同时追加记录到 `/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/00-Artifacts/image-gen.md`：
```markdown
## [badge_id] - 描述
- CDN URL: https://...
- 本地路径: /Users/mt16/dev/dizical/src/kid_app/static/badges/<id>.png
- 生成描述: PLACEHOLDER 内容
```

---

## 步骤 4：入库

### 4.1 achievements 表

```sql
INSERT INTO achievements
  (id, name, type, category, stat_logic, description,
   display_format, threshold, unlocked_template, placeholder,
   locked_template, sort_order)
VALUES
  ('<id>', '<名称>', '<分类标签>', '<milestone|seasonal>',
   --          ↑ 必须填中文标签（突破/巅峰/段位/执着/晋级/神秘）
   --          ❌ 不要填 'achievement' / 'milestone' / 'seasonal'
   '<简短计算逻辑描述>',
   '<一句话描述>',
   '<显示格式模板>',
   <阈值数字>,
   'An emoji-adjacent 3D enamel pin of [PLACEHOLDER]. ...',
   '<placeholder 英文描述>',
   'An emoji-adjacent 3D enamel pin of a child figure silhouette...',
   <sort_order>);
```

### 4.2 achievement_stats 表（仅 milestone）

```sql
INSERT INTO achievement_stats
  (achievement_id, achieved, achieved_at, raw_stats, computed_value)
VALUES
  ('<id>', 'N', NULL, '{}', NULL);
```

seasonal 类型不写入 achievement_stats。

### 4.3 achievement_badges 表

```sql
-- 已解锁版
INSERT INTO achievement_badges
  (achievement_id, url, is_locked, version, is_current)
VALUES
  ('<id>', '/static/badges/<id>.png', 0, 1, 1);

-- 锁定版（仅 milestone）
INSERT INTO achievement_badges
  (achievement_id, url, is_locked, version, is_current)
VALUES
  ('<id>', '/static/badges/<id>.png', 1, 1, 1);
```

---

## 步骤 5：加计算逻辑

编辑 `src/achievement_definitions.py`：

### milestone 类型 → `_calc_milestone()`

```python
if aid == "<id>":
    return CalcResult(
        <条件>,
        <computed_value>,
        <extra>,
        achieved_at if <条件> else None,
        "<显示条件文案>")
```

### seasonal 类型 → `_calc_seasonal()`

```python
if aid == "<id>":
    # 实时计算逻辑
    achieved = <实时条件>
    return CalcResult(achieved, <computed_value>, <extra>, None, "<条件文案>")
```

然后在 `calc_all()` 的循环里确认 category 分支走向正确。

---

## 步骤 6：验证

```bash
# 1. 确认表数据
sqlite3 /Users/mt16/dev/dizical/data/dizi.db \
  "SELECT id, name, category FROM achievements WHERE id='<id>'"

# 2. 确认计算逻辑（PYTHONPATH=src python3 -c）
python3 -c "
import sys; sys.path.insert(0, 'src')
from achievement_definitions import calc_all
r = calc_all()
print(r.get('<id>'))
"

# 3. 确认图片路径
ls -la /Users/mt16/dev/dizical/src/kid_app/static/badges/<id>.png

# 4. 启动服务，打开 badges 页验证 UI
```

---

## 相关文件索引

| 文件 | 作用 |
|------|------|
| `src/achievement_definitions.py` | 计算逻辑唯一数据源 |
| `src/migrate_achievements.py` | 建表 + 初始数据迁移脚本 |
| `docs/badge-prompts.md` | Enamel pin prompt 模板 + 已生成记录 |
| `docs/表结构.md` | achievements / achievement_stats / achievement_badges 表结构 |
| `src/kid_app/static/badges/` | badge PNG 文件目录 |
| `src/kid_app/templates/badges.html` | 勋章墙前端 |
| `tqob/00-Artifacts/image-gen.md` | Fal 生图 CDN URL + 本地路径记录 |

---

## 注意事项

- **不要在多页面共用的 db 连接上调用 `conn.close()`**（教训：badges_page() 关闭共享连接导致 500）
- **seasonal 不写 achievement_stats**，每次 `calc_all()` 实时算
- **grade_* 类型**走 `_calc_milestone()` 里的 `aid.startswith("grade_")` 分支
- **TOP 成就（top1/top2/top3）**的 condition 动态生成，展示对应排名科目，不走静态 CONDITION 字典
- **归档过滤**：统计时用 `is_archived=0` 过滤科目，不用 `is_active`
