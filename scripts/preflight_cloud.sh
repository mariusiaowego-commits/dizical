#!/usr/bin/env bash
# preflight_cloud.sh — dizical 切云前只读预检 (Sprint 09)
#
# 用途: 切流 / 部署前, 对「本地 SQLite ↔ 云 MySQL」做一次只读对账,
#       把所有已知坑 (schema 漂移 / 行数不一致 / 乐观锁列缺失 / 关键表空) 一次性暴露.
# 只读: 本脚本不做任何写操作 (只 SELECT / PRAGMA / information_schema).
#
# 用法:
#   bash scripts/preflight_cloud.sh            # 用 ~/.dizical/.env 的凭据 (推荐)
#   MYSQL_HOST=... MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DATABASE=... bash scripts/preflight_cloud.sh
#   bash scripts/preflight_cloud.sh --json     # 输出 JSON 报告 (供 agent 解析)
#
# 依赖: python3 + pymysql (项目已有)
#
# 通过标准 (全部 PASS 才允许切流):
#   [1] MySQL 连通 (SELECT VERSION)
#   [2] 表清单对齐: SQLite 15 表 ⊆ MySQL 15 表
#   [3] practice_sessions 乐观锁列: version + updated_at 必须存在 (PR-D v3)
#   [4] schema_migrations: 本地 3 与 999 都应在云端 (云端缺 3 = PR-D migration 未跑)
#   [5] 关键表行数对账: 表级 COUNT 差异 (允许 extra rows: 云 > 本), 云 < 本 = 数据缺失 → FAIL
#   [6] 空表风险: 云端业务表行数 = 0 的列出来 (切云后冷启动读空表要人工确认)
#
# 失败退出码: 0 = 全 PASS; 1 = 有 FAIL; 2 = 环境/依赖错误

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SQLITE_DB="$PROJECT_ROOT/data/dizi.db"
ENV_FILE="$HOME/.dizical/.env"

# ── 凭据来源 (优先级: 环境变量 > ~/.dizical/.env) ──────────────────────────
MYSQL_HOST="${MYSQL_HOST:-}"
MYSQL_PORT="${MYSQL_PORT:-22209}"
MYSQL_USER="${MYSQL_USER:-dizical}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-cloud1-d4gfwyvsk1435e2e4}"

if [[ -z "$MYSQL_HOST" || -z "$MYSQL_PASSWORD" ]]; then
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a
  fi
fi

if [[ -z "$MYSQL_HOST" || -z "$MYSQL_PASSWORD" ]]; then
  echo "ERROR: 缺少 MySQL 凭据" >&2
  echo "  要么传环境变量 MYSQL_HOST/MYSQL_PASSWORD, 要么在 $ENV_FILE 里配" >&2
  exit 2
fi

export MYSQL_HOST MYSQL_PORT MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE SQLITE_DB

PYTHON_BIN="$(command -v python3 || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "ERROR: 找不到 python3" >&2
  exit 2
fi

"$PYTHON_BIN" - <<'PYEOF'
import json
import os
import sqlite3
import sys

try:
    import pymysql
except ImportError:
    print("ERROR: 没装 pymysql, 跑: pip install pymysql 或 uv run --with pymysql")
    sys.exit(2)

OUT_JSON = "--json" in sys.argv[1:]
SQLITE_DB = os.environ["SQLITE_DB"]

# 跟 src/database_mysql.py / src/database.py 对齐的期望表 (15 张)
EXPECTED_TABLES = [
    "achievement_badges", "achievement_stats", "achievements",
    "daily_practices", "lessons", "payments", "practice_audit_log",
    "practice_categories", "practice_items", "practice_reports",
    "practice_sessions", "report_artifacts", "schema_migrations",
    "settings", "weekly_assignments",
]
# 行数对账忽略纯系统表
COUNT_SKIP = {"schema_migrations"}

results = []  # (check_no, name, status, detail)

def record(no, name, ok, detail):
    results.append({"check": no, "name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    if not OUT_JSON:
        mark = "✅" if ok else "❌"
        print(f"[{no}] {mark} {name}: {detail}")

# ── [1] MySQL 连通 ──────────────────────────────────────────────
try:
    conn = pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ["MYSQL_PORT"]),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        connect_timeout=10,
        cursorclass=pymysql.cursors.DictCursor,
    )
    with conn.cursor() as cur:
        cur.execute("SELECT VERSION() AS v, DATABASE() AS db")
        row = cur.fetchone()
    record(1, "MySQL 连通", True, f"{row['db']} @ {row['v']}")
except Exception as e:  # noqa: BLE001
    record(1, "MySQL 连通", False, str(e))
    if not OUT_JSON:
        print("\n结果: 1 FAIL — 无法连接 MySQL, 后续检查跳过")
    print(json.dumps({"preflight": results, "verdict": "FAIL"}, ensure_ascii=False))
    sys.exit(1)

