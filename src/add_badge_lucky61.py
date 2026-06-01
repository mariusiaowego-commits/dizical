#!/usr/bin/env python3
"""添加 5 枚六一儿童节徽章（2026-2030，category=seasonal，常驻每年 6-1 解锁）"""
import sqlite3

DB = "/Users/mt16/dev/dizical/data/dizi.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

DESC = "六一节当天完成竹笛练习即可解锁，永久保留"

badges = [
    {
        "id": "lucky_61_2026",
        "name": "幸运六一节",
        "year": 2026,
        "img": "lucky_61_2026.png",
        "sort": 32,
    },
    {
        "id": "lucky_61_2027",
        "name": "鱼跃闻韶",
        "year": 2027,
        "img": "lucky_61_2027.png",
        "sort": 33,
    },
    {
        "id": "lucky_61_2028",
        "name": "安知非鱼",
        "year": 2028,
        "img": "lucky_61_2028.png",
        "sort": 34,
    },
    {
        "id": "lucky_61_2029",
        "name": "浣溪童乐",
        "year": 2029,
        "img": "lucky_61_2029.png",
        "sort": 35,
    },
    {
        "id": "lucky_61_2030",
        "name": "逍遥游鱼",
        "year": 2030,
        "img": "lucky_61_2030.png",
        "sort": 36,
    },
]

for b in badges:
    cur.execute("SELECT 1 FROM achievements WHERE id=?", (b["id"],))
    if cur.fetchone():
        print(f"  {b['id']} 已存在，跳过")
        continue
    cur.execute("""
        INSERT INTO achievements
          (id, name, type, category, seasonal_type, stat_logic,
           description, display_format, threshold, sort_order)
        VALUES
          (?, ?, '突破', 'seasonal', 'monthly', ?,
           ?, ?, 1, ?)
    """, (
        b["id"], b["name"],
        f"exists_practice_on_{b['year']}_06_01",
        DESC,
        f"{b['year']}年6月1日完成练习解锁",
        b["sort"],
    ))
    cur.execute("""
        INSERT INTO achievement_badges
          (achievement_id, url, is_locked, version, is_current)
        VALUES (?, ?, 0, 1, 1)
    """, (b["id"], f"/static/badges/{b['img']}"))
    print(f"  + {b['id']} ({b['name']}) sort={b['sort']}, img={b['img']}")

conn.commit()

# 验证
cur.execute("""
    SELECT id, name, type, category, seasonal_type, stat_logic, sort_order
    FROM achievements
    WHERE id LIKE 'lucky_61_%'
    ORDER BY sort_order
""")
print("\n--- 验证 ---")
for row in cur.fetchall():
    print(" ", row)

cur.execute("""
    SELECT achievement_id, url, is_locked
    FROM achievement_badges
    WHERE achievement_id LIKE 'lucky_61_%'
    ORDER BY achievement_id
""")
print("\n--- 关联图 ---")
for row in cur.fetchall():
    print(" ", row)

conn.close()
print("\nDone.")
