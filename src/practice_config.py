"""
大科目/小科目 配置
单次线性问答流程，一次性配置完毕
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
    categories = get_categories()
    items = db.get_practice_items(active_only=False)

    _print("\n─── 当前大科目 ───")
    if categories:
        for c in sorted(categories, key=lambda x: x['sort_order']):
            related = [i['name'] for i in items if i.get('category_id') == c['id']]
            cats_str = '、'.join(related) if related else '（无）'
            _print(f"  {c['name']}  →  {cats_str}")
    else:
        _print("  （空）")

    uncategorized = [i['name'] for i in items if not i.get('category_id')]
    _print("\n─── 无归属小科目 ───")
    if uncategorized:
        _print("  " + "、".join(uncategorized))
    else:
        _print("  （空）")


def _confirm(prompt: str) -> bool:
    while True:
        ans = _input(f"  {prompt} [y/N]: ").strip().lower()
        if ans in ('y', 'yes'):
            return True
        elif ans in ('', 'n', 'no'):
            return False
        _print("  请输入 y 或 n")


def _step_categories() -> List[Dict]:
    """步骤1：配置大科目"""
    categories = get_categories()

    _print("\n═══════ 步骤1：大科目 ═══════")
    if categories:
        _print("当前大科目：")
        for c in sorted(categories, key=lambda x: x['sort_order']):
            _print(f"  - {c['name']}")

    _print("\n输入新大科目名称（多个用顿号分隔），直接回车跳过：")
    names = _input("> ").strip()

    if not names:
        _print("  跳过")
        return categories

    result = list(categories)
    existing = {c['name'] for c in categories}

    for i, name in enumerate(names.replace('、', ' ').split(), start=1):
        name = name.strip()
        if not name:
            continue
        if name in existing:
            _print(f"  「{name}」已存在，跳过")
            continue
        cid = add_category(name, sort_order=i)
        result.append({'id': cid, 'name': name, 'sort_order': i})
        _print(f"  ✅ 新增大科目：「{name}」")

    return result


def _step_items() -> List[Dict]:
    """步骤2：配置小科目"""
    items = db.get_practice_items(active_only=False)

    _print("\n═══════ 步骤2：小科目 ═══════")
    if items:
        _print("当前小科目：")
        for it in items:
            _print(f"  - {it['name']}")

    _print("\n输入新小科目名称（多个用顿号分隔），直接回车跳过：")
    names = _input("> ").strip()

    if not names:
        _print("  跳过")
        return items

    result = list(items)
    existing = {it['name'] for it in items}

    for name in names.replace('、', ' ').split():
        name = name.strip()
        if not name:
            continue
        if name in existing:
            _print(f"  「{name}」已存在，跳过")
            continue
        # set_item_category 会自动新增小科目（归属留空）
        set_item_category(name, None)
        result.append({'id': None, 'name': name, 'category_id': None})
        _print(f"  ✅ 新增小科目：「{name}」")

    return db.get_practice_items(active_only=False)


def _step_relations(categories: List[Dict]):
    """步骤3：配置归属关系"""
    items = db.get_practice_items(active_only=False)

    _print("\n═══════ 步骤3：归属关系 ═══════")

    cat_map = {c['name']: c['id'] for c in categories}
    if not cat_map:
        _print("  没有大科目，无法配置归属，跳过")
        return

    _print(f"可选大科目：{' | '.join(cat_map.keys())}")
    _print("给小科目指定大科目（直接回车保持现状，- 取消归属）：\n")

    for item in items:
        item_name = item['name']
        current_cat_id = item.get('category_id')
        current_cat_name = next((c['name'] for c in categories if c['id'] == current_cat_id), None)

        hint = f"（归属：{current_cat_name}）" if current_cat_name else "（无归属）"

        ans = _input(f"  {item_name} {hint} → ").strip()

        if ans == '':
            continue
        elif ans == '-':
            set_item_category(item_name, None)
            _print(f"    已取消「{item_name}」归属")
        elif ans in cat_map:
            set_item_category(item_name, cat_map[ans])
            _print(f"    ✅「{item_name}」归属「{ans}」")
        else:
            _print(f"    ⚠️  未找到大科目「{ans}」，保持现状")


def launch():
    """主入口"""
    _print("\n╔══════════════════════════════════════╗")
    _print("║      🎵 练习配置 - 大科目/小科目       ║")
    _print("╚══════════════════════════════════════╝")

    _show_current()

    # 步骤1：大科目
    categories = _step_categories()

    # 步骤2：小科目
    items = _step_items()

    # 步骤3：归属关系
    _step_relations(categories)

    # 最终确认
    _print("\n─── 最终配置 ───")
    _show_current()

    _print("\n✅ 配置完成！")
    _print("提示：可用命令管理")
    _print("  大科目：dizical practice category list/add/update/del")
    _print("  小科目：dizical practice items")
    _print("  归属：  dizical practice category set-item <小科目> <大科目>")
