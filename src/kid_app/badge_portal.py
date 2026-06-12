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


# ─── 解析 hermes portal status 输出 ─────────────────────────────
# hermes portal info/status 输出格式 (实测):
#
#   Nous Portal
#   ───────────
#   Auth:    ✓ logged in        (or: ✗ (not set)  or: not logged in)
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

# 兼容 3 种 Auth 格式 (V1.1 改进, 用户 2026-06-12 OUT-OF-BAND):
#  - "Auth: ✓ logged in"        (已登录, 跑过 hermes setup --portal 的 profile)
#  - "Auth: ✗ (not set)"         (没 setup 过 portal)
#  - "Auth:    not logged in"    (setup 过但 OAuth token 过期, 常见场景)
_AUTH_RE = re.compile(
    r"Auth:\s+(?:(✓)\s+(\S.*?)|(✗)\s+(\S.*?)|(\S.*?))\s*$",
    re.MULTILINE,
)
_MODEL_RE = re.compile(r"Model:\s+currently\s+(\S+)", re.IGNORECASE)
_IMG_GEN_RE = re.compile(r"Image generation\s+(via Nous Portal|not configured|.*?)(\n|$)", re.MULTILINE)


def _parse_auth_value(mark1: str | None, desc1: str | None, mark2: str | None, desc2: str | None) -> str:
    """从 _AUTH_RE 匹配里解析 auth 状态.

    兼容 hermes 3 种输出格式:
    - 格式 A: "Auth: ✓ logged in"        (mark1='✓', desc1='logged in')
    - 格式 B: "Auth: ✗ (not set)"         (mark2='✗', desc2='(not set)')
    - 格式 C: "Auth:    not logged in"    (mark1=mark2=None, 全 None 走 fallback)

    返回 "logged_in" / "not_logged_in" / "unknown"
    """
    if mark1 == "✓" or "logged" in (desc1 or "").lower():
        return "logged_in"
    if mark2 == "✗" or "not" in (desc2 or "").lower():
        return "not_logged_in"
    return "unknown"


def _parse_portal_output(output: str) -> PortalStatus:
    """解析 hermes portal status 的 stdout."""
    auth_status = "unknown"
    auth_match = _AUTH_RE.search(output)
    if auth_match:
        # 5 个 group: (mark1, desc1, mark2, desc2, desc3)
        # 格式 A: "Auth: ✓ logged in"    -> mark1='✓', desc1='logged in'
        # 格式 B: "Auth: ✗ (not set)"     -> mark2='✗', desc2='(not set)'
        # 格式 C: "Auth:    not logged in" -> 全 None except desc3
        mark1 = auth_match.group(1)
        desc1 = auth_match.group(2)
        mark2 = auth_match.group(3)
        desc2 = auth_match.group(4)
        desc3 = auth_match.group(5)
        # 格式 A/B 走 _parse_auth_value
        auth_status = _parse_auth_value(mark1, desc1, mark2, desc2)
        # 格式 C 单独处理 (mark1=mark2=None, desc1=desc2=None, desc3 有值)
        if desc3 and not desc1 and not desc2:
            d = desc3.lower()
            if "logged" in d and "not" not in d:
                auth_status = "logged_in"
            elif "not" in d:
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


# ─── 解析 hermes tools list 输出 ──────────────────────────────────
# hermes tools list 报 built-in toolsets 启用状态 (subprocess 友好, 跟 tools
# 交互 UI 不同). 关键字段: image_gen 启用 = badge workflow 可跑.
# 输出格式 (实测):
#   Built-in toolsets (cli):
#     ✓ enabled  web  🔍 Web Search & Scraping
#     ✗ disabled  video  🎬 Video Analysis
#     ✓ enabled  image_gen  🎨 Image Generation
_TOOLS_LIST_LINE_RE = re.compile(
    r"^\s*(✓|✗)\s+(enabled|disabled)\s+(\S+)\s+",  # 状态 + enable/disable + tool 名
    re.MULTILINE,
)


