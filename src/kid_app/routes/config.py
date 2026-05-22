"""配置管理台路由 - 练习科目配置"""

import json
from typing import Optional, List, Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.database import db
from src import practice as practice_module

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
