"""练习助手（practice-dsh）计时入库契约（dad 261102）。

要点：
· 票夹 / 仪表盘上拖出来的「练习时长」只是倒计时长度，**不入库**；入库只写实际练了多少秒。
· 写入走 POST /api/log，payload 与旧 practice 页一致；tempo_note + tempo_bpm + content
  三件齐 → 后端 has_session_detail() 为真 → 走 practice_sessions 表。
· 保存成功后回灌 D（今日时长）/ R（今日记录）两张卡的真实数据。
"""
import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.kid_app.app import app

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "src" / "kid_app" / "templates" / "practice-dsh.html"


@pytest.fixture
def client(monkeypatch):
    async def _mock_user(*args, **kwargs):
        return {"id": 1, "username": "yoyo", "role": "student"}
    monkeypatch.setattr("src.kid_app.auth.get_current_user", _mock_user)
    return TestClient(app)


@pytest.fixture
def html():
    return TPL.read_text(encoding="utf-8")


# ── 前端契约（静态） ────────────────────────────────────────────────────────

def test_post_body_has_real_log_fields(html):
    assert "fetch('/api/log'" in html, "必须 POST /api/log"
    for field in ("practice_at:", "behavior_log:", "tempo_note:", "tempo_bpm:", "content:", "seconds:"):
        assert field in html, f"payload 缺字段 {field}"


def test_selected_duration_is_not_persisted(html):
    """时长只是倒计时长度：body 里不能出现票夹选出来的 duration。"""
    body = html[html.index("async function postPracticeLog"):html.index("function enterRun()")]
    assert "duration" not in body, "入库 payload 不该带选定的练习时长"
    assert "Math.ceil(seconds / 60)" in body, "分钟必须由实际秒数换算"


def test_elapsed_captured_before_reset(html):
    """exitRun 里必须先抓实际秒数，再把 elapsed 清零。"""
    seg = html[html.index("function exitRun()"):html.index("function pauseToggle()")]
    grab = seg.index("Math.round(elapsed)")
    reset = seg.index("elapsed = 0;")
    assert grab < reset, "elapsed 必须在清零前抓取"
    assert "postPracticeLog(finalSeconds)" in seg, "退出时必须写入实际秒数"


def test_bpm_clamped_and_content_required(html):
    body = html[html.index("async function postPracticeLog"):html.index("function enterRun()")]
    assert "Math.min(200, Math.max(40" in body, "BPM 必须夹在 40–200"
    assert "if (!detail)" in body, "没有练习内容不入库"


def test_no_dead_route_and_day_refresh(html):
    assert "fetch(`/api/assignments?" not in html
    assert "window.__czReloadDay = reloadDay;" in html
    assert "fetch('/api/practices/' + d)" in html
    assert "Promise.all([get(today), get(yesterday)])" in html
    assert "fetch('/api/today-stats" not in html, "today-stats 的服务端日期可能是 UTC，会串日期"
    assert html.count("window.__czApplyDay = function (payload)") == 3, "画布顶栏 + D / R 三处都要能接真实数据"


# ── 端到端：按前端实际 payload 打一次 API ─────────────────────────────────

