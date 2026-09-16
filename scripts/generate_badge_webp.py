#!/usr/bin/env python3
"""
sprint-26091603 P1 资产管线: PNG → WebP 双档生成
- thumbs/: 320×320, quality=80, method=6  (列表墙 / 网格小卡)
- full/  : 1024×1024, quality=90, method=6 (Modal 放大 / 大屏展示)

输入: src/kid_app/static/badges/*.png (顶层, 不下钻子目录)
输出: src/kid_app/static/badges/thumbs/<name>.webp
      src/kid_app/static/badges/full/<name>.webp

技术要点:
- 保留 RGBA 透明通道 (mode='RGBA' 入参, PIL 自动处理)
- 等比缩放: thumbnail() 在 LANCZOS 滤波器下保持宽高比
- method=6 (slows down for better quality, 压缩更慢但更优)
- quality=80 thumbs / 90 full 平衡文件大小与视觉保真
- 跳过非 PNG 扩展名; 跳过子目录 (glob 不递归)
- 输出体积 vs 原始体积的缩减百分比
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

from PIL import Image

# 路径常量
REPO_ROOT = Path(__file__).resolve().parents[1]  # scripts/ → repo root
SRC_DIR = REPO_ROOT / "src" / "kid_app" / "static" / "badges"
THUMBS_DIR = SRC_DIR / "thumbs"
FULL_DIR = SRC_DIR / "full"

# 输出规格
THUMB_SIZE = (320, 320)
THUMB_QUALITY = 80
FULL_SIZE = (1024, 1024)
FULL_QUALITY = 90
WEBP_METHOD = 6  # PIL.Image.save(): 0=fast, 6=slowest/best


def is_input_png(p: Path) -> bool:
    """只收顶层 *.png, 跳过子目录与其它扩展名。"""
    return p.is_file() and p.suffix.lower() == ".png" and p.parent == SRC_DIR


def iter_inputs() -> Iterable[Path]:
    """按文件名排序, 输出可重现。"""
    return sorted(p for p in SRC_DIR.iterdir() if is_input_png(p))


def convert_one(src: Path, dst_dir: Path, target_size: tuple[int, int], quality: int) -> tuple[Path, int, int]:
    """将单张 PNG 转为 WebP 写入 dst_dir/<stem>.webp。

    返回 (输出路径, 输出字节数, 原始字节数) 供聚合统计。
    """
    src_bytes = src.stat().st_size
    with Image.open(src) as im:
        # 保留透明: PNG 含 alpha 时保留, 否则落 RGB
        # thumbnail() 在 LANCZOS 下保持宽高比, 不放大 (若原图已小于目标则保留原尺寸)
        im.thumbnail(target_size, resample=Image.Resampling.LANCZOS)
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        out_path = dst_dir / (src.stem + ".webp")
        im.save(out_path, "WEBP", quality=quality, method=WEBP_METHOD, lossless=False)
    return out_path, out_path.stat().st_size, src_bytes


def human_bytes(n: int) -> str:
    units = ("B", "KB", "MB", "GB")
    f = float(n)
    for u in units:
        if f < 1024.0:
            return f"{f:.2f} {u}"
        f /= 1024.0
    return f"{f:.2f} TB"


def pct(orig: int, new: int) -> str:
    if orig == 0:
        return "n/a"
    delta = (orig - new) / orig * 100.0
    return f"{delta:+.1f}%"


def main() -> int:
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    FULL_DIR.mkdir(parents=True, exist_ok=True)

    inputs = list(iter_inputs())
    if not inputs:
        print(f"[!] 未找到 PNG: {SRC_DIR}", file=sys.stderr)
        return 1

    print(f"[i] 输入目录: {SRC_DIR}")
    print(f"[i] 输入文件数: {len(inputs)}")
    print(f"[i] thumbs: {THUMBS_DIR}  ({THUMB_SIZE[0]}×{THUMB_SIZE[1]}, q={THUMB_QUALITY})")
    print(f"[i] full  : {FULL_DIR}    ({FULL_SIZE[0]}×{FULL_SIZE[1]}, q={FULL_QUALITY})")
    print()

    thumb_count = 0
    full_count = 0
    orig_total = 0
    thumb_total = 0
    full_total = 0
    errors: list[tuple[Path, str]] = []

    for src in inputs:
        try:
            _, tb, ob1 = convert_one(src, THUMBS_DIR, THUMB_SIZE, THUMB_QUALITY)
            _, fb, ob2 = convert_one(src, FULL_DIR, FULL_SIZE, FULL_QUALITY)
            assert ob1 == ob2, "原始字节两次读取不一致"
            thumb_count += 1
            full_count += 1
            orig_total += ob1
            thumb_total += tb
            full_total += fb
            print(f"  ✓ {src.name:32s}  {human_bytes(ob1):>9s} → thumb {human_bytes(tb):>9s}  full {human_bytes(fb):>9s}")
        except Exception as e:  # noqa: BLE001 (单文件失败不阻塞整体)
            errors.append((src, repr(e)))
            print(f"  ✗ {src.name}: {e}", file=sys.stderr)

    print()
    print("=" * 78)
    print("汇总")
    print("=" * 78)
    print(f"生成文件数:    thumbs={thumb_count}  full={full_count}  total={thumb_count + full_count}")
    print(f"原始 PNG 体积: {human_bytes(orig_total)}  ({orig_total:,} B)")
    print(f"thumbs 体积:   {human_bytes(thumb_total)}  ({thumb_total:,} B)  {pct(orig_total, thumb_total)} vs PNG")
    print(f"full   体积:   {human_bytes(full_total)}    ({full_total:,} B)  {pct(orig_total, full_total)} vs PNG")
    print(f"两档合计:      {human_bytes(thumb_total + full_total)}  {pct(orig_total * 2, thumb_total + full_total)} vs 2×PNG")
    if errors:
        print()
        print(f"[!] {len(errors)} 个文件失败:")
        for p, in_e in errors:
            print(f"  {p.name}: {in_e}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())