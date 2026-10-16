#!/usr/bin/env python3
"""加 `--dash-coral-solid` token (2026-10-09, dad 选 A).

问题: 品牌珊瑚 `--dash-coral: #FF6B6B` 当按钮底压白字只有 **2.78:1** (AA 要 4.5)。
dad 选 A: 按钮底改 `#CC3B3B` → 压白字 **4.93:1** 过关。

做法: 不直接改 `--dash-coral` (它还兼作点/环/光的颜色, 改它会动整体品牌色),
新增一个「实心底」专门 token `--dash-coral-solid: #CC3B3B`, 白字按钮用它。

契约约束: 换肤契约要求**各页 `--dash-*` 名集合一致**, 所以每页都要声明这个新 token (哪怕没用)。
本脚本幂等: 已有该 token 的页跳过; 插在每页 `--dash-coral:` 那行之后。
"""
import pathlib
import re
import sys

DEMO = pathlib.Path(__file__).resolve().parent.parent
TOKEN = "  --dash-coral-solid: #CC3B3B;"      # 珊瑚实心底 (白字 4.93:1)
TOKEN_ACCENT = "  --dash-accent-solid: #B8531F;"  # 品牌橙实心底 (白字 4.89:1; #FF8C5A 压白字只有 2.29)


def inject(path: pathlib.Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if "--dash-coral:" not in raw:
        return "无 coral token，跳过"
    new = raw
    acts = []
    if "--dash-coral-solid:" not in raw:
        new, n = re.subn(r"(?m)^(\s*--dash-coral:\s*[^;]+;)$", lambda m: m.group(1) + "\n" + TOKEN, new)
        if n:
            acts.append(f"coral-solid×{n}")
    if "--dash-accent-solid:" not in raw:
        new, n = re.subn(r"(?m)^(\s*--dash-accent:\s*[^;]+;)$", lambda m: m.group(1) + "\n" + TOKEN_ACCENT, new)
        if n:
            acts.append(f"accent-solid×{n}")
    if not acts:
        return "已有，跳过"
    path.write_text(new, encoding="utf-8")
    return "插入 " + " / ".join(acts)


def main():
    check = "--check" in sys.argv
    pages = sorted(p for p in DEMO.glob("*.html"))
    changed = 0
    for p in pages:
        res = inject(p) if not check else ("(check 模式)" if "--dash-coral-solid:" not in p.read_text(encoding="utf-8") and "--dash-coral:" in p.read_text(encoding="utf-8") else "已有/跳过")
        if res.startswith("插入"):
            changed += 1
        print(f"  {p.name:42s} {res}")
    print(f"改动 {changed} 页 (共 {len(pages)} 页)")


if __name__ == "__main__":
    main()
