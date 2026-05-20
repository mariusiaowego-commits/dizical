#!/usr/bin/env python3
"""
去白底脚本：将 PNG 白背景 → 透明
用法: python3 src/deband.py [glob_pattern]
"""
from PIL import Image, ImageFile
import os, glob, sys

ImageFile.LOAD_TRUNCATED_IMAGES = True

BADGE_DIR = "/Users/mt16/dev/dizical/src/kid_app/static/badges"

def deband(src):
    im = Image.open(src).convert("RGBA")
    pixels = im.load()
    changed = 0
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = pixels[x, y]
            if r > 220 and g > 220 and b > 220 and a > 200:
                pixels[x, y] = (0, 0, 0, 0)
                changed += 1
                continue
            if r > 200 and g > 200 and b > 200:
                mx, mn = max(r, g, b), min(r, g, b)
                if mx - mn < 30:
                    pixels[x, y] = (0, 0, 0, 0)
                    changed += 1
    im.save(src)
    total = im.width * im.height
    pct = changed * 100 // total
    print(f"  {os.path.basename(src)}: {changed}/{total} px ({pct}%) transparent")
    return changed

def main():
    if len(sys.argv) > 1:
        patterns = sys.argv[1:]
    else:
        patterns = ["early_bird_A.png", "early_bird_B_full.png", "early_bird_C_v2_full.png"]

    for pat in patterns:
        path = os.path.join(BADGE_DIR, pat)
        if os.path.isdir(path):
            for f in os.listdir(path):
                if f.endswith(".png"):
                    deband(os.path.join(path, f))
        elif "*" in pat or "?" in pat:
            for f in glob.glob(path):
                deband(f)
        elif os.path.exists(path):
            deband(path)
        else:
            print(f"  [SKIP] {pat} not found")

    print("All done.")

if __name__ == "__main__":
    main()
