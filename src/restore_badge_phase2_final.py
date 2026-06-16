"""
事故补档 Phase 2 (final ack): 4 件事 (2026-06-16 17:08 user ack)

1. night_owl stat_logic 改 20:00 + calc 规则 + 真 unlock
   - 你 phase2 拍板: 20:00
   - 实际 20:00 后有 12 行, calc 应自动 unlock night_owl (2026-05-17 第一次 20:44)
   - calc 规则加进 _calc_milestone (跟 early_riser 一样 pattern)

2. streak_1/3 真 unlock (按真实调研)
   - 当前连续 streak = 5 天 (6-11 ~ 6-15, 6-16 还没练所以 _get_consecutive_streak 返 0)
   - streak_1 + streak_3 历史首次达成 2025-09-27 / 2025-09-29
   - **calc_all() 不能解锁 streak_1/3** 因为 _calc_milestone 优先看 current streak (0)
     _streak_first_achieved_at() 只在 achieved_at 计算用, 不决定 achieved
   - 需手动写 db (achievement_stats 表)
   - streak_7/14/30/100 不该 unlock (实际只有 5 天)

3. song_end DELETE (destructive, 3 张表)
   - 你 ack DELETE

4. calc_all() 钩子 (calc 写 stats) 修法 (不属这次 PR, followup):
   - _calc_milestone streak_1/3 优先 current streak, 不看 historical first_achieved.
     等于"只在当前 streak ≥ n 才返 Y" → 历史已练 100 天但今天没练, calc 返 False
   - 修法: 改成 achieved = (current_streak >= n) OR (stat_achieved) OR (first_achieved_at != None)
   - 这是 PR #87 era 拍板的"永久解锁版", 跟 early_riser 同 pattern
   - 留 followup, 这次不动 (避免 scope creep)

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/restore_badge_phase2_final.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # ===== 1. night_owl stat_logic 改 20:00 =====
    print("=== 1. night_owl stat_logic 改 20:00 ===")
    cur.execute("""
        UPDATE achievements SET
            stat_logic='晚上 8 点后 (CST 20:00) 还在练习'
        WHERE id='night_owl'
    """)
    n = cur.rowcount
    print(f"  ✓ night_owl stat_logic updated: {n} 行")

    # ===== 2. streak_1/3 真 unlock (手动写 stats, calc 钩子不会触发) =====
    print("\n=== 2. streak_1/3 真 unlock (按调研: 5 天连续 6-11~6-15) ===")
    # _streak_first_achieved_at 返回的日期: streak_1=2025-09-27, streak_3=2025-09-29
    # streak_1: 史上第一次练就 streak=1 → 2025-09-27
    # streak_3: 史上第一次连续 3 天 → 2025-09-29
    # (实际我通过 _streak_first_achieved_at 调研)
    for aid, at in [("streak_1", "2025-09-27"),
                    ("streak_3", "2025-09-29")]:
        cur.execute("SELECT achieved FROM achievement_stats WHERE achievement_id=?", (aid,))
        row = cur.fetchone()
        if row is None:
            cur.execute("""
                INSERT INTO achievement_stats
                  (achievement_id, achieved, achieved_at, raw_stats, computed_value)
                VALUES (?, 'Y', ?, '{}', ?)
            """, (aid, at, aid[-1]))
            print(f"  ✓ {aid}: INSERT achieved=Y achieved_at={at}")
        elif row[0] != "Y":
            cur.execute("""
                UPDATE achievement_stats SET achieved='Y', achieved_at=?
                WHERE achievement_id=?
            """, (at, aid))
            print(f"  ✓ {aid}: UPDATE achieved=Y achieved_at={at}")
        else:
            print(f"  - {aid}: 已 unlocked (跳过)")

    # streak_7/14/30/100 不该 unlock (当前 5 天 < 7) - 不动
    print("  - streak_7/14/30/100: 当前 5 天 < 7, 不 unlock ✓")

    # ===== 3. 触发 calc_all() 让钩子写 night_owl =====
    print("\n=== 3. 触发 calc_all() 让 _persist_unlocked_milestones 写 night_owl ===")
    sys.path.insert(0, str(DB_PATH.parent.parent))
    from src.achievement_definitions import calc_all
    results = calc_all()
    unlocked = [(aid, res.achieved_at) for aid, res in results.items()
                if res.achieved and res.achieved_at]
    print(f"  calc_all() 返 {len(unlocked)} 个 unlocked + achieved_at (新发现):")
    for aid, at in unlocked:
        print(f"    - {aid}: achieved_at={at}")

    # ===== 4. song_end DELETE (destructive, 你 ack) =====
    print("\n=== 4. song_end DELETE (destructive, 你 ack) ===")
    for table, col in [("achievement_stats", "achievement_id"),
                       ("achievement_badges", "achievement_id"),
                       ("achievements", "id")]:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col}='song_end'")
        n_before = cur.fetchone()[0]
        cur.execute(f"DELETE FROM {table} WHERE {col}=?", ("song_end",))
        n_del = cur.rowcount
        print(f"  ✓ {table}: {n_before} 行存在, delete {n_del} 行")

    conn.commit()

    # ===== verify =====
    print("\n=== verify ===")
    cur.execute("""
        SELECT achievement_id, achieved, achieved_at FROM achievement_stats
        WHERE achievement_id IN ('streak_1','streak_3','streak_7','streak_14',
                                  'streak_30','streak_100','night_owl','song_end','first_log')
        ORDER BY achievement_id
    """)
    print("  achievement_stats:")
    for row in cur.fetchall():
        print(f"    {row}")
    cur.execute("SELECT id, name FROM achievements WHERE id='song_end'")
    row = cur.fetchone()
    print(f"  song_end in achievements: {'仍存在 ⚠️' if row else '已删 ✓'}")
    conn.close()
    print("\n✅ Phase 2 final 完成: night_owl 改 20:00 + streak_1/3 unlock + song_end 删")


if __name__ == "__main__":
    main()