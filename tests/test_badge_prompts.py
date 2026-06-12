"""tests/test_badge_prompts.py — 单元测试 badge_prompts 模块"""
import pytest

from src.kid_app.badge_prompts import (
    UNLOCKED_TPL,
    build_unlocked_prompt,
    build_unlocked_template_field,
)


class TestBuildUnlockedPrompt:
    def test_normal_placeholder(self):
        ph = "a cute chibi girl holding a bamboo flute with stars around her"
        result = build_unlocked_prompt(ph)
        assert "[PLACEHOLDER]" not in result
        assert "An emoji-adjacent 3D enamel pin" in result
        assert ph in result
        assert "Polished gold metal borders" in result
        assert "white background" in result

    def test_strips_whitespace(self):
        ph = "   a cute child playing a flute   "
        result = build_unlocked_prompt(ph)
        assert ph.strip() in result
        # 前后多余空格不残留
        assert "  a cute child playing a flute  " not in result

    def test_min_length_boundary(self):
        # 5 字符合法
        ph = "abcde"
        result = build_unlocked_prompt(ph)
        assert "abcde" in result

    def test_below_min_raises(self):
        with pytest.raises(ValueError, match="至少 5 字符"):
            build_unlocked_prompt("abcd")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="至少 5 字符"):
            build_unlocked_prompt("")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="placeholder 不能为空"):
            build_unlocked_prompt(None)  # type: ignore[arg-type]

    def test_whitespace_only_raises(self):
        # 4 个空格 < 5 字符限制
        with pytest.raises(ValueError, match="至少 5 字符"):
            build_unlocked_prompt("    ")

    def test_max_length_boundary(self):
        # 500 字符合法
        ph = "a" * 500
        result = build_unlocked_prompt(ph)
        assert ph in result

    def test_above_max_raises(self):
        with pytest.raises(ValueError, match="最多 500 字符"):
            build_unlocked_prompt("a" * 501)

    def test_long_prompt_includes_template_end(self):
        """完整 prompt 应包含模板最后一句"""
        result = build_unlocked_prompt("a magical flute")
        assert "clean white background" in result


class TestBuildUnlockedTemplateField:
    def test_normal_placeholder(self):
        ph = "a flute wearing a soldier helmet"
        result = build_unlocked_template_field(ph)
        assert "[PLACEHOLDER]" not in result
        assert ph in result

    def test_empty_placeholder_returns_fallback(self):
        # fallback 场景: DB 旧数据 placeholder 是空
        result = build_unlocked_template_field("")
        assert "[PLACEHOLDER]" not in result
        assert "an achievement icon" in result

    def test_short_placeholder_returns_fallback(self):
        result = build_unlocked_template_field("abc")
        assert "[PLACEHOLDER]" not in result
        assert "an achievement icon" in result

    def test_none_placeholder_returns_fallback(self):
        result = build_unlocked_template_field(None)  # type: ignore[arg-type]
        assert "[PLACEHOLDER]" not in result


class TestTemplateIntegrity:
    def test_template_has_placeholder_marker(self):
        """模板必须含 [PLACEHOLDER] 占位符 (运行时 replace 的依据)"""
        assert "[PLACEHOLDER]" in UNLOCKED_TPL

    def test_template_has_enamel_pin_keyword(self):
        """enamel pin 是 dizicute 强制约束 (DESIGN.md §品牌资产 line 68)"""
        assert "enamel pin" in UNLOCKED_TPL.lower()

    def test_template_has_gold_border_keyword(self):
        """cloisonné 掐丝 + 厚金边 (DESIGN.md §品牌资产)"""
        assert "gold" in UNLOCKED_TPL.lower()
        assert "border" in UNLOCKED_TPL.lower()
