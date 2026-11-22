"""结构化练习环节（sessions）契约：解析 / 落库 / 老师要求透传。

回归点：老师要求里的速度必须落在每个练习环节（session）上，练习助手选中环节后
直接带出 BPM，不再回落 ♪=80；Q 卡的大标题是环节名，不是第一条要求。
"""
import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from src import practice as practice_module


@pytest.fixture()
def client():
    """临时 SQLite + 同时替换 config 路由里绑定的 db 引用。"""
    from src.database import Database
    from src.kid_app.app import app as fastapi_app
    from src import models
    import src.database as db_module
    import src.kid_app.app as app_module
    import src.kid_app.routes.config as config_module
    import src.practice as practice_module_db

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("DATABASE_URL", "")
    new_db = Database(db_path=path)
    # worktree 的 Database() 只建基础表；content_options / is_archived 由生产迁移补列，
    # 这里补上，否则 get_practice_items 的 SELECT 直接报 no such column。
    with new_db._get_connection() as conn:
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(practice_items)")}
        if "content_options" not in cols:
            conn.execute("ALTER TABLE practice_items ADD COLUMN content_options TEXT DEFAULT ''")
        if "is_archived" not in cols:
            conn.execute("ALTER TABLE practice_items ADD COLUMN is_archived INTEGER DEFAULT 0")
        conn.commit()

    monkeypatch.setattr(models.settings, "db_path", path)
    monkeypatch.setattr(db_module, "db", new_db)
    monkeypatch.setattr(app_module, "db", new_db)
    monkeypatch.setattr(config_module, "db", new_db)
    monkeypatch.setattr(practice_module_db, "db", new_db)

    with TestClient(fastapi_app) as test_client:
        yield test_client, new_db

    monkeypatch.undo()
    try:
        os.unlink(path)
    except OSError:
        pass


def _insert_item(db, name="环节测试科目"):
    with db._get_connection() as conn:
        conn.execute("INSERT INTO practice_items (name, is_active) VALUES (?, 1)", (name,))
        conn.commit()
        row = conn.execute(
            "SELECT item_id FROM practice_items WHERE name = ? ORDER BY item_id DESC LIMIT 1",
            (name,),
        ).fetchone()
    return row["item_id"]


def test_parse_structured_and_legacy_text():
    legacy = practice_module.parse_practice_sessions("长音,吐音，连吐\n换气")
    assert [s["name"] for s in legacy] == ["长音", "吐音", "连吐", "换气"]
    assert all(s["bpm"] is None for s in legacy)

    sessions = practice_module.parse_practice_sessions(
        '[{"name":"第三段","bpm":"98","note":"♪","requirement":"多练"}]'
    )
    assert sessions == [
        {"name": "第三段", "bpm": 98, "note": "♪", "requirement": "多练"}
    ]


def test_parse_structured_drops_out_of_range_bpm():
    sessions = practice_module.parse_practice_sessions([{"name": "太快", "bpm": 260, "note": "♩"}])
    assert sessions[0]["bpm"] is None
    assert sessions[0]["note"] == "♩"


@pytest.mark.parametrize("text,expect", [
    ("80乐段 ♪=90", 90),
    ("tu （♩=65）", 65),
    ("中板70", 70),
    ("3-6行练习 ♩=72", 72),
    ("低音3、4", None),
])
def test_extract_bpm_prefers_explicit_tempo(text, expect):
    """历史名称把速度放末尾或混在名称里时，不能被前面的数字抢走。"""
    assert practice_module.extract_session_bpm(text) == expect


def test_parse_legacy_text_starting_with_bracket():
    """以 [ 开头但不是合法 JSON 的历史文本，按逗号切分而不是整段丢弃。"""
    sessions = practice_module.parse_practice_sessions("[基础]长音,吐音")
    assert [s["name"] for s in sessions] == ["[基础]长音", "吐音"]


def test_parse_accepts_bpm_with_spaces_and_dedupes():
    sessions = practice_module.parse_practice_sessions(
        [{"name": "长音", "bpm": " 72 "}, {"name": "长音", "bpm": 80}]
    )
    assert sessions == [{"name": "长音", "bpm": 72, "note": "♩", "requirement": ""}]
    dumped = practice_module.serialize_practice_sessions(sessions + sessions)
    assert json.loads(dumped) == sessions


def test_content_options_sessions_roundtrip(client, auth_as):
    test_client, db = client
    item_id = _insert_item(db)
    auth_as("dad")
    payload = {
        "sessions": [
            {"name": "八度练习", "bpm": 72, "note": "♩", "requirement": "先慢后快"},
            {"name": "正常长音练习", "bpm": 60, "note": "♪", "requirement": "气息平稳"},
        ]
    }
    res = test_client.put(f"/config/api/practice/items/{item_id}/content-options", json=payload)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["options"] == ["八度练习", "正常长音练习"]
    assert json.loads(body["content_options"])[1]["bpm"] == 60

    listed = test_client.get("/config/api/practice/items")
    assert listed.status_code == 200
    item = next(i for i in listed.json()["items"] if i["item_id"] == item_id)
    assert [s["name"] for s in item["sessions"]] == ["八度练习", "正常长音练习"]
    assert item["sessions"][1]["note"] == "♪"


