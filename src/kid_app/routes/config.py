"""配置管理台路由 - 练习科目配置"""

import json
from typing import Optional, List, Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.database import db
from src import practice as practice_module
from src.lesson_manager import LessonManager
from src.payment import PaymentManager
from src.models import Lesson, LessonStatus, PaymentStatus

lesson_manager = LessonManager()
payment_manager = PaymentManager()

router = APIRouter(prefix="/config", tags=["config"])


# ─── 辅助函数 ───────────────────────────────────────────────────────────────

def _get_categories_with_stats() -> List[Dict]:
    """获取所有大科目，附带小科目数量统计"""
    categories = practice_module.get_categories()
    items = db.get_practice_items(active_only=False, include_archived=True)
    
    for cat in categories:
        cat_items = [i for i in items if i.get('category_id') == cat['id']]
        cat['item_count'] = len(cat_items)
        cat['active_count'] = len([i for i in cat_items if not i.get('is_archived')])
        cat['archived_count'] = len([i for i in cat_items if i.get('is_archived')])
    
    return categories


def _get_items_grouped() -> Dict:
    """获取所有小科目，按状态分组"""
    items = db.get_practice_items(active_only=False, include_archived=True)
    categories = practice_module.get_categories()
    cat_map = {c['id']: c['name'] for c in categories}
    
    result = {
        'categorized': {},  # 按大科目分组
        'uncategorized': [],  # 未归属
        'archived': []  # 已归档
    }
    
    for item in items:
        item['category_name'] = cat_map.get(item.get('category_id'), '')
        
        if item.get('is_archived'):
            result['archived'].append(item)
        elif not item.get('category_id'):
            result['uncategorized'].append(item)
        else:
            cat_id = item['category_id']
            if cat_id not in result['categorized']:
                result['categorized'][cat_id] = {
                    'id': cat_id,
                    'name': cat_map.get(cat_id, ''),
                    'items': []
                }
            result['categorized'][cat_id]['items'].append(item)
    
    return result


# ─── 页面路由 ───────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def config_home():
    """配置主页 - 显示配置模块列表"""
    from src.kid_app.app import render
    return render("config")


@router.get("/practice", response_class=HTMLResponse)
def config_practice():
    """练习科目配置页"""
    from src.kid_app.app import render
    
    categories = _get_categories_with_stats()
    items_grouped = _get_items_grouped()
    
    return render(
        "config-practice",
        categories=categories,
        items_grouped=items_grouped
    )


@router.get("/lessons", response_class=HTMLResponse)
def config_lessons():
    """课程管理页"""
    from src.kid_app.app import render
    return render("config-lessons")


@router.get("/records", response_class=HTMLResponse)
def config_records():
    """练习记录管理页"""
    from src.kid_app.app import render
    return render("config-records")


@router.get("/praise", response_class=HTMLResponse)
def config_praise():
    """表扬配置页"""
    from src.kid_app.app import render, get_setting
    return render(
        "config-praise",
        pin_locked="true" if get_setting("dad_pin") else "false"
    )


# ─── API: 大科目 CRUD ───────────────────────────────────────────────────────

@router.get("/api/practice/categories")
def api_get_categories():
    """获取所有大科目"""
    categories = _get_categories_with_stats()
    return JSONResponse({"categories": categories})


@router.post("/api/practice/categories")
async def api_create_category(request: Request):
    """新增大科目"""
    try:
        body = json.loads(await request.body())
        name = body.get("name", "").strip()
        
        if not name:
            return JSONResponse({"ok": False, "error": "名称不能为空"}, status_code=400)
        
        # 检查重名
        existing = practice_module.get_categories()
        if any(c['name'] == name for c in existing):
            return JSONResponse({"ok": False, "error": f"大科目「{name}」已存在"}, status_code=409)
        
        # 计算sort_order（追加到末尾）
        max_order = max((c['sort_order'] for c in existing), default=0)
        cat_id = practice_module.add_category(name, sort_order=max_order + 1)
        
        return JSONResponse({"ok": True, "id": cat_id, "name": name})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.put("/api/practice/categories/{cat_id}")
