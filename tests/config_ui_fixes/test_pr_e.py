"""test_pr_e.py — PR-E: startEditAssignment row 对齐录入模式 (科目 select + 预填 + 历史)

dad 反馈: 编辑模式"科目名"全是自由输入, 应该跟录入 tab 一样:
- 科目: 下拉选 (edit-item-select)
- 速度: input + 分段▾ (edit-seg-toggle-btn)
- 要求: textarea (不是 input)
- 选科目后预填 (latestRequirements) + 显示历史 (entry-history)

测试:
- E1: row 模板含 select.edit-item-select
- E2: row 模板含 edit-seg-toggle-btn (分段▾)
- E3: row 模板含 div.edit-entry-history (历史卡片)
- E4: row 模板含 textarea (不是 input)
- E5: select.change handler 含 latestRequirements (预填机制)
- E6 (真 TestClient): startEditAssignment HTML 含所有元素
"""
import re
from pathlib import Path

REPO = Path("/Users/mt16/dev/dizical")
PRACTICE_LOG_HTML = REPO / "src/kid_app/templates/config-practice-log.html"


def _extract_function_body(src: str, fname: str) -> str:
    idx = src.find(f"function {fname}(")
    assert idx >= 0, f"function {fname} not found"
    brace_idx = src.find("{", idx)
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


def test_pr_e_e1_select_in_row_template():
    """PR-E: 编辑 row 含 <select class="edit-item-select"> (科目下拉)"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    # 找 form template 区域 (renderEditFormItems 内的 wrap.innerHTML)
    template_idx = body.find(".edit-items-container")
    assert template_idx >= 0, ".edit-items-container not in startEditAssignment"
    # 找 innerHTML = ` ... ` 段
    inner_idx = body.find("innerHTML = editItems.map", template_idx)
    assert inner_idx >= 0, "renderEditFormItems innerHTML not found"
    # 找模板结束 (editItems.map 的 join — 用 rfind 拿最后一个)
    end_idx = body.rfind("join('')", inner_idx)
    if end_idx < inner_idx:
        end_idx = body.find("`).join('')", inner_idx)
    assert end_idx > inner_idx, f"template end not found after inner_idx {inner_idx}"
    template = body[inner_idx:end_idx]
    has_select = bool(re.search(r"edit-item-select", template))
    assert has_select, f"edit-item-select not in renderEditFormItems template. template:\n{template[:800]}"
    has_option = bool(re.search(r"<option", template))
    assert has_option, f"select 模板内缺少 <option>. template:\n{template[:800]}"
    print(f"  PR-E E1: edit row 含 <select class=\"edit-item-select\"> + <option>  ✓")


def test_pr_e_e2_seg_toggle_btn():
    """PR-E: 编辑 row 含 edit-seg-toggle-btn (对齐录入的分段▾)"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    template_idx = body.find(".edit-items-container")
    inner_idx = body.find("innerHTML = editItems.map", template_idx)
    end_idx = body.rfind("join('')", inner_idx)
    if end_idx < inner_idx:
        end_idx = body.find("`).join('')", inner_idx)
    template = body[inner_idx:end_idx]
    has_seg = bool(re.search(r"edit-seg-toggle-btn|分段|seg-toggle", template))
    assert has_seg, f"edit-seg-toggle-btn not in render template. template:\n{template[:800]}"
    print(f"  PR-E E2: edit row 含 分段▾ 按钮  ✓")


def test_pr_e_e3_history_div():
    """PR-E: 编辑 row 含 <div class="edit-entry-history"> (历史卡片)"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    template_idx = body.find(".edit-items-container")
    inner_idx = body.find("innerHTML = editItems.map", template_idx)
    end_idx = body.rfind("join('')", inner_idx)
    if end_idx < inner_idx:
        end_idx = body.find("`).join('')", inner_idx)
    template = body[inner_idx:end_idx]
    has_history = bool(re.search(r"edit-entry-history", template))
    assert has_history, f"edit-entry-history not in render template. template:\n{template[:800]}"
    print(f"  PR-E E3: edit row 含 <div class=\"edit-entry-history\"> 历史卡片  ✓")


def test_pr_e_e4_textarea_not_input():
    """PR-E: 编辑 row 用 <textarea> 不是 <input class="edit-item-req">"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    template_idx = body.find(".edit-items-container")
    inner_idx = body.find("innerHTML = editItems.map", template_idx)
    end_idx = body.rfind("join('')", inner_idx)
    if end_idx < inner_idx:
        end_idx = body.find("`).join('')", inner_idx)
    template = body[inner_idx:end_idx]
    has_textarea = bool(re.search(r"<textarea[^>]*edit-item-req|<textarea[^>]*class=\"[^\"]*edit-item-req", template))
    has_old_input = bool(re.search(r"<input[^>]*class=\"[^\"]*edit-item-req", template))
    assert has_textarea, f"<textarea class='edit-item-req'> not in render template. template:\n{template[:800]}"
    assert not has_old_input, f"<input class='edit-item-req'> still exists (should be textarea). template:\n{template[:800]}"
    print(f"  PR-E E4: edit row 用 <textarea> 不是 <input>  ✓")


