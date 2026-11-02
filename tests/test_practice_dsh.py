"""Tests for /practice-dsh page and 3rd Tab in /practice (sprint practice-dsh-page)."""
import json
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.kid_app.app import app

ROOT = Path(__file__).resolve().parents[1]
PRACTICE_TPL = ROOT / "src" / "kid_app" / "templates" / "practice.html"
PRACTICE_DSH_TPL = ROOT / "src" / "kid_app" / "templates" / "practice-dsh.html"


@pytest.fixture
def client(monkeypatch):
    async def _mock_user(*args, **kwargs):
        return {"id": 1, "username": "yoyo", "role": "student"}
    monkeypatch.setattr("src.kid_app.auth.get_current_user", _mock_user)
    return TestClient(app)


def test_practice_page_has_three_tabs(client):
    """验证 /practice 页面顶部 Tab 栏包含三个 Tab：计时练习、快速补录、练习助手."""
    resp = client.get("/practice")
    assert resp.status_code == 200
    html = resp.text

    # Tab 头部按钮
    assert "计时练习" in html
    assert "快速补录" in html
    assert "练习助手" in html
    assert 'class="tab-btn practice-dsh-tab"' in html or "practice-dsh-tab" in html
    assert "switchTab('dsh')" in html or 'switchTab("dsh")' in html


def test_practice_page_embeds_practice_dsh_iframe(client):
    """验证 /practice 包含 #tabDsh 面板并以 iframe 嵌入 /practice-dsh."""
    resp = client.get("/practice")
    assert resp.status_code == 200
    html = resp.text

    assert 'id="tabDsh"' in html
    assert 'src="/practice-dsh?v=' in html
    assert 'allow="autoplay; microphone"' in html


def test_practice_dsh_route_accessible(client):
    """验证 GET /practice-dsh 返回 200 OK 且为 HTMLResponse."""
    resp = client.get("/practice-dsh")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    html = resp.text

    # 包含关键区域
    assert "练习助手" in html
    assert "练习票夹" in html
    assert "练习仪表盘" in html


def test_practice_dsh_structure_and_contracts():
    """静态检查 practice-dsh.html 契约元素与 demo 像素级复刻规范."""
    assert PRACTICE_DSH_TPL.exists(), "practice-dsh.html 模板文件必须存在"
    html = PRACTICE_DSH_TPL.read_text(encoding="utf-8")

    # 规范关键组件 ID（Brief 必须）：
    # 票夹卡片、票夹窄条（竖）、票夹窄条（横）、仪表盘黑区、空心数字、刻度尺、旋钮、圆弧、就绪引导
    required_ids = [
        "pkTicketCard",
        "ticketBarVert",
        "ticketBarHoriz",
        "dash",
        "metaDigits",
        "readoutDigits",
        "ruler",
        "knob",
        "arc",
        "czGuide",
        "czGuideSpot",
        "btnPrimary",
        "btnEarly",
        "pkPunchSlotWrap",
        "czTicketStage",
        "pkFolioModal",
    ]
    for eid in required_ids:
        assert f'id="{eid}"' in html, f"practice-dsh.html 缺少关键元素 #{eid}"

    # 引导逻辑源码与 GSAP 引入
    assert "__CZ_GUIDE_SRC" in html, "必须包含 __CZ_GUIDE_SRC 就绪引导逻辑"
    assert "gsap.min.js" in html, "必须引入 GSAP 动画引擎"
    assert "HollowDigits" in html, "必须包含 HollowDigits 空心数字引擎"
    assert "window.DizicalPracticeBus" in html, "必须暴露 DizicalPracticeBus"
    assert "fitWideCombo" in html, "宽屏组合必须走右栏装入"

    # 计时读数守卫：正则格式校验
    assert r"^\d{1,2}:\d{2}$" in html or r"^\d{2}:\d{2}$" in html, "必须包含 MM:SS 读数守卫正则"

    # 科目列表走真实接口。打卡 payload 仍在页面外的 practice 壳，不在这份画布模板里。
    assert "fetch('/api/items')" in html, "必须接入 GET /api/items"


def test_post_api_log_with_session_fields(client):
    """测试 POST /api/log 支持练习助手带有的 tempo_note + tempo_bpm + content 字段."""
    items_resp = client.get("/api/items?include_archived=false")
    assert items_resp.status_code == 200
    items = items_resp.json().get("items", [])
    if items:
        item = items[0]
        item_id = item["item_id"]
        item_name = item["name"]
    else:
        from src.database import db
        item_id = db.add_practice_item("测试长音", category_id=1)
        item_name = "测试长音"

    payload = {
        "date": "2026-10-28",
        "item": item_name,
        "item_id": item_id,
        "minutes": 10,
        "seconds": 600,
        "tempo_note": "♪",
        "tempo_bpm": 60,
        "content": "练习助手自动化测试连吐",
        "practice_at": "2026-10-28 13:15:00"
    }
    resp = client.post("/api/log", json=payload)
    assert resp.status_code == 200, f"Error: {resp.text}"
    data = resp.json()
    assert data.get("ok") is True, f"API 打卡保存失败: {data}"

