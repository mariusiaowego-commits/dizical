"""
大科目/小科目 配置
增删改查 - 支持单条和批量操作
"""

import sys
from typing import Optional, List, Dict

from .practice import (
    get_categories,
    add_category,
    update_category,
    delete_category,
    set_item_category,
    db,
)


def _print(msg: str):
    print(msg)


def _input(prompt: str) -> str:
    return input(prompt).strip()


def _show_current():
    """显示当前所有配置"""
    categories = get_categories()
    items = db.get_practice_items(active_only=False)

    _print("\n─── 大科目 ───")
    if categories:
        for c in sorted(categories, key=lambda x: x['sort_order']):
            related = [i['name'] for i in items if i.get('category_id') == c['id']]
            cats_str = '、'.join(related) if related else '（无）'
            _print(f"  [{c['id']}] {c['name']}  →  {cats_str}")
    else:
        _print("  （空）")

    uncategorized = [i['name'] for i in items if not i.get('category_id')]
    _print("\n─── 无归属小科目 ───")
    if uncategorized:
        for name in uncategorized:
            item = next(i for i in items if i['name'] == name)
            _print(f"  [{item['id']}] {name}")
    else:
        _print("  （空）")


def _show_menu():
    _print("")
    _print("╔══════════════════════════════════════╗")
    _print("║      🎵 练习配置 - 增删改查            ║")
    _print("╠══════════════════════════════════════╣")
    _print("║  1 大科目 - 增/删/改/重排序          ║")
    _print("║  2 小科目 - 增/删/改                 ║")
    _print("║  3 归属关系 - 设置/取消              ║")
    _print("║  0 退出                             ║")
    _print("╚══════════════════════════════════════╝")


# ─────────────────────────────────────────
# 大科目
# ─────────────────────────────────────────

def _category_add():
    """增加大科目，支持批量"""
    _print("\n  多个名称用顿号、逗号或空格分隔，直接回车返回")
    raw = _input("  新大科目名称: ").strip()
    if not raw:
        _print("  取消")
        return
    names = [n.strip() for n in raw.replace('、', ',').replace('，', ',').split(',') if n.strip()]
    existing = {c['name'] for c in get_categories()}
    added = 0
    for name in names:
        if name in existing:
            _print(f"  ⚠️  「{name}」已存在，跳过")
        else:
            cid = add_category(name)
            _print(f"  ✅ 新增 [{cid}] {name}")
            added += 1
    _print(f"  共新增 {added} 个大科目")


def _category_delete():
    """删除大科目"""
    categories = get_categories()
    if not categories:
        _print("  （无大科目）")
        return
    for c in sorted(categories, key=lambda x: x['sort_order']):
        _print(f"  [{c['id']}] {c['name']}")
    _print("  多个ID用空格分隔，直接回车返回")
    sid = _input("  输入要删除的大科目ID: ").strip()
    if not sid:
        _print("  取消")
        return
    try:
        ids = [int(x) for x in sid.split()]
    except ValueError:
        _print("  无效ID")
        return
    for cid in ids:
        target = next((c for c in categories if c['id'] == cid), None)
        if not target:
            _print(f"  ⚠️  ID {cid} 不存在，跳过")
            continue
        delete_category(cid)
        _print(f"  ✅ 已删除大科目「{target['name']}」")


def _category_rename():
    """改名大科目"""
    categories = get_categories()
    if not categories:
        _print("  （无大科目）")
        return
    for c in sorted(categories, key=lambda x: x['sort_order']):
        _print(f"  [{c['id']}] {c['name']}")
    sid = _input("  输入要改名的大科目ID: ").strip()
    if not sid:
        _print("  取消")
        return
    try:
        cid = int(sid)
    except ValueError:
        _print("  无效ID")
        return
    target = next((c for c in categories if c['id'] == cid), None)
    if not target:
        _print("  未找到该大科目")
        return
    new_name = _input(f"  新名称 [{target['name']}]: ").strip()
    if not new_name:
        _print("  取消")
        return
    update_category(cid, new_name)
    _print(f"  ✅ 「{target['name']}」 → 「{new_name}」")


