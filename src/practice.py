"""
竹笛练习管理模块
管理每日练习打卡、每周老师要求、练习进展记录
"""

import datetime as dt
import json
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


def _similarity(a: str, b: str) -> float:
    """
    计算两个字符串的相似度（0.0 ~ 1.0）。
    评分策略（从高到低）：
      1. 精确匹配 → 1.0
      2. 首字母全匹配（快速筛选）→ 0.9
      3. 子串/超串：输入是候选的子串（候选更具体）→ 0.85
      4. 子串/超串：候选是输入的子串（输入更宽泛）→ 0.60（降低误匹配）
      5. 字符重叠率（≥50%字符重叠）→ 0.4
      6. 编辑距离 → 0.2~0.35
    """
    a_lower = a.lower()
    b_lower = b.lower()

    # 1. 精确匹配
    if a_lower == b_lower:
        return 1.0

    # 2. 首字母全匹配（a 的首字母都在 b 开头出现）
    a_initials = ''.join(c for c in a_lower if c.isalnum())[:3]
    if a_initials and b_lower.startswith(a_initials):
        return 0.9

    len_a, len_b = len(a_lower), len(b_lower)
    # 3. a 是 b 的子串（b 更具体/更长，输入是简称）
    if a_lower in b_lower:
        # 短输入命中长名称：置信度高（例："单吐" in "单吐练习"）
        return 0.85
    # 4. b 是 a 的子串（a 更宽泛，输入是父类名）
    if b_lower in a_lower:
        # 长输入试图匹配短名称：降低权重避免泛称误匹配
        return 0.60

    # 5. 字符重叠率（公共字符 / 总字符）
    a_chars = set(a_lower)
    b_chars = set(b_lower)
    overlap = len(a_chars & b_chars)
    # 长度差异过大直接排除
    if max(len_a, len_b) == 0 or abs(len_a - len_b) > max(len_a, len_b) * 0.6:
        return 0.0
    overlap_ratio = overlap / max(len_a, len_b)
    if overlap_ratio >= 0.5:
        return 0.4 + overlap_ratio * 0.1  # 0.45 ~ 0.5

    # 6. 编辑距离（Levenshtein 简化版）
    # 只对中等长度字符串做，避免性能开销
    if max(len_a, len_b) <= 8:
        ed = _levenshtein(a_lower, b_lower)
        max_ed = max(len_a, len_b)
        return (1 - ed / max_ed) * 0.35 if ed < max_ed else 0.0

    return 0.0


def _levenshtein(a: str, b: str) -> int:
    """最小编辑距离（插入/删除/替换代价均为1）"""
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,   # 删除
                curr[j] + 1,       # 插入
                prev[j] + (ca != cb)  # 替换
            ))
        prev = curr
    return prev[-1]


def find_similar_items(name: str, threshold: float = 0.3) -> List[Tuple[int, str, float]]:
    """
    查找与 name 相似的已有小科目。
    返回 [(id, name, similarity), ...]，按相似度降序。
    threshold 以下的不返回。
    """
    all_items = db.get_practice_items(active_only=False)
    scored = []
    for item in all_items:
        score = _similarity(name, item['name'])
        if score >= threshold:
            scored.append((item['item_id'], item['name'], score))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored


def resolve_practice_item(item_name: str) -> Tuple[bool, str]:
    """
    将用户输入的 item_name 解析为确定的已有小科目名称。
    返回 (cancelled, resolved_name)：
      - cancelled=True 表示用户取消
      - resolved_name 为最终确认的名称（可能是新建的）
    调用方负责打印候选列表并收集用户选择。
    """
    all_items = db.get_practice_items(active_only=False)
    # 精确匹配 → 直接使用，不弹窗
    for item in all_items:
        if item['name'] == item_name:
            return False, item['name']
    # 查相似
    similar = find_similar_items(item_name)
    return False, item_name  # 调用方应根据 similar 决定是否弹窗


def save_practice(date: dt.date, items: List[Dict], log: Optional[str] = None,
                 channel: Optional[str] = None, method: Optional[str] = None) -> int:
    """
    保存每日练习记录
    items: [{"item": "基本功", "minutes": 20}, ...]
    log: 详细练习记录/进展
    channel/method: 溯源用，CLI 调用时传 ('cli', 'cli_log')
    返回: 总分钟数
    """
    total = sum(item['minutes'] for item in items)
    db.save_daily_practice(date, items, total, log,
                           channel=channel, method=method)
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
    """设置小科目归属大科目。科目不存在则抛出 ValueError。"""
    items = db.get_practice_items(active_only=False)
    for item in items:
        if item['name'] == item_name:
            db.update_practice_item_category(item['item_id'], category_id)
            return None
    raise ValueError(f"科目 '{item_name}' 不存在，无法设置分类")


def save_progress(date: dt.date, note: str) -> None:
    """保存每日一句话进展（写入 daily_practices.log）"""
    db.save_progress_to_log(date, note)


def save_weekly_assignment(lesson_date: dt.date, items: List[Dict], notes: Optional[str] = None, images: Optional[List[str]] = None, videos: Optional[List[Dict]] = None) -> None:
    """
    保存每课老师要求
    items: [{"item": "单吐练习", "requirements": "♩=82,84,86 各两天", "metronome": "♩=82"}, ...]
    """
    db.save_weekly_assignment(lesson_date, items, notes, images, videos)


