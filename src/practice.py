"""
竹笛练习管理模块
管理每日练习打卡、每周老师要求、练习进展记录
"""

import datetime as dt
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .database import db
from .models import LessonStatus


def get_last_attended_lesson_date_next() -> Optional[dt.date]:
    """
    获取最近一次已上课的下一天（作为 WeekStart）
    如果没有已上课记录，返回 None
    """
    lessons = db.get_all_lessons()
    attended = [l for l in lessons if l.status == LessonStatus.ATTENDED]
    if not attended:
        return None
    last_lesson = max(attended, key=lambda l: l.date)
    return last_lesson.date + dt.timedelta(days=1)


def get_week_start(date: dt.date) -> dt.date:
    """获取某日期所在周的周一日期"""
    return date - dt.timedelta(days=date.weekday())


def parse_practice_input(text: str) -> List[Dict[str, any]]:
    """
    解析自然语言练习输入
    支持格式：
    - "基本功20分钟，单吐15分钟"
    - "基本功20，单吐15"
    - "20分钟基本功，15分钟单吐"
    返回: [{"item": "基本功", "minutes": 20}, ...]
    """
    import re
    
    results = []
    
    # 模式1: 项目 + 数字 + 分钟/分
    pattern1 = r'([^\d\s]+?)(\d+)\s*(?:分钟|分)'
    matches = re.findall(pattern1, text)
    for item, minutes in matches:
        item = item.strip()
        if item and item not in ['今天', '练了', '了']:
            results.append({'item': item, 'minutes': int(minutes)})
    
    # 模式2: 数字 + 分钟/分 + 项目
    pattern2 = r'(\d+)\s*(?:分钟|分)\s*([^\d\s，,。]+)'
    matches = re.findall(pattern2, text)
    for minutes, item in matches:
        item = item.strip()
        if item and item not in ['今天', '练了', '了']:
            results.append({'item': item, 'minutes': int(minutes)})
    
    return results


def save_practice(date: dt.date, items: List[Dict], log: Optional[str] = None) -> int:
    """
    保存每日练习记录
    items: [{"item": "基本功", "minutes": 20}, ...]
    log: 详细练习记录/进展
    返回: 总分钟数
    """
    total = sum(item['minutes'] for item in items)

    # 确保所有练习项目都在项目库里
    for item in items:
        db.add_practice_item(item['item'])

    db.save_daily_practice(date, items, total, log)
    return total


def save_log(date: dt.date, log: str) -> None:
    """保存/追加每日练习详细记录到已存在的打卡记录"""
    existing = db.get_daily_practice(date)
    if existing:
        # 已有打卡，追加 log
        existing_log = existing.get('log') or ''
        new_log = f"{existing_log}\n{log}".strip() if existing_log else log
        db.save_daily_practice(date, existing['items'], existing['total_minutes'], new_log)
    else:
        # 没有打卡记录，创建一条仅有 log 的记录
        db.save_daily_practice(date, [], 0, log)


def get_categories() -> List[Dict]:
    """获取所有大科目"""
    return db.get_practice_categories()


def add_category(name: str, sort_order: int = 99) -> int:
    """新增大科目"""
    return db.add_practice_category(name, sort_order)


def update_category(cat_id: int, name: str, sort_order: Optional[int] = None) -> None:
    """更新大科目"""
    db.update_practice_category(cat_id, name, sort_order)


def delete_category(cat_id: int) -> None:
    """删除大科目（同时清空小科目的归属）"""
    db.delete_practice_category(cat_id)


def set_item_category(item_name: str, category_id: Optional[int]) -> None:
    """设置小科目归属大科目"""
    items = db.get_practice_items(active_only=False)
    for item in items:
        if item['name'] == item_name:
            db.update_practice_item_category(item['id'], category_id)
            return
    # 不存在则新增
    new_id = db.add_practice_item(item_name, category_id)
    return new_id


def save_progress(date: dt.date, note: str) -> None:
    """保存每日一句话进展（写入 daily_practices.log）"""
    db.save_progress_to_log(date, note)


def save_weekly_assignment(week_start: dt.date, items: List[Dict], notes: Optional[str] = None) -> None:
    """
    保存每周老师要求
    items: [{"item": "单吐练习", "requirement": "♩=82,84,86 各两天"}, ...]
    """
    # 确保所有练习项目都在项目库里
    for item in items:
        db.add_practice_item(item['item'])
    
    db.save_weekly_assignment(week_start, items, notes)


