#!/usr/bin/env python3
"""v2 四文件统一验证。
规则：
 1. 非中性色字面量（蓝灰/coral/accent/gold 及其 alpha、任何 hex 彩度色）= 0
    中性 = rgba(0,0,0,a) / rgba(255,255,255,a) / #000 / #fff（投影与高光层级，允许保留）
 2. transition: all = 0（必须列具体属性）
 3. ink 皮肤选择器活着（不在注释里）
 4. <style> 花括号平衡
 5. 内联 <script> 过 node --check
 6. 四文件 token 名集合完全相同（契约）
 7. 引用的 --dash-* 都有定义
"""
import pathlib, re, subprocess, tempfile, os, sys

DEMO = pathlib.Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003")
FILES = ["dashboard-skin-01-v2.html", "metronome-01-v2.html",
         "dashboard-bottom-blocks-01-v2.html", "requests-popout-v1-v2.html"]

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
    spans = []
    for pat in (r"(?<![-\w]):root\s*\{", r":root\[data-skin=\"ink\"\]\s*\{"):
        m = re.search(pat, css)
        if m:
            s = css.find("{", m.start())
            e = block_close(css, pat)
            spans.append((s, e))
    return spans


report = {}
for f in FILES:
    p = DEMO / f
    raw = p.read_text()
    css = strip_comments(raw)
    style = re.search(r"<style[^>]*>(.*?)</style>", css, re.S)
    body = style.group(1)
    off = style.start(1)
    spans = token_spans(css)

    violations = []
    for m in re.finditer(r"\{([^{}]*)\}", body):
        s, e = off + m.start(1), off + m.end(1)
        if any(s >= a and e <= b for a, b in spans):
            continue
        seg = m.group(1)
        for lit in list(ANYHEX.finditer(seg)) + list(ANYRGB.finditer(seg)):
            v = lit.group(0)
            if NEUTRAL.match(v) or HEXNEUTRAL.match(v):
                continue
            line = css[:s + lit.start()].count("\n") + 1
            violations.append((line, v))

    inks = ':root[data-skin="ink"]' in css
    braces = body.count("{") - body.count("}")
    tall = len(re.findall(r"transition:\s*all", body))

    jserr = []
    for i, m in enumerate(re.finditer(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", raw, re.S)):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(m.group(1))
            tmp = fh.name
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            jserr.append(f"script#{i}: " + " | ".join(r.stderr.strip().splitlines()[:2]))
        os.unlink(tmp)

    used = set(re.findall(r"var\((--[a-z0-9-]+)\)", raw))
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", raw))
    missing = sorted(x for x in used - defined if x != "--i")
    report[f] = dict(violations=violations, ink=inks, braces=braces, tall=tall,
                     jserr=jserr, missing=missing, tokens=defined)

print("=== v2 四文件验证 ===")
ok = True
for f, r in report.items():
    flag = "OK " if (not r["violations"] and r["ink"] and r["braces"] == 0
                     and r["tall"] == 0 and not r["jserr"] and not r["missing"]) else "NG "
    if flag == "NG ":
        ok = False
    print(f"\n{flag}{f}")
    print(f"    非中性色字面量: {len(r['violations'])}   transition:all: {r['tall']}   "
          f"ink皮肤: {r['ink']}   花括号差: {r['braces']}")
    print(f"    未定义 token: {r['missing'] or '无'}   JS 语法: {r['jserr'] or '通过'}")
    for line, v in r["violations"][:8]:
        print(f"      L{line}: {v}")

sets = {f: {x for x in r["tokens"] if x.startswith("--dash-")} for f, r in report.items()}
locals_ = {f: sorted(x for x in r["tokens"] if not x.startswith("--dash-")) for f, r in report.items()}
base = sets[FILES[0]]
print("\n=== 换肤契约：四文件 --dash-* 名集合 == 完全相同 ===")
for f in FILES[1:]:
    diff = sets[f] ^ base
    if diff:
        ok = False
        print(f"  NG {f}: 差异 {sorted(diff)}")
    else:
        print(f"  OK {f}: 与 {FILES[0]} 一致（{len(base)} 个 token 名）")
print("\n=== 文件本地非 --dash-* 变量（不算契约，允许不同） ===")
for f in FILES:
    print(f"  {f}: {locals_[f]}")
print("\n统一结论:", "全 PASS" if ok else "存在 NG，见上")
sys.exit(0 if ok else 1)