def _category_sort():
    """重排大科目顺序"""
    categories = get_categories()
    if not categories:
        _print("  （无大科目）")
        return
    _print("  当前顺序:")
    for c in sorted(categories, key=lambda x: x['sort_order']):
        _print(f"    [{c['id']}] {c['name']}")
    _print("  输入新顺序的ID列表（空格分隔），直接回车返回")
    ids_str = _input("  新顺序: ").strip()
    if not ids_str:
        _print("  取消")
        return
    try:
        ids = [int(x) for x in ids_str.split()]
    except ValueError:
        _print("  无效ID")
        return
    # 验证
    cat_ids = {c['id'] for c in categories}
    for cid in ids:
        if cid not in cat_ids:
            _print(f"  ⚠️  ID {cid} 不存在")
            return
    for i, cid in enumerate(ids, start=1):
        update_category(cid, next(c['name'] for c in categories if c['id'] == cid), sort_order=i)
    _print(f"  ✅ 已更新顺序: {' → '.join(next(c['name'] for c in categories if c['id'] == cid) for cid in ids)}")


def _do_category():
    _print("\n─── 大科目操作 ───")
    _print("  a 增加  d 删除  r 改名  s 重排  q 返回")
    op = _input("  选择: ").strip().lower()
    if op == 'a':
        _category_add()
    elif op == 'd':
        _category_delete()
    elif op == 'r':
        _category_rename()
    elif op == 's':
        _category_sort()
    else:
        _print("  返回")


# ─────────────────────────────────────────
# 小科目
# ─────────────────────────────────────────

def _item_add():
    """增加小科目，支持批量"""
    _print("\n  多个名称用顿号、逗号或空格分隔，直接回车返回")
    raw = _input("  新小科目名称: ").strip()
    if not raw:
        _print("  取消")
        return
    names = [n.strip() for n in raw.replace('、', ',').replace('，', ',').split(',') if n.strip()]
    existing = {it['name'] for it in db.get_practice_items(active_only=False)}
    added = 0
    for name in names:
        if name in existing:
            _print(f"  ⚠️  「{name}」已存在，跳过")
        else:
            iid = db.add_practice_item(name)
            _print(f"  ✅ 新增 [{iid}] {name}")
            added += 1
    _print(f"  共新增 {added} 个小科目")


def _item_delete():
    """删除小科目"""
    items = db.get_practice_items(active_only=False)
    if not items:
        _print("  （无小科目）")
        return
    for it in items:
        cat_name = next((c['name'] for c in get_categories() if c['id'] == it.get('category_id')), None)
        tag = f" → {cat_name}" if cat_name else ""
        _print(f"  [{it['id']}] {it['name']}{tag}")
    _print("  多个ID用空格分隔，直接回车返回")
    sid = _input("  输入要删除的小科目ID: ").strip()
    if not sid:
        _print("  取消")
        return
    try:
        ids = [int(x) for x in sid.split()]
    except ValueError:
        _print("  无效ID")
        return
    item_map = {it['id']: it['name'] for it in items}
    for iid in ids:
        if iid not in item_map:
            _print(f"  ⚠️  ID {iid} 不存在，跳过")
            continue
        db.delete_practice_item(iid)
        _print(f"  ✅ 已删除小科目「{item_map[iid]}」")