def _parse_tools_list_output(output: str) -> dict:
    """解析 hermes tools list 输出, 提取 image_gen 状态."""
    result = {
        "image_gen_enabled": False,
        "web_enabled": False,
        "tts_enabled": False,
        "browser_enabled": False,
        "raw_tools_count": 0,
    }
    for match in _TOOLS_LIST_LINE_RE.finditer(output):
        mark, status, tool_name = match.group(1), match.group(2), match.group(3)
        result["raw_tools_count"] += 1
        if mark == "✓" and status == "enabled":
            if tool_name == "image_gen":
                result["image_gen_enabled"] = True
            elif tool_name == "web":
                result["web_enabled"] = True
            elif tool_name == "tts":
                result["tts_enabled"] = True
            elif tool_name == "browser":
                result["browser_enabled"] = True
    return result


# ─── 公开 API ─────────────────────────────────────────────────────

def check_portal_status(use_cache: bool = True) -> PortalStatus:
    """调 hermes --profile dizical tools list, 解析返回 PortalStatus.

    跟 V1 PR-A 不同: V1 用 `portal info`/`status` 报 OAuth 状态. 但 hermes 当前
    跨 subprocess OAuth 不可靠 (subprocess 永远报 not_logged_in, 即使 OAuth 还在).
    V1.1 改用 `tools list` 看 image_gen 启用 (subprocess 友好, OAuth 无关).

    注意: 真正 Tool Gateway 路由 (via Nous Portal 还是直连) 只能看交互式
    `hermes tools` UI, 不在端点报告范围. 端点只报 "image_gen 可用".
    """
    # Cache 命中
    now = time.time()
    if use_cache and _cache["ts"] and (now - _cache["ts"]) < _CACHE_TTL:
        return _cache["data"]

    hermes = _find_hermes()
    profile = _get_profile()
    cmd = [hermes, "--profile", profile, "tools", "list"]
    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
    except subprocess.TimeoutExpired:
        s = PortalStatus(
            auth="unknown", image_generation="unknown",
            model="", provider="", raw_output="",
            ok_for_badge=False, error="hermes tools list 超时 (10s)",
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
            error=f"hermes tools list rc={result.returncode}: {(result.stderr or '')[:200]}",
            latency_ms=latency, checked_at=now,
        )
    else:
        # 解析 tools list, 拿 image_gen/web/tts/browser 状态
        parsed = _parse_tools_list_output(result.stdout or "")
        # image_gen 启用 = ok_for_badge (其他字段也用作参考)
        s = PortalStatus(
            auth=("logged_in" if parsed["image_gen_enabled"] else "not_logged_in"),
            image_generation=("via_portal" if parsed["image_gen_enabled"] else "not_configured"),
            model=parsed.get("image_gen_enabled") and "via hermes tools list (请用 hermes tools 交互 UI 确认 Tool Gateway 路由)" or "",
            provider="hermes",
            raw_output=result.stdout or "",
            ok_for_badge=parsed["image_gen_enabled"],
            error=None if parsed["image_gen_enabled"] else "image_gen 工具未启用 (跑 hermes setup 或 hermes tools 启用)",
            latency_ms=latency,
            checked_at=now,
        )

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


# ─── V1.1 改进 (用户 2026-06-12 OUT-OF-BAND 拍板) ────────────────────
# 用户拍板: "只查 hermes portal status 和 dizical portal status 就行"
# 11 个 KNOWN_PROFILES 全部查太冗余, 普通用户只关心这 2 个:
#   1. hermes CLI 默认 (没 --profile 走 default)
#   2. dizical (本项目用的 profile, DIZICAL_HERMES_PROFILE env)
# 这 2 个查到 ok = portal 全局 OK; 任何 1 个失败 = 告诉用户哪个断了


