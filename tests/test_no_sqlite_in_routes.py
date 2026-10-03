"""Sprint 26092901 fix/badge-claim-db: 静态守卫 — 路由层不得直连 SQLite.

背景: `src/kid_app/routes/badge_claim.py` 曾用 `sqlite3.connect(<repo>/data/dizi.db)`
直连本地 sqlite。线上 CloudRun 走云 MySQL, 而容器镜像里那份 `data/dizi.db` 是构建时的
老文件 (没有 achievement_* 三张表) → `/api/badge/unclaimed` 长期报
`no such table: achievement_stats` 500, 潜伏 18 天没被发现, 因为单测 fixture 把
`DATABASE_URL` 硬写成空串, CI 只跑 SQLite (见 tests/test_badge_claim.py)。

规则: `src/kid_app/routes/**` 一律走 `src.db_adapter` (双后端适配), 不得直接依赖 sqlite3。
豁免: 本文件所在的 tests/ 目录; 迁移脚本走 `src/migrate_*.py` (不在 routes/ 内)。
"""
from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ROUTES_DIR = PROJECT_ROOT / "src" / "kid_app" / "routes"


def _route_files() -> list[Path]:
    return sorted(p for p in ROUTES_DIR.rglob("*.py") if p.name != "__init__.py")


def test_routes_dir_exists_and_has_files():
    """守卫自身的前置断言: 扫不到文件说明路径写错, 不能让测试静默通过."""
    files = _route_files()
    assert files, f"没扫到任何路由文件: {ROUTES_DIR}"
    assert any(p.name == "badge_claim.py" for p in files)


def test_no_sqlite3_usage_in_route_modules():
    """路由层不得 import sqlite3 或调 sqlite3.* (统一走 src.db_adapter)."""
    offenders: list[str] = []
    for path in _route_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == "sqlite3":
                        offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] == "sqlite3":
                    offenders.append(
                        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} from {node.module} import ..."
                    )
            elif isinstance(node, ast.Call):
                fn = node.func
                if (
                    isinstance(fn, ast.Attribute)
                    and isinstance(fn.value, ast.Name)
                    and fn.value.id == "sqlite3"
                ):
                    offenders.append(
                        f"{path.relative_to(PROJECT_ROOT)}:{node.lineno} sqlite3.{fn.attr}(...)"
                    )
    assert not offenders, (
        "路由层禁止直接依赖 sqlite3 (线上是 MySQL, 直连本地 sqlite = 读错库 → 500)。"
        "改走 src.db_adapter:\n  " + "\n  ".join(offenders)
    )


def test_dockerignore_excludes_nested_sqlite_files():
    """镜像不能打进任何本地 sqlite 文件 (含 data/dizi.db 这类子目录里的).

    旧版 `.dockerignore` 只有 `*.db` → 只匹配根目录, `data/dizi.db` 照样被
    `Dockerfile: COPY . /app` 打进镜像 (线上"伪连通"的来源)。
    """
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
    lines = {ln.strip() for ln in dockerignore.splitlines() if ln.strip() and not ln.strip().startswith("#")}
    assert "**/*.db" in lines, f".dockerignore 必须含 **/*.db 递归规则, 现为: {sorted(lines)}"
    assert "data/" not in lines or "**/*.db" in lines  # data/ 整目录忽略也算过


def test_badge_claim_uses_db_adapter():
    """badge_claim 必须走 adapter 的连接入口 (正控: 别把修复改回去)."""
    src = (ROUTES_DIR / "badge_claim.py").read_text(encoding="utf-8")
    assert "db_adapter.get_conn()" in src
    assert "db_adapter.execute_dicts(" in src
    assert "row_factory" not in src, "sqlite3.Row 列名取值写法应已被 execute_dicts 取代"