def get_week_summary(week_start: dt.date) -> Dict:
    """获取某周的练习汇总"""
    week_end = week_start + dt.timedelta(days=6)
    
    practices = db.get_daily_practices_in_range(week_start, week_end)
    assignment = db.get_weekly_assignment(week_start)
    progress = db.get_progress_from_log_in_range(week_start, week_end)
    
    # 汇总各项目时长
    item_totals = {}
    total_minutes = 0
    practice_days = []
    
    for p in practices:
        total_minutes += p['total_minutes']
        practice_days.append(p['date'])
        for item in p['items']:
            name = item['item']
            item_totals[name] = item_totals.get(name, 0) + item['minutes']
    
    return {
        'week_start': week_start,
        'week_end': week_end,
        'assignment': assignment,
        'item_totals': item_totals,
        'total_minutes': total_minutes,
        'practice_days': len(practice_days),
        'progress': progress
    }


def get_month_summary(year: int, month: int) -> Dict:
    """获取某月的练习汇总"""
    start_date = dt.date(year, month, 1)
    if month == 12:
        end_date = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        end_date = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    
    practices = db.get_daily_practices_in_range(start_date, end_date)
    progress = db.get_progress_from_log_in_range(start_date, end_date)

    # 按项目汇总
    item_totals = {}
    total_minutes = 0
    practice_days = set()
    
    for p in practices:
        total_minutes += p['total_minutes']
        practice_days.add(p['date'])
        for item in p['items']:
            name = item['item']
            item_totals[name] = item_totals.get(name, 0) + item['minutes']
    
    # 按周分组
    weeks = []
    current = get_week_start(start_date)
    while current <= end_date:
        week_data = get_week_summary(current)
        # 只包含本月部分
        if week_data['practice_days'] > 0:
            weeks.append(week_data)
        current += dt.timedelta(days=7)
    
    return {
        'year': year,
        'month': month,
        'start_date': start_date,
        'end_date': end_date,
        'item_totals': item_totals,
        'total_minutes': total_minutes,
        'practice_days': len(practice_days),
        'total_days': end_date.day,
        'weeks': weeks,
        'progress': progress
    }


def _parse_date(date_str: str) -> Optional[dt.date]:
    """解析日期字符串，支持多种格式，统一返回 YYYY-MM-DD"""
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%m/%d', '%Y%m%d']:
        try:
            return dt.datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None


def import_logs_from_csv(csv_path: str) -> Tuple[int, int]:
    """
    从CSV批量导入练习进展log
    返回: (成功导入条数, 失败行数)

    CSV格式: Date,Log
    日期格式: YYYY-MM-DD
    逻辑: 有打卡则追加log，无打卡则新建仅log的记录
    """
    import csv

    success = 0
    failures = 0

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            try:
                date_str = row.get('Date', '').strip()
                log = row.get('Log', '').strip()

                if not date_str:
                    failures += 1
                    print(f"  Row {row_num}: missing date, skipping")
                    continue

                date = _parse_date(date_str)
                if not date:
                    failures += 1
                    print(f"  Row {row_num}: invalid date '{date_str}', skipping")
                    continue

                if not log:
                    failures += 1
                    print(f"  Row {row_num}: empty log, skipping")
                    continue

                save_log(date, log)
                success += 1
                print(f"  Imported log: {date.isoformat()}")

            except Exception as e:
                failures += 1
                print(f"  Row {row_num}: error {e}, skipping")
                continue

    return success, failures


