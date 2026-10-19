"""sprint badge-batch-261017 (2026-10-17): 练习记录型 milestone calc 的测试。

覆盖 src/achievement_definitions.py 的 PRACTICE_BADGE_RULES / _calc_practice_badge。
每条规则至少一正一反 (达成 / 未达成), 并断言 achieved_at = **首次达成日**
(_persist_unlocked_milestones 只在 achieved_at 非 None 时落库, 这条断言是防
"灰卡永不解锁" 事故的关键)。

阈值口径见 achievement_definitions.py 规则表上方注释: 门槛在 2026-10-17 按 dad 的
C 方案重设过一次 (整体抬到"刚超过现有记录", 天数口径尽量换成强度口径)。改阈值必须
同步改这里的边界数字, 两边一一对应。
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


DDL = """
    CREATE TABLE achievements (
        id TEXT PRIMARY KEY, name TEXT, type TEXT, category TEXT,
        stat_logic TEXT, description TEXT, display_format TEXT,
        threshold INTEGER, unlocked_template TEXT, placeholder TEXT,
        locked_template TEXT, sort_order INTEGER DEFAULT 0,
        seasonal_type TEXT DEFAULT 'monthly', cond_text TEXT,
        unlock_strategy TEXT DEFAULT 'calc', created_at DATETIME
    );
    CREATE TABLE achievement_stats (
        achievement_id TEXT PRIMARY KEY,
        achieved TEXT NOT NULL DEFAULT 'N',
        achieved_at DATETIME, raw_stats TEXT NOT NULL DEFAULT '{}',
        computed_value INTEGER
    );
    CREATE TABLE daily_practices (
        date TEXT PRIMARY KEY, items TEXT, total_minutes INTEGER,
        created_at DATETIME, practice_at TEXT, behavior_log TEXT
    );
    CREATE TABLE practice_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        practice_date DATE NOT NULL, item_id INTEGER NOT NULL,
        item_name TEXT NOT NULL, duration_minutes INTEGER NOT NULL,
        tempo_note TEXT NOT NULL DEFAULT '', tempo_bpm INTEGER NOT NULL DEFAULT 80,
        content TEXT NOT NULL DEFAULT '', content_source TEXT NOT NULL DEFAULT 'manual',
        is_extra BOOLEAN NOT NULL DEFAULT 0, started_at TEXT,
        created_at DATETIME, version INTEGER NOT NULL DEFAULT 1,
        updated_at DATETIME, reps INTEGER,
        duration_seconds INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE practice_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
        category_id INTEGER, sort_order INTEGER NOT NULL DEFAULT 0,
        is_active BOOLEAN NOT NULL DEFAULT 1, is_archived BOOLEAN NOT NULL DEFAULT 0,
        created_at DATETIME
    );
