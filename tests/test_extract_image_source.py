"""Stage report image 解析纯函数 (sprint-26080103 v2).

从 hermes subprocess stdout 提取图片 URL/路径.
"""
import os
import sys
from pathlib import Path

# 允许 standalone 运行 (pytest 不需要 src package)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.kid_app.utils.image_extractor import extract_image_source


import pytest


def test_extract_media_prefix():
    """MEDIA: 前缀, 后面跟本地路径 (文件不存在返 None)."""
    output = "MEDIA:/tmp/test.png\nsome other line"
    assert extract_image_source(output) is None


def test_extract_media_prefix_with_url():
    """MEDIA: 后面直接是 http URL."""
    output = "MEDIA:https://v3b.fal.media/files/x.png"
    assert extract_image_source(output) == "https://v3b.fal.media/files/x.png"


def test_extract_url_label_markdown():
    """markdown 风格: **图片已生成** URL: https://..."""
    output = (
        "**图片已生成 ✅**\n"
        "URL: https://v3b.fal.media/files/b/0aa4a54a/MNO1CKdTz2FerQXOSbEr6_4NrrBCg3.png\n"
        "内容概要 (按 prompt 要求)\n"
        "- 横版信息图\n"
    )
    assert extract_image_source(output) == "https://v3b.fal.media/files/b/0aa4a54a/MNO1CKdTz2FerQXOSbEr6_4NrrBCg3.png"


def test_extract_url_label_with_trailing_punct():
    """URL 末尾标点要 strip."""
    output = "URL: https://example.com/x.png."
    assert extract_image_source(output) == "https://example.com/x.png"


def test_extract_bare_url():
    """裸 URL 行."""
    output = "https://v3b.fal.media/files/x.png"
    assert extract_image_source(output) == "https://v3b.fal.media/files/x.png"


def test_extract_local_path_exists(tmp_path):
    """MEDIA: + 真实本地文件."""
    f = tmp_path / "test.png"
    f.write_bytes(b"\x89PNG\r\n")
    output = f"MEDIA:{f}"
    assert extract_image_source(output) == str(f)


def test_extract_priority_url_label_in_same_line():
    """同一行 URL: 标签 + 裸 URL pattern 也命中, 选 URL: 标签 (同 line 高优先级)."""
    output = "some noise URL: https://right.com/y.png more noise"
    assert extract_image_source(output) == "https://right.com/y.png"


def test_extract_priority_first_line_wins():
    """first-match-wins 跨行 (语义 1). 真实 hermes 一次输出只 1 个 URL."""
    output = "https://wrong.com/x.png\nURL: https://right.com/y.png"
    # line 1 整行是 URL → pattern 3 命中
    assert extract_image_source(output) == "https://wrong.com/x.png"


def test_extract_empty():
    """空输出返 None."""
    assert extract_image_source("") is None


def test_extract_no_match():
    """没匹配返 None."""
    output = "just some text\nno url here\n更多中文"
    assert extract_image_source(output) is None


def test_extract_url_with_jpg():
    """jpg 扩展名也支持."""
    output = "URL: https://example.com/x.jpg"
    assert extract_image_source(output) == "https://example.com/x.jpg"


def test_extract_url_with_webp():
    """webp 扩展名也支持."""
    output = "URL: https://example.com/x.webp"
    assert extract_image_source(output) == "https://example.com/x.webp"


def test_extract_url_lowercase_http():
    """小写 http 也支持 (虽然罕见)."""
    output = "URL: http://example.com/x.png"
    assert extract_image_source(output) == "http://example.com/x.png"


def test_extract_url_with_query_string():
    """URL 带 query string."""
    output = "URL: https://example.com/x.png?token=abc&t=123"
    assert extract_image_source(output) == "https://example.com/x.png?token=abc&t=123"
