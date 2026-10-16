#!/usr/bin/env python3
"""token 配对对比度表（静态，WCAG 2.1）—— v2：按皮肤限定配对，杜绝跨皮肤假阳性

只算**现实里会共存**的「文字 token × 承接面 token」组合；已知待 dad 拍板的品牌色项归 OPEN，
不计入门禁（假门禁比没门禁更坏）。

阈值：正文 4.5 / 大字号或粗体 3.0
退出码：门禁 NG > 0 时非 0（可做 CI 门禁）

用法：
  python3 scripts/token-contrast.py                # 全部 demo 页
  python3 scripts/token-contrast.py --pairs        # 连通过项一起打
  python3 scripts/token-contrast.py --cand         # 外加候选取色评估
"""
import pathlib, re, sys

DEMO = pathlib.Path(__file__).resolve().parent.parent
FILES = ["dashboard-skin-01-v2.html", "metronome-01-v2.html", "dashboard-bottom-blocks-01-v2.html",
         "requests-popout-v1-v2.html", "today-records-01.html", "d5-design-probe.html"]

TEXT_TOKENS = ["--dash-text", "--dash-text-soft", "--dash-delta-up", "--dash-delta-down"]
LIGHT_SURFACES = ["--dash-page", "--dash-white", "--dash-surface-2", "--dash-surface-soft", "--dash-shell-hi"]
INK_SURFACES = ["--dash-page", "--dash-surface-2", "--dash-surface-soft", "--dash-panel", "--dash-pill-track"]

NEED = {"--dash-text": 4.5, "--dash-text-soft": 4.5, "--dash-delta-up": 3.0, "--dash-delta-down": 3.0}
PAIRS = [("light", t, s, NEED[t], None) for s in LIGHT_SURFACES for t in TEXT_TOKENS]
PAIRS += [("ink", t, s, NEED[t], None) for s in INK_SURFACES for t in TEXT_TOKENS]
PAIRS += [("light", t, "--dash-panel", 4.5, None) for t in ("--dash-panel-text", "--dash-panel-dim")]
PAIRS += [("ink", t, "--dash-panel", 4.5, None) for t in ("--dash-panel-text", "--dash-panel-dim")]

PAIRS += [("light", "--dash-accent-text", s, 4.5, None) for s in ("--dash-white", "--dash-surface-soft")]
PAIRS += [("ink", "--dash-accent-text", s, 4.5, None) for s in ("--dash-surface-soft", "--dash-panel")]

# 复合背景：文字落在「半透明色叠在不透明面上」（例：.tag 落在 accent-wash over surface-soft）
COMPOUND = [("light", "--dash-accent-text", ["--dash-accent-wash", "--dash-surface-soft"], 4.5),
            ("ink", "--dash-accent-text", ["--dash-accent-wash", "--dash-surface-soft"], 4.5)]

# ── 朱橙（--dash-vermilion 家族）与珊瑚并列的第二主色，2026-10-10 纳入门禁 ──
PAIRS += [("light", "--dash-vermilion-text", s_, 4.5, None) for s_ in ("--dash-white", "--dash-surface-soft")]
PAIRS += [("ink", "--dash-vermilion-text", s_, 4.5, None) for s_ in ("--dash-surface-soft", "--dash-panel")]
COMPOUND += [("light", "--dash-vermilion-text", ["--dash-vermilion-wash", "--dash-surface-soft"], 4.5),
             ("ink", "--dash-vermilion-text", ["--dash-vermilion-wash", "--dash-surface-soft"], 4.5)]
OPEN_NOTE = "品牌图形色（只在这些色被当『文字』用时才算违规；D2/D3 残留文字用法待核）"
PAIRS += [("light", t, "--dash-white", 3.0, OPEN_NOTE) for t in ("--dash-accent", "--dash-mic-on", "--dash-coral")]
PAIRS += [("ink", t, "--dash-white", 3.0, OPEN_NOTE) for t in ("--dash-accent", "--dash-mic-on", "--dash-coral")]
PAIRS += [("light", t_, "--dash-white", 3.0, OPEN_NOTE) for t_ in ("--dash-vermilion",)]
PAIRS += [("ink", t_, "--dash-white", 3.0, OPEN_NOTE) for t_ in ("--dash-vermilion",)]

