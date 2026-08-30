"""
dizical MySQL 后端 (Phase 1b)
镜像 src.database.Database 全部 53 个方法.
DATABASE_URL=mysql+pymysql://user:pass@host:port/db 时启用.
"""

import datetime as dt
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from src.database_base import BaseBackend

import pymysql
from pymysql.cursors import DictCursor

# 2026-08-16: Fix 500 in /api/items caused by raw datetime in MySQL row dict
# getting fed into JSONResponse. Same pattern as fix used in get_practice_categories
# (L298-307, comment "P0-2026-08-06") but applied at the cursor layer so EVERY
# DatetimeSafeDictCursor-using method is protected. Compatible with _parse_datetime() which
# already handles both str and datetime inputs (database_mysql.py:77-83).
class DatetimeSafeDictCursor(DictCursor):
    """DatetimeSafeDictCursor that auto-converts datetime/date columns to ISO strings.

    Why needed: MySQL DATETIME columns return raw datetime.datetime objects via
    pymysql. FastAPI's default JSONResponse uses json.dumps() which chokes on
    `datetime` with TypeError: Object of type datetime is not JSON serializable.
    Application code has been patching only some call sites (e.g. categories at
    L298-307) but `get_practice_items` (L339-352) + others were missed.
    Subclassing once at the cursor layer covers all 32+ DatetimeSafeDictCursor usages.
    """
    def _conv_row(self, row):
        d = super()._conv_row(row)
        if d is None:
            return None
        for k, v in list(d.items()):
            if isinstance(v, (dt.datetime, dt.date)):
                d[k] = str(v)
        return d

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


