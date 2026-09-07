"""test_pr_c.py — PR-C: startEditAssignment 加 "+ 添加科目" 按钮

PR-C 范围:
- config-practice-log.html: startEditAssignment 重构 editItems 数组 + 加 + 添加按钮 + 删除单行按钮
- save-edit-btn handler 改读 editItems 数组 (而非 querySelectorAll)

Test 范围 (静态 regex + 真 TestClient):
- T1: startEditAssignment 函数体内有 editItems 数组声明
- T2: startEditAssignment 函数体内有 add-edit-item-btn + click handler
- T3: startEditAssignment 函数体内有删除单行按钮 + click handler
- T4: save-edit-btn handler 读 editItems 数组 (而非 .edit-item-row DOM query)
- T5: edit-form 内含 add-edit-item-btn (HTML rendered)
- T6: PUT 请求 body 包含新增的 item (真 TestClient 模拟)
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path("/Users/mt16/dev/dizical")
PRACTICE_LOG_HTML = REPO / "src/kid_app/templates/config-practice-log.html"


def _extract_function_body(src: str, fname: str) -> str:
    """抓 function fname(...) { ... } body (跨嵌套 {} 找匹配)"""
    idx = src.find(f"function {fname}(")
    assert idx >= 0, f"function {fname} not found"
    # 找第一个 {
    brace_idx = src.find("{", idx)
    assert brace_idx >= 0, f"{{ not found after {fname}"
    start = brace_idx + 1
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    return src[start:i-1]


def test_prc_t1_editItems_array():
    """startEditAssignment 必须声明 editItems 数组 (而非直接闭包生成 itemsRows)"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    has_array_decl = bool(re.search(r"\b(editItems|editItems\s*=|let\s+editItems|const\s+editItems|var\s+editItems)\b", body))
    assert has_array_decl, f"startEditAssignment must declare editItems array. body (first 600):\n{body[:600]}"
    print(f"  PR-C T1: startEditAssignment has editItems array  ✓")


def test_prc_t2_add_edit_item_btn_handler():
    """必须绑 + 添加科目 按钮 click handler (push 空 item + 重渲 form)"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    # 1. 按钮 class 存在
    has_btn = bool(re.search(r"add[-_]edit[-_]item[-_]btn|addEditItemBtn|add-edit-item", body))
    assert has_btn, f"+ 添加科目 button class not found in startEditAssignment. body (first 600):\n{body[:600]}"
    # 2. handler 绑了 click
    btn_pattern = re.search(r"add[-_]edit[-_]item[-_]btn.*?addEventListener\(['\"]click['\"]", body, re.DOTALL)
    assert btn_pattern, f"+ 添加科目 button click handler not bound. body (last 400):\n{body[-400:]}"
    print(f"  PR-C T2: + 添加科目 button + click handler  ✓")


def test_prc_t3_remove_single_row_btn():
    """必须支持删除单行 (data-idx 标识 + click handler)"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    # 找 delete/remove 单行的代码 (不依赖 class 名字, 找 .splice 配对)
    has_splice = "splice" in body
    has_data_idx = re.search(r"data-?idx|row-?index|row-?i|row-?id|row-?pos", body) is not None
    assert has_splice and has_data_idx, f"single-row delete needs splice() + idx identifier. has_splice={has_splice}, has_data_idx={has_data_idx}. body (last 600):\n{body[-600:]}"
    print(f"  PR-C T3: single-row delete supported (splice + idx)  ✓")


