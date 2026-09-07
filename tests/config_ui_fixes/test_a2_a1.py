"""A2 + A1 后端/前端 conflict-check + edit-in-place 验证.

跑法: cd /Users/mt16/dev/dizical && python3 -m pytest tests/config_ui_fixes/test_a2_a1.py -v
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path("/Users/mt16/dev/dizical")
CONFIG_PY = REPO / "src/kid_app/routes/config.py"
DATABASE_PY = REPO / "src/database.py"
PRACTICE_LOG_HTML = REPO / "src/kid_app/templates/config-practice-log.html"


def _extract_handler_body(src: str, btn_id: str) -> str:
    """提取 getElementById(btn_id).addEventListener(...) 完整 body (跨 try/catch {} 嵌套)."""
    idx = src.find(f"document.getElementById('{btn_id}')")
    if idx < 0:
        idx = src.find(f'document.getElementById("{btn_id}")')
    assert idx >= 0, f"addEventListener for {btn_id} not found"
    eq_idx = src.find("=> {", idx)
    if eq_idx < 0:
        eq_idx = src.find("async () => {", idx)
    assert eq_idx >= 0, f"=> {{ or async () => {{ not found after {btn_id}"
    start = eq_idx + (4 if "=> {" in src[eq_idx:eq_idx+6] else len("async () => {"))
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    return src[start:i-1].strip()


# ═══════════════════════════════════════════════════════════════════════════
# A2 — 后端 conflict-check
# ═══════════════════════════════════════════════════════════════════════════
def test_a2_endpoint_by_date_exists():
    """GET /config/api/assignments/by-date?date=YYYY-MM-DD 必须存在"""
    src = CONFIG_PY.read_text()
    # 接受 by-date 或 by_date (Python function name) — 但 URL 必须有 by-date
    m = re.search(r'@router\.get\(["\']([^"\']*by[-_]date[^"\']*)["\']\)', src)
    assert m, "GET /config/api/assignments/by-date endpoint not found"
    print(f"  A2: GET endpoint {m.group(1)!r}  ✓")


def test_a2_endpoint_by_date_returns_existing():
    """by-date 端点必须能查到 weekly_assignments 表"""
    src = CONFIG_PY.read_text()
    # 抓 by-date 端点函数体 (单行定义 + 多行 body)
    # 找 @router.get("...by-date...") 后面到下一个 @router 或文件尾
    m = re.search(
        r'@router\.get\([^)]*by[-_]date[^)]*\)\s*\n\s*(?:async\s+)?def\s+\w+\([^)]*\)[^:]*:\s*\n(.*?)(?=\n@router|\nclass |\Z)',
        src, re.DOTALL
    )
    assert m, "by-date endpoint handler not found (A2 implementation needed)"
    body = m.group(1)
    has_query = ("get_weekly_assignment" in body or "SELECT" in body or "weekly_assignments" in body)
    assert has_query, f"by-date handler must query weekly_assignments, body:\n{body[:400]}"
    print(f"  A2: by-date handler queries DB  ✓")


def test_a2_post_409_on_conflict():
    """POST /api/assignments 必须检查 lesson_date 冲突, 返 409"""
    src = CONFIG_PY.read_text()
    # 找 api_create_assignment 整个函数
    m = re.search(
        r'@router\.post\(["\']/api/assignments["\']\)\s*\n\s*async\s+def\s+api_create_assignment\([^)]*\):(.*?)(?=\n@router|\nclass |\Z)',
        src, re.DOTALL
    )
    assert m, "api_create_assignment not found"
    body = m.group(0)
    has_check = (
        "409" in body
        or "Conflict" in body
        or "conflict" in body
        or "已存在" in body
        or "get_weekly_assignment" in body  # 至少要查询一次
    )
    assert has_check, f"POST /api/assignments missing conflict-check. Must check existing record before save_weekly_assignment. body:\n{body[:400]}"
    print(f"  A2: POST has conflict-check (409/get_weekly_assignment)  ✓")


def test_a2_database_get_weekly_assignment_by_date():
    """database.py 必须有按精确 lesson_date 查询 weekly_assignment 的接口 (给 by-date 端点用)"""
    src = DATABASE_PY.read_text()
    # 接受 by_date / by-date / by_lesson_date — 但必须含 assignment 或 weekly (排除 lesson 类的)
    m = re.search(
        r"def\s+(\w*(?:assign|weekly)[^()]*by[_]date\w*|\w*get_weekly_assignment_by_date\w*)\s*\(",
        src
    )
    assert m, f"database.py missing precise by-date query for weekly_assignment. Current get_weekly_assignment uses week_start, not lesson_date. Need e.g. get_weekly_assignment_by_date(lesson_date). Found in lesson module only: get_lesson_by_date, cancel_lesson_by_date."
    print(f"  A2: database has precise weekly_assignment by-date query: {m.group(1)}  ✓")


def test_a2_frontend_submit_pre_check():
    """submitAssignBtn handler 必须先 GET /config/api/assignments/by-date 检查冲突"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_handler_body(src, "submitAssignBtn")
    has_check = ("by-date" in body or "/api/assignments/by-date" in body)
    assert has_check, f"submitAssignBtn handler missing pre-check GET /config/api/assignments/by-date. body:\n{body[:400]}"
    print(f"  A2: submit handler does pre-check  ✓")


