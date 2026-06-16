"""
最终恢复脚本: 3 个 early_bird + assign_pal 完整复原
(2026-06-16 事故后, 用 V1 era add_badge_early.py 描述 + 正确 url).

事故: PR #104 漏了:
1. 3 个 early_bird (early_riser / little_chick_commander / first_to_act) url
   写错: 应该是 early_bird_A/B/C.png, 不是 early_riser.png 等 (文件不存在)
2. 3 个 description 我恢复时偷懒, 用 "..." 占位, 失去 V1 era 完整典故
3. assign_pal 整个 V2 era 后加的, 不在 V1 era 40 行恢复脚本里

修法: 跑本脚本, 完整复原 3 个 early_bird (祖逖闻鸡起舞典故 + early_bird_A/B/C.png)
+ 1 个 assign_pal (V2 era 内容, 之前 commit 已验, MD5 a457f9b6)

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/restore_full_badge_v2.2.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"

# V1 era 3 个 early_bird (PR #31 era, 2026-05-20 拍板, add_badge_early.py)
# 3 个共用同一祖逖闻鸡起舞典故 (PR #31 拍板给女儿看)
EARLY_BIRD_DESC = (
    "很久很久以前，有两个好朋友，一个叫**祖逖**，一个叫**刘琨**。"
    "他们住在一起，每天睡同一张床。"
    "有一天半夜，外面突然传来——\n\n"
    "**\"喔喔喔——！\"**一只鸡在叫。\n\n"
    "刘琨迷迷糊糊翻了个身，想继续睡。"
    "但祖逖一下子坐起来，眼睛亮亮的，说：\n"
    "> **\"这不是坏声音！这是在叫我们起床呢！\"**\n\n"
    "别人都觉得半夜鸡叫很烦人，祖逖却觉得——这是在催我呀！"
    "于是他拉着刘琨跑出门，在黑漆漆的夜里，拿起剑就开始练。一直练到天亮。\n\n"
    "后来，他们每天都这样。鸡一叫，就起来练。刮风下雨也不停。"
    "再后来，两个人都变成了特别厉害的大将军。"
)

EARLY_BIRDS = [
    {
        "id": "early_riser", "name": "闻鸡起舞", "threshold": 20,
        "display_format": "当月首次练习在20:00前解锁",
        "img": "early_bird_A.png", "sort": 29,
    },
    {
        "id": "little_chick_commander", "name": "小鸡指挥官", "threshold": 17,
        "display_format": "当月首次练习在17:00前解锁",
        "img": "early_bird_B.png", "sort": 30,
    },
    {
        "id": "first_to_act", "name": "先声夺人", "threshold": 12,
        "display_format": "当月首次练习在12:00前解锁",
        "img": "early_bird_C.png", "sort": 31,
    },
]

# V2 era assign_pal (PR #98 era, 2026-06-15 拍板)
# 完整数据: id / name / type / category / stat_logic / description / display_format
# / threshold / unlock_strategy='immediate' / cond_text / placeholder
ASSIGN_PAL_META = {
    "id": "assign_pal", "name": "批改小帮手", "type": "突破", "category": "milestone",
    "placeholder": "a proud chibi girl with long black hair and big anime eyes, styled beautifully like your daughter, wearing a cute mini teacher's glasses, happily holding a golden fountain pen to grade stack of math test papers with glowing red checkmarks. Next to her stands a majestic vertical golden plaque elegantly engraved with the five prominent Chinese characters \"蒙正好少年\", surrounded by fluttering colorful number ribbons, mathematical symbols like plus and minus, and floating sparkling celebration stardust",
    "zh_story": "居里夫人拿过两次诺贝尔奖，但很少有人知道，她的女儿伊雷娜小时候最常干的事不是做实验——是帮妈妈洗试管、抄数据、整理实验记录。居里夫人的笔记本字迹潦草（毕竟她要在放射性物质和家务之间反复横跳），伊雷娜就一项项誊写清楚，有时还能挑出妈妈的计算错误。居里夫人说：\"这孩子比我仔细。\"后来伊雷娜长大了，真的自己拿了一枚诺贝尔化学奖——史上唯一一对母女诺贝尔奖得主。\n\n你帮妈妈批数学作业，画红色对勾，戴迷你教师眼镜——你以为这只是小事？伊雷娜帮妈妈抄数据，后来拿了诺贝尔奖；祖暅之帮爸爸挑错，后来算出了球体积。每一个\"帮妈妈批作业\"的小孩，都是隐藏的学术继承者。妈妈的红笔交到你手里的那一刻，你就不是小孩了——你是数学界最年轻的编外助教！蒙正好少年，批的不是作业，是未来！",
    "cond_text": "完成任意一天任意数量的批改任务",
    "display_format": "achieved_flag",
    "unlock_strategy": "immediate",  # 纪念章场景, commit 立即解锁
}


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # ===== Part 1: 3 个 early_bird (V1 era 复原) =====
    print("=== Part 1: 3 个 early_bird ===")
    for b in EARLY_BIRDS:
        # achievements: 用 UPDATE (description 全, 不用 INSERT OR IGNORE)
        # 因为 description 之前被 "..." 占位, 这次要覆盖回完整典故
        cur.execute("""
            UPDATE achievements SET
                name=?, type='突破', category='seasonal',
                stat_logic=?, description=?, display_format=?, threshold=?,
                sort_order=?
            WHERE id=?
        """, (
            b["name"],
            f"monthly_first_practice_before_{b['threshold']}",
            EARLY_BIRD_DESC,
            b["display_format"],
            b["threshold"],
            b["sort"],
            b["id"],
        ))
        n_ach = cur.rowcount

        # achievement_badges: url = /static/badges/early_bird_X.png
        cur.execute("""
            UPDATE achievement_badges SET url=?
            WHERE achievement_id=? AND is_current=1
        """, (f"/static/badges/{b['img']}", b["id"]))
        n_bdg = cur.rowcount

        print(f"  ✓ {b['id']} ({b['name']}): "
              f"achievements {n_ach} updated, "
              f"achievement_badges {n_bdg} updated, "
              f"img=early_bird_{b['img'][-5]}")
    conn.commit()

    # ===== Part 2: assign_pal (V2 era 复原) =====
    print("\n=== Part 2: assign_pal ===")
    a = ASSIGN_PAL_META
    # 1. 看是否已存在
    cur.execute("SELECT id FROM achievements WHERE id=?", (a["id"],))
    exists = cur.fetchone() is not None

    if exists:
        # UPDATE 全字段
        cur.execute("""
            UPDATE achievements SET
                name=?, type=?, category=?,
                stat_logic=?, description=?, display_format=?,
                unlock_strategy=?, cond_text=?
            WHERE id=?
        """, (
            a["name"], a["type"], a["category"],
            f"never_unlock_(designed_for_display)",  # calc 永远 Y
            a["zh_story"],  # 完整典故
            a["display_format"],
            a["unlock_strategy"],
            a["cond_text"],
            a["id"],
        ))
        print(f"  ✓ achievements updated: {cur.rowcount}")
    else:
        # INSERT 全字段
        cur.execute("""
            INSERT INTO achievements
              (id, name, type, category, stat_logic, description, display_format,
               threshold, cond_text, unlock_strategy, placeholder)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        """, (
            a["id"], a["name"], a["type"], a["category"],
            f"never_unlock_(designed_for_display)",
            a["zh_story"], a["display_format"],
            a["cond_text"], a["unlock_strategy"], a["placeholder"],
        ))
        print(f"  ✓ achievements inserted: {cur.rowcount}")

    # 2. achievement_badges: url = /static/badges/assign_pal_v2.png
    # 看是否已存在
    cur.execute("SELECT id FROM achievement_badges WHERE achievement_id=?", (a["id"],))
    if cur.fetchone():
        cur.execute("""
            UPDATE achievement_badges SET url=?, version=2, is_current=1
            WHERE achievement_id=?
        """, ("/static/badges/assign_pal_v2.png", a["id"]))
        print(f"  ✓ achievement_badges updated: {cur.rowcount}")
    else:
        cur.execute("""
            INSERT INTO achievement_badges
              (achievement_id, url, is_locked, version, is_current)
            VALUES (?, ?, 0, 2, 1)
        """, (a["id"], "/static/badges/assign_pal_v2.png"))
        print(f"  ✓ achievement_badges inserted: {cur.rowcount}")

    # 3. achievement_stats: immediate → achieved='Y' + achieved_at=now
    cur.execute("SELECT achievement_id FROM achievement_stats WHERE achievement_id=?", (a["id"],))
    if cur.fetchone():
        cur.execute("""
            UPDATE achievement_stats
            SET achieved='Y', achieved_at=CURRENT_TIMESTAMP
            WHERE achievement_id=?
        """, (a["id"],))
        print(f"  ✓ achievement_stats updated (immediate): {cur.rowcount}")
    else:
        cur.execute("""
            INSERT INTO achievement_stats
              (achievement_id, achieved, achieved_at, raw_stats, computed_value)
            VALUES (?, 'Y', CURRENT_TIMESTAMP, '{}', NULL)
        """, (a["id"],))
        print(f"  ✓ achievement_stats inserted (immediate): {cur.rowcount}")

    conn.commit()

    # ===== Verify =====
    print("\n=== verify ===")
    for bid in ["early_riser", "little_chick_commander", "first_to_act", "assign_pal"]:
        cur.execute("""
            SELECT a.id, a.name, LENGTH(a.description) as desc_len, a.unlock_strategy,
                   a.cond_text, b.url
            FROM achievements a
            LEFT JOIN achievement_badges b ON a.id = b.achievement_id AND b.is_current = 1
            WHERE a.id = ?
        """, (bid,))
        row = cur.fetchone()
        if row:
            bid_, name, desc_len, unlock, cond, url = row
            print(f"  {bid_} ({name}): desc={desc_len} 字符, unlock={unlock}, "
                  f"cond={'是' if cond else '否'}, url={url}")
    conn.close()
    print("\n✅ 全部恢复完成")


if __name__ == "__main__":
    main()