async def api_update_category(cat_id: int, request: Request):
    """更新大科目（改名/排序）"""
    try:
        body = json.loads(await request.body())
        name = body.get("name")
        sort_order = body.get("sort_order")
        
        # 验证大科目存在
        categories = practice_module.get_categories()
        target = next((c for c in categories if c['id'] == cat_id), None)
        if not target:
            return JSONResponse({"ok": False, "error": "大科目不存在"}, status_code=404)
        
        # 检查重名（如果改名）
        if name and name != target['name']:
            if any(c['name'] == name for c in categories):
                return JSONResponse({"ok": False, "error": f"大科目「{name}」已存在"}, status_code=409)
        
        # 更新
        practice_module.update_category(
            cat_id,
            name=name or target['name'],
            sort_order=sort_order if sort_order is not None else target['sort_order']
        )
        
        return JSONResponse({"ok": True})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.delete("/api/practice/categories/{cat_id}")
async def api_delete_category(cat_id: int):
    """删除大科目（仅清空归属关系，不删除小科目）"""
    try:
        # 验证大科目存在
        categories = practice_module.get_categories()
        target = next((c for c in categories if c['id'] == cat_id), None)
        if not target:
            return JSONResponse({"ok": False, "error": "大科目不存在"}, status_code=404)
        
        # 清空该大科目下所有小科目的category_id
        items = db.get_practice_items(active_only=False, include_archived=True)
        for item in items:
            if item.get('category_id') == cat_id:
                practice_module.set_item_category(item['name'], None)
        
        # 删除大科目
        practice_module.delete_category(cat_id)
        
        return JSONResponse({"ok": True})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ─── API: 大科目排序 ─────────────────────────────────────────────────────────

@router.put("/api/practice/categories/order")
async def api_reorder_categories(request: Request):
    """批量更新大科目排序"""
    try:
        body = json.loads(await request.body())
        order = body.get("order", [])  # [{id: 1, sort_order: 1}, ...]
        
        if not order:
            return JSONResponse({"ok": False, "error": "排序数据为空"}, status_code=400)
        
        # 验证所有ID存在
        categories = practice_module.get_categories()
        cat_ids = {c['id'] for c in categories}
        for item in order:
            if item['id'] not in cat_ids:
                return JSONResponse({"ok": False, "error": f"大科目ID {item['id']} 不存在"}, status_code=400)
        
        # 更新排序
        for item in order:
            cat = next(c for c in categories if c['id'] == item['id'])
            practice_module.update_category(item['id'], cat['name'], sort_order=item['sort_order'])
        
        return JSONResponse({"ok": True})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ─── API: 小科目 CRUD ───────────────────────────────────────────────────────

@router.get("/api/practice/items")
def api_get_items(include_archived: bool = True):
    """获取所有小科目"""
    items = db.get_practice_items(active_only=False, include_archived=include_archived)
    categories = practice_module.get_categories()
    cat_map = {c['id']: c['name'] for c in categories}
    
    for item in items:
        item['category_name'] = cat_map.get(item.get('category_id'), '')
    
    return JSONResponse({"items": items})


@router.post("/api/practice/items")
async def api_create_item(request: Request):
    """新增小科目"""
    try:
        body = json.loads(await request.body())
        name = body.get("name", "").strip()
        category_id = body.get("category_id")
        
        if not name:
            return JSONResponse({"ok": False, "error": "名称不能为空"}, status_code=400)
        
        # 检查重名
        existing = db.get_practice_items(active_only=False, include_archived=True)
        if any(i['name'] == name for i in existing):
            return JSONResponse({"ok": False, "error": f"小科目「{name}」已存在"}, status_code=409)
        
        # 新增
        item_id = db.add_practice_item(name, category_id=category_id)
        
        return JSONResponse({"ok": True, "item_id": item_id, "name": name})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.put("/api/practice/items/{item_id}/rename")
