"""
Badge enamel pin prompt 模板 + 组装.

历史:
- 2026-05-12 v2 统一风格 (docs/badge-prompts.md line 9-12)
- 2026-06-12 V1 提取到本模块 (PR-A)

设计:
- UNLOCKED_TPL 是单源, 所有 V1 制作的 badge 都用这个模板 + placeholder 替换
- locked 态由前端 CSS grayscale 灰度实现 (app.py:517 注释), 不需要单独 prompt
- 模板字符顺序固定, 改前要 review PRD §0.3 (enamel pin 强制约束)
"""
from __future__ import annotations


# 单源模板 (从 docs/badge-prompts.md line 9-12 提取)
UNLOCKED_TPL = (
    "An emoji-adjacent 3D enamel pin of [PLACEHOLDER]. "
    "Polished gold metal borders enclose flat, glossy enamel fills. "
    "The design is a centered, iconic illustration with a smooth, "
    "friendly silhouette and vibrant colors, matching a child's "
    "achievement badge style. Studio lighting reflects off the "
    "reflective enamel and raised gold metal edges. Orthographic, "
    "straight-on view, high quality, isolated on a clean white background."
)


def build_unlocked_prompt(placeholder: str) -> str:
    """组装完整 enamel pin prompt. placeholder 必填, 长度 5-500 字符.

    Raises:
        ValueError: placeholder 为空 / 太短 / 太长
    """
    if placeholder is None:
        raise ValueError("placeholder 不能为空")
    p = placeholder.strip()
    if len(p) < 5:
        raise ValueError(f"placeholder 至少 5 字符 (当前 {len(p)})")
    if len(p) > 500:
        raise ValueError(f"placeholder 最多 500 字符 (当前 {len(p)})")
    return UNLOCKED_TPL.replace("[PLACEHOLDER]", p)


def build_unlocked_template_field(placeholder: str) -> str:
    """返回 achievements.unlocked_template 列要存的值 (跟 build_unlocked_prompt 同效果).

    跟 build_unlocked_prompt 区别: 这个方法不抛 ValueError, 返回 fallback 字符串.
    用途: DB 已存 fallback 时 (例如旧数据 placeholder 是空), 不要让读取炸.
    """
    try:
        return build_unlocked_prompt(placeholder)
    except ValueError:
        return UNLOCKED_TPL.replace("[PLACEHOLDER]", "an achievement icon")
