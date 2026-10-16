#!/usr/bin/env python3
"""给总览页每个模块格插入「作者」徽章。按实际产出归属（不是 plan 里的初版分配）。
每条替换断言命中 1 次，命中数不符整体失败且不写盘（防半改）。"""
import re, sys
from pathlib import Path

D = Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003")
p = D / "index.html"
t = p.read_text(encoding="utf-8")

# 卡片名 → 作者（实际产出）
AUTHORS = {
    "card-practice-timer": "作者 agy（本轮九条修正 + 接共享尺子）",
    "card-metronome": "作者 agy（本轮四条修正 + 接共享尺子）",
    "card-transport-blocks": "作者 agy（本轮五条修正，留 A/B 变体）",
    "card-requests": "作者 agy（本轮改成独立卡片）",
    "card-today-records": "作者 grok 实现 · agy 设计探针",
    "card-practice-duration": "作者 hermes（我）",
    "card-dashboard-skeleton-01": "作者 hermes（我）",
    "ruler-shared-check": "作者 hermes（我）",
    "compose-01": "作者 hermes（我）",
}
CSS = ("  .auth { font-size: 10.5px; color: var(--h-soft); border: 1px solid var(--h-line);"
       " border-radius: 999px; padding: 1px 7px; white-space: nowrap; }\n")

total = 0
for card, author in AUTHORS.items():
    pat = re.compile(r'(<span class="name">' + re.escape(card) + r'</span>)')
    n = len(pat.findall(t))
    if n != 1:
        print(f"ABORT: {card} 命中 {n} 次（要 1）"); sys.exit(1)
    t = pat.sub(lambda m: m.group(1) + f'<span class="auth">{author}</span>', t, count=1)
    total += 1

if ".auth {" not in t:
    anchor = "  .tile-desc {"
    if t.count(anchor) != 1:
        print(f"ABORT: CSS 锚点命中 {t.count(anchor)} 次"); sys.exit(1)
    t = t.replace(anchor, CSS + anchor, 1)

p.write_text(t, encoding="utf-8")
print(f"WROTE index.html：插入 {total} 个作者徽章 + .auth 样式")
print("残留未标作者:", [m for m in re.findall(r'<span class="name">([^<]+)</span>', t) if m not in AUTHORS])