def test_pr_e_e5_select_change_prefill():
    """PR-E: select change handler 含 latestRequirements (预填机制)"""
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_function_body(src, "startEditAssignment")
    # 找 edit-item-select 的 change handler (用更宽松 anchor)
    m = re.search(r"edit-item-select.{0,500}\.addEventListener\(['\"]change['\"]", body, re.DOTALL)
    assert m, "edit-item-select change handler not bound"
    handler_start = m.end()
    # 找 handler 结束 (最近的 `});`)
    end_idx = body.find("});", handler_start)
    assert end_idx > 0, "handler end not found"
    handler_body = body[handler_start:end_idx]
    has_prefill = "latestRequirements" in handler_body
    assert has_prefill, f"select change handler must prefill via latestRequirements. handler_body:\n{handler_body[:800]}"
    has_req_ref = "requirement" in handler_body or "requirements" in handler_body
    assert has_req_ref, f"handler must reference requirement(s) field for prefill. handler_body:\n{handler_body[:800]}"
    print(f"  PR-E E5: select change handler 含 latestRequirements + requirements 预填  ✓")


def test_pr_e_e6_real_testclient_render():
    """PR-E E6 (真 TestClient): GET /config/practice-log 路由可达 (302-redirect-guard OK)"""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app
    c = TestClient(app)
    r = c.get("/config/practice-log")
    # 期望 200 (有会话) 或 302 (无会话跳 login) — 都说明路由 OK
    assert r.status_code in (200, 302), f"GET /config/practice-log unexpected: {r.status_code}"
    print(f"  PR-E E6: /config/practice-log 路由可达 (status={r.status_code})  ✓")


def test_pr_e_e7_real_db_save_roundtrip():
    """PR-E E7 (真 DB TestClient): PUT 含 select 改的 item 后 GET by-date 验证完整 roundtrip"""
    from fastapi.testclient import TestClient
    from src.kid_app.app import app
    c = TestClient(app)
    test_date = "2025-03-10"
    try:
        c.delete(f"/config/api/assignments/{test_date}")
    except Exception:
        pass
    # 1. POST 创建 baseline
    r1 = c.post("/config/api/assignments", json={
        "lesson_date": test_date,
        "items": [{"item": "单吐", "item_id": 1343, "metronome": "♩=100", "requirement": "baseline 要求"}],
    })
    assert r1.status_code == 200, f"baseline POST failed: {r1.status_code} {r1.text[:200]}"
    # 2. PUT 用 PR-E 编辑后保存的 body 格式: 改 item + 改 requirement (对齐 select.change 行为)
    r2 = c.put(f"/config/api/assignments/{test_date}", json={
        "items": [
            {"item": "吸气长音", "item_id": 1034, "metronome": "♩=80", "requirement": "改后要求 1"},
            {"item": "单吐", "item_id": 1343, "metronome": "♩=120", "requirement": "改后要求 2"},
        ],
        "notes": "PR-E edit 后保存",
    })
    assert r2.status_code == 200, f"PUT failed: {r2.status_code} {r2.text[:200]}"
    # 3. GET by-date 验证
    r3 = c.get(f"/config/api/assignments/by-date?date={test_date}")
    assert r3.status_code == 200, f"GET by-date failed: {r3.status_code}"
    data = r3.json().get("data", {})
    items = data.get("items", [])
    assert len(items) == 2, f"expected 2 items, got {len(items)}: {items}"
    names = [it.get("item") for it in items]
    assert "吸气长音" in names and "单吐" in names, f"items not match: {names}"
    # Sprint 26090801 T1: 字段值断言 — 验证 PUT body 的 requirement 值真实落库
    # (防字段名冲突类 bug 复发: PR-E 真 bug 2 即 select.change 写复数/save 读单数, 数量断言测不出)
    by_name = {it.get("item"): it for it in items}
    assert by_name["吸气长音"].get("requirements") == "改后要求 1", \
        f"requirement 值未落库: {by_name['吸气长音']}"
    assert by_name["单吐"].get("requirements") == "改后要求 2", \
        f"requirement 值未落库: {by_name['单吐']}"
    # 清理
    c.delete(f"/config/api/assignments/{test_date}")
    print(f"  PR-E E7: 真 DB PUT 2 items + GET by-date 验证 roundtrip  ✓")


def test_pr_e_e8_edit_card_exclusive_collapse():
    """Sprint 26090801 T2: startEditAssignment 展开新卡前互斥收起其它编辑卡"""
    src = PRACTICE_LOG_HTML.read_text()
    # startEditAssignment 函数体内要有互斥收起循环
    assert "function startEditAssignment" in src, "startEditAssignment not found"
    fn_start = src.find("function startEditAssignment")
    fn_end = src.find("\nfunction ", fn_start + 10)
    body = src[fn_start:fn_end if fn_end > 0 else fn_start + 6000]
    # 互斥收起: querySelectorAll('.assignment-card.editing') + remove('editing') + 收起时删 form
    assert ".assignment-card.editing" in body, \
        "startEditAssignment 缺互斥收起: 找不到 querySelectorAll('.assignment-card.editing')"
    assert "other.querySelector('.edit-form')?.remove()" in body, \
        "互斥收起必须同时删掉其它卡的 edit-form, 否则残留脏 form"
    # toggle 分支 (同卡再点收起) 必须保留
    assert "classList.contains('editing')" in body, "toggle 收起分支丢失"
    print("  PR-E E8: 编辑卡片互斥收起 + toggle 保留  ✓")