async def api_rename_item(item_id: int, request: Request):
    """重命名小科目"""
    try:
        body = json.loads(await request.body())
        new_name = body.get("name", "").strip()
        
        if not new_name:
            return JSONResponse({"ok": False, "error": "名称不能为空"}, status_code=400)
        
        # 验证小科目存在
        items = db.get_practice_items(active_only=False, include_archived=True)
        target = next((i for i in items if i['item_id'] == item_id), None)
        if not target:
            return JSONResponse({"ok": False, "error": "小科目不存在"}, status_code=404)
        
        # 检查重名
        if any(i['name'] == new_name and i['item_id'] != item_id for i in items):
            return JSONResponse({"ok": False, "error": f"小科目「{new_name}」已存在"}, status_code=409)
        
        # 更新
        db.update_practice_item_name(item_id, new_name)
        
        return JSONResponse({"ok": True})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.delete("/api/practice/items/{item_id}")
async def api_delete_item(item_id: int):
    """删除小科目"""
    try:
        # 验证小科目存在
        items = db.get_practice_items(active_only=False, include_archived=True)
        target = next((i for i in items if i['item_id'] == item_id), None)
        if not target:
            return JSONResponse({"ok": False, "error": "小科目不存在"}, status_code=404)
        
        # 删除
        db.delete_practice_item(item_id)
        
        return JSONResponse({"ok": True})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ─── API: 归属关系 ───────────────────────────────────────────────────────────

@router.put("/api/practice/items/{item_id}/category")
async def api_set_item_category(item_id: int, request: Request):
    """设置小科目的归属大科目"""
    try:
        body = json.loads(await request.body())
        category_id = body.get("category_id")  # None表示取消归属
        
        # 验证小科目存在
        items = db.get_practice_items(active_only=False, include_archived=True)
        target = next((i for i in items if i['item_id'] == item_id), None)
        if not target:
            return JSONResponse({"ok": False, "error": "小科目不存在"}, status_code=404)
        
        # 验证大科目存在（如果设置了category_id）
        if category_id is not None:
            categories = practice_module.get_categories()
            if not any(c['id'] == category_id for c in categories):
                return JSONResponse({"ok": False, "error": "大科目不存在"}, status_code=404)
        
        # 更新归属
        practice_module.set_item_category(target['name'], category_id)
        
        return JSONResponse({"ok": True})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ─── API: 归档管理 ───────────────────────────────────────────────────────────

@router.post("/api/practice/items/{item_id}/archive")
async def api_archive_item(item_id: int):
    """归档小科目"""
    try:
        # 验证小科目存在
        items = db.get_practice_items(active_only=False, include_archived=True)
        target = next((i for i in items if i['item_id'] == item_id), None)
        if not target:
            return JSONResponse({"ok": False, "error": "小科目不存在"}, status_code=404)
        
        if target.get('is_archived'):
            return JSONResponse({"ok": False, "error": "小科目已归档"}, status_code=409)
        
        # 归档
        db.archive_practice_item(item_id)
        
        return JSONResponse({"ok": True})
    
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/practice/items/{item_id}/unarchive")
async def api_unarchive_item(item_id: int):
    """取消归档"""
    try:
        # 验证小科目存在
        items = db.get_practice_items(active_only=False, include_archived=True)
        target = next((i for i in items if i['item_id'] == item_id), None)
        if not target:
            return JSONResponse({"ok": False, "error": "小科目不存在"}, status_code=404)
        
        if not target.get('is_archived'):
            return JSONResponse({"ok": False, "error": "小科目未归档"}, status_code=409)
        
        # 取消归档
        db.unarchive_practice_item(item_id)

        return JSONResponse({"ok": True})

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ─── API: 练习记录 ───────────────────────────────────────────────────────────

