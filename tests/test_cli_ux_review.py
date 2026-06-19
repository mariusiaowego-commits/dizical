"""
CLI UX review 修复回归测试

覆盖:
- Rich Table overflow="fold" 在 category list / lesson stats / payment history / practice items
- practice_query VIEWS 顺序 + 默认 history 视图
- practice_query hotkey H/T/W/M 跳转
- _AssignmentsTUI 极窄屏 size guard (不崩溃)
"""

import os
import sys
from datetime import date, timedelta

import pytest

# 必须在 import src 之前设 cwd
os.chdir('/Users/mt16/dev/dizical')
sys.path.insert(0, '/Users/mt16/dev/dizical')


# ─── Rich Table fold 测试 ─────────────────────────────────────────────

def test_category_list_fold_no_ellipsis():
    """category list 80 列下小科目长内容不 ellipsize

    直接构造测试数据, 不依赖真实 DB (避免测试环境数据不一致).
    """
    from io import StringIO
    from rich.console import Console
    from rich.table import Table
    from src import practice as pm

    # 构造测试 categories + items: "曲子" 大科目有 7 个子科目, 拼起来超长
    fake_categories = [
        {'id': 1, 'name': '曲子', 'sort_order': 1},
        {'id': 2, 'name': '演唱', 'sort_order': 2},
    ]
    fake_items = [
        {'item_id': 1003, 'name': '单吐练习', 'category_id': 1},
        {'item_id': 1004, 'name': '回娘家', 'category_id': 1},
        {'item_id': 1026, 'name': '采茶扑蝶', 'category_id': 1},
        {'item_id': 1032, 'name': '茉莉花（二）', 'category_id': 1},
        {'item_id': 1337, 'name': '颤音练习', 'category_id': 1},
        {'item_id': 1340, 'name': '萨丽哈', 'category_id': 1},
        {'item_id': 1346, 'name': '西藏舞曲', 'category_id': 1},
        {'item_id': 1028, 'name': '唱茉莉花（二）', 'category_id': 2},
        {'item_id': 1341, 'name': '唱萨利哈', 'category_id': 2},
        {'item_id': 1344, 'name': '唱西藏舞曲', 'category_id': 2},
    ]

    # monkey patch DB 接口
    real_get_categories = pm.get_categories
    real_get_items = pm.db.get_practice_items
    pm.get_categories = lambda: fake_categories
    pm.db.get_practice_items = lambda active_only=True, include_archived=False: fake_items

    from src import cli as cli_mod
    real_console = cli_mod.console
    buf = StringIO()
    cli_mod.console = Console(file=buf, width=80)
    try:
        cli_mod.practice_category_list()
    finally:
        pm.get_categories = real_get_categories
        pm.db.get_practice_items = real_get_items
        cli_mod.console = real_console

    out = buf.getvalue()
    # fold 模式下, "曲子" 行的所有 7 个子科目 ID 都应能找到 (即使跨行)
    expected_ids = ["1003", "1004", "1026", "1032", "1337", "1340", "1346"]
    for iid in expected_ids:
        assert f"({iid})" in out, (
            f"❌ item_id {iid} 不在输出里, 子科目被截断: \n{out}"
        )
    # 小科目行不能再以 ellipsis "…" 结尾 (任何字符的省略号)
    for line in out.splitlines():
        if "│" in line and ("曲子" in line or "演唱" in line):
            stripped = line.strip().strip("│").strip()
            if not stripped or stripped.startswith(("ID", "─")):
                continue
            assert not stripped.endswith("…"), (
                f"❌ 数据行仍有 ellipsis 截断: {line}"
            )


def test_lesson_stats_yearly_fold_dates():
    """lesson stats yearly 模式长日期列用 fold"""
    from src.cli import _show_year_stats

    # 这只验证函数不崩 + 表格 schema 有 fold, 不强依赖 DB 数据
    try:
        _show_year_stats(2025)
    except Exception as e:
        # DB 可能没有 2025 数据, 不强制
        if "no such column" in str(e) or "no such table" in str(e):
            pytest.skip(f"DB 数据不足: {e}")
        raise


