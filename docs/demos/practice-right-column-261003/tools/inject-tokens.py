#!/usr/bin/env python3
"""把 dashboard-skin-01-v2.html 的两块 :root token 定义原样注入目标页的 @@TOKENS@@ 占位。
用法：python3 tools/inject-tokens.py [目标文件名]（默认 card-dashboard-skeleton-01.html）
不手抄 → 不会漂。注入后校验：--dash-* 名个数、有没自我引用。
"""
import re, sys
from pathlib import Path

D = Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003")
src = (D / "dashboard-skin-01-v2.html").read_text(encoding="utf-8")
dst_p = D / (sys.argv[1] if len(sys.argv) > 1 else "card-dashboard-skeleton-01.html")
dst = dst_p.read_text(encoding="utf-8")


def extract(text, header_re):
    m = re.search(header_re, text)
    if not m:
        print(f"ABORT: 找不到块 {header_re}"); sys.exit(1)
    i = text.index("{", m.start())
    depth, j = 0, None
    for k in range(i, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                j = k
                break
    return text[m.start():j + 1]


light = extract(src, r"\n\s*:root\s*\{")
ink = extract(src, r":root\[data-skin=\"ink\"\]\s*\{")
block = "  /* ── token 契约：从 dashboard-skin-01-v2.html 原样抽取（勿手改，改契约要全文件同步） ── */\n" + light + "\n" + ink

if "@@TOKENS@@" not in dst:
    print(f"ABORT: {dst_p.name} 里没有 @@TOKENS@@ 占位"); sys.exit(1)
out = dst.replace("@@TOKENS@@", block)
dst_p.write_text(out, encoding="utf-8")

names = set(re.findall(r"(--dash-[a-z0-9-]+)\s*:", out))
selfref = [n for n in names if re.search(rf"{re.escape(n)}\s*:\s*var\({re.escape(n)}\)", out)]
print(f"WROTE {dst_p.name}，注入 {len(names)} 个 --dash-* 名；自我引用 {len(selfref)}: {selfref}")
