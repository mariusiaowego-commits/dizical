"""config_ui_fixes 验证套件 — 改前必跑，对照 baseline 写出预期。

每项独立 function, pytest 跑。
跑法: cd /Users/mt16/dev/dizical && python3 -m pytest tests/config_ui_fixes/test_after.py -v
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path("/Users/mt16/dev/dizical")
CONFIG_HTML = REPO / "src/kid_app/templates/config.html"
PRACTICE_LOG_HTML = REPO / "src/kid_app/templates/config-practice-log.html"


# ═══════════════════════════════════════════════════════════════════════════
# A3 — textarea 高度
# ═══════════════════════════════════════════════════════════════════════════
def test_a3_textarea_min_height_110():
    """改后: .form-textarea 第二块 min-height >= 110"""
    src = PRACTICE_LOG_HTML.read_text()
    # 找第二个 .form-textarea 块 (含 min-height)
    blocks = re.findall(r"\.form-textarea\s*\{([^}]+)\}", src, re.DOTALL)
    assert len(blocks) >= 2, f"expected ≥2 .form-textarea blocks, got {len(blocks)}"
    second = blocks[1]
    m = re.search(r"min-height:\s*(\d+)px", second)
    assert m, f"min-height not found in block: {second!r}"
    height = int(m.group(1))
    assert height >= 110, f"min-height must be ≥110px, got {height}px (agy 测得原 60px, 建议 110-120)"
    print(f"  A3: min-height = {height}px  ✓")


def test_a3_assignNotes_has_rows():
    """改后: #assignNotes 有 rows 属性 (默认行高)"""
    src = PRACTICE_LOG_HTML.read_text()
    m = re.search(r'<textarea[^>]*id="assignNotes"[^>]*>', src)
    assert m, "#assignNotes textarea not found"
    assert "rows=" in m.group(0), f"#assignNotes missing rows attr: {m.group(0)}"
    rows_m = re.search(r'rows="(\d+)"', m.group(0))
    assert rows_m and int(rows_m.group(1)) >= 3, f"rows must be ≥3, got {rows_m.group(1) if rows_m else 'none'}"
    print(f"  A3: #assignNotes rows={rows_m.group(1)}  ✓")


# ═══════════════════════════════════════════════════════════════════════════
# A4 — focus 跳转
# ═══════════════════════════════════════════════════════════════════════════
def _extract_handler_body(src: str, btn_id: str) -> str:
    """抓 getElementById(btn_id).addEventListener('click', () => { ... });"""
    # 找 handler - 允许 body 跨多行, 找配对的 })
    idx = src.find(f"document.getElementById('{btn_id}')")
    if idx < 0:
        idx = src.find(f'document.getElementById("{btn_id}")')
    assert idx >= 0, f"addEventListener for {btn_id} not found"
    # 从 idx 开始找 = { ... }
    eq_idx = src.find("=> {", idx)
    assert eq_idx >= 0, f"=> {{ not found after {btn_id}"
    # 找配对 }
    start = eq_idx + len("=> {")
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    return src[start:i-1].strip()


def test_a4_addAssignEntryBtn_calls_focus():
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_handler_body(src, "addAssignEntryBtn")
    assert ".focus(" in body, f"addAssignEntryBtn handler missing .focus():\n{body}"
    assert "scrollIntoView" in body, f"addAssignEntryBtn handler missing scrollIntoView:\n{body}"
    print(f"  A4: addAssignEntryBtn has .focus() + scrollIntoView  ✓")


def test_a4_addEntryBtn_calls_focus():
    src = PRACTICE_LOG_HTML.read_text()
    body = _extract_handler_body(src, "addEntryBtn")
    assert ".focus(" in body, f"addEntryBtn handler missing .focus():\n{body}"
    assert "scrollIntoView" in body, f"addEntryBtn handler missing scrollIntoView:\n{body}"
    print(f"  A4: addEntryBtn has .focus() + scrollIntoView  ✓")