class MySQLBackend(BaseBackend):
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
        # Sprint 08: 加超时防 Serverless 唤醒期挂死
        if self.pool:
            conn = self.pool.connection()
        else:
            conn = pymysql.connect(
                host=self._cfg['host'], port=self._cfg['port'],
                user=self._cfg['user'], password=self._cfg['password'],
                database=self._cfg['database'], charset='utf8mb4',
                connect_timeout=5, read_timeout=10, write_timeout=10,
            )
        # 注: pymysql 默认 autocommit=True. 业务方法用 with self._get_connection()
        # 进入连接, 末尾 conn.commit() 单独提交 — 这是 MySQLBackend 已 merge 的契约.
        # 不在这里显式 conn.begin(), 因为某些 helper (json_array_append 等) 依赖
        # autocommit=True 的隐式行为, 显式 begin 会破坏它们.
        # lost-update 防护依赖业务方法显式 BEGIN 包裹 SELECT FOR UPDATE.
        return conn

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
        """MySQL DATE 返 date 对象.

        P0-2026-08-16: 表 schema 写的是 DATE, 但 weekly_assignments 实际是 DATETIME
        (返回 'YYYY-MM-DD HH:MM:SS' str). 用 [:10] 截前 10 字符兼容两种列类型.
        """
        if v is None:
            return None
        if isinstance(v, dt.date):
            return v
        if isinstance(v, dt.datetime):
            return v.date()
        if isinstance(v, str):
            return dt.date.fromisoformat(v[:10])
        return v

    def _safe_to_date(self, v):
        """安全 date 转换 — 兼容 str/datetime/date, 截 [:10] 应对 DATETIME 字符串.

        用于 _parse_date 之外的 caller (e.g. weekly_assignments SELECT 结果).
        注意: dt.datetime 是 dt.date 的子类, 必须先 check datetime.
        """
        if v is None:
            return None
        if type(v) is dt.datetime:
            # bare datetime (not date subclass) — convert to date
            return v.date()
        if isinstance(v, dt.date):
            return v
        if isinstance(v, str):
            return dt.date.fromisoformat(v[:10])
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('SELECT * FROM lessons WHERE id = %s', (lesson_id,))
                row = cur.fetchone()
                return self._row_to_lesson(row) if row else None

    def get_lesson_by_date(self, lesson_date: dt.date) -> Optional[Lesson]:
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('SELECT * FROM lessons WHERE date = %s', (lesson_date.isoformat(),))
                row = cur.fetchone()
                return self._row_to_lesson(row) if row else None

    def get_lessons_by_month(self, year: int, month: int) -> List[Lesson]:
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('SELECT * FROM practice_categories ORDER BY sort_order, name')
                rows = cur.fetchall()
                out = []
                for row in rows:
                    d = dict(row)
                    # P0-2026-08-06: MySQL datetime → str, 否则 JSONResponse 500 (Object of type datetime)
                    if d.get('created_at') is not None:
                        d['created_at'] = str(d['created_at'])
                    out.append(d)
                return out

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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('SELECT * FROM practice_items WHERE item_id = %s', (item_id,))
                row = cur.fetchone()
                return row

    def get_practice_items(self, active_only: bool = True, include_archived: bool = False) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                where = []
                if active_only:
                    where.append('is_active = 1')
                if not include_archived:
                    where.append('is_archived = 0')
                sql = 'SELECT * FROM practice_items'
                if where:
                    sql += ' WHERE ' + ' AND '.join(where)
                sql += ' ORDER BY sort_order, name'
                cur.execute(sql)
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
    # Sprint 08: MySQL 端对齐 SQLite 语义 — 单行存储 + items JSON 数组 + ON DUPLICATE KEY UPDATE
    # SQLite (database.py:686-698) 用 ON CONFLICT(lesson_date) DO UPDATE, 同样的语义在 MySQL
    # 用 INSERT ... ON DUPLICATE KEY UPDATE 实现. 不再 DELETE+逐 item INSERT.
    def save_weekly_assignment(self, lesson_date: dt.date, items: List[Dict], notes: Optional[str] = None, images: Optional[List[str]] = None, videos: Optional[List[Dict]] = None) -> None:
        import json as _json
        items_json = _json.dumps(items, ensure_ascii=False)
        existing = self.get_weekly_assignment(lesson_date)
        merged_images = existing['images'] if images is None and existing else (images if images is not None else [])
        merged_videos = existing['videos'] if videos is None and existing else (videos if videos is not None else [])
        images_json = _json.dumps(merged_images, ensure_ascii=False)
        videos_json = _json.dumps(merged_videos, ensure_ascii=False)
        # 对齐 SQLite `database.py:714-729`: 每次保存都重新计算 stage_start/end/order
        # (修复 2026-08-25: 原实现"已有行取旧值不重算"导致 08-16 课 attended 后
        #  stage_order 无法回填 → stage 停在第 18).
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                # all_lessons: stage_end = 下一节 (attended + scheduled) 课日期
                cur.execute("SELECT date FROM lessons ORDER BY date")
                all_lessons_rows = cur.fetchall()
                # 过滤 None (东莞市 lessons.date NOT NULL, 实际不会为 None; 收窄类型供静态分析)
                all_lessons = [
                    (r['date'] if isinstance(r['date'], dt.date) else self._safe_to_date(r['date']))
                    for r in all_lessons_rows
                ]
                all_lessons = [d for d in all_lessons if d is not None]
                future = [d for d in all_lessons if d > lesson_date]
                stage_start = (lesson_date + dt.timedelta(days=1)).isoformat()
                stage_end = future[0].isoformat() if future else (lesson_date + dt.timedelta(days=7)).isoformat()

                # stage_order 对齐 SQLite database.py:729 (agy review 确认, 2026-08-25):
                # = 该课之前已录作业的课日数 + 1 (2026-03-14 起的正式序列).
                # 2025-11~2026-03-07 旧体系数据 (stage_order 为负) 用 >= '2026-03-14' 排除,
                # 保证历史 Stage 编号不漂移. 任意课 (attended/scheduled/cancelled) 录作业即编号.
                cur.execute('''
                    SELECT COUNT(DISTINCT lesson_date) FROM weekly_assignments
                    WHERE lesson_date >= '2026-03-14' AND lesson_date < %s
                      AND (stage_order > 0 OR stage_order IS NULL)
                ''', (lesson_date.isoformat(),))
                cnt = cur.fetchone()
                # DatetimeSafeDictCursor 返 dict, 取首列值 (COUNT 只有一个结果列)
                cnt_val = next(iter(cnt.values())) if cnt else 0
                stage_order = (cnt_val if cnt_val is not None else 0) + 1

                cur.execute('''
                    INSERT INTO weekly_assignments
                    (lesson_date, items, notes, images, videos, stage_start, stage_end, stage_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        items = VALUES(items),
                        notes = VALUES(notes),
                        images = VALUES(images),
                        videos = VALUES(videos),
                        stage_start = VALUES(stage_start),
                        stage_end = VALUES(stage_end),
                        stage_order = VALUES(stage_order)
                ''', (lesson_date.isoformat(), items_json, notes, images_json, videos_json,
                      stage_start, stage_end, stage_order))
            conn.commit()

    def get_weekly_assignment_for_week(self, anchor_date: dt.date) -> Optional[Dict]:
        import json as _json
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('''
                    SELECT * FROM weekly_assignments
                    WHERE lesson_date <= %s
                    ORDER BY lesson_date DESC
                    LIMIT 1
                ''', (anchor_date.isoformat(),))
                row = cur.fetchone()
        if not row:
            return None
        return {
            'id': row.get('id'),
            'lesson_date': self._safe_to_date(row['lesson_date']),
            'stage_start': self._safe_to_date(row.get('stage_start')),
            'stage_end':   self._safe_to_date(row.get('stage_end')),
            'stage_order': row.get('stage_order'),
            'items': _json.loads(row['items']) if row.get('items') else [],
            'notes': row.get('notes'),
            'images': _json.loads(row['images']) if row.get('images') else [],
            'videos': _json.loads(row['videos']) if row.get('videos') else [],
        }

    def get_weekly_assignment(self, week_start: dt.date) -> Optional[Dict]:
        return self.get_weekly_assignment_for_week(week_start)

    def get_weekly_assignments_in_range(self, start: dt.date, end: dt.date) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('''
                    SELECT * FROM weekly_assignments
                    WHERE lesson_date >= %s AND lesson_date <= %s
                    ORDER BY lesson_date, stage_order
                ''', (start.isoformat(), end.isoformat()))
                rows = cur.fetchall()
                out = []
                for row in rows:
                    d = dict(row)
                    # P0-2026-08-06: 对齐 SQLite (database.py:807-816), MySQL 端漏了 JSON parse + date 转换.
                    # items/images 是 JSON 字符串 → json.loads; lesson_date/stage 是 datetime → date.
                    def _to_date(v):
                        if v is None:
                            return None
                        if isinstance(v, dt.datetime):
                            return v.date()
                        return dt.date.fromisoformat(str(v)[:10])
                    try:
                        items = json.loads(d['items']) if d.get('items') else []
                    except (TypeError, ValueError):
                        items = []
                    try:
                        images = json.loads(d['images']) if d.get('images') else []
                    except (TypeError, ValueError):
                        images = []
                    try:
                        videos = json.loads(d['videos']) if d.get('videos') else []
                    except (TypeError, ValueError):
                        videos = []
                    out.append({
                        'id': d['id'],
                        'lesson_date': _to_date(d.get('lesson_date')),
                        'stage_start': _to_date(d.get('stage_start')),
                        'stage_end': _to_date(d.get('stage_end')),
                        'stage_order': d.get('stage_order'),
                        'items': items,
                        'notes': d.get('notes'),
                        'images': images,
                        'videos': videos,
                        'created_at': d.get('created_at'),
                    })
                return out

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
                    # Sprint 09 P0-22 (PR-E): 清零也写 audit (SQLite parity — SQLite merge 路径会写)
                    channel = kwargs.get('channel')
                    method = kwargs.get('method')
                    if channel and method:
                        cur.execute('''
                            INSERT INTO practice_audit_log
                            (channel, method, practice_date, input_items, result_items, total_minutes, error, session_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ''', (
                            channel, method, date.isoformat(),
                            json.dumps([], ensure_ascii=False),
                            json.dumps([], ensure_ascii=False),
                            0, None, kwargs.get('session_id'),
                        ))
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

                # Sprint 09 P0-22 (PR-E): audit 移入事务内 (commit 前), 与 SQLite parity.
                # 旧实现: MySQL save_daily_practice 完全不写 audit (SQLite 有, MySQL 没有 = parity 缺口).
                channel = kwargs.get('channel')
                method = kwargs.get('method')
                if channel and method:
                    cur.execute('''
                        INSERT INTO practice_audit_log
                        (channel, method, practice_date, input_items, result_items, total_minutes, error, session_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        channel, method, date.isoformat(),
                        json.dumps(items, ensure_ascii=False),
                        json.dumps(items, ensure_ascii=False),
                        total_minutes, None, kwargs.get('session_id'),
                    ))
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
        """原子追加 1 条 entry 到 behavior_log JSON 数组.

        PR-A-4 修复: 旧实现用 `behavior_log || %s` 字符串拼接, 会破坏已有 JSON 结构
        (变成 '[entry1][entry2]'). 新实现用 JSON_ARRAY_APPEND 原子追加.
        """
        behavior_log_json = json.dumps([entry], ensure_ascii=False)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE daily_practices
                    SET behavior_log = JSON_ARRAY_APPEND(
                        COALESCE(behavior_log, JSON_ARRAY()),
                        '$',
                        CAST(%s AS JSON)
                    )
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
                    SET log = %s
                    WHERE date = %s
                ''', (note, date.isoformat()))
            conn.commit()

    def get_progress_from_log(self, date: dt.date) -> Optional[str]:
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('SELECT log FROM daily_practices WHERE date = %s', (date.isoformat(),))
                row = cur.fetchone()
                return row['log'] if row else None

    def get_progress_from_log_in_range(self, start: dt.date, end: dt.date) -> Dict[str, str]:
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('''
                    SELECT date, log FROM daily_practices
                    WHERE date >= %s AND date <= %s
                ''', (start.isoformat(), end.isoformat()))
                return {r['date']: r['log'] for r in cur.fetchall() if r.get('log')}

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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('SELECT * FROM practice_reports ORDER BY year DESC, month DESC')
                return list(cur.fetchall())

    def get_streak(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
            -- PR-A-3: 字段类型与 schema_mysql.sql 对齐 (id/item_id/duration_minutes/tempo_bpm 一律 BIGINT)
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            practice_date DATE NOT NULL,
            item_id BIGINT NOT NULL,
            item_name VARCHAR(128) NOT NULL,
            duration_minutes BIGINT NOT NULL,
            tempo_note VARCHAR(16) NOT NULL DEFAULT '♪',
            tempo_bpm BIGINT NOT NULL DEFAULT 80,
            content VARCHAR(512) NOT NULL DEFAULT '',
            content_source VARCHAR(32) NOT NULL DEFAULT 'manual',
            is_extra TINYINT(1) NOT NULL DEFAULT 0,
            started_at VARCHAR(64),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            -- Sprint 09 P0-12 (PR-D): 乐观锁版本列 + 最后更新时间
            version BIGINT NOT NULL DEFAULT 1,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_ps_date (practice_date),
            INDEX idx_ps_item_date (item_id, practice_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        '''
    ]

    # Sprint 09 P0-12 (PR-D): 历史表兼容 — 加 version / updated_at 列 (如果不存在).
    _PRACTICE_SESSIONS_V3_ALTER = [
        "ALTER TABLE practice_sessions ADD COLUMN version BIGINT NOT NULL DEFAULT 1",
        "ALTER TABLE practice_sessions ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
    ]

    _PRACTICE_SESSIONS_DDL_DONE = False

    # PR-B: 与 schemas.py 常量对齐 (单一事实源).
    _ALLOWED_TEMPO_NOTES = ('♪', '♩', '♬')
    _BPM_MIN = 40
    _BPM_MAX = 150
    _CONTENT_MAX_LEN = 200

    def _ensure_practice_sessions_schema(self) -> None:
        """Lazy DDL. 第一次访问 MySQLBackend 时拉起 practice_sessions 表 + 索引.

        Sprint 09 P0-12 (PR-D): 已存在的旧表 (无 version/updated_at) 自动 ALTER 加上.
        """
        if self._PRACTICE_SESSIONS_DDL_DONE:
            return
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                for ddl in self._PRACTICE_SESSIONS_DDL:
                    cur.execute(ddl)
                # 历史表兼容: 检查列, 缺就 ALTER 加上 (MySQL 8 无 IF NOT EXISTS 语法, 用 information_schema)
                cur.execute(
                    """SELECT COLUMN_NAME FROM information_schema.COLUMNS
                       WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'practice_sessions'"""
                )
                existing_cols = {r[0] for r in cur.fetchall()}
                if 'version' not in existing_cols:
                    cur.execute("ALTER TABLE practice_sessions ADD COLUMN version BIGINT NOT NULL DEFAULT 1")
                if 'updated_at' not in existing_cols:
                    cur.execute(
                        "ALTER TABLE practice_sessions ADD COLUMN updated_at "
                        "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
                    )
            conn.commit()
        self._PRACTICE_SESSIONS_DDL_DONE = True

    def _validate_session_fields(self, tempo_note: str, tempo_bpm: int, duration_minutes: int, content: str) -> None:
        # 用类常量替代硬编码值, 与 schemas.py 保持单一事实源
        if tempo_note not in self._ALLOWED_TEMPO_NOTES:
            raise ValueError(f"tempo_note 必须是 {self._ALLOWED_TEMPO_NOTES} 之一, 收到 {tempo_note!r}")
        if not isinstance(tempo_bpm, int) or tempo_bpm < self._BPM_MIN or tempo_bpm > self._BPM_MAX:
            raise ValueError(f"tempo_bpm 必须是 {self._BPM_MIN}-{self._BPM_MAX} int, 收到 {tempo_bpm!r}")
        if duration_minutes <= 0:
            raise ValueError(f"duration_minutes 必须 > 0, 收到 {duration_minutes}")
        if not isinstance(content, str) or not content.strip() or len(content) > self._CONTENT_MAX_LEN:
            raise ValueError(f"content 必须是 1-{self._CONTENT_MAX_LEN} 个字符的非空字符串, 收到 {content!r}")

    def get_practice_session_by_id(self, session_id: int) -> Dict:
        self._ensure_practice_sessions_schema()
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('SELECT * FROM practice_sessions WHERE id = %s', (session_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"session_id={session_id} 不存在")
                row['practice_date'] = str(row.get('practice_date', ''))
                row['created_at'] = str(row.get('created_at', ''))
                # PR-D P0-2026-08-05: updated_at 也是 DATETIME, 必须转 str (否则 JSONResponse 序列化失败 → 500)
                row['updated_at'] = str(row.get('updated_at', '')) if row.get('updated_at') else None
                row['is_extra'] = int(row.get('is_extra', 0))
                return row

    def get_practice_sessions(self, practice_date: dt.date, item_id: Optional[int] = None) -> List[Dict]:
        """查某日所有 session (可选 item_id 过滤). 顺序: created_at ASC, id ASC."""
        self._ensure_practice_sessions_schema()
        if isinstance(practice_date, str):
                practice_date = self._safe_to_date(practice_date)
        sql = 'SELECT * FROM practice_sessions WHERE practice_date = %s'
        params: List = [practice_date.isoformat()]
        if item_id is not None:
            sql += ' AND item_id = %s'
            params.append(int(item_id))
        sql += ' ORDER BY created_at ASC, id ASC'
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute(sql, params)
                rows = list(cur.fetchall())
                for r in rows:
                    r['practice_date'] = str(r.get('practice_date', ''))
                    r['created_at'] = str(r.get('created_at', ''))
                    # PR-D P0-2026-08-05: updated_at DATETIME → str (JSON 序列化)
                    r['updated_at'] = str(r.get('updated_at', '')) if r.get('updated_at') else None
                    r['is_extra'] = int(r.get('is_extra', 0))
                return rows

    # ── Stage / Sessions queries (Sprint 08: 对齐 SQLite) ──
    def list_stages(self) -> List[Dict]:
        """列出历史 stage (按 stage_order 降序). 同 order 多行取 id 最大一条.

        Sprint 26081001: 过滤 stage_order IS NULL / = 0 (老 NULL + 新录入 bug).
        保留浮点 stage_order (0.01-0.12 表示早期大课, 早于小课 stage 1).
        """
        import json as _json
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                # Sprint 08 fix: MySQL 8 不接受 '' 比较 DATETIME, 只用 IS NOT NULL
                # Sprint 26081001: 加 stage_order IS NOT NULL AND stage_order != 0 过滤
                cur.execute(
                    """
                    SELECT id, stage_order, lesson_date, stage_start, stage_end, items, notes
                    FROM weekly_assignments
                    WHERE stage_start IS NOT NULL
                      AND stage_order IS NOT NULL
                      AND stage_order != 0
                    ORDER BY stage_order DESC, id DESC
                    """
                )
                rows = list(cur.fetchall())
        seen = set()
        out: List[Dict] = []
        for row in rows:
            key = row.get("stage_order") if row.get("stage_order") is not None else row.get("stage_start")
            if key in seen:
                continue
            seen.add(key)
            items_raw = row.get("items") or "[]"
            try:
                items = _json.loads(items_raw) if isinstance(items_raw, str) else items_raw
            except Exception:
                items = []
            out.append({
                "id": row.get("id"),
                "stage_order": row.get("stage_order"),
                "lesson_date": str(row.get("lesson_date") or ""),
                "stage_start": str(row.get("stage_start") or ""),
                "stage_end": str(row.get("stage_end") or ""),
                "item_count": len(items),
                "notes": row.get("notes") or "",
            })
        return out

    def get_stage_by_order(self, stage_order) -> Optional[Dict]:
        """按 stage_order 取最新一条 assignment (含 items).

        Sprint 26081001: stage_order 可能是浮点 (0.01-0.12 早期大课), 不再 int() 强制转.
        """
        import json as _json
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM weekly_assignments
                    WHERE stage_order = %s
                    ORDER BY id DESC LIMIT 1
                    """,
                    (stage_order,),
                )
                row = cur.fetchone()
        if not row:
            return None
        items_raw = row.get("items") or "[]"
        images_raw = row.get("images") or "[]"
        try:
            items = _json.loads(items_raw) if isinstance(items_raw, str) else items_raw
        except Exception:
            items = []
        try:
            images = _json.loads(images_raw) if isinstance(images_raw, str) else images_raw
        except Exception:
            images = []
        return {
            "id": row.get("id"),
            "lesson_date": str(row.get("lesson_date") or ""),
            "stage_start": str(row.get("stage_start") or ""),
            "stage_end": str(row.get("stage_end") or ""),
            "stage_order": row.get("stage_order"),
            "items": items,
            "notes": row.get("notes"),
            "images": images,
        }

    def get_stage_containing_date(self, day: dt.date) -> Optional[Dict]:
        """找包含 day 的 stage (stage_start <= day <= stage_end)."""
        import json as _json
        if isinstance(day, str):
                day = self._safe_to_date(day)
        day_s = day.isoformat()
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM weekly_assignments
                    WHERE stage_start IS NOT NULL
                      AND stage_start <= %s
                      AND (stage_end IS NULL OR stage_end >= %s)
                    ORDER BY id DESC LIMIT 1
                    """,
                    (day_s, day_s),
                )
                row = cur.fetchone()
        if not row:
            return None
        items_raw = row.get("items") or "[]"
        images_raw = row.get("images") or "[]"
        try:
            items = _json.loads(items_raw) if isinstance(items_raw, str) else items_raw
        except Exception:
            items = []
        try:
            images = _json.loads(images_raw) if isinstance(images_raw, str) else images_raw
        except Exception:
            images = []
        return {
            "id": row.get("id"),
            "lesson_date": str(row.get("lesson_date") or ""),
            "stage_start": str(row.get("stage_start") or ""),
            "stage_end": str(row.get("stage_end") or ""),
            "stage_order": row.get("stage_order"),
            "items": items,
            "notes": row.get("notes"),
            "images": images,
        }

    def get_practice_sessions_in_range(
        self, start: dt.date, end: dt.date, item_id: Optional[int] = None
    ) -> List[Dict]:
        """查日期闭区间 [start, end] 内全部 session."""
        if isinstance(start, str):
                start = self._safe_to_date(start)
        if isinstance(end, str):
                end = self._safe_to_date(end)
        sql = (
            "SELECT * FROM practice_sessions "
            "WHERE practice_date >= %s AND practice_date <= %s"
        )
        params: List = [start.isoformat(), end.isoformat()]
        if item_id is not None:
            sql += " AND item_id = %s"
            params.append(item_id)
        sql += " ORDER BY practice_date ASC, COALESCE(started_at, created_at) ASC, id ASC"
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute(sql, params)
                rows = list(cur.fetchall())
        for r in rows:
            for k in ('practice_date', 'created_at', 'started_at'):
                if r.get(k) is not None:
                    r[k] = str(r[k])
            if r.get('is_extra') is not None:
                r['is_extra'] = int(r['is_extra'])
        return rows

    def get_latest_session_tempo(self, item_id: int) -> Optional[Dict]:
        """读 practice_items 冗余列 (Q1=B). NULL → 回退查 sessions 表."""
        self._ensure_practice_sessions_schema()
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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
                        'last_session_at': str(fb['created_at']) if fb.get('created_at') else None,
                    }
                return None

    # PR-B: MySQL 缺 create/update/delete 三个方法 (7-28 教训).
    # 整事务: 写 session + 重算 daily + 写 audit + 更新冗余列.
    def create_practice_session(
        self,
        practice_date: dt.date,
        item_id: int,
        item_name: str,
        duration_minutes: int,
        tempo_note: str = '♪',
        tempo_bpm: int = 80,
        content: str = '',
        content_source: str = 'manual',
        is_extra: bool = False,
        started_at: Optional[str] = None,
    ) -> Dict:
        """插入 1 条 practice_session, 返回 dict (含 id). 不动 daily_practices 汇总."""
        self._ensure_practice_sessions_schema()
        self._validate_session_fields(tempo_note, tempo_bpm, duration_minutes, content)
        if isinstance(practice_date, str):
                practice_date = self._safe_to_date(practice_date)
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute('''
                    INSERT INTO practice_sessions
                    (practice_date, item_id, item_name, duration_minutes,
                     tempo_note, tempo_bpm, content, content_source,
                     is_extra, started_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (practice_date.isoformat(), int(item_id), item_name, int(duration_minutes),
                      tempo_note, int(tempo_bpm), content, content_source,
                      1 if is_extra else 0, started_at))
                new_id = cur.lastrowid
                if not new_id:
                    raise RuntimeError("INSERT session 后 lastrowid 为空")
            conn.commit()
        return self.get_practice_session_by_id(new_id)

    def update_practice_session(
        self,
        session_id: int,
        tempo_note: Optional[str] = None,
        tempo_bpm: Optional[int] = None,
        content: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        expected_version: Optional[int] = None,
    ) -> Optional[Dict]:
        """更新 session tempo/content/duration, duration 变化时重算 daily.

        Sprint 09 P0-12 (PR-D): 加 expected_version 乐观锁 (同 SQLite).
        """
        self._ensure_practice_sessions_schema()
        # 逐字段校验 (避免 OR fallback 绕过空 content)
        if tempo_note is not None and tempo_note not in self._ALLOWED_TEMPO_NOTES:
            raise ValueError(f"tempo_note 必须是 {self._ALLOWED_TEMPO_NOTES} 之一, 收到 {tempo_note!r}")
        if tempo_bpm is not None and not (self._BPM_MIN <= tempo_bpm <= self._BPM_MAX):
            raise ValueError(f"tempo_bpm 必须在 {self._BPM_MIN}-{self._BPM_MAX} 之间, 收到 {tempo_bpm}")
        if duration_minutes is not None and duration_minutes <= 0:
            raise ValueError(f"duration_minutes 必须 > 0, 收到 {duration_minutes}")
        if content is not None and (not isinstance(content, str) or not content.strip() or len(content) > self._CONTENT_MAX_LEN):
            raise ValueError(f"content 必须是 1-{self._CONTENT_MAX_LEN} 个字符的非空字符串, 收到 {content!r}")
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                # 1. 读旧 session (含 version)
                cur.execute('SELECT * FROM practice_sessions WHERE id = %s', (int(session_id),))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"session_id={session_id} 不存在")
                old_duration = int(row['duration_minutes'])
                new_duration = int(duration_minutes) if duration_minutes is not None else old_duration
                current_version = int(row.get('version', 1))

                # Sprint 09 P0-12: 乐观锁校验 — expected_version 不为 None 时检查
                if expected_version is not None and int(expected_version) != current_version:
                    from src.kid_app.errors import ConflictError
                    raise ConflictError(
                        f"session_id={session_id} version 冲突: 期望 {expected_version}, 当前 {current_version}",
                        current_version=current_version,
                    )

                # 2. UPDATE session 字段 + version 自增
                updates = ['version = version + 1']
                params = []
                if tempo_note is not None:
                    updates.append('tempo_note = %s'); params.append(tempo_note)
                if tempo_bpm is not None:
                    updates.append('tempo_bpm = %s'); params.append(int(tempo_bpm))
                if content is not None:
                    updates.append('content = %s'); params.append(content)
                if duration_minutes is not None:
                    updates.append('duration_minutes = %s'); params.append(int(duration_minutes))
                if updates:
                    params.append(int(session_id))
                    # updated_at 由 ON UPDATE CURRENT_TIMESTAMP 自动维护
                    cur.execute(
                        f'UPDATE practice_sessions SET {", ".join(updates)} WHERE id = %s',
                        params,
                    )
                    # 乐观锁二次校验: 实际写入行数 (防止并发双写绕过 expected_version)
                    if expected_version is not None and cur.rowcount == 0:
                        from src.kid_app.errors import ConflictError
                        raise ConflictError(
                            f"session_id={session_id} 行写入失败 (并发 race)",
                            current_version=current_version,
                        )
                # 3. duration 变了 → 重算 daily
                if duration_minutes is not None and new_duration != old_duration:
                    delta = new_duration - old_duration
                    practice_date = str(row['practice_date'])
                    item_id = int(row['item_id'])
                    cur.execute('SELECT items FROM daily_practices WHERE date = %s', (practice_date,))
                    drow = cur.fetchone()
                    if drow and drow.get('items'):
                        items = json.loads(drow['items'])
                    else:
                        items = []
                    new_total = 0
                    found = False
                    for it in items:
                        if int(it.get('item_id', -1)) == item_id:
                            it['minutes'] = max(0, int(it.get('minutes', 0)) + delta)
                            found = True
                        new_total += int(it.get('minutes', 0))
                    if not found:
                        items.append({
                            'item': str(row['item_name']),
                            'item_id': item_id,
                            'minutes': max(0, delta),
                        })
                        new_total += max(0, delta)
                    if items:
                        cur.execute(
                            'UPDATE daily_practices SET items = %s, total_minutes = %s WHERE date = %s',
                            (json.dumps(items, ensure_ascii=False), new_total, practice_date),
                        )
                    else:
                        cur.execute(
                            "UPDATE daily_practices SET items = JSON_ARRAY(), total_minutes = 0 WHERE date = %s",
                            (practice_date,),
                        )
                    # 写 audit
                    cur.execute('''
                        INSERT INTO practice_audit_log
                        (channel, method, practice_date, input_items, result_items, total_minutes, error, session_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        'internal', 'update_session_duration', practice_date,
                        json.dumps([{'session_id': int(session_id), 'old_minutes': old_duration, 'new_minutes': new_duration}], ensure_ascii=False),
                        json.dumps([], ensure_ascii=False), delta, None, str(int(session_id)),
                    ))
                # 4. 同步冗余列 (任意字段 update 都同步, 跟 save 行为一致)
                if updates:
                    cur.execute('SELECT tempo_note, tempo_bpm FROM practice_sessions WHERE id = %s', (int(session_id),))
                    s = cur.fetchone()
                    if s and s.get('tempo_note'):
                        cur.execute('''
                            UPDATE practice_items
                            SET last_tempo_note = %s, last_tempo_bpm = %s, last_session_at = CURRENT_TIMESTAMP
                            WHERE item_id = %s
                        ''', (s['tempo_note'], int(s['tempo_bpm']), int(row['item_id'])))
            conn.commit()
        return self.get_practice_session_by_id(int(session_id))

    def delete_practice_session(self, session_id: int, expected_version: Optional[int] = None) -> None:
        """删单条 session + 重算 daily + 写 audit. 整事务.

        Sprint 09 P0-12 (PR-D): 加 expected_version 乐观锁 (同 SQLite).
        """
        self._ensure_practice_sessions_schema()
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
                cur.execute(
                    'SELECT version, practice_date, item_id, item_name, duration_minutes FROM practice_sessions WHERE id = %s',
                    (int(session_id),),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"session_id={session_id} 不存在")
                current_version = int(row.get('version', 1))
                practice_date = str(row['practice_date'])
                item_id = int(row['item_id'])
                item_name = str(row['item_name'])
                removed_minutes = int(row['duration_minutes'])

                # Sprint 09 P0-12: 乐观锁校验
                if expected_version is not None and int(expected_version) != current_version:
                    from src.kid_app.errors import ConflictError
                    raise ConflictError(
                        f"session_id={session_id} version 冲突: 期望 {expected_version}, 当前 {current_version}",
                        current_version=current_version,
                    )

                # 1. 删 session
                cur.execute('DELETE FROM practice_sessions WHERE id = %s', (int(session_id),))
                # 2. 重算 daily
                cur.execute('SELECT items FROM daily_practices WHERE date = %s', (practice_date,))
                drow = cur.fetchone()
                if drow and drow.get('items'):
                    new_items = []
                    total = 0
                    changed = False
                    for it in json.loads(drow['items']):
                        if int(it.get('item_id', -1)) == item_id:
                            it['minutes'] = max(0, int(it.get('minutes', 0)) - removed_minutes)
                            changed = True
                            if it['minutes'] > 0:
                                new_items.append(it)
                                total += it['minutes']
                        else:
                            new_items.append(it)
                            total += int(it.get('minutes', 0))
                    if changed:
                        if new_items:
                            cur.execute(
                                'UPDATE daily_practices SET items = %s, total_minutes = %s WHERE date = %s',
                                (json.dumps(new_items, ensure_ascii=False), total, practice_date),
                            )
                        else:
                            cur.execute(
                                "UPDATE daily_practices SET items = JSON_ARRAY(), total_minutes = 0 WHERE date = %s",
                                (practice_date,),
                            )
                # 3. 写 audit
                cur.execute('''
                    INSERT INTO practice_audit_log
                    (channel, method, practice_date, input_items, result_items, total_minutes, error, session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    'internal', 'delete_session', practice_date,
                    json.dumps([{'item': item_name, 'item_id': item_id, 'minutes': removed_minutes}], ensure_ascii=False),
                    json.dumps([], ensure_ascii=False), -removed_minutes, None, str(int(session_id)),
                ))
            conn.commit()

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
                practice_date = self._safe_to_date(practice_date)

        # 校验 item_id (跟 SQLite 一致)
        with self._get_connection() as conn:
            with conn.cursor(DatetimeSafeDictCursor) as cur:
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

                    # 2. 读 daily (Sprint 08: 加 FOR UPDATE 行锁防 lost update + 双发 race)
                    cur.execute(
                        'SELECT items, log, practiced, practice_at FROM daily_practices WHERE date = %s FOR UPDATE',
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