def _frontend_payload(item_id, item_name, seconds, practice_at, content="连吐 1-16 小节"):
    minutes = max(1, -(-seconds // 60))  # ceil
    return {
        "date": practice_at[:10],
        "item": item_name,
        "item_id": item_id,
        "minutes": minutes,
        "seconds": seconds,
        "log": "",
        "practice_at": practice_at,
        "behavior_log": [{
            "enter_time": practice_at,
            "item": item_name,
            "minutes": minutes,
            "seconds": seconds,
        }],
        "tempo_note": "♩",
        "tempo_bpm": 60,
        "content": content,
    }


def _first_item(client):
    """本地临时测试库可能是空的 —— 造一个科目。"""
    items = client.get("/api/items?include_archived=false").json().get("items", [])
    if items:
        return items[0]
    from src.database import db
    item_id = db.add_practice_item("测试长音", category_id=1)
    return {"item_id": item_id, "name": "测试长音"}


def test_log_writes_session_with_actual_seconds(client):
    item = _first_item(client)
    practice_at = "2026-11-02 09:00:00.000"

    resp = client.post("/api/log", json=_frontend_payload(item["item_id"], item["name"], 65, practice_at))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("ok") is True, data

    day = dt.date(2026, 11, 2)
    sessions = client.get(f"/api/practices/{day.isoformat()}").json()["sessions"]
    mine = [s for s in sessions if str(s.get("started_at", "")).startswith("2026-11-02 09:00")]
    assert mine, f"没有写入 session: {sessions}"
    assert mine[0]["duration_seconds"] == 65, f"秒数应写真实值 65: {mine[0]}"
    assert mine[0]["tempo_bpm"] == 60
    assert mine[0]["content"] == "连吐 1-16 小节"


def test_second_write_keeps_first_practice_at(client):
    """第二次打卡不改当天首次练习时间（practice_at 只在 INSERT 时写）。"""
    item = _first_item(client)
    first_at = "2026-11-02 10:00:00.000"
    second_at = "2026-11-02 11:30:00.000"
    client.post("/api/log", json=_frontend_payload(item["item_id"], item["name"], 30, first_at))
    client.post("/api/log", json=_frontend_payload(item["item_id"], item["name"], 45, second_at, content="换气练习"))

    day = client.get("/api/practices/2026-11-02").json()
    sessions = [s for s in day["sessions"] if str(s.get("started_at", "")).startswith("2026-11-02")]
    assert len(sessions) >= 2, sessions
    assert day["total_seconds"] >= 75, day["total_seconds"]


# ── 审计 P1：A 卡自己计时那条路径 ─────────────────────────────────────────

def test_dashboard_start_always_enters_ticket_timer(html):
    """点仪表盘「开始」必须让票夹计时器也起来 —— 只看 stage-running 会漏掉
    「票夹已是窄条但计时器没起」的那条路径，那段练习会不入库。"""
    seg = html[html.index("function bridgeCardA()"):html.index("function bridgeCanvas()")]
    assert "else if (!canvasRunning())" not in seg, "run 分支不能只看 stage-running"
    assert "setCanvasStage('run')" in seg, "run 分支必须调 setCanvasStage('run')"


def test_external_run_fallback_is_wired(html):
    """票夹没计时、只有 A 卡在跑时，用 A 卡的秒数兜底记账。"""
    assert "window.__czSaveExternalRun = function (seconds, startedAtCst)" in html
    assert "window.__czRunInfo = function ()" in html
    assert "function saveExternalRunIfNeeded()" in html
    assert "saveExternalRunIfNeeded();" in html, "停止时必须调用兜底记账"
    assert "lastElapsed: lastRunSeconds" in html, "A 卡要在进准备态前定格秒数"


def test_duration_card_timeline_has_readable_span(html):
    """D 卡时间轴至少铺 30 分钟，否则一段短练习的刻度全挤在一起。"""
    assert "Math.max(1800, (last - first) / 1000)" in html


def test_today_and_yesterday_fetch_are_independent(html):
    """昨天接口挂了不能连今天的真实数据一起丢掉。"""
    assert "Promise.all([get(today), get(yesterday)])" in html


def test_pause_is_synced_to_ticket_timer(html):
    """仪表盘暂停 → 票夹计时器也要停，否则暂停的墙钟时间会被算进入库秒数。"""
    assert "window.__czPause = function ()" in html
    assert "window.__czResume = function ()" in html
    seg = html[html.index("function bridgeCardA()"):html.index("function bridgeCanvas()")]
    assert "mode === 'pause'" in seg, "bridge 必须处理 pause 状态"
    assert "__czPause()" in seg and "__czResume()" in seg


def test_card_a_natural_end_triggers_fallback_save(html):
    """A 卡自己走到点（没有 click）也要触发兜底记账。"""
    assert "function notifyRunEnd()" in html
    assert "window.__czOnCardARunEnd = function (info)" in html
    assert "window.__czSaveExternalRunIfNeeded = saveExternalRunIfNeeded;" in html


def test_yesterday_unavailable_is_not_treated_as_zero(html):
    """昨天接口失败不能当成「昨天没练」去做对比。"""
    assert "yesterday_known" in html
    assert "yesterday: res[1] || null" in html
    assert "昨日数据不可用" in html
    assert "var yest = (payload && payload.yesterday) ? payload.yesterday : null;" in html, \
        "R 卡不能把 null 昨天折成空对象（那等于把失败当成昨天 0 秒）"
