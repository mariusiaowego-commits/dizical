"""
Test: _calc_seasonal monthly 早练类 badge 双后端 practice_at 兼容.

Pitfall 38 (sprint 26080701): MySQL practice_at / date 返 datetime 对象, 老代码
多处 `[11:16]` / `[:19]` slice 直接 TypeError, try/except 静默吃掉或冒泡.

修复后 calc 必须:
- SQLite str 输入 → 正常解析
- MySQL datetime 输入 → str() 后正常解析, achieved=True

策略: 复制 prod dizi.db 到 tmp_path (避免测试污染 prod). prod 里 8-02 10:00 + 8-13 10:27
两条 < 12:00 练习 → first_to_act 应激活 (老代码是 False).
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


def test_early_riser_threshold_20_active(monkeypatch, prod_db_copy):
    """回归: early_riser 阈值 20:00, prod 最早 12:00 → 应激活."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    r = results["early_riser"]
    assert r.achieved is True
    assert "首次达成 2025-09-27 12:00" in r.condition


def test_little_chick_threshold_17_active(monkeypatch, prod_db_copy):
    """回归: little_chick_commander 阈值 17:00, prod 最早 12:00 → 应激活."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    r = results["little_chick_commander"]
    assert r.achieved is True
    assert "首次达成 2025-09-27 12:00" in r.condition


def test_first_to_act_threshold_12_active(monkeypatch, prod_db_copy):
    """PITFALL 38 主修复: first_to_act 阈值 12:00, prod 里有 2026-06-13 10:27 →
    修复前 achieved=False (TypeError 静默吃掉); 修复后 achieved=True."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    r = results["first_to_act"]
    assert r.achieved is True, (
        f"PITFALL 38 未修复: first_to_act 期望 True (10:27 < 12:00), "
        f"actual achieved={r.achieved}, condition={r.condition}"
    )
    assert "首次达成 2026-06-13 10:27" in r.condition


def test_early_riser_cond_format_no_datetime_leak(monkeypatch, prod_db_copy):
    """cond 文案不能含 raw datetime 'YYYY-MM-DD HH:MM:SS.ssss' 字符串 (难看)."""
    _wire_to_test_db(monkeypatch, prod_db_copy)
    results = calc_all()
    for aid in ["early_riser", "little_chick_commander", "first_to_act"]:
        r = results[aid]
        assert r.achieved is True
        # 不能含 '00:00:00' (date 字段 raw datetime 默认 00:00:00 段)
        assert "00:00:00" not in r.condition, (
            f"{aid} cond 含 raw datetime 段: {r.condition}"
        )