"""
迁移：新建 achievements + achievement_stats + achievement_badges 表
dizi.db（练习数据库）

achievements      : 成就定义（静态），含prompt模板
achievement_stats : 动态状态（achieved Y/N / raw_stats / computed_value）
achievement_badges: badge图片版本历史（每次生新图插入一条，is_current=1）

prompt模板字段：
  unlocked_template : 已解锁生图prompt，含 [PLACEHOLDER] 占位符
  placeholder       : 替换 [PLACEHOLDER] 的实际主体内容
  locked_template  : 未解锁生图prompt，含 [PLACEHOLDER] 占位符
"""
import sqlite3
import json
import datetime as dt

DB_PATH = "/Users/mt16/dev/dizical/data/dizi.db"

# ─── achievements 定义数据 ───────────────────────────────────────────────
# category: milestone=里程碑达成型（有achieved Y/N/一次性解锁）,
#            seasonal=赛季型（固定周期重置统计）
ACHIEVEMENTS = [
    # ── 赛季型（seasonal）─────────────────────────────────────────────
    {
        "id": "total_60",
        "name": "小水滴",
        "type": "突破",
        "category": "seasonal",
        "stat_logic": "当月累计练习超过60分钟（自然月）",
        "description": "小水滴嗒嗒嗒滴了几十天，把大石头滴穿了。你一个月练满60分钟，小水滴\"嗒嗒嗒\"，把60分钟这关也滴穿啦！",
        "display_format": "time_hours_minutes",
        "threshold": 60,
    },
    {
        "id": "week_champ",
        "name": "绕梁七日",
        "type": "巅峰",
        "category": "seasonal",
        "stat_logic": "本周（stage_start→stage_end）练习时长超过上周",
        "description": "古代有个姐姐叫韩娥，她唱歌太好听了，唱完了声音还在房梁上绕了三天才肯走——你练笛子超过上周的自己，说明你的笛声也能绕梁啦！🎵",
        "display_format": "minutes",
        "threshold": None,
    },
    {
        "id": "full_month",
        "name": "刮目相看",
        "type": "巅峰",
        "category": "seasonal",
        "stat_logic": "本月练习时长超过上月（自然月）",
        "description": "古代有个叫吕蒙的大哥哥，没时间读书，后来开始每天读一点点。他的朋友遇到他，说：哇！你已经不是之前那个人！不是以前那个你了！吕蒙说：我们才分别三天，你就要把眼睛好好擦一擦，重新看我了！你的这个月比上个月练得还多——你同学如果上个月遇到你，这个月再听你吹笛子会说：哇！你已经不是那个你了",
        "display_format": "minutes",
        "threshold": None,
    },
    {
        "id": "top1",
        "name": "情有独钟",
        "type": "突破",
        "category": "seasonal",
        "stat_logic": "当月练习时长第1名的科目",
        "description": "古代有个下棋很厉害的人叫奕秋，他教两个小朋友下棋。一个小朋友竖起耳朵认认真真听着；另一个总东张西望，想外面有什么好玩的。最后那个专心的小朋友，下棋越来越厉害，比另一个厉害好多好多。你所有的科目里这个月xxx这个吹得最多！",
        "display_format": "top_items",
        "threshold": None,
    },
    # ── 里程碑达成型（milestone）────────────────────────────────────────
    {
        "id": "streak_1",
        "name": "初试啼声",
        "type": "突破",
        "category": "milestone",
        "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥1 天",
        "description": "开始你的练习之旅！",
        "display_format": "days",
        "threshold": 1,
    },
    {
        "id": "streak_3",
        "name": "小火焰",
        "type": "执着",
        "category": "milestone",
        "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥3 天",
        "description": "连续打卡，笛子都被你吹服了！",
        "display_format": "days",
        "threshold": 3,
    },
    {
        "id": "streak_7",
        "name": "周冠军",
        "type": "执着",
        "category": "milestone",
        "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥7 天",
        "description": "坚持一周，你就是时间管理大师！",
        "display_format": "days",
        "threshold": 7,
    },
    {
        "id": "streak_14",
        "name": "双周传说",
        "type": "执着",
        "category": "milestone",
        "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥14 天",
        "description": "两周坚持，传说初现！",
        "display_format": "days",
        "threshold": 14,
    },
    {
        "id": "streak_30",
        "name": "月度王者",
        "type": "晋级",
        "category": "milestone",
        "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥30 天",
        "description": "整月打卡，王者风范！",
        "display_format": "days",
        "threshold": 30,
    },
    {
        "id": "streak_100",
        "name": "百日传奇",
        "type": "晋级",
        "category": "milestone",
        "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥100 天",
        "description": "百日坚持，传奇诞生！",
        "display_format": "days",
        "threshold": 100,
    },
    {
        "id": "total_300",
        "name": "五小时战士",
        "type": "突破",
        "category": "milestone",
        "stat_logic": "所有 daily_practices.total_minutes 累加 ≥300 分钟",
        "description": "五小时积累，小试牛刀！",
        "display_format": "time_hours_minutes",
        "threshold": 300,
    },
    {
        "id": "total_600",
        "name": "十小时大师",
        "type": "巅峰",
        "category": "milestone",
        "stat_logic": "所有 daily_practices.total_minutes 累加 ≥600 分钟",
        "description": "十小时磨砺，大师初成！",
        "display_format": "time_hours_minutes",
        "threshold": 600,
    },
    {
        "id": "total_1000",
        "name": "千分钟传奇",
        "type": "巅峰",
        "category": "milestone",
        "stat_logic": "所有 daily_practices.total_minutes 累加 ≥1000 分钟",
        "description": "千分钟传奇前无古人！",
        "display_format": "time_hours_minutes",
        "threshold": 1000,
    },
    {
        "id": "first_log",
        "name": "第一声",
        "type": "突破",
        "category": "milestone",
        "stat_logic": "存在至少一条练习记录（total_minutes > 0）即为达成",
        "description": "第一次吹响你的笛子！",
        "display_format": "achieved_flag",
        "threshold": 1,
    },
    {
        "id": "all_items",
        "name": "全能选手",
        "type": "神秘",
        "category": "milestone",
        "stat_logic": "同一天练习所有科目（以 practice_items 活跃小项数量为准）",
        "description": "全能选手，样样精通！",
        "display_format": "achieved_flag",
        "threshold": None,
    },
    {
        "id": "double",
        "name": "加练狂魔",
        "type": "执着",
        "category": "milestone",
        "stat_logic": "同一天完成 ≥2 次打卡（多条记录合并后项数 ≥2）",
        "description": "同一天两次练习，卷王诞生！",
        "display_format": "achieved_flag",
        "threshold": 2,
    },
    {
        "id": "top2",
        "name": "TOP2 卷王",
        "type": "突破",
        "category": "milestone",
        "stat_logic": "按 item name 汇总累计时长，第2名科目",
        "description": "练习时长第二多，同样出色！",
        "display_format": "top_items",
        "threshold": 2,
    },
    {
        "id": "top3",
        "name": "TOP3 新星",
        "type": "突破",
        "category": "milestone",
        "stat_logic": "按 item name 汇总累计时长，第3名科目",
        "description": "练习时长第三名，新星升起！",
        "display_format": "top_items",
        "threshold": 3,
    },
    # ── 段位系（milestone）───────────────────────────────────────────
    {
        "id": "grade_1",
        "name": "一级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过一级竹笛考级",
        "description": "恭喜考取一级！",
        "display_format": "achieved_flag",
        "threshold": 1,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 1 on it, confetti and musical notes floating around, celebratory mood",
        "achieved": "Y",
        "achieved_at": "2026-07-01 00:00:00",
    },
    {
        "id": "grade_2",
        "name": "二级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过二级竹笛考级",
        "description": "恭喜考取二级！",
        "display_format": "achieved_flag",
        "threshold": 2,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 2 on it, confetti and musical notes floating around, celebratory mood",
    },
    {
        "id": "grade_3",
        "name": "三级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过三级竹笛考级",
        "description": "恭喜考取三级！",
        "display_format": "achieved_flag",
        "threshold": 3,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 3 on it, confetti and musical notes floating around, celebratory mood",
    },
    {
        "id": "grade_4",
        "name": "四级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过四级竹笛考级",
        "description": "恭喜考取四级！",
        "display_format": "achieved_flag",
        "threshold": 4,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 4 on it, confetti and musical notes floating around, celebratory mood",
    },
    {
        "id": "grade_5",
        "name": "五级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过五级竹笛考级",
        "description": "恭喜考取五级！",
        "display_format": "achieved_flag",
        "threshold": 5,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 5 on it, confetti and musical notes floating around, celebratory mood",
    },
    {
        "id": "grade_6",
        "name": "六级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过六级竹笛考级",
        "description": "恭喜考取六级！",
        "display_format": "achieved_flag",
        "threshold": 6,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 6 on it, confetti and musical notes floating around, celebratory mood",
    },
    {
        "id": "grade_7",
        "name": "七级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过七级竹笛考级",
        "description": "恭喜考取七级！",
        "display_format": "achieved_flag",
        "threshold": 7,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 7 on it, confetti and musical notes floating around, celebratory mood",
    },
    {
        "id": "grade_8",
        "name": "八级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过八级竹笛考级",
        "description": "恭喜考取八级！",
        "display_format": "achieved_flag",
        "threshold": 8,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 8 on it, confetti and musical notes floating around, celebratory mood",
    },
    {
        "id": "grade_9",
        "name": "九级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过九级竹笛考级",
        "description": "恭喜考取九级！",
        "display_format": "achieved_flag",
        "threshold": 9,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 9 on it, confetti and musical notes floating around, celebratory mood",
    },
    {
        "id": "grade_10",
        "name": "十级",
        "type": "段位",
        "category": "milestone",
        "stat_logic": "通过十级竹笛考级",
        "description": "恭喜考取十级！",
        "display_format": "achieved_flag",
        "threshold": 10,
        "placeholder": "a cute Asian child with dark black hair, straight bangs, hair braided into buns on top sides with two short strands hanging down near ears, round face with baby fat, very fair porcelain skin, large expressive eyes looking at viewer, slight gentle smile, wearing a white polo shirt with pink collar and pink placket with white buttons, school uniform style, proudly holding a bamboo flute with red tassels, a golden certificate with the number 10 on it, confetti and musical notes floating around, celebratory mood",
    },
]


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ─── 删除旧表 ─────────────────────────────────────────────────────
    cur.execute("DROP TABLE IF EXISTS achievement_badges")
    cur.execute("DROP TABLE IF EXISTS achievement_stats")
    cur.execute("DROP TABLE IF EXISTS achievements")

    # ─── 创建 achievements 表（定义）──────────────────────────────────
    cur.execute("""
        CREATE TABLE achievements (
            id                TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            type              TEXT NOT NULL,
            category          TEXT NOT NULL DEFAULT 'milestone',
            stat_logic        TEXT NOT NULL,
            description       TEXT NOT NULL,
            display_format    TEXT NOT NULL,
            threshold         INTEGER,
            unlocked_template TEXT,
            placeholder       TEXT,
            locked_template   TEXT,
            sort_order        INTEGER DEFAULT 0,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ─── 创建 achievement_stats 表（动态状态）──────────────────────────
    cur.execute("""
        CREATE TABLE achievement_stats (
            achievement_id   TEXT PRIMARY KEY REFERENCES achievements(id),
            achieved         TEXT DEFAULT 'N',
            achieved_at      DATETIME,
            raw_stats        TEXT,
            computed_value   TEXT,
            updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ─── 创建 achievement_badges 表（badge版本历史）────────────────────
    cur.execute("""
        CREATE TABLE achievement_badges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            achievement_id  TEXT NOT NULL REFERENCES achievements(id),
            url             TEXT NOT NULL,
            is_locked       INTEGER DEFAULT 0,
            version         INTEGER DEFAULT 1,
            is_current      INTEGER DEFAULT 1,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    UNLOCKED_TPL = "An emoji-adjacent 3D enamel pin of [PLACEHOLDER]. Polished gold metal borders enclose flat, glossy enamel fills. The design is a centered, iconic illustration with a smooth, friendly silhouette and vibrant colors, matching a child achievement badge style. Studio lighting reflects off the reflective enamel and raised gold metal edges. Orthographic, straight-on view, high quality, isolated on a clean white background."
    LOCKED_TPL = "An emoji-adjacent 3D enamel pin of a child figure silhouette, hair braided into buns on top, round head outline, holding a bamboo flute outline, certificate shape outline nearby, floating musical notes and confetti outlines around. Made of heavy dark brushed iron, monochromatic charcoal grey, non-reflective matte finish, rustic metal texture, no vibrant colors, no facial features, no body details, just smooth silhouette contours with subtle ambient occlusion at edges and periphery. The design is a centered, iconic outline illustration. Orthographic, straight-on view, high quality, isolated on a clean white background."

    # ─── 写入 achievements ────────────────────────────────────────────
    for idx, a in enumerate(ACHIEVEMENTS, 1):
        placeholder = a.get("placeholder", "")
        cur.execute("""
            INSERT INTO achievements
                (id, name, type, category, stat_logic, description,
                 display_format, threshold,
                 unlocked_template, placeholder, locked_template,
                 sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            a["id"], a["name"], a["type"], a["category"],
            a["stat_logic"], a["description"], a["display_format"],
            a["threshold"],
            UNLOCKED_TPL if placeholder else None,
            placeholder if placeholder else None,
            LOCKED_TPL if placeholder else None,
            idx,
        ))

    # ─── 初始化 achievement_stats ────────────────────────────────────
    for a in ACHIEVEMENTS:
        achieved = a.get("achieved", "N")
        achieved_at = a.get("achieved_at")
        computed = "1" if achieved == "Y" else None
        cur.execute("""
            INSERT INTO achievement_stats
                (achievement_id, achieved, achieved_at, raw_stats, computed_value)
            VALUES (?, ?, ?, '{}', ?)
        """, (a["id"], achieved, achieved_at, computed))

    # ─── 迁移现有 badge URL 到 achievement_badges ─────────────────────
    # 当前 achievements.unlocked_url / locked_url 的值全部迁入 achievement_badges
    # 作为 version=1, is_current=1
    badge_rows = []
    for a in ACHIEVEMENTS:
        uid = f"/static/badges/{a['id']}.png"
        lid = f"/static/badges/{a['id']}.png"
        # unlocked
        badge_rows.append((a["id"], uid, 0, 1, 1))
        # locked（milestone 型才有 locked 版本）
        if a["category"] == "milestone":
            badge_rows.append((a["id"], lid, 1, 1, 1))

    cur.executemany("""
        INSERT INTO achievement_badges (achievement_id, url, is_locked, version, is_current)
        VALUES (?, ?, ?, ?, ?)
    """, badge_rows)

    conn.commit()

    # ─── 验证 ─────────────────────────────────────────────────────────
    print("=== 表统计 ===")
    for table, col in [("achievements", "COUNT(*)"), ("achievement_stats", "COUNT(*)"), ("achievement_badges", "COUNT(*)")]:
        cur.execute(f"SELECT {col} FROM {table}")
        print(f"  {table}: {cur.fetchone()[0]} 条")

    print()
    print("=== achievements 分类汇总 ===")
    cur.execute("SELECT category, COUNT(*) FROM achievements GROUP BY category")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]} 条")

    print()
    print("=== achievement_badges 示例（每成就最新一条）===")
    cur.execute("""
        SELECT ab.achievement_id, a.name, ab.url, ab.is_locked, ab.version, ab.is_current
        FROM achievement_badges ab
        JOIN achievements a ON a.id = ab.achievement_id
        WHERE ab.id IN (
            SELECT id FROM achievement_badges
            WHERE achievement_id = ab.achievement_id AND is_locked = ab.is_locked
            ORDER BY version DESC LIMIT 1
        )
        ORDER BY ab.achievement_id, ab.is_locked
    """)
    for row in cur.fetchall():
        locked_str = "未解锁" if row[3] else "已解锁"
        print(f"  {row[0]} [{locked_str}] v{row[4]} current={row[5]}  {row[2]}")

    conn.close()
    print()
    print("迁移完成！")


if __name__ == "__main__":
    migrate()
