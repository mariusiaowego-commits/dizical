#!/usr/bin/env python3
"""把「珊瑚底 + 白字」的按钮/胶囊底色换成 `--dash-coral-solid` (2026-10-09, dad 选 A).

判据: 只有**同一条 CSS 规则里同时出现** `background: var(--dash-coral)` 与 `color: var(--dash-white)`
的, 才是 #FF6B6B 压白字 (2.78:1, 不达 AA) 的问题点 —— 换成 #CC3B3B (4.93:1)。
其他用 coral 的地方 (点/环/光/描边/深色文字) 一律不动, 品牌色不变。

幂等: 已经不是 --dash-coral 的规则不会重复改。
用法: python3 tools/fix-coral-white-contrast.py [--check]
"""
import pathlib
import re
import sys

DEMO = pathlib.Path(__file__).resolve().parent.parent
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)


def fix(path: pathlib.Path) -> list[tuple[str, str]]:
    raw = path.read_text(encoding="utf-8")
    hits: list[tuple[str, str]] = []
    PAIRS = [("--dash-coral", "--dash-coral-solid"), ("--dash-accent", "--dash-accent-solid")]

    def repl(m):
        sel, body = m.group(1), m.group(2)
        for base, solid in PAIRS:
            # 只看**实心背景** (background / background-color 的整值), 不碰渐变/描边
            if re.search(rf"background(-color)?:\s*var\({base}\)", body) and "var(--dash-white)" in body:
                new_body = re.sub(rf"(background(-color)?:\s*)var\({base}\)", rf"\1var({solid})", body)
                hits.append((" ".join(sel.split()), base))
                return sel + "{" + new_body + "}"
        return m.group(0)

    new = RULE.sub(repl, raw)
    if hits and "--check" not in sys.argv:
        path.write_text(new, encoding="utf-8")
    return hits


def main():
    total = 0
    for p in sorted(DEMO.glob("*.html")):
        hits = fix(p)
        if hits:
            print(f"{p.name}:")
            for sel, first in hits:
                print(f"    {sel[:78]}")
            total += len(hits)
    print(f"{'[check] ' if '--check' in sys.argv else ''}共 {total} 条规则换成 --dash-coral-solid")


if __name__ == "__main__":
    main()