"""


@pytest.fixture
def conn(tmp_path):
    db = sqlite3.connect(str(tmp_path / "practice_badges.db"))
    db.row_factory = sqlite3.Row
    db.executescript(DDL)
    yield db
    db.close()


@pytest.fixture
def conn_typed(tmp_path):
    """像 MySQL 那样把 DATE 列直接交回 datetime.date 对象。

    生产跑在 MySQL: DATE 列经 pymysql 读出来是 date, 不是字符串。SQLite 默认读字符串,
    所以必须开 PARSE_DECLTYPES 才能把这条类型路径测到 —— 否则 prod-only 的类型 bug
    在测试里永远看不见。
    """
    db = sqlite3.connect(str(tmp_path / "typed.db"),
                         detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    db.executescript(DDL)
    yield db
    db.close()


def sess(conn, d, iid, mins, tempo=80):
    conn.execute(
        "INSERT INTO practice_sessions (practice_date, item_id, item_name, duration_minutes, tempo_bpm) "
        "VALUES (?, ?, ?, ?, ?)", (d, iid, f"item{iid}", mins, tempo))


def day(conn, d, mins):
    conn.execute("INSERT INTO daily_practices (date, total_minutes) VALUES (?, ?)", (d, mins))


def calc(conn, aid, today="2026-10-17"):
    from src.achievement_definitions import _calc_milestone
    return _calc_milestone(
        conn, aid, stats={}, streak=1, total_mins=0, top_items=[],
        has_all_items=False, all_items_achieved_at=None, has_double=False,
        today=date.fromisoformat(today))


# ─── 原语级: single_min / over_min / session_count ─────────────────────────

def test_rep_hui_niangjia_single_min_15(conn):
    """回娘家: 单次 >= 15 分钟 (实测最大 10)"""
    sess(conn, "2026-05-18", 1004, 14)
    assert calc(conn, "rep_hui_niangjia").achieved is False
    sess(conn, "2026-05-20", 1004, 15)
    r = calc(conn, "rep_hui_niangjia")
    assert r.achieved is True and r.achieved_at == "2026-05-20"


def test_rep_saliha_single_min_25(conn):
    """萨丽哈: 单次 >= 25 分钟 (实测最大 18)"""
    sess(conn, "2026-05-22", 1340, 24)
    assert calc(conn, "rep_saliha").achieved is False
    sess(conn, "2026-05-24", 1340, 25)
    assert calc(conn, "rep_saliha").achieved_at == "2026-05-24"


def test_rep_chun_geng_qu_strictly_over_10(conn):
    """> 10 分钟 (不是 >=)"""
    sess(conn, "2026-09-20", 1352, 10)
    assert calc(conn, "rep_chun_geng_qu").achieved is False
    sess(conn, "2026-09-21", 1352, 11)
    assert calc(conn, "rep_chun_geng_qu").achieved_at == "2026-09-21"


def test_rep_moli_hua_session_count_12(conn):
    """茉莉花: 累计 12 段 (两个 item_id 合并计, 实测 6)"""
    for i in range(6):
        sess(conn, f"2026-05-{1 + i:02d}", 1028, 3)
    for i in range(5):
        sess(conn, f"2026-06-{1 + i:02d}", 1032, 3)
    assert calc(conn, "rep_moli_hua").achieved is False        # 累计 11 段
    sess(conn, "2026-06-06", 1032, 3)
    assert calc(conn, "rep_moli_hua").achieved_at == "2026-06-06"


# ─── two_day_sum / day_sessions / days_and_total ───────────────────────────

def test_rep_caicha_pudie_two_consecutive_days_40(conn):
    """采茶扑蝶: 连续两天累计 >= 40 分钟 (实测 32); 不连续不算"""
    sess(conn, "2026-04-24", 1026, 20)
    sess(conn, "2026-04-26", 1026, 19)          # 隔了一天
    assert calc(conn, "rep_caicha_pudie").achieved is False
    sess(conn, "2026-04-25", 1026, 20)
    r = calc(conn, "rep_caicha_pudie")
    assert r.achieved is True and r.achieved_at == "2026-04-25"


def test_rep_xiao_kanxi_day_sessions_5(conn):
    """关东小看戏: 同一天分段练满 5 段 (实测 3)"""
    for _ in range(4):
        sess(conn, "2026-09-08", 1351, 3)
    assert calc(conn, "rep_xiao_kanxi").achieved is False
    sess(conn, "2026-09-08", 1351, 3)
    assert calc(conn, "rep_xiao_kanxi").achieved_at == "2026-09-08"


def test_rep_xizang_wuqu_day_sessions_10(conn):
    """雪域弦子跳: 同一天 10 段 (实测 8)"""
    for _ in range(9):
        sess(conn, "2026-07-29", 1346, 2)
    assert calc(conn, "rep_xizang_wuqu").achieved is False
    sess(conn, "2026-07-29", 1346, 2)
    assert calc(conn, "rep_xizang_wuqu").achieved_at == "2026-07-29"


def test_rep_zi_zhu_diao_days_and_total(conn):
    """紫竹调: 20 天 且 累计 180 分钟 (两个条件都要, 实测 16 天/112 分)"""
    for i in range(19):                          # 19 天 190 分钟 → 天数不够
        sess(conn, f"2026-08-{i + 1:02d}", 1348, 10)
    assert calc(conn, "rep_zi_zhu_diao").achieved is False
    sess(conn, "2026-08-20", 1348, 5)            # 第 20 天
    assert calc(conn, "rep_zi_zhu_diao").achieved_at == "2026-08-20"


def test_rep_zi_zhu_diao_minutes_also_needed(conn):
    """天数够了但总时长不够 → 仍不达成"""
    for i in range(1, 21):
        sess(conn, f"2026-08-{i:02d}", 1348, 8)   # 20 天 / 160 分钟
    assert calc(conn, "rep_zi_zhu_diao").achieved is False


def test_rep_xin_qu_kai_huang_two_weeks_every_day(conn):
    """新曲开荒: 首练起 14 天内练满 14 天 (实测最多 13)"""
    d = date(2026, 9, 1)
    for i in range(13):
        sess(conn, (d + timedelta(days=i)).isoformat(), 1352, 5)
    assert calc(conn, "rep_xin_qu_kai_huang").achieved is False
    sess(conn, "2026-09-14", 1352, 5)
    assert calc(conn, "rep_xin_qu_kai_huang").achieved_at == "2026-09-14"


# ─── 技巧组 ────────────────────────────────────────────────────────────────

def test_tech_chang_yin_single_min_20(conn):
    """深潭潜龙息: 长音单次 >= 20 分钟 (实测 17)"""
    sess(conn, "2026-05-03", 1034, 19)
    assert calc(conn, "tech_chang_yin").achieved is False
    sess(conn, "2026-05-05", 1034, 20)
    assert calc(conn, "tech_chang_yin").achieved_at == "2026-05-05"


def test_tech_dan_tu_days_and_tempo_120(conn):
    """单吐: 20 天 且 有一次 tempo >= 120 (实测速度 118, 天数早就够)"""
    for i in range(1, 21):
        sess(conn, f"2026-08-{i:02d}", 1343, 2, tempo=80)
    assert calc(conn, "tech_dan_tu").achieved is False
    sess(conn, "2026-09-20", 1343, 2, tempo=120)
    assert calc(conn, "tech_dan_tu").achieved_at == "2026-09-20"


def test_tech_shuang_tu_same_session_needs_both(conn):
    """双吐: 同一段既 >= 3 分钟又 tempo >= 90 (实测 70)"""
    sess(conn, "2026-09-10", 1350, 3, tempo=89)
    assert calc(conn, "tech_shuang_tu").achieved is False
    sess(conn, "2026-09-12", 1350, 3, tempo=90)
    assert calc(conn, "tech_shuang_tu").achieved_at == "2026-09-12"


def test_tech_chan_yin_consecutive_10(conn):
    """无名指生花: 颤音单项连续练 10 天 (实测单项目最长 5)

    注意 _first_consec_item_days 是**按单个 item 各算各的**连续天数: 两个 item
    交替练不会拼成一条连续记录 (ids 里任一 item 单独达标即可)。
    """
    d = date(2026, 5, 10)
    for i in range(9):
        sess(conn, (d + timedelta(days=i)).isoformat(), 1337, 5)
    assert calc(conn, "tech_chan_yin").achieved is False
    sess(conn, "2026-05-19", 1337, 5)
    assert calc(conn, "tech_chan_yin").achieved_at == "2026-05-19"


def test_tech_chan_yin_items_do_not_merge(conn):
    """两个 item 交替练 → 各自连续只有 1 天, 不达成"""
    d = date(2026, 5, 10)
    for i in range(12):
        sess(conn, (d + timedelta(days=i)).isoformat(), 1337 if i % 2 == 0 else 1347, 5)
    assert calc(conn, "tech_chan_yin").achieved is False


def test_tech_dan_tu_4_tempo_110(conn):
    """四级吐音锋: tempo >= 110 (实测 100)"""
    sess(conn, "2026-09-01", 1349, 5, tempo=109)
    assert calc(conn, "tech_dan_tu_4").achieved is False
    sess(conn, "2026-09-02", 1349, 5, tempo=110)
    assert calc(conn, "tech_dan_tu_4").achieved_at == "2026-09-02"


def test_tech_ji_ben_gong_consecutive_5(conn):
    """九级石阶实: 低音 re 音阶连续 5 天 (实测 3)"""
    d = date(2026, 5, 1)
    for i in range(4):
        sess(conn, (d + timedelta(days=i)).isoformat(), 1033, 3)
    assert calc(conn, "tech_ji_ben_gong").achieved is False
    sess(conn, "2026-05-05", 1033, 3)
    assert calc(conn, "tech_ji_ben_gong").achieved_at == "2026-05-05"


def test_tech_ji_ben_gong_gap_resets(conn):
    """断开重来 (4/30, 5/1, 5/3, 5/4 → 不连续)"""
    for d in ("2026-04-30", "2026-05-01", "2026-05-03", "2026-05-04"):
        sess(conn, d, 1033, 3)
    assert calc(conn, "tech_ji_ben_gong").achieved is False


# ─── 典故组 ────────────────────────────────────────────────────────────────

def test_lore_xiao_shi_total_min_10000_daily(conn):
    """彩凤听箫来: 累计总时长 >= 10000 分钟 (daily_practices 口径, 实测 9419)

    口径必须是 daily_practices —— 孩子端看到的「累计总时长」就是这一列。
    practice_sessions 分段和(实测 6496)不是这个数, 所以只写 session 的行必须**不达成**。
    """
    sess(conn, "2026-01-01", 1001, 99999)        # 只有分段明细 → 不算
    assert calc(conn, "lore_xiao_shi").achieved is False
    for i in range(1, 10):
        day(conn, f"2026-0{i}-01", 1111)         # 9 × 1111 = 9999
    assert calc(conn, "lore_xiao_shi").achieved is False
    day(conn, "2026-10-01", 1)                   # 10000 → 达成
    r = calc(conn, "lore_xiao_shi")
    assert r.achieved is True and r.achieved_at == "2026-10-01"


def test_lore_li_guinian_five_pieces_twenty_days(conn):
    """岐王乐客年: 5 首曲目各练满 20 天 (实测只有 4 首 >= 20 天)"""
    for pid in (1004, 1026, 1340, 1346):
        for i in range(20):
            sess(conn, f"2026-02-{i + 1:02d}", pid, 5)
    assert calc(conn, "lore_li_guinian").achieved is False       # 只有 4 首
    for i in range(20):
        sess(conn, f"2026-03-{i + 1:02d}", 1351, 5)
    assert calc(conn, "lore_li_guinian").achieved_at == "2026-03-20"


def test_lore_li_mo_consecutive_15(conn):
    """李谟偷曲: 同一首曲子连续 15 天 (实测连续 12)"""
    d = date(2026, 6, 1)
    for i in range(14):
        sess(conn, (d + timedelta(days=i)).isoformat(), 1352, 5)
    assert calc(conn, "lore_li_mo").achieved is False
    sess(conn, "2026-06-15", 1352, 5)
    assert calc(conn, "lore_li_mo").achieved_at == "2026-06-15"


def test_lore_cai_yong_month_minutes_1500(conn):
    """柯亭识良竹: 单月累计 1500 分钟 (实测单月最高 1418)

    天数口径已饱和 (她单月最多练满 31 天), 所以换成时长口径。
    """
    for i in range(1, 15):
        day(conn, f"2026-08-{i:02d}", 100)          # 1400 分钟
    assert calc(conn, "lore_cai_yong").achieved is False
    day(conn, "2026-08-15", 100)                     # 1500 分钟 → 达成
    assert calc(conn, "lore_cai_yong").achieved_at == "2026-08-15"


def test_lore_cai_yong_month_resets(conn):
    """跨月不累计: 7 月 1000 + 8 月 1000 → 单月都不到 1500"""
    for i in range(1, 11):
        day(conn, f"2026-07-{i:02d}", 100)
        day(conn, f"2026-08-{i:02d}", 100)
    assert calc(conn, "lore_cai_yong").achieved is False


def test_lore_ma_rong_week_minutes_450(conn):
    """马融赋长笛: 自然周累计 450 分钟 (实测最高一周 410); 2026-08-31 是周一"""
    day(conn, "2026-08-31", 449)
    assert calc(conn, "lore_ma_rong").achieved is False
    day(conn, "2026-09-06", 1)                       # 周日, 仍属同一周
    assert calc(conn, "lore_ma_rong").achieved_at == "2026-09-06"


def test_lore_ma_rong_week_does_not_cross_boundary(conn):
    """跨周不算: 8/30(周日) + 8/31(周一) 是两个周 → 不达成"""
    day(conn, "2026-08-30", 300)
    day(conn, "2026-08-31", 300)
    assert calc(conn, "lore_ma_rong").achieved is False


def test_lore_huan_yi_15_segments_same_day(conn):
    """桓伊三弄客: 同日 15 段 (实测 12)"""
    for _ in range(14):
        sess(conn, "2026-07-29", 1346, 1)
    assert calc(conn, "lore_huan_yi").achieved is False
    sess(conn, "2026-07-29", 1346, 1)
    assert calc(conn, "lore_huan_yi").achieved_at == "2026-07-29"


# ─── 节令组 ────────────────────────────────────────────────────────────────

def test_season_mid_autumn_window(conn):
    """2026 中秋 = 09-25, 窗口 ±3 天"""
    day(conn, "2026-09-30", 20)
    assert calc(conn, "season_mid_autumn").achieved is False
    day(conn, "2026-09-26", 20)
    assert calc(conn, "season_mid_autumn").achieved_at == "2026-09-26"


def test_season_new_year_first_three_days(conn):
    """2026 春节 = 02-17, 窗口 初一~初三 (02-17 ~ 02-19)"""
    day(conn, "2026-02-20", 20)
    assert calc(conn, "season_new_year").achieved is False
    day(conn, "2026-02-18", 20)
    assert calc(conn, "season_new_year").achieved_at == "2026-02-18"


def test_season_duan_wu_exact_day(conn):
    """2026 端午 = 06-19, 仅当天"""
    day(conn, "2026-06-18", 20)
    assert calc(conn, "season_duan_wu").achieved is False
    day(conn, "2026-06-19", 20)
    assert calc(conn, "season_duan_wu").achieved_at == "2026-06-19"


def test_season_school_start_week(conn):
    """9/1~9/7 内 >= 3 天"""
    day(conn, "2026-09-01", 20)
    day(conn, "2026-09-09", 20)
    assert calc(conn, "season_school_start").achieved is False
    day(conn, "2026-09-02", 20)
    day(conn, "2026-09-03", 20)
    assert calc(conn, "season_school_start").achieved_at == "2026-09-03"


def test_season_summer_ten_days_over_60min(conn):
    """三伏清风笛: 七八月里 10 天单日 >= 60 分钟 (实测只有 6 天)

    "练过但不足 60 分钟"的天不算 —— 这是把天数口径换成强度口径后的关键差别。
    """
    for i in range(1, 10):
        day(conn, f"2026-07-{i:02d}", 60)
    day(conn, "2026-07-10", 59)                       # 不足 60, 不计
    day(conn, "2026-07-11", 59)
    assert calc(conn, "season_summer").achieved is False
    day(conn, "2026-07-20", 60)                       # 第 10 个达标日
    assert calc(conn, "season_summer").achieved_at == "2026-07-20"


def test_season_summer_counts_only_jul_aug(conn):
    """6 月 / 9 月不算"""
    for i in range(1, 11):
        day(conn, f"2026-06-{i:02d}", 90)
        day(conn, f"2026-09-{i:02d}", 90)
    assert calc(conn, "season_summer").achieved is False


def test_season_dong_zhi_long_tone_5_min(conn):
    """2026 冬至 = 12-22, 当天长音 item(1034) >= 5 分钟"""
    sess(conn, "2026-12-22", 1034, 4)
    assert calc(conn, "season_dong_zhi").achieved is False
    sess(conn, "2026-12-22", 1034, 1)
    assert calc(conn, "season_dong_zhi").achieved_at == "2026-12-22"


# ─── 勇气组 ────────────────────────────────────────────────────────────────

def test_brave_sick_back_gap(conn):
    """中断 >= 8 天后重新开练 (间隔 7 天不算)"""
    day(conn, "2026-07-01", 20)
    day(conn, "2026-07-08", 20)
    assert calc(conn, "brave_sick_back").achieved is False      # 间隔 7 天
    day(conn, "2026-07-17", 20)                                 # 距 07-08 间隔 9 天
    assert calc(conn, "brave_sick_back").achieved_at == "2026-07-17"


def test_brave_exam_pass_single_min_60(conn):
    """考场亮玉管: 考试曲单次 >= 60 分钟 (实测 50)"""
    sess(conn, "2026-08-24", 1339, 59)
    assert calc(conn, "brave_exam_pass").achieved is False
    sess(conn, "2026-08-26", 1339, 60)
    assert calc(conn, "brave_exam_pass").achieved_at == "2026-08-26"


def test_brave_class_back_75_min(conn):
    """回课满堂彩: 回课单次 >= 75 分钟 (实测 60)"""
    sess(conn, "2026-08-16", 1338, 74)
    assert calc(conn, "brave_class_back").achieved is False
    sess(conn, "2026-08-18", 1338, 75)
    assert calc(conn, "brave_class_back").achieved_at == "2026-08-18"


# ─── 与旧链路共存 / 不劫持 ─────────────────────────────────────────────────

def test_every_rule_kind_is_supported():
    """规则表里的每个 kind 都必须在 PRACTICE_RULE_KINDS 白名单内。

    kind 写错 ⇒ dispatch 落到 else 返 None ⇒ 那枚徽章永远灰着, 而且不抛异常、测试全绿。
    这条测试是那个护栏的守卫: 以后有人在表里写错/改名 kind, 这里立刻红。
    """
    from src.achievement_definitions import PRACTICE_BADGE_RULES, PRACTICE_RULE_KINDS
    bad = {k: r["kind"] for k, r in PRACTICE_BADGE_RULES.items()
           if r["kind"] not in PRACTICE_RULE_KINDS}
    assert bad == {}, f"规则表里有不支持的 kind: {bad}"


def test_unknown_kind_is_loud_not_silent(conn, caplog, monkeypatch):
    """表外 kind 必须「返未达成 + 打 ERROR 日志」, 不许静默失活。"""
    from src.achievement_definitions import PRACTICE_BADGE_RULES
    monkeypatch.setitem(PRACTICE_BADGE_RULES, "typo_probe_badge",
                        {"kind": "single_mni", "ids": (1,), "m": 1})
    with caplog.at_level("ERROR"):
        r = calc(conn, "typo_probe_badge")
    assert r.achieved is False
    assert any("不在支持集合内" in rec.getMessage() for rec in caplog.records), \
        "表外 kind 没有打日志 —— 这类失活必须留痕迹"


def test_sessions_read_failure_logs_warning(conn, caplog):
    """practice_sessions 表缺失 → 返未达成 + 留 WARNING 日志 (线上集体不亮时要有线索)"""
    conn.execute("DROP TABLE practice_sessions")
    with caplog.at_level("WARNING"):
        calc(conn, "rep_saliha")
    assert any("practice_sessions 读取失败" in rec.getMessage() for rec in caplog.records)


def test_unknown_id_not_hijacked(conn):
    """不在规则表里的 id 走原链路 (这里落通用 fallback), 不被新分支拦下"""
    r = calc(conn, "some_id_that_does_not_exist")
    assert r.achieved is False and r.achieved_at is None


def test_existing_badge_still_uses_old_chain(conn):
    """streak_7 仍由原 streak 分支处理 (空库 → 未达成)"""
    r = calc(conn, "streak_7")
    assert r.achieved is False


def test_stats_history_date_wins(conn):
    """stats 里已有达成时间 → 不可变, 用它而不是重算"""
    from src.achievement_definitions import _calc_milestone
    sess(conn, "2026-09-02", 1340, 25)
    stats = {"rep_saliha": {"achieved": "Y", "achieved_at": "2026-01-01"}}
    r = _calc_milestone(
        conn, "rep_saliha", stats=stats, streak=1, total_mins=0, top_items=[],
        has_all_items=False, all_items_achieved_at=None, has_double=False,
        today=date(2026, 10, 17))
    assert r.achieved is True and r.achieved_at == "2026-01-01"


def test_missing_practice_sessions_table_does_not_crash(conn):
    """老库没有 practice_sessions 表 → 返未达成, 不抛异常"""
    conn.execute("DROP TABLE practice_sessions")
    r = calc(conn, "rep_saliha")
    assert r.achieved is False


# ─── 跨后端类型 / 脏数据 (生产是 MySQL, 测试是 SQLite) ───────────────────────

def test_rules_work_with_mysql_date_objects(conn_typed):
    """MySQL 的 DATE 列读出来是 date 对象, 不是字符串 —— 规则必须照常判定。

    SQLite 默认把 DATE 读成字符串, 所以只有 conn_typed (PARSE_DECLTYPES) 能测到
    这条生产路径; 否则 prod-only 的类型 bug 在测试里永远看不见。
    """
    sess(conn_typed, "2026-09-01", 1340, 24)
    assert calc(conn_typed, "rep_saliha").achieved is False
    sess(conn_typed, "2026-09-02", 1340, 25)
    r = calc(conn_typed, "rep_saliha")
    assert r.achieved is True and r.achieved_at == "2026-09-02"


def test_rules_work_with_mysql_date_objects_daily(conn_typed):
    """daily_practices 走 date 对象时同样成立 (单月时长口径)。"""
    for i in range(1, 15):
        day(conn_typed, f"2026-08-{i:02d}", 100)
    assert calc(conn_typed, "lore_cai_yong").achieved is False
    day(conn_typed, "2026-08-15", 100)
    assert calc(conn_typed, "lore_cai_yong").achieved_at == "2026-08-15"


def test_date_str_normalizes_both_backends():
    from src.achievement_definitions import _date_str
    assert _date_str(date(2026, 9, 1)) == "2026-09-01"          # MySQL DATE
    assert _date_str(datetime(2026, 9, 1, 8, 30)) == "2026-09-01"  # MySQL DATETIME
    assert _date_str("2026-09-01") == "2026-09-01"              # SQLite
    assert _date_str(None) is None


def test_dirty_date_row_is_skipped_not_fatal(conn):
    """一行脏日期必须只跳过该行, 不能把整轮 calc 打断。

    这里抛出去会打断 calc_all → 所有徽章一起不解锁, 是比"少判一张"严重得多的故障。
    """
    conn.execute("INSERT INTO practice_sessions (practice_date, item_id, item_name, duration_minutes) "
                 "VALUES ('not-a-date', 1340, 'x', 30)")
    conn.execute("INSERT INTO daily_practices (date, total_minutes) VALUES ('garbage', 99)")
    sess(conn, "2026-09-02", 1340, 25)
    day(conn, "2026-09-02", 20)
    r = calc(conn, "rep_saliha")
    assert r.achieved is True and r.achieved_at == "2026-09-02"


def test_dirty_duration_row_is_skipped_not_fatal(conn):
    """时长字段是文本 → 跳过该行, 其余行照常判定。"""
    conn.execute("INSERT INTO practice_sessions (practice_date, item_id, item_name, duration_minutes) "
                 "VALUES ('2026-09-01', 1340, 'x', 'abc')")
    sess(conn, "2026-09-02", 1340, 25)
    r = calc(conn, "rep_saliha")
    assert r.achieved is True and r.achieved_at == "2026-09-02"


# ─── D1=A (2026-10-19): day_sessions 口径 = 同日跨曲目合计 ─────────────────────
#
# 原语 _first_day_sessions 的分组键曾是 (日期, item_id) ⇒ 测的是"单曲单日"
# (PIECE 曲目下峰值 8), 而卡面「同一天分段练满 15 段」/卡背「一天里扎扎实实
# 练满十五段」都没限定同一首曲子。dad 拍板 D1=A: 分组键只按日期。
#
# 下面 4 个用例是这个口径的护栏: 跨曲目合计成立、单 id 规则逐值不变。
# 负控: 把分组键改回 (d, iid) → test_lore_huan_yi_cross_item_same_day_* 变红。

def test_lore_huan_yi_cross_item_same_day_sums_up(conn):
    """跨曲目同日合计: 8(1346) + 7(1351) = 15 段 ⇒ 达成 (改前按 (d,iid) 只有 8 段)。"""
    for _ in range(8):
        sess(conn, "2026-07-29", 1346, 1)
    for _ in range(6):
        sess(conn, "2026-07-29", 1351, 1)
    assert calc(conn, "lore_huan_yi").achieved is False      # 合计 14 段
    sess(conn, "2026-07-29", 1351, 1)                        # 合计 15 段
    r = calc(conn, "lore_huan_yi")
    assert r.achieved is True and r.achieved_at == "2026-07-29"
    assert r.computed_value == 15


def test_lore_huan_yi_cross_item_one_short(conn):
    """跨曲目同日合计差 1 段 ⇒ 未达成 (边界负控, 不许 >= 变 >)。"""
    for _ in range(8):
        sess(conn, "2026-07-29", 1346, 1)
    for _ in range(6):
        sess(conn, "2026-07-29", 1351, 1)
    r = calc(conn, "lore_huan_yi")
    assert r.achieved is False
    assert r.computed_value == 14 and r.achieved_at is None


def test_lore_huan_yi_cross_item_different_days_do_not_sum(conn):
    """跨曲目但**不同日**不得合并计数 —— 口径是"同一天合计", 不是"累计"。"""
    for _ in range(8):
        sess(conn, "2026-07-29", 1346, 1)
    for _ in range(7):
        sess(conn, "2026-07-30", 1351, 1)
    r = calc(conn, "lore_huan_yi")
    assert r.achieved is False
    assert r.computed_value == 8 and r.achieved_at is None


def test_day_sessions_single_id_rules_unchanged(conn):
    """单 id 规则两种口径等价: 分组键里的 item_id 是常量, 逐值不变。

    rep_xizang_wuqu (1346, n=10) 与 rep_xiao_kanxi (1351, n=5) 各自只有一个 id,
    改口径前后 computed_value / achieved_at 必须完全一致。
    """
    for _ in range(8):
        sess(conn, "2026-07-29", 1346, 2)
    for _ in range(3):
        sess(conn, "2026-09-08", 1351, 3)
    wuqu, kanxi = calc(conn, "rep_xizang_wuqu"), calc(conn, "rep_xiao_kanxi")
    assert (wuqu.achieved, wuqu.computed_value, wuqu.achieved_at) == (False, 8, None)
    assert (kanxi.achieved, kanxi.computed_value, kanxi.achieved_at) == (False, 3, None)
    # 单 id 补到阈值仍照常达成 (证明不是"永远不亮")
    for _ in range(2):
        sess(conn, "2026-07-29", 1346, 2)
    for _ in range(2):
        sess(conn, "2026-09-08", 1351, 3)
    wuqu, kanxi = calc(conn, "rep_xizang_wuqu"), calc(conn, "rep_xiao_kanxi")
    assert (wuqu.achieved, wuqu.computed_value, wuqu.achieved_at) == (True, 10, "2026-07-29")
    assert (kanxi.achieved, kanxi.computed_value, kanxi.achieved_at) == (True, 5, "2026-09-08")