def query_assignments(
    start: Optional[dt.date] = None,
    end: Optional[dt.date] = None,
    weeks: Optional[int] = None,
) -> List[Dict]:
    """
    查询每周老师要求，支持日期范围或过去 N 周。

    返回: [{
        "week_start": date,
        "items": [{"item": "...", "requirements": "...", "metronome": "..."}],
        "notes": "...",
        "total_items": N
    }, ...]
    """
    if weeks is not None:
        end_date = dt.date.today() + dt.timedelta(weeks=1)
        start_date = end_date - dt.timedelta(weeks=weeks)
    elif start and end:
        start_date, end_date = start, end
    else:
        # 默认过去 4 周（多往前看一周，覆盖当前所在周）
        end_date = dt.date.today() + dt.timedelta(weeks=1)
        start_date = end_date - dt.timedelta(weeks=4)

    return db.get_weekly_assignments_in_range(start_date, end_date)


def get_assignments_summary(weeks: int = 4) -> Dict:
    """
    汇总过去 N 周的作业要求。
    返回: {
        "total_weeks": N,
        "weeks": [...],  # 每周明细
        "item_counts": {"项目名": 出现次数},
        "recent_items": [{"week_start": date, "item": name, "requirements": text}, ...]
    }
    """
    assignments = query_assignments(weeks=weeks)

    item_counts: Dict[str, int] = {}
    recent_items: List[Dict] = []

    for a in assignments:
        for it in a['items']:
            name = it['item']
            item_counts[name] = item_counts.get(name, 0) + 1
            recent_items.append({
                'lesson_date': a['lesson_date'],
                'item': name,
                'requirements': it['requirements'] if 'requirements' in it else it.get('requirement', ''),
            })

    return {
        'total_weeks': len(assignments),
        'weeks': assignments,
        'item_counts': item_counts,
        'recent_items': recent_items,
    }


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
        items_raw = p['items']
        if isinstance(items_raw, str):
            items_raw = json.loads(items_raw)
        for item in (items_raw or []):
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


def get_week_days(week_start: dt.date) -> Dict[str, Dict]:
    """
    获取某周每天的练习明细（用于日历网格渲染）
    返回: {日期str: {date, has_practice, total_minutes, items, progress, is_today, is_future}, ...}
    """
    week_end = week_start + dt.timedelta(days=6)
    today = dt.date.today()

    practices = db.get_daily_practices_in_range(week_start, week_end)
    progress = db.get_progress_from_log_in_range(week_start, week_end)

    # 构建每天的记录（7天必须有值）
    days = {}
    for i in range(7):
        d = week_start + dt.timedelta(days=i)
        days[d.isoformat()] = {
            'date': d,
            'has_practice': False,
            'total_minutes': 0,
            'items': [],
            'progress': None,
            'is_today': d == today,
            'is_future': d > today,
        }

    for p in practices:
        raw = p['date']
        key = raw.isoformat()[:10] if hasattr(raw, 'isoformat') else str(raw)[:10]
        if key in days:
            days[key]['has_practice'] = True
            days[key]['total_minutes'] = p['total_minutes']
            # 确保 items 是 list 而非 JSON 字符串（防御旧数据或异常路径）
            items_raw = p['items']
            if isinstance(items_raw, str):
                items_raw = json.loads(items_raw)
            days[key]['items'] = items_raw if items_raw else []

    for key, note in progress.items():
        if key in days:
            days[key]['progress'] = note

    return days


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
        items_raw = p['items']
        if isinstance(items_raw, str):
            items_raw = json.loads(items_raw)
        for item in (items_raw or []):
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
            d = dt.datetime.strptime(date_str, fmt).date()
            if d.year == 1900:
                d = d.replace(year=dt.date.today().year)
            return d
        except Exception:
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
                            item_id = db._match_practice_item_id(col_stripped)
                            if item_id is None:
                                print(f"  Row {row_num}: 科目 '{col_stripped}' 无法匹配到已知科目，跳过")
                                continue
                            items.append({'item': col_stripped, 'item_id': item_id, 'minutes': minutes})
                    except Exception:
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
        raw = p['date']
        key = raw.isoformat()[:10] if hasattr(raw, 'isoformat') else str(raw)[:10]
        if key in calendar:
            calendar[key]['has_practice'] = True
            calendar[key]['total_minutes'] = p['total_minutes']
            calendar[key]['items'] = p['items']
            calendar[key]['log'] = p.get('log')
    
    for key, note in progress.items():
        if key in calendar:
            calendar[key]['progress'] = note

    return calendar


def get_week_practices(week_start: dt.date) -> Dict:
    """导出周报用的练习数据（兼容 export_weekly_practice_report）"""
    summary = get_week_summary(week_start)
    days = get_week_days(week_start)
    return {
        "daily": [
            {
                "date": d.isoformat(),
                "total_minutes": days[d.isoformat()]["total_minutes"],
                "items": days[d.isoformat()]["items"],
                "progress_note": days[d.isoformat()].get("progress"),
            }
            for d in [week_start + dt.timedelta(days=i) for i in range(7)]
        ]
    }


def get_week_stats(week_start: dt.date) -> Dict:
    """导出周报用的统计数据（兼容 export_weekly_practice_report）"""
    summary = get_week_summary(week_start)
    return {
        "practice_days": summary["practice_days"],
        "total_minutes": summary["total_minutes"],
        "avg_minutes": summary["total_minutes"] / max(summary["practice_days"], 1),
    }
