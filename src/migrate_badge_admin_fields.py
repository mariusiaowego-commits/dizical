"""
Migration: 添加 badge 后台管理字段

新增字段：
- achievements.display_on_achievements (INTEGER DEFAULT 1)
- achievements.sort_order_override (INTEGER)
"""

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"


def migrate():
    """执行迁移"""
    conn = sqlite3.connect(_DB_PATH)
    cursor = conn.cursor()
    
    # 检查字段是否已存在
    cursor.execute("PRAGMA table_info(achievements)")
    columns = [row[1] for row in cursor.fetchall()]
    
    # 添加 display_on_achievements 字段
    if "display_on_achievements" not in columns:
        print("Adding display_on_achievements column...")
        cursor.execute("""
            ALTER TABLE achievements 
            ADD COLUMN display_on_achievements INTEGER DEFAULT 1
        """)
    
    # 添加 sort_order_override 字段
    if "sort_order_override" not in columns:
        print("Adding sort_order_override column...")
        cursor.execute("""
            ALTER TABLE achievements 
            ADD COLUMN sort_order_override INTEGER
        """)
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")


if __name__ == "__main__":
    migrate()
