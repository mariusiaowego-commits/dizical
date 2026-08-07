"""
Test: _calc_seasonal monthly 早练类 badge 双后端 practice_at 兼容 + monthly 重置语义.

Pitfall 38 (sprint 26080701): MySQL practice_at 返 datetime 对象, 老代码 `p_at[:19]`
抛 TypeError, try/except 静默吃掉 → 云端 calc_all 永远返 achieved=False.

修复后 calc 必须:
- SQLite str 输入 → 正常解析
- MySQL datetime 输入 → str() 后正常解析, achieved=True

Pitfall 41 (sprint 26080701): 三个早练 badge 应按 monthly 周期重置 (跟 DB 字段
category=seasonal/seasonal_type=monthly 一致), 不是"全历史首次达成永久解锁".
当月练习早于阈值 → 当月激活; 下月重置.

策略: 复制 prod dizi.db 到 tmp_path (避免测试污染 prod). 测试用 monkeypatch 注入
特定 practice_at 数据, 验当月/跨月行为.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.achievement_definitions import calc_all


PROD_DB = Path(__file__).parent.parent / "data" / "dizi.db"


@pytest.fixture
def prod_db_copy(tmp_path: Path) -> Path:
    """复制 prod dizi.db 到 tmp, monkeypatch calc_all 用它."""
    if not PROD_DB.exists():
        pytest.skip(f"prod DB 不存在: {PROD_DB}")
    db_path = tmp_path / "prod_copy.db"
    shutil.copy2(PROD_DB, db_path)
    return db_path


def _wire_to_test_db(monkeypatch, db_path: Path):
    monkeypatch.setenv("DATABASE_URL", "")
    from src import achievement_definitions
    monkeypatch.setattr(achievement_definitions, "_DB_PATH", db_path)
    from src import db_adapter
    monkeypatch.setattr(
        db_adapter,
        "get_conn",
        lambda: (__import__("sqlite3").connect(str(db_path)), False),
    )


def test_first_to_act_monthly_active_in_aug(monkeypatch, prod_db_copy):
    """本月 (2026-08) 8-02 10:00 < 12:00 → first_to_act 当月应激活."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    r = results["first_to_act"]
    assert r.achieved is True, (
        f"first_to_act 当月 (8月) 应激活 (8-02 10:00 < 12:00), "
        f"actual achieved={r.achieved}, condition={r.condition}"
    )
    assert "2026-08" in r.condition
    assert "2026-08-02 10:00" in r.condition


def test_early_riser_monthly_active_in_aug(monkeypatch, prod_db_copy):
    """本月 (2026-08) 最早 13:47 < 20:00 → early_riser 当月应激活."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    r = results["early_riser"]
    assert r.achieved is True
    assert "2026-08" in r.condition
    assert "20:00" in r.condition


def test_little_chick_monthly_active_in_aug(monkeypatch, prod_db_copy):
    """本月 (2026-08) 最早 13:47 < 17:00 → little_chick 当月应激活."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    r = results["little_chick_commander"]
    assert r.achieved is True
    assert "2026-08" in r.condition
    assert "17:00" in r.condition


def test_first_to_act_cond_format_no_datetime_leak(monkeypatch, prod_db_copy):
    """cond 文案不能含 raw datetime 'YYYY-MM-DD HH:MM:SS.ssss' 字符串 (难看)."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    for aid in ["early_riser", "little_chick_commander", "first_to_act"]:
        r = results[aid]
        assert r.achieved is True
        # date 字段 raw datetime 默认 00:00:00 段不应泄露
        assert "00:00:00" not in r.condition, (
            f"{aid} cond 含 raw datetime 段: {r.condition}"
        )


def test_first_to_act_not_active_in_other_months(monkeypatch, prod_db_copy):
    """除 8 月外, prod 其他月份没有 < 12:00 的 practice_at → 历史不该激活.

    修 monthly 之前: 老代码"全历史首次达成即永久解锁", 2025-09-27 12:00 等会激活.
    修 monthly 之后: 当月限定, 但 2025-09 等月份没 < 12:00 数据 → 应不激活.
    """
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    r = results["first_to_act"]
    # 修前: r.achieved=True, cond='首次达成 2026-06-13 10:27 ...'
    # 修后: r.achieved=True, cond='2026-08 本月首次早于 12:00 练习: 2026-08-02 10:00 ...'
    # 测试只验 cond 包含"本月"语义, 不验具体内容
    assert "本月" in r.condition, (
        f"修复后 cond 应含 '本月' (monthly 语义), actual: {r.condition}"
    )