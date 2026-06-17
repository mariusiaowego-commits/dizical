"""
Badge 后台管理路由 - 元数据编辑 + 排序管理

功能：
1. Badge 元数据编辑 (name/cond_text/description)
2. Badge 图片预览
3. Achievements 展示排序管理
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from src.database import db

router = APIRouter(prefix="/config/badge-admin", tags=["badge-admin"])


# ─── 辅助函数 ───────────────────────────────────────────────────────────────

def _get_all_badges() -> List[Dict[str, Any]]:
    """获取所有 badges 及其元数据"""
    conn = db._get_connection()
    cur = conn.execute("""
        SELECT id, name, type, category, stat_logic, description,
               threshold, unlock_strategy, cond_text, achieved_at_override,
               sort_order, display_on_achievements
        FROM achievements
        ORDER BY sort_order, id
    """)
    cols = [d[0] for d in cur.description]
    badges = [dict(zip(cols, row)) for row in cur.fetchall()]
    
    # 获取每个 badge 的图片信息
    for badge in badges:
        cur = conn.execute("""
            SELECT url, version, is_current
            FROM achievement_badges
            WHERE achievement_id = ?
            ORDER BY version DESC
            LIMIT 1
        """, (badge["id"],))
        row = cur.fetchone()
        if row:
            badge["badge_url"] = row[0]
            badge["badge_version"] = row[1]
            badge["badge_is_current"] = row[2]
        else:
            badge["badge_url"] = None
            badge["badge_version"] = None
            badge["badge_is_current"] = None
        
        # 获取解锁状态
        cur = conn.execute("""
            SELECT achieved, achieved_at
            FROM achievement_stats
            WHERE achievement_id = ?
        """, (badge["id"],))
        row = cur.fetchone()
        if row:
            badge["achieved"] = row[0] == "Y"
            badge["achieved_at"] = row[1]
        else:
            badge["achieved"] = False
            badge["achieved_at"] = None
    
    return badges


def _update_badge_metadata(badge_id: str, updates: Dict[str, Any]) -> bool:
    """更新 badge 元数据"""
    allowed_fields = {"name", "cond_text", "description", "stat_logic", 
                      "unlock_strategy", "achieved_at_override", "sort_order",
                      "display_on_achievements"}
    
    # 过滤允许的字段
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not filtered_updates:
        return False
    
    conn = db._get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in filtered_updates.keys())
    values = list(filtered_updates.values())
    values.append(badge_id)
    
    conn.execute(f"""
        UPDATE achievements
        SET {set_clause}
        WHERE id = ?
    """, values)
    conn.commit()
    return True


def _update_sort_order(order_list: List[Dict[str, Any]]) -> bool:
    """批量更新排序顺序"""
    conn = db._get_connection()
    for item in order_list:
        badge_id = item.get("id")
        sort_order = item.get("sort_order", 0)
        if badge_id:
            conn.execute("""
                UPDATE achievements
                SET sort_order = ?
                WHERE id = ?
            """, (sort_order, badge_id))
    conn.commit()
    return True


def _get_display_config() -> Dict[str, Any]:
    """获取显示配置"""
    conn = db._get_connection()
    cur = conn.execute("""
        SELECT key, value FROM settings
        WHERE key LIKE 'badge_display_%'
    """)
    config = {row[0]: row[1] for row in cur.fetchall()}
    
    return {
        "sort_mode": config.get("badge_display_sort_mode", "achieved_at_desc"),
        "show_locked": config.get("badge_display_show_locked", "true") == "true",
        "group_by_category": config.get("badge_display_group_by_category", "false") == "true",
    }


def _update_display_config(config: Dict[str, Any]) -> bool:
    """更新显示配置"""
    conn = db._get_connection()
    for key, value in config.items():
        db_key = f"badge_display_{key}"
        conn.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (db_key, str(value).lower() if isinstance(value, bool) else str(value)))
    conn.commit()
    return True


# ─── 页面路由 ───────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def badge_admin_page():
    """Badge 后台管理页面"""
    from src.kid_app.app import render
    
    badges = _get_all_badges()
    display_config = _get_display_config()
    
    return render(
        "config-badge-admin",
        active_nav="portal",
        badges_json=json.dumps(badges, ensure_ascii=False),
        display_config_json=json.dumps(display_config, ensure_ascii=False),
    )


# ─── API 端点 ───────────────────────────────────────────────────────────────

@router.get("/api/badges")
def api_get_badges():
    """获取所有 badges"""
    badges = _get_all_badges()
    return JSONResponse({"badges": badges})


@router.get("/api/badges/{badge_id}")
def api_get_badge(badge_id: str):
    """获取单个 badge"""
    badges = _get_all_badges()
    badge = next((b for b in badges if b["id"] == badge_id), None)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    return JSONResponse({"badge": badge})


@router.put("/api/badges/{badge_id}")
async def api_update_badge(badge_id: str, request: Request):
    """更新 badge 元数据"""
    body = await request.json()
    
    # 验证 badge 存在
    badges = _get_all_badges()
    badge = next((b for b in badges if b["id"] == badge_id), None)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    
    # 更新元数据
    success = _update_badge_metadata(badge_id, body)
    
    if success:
        return JSONResponse({"ok": True, "message": "Badge updated"})
    else:
        return JSONResponse({"ok": False, "message": "No valid fields to update"}, status_code=400)


@router.put("/api/badges/sort-order")
async def api_update_sort_order(request: Request):
    """批量更新排序顺序"""
    body = await request.json()
    order_list = body.get("order", [])
    
    if not order_list:
        return JSONResponse({"ok": False, "message": "No order provided"}, status_code=400)
    
    success = _update_sort_order(order_list)
    
    if success:
        return JSONResponse({"ok": True, "message": "Sort order updated"})
    else:
        return JSONResponse({"ok": False, "message": "Failed to update sort order"}, status_code=500)


@router.get("/api/display-config")
def api_get_display_config():
    """获取显示配置"""
    config = _get_display_config()
    return JSONResponse({"config": config})


@router.put("/api/display-config")
async def api_update_display_config(request: Request):
    """更新显示配置"""
    body = await request.json()
    
    success = _update_display_config(body)
    
    if success:
        return JSONResponse({"ok": True, "message": "Display config updated"})
    else:
        return JSONResponse({"ok": False, "message": "Failed to update config"}, status_code=500)
