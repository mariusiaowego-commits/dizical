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
    return render("config", active_nav="portal")


@router.get("/practice", response_class=HTMLResponse)
def config_practice():
    """练习科目配置页"""
    from src.kid_app.app import render
    
    categories = _get_categories_with_stats()
    items_grouped = _get_items_grouped()
    
    return render(
        "config-practice",
        active_nav="portal",  # sidebar: Portal
        categories=categories,
        items_grouped=items_grouped
    )


@router.get("/lessons", response_class=HTMLResponse)
def config_lessons():
    """课程管理页"""
    from src.kid_app.app import render
    return render("config-lessons", active_nav="portal")


@router.get("/records", response_class=HTMLResponse)
def config_records():
    """练习记录管理页"""
    from src.kid_app.app import render
    return render("config-records", active_nav="portal")


@router.get("/praise", response_class=HTMLResponse)
def config_praise():
    """表扬配置页"""
    from src.kid_app.app import render, get_setting
    return render(
        "config-praise",
        active_nav="portal",  # sidebar: Portal (praise 区块)
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
async def api_cancel_lesson(request: Request, date: str = ""):
    """取消课程. 兼容两种调用: query (?date=YYYY-MM-DD) 或 JSON body ({"date": "..."})."""
    try:
        import datetime as dt
        if not date:
            try:
                body = json.loads(await request.body())
                date = body.get('date', '')
            except Exception:
                pass
        if not date:
            return JSONResponse({"ok": False, "error": "缺少 date 参数"}, status_code=400)
        lesson_date = dt.date.fromisoformat(date)
        success = lesson_manager.cancel_lesson(lesson_date)
        return JSONResponse({"ok": success})
    except ValueError as e:
        return JSONResponse({"ok": False, "error": f"日期格式错误: {e}"}, status_code=400)
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


# ═══════════════════════════════════════════════════════════════════════════
# 盲盒主题配置
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/blindbox", response_class=HTMLResponse)
def config_blindbox():
    """盲盒主题配置页 — 选择每周打卡盲盒的故事主题"""
    from src.kid_app.app import render, get_setting, THEMES, ACTIVE_THEME_SETTING_KEY, DEFAULT_THEME
    current = get_setting(ACTIVE_THEME_SETTING_KEY) or DEFAULT_THEME
    return render(
        "config-blindbox",
        active_nav="portal",  # sidebar: Portal
        pin_locked="true" if get_setting("dad_pin") else "false",
        themes=list(THEMES.values()),
        current_theme=current,
    )


@router.get("/api/blindbox/theme")
async def api_get_blindbox_theme():
    """获取当前生效主题 + 所有可用主题列表"""
    from src.kid_app.app import get_active_theme, THEMES
    return JSONResponse({
        "ok": True,
        "active": get_active_theme()["slug"],
        "themes": [
            {
                "slug": t["slug"],
                "title": t["title"],
                "tag": t["tag"],
                "desc": t["desc"],
                "cover": t["cover"],
            }
            for t in THEMES.values()
        ],
    })


@router.post("/api/blindbox/theme")
async def api_set_blindbox_theme(request: Request):
    """切换当前生效主题（需 PIN 验证）"""
    from src.kid_app.app import THEMES, ACTIVE_THEME_SETTING_KEY

    body = json.loads(await request.body())
    pin = body.get("pin", "")
    slug = body.get("theme", "").strip()

    # PIN 验证（与 config-praise 保持一致）
    stored_pin = db.get_setting("dad_pin")
    if stored_pin and pin != stored_pin:
        return JSONResponse({"ok": False, "error": "PIN 不对"}, status_code=401)

    if slug not in THEMES:
        return JSONResponse({"ok": False, "error": f"未知主题: {slug}"}, status_code=400)

    db.set_setting(ACTIVE_THEME_SETTING_KEY, slug)
    return JSONResponse({"ok": True, "active": slug})


# ── 练习记录管理 API ─────────────────────────────────────────────────────────

@router.get("/practice-log", response_class=HTMLResponse)
def config_practice_log():
    """练习记录管理页面"""
    from src.kid_app.app import render
    return render("config-practice-log", active_nav="portal")


@router.get("/api/practice-week")
def api_practice_week(date_str: Optional[str] = None):
    """本周练习数据（汇总 + 每天明细）"""
    import datetime as dt
    if date_str:
        anchor = dt.date.fromisoformat(date_str)
    else:
        anchor = dt.date.today()
    week_start = practice_module.get_week_start(anchor)
    summary = practice_module.get_week_summary(week_start)
    days = practice_module.get_week_days(week_start)

    # 序列化 date 对象
    days_serialized = {}
    for key, day in days.items():
        days_serialized[key] = {
            **day,
            "date": day["date"].isoformat() if hasattr(day["date"], "isoformat") else str(day["date"]),
        }

    return JSONResponse({
        "week_start": week_start.isoformat(),
        "week_end": summary["week_end"].isoformat(),
        "total_minutes": summary["total_minutes"],
        "practice_days": summary["practice_days"],
        "item_totals": summary["item_totals"],
        "assignment": _serialize_assignment(summary["assignment"]),
        "days": days_serialized,
    })


@router.get("/api/assignments")
def api_get_assignments(weeks: int = 8, item: Optional[str] = None):
    """查询历史老师要求"""
    assignments = practice_module.query_assignments(weeks=weeks)
    result = []
    for a in assignments:
        entry = {
            "lesson_date": a["lesson_date"].isoformat() if hasattr(a["lesson_date"], "isoformat") else str(a["lesson_date"]),
            "items": a["items"],
            "notes": a.get("notes", ""),
        }
        if item:
            matched = [it for it in a["items"] if item in it.get("item", "")]
            if not matched:
                continue
            entry["items"] = matched
        result.append(entry)
    # 最新课在前
    result.sort(key=lambda x: x["lesson_date"], reverse=True)
    return JSONResponse({"assignments": result})


@router.post("/api/assignments")
async def api_create_assignment(request: Request):
    """录入老师要求"""
    body = json.loads(await request.body())
    lesson_date_str = body.get("lesson_date")
    items = body.get("items", [])  # [{item, item_id, requirement}]
    notes = body.get("notes", "")

    if not lesson_date_str:
        # 自动推算最近已上课日期
        from src.models import LessonStatus
        lessons = db.get_all_lessons()
        attended = [l for l in lessons if l.status == LessonStatus.ATTENDED]
        if attended:
            lesson_date = max(attended, key=lambda l: l.date).date
        else:
            return JSONResponse({"ok": False, "error": "无已上课记录，请指定 lesson_date"}, status_code=400)
    else:
        import datetime as dt
        lesson_date = dt.date.fromisoformat(lesson_date_str)

    if not items:
        return JSONResponse({"ok": False, "error": "请提供练习项目和要求"}, status_code=400)

    # 格式化 items
    formatted = []
    for it in items:
        formatted.append({
            "item": it.get("item", ""),
            "item_id": it.get("item_id"),
            "requirements": it.get("requirement", it.get("requirements", "")),
        })

    db.save_weekly_assignment(lesson_date, formatted, notes=notes or None)
    return JSONResponse({"ok": True, "lesson_date": lesson_date.isoformat()})


@router.get("/api/practice-month-summary")
def api_practice_month_summary(year: Optional[int] = None, month: Optional[int] = None):
    """月度练习汇总（用于月报生成）"""
    import datetime as dt
    today = dt.date.today()
    year = year or today.year
    month = month or today.month
    data = practice_module.get_month_summary(year, month)
    return JSONResponse({
        "year": year,
        "month": month,
        "total_minutes": data["total_minutes"],
        "practice_days": data["practice_days"],
        "item_totals": data["item_totals"],
        "daily_minutes": data.get("daily_minutes", {}),
    })


def _serialize_assignment(assignment):
    """序列化 weekly_assignment 对象"""
    if not assignment:
        return None
    result = {
        "items": assignment.get("items", []),
        "notes": assignment.get("notes", ""),
    }
    if "lesson_date" in assignment:
        ld = assignment["lesson_date"]
        result["lesson_date"] = ld.isoformat() if hasattr(ld, "isoformat") else str(ld)
    return result


# ── 练习月报生成 API ─────────────────────────────────────────────────────────

@router.get("/api/practice-report/history")
def api_practice_report_history(year: Optional[int] = None, month: Optional[int] = None):
    """查询已生成的月报图片"""
    import datetime as dt
    with db._get_connection() as conn:
        cursor = conn.cursor()
        if year and month:
            cursor.execute(
                "SELECT * FROM practice_reports WHERE year=? AND month=? ORDER BY created_at DESC",
                (year, month)
            )
        else:
            cursor.execute("SELECT * FROM practice_reports ORDER BY year DESC, month DESC, created_at DESC")
        rows = cursor.fetchall()

    reports = []
    for row in rows:
        reports.append({
            "id": row["id"],
            "year": row["year"],
            "month": row["month"],
            "style": row["style"],
            "prompt": row["prompt"] or "",
            "image_url": f"/config/api/practice-report/image/{row['id']}",
            "created_at": row["created_at"],
        })
    return JSONResponse({"reports": reports})


@router.get("/api/practice-report/image/{report_id}")
def api_practice_report_image(report_id: int):
    """返回月报图片文件"""
    from fastapi.responses import FileResponse
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT image_path FROM practice_reports WHERE id=?", (report_id,))
        row = cursor.fetchone()
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    import os
    if not os.path.exists(row["image_path"]):
        return JSONResponse({"error": "file missing"}, status_code=404)
    return FileResponse(row["image_path"], media_type="image/png")


@router.post("/api/practice-report/generate")
async def api_practice_report_generate(request: Request):
    """生成月报图片（SSE 流式状态输出）"""
    import datetime as dt
    import os
    import urllib.request
    from pathlib import Path
    from fastapi.responses import StreamingResponse

    body = json.loads(await request.body())
    year = body.get("year")
    month = body.get("month")
    style = body.get("style", "academic")

    if not year or not month:
        today = dt.date.today()
        year = year or today.year
        month = month or today.month

    # 项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    async def generate_stream():
        import asyncio
        import threading
        import queue

        result_queue = queue.Queue()

        def run_generation():
            try:
                # 步骤 1: 构建 prompt
                result_queue.put(("status", "构建 prompt..."))
                from src.report_templates import build_monthly_report_prompt
                prompt, aspect_ratio, data = build_monthly_report_prompt(year, month, style)
                result_queue.put(("status", f"Prompt 已构建（{len(prompt)} 字符）"))

                # 步骤 2: 调用 image_generate
                # 写入临时文件，通过 stdin 传给 hermes chat（避免命令行超长）
                import subprocess, tempfile
                result_queue.put(("status", "正在调用 hermes + FAL gpt-image-2 生成图片，约需 30-60 秒..."))
                query = f"用 image_generate 工具生成图片，prompt 如下，aspect_ratio 用 portrait：\n\n{prompt}"
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(query)
                    tmp_path = f.name
                # 用 shell 管道读取临时文件
                shell_cmd = f'hermes chat -q "$(cat {tmp_path})" -t image_gen --yolo -Q'
                proc = subprocess.Popen(
                    shell_cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    cwd=project_root, bufsize=1, text=True,
                )

                # 实时读取 stdout 每行输出
                output_lines = []
                for line in proc.stdout:
                    line = line.rstrip()
                    output_lines.append(line)
                    result_queue.put(("output", line))

                proc.wait(timeout=120)
                output = "\n".join(output_lines)
                result_queue.put(("status", f"hermes 进程结束 (exit={proc.returncode})"))

                # 清理临时文件
                import os
                os.unlink(tmp_path)

                # 从输出中提取图片路径或 URL
                image_source = None
                for line in output.split("\n"):
                    line = line.strip()
                    if "MEDIA:" in line:
                        parts = line.split("MEDIA:")
                        if len(parts) > 1:
                            candidate = parts[1].strip().split()[0]
                            if os.path.exists(candidate):
                                image_source = candidate
                                break
                    if line.startswith("http") and (".png" in line or ".jpg" in line or "fal" in line):
                        image_source = line
                        break
                    if line.startswith("/") and (line.endswith(".png") or line.endswith(".jpg")):
                        if os.path.exists(line):
                            image_source = line
                            break

                if not image_source:
                    result_queue.put(("error", f"未找到图片。hermes 输出:\n{output[:300]}"))
                    return

                result_queue.put(("status", "图片已获取，正在保存..."))

                # 步骤 3: 保存到本地
                report_dir = os.path.join(project_root, "data", "reports")
                os.makedirs(report_dir, exist_ok=True)
                filename = f"{year}-{month:02d}-练习报告-{style}.png"
                dest_path = os.path.join(report_dir, filename)

                if image_source.startswith("http"):
                    urllib.request.urlretrieve(image_source, dest_path)
                elif os.path.exists(image_source):
                    import shutil
                    shutil.copy2(image_source, dest_path)
                else:
                    result_queue.put(("error", f"图片路径无效: {image_source}"))
                    return

                result_queue.put(("status", "图片已保存，正在记录到数据库..."))

                # 步骤 4: 记录到数据库
                with db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO practice_reports (year, month, style, prompt, image_path) VALUES (?, ?, ?, ?, ?)",
                        (year, month, style, prompt, dest_path)
                    )
                    report_id = cursor.lastrowid

                result_queue.put(("done", {
                    "ok": True,
                    "report_id": report_id,
                    "image_url": f"/config/api/practice-report/image/{report_id}",
                    "year": year,
                    "month": month,
                    "style": style,
                }))

            except Exception as e:
                result_queue.put(("error", str(e)))

        # 在后台线程运行
        thread = threading.Thread(target=run_generation)
        thread.start()

        # 流式输出状态
        while True:
            try:
                msg_type, msg_data = result_queue.get(timeout=120)
                if msg_type == "status":
                    yield f"data: {json.dumps({'type': 'status', 'message': msg_data})}\n\n"
                elif msg_type == "output":
                    yield f"data: {json.dumps({'type': 'output', 'message': msg_data})}\n\n"
                elif msg_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': msg_data})}\n\n"
                    break
                elif msg_type == "done":
                    yield f"data: {json.dumps({'type': 'done', 'data': msg_data})}\n\n"
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': '生成超时（120秒）'})}\n\n"
                break

        thread.join(timeout=5)

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
