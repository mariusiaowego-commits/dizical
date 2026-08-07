"""
Migration: fix 3 已知脏数据 — sprint 26080701 (2026-08-07)

修复项:
1. achievement_badges 表 streak_7 url → /static/badges/streak_7.png
   (云端 8-03 写入 streak_7_v1.png 但文件从未存在, 8-05 commit 95bc163 已修本地)
2. achievements 表三个早练 badge 的 description 字段:
   - early_riser (threshold 20) → "晚上八点前"
   - little_chick_commander (threshold 17) → "下午五点前"
   - first_to_act (threshold 12) → "中午十二点前"
   (8-03 三段 desc 复制粘贴漏改, 都写成"晚上八点前")

执行模式 (互斥):
    python src/migrate_fix_badges_260807.py --target=local    # 改本地 SQLite data/dizi.db
    python src/migrate_fix_badges_260807.py --target=cloud    # 改云端 MySQL (用 ~/.dizical/.env)

idempotent: 多次跑结果一致 (用 WHERE url=? / WHERE id=? AND description LIKE '...' 限定)
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"
BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"

# 三个 desc 文案差异化 (按 calc 阈值 20/17/12, 跟 achievement_definitions.py:717 同步)
DESC_EARLY_RISER = (
    "很久很久以前，有两个好朋友，一个叫**祖逖**，一个叫**刘琨**。\n"
    "他们住在一起，每天睡同一张床。有一天半夜，外面突然传来——\n\n"
    "**\"喔喔喔——！\"**\n\n"
    "一只鸡在叫。\n\n"
    "刘琨迷迷糊糊翻了个身，想继续睡。\n"
    "但祖逖一下子坐起来，眼睛亮亮的，说：\n"
    "> **\"这不是坏声音！这是在叫我们起床呢！\"**\n\n"
    "别人都觉得半夜鸡叫很烦人，祖逖却觉得——这是在催我呀！于是他拉着刘琨跑出门，"
    "在黑漆漆的夜里，拿起剑就开始练。一直练到天亮。\n\n"
    "后来，他们每天都这样。鸡一叫，就起来练。刮风下雨也不停。\n"
    "再后来，两个人都变成了特别厉害的大将军。\n\n"
    "---\n\n"
    "那声鸡叫，别人听到的是——\"好吵，还想睡。\"\n"
    "祖逖听到的是——**\"现在就可以开始了！\"**\n\n"
    "---\n\n"
    "你拿着竹笛，在晚上八点前吹响第一个音——\n"
    "就像祖逖听到鸡叫就跳起来一样。\n"
    "别人觉得还早呢，你已经开始了。\n"
    "**所以这枚勋章叫「闻鸡起笛」。**\n"
    "别人等天亮，你等笛响。"
)

DESC_LITTLE_CHICK = (
    "鸡窝里住着一只小鸡，它每天负责叫大家起床。\n"
    "小鸡不像大公鸡那么洪亮，它的嗓音细细的，像竹笛的高音区——清脆又带点奶声。\n"
    "但它特别准时：太阳还没露脸，它就开始叫了。\n"
    "别的动物嫌它吵，它就歪着脑袋解释：\"我不是在催你们嘛——我是怕你们错过最美的晨光呀！\"\n\n"
    "---\n\n"
    "你拿着竹笛，在下午五点前吹响第一个音——\n"
    "天还没黑透呢，笛声就先到了。\n"
    "别人还在吃晚饭准备休息，你已经吹完了今天的练习。\n"
    "**所以这枚勋章叫「小鸡指挥官」。**\n"
    "小鸡一叫，全场都醒。"
)

DESC_FIRST_TO_ACT = (
    "每天中午十二点，学校的钟声响了——别的同学这才想起要练琴。\n"
    "可是你呢？笛子已经在手上了，第一个音已经吹响了。\n"
    "十二点的阳光照进窗户，笛膜微微振动，音符像小鹿一样跳出来——\n"
    "别人还在翻乐谱，你已经把曲子吹完一遍啦！\n\n"
    "---\n\n"
    "你拿着竹笛，在中午十二点前吹响第一个音——\n"
    "别人还在想\"要不要练呢\"，你已经吹完第一段啦。\n"
    "先声夺人，就是这个意思：你的笛声比所有人先到。\n"
    "**所以这枚勋章叫「先声夺人」。**\n"
    "十二点还没到，你已经领先了一整个下午。"
)

DESC_MAP = {
    "early_riser": DESC_EARLY_RISER,
    "little_chick_commander": DESC_LITTLE_CHICK,
    "first_to_act": DESC_FIRST_TO_ACT,
}


def _backup_local(rows_for_backup: list[str]) -> Path:
    """把要改的行 dump 到 data/backups/ 让 dad 可回滚."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    p = BACKUP_DIR / f"badges-260807-pre-migrate-{ts}.txt"
    with open(p, "w", encoding="utf-8") as f:
        f.write("# Pre-migrate snapshot (sprint 26080701)\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write("# Format: table | key | old_value\n")
        for line in rows_for_backup:
            f.write(line + "\n")
    return p


def _apply_local() -> None:
    """改本地 SQLite. idempotent — WHERE 限定原值."""
    if not DB_PATH.exists():
        print(f"DB 不存在 ({DB_PATH}), 跳过")
        return
    conn = sqlite3.connect(str(DB_PATH))
    try:
        # 1. streak_7 url 修复
        cur = conn.execute(
            "SELECT url FROM achievement_badges WHERE achievement_id='streak_7' AND is_current=1"
        )
        rows = cur.fetchall()
        old_url = rows[0][0] if rows else "(无)"
        if old_url != "/static/badges/streak_7.png":
            _backup_local([(
                f"achievement_badges | streak_7 | url={old_url} | "
                f"is_current=1 → /static/badges/streak_7.png"
            )])
            conn.execute(
                "UPDATE achievement_badges SET url='/static/badges/streak_7.png' "
                "WHERE achievement_id='streak_7' AND is_current=1 "
                "AND url='/static/badges/streak_7_v1.png'"
            )
            conn.commit()
            print(f"  streak_7 url: {old_url} → /static/badges/streak_7.png")
        else:
            print(f"  streak_7 url 已是 streak_7.png, 跳过")

        # 2. 三个 desc 文案修复
        for aid, new_desc in DESC_MAP.items():
            cur = conn.execute(
                "SELECT description FROM achievements WHERE id=?", (aid,)
            )
            row = cur.fetchone()
            old_desc = row[0] if row else None
            if old_desc and "晚上八点前" in old_desc:
                _backup_local([(
                    f"achievements | {aid} | description={old_desc[:80]}... → <{len(new_desc)} chars new>"
                )])
                conn.execute(
                    "UPDATE achievements SET description=? WHERE id=?",
                    (new_desc, aid),
                )
                conn.commit()
                print(f"  {aid} description: 已更新 (407字 → {len(new_desc)}字)")
            else:
                print(f"  {aid} description 不含旧模板, 跳过")
    finally:
        conn.close()
    print("\n本地 SQLite 修复完成")


def _apply_cloud() -> None:
    """改云端 MySQL. 用 pymysql 直连 (DATABASE_URL 从 ~/.dizical/.env 读)."""
    env_path = Path.home() / ".dizical" / ".env"
    if not env_path.exists():
        print(f"~/.dizical/.env 不存在, 无法连云")
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip().strip('"').strip("'")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or not db_url.startswith("mysql"):
        print(f"DATABASE_URL 未设或非 mysql: {db_url!r}")
        sys.exit(1)

    import pymysql
    from urllib.parse import urlparse, unquote
    parsed = urlparse(db_url.replace("mysql+pymysql://", "mysql://"))
    user = unquote(parsed.username or "")
    pwd = unquote(parsed.password or "")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 3306
    db = parsed.path.lstrip("/")

    conn = pymysql.connect(
        host=host, port=port, user=user, password=pwd, database=db,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, url, is_current, version FROM achievement_badges "
                "WHERE achievement_id='streak_7'"
            )
            rows = cur.fetchall()
            print(f"  云端 streak_7 当前有 {len(rows)} 条:")
            for r in rows:
                print(f"    {r}")
            cur.execute(
                "SELECT id, url FROM achievement_badges "
                "WHERE achievement_id='streak_7' AND is_current=1"
            )
            row = cur.fetchone()
            if row and row["url"] != "/static/badges/streak_7.png":
                cur.execute(
                    "UPDATE achievement_badges SET url='/static/badges/streak_7.png' "
                    "WHERE id=%s",
                    (row["id"],),
                )
                conn.commit()
                print(f"  streak_7 url: {row['url']} → /static/badges/streak_7.png (id={row['id']})")
            else:
                print(f"  streak_7 url 已是 streak_7.png, 跳过")

            for aid, new_desc in DESC_MAP.items():
                cur.execute(
                    "SELECT description FROM achievements WHERE id=%s", (aid,)
                )
                row = cur.fetchone()
                old_desc = row["description"] if row else None
                if old_desc and "晚上八点前" in old_desc:
                    cur.execute(
                        "UPDATE achievements SET description=%s WHERE id=%s",
                        (new_desc, aid),
                    )
                    conn.commit()
                    print(f"  {aid} description: 已更新 ({len(old_desc)}字 → {len(new_desc)}字)")
                else:
                    print(f"  {aid} description 不含旧模板, 跳过 (已是新文案或缺失)")
    finally:
        conn.close()
    print("\n云端 MySQL 修复完成")


def main():
    parser = argparse.ArgumentParser(description="Fix 3 badges data bugs (sprint 26080701)")
    parser.add_argument("--target", choices=["local", "cloud"], required=True,
                        help="local=改本地 SQLite; cloud=改云端 MySQL (走 ~/.dizical/.env)")
    args = parser.parse_args()

    print(f"=== migrate_fix_badges_260807.py --target={args.target} ===")
    if args.target == "local":
        _apply_local()
    else:
        _apply_cloud()


if __name__ == "__main__":
    main()