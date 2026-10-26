#!/usr/bin/env python3
"""
tools/sync-demo-templates.py
dizical demo v38 · 单一真源模板同步与校验工具

功能：
  1. 默认模式：将 cards/ 目录下的 6 个权威单卡文件，原样注入到 canvas-01.html 的 <template> 内部。
  2. --check 模式：只做比对校验，若有任何字节级差异，立即输出差异文件、行号与上下文并退出码 1；一致则退出码 0。
"""

import os
import sys
import difflib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_DIR = os.path.dirname(SCRIPT_DIR)
CANVAS_FILE = os.path.join(DEMO_DIR, "canvas-01.html")
CARDS_DIR = os.path.join(DEMO_DIR, "cards")

TEMPLATE_MAP = [
    ("tpl-A", "card-a-dashboard.html"),
    ("tpl-B", "card-b-metronome-full.html"),
    ("tpl-S", "card-s-metronome-strip.html"),
    ("tpl-D", "card-d-duration.html"),
    ("tpl-R", "card-r-records.html"),
    ("tpl-Q", "card-q-requests.html"),
]

def load_canvas_lines():
    with open(CANVAS_FILE, "r", encoding="utf-8") as f:
        return f.readlines()

def load_card_lines(fname):
    card_path = os.path.join(CARDS_DIR, fname)
    if not os.path.exists(card_path):
        raise FileNotFoundError(f"Card file not found: {card_path}")
    with open(card_path, "r", encoding="utf-8") as f:
        return f.readlines()

def extract_template_from_lines(lines, tid):
    prefix = f'  <template id="{tid}">'
    start_idx = None
    for i, line in enumerate(lines):
        if prefix in line:
            start_idx = i
            break
    if start_idx is None:
        raise ValueError(f"Template tag not found: {prefix}")

    end_idx = None
    for i in range(start_idx, len(lines)):
        if "</template>" in lines[i]:
            end_idx = i
            break
    if end_idx is None:
        raise ValueError(f"Closing </template> tag not found for {tid}")

    # 内联内容：首行去掉前缀 prefix，末行去掉 </template>
    inner_lines = [lines[start_idx][len(prefix):]] + lines[start_idx + 1:end_idx]
    return start_idx, end_idx, inner_lines

def check_sync():
    lines = load_canvas_lines()
    has_diff = False

    for tid, fname in TEMPLATE_MAP:
        try:
            start_idx, end_idx, inner_lines = extract_template_from_lines(lines, tid)
        except Exception as e:
            print(f"[FAIL] {tid}: {e}")
            return False

        card_lines = load_card_lines(fname)

        if inner_lines != card_lines:
            has_diff = True
            print(f"\n❌ [DIFF DETECTED] 模板 {tid} 与权威源 cards/{fname} 存在差异！")
            diff = list(difflib.unified_diff(
                inner_lines,
                card_lines,
                fromfile=f"canvas-01.html (<template id=\"{tid}\">)",
                tofile=f"cards/{fname}",
                lineterm=""
            ))
            # 打印首个差异 hunk
            print("\n".join(diff[:25]))
            if len(diff) > 25:
                print(f"... 剩余 {len(diff) - 25} 行差异省略 ...")

    if has_diff:
        print("\n[FAIL] 校验失败：内联模板与 cards/ 权威源不一致。请确认后运行 python3 tools/sync-demo-templates.py 同步。")
        return False
    else:
        print(f"✅ [PASS] 6 个模板在 canvas-01.html 与 cards/ 权威源 100% 字节级一致。")
        return True

def apply_sync():
    lines = load_canvas_lines()
    rebuilt_lines = []
    curr = 0

    for tid, fname in TEMPLATE_MAP:
        prefix = f'  <template id="{tid}">'
        start_idx, end_idx, _ = extract_template_from_lines(lines, tid)
        card_lines = load_card_lines(fname)

        # 插入当前模板之前的内容
        rebuilt_lines.extend(lines[curr:start_idx])

        # 拼接当前模板：
        # 首行：'  <template id="tpl-X">' + card_lines[0]
        # 中间：card_lines[1:]
        # 末行：'</template>\n'
        rebuilt_lines.append(prefix + card_lines[0])
        rebuilt_lines.extend(card_lines[1:])
        rebuilt_lines.append("</template>\n")

        curr = end_idx + 1

    # 插入最后一个模板之后的内容
    rebuilt_lines.extend(lines[curr:])

    with open(CANVAS_FILE, "w", encoding="utf-8") as f:
        f.writelines(rebuilt_lines)

    print(f"✅ [SYNC SUCCESS] 已将 cards/ 下 6 个权威单卡成功注入 {CANVAS_FILE}。")
    return True

if __name__ == "__main__":
    is_check = ("--check" in sys.argv)
    if is_check:
        ok = check_sync()
        sys.exit(0 if ok else 1)
    else:
        ok = apply_sync()
        sys.exit(0 if ok else 1)
