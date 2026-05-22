#!/usr/bin/env python3
"""
增量迁移：seasonal_cycle 字段 + daily_checkin badge
- achievements.seasonal_type
- achievement_stats.cycle_type / cycle_key / cycle_achieved_at
- 新增 daily_checkin badge
用法: python3 src/migrate_seasonal_cycle.py
"""
import sqlite3

DB_PATH = "/Users/mt16/dev/dizical/data/dizi.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── achievements.seasonal_type ──────────────────────────────────
    try:
        cur.execute("ALTER TABLE achievements ADD COLUMN seasonal_type TEXT DEFAULT 'monthly'")
        print("+ achievements.seasonal_type")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  achievements.seasonal_type 已存在，跳过")
        else:
            raise

    # ── achievement_stats 新字段 ────────────────────────────────────
    for col, dtype in [
        ("cycle_type",   "TEXT"),
        ("cycle_key",    "TEXT"),
        ("cycle_achieved_at", "DATETIME"),
    ]:
        try:
            cur.execute(f"ALTER TABLE achievement_stats ADD COLUMN {col} {dtype}")
            print(f"+ achievement_stats.{col}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  achievement_stats.{col} 已存在，跳过")
            else:
                raise

    # ── 更新现有 seasonal badge 的 seasonal_type ────────────────────
    updates = [
        ("monthly", "total_60"),
        ("stage",   "week_champ"),
        ("stage",   "full_month"),
        ("stage",   "top1"),
        ("stage",   "early_riser"),
        ("stage",   "little_chick_commander"),
        ("stage",   "first_to_act"),
    ]
    for stype, aid in updates:
        cur.execute(
            "UPDATE achievements SET seasonal_type=? WHERE id=? AND category='seasonal'",
            (stype, aid))
        if cur.rowcount:
            print(f"  updated {aid} → seasonal_type={stype}")

    # ── 插入 daily_checkin badge ───────────────────────────────────
    cur.execute("SELECT 1 FROM achievements WHERE id='daily_checkin'")
    if cur.fetchone():
        print("  daily_checkin 已存在，跳过")
    else:
        cur.execute("""
            INSERT INTO achievements
                (id, name, type, category, seasonal_type, stat_logic,
                 description, display_format, threshold, sort_order)
            VALUES
                ('daily_checkin', '每日打卡', '突破', 'seasonal', 'daily',
                 'daily_checkin', '每日完成练习即可获得', '已打卡', 1, 99)
        """)
        print("+ daily_checkin badge")

    conn.commit()
    conn.close()
    print("迁移完成！")


if __name__ == "__main__":
    migrate()
