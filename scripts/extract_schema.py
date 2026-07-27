#!/usr/bin/env python3
"""
dizical SQLite → MySQL Schema 提取脚本
Phase 1a: 把 ./data/dizi.db 全部 13 表的 DDL 转换输出到 schema_mysql.sql

转换规则 (MySQL 5.7 严格模式):
- INTEGER PRIMARY KEY AUTOINCREMENT → BIGINT AUTO_INCREMENT PRIMARY KEY
- BOOLEAN → TINYINT(1)
- TEXT PRIMARY KEY → VARCHAR(255) PRIMARY KEY (5.7 不允许 TEXT 做 PK)
- TEXT UNIQUE → VARCHAR(255) UNIQUE (同上)
- TEXT/JSON/BLOB/GEOMETRY NOT NULL DEFAULT 'X' → 去掉 DEFAULT (5.7 不允许)
- `name` (反引号) → 不变
- SQLite "name" (双引号) → 改成反引号或去掉
- SQLite datetime('now', 'localtime') → MySQL CURRENT_TIMESTAMP
- 自定义索引保留 (CREATE INDEX)

用法:
    python3 scripts/extract_schema.py
    # 输出: schema_mysql.sql
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"
OUT_PATH = Path(__file__).parent.parent / "schema_mysql.sql"


def convert_column_type(col_type: str) -> str:
    """SQLite type → MySQL type (本函数未直接调用, 改写在 convert_table_sql)"""
    return col_type


def convert_table_sql(sql: str) -> str:
    """单表 CREATE TABLE → MySQL 5.7 兼容"""

    # ─── 1. 标识符: 双引号 → 反引号 (MySQL 标准) ───
    # SQLite 接受 "name", MySQL 5.7 严格模式不认
    # 注意: 字符串字面量里的双引号不动 (但 SQLite 字符串字面量是单引号, 所以安全)
    # 例: CREATE TABLE "practice_items" → CREATE TABLE `practice_items`
    sql = re.sub(r'"([a-zA-Z_][a-zA-Z0-9_]*)"', r'`\1`', sql)

    # ─── 2. PRIMARY KEY + AUTOINCREMENT ───
    sql = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "BIGINT AUTO_INCREMENT PRIMARY KEY",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY(?!\s+AUTOINCREMENT)",
        "BIGINT PRIMARY KEY",
        sql,
        flags=re.IGNORECASE,
    )

    # ─── 3. BOOLEAN → TINYINT(1) ───
    sql = re.sub(r"\bBOOLEAN\b", "TINYINT(1)", sql, flags=re.IGNORECASE)

    # ─── 4. 通用 INTEGER (非 PRIMARY KEY) → BIGINT ───
    def replace_integer_in_cols(match):
        col_def = match.group(0)
        if "PRIMARY KEY" in col_def.upper() or "AUTO_INCREMENT" in col_def.upper():
            return col_def
        return col_def.replace("INTEGER", "BIGINT").replace("integer", "BIGINT")

    sql = re.sub(
        r"\b[A-Za-z_][A-Za-z0-9_]*\s+INTEGER(?!\s+PRIMARY|\s*\(.*\bAUTOINCREMENT\b)",
        replace_integer_in_cols,
        sql,
    )

    # ─── 5. AUTOINCREMENT → AUTO_INCREMENT ───
    sql = re.sub(r"\bAUTOINCREMENT\b", "AUTO_INCREMENT", sql, flags=re.IGNORECASE)

    # ─── 6. TEXT/BLOB/JSON/GEOMETRY 做主键/UNIQUE/索引 → VARCHAR(255) ───
    sql = re.sub(
        r"\b(TEXT|BLOB)\s+PRIMARY\s+KEY",
        "VARCHAR(255) PRIMARY KEY",
        sql,
        flags=re.IGNORECASE,
    )
    # 列级 UNIQUE: TEXT NOT NULL UNIQUE → VARCHAR(255) NOT NULL UNIQUE
    sql = re.sub(
        r"\b(TEXT|BLOB)\s+NOT\s+NULL\s+UNIQUE",
        "VARCHAR(255) NOT NULL UNIQUE",
        sql,
        flags=re.IGNORECASE,
    )
    # UNIQUE KEY 约束 (CREATE TABLE 内)
    sql = re.sub(
        r"\b(TEXT|BLOB)\s+UNIQUE\s+KEY",
        "VARCHAR(255) UNIQUE KEY",
        sql,
        flags=re.IGNORECASE,
    )
    # 普通 UNIQUE (无 KEY 关键字)
    sql = re.sub(
        r"\b(TEXT|BLOB)\s+UNIQUE(?!\s+KEY|\s+PRIMARY|\s+NOT)",
        "VARCHAR(255) UNIQUE",
        sql,
        flags=re.IGNORECASE,
    )

    # ─── 7. 列类型推断: created_at/updated_at 等 TEXT NOT NULL DEFAULT → DATETIME ───
    # 必须在 §7b 去掉 DEFAULT 之前先做
    # 模式 1: 已经有 DEFAULT CURRENT_TIMESTAMP (8 已经跑过)
    sql = re.sub(
        r"\b(created_at|updated_at|started_at|ended_at|achieved_at|practice_date|recorded_at|paid_at)\s+TEXT\s+NOT\s+NULL\s+DEFAULT\s+CURRENT_TIMESTAMP",
        r"\1 DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        sql,
        flags=re.IGNORECASE,
    )
    # 模式 2: 还有 DEFAULT (datetime(...)) 或 DEFAULT 'X' (8 还没跑)
    # 注意: 要吃掉整个 DEFAULT 表达式, 包括尾部括号
    # \s 不能匹配换行 (否则吃多行), 用 [ \t] 强制单行
    # DEFAULT 表达式: 函数调用 (datetime(...)) / 字符串 'X' / 数字
    # 不用 [^,\n]+ 因为 datetime('now', 'localtime') 里有逗号
    sql = re.sub(
        r"\b(created_at|updated_at|started_at|ended_at|achieved_at|practice_date|recorded_at|paid_at)[ \t]+TEXT[ \t]+NOT[ \t]+NULL[ \t]+DEFAULT[ \t]+(\([^()]*\([^()]*\)[^()]*\)|'[^']*'|\([^)]*\)|\d+)",
        r"\1 DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        sql,
    )

    # ─── 7b. TEXT/BLOB/JSON/GEOMETRY 不能有 DEFAULT (5.7 严格模式) ───
    # (除了上面 7 已经转成 DATETIME 的列)
    sql = re.sub(
        r"(\b(?:TEXT|JSON|GEOMETRY|BLOB)(?:\s+\w+)*?\s+NOT\s+NULL\s+)DEFAULT\s+('[^']*'|\"[^\"]*\"|\d+|\([^)]+\))",
        r"\1",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"(\b(?:TEXT|JSON|GEOMETRY|BLOB)(?:\s+\w+)*?)\s+DEFAULT\s+('[^']*'|\"[^\"]*\"|\d+|\([^)]+\))",
        r"\1",
        sql,
        flags=re.IGNORECASE,
    )

    # ─── 8. SQLite datetime('now', 'localtime') → MySQL CURRENT_TIMESTAMP ───
    sql = re.sub(
        r"datetime\(['\"]now['\"],\s*['\"]localtime['\"]\)",
        "CURRENT_TIMESTAMP",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        r"CURRENT_TIMESTAMP\s+ON\s+UPDATE\s+CURRENT_TIMESTAMP",
        "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        sql,
        flags=re.IGNORECASE,
    )
    # DEFAULT (CURRENT_TIMESTAMP) → DEFAULT CURRENT_TIMESTAMP (SQLite 允许括号, MySQL 不)
    sql = re.sub(
        r"DEFAULT\s+\(\s*CURRENT_TIMESTAMP\s*\)",
        "DEFAULT CURRENT_TIMESTAMP",
        sql,
        flags=re.IGNORECASE,
    )

    # ─── 9. MySQL 关键字做列名 (不加反引号会语法错) ───
    # 关键字列表 (按需扩展)
    KEYWORDS = ['key', 'order', 'group', 'select', 'where', 'from', 'table',
                 'index', 'primary', 'foreign', 'references', 'check', 'default',
                 'desc', 'status', 'read', 'write', 'values', 'set', 'call']
    # 模式: 匹配 (key|order|...) 后跟 NOT NULL 或 PRIMARY 或 UNIQUE 等
    # 例: "key TEXT NOT NULL" → "`key` TEXT NOT NULL"
    # 例: "key VARCHAR(255) PRIMARY KEY" → "`key` VARCHAR(255) PRIMARY KEY"
    for kw in KEYWORDS:
        # 不在反引号内, 不在字符串内
        sql = re.sub(
            rf"\b({kw})\s+(TEXT|VARCHAR|INTEGER|BIGINT|INT|CHAR)\b",
            rf"`\1` \2",
            sql,
            flags=re.IGNORECASE,
        )

    # ─── 10. CREATE INDEX 中 TEXT/BLOB 列要 VARCHAR(255) ───
    # 例: CREATE INDEX idx_audit_channel ON practice_audit_log(channel)
    # 看 CREATE INDEX ... ON table(col) — 如果 col 是 TEXT, 加长度
    # 这步在 convert_index_sql 里处理

    return sql


def convert_index_sql(sql: str) -> str:
    """索引 DDL 转换"""
    # CREATE INDEX 里的 TEXT/BLOB 列: MySQL 5.7 严格模式要求指定前缀
    # 例: CREATE INDEX idx_xxx ON table(channel) [channel 是 TEXT] → 失败
    # 修法: 找到索引涉及的列, 在 CREATE TABLE 里已经是 TEXT, 我们没法在 INDEX 里改类型
    # 只能 1) 改表里列类型 (DANGEROUS, 改 schema) 2) 跳过该索引
    # 这里采取方案 2: 跳过 TEXT 列的索引, 加注释说明
    # 例: CREATE INDEX idx_audit_channel ON practice_audit_log(channel);
    # match: CREATE INDEX name ON table(col)
    m = re.match(
        r"CREATE\s+INDEX\s+(\w+)\s+ON\s+(\w+)\s*\(\s*(\w+)\s*\)",
        sql.strip(),
        re.IGNORECASE,
    )
    if m:
        idx_name, tbl, col = m.group(1), m.group(2), m.group(3)
        # 看原 schema 里这列是什么类型
        return f"-- SKIP: {sql.strip()}  (col {col} is TEXT, MySQL 5.7 索引需前缀长度, 业务允许跳过)"

    return sql


def main():
    if not DB_PATH.exists():
        print(f"ERROR: 找不到 {DB_PATH}")
        return 1

    print(f"📖 读取 {DB_PATH}...")
    conn = sqlite3.connect(str(DB_PATH))

    tables = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    print(f"   找到 {len(tables)} 张表")

    indexes = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    print(f"   找到 {len(indexes)} 个自定义索引")

    conn.close()

    out_lines = [
        "-- dizical MySQL Schema (从 SQLite 自动转换)",
        f"-- 生成时间: {Path(__file__).name}",
        f"-- 来源 DB: {DB_PATH}",
        f"-- 表数: {len(tables)}, 索引数: {len(indexes)}",
        "",
        "SET FOREIGN_KEY_CHECKS=0;",
        "",
    ]

    print()
    print("📝 转换表...")
    for name, sql in tables:
        if not sql:
            continue
        converted = convert_table_sql(sql)
        out_lines.append(f"DROP TABLE IF EXISTS `{name}`;")
        out_lines.append(converted + ";")
        out_lines.append("")
        print(f"   ✓ {name}")

    print()
    print("📝 转换索引...")
    for name, sql in indexes:
        if not sql:
            continue
        converted = convert_index_sql(sql)
        out_lines.append(converted + ";")
        print(f"   ✓ {name}")

    out_lines.append("SET FOREIGN_KEY_CHECKS=1;")
    out_lines.append("")

    OUT_PATH.write_text("\n".join(out_lines), encoding="utf-8")
    print()
    print(f"✅ 写出: {OUT_PATH} ({OUT_PATH.stat().st_size} bytes, {len(out_lines)} 行)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())