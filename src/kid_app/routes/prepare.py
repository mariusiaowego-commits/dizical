"""练习准备页面路由"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import datetime as dt
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from src.kid_app.app import app, render, get_child_name, get_practice_items, get_today_assignment, get_yesterday_practice

router = APIRouter()

@router.get("/prepare", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def prepare_page():
    child_name = get_child_name()
    today = dt.date.today()
    week_start = today - dt.timedelta(days=today.weekday())
    assignment = get_today_assignment()
    yesterday = get_yesterday_practice()
    
    # 解析老师要求
    assignment_items = []
    if assignment and assignment.get("items"):
        for item in assignment["items"]:
            assignment_items.append(f"<li>{item['item']}：{item.get('requirements') or item.get('requirement', '')}</li>")
    assignment_html = "\n".join(assignment_items) if assignment_items else "<li>暂无本周要求</li>"
    
    # 分析昨天缺什么
    suggestions = []
    if yesterday:
        yesterday_items = {it["item"]: it["minutes"] for it in yesterday.get("items", [])}
        # 如果某项练习时长很短，给出建议
        for item_name, mins in yesterday_items.items():
            if mins < 10:
                suggestions.append(f"昨天{item_name}只练了{mins}分钟，今天可以多练一会儿")
    
    # 检查今天是否已打卡
    today_practice = None
    try:
        from src.database import db
        today_practice = db.get_daily_practice(today)
    except Exception:
        pass
    
    return render(
        "prepare",
        child_name=child_name,
        today_str=today.strftime("%Y年%m月%d日"),
        weekday_str=["周一","周二","周三","周四","周五","周六","周日"][today.weekday()],
        assignment_html=assignment_html,
        suggestions="\n".join(f"<li>{s}</li>" for s in suggestions) if suggestions else "",
        already_practiced="已打卡" if today_practice and today_practice.get("total_minutes", 0) > 0 else "未打卡",
    )