@router.get("/api/records/stats")
def api_records_stats():
    """本周+本月练习统计"""
    import datetime as dt
    today = dt.date.today()
    week_start = today - dt.timedelta(days=today.weekday())
    week_practices = db.get_daily_practices_in_range(week_start, today)
    week_mins = sum(p.get('total_minutes', 0) for p in week_practices)
    week_days = sum(1 for p in week_practices if p.get('total_minutes', 0) > 0)
    month_start = dt.date(today.year, today.month, 1)
    month_practices = db.get_daily_practices_in_range(month_start, today)
    month_mins = sum(p.get('total_minutes', 0) for p in month_practices)
    month_days = sum(1 for p in month_practices if p.get('total_minutes', 0) > 0)
    return JSONResponse({
        "week": {"minutes": week_mins, "days": week_days, "start": week_start.isoformat(), "end": today.isoformat()},
        "month": {"minutes": month_mins, "days": month_days, "start": month_start.isoformat()}
    })


@router.get("/api/records")
def api_get_records(year: int, month: int):
    """获取指定月份的练习日历数据（每天是否有练习）"""
    import datetime as dt
    start = dt.date(year, month, 1)
    if month == 12:
        end = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        end = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    practices = db.get_daily_practices_in_range(start, end)
    result = {}
    for p in practices:
        d = p['date']
        items_raw = p.get('items', '')
        if isinstance(items_raw, str):
            try:
                items_raw = json.loads(items_raw)
            except Exception:
                items_raw = []
        result[d.isoformat()] = {
            'total_minutes': p.get('total_minutes', 0),
            'item_count': len(items_raw) if items_raw else 0,
            'practiced': p.get('practiced', 'Y')
        }
    return JSONResponse(result)


@router.get("/api/records/{date_str}")
def api_get_record(date_str: str):
    """获取某天的练习记录"""
    import datetime as dt
    try:
        date = dt.date.fromisoformat(date_str)
    except ValueError:
        return JSONResponse({"ok": False, "error": "日期格式错误"}, status_code=400)

    record = db.get_daily_practice(date)
    if not record:
        return JSONResponse({"ok": False, "error": "当天无记录"}, status_code=404)

    items_raw = record.get('items', '')
    if isinstance(items_raw, str):
        try:
            items_raw = json.loads(items_raw)
        except Exception:
            items_raw = []

    # 补上 item_id（从名称匹配）
    all_items = {i['name']: i['item_id'] for i in db.get_practice_items(active_only=True)}
    for item in items_raw:
        item['item_id'] = all_items.get(item.get('item'))

    return JSONResponse({
        "date": date_str,
        "total_minutes": record.get('total_minutes', 0),
        "items": items_raw,
        "log": record.get('log', ''),
        "practiced": record.get('practiced', 'Y')
    })


@router.post("/api/records")
async def api_save_record(request: Request):
    """新增/覆盖练习记录"""
    try:
        body = json.loads(await request.body())
        date_str = body.get('date')
        items = body.get('items', [])
        total_minutes = body.get('total_minutes', 0)
        log = body.get('log', '')
        practiced = body.get('practiced', 'Y')

        if not date_str:
            return JSONResponse({"ok": False, "error": "日期不能为空"}, status_code=400)

        import datetime as dt
        date = dt.date.fromisoformat(date_str)

        if total_minutes == 0 and items:
            total_minutes = sum(i.get('minutes', 0) for i in items)

        db.save_daily_practice(
            date=date,
            items=items,
            total_minutes=total_minutes,
            log=log,
            practiced=practiced,
            channel='web',
            method='config-records'
        )
        return JSONResponse({"ok": True})

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.delete("/api/records/{date_str}")
async def api_delete_record(date_str: str):
    """清空某天练习记录（不物理删除，只清零）"""
    try:
        import datetime as dt
        date = dt.date.fromisoformat(date_str)
        db.save_daily_practice(
            date=date,
            items=[],
            total_minutes=0,
            log='',
            practiced='N',
            channel='web',
            method='config-records-delete'
        )
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ─── API: 课程管理 ───────────────────────────────────────────────────────────

