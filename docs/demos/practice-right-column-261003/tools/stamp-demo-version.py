#!/usr/bin/env python3
"""给每个 demo 页盖「demo 版本号」徽章 + 维护 VERSIONS.md 清单。

背景（dad 2026-10-08）：「demo 的版本迭代也最好搞一个 demo 版本号，否则我不知道哪个是哪个了，
因为 demo 要改很多次」。

版本口径（两级）：
  demo vX.Y     = 全局迭代轮次（X = 轮，Y = 同轮内的小改）
  卡 vN         = 单张卡自己的设计版本（文件名的 -vN 后缀）
一页的完整身份 = 「demo vX.Y · 卡 vN · 日期」，盖在页面顶栏，同时写进 VERSIONS.md。

用法：
  python3 tools/stamp-demo-version.py            # 按下面 TABLE 盖章 + 写 VERSIONS.md
  python3 tools/stamp-demo-version.py --check    # 只报差异，不写盘（CI 友好）
改动是幂等的：已有 <span class="demo-ver"> 就替换内容，不重复插。
"""
import pathlib, re, sys

DEMO = pathlib.Path(__file__).resolve().parent.parent
DEMO_VERSION = "v3.15"       # 全局：261028 计时读数守卫（点开始后 run 态只接受 MM:SS，总线推的时长不再覆盖倒计时）
DEMO_DATE = "2026-10-28"

# 文件 → (卡版本, 一句话状态)。卡版本对齐文件名后缀；无 vN 后缀的记 "—"。
TABLE = [
    ("dashboard-skin-01-v3.html",            "v3", "① 练习计时卡：拱与旋钮【同心】(偏差 0) · 拱半径收到 85px 深 24/32 可切 · 拱-边缘交接处圆角(左右不对称 0) · 点域 -120→120 与指针完全一致 · 点-拱净距 ≥10px · 页脚三格居中(边距 19.2/18)"),
    ("practice-duration-card-01-v3.html",    "v3", "⑥ 今日时长卡：★ 全站深色基准 · 刻度 = 每段起点 + 末段结束点(3 段→4 刻度) · 首刻度与首段左端对齐(差 0) · 虚线纯 1px 点线"),
    ("requests-card-01-v3.html",             "v3", "④ 老师要求卡：拖动露出下一张 + 前后 dot 都能看清 · dad 已定稿，本轮冻结"),
    ("metronome-01-v4.html",                 "v4", "② 节拍器卡：5 音色 + 音色抽屉 + 灯声同步 + 深墨接 D6 + 440 档真重排 + rAF 驱动灯效"),
    ("metronome-02-strip.html",              "v1", "②-B 节拍器竖长条挂件：宽 0.333 · bpm-label 右 2 个 ‹ › 箭头(速度滑杆已删) · 菜单不出滚动条"),
    ("metronome-01-v3.html",                 "v3", "② 节拍器卡：A 甲板分级 + 音色抽屉(不透明底板/外部点击与 ESC 收起) · 旋钮只调速去掉单击启停 · 440 档 LED 保持一字排开 · pad 档真双栏 · 改垂直位移拖拽 · 三处信息去冗余 · 补 data-term 兜底 · 甲板高 190→174 · 灯效改 rAF · 关强弱拍保留第 1 拍 0.55 微光"),
    ("compose-02.html",                      "v3", "组合视图：横排等高 608 · 手机 440 纵排等宽 · 组合1(计时+老师要求+今日时长)一屏不横滑"),
    ("today-records-01.html",                "v1", "⑤ 今日记录卡：折叠/展开 + 占位微条"),
    ("card-dashboard-skeleton-01.html",      "v1", "轨道骨架：吸附 + 左右切卡（dad 保留）"),
    ("ruler-shared-check.html",              "v1", "共享尺子接入自检页"),
    ("canvas-01.html",                       "v1", "★ 右栏顶替 pk-main-col：真画布 practice-ticket-v4-260920 逐字搬入（本体零改动）+ **等高卡片网格**（右栏每张卡高度 = 左栏票卡：1133 档 577）+ **三组合**（image23/24 结构：组合1 仪表盘+底部卧卡+竖条通高 / 组合2 一行并排 / 组合3 复合列）+ **卡槽窄孔**（孔比黑区窄 28px 肩，孔上下两半 z42/z46 夹住卡片）+ 双向联动总线（`DizicalPracticeBus`，负控真红）+ 轨内真横滑 · v3.10 卡槽插入卡改主题色（去黑、实色不透明）· v3.12 票夹变形动画不跳变（过渡态 .stage-morphing，1133 实测宽 360→341→165→56→50）· 440 横条内容不再被压扁（实测内容宽 71.3px，此前 4.2px）· 票面时长任何路径都回灌仪表盘 ruler"),
    ("compose-03.html",                      "v1", "组合自选台：5 预设 + 8 模块勾选 + localStorage + 一屏单行 + 横滑（槽位外框已拆）"),
    ("index.html",                           "—",  "总览页（入口）"),
    # 上一轮留档（对照用）
    ("dashboard-skin-01-v2.html",            "v2", "① 计时卡上一版（对照）"),
    ("metronome-01-v2.html",                 "v2", "② 节拍器上一版（对照）"),
    ("dashboard-bottom-blocks-01-v2.html",   "v2", "③ 下方三块（已并入 D1，留作对照）"),
    ("requests-card-01.html",                "v2", "④ 老师要求上一版（对照）"),
    ("practice-duration-card-01.html",       "v2", "⑥ 时长卡上一版（对照）"),
    ("compose-01.html",                      "v1", "组合视图上一版（卡片列车，对照）"),
    # ── 右栏卡片唯一真源（S19 轮：全视口统一窄孔卡槽 + 440 四项修复）──
    ("cards/card-a-dashboard.html",          "v3", "A 仪表盘卡：1133/744/440 全视口统一窄孔卡槽（孔肩 28px，卡比孔再窄 8px，露卡 1/5）· 440 指示灯落在黑区右肩内 · 孔左右缘严格对齐 MIC/电池（误差 0px）· 读数靠中 · 喇叭孔 56px 与按钮净距 ≥32px · v3.13 开始计时就绪门禁：票夹选齐前「开始」点不动（按钮 disabled + 原因提示），计时时长以票夹为真源"),
    ("cards/card-b-metronome-full.html",     "v3", "B 全功能节拍器卡（本轮未动，仅同步版本号）"),
    ("cards/card-s-metronome-strip.html",    "v1", "S 节拍器横条卡（feed 流下票夹变形为横 bar，本轮未动）"),
    ("cards/card-d-duration.html",           "v3", "D 今日练习时长卡（本轮未动，仅同步版本号）"),
    ("cards/card-r-records.html",            "v1", "R 今日练习记录卡（本轮未动，仅同步版本号）"),
    ("cards/card-q-requests.html",           "v3", "Q 老师要求卡（本轮未动，仅同步版本号）"),
]

