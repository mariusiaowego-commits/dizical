"""badge alpha 破损审计 (只读)

判据:
  1. uniq_alpha == 2  → 硬二值掩膜 (无抗锯齿, 边缘必然锯齿/灰边)
  2. interior_removed = 轮廓内 alpha==0 的像素 (轮廓 = binary_fill_holes(alpha>0))
     → 抠图把画内像素当背景割掉了 = 真正的"破洞"
  3. 内部破洞像素的 RGB 是否被改写 (PIL 阈值路径保留 RGB, 只改 alpha)

用法: python3 scripts/audit_badge_alpha.py
"""
from __future__ import annotations

import glob
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

BADGE_DIR = "src/kid_app/static/badges"


def audit(path: str) -> dict:
    im = Image.open(path).convert("RGBA")
    a = np.array(im)
    al = a[:, :, 3]
    sil = ndimage.binary_fill_holes(al > 0)
    interior = sil & (al == 0)
    n_int = int(interior.sum())
    sil_px = int(sil.sum())
    lbl, k = ndimage.label(interior)
    rgb = a[:, :, :3][interior]
    return {
        "file": os.path.basename(path),
        "size": im.size[0],
        "uniq_alpha": int(len(np.unique(al))),
        "partial_pct": round(float(((al > 0) & (al < 255)).mean()) * 100, 2),
        "sil_px": sil_px,
        "interior_px": n_int,
        "interior_pct": round(100.0 * n_int / max(1, sil_px), 2),
        "interior_comps": int(k),
        "flat_rgb": bool(n_int and rgb.min() == rgb.max()),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=BADGE_DIR, help="要审计的目录 (默认 src/kid_app/static/badges)")
    ap.add_argument("--ext", default="png", help="扩展名 (默认 png; webp 档用 webp)")
    ap.add_argument("--only", default="", help="只审计文件名含该子串的图")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.dir, f"*.{args.ext}")))
    if args.only:
        paths = [p for p in paths if args.only in os.path.basename(p)]

    rows = []
    for p in paths:
        try:
            rows.append(audit(p))
        except Exception as exc:  # 坏文件单独列出, 不中断
            rows.append({"file": os.path.basename(p), "err": str(exc)})

    ok = [r for r in rows if "err" not in r]
    ok.sort(key=lambda r: -r["interior_pct"])

    print(f"{'file':52s} {'uniqA':>5s} {'part%':>6s} {'holes%':>7s} {'holes_px':>9s} {'comps':>6s} flatRGB")
    for r in ok:
        print(
            f"{r['file']:52s} {r['uniq_alpha']:5d} {r['partial_pct']:6.2f} "
            f"{r['interior_pct']:7.2f} {r['interior_px']:9d} {r['interior_comps']:6d} {r['flat_rgb']}"
        )

    binary = [r for r in ok if r["uniq_alpha"] == 2]
    holed = [r for r in ok if r["interior_pct"] >= 1.0]
    clean = [r for r in ok if r["interior_pct"] < 0.2 and r["uniq_alpha"] > 2]
    print()
    print(f"总数 {len(ok)} (坏文件 {len(rows) - len(ok)})")
    print(f"硬二值掩膜 (无抗锯齿): {len(binary)}")
    print(f"破洞 >= 1.0% 画面: {len(holed)}")
    print(f"干净 (软边 + 破洞 <0.2%): {len(clean)}")
    print()
    print("破洞 TOP 15:")
    for r in ok[:15]:
        print(f"  {r['interior_pct']:6.2f}%  {r['interior_px']:7d}px  {r['file']}")
    print()
    print("硬二值掩膜清单:")
    for r in binary:
        print(f"  holes={r['interior_pct']:6.2f}%  {r['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
