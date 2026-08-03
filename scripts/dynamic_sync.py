#!/usr/bin/env python3
"""动态 schema 同步：从 SQLite 读真实结构 → 建 MySQL 表 → 迁移数据"""
import sqlite3
import pymysql
import sys
import re
from datetime import datetime

SQLITE_PATH = "/Users/mt16/dev/dizical/data/dizi.db"
MYSQL_CFG = {
    "host": "sh-cynosdbmysql-grp-3nsxknle.sql.tencentcdb.com",
    "port": 22209,
    "user": "dizical",
    "password": "qlAWThorx0Z6fTU5",
    "database": "cloud1-d4gfwyvsk1435e2e4",
    "charset": "utf8mb4"
}

# 迁移顺序（外键先后）
MIGRATE_ORDER = [
    "settings", "practice_categories", "practice_items",
    "lessons", "daily_practices", "practice_sessions",
    "weekly_assignments", "achievements", "achievement_badges",
    "achievement_stats", "practice_reports", "report_artifacts",
    "payments", "practice_audit_log", "schema_migrations"
]

def sqlite_type_to_mysql(sqlite_type):
    """SQLite 类型转 MySQL 兼容类型"""
    t = sqlite_type.upper().strip()
    if "INTEGER" in t or "INT" in t or "BIGINT" in t:
        return "BIGINT"
    if "VARCHAR" in t:
        # 提取长度，超过 191 用 TEXT
        m = re.search(r"\((\d+)\)", t)
        if m and int(m.group(1)) <= 191:
            return f"VARCHAR({m.group(1)})"
        return "TEXT"
    if "TEXT" in t:
        return "TEXT"
    if "REAL" in t or "FLOAT" in t or "DOUBLE" in t:
        return "DOUBLE"
    if "BOOLEAN" in t or "TINYINT" in t:
        return "TINYINT(1)"
    if "BLOB" in t:
        return "BLOB"
    if "DATE" in t or "TIMESTAMP" in t or "DATETIME" in t:
        return "DATETIME"
    if "DECIMAL" in t or "NUMERIC" in t:
        return "DECIMAL(10,2)"
    return "TEXT"

def main():
    print(f"[{datetime.now()}] 开始动态 schema 同步...")
    
    # 连接
    sqlite = sqlite3.connect(SQLITE_PATH)
    sqlite.row_factory = sqlite3.Row
    sc = sqlite.cursor()
    
    mysql = pymysql.connect(**MYSQL_CFG)
    mc = mysql.cursor()
    
    # 1. 清空所有表
    print("  清空云端表...")
    mc.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in reversed(MIGRATE_ORDER):
        mc.execute(f"DROP TABLE IF EXISTS {table}")
    mysql.commit()
    
    # 2. 为每张表动态建表 + 迁移数据
    total_rows = 0
    mismatch = 0
    
    for table in MIGRATE_ORDER:
        # 取 SQLite 表结构
        sc.execute(f"PRAGMA table_info({table})")
        cols = sc.fetchall()
        if not cols:
            print(f"  ⚠️ 跳过 {table}（无字段）")
            continue
        
        # 构建 MySQL CREATE TABLE
        col_defs = []
        for c in cols:
            col_name = f"`{c['name']}`"
            col_type = sqlite_type_to_mysql(c['type'])
            
            # 约束
            constraints = []
            if c['notnull']:
                constraints.append("NOT NULL")
            if c['dflt_value'] is not None:
                # MySQL 不允许 TEXT 有默认值，跳过
                if col_type not in ("TEXT", "BLOB", "JSON"):
                    default = str(c['dflt_value']).strip("'\"")
                    if default.lower() in ('current_timestamp', 'now', 'localtime'):
                        constraints.append("DEFAULT CURRENT_TIMESTAMP")
                    elif default:
                        constraints.append(f"DEFAULT '{default}'")
            if c['pk'] == 1:
                constraints.append("PRIMARY KEY")
            
            # 特殊处理：主键 + AUTO_INCREMENT，TEXT 不能做主键
            full_def = f"{col_name} {col_type} {' '.join(constraints)}"
            if c['pk'] == 1 and col_type in ("BIGINT", "INT"):
                full_def = full_def.replace("PRIMARY KEY", "AUTO_INCREMENT PRIMARY KEY")
            elif c['pk'] == 1 and col_type in ("TEXT", "VARCHAR"):
                # TEXT/VARCHAR 主键限制长度
                full_def = full_def.replace("` TEXT PRIMARY KEY", "` VARCHAR(191) PRIMARY KEY")
                full_def = full_def.replace("` VARCHAR", "` VARCHAR")
            
            col_defs.append(full_def)
        
        # 建表
        create_sql = f"CREATE TABLE {table} ({', '.join(col_defs)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        try:
            mc.execute(create_sql)
        except Exception as e:
            print(f"  ❌ {table} 建表失败: {e}")
            print(f"    SQL: {create_sql[:100]}...")
            mismatch += 1
            continue
        
        # 迁移数据
        sc.execute(f"SELECT * FROM {table}")
        rows = sc.fetchall()
        if rows:
            cols_list = [c["name"] for c in cols]
            placeholders = ", ".join(["%s"] * len(cols_list))
            insert_sql = f"INSERT INTO {table} ({', '.join([f'`{c}`' for c in cols_list])}) VALUES ({placeholders})"
            try:
                mc.executemany(insert_sql, [tuple(r) for r in rows])
                total_rows += len(rows)
                print(f"  ✅ {table}: {len(rows)} 行")
            except Exception as e:
                print(f"  ❌ {table} 迁移失败: {e}")
                mismatch += 1
                continue
        else:
            print(f"  ✅ {table}: 0 行")
    
    mysql.commit()
    mc.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    # 3. 最终校验
    print(f"\n  最终校验:")
    for table in MIGRATE_ORDER:
        try:
            sc.execute(f"SELECT COUNT(*) FROM {table}")
            sqlite_count = sc.fetchone()[0]
            mc.execute(f"SELECT COUNT(*) FROM {table}")
            mysql_count = mc.fetchone()[0]
            if sqlite_count != mysql_count:
                print(f"    ❌ {table}: SQLite={sqlite_count}, MySQL={mysql_count}")
                mismatch += 1
        except Exception as e:
            print(f"    ⚠️ {table}: 校验跳过 - {e}")
    
    sqlite.close()
    mysql.close()
    
    if mismatch == 0:
        print(f"\n[{datetime.now()}] ✅ 100% 同步成功！总计 {total_rows} 行")
        return 0
    else:
        print(f"\n[{datetime.now()}] ❌ 共 {mismatch} 个问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())
