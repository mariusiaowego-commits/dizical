import sqlite3
import datetime as dt
from typing import List, Optional, Dict, Any
from pathlib import Path
from .models import Lesson, Payment, LessonStatus, settings


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.db_path
        self._ensure_db_directory()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_tables()

    def _ensure_db_directory(self) -> None:
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
            # macOS 上 WAL 偶发 unable to open database file，改用默认 DELETE journal
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Lessons table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    fee INTEGER NOT NULL DEFAULT 600,
                    fee_paid BOOLEAN NOT NULL DEFAULT 0,
                    is_holiday_conflict BOOLEAN NOT NULL DEFAULT 0,
                    notes TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Payments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payment_date DATE NOT NULL,
                    amount INTEGER NOT NULL,
                    lesson_ids TEXT NOT NULL DEFAULT '',
                    payment_method TEXT NOT NULL DEFAULT '现金',
                    notes TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Practice items table (练习项目库)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS practice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category_id INTEGER REFERENCES practice_categories(id),
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Practice categories table (练习大科目)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS practice_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert default categories if empty
            cursor.execute('SELECT COUNT(*) as cnt FROM practice_categories')
            if cursor.fetchone()['cnt'] == 0:
                default_cats = [
                    ('基本功', 0),
                    ('唱', 1),
                    ('分析', 2),
                    ('小节', 3),
                    ('句子', 4),
                    ('全曲', 5),
                ]
                cursor.executemany(
                    'INSERT INTO practice_categories (name, sort_order) VALUES (?, ?)',
                    default_cats
                )

            # Daily practice audit log（数据溯源）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS practice_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    method TEXT NOT NULL,
                    practice_date DATE NOT NULL,
                    input_items JSON,
                    result_items JSON,
                    total_minutes INTEGER,
                    session_id TEXT,
                    error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_date ON practice_audit_log(practice_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_channel ON practice_audit_log(channel)')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weekly_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_date DATE NOT NULL,
                    items TEXT NOT NULL DEFAULT '[]',
                    notes TEXT,
                    images TEXT NOT NULL DEFAULT '[]',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(lesson_date)
                )
            ''')

            # Migration: add images column if missing
            cursor.execute("PRAGMA table_info(weekly_assignments)")
            wa_columns = [col['name'] for col in cursor.fetchall()]
            if 'images' not in wa_columns:
                cursor.execute('ALTER TABLE weekly_assignments ADD COLUMN images TEXT NOT NULL DEFAULT \'[]\'')

            # Migration: add stage_start / stage_end columns if missing
            cursor.execute("PRAGMA table_info(weekly_assignments)")
            wa_columns = {col['name'] for col in cursor.fetchall()}
            if 'stage_start' not in wa_columns:
                cursor.execute('ALTER TABLE weekly_assignments ADD COLUMN stage_start DATE')
                cursor.execute('ALTER TABLE weekly_assignments ADD COLUMN stage_end DATE')

                # 回填：stage_start = lesson_date + 1天，stage_end = 下一节（attended + scheduled）课日期
                cursor.execute("SELECT date FROM lessons ORDER BY date")
                all_lessons = [dt.date.fromisoformat(r[0]) for r in cursor.fetchall()]
                cursor.execute("SELECT date FROM lessons WHERE status = 'attended' ORDER BY date")
                attended_dates = [dt.date.fromisoformat(r[0]) for r in cursor.fetchall()]
                cursor.execute("SELECT id, lesson_date FROM weekly_assignments")
                for row in cursor.fetchall():
                    ld = dt.date.fromisoformat(row[1])
                    future = [d for d in all_lessons if d > ld]
                    stage_end = future[0].isoformat() if future else None
                    stage_start = (ld + dt.timedelta(days=1)).isoformat()
                    stage_order = attended_dates.index(ld) + 1 if ld in attended_dates else None
                    cursor.execute(
                        "UPDATE weekly_assignments SET stage_start = ?, stage_end = ?, stage_order = ? WHERE id = ?",
                        (stage_start, stage_end, stage_order, row[0])
                    )

            # Daily practices table (每日分项打卡)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_practices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    items TEXT NOT NULL DEFAULT '[]',
                    total_minutes INTEGER NOT NULL DEFAULT 0,
                    log TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes
            cursor.execute("PRAGMA table_info(daily_practices)")
            columns = [col['name'] for col in cursor.fetchall()]
            if 'log' not in columns:
                cursor.execute('ALTER TABLE daily_practices ADD COLUMN log TEXT')

            # Migration: add category_id if practice_items doesn't have it
            cursor.execute("PRAGMA table_info(practice_items)")
            item_columns = [col['name'] for col in cursor.fetchall()]
            if 'category_id' not in item_columns:
                cursor.execute('ALTER TABLE practice_items ADD COLUMN category_id INTEGER REFERENCES practice_categories(id)')
            if 'sort_order' not in item_columns:
                cursor.execute('ALTER TABLE practice_items ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0')
            if 'is_archived' not in item_columns:
                cursor.execute('ALTER TABLE practice_items ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0')

            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_lessons_date ON lessons(date)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_practices_date ON daily_practices(date)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_assignments_week ON weekly_assignments(lesson_date)
            ''')

            conn.commit()

    def _row_to_lesson(self, row: sqlite3.Row) -> Lesson:
        return Lesson(
            id=row['id'],
            date=dt.date.fromisoformat(row['date']),
            time=dt.time.fromisoformat(row['time']),
            status=LessonStatus(row['status']),
            fee=row['fee'],
            fee_paid=bool(row['fee_paid']),
            is_holiday_conflict=bool(row['is_holiday_conflict']),
            notes=row['notes'],
            created_at=dt.datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=dt.datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
        )

    def _row_to_payment(self, row: sqlite3.Row) -> Payment:
        return Payment(
            id=row['id'],
            payment_date=dt.date.fromisoformat(row['payment_date']),
            amount=row['amount'],
            lesson_ids=row['lesson_ids'],
            payment_method=row['payment_method'],
            notes=row['notes'],
            created_at=dt.datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        )

    # Lesson operations
    def add_lesson(self, lesson: Lesson) -> Lesson:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO lessons (date, time, status, fee, fee_paid, is_holiday_conflict, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                lesson.date.isoformat(),
                lesson.time.isoformat(),
                lesson.status.value,
                lesson.fee,
                lesson.fee_paid,
                lesson.is_holiday_conflict,
                lesson.notes,
            ))
            lesson.id = cursor.lastrowid
            conn.commit()
            return self.get_lesson(lesson.id)

    def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,))
            row = cursor.fetchone()
            return self._row_to_lesson(row) if row else None

    def get_lesson_by_date(self, lesson_date: dt.date) -> Optional[Lesson]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM lessons WHERE date = ?', (lesson_date.isoformat(),))
            row = cursor.fetchone()
            return self._row_to_lesson(row) if row else None

    def get_lessons_by_month(self, year: int, month: int) -> List[Lesson]:
        start_date = dt.date(year, month, 1)
        if month == 12:
            end_date = dt.date(year + 1, 1, 1)
        else:
            end_date = dt.date(year, month + 1, 1)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM lessons
                WHERE date >= ? AND date < ?
                ORDER BY date ASC
            ''', (start_date.isoformat(), end_date.isoformat()))
            return [self._row_to_lesson(row) for row in cursor.fetchall()]

    def get_all_lessons(self) -> List[Lesson]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM lessons ORDER BY date ASC')
            return [self._row_to_lesson(row) for row in cursor.fetchall()]

    def update_lesson(self, lesson: Lesson) -> Optional[Lesson]:
        if not lesson.id:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE lessons
                SET date = ?, time = ?, status = ?, fee = ?, fee_paid = ?,
                    is_holiday_conflict = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                lesson.date.isoformat(),
                lesson.time.isoformat(),
                lesson.status.value,
                lesson.fee,
                lesson.fee_paid,
                lesson.is_holiday_conflict,
                lesson.notes,
                lesson.id,
            ))
            conn.commit()
            return self.get_lesson(lesson.id)

    def delete_lesson(self, lesson_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
            conn.commit()
            return cursor.rowcount > 0

    def cancel_lesson_by_date(self, lesson_date: dt.date) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE lessons
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE date = ?
            ''', (LessonStatus.CANCELLED.value, lesson_date.isoformat()))
            conn.commit()
            return cursor.rowcount > 0

    # Payment operations
    def add_payment(self, payment: Payment) -> Payment:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO payments (payment_date, amount, lesson_ids, payment_method, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                payment.payment_date.isoformat(),
                payment.amount,
                payment.lesson_ids,
                payment.payment_method,
                payment.notes,
            ))
            payment.id = cursor.lastrowid
            conn.commit()
            return payment

    def get_payments_by_month(self, year: int, month: int) -> List[Payment]:
        start_date = dt.date(year, month, 1)
        if month == 12:
            end_date = dt.date(year + 1, 1, 1)
        else:
            end_date = dt.date(year, month + 1, 1)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM payments
                WHERE payment_date >= ? AND payment_date < ?
                ORDER BY payment_date ASC
            ''', (start_date.isoformat(), end_date.isoformat()))
            return [self._row_to_payment(row) for row in cursor.fetchall()]

    def get_all_payments(self) -> List[Payment]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM payments ORDER BY payment_date ASC')
            return [self._row_to_payment(row) for row in cursor.fetchall()]

    # Settings operations
    def set_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    # Practice category operations
    def add_practice_category(self, name: str, sort_order: int = 99) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO practice_categories (name, sort_order) VALUES (?, ?)
            ''', (name, sort_order))
            conn.commit()
            if cursor.rowcount == 0:
                cursor.execute('SELECT id FROM practice_categories WHERE name = ?', (name,))
                row = cursor.fetchone()
                return row['id']
            return cursor.lastrowid

    def get_practice_categories(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM practice_categories ORDER BY sort_order, name')
            return [dict(row) for row in cursor.fetchall()]

    def update_practice_category(self, cat_id: int, name: str, sort_order: Optional[int] = None) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if sort_order is not None:
                cursor.execute('UPDATE practice_categories SET name = ?, sort_order = ? WHERE id = ?',
                             (name, sort_order, cat_id))
            else:
                cursor.execute('UPDATE practice_categories SET name = ? WHERE id = ?', (name, cat_id))
            conn.commit()

    def delete_practice_category(self, cat_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 先把该分类下的小科目清空分类
            cursor.execute('UPDATE practice_items SET category_id = NULL WHERE category_id = ?', (cat_id,))
            cursor.execute('DELETE FROM practice_categories WHERE id = ?', (cat_id,))
            conn.commit()

    # Practice item operations
    def add_practice_item(self, name: str, category_id: Optional[int] = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO practice_items (name, category_id) VALUES (?, ?)
            ''', (name, category_id))
            conn.commit()
            if cursor.rowcount == 0:
                cursor.execute('SELECT item_id FROM practice_items WHERE name = ?', (name,))
                row = cursor.fetchone()
                return row['item_id']
            return cursor.lastrowid

    def get_practice_item_by_id(self, item_id: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM practice_items WHERE item_id = ?", (item_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_practice_items(self, active_only: bool = True, include_archived: bool = False) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            where = []
            if active_only:
                where.append('pi.is_active = 1')
            if not include_archived:
                where.append('pi.is_archived = 0')
            sql = 'SELECT pi.*, pc.name as category_name FROM practice_items pi LEFT JOIN practice_categories pc ON pi.category_id = pc.id'
            if where:
                sql += ' WHERE ' + ' AND '.join(where)
            sql += ' ORDER BY pc.sort_order, pi.sort_order, pi.name'
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]

    def create_practice_item(self, name: str, category_id: Optional[int] = None) -> int:
        """创建新的练习小科目，返回新条目的 item_id。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO practice_items (name, category_id, sort_order, is_active, is_archived) VALUES (?, ?, 0, 1, 0)",
                (name, category_id)
            )
            conn.commit()
            return cursor.lastrowid

    def update_practice_item_category(self, item_id: int, category_id: Optional[int]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE practice_items SET category_id = ? WHERE item_id = ?', (category_id, item_id))
            conn.commit()

    def deactivate_practice_item(self, item_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE practice_items SET is_active = 0 WHERE item_id = ?', (item_id,))
            conn.commit()

    def delete_practice_item(self, item_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM practice_items WHERE item_id = ?', (item_id,))
            conn.commit()

    def update_practice_item_name(self, item_id: int, name: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE practice_items SET name = ? WHERE item_id = ?', (name, item_id))
            conn.commit()

    def update_practice_item_sort_order(self, item_id: int, sort_order: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE practice_items SET sort_order = ? WHERE item_id = ?', (sort_order, item_id))
            conn.commit()

    def archive_practice_item(self, item_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE practice_items SET is_archived = 1 WHERE item_id = ?', (item_id,))
            conn.commit()

    def unarchive_practice_item(self, item_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE practice_items SET is_archived = 0 WHERE item_id = ?', (item_id,))
            conn.commit()

    def merge_practice_item(self, from_id: int, to_id: int, from_name: str, to_name: str) -> None:
        """
        合并两个小科目：删除 from_id，保留 to_id，
        同时把所有历史记录里的 from_name 替换为 to_name。
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. 找出所有涉及 from_name 的历史记录
            cursor.execute('SELECT date, items FROM daily_practices')
            rows = cursor.fetchall()

            # 2. 逐条检查并更新包含 from_name 的记录
            for row in rows:
                date_str, items_json = row['date'], row['items']
                try:
                    items = json.loads(items_json)
                except (json.JSONDecodeError, TypeError):
                    continue
                changed = False
                for entry in items:
                    if isinstance(entry, dict) and entry.get('item') == from_name:
                        entry['item'] = to_name
                        changed = True
                if changed:
                    cursor.execute(
                        'UPDATE daily_practices SET items = ? WHERE date = ?',
                        (json.dumps(items, ensure_ascii=False), date_str)
                    )

            # 3. 删除被合并的小科目
            cursor.execute('DELETE FROM practice_items WHERE item_id = ?', (from_id,))
            conn.commit()

    def _match_practice_item_id(self, item_name: str) -> Optional[int]:
        """将自由文本科目名 fuzzy-match 到 practice_items 表的 id，失败返回 None"""
        from difflib import SequenceMatcher
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_id, name FROM practice_items WHERE is_archived = 0")
            pi_map = {name: item_id for item_id, name in cursor.fetchall()}
        name = item_name.strip()
        if name in pi_map:
            return pi_map[name]
        for pi_name, pid in pi_map.items():
            if pi_name in name:
                return pid
        for pi_name, pid in pi_map.items():
            if name in pi_name:
                return pid
        best_ratio, best_pid = 0, None
        for pi_name, pid in pi_map.items():
            r = SequenceMatcher(None, name, pi_name).ratio()
            if r > best_ratio and r > 0.6:
                best_ratio, best_pid = r, pid
        return best_pid

    def validate_item_id(self, item_id: int) -> Optional[int]:
        """验证 item_id 是否合法（存在于 practice_items 且 is_archived=0）。无效返回 None。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT item_id FROM practice_items WHERE item_id = ? AND is_archived = 0', (item_id,))
            if cursor.fetchone():
                return item_id
            return None

    # Weekly assignment operations
    def save_weekly_assignment(self, lesson_date: dt.date, items: List[Dict], notes: Optional[str] = None, images: Optional[List[str]] = None) -> None:
        import json
        if isinstance(lesson_date, str):
            lesson_date = dt.date.fromisoformat(lesson_date)
        # 增量追加：查询现有 items，合并新旧（按 item 名称去重），再保存
        existing = self.get_weekly_assignment(lesson_date)
        if existing:
            # 按 item 名称去重：新items覆盖旧requirement，旧items保留
            existing_map = {it['item']: it for it in existing['items']}
            for new_item in items:
                existing_map[new_item['item']] = new_item
            merged_items = list(existing_map.values())
        else:
            merged_items = items

        # 补充 item_id（fuzzy match：只有 item_id 为 None/0 时才尝试匹配）
        for it in merged_items:
            if not it.get('item_id'):
                matched = self._match_practice_item_id(it['item'])
                if matched:
                    it['item_id'] = matched
            # 规范化字段名：requirement → requirements（避免新旧数据混用）
            if 'requirement' in it and 'requirements' not in it:
                it['requirements'] = it.pop('requirement')
            if 'requirements' not in it:
                it['requirements'] = ''
            if 'metronome' not in it:
                it['metronome'] = ''

        # 保留 notes（首次录入时保存，后续追加时保留原有 notes 除非明确传入）
        final_notes = notes if notes is not None else (existing['notes'] if existing else None)
        # 保留 images
        merged_images = existing['images'] if existing else []

        # 计算 stage_start = lesson_date + 1，stage_end = 下一节（attended + scheduled）课日期
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT date FROM lessons ORDER BY date")
            all_lessons = [dt.date.fromisoformat(r[0]) for r in cursor.fetchall()]
            cursor.execute("SELECT date FROM lessons WHERE status = 'attended' ORDER BY date")
            attended_dates = [dt.date.fromisoformat(r[0]) for r in cursor.fetchall()]
            stage_start = (lesson_date + dt.timedelta(days=1)).isoformat()
            future = [d for d in all_lessons if d > lesson_date]
            stage_end = future[0].isoformat() if future else None
            stage_order = attended_dates.index(lesson_date) + 1 if lesson_date in attended_dates else None

            cursor.execute('''
                INSERT OR REPLACE INTO weekly_assignments (lesson_date, stage_start, stage_end, stage_order, items, notes, images)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (lesson_date.isoformat(), stage_start, stage_end, stage_order,
                  json.dumps(merged_items, ensure_ascii=False), final_notes,
                  json.dumps(merged_images, ensure_ascii=False)))
            conn.commit()

    def get_weekly_assignment_for_week(self, anchor_date: dt.date) -> Optional[Dict]:
        """查找最接近 anchor_date 的那条作业记录（lesson_date <= anchor_date，按时间倒序取第一条）。
        这样不管家长存的是周一还是周中上课日，都能匹配到对应的自然周。"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM weekly_assignments
                WHERE lesson_date <= ?
                ORDER BY lesson_date DESC
                LIMIT 1
            ''', (anchor_date.isoformat(),))
            row = cursor.fetchone()
            if row:
                import json
                return {
                    'id': row['id'],
                    'lesson_date': dt.date.fromisoformat(row['lesson_date']),
                    'stage_start': dt.date.fromisoformat(row['stage_start']) if row['stage_start'] else None,
                    'stage_end': dt.date.fromisoformat(row['stage_end']) if row['stage_end'] else None,
                    'stage_order': row['stage_order'],
                    'items': json.loads(row['items']),
                    'notes': row['notes'],
                    'images': json.loads(row['images']) if row['images'] else []
                }
            return None

    def get_weekly_assignment(self, week_start: dt.date) -> Optional[Dict]:
        """查找指定自然周（week_start 为周一）的作业记录。
        找该周最接近的 lesson_date（上课日），返回对应的作业。"""
        if isinstance(week_start, str):
            week_start = dt.date.fromisoformat(week_start)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            week_end = week_start + dt.timedelta(days=6)
            cursor.execute('''
                SELECT * FROM weekly_assignments
                WHERE lesson_date >= ? AND lesson_date <= ?
                ORDER BY lesson_date DESC
                LIMIT 1
            ''', (week_start.isoformat(), week_end.isoformat()))
            row = cursor.fetchone()
            if row:
                import json
                return {
                    'id': row['id'],
                    'lesson_date': dt.date.fromisoformat(row['lesson_date']),
                    'stage_start': dt.date.fromisoformat(row['stage_start']) if row['stage_start'] else None,
                    'stage_end': dt.date.fromisoformat(row['stage_end']) if row['stage_end'] else None,
                    'stage_order': row['stage_order'],
                    'items': json.loads(row['items']),
                    'notes': row['notes'],
                    'images': json.loads(row['images']) if row['images'] else []
                }
            return None

    def get_weekly_assignments_in_range(self, start: dt.date, end: dt.date) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM weekly_assignments
                WHERE lesson_date >= ? AND lesson_date <= ?
                ORDER BY lesson_date
            ''', (start.isoformat(), end.isoformat()))
            import json
            return [{
                'id': row['id'],
                'lesson_date': dt.date.fromisoformat(row['lesson_date']),
                'stage_start': dt.date.fromisoformat(row['stage_start']) if row['stage_start'] else None,
                'stage_end': dt.date.fromisoformat(row['stage_end']) if row['stage_end'] else None,
                'stage_order': row['stage_order'],
                'items': json.loads(row['items']),
                'notes': row['notes'],
                'images': json.loads(row['images']) if row['images'] else []
            } for row in cursor.fetchall()]

    # Daily practice operations
    def save_daily_practice(self, date: dt.date, items: List[Dict], total_minutes: int, log: Optional[str] = None, practiced: str = 'Y',
                            channel: Optional[str] = None, method: Optional[str] = None, session_id: Optional[str] = None) -> None:
        import json
        if isinstance(date, str):
            date = dt.date.fromisoformat(date)
        input_items = list(items)  # 原始输入，用于 audit log
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # BEGIN IMMEDIATE 获取写锁，防止并发覆盖
            cursor.execute('BEGIN IMMEDIATE')

            # 验证所有 item_id 合法性，无效则抛异常
            for it in items:
                vid = it.get('item_id')
                if vid is None:
                    raise ValueError(f"科目 {it.get('item')} 缺少 item_id")
                cursor.execute('SELECT item_id FROM practice_items WHERE item_id = ? AND is_archived = 0', (vid,))
                if not cursor.fetchone():
                    raise ValueError(f"科目 ID {vid}（{it.get('item')}）不存在或已归档")

            cursor.execute('SELECT items, log, practiced FROM daily_practices WHERE date = ?', (date.isoformat(),))
            row = cursor.fetchone()
            if row:
                existing_items = json.loads(row[0]) if row[0] else []
                existing_log = row[1] or ''
                existing_practiced = row[2] or 'Y'

                # 合并 items：同名累加分钟数，不同则追加
                for it in items:
                    found = False
                    for ex in existing_items:
                        if ex.get('item') == it['item']:
                            ex['minutes'] += it['minutes']
                            found = True
                            break
                    if not found:
                        existing_items.append(it)
                merged_items = existing_items
                merged_total = sum(it.get('minutes', 0) for it in merged_items)
                merged_log = (existing_log + '\n' + log).strip() if log else existing_log
                final_practiced = 'Y' if merged_total > 0 else existing_practiced
                cursor.execute('''
                    UPDATE daily_practices
                    SET items = ?, total_minutes = ?, log = ?, practiced = ?
                    WHERE date = ?
                ''', (json.dumps(merged_items, ensure_ascii=False), merged_total, merged_log, final_practiced, date.isoformat()))
                audit_items = merged_items
                audit_total = merged_total
            else:
                # 新建记录
                cursor.execute('''
                    INSERT INTO daily_practices (date, items, total_minutes, log, practiced)
                    VALUES (?, ?, ?, ?, ?)
                ''', (date.isoformat(), json.dumps(items, ensure_ascii=False), total_minutes, log, practiced))
                audit_items = items
                audit_total = total_minutes
            conn.commit()

        # audit log 写在事务外（事务已提交，不会被回滚）
        if channel and method:
            self.log_practice_audit(channel, method, date, input_items, audit_items, audit_total, session_id=session_id)

    def log_practice_audit(self, channel: str, method: str, practice_date: dt.date,
                           input_items: List[Dict], result_items: List[Dict],
                           total_minutes: int, error: Optional[str] = None,
                           session_id: Optional[str] = None) -> None:
        """写一条练习录入审计日志（数据溯源用）"""
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO practice_audit_log
                (channel, method, practice_date, input_items, result_items, total_minutes, error, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (channel, method, practice_date.isoformat(),
                  json.dumps(input_items, ensure_ascii=False),
                  json.dumps(result_items, ensure_ascii=False),
                  total_minutes, error, session_id))
            conn.commit()

    def append_behavior_log(self, date: dt.date, entry: Dict) -> None:
        """追加一条行为日志到当天的 behavior_log JSON 数组"""
        import json
        if isinstance(date, str):
            date = dt.date.fromisoformat(date)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('BEGIN IMMEDIATE')
            cursor.execute('SELECT behavior_log FROM daily_practices WHERE date = ?', (date.isoformat(),))
            row = cursor.fetchone()
            if row:
                log_list = json.loads(row[0]) if row[0] else []
            else:
                log_list = []
            log_list.append(entry)
            cursor.execute('''
                UPDATE daily_practices SET behavior_log = ? WHERE date = ?
            ''', (json.dumps(log_list, ensure_ascii=False), date.isoformat()))
            conn.commit()

    @staticmethod
    def _normalize_items(raw) -> List[Dict]:
        """
        兼容旧数据格式：将 ['item1', 'item2'] 字符串列表
        规范化为 [{'item': 'item1', 'minutes': 0}, ...]
        正常格式直接返回。
        """
        import json
        items = json.loads(raw) if isinstance(raw, str) else raw
        if not items:
            return []
        if items and isinstance(items[0], str):
            return [{'item': name, 'minutes': 0} for name in items]
        return items

    def remove_daily_practice_record_by_id(self, date: dt.date, item_id: int) -> None:
        """根据日期和 item_id 从 JSON items 数组中删除指定项目"""
        import json as _json
        existing = self.get_daily_practice(date)
        if not existing:
            return
        items = existing.get("items", [])
        new_items = [it for it in items if it.get("item_id") != item_id]
        if not new_items:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM daily_practices WHERE date = ?', (date.isoformat(),))
                conn.commit()
        else:
            new_total = sum(it.get("minutes", 0) for it in new_items)
            # 直接写 DB，绕过 save_daily_practice 的合并逻辑，避免旧数据干扰
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_practices (date, items, total_minutes, log, practiced)
                    VALUES (?, ?, ?, ?, ?)
                ''', (date.isoformat(), _json.dumps(new_items, ensure_ascii=False),
                      new_total, existing.get("log", ""), 'Y'))
                conn.commit()

    def remove_daily_practice_item(self, date: dt.date, item_name: str) -> None:
        """从指定日期的练习记录中删除一个项目（减少其分钟数），若无其他项目则删除整条记录"""
        existing = self.get_daily_practice(date)
        if not existing:
            return
        items = existing.get("items", [])
        new_items = [it for it in items if it.get("item") != item_name]
        if not new_items:
            # 删除整条记录
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM daily_practices WHERE date = ?', (date.isoformat(),))
                conn.commit()
        else:
            new_total = sum(it.get("minutes", 0) for it in new_items)
            self.save_daily_practice(date, new_items, new_total, existing.get("log"),
                                   channel='internal', method='remove_record')

    def get_daily_practice(self, date: dt.date) -> Optional[Dict]:
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM daily_practices WHERE date = ?', (date.isoformat(),))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'date': dt.date.fromisoformat(row['date']),
                    'items': self._normalize_items(row['items']),
                    'total_minutes': row['total_minutes'],
                    'log': row['log'],
                    'practiced': row['practiced'] if 'practiced' in row.keys() else 'Y',
                    'behavior_log': json.loads(row['behavior_log']) if 'behavior_log' in row.keys() else [],
                }
            return None

    def get_daily_practices_in_range(self, start: dt.date, end: dt.date) -> List[Dict]:
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM daily_practices
                WHERE date >= ? AND date <= ?
                ORDER BY date
            ''', (start.isoformat(), end.isoformat()))
            return [{
                'id': row['id'],
                'date': dt.date.fromisoformat(row['date']),
                'items': self._normalize_items(row['items']),
                'total_minutes': row['total_minutes'],
                'log': row['log'],
                'practiced': row['practiced'] if 'practiced' in row.keys() else 'Y',
                'behavior_log': json.loads(row['behavior_log']) if 'behavior_log' in row.keys() else [],
            } for row in cursor.fetchall()]

    # ─── Progress → daily_practices.log ───────────────────────────────────────
    def save_progress_to_log(self, date: dt.date, note: str) -> None:
        """
        将一句话进展追加到 daily_practices.log。
        有打卡记录 → 追加到 log；无打卡 → 创建仅有 log 的记录。
        """
        existing = self.get_daily_practice(date)
        if existing:
            existing_log = existing.get('log') or ''
            new_log = f"{existing_log}\n{note}".strip()
            self.save_daily_practice(date, existing['items'], existing['total_minutes'], new_log,
                                   channel='internal', method='note')
        else:
            self.save_daily_practice(date, [], 0, note, practiced='N',
                                   channel='internal', method='note')

    def get_progress_from_log(self, date: dt.date) -> Optional[str]:
        """读取某日的进展（从 daily_practices.log，取第一条非空行）"""
        row = self.get_daily_practice(date)
        if not row or not row.get('log'):
            return None
        lines = [l.strip() for l in row['log'].splitlines() if l.strip()]
        return lines[0] if lines else None

    def get_progress_from_log_in_range(self, start: dt.date, end: dt.date) -> Dict[str, str]:
        """读取日期区间内所有进展摘要（每天取 log 第一行）"""
        practices = self.get_daily_practices_in_range(start, end)
        result = {}
        for p in practices:
            log = p.get('log')
            if log:
                lines = [l.strip() for l in log.splitlines() if l.strip()]
                if lines:
                    result[p['date'].isoformat()] = lines[0]
        return result

    # ─── 一次性迁移：daily_progress → daily_practices.log ────────────────────
    def migrate_daily_progress_to_log(self) -> int:
        """
        将 daily_progress 表的所有 note 迁移到 daily_practices.log。
        返回迁移条数。
        """
        import json
        migrated = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT date, note FROM daily_progress ORDER BY date')
            for row in cursor.fetchall():
                date = dt.date.fromisoformat(row['date'])
                note = row['note']
                if not note:
                    continue
                # 读取现有 daily_practice（如果有）
                cursor2 = conn.cursor()
                cursor2.execute('SELECT items, total_minutes, log FROM daily_practices WHERE date = ?',
                                (date.isoformat(),))
                existing_row = cursor2.fetchone()
                if existing_row:
                    items = json.loads(existing_row['items'] or '[]')
                    total = existing_row['total_minutes'] or 0
                    existing_log = existing_row['log'] or ''
                    new_log = f"{existing_log}\n{note}".strip() if existing_log else note
                    cursor2.execute('''
                        UPDATE daily_practices SET items=?, total_minutes=?, log=?
                        WHERE date=?
                    ''', (json.dumps(items), total, new_log, date.isoformat()))
                else:
                    cursor2.execute('''
                        INSERT INTO daily_practices (date, items, total_minutes, log)
                        VALUES (?, '[]', 0, ?)
                    ''', (date.isoformat(), note))
                migrated += 1
            conn.commit()
        return migrated


# Global database instance
db = Database()
