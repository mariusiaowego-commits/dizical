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

import ast
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


# ─── 静态守卫: close() 必须在 finally (或专用 close 包装器) 里 ───────────────
#
# 背景 (2026-09-30 grok PR #348 审计非阻断项): `achievement_definitions.calc_all`
# 与 `get_achievements_by_type` 只在成功路径 conn.close() → 中途抛异常就漏关
# (MySQL 侧 = 池连接不归还)。跟 P3-1 同族, 用 AST 守卫住整个类。

# 请求期 / 常驻进程会跑的模块 (one-shot migrate_*.py 脚本不在内: 进程随即退出, 不构成池压力)
_CLOSE_GUARD_SCOPE = (
    "kid_app",
    "db_adapter.py",
    "achievement_definitions.py",
    "database_mysql.py",
    "cli.py",
)


def _bare_close_lines(nodes) -> set[int]:
    """只挑 DB 连接名上的 close() — `conn.close()` / `_conn.close()`。

    排除 `self.pool.close()` (方法定义) 与 `s.close()` (socket, 一次性对象不构成池压力)。
    """
    out: set[int] = set()
    for n in nodes:
        for sub in ast.walk(n):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "close"
                and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id.lstrip("_").startswith("conn")
            ):
                out.add(sub.lineno)
    return out


def _guard_offenders(path: Path) -> list[int]:
    tree = ast.parse(path.read_text())
    safe: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            if node.finalbody:
                safe |= _bare_close_lines(node.finalbody)
            elif len(node.body) <= 2 and _bare_close_lines(node.body):
                # 专用 close 包装器 (如 badge_claim._close_quietly: try: conn.close() except: log)
                safe |= _bare_close_lines(node.body)
    return sorted(_bare_close_lines([tree]) - safe)


def test_close_must_be_in_finally_or_dedicated_closer():
    """静态锁: 生产代码里 `conn.close()` 不许裸放在函数体末尾 (异常路径漏关)。"""
    offenders: list[str] = []
    for rel in _CLOSE_GUARD_SCOPE:
        base = SRC / rel
        files = sorted(base.rglob("*.py")) if base.is_dir() else [base]
        for f in files:
            for line_no in _guard_offenders(f):
                offenders.append(f"{f.relative_to(SRC.parent)}:{line_no}")
    assert not offenders, (
        "这些 close() 不在 finally / 专用包装器里 → 异常路径漏关 (MySQL = 池不归还): "
        + ", ".join(offenders)
    )


def test_calc_all_closes_conn_when_body_raises(monkeypatch):
    """行为锁: calc_all 中途抛异常, 连接也必须 close。"""
    from src import achievement_definitions as ad

    fake_conn = MagicMock()

    def boom(*a, **kw):
        raise RuntimeError("calc 中途炸")

    monkeypatch.setattr(ad, "_get_conn", lambda: (fake_conn, True))
    monkeypatch.setattr(ad, "_get_achievements", boom)

    with pytest.raises(RuntimeError):
        ad.calc_all()

    assert fake_conn.close.called, "calc_all 异常路径没 close → MySQL 池连接不归还"


def test_get_achievements_by_type_closes_conn_when_body_raises(monkeypatch):
    """行为锁: get_achievements_by_type 中途抛异常, 连接也必须 close。"""
    from src import achievement_definitions as ad

    fake_conn = MagicMock()

    def boom(*a, **kw):
        raise RuntimeError("_exec 中途炸")

    monkeypatch.setattr(ad, "_get_conn", lambda: (fake_conn, True))
    monkeypatch.setattr(ad, "_exec", boom)

    with pytest.raises(RuntimeError):
        ad.get_achievements_by_type("seasonal")

    assert fake_conn.close.called, "get_achievements_by_type 异常路径没 close → 连接泄漏"


def test_cli_get_last_practice_closes_conn(monkeypatch):
    """行为锁: `cli._get_last_practice()` 用完归还连接。

    CLI 仪表盘每 ~3 秒调一次本函数; 旧写法借了连接就 return, 从不 close →
    MySQL 池连接在 CLI 进程里一路涨 (2026-09-30 grok 审计记录, 尾巴清理)。
    """
    from src import cli
    import src.database as dbmod

    fake_conn = MagicMock()
    fake_conn.execute.return_value.fetchone.return_value = None  # 无记录 → 提前 return None

    class _FakeDB:
        @staticmethod
        def _get_connection():
            return fake_conn

    monkeypatch.setattr(dbmod, "db", _FakeDB)

    assert cli._get_last_practice() is None
    assert fake_conn.close.called, "cli._get_last_practice 用完没 close → 连接不归还"