def _check_one_profile_portal(profile: str | None, timeout: int = 8) -> dict:
    """查单个 profile 的 Tool Gateway 状态 (V1.1 改用 `tools list` 替代 `portal info`).

    Args:
        profile: profile 名. None = 调 hermes CLI 默认 (没 --profile)
        timeout: 单次 subprocess 超时

    Returns:
        {
            "profile": str,        # 显式 "default" 表示 hermes CLI 默认 (没 --profile)
            "auth": "logged_in" | "not_logged_in" | "unknown",
            "image_generation": "via_portal" | "not_configured" | "unknown",
            "model": str,
            "ok_for_badge": bool,
            "error": str | None,
            "latency_ms": int,
        }
    """
    hermes = _find_hermes()
    # profile=None 走 hermes CLI 默认 (--profile flag 不加)
    if profile is None:
        cmd = [hermes, "tools", "list"]
        display_name = "default"
    else:
        cmd = [hermes, "--profile", profile, "tools", "list"]
        display_name = profile

    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "profile": display_name, "auth": "unknown", "image_generation": "unknown",
            "model": "", "ok_for_badge": False,
            "error": f"hermes tools list 超时 ({timeout}s)",
            "latency_ms": int((time.monotonic() - t0) * 1000),
        }
    except FileNotFoundError as e:
        return {
            "profile": display_name, "auth": "unknown", "image_generation": "unknown",
            "model": "", "ok_for_badge": False,
            "error": f"hermes CLI 找不到: {e}",
            "latency_ms": int((time.monotonic() - t0) * 1000),
        }
    if result.returncode != 0:
        return {
            "profile": display_name, "auth": "unknown", "image_generation": "unknown",
            "model": "", "ok_for_badge": False,
            "error": f"hermes tools list rc={result.returncode}: {(result.stderr or '')[:200]}",
            "latency_ms": int((time.monotonic() - t0) * 1000),
        }
    parsed = _parse_tools_list_output(result.stdout or "")
    return {
        "profile": display_name,
        "auth": "logged_in" if parsed["image_gen_enabled"] else "not_logged_in",
        "image_generation": "via_portal" if parsed["image_gen_enabled"] else "not_configured",
        "model": "hermes",
        "ok_for_badge": parsed["image_gen_enabled"],
        "error": None if parsed["image_gen_enabled"] else "image_gen 未启用 (请跑 hermes tools 启用)",
        "latency_ms": int((time.monotonic() - t0) * 1000),
    }


def check_two_profiles_portal() -> list[dict]:
    """查 hermes CLI 默认 + dizical profile 2 个 portal 状态 (并发).

    用户 2026-06-12 OUT-OF-BAND 拍板: "只查 hermes portal status 和 dizical portal status"
    理由: 普通用户只关心这 2 个, 11 个 KNOWN_PROFILES 全部查太冗余.

    Returns:
        list[dict] 长度 2, 每条同 _check_one_profile_portal
        元素 0 = hermes CLI 默认 (profile_name="default")
        元素 1 = dizical profile (profile_name="dizical" 或 DIZICAL_HERMES_PROFILE env)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    # dizical profile 跟 _get_profile() 同步 (用 env, 默认 "dizical")
    dizical_profile = _get_profile()
    targets = [
        (None, "default"),                # hermes CLI 默认
        (dizical_profile, dizical_profile),  # dizical (本项目用)
    ]
    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {ex.submit(_check_one_profile_portal, prof_arg): display
                   for prof_arg, display in targets}
        results: list[dict] = []
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({
                    "profile": futures[fut], "auth": "unknown",
                    "image_generation": "unknown", "model": "",
                    "ok_for_badge": False, "error": f"concurrent: {e}",
                    "latency_ms": 0,
                })
    # 按 display 名字固定顺序 (default, dizical_profile)
    results.sort(key=lambda r: 0 if r["profile"] == "default" else 1)
    return results
