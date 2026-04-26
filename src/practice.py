"""
竹笛练习管理模块
管理每日练习打卡、每周老师要求、练习进展记录
"""

import datetime as dt
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .database import db


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


def save_practice(date: dt.date, items: List[Dict]) -> int:
    """
    保存每日练习记录
    items: [{"item": "基本功", "minutes": 20}, ...]
    返回: 总分钟数
    """
    total = sum(item['minutes'] for item in items)
    
    # 确保所有练习项目都在项目库里
    for item in items:
        db.add_practice_item(item['item'])
    
    db.save_daily_practice(date, items, total)
    return total


def save_progress(date: dt.date, note: str) -> None:
    """保存每日一句话进展"""
    db.save_daily_progress(date, note)


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
    progress = db.get_daily_progress_in_range(week_start, week_end)
    
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
    progress = db.get_daily_progress_in_range(start_date, end_date)
    
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


def import_from_csv(csv_path: str, date_column: str = 'Date', items_columns: Optional[List[str]] = None) -> Tuple[int, int]:
    """
    从CSV导入练习记录
    返回: (成功导入天数, 失败行数)
    """
    import csv
    
    success = 0
    failures = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # 解析日期
                date_str = row.get(date_column, '').strip()
                if not date_str:
                    failures += 1
                    continue
                
                # 尝试多种日期格式
                date = None
                for fmt in ['%Y/%m/%d', '%Y-%m-%d', '%m/%d', '%Y%m%d']:
                    try:
                        date = dt.datetime.strptime(date_str, fmt).date()
                        break
                    except:
                        continue
                
                if not date:
                    failures += 1
                    continue
                
                # 收集练习项目
                items = []
                for col, val in row.items():
                    if col == date_column or col == 'Name' or col == 'total' or col == 'Total' or col == 'Σ':
                        continue
                    if not val or val.strip() == '' or val.strip() == '0':
                        continue
                    try:
                        minutes = int(float(val.strip()))
                        if minutes > 0:
                            items.append({'item': col.strip(), 'minutes': minutes})
                    except:
                        continue
                
                if items:
                    save_practice(date, items)
                    success += 1
                
            except Exception as e:
                failures += 1
                continue
    
    return success, failures


def get_practice_calendar(year: int, month: int) -> Dict[str, any]:
    """
    获取月度练习日历数据
    返回: {日期: {has_practice, total_minutes, items}, ...}
    """
    start_date = dt.date(year, month, 1)
    if month == 12:
        end_date = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        end_date = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    
    practices = db.get_daily_practices_in_range(start_date, end_date)
    progress = db.get_daily_progress_in_range(start_date, end_date)
    
    calendar = {}
    current = start_date
    while current <= end_date:
        calendar[current.isoformat()] = {
            'has_practice': False,
            'total_minutes': 0,
            'items': [],
            'progress': None
        }
        current += dt.timedelta(days=1)
    
    for p in practices:
        key = p['date'].isoformat()
        if key in calendar:
            calendar[key]['has_practice'] = True
            calendar[key]['total_minutes'] = p['total_minutes']
            calendar[key]['items'] = p['items']
    
    for date, note in progress.items():
        key = date.isoformat()
        if key in calendar:
            calendar[key]['progress'] = note
    
    return calendar
