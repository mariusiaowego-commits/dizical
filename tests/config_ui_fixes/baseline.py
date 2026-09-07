"""config_ui_fixes 基线验证 — 改之前的现状。

跑一次，把所有改前的"现状"打印出来。
后续每个修复做完，跑对应的 verify_xxx.py，对比基线。
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path("/Users/mt16/dev/dizical")
CONFIG_HTML = REPO / "src/kid_app/templates/config.html"
PRACTICE_LOG_HTML = REPO / "src/kid_app/templates/config-practice-log.html"
KOBOYO_DIR = REPO / "src/kid_app/static/icons/koboyo"


def banner(title: str):
    print("\n" + "=" * 70)
    print(f"BASELINE: {title}")
    print("=" * 70)


# ── A3 ────────────────────────────────────────────────────────────
def baseline_a3_textarea_height():
    banner("A3 — textarea min-height")
    src = PRACTICE_LOG_HTML.read_text()
    # 抓所有 .form-textarea { ... } blocks (DOTALL)
    blocks = re.findall(r"\.form-textarea\s*\{([^}]+)\}", src, re.DOTALL)
    for i, b in enumerate(blocks):
        print(f"--- .form-textarea block #{i+1} ---")
        for line in b.strip().splitlines():
            print(f"  {line.strip()}")
    # 抓 #assignNotes 标签
    m2 = re.search(r'<textarea[^>]*id="assignNotes"[^>]*>', src)
    print(f"\n#assignNotes tag: {m2.group(0).strip() if m2 else 'NOT FOUND'}")
    # rows 属性？
    has_rows_assign = bool(re.search(r'<textarea[^>]*id="assignNotes"[^>]*\brows=', src))
    print(f"#assignNotes has rows attr: {'YES' if has_rows_assign else 'NO'}")
    # logNote
    m3 = re.search(r'<textarea[^>]*id="logNote"[^>]*>', src)
    print(f"\n#logNote tag: {m3.group(0).strip() if m3 else 'NOT FOUND'}")
    has_rows_log = bool(re.search(r'<textarea[^>]*id="logNote"[^>]*\brows=', src))
    print(f"#logNote has rows attr: {'YES' if has_rows_log else 'NO'}")


# ── A4 ────────────────────────────────────────────────────────────
def baseline_a4_focus_jump():
    banner("A4 — addAssignEntryBtn handler focus")
    src = PRACTICE_LOG_HTML.read_text()
    # 找 addAssignEntryBtn listener 完整 body
    m = re.search(
        r"document\.getElementById\(['\"]addAssignEntryBtn['\"]\)\.addEventListener\(['\"]click['\"],\s*\(\)\s*=>\s*\{(.+?)\}\);",
        src, re.DOTALL
    )
    if m:
        body = m.group(1).strip()
        print(f"handler body:\n{body}")
        print(f"contains '.focus(': {'YES' if '.focus(' in body else 'NO'}")
        print(f"contains 'scrollIntoView': {'YES' if 'scrollIntoView' in body else 'NO'}")
    else:
        print("handler NOT FOUND (regex too narrow)")

    # addEntryBtn 同样
    m2 = re.search(
        r"document\.getElementById\(['\"]addEntryBtn['\"]\)\.addEventListener\(['\"]click['\"],\s*\(\)\s*=>\s*\{(.+?)\}\);",
        src, re.DOTALL
    )
    if m2:
        body = m2.group(1).strip()
        print(f"\naddEntryBtn handler body:\n{body}")
        print(f"contains '.focus(': {'YES' if '.focus(' in body else 'NO'}")
        print(f"contains 'scrollIntoView': {'YES' if 'scrollIntoView' in body else 'NO'}")


# ── A5 ────────────────────────────────────────────────────────────
def baseline_a5_color_strips():
    banner("A5 — hard-coded red strips")
    src = PRACTICE_LOG_HTML.read_text()
    for cls in ["assign-subject", "log-entry-row", "entry-assign-hint"]:
        m = re.search(rf"\.{cls}\s*\{{[^}}]*border-left[^}}]*\}}", src)
        print(f".{cls}: {m.group(0).strip() if m else 'NOT FOUND'}")
    # 有没有 nth-child
    nth_count = len(re.findall(r":nth-child\(", src))
    print(f"nth-child occurrences total: {nth_count}")


# ── B1 ────────────────────────────────────────────────────────────
def baseline_b1_svg_health():
    banner("B1 — koboyo svg health (3 broken icons)")
    broken_xml = []
    broken_path = []
    for svg in sorted(KOBOYO_DIR.glob("*.svg")):
        text = svg.read_text()
        # 1. XML 闭合标签格式
        xml_ok = True
        try:
            ET.fromstring(text)
        except ET.ParseError as e:
            xml_ok = False
            broken_xml.append((svg.name, str(e)))
        # 2. path d 字符串里 "-\s+\d" (负号后空格)
        path_breaks = re.findall(r"-\s+[\d\.]+", text)
        if path_breaks:
            broken_path.append((svg.name, path_breaks[:5]))
        print(f"  {svg.name:42s}  XML={'OK' if xml_ok else 'BROKEN'}  path_breaks={len(path_breaks)}")

    print(f"\nBroken XML count: {len(broken_xml)}")
    for n, e in broken_xml:
        print(f"  - {n}: {e[:80]}")
    print(f"\nPath with breaks count: {len(broken_path)}")
    for n, t in broken_path:
        print(f"  - {n}: {t}")


def baseline_b1_config_html_usage():
    banner("B1 — config.html uses 3 external koboyo svg")
    src = CONFIG_HTML.read_text()
    refs = re.findall(r'<img\s+src="(/static/icons/koboyo/[^"]+)"', src)
    print(f"<img src='/static/icons/koboyo/...'> count: {len(refs)}")
    for r in refs:
        print(f"  - {r}")
    inline_svg = len(re.findall(r"<svg[^>]*>", src))
    print(f"inline <svg ...> count: {inline_svg}")


if __name__ == "__main__":
    baseline_a3_textarea_height()
    baseline_a4_focus_jump()
    baseline_a5_color_strips()
    baseline_b1_svg_health()
    baseline_b1_config_html_usage()
    print("\n" + "=" * 70)
    print("Baseline captured. Save this output as 'before' for comparison.")
    print("=" * 70)
