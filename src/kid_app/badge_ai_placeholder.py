"""
Badge AI placeholder 草拟 — 薄壳调用 dizical hermes profile.

设计 (用户 2026-06-12 拍板, moni 模式):
- **不直接持 LLM key**. 走 hermes CLI, hermes 持所有 provider 的 key
- **dizical profile 隔离**: subprocess 调 `hermes chat --profile dizical`, 跟 coder/moni 等 profile 互不污染记忆
- **DIZICAL_HERMES_PROFILE env**: 默认 "dizical", 可覆盖 (跟 moni 的 MONI_HERMES_PROFILE 同模式)
- **provider/model 由 hermes 配置**: 调 `hermes chat` 不传 --provider --model, 让 hermes 读 dizical profile 的 config.yaml
- **fail-loud**: hermes 进程失败/超时/PROFILE_NOT_FOUND 抛明确错误, 不静默 fallback
- **fallback 占位**: 仅 DeepSeek API 在 hermes 内部失败时, hermes 自己返回错误, 我们透传
- **.env**: dizical 项目 .env 只需包含 DIZICAL_HERMES_PROFILE=*** (其它 key 都在 hermes ~/.hermes/profiles/dizical/.env)

依赖:
- subprocess 调 hermes CLI (PATH 上要有 hermes, macOS GUI app 同名问题: 走绝对路径)
- 路径: src/kid_app/badge_ai_placeholder.py

历史:
- 2026-06-12 V1 PR-A 创建
- 2026-06-12 用户拍板改方向: 走 hermes dizical profile, 不再直连 DeepSeek
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ─── 配置 ──────────────────────────────────────────────────────────

# hermes CLI 绝对路径 (避免 macOS GUI app 启 uvicorn 时 PATH 不含 Homebrew)
# 跟 AGENTS.md 启动坑点"macOS GUI app 启动 uvicorn 时 PATH 不含 Homebrew" 同一类问题
# 默认 ~/.local/bin/hermes, 可通过 HERMES_PATH env 覆盖
_HERMES_PATH = Path(os.environ.get("HERMES_PATH", str(Path.home() / ".local" / "bin" / "hermes")))
# Profile 名从环境变量读, 默认 "dizical"
_DEFAULT_PROFILE = "dizical"

# 单次 LLM 调用超时 (秒). DeepSeek 慢响应通常 10-30s, 给 60s 缓冲
_LLM_TIMEOUT = 60

# prompt 中文化 (跟 moni 类似, 走英文 LLM)
_PROMPT_TPL = (
    "You are writing an English image description for a chibi enamel pin badge "
    "in a child's dizi (bamboo flute) practice app. The character is a black-haired "
    "chibi girl playing a bamboo flute. Visual style: emoji-adjacent 3D enamel pin, "
    "polished gold borders, glossy enamel fills, vibrant colors, friendly silhouette, "
    "white background.\n\n"
    "Given the Chinese badge name and reference story below, output a 1-2 sentence "
    "English description (30-120 words) for the badge image. Focus on: character "
    "doing something story-related, key visual props, optional dramatic/cute element.\n\n"
    "Output ONLY the English description. No preamble, no explanation, no quotes.\n\n"
    "Badge name (Chinese): {badge_name}\n"
    "Reference story (Chinese, may be long典故): {zh_story}\n"
)


# ─── 工具函数 ─────────────────────────────────────────────────────

def _find_hermes() -> str:
    """找 hermes CLI 绝对路径. fail-loud.

    顺序:
    1. 硬编码 ~/.local/bin/hermes (我们已确认存在)
    2. shutil.which("hermes") 兜底
    3. 都没找到 → 报错带明确指引
    """
    if _HERMES_PATH.exists():
        return str(_HERMES_PATH)
    which = shutil.which("hermes")
    if which:
        return which
    raise RuntimeError(
        "hermes CLI 找不到. V1 需要 hermes 调用 LLM. 安装方法: "
        "https://hermes-agent.nousresearch.com/docs  (或 `pip install hermes-agent`)"
    )


def _get_profile() -> str:
    """从环境变量读 hermes profile name."""
    return os.environ.get("DIZICAL_HERMES_PROFILE", _DEFAULT_PROFILE).strip() or _DEFAULT_PROFILE


# ─── 公开 API ─────────────────────────────────────────────────────

def draft_placeholder(zh_story: str, badge_name: str) -> str:
    """调 dizical hermes profile 生成英文 placeholder.

    Args:
        zh_story: 中文典故 (来自前端, 任意长度)
        badge_name: 中文 badge 名称 (例如 "幸运六一节")

    Returns:
        英文 placeholder 字符串 (30-200 词)

    Raises:
        ValueError: zh_story / badge_name 缺失或太短
        RuntimeError: hermes 进程失败/超时/PROFILE_NOT_FOUND
    """
    # ── 校验输入 ──
    if not zh_story or len(zh_story.strip()) < 5:
        raise ValueError("zh_story 至少 5 字符")
    if not badge_name or len(badge_name.strip()) < 1:
        raise ValueError("badge_name 不能为空")

    hermes = _find_hermes()
    profile = _get_profile()
    prompt = _PROMPT_TPL.format(
        badge_name=badge_name.strip(),
        zh_story=zh_story.strip(),
    )

    # ── 构造命令 (list argv, 安全, 不走 shell=True) ──
    # 跟 moni/moni/llm/client.py:73-78 一致, 但去掉 --provider --model
    # (让 hermes 读 dizical profile config.yaml 的 model.default)
    cmd = [
        hermes, "chat",
        "-q", prompt,
        "--profile", profile,
        "-Q",  # no-interactive quick mode
        "--yolo",  # 自动确认 (non-interactive 必须)
    ]

    logger.info(f"调 hermes 生成 placeholder, profile={profile}, prompt_len={len(prompt)}")

    # ── 调子进程 ──
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_LLM_TIMEOUT,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"hermes chat 超时 ({_LLM_TIMEOUT}s, profile={profile}). "
            f"网络慢或模型 hang. 重试或换 provider."
        ) from e
    except FileNotFoundError as e:
        raise RuntimeError(
            f"hermes CLI 不在 PATH: {hermes}. 重新装一下."
        ) from e

    if result.returncode != 0:
        err = (result.stderr or "").strip()[:500]
        # 特殊: profile not found
        if "profile" in err.lower() and "not found" in err.lower():
            raise RuntimeError(
                f"hermes profile '{profile}' 不存在. "
                f"需要: `hermes profile create {profile} --clone-from moni` "
                f"(详见 tech-spec §0.4)"
            ) from RuntimeError(err)
        raise RuntimeError(
            f"hermes chat 失败 (rc={result.returncode}, profile={profile}): {err}"
        )

    # ── 解析 stdout ──
    # hermes chat -Q 模式输出: 第一行 "session_id: <id>", 之后是 content
    lines = (result.stdout or "").splitlines()
    content_lines = [ln for ln in lines if not ln.startswith("session_id:")]
    reply = "\n".join(content_lines).strip()

    if not reply:
        raise RuntimeError(f"hermes 返回空. stdout 前 200 字符: {result.stdout[:200]}")

    # ── 清洗 ──
    placeholder = reply.strip()
    # 偶尔 LLM 会包 ``` 包裹
    placeholder = re.sub(r"^```(?:[a-z]*\n)?", "", placeholder)
    placeholder = re.sub(r"\n?```$", "", placeholder)
    placeholder = placeholder.strip().strip('"').strip("'")

    # ── 长度 sanity check ──
    if len(placeholder) < 10:
        raise RuntimeError(
            f"hermes 返回的 placeholder 太短 ({len(placeholder)} 字符): {placeholder!r}"
        )

    return placeholder


# ─── 健康检查 (测试用) ─────────────────────────────────────────────

def is_configured() -> bool:
    """检查 hermes CLI + profile 是否可用. 用于健康检查端点.

    不实际调 LLM (避免烧 credits), 只检查:
    1. hermes CLI 在 PATH
    2. profile 存在 (用 `hermes profile show <name>` 检查, 5s 内超时)
    """
    try:
        _find_hermes()
    except RuntimeError:
        return False

    profile = _get_profile()
    try:
        result = subprocess.run(
            [_find_hermes(), "profile", "show", profile],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False