# ── [2] 表清单对齐 ──────────────────────────────────────────────
try:
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        mysql_tables = {list(r.values())[0] for r in cur.fetchall()}
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_tables = {r[0] for r in sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    missing_in_mysql = sorted(set(EXPECTED_TABLES) - mysql_tables)
    missing_in_sqlite = sorted(set(EXPECTED_TABLES) - sqlite_tables)
    ok = not missing_in_mysql and not missing_in_sqlite
    detail = f"MySQL {len(mysql_tables)} 表, SQLite {len(sqlite_tables)} 表"
    if missing_in_mysql:
        detail += f"; 云缺: {missing_in_mysql}"
    if missing_in_sqlite:
        detail += f"; 本地缺: {missing_in_sqlite}"
    record(2, "表清单对齐", ok, detail)
except Exception as e:  # noqa: BLE001
    record(2, "表清单对齐", False, str(e))

# ── [3] practice_sessions 乐观锁列 (PR-D v3) ─────────────────────
try:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'practice_sessions'")
        ps_cols = {r["COLUMN_NAME"] for r in cur.fetchall()}
    missing_cols = sorted({"version", "updated_at"} - ps_cols)
    ok = not missing_cols
    detail = f"列: {sorted(ps_cols)}"
    if missing_cols:
        detail = f"缺乐观锁列: {missing_cols} (PR-D v3 migration 未跑, 049 部署后首次访问会 lazy ALTER)"
    record(3, "practice_sessions 乐观锁列", ok, detail)
except Exception as e:  # noqa: BLE001
    record(3, "practice_sessions 乐观锁列", False, str(e))

# ── [4] schema_migrations 版本 ──────────────────────────────────
try:
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations ORDER BY version")
        mysql_vers = [int(r["version"]) for r in cur.fetchall()]
    sqlite_vers = [r[0] for r in sqlite_conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
    missing = sorted(set(sqlite_vers) - set(mysql_vers))
    # 本地 3 是 PR-D; 999 是 practice_sessions 建表. 云端必须 ≥ 本地.
    ok = not missing
    detail = f"云端 {mysql_vers}, 本地 {sqlite_vers}"
    if missing:
        detail = f"云端缺版本 {missing} (PR-D v3 未在云端跑过, 预期: 049 部署后 lazy ALTER 补齐)"
    record(4, "schema_migrations", ok, detail)
except Exception as e:  # noqa: BLE001
    record(4, "schema_migrations", False, str(e))

# ── [5] 关键表行数对账 ──────────────────────────────────────────
try:
    diffs = []
    for t in sorted(EXPECTED_TABLES):
        if t in COUNT_SKIP:
            continue
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS c FROM `{t}`")
            mc = int(cur.fetchone()["c"])
        try:
            sc = int(sqlite_conn.execute(f"SELECT COUNT(*) FROM `{t}`").fetchone()[0])
        except sqlite3.OperationalError:
            sc = -1  # 本地没这张表
        if mc < sc:
            diffs.append(f"{t}: 云={mc} < 本地={sc} (数据缺失!)")
        elif mc > sc:
            diffs.append(f"{t}: 云={mc} > 本地={sc} (+{mc - sc})")
        elif mc == 0 and sc == 0:
            diffs.append(f"{t}: 两边都空")
    # 云 ≥ 本地 视为 PASS (云是超集); 只有云 < 本地是 FAIL
    hard_fail = [d for d in diffs if "数据缺失" in d]
    detail = "; ".join(diffs) if diffs else "全部一致"
    record(5, "行数对账", not hard_fail, detail)
except Exception as e:  # noqa: BLE001
    record(5, "行数对账", False, str(e))

# ── [6] 空表风险 ────────────────────────────────────────────────
try:
    empty = []
    for t in sorted(EXPECTED_TABLES):
        if t in COUNT_SKIP:
            continue
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS c FROM `{t}`")
            if int(cur.fetchone()["c"]) == 0:
                empty.append(t)
    # 空表不判 FAIL (可能本来就是空业务), 只提示
    detail = f"云端空表: {empty}" if empty else "无空表"
    record(6, "空表风险提示", True, detail)
except Exception as e:  # noqa: BLE001
    record(6, "空表风险提示", False, str(e))

conn.close()
sqlite_conn.close()

fails = [r for r in results if r["status"] == "FAIL"]
verdict = "PASS" if not fails else "FAIL"
if not OUT_JSON:
    print()
    print(f"== preflight 结果: {verdict} ({len(results) - len(fails)}/{len(results)} PASS) ==")
    if fails:
        for f in fails:
            print(f"  ❌ [{f['check']}] {f['name']}")
        print()
        print("FAIL 项会阻塞切流. 修复后重跑本脚本.")
    else:
        print("  全部通过, 可以继续切流准备. (注: 这只是只读预检, 不等于运行时验证)")

print(json.dumps({"preflight": results, "verdict": verdict}, ensure_ascii=False))
sys.exit(0 if not fails else 1)
PYEOF
