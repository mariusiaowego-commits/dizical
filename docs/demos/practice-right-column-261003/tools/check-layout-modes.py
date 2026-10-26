#!/usr/bin/env python3
"""
tools/check-layout-modes.py
dizical demo v38 · S2 模式响应与 data-vp 样式选择器扫描工具

功能：
  扫描 cards/*.html 中的 <style> 块，统计 [data-vp= 作为 CSS 样式选择器出现的次数。
  白名单：HTML 标签上的属性、JS 脚本里的 dataset.vp 读取均不计入。
"""

import os
import glob
import re

CARDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cards")

def scan_card_css(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取所有 <style>...</style> 块
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.IGNORECASE)
    
    matches = []
    for block in style_blocks:
        lines = block.splitlines()
        for idx, line in enumerate(lines):
            # 忽略纯注释行
            stripped = line.strip()
            if stripped.startswith("/*") and stripped.endswith("*/"):
                continue
            if "//" in stripped and stripped.startswith("//"):
                continue
            if "[data-vp=" in line or "[data-vp " in line:
                matches.append((idx + 1, stripped))
    return matches

def main():
    card_files = sorted(glob.glob(os.path.join(CARDS_DIR, "card-*.html")))
    total = 0
    print("═" * 70)
    print("  dizical demo v38 · CSS [data-vp] 样式选择器扫描报告")
    print("═" * 70)
    
    for f in card_files:
        fname = os.path.basename(f)
        matches = scan_card_css(f)
        cnt = len(matches)
        total += cnt
        print(f"  {fname:<30} : {cnt:>2} 处")
        for ln, txt in matches[:5]:
            print(f"    L{ln:<4}: {txt[:60]}")
        if cnt > 5:
            print(f"    ... 剩余 {cnt - 5} 处省略 ...")

    print("─" * 70)
    print(f"  合计 CSS [data-vp] 选择器总数: {total}")
    print("═" * 70)
    return total

if __name__ == "__main__":
    main()