@router.get("/api/lessons")
async def api_lessons(year: int, month: int):
    """获取指定月份的课程列表"""
    try:
        lessons = lesson_manager.get_lessons(year, month)
        return {
            "ok": True,
            "lessons": [
                {
                    "date": l.date.isoformat(),
                    "time": l.time.strftime("%H:%M"),
                    "status": l.status.value,
                    "fee": l.fee,
                    "fee_paid": l.fee_paid,
                    "notes": l.notes,
                }
                for l in lessons
            ]
        }
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/lessons")
async def api_add_lesson(date: str):
    """添加课程"""
    try:
        import datetime as dt
        lesson_date = dt.date.fromisoformat(date)
        lesson = lesson_manager.add_lesson(lesson_date)
        return JSONResponse({"ok": True, "lesson": {
            "date": lesson.date.isoformat(),
            "time": lesson.time.strftime("%H:%M"),
            "status": lesson.status.value,
            "fee": lesson.fee,
        }})
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/lessons/cancel")
async def api_cancel_lesson(date: str):
    """取消课程"""
    try:
        import datetime as dt
        lesson_date = dt.date.fromisoformat(date)
        success = lesson_manager.cancel_lesson(lesson_date)
        return JSONResponse({"ok": success})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/lessons/confirm")
async def api_confirm_lesson(date: str):
    """确认上课"""
    try:
        import datetime as dt
        lesson_date = dt.date.fromisoformat(date)
        lesson = lesson_manager.confirm_attendance(lesson_date)
        if lesson:
            return JSONResponse({"ok": True, "lesson": {
                "date": lesson.date.isoformat(),
                "status": lesson.status.value,
            }})
        return JSONResponse({"ok": False, "error": "未找到课程"}, status_code=404)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/lessons/reschedule")
async def api_reschedule_lesson(from_date: str, to_date: str):
    """调课"""
    try:
        import datetime as dt
        fd = dt.date.fromisoformat(from_date)
        td = dt.date.fromisoformat(to_date)
        lesson = lesson_manager.reschedule_lesson(fd, td)
        return JSONResponse({"ok": True, "lesson": {
            "date": lesson.date.isoformat(),
            "time": lesson.time.strftime("%H:%M"),
        }})
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/lessons/generate")
async def api_generate_lessons(year: int, month: int, overwrite: bool = False):
    """生成月度课程计划"""
    try:
        plan = lesson_manager.generate_monthly_lessons(year, month, overwrite=overwrite)
        lessons = lesson_manager.get_lessons(year, month)
        return JSONResponse({"ok": True, "total_lessons": plan.total_lessons, "holiday_conflicts": plan.holiday_conflicts, "lessons": [
            {"date": l.date.isoformat(), "time": l.time.strftime("%H:%M"), "status": l.status.value}
            for l in lessons
        ]})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/api/lessons/stats")
async def api_lesson_stats(year: int, month: int):
    """课程统计"""
    try:
        lessons = lesson_manager.get_lessons(year, month)
        ps = payment_manager.get_monthly_payment_status(year, month)
        arranged = len([l for l in lessons if l.status == LessonStatus.SCHEDULED])
        attended = len([l for l in lessons if l.status == LessonStatus.ATTENDED])
        cancelled = len([l for l in lessons if l.status == LessonStatus.CANCELLED])
        total_fee = sum(l.fee for l in lessons if l.status != LessonStatus.CANCELLED)
        paid_fee = sum(l.fee for l in lessons if l.fee_paid and l.status != LessonStatus.CANCELLED)
        return JSONResponse({
            "ok": True,
            "arranged": arranged,
            "attended": attended,
            "cancelled": cancelled,
            "total_fee": total_fee,
            "paid_fee": paid_fee,
            "balance": total_fee - paid_fee,
            "last_lesson_date": str(ps.last_lesson_date) if ps.last_lesson_date else None,
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/api/lessons/fee-paid")
async def api_mark_fee_paid(date: str, paid: bool = True):
    """标记学费已缴"""
    try:
        import datetime as dt
        lesson_date = dt.date.fromisoformat(date)
        lesson = lesson_manager.mark_fee_paid(lesson_date, paid)
        return JSONResponse({"ok": True, "fee_paid": lesson.fee_paid if lesson else False})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ─── API: 练习统计（已移到上方 /api/records/stats） ────────────────────────────
