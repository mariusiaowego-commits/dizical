"""
Nous Portal 状态检查 + 连通性测试.

设计 (用户 2026-06-12 拍板):
- dizical 项目不直接连 Nous API, 走 hermes Tool Gateway
- dizical profile 必须配置 Tool Gateway "Image generation: via Nous Portal"
- 此模块只检查 Tool Gateway 状态, 不实际生图 (生图走 badge_generator)
- 调 `hermes --profile dizical portal status` 解析 stdout
- 结果可缓存 (60s) 减少 subprocess 开销

依赖:
- subprocess 调 hermes CLI
- 路径: src/kid_app/badge_portal.py
"""
from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from src.kid_app.badge_ai_placeholder import _find_hermes, _get_profile

logger = logging.getLogger(__name__)

# Cache TTL (秒). 60s 同 BADGE_URLS cache
_CACHE_TTL = 60
_cache: dict = {"ts": 0.0, "data": None}


# ─── 数据类 ───────────────────────────────────────────────────────

@dataclass
class PortalStatus:
    """Nous Portal + Tool Gateway 状态."""

    auth: str                       # "logged_in" | "not_logged_in" | "unknown"
    image_generation: str           # "via_portal" | "not_configured" | "unknown"
    model: str                      # 当前 model 名字
    provider: str                   # 当前 provider 名字
    raw_output: str                 # 完整 stdout (debug 用)
    ok_for_badge: bool              # 全部绿灯: auth=logged_in AND image=via_portal
    error: str | None               # 失败原因 (ok=True 时 None)
    latency_ms: int                 # 调 hermes 本身耗时
    checked_at: float               # timestamp


# ─── 解析 hermes portal status 输出 ───────────────────────────────

# hermes portal info/status 输出格式 (实测):
#
#   Nous Portal
#   ───────────
#   Auth:    ✓ logged in        (or: ✗ (not set))
#   Portal:  https://portal.nousresearch.com
#   API:     https://inference-api.nousresearch.com/v1
#   Model:   currently xiaomi (switch with `hermes model`)
#
#   Tool Gateway
#   ────────────
#   Web tools            via Nous Portal
#   Image generation     via Nous Portal
#   Video generation     not configured
#   OpenAI TTS           via Nous Portal
#   Browser automation   via Nous Portal
#   Modal execution      local

_AUTH_RE = re.compile(r"Auth:\s+(✓|✗)\s+(\S.*?)(?:\n|$)", re.MULTILINE)
_MODEL_RE = re.compile(r"Model:\s+currently\s+(\S+)", re.IGNORECASE)
_IMG_GEN_RE = re.compile(r"Image generation\s+(via Nous Portal|not configured|.*?)(\n|$)", re.MULTILINE)


def _parse_portal_output(output: str) -> PortalStatus:
    """解析 hermes portal status 的 stdout."""
    auth_status = "unknown"
    auth_match = _AUTH_RE.search(output)
    if auth_match:
        mark, desc = auth_match.group(1), auth_match.group(2)
        if mark == "✓" or "logged" in desc.lower():
            auth_status = "logged_in"
        elif mark == "✗" or "not" in desc.lower():
            auth_status = "not_logged_in"

    model_str = "unknown"
    model_match = _MODEL_RE.search(output)
    if model_match:
        # "currently xiaomi" → provider = "xiaomi"
        model_str = model_match.group(1).strip()

    img_gen_status = "unknown"
    img_match = _IMG_GEN_RE.search(output)
    if img_match:
        desc = img_match.group(1).strip()
        if "via Nous Portal" in desc:
            img_gen_status = "via_portal"
        elif "not configured" in desc:
            img_gen_status = "not_configured"

    # ok_for_badge 综合判断
    ok = (auth_status == "logged_in") and (img_gen_status == "via_portal")
    error = None
    if not ok:
        problems = []
        if auth_status != "logged_in":
            problems.append(f"portal auth: {auth_status}")
        if img_gen_status != "via_portal":
            problems.append(f"image generation: {img_gen_status}")
        error = "; ".join(problems)

    return PortalStatus(
        auth=auth_status,
        image_generation=img_gen_status,
        model=model_str,
        provider=model_str,  # hermes portal output 用 "Model: currently xiaomi" 写法, provider = model
        raw_output=output,
        ok_for_badge=ok,
        error=error,
        latency_ms=0,  # 调用方填
        checked_at=time.time(),
    )


# ─── 公开 API ─────────────────────────────────────────────────────

def check_portal_status(use_cache: bool = True) -> PortalStatus:
    """调 hermes --profile dizical portal status, 解析返回 PortalStatus.

    Args:
        use_cache: True=60s 内复用上次结果, False=强制重查
    """
    # Cache 命中
    now = time.time()
    if use_cache and _cache["ts"] and (now - _cache["ts"]) < _CACHE_TTL:
        return _cache["data"]

    hermes = _find_hermes()
    profile = _get_profile()
    cmd = [hermes, "--profile", profile, "portal", "status"]
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        s = PortalStatus(
            auth="unknown", image_generation="unknown",
            model="", provider="", raw_output="",
            ok_for_badge=False, error="hermes portal status 超时 (10s)",
            latency_ms=int((time.monotonic() - t0) * 1000),
            checked_at=now,
        )
        _cache["ts"] = now
        _cache["data"] = s
        return s
    except FileNotFoundError as e:
        s = PortalStatus(
            auth="unknown", image_generation="unknown",
            model="", provider="", raw_output="",
            ok_for_badge=False, error=f"hermes CLI 找不到: {e}",
            latency_ms=int((time.monotonic() - t0) * 1000),
            checked_at=now,
        )
        _cache["ts"] = now
        _cache["data"] = s
        return s

    latency = int((time.monotonic() - t0) * 1000)

    if result.returncode != 0:
        s = PortalStatus(
            auth="unknown", image_generation="unknown",
            model="", provider="", raw_output=result.stderr or "",
            ok_for_badge=False,
            error=f"hermes portal status rc={result.returncode}: {(result.stderr or '')[:200]}",
            latency_ms=latency, checked_at=now,
        )
    else:
        s = _parse_portal_output(result.stdout or "")
        s.latency_ms = latency

    _cache["ts"] = now
    _cache["data"] = s
    return s


def invalidate_cache() -> None:
    """清 cache, 下次 check_portal_status 强制重查.

    用途:
    - 用户在 /config 手动点 "刷新状态" 时
    - 用户切换 hermes model 后 (自动调一次)
    """
    _cache["ts"] = 0.0
    _cache["data"] = None


def is_ready_for_badge_workflow() -> tuple[bool, str]:
    """便利方法: portal 状态是否适合跑 badge workflow. 返回 (ok, message)."""
    s = check_portal_status()
    if s.ok_for_badge:
        return True, f"Portal 正常 (model={s.model})"
    return False, s.error or "Portal 状态未知"
