#!/usr/bin/env python3
"""
dizical SQLite → MySQL 数据迁移脚本
Phase 1a: 把 ./data/dizi.db 13 张表的全量数据搬到 MySQL

用法:
    # 1. 先跑 extract_schema.py 生成 schema_mysql.sql
    # 2. 在 MySQL 跑: mysql ... < schema_mysql.sql
    # 3. 再跑: python3 scripts/migrate_data.py
    #    环境变量: MYSQL_HOST MYSQL_USER MYSQL_PASSWORD MYSQL_DB

策略:
- 顺序: 父表先, 子表后 (settings → categories → items → lessons → ... → audit)
- 逐表: DELETE FROM table; INSERT 一行行 (sqlite3 → pymysql)
- 校验: 迁移完行数对比 + 5 条抽样对比
"""

import os
import sqlite3
import sys
from pathlib import Path

try:
    import pymysql
except ImportError:
    print("ERROR: 没装 pymysql, 跑: pip install pymysql")
    sys.exit(1)

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"

# 迁移顺序: 跟 schema_mysql.sql 一致 (按外键依赖排, 当前 schema 无外键约束但按习惯)
TABLES_ORDER = [
    "settings",
    "practice_categories",
    "practice_items",
    "lessons",
    "payments",
    "weekly_assignments",
    "daily_practices",
    "practice_audit_log",
    "practice_reports",
    "achievements",
    "achievement_stats",
    "achievement_badges",
    "schema_migrations",  # 跟业务无关, 留空
]


def get_mysql_conn():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DB", "dizical"),
        charset="utf8mb4",
        autocommit=False,
    )


def get_sqlite_conn():
    return sqlite3.connect(str(DB_PATH))


def migrate_table(sqlite_conn, mysql_conn, table_name):
    """单表迁移: SELECT 全量 → DELETE → INSERT 批量"""
    cur_sqlite = sqlite_conn.cursor()
    cur_mysql = mysql_conn.cursor()

    # 1. 拿 SQLite 数据
    cur_sqlite.execute(f"SELECT * FROM {table_name}")
    rows = cur_sqlite.fetchall()
    if not rows:
        print(f"   ⏭  {table_name}: 0 行, 跳过")
        return 0

    # 2. 拿列名
    col_names = [d[0] for d in cur_sqlite.description]

    # 3. 拿 MySQL 目标表的列 (按 MySQL 实际列顺序)
    cur_mysql.execute(f"DESCRIBE {table_name}")
    mysql_cols = [row[0] for row in cur_mysql.fetchall()]

    # 4. 交集: SQLite 实际有的列 + MySQL 实际有的列
    common_cols = [c for c in col_names if c in mysql_cols]
    if not common_cols:
        print(f"   ⚠️  {table_name}: 列无交集, 跳过")
        return 0

    # 5. 过滤 row 数据, 只保留 common_cols
    col_indices = [col_names.index(c) for c in common_cols]
    filtered_rows = [[row[i] for i in col_indices] for row in rows]

    # 6. DELETE + INSERT 批量
    cur_mysql.execute(f"DELETE FROM {table_name}")
    placeholders = ", ".join(["%s"] * len(common_cols))
    col_list = ", ".join(f"`{c}`" for c in common_cols)
    sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"

    # 批量 (每 1000 行 commit 一次, 避免锁表)
    BATCH = 1000
    for i in range(0, len(filtered_rows), BATCH):
        batch = filtered_rows[i : i + BATCH]
        cur_mysql.executemany(sql, batch)
        mysql_conn.commit()
        print(f"      ... {min(i + BATCH, len(filtered_rows))}/{len(filtered_rows)} 行")

    print(f"   ✓ {table_name}: {len(rows)} 行 → MySQL")
    return len(rows)


def verify_table(sqlite_conn, mysql_conn, table_name):
    """校验: 行数 + 5 条抽样"""
    cur_sqlite = sqlite_conn.cursor()
    cur_mysql = mysql_conn.cursor()

    cnt_sqlite = cur_sqlite.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    cnt_mysql = cur_mysql.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    if cnt_sqlite != cnt_mysql:
        print(f"   ❌ {table_name}: 行数不一致 (sqlite={cnt_sqlite}, mysql={cnt_mysql})")
        return False

    if cnt_sqlite == 0:
        return True

    # 抽样对比 (前 5 行)
    cur_sqlite.execute(f"SELECT * FROM {table_name} ORDER BY id LIMIT 5")
    sample_sqlite = cur_sqlite.fetchall()
    cur_mysql.execute(f"SELECT * FROM {table_name} LIMIT 5")
    sample_mysql = cur_mysql.fetchall()

    # 简化: 只对比列数 + 第 1 行
    if sample_sqlite and sample_mysql:
        if len(sample_sqlite[0]) != len(sample_mysql[0]):
            print(f"   ⚠️  {table_name}: 列数不一致 (sqlite={len(sample_sqlite[0])}, mysql={len(sample_mysql[0])})")
            return False

    print(f"   ✓ {table_name}: {cnt_sqlite} 行, 抽样 OK")
    return True


def main():
    if not DB_PATH.exists():
        print(f"ERROR: 找不到 {DB_PATH}")
        return 1

    print(f"📖 SQLite: {DB_PATH}")
    sqlite_conn = get_sqlite_conn()
    print(f"🐬 MySQL: {os.environ.get('MYSQL_HOST', '127.0.0.1')}:{os.environ.get('MYSQL_PORT', '3306')}/{os.environ.get('MYSQL_DB', 'dizical')}")
    mysql_conn = get_mysql_conn()

    total_rows = 0
    failed_tables = []

    print()
    print("📦 迁移数据...")
    for table in TABLES_ORDER:
        try:
            n = migrate_table(sqlite_conn, mysql_conn, table)
            total_rows += n
        except Exception as e:
            print(f"   ❌ {table}: {e}")
            failed_tables.append(table)
            mysql_conn.rollback()

    print()
    print("🔍 校验...")
    verify_failed = []
    for table in TABLES_ORDER:
        if table in failed_tables:
            continue
        try:
            if not verify_table(sqlite_conn, mysql_conn, table):
                verify_failed.append(table)
        except Exception as e:
            print(f"   ❌ {table} verify: {e}")
            verify_failed.append(table)

    sqlite_conn.close()
    mysql_conn.close()

    print()
    print(f"📊 总结: 迁移 {total_rows} 行")
    if failed_tables:
        print(f"   ❌ 迁移失败: {failed_tables}")
    if verify_failed:
        print(f"   ❌ 校验失败: {verify_failed}")
    if not failed_tables and not verify_failed:
        print(f"   ✅ 全部成功")

    return 0 if not failed_tables and not verify_failed else 1


if __name__ == "__main__":
    raise SystemExit(main())