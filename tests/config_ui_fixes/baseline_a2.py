"""config_ui_fixes A2 baseline — 改之前的现状 (config.py + database.py + practice module)."""
import re
import sys
from pathlib import Path

REPO = Path("/Users/mt16/dev/dizical")
CONFIG_PY = REPO / "src/kid_app/routes/config.py"
DATABASE_PY = REPO / "src/database.py"
PRACTICE_LOG_HTML = REPO / "src/kid_app/templates/config-practice-log.html"


def banner(title: str):
    print("\n" + "=" * 70)
    print(f"BASELINE A2: {title}")
    print("=" * 70)


def baseline_a2_endpoints():
    banner("A2 — endpoints for conflict-check")
    src = CONFIG_PY.read_text()
    # 检查是否已有 GET /api/assignments/by-date 端点
    has_by_date = bool(re.search(r'@router\.get\(["\']/api/assignments/by-date["\']\)', src))
    print(f"GET /api/assignments/by-date exists: {'YES' if has_by_date else 'NO'}")
    # 检查 POST /api/assignments 是否含 conflict-check
    post_block_m = re.search(
        r'@router\.post\(["\']/api/assignments["\']\)\s*\n\s*async def api_create_assignment.*?(?=\n@router|\nclass |\Z)',
        src, re.DOTALL
    )
    if post_block_m:
        body = post_block_m.group(0)
        has_conflict = ("409" in body or "conflict" in body.lower() or "已存在" in body or "exists" in body.lower())
        print(f"POST /api/assignments has conflict-check (409/exists check): {'YES' if has_conflict else 'NO'}")
        # 看 POST 是不是直接 save 不检查
        print(f"POST directly calls save_weekly_assignment: {'save_weekly_assignment' in body}")


def baseline_a2_frontend_handlers():
    banner("A2 — frontend submit handler")
    src = PRACTICE_LOG_HTML.read_text()
    # 用 _extract_handler_body (跟 test_after.py 同款) 抓 submitAssignBtn body
    idx = src.find("document.getElementById('submitAssignBtn')")
    if idx < 0:
        idx = src.find('document.getElementById("submitAssignBtn")')
    if idx < 0:
        print("submitAssignBtn handler not found")
        return
    eq_idx = src.find("=> {", idx)
    if eq_idx < 0:
        eq_idx = src.find("async () => {", idx)
    start = eq_idx + (len("=> {") if "=> {" in src[eq_idx:eq_idx+6] else len("async () => {"))
    depth = 1
    i = start
    while i < len(src) and depth > 0:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
        i += 1
    body = src[start:i-1].strip()
    # 检查 conflict-check 关键字
    has_check = ("by-date" in body or "409" in body or "conflict" in body.lower() or "覆盖" in body)
    print(f"submit handler has pre-check (by-date/409/conflict/覆盖): {'YES' if has_check else 'NO'}")
    # 检查 confirm() 调用
    has_confirm = "confirm(" in body
    print(f"submit handler has confirm() dialog: {'YES' if has_confirm else 'NO'}")
    # 检查 PUT 调
    has_put = "PUT" in body or "method: 'PUT'" in body or 'method: "PUT"' in body
    print(f"submit handler has PUT call (existing path /api/assignments/{{date}}): {'YES' if has_put else 'NO'}")
    # 直接 POST?
    has_post = "'/config/api/assignments'" in body and "method: 'POST'" in body
    print(f"submit handler still has direct POST (will be replaced by check): {'YES' if has_post else 'NO'}")


def baseline_a2_database_layer():
    banner("A2 — database layer (precise by-date lookup)")
    db = DATABASE_PY.read_text()
    # 检查是否有 get_weekly_assignment_by_date 或类似精确查
    patterns = [
        r"def\s+get_weekly_assignment_by_date\b",
        r"def\s+get_assignment_by_lesson_date\b",
        r"def\s+query_assignment_by_date\b",
    ]
    for p in patterns:
        m = re.search(p, db)
        print(f"  pattern {p!r}: {'FOUND' if m else 'not found'}")
    # 现有 get_weekly_assignment 签名
    m = re.search(r"def\s+get_weekly_assignment\(self[^)]*\)", db)
    print(f"\nexisting get_weekly_assignment signature: {m.group(0) if m else 'NOT FOUND'}")


if __name__ == "__main__":
    baseline_a2_endpoints()
    baseline_a2_frontend_handlers()
    baseline_a2_database_layer()
    print("\n" + "=" * 70)
    print("Baseline A2 captured.")
    print("=" * 70)