CANDIDATES = {
    "红字（多）浅银候选 → 需 >=3.0": ["#FF6B6B", "#F2554F", "#E04A4A", "#D9453F"],
    "绿字（少）浅银候选 → 需 >=3.0": ["#10B981", "#0E9E6E", "#0C8A60", "#0A7A55"],
    "补录标签 11px → 需 >=4.5": ["#FF8C5A", "#E0703A", "#C85F2E", "#B8531F", "#A34A00"],
}


def parse_color(v):
    v = v.strip()
    m = re.match(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", v)
    if m:
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = re.match(r"^rgba?\(([^)]+)\)$", v)
    if m:
        p = [float(x) for x in re.split(r"[,\s/]+", m.group(1)) if x]
        return (p[0], p[1], p[2], p[3] if len(p) > 3 else 1.0)
    return None


def over(fg, bg):
    a = fg[3]
    return (fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a), 1.0)


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(fg, bg):
    a, b = lum(over(fg, bg)), lum(bg)
    hi, lo = max(a, b), min(a, b)
    return round((hi + 0.05) / (lo + 0.05), 2)


def token_maps(path):
    raw = path.read_text()
    out = {}
    for key, pat in (("light", r"(?<![-\w]):root\s*\{"), ("ink", r':root\[data-skin="ink"\]\s*\{')):
        m = re.search(pat, raw)
        if not m:
            continue
        i, depth, j = raw.find("{", m.start()), 0, None
        for k in range(i, len(raw)):
            if raw[k] == "{":
                depth += 1
            elif raw[k] == "}":
                depth -= 1
                if depth == 0:
                    j = k
                    break
        out[key] = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", raw[i:j]))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    verbose = "--pairs" in sys.argv
    total_ng = 0
    for f in (args or FILES):
        p = DEMO / f
        if not p.exists():
            print(f"-- {f} 不在")
            continue
        maps = token_maps(p)
        print(f"\n=== {f} ===")
        for skin in ("light", "ink"):
            t = maps.get(skin) or {}
            gate, opened = [], []
            for sk, txt, surf, need, note in PAIRS:
                if sk != skin or txt not in t or surf not in t:
                    continue
                a, b = parse_color(t[txt]), parse_color(t[surf])
                if not a or not b:
                    print(f"     ?? 未判定（值解析不了）: {txt}={t[txt]} / {surf}={t[surf]}")
                    continue
                r = ratio(a, b)
                (opened if note else gate).append((r >= need, r, need, txt, surf))
            for sk, txt, layers, need in COMPOUND:
                if sk != skin or txt not in t or any(l not in t for l in layers):
                    continue
                vals = [parse_color(t[x]) for x in layers] + [parse_color(t[txt])]
                if any(v is None for v in vals):
                    bad = [x for x, v in zip(list(layers) + [txt], vals) if v is None]
                    print("     ?? 未判定（值解析不了）: " + "; ".join(f"{x}={t[x]}" for x in bad))
                    continue
                base = vals[-2]
                for v in reversed(vals[:-2]):
                    base = over(v, base)
                r = ratio(vals[-1], base)
                gate.append((r >= need, r, need, txt, " + ".join(x.replace("--dash-", "") for x in layers)))
            ng = [x for x in gate if not x[0]]
            total_ng += len(ng)
            print(f"  [{skin}] 门禁 {len(gate)} 组 → 不合格 {len(ng)}；OPEN {len(opened)} 组（不计门禁）")
            for ok, r, need, txt, surf in sorted(gate, key=lambda x: x[1]):
                if verbose or not ok:
                    print(f"     {'OK' if ok else 'NG'} {r:>5} / {need}  {txt} on {surf}")
            for ok, r, need, txt, surf in sorted(opened, key=lambda x: x[1]):
                if verbose or not ok:
                    print(f"     {'OPEN-OK' if ok else 'OPEN-NG'} {r:>5} / {need}  {txt} on {surf}")
    print(f"\n→ 门禁不合格合计：{total_ng}")

    if "--cand" in sys.argv:
        print("\n=== 候选取色评估 ===")
        wash = over(parse_color("rgba(255,140,90,0.08)"), parse_color("#FFFFFF"))
        for title, vals in CANDIDATES.items():
            print(f"  {title}")
            for v in vals:
                c = parse_color(v)
                print(f"     {v:<10} white={ratio(c, parse_color('#FFFFFF')):>5}  "
                      f"surface-soft={ratio(c, parse_color('#FFFDFB')):>5}  accent-wash={ratio(c, wash):>5}  "
                      f"ink卡片#1A1E22={ratio(c, parse_color('#1A1E22')):>5}")
    sys.exit(1 if total_ng else 0)


main()
