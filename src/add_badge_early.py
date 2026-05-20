#!/usr/bin/env python3
"""添加闻鸡起舞系列 seasonal badge"""
import sqlite3

DB = "/Users/mt16/dev/dizical/data/dizi.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

UNLOCKED_TPL = (
    "An emoji-adjacent 3D enamel pin of [PLACEHOLDER]. "
    "Polished gold metal borders enclose flat, glossy enamel fills. "
    "The design is a centered, iconic illustration with a smooth, friendly silhouette "
    "and vibrant colors, matching a child's achievement badge style. "
    "Studio lighting reflects off the reflective enamel and raised gold metal edges. "
    "Orthographic, straight-on view, high quality, isolated on a clean white background."
)

DESC = (
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

badges = [
    {
        "id": "early_riser",
        "name": "闻鸡起舞",
        "threshold": 20,
        "display_format": "当月首次练习在20:00前解锁",
        "placeholder": "a cute black-haired chibi girl stepping to a rhythmic dance while playing her bamboo flute, alongside a chubby adorable little rooster wearing a golden alarm clock tie who is also dancing on one foot, surrounded by flying golden feathers and sparkling musical notes",
        "img": "early_bird_A.png",
        "sort": 29,
    },
    {
        "id": "little_chick_commander",
        "name": "小鸡指挥官",
        "threshold": 17,
        "display_format": "当月首次练习在17:00前解锁",
        "placeholder": "a cute anime girl with long black hair spinning in a joyful dance with her bamboo flute, while a cheeky little morning chick wearing tiny sunglasses perches on her shoulder, waving a golden conductor baton like a mini maestro",
        "img": "early_bird_B.png",
        "sort": 30,
    },
    {
        "id": "first_to_act",
        "name": "先声夺人",
        "threshold": 12,
        "display_format": "当月首次练习在12:00前解锁",
        "placeholder": "a proud chibi girl with long black hair holding her bamboo flute high like a victory torch, standing side-by-side with a spirited tiny rooster crowing happily on top of a perfectly round golden clock face, with explosive coral-pink and gold sparkle particles in the background",
        "img": "early_bird_C.png",
        "sort": 31,
    },
]

for b in badges:
    placeholder = b["placeholder"]
    unlocked_tpl = UNLOCKED_TPL.replace("[PLACEHOLDER]", placeholder)
    url = f"/static/badges/{b['img']}"

    cur.execute("""
        INSERT INTO achievements
          (id, name, type, category, stat_logic, description,
           display_format, threshold, unlocked_template, placeholder,
           locked_template, sort_order)
        VALUES (?, ?, 'achievement', 'seasonal', ?, ?, ?, ?, ?, ?, NULL, ?)
    """, (
        b["id"], b["name"],
        f"monthly_first_practice_before_{b['threshold']}",
        DESC, b["display_format"], b["threshold"],
        unlocked_tpl, placeholder,
        b["sort"],
    ))

    cur.execute("""
        INSERT INTO achievement_badges
          (achievement_id, url, is_locked, version, is_current)
        VALUES (?, ?, 0, 1, 1)
    """, (b["id"], url))

    print(f"  + {b['id']} ({b['name']}) sort={b['sort']}, img={b['img']}")

conn.commit()

# 验证
cur.execute("SELECT id, name, category, sort_order FROM achievements WHERE id IN ('early_riser','little_chick_commander','first_to_act')")
for row in cur.fetchall():
    print(f"  verified: {row}")

conn.close()
print("Done.")
