#!/usr/bin/env python3
"""
安全同步：本地 SQLite → 云 MySQL (merge-only, 不覆盖)
策略：
  1. 补 MySQL 缺列 (practice_items: last_tempo_note/bpm/session_at)
  2. 建 MySQL 缺表 (practice_sessions)
  3. 逐表 INSERT IGNORE (不更新已有行)
"""

import sqlite3, pymysql, sys, json

LOCAL_DB = '/Users/mt16/dev/dizical/data/dizi.db'
MYSQL = {
    'host': 'sh-cynosdbmysql-grp-7phqjce6.sql.tencentcdb.com',
    'port': 21743, 'user': 'dizical', 'password': 'Qpwoei1234',
    'database': 'cloud1-d4gfwyvsk1435e2e4',
    'charset': 'utf8mb4', 'connect_timeout': 10,
}

def main():
    local = sqlite3.connect(LOCAL_DB); local.row_factory = sqlite3.Row
    cloud = pymysql.connect(**MYSQL)

    print("=== 本地 SQLite → 云 MySQL 安全合并同步 ===\n")

    # ─── Step 0: 补 MySQL 缺列 ───
    print("[0] 补 MySQL practice_items 缺列 (last_tempo_note/bpm/session_at)...")
    for col, typedef in [
        ('last_tempo_note', 'TEXT'),
        ('last_tempo_bpm', 'INTEGER'),
        ('last_session_at', 'DATETIME'),
    ]:
        try:
            cloud.cursor().execute(f"ALTER TABLE practice_items ADD COLUMN {col} {typedef}")
            print(f"  + {col} ({typedef})")
        except pymysql.err.OperationalError as e:
            if 'Duplicate column' in str(e):
                print(f"  ✓ {col} 已存在")
            else:
                raise
    cloud.commit()

    # ─── Step 1: practice_sessions 建表 ───
    print("\n[1] practice_sessions 建表 + 数据同步...")
    cloud.cursor().execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            practice_date DATE NOT NULL,
            item_id INTEGER NOT NULL,
            item_name TEXT,
            duration_minutes INTEGER NOT NULL DEFAULT 0,
            tempo_note TEXT,
            tempo_bpm INTEGER DEFAULT 80,
            content TEXT,
            content_source TEXT,
            is_extra TINYINT(1) DEFAULT 0,
            started_at TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_ps_item (item_id),
            INDEX idx_ps_date (practice_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cloud.commit()

    rows = local.execute('SELECT * FROM practice_sessions ORDER BY id').fetchall()
    ins = 0
    for row in rows:
        d = dict(row); d.setdefault('is_extra', False)
        try:
            cloud.cursor().execute(
                """INSERT IGNORE INTO practice_sessions
                   (id,practice_date,item_id,item_name,duration_minutes,
                    tempo_note,tempo_bpm,content,content_source,is_extra,started_at,created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d['id'], d['practice_date'], d['item_id'], d.get('item_name'),
                 d['duration_minutes'], d.get('tempo_note','♪'), d.get('tempo_bpm',80),
                 d.get('content',''), d.get('content_source','manual'),
                 int(d['is_extra'] or 0), d.get('started_at'), d.get('created_at')))
            ins += 1
        except Exception as e:
            print(f"  SKIP id={d['id']}: {e}")
    cloud.commit()
    print(f"  → {ins} rows\n")

    # ─── Step 2: daily_practices INSERT IGNORE ───
    print("[2] daily_practices...")
    rows = local.execute('SELECT * FROM daily_practices ORDER BY date').fetchall()
    ins = 0
    for row in rows:
        d = dict(row)
        try:
            cloud.cursor().execute(
                """INSERT IGNORE INTO daily_practices
                   (id,date,items,total_minutes,created_at,log,practiced,behavior_log,practice_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d['id'], d['date'], d['items'], d['total_minutes'],
                 d.get('created_at'), d.get('log'), d.get('practiced'),
                 d.get('behavior_log'), d.get('practice_at')))
            ins += 1
        except Exception as e:
            print(f"  SKIP date={d['date']}: {e}")
    cloud.commit()
    print(f"  → {ins} rows\n")

    # ─── Step 3: lessons ───
    print("[3] lessons...")
    rows = local.execute('SELECT * FROM lessons ORDER BY date').fetchall()
    ins = 0
    for row in rows:
        d = dict(row)
        try:
            cloud.cursor().execute(
                """INSERT IGNORE INTO lessons
                   (id,date,time,status,fee,fee_paid,is_holiday_conflict,notes,created_at,updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d['id'], d['date'], d['time'], d['status'], d['fee'],
                 d['fee_paid'], d.get('is_holiday_conflict',False),
                 d.get('notes'), d.get('created_at'), d.get('updated_at')))
            ins += 1
        except Exception as e:
            print(f"  SKIP date={d['date']}: {e}")
    cloud.commit()
    print(f"  → {ins} rows\n")

    # ─── Step 4: practice_audit_log ───
    print("[4] practice_audit_log...")
    rows = local.execute('SELECT * FROM practice_audit_log ORDER BY id').fetchall()
    ins = 0
    for row in rows:
        d = dict(row)
        try:
            cloud.cursor().execute(
                """INSERT IGNORE INTO practice_audit_log
                   (id,channel,method,practice_date,input_items,result_items,
                    total_minutes,session_id,error,created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d['id'], d['channel'], d['method'], d['practice_date'],
                 d.get('input_items'), d.get('result_items'), d.get('total_minutes'),
                 d.get('session_id'), d.get('error'), d.get('created_at')))
            ins += 1
        except Exception as e:
            print(f"  SKIP id={d['id']}: {e}")
    cloud.commit()
    print(f"  → {ins} rows\n")

    # ─── Step 5: practice_items (INSERT IGNORE by name, MySQL PK=item_id) ───
    print("[5] practice_items (补 last_tempo 列)...")
    rows = local.execute('SELECT * FROM practice_items ORDER BY item_id').fetchall()
    ins, upd = 0, 0
    for row in rows:
        d = dict(row)
        try:
            cloud.cursor().execute(
                """INSERT IGNORE INTO practice_items
                   (item_id,name,category_id,sort_order,is_active,is_archived,created_at,
                    last_tempo_note,last_tempo_bpm,last_session_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d['item_id'], d['name'], d.get('category_id'), d.get('sort_order',0),
                 d.get('is_active',1), d.get('is_archived',0), d.get('created_at'),
                 d.get('last_tempo_note'), d.get('last_tempo_bpm'), d.get('last_session_at')))
            # if IGNORE skipped (duplicate), UPDATE the tempo columns
            if cloud.cursor().rowcount == 0:
                cloud.cursor().execute(
                    """UPDATE practice_items SET
                       last_tempo_note=%s, last_tempo_bpm=%s, last_session_at=%s
                       WHERE item_id=%s""",
                    (d.get('last_tempo_note'), d.get('last_tempo_bpm'),
                     d.get('last_session_at'), d['item_id']))
                upd += 1
            else:
                ins += 1
        except Exception as e:
            print(f"  SKIP name={d['name']}: {e}")
    cloud.commit()
    print(f"  → {ins} insert + {upd} update\n")

    # ─── Step 6: settings ───
    print("[6] settings...")
    rows = local.execute('SELECT * FROM settings ORDER BY key').fetchall()
    ins = 0
    for row in rows:
        d = dict(row)
        try:
            cloud.cursor().execute(
                "INSERT IGNORE INTO settings (`key`, value, updated_at) VALUES (%s,%s,%s)",
                (d['key'], d['value'], d.get('updated_at')))
            ins += 1
        except Exception as e:
            print(f"  SKIP key={d['key']}: {e}")
    cloud.commit()
    print(f"  → {ins} rows\n")

    # ─── Step 7: 其余表 (已等行) skip, 只报差异 ───
    other_tables = ['practice_categories','weekly_assignments','payments',
                    'achievements','achievement_stats','achievement_badges',
                    'practice_reports','report_artifacts','schema_migrations']
    for t in other_tables:
        lc = local.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
        cloud.cursor().execute(f'SELECT COUNT(*) FROM {t}')
        cc = cloud.cursor().fetchone()[0]
        if lc != cc:
            print(f"  ⚠ {t}: local={lc} cloud={cc} — 未同步 (需人工检查)")

    # ─── Summary ───
    print("\n=== 同步完成 ===")
    for t in ['practice_sessions','daily_practices','lessons','practice_audit_log','practice_items']:
        cloud.cursor().execute(f'SELECT COUNT(*) FROM {t}')
        cc = cloud.cursor().fetchone()[0]
        lc = local.execute(f'SELECT COUNT(*) FROM [{t}]').fetchone()[0]
        ok = "✓" if cc >= lc else f"⚠ {cc}<{lc}"
        print(f"  {t}: cloud={cc} local={lc} {ok}")

    cloud.cursor().execute("SELECT MAX(date) FROM daily_practices")
    print(f"  latest daily_practices: cloud={cloud.cursor().fetchone()[0]}")

    local.close(); cloud.close()

if __name__ == '__main__':
    main()
