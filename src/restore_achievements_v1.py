"""
恢复 V1 era achievements 表 (2026-06-16 事故恢复).

背景: tests/conftest.py 之前 V2.3 改造时加了 '每次 session 重置表结构'
逻辑 (DROP 3 张 badge 表), worktree 跟主仓共用同一份 db, 导致 6-16 中午
跑 pytest 时 achievements/stats/badges 3 张表被清空.

修法: 本脚本只 INSERT OR IGNORE 38 行 V1 era standard badge 定义,
不 DROP 任何表, 不 DELETE 任何行, 跑完跟 V1 era 6-09 状态一致.

后续 milestone 自动解锁由 calc_all() 自动触发 (grade_1~10 + 8 milestone
已在 PR #86 合入代码).

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/restore_achievements_v1.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"

# V1 era 38 行 (从 migrate_achievements.py line 23-250 提取, 6-09 拍板)
# 包含 grade_1~10 + streak_1/3/7/14/30/100 + total_300/600/1000 + first_log + all_items
# + double + top1/2/3 + week_champ + full_month + lucky_61_2026~2030
ACHIEVEMENTS = [
    # ── 赛季型 (seasonal, 实时计算) ──
    {"id": "total_60", "name": "小水滴", "type": "突破", "category": "seasonal",
     "stat_logic": "当月累计练习超过60分钟（自然月）",
     "description": "小水滴嗒嗒嗒滴了几十天，把大石头滴穿了。你一个月练满60分钟，小水滴\"嗒嗒嗒\"，把60分钟这关也滴穿啦！",
     "display_format": "time_hours_minutes", "threshold": 60},
    {"id": "week_champ", "name": "绕梁七日", "type": "巅峰", "category": "seasonal",
     "stat_logic": "本周（stage_start→stage_end）练习时长超过上周",
     "description": "古代有个姐姐叫韩娥，她唱歌太好听了，唱完了声音还在房梁上绕了三天才肯走——你练笛子超过上周的自己，说明你的笛声也能绕梁啦！🎵",
     "display_format": "minutes", "threshold": None},
    {"id": "full_month", "name": "刮目相看", "type": "巅峰", "category": "seasonal",
     "stat_logic": "本月练习时长超过上月（自然月）",
     "description": "古代有个叫吕蒙的大哥哥，没时间读书，后来开始每天读一点点...",
     "display_format": "minutes", "threshold": None},
    {"id": "top1", "name": "情有独钟", "type": "突破", "category": "seasonal",
     "stat_logic": "当月练习时长第1名的科目",
     "description": "古代有个下棋很厉害的人叫奕秋...",
     "display_format": "top_items", "threshold": None},
    # ── 里程碑达成型 (milestone) ──
    {"id": "streak_1", "name": "初试啼声", "type": "突破", "category": "milestone",
     "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥1 天",
     "description": "开始你的练习之旅！", "display_format": "days", "threshold": 1},
    {"id": "streak_3", "name": "小火焰", "type": "执着", "category": "milestone",
     "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥3 天",
     "description": "连续打卡，笛子都被你吹服了！", "display_format": "days", "threshold": 3},
    {"id": "streak_7", "name": "周冠军", "type": "执着", "category": "milestone",
     "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥7 天",
     "description": "坚持一周，你就是时间管理大师！", "display_format": "days", "threshold": 7},
    {"id": "streak_14", "name": "双周传说", "type": "执着", "category": "milestone",
     "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥14 天",
     "description": "两周坚持，传说初现！", "display_format": "days", "threshold": 14},
    {"id": "streak_30", "name": "月度王者", "type": "晋级", "category": "milestone",
     "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥30 天",
     "description": "整月打卡，王者风范！", "display_format": "days", "threshold": 30},
    {"id": "streak_100", "name": "百日传奇", "type": "晋级", "category": "milestone",
     "stat_logic": "从今天往前数，连续每天练习 ≥10 分钟的天数 ≥100 天",
     "description": "百日坚持，传奇诞生！", "display_format": "days", "threshold": 100},
    {"id": "total_300", "name": "五小时战士", "type": "突破", "category": "milestone",
     "stat_logic": "所有 daily_practices.total_minutes 累加 ≥300 分钟",
     "description": "五小时积累，小试牛刀！", "display_format": "time_hours_minutes", "threshold": 300},
    {"id": "total_600", "name": "十小时大师", "type": "巅峰", "category": "milestone",
     "stat_logic": "所有 daily_practices.total_minutes 累加 ≥600 分钟",
     "description": "十小时磨砺，大师初成！", "display_format": "time_hours_minutes", "threshold": 600},
    {"id": "total_1000", "name": "千分钟传奇", "type": "巅峰", "category": "milestone",
     "stat_logic": "所有 daily_practices.total_minutes 累加 ≥1000 分钟",
     "description": "千分钟传奇前无古人！", "display_format": "time_hours_minutes", "threshold": 1000},
    {"id": "first_log", "name": "第一声", "type": "突破", "category": "milestone",
     "stat_logic": "完成第一次练习", "description": "第一次吹响你的笛子！",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "all_items", "name": "全能选手", "type": "神秘", "category": "milestone",
     "stat_logic": "一天内完成老师布置的所有练习科目",
     "description": "一天内完成老师布置的所有练习科目！", "display_format": "achieved_flag", "threshold": None},
    {"id": "double", "name": "加练狂魔", "type": "执着", "category": "milestone",
     "stat_logic": "同一天两次练习",
     "description": "同一天两次练习，卷王诞生！", "display_format": "days", "threshold": None},
    {"id": "top2", "name": "TOP2 卷王", "type": "突破", "category": "milestone",
     "stat_logic": "累计时长第2名",
     "description": "练习时长第二多，同样出色！", "display_format": "top_items", "threshold": None},
    {"id": "top3", "name": "TOP3 新星", "type": "突破", "category": "milestone",
     "stat_logic": "累计时长第3名",
     "description": "练习时长第三名，新星升起！", "display_format": "top_items", "threshold": None},
    # ── 考级 (grade) ──
    {"id": "grade_1", "name": "小笛芽", "type": "段位", "category": "milestone",
     "stat_logic": "考取 1 级", "description": "传说竹林里最嫩的那根竹笋...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_2", "name": "音符精灵", "type": "段位", "category": "milestone",
     "stat_logic": "考取 2 级", "description": "八仙里的韩湘子...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_3", "name": "旋律萤火", "type": "段位", "category": "milestone",
     "stat_logic": "考取 3 级", "description": "车胤小时候家里穷...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_4", "name": "风铃花仙", "type": "段位", "category": "milestone",
     "stat_logic": "考取 4 级", "description": "传说花木兰从军回来...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_5", "name": "星光灵狐", "type": "段位", "category": "milestone",
     "stat_logic": "考取 5 级", "description": "《聊斋》里有个狐仙...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_6", "name": "月影独角兽", "type": "段位", "category": "milestone",
     "stat_logic": "考取 6 级", "description": "嫦娥奔月后...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_7", "name": "云端笛侠", "type": "段位", "category": "milestone",
     "stat_logic": "考取 7 级", "description": "李白说危楼高百尺...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_8", "name": "凤鸣仙子", "type": "段位", "category": "milestone",
     "stat_logic": "考取 8 级", "description": "传说萧史吹箫引凤...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_9", "name": "龙吟天女", "type": "段位", "category": "milestone",
     "stat_logic": "考取 9 级", "description": "敦煌壁画里的飞天...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "grade_10", "name": "天籁笛仙", "type": "段位", "category": "milestone",
     "stat_logic": "考取 10 级", "description": "伯牙弹琴，钟子期...",
     "display_format": "achieved_flag", "threshold": None},
    # ── 闻鸡起舞系列 (3 个) ──
    {"id": "early_riser", "name": "闻鸡起舞", "type": "突破", "category": "seasonal",
     "stat_logic": "首次达成 CST 12:00 之前练习",
     "description": "很久很久以前，有两个好朋友，一个叫祖逖，一个叫刘琨...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "little_chick_commander", "name": "小鸡指挥官", "type": "突破", "category": "seasonal",
     "stat_logic": "首次达成 CST 17:00 之前练习",
     "description": "很久很久以前...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "first_to_act", "name": "先声夺人", "type": "突破", "category": "seasonal",
     "stat_logic": "首次达成 CST 12:00 之前练习 (含历史)",
     "description": "很久很久以前...",
     "display_format": "achieved_flag", "threshold": None},
    # ── 额外: night_owl, one_breath, song_end, comeback ──
    {"id": "night_owl", "name": "夜猫子", "type": "突破", "category": "milestone",
     "stat_logic": "晚上 9 点后练习",
     "description": "夜深了还在练...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "one_breath", "name": "一口气", "type": "突破", "category": "milestone",
     "stat_logic": "单次练习 ≥10 分钟",
     "description": "一口气吹了 10 分钟...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "song_end", "name": "曲终人散", "type": "突破", "category": "milestone",
     "stat_logic": "完整吹完一首曲子",
     "description": "曲终了...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "comeback", "name": "东山再起", "type": "突破", "category": "milestone",
     "stat_logic": "断练 7 天后恢复",
     "description": "离开又回来...",
     "display_format": "achieved_flag", "threshold": None},
    # ── 6.1 儿童节 (lucky_61_2026~2030) ──
    # 2026-07-01 拍板: 改为 milestone. 历史上对应年份 06-01 当天练过 → 永久解锁.
    {"id": "lucky_61_2026", "name": "幸运六一节", "type": "突破", "category": "milestone",
     "stat_logic": "2026-06-01 练习", "description": "六一节...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "lucky_61_2027", "name": "鱼跃闻韶", "type": "突破", "category": "milestone",
     "stat_logic": "2027-06-01 练习", "description": "孔子在齐国...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "lucky_61_2028", "name": "安知非鱼", "type": "突破", "category": "milestone",
     "stat_logic": "2028-06-01 练习", "description": "庄子和惠子...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "lucky_61_2029", "name": "浣溪童乐", "type": "突破", "category": "milestone",
     "stat_logic": "2029-06-01 练习", "description": "辛弃疾...",
     "display_format": "achieved_flag", "threshold": None},
    {"id": "lucky_61_2030", "name": "逍遥游鱼", "type": "突破", "category": "milestone",
     "stat_logic": "2030-06-01 练习", "description": "叶公好龙...",
     "display_format": "achieved_flag", "threshold": None},
]


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 1. 确保表存在 (CREATE IF NOT EXISTS)
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS achievements (
            id                TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            type              TEXT NOT NULL,
            category          TEXT NOT NULL DEFAULT 'milestone',
            stat_logic        TEXT NOT NULL,
            description       TEXT NOT NULL,
            display_format    TEXT NOT NULL,
            threshold         INTEGER,
            unlocked_template TEXT,
            placeholder       TEXT,
            locked_template   TEXT,
            sort_order        INTEGER DEFAULT 0,
            seasonal_type     TEXT DEFAULT 'monthly',
            cond_text         TEXT,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS achievement_stats (
            achievement_id TEXT PRIMARY KEY,
            achieved       TEXT NOT NULL DEFAULT 'N',
            achieved_at    DATETIME,
            raw_stats      TEXT NOT NULL DEFAULT '{}',
            computed_value INTEGER
        );
        CREATE TABLE IF NOT EXISTS achievement_badges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            achievement_id  TEXT NOT NULL,
            url             TEXT NOT NULL,
            is_locked       INTEGER NOT NULL DEFAULT 0,
            version         INTEGER NOT NULL DEFAULT 1,
            is_current      INTEGER NOT NULL DEFAULT 1,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. INSERT OR IGNORE (idempotent, 不覆盖现有)
    inserted = 0
    skipped = 0
    for a in ACHIEVEMENTS:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO achievements
                  (id, name, type, category, stat_logic, description,
                   display_format, threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (a["id"], a["name"], a["type"], a["category"], a["stat_logic"],
                  a["description"], a["display_format"], a.get("threshold")))
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"⚠️  跳过 {a['id']}: {e}")
    conn.commit()

    print(f"✓ 尝试 insert {len(ACHIEVEMENTS)} 行")
    print(f"  新增: {inserted}")
    print(f"  已存在 (跳过): {skipped}")

    # 3. verify
    cur.execute("SELECT COUNT(*) FROM achievements")
    n = cur.fetchone()[0]
    print(f"✓ achievements 表现在 {n} 行")
    conn.close()


if __name__ == "__main__":
    main()
