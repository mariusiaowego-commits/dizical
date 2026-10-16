#!/usr/bin/env python3
"""只补 token 定义块（守卫改成精确检查注释标记）。"""
import pathlib, re, sys

DEMO = pathlib.Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003")
FILES = ["dashboard-skin-01-v2.html", "metronome-01-v2.html",
         "dashboard-bottom-blocks-01-v2.html", "requests-popout-v1-v2.html"]

LIGHT = """    /* ── v2 追加：透明度阶梯。混色（蓝灰/coral/accent/gold 的 alpha）必须走 token，
          审查规则：非中性色一律不得在组件里出现字面量 ── */
    --dash-ink-a04: rgba(44, 62, 80, 0.04);
    --dash-ink-a12: rgba(44, 62, 80, 0.12);
    --dash-ink-a16: rgba(44, 62, 80, 0.16);
    --dash-ink-a25: rgba(44, 62, 80, 0.25);
    --dash-ink-a42: rgba(44, 62, 80, 0.42);
    --dash-coral-glow: rgba(255, 107, 107, 0.45);
    --dash-coral-a25: rgba(255, 107, 107, 0.25);
    --dash-accent-soft: #FFA073;
    --dash-accent-wash: rgba(255, 140, 90, 0.08);
    --dash-accent-line: rgba(255, 140, 90, 0.30);
    --dash-accent-glow: rgba(255, 140, 90, 0.35);
    --dash-gold-a35: rgba(212, 175, 55, 0.35);
    --dash-gold-glow: rgba(255, 210, 100, 0.60);
"""
INK = """    /* v2 追加：深墨底上蓝灰透明不可见，翻向暖白；品牌 alpha 沿用浅银值 */
    --dash-ink-a04: rgba(255, 248, 240, 0.04);
    --dash-ink-a12: rgba(255, 248, 240, 0.10);
    --dash-ink-a16: rgba(255, 248, 240, 0.14);
    --dash-ink-a25: rgba(255, 248, 240, 0.22);
    --dash-ink-a42: rgba(0, 0, 0, 0.45);
"""


def block_close(text, pattern):
    m = re.search(pattern, text)
    if not m:
        return None
    start = text.find("{", m.start())
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


bad = 0
for f in FILES:
    p = DEMO / f
    t = p.read_text()
    light_mark = "v2 追加：透明度阶梯"
    ink_mark = "深墨底上蓝灰透明不可见"
    if light_mark not in t:
        pos = block_close(t, r"(?<![-\w]):root\s*\{")
        if pos is None:
            print(f"  ! {f}: 浅银 :root 未找到"); bad += 1; continue
        t = t[:pos] + LIGHT + t[pos:]
    if ink_mark not in t:
        pos = block_close(t, r":root\[data-skin=\"ink\"\]\s*\{")
        if pos is None:
            print(f"  ! {f}: 深墨 :root 未找到"); bad += 1; continue
        t = t[:pos] + INK + t[pos:]
    p.write_text(t)
    defs = t.count("--dash-ink-a04: ")
    uses = t.count("var(--dash-ink-a04)")
    print(f"  {f}: 定义 {defs} 处（应 2）| 引用 {uses} 处")

# 未定义引用检查：文件里用到的每个 --dash-* 是否都有定义
print("\n=== 未定义 token 引用检查 ===")
for f in FILES:
    t = (DEMO / f).read_text()
    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", t))
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", t))
    missing = sorted(used - defined)
    print(f"  {f}: 引用 {len(used)} / 未定义 {missing if missing else '无'}")
sys.exit(1 if bad else 0)