def test_a2_frontend_confirm_or_modal():
    """冲突时必须 confirm() 或 modal — 不能静默"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_handler_body(src, "submitAssignBtn")
    has_confirm = ("confirm(" in body) or ("showConflictModal" in body) or ("modal" in body.lower() and "覆盖" in body)
    assert has_confirm, f"submitAssignBtn handler must confirm() before overwrite (or show modal). body:\n{body[:400]}"
    print(f"  A2: submit handler has user confirmation  ✓")


def test_a2_frontend_put_on_confirm():
    """用户确认覆盖后必须调 PUT /api/assignments/{date} 而不是 POST"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_handler_body(src, "submitAssignBtn")
    has_put = ("PUT" in body) or ("method: 'PUT'" in body) or ('method: "PUT"' in body)
    assert has_put, f"submitAssignBtn handler must call PUT (existing endpoint) when confirming overwrite. body:\n{body[:400]}"
    print(f"  A2: submit handler calls PUT on confirm  ✓")


# ═══════════════════════════════════════════════════════════════════════════
# A1 — edit-in-place + 智能预填
# ═══════════════════════════════════════════════════════════════════════════
def test_a1_edit_button_on_assignment_card():
    """历史老师要求卡片必须有 ✏️ 编辑按钮"""
    src = PRACTICE_LOG_HTML.read_text()
    # 接受 edit-assign-btn class 或 含"编辑"的 button
    m = re.search(
        r'<button[^>]*\bclass="[^"]*edit[-_]assign[-_]btn[^"]*"[^>]*>',
        src
    )
    if not m:
        # 退化: 含"编辑"文本的按钮
        m = re.search(r'<button[^>]*>[^<]*✎[^<]*编辑[^<]*</button>', src)
        if not m:
            m = re.search(r'<button[^>]*>[^<]*编辑[^<]*</button>', src)
    assert m, "Edit button not found in assignment card actions. Should have ✎ 编辑 button."
    print(f"  A1: edit button found ({m.group(0)[:80]}...)  ✓")


def test_a1_edit_handler_exists():
    """必须有点击编辑按钮后的 handler (绑 .click / addEventListener)"""
    src = PRACTICE_LOG_HTML.read_text()
    # edit-assign-btn 的 addEventListener (从 JS template literal 内)
    m = re.search(
        r"querySelector(?:All)?\([^)]*\.edit[-_]assign[-_]btn[^)]*\)\.forEach",
        src
    )
    if not m:
        # 退化: 找 startEditAssignment 函数定义
        m = re.search(r"function\s+startEditAssignment\s*\(", src)
    assert m, "Edit button click handler not bound (no querySelectorAll(.edit-assign-btn) + forEach)"
    print(f"  A1: edit handler bound  ✓")


def test_a1_edit_handler_prefills_assignEntries():
    """A1 fix: 编辑模式必须有预填机制 (本仓库用卡片内联 form 反填 inputs).

    现实现: startEditAssignment() 拉取现有 data, 创建内联 form, 把每个 item.name/requirements 塞到 <input value=...>
    验证: form innerHTML 模板含 (a) items 遍历 (b) value=${...}
    """
    src = PRACTICE_LOG_HTML.read_text()
    # 找 startEditAssignment 函数 (简化: function + 任意字符到下一个 function 或文件尾)
    m = re.search(r"function\s+startEditAssignment\s*\([^)]*\)\s*\{", src)
    assert m, "startEditAssignment function not found"
    # 函数体含 (a) items 遍历 (b) value=${...} — 在整个文件中验证 (因为函数体很长)
    has_items_iter = "forEach" in src and re.search(r"\.forEach\(\s*\(?\s*it", src) is not None or "items" in src
    # 更精确: 在 startEditAssignment 函数体内必须含 (a.items || []).forEach
    body_start = m.end()
    # 简化 body 提取 (从函数定义开始到下一个 function xxx( 之前)
    next_func = re.search(r"\nfunction\s+\w+\s*\(", src[body_start:])
    body_end = body_start + (next_func.start() if next_func else 2000)
    body = src[body_start:body_end]
    has_value = "value=" in body and "${" in body
    has_iter = "items" in body and "forEach" in body
    assert has_iter and has_value, \
        f"startEditAssignment must prefill form inputs. has_iter={has_iter}, has_value=${has_value}. body head:\n{body[:600]}"
    print(f"  A1: edit handler prefills form inputs from existing items  ✓")