@pytest.mark.parametrize("sessions,expect", [
    ([{"name": "越界", "bpm": 260}], "速度需在 40–200"),
    ([{"name": "名" * 51}], "超过 50 字"),
    ([{"name": ""}], "环节名称不能为空"),
])
def test_content_options_rejects_invalid_session(client, auth_as, sessions, expect):
    test_client, db = client
    item_id = _insert_item(db)
    auth_as("dad")
    res = test_client.put(f"/config/api/practice/items/{item_id}/content-options", json={"sessions": sessions})
    assert res.status_code == 400, res.text
    assert expect in res.json()["error"]


@pytest.mark.parametrize("text,expect", [
    ("速度80", 80),
    ("速度 90", 90),
    ("速度＝88", 88),
    ("80 bpm", 80),
    ("72BPM", 72),
    ("每分钟80拍", 80),
    ("♩＝90", 90),
    ("♩=240 ♪=90", 90),
    ("♩=30 ♪=90", 90),
    ("bpm=100", 100),
    ("80拍", None),
    ("第100拍", None),
    ("共120拍", None),
    ("中音54", None),
    ("低音34；低音54", None),
    ("第48条", None),
    ("[1001] 长音练习", None),
    ("长音 45秒", None),
])
def test_extract_bpm_ignores_note_names_and_numbers(text, expect):
    """裸数字只在速度语境里才算 BPM；音名/小节号/编号/拍数不能打到节拍器上。"""
    assert practice_module.extract_session_bpm(text) == expect


def _frontend_extract_bpm_block() -> str:
    from pathlib import Path
    html = Path(__file__).resolve().parents[1].joinpath(
        "src/kid_app/templates/practice-dsh.html"
    ).read_text(encoding="utf-8")
    start = html.index("  var TEMPO_RE")
    return html[start:html.index("  function extractNote", start)]


def test_frontend_and_backend_extract_bpm_agree():
    """前后端同一张表：画布不能一边 API 给 90、一边自己算成 null。"""
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        pytest.skip("node 不可用，跳过前后端口径对照")
    cases = ["速度80", "80拍", "第100拍", "每分钟80拍", "72 bpm", "♩＝90",
             "♩=240 ♪=90", "♩=30 ♪=90", "80乐段 ♪=90", "中音54", "[1001] 长音练习"]
    driver = _frontend_extract_bpm_block() + (
        "\nconst cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "\nprocess.stdout.write(JSON.stringify(cases.map(extractBpm)));"
    )
    out = subprocess.run(
        [node, "-e", driver], input=json.dumps(cases), text=True,
        capture_output=True, check=True, timeout=30,
    ).stdout
    assert json.loads(out) == [practice_module.extract_session_bpm(c) for c in cases]


def test_assignment_sessions_passthrough(client, auth_as):
    test_client, db = client
    item_id = _insert_item(db, "春耕曲环节")
    auth_as("dad")
    sessions = [
        {"name": "主题", "bpm": 60, "note": "♩", "requirement": "田园风味"},
        {"name": "第三段", "bpm": 98, "note": "♪", "requirement": "多练"},
    ]
    created = test_client.post("/config/api/assignments", json={
        "lesson_date": "2026-11-21",
        "items": [{"item": "春耕曲环节", "item_id": item_id, "requirement": "", "sessions": sessions}],
        "notes": "",
    })
    assert created.status_code == 200, created.text
    assert created.json()["ok"] is True

    listed = test_client.get("/config/api/assignments?weeks=52")
    asg = next(a for a in listed.json()["assignments"] if a["lesson_date"] == "2026-11-21")
    item = next(i for i in asg["items"] if i["item_id"] == item_id)
    assert [s["name"] for s in item["sessions"]] == ["主题", "第三段"]
    assert item["sessions"][1]["bpm"] == 98
    # 老消费者仍能读到聚合后的速度串
    assert item["metronome"] == "♩=60 / ♪=98"


def test_history_assignment_does_not_inherit_current_sessions(client, auth_as):
    """两周前没存 sessions 的作业保持空，不能借用今天配置的环节与速度。"""
    test_client, db = client
    item_id = _insert_item(db, "历史环节科目")
    auth_as("dad")
    put = test_client.put(
        f"/config/api/practice/items/{item_id}/content-options",
        json={"sessions": [{"name": "新环节", "bpm": 72, "note": "♩", "requirement": ""}]},
    )
    assert put.status_code == 200, put.text
    for day in ("2026-11-08", "2026-11-21"):
        res = test_client.post("/config/api/assignments", json={
            "lesson_date": day,
            "items": [{"item": "历史环节科目", "item_id": item_id, "requirement": "老要求"}],
            "notes": "",
        })
        assert res.status_code == 200, res.text

    listed = test_client.get("/config/api/assignments?weeks=52")
    by_day = {a["lesson_date"]: a for a in listed.json()["assignments"]}
    old_item = next(i for i in by_day["2026-11-08"]["items"] if i["item_id"] == item_id)
    new_item = next(i for i in by_day["2026-11-21"]["items"] if i["item_id"] == item_id)
    assert old_item["sessions"] == []
    assert [s["name"] for s in new_item["sessions"]] == ["新环节"]
    assert new_item["sessions"][0]["bpm"] == 72