MARK = '<span class="demo-ver"'
CSS_MARK = "/* demo-ver badge */"
CSS = """  /* demo-ver badge */
  .demo-ver{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;
    font-size:11px;letter-spacing:.02em;border:1px solid var(--dash-ink-a16);color:var(--dash-text-soft);
    background:var(--dash-surface-soft)}
  .demo-ver b{color:var(--dash-accent-text);font-weight:600}"""


def badge(text):
    return f'{MARK} title="demo 版本（工具自动盖，勿手改）">{text}</span>'


def inject(path: pathlib.Path, card_v, note):
    raw = path.read_text(encoding="utf-8")
    if path.name == "index.html":
        return raw, "总览页：不改正文（版本号由页头展示）"
    label = f'<b>demo {DEMO_VERSION}</b> · 卡 {card_v} · {DEMO_DATE}'
    if MARK in raw:
        new = re.sub(re.escape(MARK) + r'[^>]*>.*?</span>', badge(label), raw, count=1, flags=re.S)
        action = "替换已有徽章"
    else:
        # 插到顶栏第一个容器里（.bar / .stage-bar / .toolbar 都试），否则插在 <body> 之后
        m = re.search(r'<(div|header)[^>]*class="[^"]*(?:bar|toolbar|tools)[^"]*"[^>]*>', raw)
        if m:
            at = m.end()
            new = raw[:at] + "\n  " + badge(label) + raw[at:]
            action = "插入顶栏"
        else:
            m2 = re.search(r"<body[^>]*>", raw)
            at = m2.end() if m2 else 0
            new = raw[:at] + "\n" + badge(label) + raw[at:]
            action = "插入 body 起首"
    # 补徽章样式（只补一次）
    if CSS_MARK not in new:
        for anchor in ("</style>",):
            i = new.find(anchor)
            if i != -1:
                new = new[:i] + CSS + "\n" + new[i:]
                break
    return new, action


