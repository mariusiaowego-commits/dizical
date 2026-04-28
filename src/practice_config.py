"""
大科目/小科目 配置 TUI
用 curses 实现分层菜单管理
"""

import curses
import traceback
from typing import Optional, List, Dict, Any

from .practice import (
    get_categories,
    add_category,
    update_category,
    delete_category,
    set_item_category,
    db,
)
from .models import LessonStatus


# --- 颜色对 ---
PAIR_HEADER = 1
PAIR_SELECTED = 2
PAIR_NORMAL = 3
PAIR_BORDER = 4
PAIR_PROMPT = 5
PAIR_ERROR = 6
PAIR_SUCCESS = 7


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(PAIR_HEADER, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(PAIR_SELECTED, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(PAIR_NORMAL, curses.COLOR_WHITE, -1)
    curses.init_pair(PAIR_BORDER, curses.COLOR_CYAN, -1)
    curses.init_pair(PAIR_PROMPT, curses.COLOR_YELLOW, -1)
    curses.init_pair(PAIR_ERROR, curses.COLOR_RED, -1)
    curses.init_pair(PAIR_SUCCESS, curses.COLOR_GREEN, -1)


class PracticeConfigTUI:
    def __init__(self, stdscr: curses.window):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.current_menu = "main"
        self.selected_idx = 0
        self.categories: List[Dict] = []
        self.items: List[Dict] = []
        self.category_items: Dict[int, List[Dict]] = {}  # cat_id -> items
        self.message = ""
        self.msg_attr = PAIR_NORMAL
        self.input_buf = ""
        self.input_prompt = ""
        self.input_target: Any = None  # e.g. ("add_category", None) or ("rename_category", cat_id)
        self.confirm_action: Optional[tuple] = None

    # ─── 数据加载 ───────────────────────────────────────────────

    def load_data(self):
        self.categories = get_categories()
        all_items = db.get_practice_items(active_only=False)
        self.items = all_items
        self.category_items = {}
        uncategorized = []
        for item in all_items:
            cat_id = item.get("category_id")
            if cat_id and cat_id in {c["id"] for c in self.categories}:
                if cat_id not in self.category_items:
                    self.category_items[cat_id] = []
                self.category_items[cat_id].append(item)
            else:
                uncategorized.append(item)
        if uncategorized:
            self.category_items[0] = uncategorized

    # ─── 绘制 ───────────────────────────────────────────────────

    def draw(self):
        self.height, self.width = self.stdscr.getmaxyx()
        self.stdscr.clear()
        self.stdscr.border()

        if self.input_prompt:
            self._draw_input_screen()
            return

        if self.confirm_action:
            self._draw_confirm_screen()
            return

        if self.current_menu == "main":
            self._draw_main_menu()
        elif self.current_menu == "category_list":
            self._draw_category_list()
        elif self.current_menu == "item_list":
            self._draw_item_list()
        elif self.current_menu == "relation":
            self._draw_relation_menu()

        # 底部状态栏
        self._draw_status_bar()

        self.stdscr.refresh()

    def _center(self, text: str, width: int) -> str:
        visible = len(text)
        pad = (width - visible) // 2
        return " " * pad + text

    def _header(self, title: str):
        attr = curses.color_pair(PAIR_HEADER) | curses.A_BOLD
        self.stdscr.addstr(0, 0, " " * self.width, curses.color_pair(PAIR_HEADER))
        self.stdscr.addstr(0, 2, title[: self.width - 4], attr)

    def _draw_main_menu(self):
        self._header("⚙  练习配置")
        items = [
            "🐔 大科目管理",
            "📋 小科目管理",
            "🔗 归属关系配置",
            "",
            "🚪 退出",
        ]
        for i, line in enumerate(items, start=2):
            if i >= self.height - 1:
                break
            if i == self.height - 1:
                break
            if line == "":
                continue
            selected = (i - 2 == self.selected_idx)
            attr = curses.color_pair(PAIR_SELECTED) if selected else curses.color_pair(PAIR_NORMAL)
            prefix = "▶ " if selected else "  "
            self.stdscr.addstr(i, 2, prefix + line, attr)

    def _draw_category_list(self):
        self._header("🐔 大科目管理")
        cats = self.categories
        n = len(cats)
        menu_items = [f"{c['name']}  (排序:{c['sort_order']})" for c in cats]
        menu_items += ["", "➕ 新增大科目", "✏ 重命名", "🗑 删除", "", "← 返回"]

        offset = 2
        for i, line in enumerate(menu_items, start=offset):
            if i >= self.height - 1:
                break
            row = i - offset
            if row < n:
                cat_id = cats[row]["id"]
                selected = (self.selected_idx == row)
            elif line == "":
                continue
            elif line == "➕ 新增大科目":
                selected = self.selected_idx == n
            elif line == "✏ 重命名":
                selected = self.selected_idx == n + 1
            elif line == "🗑 删除":
                selected = self.selected_idx == n + 2
            elif line == "← 返回":
                selected = self.selected_idx == n + 4
            else:
                continue
            attr = curses.color_pair(PAIR_SELECTED) if selected else curses.color_pair(PAIR_NORMAL)
            prefix = "▶ " if selected else "  "
            self.stdscr.addstr(i, 2, prefix + line, attr)

    def _draw_item_list(self):
        self._header("📋 小科目管理")
        items = self.items
        n = len(items)
        menu_items = [f"{i['name']}" for i in items]
        menu_items += ["", "➕ 新增小科目", "🗑 删除", "", "← 返回"]

        offset = 2
        for i, line in enumerate(menu_items, start=offset):
            if i >= self.height - 1:
                break
            row = i - offset
            if row < n:
                selected = self.selected_idx == row
            elif line == "":
                continue
            elif line == "➕ 新增小科目":
                selected = self.selected_idx == n
            elif line == "🗑 删除":
                selected = self.selected_idx == n + 1
            elif line == "← 返回":
                selected = self.selected_idx == n + 3
            else:
                continue
            attr = curses.color_pair(PAIR_SELECTED) if selected else curses.color_pair(PAIR_NORMAL)
            prefix = "▶ " if selected else "  "
            self.stdscr.addstr(i, 2, prefix + line, attr)

    def _draw_relation_menu(self):
        self._header("🔗 归属关系配置")
        self.stdscr.addstr(2, 2, "选择小科目以修改其归属大科目（-=无归属）：", curses.color_pair(PAIR_PROMPT))

        # 构建展示列表：所有小科目 + 归属信息
        items_with_cat = []
        for item in self.items:
            cat_id = item.get("category_id")
            cat_name = None
            for c in self.categories:
                if c["id"] == cat_id:
                    cat_name = c["name"]
                    break
            items_with_cat.append((item, cat_name))

        n = len(items_with_cat)
        menu_items = [f"{item['name']}  →  {cat_name or '无归属'}" for item, cat_name in items_with_cat]
        menu_items += ["", "← 返回"]

        offset = 4
        for i, line in enumerate(menu_items, start=offset):
            if i >= self.height - 1:
                break
            row = i - offset
            if row < n:
                selected = self.selected_idx == row
                item, cat_name = items_with_cat[row]
                # 高亮没有归属的
                if cat_name is None:
                    line_color = PAIR_PROMPT if selected else PAIR_ERROR
                else:
                    line_color = PAIR_SELECTED if selected else PAIR_NORMAL
                attr = curses.color_pair(line_color) if selected else curses.color_pair(PAIR_NORMAL)
                if selected:
                    attr = curses.color_pair(PAIR_SELECTED)
            elif line == "← 返回":
                selected = self.selected_idx == n + 1
                attr = curses.color_pair(PAIR_SELECTED) if selected else curses.color_pair(PAIR_NORMAL)
            else:
                continue
            prefix = "▶ " if selected else "  "
            self.stdscr.addstr(i, 2, prefix + line, attr)

    def _draw_status_bar(self):
        msg = self.message
        if msg:
            attr = curses.color_pair(self.msg_attr)
        else:
            msg = "↑↓ 选择  Enter 确认  Q 退出"
            attr = curses.color_pair(PAIR_BORDER)
        self.stdscr.addstr(self.height - 1, 2, msg[: self.width - 4], attr)

    def _draw_input_screen(self):
        self._header("📝 " + self.input_prompt)
        h, w = self.height, self.width
        # 画输入框
        box_y = h // 2 - 2
        self.stdscr.addstr(box_y, 2, "─" * (w - 4), curses.color_pair(PAIR_BORDER))
        self.stdscr.addstr(box_y + 1, 2, "│ " + self.input_buf + " " * (w - 7 - len(self.input_buf)), curses.color_pair(PAIR_NORMAL))
        self.stdscr.addstr(box_y + 2, 2, "─" * (w - 4), curses.color_pair(PAIR_BORDER))
        self.stdscr.addstr(box_y + 3, 2, "Enter 确认   Esc 取消", curses.color_pair(PAIR_BORDER))
        self.stdscr.refresh()

    def _draw_confirm_screen(self):
        self._header("⚠ 确认操作")
        action, target = self.confirm_action
        self.stdscr.addstr(3, 2, f"确定要 {action} 吗？", curses.color_pair(PAIR_PROMPT))
        self.stdscr.addstr(5, 2, "▶ 是 (Y)", curses.color_pair(PAIR_SELECTED) if self.selected_idx == 0 else curses.color_pair(PAIR_NORMAL))
        self.stdscr.addstr(6, 2, "  否 (N)", curses.color_pair(PAIR_SELECTED) if self.selected_idx == 1 else curses.color_pair(PAIR_NORMAL))

    # ─── 按键处理 ─────────────────────────────────────────────

    def handle_key(self, key: int) -> bool:
        """返回 True 表示退出"""
        if self.input_prompt:
            return self._handle_input_key(key)
        if self.confirm_action:
            return self._handle_confirm_key(key)

        if key in (curses.KEY_UP, ord("k")):
            self._move_cursor(-1)
        elif key in (curses.KEY_DOWN, ord("j")):
            self._move_cursor(1)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._handle_enter()
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self._handle_back()
        elif key in (ord("q"), ord("Q")):
            return True
        elif key in (curses.KEY_LEFT, ord("h"), 27):  # 27=Esc
            self._go_back()
        return False

    def _move_cursor(self, delta: int):
        n = self._current_menu_length()
        self.selected_idx = max(0, min(n - 1, self.selected_idx + delta))
        self.message = ""

    def _current_menu_length(self) -> int:
        if self.current_menu == "main":
            return 4
        elif self.current_menu == "category_list":
            return len(self.categories) + 4
        elif self.current_menu == "item_list":
            return len(self.items) + 3
        elif self.current_menu == "relation":
            return len(self.items) + 1
        return 4

    def _handle_enter(self):
        self.message = ""
        if self.current_menu == "main":
            self._enter_main()
        elif self.current_menu == "category_list":
            self._enter_category_list()
        elif self.current_menu == "item_list":
            self._enter_item_list()
        elif self.current_menu == "relation":
            self._enter_relation()

    def _enter_main(self):
        idx = self.selected_idx
        if idx == 0:
            self.current_menu = "category_list"
        elif idx == 1:
            self.current_menu = "item_list"
        elif idx == 2:
            self.current_menu = "relation"
        elif idx == 3:
            return True
        self.selected_idx = 0

    def _enter_category_list(self):
        cats = self.categories
        n = len(cats)
        idx = self.selected_idx
        if idx < n:
            # 选中某个大科目：显示子菜单（重命名/删除）
            self.selected_idx = 0
            self.current_menu = "category_detail"
            self._detail_cat_id = cats[idx]["id"]
            self._detail_cat_name = cats[idx]["name"]
        elif idx == n:
            # 新增
            self.input_prompt = "新增大科目名称"
            self.input_buf = ""
            self.input_target = ("add_category", None)
        elif idx == n + 1:
            # 重命名
            cats2 = self.categories
            if not cats2:
                self.message = "没有可重命名的大科目"
                return
            self.current_menu = "category_rename_select"
            self.selected_idx = 0
        elif idx == n + 2:
            # 删除
            cats2 = self.categories
            if not cats2:
                self.message = "没有可删除的大科目"
                return
            self.current_menu = "category_delete_select"
            self.selected_idx = 0
        elif idx == n + 4:
            self.current_menu = "main"
        self.selected_idx = 0

    def _enter_item_list(self):
        items = self.items
        n = len(items)
        idx = self.selected_idx
        if idx < n:
            self.current_menu = "item_detail"
            self._detail_item_id = items[idx]["id"]
            self._detail_item_name = items[idx]["name"]
            self.selected_idx = 0
        elif idx == n:
            self.input_prompt = "新增小科目名称"
            self.input_buf = ""
            self.input_target = ("add_item", None)
        elif idx == n + 1:
            self.current_menu = "item_delete_select"
            self.selected_idx = 0
        elif idx == n + 3:
            self.current_menu = "main"
        self.selected_idx = 0

    def _enter_relation(self):
        items = self.items
        n = len(items)
        idx = self.selected_idx
        if idx < n:
            self.input_prompt = f"设置 '{items[idx]['name']}' 的归属（-=无归属）"
            self.input_buf = ""
            self.input_target = ("set_relation", items[idx]["id"])
        elif idx == n + 1:
            self.current_menu = "main"
        self.selected_idx = 0

    def _handle_confirm_key(self, key: int) -> bool:
        if key in (ord("y"), ord("Y"), curses.KEY_ENTER, 10, 13):
            self._do_confirm_action()
            self.confirm_action = None
            self.selected_idx = 0
        elif key in (ord("n"), ord("N"), 27):
            self.confirm_action = None
            self.selected_idx = 0
        return False

    def _do_confirm_action(self):
        action, target = self.confirm_action
        if action == "del_category":
            cat_id = target
            try:
                delete_category(cat_id)
                self.message = f"已删除大科目 ID={cat_id}"
                self.msg_attr = PAIR_SUCCESS
            except Exception as e:
                self.message = f"删除失败: {e}"
                self.msg_attr = PAIR_ERROR
        elif action == "del_item":
            item_id = target
            try:
                db.delete_practice_item(item_id)
                self.message = f"已删除小科目 ID={item_id}"
                self.msg_attr = PAIR_SUCCESS
            except Exception as e:
                self.message = f"删除失败: {e}"
                self.msg_attr = PAIR_ERROR
        self.load_data()

    def _handle_input_key(self, key: int) -> bool:
        if key in (curses.KEY_ENTER, 10, 13):
            self._commit_input()
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.input_buf = self.input_buf[:-1]
        elif key in (27,):
            self.input_prompt = ""
            self.input_buf = ""
            self.input_target = None
        elif 32 <= key <= 126:
            self.input_buf += chr(key)
        return False

    def _commit_input(self):
        if not self.input_buf.strip():
            self.input_prompt = ""
            self.input_buf = ""
            self.input_target = None
            return

        action, target = self.input_target
        if action == "add_category":
            try:
                cid = add_category(self.input_buf.strip())
                self.message = f"已新增大科目 (ID={cid})"
                self.msg_attr = PAIR_SUCCESS
            except Exception as e:
                self.message = f"新增失败: {e}"
                self.msg_attr = PAIR_ERROR
        elif action == "rename_category":
            cat_id = target
            try:
                update_category(cat_id, self.input_buf.strip())
                self.message = f"已重命名大科目 ID={cat_id}"
                self.msg_attr = PAIR_SUCCESS
            except Exception as e:
                self.message = f"重命名失败: {e}"
                self.msg_attr = PAIR_ERROR
        elif action == "add_item":
            try:
                from .practice import set_item_category as _sci
                _sci(self.input_buf.strip(), None)
                self.message = f"已新增小科目: {self.input_buf.strip()}"
                self.msg_attr = PAIR_SUCCESS
            except Exception as e:
                self.message = f"新增失败: {e}"
                self.msg_attr = PAIR_ERROR
        elif action == "set_relation":
            item_id = target
            # 查找 item
            item_name = None
            for it in self.items:
                if it["id"] == item_id:
                    item_name = it["name"]
                    break
            cat_name = self.input_buf.strip()
            try:
                if cat_name == "-":
                    set_item_category(item_name, None)
                    self.message = f"已取消 {item_name} 的归属"
                else:
                    cats = get_categories()
                    cat_map = {c["name"]: c["id"] for c in cats}
                    if cat_name not in cat_map:
                        self.message = f"未找到大科目: {cat_name}"
                        self.msg_attr = PAIR_ERROR
                        self.input_prompt = ""
                        self.input_buf = ""
                        self.input_target = None
                        return
                    set_item_category(item_name, cat_map[cat_name])
                    self.message = f"已将 {item_name} 归属到 {cat_name}"
                self.msg_attr = PAIR_SUCCESS
            except Exception as e:
                self.message = f"设置失败: {e}"
                self.msg_attr = PAIR_ERROR
        self.input_prompt = ""
        self.input_buf = ""
        self.input_target = None
        self.load_data()

    def _handle_back(self):
        self._go_back()

    def _go_back(self):
        if self.current_menu == "category_list":
            self.current_menu = "main"
        elif self.current_menu == "category_detail":
            self.current_menu = "category_list"
        elif self.current_menu in ("category_rename_select", "category_delete_select"):
            self.current_menu = "category_list"
            self.selected_idx = 0
        elif self.current_menu == "item_list":
            self.current_menu = "main"
        elif self.current_menu == "item_detail":
            self.current_menu = "item_list"
        elif self.current_menu == "item_delete_select":
            self.current_menu = "item_list"
            self.selected_idx = 0
        elif self.current_menu == "relation":
            self.current_menu = "main"
        self.selected_idx = 0

    def _on_category_action(self, action: str):
        """处理大科目子菜单动作"""
        cats = self.categories
        idx = self.selected_idx
        if idx >= len(cats):
            return
        cat = cats[idx]
        if action == "rename":
            self.input_prompt = f"重命名大科目 '{cat['name']}'"
            self.input_buf = cat["name"]
            self.input_target = ("rename_category", cat["id"])
        elif action == "delete":
            self.confirm_action = ("del_category", cat["id"])
            self.selected_idx = 0

    # ─── Category Detail 子菜单 ────────────────────────────────
    # 选中某个大科目后进入，显示重命名/删除/返回

    def _draw_category_detail(self):
        self._header(f"🐔 大科目: {self._detail_cat_name}")
        menu = [
            "✏ 重命名",
            "🗑 删除",
            "",
            "← 返回",
        ]
        for i, line in enumerate(menu, start=2):
            if i >= self.height - 1:
                break
            if line == "":
                continue
            selected = self.selected_idx == i - 2
            attr = curses.color_pair(PAIR_SELECTED) if selected else curses.color_pair(PAIR_NORMAL)
            prefix = "▶ " if selected else "  "
            self.stdscr.addstr(i, 2, prefix + line, attr)

    def _enter_category_detail(self):
        idx = self.selected_idx
        if idx == 0:
            self._on_category_action("rename")
        elif idx == 1:
            self._on_category_action("delete")
        elif idx == 3:
            self.current_menu = "category_list"

    # ─── Item Detail 子菜单 ────────────────────────────────────
    def _draw_item_detail(self):
        self._header(f"📋 小科目: {self._detail_item_name}")
        menu = [
            "🗑 删除",
            "",
            "← 返回",
        ]
        for i, line in enumerate(menu, start=2):
            if i >= self.height - 1:
                break
            if line == "":
                continue
            selected = self.selected_idx == i - 2
            attr = curses.color_pair(PAIR_SELECTED) if selected else curses.color_pair(PAIR_NORMAL)
            prefix = "▶ " if selected else "  "
            self.stdscr.addstr(i, 2, prefix + line, attr)

    def _enter_item_detail(self):
        idx = self.selected_idx
        if idx == 0:
            self.confirm_action = ("del_item", self._detail_item_id)
            self.selected_idx = 0
        elif idx == 2:
            self.current_menu = "item_list"


# ─── 主入口 ───────────────────────────────────────────────────────────────

def run_tui(stdscr: curses.window):
    init_colors()
    stdscr.clear()
    curses.curs_set(0)
    stdscr.nodelay(False)

    tui = PracticeConfigTUI(stdscr)
    tui.load_data()

    while True:
        tui.draw()
        if tui.current_menu == "category_detail":
            tui._draw_category_detail()
            tui.stdscr.refresh()
            key = tui.stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                tui.selected_idx = max(0, tui.selected_idx - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                tui.selected_idx = min(3, tui.selected_idx + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                tui._enter_category_detail()
            elif key in (27, curses.KEY_LEFT, ord("h"), ord("q"), ord("Q")):
                tui._go_back()
        elif tui.current_menu == "item_detail":
            tui._draw_item_detail()
            tui.stdscr.refresh()
            key = tui.stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                tui.selected_idx = max(0, tui.selected_idx - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                tui.selected_idx = min(2, tui.selected_idx + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                tui._enter_item_detail()
            elif key in (27, curses.KEY_LEFT, ord("h"), ord("q"), ord("Q")):
                tui._go_back()
        elif tui.current_menu in ("category_rename_select", "category_delete_select"):
            cats = tui.categories
            n = len(cats)
            tui._header("↩ 选择要操作的大科目，回车确认")
            for i, cat in enumerate(cats):
                row = i + 2
                if row >= tui.height - 1:
                    break
                selected = tui.selected_idx == i
                attr = curses.color_pair(PAIR_SELECTED) if selected else curses.color_pair(PAIR_NORMAL)
                line = f"▶ {cat['name']}" if selected else f"  {cat['name']}"
                tui.stdscr.addstr(row, 2, line, attr)
            tui.stdscr.addstr(tui.height - 1, 2, "↑↓ 选择  Enter 确认  Esc 返回", curses.color_pair(PAIR_BORDER))
            tui.stdscr.refresh()
            key = tui.stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                tui.selected_idx = max(0, tui.selected_idx - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                tui.selected_idx = min(n - 1, tui.selected_idx + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                cat = cats[tui.selected_idx]
                if tui.current_menu == "category_rename_select":
                    tui.input_prompt = f"重命名 '{cat['name']}'"
                    tui.input_buf = cat["name"]
                    tui.input_target = ("rename_category", cat["id"])
                elif tui.current_menu == "category_delete_select":
                    tui.confirm_action = ("del_category", cat["id"])
                tui.selected_idx = 0
            elif key in (27,):
                tui.current_menu = "category_list"
                tui.selected_idx = 0
        elif tui.current_menu == "item_delete_select":
            items = tui.items
            n = len(items)
            tui._header("🗑 选择要删除的小科目，回车确认")
            for i, item in enumerate(items):
                row = i + 2
                if row >= tui.height - 1:
                    break
                selected = tui.selected_idx == i
                attr = curses.color_pair(PAIR_SELECTED) if selected else curses.color_pair(PAIR_NORMAL)
                line = f"▶ {item['name']}" if selected else f"  {item['name']}"
                tui.stdscr.addstr(row, 2, line, attr)
            tui.stdscr.addstr(tui.height - 1, 2, "↑↓ 选择  Enter 确认  Esc 返回", curses.color_pair(PAIR_BORDER))
            tui.stdscr.refresh()
            key = tui.stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                tui.selected_idx = max(0, tui.selected_idx - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                tui.selected_idx = min(n - 1, tui.selected_idx + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                item = items[tui.selected_idx]
                tui.confirm_action = ("del_item", item["id"])
                tui.selected_idx = 0
            elif key in (27,):
                tui.current_menu = "item_list"
                tui.selected_idx = 0
        else:
            key = tui.stdscr.getch()
            if tui.handle_key(key):
                break

    curses.endwin()


def launch():
    curses.wrapper(run_tui)
