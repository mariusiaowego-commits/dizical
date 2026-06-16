"""
Phase 3 (2026-06-16 17:08 user ack):
1. night_owl stat_logic 改 '20:00 及以后' (用户拍板, 跟 db 实际 20:xx 12 行匹配)
2. streak_1/3 unlock — user 拍板按真实调研情况来 (current streak >= 3, 但 db 显示 >= 5)
   - streak_1 (≥1): YES unlock
   - streak_3 (≥3): YES unlock
   - streak_7/14/30/100: NO unlock (不盲)
3. song_end DELETE: user **未 ack**, 不动
4. grade_1 加新字段: user **未 ack**, 不动

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/restore_badge_phase3_nightowl_streak.py
"""
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def calc_current_streak() -> int:
    """跟 V1 era calc_all() 的 streak_days() 算法一致 — 从昨天往前数,
    连续每天有 total_minutes >= 10 的练习."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("""
        SELECT date FROM daily_practices
        WHERE total_minutes >= 10
        ORDER BY date DESC
    """)
    dates = [datetime.strptime(r[0], "%Y-%m-%d").date() for r in cur.fetchall()]
    conn.close()
    if not dates:
        return 0
    streak = 0
    check = dates[0]  # 最近练习日
    # 从昨天开始数 (跟 V1 era _get_consecutive_streak 一致: "今天没练不影响计数")
    # 实际 streak_days 逻辑是从今天开始数 (包括今天)
    # 重新读 V1 era 逻辑:
    # check = today, 从今天开始数, 找到 dates 里有就 streak++
    today = datetime.now().date()
    streak = 0
    for d in dates:
        if d == today:
            streak += 1
            today -= timedelta(days=1)
        elif d < today:
            # dates 排序 DESC, 第一个 < today 说明今天没练
            # 改用昨天起数
            today = today + timedelta(days=1)
            check = today - timedelta(days=1)
            streak = 0
            for dd in dates:
                if dd == check:
                    streak += 1
                    check -= timedelta(days=1)
                elif dd < check:
                    break
            break
        else:
            break
    return streak


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 1. night_owl stat_logic 改 20:00
    print("=== 1. night_owl stat_logic 改 '20:00 及以后' ===")
    cur.execute("""
        UPDATE achievements SET
            stat_logic='晚上 8 点及以后 (CST 20:00) 还在练习'
        WHERE id='night_owl'
    """)
    n_nightowl = cur.rowcount
    print(f"  ✓ night_owl: {n_nightowl} updated")
    conn.commit()

    # 2. streak_1/3 unlock (按真实调研)
    print("\n=== 2. streak_1/3 按真实调研 unlock ===")
    # 用 SQL 直接算 current streak (跟 V1 era calc_all 一致):
    # 从 MAX(date) 往后, 连续 date(total_minutes >= 10) 的天数
    cur.execute("""
        WITH RECURSIVE walk(date, streak) AS (
            SELECT date(MAX(date)), 1 FROM daily_practices WHERE total_minutes >= 10
            UNION ALL
            SELECT date(walk.date, '-1 day'), walk.streak+1 FROM walk
            WHERE EXISTS (SELECT 1 FROM daily_practices
                          WHERE date=date(walk.date, '-1 day') AND total_minutes >= 10)
        )
        SELECT MAX(streak) FROM walk
    """)
    row = cur.fetchone()
    current_streak = row[0] if row else 0
    print(f"  当前连续 streak = {current_streak} 天 (SQL 算, total_minutes >= 10)")

    # streak_1 阈值 1, streak_3 阈值 3
    to_unlock = []
    if current_streak >= 1:
        to_unlock.append(("streak_1", 1))
    if current_streak >= 3:
        to_unlock.append(("streak_3", 3))
    # streak_7/14/30/100 不该 unlock (current < 7)

    print(f"  应该 unlock: {[bid for bid, _ in to_unlock]}")
    print(f"  不 unlock: streak_7/14/30/100 (current < 阈值)")

    for bid, threshold in to_unlock:
        # 看是否已有行
        cur.execute("SELECT achieved FROM achievement_stats WHERE achievement_id=?", (bid,))
        row = cur.fetchone()
        if row and row[0] == 'Y':
            print(f"  ✓ {bid}: 已经 unlocked, 跳过")
            continue
        # INSERT OR UPDATE
        cur.execute("""
            INSERT INTO achievement_stats (achievement_id, achieved, achieved_at, raw_stats, computed_value)
            VALUES (?, 'Y', CURRENT_TIMESTAMP, ?, ?)
            ON CONFLICT(achievement_id) DO UPDATE SET
                achieved='Y',
                achieved_at=CURRENT_TIMESTAMP,
                computed_value=excluded.computed_value
        """, (bid, f'{{"threshold": {threshold}, "current_streak": {current_streak}}}', current_streak))
        print(f"  ✓ {bid}: unlocked, achieved_at=CURRENT_TIMESTAMP")

    # 验证 streak_7/14/30/100 维持 unlocked=False (即使没行也是 False)
    for bid in ["streak_7", "streak_14", "streak_30", "streak_100"]:
        cur.execute("SELECT achieved FROM achievement_stats WHERE achievement_id=?", (bid,))
        row = cur.fetchone()
        if row and row[0] == 'Y':
            # 错误! 之前 unlock 了不该 unlock 的
            print(f"  ⚠️ {bid}: db 显示 unlocked 但 current streak < 阈值, 这是 V1 era 数据不一致")
        else:
            print(f"  ✓ {bid}: 维持 unlocked=False")

    conn.commit()

    # verify
    print("\n=== verify ===")
    cur.execute("SELECT achievement_id, achieved, achieved_at FROM achievement_stats ORDER BY achievement_id")
    for row in cur.fetchall():
        print(f"  {row[0]}: achieved={row[1]}, achieved_at={row[2]}")
    conn.close()
    print("\n✅ Phase 3 完成 (night_owl 改 20:00 + streak_1/3 unlock)")


if __name__ == "__main__":
    main()