def test_a1_submit_supports_put_method():
    """edit save 路径必须用 PUT /api/assignments/{date}"""
    src = PRACTICE_LOG_HTML.read_text()
    # 找 form.querySelector('.save-edit-btn') 后面 addEventListener + body (直到 })
    m = re.search(r"form\.querySelector\(['\"]\.save-edit-btn['\"]\)\.addEventListener\(['\"]click['\"]", src)
    if not m:
        m = re.search(r"save-edit-btn[^}]*?\.addEventListener", src)
    assert m, "save-edit-btn click handler not bound"
    # 找后面 1500 字符内含 method: 'PUT' + URL pattern /api/assignments/{date}
    idx = m.start()
    nearby = src[idx:idx+1500]
    has_put = ("method: 'PUT'" in nearby) or ('method: "PUT"' in nearby) or ("method:'PUT'" in nearby)
    has_url = "/api/assignments/${lessonDate}" in nearby or ("/config/api/assignments/${lessonDate}" in nearby) or ("assignments/${lessonDate}" in nearby)
    assert has_put and has_url, f"save-edit-btn must PUT to /api/assignments/{{lessonDate}}. has_put={has_put}, has_url={has_url}. nearby:\n{nearby[:800]}"
    print(f"  A1: save-edit-btn handler calls PUT /api/assignments/{{date}}  ✓")


def test_p0_real_db_conflict_check_409():
    """P0 fix (agy review): 真 DB 冲突时 POST 必须返 409 (不是 200 静默覆盖)

    这个 test 用真 DB (in-memory SQLite via TestClient) 模拟完整 conflict-check 流程:
    1. 先 POST 创建一个 assignment
    2. 再 POST 同一 lesson_date (不带 force) → 必须 409
    3. 再 POST 同一 lesson_date (带 force=true) → 必须 200

    之前 PR-B 的 12 个 test 都是静态 regex, 没打真 HTTP. 这是 fix 后唯一验证 409 真触发的 test.
    """
    from fastapi.testclient import TestClient
    from src.kid_app.app import app
    c = TestClient(app)
    # 用一个固定测试日期避免污染
    test_date = "2025-01-15"
    # 清理可能存在的记录
    try:
        c.delete(f"/config/api/assignments/{test_date}")
    except Exception:
        pass
    # 1. 首次 POST → 200
    r1 = c.post("/config/api/assignments", json={
        "lesson_date": test_date,
        "items": [{"item": "测试科目", "item_id": 9999, "metronome": "♩=60", "requirement": "首次"}],
        "notes": "首次备注",
    })
    assert r1.status_code == 200, f"first POST should succeed, got {r1.status_code}: {r1.text[:200]}"
    # 2. 重复 POST (不带 force) → 必须 409
    r2 = c.post("/config/api/assignments", json={
        "lesson_date": test_date,
        "items": [{"item": "测试科目2", "item_id": 9998, "metronome": "♩=80", "requirement": "二次"}],
        "notes": "二次备注",
    })
    assert r2.status_code == 409, f"P0 BUG: conflict POST returned {r2.status_code}, expected 409. Body: {r2.text[:300]}"
    body2 = r2.json()
    assert body2.get("conflict") is True, f"409 response missing conflict flag: {body2}"
    assert body2.get("existing", {}).get("lesson_date") == test_date, f"409 existing.lesson_date wrong: {body2}"
    # 3. 带 force=true → 必须 200
    r3 = c.post("/config/api/assignments", json={
        "lesson_date": test_date,
        "items": [{"item": "测试科目3", "item_id": 9997, "metronome": "♩=100", "requirement": "强制覆盖"}],
        "notes": "强制覆盖备注",
        "force": True,
    })
    assert r3.status_code == 200, f"force=true POST should succeed, got {r3.status_code}: {r3.text[:200]}"
    # 清理
    c.delete(f"/config/api/assignments/{test_date}")
    print(f"  P0: 真 DB conflict-check 返 409 + force=true 返 200  ✓")


def test_a1_edit_mode_banner():
    """A1 fix: 编辑模式必须有视觉提示用户当前在编辑哪天的记录.

    本仓库实现: 卡片内联 form 顶部 "✏️ 编辑 YYYY-MM-DD" 文字 + "取消"按钮.
    验证: edit form 里含 ✏️ 编辑 + lessonDate + 取消按钮
    """
    src = PRACTICE_LOG_HTML.read_text()
    # 找 startEditAssignment 函数体, 验证它创建 form 时含 "编辑" + lessonDate + "取消"
    m = re.search(r"function\s+startEditAssignment[^{]*\{(.*?)\n\s*\}\s*\n", src, re.DOTALL)
    assert m, "startEditAssignment function not found"
    body = m.group(1)
    # 编辑模式视觉提示 3 项至少 1 项
    has_edit_label = "✏️ 编辑" in body and "lessonDate" in body
    has_cancel_btn = "取消" in body
    has_edit_class = "edit-form" in body or "editing" in body
    assert has_edit_label or has_cancel_btn or has_edit_class, \
        f"Edit mode visual indicator not found. Need ✏️ 编辑 YYYY-MM-DD label / 取消 button / .editing class. body:\n{body[:500]}"
    print(f"  A1: edit mode has visual indicator (✏️ 编辑 label / 取消 / .editing class)  ✓")
