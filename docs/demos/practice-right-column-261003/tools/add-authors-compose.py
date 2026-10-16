#!/usr/bin/env python3
"""给组合页每个卡槽加作者标注。按实际产出归属。断言每条命中 1 次，命中数不符整体失败且不写盘。"""
import re, sys
from pathlib import Path

D = Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003")
p = D / "compose-01.html"
t = p.read_text(encoding="utf-8")

AUTHORS = {
    "card-practice-timer": "agy",
    "card-metronome": "agy",
    "card-transport-blocks": "agy",
    "card-requests": "agy",
    "card-today-records": "grok",
    "card-practice-duration": "hermes",
}

for card, author in AUTHORS.items():
    pat = re.compile(r'(<div class="slot-hd"><b>[^<]+</b><span class="n">' + re.escape(card) + r'</span>)')
    n = len(pat.findall(t))
    if n != 1:
        print(f"ABORT: {card} 命中 {n} 次（要 1）"); sys.exit(1)
    t = pat.sub(lambda m: m.group(1) + f'<span class="auth">{author}</span>', t, count=1)

if ".auth {" not in t:
    anchor = "  .slot iframe {"
    if t.count(anchor) != 1:
        print(f"ABORT: CSS 锚点命中 {t.count(anchor)} 次"); sys.exit(1)
    t = t.replace(anchor,
                  "  .slot-hd .auth { margin-left: auto; font-size: 10.5px; color: var(--dash-coral-text);"
                  " border: 1px solid var(--dash-ink-a16); border-radius: 999px; padding: 1px 7px; }\n" + anchor, 1)

p.write_text(t, encoding="utf-8")
print(f"WROTE compose-01.html：{len(AUTHORS)} 个卡槽加作者标注")
