#!/usr/bin/env python3
"""从 dashboard-skin-01-v2.html 读出 token 真值，生成 token-spec.md（值不手抄）。"""
import pathlib, re

DEMO = pathlib.Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003")
src = (DEMO / "dashboard-skin-01-v2.html").read_text()


def grab(pattern):
    m = re.search(pattern, src)
    start = src.find("{", m.start())
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start + 1:i]
    raise SystemExit("块未闭合")


def toks(block):
    out = []
    for m in re.finditer(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", block):
        out.append((m.group(1), m.group(2).strip()))
    return out


light = toks(grab(r"(?<![-\w]):root\s*\{"))
ink = toks(grab(r':root\[data-skin="ink"\]\s*\{'))
ink_map = dict(ink)

NEW = {"--dash-ink-a04", "--dash-ink-a12", "--dash-ink-a16", "--dash-ink-a25", "--dash-ink-a42",
       "--dash-coral-glow", "--dash-coral-a25", "--dash-accent-soft", "--dash-accent-wash",
       "--dash-accent-line", "--dash-accent-glow", "--dash-gold-a35", "--dash-gold-glow"}

lines = [
    "# practice 右栏 demo · Token 规格 (v2)",
    "",
    "> 由 `gen-token-spec.py` 从 `dashboard-skin-01-v2.html` 读出真值生成，非手抄。",
    "> 四文件（D1/D2/D3/D4 的 `-v2.html`）共享同一份 `--dash-*` 名集合（62 个），契约由 `verify-v2b.py` 校验。",
    "",
    f"## 一、浅银皮肤 `:root`（{len(light)} 项）",
    "",
    "| token | 值 | v2 |",
    "|-------|-----|----|",
]
for k, v in light:
    lines.append(f"| `{k}` | `{v}` | {'新增' if k in NEW else ''} |")

lines += [
    "",
    f"## 二、深墨皮肤 `:root[data-skin=\"ink\"]`（覆盖 {len(ink)} 项）",
    "",
    "| token | 深墨值 | 说明 |",
    "|-------|--------|------|",
]
for k, v in ink:
    note = ""
    if k in NEW:
        note = "深墨下把中性透明翻向暖白"
    lines.append(f"| `{k}` | `{v}` | {note} |")

lines += [
    "",
    "未被深墨覆盖的 token 继承浅银值（品牌色 `--dash-coral` / `--dash-accent` / `--dash-gold` 及各自 alpha 阶梯，两套皮肤一致）。",
    "",
    "## 三、审查规则（v2 起生效，脚本化）",
    "",
    "1. **非中性色禁止字面量**：蓝灰 `rgb(44,62,80)`、`#FF6B6B` coral、`#FF8C5A` accent、`#D4AF37` gold 及其 alpha 混色，组件里一律只能 `var(--dash-*)`。",
    "2. **中性黑/白 alpha 允许保留**：`rgba(0,0,0,α)`、`rgba(255,255,255,α)`、`#000`、`#fff` —— 属投影/内阴影/高光层级，不是颜色身份，换肤不需要改。",
    "3. **禁止 `transition: all`**：必须列具体属性。",
    "4. **深墨皮肤必须活体**：`:root[data-skin=\"ink\"]` 不得被注释掉。",
    "",
    "校验入口：`python3 verify-v2b.py`（四文件非中性色字面量 = 0 / `transition:all` = 0 / ink 活体 / 花括号平衡 / 内联 JS 过 `node --check` / 引用 token 全部有定义 / `--dash-*` 名集合四文件一致）。",
]

out = DEMO / "token-spec.md"
out.write_text("\n".join(lines) + "\n")
print(f"OK 写入 {out.name}: 浅银 {len(light)} 项 / 深墨覆盖 {len(ink)} 项")
new_in_light = [k for k, _ in light if k in NEW]
print(f"   新增（浅银）: {len(new_in_light)} 项 -> {new_in_light}")