def test_prc_t4_save_uses_editItems_array():
    """save-edit-btn handler 读 editItems 数组 (而非 querySelectorAll .edit-item-row)"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    # 找 save-edit-btn (在 form.innerHTML 字符串里) - 不是真的 handler 位置
    # 找 form.querySelector('.save-edit-btn') 后面紧邻的 addEventListener
    save_query_idx = body.find("form.querySelector('.save-edit-btn')")
    assert save_query_idx >= 0, "save-edit-btn querySelector not found"
    listener_idx = body.find("addEventListener('click'", save_query_idx)
    assert listener_idx >= 0, "save-edit-btn click handler not found"
    # 找 handler 函数结束: 下一个 "loadAssignments()" 调用 (save handler 成功后调)
    load_idx = body.find("loadAssignments()", listener_idx)
    assert load_idx > 0, "save handler end (loadAssignments) not found"
    # save handler body: 从 addEventListener 到 loadAssignments 之前
    handler_start = listener_idx + len("addEventListener('click'")
    save_body = body[handler_start:load_idx]
    has_edit_items_read = bool(re.search(r"\beditItems\b", save_body))
    has_query_selector_all = bool(re.search(r"querySelectorAll\(['\"]\.edit-item-row", save_body))
    assert has_edit_items_read, f"save handler must read editItems array. save_body:\n{save_body[:600]}"
    assert not has_query_selector_all, f"save handler should NOT querySelectorAll('.edit-item-row') (改读 editItems 数组). save_body:\n{save_body[:600]}"
    print(f"  PR-C T4: save handler reads editItems array (no DOM querySelectorAll)  ✓")


def test_prc_t5_html_renders_add_button():
    """edit-form 内 HTML 模板必须含 + 添加科目 按钮"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    # 找 form.innerHTML = ` ... ` 字符串
    innerHTML_idx = body.find("form.innerHTML = `")
    assert innerHTML_idx >= 0, "form.innerHTML template not found"
    # 找反引号结束
    template_end = body.find("`", innerHTML_idx + len("form.innerHTML = `"))
    assert template_end > 0, "form.innerHTML template end not found"
    template = body[innerHTML_idx:template_end + 1]
    has_add_btn = bool(re.search(r"add[-_]edit[-_]item[-_]btn|addEditItemBtn", template))
    assert has_add_btn, f"+ 添加科目 button not in form template. template:\n{template[:800]}"
    print(f"  PR-C T5: form HTML template contains + 添加科目 button  ✓")


def test_prc_t6_real_put_with_new_item():
    """PR-C 完成后真 DB TestClient: PUT 含新增 item 的 body 应被后端接受 (200)"""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app
    c = TestClient(app)
    test_date = "2025-02-20"
    try:
        c.delete(f"/config/api/assignments/{test_date}")
    except Exception:
        pass
    # 1. 先 POST 创建一条 (模拟既有记录)
    r1 = c.post("/config/api/assignments", json={
        "lesson_date": test_date,
        "items": [{"item": "原科目", "item_id": 8888, "metronome": "♩=60", "requirement": "原要求"}],
        "notes": "原备注",
    }, headers={"X-Force": "1"})
    # 用 force 或 ensure 不冲突 (这个日期 2025-02-20 应该没数据)
    assert r1.status_code == 200, f"first POST failed: {r1.status_code} {r1.text[:200]}"
    # 2. PUT 一条含 2 个 item (模拟"点 + 添加" 后用户填了第 2 个科目)
    r2 = c.put(f"/config/api/assignments/{test_date}", json={
        "lesson_date": test_date,
        "items": [
            {"item": "原科目", "item_id": 8888, "metronome": "♩=60", "requirement": "原要求改"},
            {"item": "新加科目", "item_id": 8889, "metronome": "♩=80", "requirement": "新加要求"},
        ],
        "notes": "改后备注",
    })
    assert r2.status_code == 200, f"PUT with new item failed: {r2.status_code} {r2.text[:200]}"
    # 3. GET by-date 验证
    r3 = c.get(f"/config/api/assignments/by-date?date={test_date}")
    assert r3.status_code == 200
    data = r3.json().get("data", {})
    assert data.get("items_count") == 2, f"expected 2 items, got {data.get('items_count')}: {data}"
    items = data.get("items") or []
    item_names = [it.get("item") for it in items]
    assert "新加科目" in item_names, f"新加科目 not in items: {item_names}"
    # 清理
    c.delete(f"/config/api/assignments/{test_date}")
    print(f"  PR-C T6: PUT 含新增 item → 后端接受, GET by-date 验证 items_count=2 + 新科目存在  ✓")


if __name__ == "__main__":
    # 当作脚本跑
    for f in [test_prc_t1_editItems_array, test_prc_t2_add_edit_item_btn_handler,
              test_prc_t3_remove_single_row_btn, test_prc_t4_save_uses_editItems_array,
              test_prc_t5_html_renders_add_button]:
        try:
            f()
        except AssertionError as e:
            print(f"  FAIL: {f.__name__}: {e}")
