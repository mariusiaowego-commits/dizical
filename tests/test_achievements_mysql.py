"""
fix/achievements-mysql-conn (2026-07-24) 回归测试.

目的:
- calc_all() 必须同时跑通 SQLite 和 MySQL, 跨后端结果稳定
- 防止后续任何人改回 SQLite 写死 (硬编码 json_each/strftime/conn.execute)

CI 配置建议:
  - tests/test_achievements_mysql.py 在 CI 跑
  - DATABASE_URL 必须注入 (跟 CloudRun 一致), 测的是生产路径
  - 本地 SQLite 也跑一次, 验本地开发不被破坏
"""
import os
import json
import pytest
from collections import Counter


@pytest.fixture(scope="module")
def sqlite_results():
    """跑 calc_all 走 SQLite 本地, 取 5 字段稳定快照."""
    os.environ.pop("DATABASE_URL", None)
    # 清掉 DATABASE_URL 让 db_adapter 走 SQLite
    import importlib
    from src import db_adapter
    importlib.reload(db_adapter)
    from src.achievement_definitions import calc_all
    r = calc_all()
    return _snapshot(r)


@pytest.fixture(scope="module")
def mysql_results():
    """跑 calc_all 走 MySQL (云), 取 5 字段稳定快照."""
    db_url = os.environ.get("MYSQL_TEST_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("MYSQL_TEST_URL/DATABASE_URL 未配置, 跳过 MySQL 跨库测试")
    os.environ["DATABASE_URL"] = str(db_url)
    # reload 让 db_adapter 重新检测
    import importlib
    from src import db_adapter
    importlib.reload(db_adapter)
    from src.achievement_definitions import calc_all
    r = calc_all()
    return _snapshot(r)


def _snapshot(r):
    """把 CalcResult dict 转成 {aid: {5 字段}}."""
    return {
        k: {
            "achieved": v.achieved,
            "computed_value": v.computed_value,
            "achieved_at": str(v.achieved_at),
            "condition": v.condition,
            "seasonal_type": v.seasonal_type,
        }
        for k, v in r.items()
    }


def test_calc_all_returns_dict():
    """基本形状: 必须返 dict, 非空."""
    from src.achievement_definitions import calc_all
    r = calc_all()
    assert isinstance(r, dict)
    assert len(r) > 0


def test_calc_all_sqlite_stable(snapshot_path="data/_baseline_sqlite.json"):
    """SQLite 跑两次, 完全相同 (重入稳定性)."""
    import importlib
    from src import db_adapter
    os.environ.pop("DATABASE_URL", None)
    importlib.reload(db_adapter)
    from src.achievement_definitions import calc_all

    r1 = _snapshot(calc_all())
    r2 = _snapshot(calc_all())
    assert r1 == r2, f"SQLite 重入不稳定:\ndiff={json.dumps(_diff(r1, r2), ensure_ascii=False)[:500]}"


def test_calc_all_mysql_stable():
    """MySQL 跑两次, 完全相同 (重入稳定性).

    用 subprocess 隔离: 防止 db/Database 实例在 pytest 进程内被 reload 时保留 SQLite conn.
    """
    import subprocess
    import sys
    db_url = os.environ.get("MYSQL_TEST_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("MYSQL_TEST_URL/DATABASE_URL 未配置")

    def run_once():
        result = subprocess.run(
            [sys.executable, "-c",
             "import os, json\n"
             f"os.environ['DATABASE_URL'] = '{db_url}'\n"
             "from src.achievement_definitions import calc_all\n"
             "r = calc_all()\n"
             "data = {k: {'achieved': v.achieved, 'computed_value': v.computed_value, "
             "'achieved_at': str(v.achieved_at), 'condition': v.condition, "
             "'seasonal_type': v.seasonal_type} for k,v in r.items()}\n"
             "print(json.dumps(data, sort_keys=True, ensure_ascii=False))"
             ],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"subprocess failed:\n{result.stderr}"
        return json.loads(result.stdout)

    r1 = run_once()
    r2 = run_once()
    assert r1 == r2, f"MySQL 重入不稳定:\ndiff={json.dumps(_diff(r1, r2), ensure_ascii=False)[:500]}"


def test_achievement_definitions_no_sqlite_specific():
    """防止回退: 禁止 achievement_definitions.py 里出现 SQLite 专有语法."""
    from pathlib import Path
    import re
    src = Path("src/achievement_definitions.py").read_text()
    # 移除 docstring ("""...""" 三引号块) 和行注释 (#...)
    code_only = re.sub(r'"""[\s\S]*?"""', '', src)
    code_only = re.sub(r'#.*$', '', code_only, flags=re.MULTILINE)
    forbidden = ["sqlite3.connect(", "json_each(", "strftime("]
    for token in forbidden:
        assert token not in code_only, (
            f"禁止 SQLite 专有语法: {token} (跨后端必须用 src.db_adapter)"
        )


def test_achievement_definitions_no_direct_conn_execute():
    """防止回退: 禁止 achievement_definitions.py 直接调 conn.execute().
    所有 SQL 走 _exec() → db_adapter.execute()."""
    from pathlib import Path
    import re
    src = Path("src/achievement_definitions.py").read_text()
    # 匹配 'conn.execute(' 但允许 'cur = conn.cursor()'
    matches = re.findall(r"conn\.execute\(", src)
    assert len(matches) == 0, f"禁止 conn.execute() 直调 (要通过 _exec): 找到 {len(matches)} 处"


def _diff(a, b):
    """生成 2 个 dict 的 field-level diff."""
    out = {}
    for k in set(a) | set(b):
        if a.get(k) != b.get(k):
            out[k] = {"now": a.get(k), "baseline": b.get(k)}
    return out
