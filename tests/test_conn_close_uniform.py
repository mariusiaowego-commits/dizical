"""Sprint 26093001 audit-followups: P3-1 连接归还统一 (防回潮 + 行为锁)

背景 (2026-09-29 PR 级审计 P3-1): MySQL 侧连接来自 DBUtils PooledDB,
`close()` = 归还池 (不销毁)。旧代码在 18 处写成 `if not is_mysql: conn.close()`
→ MySQL 分支永不 close, 连接只能靠 GC 兜底, 高并发下耗尽池。
审计只抓到 badge_workflow 2 处, 实测同族面 18 处 (auth.py 14 / badge_workflow 2 /
config_users.py 1 / auth_web.py 1)。

本文件两条锁:
  1. 静态防回潮: src/ 生产代码里不许再出现 `if not is_mysql` 跳过 close
  2. 行为锁: MySQL 分支 (is_mysql=True) 走完请求后, 连接必须被 close
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"


def test_no_if_not_is_mysql_skip_close_in_production_code():
    """静态锁: 生产代码不许再写 `if not is_mysql:` 跳过 close (池泄漏)。

    允许保留 `is_mysql` 的**真用途** (如 auth.py 用它选 datetime 格式),
    这里只禁「按 backend 跳过 close」这一种形态。
    """
    offenders: list[str] = []
    for f in sorted(SRC.rglob("*.py")):
        text = f.read_text()
        for m in re.finditer(r"if not is_mysql\s*:", text):
            line_no = text[: m.start()].count("\n") + 1
            offenders.append(f"{f.relative_to(SRC.parent)}:{line_no}")
    assert not offenders, (
        "这些地方仍在按 backend 跳过 close → MySQL 池连接不归还: " + ", ".join(offenders)
    )


def test_mysql_branch_still_closes_connection(monkeypatch):
    """行为锁: MySQL 分支下走完一次查询, 连接必须被 close (归还池).

    旧写法 (if not is_mysql: conn.close()) 在 is_mysql=True 时不 close →
    本断言 `close.called` 会红。
    """
    from src.kid_app import auth

    fake_conn = MagicMock()
    fake_conn.cursor.return_value.fetchone.return_value = None  # → 函数提前 return None

    monkeypatch.setattr("src.db_adapter.get_conn", lambda: (fake_conn, True))

    auth.fetch_user_by_username("nobody")

    assert fake_conn.close.called, (
        "MySQL 分支没 close 连接 → PooledDB 连接不回池 (审计 P3-1 的原始缺陷)"
    )


def test_mysql_branch_closes_even_when_query_raises(monkeypatch):
    """行为锁: 查询抛异常时也必须 close (finally 语义)。"""
    from src.kid_app import auth

    fake_conn = MagicMock()
    fake_conn.cursor.side_effect = RuntimeError("boom")

    monkeypatch.setattr("src.db_adapter.get_conn", lambda: (fake_conn, True))

    with pytest.raises(RuntimeError):
        auth.fetch_user_by_username("nobody")

    assert fake_conn.close.called, "异常路径没 close → 连接泄漏"
