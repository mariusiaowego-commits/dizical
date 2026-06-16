"""
V2.6+ (2026-06-16 17:30) DELETE song_end + comeback badge (destructive).

用户 ack: 'song_end 算了不用了 删掉吧' + 'comeback 不要了 删掉吧'.

destructive 影响 (报备):
- 删 2 行 achievements (song_end + comeback)
- 删 2 行 achievement_badges (依赖 achievement_id cascade, 但 SQLite 默认无 FK,
  显式 DELETE)
- 删 2 PNG (src/kid_app/static/badges/song_end.png + comeback.png)

git 仍在 (PR 提交历史, 找得回来). PNG 在 git 也有 (e25dba3+ 等 commit).

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/delete_badge_v2.6.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"
STATIC_DIR = Path(__file__).parent / "static" / "badges"

DELETED_BADGES = ["song_end", "comeback"]


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    print("=== DELETE song_end + comeback (destructive) ===")
    for bid in DELETED_BADGES:
        # 1. 删 achievement_stats (先删, 避免 FK constraint)
        cur.execute("DELETE FROM achievement_stats WHERE achievement_id=?", (bid,))
        n_stats = cur.rowcount

        # 2. 删 achievement_badges
        cur.execute("DELETE FROM achievement_badges WHERE achievement_id=?", (bid,))
        n_bdg = cur.rowcount

        # 3. 删 achievements
        cur.execute("DELETE FROM achievements WHERE id=?", (bid,))
        n_ach = cur.rowcount

        # 4. 删 PNG 文件 (rc 失败不报错)
        png = STATIC_DIR / f"{bid}.png"
        png_removed = False
        if png.exists():
            png.unlink()
            png_removed = True

        print(f"  ✓ {bid}: achievements {n_ach} / badges {n_bdg} / stats {n_stats} 删, PNG {'删' if png_removed else '无'}")

    conn.commit()
    conn.close()
    print(f"\n✅ {len(DELETED_BADGES)} badges deleted (song_end + comeback)")


if __name__ == "__main__":
    main()