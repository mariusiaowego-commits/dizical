"""sprint 26100101 F4 / F4b 锁: 「负数秒」是坏数据, 不得被洗成 minutes*60。

背景（独立代码评审 P2）：`_item_secs` 与 `pick_seconds` 原先写 `if secs <= 0 and mins > 0`
→ 负数秒（数据被写坏）也按"未回填"回退，把坏数据伪装成正常值。
本文件对拍三处同口径实现（sqlite / MySQL / duration_fmt）并驱动 JS 侧检查。

负控（人工验证过）：
- 把 `src/database.py` 的 `secs == 0` 改回 `secs <= 0` → test_sqlite_negative_seconds_is_zero 红（0 → 180）
- 把 `pick_seconds` 的 `if s < 0: return 0` 改回回退 → test_pick_seconds_negative_is_zero 红
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from src.database import _item_secs as sqlite_item_secs
from src.database_mysql import _item_secs as mysql_item_secs
from src.kid_app.duration_fmt import pick_seconds

REPO_ROOT = Path(__file__).resolve().parent.parent
JS_CHECK = REPO_ROOT / "tests" / "js" / "duration_pick_negative_check.js"


# ── 1. sqlite 存储层 ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("item,expected", [
    ({"minutes": 3, "seconds": -5}, 0),      # 负数秒 → 0（原实现 180）
    ({"minutes": 3, "seconds": -1}, 0),
    ({"minutes": 0, "seconds": -5}, 0),      # 改前也是 0 → 不能当负控
    ({"minutes": 3, "seconds": 0}, 180),     # 0 = 未回填 → 仍要回退
    ({"minutes": 3, "seconds": 90}, 90),
    ({"minutes": 0, "seconds": 0}, 0),
])
def test_sqlite_negative_seconds_is_zero(item, expected):
    assert sqlite_item_secs(item) == expected


# ── 2. MySQL 存储层（同一段契约, 不 import database） ─────────────────────────
@pytest.mark.parametrize("item,expected", [
    ({"minutes": 3, "seconds": -5}, 0),
    ({"minutes": 3, "seconds": 0}, 180),
    ({"minutes": 3, "seconds": 90}, 90),
    ({"minutes": 0, "seconds": -5}, 0),
])
def test_mysql_negative_seconds_is_zero(item, expected):
    """只改 sqlite 不改 MySQL 时这条会红 —— 生产走 MySQL。"""
    assert mysql_item_secs(item) == expected


# ── 3. 读路径 pick_seconds（页面/API 展示用） ────────────────────────────────
@pytest.mark.parametrize("secs,mins,expected", [
    (-5, 3, 0),        # 负数 → 0（原实现 180）
    (-1, 0, 0),
    (0, 3, 180),       # 0 → 回退
    (None, 3, 180),    # 缺省 → 回退
    (90, 2, 90),
    (45, 0, 45),
])
def test_pick_seconds_negative_is_zero(secs, mins, expected):
    assert pick_seconds(secs, mins) == expected


# ── 4. JS 侧同口径（真跑 node, 不手推） ──────────────────────────────────────
def test_js_pick_negative_is_zero():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 不在 PATH")
    r = subprocess.run([node, str(JS_CHECK)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node 检查失败:\n{r.stdout}\n{r.stderr}"
    assert "10/10 passed" in r.stdout, r.stdout