def import_assignments_from_csv(csv_path: str) -> Tuple[int, int]:
    """
    从CSV批量导入每周老师要求
    返回: (成功导入周数, 失败行数)

    CSV格式: WeekStart,Item,Requirement
    日期格式: YYYY-MM-DD
    同一周的多条要求会合并为一条
    """
    import csv
    from collections import defaultdict

    failures = 0
    # 按周聚合: week_start -> (items, notes)
    weekly_data: dict = defaultdict(lambda: {'items': [], 'notes': None})

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row_num, row in enumerate(reader, start=2):
            try:
                week_str = row.get('WeekStart', '').strip()
                item = row.get('Item', '').strip()
                requirement = row.get('Requirement', '').strip()
                notes = row.get('Notes', '').strip() or None

                # 如果 WeekStart 为空，自动推算：上次上课的下一天
                if not week_str:
                    inferred = get_last_attended_lesson_date_next()
                    if inferred:
                        week_start = inferred
                        print(f"  Row {row_num}: WeekStart empty, auto-inferred to {week_start.isoformat()}")
                    else:
                        failures += 1
                        print(f"  Row {row_num}: no WeekStart and no attended lesson found, skipping")
                        continue
                else:
                    week_start = _parse_date(week_str)
                    if not week_start:
                        failures += 1
                        print(f"  Row {row_num}: invalid WeekStart '{week_str}', skipping")
                        continue

                if not item or not requirement:
                    failures += 1
                    print(f"  Row {row_num}: missing Item or Requirement, skipping")
                    continue

                weekly_data[week_start]['items'].append({'item': item, 'requirement': requirement})
                if notes:
                    weekly_data[week_start]['notes'] = notes

            except Exception as e:
                failures += 1
                print(f"  Row {row_num}: error {e}, skipping")
                continue

    success = 0
    for week_start, data in sorted(weekly_data.items()):
        try:
            save_weekly_assignment(week_start, data['items'], data['notes'])
            success += 1
            print(f"  Imported assignment: {week_start.isoformat()} ({len(data['items'])} items)")
        except Exception as e:
            failures += 1
            print(f"  Failed to save {week_start.isoformat()}: {e}")

    return success, failures


def import_from_csv(csv_path: str, date_column: str = 'Date') -> Tuple[int, int]:
    """
    从Notion导出的CSV导入练习记录
    返回: (成功导入天数, 失败行数)

    CSV格式: Name, Date, 上课, 乐理, 单吐, 基本功, 歌曲-吹, ...
    日期格式: YYYY-MM-DD
    跳过列: Name(只是展示名), Date, 上课, 乐理
    """
    import csv
    
    success = 0
    failures = 0
    
    # 跳过这些列（不是练习项目）
    skip_cols = {'Name', 'Date', '上课', '乐理', 'total', 'Total', 'Σ', '总时长'}
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):
            try:
                # 解析日期 - 用 Date 列
                date_str = row.get(date_column, '').strip()
                if not date_str:
                    failures += 1
                    print(f"  Row {row_num}: missing date, skipping")
                    continue
                
                date = _parse_date(date_str)
                if not date:
                    failures += 1
                    print(f"  Row {row_num}: invalid date '{date_str}', skipping")
                    continue
                
                # 收集练习项目（跳过特定列）
                items = []
                for col, val in row.items():
                    col_stripped = col.strip()
                    # 跳过非练习列
                    if col_stripped in skip_cols:
                        continue
                    # 跳过空值或0
                    if not val or val.strip() == '' or val.strip() == '0':
                        continue
                    try:
                        minutes = int(float(val.strip()))
                        if minutes > 0:
                            items.append({'item': col_stripped, 'minutes': minutes})
                    except:
                        continue
                
                if items:
                    save_practice(date, items)
                    success += 1
                    print(f"  Imported: {date} - {len(items)} items")
                else:
                    failures += 1
                    print(f"  Row {row_num}: no valid items, skipping")
                
            except Exception as e:
                failures += 1
                print(f"  Row {row_num}: error {e}, skipping")
                continue
    
    return success, failures


def get_practice_calendar(year: int, month: int) -> Dict[str, any]:
    """
    获取月度练习日历数据
    返回: {日期: {has_practice, total_minutes, items, log, progress}, ...}
    """
    start_date = dt.date(year, month, 1)
    if month == 12:
        end_date = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        end_date = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    
    practices = db.get_daily_practices_in_range(start_date, end_date)
    progress = db.get_progress_from_log_in_range(start_date, end_date)
    
    calendar = {}
    current = start_date
    while current <= end_date:
        calendar[current.isoformat()] = {
            'has_practice': False,
            'total_minutes': 0,
            'items': [],
            'log': None,
            'progress': None
        }
        current += dt.timedelta(days=1)
    
    for p in practices:
        key = p['date'].isoformat()
        if key in calendar:
            calendar[key]['has_practice'] = True
            calendar[key]['total_minutes'] = p['total_minutes']
            calendar[key]['items'] = p['items']
            calendar[key]['log'] = p.get('log')
    
    for date, note in progress.items():
        key = date.isoformat()
        if key in calendar:
            calendar[key]['progress'] = note
    
    return calendar
