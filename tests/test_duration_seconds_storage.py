"""sprint 26093002 P1-3 锁: seconds == 0 且 minutes > 0 的旧条目必须按 minutes * 60 视作。

agy 复核 P1-3: `it.get('seconds', default)` 在 key 存在且值为 0 时不走 default, 会把
历史分钟权重算成 0 秒。这里直接对拍 `_item_secs` 与合并后的 daily 汇总。
"""
from __future__ import annotations

import datetime as dt
import json

import pytest

from src.database import Database, _item_secs


# ── 1. 单元锁: _item_secs 的 4 条分支 ────────────────────────────────────────
@pytest.mark.parametrize("item,expected", [
    ({"seconds": 0, "minutes": 5}, 300),      # seconds=0 且 minutes>0 → 回退 minutes*60
    ({"seconds": 0, "minutes": 0}, 0),        # 双方都 0 → 0
    ({"minutes": 5}, 300),                    # 无 seconds → 回退
    ({"seconds": 90, "minutes": 2}, 90),      # 有真实秒 → 用秒, 不看分钟
    ({"seconds": None, "minutes": 3}, 180),   # None → 回退
    ({"seconds": 45, "minutes": 0}, 45),      # 秒 < 1 分钟且分钟为 0 → 保留秒
])
def test_item_secs_falls_back_when_zero(item, expected):
    assert _item_secs(item) == expected


# ── 2. 集成锁: 库里存着 seconds=0 的旧条目, 再写入同科目要累加正确 ──────────
def test_merge_accumulates_legacy_zero_seconds_as_minutes(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    day = dt.date(2026, 9, 30)
    item_id = db.create_practice_item("长音")
    name = "长音"

    # 手工塞一条「秒列为 0」的旧条目, 模拟未回填的老数据 (绕过 save 的归一化)
    legacy = [{"item": name, "item_id": item_id, "minutes": 5, "seconds": 0}]
    with db._get_connection() as conn:  # noqa: SLF001
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO daily_practices (date, items, total_minutes, total_seconds, log, practiced) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (day.isoformat(), json.dumps(legacy, ensure_ascii=False), 5, 0, "", "Y"),
        )
        conn.commit()

    # 再练 90 秒 (minutes = ceil(90/60) = 2), 同科目 → 合并
    db.save_daily_practice(
        day,
        [{"item": name, "item_id": item_id, "minutes": 2, "seconds": 90}],
        2, "", channel="test", method="unit",
    )

    daily = db.get_daily_practice(day)
    assert daily is not None
    # minutes: 逐条 ceil 后相加 (语义不变)
    assert daily["total_minutes"] == 7
    # seconds: 5*60 + 90 = 390 (旧条目按分钟回退, 不是 0 + 90 = 90)
    assert daily["total_seconds"] == 390
    assert daily["items"][0]["seconds"] == 390
    assert daily["items"][0]["minutes"] == 7


# ── 3. 集成锁: 提前结束 10 秒这种「不足 1 分钟」不会被抬成整分钟 ─────────────
def test_short_session_keeps_real_seconds(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    day = dt.date(2026, 9, 30)
    item_id = db.create_practice_item("长音")
    db.save_daily_practice(
        day,
        [{"item": "长音", "item_id": item_id, "minutes": 1, "seconds": 10}],
        1, "", channel="test", method="unit",
    )
    daily = db.get_daily_practice(day)
    # minutes 仍是 ceil(10/60)=1 (徽章判定用), seconds 保留真值 10
    assert daily["total_minutes"] == 1
    assert daily["total_seconds"] == 10
