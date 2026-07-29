"""PR-D: 5s dedup 防重放测试 (单元级, 避开 db 单例 reload 问题).

直接验证 _check_dedup / _record_dedup helper 函数 (不通过 TestClient).
"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.kid_app.app import (  # noqa
    _check_dedup,
    _record_dedup,
    _DEDUP_WINDOW_SECONDS,
)


def test_dedup_check_returns_none_first_time():
    """首次: _check_dedup 应返 None (没缓存)."""
    assert _check_dedup(909, 5) is None


def test_record_dedup_then_check_within_5s_returns_cached():
    """5s 内: 返缓存."""
    body = {"ok": True, "session": {"id": 100, "duration_minutes": 5}}
    _record_dedup(909, 5, body)
    cached = _check_dedup(909, 5)
    assert cached is not None
    assert cached == body
    assert cached["session"]["id"] == 100


def test_dedup_different_minutes_does_not_match():
    """不同 minutes 不命中缓存."""
    _record_dedup(909, 5, {"ok": True, "session": {"id": 100}})
    assert _check_dedup(909, 10) is None


def test_dedup_different_item_id_does_not_match():
    """不同 item_id 不命中缓存."""
    _record_dedup(909, 5, {"ok": True, "session": {"id": 100}})
    assert _check_dedup(910, 5) is None


def test_dedup_check_does_not_record():
    """_check_dedup 只读, 不写缓存."""
    initial = _check_dedup(911, 7)
    assert initial is None
    # 再次 check, 还应 None (没副作用)
    again = _check_dedup(911, 7)
    assert again is None


def test_dedup_check_zero_values():
    """item_id 或 minutes 为 0 → 返 None (不参与 dedup)."""
    _record_dedup(912, 5, {"ok": True})
    assert _check_dedup(0, 5) is None
    assert _check_dedup(912, 0) is None


def test_dedup_expires_after_window():
    """5s 后: 缓存过期, 返 None."""
    # 用更短的 window 模拟: 直接修改全局
    import src.kid_app.app as app_mod
    original_window = app_mod._DEDUP_WINDOW_SECONDS
    app_mod._DEDUP_WINDOW_SECONDS = 0.1
    try:
        _record_dedup(913, 5, {"ok": True})
        assert _check_dedup(913, 5) is not None
        time.sleep(0.2)
        assert _check_dedup(913, 5) is None
    finally:
        app_mod._DEDUP_WINDOW_SECONDS = original_window
