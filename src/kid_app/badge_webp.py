"""badge PNG → WebP 双档派生 (运行时模块 —— 必须随 src/ 进镜像)。

为什么放在 `src/kid_app/` 而不是 `scripts/` (2026-10-17 线上事故):
生产 CloudRun 走 tcb 上传 ZIP, `.tcbignore` 里 `scripts/` 整目录被排除 ——
于是 `scripts/generate_badge_webp.py` 不在容器的 `/app` 里。commit 走到 webp 派生即抛
`[Errno 2] No such file or directory: '/app/scripts/generate_badge_webp.py'`,
而 commit 是 Storage First 全链: 派生失败 → 图与 webp 都不落 → 三表不入库, 徽章永远落不了地。

**规则: 被运行时代码 import 的模块一律不许放 `scripts/`** (scripts/ 只放 CLI / 运维入口, 不进镜像)。
本模块是 badge commit / replace-image 的运行时依赖, 因此必须住在 `src/kid_app/` 下。

规格 (与 sprint-26091603 资产管线一致):
- thumbs/: 320×320, quality=80, method=6  (列表墙 / 网格小卡)
- full/  : 1024×1024, quality=90, method=6 (Modal 放大 / 大屏展示)
- 保留 RGBA 透明通道; 等比缩进不放大小图; method=6 = 压缩慢但质量最好
"""
from __future__ import annotations

import io

from PIL import Image

# 输出规格 (唯一真源 —— scripts/generate_badge_webp.py 从这里 import, 不要各写一份)
THUMB_SIZE = (320, 320)
THUMB_QUALITY = 80
FULL_SIZE = (1024, 1024)
FULL_QUALITY = 90
WEBP_METHOD = 6  # PIL.Image.save(): 0=fast, 6=slowest/best


def encode_webp(im: Image.Image, target_size: tuple[int, int], quality: int) -> bytes:
    """等比缩进 target_size (不放大) 后编码 WebP. 不改调用方手里的那张图."""
    frame = im.copy()
    # thumbnail() 在 LANCZOS 下保持宽高比, 不放大 (若原图已小于目标则保留原尺寸)
    frame.thumbnail(target_size, resample=Image.Resampling.LANCZOS)
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")
    buf = io.BytesIO()
    buf.name = "badge.webp"  # Pillow 靠扩展名选 WEBP encoder
    frame.save(buf, "WEBP", quality=quality, method=WEBP_METHOD, lossless=False)
    return buf.getvalue()


def webp_variants(png_bytes: bytes) -> tuple[bytes, bytes]:
    """从 PNG 字节派生两档 WebP, 不写盘.

    返回 (thumbs, full): 320×320 q80 / 1024×1024 q90, method=6, RGBA.
    commit / replace-image 用这一份, 不跑 CLI 的全目录批处理.
    """
    with Image.open(io.BytesIO(png_bytes)) as im:
        return (
            encode_webp(im, THUMB_SIZE, THUMB_QUALITY),
            encode_webp(im, FULL_SIZE, FULL_QUALITY),
        )
