"""今日练习记录单条编辑/删除的前端契约（v3.50）。

事故线索（2026-11-11 审计）：
- 编辑弹窗把 BPM 边界写成 30–240，后端是 40–200 → 合法 UI 输入直接 400。
- 保存时把 tempo_note 拼成 '♩=84'，后端只接受单字符 → 必 400。
- 刷新找的是 window.parent（画布层），__czReloadDay 在宿主上 → 编辑后界面不更新。

这些断言都是静态契约，不碰数据库；真机行为由 /api/practice-sessions 的接口测试守。
"""

from pathlib import Path

from src.kid_app.schemas import BPM_MAX, BPM_MIN

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "src" / "kid_app" / "templates" / "practice-dsh.html"


def _html() -> str:
    return TPL.read_text(encoding="utf-8")


def test_edit_dialog_writes_through_session_api():
    src = _html()
    assert 'id="s2EditOverlay"' in src
    assert "'/api/practice-sessions/' + sessionId" in src
    assert "method: 'PUT'" in src
    assert "method: 'DELETE'" in src


def test_bpm_input_matches_backend_bounds():
    src = _html()
    assert f'id="s2EditBpm" type="number" inputmode="numeric" min="{BPM_MIN}" max="{BPM_MAX}"' in src
    assert f"bpm >= {BPM_MIN} && bpm <= {BPM_MAX}" in src


def test_tempo_note_sent_as_single_symbol():
    src = _html()
    assert "tempo_note: editNoteValue()," in src
    assert "editNoteValue() + '='" not in src


def test_reload_walks_ancestor_frames():
    src = _html()
    assert "win !== win.top" in src
    assert "typeof win.__czReloadDay === 'function'" in src


def test_record_row_renders_real_note_symbol():
    src = _html()
    assert "noteFromSession(session) + '=' + bpm" in src
    assert "'♩=' + session.tempo_bpm" not in src
