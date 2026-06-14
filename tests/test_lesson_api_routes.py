"""课程管理 API 路由测试 (fix/lesson-api-body-parsing)

背景: 2026-06-14 用户在 config-lessons 页点"确认上课"按钮,
前端 POST /api/lessons/confirm 走 JSON body 传 {date}, 但后端 endpoint
签名 def api_confirm_lesson(date: str) 把 date 当 query 参数收.
FastAPI 422 Field required, 前端 alert 'undefined' (response 走 FastAPI
默认 422 格式, 没有 {ok, error} 字段).

同样的 bug 影响 2 个 endpoint:
- POST /api/lessons (add) — 同样 body/query 不匹配
- POST /api/lessons/confirm (confirm) — 同上

修复: 按已修好的 api_cancel_lesson 模式, 让 add + confirm 也兼容
query + body 两种传参. 同步加 ValueError -> 400 友好报错.

测试覆盖 (5 cases):
1. confirm: body 传 date → 200 OK + status=attended (新修的路径)
2. confirm: query 传 date → 200 OK (旧路径, 向后兼容)
3. confirm: 不传 date → 400 with {ok, error} (不是 FastAPI 422)
4. add: body 传 date → 200 OK + lesson 创建
5. add: 重复 add 已存在日期 → 400 with {ok, error}

硬约束:
- 不破 dizical 核心功能
- 测试用 2099-12-31 这种永不会出现在女儿课表的"测试日期"
- teardown 清理: cancel_lesson 删除测试数据
"""

from fastapi.testclient import TestClient

from src.kid_app.app import app
from src.models import LessonStatus

client = TestClient(app)

# 测试用日期: 2099 年, 永远不会出现在女儿真实课表
TEST_DATE = "2099-12-31"


def _cleanup():
    """测试清理: 物理删除任何残留的 TEST_DATE 课程

    cancel_lesson 只翻 status=cancelled 不真删, 多次跑测试会撞 "课程已存在".
    直连 db.delete_lesson by id 物理删.
    """
    import datetime as dt
    from src.database import db
    existing = db.get_lesson_by_date(dt.date.fromisoformat(TEST_DATE))
    if existing and existing.id is not None:
        db.delete_lesson(existing.id)


def setup_function(_):
    """每个 test 前清理"""
    _cleanup()


def teardown_function(_):
    """每个 test 后清理"""
    _cleanup()


# ─── confirm endpoint ─────────────────────────────────────


def test_confirm_with_body_returns_200_and_attended():
    """confirm: JSON body 传 date → 200 OK + status=attended (新修的路径)

    回归: 修复前这个调用返 422 (FastAPI 校验 query.date 缺失).
    """
    # 先 add 一节课程 (走已修过的 add 路径)
    add_res = client.post("/config/api/lessons", json={"date": TEST_DATE})
    assert add_res.status_code == 200, f"add failed: {add_res.status_code} {add_res.text}"
    assert add_res.json()["ok"] is True

    # 关键: 用 body 传 date 确认上课
    res = client.post(
        "/config/api/lessons/confirm",
        json={"date": TEST_DATE},
    )
    assert res.status_code == 200, f"expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["ok"] is True
    assert data["lesson"]["date"] == TEST_DATE
    assert data["lesson"]["status"] == "attended"


def test_confirm_with_query_returns_200_and_attended():
    """confirm: query string 传 date → 200 OK (向后兼容, 旧路径)

    不破已有用法: 万一别处 (CLI / 脚本 / 老 curl) 用 query 调, 仍能跑.
    """
    # 准备课程
    client.post("/config/api/lessons", json={"date": TEST_DATE})

    # 用 query 传 (旧 API 风格)
    res = client.post(f"/config/api/lessons/confirm?date={TEST_DATE}")
    assert res.status_code == 200, f"expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["ok"] is True
    assert data["lesson"]["status"] == "attended"


def test_confirm_missing_date_returns_400_with_error_field():
    """confirm: 不传 date → 400 + {ok: false, error: '...'} (不是 FastAPI 422)

    回归: 修复前 FastAPI 422 返 {"detail": [...]} 这种格式,
    前端 res.error 取不到 → alert 'undefined'.
    修复后我们用 {ok, error} 格式, 前端能正确显示.
    """
    res = client.post("/config/api/lessons/confirm")
    assert res.status_code == 400, f"expected 400, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["ok"] is False
    assert "error" in data, f"missing error field: {data}"
    assert "date" in data["error"].lower()


# ─── add endpoint ─────────────────────────────────────────


def test_add_with_body_returns_200_and_creates_lesson():
    """add: JSON body 传 date → 200 OK + 创建课程 (新修的路径)

    回归: 修复前 '添加' 按钮也是坏的, 用户在 UI 加课程失败.
    """
    res = client.post("/config/api/lessons", json={"date": TEST_DATE})
    assert res.status_code == 200, f"expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["ok"] is True
    assert data["lesson"]["date"] == TEST_DATE
    assert data["lesson"]["status"] == "scheduled"
    assert data["lesson"]["fee"] == 600  # default


def test_add_duplicate_date_returns_400_with_error_field():
    """add: 重复 add 同一天 → 400 + {ok: false, error: '课程已存在'}

    业务规则: add_lesson 内部检查重复会抛 ValueError,
    修复前被通用 except 包了, error 格式仍能透传, 但保留测试覆盖
    '重复 add' 这个负面场景, 防止后续重构破坏.
    """
    # 第一次 add
    r1 = client.post("/config/api/lessons", json={"date": TEST_DATE})
    assert r1.status_code == 200, f"first add failed: {r1.text}"
    # 第二次 add (重复)
    r2 = client.post("/config/api/lessons", json={"date": TEST_DATE})
    assert r2.status_code == 400, f"expected 400 for dup, got {r2.status_code}: {r2.text}"
    data = r2.json()
    assert data["ok"] is False
    assert "error" in data
    assert "已存在" in data["error"] or "exist" in data["error"].lower()
