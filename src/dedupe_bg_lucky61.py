#!/usr/bin/env python3
"""去白底：5 张 lucky_61_*.png → RGBA + 透明背景。参考 docs/badge-workflow.md"""
from PIL import Image
import os

DIR = "/Users/mt16/dev/dizical/src/kid_app/static/badges"
files = [f"lucky_61_{y}.png" for y in range(2026, 2031)]

for name in files:
    src = os.path.join(DIR, name)
    im = Image.open(src).convert("RGBA")
    pixels = im.load()
    w, h = im.size
    changed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            # 规则 1：纯白 → 透明
            if r > 220 and g > 220 and b > 220 and a > 200:
                pixels[x, y] = (r, g, b, 0)
                changed += 1
            # 规则 2：近白 + 低饱和（抗锯齿）→ 透明
            elif r > 200 and g > 200 and b > 200:
                if max(r, g, b) - min(r, g, b) < 30:
                    pixels[x, y] = (r, g, b, 0)
                    changed += 1
    im.save(src)
    print(f"  {name}: {changed} px → transparent ({changed/(w*h)*100:.1f}%)")
print("Done.")
