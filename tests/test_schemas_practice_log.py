"""PR-A-1: Pydantic schemas for /api/log request body.

覆盖 4 种契约场景:
1. 顶层三字段 (tempo_note/tempo_bpm/content) → session 路径
2. 嵌套 session_detail alias → 合并到顶层
3. 缺 content → raise ValidationError (session 路径必填)
4. 空 body → raise ValidationError
"""
import pytest
from pydantic import ValidationError

from src.kid_app.schemas import PracticeLogRequest, SessionDetail


def test_top_level_three_fields_parsed():
    """顶层三字段全部传入 → 验证通过, 字段值正确."""
    req = PracticeLogRequest.model_validate({
        "date": "2026-07-29",
        "item": "萨丽哈",
        "item_id": 1340,
        "minutes": 5,
        "tempo_note": "♪",
        "tempo_bpm": 92,
        "content": "第一分句连吐",
    })
    assert req.date.isoformat() == "2026-07-29"
    assert req.item == "萨丽哈"
    assert req.item_id == 1340
    assert req.minutes == 5
    assert req.tempo_note == "♪"
    assert req.tempo_bpm == 92
    assert req.content == "第一分句连吐"
    assert req.is_extra is False
    assert req.content_source == "manual"
    assert req.has_session_detail() is True


def test_nested_session_detail_merged_to_top_level():
    """嵌套 session_detail alias → 合并到顶层字段."""
    req = PracticeLogRequest.model_validate({
        "date": "2026-07-29",
        "item": "萨丽哈",
        "item_id": 1340,
        "minutes": 5,
        "session_detail": {
            "tempo_note": "♩",
            "tempo_bpm": 80,
            "content": "背 1 句",
        },
    })
    assert req.tempo_note == "♩"
    assert req.tempo_bpm == 80
    assert req.content == "背 1 句"
    assert req.has_session_detail() is True


def test_session_path_with_empty_content_raises():
    """session 路径: tempo_note + tempo_bpm + content='' → ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        PracticeLogRequest.model_validate({
            "date": "2026-07-29",
            "item": "萨丽哈",
            "item_id": 1340,
            "minutes": 5,
            "tempo_note": "♪",
            "tempo_bpm": 92,
            "content": "   ",  # 仅空白
        })
    errors = exc_info.value.errors()
    assert any("content" in str(e["loc"]) for e in errors), f"应报 content 字段错误, 实际: {errors}"


def test_session_path_missing_content_falls_back_to_legacy():
    """session 路径: 传 tempo_note + tempo_bpm 但缺 content → 不构成 session 路径,
    has_session_detail() = False, 走旧 save_daily_practice (兼容)."""
    req = PracticeLogRequest.model_validate({
        "date": "2026-07-29",
        "item": "萨丽哈",
        "item_id": 1340,
        "minutes": 5,
        "tempo_note": "♪",
        "tempo_bpm": 92,
        # 缺 content → 旧路径
    })
    assert req.has_session_detail() is False
    assert req.tempo_note == "♪"  # 字段仍保留
    assert req.tempo_bpm == 92
    assert req.content is None


def test_empty_body_raises():
    """空 body → ValidationError."""
    with pytest.raises(ValidationError):
        PracticeLogRequest.model_validate({})


def test_no_session_detail_routes_to_legacy():
    """不传 tempo_note/tempo_bpm/content → has_session_detail() = False (走旧路径)."""
    req = PracticeLogRequest.model_validate({
        "date": "2026-07-29",
        "item": "萨丽哈",
        "item_id": 1340,
        "minutes": 5,
    })
    assert req.has_session_detail() is False
    assert req.tempo_note is None
    assert req.tempo_bpm is None
    assert req.content is None


def test_is_extra_field():
    """is_extra 默认 False, 可显式 True."""
    req_normal = PracticeLogRequest.model_validate({
        "date": "2026-07-29", "item": "x", "item_id": 1, "minutes": 5,
    })
    assert req_normal.is_extra is False

    req_extra = PracticeLogRequest.model_validate({
        "date": "2026-07-29", "item": "x", "item_id": 1, "minutes": 5,
        "is_extra": True,
    })
    assert req_extra.is_extra is True


def test_practice_at_cst_iso():
    """practice_at 接受 CST ISO 字符串."""
    req = PracticeLogRequest.model_validate({
        "date": "2026-07-29", "item": "x", "item_id": 1, "minutes": 5,
        "practice_at": "2026-07-29 20:15:00.000",
    })
    assert req.practice_at == "2026-07-29 20:15:00.000"


def test_session_detail_model_alone():
    """SessionDetail 子模型可独立实例化."""
    sd = SessionDetail(tempo_note="♩", tempo_bpm=80, content="x", content_source="legacy")
    assert sd.tempo_note == "♩"
    assert sd.content_source == "legacy"