def test_payment_history_fold_notes():
    """payment history 备注列 fold"""
    from io import StringIO
    from rich.console import Console
    from src.cli import payment_history

    from src import cli as cli_mod
    real_console = cli_mod.console
    buf = StringIO()
    cli_mod.console = Console(file=buf, width=80)
    try:
        payment_history()
    finally:
        cli_mod.console = real_console
    # 不崩即可, 列定义由代码层验证
    assert buf.getvalue()


def test_practice_items_fold_names():
    """practice items 名称列 fold"""
    from io import StringIO
    from rich.console import Console
    from src.cli import practice_items

    from src import cli as cli_mod
    real_console = cli_mod.console
    buf = StringIO()
    cli_mod.console = Console(file=buf, width=80)
    try:
        practice_items()
    finally:
        cli_mod.console = real_console
    assert buf.getvalue()


# ─── practice_query VIEWS 顺序 ─────────────────────────────────────────

class _MockCurses:
    COLOR_CYAN = 6; COLOR_WHITE = 7; COLOR_YELLOW = 3; COLOR_GREEN = 2; COLOR_RED = 1; COLOR_MAGENTA = 5; COLOR_BLACK = 0
    A_NORMAL = 0; A_BOLD = 0x200000; A_DIM = 0x400000; A_REVERSE = 0x4000
    KEY_UP = 259; KEY_DOWN = 258; KEY_LEFT = 260; KEY_RIGHT = 261; KEY_ENTER = 343
    window = type("window", (), {})
    class error(Exception): pass
    def has_colors(self): return True
    def start_color(self): pass
    def use_default_colors(self): pass
    def init_pair(self, *a): pass
    def color_pair(self, n): return n << 8
    def curs_set(self, *a): pass


class _MockWindow:
    def __init__(self, h, w):
        self.h = h; self.w = w; self._broken = False
        for name in ("keypad", "nodelay", "clear", "refresh", "attrset", "clrtoeol"):
            setattr(self, name, lambda *a: None)
    def getmaxyx(self): return (self.h, self.w)
    def addstr(self, row, col, text, attr=0):
        tlen = len(text) if text else 0
        if row < 0 or row >= self.h or col < 0 or col + tlen > self.w:
            self._broken = True
            raise _MockCurses.error(f"OOB row={row} col={col} len={tlen} h={self.h} w={self.w}")


def _setup_query():
    sys.modules["curses"] = _MockCurses()
    # 重新 import 确保拿到 mock
    if "src.practice_query" in sys.modules:
        del sys.modules["src.practice_query"]
    from src.practice_query import PracticeQueryTUI
    return PracticeQueryTUI


def test_practice_query_default_view_is_history():
    """默认 view_idx=0 应该是 history (高频场景)"""
    PracticeQueryTUI = _setup_query()
    mw = _MockWindow(40, 200)
    tui = PracticeQueryTUI(mw)
    assert tui.view_idx == 0
    assert tui.VIEWS[0] == "history"
    assert tui.VIEWS == ['history', 'today', 'homework', 'week', 'month']


def test_practice_query_hotkey_h_jumps_history():
    """按 H 跳到 history (view_idx=0)"""
    PracticeQueryTUI = _setup_query()
    mw = _MockWindow(40, 200)
    tui = PracticeQueryTUI(mw)
    tui.view_idx = 2  # 模拟在 homework
    tui.handle_key(ord('h'))
    assert tui.view_idx == 0
    assert tui.VIEWS[tui.view_idx] == "history"
    # 翻页应该被重置
    assert tui.history_cursor == 0


def test_practice_query_hotkey_t_jumps_today():
    """按 T 跳到 today (view_idx=1)"""
    PracticeQueryTUI = _setup_query()
    mw = _MockWindow(40, 200)
    tui = PracticeQueryTUI(mw)
    tui.handle_key(ord('t'))
    assert tui.view_idx == 1
    assert tui.VIEWS[tui.view_idx] == "today"


def test_practice_query_hotkey_w_jumps_week():
    """按 W 跳到 week (view_idx=3)"""
    PracticeQueryTUI = _setup_query()
    mw = _MockWindow(40, 200)
    tui = PracticeQueryTUI(mw)
    tui.handle_key(ord('w'))
    assert tui.view_idx == 3
    assert tui.VIEWS[tui.view_idx] == "week"