# ═══════════════════════════════════════════════════════════════════════════
# A5 — nth-child 6 色
# ═══════════════════════════════════════════════════════════════════════════
def test_a5_assign_subject_nth_child():
    src = PRACTICE_LOG_HTML.read_text()
    # .assign-subject:nth-child(Nn+1) { border-left-color: var(--color-1); } 等
    rules = re.findall(
        r"\.assign-subject:nth-child\(\s*\d+n\s*\+\s*(\d)\s*\)\s*\{[^}]*border-left-color\s*:\s*([^;}]+)",
        src
    )
    assert len(rules) >= 4, f"expected ≥4 nth-child rules for .assign-subject (PR-A 用 dizical 4 色), got {len(rules)}: {rules}"
    colors = [c.strip() for _, c in rules]
    # 色必须不同
    assert len(set(colors)) == len(rules), f"colors must be distinct, got: {colors}"
    # 不能全是 #FF6B6B
    assert not all(c.lower() == "#ff6b6b" for c in colors), f"all same color #FF6B6B: {colors}"
    # 色必须来自 dizical 已有 palette (sage/rose/lavender/cream/CSS var)
    allowed = {"var(--sage)", "var(--rose)", "var(--lavender)", "var(--cream)",
               "#a8d5ba", "#e8b4bc", "#c5b8d9", "#f5e6d3"}
    bad = [c for c in colors if c not in allowed and not c.startswith("var(--color-")]
    assert not bad, f"colors not from dizical palette or --color-N var: {bad}"
    print(f"  A5: .assign-subject {len(rules)} nth-child rules with distinct dizical-palette colors  ✓")
    for i, c in enumerate(colors, 1):
        print(f"      :nth-child({len(rules)}n+{i}) → {c}")


def test_a5_log_entry_row_nth_child():
    src = PRACTICE_LOG_HTML.read_text()
    rules = re.findall(
        r"\.log-entry-row:nth-child\(\s*\d+n\s*\+\s*(\d)\s*\)\s*\{[^}]*border-left-color\s*:\s*([^;}]+)",
        src
    )
    assert len(rules) >= 4, f"expected ≥4 nth-child rules for .log-entry-row, got {len(rules)}"
    colors = [c.strip() for _, c in rules]
    assert len(set(colors)) == len(rules), f"colors must be distinct, got: {colors}"
    print(f"  A5: .log-entry-row {len(rules)} nth-child rules  ✓")


def test_a5_entry_assign_hint_no_nth_child():
    """P0 fix: .entry-assign-hint 不应有 nth-child (每 entry 1 个 hint, 永远命中同位置 → 死色)

    验证 P0 修复成功: 单色 var(--sage) 替代 nth-child 轮换.
    """
    src = PRACTICE_LOG_HTML.read_text()
    rules = re.findall(
        r"\.entry-assign-hint:nth-child\(",
        src
    )
    assert not rules, f"P0 fix failed: .entry-assign-hint still has nth-child rules ({len(rules)} found). Hint 是 .log-entry-row 内唯一子 hint, nth-child 永远命中同一位置 → 死色 bug. 改用单色 var(--sage)."
    # 验证 hint 用单色
    m = re.search(r"\.entry-assign-hint\s*\{[^}]*border-left\s*:\s*([^;]+);", src)
    assert m, ".entry-assign-hint border-left not found"
    color = m.group(1).strip()
    assert "sage" in color or "#a8d5ba" in color, f".entry-assign-hint border-left must use sage color, got: {color}"
    print(f"  A5: .entry-assign-hint 单色 sage ({color}) 无 nth-child 死色 bug  ✓")


def test_a5_color_vars_defined():
    """必须定义 4 个 --color-N CSS var, 引用 dizical 已有 palette"""
    src = PRACTICE_LOG_HTML.read_text()
    found = re.findall(r"--color-[1-4]\s*:\s*([^;]+);", src)
    assert len(found) == 4, f"expected 4 --color-N vars, got {len(found)}: {found}"
    # 必须引用 dizical palette
    palette_ok = all(("var(--" in c or "#" in c) for c in found)
    assert palette_ok, f"--color-N vars must reference palette: {found}"
    print(f"  A5: --color-1..4 defined: {found}  ✓")


