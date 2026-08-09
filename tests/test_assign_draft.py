"""回归测试: 老师要求草稿缓存 (S4, 2026-08-09).

需求1: config 表单录入内容先缓存成草稿, 下次打开优先看到; 刷新前二次确认.

模板层面断言 (不跑真实浏览器):
1. 草稿函数存在: collectAssignDraft / saveAssignDraft / restoreAssignDraft / clearAssignDraft
2. localStorage key 常量 + 防抖 scheduleAssignDraftSave
3. beforeunload 拦截存在 (e.returnValue = '')
4. 提交成功回调里调用 clearAssignDraft
5. init 时调用 restoreAssignDraft
6. 事件委托监听 input/change 存草稿
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(scope="module")
def html():
    from fastapi.testclient import TestClient
    from src.kid_app.app import app

    with TestClient(app) as c:
        return c.get("/config/practice-log").text


def test_draft_functions_exist(html):
    for fn in ("collectAssignDraft", "saveAssignDraft", "restoreAssignDraft",
               "clearAssignDraft", "scheduleAssignDraftSave", "hasAssignDraftContent"):
        assert f"function {fn}" in html, f"缺 {fn}"


def test_draft_key_and_debounce(html):
    assert "dizical:assign-draft:v1" in html
    assert "setTimeout(saveAssignDraft, 500)" in html  # 防抖 500ms


def test_beforeunload_intercept(html):
    assert "beforeunload" in html
    assert "e.returnValue = ''" in html


def test_clear_on_submit_success(html):
    assert "clearAssignDraft(); // 需求1: 提交成功后清草稿" in html


def test_restore_on_init(html):
    assert "restoreAssignDraft();" in html


def test_event_delegation(html):
    assert "addEventListener('input'" in html
    assert "addEventListener('change'" in html
    assert "closest('#tab-assign')" in html


def test_add_remove_row_saves_draft(html):
    assert "scheduleAssignDraftSave(); // 需求1: 添加行也存草稿" in html
    assert "scheduleAssignDraftSave(); // 需求1: 删除行也存草稿" in html
    assert "scheduleAssignDraftSave(); // 需求1: 上传配图也存草稿" in html
