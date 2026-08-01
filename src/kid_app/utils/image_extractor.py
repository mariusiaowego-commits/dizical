"""Stage report image 解析纯函数 (sprint-26080103 v2).

从 hermes subprocess stdout 提取图片 URL/路径.

支持 3 种输出格式:
1. "MEDIA:/path/to/file.png" (最常见, hermes chat CLI 标准)
2. "URL: https://...png" 或 "**图片已生成** URL: https://...png" (markdown 风格)
3. "https://...png" (裸 URL)
"""
import os
import re
from typing import Optional


# Pattern 1: MEDIA:/path 或 MEDIA: URL (legacy 格式)
_MEDIA_PATTERN = re.compile(r"MEDIA:\s*(\S+)")

# Pattern 2: URL: http(s)://... 任意扩展名 (markdown 格式)
_URL_LABEL_PATTERN = re.compile(r"URL:\s*(https?://\S+)", re.IGNORECASE)

# Pattern 3: 裸 URL (一行整个是 URL, 含 .png/.jpg/.webp/.jpeg)
_BARE_URL_PATTERN = re.compile(r"^https?://\S+\.(?:png|jpg|jpeg|webp)", re.IGNORECASE)

# Pattern 4: 本地路径
_LOCAL_PATH_PATTERN = re.compile(r"^/[\w/.-]+\.(?:png|jpg|jpeg|webp)$", re.IGNORECASE)


def extract_image_source(output: str) -> Optional[str]:
    """从 hermes stdout 提取图片源 (URL 或本地路径).

    优先级 (按 hermes 实际输出最稳的):
    1. MEDIA: 前缀 (legacy, hermes chat CLI 标准)
    2. URL: 标签 (markdown 风格, gemini 实际输出格式)
    3. 裸 URL (含图片扩展名, 一行整个是 URL)
    4. 本地绝对路径 (含图片扩展名且存在)

    Returns:
        URL 字符串 (http://, https://) 或本地绝对路径, 找不到返 None.
    """
    # 每行同时跑 4 个 pattern, 按优先级选 (1 > 2 > 3 > 4)
    # 选第一个非 None 匹配
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        # 1. MEDIA: 前缀
        m = _MEDIA_PATTERN.search(line)
        if m:
            cand = m.group(1)
            if cand.startswith("http://") or cand.startswith("https://"):
                return cand
            if os.path.isabs(cand) and os.path.exists(cand):
                return cand
            # MEDIA: 但不是 URL 也不是有效路径, 跳过整行
            continue

        # 2. URL: 标签
        m = _URL_LABEL_PATTERN.search(line)
        if m:
            url = m.group(1).rstrip(".,;:)")
            if url.startswith("http://") or url.startswith("https://"):
                return url
            continue

        # 3. 裸 URL
        m = _BARE_URL_PATTERN.search(line)
        if m:
            url = m.group(0).rstrip(".,;:)")
            return url

        # 4. 本地绝对路径
        m = _LOCAL_PATH_PATTERN.search(line)
        if m:
            cand = m.group(0)
            if os.path.exists(cand):
                return cand

    return None