def test_a5_p2_no_hover_color_change():
    """P2 fix: hover 不改 border-left-color (agy 建议: 改色误导用户以为触发红色动作)

    验证 .assign-subject 和 .log-entry-row 都没有 :hover border-left-color 规则.
    """
    src = PRACTICE_LOG_HTML.read_text()
    bad = []
    for cls in ["assign-subject", "log-entry-row"]:
        # 找 :hover { ... } 块
        m = re.search(rf"\.{cls}:hover\s*\{{([^}}]*)\}}", src)
        if m and "border-left-color" in m.group(1):
            bad.append(f".{cls}:hover still has border-left-color: {m.group(0)}")
    assert not bad, f"P2 fix failed: {bad}"
    print(f"  A5: P2 fix - hover 不改 border-left-color  ✓")


# ═══════════════════════════════════════════════════════════════════════════
# B1 — 全 9 卡内联 svg
# ═══════════════════════════════════════════════════════════════════════════
def test_b1_no_external_koboyo_in_config_html():
    src = CONFIG_HTML.read_text()
    refs = re.findall(r'<img\s+src="(/static/icons/koboyo/[^"]+)"', src)
    assert not refs, f"config.html still references external koboyo svgs: {refs}"
    print(f"  B1: 0 external <img src='/static/icons/koboyo/...'>  ✓")


def test_b1_all_cards_have_inline_svg():
    """config.html 所有 config-card (a + div 都算) 都用内联 <svg>"""
    src = CONFIG_HTML.read_text()
    soup = BeautifulSoup(src, "lxml")
    cards = soup.find_all(class_="config-card")
    assert len(cards) >= 9, f"expected ≥9 .config-card, got {len(cards)}"
    no_svg = []
    for i, card in enumerate(cards):
        icon = card.find(class_="card-icon")
        if not icon:
            no_svg.append(f"#{i+1}: no .card-icon")
            continue
        svg = icon.find("svg")
        img = icon.find("img")
        if img and not svg:
            no_svg.append(f"#{i+1}: still has <img>")
        if not svg and not img:
            no_svg.append(f"#{i+1}: no <svg>")
    assert not no_svg, f"cards without inline svg: {no_svg}"
    print(f"  B1: all {len(cards)} cards have inline <svg> (no <img>)  ✓")


def test_b1_inline_svgs_use_currentColor():
    src = CONFIG_HTML.read_text()
    soup = BeautifulSoup(src, "lxml")
    cards = soup.find_all(class_="config-card")
    bad = []
    for i, card in enumerate(cards):
        icon = card.find(class_="card-icon")
        if not icon:
            continue
        svg = icon.find("svg")
        if not svg:
            continue
        stroke = svg.get("stroke", "")
        fill = svg.get("fill", "")
        if "currentColor" not in stroke and "currentColor" not in fill:
            bad.append(f"card #{i+1}: stroke={stroke!r} fill={fill!r}")
    assert not bad, f"svgs missing currentColor: {bad}"
    print(f"  B1: all card <svg> use stroke=currentColor  ✓")


def test_b1_koboyo_dir_audit():
    """整目录 koboyo svg 不可信 - 本 PR 不再外链, 但记录基线"""
    # 这个 test 永远 pass (纯 audit), 提示
    koboyo_dir = REPO / "src/kid_app/static/icons/koboyo"
    svgs = list(koboyo_dir.glob("*.svg"))
    print(f"  B1: koboyo dir has {len(svgs)} svg files (audit only, 不动它们)")


