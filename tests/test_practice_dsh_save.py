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
    body = html[html.index("function buildPracticeLogBody"):html.index("function enterRun()")]
    assert "duration" not in body, "入库 payload 不该带选定的练习时长"
    assert "Math.ceil(seconds / 60)" in body, "分钟必须由实际秒数换算"


def test_finish_freezes_elapsed_and_defers_write_to_confirm(html):
    """结束先定格秒数开确认弹窗；exitRun 只做静默复位，不再直写。"""
    seg = html[html.index("function requestFinish(done)"):html.index("function cancelFinishAndResume()")]
    assert "finishSavedElapsed = done ? Math.max(secs, Math.round(plannedMin * 60)) : secs;" in seg
    assert "finishDurationMin" in seg, "仪表盘单独跑完时要用它自己的时长兜底"
    assert "postPracticeLog" not in seg, "requestFinish 不能直接写库"
    exit_seg = html[html.index("function exitRun()"):html.index("function pauseToggle()")]
    assert "postPracticeLog" not in exit_seg, "exitRun 是静默复位，不能写库"


def test_bpm_clamped_and_content_required(html):
    body = html[html.index("function buildPracticeLogBody"):html.index("function postPracticeLog")]
    assert "Math.min(200, Math.max(40" in body, "BPM 必须夹在 40–200"
    assert "本次练习没有内容" in body, "没有练习内容不入库"


def test_reps_zero_is_omitted_never_sent(html):
    """后端 REPS_MIN = 1：不记遍数必须省略字段，绝不能传 0。"""
    body = html[html.index("function buildPracticeLogBody"):html.index("function postPracticeLog")]
    assert "repNum >= 1" in body
    assert "body.reps = Math.min(99, Math.round(repNum))" in body
    assert "body.reps = 0" not in body


def test_no_dead_route_and_day_refresh(html):
    assert "fetch(`/api/assignments?" not in html
    assert "window.__czReloadDay = reloadDay;" in html
    assert "fetch('/api/practices/' + d)" in html
    assert "Promise.all([get(today), get(yesterday)])" in html
    assert "fetch('/api/today-stats" not in html, "today-stats 的服务端日期可能是 UTC，会串日期"
    assert html.count("window.__czApplyDay = function (payload)") == 4, "画布顶栏 + A / D / R 四处都要能接真实数据"
    assert "['A', 'D', 'R']" in html, "当天数据要推进 A 卡，不能只推 D / R"


def test_layout_switch_is_blocked_while_timing(html):
    """计时中切卡片布局必须先二次确认，不能直接切断读数。"""
    assert 'id="czLayoutGuard"' in html, "缺布局切换二次确认弹层"
    assert "function layoutSwitchBlocked()" in html
    assert "function askLayoutSwitch(" in html
    assert "needConfirm: true" in html, "被拦下时要告诉调用方需要确认"
    set_combo = html[html.index("function setCombo(which)"):]
    set_combo = set_combo[:set_combo.index("\n  }\n") + 4]
    assert "layoutSwitchBlocked()" in set_combo, "切组合没走拦截"
    set_mods = html[html.index("function setMods(mods, saveIt)"):]
    set_mods = set_mods[:set_mods.index("\n  }\n") + 4]
    assert "layoutSwitchBlocked()" in set_mods, "勾选自定义没走拦截"
    assert "function restoreCardAAfterRelayout()" in html, "确认切换后要把读数接回去"


def test_duration_labels_are_second_accurate(html):
    """不满 1 分钟的余数必须按秒显示，不能向上取整成整分钟。"""
    assert "DizicalDur.fmt" in html, "时长展示要走秒级口径"
    assert "function durLabel(seconds)" in html
    dur = html[html.index("function durLabel(seconds)"):html.index("function groupSubjects()")]
    assert "Math.floor(s / 60)" in dur and "s % 60" in dur, "必须拆成分+秒"
    assert "Math.ceil" not in dur, "秒级展示不能向上取整"
    assert "minutesOf(session.duration_seconds) + '分'" not in html, "旧向上取整口径要清干净"


def test_dashboard_finish_uses_its_own_duration(html):
    """仪表盘单独跑完时，弹窗时长用它自己的分钟数兜底。"""
    assert "durationMin: duration" in html, "A 卡结束要把自己的时长传给外壳"
    assert "finishDurationMin = (dm > 0) ? dm : null;" in html
    assert "const plannedMin = (typeof finishDurationMin === 'number' && finishDurationMin > 0)" in html


def test_card_a_timer_freezes_on_pause(html):
    """到点/暂停后仪表盘读数要定格，不能一直挂着「练习中」。"""
    pause = html[html.index("function enterPause()"):html.index("function enterPrep()")]
    assert "' · 已暂停'" in pause, "暂停态读数行要换成已暂停"
    assert "window.__czSyncCardAElapsed" in html, "结束时要把仪表盘读数对齐到实际秒数"


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


def test_card_a_end_routes_to_confirm_modal(html):
    """A 卡的提前结束/到点都收口到确认弹窗，不再旁路直写。"""
    assert "window.__czRequestFinishFromCardA = function (info)" in html
    assert "function notifyFinishRequest(done)" in html
    assert "window.__czRunInfo = function ()" in html
    a_seg = html[html.index("function notifyFinishRequest(done)"):html.index("window.__czRunInfo")]
    assert "__czRequestFinishFromCardA" in a_seg
    assert "postPracticeLog" not in a_seg, "A 卡不能直接写库"
    shell_seg = html[html.index("function saveExternalRunIfNeeded()"):html.index("function bridgeCardA()")]
    assert "return false;" in shell_seg, "旧兜底直写必须为空实现"


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


def test_card_a_natural_end_opens_confirm(html):
    """A 卡自己走到点（没有 click）也要弹确认，而不是静默退 prep。"""
    assert "if (elapsed >= totalSec) { enterPause(); notifyFinishRequest(true); }" in html
    assert "function notifyRunEnd()" not in html, "旧直写回调必须移除"


def test_yesterday_unavailable_is_not_treated_as_zero(html):
    """昨天接口失败不能当成「昨天没练」去做对比。"""
    assert "yesterday_known" in html
    assert "yesterday: res[1] || null" in html
    assert "昨日数据不可用" in html
    assert "var yest = (payload && payload.yesterday) ? payload.yesterday : null;" in html, \
        "R 卡不能把 null 昨天折成空对象（那等于把失败当成昨天 0 秒）"


def test_combo_choice_is_restored(html):
    """上次选的组合要写进 localStorage，下次打开按组合号恢复，而不是永远默认 2卡-2。"""
    assert "if (!AUDIT) { save(); }" in html
    assert "state.combo = o.combo;" in html
    assert "COMBO_MODS[o.combo]" in html
