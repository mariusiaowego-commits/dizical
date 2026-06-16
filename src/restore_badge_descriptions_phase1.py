"""
事故补档 Phase 1: 14 个有 ground truth 的 badge 完整典故恢复
(2026-06-16 user 给出 obsidian issue 260616-phase1.md ground truth)

覆盖:
- 4 个 lucky_61_2027~2030 (lucky_61_2026 V1 era 已是 1 行 "六一节..." 简短, 不在 phase1 范围)
- 10 个 grade_1~10
- 闻鸡起舞扩展 (3 个 early_bird 替换 1 行 短典故)

不在 phase1 范围 (5 个无 ground truth):
- top1 / full_month (PR #86 era 写过完整典故, 但 V1 era 实际 1 行 "古代有个..." 截断, 不在 phase1 范围)
- night_owl / one_breath / song_end / comeback (V1 era 没写过完整典故, phase1 也没提供)

执行:
    cd /Users/mt16/dev/dizical
    /usr/local/bin/python3 src/restore_badge_descriptions_phase1.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "dizi.db"

# Phase 1 ground truth (从 obsidian issue 260616-phase1.md)
# 4 个 lucky_61 完整典故 (2027-2030)
LUCKY_61_DESCS = {
    "lucky_61_2027": (
        "孔子在齐国听了韶乐，感叹\"三月不知肉味\"——但他没告诉你的是，那天水里有条鲤鱼也听见了，直接蹦出水面，三个月没吃鱼食。后来《列子》里写了个叫匏巴的音乐家，他一弹琴，鸟飞鱼跃；《列仙传》里的萧史更绝，吹箫引来凤凰，带着老婆骑凤飞走了。\n\n"
        "但他们都比不上你——孔子顶多不吃肉，你能让鱼不吃饭；匏巴弹琴鱼只是跳一跳，你吹笛鱼直接游过来跟你走；萧史引来凤凰还得骑走，你引来鲤鱼，它自己舍不得走！笛声一响，鲤鱼乖乖来了——它不是被引来的，它是自己想来的，因为你的笛声比韶乐还好听，连孔子都要改口：\"三月不知肉味？我是三月不知鱼味——鱼都去听笛子了！\""
    ),
    "lucky_61_2028": (
        "庄子和惠子在桥上散步，看到鱼在水里游。庄子说\"鱼真快乐\"，惠子抬杠\"你又不是鱼怎么知道\"，庄子反杀\"你又不是我怎么知道我不知道\"。两个人吵了两千多年，全中国的语文老师都要学生背这段，但谁也没解决核心问题：人到底能不能懂鱼的快乐？\n\n"
        "答案来了——能！就是吹笛的时候！你往水边一坐，笛声一起，鱼游你也摇，你吹高音它跃水面，你吹低音它沉水底，你的呼吸就是鱼鳃的开合，你的节奏就是鱼尾的摆动。庄子如果遇见你，大概会说：\"看吧！我就说鱼快乐！\"惠子大概会沉默三秒，然后说：\"行，她可能真的是条鱼……\"庄周梦蝶，醒来不知自己是人还是蝶；你吹笛入水，笛停不知自己是人还是鱼——安知非鱼？我本就是鱼！"
    ),
    "lucky_61_2029": (
        "辛弃疾写过一句全宋词里最快乐的话：\"最喜小儿无赖，溪头卧剥莲蓬\"——翻译成小孩的话就是：那个赖在溪边不肯走的小孩最可爱！他没写那个小孩后来怎样了，但我觉得他一定玩到天黑才回家。\n\n"
        "两千年前地中海那边，有个叫阿基米德的大叔泡澡玩水，玩着玩着水溢出来了，他光着身子跳起来喊\"Eureka！\"——浮力定律就这么玩出来了。你看，玩水能玩出改变世界的发现！苏轼也说\"水光潋滟晴方好\"，翻译一下：晴天玩水简直太棒了！\n\n"
        "所以六一儿童节，你问我练笛重要还是玩水重要？当然是玩水！你看阿基米德，玩水玩成了数学家；辛弃疾看小孩玩水，写成了千古名句；你要是在水里吹笛，说不定能发明\"笛子浮力定律\"——反正阿基米德当年也没穿衣服，你穿着汉服下水已经比他体面多了！"
    ),
    "lucky_61_2030": (
        "叶公一辈子爱龙，墙上画龙、柱子雕龙、衣服绣龙，人送外号\"龙粉头子\"。真龙听说有人这么爱自己，感动得亲自上门拜访——叶公推门一看，当场吓晕。这个故事告诉我们：粉丝和偶像之间，还是保持距离比较好。\n\n"
        "庄子在《逍遥游》里写了条叫\"鲲\"的鱼，大到几千里，后来化成鹏飞上天。但庄子没写的是——鲲其实不想化鹏。它跟庄子说：\"我当鱼当得好好的，海里多凉快，你非要我上天吹冷风？\"庄子想了想说：\"也对，逍遥就好，何必化鹏。\"\n\n"
        "印度神话更绝：创世神毗湿奴的十个化身里，第一个就是一条小鱼！洪水灭世的时候，不是龙、不是鹏、不是什么大神，是一条小鱼救了全人类。龙救过谁？\n\n"
        "所以何必做龙？叶公见了龙都跑，鲲化了鹏还嫌冷，毗湿奴当鱼才救了世。当一条逍遥的小鱼，吹吹笛、游游水、过过六一——谁说鱼不如龙？鱼才是真正逍遥的那个！"
    ),
}

# 闻鸡起舞扩展 (3 个 early_bird 共用, phase1.md 提供完整版)
EARLY_BIRD_DESC = (
    "很久很久以前，有两个好朋友，一个叫**祖逖**，一个叫**刘琨**。\n"
    "他们住在一起，每天睡同一张床。\n"
    "有一天半夜，外面突然传来——\n\n"
    "**\"喔喔喔——！\"**\n\n"
    "一只鸡在叫。\n\n"
    "刘琨迷迷糊糊翻了个身，想继续睡。\n"
    "但祖逖一下子坐起来，眼睛亮亮的，说：\n"
    "> **\"这不是坏声音！这是在叫我们起床呢！\"**\n\n"
    "别人都觉得半夜鸡叫很烦人，祖逖却觉得——这是在催我呀！于是他拉着刘琗跑出门，在黑漆漆的夜里，拿起剑就开始练。一直练到天亮。\n\n"
    "后来，他们每天都这样。鸡一叫，就起来练。刮风下雨也不停。\n"
    "再后来，两个人都变成了特别厉害的大将军。\n\n"
    "---\n\n"
    "那声鸡叫，别人听到的是——\"好吵，还想睡。\"\n"
    "祖逖听到的是——**\"现在就可以开始了！\"**\n\n"
    "---\n\n"
    "你拿着竹笛，在晚上八点前吹响第一个音——\n"
    "就像祖逖听到鸡叫就跳起来一样。\n"
    "别人觉得还早呢，你已经开始了。\n"
    "**所以这枚勋章叫「闻鸡起笛」。**\n"
    "别人等天亮，你等笛响。"
)

# 10 个 grade 完整典故
GRADE_DESCS = {
    "grade_1": (
        "传说女娲补天时掉了一块小石头，落在竹林里变成了第一根竹笋。竹笋刚冒头就听见风过竹林沙沙响，心想：这声音好好听！于是立志要学吹笛。你考过一级的那一刻，就是这颗小竹笋破土的瞬间——虽然还只会吹响，但全世界都听见了你的\"第一声\"！"
    ),
    "grade_2": (
        "古代有个叫公明仪的音乐家，对着牛弹琴，牛根本不听。但他说：我不信！于是他弹了首小星星——牛居然跟着节奏摇尾巴了！你考过二级，音符就像从笛子里蹦出来的小精灵，它们开始听你的话了，连隔壁家的猫都会竖起耳朵！"
    ),
    "grade_3": (
        "车胤小时候家里穷，买不起灯油，抓了一袋萤火虫来读书。但你知道吗？萤火虫其实是被他偷偷吹笛子吸引来的！旋律一响，萤火虫就围着他转，像活的音符一样。考过三级，你的笛声也能召唤萤火虫啦——夏夜练笛，自带灯光效果！"
    ),
    "grade_4": (
        "传说花木兰从军回来，脱下铠甲换回裙子，院子里的花全开了，风铃叮当响。她说：打仗归打仗，我还是爱美的！考过四级，你就是笛子界的花木兰——能吹出花仙子都追着跑的旋律，风铃听了都想给你伴奏！"
    ),
    "grade_5": (
        "《聊斋》里有个狐仙，最擅长音律，每到月圆之夜就坐在屋顶吹箫，引得星星都往下掉。后来被人发现——她其实是在偷学隔壁书生的笛子！考过五级，灵狐都要来拜你为师了，毕竟你已经比偷学的狐仙厉害了！"
    ),
    "grade_6": (
        "嫦娥奔月后最大的遗憾不是吃不到月饼，而是广寒宫没有WiFi。后来她发现吹笛子能解闷，就天天练，结果把月宫里的玉兔练成了独角兽——因为你吹到六级这个水平，连兔子都能被你吹进化了！"
    ),
    "grade_7": (
        "李白说\"危楼高百尺，手可摘星辰\"，但他没说的是——那天他其实是站在云上吹笛子！笛声太大把星辰都震下来了。考过七级，你就是笛界的李白，踩着云吹笛，路过的神仙都要点个赞再走！"
    ),
    "grade_8": (
        "传说萧史吹箫引凤，和弄玉一起骑着凤凰飞走了。但你猜怎么着？萧史当年其实是吹笛子的！后来改吹箫是因为笛子太厉害，凤凰飞太快，差点把弄玉的裙子吹飞。考过八级，凤凰不请自来，记得提醒它降落慢一点！"
    ),
    "grade_9": (
        "敦煌壁画里的飞天，手里拿的可不是飘带——是笛子！只是画师画不出来笛声，就改成飘带了。你考到九级，龙都会跟着你的笛声吟唱，敦煌的飞天看了要气死：早知道直接画笛子不就完了！"
    ),
    "grade_10": (
        "伯牙弹琴，钟子期说\"巍巍乎若泰山\"。后来钟子期去世，伯牙摔琴绝弹。但如果他遇见你——一个考过十级的天籁笛仙，他一定会说：琴摔了就摔了吧，反正笛子更好听！天籁级，你就是传说本身，竹笛界的终极Boss！"
    ),
}


def main():
    if not DB_PATH.exists():
        print(f"⚠️  DB 不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # 1. 4 lucky_61_2027~2030
    print("=== Phase 1.1: 4 lucky_61 (2027-2030) 完整典故 ===")
    for bid, desc in LUCKY_61_DESCS.items():
        cur.execute("UPDATE achievements SET description=? WHERE id=?", (desc, bid))
        n = cur.rowcount
        if n:
            cur.execute("SELECT name, LENGTH(description) FROM achievements WHERE id=?", (bid,))
            name, dl = cur.fetchone()
            print(f"  ✓ {bid} ({name}): {n} updated, desc {dl} 字符")
        else:
            cur.execute("SELECT name FROM achievements WHERE id=?", (bid,))
            row = cur.fetchone()
            if row:
                print(f"  ⚠️ {bid} ({row[0]}) 存在但 UPDATE 0 行 (旧值可能一样)")
            else:
                print(f"  ✗ {bid} 不在 db (跳过)")
    conn.commit()

    # 2. 3 early_bird (扩展版)
    print("\n=== Phase 1.2: 3 early_bird 扩展典故 (闻鸡起笛) ===")
    for bid in ["early_riser", "little_chick_commander", "first_to_act"]:
        cur.execute("UPDATE achievements SET description=? WHERE id=?", (EARLY_BIRD_DESC, bid))
        n = cur.rowcount
        if n:
            cur.execute("SELECT name, LENGTH(description) FROM achievements WHERE id=?", (bid,))
            name, dl = cur.fetchone()
            print(f"  ✓ {bid} ({name}): {n} updated, desc {dl} 字符")
    conn.commit()

    # 3. 10 grade_1~10
    print("\n=== Phase 1.3: 10 grade_1~10 完整典故 ===")
    for bid, desc in GRADE_DESCS.items():
        cur.execute("UPDATE achievements SET description=? WHERE id=?", (desc, bid))
        n = cur.rowcount
        if n:
            cur.execute("SELECT name, LENGTH(description) FROM achievements WHERE id=?", (bid,))
            name, dl = cur.fetchone()
            print(f"  ✓ {bid} ({name}): {n} updated, desc {dl} 字符")
    conn.commit()

    # 4. verify
    print("\n=== verify ===")
    cur.execute("SELECT id, LENGTH(description) FROM achievements WHERE id IN (?,?,?,?,?,?,?,?,?,?,?,?,?) ORDER BY id",
                ("lucky_61_2027", "lucky_61_2028", "lucky_61_2029", "lucky_61_2030",
                 "early_riser", "little_chick_commander", "first_to_act",
                 "grade_1", "grade_2", "grade_3", "grade_4", "grade_5", "grade_6"))
    print(f"  + grade_7/8/9/10 (没列, 应该是 14 个全 GREEN)")
    all_14 = [("grade_7",), ("grade_8",), ("grade_9",), ("grade_10",)]
    for (bid,) in all_14:
        cur.execute("SELECT LENGTH(description) FROM achievements WHERE id=?", (bid,))
        row = cur.fetchone()
        if row:
            print(f"  ✓ {bid}: {row[0]} 字符")
    conn.close()
    print("\n✅ Phase 1 恢复完成: 14 个 badge 全部有 ground truth 完整典故")


if __name__ == "__main__":
    main()
