"""
V2.6 (2026-06-16) feat/badge-achieved-at-override:
通用字段 + UI + calc, 让"表彰型/纪念章型"徽章不 calc 直接 unlocked.

背景:
- V2 era 早期 (PR #101) 设计 unlock_strategy 字段 (immediate/calc), immediate 是纪念章.
- 但 badges_page/achievements_page 走 calc_all(), 不读 stats.achieved for unlock_strategy='immediate',
  所以 assign_pal db Y 但 UI locked (你 2026-06-16 反馈).
- 你 issue 拍板 (grade 1-10 + 纪念章场景): 以后会有很多表彰型徽章, 都**不走 calc**.
- 修法: 加通用 `achieved_at_override` 字段, 跟 unlock_strategy='immediate' 二选一都 OK,
  但 achieved_at_override 语义更清晰 (含具体解锁时间).

修法:
1. DB: achievements 加列 achieved_at_override (TEXT, nullable)
2. Calc: _calc_milestone 加 grade_X + achieved_at_override 检查
3. 路由: badges_page / achievements_page 路由检查 override/immediate,
   直接返 achieved=Y (跳过 calc_all)
4. UI: 表单 (config-badge.html) 加 1 个 datetime input, modal-cond 显示 override 时间
5. UI: badges.html + achievements.html modal-cond 模板加 ${esc(d.achieved_at)} 显示
6. Migration: src/migrate_add_achieved_at_override.py (idempotent)
7. Tests: test_achieved_at_override.py 5+ cases

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/migrate_add_achieved_at_override.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def _has_column(conn, table, col):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


def _has_table(conn, table):
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return cur.fetchone() is not None


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))

    # 1. achievements 表: 加 achieved_at_override 列 (跟 cond_text 同 pattern)
    if _has_table(conn, "achievements"):
        if not _has_column(conn, "achievements", "achieved_at_override"):
            print("achievements 表: 添加 achieved_at_override 列")
            conn.execute("""
                ALTER TABLE achievements
                ADD COLUMN achieved_at_override TEXT
            """)
        else:
            print("achievements 表: achieved_at_override 列已存在 (幂等)")
    else:
        print("⚠️ achievements 表不存在 (worktree 新 db?), 等 conftest 创表后跑")

    conn.commit()

    # 2. verify
    if _has_table(conn, "achievements"):
        cur = conn.execute("PRAGMA table_info(achievements)")
        cols = [row[1] for row in cur.fetchall()]
        if "achieved_at_override" in cols:
            print(f"✓ achievements 表新列 verified: achieved_at_override 在, 总 {len(cols)} 列")
        else:
            print(f"✗ achievements 表新列未生效")

    conn.close()
    print("\n✅ Migration 完成 (achievements 加 achieved_at_override 列)")


if __name__ == "__main__":
    main()