def test_stage_duration_reads_mysql_json_string(client, monkeypatch):
    """MySQL 把 items 当字符串返回，键是 item 不是 name。时长不能停在 0。"""
    import datetime as dt
    from src.kid_app.routes import config as config_routes

    lesson = dt.date(2026, 10, 20)

    def fake_assignments(weeks=8, item=None):
        return [{
            "lesson_date": lesson,
            "items": [{"item": "春耕曲", "item_id": 1350, "requirements": "慢练"}],
            "notes": "",
            "images": [],
            "videos": [],
            "stage_order": 1,
            "stage_start": dt.date(2026, 10, 1),
            "stage_end": dt.date(2026, 10, 31),
        }]

    def fake_range(start, end):
        return [{
            "items": '[{"item": "春耕曲", "minutes": 2, "seconds": 90}]',
        }]

    monkeypatch.setattr(config_routes.practice_module, "query_assignments", fake_assignments)
    monkeypatch.setattr(config_routes.db, "get_daily_practices_in_range", fake_range)
    monkeypatch.setattr(
        config_routes.db,
        "get_practice_items",
        lambda: [{"item_id": 1350, "name": "春耕曲"}],
    )

    resp = client.get("/config/api/assignments?weeks=24&item=1350")
    assert resp.status_code == 200, resp.text
    rows = resp.json()["assignments"]
    assert len(rows) == 1
    assert rows[0]["total_seconds_per_stage"] == 90
    assert rows[0]["stage_duration_text"] == "1分30秒"
    assert rows[0]["items"][0]["item"] == "春耕曲"


def test_practice_dsh_category_fallback_and_no_dead_assignments_route():
    html = PRACTICE_DSH_TPL.read_text()
    assert "ITEM_CATEGORIES[a.category_id]" in html
    assert "fetch(`/api/assignments?" not in html
    assert 'fetch(`/config/api/assignments?weeks=24&item=' in html


def test_finish_confirm_modal_contract():
    """结束确认弹窗是唯一入库入口（P0：提前结束/到点/A 卡都要先确认）。"""
    html = PRACTICE_DSH_TPL.read_text(encoding="utf-8")

    for eid in [
        "pkFinishConfirmModal",
        "pkFinishScreenMain",
        "pkFinishScreenZero",
        "pkFinishDurationVal",
        "pkFinishSubmitBtn",
        "pkFinishResumeBtn",
        "pkFinishAbortBtn",
        "pkFinishZeroBackBtn",
        "pkFinishZeroConfirmBtn",
        "pkRepsReadout",
        "pkRepsMinus",
        "pkRepsPlus",
        "pkFinishErrorBanner",
    ]:
        assert f'id="{eid}"' in html, f"缺少结束确认弹窗元素 #{eid}"

    # 状态机与守卫
    for token in [
        "finishPending",
        "finishSubmitting",
        "finishSavedElapsed",
        "function requestFinish(done)",
        "function finalizeExitRun(opts)",
        "function cancelFinishAndResume()",
        "function abortFinishAndDiscard()",
        "function confirmFinish()",
        "async function submitConfirmedPractice(reps)",
        "window.__czIsPracticeBusy",
    ]:
        assert token in html, f"缺少结束确认状态机片段: {token}"

    # 失败保活：8 秒超时 + sessionStorage 暂存 + 重试
    assert "AbortController" in html and "8000" in html
    assert "dsh_pending" in html and "_log_v1" in html
    assert "重试提交" in html

    # 离开保护
    assert "beforeunload" in html


def test_practice_tab_switch_guards_dsh_busy():
    """dsh 在计时/待确认时，切页签要先过保护弹窗。"""
    html = PRACTICE_TPL.read_text(encoding="utf-8")
    assert "function dshBusy()" in html
    assert "cw.__cz.isBusy()" in html
    assert "pendingTab" in html
    assert "timerProtectText" in html


def test_finish_modal_is_anchored_to_visible_band():
    """画布 iframe 高度 = 内容自然高，fixed 弹层必须锚到 --cz-band-*，否则居中到视口外。"""
    html = PRACTICE_DSH_TPL.read_text(encoding="utf-8")
    assert ".pk-folio-modal, .pk-overlay, .popout-backdrop, .cz-pop-mask, .pk-finish-modal {" in html
    assert ".pk-finish-box { max-height: calc(var(--cz-band-h, 100vh) - 24px) !important; }" in html


def test_bridge_does_not_resume_card_a_during_finish_confirm():
    """确认弹窗期间 A 卡必须停在 pause，反向桥不能把它拉回 run。"""
    html = PRACTICE_DSH_TPL.read_text(encoding="utf-8")
    assert "window.__czIsFinishing = function ()" in html
    seg = html[html.index("function bridgeCanvas()"):html.index("bridgeCardA();", html.index("function bridgeCanvas()"))]
    assert "__czIsFinishing()" in seg
    assert "return;" in seg


def test_failure_returns_to_visible_screen_and_replays_pending():
    """失败时切回第一屏（错误条 / 重试按钮在那），并且启动时能补交暂存 payload。"""
    html = PRACTICE_DSH_TPL.read_text(encoding="utf-8")
    seg = html[html.index("async function submitConfirmedPractice"):html.index("function finalizeExitRun")]
    assert "showFinishScreen('main');" in seg
    assert "function replayPendingLog()" in html
    assert "sessionStorage.getItem(PENDING_LOG_KEY)" in html
    assert "12 * 3600 * 1000" in html


def test_audit_reset_is_silent_and_tab_leave_stops_dsh():
    html = PRACTICE_DSH_TPL.read_text(encoding="utf-8")
    assert "window.__czAuditSilentFinish" in html
    page = PRACTICE_TPL.read_text(encoding="utf-8")
    assert "cw.__cz.abandon()" in page
    assert "abandon: function ()" in html
