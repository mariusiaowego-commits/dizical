"""今日练习记录弹层（#czPopFrame）的数据回灌契约（v3.51）。

事故：弹层 iframe 挂在宿主 document 上，不在 czCanvas 里，
applyDayToModules 只遍历画布内 iframe[data-mod]，弹层因此永远停在空态 ——
「查看记录明细」没有数据，单条编辑入口也不可达。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "src" / "kid_app" / "templates" / "practice-dsh.html"


def _html() -> str:
    return TPL.read_text(encoding="utf-8")


def test_popout_frame_gets_day_payload_on_load():
    src = _html()
    seg = src[src.index("function buildPop()"):src.index("function refreshPopSummary()")]
    assert "f.srcdoc = moduleSource('R');" in seg
    assert "f.contentWindow.__czApplyDay(dayPayload)" in seg, "弹层装载后必须推当日数据"


def test_apply_day_pushes_popout_frame_outside_canvas():
    src = _html()
    seg = src[src.index("function applyDayToModules()"):src.index("function reloadDay()")]
    assert "document.getElementById('czPopFrame')" in seg, "弹层不在画布，必须单独推"
    assert "refreshPopSummary()" in seg, "推完数据要刷新底栏汇总"


def test_version_is_v351():
    src = _html()
    assert "var DSH_VERSION = 'v3.51';" in src
