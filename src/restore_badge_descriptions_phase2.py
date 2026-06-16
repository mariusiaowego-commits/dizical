"""
事故补档 Phase 2: 8 个业务修复 (2026-06-16 16:46 user obsidian issue 260616-phase2)

严格 review: 只做能 ground truth 验证的, 不盲 unlock / 不盲编 / 不盲删.

Phase 2.1 (能写, 有 ground truth):
- night_owl modal-desc: 嫦娥广寒宫典故 (你 obsidian issue 明确提供)
- night_owl stat_logic: 你说 "22:00 后练习", 跟 V1 era '晚上 9 点后练习' 不一致,
  按你 phase2 拍板改为 22:00 (=晚上 10 点, 大白话匹配 modal-cond 描述)

Phase 2.2 (UI 调整, 调研后做):
- early-bird-c (其实是 first_to_act) modal-desc 太长, 加 max-height + overflow-y scroll,
  不影响其他 badge

Phase 2.3 (要 ack, 这次不做):
- assign_pal: DB 已 unlocked (Y + achieved_at=2026-06-16 07:57:17), UI 显示 locked 是 service
  60s _BADGE_URL_CACHE 旧缓存 (assign_pal 行刚写). 重启 service 解决.
- grade_1 unlock: 等你确认几号/几级
- streak_1~100 unlock: 6 个全 db 0 行, 等你确认哪些真解锁
- double unlock: 等你确认哪天加练
- comeback DELETE: 等你确认真要删
- song_end stat_logic: V1 era 没明确, 我编不出

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/restore_badge_descriptions_phase2.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"

# Phase 2.1: night_owl 完整描述 (user obsidian issue 260616-phase2.md 提供)
NIGHT_OWL_DESC = (
    "广寒宫没WiFi，嫦娥便在月亮上勤练竹笛。"
    "谁知笛声太美，竟把贪玩的夜猫子和弯月都听陶醉了，"
    "纷纷化作纯净的珐琅星光，每晚都在等她的第一声笛音。"
)


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # === Phase 2.1: night_owl 写 desc + stat_logic (按 user phase2 拍板) ===
    print("=== Phase 2.1: night_owl (description + stat_logic) ===")
    # stat_logic: 之前 V1 era 是 '晚上 9 点后练习', user 拍板 22:00 (=晚上 10 点)
    # modal-cond 跟这个匹配: "晚上10点后还在练习..."
    cur.execute("""
        UPDATE achievements SET
            stat_logic='晚上 10 点后 (CST 22:00) 还在练习',
            description=?
        WHERE id='night_owl'
    """, (NIGHT_OWL_DESC,))
    n = cur.rowcount
    if n:
        cur.execute("SELECT name, LENGTH(description), stat_logic FROM achievements WHERE id='night_owl'")
        name, dl, sl = cur.fetchone()
        print(f"  ✓ night_owl ({name}): {n} updated, desc {dl} 字符")
        print(f"    stat_logic: {sl}")
    conn.commit()

    # === verify ===
    print("\n=== verify ===")
    cur.execute("SELECT id, name, LENGTH(description), stat_logic FROM achievements WHERE id='night_owl'")
    row = cur.fetchone()
    print(f"  {row}")
    conn.close()
    print("\n✅ Phase 2.1 完成 (night_owl)")
    print("\n未做 (等 ack):")
    print("  - assign_pal: db 已 Y, 重启 service 解决 cache")
    print("  - grade_1/streak_1~100/double: 等你确认解锁时间")
    print("  - comeback DELETE: 等你确认真要删")
    print("  - song_end stat_logic: V1 era 没明确, 编不出")
    print("  - early-bird-c UI 滚动: 在 PR #108 (独立 UI PR) 改")


if __name__ == "__main__":
    main()