def main():
    check = "--check" in sys.argv
    rows, changed = [], []
    for name, card_v, note in TABLE:
        p = DEMO / name
        if not p.exists():
            rows.append((name, card_v, note, "缺失"))
            continue
        out, action = inject(p, card_v, note)
        rows.append((name, card_v, note, action))
        if out != p.read_text(encoding="utf-8"):
            changed.append((name, action))
            if not check:
                p.write_text(out, encoding="utf-8")

    manifest = DEMO / "VERSIONS.md"
    lines = ["---", "source: ai-agent", "project: dizical",
             "sprint: sprint-26100602-round2-mrd2610062214", f"updated: {DEMO_DATE}", "---", "",
             "# demo 版本清单（自动生成，勿手改本体）", "",
             f"**当前 demo 版本：{DEMO_VERSION}**（{DEMO_DATE}）　口径：`demo vX.Y` = 全局轮次；`卡 vN` = 单卡设计版本", "",
             "| 页面 | demo 版本 | 卡版本 | 说明 |", "|:--|:--|:--|:--|"]
    for name, card_v, note in TABLE:
        lines.append(f"| `{name}` | {DEMO_VERSION} | {card_v} | {note} |")
    lines += ["", "## 历史轮次", "",
              "- **demo v1.0**（2026-10-03/04）：W1–W7 各卡首版 + 骨架 + 共享尺子（文件后缀 `-v2` 的就是那一轮）",
              "- **demo v2.0**（2026-10-08）：2610062214 反馈落地（D1/D2/D4/D6/compose + 架构级作用域修复）",
              "- **demo v2.1**（2026-10-08）：节拍器音色优化 —— 4 种音色（木鱼 / 电子滴答 / 牛铃 / 鼓槌）"
              "+ 灯声同步（灯走音频时钟，不再 setTimeout）+ 四拍等强（dad 明确不要第 1 拍重音）",
              "- **demo v2.2**（2026-10-08）：dad `## 2610081651` 反馈落地 —— 拱交错重做（拱-尺呼吸带 6px→50px）"
              "· D6 定为全站深色基准 · 第 5 种音色 classic（响亮默认声）· 设置挪弹窗 · 新增竖长条挂件卡 ·"
              "细体字 0–9 全套 · 花开增量动效 · 麦克风真驱动 + 金属沉头回归",
              "- **demo v2.3**（2026-10-09）：dad `## 2610090827` 反馈落地 —— 弧两肩零侵入（三探针 0，间隙 30.1px）"
              "· 时间读数提权为 Hero（12→20 / 11→22 / 12→18px）· D6 虚线根因修复 + 时分秒联动 · ④ 拖动露下张 + 前后点可见"
              "· 竖条卡布局重做 · 组合页横排等高 608 + 手机纵排等宽 + 组合1 · 白字压底改 --dash-coral-solid/#CC3B3B 与"
              " --dash-accent-solid/#B8531F（对比度 0 不合格）",
              "- **demo v2.5**（2026-10-10）：dad `## 2610100854` 反馈落地 —— D1 拱与旋钮**同心**（实测偏差 0，此前点环/拱心相差 110px）、拱半径 140→85px、"
              "拱与面板边缘交接处加**圆角**（左右不对称 0，此前左侧是折角）· 点域 -120→120 与指针**完全一致**（此前只 152°，差 88°）· "
              "页脚三格**居中 + 安全边距** 19.2/18px（此前右文字溢出格子并贴边）· "
              "D6 刻度语义 = **每段起点 + 末段结束点**（3 段→4 刻度，首刻度与首段左端差 0）· "
              "D2 音色抽屉改**不透明底板**（与主按钮/旋钮/预设相交 0；外部点击 / ESC / 再点均可收起）· 旋钮**只调速**去掉单击启停 · "
              "440 档 LED 保持**一字排开**（不再 2×2）· pad 档**真双栏**（overlapX −73，第 2 列不再空）· 拖拽改**垂直位移**（脱离 atan2 挡读数）· "
              "三处速度信息**去冗余**（顶 4/4+强弱拍 / 中 82 BPM / 底 萨丽哈★）· 预设补 `data-term` + 非预设 BPM 中文术语兜底 · "
              "甲板高 190→174（保留 A 的形态阶梯）· 灯效改 **rAF + audioCtx.currentTime**（LED 路径断言禁止 setTimeout）· "
              "关强弱拍时第 1 拍保留 0.55 珊瑚微光（音频侧仍四拍同频同增益）",
              "- **demo v2.6**（2026-10-10）：dad `## 2610101121` 反馈落地 —— D1 拱与面板交接处外凸**耳片改内凹圆角 16px**（页顶留 12/16 开关；左右不对称 0 / 切线连续 true / 拱同心偏差 0 / 点-拱净距 10px）· "
              "D1 计时读数**倒计时改正向计时**（0→3 秒递增，方向 `forward_elapsed`，标签不再是\"剩余\"）· "
              "D1 右侧 BPM 改用 **Range 量文字墨迹**（1133 档 25.2px / 440 档 25px，此前元素盒子看着 18px、文字墨迹只剩 4px）· "
              "D6 刻度行**贴线 2px** · 虚线在橙胶囊**居中 0** · 数字 **6 与 9 改正圆**（宽高比 1）+ 笔画净空 0.8px（此前搭接交叉）· "
              "D2 主按钮改 **52×128 r14**、文案「启动节拍器」→「**开始/暂停**」2 字 + 音色入口成**胶囊**挂主按钮**右侧同一排**（中心差 0）、试听进抽屉、甲板高 190→124 · "
              "compose 组合1 = **上仪表盘整行 + 下两张并排**（上宽 586 = 下合计 586，偏差 0）",
              "- **demo v2.7**（2026-10-10）：dad `## 2610101554` 反馈落地 —— D1 默认档改 **浅凹 24 / 圆角 16 / 20 点**且 20 点点径**减到 4.5px**（16 点时 6px）· "
              "谱架键换**沉头浅凹语言**（idle 对比度 2.29→**7.33**、补激活态 4.93、**外投影 2 层→0 层**），该行改「主控件行 + 说明行」后三列 **centerline 极差 18.50→0** · "
              "`diag-card` 框套框重写为**单框**（容器框 2→1、嵌套 1→0 对、竖扫描线 4→2 条），顺手修深墨皮肤**白底白字**（状态 1.05→15.92 / 提示 1.33→12.52）· "
              "`c-left` 与 `cover-col` **同中轴**（偏差 0），ruler 266→242 缩短 · "
              "D6 `timeline-rail-capsule` 高度 **34→51**（×1.5）、dash 下新增**练习时长文字**「42 分钟」（90 → 1.5 小时）、刻度与文字到 dash 各留 **6px** · "
              "D2 甲板**推倒重做三层**（释义层 13px + 意大利语术语 / 主操作台 70%+30% 同高 52 / 预设两行滑动药丸 h34 r9999）+ 层间距 **16/12/18** + 卡底 20，± 键改 **44×44 纯圆浅色浮键**（与旋钮 16px 呼吸）· "
              "预设标签改**数据驱动**（取自 `weekly_assignments` 当前科目老师要求的速度，样式抄左栏 `.pk-pill`，黑白两皮肤）· 旋钮拖动改**水平**（左→右 = 最大）",
              "- **demo v2.8**（2026-10-10）：dad `## 2610102107` 反馈落地 —— D1 谱架模式键按参考图（新拟物凸起浮雕）重做：无硬边框 / 1 层柔和外投影 alpha 0.06 / 顶部内高光 / 图标在上文字在下 **同轴 0px**，文案严格居中（左右留白 **3 / 3**）；440 档键撑满列宽不再溢出 · D1 计时读数改用 **D6 时长卡的空心 monoline 数字**（抽 `shared/hollow-digits.js`）并**放大 3 倍**（1133 档 **60px** = 基准 20×3；744 档 66 / 440 档 54），**去掉「已练」字样**只留数字计时 · D6 `rail-duration-row` / `time-ticks-row` 更贴近 dash（CSS 偏移 8 → 3.5 / 5.5px，canvas 墨迹净距 **5.07 / 4.86px**，仍在 ≥4 安全距离内）且字重 **800 → 400** 细体 · D2 744 布局重构：**贯通卡顶的中枢栏**（4/4 徽标 + 4 粒灯单行居中偏移 **0.02px** + 强弱拍胶囊 + 1px 细分割线）+ 双栏 **42% : 58%** + 左栏 38×38 圆键（与旋钮 18px / 与开始键 29.55px）+ 右栏 L2 **双列网格**任务卡（32 段文字 **0 裁切**）+ L3 药丸 h32 r9999；`ps-row` 横向拖拽/滚轮/键盘可滑（根因 `scroll-behavior: smooth` + 缺指针拖拽）；音色抽屉改**贴按钮弹出**（右缘对齐差 0 / 竖直 6px / z25）；甲板按钮视觉高 **52 → 26** 且用伪元素把命中区补回 **44** · 另出独立对照卡 `metronome-01-v5.html`（pixel 版，同一规格另一实现，供二选一）· 参考渲染图 `assets/metronome-744-render-261010.png`（Nous Portal image_generate）",
              "- **demo v2.9**（2026-10-10）：dad 追加 5 条 —— ① D1 `readout` 准备态在分钟数字**右侧**加「分钟」小字（**11px / 底部对齐差 0 / 在数字右侧 / 计时中隐藏**）· ② compose-02 组合1 窄槽降级：实测并排需要 **656px**（340+16+300）→ 820 内宽 788 **仍并排**、620 内宽 588 与 460 内宽 428 **降为一行一张**（三档 `hasScrollX/cardsOverflow` 全 false）· ③ 全部 10 张卡的撞色/鲜艳色统一取 D6 `timeline-rail-capsule` 的 **`--dash-accent` = #FF5722 朱橙**（派生 `-soft #FF8A5C` / 浅底文字 `#A04217` / 深墨文字 `#FF9E7A` / 白字压底 `-solid #B8531F`），并写入核心 design：`uiux-asset-library/design-system/dizicute/DESIGN.md` §核心颜色 + dizical `DESIGN.md` 同步 · ④ `src/` 后端 `first_practice_at` 在**沙盒库**跑通（dry-run 待回填 325 / 留 NULL 13 → apply → 再跑 0 幂等 → 读接口返回 `first_practice_at` + `span_seconds`，生产库一行未动）",
              "- **demo v3.0**（2026-10-11）：右栏定稿轮 —— ① D1 三处修正：谱架键**中轴与所在列/纵向模块对齐（实测差 0）**、右留白 24 与列同口径；计时开始后「分钟」单位隐藏（根因：实值是 `data-mode=\"run\"`，旧选择器写的 `running` 永不匹配）；`grille-6x8.variant-countersink` 准备态**完全静止**、运行态 `waveRippleUp` **自下而上**（底孔延迟 0.105s → 顶孔 0.665s）、**与 cover-frame 同宽 72px（差 0）**、8 列 × 8 行 64 孔 · ② 朱橙 `#FF5722` 按「与珊瑚合作、不替代」重新融入核心 design：珊瑚仍是第一主色、**暖橙 `#FF8C5A` 还原保留**、朱橙新立为第二主色（能量/进度/强度），demo 另立 `--dash-vermilion*` 一族（契约 70 → 77 名，含 4 张留档页 + 2 张骨架页补齐）· ③ 新增组合选择页 `compose-03.html`：5 个预设 + 8 模块自由勾选（localStorage 记忆）+ **一屏单行**（rows=1 断言）+ 塞不下**横向滚动**（实测 track clientW 1133 / scrollW 2442 真能滚）· ④ 并入计划 `plan-merge-261010f.md`（左栏票根 × 右栏六卡，4 步走 + 映射表 + 风险对策 + 里程碑）",
              "- **demo v3.1**（2026-10-11）：右栏并进真画布 —— ① D1 孔阵 `grille-6x8.variant-countersink` 从 **CSS 自循环**改为**真实麦克风电平驱动**（`AnalyserNode` 时域 RMS 做总强度 + 频域分段做列差异；静音全基态、无自循环动画；电平 0.35 只亮底排、1.0 全 **64 孔**亮到 scale 1.42 + 朱橙辉光；暴露 `__grilleLevel(v)` 注入 + `__grilleMode`；真机麦克风采样 headless 标 SKIPPED）· ② 共享件 `shared/hollow-digits.js` 数字内部**黑块**修复：`<g>` 缺 `fill` 吃到 SVG 默认纯黑 → 补 `fill=\"none\"`，实测渲染 5 元素 fill 全 none / 黑填充 0 · ③ 深墨皮肤「分钟」小字色 `--dash-text-soft` 解析成 #666 → 实测改后 `rgba(255,248,240,0.62)`、对面板对比度 **15.92** · ④ 新增 `canvas-01.html`：真画布 `practice-ticket-v4-260920.html` 用 `srcdoc` 逐字搬入（**本体零改动** sha256 前 16 位 `e86d4bc56163218d`），模块列挂进 **`#pkMainCol.pk-main-col` 顶替其内容**（原 7 块实测全 0：`#pkInstrCard` / `#pkReqCard` / `#pkSlotIdle` / `#pkStartBtn` / `.timer-block` / `.pk-slot4-box` / `.pk-running-telemetry`）；模块祖先链实测命中 pk-main-col；卡外**无壳**（4 层父级 border 0px none / radius 0px / bg 透明 / shadow none）；轨内真横滑（`#czRail` clientW 863 / scrollW 2516 / overflow-x auto，三次采样 0→827→0）；**插入卡槽动画**在仪表盘之上（待命 `getAnimations()`=0 + 两次 transform 均 none + 与槽不相交 gap 14px；触发后几何相交、`miniTop 90 = slotTop 90` 落定、`dashMode prep→run`、缓动 `cubic-bezier(.34,1.56,.64,1)`、声明 280ms / observedMs 308.4 fallback）· ⑤ compose-03 槽位外框按 dad 意见**全拆**（border / radius 20 / 底色 / 阴影删除）",
              "- **demo v3.2**（2026-10-11）：按 agy 独立 review（`review-agy-canvas-261011.md`：结论「暂不建议交付」+ P0-1/P0-2/P1-1/P1-2/P2-1/P2-2）与 §6 真窗口复验修缮 ——① **P0-1 高度击穿**修：模块列底实测 717/736/750 → 票卡 654（越界 61~96px）→ 改 `syncRailBudget()` 运行时算 `rail.maxHeight`，复验真窗口 1280/1133 三预设 `modColBottom 686.0 = ticketBottom 686.0`（越界 **0.0px**）·② **P0-2 窄屏堆叠**修：`@media (max-width:1023px)` 注入画布文档内 + `setVp()` 联动画布 iframe 宽度（原来只改卡片 `data-vp`）→ 真 744 窗口 column/580/580/行数=模块数、真 440 column/408/408；**桌面窗口点「744」也真生效**（实测 docClientW 744 · 轨 580/580 无横滑 · 行数 2/3/6）；负控窄屏强撑单行 440 档 66 红 / 744 档 71 红 ·③ **P1-1 状态机桥接**：落定调画布 `enterRun()`（内容未选先兜底 `content_options[0]`）+ 监听 `#pkStateToggle` 双向联动 → 实测左侧真实票卡 380 → **220** 真收窄、`enterRun 已进态`、复位 `exitRun 已复位` 回 379 ·④ **P1-2 深墨同翻**：走 `CANVAS_SCOPE` 运行时注入（画布源文件零改动）→ 实测 ink：stageBg `rgb(20,24,28)` / ticketBg `rgb(30,36,43)` / topBg `rgb(26,30,34)`；light 三者 transparent；新断言 C1b 查**画布本体实测底色**（上轮那条「验了等于没验」的 C1 已换掉）·⑤ **P2-1 兜底抢跑**修：`FALLBACK_MS` 320 → **500** 且等待期间**禁 cancel**（cancel 会让 onfinish 永久失去机会）→ 真时钟空载 onfinish 293ms / 抖 60ms 351 / 抖 80ms 372 / 事件不派发档（`?swallowfinish=1`）onfinish-by-clock 752；报告口径拆开 `animDurationMs`(280) 与 `measureSpanMs`；审计环境确实拿不到动画时**如实标 SKIPPED + 真窗口实测数**（不写成绿）·⑥ 我（hermes）本人复算：普通浏览器会话 `?audit=1` → `verdict ASSERT_OK` / `failures []` / 24 格；`insert.after.landedBy onfinish`（landedAt 441.2ms，兜底 500）；verify-demos canvas-01 + compose-03 双 OK、对比度 0、画布 sha256 `e86d4bc56163218d` 保持",
              "- **demo v3.3**（2026-10-13）：dad 等高反馈（左栏票卡 360×1024 vs 右栏仪表盘不等高）+ 三组合落地 ——① **等高卡片网格**：右栏每张卡高度 == 左栏票卡（1133 档票卡 360×577；组合1 `A326+12+(D/R 239)=577`、组合2 `A/S/R 全 577`、组合3 `B385+12+D180=577`，底边全 = 票卡底 635）·② **高度回环根治**：iframe 高度不再由画布 `scrollHeight` 反推（实测 `iframe.clientHeight 656 == 画布 scrollHeight 656`，且票卡不被竖切）·③ **卡槽**：接缝 slot 底 51 → 仪表盘顶 58 = **+7px**（此前 −54 重叠）；插入动画全撤（`runInsert`/`FALLBACK_MS`/`insertTicket` 计数 0）·④ **组合树**按 `参考图文字基线-261012.md`（image23/24）落地，可见模块集合 == `state.mods` 三组合逐一命中 ·⑤ **联动双向真通**：`DizicalPracticeBus` 左 60→63 时右 82→85 逐次跟随、反向右 +1 左跟随、组合重挂后仍通；`?negctl=bus` 真报红且 verdict 写明「右栏 82 没跟着变（左栏 62）」（不再静默降级）·⑥ 画布源 `practice-ticket-v4-260920.html` 零改动（sha256 `e86d4bc56163218d`）；`verify-demos` 16 页 OK / 0 FAIL、`token-contrast` 不合格 0",
              "- **demo v3.5**（2026-10-16）：dad 文档 `PRDs/2610160819-demov3.4问题.md` 八条整轮修复 ——① **A 卡错位/裁切根治**：组合1 里旋钮与「开始/提前结束/按钮组」相交 499.5/790.9/1879.6px² → 0（旋钮不再压按钮）、`#panel` 内部裁 54 → 0、`#mid` 裁 55 → 0、封面名 0×0 → 34.3×13.2 可见、读数行 cx 由 +55px 偏 → == 卡中轴 ·② **arc 点环同心**：20 个点到旋钮圆心半径 106.26~106.38（散布 0.13px）＝几何同心，点不再落在旋钮面上 ·③ **缺口咬深 = 规格**：mask 圆心 y 由写死 242.5px → 按面板高计算，实测咬深 24px（= `--notch-depth`）·④ **卡槽**：`#pkPunchSlotWrap` 18 → 50px（agy 规格 48~54），落在 A 卡内、主屏之上 ·⑤ **今日记录卡**：迷你卡底色 rgb(232,229,224) 灰 → rgb(22,26,30)=#161A1E（与时长卡同族）· ⑥ **记录弹窗**：`#czPopFrame` 渲染「科目|总时长|速度|单次|明细|占比」12 行明细，且弹窗内 demo chrome（徽章/视口/皮肤切换）全隐 ·⑦ **744/440 内容驱动高度**（旧六卡写死 460）：744 = A573/B681/S108/D213/R719/Q556、440 = A678/B768/S345/D213/R797/Q556，六值异构且卡内滚动条 0（旧 R 缺 67/169px）·⑧ **S 竖条 → 横条**：h(S) 150 → 108（agy 判据 ≤120），内部 top/mid/bot 横排 ·⑨ **D 卡元素恢复**（组合1 224 宽）：空心时钟 135×44 + 时间轴胶囊 206×51(4 刻度) + 图标组，下方空白 63% → 0% ·⑩ 画布源零改动（sha256 `e86d4bc56163218d`）；`verify-demos` 16 页 OK / 0 FAIL、`token-contrast` 不合格 0",
              "- **demo v3.6**（2026-10-22）：八条整轮落地 —— ① 圆钮接缝 1px 外壳描边 · ② 卡槽与仪表盘等宽 · ③ 插卡改自上而下 · ④ 去灰直角（`.diag-card` 无上边框 + 卧卡 dash 圆角裁切）· ⑤ BPM 左票/竖条/仪表盘绝对值同步 · ⑥ 组合1 时长卡 32px 时钟 + 44px 时间轴胶囊 · ⑦ 440 顶栏双行 · ⑧ 440 面板底部 78px 留白；verify-demos canvas-01 OK、token-contrast 0 不合格、R2 0 failures",
              "- **demo v3.7**（2026-10-26）：S17+S18 整轮落地 —— ① **卡槽窄孔化**：槽体透明，黑区上沿只留一道比黑区窄 28px 肩的缝；孔上下两半（`::after` z42 垫卡后 / `::before` z46 盖卡底）把卡片夹在中间 = 卡片从孔中穿过；孔所有状态常驻（准备态也在）·② **插卡动画不穿帮**：`pkCardToSlot` / `pkCardToSlotFeed` 全程 `translateY ≤ 0`（72% 归座 0px → 85% 回弹 −2px → 100% 落定 0px），逐帧实测卡底越过孔底 **0.00px**、回弹期卡底留在下半孔遮罩内 **7.00px** ·③ **MIC / 电池对齐卡槽孔缘**：`.status` 改 `padding: 0 var(--cz-status-pad-x,16px)`，实测 1133 C1/C2/C3 两态 `micLeftFromPanel = holeLeftFromPanel = 28.0px`、`batRightFromPanel = holeRightFromPanel = 28.0px`（误差 0.0px）·④ **读数与封面图上下居中**：新增 `alignReadoutWithCover()` 写 `--cz-readout-dx/dy`，实测 `digitsCoverCyDiff = 0.0px`，水平落在封面图右缘与右侧安全边界中点偏左 6px ·⑤ **页脚贴黑区下缘**：`--cz-foot-top = panel 高 − 20px`（不再由圆点弧顶牵制），实测「今日 xx分」距底 4.0px、「BPM xx」距底 0–2px ·⑥ **卡槽指示灯常驻同位**：`.cz-slot-led` 准备态/计时态同一孔肩位置，feed 流无孔肩则隐藏 ·⑦ **feed 流修右侧溢出 24px**（`crownInset` 统一 12px）+ 440 档旋钮 176→136px；门禁 `verify.js --strict` 11/11 PASS、6 模板字节级一致、CSS `[data-vp]` 0 处",
              "- **demo v3.8**（2026-10-27）：S19 整轮落地 —— ① **744 / 440 全面复刻 1133 窄孔卡槽**：删除 `isFeedA` 整带露卡分支，三视口统一 `data-hole=\"1\"`、`holeInset=28`、`cardInset=36`、露卡 1/5（实测 exposedRatio 19.8%–20.1%）·② **440 指示灯与卡槽对称根治**：`updateCardSlotGeometry()` 直接读取 iframe 内 `#panel` 真实边界定位 `.cz-astack-crown`，并修复 `syncAll`/`measureCardContent` 首次加载少算 `--cz-panel-pt` 触发纵向滚动条挤歪黑区 15px 的根因，LED 定位在孔右肩中点 `right: 10.5px`（实测 440/744/1133 `holeLeft - micLeft = 0.0px`、`holeRight - batRight = 0.0px`、`holeSymDiff = 0.0px`、`ledInsidePanel = true`）·③ **440 读数靠中**：`alignReadoutWithCover()` 准备态扣除「分钟」下标半宽往左收敛（440 下数字中心 215.7px vs 面板中心 220.0px），计时态 4 位数自动保留与封面 ≥14px 安全边距 ·④ **440 按钮与喇叭孔零重叠**：440 档 `.grille-6x8` 缩至 56×56px、`.grid-3col` 列宽 64px + `column-gap: 8px`，`alignSpeakerWithCover()` 限制最大右偏保留 ≥12px 净距（实测 440 下 `grillePillGap = 32–34px`）；门禁 `verify.js --strict` 11/11 PASS", "",
              "- **demo v3.11**（2026-10-27）：S22 票夹改制 —— ① **票夹空态**：首次打开（无任何选择）时科目与本次练习内容置空，等用户首次选择·② **选满两项即变形**：不再等点仪表盘「开始」，选完科目 + 内容立刻触发「票夹 → 黑色窄条」动画（`.stage-bar` 与计时态 `.stage-running` 解耦，插卡 / 「进行中」标签 / run-only 显隐都不提前触发）·③ **窄条上「重新选择」按钮**：同 UI 规范，点了窄条变回票夹 UI，**科目与内容保留最近一次选择**，计时期间置灰不可点·④ **ruler ↔ 票夹时长联动**：仪表盘拖 ruler 改时长，票面与窄条同步；⑤ 修掉三个自测回归：旧兜底定时器把计时态打回准备态（加代际令牌）、窄条塌成 0 高（`--cz-bar-h`）、剩余时间倒读（去掉 rotate(180deg) 改横排 11px）",
              "- **demo v3.12**（2026-10-27）：S22 收尾 + agy 复核轮 —— ① **票夹变形动画不跳变**（P0）：`.stage-bar` 用 `!important` 锁死几何，GSAP 内联补间被样式表 `!important` 覆盖，票夹在补间首帧直接跳成 50px；新增过渡态 `.stage-morphing`（只负责把窄条显示出来、不锁几何），动画结束再切回 `.stage-bar` 稳态。实测 1133 宽 360→341→165→56→50（5 档）、744/440 高 791→728→279→61→52（6/5 档），反向「重新选择」宽 50→60→196→347→360（15 档）·② **440 横条内容不再被压扁**（P1）：≤600 隐藏窄条内冗余 BPM、标签「本次内容」→「本次」、压缩内边距，实测内容宽 4.2px → **71.3px**（scrollWidth 71 ≤ clientWidth，无裁切）·③ **票面时长任何路径回灌仪表盘**（P1）：`ttSetDuration` 包装层补 `bus.duration(duration,'left_ticket')`，实测点票面时长键 → 票面 11 / 仪表盘 ruler 11 / 窄条 11:00 三处一致（此前 ruler 停在 10）·④ **窄条高度随视口重算**（P2）：`refreshBarHeight()` 挂在 resize 上，撤 `.stage-bar` 量票卡自然高度再写回 `--cz-bar-h`（实测 651px→650px）·⑤ 「重新选择」期间保留最近一次选择、计时中置灰；门禁 `verify.js --strict` 15/15 PASS、6 模板字节级一致、CSS `[data-vp]` 0 处", "",
              "- **demo v3.13**（2026-10-28）：开始计时就绪门禁 —— ① **票夹是唯一真源**：`__czPracticeReady()` 汇总「科目 + 本次练习内容 + 时长」三项，未选齐时仪表盘「开始」`disabled`（标题与读数行给出原因），点击不产生任何计时；选齐后按钮恢复，**计时时长取票夹那份**（实测票夹 18 分 → A 卡 ruler 18 → 计时 18，窄条剩余 18:00）·② **去掉自动补选**：`enterRun()` 不再替用户挑科目/内容（此前会记下一份用户从没选过的内容）；demo 调试壳 `setCanvasStage('run')` 仍代选，那是壳行为不是产品行为·③ **总线新增 ready 通道**：`DizicalPracticeBus.ready(flag, reason)` → A 卡 `setPracticeReady()`，卡重挂/载入时 `settleAfterReady()` 重新推送·④ 门禁新增项 16（就绪门禁 × 3 视口）；`verify.js --strict` 16/16 PASS",
              "- **demo v3.14**（2026-10-28）：就绪引导（onboarding coach mark）—— ① **置灰也要能点**：仪表盘「开始」不再用真 `disabled`（它会吞掉 click，引导永远弹不出来），改成 `aria-disabled=true` + `is-locked` 视觉置灰类（实测 opacity 0.38），点它不产生计时，只触发引导·② **一次只提醒一项**：优先级 **科目 > 练习内容 > 速度 > 时长**，缺哪项指哪项；选了科目后引导自动改指「练习内容」，全齐自动收起（实测 3 视口一致）·③ **画布层 coach mark**：引导画在票夹所在文档，聚光框（朱橙描边脉冲）精确压住缺的那一项（目标交集 ≥ 60%），卡片 238×128px 始终落在票夹矩形内（三视口实测全部 true），带 4 步进度胶囊「科目 · 内容 · 速度 · 时长」+ CTA（科目→打开票夹 / 内容→聚焦输入框）·④ 点 CTA / 点外部 / Esc 三种方式都能收起；CTA 点「打开票夹选科目」实测弹窗 display:flex 打开·⑤ 门禁新增项 17（就绪引导 × 3 视口）；`verify.js --strict` 17/17 PASS", ""]
    if not check:
        manifest.write_text("\n".join(lines), encoding="utf-8")

    print(f"{'[check] ' if check else ''}demo {DEMO_VERSION} · {len(TABLE)} 页")
    for name, card_v, note, action in rows:
        print(f"  {name:38s} 卡 {card_v:3s} {action}")
    print(f"改动 {len(changed)} 页；VERSIONS.md {'未写（check 模式）' if check else '已写'}")


if __name__ == "__main__":
    main()
