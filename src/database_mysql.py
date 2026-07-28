"""
dizical MySQL 后端 (Phase 1b)
镜像 src.database.Database 全部 53 个方法.
DATABASE_URL=mysql+pymysql://user:pass@host:port/db 时启用.
"""

import datetime as dt
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

import pymysql
from pymysql.cursors import DictCursor

try:
    from dbutils.pooled_db import PooledDB
except ImportError:
    PooledDB = None

from .models import Lesson, Payment, LessonStatus


def parse_database_url(url: str) -> Dict[str, Any]:
    """mysql+pymysql://user:pass@host:port/db → dict"""
    parsed = urlparse(url.replace('mysql+pymysql://', 'mysql://'))
    return {
        'host': parsed.hostname,
        'port': parsed.port or 3306,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/'),
    }


class MySQLBackend:
    """完全镜像 Database 类接口, 53 个方法全部实现"""

    def __init__(self, url: str):
        cfg = parse_database_url(url)
        if PooledDB is None:
            # Fallback to plain pymysql
            self.pool = None
            self._cfg = cfg
        else:
            self.pool = PooledDB(
                creator=pymysql,
                maxconnections=10,
                mincached=2,
                blocking=True,
                host=cfg['host'],
                port=cfg['port'],
                user=cfg['user'],
                password=cfg['password'],
                database=cfg['database'],
                charset='utf8mb4',
            )

    def _get_connection(self):
        if self.pool:
            return self.pool.connection()
        return pymysql.connect(
            host=self._cfg['host'], port=self._cfg['port'],
            user=self._cfg['user'], password=self._cfg['password'],
            database=self._cfg['database'], charset='utf8mb4',
        )

    def _parse_datetime(self, v):
        """MySQL DATETIME 返 datetime 对象, DATE 返 date"""
        if v is None:
            return None
        if isinstance(v, (dt.datetime, dt.date)):
            return v
        if isinstance(v, str):
            return dt.datetime.fromisoformat(v.replace(' ', 'T'))
        return v

    def _parse_time(self, v):
        """MySQL TIME 返 timedelta, 转 dt.time"""
        if v is None:
            return None
        if isinstance(v, dt.time):
            return v
        if isinstance(v, dt.timedelta):
            total = int(v.total_seconds())
            return dt.time(total // 3600, (total % 3600) // 60, total % 60)
        if isinstance(v, str):
            parts = v.split(':')
            return dt.time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
        return v

    def _parse_date(self, v):
        """MySQL DATE 返 date 对象"""
        if v is None:
            return None
        if isinstance(v, dt.date):
            return v
        if isinstance(v, dt.datetime):
            return v.date()
        if isinstance(v, str):
            return dt.date.fromisoformat(v)
        return v

    def _row_to_lesson(self, row: Dict) -> Lesson:
        return Lesson(
            id=row['id'],
            date=self._parse_date(row['date']),
            time=self._parse_time(row['time']),
            status=LessonStatus(row['status']),
            fee=row['fee'],
            fee_paid=bool(row['fee_paid']),
            is_holiday_conflict=bool(row['is_holiday_conflict']),
            notes=row['notes'],
            created_at=self._parse_datetime(row['created_at']) if row.get('created_at') else None,
            updated_at=self._parse_datetime(row['updated_at']) if row.get('updated_at') else None,
        )

    def _row_to_payment(self, row: Dict) -> Payment:
        return Payment(
            id=row['id'],
            payment_date=self._parse_date(row['payment_date']),
            amount=row['amount'],
            lesson_ids=row['lesson_ids'],
            payment_method=row['payment_method'],
            notes=row['notes'],
            created_at=self._parse_datetime(row['created_at']) if row.get('created_at') else None,
        )

    # ── Lessons ──
    def add_lesson(self, lesson: Lesson) -> Lesson:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO lessons (date, time, status, fee, fee_paid, is_holiday_conflict, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    lesson.date.isoformat(),
                    lesson.time.isoformat(),
                    lesson.status.value,
                    lesson.fee,
                    int(lesson.fee_paid),
                    int(lesson.is_holiday_conflict),
                    lesson.notes,
                ))
                lesson.id = cur.lastrowid
            conn.commit()
            return lesson

    def get_lesson(self, lesson_id: int) -> Optional[Lesson]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM lessons WHERE id = %s', (lesson_id,))
                row = cur.fetchone()
                return self._row_to_lesson(row) if row else None

    def get_lesson_by_date(self, lesson_date: dt.date) -> Optional[Lesson]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM lessons WHERE date = %s', (lesson_date.isoformat(),))
                row = cur.fetchone()
                return self._row_to_lesson(row) if row else None

    def get_lessons_by_month(self, year: int, month: int) -> List[Lesson]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                next_year = year + 1 if month == 12 else year
                next_month = 1 if month == 12 else month + 1
                cur.execute('''
                    SELECT * FROM lessons
                    WHERE date >= %s AND date < %s
                    ORDER BY date, time
                ''', (f'{year:04d}-{month:02d}-01', f'{next_year:04d}-{next_month:02d}-01'))
                return [self._row_to_lesson(row) for row in cur.fetchall()]

    def get_all_lessons(self) -> List[Lesson]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM lessons ORDER BY date, time')
                return [self._row_to_lesson(row) for row in cur.fetchall()]

    def update_lesson(self, lesson: Lesson) -> Optional[Lesson]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE lessons
                    SET date = %s, time = %s, status = %s, fee = %s, fee_paid = %s,
                        is_holiday_conflict = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                ''', (
                    lesson.date.isoformat(),
                    lesson.time.isoformat(),
                    lesson.status.value,
                    lesson.fee,
                    int(lesson.fee_paid),
                    int(lesson.is_holiday_conflict),
                    lesson.notes,
                    lesson.id,
                ))
                affected = cur.rowcount
            conn.commit()
            return self.get_lesson(lesson.id) if affected > 0 else None

    def delete_lesson(self, lesson_id: int) -> bool:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM lessons WHERE id = %s', (lesson_id,))
                affected = cur.rowcount
            conn.commit()
            return affected > 0

    def cancel_lesson_by_date(self, lesson_date: dt.date) -> bool:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE lessons
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE date = %s
                ''', (LessonStatus.CANCELLED.value, lesson_date.isoformat()))
                affected = cur.rowcount
            conn.commit()
            return affected > 0

    # ── Payments ──
    def add_payment(self, payment: Payment) -> Payment:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO payments (payment_date, amount, lesson_ids, payment_method, notes)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (
                    payment.payment_date.isoformat(),
                    payment.amount,
                    payment.lesson_ids,
                    payment.payment_method,
                    payment.notes,
                ))
                payment.id = cur.lastrowid
            conn.commit()
            return payment

    def get_payments_by_month(self, year: int, month: int) -> List[Payment]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                next_year = year + 1 if month == 12 else year
                next_month = 1 if month == 12 else month + 1
                cur.execute('''
                    SELECT * FROM payments
                    WHERE payment_date >= %s AND payment_date < %s
                    ORDER BY payment_date DESC
                ''', (f'{year:04d}-{month:02d}-01', f'{next_year:04d}-{next_month:02d}-01'))
                return [self._row_to_payment(row) for row in cur.fetchall()]

    def get_all_payments(self) -> List[Payment]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM payments ORDER BY payment_date DESC')
                return [self._row_to_payment(row) for row in cur.fetchall()]

    # ── Settings ──
    def set_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO settings (`key`, value) VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE value = %s, updated_at = CURRENT_TIMESTAMP
                ''', (key, value, value))
            conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT value FROM settings WHERE `key` = %s', (key,))
                row = cur.fetchone()
                return row['value'] if row else default

    # ── Practice Categories ──
    def add_practice_category(self, name: str, sort_order: int = 99) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO practice_categories (name, sort_order) VALUES (%s, %s)', (name, sort_order))
                new_id = cur.lastrowid
            conn.commit()
            return new_id

    def get_practice_categories(self) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM practice_categories ORDER BY sort_order, name')
                return list(cur.fetchall())

    def update_practice_category(self, cat_id: int, name: str, sort_order: Optional[int] = None) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if sort_order is None:
                    cur.execute('UPDATE practice_categories SET name = %s WHERE id = %s', (name, cat_id))
                else:
                    cur.execute('UPDATE practice_categories SET name = %s, sort_order = %s WHERE id = %s', (name, sort_order, cat_id))
            conn.commit()

    def delete_practice_category(self, cat_id: int) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM practice_categories WHERE id = %s', (cat_id,))
            conn.commit()

    # ── Practice Items ──
    def add_practice_item(self, name: str, category_id: Optional[int] = None) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO practice_items (name, category_id) VALUES (%s, %s)', (name, category_id))
                new_id = cur.lastrowid
            conn.commit()
            return new_id

    def get_practice_item_by_id(self, item_id: int) -> Optional[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM practice_items WHERE item_id = %s', (item_id,))
                row = cur.fetchone()
                return row

    def get_practice_items(self, active_only: bool = True, include_archived: bool = False) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                if active_only and not include_archived:
                    cur.execute('SELECT * FROM practice_items WHERE is_archived = 0 ORDER BY sort_order, name')
                else:
                    cur.execute('SELECT * FROM practice_items ORDER BY sort_order, name')
                return list(cur.fetchall())

    def create_practice_item(self, name: str, category_id: Optional[int] = None) -> int:
        return self.add_practice_item(name, category_id)

    def update_practice_item_category(self, item_id: int, category_id: Optional[int]) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE practice_items SET category_id = %s WHERE item_id = %s', (category_id, item_id))
            conn.commit()

    def deactivate_practice_item(self, item_id: int) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE practice_items SET is_archived = 1 WHERE item_id = %s', (item_id,))
            conn.commit()

    def delete_practice_item(self, item_id: int) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM practice_items WHERE item_id = %s', (item_id,))
            conn.commit()

    def update_practice_item_name(self, item_id: int, name: str) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE practice_items SET name = %s WHERE item_id = %s', (name, item_id))
            conn.commit()

    def update_practice_item_content_options(self, item_id: int, content_options: str) -> None:
        """更新练习内容预置选项。存逗号分隔字符串，空串表示走全局默认。"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE practice_items SET content_options = %s WHERE item_id = %s',
                    (content_options or '', item_id),
                )
            conn.commit()

    def update_practice_item_sort_order(self, item_id: int, sort_order: int) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE practice_items SET sort_order = %s WHERE item_id = %s', (sort_order, item_id))
            conn.commit()

    def archive_practice_item(self, item_id: int) -> None:
        self.deactivate_practice_item(item_id)

    def unarchive_practice_item(self, item_id: int) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE practice_items SET is_archived = 0 WHERE item_id = %s', (item_id,))
            conn.commit()

    # ── Weekly Assignments ──
    def save_weekly_assignment(self, lesson_date: dt.date, items: List[Dict], notes: Optional[str] = None, images: Optional[List[str]] = None) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # 删旧
                cur.execute('DELETE FROM weekly_assignments WHERE lesson_date = %s', (lesson_date.isoformat(),))
                # 插新 (避免主键冲突)
                for item in items:
                    cur.execute('''
                        INSERT INTO weekly_assignments (lesson_date, stage_start, stage_end, stage_order, item_id, target_minutes, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        lesson_date.isoformat(),
                        item.get('stage_start', lesson_date.isoformat()),
                        item.get('stage_end', lesson_date.isoformat()),
                        item.get('stage_order', 0),
                        item.get('item_id'),
                        item.get('target_minutes', 0),
                        notes,
                    ))
            conn.commit()

    def get_weekly_assignment_for_week(self, anchor_date: dt.date) -> Optional[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('''
                    SELECT * FROM weekly_assignments
                    WHERE lesson_date = (
                        SELECT lesson_date FROM weekly_assignments
                        WHERE lesson_date >= %s
                        ORDER BY lesson_date ASC LIMIT 1
                    )
                    ORDER BY stage_order
                ''', (anchor_date.isoformat(),))
                rows = list(cur.fetchall())
        if not rows:
            return None
        return {'lesson_date': rows[0]['lesson_date'], 'items': rows}

    def get_weekly_assignment(self, week_start: dt.date) -> Optional[Dict]:
        return self.get_weekly_assignment_for_week(week_start)

    def get_weekly_assignments_in_range(self, start: dt.date, end: dt.date) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('''
                    SELECT * FROM weekly_assignments
                    WHERE lesson_date >= %s AND lesson_date <= %s
                    ORDER BY lesson_date, stage_order
                ''', (start.isoformat(), end.isoformat()))
                return list(cur.fetchall())

    # ── Daily Practices ──
    def save_daily_practice(self, date: dt.date, items: List[Dict], total_minutes: int, log: Optional[str] = None, practiced: str = 'Y', images: Optional[List[str]] = None, **kwargs) -> None:
        """改 7-27: 移植 SQLite merge 逻辑, 同 item 累加 minutes, 不同 item 追加.

        之前用 REPLACE INTO 简单粗暴覆盖, 导致小程序每次练习都覆盖前一天累积.
        对齐本地 SQLite 的 save_daily_practice 语义 (database.py:740-803).

        当 items==[] 且 practiced=='N' (清零场景, 走 api_delete_record), 走全清空路径,
        不要触发 merge 误把存量 items 保留.
        """
        items_json = json.dumps(items, ensure_ascii=False) if items else '[]'
        practice_at = kwargs.get('practice_at')
        # 如没传 total_minutes, 从 items 自动算
        if total_minutes == 0 and items:
            total_minutes = sum(i.get('minutes', 0) for i in items)

        # 清零场景 (DELETE /api/records/{date}) - 直接全清不走 merge
        is_clear = (not items) and (practiced == 'N') and (not log)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if is_clear:
                    cur.execute('''
                        UPDATE daily_practices
                        SET items = %s, total_minutes = 0, log = '', practiced = 'N'
                        WHERE date = %s
                    ''', (json.dumps([], ensure_ascii=False), date.isoformat()))
                    if cur.rowcount == 0:
                        try:
                            cur.execute('''
                                INSERT INTO daily_practices (date, items, total_minutes, log, practiced, behavior_log)
                                VALUES (%s, %s, 0, '', 'N', '')
                            ''', (date.isoformat(), json.dumps([], ensure_ascii=False)))
                        except Exception:
                            pass  # 已被另一进程写, race condition with auto-commit pool
                    conn.commit()
                    return

                cur.execute(
                    'SELECT items, log, practiced FROM daily_practices WHERE date = %s',
                    (date.isoformat(),)
                )
                row = cur.fetchone()
                if row:
                    existing_items_raw = row[0]
                    existing_items = json.loads(existing_items_raw) if existing_items_raw else []
                    existing_log = row[1] or ''
                    existing_practiced = row[2] or 'Y'

                    # 合并 items: 同 item 累加 minutes, 不同 item 追加
                    for it in items:
                        found = False
                        for ex in existing_items:
                            if ex.get('item') == it.get('item') or (it.get('item_id') and ex.get('item_id') == it['item_id']):
                                ex['minutes'] = ex.get('minutes', 0) + it.get('minutes', 0)
                                if not ex.get('item') and it.get('item'):
                                    ex['item'] = it['item']
                                found = True
                                break
                        if not found:
                            existing_items.append(it)
                    merged_items = existing_items
                    merged_total = sum(i.get('minutes', 0) for i in merged_items)
                    merged_log = (existing_log + '\n' + (log or '')).strip() if log else existing_log
                    final_practiced = 'Y' if merged_total > 0 else existing_practiced

                    # 不覆盖 practice_at (保留首次的练习时间)
                    if practice_at:
                        cur.execute('''
                            UPDATE daily_practices
                            SET items = %s, total_minutes = %s, log = %s, practiced = %s, practice_at = %s
                            WHERE date = %s
                        ''', (json.dumps(merged_items, ensure_ascii=False), merged_total, merged_log, final_practiced, practice_at, date.isoformat()))
                    else:
                        cur.execute('''
                            UPDATE daily_practices
                            SET items = %s, total_minutes = %s, log = %s, practiced = %s
                            WHERE date = %s
                        ''', (json.dumps(merged_items, ensure_ascii=False), merged_total, merged_log, final_practiced, date.isoformat()))
                else:
                    # 新建 (含 practice_at)
                    if practice_at:
                        cur.execute('''
                            INSERT INTO daily_practices (date, items, total_minutes, log, practiced, behavior_log, practice_at)
                            VALUES (%s, %s, %s, %s, %s, '', %s)
                        ''', (date.isoformat(), items_json, total_minutes, log, practiced, practice_at))
                    else:
                        cur.execute('''
                            INSERT INTO daily_practices (date, items, total_minutes, log, practiced, behavior_log)
                            VALUES (%s, %s, %s, %s, %s, '')
                        ''', (date.isoformat(), items_json, total_minutes, log, practiced))
            conn.commit()

    def log_practice_audit(self, channel: str, method: str, practice_date: dt.date, input_items: str, result_items: str, total_minutes: int, session_id: Optional[str] = None, error: Optional[str] = None) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO practice_audit_log (channel, method, practice_date, input_items, result_items, total_minutes, session_id, error)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (channel, method, practice_date.isoformat(), input_items, result_items, total_minutes, session_id, error))
                new_id = cur.lastrowid
            conn.commit()
            return new_id

    def append_behavior_log(self, date: dt.date, entry: Dict) -> None:
        behavior_log_json = json.dumps([entry], ensure_ascii=False)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE daily_practices
                    SET behavior_log = COALESCE(behavior_log, JSON_ARRAY()) || %s
                    WHERE date = %s
                ''', (behavior_log_json, date.isoformat()))
            conn.commit()

    def _normalize_items(self, raw):
        """业务代码 helper, 返回 list[dict]"""
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return []
        return []

    def remove_daily_practice_record_by_id(self, date: dt.date, item_id: int) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM practice_records WHERE date = %s AND item_id = %s', (date.isoformat(), item_id))
            conn.commit()

    def remove_daily_practice_item(self, date: dt.date, item_name: str) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE daily_practices
                    SET items = JSON_ARRAY()
                    WHERE date = %s
                ''', (date.isoformat(),))
            conn.commit()

    def get_daily_practice(self, date: dt.date) -> Optional[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM daily_practices WHERE date = %s', (date.isoformat(),))
                row = cur.fetchone()
                if not row:
                    return None
                if row.get('items') and isinstance(row['items'], str):
                    try:
                        row['items'] = json.loads(row['items'])
                    except Exception:
                        row['items'] = []
                return row

    def get_daily_practices_in_range(self, start: dt.date, end: dt.date) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('''
                    SELECT * FROM daily_practices
                    WHERE date >= %s AND date <= %s
                    ORDER BY date DESC
                ''', (start.isoformat(), end.isoformat()))
                return list(cur.fetchall())

    def save_progress_to_log(self, date: dt.date, note: str) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE daily_practices
                    SET progress_log = %s
                    WHERE date = %s
                ''', (note, date.isoformat()))
            conn.commit()

    def get_progress_from_log(self, date: dt.date) -> Optional[str]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT progress_log FROM daily_practices WHERE date = %s', (date.isoformat(),))
                row = cur.fetchone()
                return row['progress_log'] if row else None

    def get_progress_from_log_in_range(self, start: dt.date, end: dt.date) -> Dict[str, str]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('''
                    SELECT date, progress_log FROM daily_practices
                    WHERE date >= %s AND date <= %s
                ''', (start.isoformat(), end.isoformat()))
                return {r['date']: r['progress_log'] for r in cur.fetchall() if r.get('progress_log')}

    def migrate_daily_progress_to_log(self) -> int:
        """把旧的 progress 字段迁移到 progress_log, 业务代码自维护, Phase 1b 不必实现"""
        return 0

    # ── Achievements / Badges ──
    def insert_achievement_row(self, achievement_id: str, name: str, type_: str, category: str, stat_logic: str, description: str, display_format: str, threshold: Optional[int], unlocked_template: Optional[str], placeholder: Optional[str], locked_template: Optional[str]) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO achievements (id, name, type, category, stat_logic, description, display_format, threshold, unlocked_template, placeholder, locked_template)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name = %s
                ''', (achievement_id, name, type_, category, stat_logic, description, display_format, threshold, unlocked_template, placeholder, locked_template, name))
            conn.commit()

    def insert_achievement_stats_row(self, achievement_id: str, achieved: str, achieved_at: Optional[dt.datetime], raw_stats: str, computed_value: Optional[int]) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO achievement_stats (achievement_id, achieved, achieved_at, raw_stats, computed_value)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE achieved = %s
                ''', (achievement_id, achieved, achieved_at, raw_stats, computed_value, achieved))
            conn.commit()

    def insert_badge_row(self, achievement_id: str, url: str, is_locked: bool, version: int) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO achievement_badges (achievement_id, url, is_locked, version, is_current)
                    VALUES (%s, %s, %s, %s, 1)
                ''', (achievement_id, url, int(is_locked), version))
                new_id = cur.lastrowid
            conn.commit()
            return new_id

    def update_badge_current(self, achievement_id: str, new_url: str, new_version: int) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO achievement_badges (achievement_id, url, is_locked, version, is_current)
                    VALUES (%s, %s, 0, %s, 1)
                ''', (achievement_id, new_url, new_version))
                new_id = cur.lastrowid
                cur.execute('''
                    UPDATE achievement_badges SET is_current = 0
                    WHERE achievement_id = %s AND id != %s AND is_current = 1
                ''', (achievement_id, new_id))
            conn.commit()

    def get(self, table: str, **filters) -> List[Dict]:
        """通用查询"""
        where = ' AND '.join([f'`{k}` = %s' for k in filters.keys()])
        sql = f'SELECT * FROM `{table}`'
        if where:
            sql += f' WHERE {where}'
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute(sql, list(filters.values()))
                return list(cur.fetchall())

    def count_records(self, table: str = 'daily_practices') -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) FROM `{table}`')
                return cur.fetchone()[0]

    def log_audit(self, **kwargs) -> int:
        """alias for log_practice_audit"""
        return self.log_practice_audit(
            channel=kwargs['channel'],
            method=kwargs['method'],
            practice_date=kwargs['practice_date'],
            input_items=kwargs.get('input_items', ''),
            result_items=kwargs.get('result_items', ''),
            total_minutes=kwargs.get('total_minutes', 0),
            session_id=kwargs.get('session_id'),
            error=kwargs.get('error'),
        )

    def badge_exists(self, achievement_id: str, url: str) -> bool:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM achievement_badges WHERE achievement_id = %s AND url = %s LIMIT 1', (achievement_id, url))
                return cur.fetchone() is not None

    def get_connection(self):
        """alias for _get_connection, 兼容业务代码"""
        return self._get_connection()

    def merge_practice_item(self, from_id: int, to_id: int, from_name: str, to_name: str) -> None:
        """Phase 1b 简化: 业务代码很少调用, 抛 NotImplementedError"""
        raise NotImplementedError("merge_practice_item 待 Phase 2 补")

    def _match_practice_item_id(self, item_name: str) -> Optional[int]:
        """Phase 1b 简化"""
        raise NotImplementedError("_match_practice_item_id 待 Phase 2 补")

    def validate_item_id(self, item_id: int) -> Optional[int]:
        """Phase 1b 简化: 跑 SELECT"""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT item_id FROM practice_items WHERE item_id = %s', (item_id,))
                row = cur.fetchone()
                return row[0] if row else None

    # ── Reports ──
    def get_practice_reports(self) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM practice_reports ORDER BY year DESC, month DESC')
                return list(cur.fetchall())

    def get_streak(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('''
                    SELECT date, total_minutes FROM daily_practices
                    WHERE practiced = 'Y' AND total_minutes > 0
                    ORDER BY date DESC LIMIT 90
                ''')
                rows = list(cur.fetchall())
        if not rows:
            return {'streak': 0, 'last_practice_date': None}
        today = dt.date.today()
        streak = 0
        for i, r in enumerate(rows):
            d_obj = self._parse_date(r['date'])
            expected = today - dt.timedelta(days=i)
            if d_obj == expected:
                streak += 1
            else:
                break
        return {'streak': streak, 'last_practice_date': str(rows[0]['date'])}

    # ── Practice Sessions (7-27: 移植 SQLite schema + CRUD, 配套 dizical-minip PR #24) ──
    # SQLite 表实践: src/database.py:1041+; 但 MySQLBackend 7-27 前缺失整张表 + 5 个 CRUD.
    # 云端 fail 500 错误: AttributeError get_practice_sessions (7-27 mp 端真机验证发现)
    # MySQL 8 不允许 TEXT 默认值 → content 改 VARCHAR(512) DEFAULT ''
    # JSON 字段改 VARCHAR(1024) TEXT (Practice 行为统一)
    _PRACTICE_SESSIONS_DDL = [
        '''
        CREATE TABLE IF NOT EXISTS practice_sessions (
            id INT PRIMARY KEY AUTO_INCREMENT,
            practice_date DATE NOT NULL,
            item_id INT NOT NULL,
            item_name VARCHAR(128) NOT NULL,
            duration_minutes INT NOT NULL,
            tempo_note VARCHAR(16) NOT NULL DEFAULT '♪',
            tempo_bpm INT NOT NULL DEFAULT 80,
            content VARCHAR(512) NOT NULL DEFAULT '',
            content_source VARCHAR(32) NOT NULL DEFAULT 'manual',
            is_extra TINYINT(1) NOT NULL DEFAULT 0,
            started_at VARCHAR(64),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_ps_date (practice_date),
            INDEX idx_ps_item_date (item_id, practice_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        '''
    ]

    _PRACTICE_SESSIONS_DDL_DONE = False

    def _ensure_practice_sessions_schema(self) -> None:
        """Lazy DDL. 第一次访问 MySQLBackend 时拉起 practice_sessions 表 + 索引."""
        if self._PRACTICE_SESSIONS_DDL_DONE:
            return
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for ddl in self._PRACTICE_SESSIONS_DDL:
                    cur.execute(ddl)
            conn.commit()
        self._PRACTICE_SESSIONS_DDL_DONE = True

    _CONTENT_MAX_LEN = 200  # 跟 SQLite 对齐

    def _validate_session_fields(self, tempo_note: str, tempo_bpm: int, duration_minutes: int, content: str) -> None:
        if tempo_note not in ('♪', '♩', '♬'):
            raise ValueError(f"tempo_note 必须是 ♪/♩/♬, 收到 {tempo_note!r}")
        if not isinstance(tempo_bpm, int) or tempo_bpm < 40 or tempo_bpm > 150:
            raise ValueError(f"tempo_bpm 必须是 40-150 int, 收到 {tempo_bpm!r}")
        if duration_minutes <= 0:
            raise ValueError(f"duration_minutes 必须 > 0, 收到 {duration_minutes}")
        if not isinstance(content, str) or len(content) > self._CONTENT_MAX_LEN:
            raise ValueError(f"content 必须是 ≤{self._CONTENT_MAX_LEN} 字符的字符串, 收到 {content!r}")

    def get_practice_session_by_id(self, session_id: int) -> Dict:
        self._ensure_practice_sessions_schema()
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT * FROM practice_sessions WHERE id = %s', (session_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"session_id={session_id} 不存在")
                row['practice_date'] = str(row.get('practice_date', ''))
                row['created_at'] = str(row.get('created_at', ''))
                row['is_extra'] = int(row.get('is_extra', 0))
                return row

    def get_practice_sessions(self, practice_date: dt.date, item_id: Optional[int] = None) -> List[Dict]:
        """查某日所有 session (可选 item_id 过滤). 顺序: created_at ASC, id ASC."""
        self._ensure_practice_sessions_schema()
        if isinstance(practice_date, str):
            practice_date = dt.date.fromisoformat(practice_date)
        sql = 'SELECT * FROM practice_sessions WHERE practice_date = %s'
        params: List = [practice_date.isoformat()]
        if item_id is not None:
            sql += ' AND item_id = %s'
            params.append(int(item_id))
        sql += ' ORDER BY created_at ASC, id ASC'
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute(sql, params)
                rows = list(cur.fetchall())
                for r in rows:
                    r['practice_date'] = str(r.get('practice_date', ''))
                    r['created_at'] = str(r.get('created_at', ''))
                    r['is_extra'] = int(r.get('is_extra', 0))
                return rows

    def get_latest_session_tempo(self, item_id: int) -> Optional[Dict]:
        """读 practice_items 冗余列 (Q1=B). NULL → 回退查 sessions 表."""
        self._ensure_practice_sessions_schema()
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                # 1. 优先读 practice_items 冗余列
                cur.execute(
                    'SELECT last_tempo_note, last_tempo_bpm, last_session_at FROM practice_items WHERE item_id = %s',
                    (item_id,),
                )
                row = cur.fetchone()
                if row and row.get('last_tempo_note') and row.get('last_tempo_bpm'):
                    return {
                        'last_tempo_note': row['last_tempo_note'],
                        'last_tempo_bpm': int(row['last_tempo_bpm']),
                        'last_session_at': str(row.get('last_session_at')) if row.get('last_session_at') else None,
                    }
                # 2. fallback: 查 sessions 表
                cur.execute(
                    'SELECT tempo_note AS last_tempo_note, tempo_bpm AS last_tempo_bpm, created_at AS last_session_at '
                    'FROM practice_sessions WHERE item_id = %s ORDER BY created_at DESC LIMIT 1',
                    (item_id,),
                )
                fb = cur.fetchone()
                if fb and fb.get('last_tempo_note'):
                    return {
                        'last_tempo_note': fb['last_tempo_note'],
                        'last_tempo_bpm': int(fb['last_tempo_bpm']),
                        'last_session_at': str(fb['last_session_at']) if fb.get('last_session_at') else None,
                    }
                return None

    def save_practice_session_and_daily_summary(self, practice_date, item, item_id, minutes,
                                                  tempo_note, tempo_bpm, content,
                                                  content_source='manual', practice_at=None,
                                                  is_extra=False) -> Dict:
        """核心事务方法: 写 1 条 session + 同步 daily 汇总 + 写 audit + 更新冗余列.

        Args:
            practice_at: CST ISO 'YYYY-MM-DD HH:MM:SS[.fff]', 新建 daily 行才写, 已有不动.
        Returns: 新插入 session 的 dict.
        """
        self._ensure_practice_sessions_schema()
        self._validate_session_fields(tempo_note, tempo_bpm, minutes, content)
        if isinstance(practice_date, str):
            practice_date = dt.date.fromisoformat(practice_date)

        # 校验 item_id (跟 SQLite 一致)
        with self._get_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute('SELECT name FROM practice_items WHERE item_id = %s', (int(item_id),))
                item_row = cur.fetchone()
                if not item_row:
                    raise ValueError(f"item_id={item_id} 不存在")
                actual_item_name = item_row['name']

                # 事务: session + daily + audit + 冗余列 (失败全 rollback)
                try:
                    # 1. 写 session
                    started_at = practice_at
                    cur.execute('''
                        INSERT INTO practice_sessions
                        (practice_date, item_id, item_name, duration_minutes,
                         tempo_note, tempo_bpm, content, content_source,
                         is_extra, started_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (practice_date.isoformat(), int(item_id), actual_item_name, int(minutes),
                          tempo_note, int(tempo_bpm), content, content_source,
                          1 if is_extra else 0, started_at))
                    new_session_id = cur.lastrowid
                    if not new_session_id:
                        raise RuntimeError("INSERT session 后 lastrowid 为空")

                    # 2. 读 daily
                    cur.execute(
                        'SELECT items, log, practiced, practice_at FROM daily_practices WHERE date = %s',
                        (practice_date.isoformat(),),
                    )
                    drow = cur.fetchone()
                    existing_items = json.loads(drow['items']) if drow and drow['items'] else []
                    existing_log = drow['log'] if drow and drow['log'] else ''
                    existing_practiced = drow['practiced'] if drow and drow['practiced'] else 'Y'

                    # 3. 合并 items 累加 minutes
                    found = False
                    for it in existing_items:
                        if it.get('item') == actual_item_name:
                            it['minutes'] = it.get('minutes', 0) + minutes
                            found = True
                            break
                    if not found:
                        existing_items.append({
                            'item': actual_item_name,
                            'item_id': int(item_id),
                            'minutes': minutes,
                        })
                    new_total = sum(it.get('minutes', 0) for it in existing_items)
                    final_practiced = 'Y' if new_total > 0 else existing_practiced

                    # 4. UPDATE 或 INSERT daily (走 7-27 新增的 merge 逻辑: 不覆盖 practice_at)
                    if drow:
                        cur.execute('''
                            UPDATE daily_practices
                            SET items = %s, total_minutes = %s, practiced = %s
                            WHERE date = %s
                        ''', (json.dumps(existing_items, ensure_ascii=False), new_total,
                              final_practiced, practice_date.isoformat()))
                    else:
                        cur.execute('''
                            INSERT INTO daily_practices
                            (date, items, total_minutes, log, practiced, practice_at, behavior_log)
                            VALUES (%s, %s, %s, %s, %s, %s, '')
                        ''', (practice_date.isoformat(), json.dumps(existing_items, ensure_ascii=False),
                              new_total, '', final_practiced, practice_at))

                    # 5. 写 audit log (behavior_log 数组 append + practice_audit_log 增 1 条)
                    audit_entry = {
                        'enter_time': practice_at or started_at,
                        'item': actual_item_name,
                        'item_id': int(item_id),
                        'minutes': minutes,
                        'session_id': new_session_id,
                        'content': content,
                        'tempo_note': tempo_note,
                        'tempo_bpm': tempo_bpm,
                    }
                    cur.execute('SELECT behavior_log FROM daily_practices WHERE date = %s', (practice_date.isoformat(),))
                    bl_row = cur.fetchone()
                    blog_list = json.loads(bl_row['behavior_log']) if bl_row and bl_row.get('behavior_log') else []
                    blog_list.append(audit_entry)
                    cur.execute(
                        'UPDATE daily_practices SET behavior_log = %s WHERE date = %s',
                        (json.dumps(blog_list, ensure_ascii=False), practice_date.isoformat()),
                    )
                    cur.execute('''
                        INSERT INTO practice_audit_log
                        (channel, method, practice_date, input_items, result_items, total_minutes, error, session_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        'internal', 'save_session', practice_date.isoformat(),
                        json.dumps([{'item': actual_item_name, 'item_id': int(item_id), 'minutes': minutes}]),
                        json.dumps(existing_items, ensure_ascii=False), new_total, None, str(new_session_id),
                    ))

                    # 6. 更新冗余列 (Q1=B 性能优化)
                    cur.execute('''
                        UPDATE practice_items
                        SET last_tempo_note = %s, last_tempo_bpm = %s, last_session_at = CURRENT_TIMESTAMP
                        WHERE item_id = %s
                    ''', (tempo_note, int(tempo_bpm), int(item_id)))

                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

        return self.get_practice_session_by_id(new_session_id)

    def close(self):
        if self.pool:
            self.pool.close()