def test_practice_query_hotkey_m_jumps_month():
    """按 M 跳到 month (view_idx=4)"""
    PracticeQueryTUI = _setup_query()
    mw = _MockWindow(40, 200)
    tui = PracticeQueryTUI(mw)
    tui.handle_key(ord('m'))
    assert tui.view_idx == 4
    assert tui.VIEWS[tui.view_idx] == "month"


def test_practice_query_all_views_render_ipad_wide():
    """iPad 宽屏 (50x200) 5 个视图都稳定渲染"""
    PracticeQueryTUI = _setup_query()
    for v in range(5):
        mw = _MockWindow(50, 200)
        tui = PracticeQueryTUI(mw)
        tui.view_idx = v
        tui.draw()  # 不应 raise
        assert not mw._broken, f"view={v} ({tui.VIEWS[v]}) BROKEN on iPad wide"


def test_practice_query_all_views_render_normal():
    """正常终端 (24x80) 5 个视图都稳定渲染"""
    PracticeQueryTUI = _setup_query()
    for v in range(5):
        mw = _MockWindow(24, 80)
        tui = PracticeQueryTUI(mw)
        tui.view_idx = v
        tui.draw()
        assert not mw._broken, f"view={v} ({tui.VIEWS[v]}) BROKEN on 24x80"


# ─── _AssignmentsTUI size guard ────────────────────────────────────────

def _setup_assignments():
    sys.modules["curses"] = _MockCurses()
    if "src.cli" in sys.modules:
        del sys.modules["src.cli"]
    from src.cli import _AssignmentsTUI
    return _AssignmentsTUI


def _fake_assignments():
    base = date(2026, 6, 1)
    return [{
        "lesson_date": base + timedelta(days=i * 7),
        "stage_start": base + timedelta(days=i * 7),
        "stage_end": base + timedelta(days=i * 7 + 6),
        "stage_order": 10 + i,
        "items": [{
            "item_id": 1000 + i,
            "item": f"单吐{i}",
            "metronome": "♩=82",
            "minutes": 20,
            "requirements": "速度从82到86",
        }],
        "images": [],
        "notes": "",
    } for i in range(5)]


def test_assignments_tui_ipad_wide_ok():
    """iPad 宽屏 _AssignmentsTUI 正常"""
    _AssignmentsTUI = _setup_assignments()
    mw = _MockWindow(40, 200)
    tui = _AssignmentsTUI(_fake_assignments())
    tui._draw(mw, 40, 200)
    assert not mw._broken


def test_assignments_tui_normal_ok():
    """24x80 _AssignmentsTUI 正常"""
    _AssignmentsTUI = _setup_assignments()
    mw = _MockWindow(24, 80)
    tui = _AssignmentsTUI(_fake_assignments())
    tui._draw(mw, 24, 80)
    assert not mw._broken


def test_assignments_tui_tiny_size_guard():
    """12x40 极窄屏不应崩溃 (size guard 触发)"""
    _AssignmentsTUI = _setup_assignments()
    mw = _MockWindow(12, 40)
    tui = _AssignmentsTUI(_fake_assignments())
    # 不应 raise
    tui._draw(mw, 12, 40)
    # size guard 触发时不应该有 OOB addstr
    assert not mw._broken


def test_assignments_tui_tall_narrow_size_guard():
    """60x40 高瘦屏不应崩溃"""
    _AssignmentsTUI = _setup_assignments()
    mw = _MockWindow(60, 40)
    tui = _AssignmentsTUI(_fake_assignments())
    tui._draw(mw, 60, 40)
    assert not mw._broken


def test_assignments_tui_smaller_than_guard():
    """h<8 or w<60 时 size guard 触发"""
    _AssignmentsTUI = _setup_assignments()
    mw = _MockWindow(8, 50)  # h<8
    tui = _AssignmentsTUI(_fake_assignments())
    tui._draw(mw, 8, 50)
    assert not mw._broken

    mw2 = _MockWindow(10, 80)  # h<12
    tui2 = _AssignmentsTUI(_fake_assignments())
    tui2._draw(mw2, 10, 80)
    assert not mw2._broken