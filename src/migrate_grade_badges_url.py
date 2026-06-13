"""
迁移: 修正 grade_1~10 的 achievement_badges.url 后缀
─────────────────────────────────────────────────────
背景 (2026-06-13 发现):
- migrate_achievements.py:414 写 url 时写死 f"/static/badges/{aid}.png" (无后缀)
- 实际磁盘文件叫 grade_N-u.png / grade_N-l.png (bd7027b commit 起的命名)
- 结果: 20 行 grade_* url 全部 404 → 前端 fallback medal_badge.png
  → "考级 1-10 的漂亮图全没了" 现象

修复:
- is_locked=0 行 url: grade_N.png → grade_N-u.png
- is_locked=1 行 url: grade_N.png → grade_N-l.png
- 只动 is_current=1 的行 (历史版本不动)
- 不动磁盘文件 (-u/-l.png 都在)

幂等: 二次运行检测到无改动直接跳过.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)

    # 查改动前状态
    rows = conn.execute(
        "SELECT id, achievement_id, is_locked, url FROM achievement_badges "
        "WHERE achievement_id LIKE 'grade_%' AND is_current = 1 "
        "ORDER BY achievement_id, is_locked"
    ).fetchall()
    print(f"=== 修复前 ({len(rows)} 行) ===")
    for r in rows:
        print(f"  id={r[0]:3d}  {r[1]:8s}  is_locked={r[2]}  url={r[3]}")

    # 改 unlocked 行 (-u.png)
    n_unlocked = conn.execute(
        "UPDATE achievement_badges "
        "SET url = REPLACE(url, 'grade_' || SUBSTR(achievement_id, 7) || '.png', "
        "                   'grade_' || SUBSTR(achievement_id, 7) || '-u.png') "
        "WHERE achievement_id LIKE 'grade_%' AND is_locked = 0 AND is_current = 1"
    ).rowcount

    # 改 locked 行 (-l.png)
    n_locked = conn.execute(
        "UPDATE achievement_badges "
        "SET url = REPLACE(url, 'grade_' || SUBSTR(achievement_id, 7) || '.png', "
        "                   'grade_' || SUBSTR(achievement_id, 7) || '-l.png') "
        "WHERE achievement_id LIKE 'grade_%' AND is_locked = 1 AND is_current = 1"
    ).rowcount

    conn.commit()
    print(f"\n=== 改动: unlocked={n_unlocked} 行, locked={n_locked} 行 ===")

    # 验证: 改完后磁盘文件存在 + 二次跑会 0 改动
    rows_after = conn.execute(
        "SELECT id, achievement_id, is_locked, url FROM achievement_badges "
        "WHERE achievement_id LIKE 'grade_%' AND is_current = 1 "
        "ORDER BY achievement_id, is_locked"
    ).fetchall()
    print(f"\n=== 修复后 ({len(rows_after)} 行) ===")
    all_ok = True
    static_dir = Path(__file__).parent / "kid_app" / "static"
    for r in rows_after:
        aid, url, is_locked = r[1], r[3], r[2]
        disk = static_dir / url.replace("/static/", "")
        exists = disk.exists()
        flag = "✓" if exists else "✗ MISSING"
        if not exists:
            all_ok = False
        print(f"  {flag}  {aid:8s}  is_locked={is_locked}  url={url}")

    print()
    if all_ok:
        print("✅ 全部 url 正确指向磁盘文件")
    else:
        print("❌ 有 url 找不到磁盘文件, 请检查")

    # 查还有没有 grade_*.png (无 -u/-l) 残留
    leftover = conn.execute(
        "SELECT COUNT(*) FROM achievement_badges "
        "WHERE achievement_id LIKE 'grade_%' "
        "  AND (url LIKE '%/grade_%.png' AND url NOT LIKE '%-u.png' AND url NOT LIKE '%-l.png')"
    ).fetchone()[0]
    print(f"\n无后缀残留: {leftover} 行 (期望 0)")

    conn.close()


if __name__ == "__main__":
    main()