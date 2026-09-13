"""
Sprint 26091201 feat/badge-3d-ccg — Part B-1: card_theme 解析单一事实源.

Dad 2026-09-12 拍板:
- 优先用 achievements.card_theme (列 DEFAULT NULL)
- 未设时按 achievements.type 兜底映射 (agy 原方案按 category 是错的 — achievements.category
  只有 'milestone' / 'seasonal' 两个家族值, 跟主题无关; 人读分类是 type 字段)
- 仍未命中走 category=='seasonal' → 'frost'
- 仍未命中走 'azure'

参考:
- agy 方案 B.3 (agy-ccg-plan-260912.md) — 5 套主题色板
- 实现 B.4 映射 (此文件以 type 而非 category 为准, 修正原方案)
"""
from __future__ import annotations

# ─── 契约常量 ────────────────────────────────────────────────────────
DEFAULT_CARD_THEME = "azure"
VALID_CARD_THEMES = ("azure", "bamboo", "coral", "imperial", "frost")

# 按 achievements.type 兜底 (不是 category). 修正 agy B.4 表.
TYPE_THEME_MAP: dict[str, str] = {
    "突破": "azure",      # 23 行 — 日常突破, 沉稳深蓝
    "执着": "bamboo",     # 4 行 — 每日坚持, 竹林翠绿
    "段位": "bamboo",     # 10 行 — 基本功进阶, 同翠绿
    "巅峰": "coral",      # 4 行 — 大型考级/舞台, 热烈珊瑚
    "晋级": "coral",      # 2 行 — 考级晋升, 同珊瑚
    "神秘": "imperial",   # 1 行 — 隐藏成就, 皇紫耀金
    # seasonal (category) 走下方独立兜底
}


def _normalize_card_theme(value: object) -> str | None:
    """脏数据规整: 字符串小写去空格; 非 str / 空串返 None.

    Returns:
        合法 slug 或 None (调用方走兜底链)
    """
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    if v in VALID_CARD_THEMES:
        return v
    return None


def resolve_card_theme(
    badge_type: object = None,
    card_theme: object = None,
    category: object = None,
) -> str:
    """单点解析 badge 的 card_theme.

    优先级 (严格):
      1. card_theme 显式且合法 (小写去空格后 in VALID_CARD_THEMES) → 用它
      2. badge_type 命中 TYPE_THEME_MAP → 用它
      3. category == "seasonal" → "frost"
      4. 兜底 DEFAULT_CARD_THEME ("azure")

    脏数据 (非法 slug) 一律落回兜底链, 不抛异常.

    Args:
        badge_type: achievements.type (中文人读分类, 例 "突破"/"段位")
        card_theme: achievements.card_theme (DB 列, 可能 None / 脏值)
        category: achievements.category (家族值, "milestone"/"seasonal"/...)

    Returns:
        VALID_CARD_THEMES 中之一, 保证 str
    """
    # 1. 显式 card_theme 优先 (含大小写/空白容错)
    normalized = _normalize_card_theme(card_theme)
    if normalized is not None:
        return normalized

    # 2. type 兜底
    if isinstance(badge_type, str):
        t = badge_type.strip()
        if t in TYPE_THEME_MAP:
            return TYPE_THEME_MAP[t]

    # 3. category seasonal → frost
    if isinstance(category, str) and category.strip().lower() == "seasonal":
        return "frost"

    # 4. 默认
    return DEFAULT_CARD_THEME


__all__ = [
    "DEFAULT_CARD_THEME",
    "VALID_CARD_THEMES",
    "TYPE_THEME_MAP",
    "resolve_card_theme",
]


# ─── 星级 card_stars 契约 (dad image#9/4) ─────────────────────────────
# dad 2026-09-12: "ccg-stars 是 hard code 的还是每个 badge 背后有星级的字段支持?
#                 我建议要有后端的支撑, 不能写死。"
# 实现: achievements.card_stars 列 (NULL → 本文件按 type 兜底), 前端只做钳位。
STARS_MIN = 1
STARS_MAX = 5
DEFAULT_CARD_STARS = 3

# 无 card_stars 时按 achievements.type 兜底 (星越多越稀有/越难)
TYPE_STARS_MAP: dict[str, int] = {
    "突破": 2,   # 23 行 — 日常突破, 最常见
    "执着": 3,   # 4 行 — 每日坚持
    "段位": 3,   # 10 行 — 基本功进阶
    "晋级": 4,   # 2 行 — 考级晋升
    "神秘": 4,   # 1 行 — 隐藏成就
    "巅峰": 5,   # 4 行 — 大型考级/舞台
}


def normalize_card_stars(value: object) -> int | None:
    """脏数据规整: '4' / 4 → 4; 越界钳到 [STARS_MIN, STARS_MAX]; 非数返 None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return max(STARS_MIN, min(STARS_MAX, n))


def resolve_card_stars(
    card_stars: object = None,
    badge_type: object = None,
    category: object = None,
) -> int:
    """单点解析 badge 星级 (1..5).

    优先级 (严格):
      1. card_stars 显式且可解析 → 钳位后用它
      2. badge_type 命中 TYPE_STARS_MAP → 用它
      3. category == "seasonal" → 4
      4. 兜底 DEFAULT_CARD_STARS (3)

    Args:
        card_stars: achievements.card_stars (可能 None / 脏值 / 字符串)
        badge_type: achievements.type ("突破"/"段位"/...)
        category: achievements.category ("milestone"/"seasonal"/...)

    Returns:
        int in [STARS_MIN, STARS_MAX], 保证可 JSON 序列化
    """
    n = normalize_card_stars(card_stars)
    if n is not None:
        return n
    if isinstance(badge_type, str) and badge_type.strip() in TYPE_STARS_MAP:
        return TYPE_STARS_MAP[badge_type.strip()]
    if isinstance(category, str) and category.strip().lower() == "seasonal":
        return 4
    return DEFAULT_CARD_STARS