def _item_rename():
    """改名小科目"""
    items = db.get_practice_items(active_only=False)
    if not items:
        _print("  （无小科目）")
        return
    for it in items:
        cat_name = next((c['name'] for c in get_categories() if c['id'] == it.get('category_id')), None)
        tag = f" → {cat_name}" if cat_name else ""
        _print(f"  [{it['id']}] {it['name']}{tag}")
    sid = _input("  输入要改名的小科目ID: ").strip()
    if not sid:
        _print("  取消")
        return
    try:
        iid = int(sid)
    except ValueError:
        _print("  无效ID")
        return
    target = next((it for it in items if it['id'] == iid), None)
    if not target:
        _print("  未找到该小科目")
        return
    new_name = _input(f"  新名称 [{target['name']}]: ").strip()
    if not new_name:
        _print("  取消")
        return
    if new_name == target['name']:
        _print("  名字未变")
        return

    # 检查新名字是否已被其他小科目使用
    existing = next((it for it in items if it['name'] == new_name and it['id'] != iid), None)
    if existing:
        _print(f"\n  ⚠️  「{new_name}」已存在（id={existing['id']}）")
        _print(f"  是否合并？「{target['name']}」的数据将并入「{new_name}」")
        confirm = _input("  确认合并？[y/N]: ").strip().lower()
        if confirm not in ('y', 'yes'):
            _print("  取消")
            return
        # 删除已存在的项，保留目标项改名，同时合并历史记录
        db.merge_practice_item(existing['id'], iid, target['name'], new_name)
        _print(f"  ✅ 「{target['name']}」已合并到「{new_name}」")
    else:
        db.update_practice_item_name(iid, new_name)
        _print(f"  ✅ 「{target['name']}」 → 「{new_name}」")


def _do_item():
    _print("\n─── 小科目操作 ───")
    _print("  a 增加  d 删除  r 改名  q 返回")
    op = _input("  选择: ").strip().lower()
    if op == 'a':
        _item_add()
    elif op == 'd':
        _item_delete()
    elif op == 'r':
        _item_rename()
    else:
        _print("  返回")


# ─────────────────────────────────────────
# 归属关系
# ─────────────────────────────────────────

def _relation_set():
    """设置归属关系"""
    items = db.get_practice_items(active_only=False)
    categories = get_categories()
    if not items:
        _print("  （无小科目）")
        return
    if not categories:
        _print("  （无大科目，请先增加大科目）")
        return

    cat_id_map = {str(c['id']): c['name'] for c in categories}
    cat_name_map = {c['name']: c['id'] for c in categories}

    _print("  可用大科目:")
    for c in categories:
        _print(f"    [{c['id']}] {c['name']}")
    _print("  格式: 小科目ID 大科目ID（空格分隔），一行一条，- 取消归属，直接回车返回\n")

    while True:
        line = _input("  > ").strip()
        if not line:
            _print("  完成归属设置")
            break
        if line == '-':
            # 取消全部归属
            for it in items:
                if it.get('category_id'):
                    set_item_category(it['name'], None)
            _print("  ✅ 已取消所有归属")
            continue
        parts = line.split()
        if len(parts) != 2:
            _print("  ⚠️  格式: 小科目ID 大科目ID")
            continue
        item_id_str, cat_id_str = parts
        try:
            item_id = int(item_id_str)
            cat_id = int(cat_id_str)
        except ValueError:
            _print("  ⚠️  ID必须是数字")
            continue
        item = next((it for it in items if it['id'] == item_id), None)
        if not item:
            _print(f"  ⚠️  小科目ID {item_id} 不存在")
            continue
        if cat_id_str == '-':
            set_item_category(item['name'], None)
            _print(f"    ✅ 「{item['name']}」取消归属")
        elif cat_id_str not in cat_id_map:
            _print(f"  ⚠️  大科目ID {cat_id} 不存在")
            continue
        else:
            set_item_category(item['name'], cat_id)
            _print(f"    ✅ 「{item['name']}」归属「{cat_id_map[cat_id_str]}」")


def _do_relation():
    _print("\n─── 归属关系操作 ───")
    _print("  s 逐条设置  q 返回")
    op = _input("  选择: ").strip().lower()
    if op == 's':
        _relation_set()
    else:
        _print("  返回")


# ─────────────────────────────────────────
# 主循环
# ─────────────────────────────────────────

def launch():
    _print("\n╔══════════════════════════════════════╗")
    _print("║      🎵 练习配置 - 增删改查            ║")
    _print("╚══════════════════════════════════════╝")

    while True:
        _show_current()
        _show_menu()
        choice = _input("\n▶ 选择: ").strip()

        if choice == '0':
            _print("\n👋 已退出配置")
            break
        elif choice == '1':
            _do_category()
        elif choice == '2':
            _do_item()
        elif choice == '3':
            _do_relation()
        else:
            _print("  无效选择，请输入 0-3")
