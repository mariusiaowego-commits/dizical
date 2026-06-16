"""
恢复 achievement_badges 表 (跟 achievements/stats 配套).

事故: 2026-06-16 conftest DROP 3 张 badge 表, achievements 已恢复 (40 行),
但 achievement_badges 0 行. get_badge_url() fallback 到默认图, 所有 badge
显示同一张 medal_badge.png 占位图.

修法: 只 INSERT achievement_badges, url = /static/badges/{id}.png
(跟 V1 era migrate_achievements.py 写入逻辑一致, 不 DROP).

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/restore_achievement_badges_v1.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"

# 跟 restore_achievements_v1.py 同步 (40 行 V1 era badge)
BADGE_IDS = [
    # seasonal
    "total_60", "week_champ", "full_month", "top1",
    "early_riser", "little_chick_commander", "first_to_act",
    "lucky_61_2026", "lucky_61_2027", "lucky_61_2028", "lucky_61_2029", "lucky_61_2030",
    # milestone
    "streak_1", "streak_3", "streak_7", "streak_14", "streak_30", "streak_100",
    "total_300", "total_600", "total_1000",
    "first_log", "all_items", "double", "top2", "top3",
    "grade_1", "grade_2", "grade_3", "grade_4", "grade_5",
    "grade_6", "grade_7", "grade_8", "grade_9", "grade_10",
    "night_owl", "one_breath", "song_end", "comeback",
    # grade_1~10: 实际文件名是 grade_N-l.png (locked 态) 跟 grade_N-u.png (unlocked 态)
    # V1 era 用 -l 默认, unlocked 时 badge_generator 切换 url (TODO 验证)
]


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 1. 确保表存在
    cur.execute("""
        CREATE TABLE IF NOT EXISTS achievement_badges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            achievement_id  TEXT NOT NULL,
            url             TEXT NOT NULL,
            is_locked       INTEGER NOT NULL DEFAULT 0,
            version         INTEGER NOT NULL DEFAULT 1,
            is_current      INTEGER NOT NULL DEFAULT 1,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # 2. INSERT OR IGNORE (idempotent)
    inserted = 0
    skipped = 0
    for bid in BADGE_IDS:
        url = f"/static/badges/{bid}.png"
        cur.execute("""
            INSERT OR IGNORE INTO achievement_badges
              (achievement_id, url, is_locked, version, is_current)
            VALUES (?, ?, 0, 1, 1)
        """, (bid, url))
        if cur.rowcount > 0:
            inserted += 1
        else:
            skipped += 1
    conn.commit()

    print(f"✓ 尝试 insert {len(BADGE_IDS)} 行")
    print(f"  新增: {inserted}")
    print(f"  已存在 (跳过): {skipped}")

    # 3. fix grade_1~10 url (实际文件名是 -l.png / -u.png, 不是 .png)
    for n in range(1, 11):
        cur.execute("""
            UPDATE achievement_badges SET url=?
            WHERE achievement_id=? AND url=?
        """, (f"/static/badges/grade_{n}-l.png", f"grade_{n}", f"/static/badges/grade_{n}.png"))
    conn.commit()
    cur.execute("SELECT changes()")
    grade_fixed = cur.fetchone()[0]
    if grade_fixed:
        print(f"✓ grade_1~10 url 修到 -l.png: {grade_fixed} 行")
    
    # 4. verify
    cur.execute("SELECT COUNT(*) FROM achievement_badges")
    n = cur.fetchone()[0]
    print(f"✓ achievement_badges 表现在 {n} 行")
    conn.close()


if __name__ == "__main__":
    main()
