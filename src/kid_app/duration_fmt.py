"""练习时长展示口径 B。与 static/js/duration-fmt.js 同一套规则。

0 秒 → 空字符串；<60 → ``N秒``；整分钟 → ``N分``；有余数 → ``N分M秒``。
``short`` 给月历格子：``mm:ss``，分钟可以超过 59，0 秒同样不显示。
"""
from __future__ import annotations

import inspect
import math
from typing import Any, Callable, Optional


def fmt(sec: Any) -> str:
    n = _as_int(sec)
    if n is None or n <= 0:
        return ""
    if n < 60:
        return f"{n}秒"
    minutes, rem = divmod(n, 60)
    if rem == 0:
        return f"{minutes}分"
    return f"{minutes}分{rem}秒"


def short(sec: Any) -> str:
    n = _as_int(sec)
    if n is None or n <= 0:
        return ""
    minutes, rem = divmod(n, 60)
    return f"{minutes}:{rem:02d}"


def pick_seconds(seconds: Any, minutes: Any) -> int:
    """优先用已存的秒。缺省、或秒为 0 但分钟 > 0（未回填的 DEFAULT 0）时用分钟 × 60。"""
    mins = _as_int(minutes)
    if mins is None or mins < 0:
        mins = 0
    if seconds is None or seconds == "":
        return mins * 60
    s = _as_int(seconds)
    if s is None or s < 0:
        return mins * 60
    if s == 0 and mins > 0:
        return mins * 60
    return s


def write_minutes(minutes: int, seconds: Optional[int]) -> int:
    """显式带了秒且秒 > 0 时，落库分钟 = ceil(秒/60)，至少 1。没带秒则原样返回。"""
    m = int(minutes or 0)
    if seconds is None:
        return m
    s = int(seconds)
    if s <= 0:
        return m
    return max(1, math.ceil(s / 60))


def resolve_request_seconds(seconds: Optional[int], minutes: int) -> int:
    if seconds is None:
        return int(minutes or 0) * 60
    return int(seconds)


def annotate_item(it: dict) -> dict:
    out = dict(it)
    out["seconds"] = pick_seconds(out.get("seconds"), out.get("minutes"))
    return out


def annotate_session(s: dict) -> dict:
    out = dict(s)
    out["duration_seconds"] = pick_seconds(out.get("duration_seconds"), out.get("duration_minutes"))
    return out


def annotate_behavior(entry: dict) -> dict:
    out = dict(entry)
    out["seconds"] = pick_seconds(out.get("seconds"), out.get("minutes"))
    return out


def total_seconds_of_practice(p: Optional[dict]) -> int:
    """当日合计 = 各条 seconds 相加。没有明细时回退到 total_seconds / total_minutes×60。"""
    if not p:
        return 0
    items = p.get("items") or []
    if isinstance(items, str):
        import json
        try:
            items = json.loads(items) if items else []
        except (TypeError, ValueError):
            items = []
    if isinstance(items, list) and items:
        total = 0
        for it in items:
            if isinstance(it, dict):
                total += pick_seconds(it.get("seconds"), it.get("minutes"))
        return total
    return pick_seconds(p.get("total_seconds"), p.get("total_minutes"))


def invoke(fn: Callable, *args, **kwargs):
    """只把对方签名里有的关键字传进去。MySQL 镜像还没接 seconds 时不要 TypeError。"""
    sig = inspect.signature(fn)
    if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return fn(*args, **kwargs)


def _as_int(v: Any) -> Optional[int]:
    if v is None or v is True or v is False or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
