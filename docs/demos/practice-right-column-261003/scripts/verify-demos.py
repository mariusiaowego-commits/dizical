#!/usr/bin/env python3
"""demo 通用审计（P1–P4 共用）。自动纳入 demo 目录下所有 v2/新建页面。

七项 + 一项契约：
 1 非中性色字面量 = 0（中性 = rgba(0,0,0,a) / rgba(255,255,255,a) / #000 / #fff）
 2 transition: all = 0
 3 :root[data-skin="ink"] 皮肤活体（未被注释）
 4 <style> 花括号平衡
 5 内联 <script> 过 node --check
 6 引用的 --dash-* 都有定义
 7 @media (max-width: 480px) / 440 视口下不写死超宽固定值（警告级：出现 min-width>440px 的固定值）
 8 【契约】所有页面 --dash-* 名集合一致

用法：python3 scripts/verify-demos.py [文件名...]（默认自动收集）
"""
import pathlib, re, subprocess, tempfile, os, sys

DEMO = pathlib.Path(__file__).resolve().parent.parent
AUTO_ORDER = [
    "index.html",
    "dashboard-skin-01-v3.html",
    "metronome-01-v4.html",
    "metronome-02-strip.html",
    "metronome-01-v3.html",
    "dashboard-bottom-blocks-01-v2.html",
    "requests-card-01-v3.html",
    "today-records-01.html",
    "practice-duration-card-01-v3.html",
    "compose-02.html",
    "card-dashboard-skeleton-01.html",
    "ruler-shared-check.html",
    # 上一轮留档（对照用，仍纳入契约一致性检查）
    "dashboard-skin-01-v2.html",
    "metronome-01-v2.html",
    "requests-popout-v1-v2.html",
    "d5-design-probe.html",
]

NEUTRAL = re.compile(r"rgba?\(\s*(?:0\s*,\s*0\s*,\s*0|255\s*,\s*255\s*,\s*255)\s*[,)]", re.I)
HEXNEUTRAL = re.compile(r"#(?:000|fff|000000|ffffff)\b", re.I)
ANYHEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
ANYRGB = re.compile(r"rgba?\([^)]*\)")


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), css, flags=re.S)


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


def token_spans(css):
    out = []
    for pat in (r"(?<![-\w]):root\s*\{", r":root\[data-skin=\"ink\"\]\s*\{"):
        e = block_close(css, pat)
        if e is not None:
            m = re.search(pat, css)
            out.append((css.find("{", m.start()), e))
    return out


def check(path):
    raw = path.read_text()
    css = strip_comments(raw)
    st = re.search(r"<style[^>]*>(.*?)</style>", css, re.S)
    body = st.group(1) if st else ""
    off = st.start(1) if st else 0
    spans = token_spans(css)

    bad = []
    for m in re.finditer(r"\{([^{}]*)\}", body):
        s, e = off + m.start(1), off + m.end(1)
        if any(s >= a and e <= b for a, b in spans):
            continue
        for lit in list(ANYHEX.finditer(m.group(1))) + list(ANYRGB.finditer(m.group(1))):
            v = lit.group(0)
            if NEUTRAL.match(v) or HEXNEUTRAL.match(v):
                continue
            bad.append((css[:s + lit.start()].count("\n") + 1, v))

    js = []
    for i, m in enumerate(re.finditer(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", raw, re.S)):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(m.group(1))
            tmp = fh.name
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            js.append(f"script#{i}: " + " | ".join(r.stderr.strip().splitlines()[:2]))
        os.unlink(tmp)

    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", raw))
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", raw))
    missing = sorted(x for x in used - defined if x not in ("--i", "--knob-deg"))

    wide = sorted(set(re.findall(r"(?:min-)?width:\s*(\d{4,})px", body)))

    return dict(
        violations=bad, ink=':root[data-skin="ink"]' in css,
        braces=body.count("{") - body.count("}"),
        tall=len(re.findall(r"transition:\s*all", body)),
        jserr=js, missing=missing, wide=wide,
        tokens={t for t in defined if t.startswith("--dash-")},
        has_audit=bool(re.search(r"['\"]audit['\"]|get\(['\"]audit['\"]\)|audit\s*==?=|audit=1", raw)),
        # 门禁：引了共享尺子就必须真有尺子 markup（2026-10-06 踩坑：节拍器卡引了共享件却没打算放尺子，
        # 结果 .tick/.ruler 样式洒进去，dad 在 compose 里看到「节拍器卡里长出一把刻度尺」）
        ruler_include=bool(re.search(r"shared/ruler-production\.(?:css|js)", raw)),
        ruler_markup=bool(re.search(r'ruler-wrap', raw)) and bool(re.search(r'id=["\']ruler["\']', raw)),
        ruler_scope_ng=False,   # 下面统一判定
        # 门禁：旧文字色 token 不许再当 color 用（--dash-ink / --dash-muted 在深墨下不翻转）
        legacy_text=len(re.findall(r"color:\s*var\(--dash-(?:ink|muted)\)", raw))
        + len(re.findall(r"\.style\.color\s*=\s*['\"]var\(--dash-(?:ink|muted)\)['\"]", raw)),
        bytes=len(raw),
    )


targets = sys.argv[1:] or [f for f in AUTO_ORDER if (DEMO / f).exists()]
present = []
print("=== demo 通用审计 ===")
for f in targets:
    p = DEMO / f
    if not p.exists():
        print(f"\n-- {f}: 尚未交付（跳过）")
        continue
    r = check(p)
    r["ruler_scope_ng"] = r["ruler_include"] and not r["ruler_markup"]
    present.append((f, r))
    ok = (not r["violations"] and r["ink"] and r["braces"] == 0
          and r["tall"] == 0 and not r["jserr"] and not r["missing"] and r["legacy_text"] == 0
          and not r["ruler_scope_ng"])
    print(f"\n{'OK ' if ok else 'NG '}{f}  ({r['bytes']} B)")
    print(f"    非中性色字面量 {len(r['violations'])} / transition:all {r['tall']} / ink {r['ink']} / "
          f"括号差 {r['braces']} / audit模式 {'有' if r['has_audit'] else '无'}")
    print(f"    未定义 token {r['missing'] or '无'} / JS {r['jserr'] or '通过'} / 写死超宽值 {r['wide'] or '无'}")
    print(f"    共享尺子 引用 {'有' if r['ruler_include'] else '无'} / markup {'有' if r['ruler_markup'] else '无'}"
          + ("  ← NG：引了共享尺子却没有尺子 markup（样式会洒进来）" if r["ruler_scope_ng"] else ""))
    print(f"    旧文字色 (--dash-ink/--dash-muted 当 color) {r['legacy_text']}"
          + ("  ← 必须为 0" if r["legacy_text"] else "  OK"))
    for line, v in r["violations"][:6]:
        print(f"      L{line}: {v}")

if len(present) > 1:
    # 基线：第一个真正定义 --dash-* 的页面（index / compose / 骨架这类目录页没有 token，不能当基线）
    tok = [(f, r) for f, r in present if r["tokens"]]
    base_f, base = tok[0]
    print(f"\n=== 换肤契约：所有页面 --dash-* 名集合 == {base_f} ===")
    for f, r in tok[1:]:
        d = r["tokens"] ^ base["tokens"]
        print(f"  {'OK ' if not d else 'NG '}{f}: " + (f"一致（{len(base['tokens'])} 个）" if not d else f"差异 {sorted(d)}"))
    skipped = [f for f, r in present if not r["tokens"]]
    if skipped:
        print(f"  （跳过无 token 页：{', '.join(skipped)}）")
