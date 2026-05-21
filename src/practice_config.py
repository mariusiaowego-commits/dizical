"""
大科目/小科目 配置
增删改查 - 规范：所有子菜单 while True + q 逐层返回
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


def _banner(title: str):
    """打印标题栏"""
    _print(f"\n╔{'═' * 40}╗")
    _print(f"║  🎵 {title}")
    _print(f"╚{'═' * 40}╝")


def _done():
    """操作完成后提示，可继续或返回"""
    _print("\n  ▶ 任意键返回菜单，q 退出一层")
    ch = _input("  > ").strip()
    if ch.lower() == 'q':
        return 'q'
    return 'continue'


# ─────────────────────────────────────────
# 归属关系
# ─────────────────────────────────────────

def _relation_set():
    """设置归属关系 - 自循环，q 逐层返回"""
    while True:
        items = db.get_practice_items(active_only=False, include_archived=True)
        categories = get_categories()

        _banner("归属关系")
        _print("\n  【说明】输入格式: 小科目ID 大科目ID")
        _print("  取消归属: 小科目ID -\n")

        if not categories:
            _print("  ⚠️  目前没有大科目，请先在主菜单增加大科目")
            _input("\n  ▶ 回车返回主菜单")
            return

        _print("  可用大科目:")
        for c in categories:
            _print(f"    [{c['id']}] {c['name']}")

        _print("\n  当前归属情况:")
        cat_map = {c['id']: c['name'] for c in categories}
        for it in items:
            cat = cat_map.get(it.get('category_id'), '')
            status = f" → {cat}" if cat else "（未归属）"
            archived_tag = " 📁" if it.get('is_archived') else ""
            _print(f"  [{it['item_id']}] {it['name']}{archived_tag}{status}")

        _print("\n  q 取消全部归属并返回  |  直接回车完成设置并返回")
        line = _input("\n  > ").strip()

        if line.lower() == 'q':
            # 取消全部归属
            for it in items:
                if it.get('category_id'):
                    set_item_category(it['name'], None)
            _print("  ✅ 已取消所有归属")
            return

        if not line:
            _print("  完成归属设置")
            return

        parts = line.split()
        if len(parts) != 2:
            _print("  ⚠️  格式: 小科目ID 大科目ID（用空格分隔）")
            continue

        item_id_str, cat_id_str = parts
        try:
            item_id = int(item_id_str)
        except ValueError:
            _print("  ⚠️  小科目ID必须是数字")
            continue

        item = next((it for it in items if it['item_id'] == item_id), None)
        if not item:
            _print(f"  ⚠️  小科目ID {item_id} 不存在")
            continue

        if cat_id_str == '-':
            set_item_category(item['name'], None)
            _print(f"  ✅ 「{item['name']}」已取消归属")
        elif cat_id_str not in {str(c['id']) for c in categories}:
            _print(f"  ⚠️  大科目ID {cat_id_str} 不存在")
            continue
        else:
            cat_name = next(c['name'] for c in categories if str(c['id']) == cat_id_str)
            set_item_category(item['name'], int(cat_id_str))
            _print(f"  ✅ 「{item['name']}」归属「{cat_name}」")


# ─────────────────────────────────────────
# 归档
# ─────────────────────────────────────────

def _do_archive():
    """归档管理 - 自循环，q 退到主菜单"""
    while True:
        all_items = db.get_practice_items(active_only=False, include_archived=True)
        archived = [it for it in all_items if it.get('is_archived')]
        cats = {c['id']: c['name'] for c in get_categories()}

        _banner("归档管理")

        _print("\n─── 已归档小科目 ───")
        if not archived:
            _print("  （暂无）")
        else:
            for it in archived:
                cat = cats.get(it.get('category_id'), '')
                path = f" → {cat}" if cat else ""
                _print(f"  [{it['item_id']}] {it['name']}{path}")
            _print(f"  共 {len(archived)} 个")

        _print("\n  a 归档小科目（设为老科目，不再出现在练习选择中）")
        _print("  u 取消归档（恢复为可练习科目）")
        _print("  q 返回主菜单")

        op = _input("\n  ▶ 选择: ").strip().lower()
        if op == 'q':
            return
        elif op == 'a':
            _archive_choose(switch_to=True)
        elif op == 'u':
            _archive_choose(switch_to=False)
        else:
            _print("  ⚠️  无效选择")


def _archive_choose(switch_to: bool):
    """归档/取消归档 - 自循环，q 退回 _do_archive"""
    action = "归档" if switch_to else "取消归档"
    state_label = "未归档" if switch_to else "已归档"

    while True:
        all_items = db.get_practice_items(active_only=False, include_archived=True)
        candidates = [it for it in all_items if bool(it.get('is_archived')) == (not switch_to)]
        cats = {c['id']: c['name'] for c in get_categories()}

        _banner(f"{action}小科目（当前: {state_label}）")

        if not candidates:
            _print(f"\n  没有需要{action}的小科目")
            _input("\n  ▶ 回车返回")
            return

        for it in candidates:
            cat = cats.get(it.get('category_id'), '')
            path = f" → {cat}" if cat else ""
            _print(f"  [{it['item_id']}] {it['name']}{path}")

        _print(f"\n  多个ID用空格分隔，q 返回上级")
        sid = _input(f"  ▶ 输入要{action}的小科目ID: ").strip()
        if sid.lower() == 'q':
            return
        if not sid:
            _print("  取消")
            continue

        try:
            ids = [int(x) for x in sid.split()]
        except ValueError:
            _print("  ⚠️  ID必须是数字")
            continue

        for iid in ids:
            target = next((it for it in candidates if it['item_id'] == iid), None)
            if not target:
                _print(f"  ⚠️  ID {iid} 不在列表中，跳过")
                continue
            if switch_to:
                db.archive_practice_item(iid)
                _print(f"  ✅ 「{target['name']}」已归档")
            else:
                db.unarchive_practice_item(iid)
                _print(f"  ✅ 「{target['name']}」已取消归档")

        remaining = [it for it in db.get_practice_items(active_only=False, include_archived=True) if it.get('is_archived')]
        _print(f"\n  当前已归档 {len(remaining)} 个")

        ch = _input("\n  ▶ 回车继续操作，q 返回上级: ").strip()
        if ch.lower() == 'q':
            return


# ─────────────────────────────────────────
# 大科目
# ─────────────────────────────────────────

def _do_category():
    """大科目管理 - 自循环，q 退到主菜单"""
    while True:
        categories = get_categories()
        items = db.get_practice_items(active_only=False, include_archived=True)

        _banner("大科目管理")

        _print("\n─── 当前大科目 ───")
        if not categories:
            _print("  （暂无）")
        else:
            for c in sorted(categories, key=lambda x: x['sort_order']):
                related = [i for i in items if i.get('category_id') == c['id']]
                names = '、'.join([i['name'] for i in related]) or '（无）'
                _print(f"  [{c['id']}] {c['name']}  →  {names}")

        _print("\n  a 增加大科目")
        _print("  d 删除大科目")
        _print("  r 改名大科目")
        _print("  s 重排顺序")
        _print("  q 返回主菜单")

        op = _input("\n  ▶ 选择: ").strip().lower()
        if op == 'q':
            return
        elif op == 'a':
            _category_add()
        elif op == 'd':
            _category_delete()
        elif op == 'r':
            _category_rename()
        elif op == 's':
            _category_sort()
        else:
            _print("  ⚠️  无效选择")


def _category_add():
    while True:
        _banner("增加大科目")
        _print("\n  多个名称用顿号、逗号或空格分隔，q 返回")
        raw = _input("  新大科目名称: ").strip()
        if raw.lower() == 'q':
            return
        if not raw:
            _print("  取消")
            continue
        names = [n.strip() for n in raw.replace('、', ',').replace('，', ',').split(',') if n.strip()]
        existing = {c['name'] for c in get_categories()}
        added = 0
        for name in names:
            if name in existing:
                _print(f"  ⚠️  「{name}」已存在，跳过")
            else:
                cid = add_category(name)
                _print(f"  ✅ [{cid}] {name}")
                added += 1
        _print(f"\n  共新增 {added} 个")
        if _input("\n  ▶ 回车继续增加，q 返回: ").strip().lower() == 'q':
            return


def _category_delete():
    while True:
        categories = get_categories()
        if not categories:
            _banner("删除大科目")
            _print("\n  （无大科目）")
            _input("\n  ▶ 回车返回: ")
            return

        _banner("删除大科目")
        for c in sorted(categories, key=lambda x: x['sort_order']):
            _print(f"  [{c['id']}] {c['name']}")
        _print("\n  多个ID用空格分隔，q 返回")
        sid = _input("  ▶ 输入要删除的大科目ID: ").strip()
        if sid.lower() == 'q':
            return
        if not sid:
            continue
        try:
            ids = [int(x) for x in sid.split()]
        except ValueError:
            _print("  ⚠️  无效ID")
            continue
        for cid in ids:
            target = next((c for c in categories if c['id'] == cid), None)
            if not target:
                _print(f"  ⚠️  ID {cid} 不存在，跳过")
                continue
            delete_category(cid)
            _print(f"  ✅ 已删除「{target['name']}」")


def _category_rename():
    while True:
        categories = get_categories()
        if not categories:
            _banner("改名大科目")
            _print("\n  （无大科目）")
            _input("\n  ▶ 回车返回: ")
            return

        _banner("改名大科目")
        for c in sorted(categories, key=lambda x: x['sort_order']):
            _print(f"  [{c['id']}] {c['name']}")
        sid = _input("\n  ▶ 输入要改名的大科目ID（q 返回）: ").strip()
        if sid.lower() == 'q':
            return
        if not sid:
            continue
        try:
            cid = int(sid)
        except ValueError:
            _print("  ⚠️  无效ID")
            continue
        target = next((c for c in categories if c['id'] == cid), None)
        if not target:
            _print("  ⚠️  未找到该大科目")
            continue
        new_name = _input(f"  新名称 [{target['name']}]: ").strip()
        if not new_name:
            _print("  取消")
            continue
        update_category(cid, new_name)
        _print(f"  ✅ 「{target['name']}」 → 「{new_name}」")
        if _input("\n  ▶ 回车继续改名，q 返回: ").strip().lower() == 'q':
            return


def _category_sort():
    while True:
        categories = get_categories()
        if not categories:
            _banner("重排顺序")
            _print("\n  （无大科目）")
            _input("\n  ▶ 回车返回: ")
            return

        _banner("重排顺序")
        _print("  当前顺序:")
        for c in sorted(categories, key=lambda x: x['sort_order']):
            _print(f"    [{c['id']}] {c['name']}")
        _print("\n  输入新顺序的ID列表（空格分隔），q 返回")
        ids_str = _input("  ▶ 新顺序: ").strip()
        if ids_str.lower() == 'q':
            return
        if not ids_str:
            continue
        try:
            ids = [int(x) for x in ids_str.split()]
        except ValueError:
            _print("  ⚠️  无效ID")
            continue

        cat_ids = {c['id'] for c in categories}
        # 验证：重复ID
        if len(ids) != len(set(ids)):
            dupes = [x for x in ids if ids.count(x) > 1]
            _print(f"  ⚠️  ID 列表有重复: {set(dupes)}")
            continue
        # 验证：覆盖完整性
        missing = cat_ids - set(ids)
        if missing:
            names = [next(c['name'] for c in categories if c['id'] == m) for m in missing]
            _print(f"  ⚠️  遗漏了 {len(missing)} 个大科目: {', '.join(names)}")
            continue
        if len(ids) != len(cat_ids):
            _print(f"  ⚠️  ID数量不对（应有 {len(cat_ids)} 个）")
            continue

        for i, cid in enumerate(ids, start=1):
            c = next(c for c in categories if c['id'] == cid)
            update_category(cid, c['name'], sort_order=i)
        _print(f"  ✅ 已更新顺序")

        if _input("\n  ▶ 回车返回: ").strip().lower() == 'q':
            return
        return


# ─────────────────────────────────────────
# 小科目
# ─────────────────────────────────────────

def _do_item():
    """小科目管理 - 自循环，q 退到主菜单"""
    while True:
        items = db.get_practice_items(active_only=False, include_archived=True)
        categories = get_categories()
        cat_map = {c['id']: c['name'] for c in categories}

        _banner("小科目管理")

        _print("\n─── 当前小科目 ───")
        if not items:
            _print("  （暂无）")
        else:
            for it in items:
                cat = cat_map.get(it.get('category_id'), '')
                path = f" → {cat}" if cat else "（未归属）"
                tag = " 📁" if it.get('is_archived') else ""
                _print(f"  [{it['item_id']}] {it['name']}{tag}  {path}")

        _print("\n  a 增加小科目")
        _print("  d 删除小科目")
        _print("  r 改名小科目")
        _print("  q 返回主菜单")

        op = _input("\n  ▶ 选择: ").strip().lower()
        if op == 'q':
            return
        elif op == 'a':
            _item_add()
        elif op == 'd':
            _item_delete()
        elif op == 'r':
            _item_rename()
        else:
            _print("  ⚠️  无效选择")


def _item_add():
    while True:
        _banner("增加小科目")
        _print("\n  多个名称用顿号、逗号或空格分隔，q 返回")
        raw = _input("  新小科目名称: ").strip()
        if raw.lower() == 'q':
            return
        if not raw:
            _print("  取消")
            continue
        names = [n.strip() for n in raw.replace('、', ',').replace('，', ',').split(',') if n.strip()]
        existing = {it['name'] for it in db.get_practice_items(active_only=False, include_archived=True)}
        added = 0
        for name in names:
            if name in existing:
                _print(f"  ⚠️  「{name}」已存在，跳过")
            else:
                iid = db.add_practice_item(name)
                _print(f"  ✅ [{iid}] {name}")
                added += 1
        _print(f"\n  共新增 {added} 个")
        if _input("\n  ▶ 回车继续增加，q 返回: ").strip().lower() == 'q':
            return


def _item_delete():
    while True:
        items = db.get_practice_items(active_only=False, include_archived=True)
        if not items:
            _banner("删除小科目")
            _print("\n  （无小科目）")
            _input("\n  ▶ 回车返回: ")
            return

        cats = {c['id']: c['name'] for c in get_categories()}
        _banner("删除小科目")
        for it in items:
            cat = cats.get(it.get('category_id'), '')
            path = f" → {cat}" if cat else ""
            tag = " 📁" if it.get('is_archived') else ""
            _print(f"  [{it['item_id']}] {it['name']}{tag}{path}")

        _print("\n  多个ID用空格分隔，q 返回")
        sid = _input("  ▶ 输入要删除的小科目ID: ").strip()
        if sid.lower() == 'q':
            return
        if not sid:
            continue
        try:
            ids = [int(x) for x in sid.split()]
        except ValueError:
            _print("  ⚠️  无效ID")
            continue
        item_map = {it['item_id']: it['name'] for it in items}
        for iid in ids:
            if iid not in item_map:
                _print(f"  ⚠️  ID {iid} 不存在，跳过")
                continue
            db.delete_practice_item(iid)
            _print(f"  ✅ 已删除「{item_map[iid]}」")


def _item_rename():
    while True:
        items = db.get_practice_items(active_only=False, include_archived=True)
        if not items:
            _banner("改名小科目")
            _print("\n  （无小科目）")
            _input("\n  ▶ 回车返回: ")
            return

        cats = {c['id']: c['name'] for c in get_categories()}
        _banner("改名小科目")
        for it in items:
            cat = cats.get(it.get('category_id'), '')
            path = f" → {cat}" if cat else ""
            tag = " 📁" if it.get('is_archived') else ""
            _print(f"  [{it['item_id']}] {it['name']}{tag}{path}")

        sid = _input("\n  ▶ 输入要改名的小科目ID（q 返回）: ").strip()
        if sid.lower() == 'q':
            return
        if not sid:
            continue
        try:
            iid = int(sid)
        except ValueError:
            _print("  ⚠️  无效ID")
            continue
        target = next((it for it in items if it['item_id'] == iid), None)
        if not target:
            _print("  ⚠️  未找到该小科目")
            continue
        new_name = _input(f"  新名称 [{target['name']}]: ").strip()
        if not new_name:
            _print("  取消")
            continue
        if new_name == target['name']:
            _print("  名字未变")
            continue
        existing = next((it for it in items if it['name'] == new_name and it['item_id'] != iid), None)
        if existing:
            _print(f"\n  ⚠️  「{new_name}」已存在（id={existing['item_id']}）")
            confirm = _input(f"  确认合并？「{target['name']}」数据将并入「{new_name}」[y/N]: ").strip().lower()
            if confirm in ('y', 'yes'):
                db.merge_practice_item(existing['item_id'], iid, target['name'], new_name)
                _print(f"  ✅ 「{target['name']}」已合并到「{new_name}」")
            else:
                _print("  取消合并")
        else:
            db.update_practice_item_name(iid, new_name)
            _print(f"  ✅ 「{target['name']}」 → 「{new_name}」")

        if _input("\n  ▶ 回车继续改名，q 返回: ").strip().lower() == 'q':
            return


# ─────────────────────────────────────────
# 主菜单
# ─────────────────────────────────────────

def _show_current():
    """显示当前配置总览（主菜单时调用）"""
    categories = get_categories()
    items = db.get_practice_items(active_only=False, include_archived=True)
    cats = {c['id']: c['name'] for c in categories}

    _print("\n─── 大科目 ───")
    if categories:
        for c in sorted(categories, key=lambda x: x['sort_order']):
            _print(f"  [{c['id']}] {c['name']}")
            related = sorted((i for i in items if i.get('category_id') == c['id']), key=lambda x: x.get('item_id', 0))
            if related:
                for i in related:
                    tag = "📁" if i.get('is_archived') else ""
                    _print(f"      [{i['item_id']}] {i['name']} {tag}")
            else:
                _print(f"      （无）")
    else:
        _print("  （空）")

    uncategorized = [i for i in items if not i.get('category_id')]
    _print("\n─── 未归属小科目 ───")
    if uncategorized:
        for it in uncategorized:
            tag = " 📁" if it.get('is_archived') else ""
            _print(f"  [{it['item_id']}] {it['name']}{tag}")
    else:
        _print("  （空）")

    archived = sorted((i for i in items if i.get('is_archived')), key=lambda x: x.get('item_id', 0))
    if archived:
        _print(f"\n─── 已归档小科目 ({len(archived)} 个) ───")
        for it in archived:
            _print(f"  [{it['item_id']}] {it['name']}")


def _show_menu():
    _print("")
    _print("╔══════════════════════════════════════╗")
    _print("║      🎵 练习配置                      ║")
    _print("╠══════════════════════════════════════╣")
    _print("║  1 大科目 - 增/删/改/重排序          ║")
    _print("║  2 小科目 - 增/删/改                 ║")
    _print("║  3 归属关系 - 设置/取消              ║")
    _print("║  4 归档管理                          ║")
    _print("║  0 退出                             ║")
    _print("╚══════════════════════════════════════╝")


def launch():
    """主入口 - 每次显示当前状态+菜单，用户选0才退出"""
    while True:
        _show_current()
        _show_menu()
        choice = _input("\n▶ 选择 (0-4): ").strip()

        if choice == '0':
            _print("\n👋 已退出配置")
            break
        elif choice == '1':
            _do_category()
        elif choice == '2':
            _do_item()
        elif choice == '3':
            _relation_set()
        elif choice == '4':
            _do_archive()
        else:
            _print("  ⚠️  无效选择，请输入 0-4")
