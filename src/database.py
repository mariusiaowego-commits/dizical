import sqlite3
import datetime as dt
from typing import List, Optional, Dict, Any
from pathlib import Path
from .models import Lesson, Payment, LessonStatus, settings


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.db_path
        self._ensure_db_directory()
        self._init_tables()

    def _ensure_db_directory(self) -> None:
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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

            # Weekly assignments table (每周老师要求)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weekly_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_start_date DATE NOT NULL,
                    items TEXT NOT NULL DEFAULT '[]',
                    notes TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(week_start_date)
                )
            ''')

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

            # Daily progress table (每日一句话进展)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    note TEXT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Migration: add log column if daily_practices doesn't have it
            cursor.execute("PRAGMA table_info(daily_practices)")
            columns = [col['name'] for col in cursor.fetchall()]
            if 'log' not in columns:
                cursor.execute('ALTER TABLE daily_practices ADD COLUMN log TEXT')

            # Migration: add category_id if practice_items doesn't have it
            cursor.execute("PRAGMA table_info(practice_items)")
            item_columns = [col['name'] for col in cursor.fetchall()]
            if 'category_id' not in item_columns:
                cursor.execute('ALTER TABLE practice_items ADD COLUMN category_id INTEGER REFERENCES practice_categories(id)')

            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_lessons_date ON lessons(date)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_practices_date ON daily_practices(date)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_progress_date ON daily_progress(date)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_assignments_week ON weekly_assignments(week_start_date)
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
                cursor.execute('SELECT id FROM practice_items WHERE name = ?', (name,))
                row = cursor.fetchone()
                return row['id']
            return cursor.lastrowid

    def get_practice_items(self, active_only: bool = True) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute('SELECT pi.*, pc.name as category_name FROM practice_items pi LEFT JOIN practice_categories pc ON pi.category_id = pc.id WHERE pi.is_active = 1 ORDER BY pc.sort_order, pi.name')
            else:
                cursor.execute('SELECT pi.*, pc.name as category_name FROM practice_items pi LEFT JOIN practice_categories pc ON pi.category_id = pc.id ORDER BY pc.sort_order, pi.name')
            return [dict(row) for row in cursor.fetchall()]

    def update_practice_item_category(self, item_id: int, category_id: Optional[int]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE practice_items SET category_id = ? WHERE id = ?', (category_id, item_id))
            conn.commit()

    def deactivate_practice_item(self, item_id: int) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE practice_items SET is_active = 0 WHERE id = ?', (item_id,))
            conn.commit()

    # Weekly assignment operations
    def save_weekly_assignment(self, week_start_date: dt.date, items: List[Dict], notes: Optional[str] = None) -> None:
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO weekly_assignments (week_start_date, items, notes)
                VALUES (?, ?, ?)
            ''', (week_start_date.isoformat(), json.dumps(items, ensure_ascii=False), notes))
            conn.commit()

    def get_weekly_assignment(self, week_start_date: dt.date) -> Optional[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM weekly_assignments WHERE week_start_date = ?', (week_start_date.isoformat(),))
            row = cursor.fetchone()
            if row:
                import json
                return {
                    'id': row['id'],
                    'week_start_date': dt.date.fromisoformat(row['week_start_date']),
                    'items': json.loads(row['items']),
                    'notes': row['notes']
                }
            return None

    def get_weekly_assignments_in_range(self, start: dt.date, end: dt.date) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM weekly_assignments
                WHERE week_start_date >= ? AND week_start_date <= ?
                ORDER BY week_start_date
            ''', (start.isoformat(), end.isoformat()))
            import json
            return [{
                'id': row['id'],
                'week_start_date': dt.date.fromisoformat(row['week_start_date']),
                'items': json.loads(row['items']),
                'notes': row['notes']
            } for row in cursor.fetchall()]

    # Daily practice operations
    def save_daily_practice(self, date: dt.date, items: List[Dict], total_minutes: int, log: Optional[str] = None) -> None:
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_practices (date, items, total_minutes, log)
                VALUES (?, ?, ?, ?)
            ''', (date.isoformat(), json.dumps(items, ensure_ascii=False), total_minutes, log))
            conn.commit()

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
                    'items': json.loads(row['items']),
                    'total_minutes': row['total_minutes'],
                    'log': row['log']
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
                'items': json.loads(row['items']),
                'total_minutes': row['total_minutes'],
                'log': row['log']
            } for row in cursor.fetchall()]

    # Daily progress operations
    def save_daily_progress(self, date: dt.date, note: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_progress (date, note)
                VALUES (?, ?)
            ''', (date.isoformat(), note))
            conn.commit()

    def get_daily_progress(self, date: dt.date) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT note FROM daily_progress WHERE date = ?', (date.isoformat(),))
            row = cursor.fetchone()
            return row['note'] if row else None

    def get_daily_progress_in_range(self, start: dt.date, end: dt.date) -> Dict[str, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT date, note FROM daily_progress
                WHERE date >= ? AND date <= ?
                ORDER BY date
            ''', (start.isoformat(), end.isoformat()))
            return {dt.date.fromisoformat(row['date']): row['note'] for row in cursor.fetchall()}


# Global database instance
db = Database()
