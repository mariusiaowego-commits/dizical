"""Stage 维 report 图片 prompt 构造测试.

TDD red → green: 先写失败测试, 再写 build_stage_image_prompt 绿测.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.report_templates import build_stage_image_prompt


def _payload_full():
    """完整 stage payload (模拟 _build_stage_detail_payload 输出)."""
    return {
        "stage_order": 1,
        "stage_start": "2026-07-20",
        "stage_end": "2026-08-02",
        "effective_end": "2026-08-02",
        "lesson_date": "2026-08-02",
        "notes": None,
        "summary": {
            "total_minutes": 130,
            "practice_days": 5,
            "session_count": 12,
            "item_count": 3,
        },
        "by_item": [
            {"item_id": 1, "item_name": "长音", "minutes": 60, "session_count": 8},
            {"item_id": 2, "item_name": "吐音", "minutes": 40, "session_count": 3},
            {"item_id": 3, "item_name": "活指", "minutes": 30, "session_count": 1},
        ],
        "days": [
            {
                "date": "2026-07-25",
                "total_minutes": 30,
                "session_count": 3,
                "groups": [
                    {
                        "item_id": 1,
                        "item_name": "长音",
                        "minutes": 20,
                        "sessions": [
                            {"duration_minutes": 10, "content": "吐音练习"},
                            {"duration_minutes": 10, "content": "长音保持"},
                        ],
                    },
                    {
                        "item_id": 2,
                        "item_name": "吐音",
                        "minutes": 10,
                        "sessions": [{"duration_minutes": 10, "content": ""}],
                    },
                ],
            },
            {
                "date": "2026-07-27",
                "total_minutes": 25,
                "session_count": 2,
                "groups": [
                    {
                        "item_id": 1,
                        "item_name": "长音",
                        "minutes": 25,
                        "sessions": [{"duration_minutes": 25, "content": "低八度练习"}],
                    },
                ],
            },
        ],
    }


def test_returns_prompt_and_aspect():
    """happy: 返 (prompt, aspect) tuple."""
    prompt, aspect = build_stage_image_prompt(_payload_full(), "YoYo")
    assert isinstance(prompt, str)
    assert isinstance(aspect, str)


def test_aspect_ratio_is_landscape():
    """stage 表格横向 → 图片横版."""
    _, aspect = build_stage_image_prompt(_payload_full(), "YoYo")
    assert aspect == "landscape"


def test_prompt_contains_stage_order():
    prompt, _ = build_stage_image_prompt(_payload_full(), "YoYo")
    assert "Stage 1" in prompt


def test_prompt_contains_period():
    prompt, _ = build_stage_image_prompt(_payload_full(), "YoYo")
    assert "2026-07-20" in prompt
    assert "2026-08-02" in prompt


def test_prompt_contains_summary_numbers():
    prompt, _ = build_stage_image_prompt(_payload_full(), "YoYo")
    assert "130" in prompt  # total_minutes
    assert "5" in prompt    # practice_days
    assert "12" in prompt   # session_count


def test_prompt_contains_item_names():
    prompt, _ = build_stage_image_prompt(_payload_full(), "YoYo")
    assert "长音" in prompt
    assert "吐音" in prompt
    assert "活指" in prompt


def test_prompt_contains_day_content():
    prompt, _ = build_stage_image_prompt(_payload_full(), "YoYo")
    assert "2026-07-25" in prompt
    assert "吐音练习" in prompt


def test_prompt_contains_child_name():
    prompt, _ = build_stage_image_prompt(_payload_full(), "YoYo")
    assert "YoYo" in prompt


def test_prompt_no_unescaped_placeholders():
    """layout 段占位符都填了, style 段可以保留 {xxx} 形式 (给 LLM 看的示例)."""
    prompt, _ = build_stage_image_prompt(_payload_full(), "YoYo")
    import re
    # 找到"layout" 段后, "data_fields" 段之前
    layout_start = prompt.find("# 内容布局")
    layout_end = prompt.find("\n# data_fields", layout_start) if layout_start >= 0 else -1
    if layout_start >= 0 and layout_end > layout_start:
        layout_section = prompt[layout_start:layout_end]
        leftover = re.findall(r"\{[a-z_]+\}", layout_section)
        assert leftover == [], f"layout 段未替换的占位符: {leftover}"


def test_empty_days_no_crash():
    """空 days 也能产 prompt, 含'暂无练习日'兜底文案."""
    p = _payload_full()
    p["days"] = []
    p["by_item"] = []
    p["summary"] = {"total_minutes": 0, "practice_days": 0, "session_count": 0, "item_count": 0}
    prompt, _ = build_stage_image_prompt(p, "YoYo")
    assert "暂无练习日" in prompt or "暂无数据" in prompt


def test_minutes_percentage_in_item_bar():
    """科目小计包含百分比 (跟 bar chart 写法)."""
    prompt, _ = build_stage_image_prompt(_payload_full(), "YoYo")
    # 长音 60/130 ≈ 46%
    assert "46%" in prompt or "46" in prompt


def test_session_content_truncated_in_summary():
    """内容预览有截断逻辑 (避免 prompt 过长)."""
    long_content = "x" * 200
    p = _payload_full()
    p["days"][0]["groups"][0]["sessions"][0]["content"] = long_content
    prompt, _ = build_stage_image_prompt(p, "YoYo")
    # prompt 不应包含 200 个 x 全部
    assert prompt.count("x") < 100