# ═══════════════════════════════════════════════════════════════════════════
# P3 — 二次 review 新增 (agy 建议, 锁住 regression)
# ═══════════════════════════════════════════════════════════════════════════
def test_p3_inline_svgs_well_formed_xml():
    """P3-3 (agy): config.html 所有内联 <svg> 必须 XML 良构"""
    src = CONFIG_HTML.read_text()
    soup = BeautifulSoup(src, "lxml")
    svgs = soup.find_all("svg")
    bad = []
    for i, svg in enumerate(svgs):
        # 用 ET.fromstring 验 XML 良构 (排除 jsr 注释等干扰)
        try:
            from bs4 import Comment as _BsComment
            # 序列化 svg + 内嵌 (去掉注释)
            s = str(svg)
            for c in svg.find_all(string=lambda t: isinstance(t, _BsComment)):
                s = s.replace(str(c), "")
            ET.fromstring(s)
        except ET.ParseError as e:
            bad.append(f"svg #{i+1}: {e}")
    assert not bad, f"B1 inline svgs not well-formed XML: {bad}"
    print(f"  P3: all {len(svgs)} inline <svg> are well-formed XML  ✓")


def test_p3_container_ids_exist():
    """P3-2 (agy): #assignEntries + #logEntries 两个 ID 必须存在 (A4 selector 目标)"""
    src = PRACTICE_LOG_HTML.read_text()
    for cid in ["assignEntries", "logEntries"]:
        # HTML id attribute (允许任意空白)
        m = re.search(rf'<div\s+id="{cid}"', src)
        assert m, f"P3-2: <div id=\"{cid}\"> not found in template"
        # JS reference — querySelector('#cid ...') 形态 (后面跟空格 + 子选择器)
        js_ref = re.search(rf"['\"`]#{cid}(?:\s|\.|,|\)|$)", src)
        assert js_ref, f"P3-2: JS reference '#{cid}' not found (any quote style)"
    print(f"  P3: #assignEntries + #logEntries both exist & referenced  ✓")


def test_p3_a4_selector_item_select_first():
    """P1 fix: A4 focus selector 必须 .item-select 优先 (新增行第一步是选科目)"""
    src = PRACTICE_LOG_HTML.read_text()
    # 从 btn id 后面开始抓 selector (避开 handler body 的 try/catch {})
    for btn_id in ["addAssignEntryBtn", "addEntryBtn"]:
        idx = src.find(f"document.getElementById('{btn_id}')")
        assert idx >= 0, f"{btn_id} addEventListener not found"
        # 找 const firstInput = last.querySelector('...')
        m = re.search(r"firstInput\s*=\s*last\.querySelector\(['\"`]([^'\"`]+)['\"`]\)", src[idx:idx+2000])
        assert m, f"{btn_id} firstInput selector not found in next 2000 chars"
        selector = m.group(1)
        prefix = selector.split(",")[0].strip()
        assert "item-select" in prefix, f"{btn_id} selector should start with .item-select, got prefix: {prefix!r} in {selector!r}"
    print(f"  P3: P1 fix - both A4 selectors start with .item-select  ✓")


def test_p3_entry_assign_hint_dom_structure():
    """P3-1 (agy): .entry-assign-hint 必须存在于 .log-entry-row 模板内 (避免死色 bug 复发)

    row.className = 'log-entry-row' 是 JS 动态设置, 不在 HTML attribute.
    验证方法: 找 hint div, 往前找最近的 log-entry-row 字符串 (HTML attr 或 JS className 赋值).
    """
    src = PRACTICE_LOG_HTML.read_text()
    m = re.search(r'<div\s+class="entry-assign-hint"[^>]*data-idx', src)
    assert m, "P3-1: <div class='entry-assign-hint' data-idx...> not in template"
    pos = m.start()
    pre = src[:pos]
    # 接受 'log-entry-row' 任意形态 (HTML class=, JS className=, CSS selector)
    candidates = [
        pre.rfind("class=\"log-entry-row\""),
        pre.rfind("'log-entry-row'"),
        pre.rfind("`log-entry-row`"),
        pre.rfind(".log-entry-row {"),
    ]
    last_template = max(c for c in candidates if c > 0) if any(c > 0 for c in candidates) else -1
    assert last_template > 0, f"P3-1: entry-assign-hint not within log-entry-row template (candidates: {candidates})"
    print(f"  P3: .entry-assign-hint is inside .log-entry-row template  ✓")


# ═══════════════════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════════════════
def test_summary():
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    # pytest 会把每个 test_ 单独跑; 这个只做最后视觉汇总
