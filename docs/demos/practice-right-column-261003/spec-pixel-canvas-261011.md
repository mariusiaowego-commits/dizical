---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
---

# spec-pixel-canvas-261011 · 右栏「顶替 pk-main-col」+ 插入卡槽动画

    owner      pixel
    上游       brief-pixel-canvas-mount-261011.md ＋ rework-pixel-canvas-261011.md（合并执行）
    日期       2026-10-11
    主产       docs/demos/practice-right-column-261003/canvas-01.html（634,893 字符 / 676,307 字节 / 16,231 行）
    可改       docs/demos/practice-right-column-261003/compose-03.html（拆外框 + 指路）
    底座       docs/demos/practice-ticket-v4-260920.html（**本体零改动**，sha256 前 16 位 e86d4bc56163218d 实测保持）
    口径       只碰 docs/demos/ · 不加依赖 · 不 commit / 不 push · 画布内配色用画布自己的 token

---

## 0 本轮（261011f）P2-1 在普通浏览器会话里仍红 —— 先定案再修

    现象（hermes 普通浏览器会话，非脚本）：verdict ASSERT_FAIL · P2-1 fail
          landedBy fallback · landedAt 502ms · jitter 0 · 同时 clockProbe.advanced === true

    定案（先测后判；三件套实测原文见 §10 B 表）
      兜底时刻插入动画态 = {playState: "running", currentTime: 0, startTime: null}
      帧数（外层 / 画布）= 3~4 帧（整个插入用例期间）
      → **既不是「兜底太短」，也不是「元素不可见」**：那次会话里**插入动画压根没获得运行机会** ——
        `startTime` 仍为 null = 动画停在 pending，一次合成帧都没轮到它 → `onfinish` 在物理上不可能派发 →
        任何时长的兜底都会赢。根因是**渲染环境**（无帧 / 被遮挡 / 重度节流），不是时序参数。
      （对照：同一份代码在真时钟前台会话 293ms 就 onfinish；抖 60/80ms 仍 onfinish）

    修法（两条，按 fix 单口径）
      ① 兜底不再按死时长盲抢：到点先看动画时钟 —— 推进中 → **不抢**，继续等 onfinish（每 250ms 复查，最多 8 次 = 2.5s 上限）；
         时钟冻结（currentTime 0）→ 才落定。**等待期间不 cancel()**（cancel 会让 onfinish 永久失去机会 —— 这是上一轮的真根因）
      ② 动画已跑过终点（currentTime ≥ 280）但事件仍没派发 → 出口单列 `onfinish-by-clock`
         （不冒充事件、也不算兜底抢跑）；只有 `fallback`（时钟冻结）与 `fallback-timeout`（推进但没到终点）才算兜底
      ③ 断言口径重写（写死在结果里）
         - 动画跑过（currentTime > 0 或已 start）+ 真时钟 → 必须是 `onfinish` / `onfinish-by-clock`，否则红（红行带 8 项实测）
         - 动画没获得运行机会（startTime null / currentTime 0，帧数个位数）或时钟冻结 → **SKIPPED**：如实写进 `skipped[]`
           （含动画态 / 帧数 / 可见性 / 真窗口实测数），**不写绿也不判红**
      ④ 诊断开关（新增，留在页里可复现）：`?swallowfinish=1` 模拟「时钟推进但 finish 事件不派发」；`?jitter=N` 造主线程负载（保留）

    实测（真时钟 Playwright chromium 1280×800，5 例全绿）
      前台可见             landedBy onfinish · landedAt 297.2ms（复查 0 次）
      抖动 60ms            landedBy onfinish · landedAt 354.5ms
      抖动 80ms            landedBy onfinish · landedAt 371.5ms
      事件不派发（复现 hermes） landedBy onfinish-by-clock · landedAt 751.3ms（复查 2 次 · 兜底时刻 {playState: finished, currentTime: 280}）
      事件不派发 + 抖 60ms   landedBy onfinish-by-clock · landedAt 753ms
    无头（virtual-time）5 窗口：动画态 {running, currentTime 0, startTime null} · 帧数 3~4 → 全部走 SKIPPED 分支（不判红，理由写进 skipped[]）
    agy 脚本重跑：direct_race onfinish 293.8ms · jitter_race onfinish 329.9ms · §2 场景 docClientW 744 · column · rowCount 2/3/6 ✓
    负控不变：加壳 132 · 待命自循环 1 · 窄屏强撑单行 66（440）/ 70（744）

---

## 0d 本轮（261011e）agy v2 复验剩余两条 —— 落地与实测

    依据   review-agy-canvas-261011.md §6 复验（v2）+ fix-pixel-canvas-261011e.md
    结论   ① 卡内视口档 → 画布 iframe 宽度联动：已通（三档实测 + 交互复核）
           ② FALLBACK_MS 320 → 500 + 抖动自检：真时钟空载 / 抖 60ms / 抖 80ms 三档全部 onfinish
           5 窗口 × 24 格 = 120 格全绿 · 4 条负控真红（132 / 1 / 66 / 71）

### ① P0-2「只修了真窗口那一路」→ 补脚手架联动

    根因（agy 定位，实测一致）：顶栏 `#czVp` 的 `setVp()` 只改卡片 iframe 的 data-vp，
    画布 iframe 自身仍是外层窗口宽（1265）→ 画布文档里注入的 `@media (max-width:1023px)` 不生效、模块轨不切纵向
    改法：新增 `applyCanvasViewport()` —— 画布 iframe 宽度 = min(卡内视口档, 外层可用宽)，下限 320px；
          `setVp()` / 画布 load / window resize 三处都调；`#czCanvas` 补 `margin: 0 auto`（窄于外层时居中）
    断言补一条（每格）：`|画布文档 clientW − min(档, 外层可用)| ≤ 16`，并把 vpWant / vpAppliedW / vpAvail / vpExpectW 打进结果
    实测（同一份 1600×1000 结果里三档并排，预设3 六卡）
      档 1133：iframe 1133 · 画布 clientW 1133 · 轨 row    · 2516/725 · 行数 1 / 模块数 6
      档 744 ：iframe 744  · 画布 clientW 744  · 轨 column · 580/580  · 行数 6 / 模块数 6 ✓ 堆叠
      档 440 ：iframe 440  · 画布 clientW 440  · 轨 column · 408/408  · 行数 6 / 模块数 6 ✓ 堆叠
    交互复核（真时钟，外层窗口 1280）：点顶栏「卡内视口 744」→ docClientW 744 · iframeW 744 · railFlex column · 580/580 · 行数 2 = 模块数 2；
                                    再点「440」→ docClientW 440 · iframeW 440 · column
    窄屏负控保留：`?audit=1&negctl=row` → 440 档 66 条红 / 744 档 71 条红
    另：窄屏 E2 断言改成「模块列右缘 ≤ 画布 clientW」+ 单列记录画布文档自身溢出
        （440 档 +5px 的元凶是画布自己的 `aside#pkRecordsDrawer`，`mine:false`）—— 画布本体零改动，它自带的几像素不算我头上

### ② P2-1「没修好」→ 兜底窗口 320 → 500ms + 抖动自检

    改法：`FALLBACK_MS = 500`；声明时长 280ms 与 cubic-bezier(0.34,1.56,0.64,1) 一字未动
    抖动自检（新增 `?jitter=N`：触发插卡后阻塞主线程 N ms，复现 agy 的「轻度抖动」场景）：
    结果里三个数分开记 —— `jitterMs`（负载毫秒）· `landedAtMs`（真出口时延）· `fallbackDueMs`（兜底到期时刻）
    采样口径拆开：`animDurationMs`（动画声明时长）vs `measureSpanMs`（触发→读数的采样跨度，含负载 + waitAnim + 420ms 稳定等待）；
    `observedMs` 保留但附 `observedMsNote` 说明它是采样跨度、不是动画时长
    实测（真时钟 Playwright chromium，1280×800）
      空载      ：landedBy onfinish · landedAt 309.1ms · 兜底到期 500ms · animDurationMs 280 · measureSpanMs 776.2 · clockProbe.advanced True
      抖动 60ms ：landedBy onfinish · landedAt 337.0ms · 兜底到期 500ms · measureSpanMs 795.4 · probe 完成 246.8ms
      抖动 80ms ：landedBy onfinish · landedAt 356.3ms · 兜底到期 500ms · measureSpanMs 810.1 · probe 完成 265.9ms
      → 抖动把真出口从 ~309ms 推到 ~356ms，仍远早于 500ms 兜底：真出口稳定是 onfinish（agy 场景已覆盖）
    新增断言（自洽口径）：`clockProbe.advanced === true` 时 `landedBy` 必须是 `onfinish` 且 `landedAtMs ≤ fallbackDueMs`；
    时钟冻结的无头档跳过该断言并在结果里写明 `p21Note`（无头实测 landedBy fallback · landedAt 500 · advanced false）

---

## 0c 本轮（261011c）按 agy 判决修缮 —— 6 条落地与实测

    依据   review-agy-canvas-261011.md（agy 独立复核）+ fix-pixel-canvas-261011c.md（判决落地单）
    结论   5 个窗口 × 24 格 = 120 格全部 ASSERT_OK / failures []（含 agy 的 1280×800 窗口）
           真时钟复核（Playwright chromium，非 virtual-time）同样 ASSERT_OK / failures []
           4 条负控真红：加壳 132 条 · 待命自循环 1 条 · 窄屏强撑单行 66 条（440 档）/ 72 条（744 档）

### P0-1 模块列高击穿画布底线 —— 修

    agy 实测：模块列 717/736/750px vs 票卡与 wrapper 654px，溢出 61~96px
    改法：① `.cz-insert` 总高 102 → 74px（上下 padding 10→4px、舞台 82→66px、缩略/槽 34→30px、行间距 16→14px）
          ② 卡片轨 max-height 运行时算：票卡底线 − 卡槽条底线 − 12px（宽屏才约束；窄屏画布已堆叠、模块列本就在票卡下方）
             超出部分在轨内纵向自理（overflow-y: auto），绝不把卡片顶出画布底边
    实测（交付态）
      1280×800（agy 的窗口）：模块列底 599 = 票卡底 599（溢出 0；修前 61~96）· 轨 max-height 481px
      1600×1000：745 ≤ 831.7 · 轨 max-height 689px ｜ 1133×800：599 = 599 · 481px
      744/440 档：轨 max-height 清空（画布已堆叠）· P0-1 断言不适用（只在宽屏判）

### P0-2 窄屏强撑单行横滑 —— 修

    改法：`@media (max-width: 1023px) { .cz-rail { flex-direction: column; align-items: stretch; overflow-x: visible; overflow-y: visible; } .cz-mod { width: 100%; } .cz-mod > iframe { width: 100% !important; } }`
    断言改口径：A1 只在「画布文档 clientW ≥ 1024」断 `rowCount === 1`；
                `< 1024` 改断三条：行数 = 模块数（纵向堆叠）· 轨 flex-direction = column · 轨 scrollW === clientW（无横向溢出）
    实测
      744 档（clientW 744）：预设③ 行数 6（= 模块数 6）· 轨 580/580 · flex column ✓
      440 档（clientW 500）：行数 6 · 轨 468/468 · flex column ✓
      负控 `?audit=1&negctl=row`（窄屏仍强撑横排）→ 440 档 66 条红 / 744 档 72 条红，三条断言各命中且带实测两端
    未用 `transform: scale()` 凑一屏（agy 已否：亚像素模糊 + 点击坐标错位）

### P1-1 插卡触发与画布状态机脱节 —— 接通（双向 + 顶栏文案）

    ① 落定回调 `land()` 里调 `canvasDoc().defaultView.enterRun()`；画布内容未选时先点第一个 `.pk-session-pill`
       （DOM 第一个胶囊文案 == cur.content_options[0]，等价用户手选；不改画布变量）
    ② 监听画布 `#pkStateToggle`：等状态稳定（≥700ms + 连续两次同值；画布自己的收窄/展开补间约 500ms 才落定）再镜像
       进练习态 → `runInsert()`（未入槽时）｜ 回准备态 → `resetInsert()`
    ③ Card A `#btnPrimary` 点击 → 读卡内 `data-mode`（prep/run/pause）→ 同步画布顶栏 `#pkBrand` 文案
       + 联动画布 `#pkPauseBtn`（暂停/继续），并向父级派发 `cz-card-a-mode` 事件
       卡片源文件零改动：监听装在宿主侧（同源 iframe 内 addEventListener）
    实测（真时钟 1280×800）
      点插卡：stage-prep → stage-running · 票卡 380 → 220 · brand 进行中 · toggle 切回准备态 · 卡 A prep → run
      顶栏切回准备态：stage-prep · 缩略图复位（transform 清空）· 状态文字回「待命入槽」· 卡 A 回 prep
      顶栏切到练习态：stage-running · 缩略图自动入槽 · 状态文字「已入槽」
      Card A 暂停：brand「已暂停」+ 画布 pauseBtn「继续练习」；恢复：brand「进行中」+ pauseBtn「暂停」
    无头环境补丁（如实）：GSAP 时间轴在 virtual-time 下不跑完 → 进/退练习态各挂宽限期兜底
      （enterCanvasRun 300ms / exitCanvasRun 260ms，只补 DOM 终态；画布自身 started/timerRunning 早已复位）
      结果里记 `sync: 'enterRun 已进态' | 'forced-run（无头…）'` 与 `exitSync: 'exitRun 已复位' | 'forced-prep（无头…）'`

### P1-2 深墨换肤割裂 —— 宿主运行时注入补齐（画布源文件零改动，sha256 e86d4bc56163218d 保持）

    注入（CANVAS_SCOPE）：`:root[data-skin="ink"]` 覆盖 html/body + `#practiceStage` #14181C · `#pkTicketCard` #1E242B + 文字 #FFF8F0
                        · `.pk-top` #1A1E22 · `.pk-stage-wrap` 透明（取值按 agy 判决，画布 scope 内不引 --dash-* 新名）
    `setSkin()` 同步给 `canvasDoc().documentElement` 挂/摘 `data-skin="ink"`（画布载入时也补一次）
    断言改写：C1a 保留（模块 data-skin 同翻）+ C1b 新增：实测画布本体**有效底色**（沿祖先链第一个有底元素）两皮肤必须不同
    实测（真时钟）
      浅银：body/stage/ticket/top 有效底色 = transparent（透出外层页面底色 rgb(255, 248, 240)）
      深墨：rgb(20, 24, 28) / rgb(20, 24, 28) / rgb(30, 36, 43) / rgb(26, 30, 34)
            —— 与 agy 判决的 #14181C / #1E242B / #1A1E22 逐位对上

### P2-1 兜底计时器误伤真事件 —— 修（280 → 320ms）

    兜底改 `setTimeout(land('fallback'), FALLBACK_MS = 320)`；动画声明时长 280ms 与 cubic-bezier(0.34,1.56,0.64,1) 一字未动
    实测
      真时钟（Playwright chromium）：`landedBy = onfinish` ✓（不再被兜底抢跑）· clockProbe ct0 0 → ct1 200 · playState finished · advanced true
      无头 virtual-time：`landedBy = fallback` · clockProbe advanced **false**（currentTime 恒 0、playState running）
      → agy 判断成立：不是「无头不能触发 onfinish」，而是兜底 280ms 抢在 287ms 前；改 320ms 后真出口即 onfinish。
        无头档仍 fallback，因为该环境动画时钟确实冻结（两种环境各自的实测都留在附录）

### P2-2 多卡并排高度不一 → 矮卡底部留白 —— 给规则 + 取舍说明

    选「轨内 align-items: flex-start + 每卡自撑高，不统一拉伸」，理由：
      ① 卡片是 iframe，`align-items: stretch` 只会拉出空白，不会让卡内内容变高；
      ② agy 另提的「给矮卡加柔和底衬」= 卡片外再加一层可见壳，违反 dad「卡片自带样式是唯一可见的框」且会被 B1 断言判红；
      ③ 本轮 P0-1 后卡片轨本身成了「票卡高度预算内的滚动面」→ 矮卡下方空档属于滚动面，不再是被戳穿的洞
    实测：预设②（A+D+Q）轨 max-height 481（1280×800）· 卡 D 313px 自撑高不拉伸 · 轨内纵向自理（scrollH > clientH 时出滚动条）

    补记（本轮顺带修的同类问题）：宽屏下卡内视口档沿用用户选择（data-vp 驱动卡内布局，demo 既有约定）；
    仅当画布已堆叠（<1024）时按实际卡宽降档，避免 1133 档塞进 468px 卡内溢出。结果里记 `vpEffective` / `vpStacked`。

---

## 0b 上一轮（261011 · 并进真画布）实测 verdict（先贴数，再说结论）

**交付态自跑 4 个窗口，全部 `verdict: ASSERT_OK` / `failures: []`**（每格 24 组合 = 4 预设 × 3 视口 × 2 皮肤）：

    ┌───────────┬──────────┬──────────┬──────────────────────────────┐
    │ 窗口      │ verdict  │ failures │ 画布 stage-wrap / 公式值      │
    ├───────────┼──────────┼──────────┼──────────────────────────────┤
    │ 1600×1000 │ASSERT_OK │ []       │ 1280 / 1280                   │
    │ 1281×800  │ASSERT_OK │ []       │ 1269 / 1269  ← hermes 复现窗口 │
    │ 1440×900  │ASSERT_OK │ []       │ 1280 / 1280                   │
    │ 1133×800  │ASSERT_OK │ []       │ 1121 / 1121                   │
    └───────────┴──────────┴──────────┴──────────────────────────────┘

    负控①（把 slot 壳加回模块盒/模块列）：verdict ASSERT_FAIL · 132 条红
    负控②（待命态自循环动画）：verdict ASSERT_FAIL · 1 条红（H2，带两端原文）
    红条数变化：hermes 复现窗口 **24 → 0**（修了 E2 宽度断言与横滑检测两条）

---

## 1 返工单三条的处置（rework-pixel-canvas-261011.md）

### 1.1 E2 宽度断言口径写歪了（不是布局缺陷）

根因（与 hermes 判断一致）：画布本体 `body` 自带**水平 padding**，`min(1280, 视口)` 漏掉了它。

    1600 宽：画布文档 clientW 1600 · body 水平 padding 32 → stage-wrap 实得 1280（1280 上限生效）
    1281 宽：画布文档 clientW 1281 · body 水平 padding 32 → stage-wrap 实得 1269
    1133 宽：画布文档 clientW 1133 · body 水平 padding 32 → stage-wrap 实得 1121
    （hermes 量到 6px/边 是更窄档下画布自己的媒体查询改了 body padding → 所以**不能硬编码**）

处置（选了返工单第 1 种，把第 2 种降级为交叉核对）：

    E2 期望值 = min(1280, 画布文档 clientW − 画布 body 水平 padding)   ← padding 从 computedStyle 实测取
    隔离基线：仍单独开一次画布本体（同宽 iframe），但**不做两数直接相等**的断言 ——
      基线 iframe 内容更高会出竖向滚动条、clientW 少 ~15px（1281 档实测：基线 1249（带滚动条）/ 注入侧 1269（不带））
      → 直接比会假红。改成断言「**基线自己也满足同一条公式**」，并把基线 wrapW/clientW/padding/公式值全部打进结果 ✓

**修后实测**：1600 → 1280=1280 ✓ · 1281 → 1269=1269 ✓ · 1440 → 1280=1280 ✓ · 1133 → 1121=1121 ✓ · 基线自洽 ✓

顺带修的同类问题：E1「票卡恒 380」在 1133 档假红（画布自己的媒体查询把票卡收窄到 360）→ 改成按画布自己的断点分档：
`≥1200 → 380` · `1024–1199 → 340~380` · `<1024 → 画布堆叠，不判` ✓

### 1.2 横滑检测读了 `documentElement`，误报

处置：沿**模块祖先链**找真滚动容器（`overflow-x` 为 `auto`/`scroll` 且 `scrollWidth > clientWidth`），做 **0 → 中段 → 0 三次采样**，三个实测数进结果 ✓

**实测**：真容器 = `.cz-rail`（卡片单行轨）

    预设②（A+D+Q，模块总宽 1316）：rail scrollW 1368 / clientW 882 · 三采样 firstLeft 560 → 317 → 560（真滚 243px ✓）
    预设③（六卡，总宽 2392）：rail scrollW 2516 / clientW 882 · 三采样 firstLeft 560 → −257 → 560 ✓

并补反向断言 **G2**：模块没超宽就不许有滚动容器（预设① 总宽 644 ≤ 883 → 实测「无（模块没超宽）」✓）

### 1.3 JSON 顶部补 `verdict`，spec 结论贴当次实测

JSON 顶部现在是 `{ verdict, failures, baseline, results, insert, skipped, assertions }` ✓
本 spec §0 的结论 = 当次跑出的 verdict/failures 原文 ✓；完整摘要见 §10 附录（含每格 rowCount / scrollable / 横滑容器三采样 / 裁切数 / pk-main-col 命中 / 原块残留）✓

---

## 2 接法：模块列挂进 `pk-main-col` 内部（顶替原内容）

### 2.1 画布原 DOM 被动了什么（都在画布文档内、运行时注入；画布文件零改动）

    #practiceStage
      .pk-top（顶部 banner：保留不动）
      main.pk-stage-wrap（画布原生两列布局：保留不动）
        aside.pk-left-col（左栏票卡：保留不动）
        div.pk-main-col#pkMainCol
          └ aside.cz-mod-col#czModCol        ← 模块列（挂进来，顶替原内容）
              ├ div.cz-insert#czInsert       ← 插入卡槽（模块列最上方、仪表盘卡片之上）
              └ div.cz-rail#czRail           ← 卡片单行轨（塞不下在轨内自己横滑）
                  ├ .cz-mod[A] → iframe(dashboard-skin-01-v3)   仪表盘
                  ├ .cz-mod[B] → iframe(metronome-01-v3)        节拍器
                  ├ .cz-mod[S] → iframe(metronome-02-strip)     竖条
                  ├ .cz-mod[D] → iframe(practice-duration-card) 今日时长
                  ├ .cz-mod[R] → iframe(today-records-01)       今日记录
                  └ .cz-mod[Q] → iframe(requests-card-01-v3)    老师要求
      div#czStubHost[hidden]                 ← 被顶替的原画布块搬到这里（见 2.2）
      footer.pk-footer-note（保留不动）

### 2.2 被顶替的原画布块：**搬走**而不是删除（关键取舍）

dad 截图那块 = `pk-main-col` 的原内容：

    #pkInstrCard（仪表卡壳）内含：
      入卡槽说明行  #pkSlotIdle（「打卡机入卡槽 · 点击下方『检票 · 开始练习』自动插入票卡」+「待命入槽」）
      计时大框      .timer-block（10:00 + 分钟药丸 + 尺子 + ±）
      检票按钮      #pkStartBtn（「检票 · 开始练习」）+ .pk-slot4-box（含运行态控制条）
      运行态遥测    .pk-running-telemetry
    #pkReqCard（老师要求板块）

**处置 = 整块搬到 `#czStubHost[hidden]`**，不 `remove()`。理由：画布自己的 JS 会 `getElementById('pkStartBtn')` / `syncStartState()` / 计时器按 id 找元素，直接删会抛错、把画布打挂；搬到隐藏宿主后它们仍在文档里（JS 找得到 ✓）、但不在 `pk-main-col` 里、也不可见 ✓

**断言实测（每格）**：`pk-main-col` 内 7 个选择器命中数全 0

    #pkInstrCard:0 · #pkReqCard:0 · #pkSlotIdle:0 · .timer-block:0 · #pkStartBtn:0 · .pk-running-telemetry:0 · .pk-slot4-box:0

### 2.3 断言：模块必须在 `pk-main-col` 内（实测祖先链）

    F1：每个模块向上走祖先链，必须命中 #pkMainCol —— 24 格 × 各模块实测全 True
    模块祖先链实测：div.cz-mod < div.cz-rail < aside.cz-mod-col < div#pkMainCol < main.pk-stage-wrap < #practiceStage

### 2.4 几何实测（预设③）

    画布：stage-wrap 1280（1600 档）/ 1269（1281 档）/ 1121（1133 档）· 票卡 380 / 380 / 360 · 中栏 882 / 879 / 751
    模块盒（设计宽 + 12px 留投影）：A 472×587(460) · B 432×620(420) · S 172×480(160) · D 392×313(380) · R 472×581(460) · Q 452×606(440)
    卡片单行轨：预设② rail 1368/882 · 预设③ rail 2516/882（在 pk-main-col 内部横滑）
    单行：24 格 rowCount = 1（预设④ 无模块 = 0）· 裁切 0 · 卡外无壳（B1 每层 border 0px none / radius 0px / bg alpha 0 / shadow none）

### 2.5 组合开关仍在画布外

    .cz-bar（画布外细条）：① 仪表盘+竖条 = A+S · ② 仪表盘+时长+要求 = A+D+Q · ③ 全右栏六卡 · ④ 只票卡（模块列空）
    另有 6 个勾选框自由组合 · 卡内视口 1133/744/440 · 皮肤 浅银/深墨 · 选择写 localStorage（canvas01_state）

### 2.6 画布本体零改动 + 一处既有缺陷

`practice-ticket-v4-260920.html` 一个字节没改（sha `e86d4bc56163218d`）。搬入方式：全文放 `<template>`，运行时补
`<!DOCTYPE html>` + `<base href="<docs/demos 绝对路径>">` → 它的 `./practice-skeleton-260920/real-practice.css`、
`./vendor/gsap.min.js`、`./assets/…png` 全部照原样解析（不重写它任何一行）。

顺手补的既有缺陷：`.ac-digit` 用了 `var(--ac-fade)` 但画布从未定义（`mask-image` 一直失效）→ 注入样式里补 `--ac-fade: none`，
既过门禁的「未定义 token」，也保持画布今天的实际观感**不变**。

---

## 3 插入卡槽动画（模块列最上方、仪表盘卡片之上）

### 3.1 形态与状态

    位置     .cz-insert（模块列第一个孩子，卡片单行轨之上 = 仪表盘卡片之上）
    槽       .cz-slot 150×34 · r7 · 虚线描边 + inset 阴影（画布自己的 token：--surface-well / --border-strong）
    票卡缩略 .cz-mini 150×34 · r7 · 白底 + 珊瑚描边（--surface-card / --c-primary）+ 打孔 + 科目名「吸气长音」
    触发     .cz-insert-btn#czInsertBtn「插入票卡 · 点亮仪表盘」（按钮命名 czInsert；原画布「检票 · 开始练习」已被顶替）
    状态文字 .cz-insert-stat#czInsertStat：待命入槽 → 已入槽 · 仪表盘已点亮（运行态）

### 3.2 动画规格（实测值）

    duration      280ms（WAAPI timing 读回 = 280，断言 ≤320 ✓）
    easing        cubic-bezier(0.34, 1.56, 0.64, 1)（back.out 量级，过冲约 10%；无弹跳过头、无旋转图标、无 emoji）
    keyframes     translateY(0px) → translateY(48px)（48 = 槽顶 − 票卡顶，按实际几何算）
    落定后        票卡与槽几何相交（miniTop 114 = slotTop 114，slot 114~148）✓
                 仪表盘点亮：<html data-cz-lit="1"> + body outline 2px --dash-coral-glow（实测 outlineW 2px）
                 + 真点卡片自己的 #btnPrimary → #dash[data-mode] prep → run（实测 after.dashMode = run ✓）
    待命态        票卡悬在槽上方、净距 14px、不相交、transform 两次采样一致、animation-name: none

### 3.3 断言（H1–H6）

    H1 待命态票卡与槽不相交（几何判定）+ 净距 ≥4px        实测 gapPx 14 · intersects false ✓
    H2 待命态无动画：两次 transform 采样一致 + getAnimations=0 + **animation-name: none**（声明值爪）
       —— 无头环境动画时钟不走、getAnimations 抓不到 CSS 动画，故用声明值当爪（负控②靠这条红）
    H3 待命态仪表盘在 prep                                实测 data-mode prep ✓
    H4 触发后票卡与槽**几何相交**（不是看类名）            实测 miniTop 114 / slot 114~148 ✓
    H5 触发后仪表盘进入运行态                              实测 data-mode run · data-cz-lit 1 · outlineW 2px ✓
    H6 动画总时长 ≤320ms + 缓动函数名                      实测 declaredMs 280 · cubic-bezier(0.34, 1.56, 0.64, 1) ✓

### 3.4 无头环境的一处如实交代

headless + `--virtual-time-budget` 下**动画时钟不推进**：WAAPI 的 `finished`/`onfinish` 不触发、CSS 动画也不跑（`getAnimations()` 返回 0）。
处置（不是绕过断言，是让状态机在两种环境都能落定）：

    runInsert() 同时挂两路落定：anim.onfinish（真浏览器 280ms 落定）+ setTimeout(280ms) 兜底
    落定函数里先 cancel 掉动画再写 inline transform —— fill:forwards 的动画会盖住 inline style，
    不 cancel 就永远量到「没落定」（第一版就是这么假红的）
    结果里如实记录 landedBy：本次 4 个窗口都是 'fallback'（真浏览器会是 'onfinish'）
    因此 H6 断的是**动画声明总时长**（280ms，WAAPI timing 读回），observedMs（约 300ms）只作参考打印

---

## 4 24 格实测表（4 预设 × 3 视口 × 2 皮肤）

    ┌────────┬──────────────────┬──────┬──────────┬──────────────────────────┬──────┐
    │ 组合   │ 模块             │ 行数 │ 模块总宽 │ 卡片轨 scrollW/clientW   │ 裁切 │
    ├────────┼──────────────────┼──────┼──────────┼──────────────────────────┼──────┤
    │ 预设①  │ A+S              │ 1    │ 644      │ 883/883（没超宽，无滚动）│ 0    │
    │ 预设②  │ A+D+Q            │ 1    │ 1316     │ 1368/882（轨内横滑）     │ 0    │
    │ 预设③  │ A+B+S+D+R+Q      │ 1    │ 2392     │ 2516/882（轨内横滑）     │ 0    │
    │ 预设④  │ （无）           │ 0    │ 0        │ 882/882                  │ 0    │
    └────────┴──────────────────┴──────┴──────────┴──────────────────────────┴──────┘
    （三档视口 × 两皮肤数字一致：视口档只改卡内布局，不改模块盒宽；深墨档六模块 data-skin 全 ink ✓）

    断言清单
      A1 单行 · A2 不裁切 · B1 卡外无壳 · B2 画布/iframe/body 无描边 · C1 皮肤同翻 · D1 脚手架已隐
      E1 票卡宽（按画布断点分档）· E2 stage-wrap = 公式值 · F1 模块在 pk-main-col 内 · F2 原块已移除
      G1 超宽时必须能真滚 · G2 不超宽时不许有滚动容器 · H1–H6 插入卡槽 · SKIPPED 音频（headless 无音频设备）

---

## 5 负控（三条，红行都带两端原文）

### 5.0 负控③：窄屏仍强撑单行横滑（本轮新增）

    ?audit=1&negctl=row（440 档窗口）→ ASSERT_FAIL · 66 条红；744 档 → 72 条红，例：

      A1 fail [预设1/1133/light] 窄屏未纵向堆叠：行数 1 期望 = 模块数 2（画布文档 clientW 500 < 1024）· 轨 flex-direction=row
      A1 fail [预设1/1133/light] 窄屏轨未改纵向：flex-direction=row（期望 column）
      A1 fail [预设1/1133/light] 窄屏仍有横向溢出：轨 scrollW 628 > clientW 468

### 5.1 负控①：把 dad 否掉的 slot 壳加回模块盒 + 模块列

    ?audit=1&negctl=1 → ASSERT_FAIL · 132 条红，例：

      B1 fail [预设1/1133/light/A] 卡片外多了可见壳：div.cz-mod
        border=1px solid rgba(44, 62, 80, 0.12)（期望 0px none）
        radius=20px（期望 0px）· bg=rgb(255, 255, 255)（期望 alpha 0）
        shadow=rgba(44, 62, 80, 0.04) 0px 1px 3px 0px（期望 none）
      B1 fail [预设1/1133/light/A] 卡片外多了可见壳：aside#czModCol.cz-mod-col
        radius=24px（期望 0px）· bg=rgba(44, 62, 80, 0.06)（期望 alpha 0）

### 5.2 负控②：待命态自循环动画

    ?audit=1&negctl=insert → ASSERT_FAIL · 1 条红：

      H2 fail [插入卡槽/待命] 待命态声明了 CSS 动画：animation-name=czNegLoop · duration=0.9s
        · iteration=infinite · play-state=running（期望 animation-name: none）
        ｜ 两次 transform 实测（150ms 间隔）：none vs none
        （无头环境动画时钟不走 → 两次采样必然相同，这条红由上面的声明值判出；真浏览器里两次会不同）

---

## 6 门禁

    python3 scripts/verify-demos.py canvas-01.html compose-03.html
      → OK ×2 · 非中性色字面量 0 · transition:all 0 · ink True · 括号差 0 · 未定义 token 无
        · JS 过 node --check · 旧文字色 0 · 共享尺子 引用/ markup 都有
      → 换肤契约：--dash-* 名集合一致（77 个）
    python3 scripts/token-contrast.py canvas-01.html → 门禁不合格合计 0
    compose-03.html?audit=1 → ASSERT_OK（拆外框 + 指路后未破坏它自己的自检）
    画布本体 sha256 前 16 位 e86d4bc56163218d（实测保持，零改动）

---

## 7 待 dad 拍板

    1 卡片单行轨的宽度分配：现在是「各卡按自己设计宽排一行、轨内横滑」（预设②③ 需要右滑）。
      若你要的是「一屏内全部塞下（卡片各自压窄）」，改 grid-auto-columns: minmax(300px, 1fr) 即可，请给口径。
    2 插入卡槽的触发：现在用模块列自带的「插入票卡 · 点亮仪表盘」按钮（原画布「检票 · 开始练习」已被顶替）。
      要不要接回画布的语义（比如顶部 banner 上放一个入口）？
    3 待命态票卡要不要显示真实数据（现在写死「吸气长音」缩略）？
    4 窄屏（<1024）下卡内视口档会按实际卡宽自动降档（防卡内溢出）；要不要在窄屏干脆隐藏「卡内视口」开关？
    5 宽屏下卡片轨成了「票卡高度预算内的滚动面」：800 高的窗口里预设②③ 需在轨内纵向滚一点才看完最高的卡。
      若你要「一屏看完不滚动」，得放宽模块列高度上限（会重新顶出画布底边）或压窄卡片 —— 两者互斥，请给口径。

---

## 8 遗留 / 已知问题

    · 卡片是构建时刻快照：改卡后要重跑 gen_canvas.py 再同步（sha 见 §10 附录 manifest）
    · 画布没有深墨皮肤（它的 token 只有一套），换肤只翻模块；画布保持原样
    · 横滑靠浏览器原生（触控板两指 / Shift+滚轮 / 滚动条）；没做拖拽横滑与键盘 ←→
    · 被顶替的原块在 #czStubHost 里仍在跑画布自己的计时逻辑（不可见）；顶部 banner 的「今日记录」药丸等仍可点
    · 无头环境动画时钟不走（见 §3.4）：H6 断的是声明时长；真浏览器请 dad 目视一次落定手感（≤320ms）
    · 画布本体的既有缺陷（只补定义不改本体）：.ac-digit 用了未定义的 var(--ac-fade)
    · 440 窗口下本页组合开关细条自身会把文档撑到约 500px 宽（demo 脚手架 min-content，不是画布问题）；
      画布在该档仍走 <1024 堆叠分支（断言按画布文档 clientW 判，不受影响）
    · 无头环境动画时钟冻结（clockProbe advanced false）：插入动画落定靠 500ms 起点的时钟感知兜底、画布进/退练习态靠 300/260ms 宽限期兜底；
      真浏览器里两者都走真事件（landedBy onfinish / exitSync「exitRun 已复位」），已用 Playwright chromium 复核
    · P2-1 出口有三个值，别混：`onfinish`（真事件）· `onfinish-by-clock`（动画自己跑过终点 280ms，只是 finish 事件没派发）·
      `fallback`（时钟冻结，动画没跑）· `fallback-timeout`（推进但没到终点 —— 异常，判红）。
      动画**没获得运行机会**（startTime null / currentTime 0 / 帧数个位数）时该断言走 SKIPPED 并写进 `skipped[]`：不写绿、不判红
    · 卡内视口档现在会同时改**画布 iframe 自身宽度**（= min(档, 外层可用宽)）→ 外层窗口比档宽时，画布两侧露出页面底色
      （刻意的「设备预览」观感；不是壳，B2 断言仍绿）。窄窗口里选大档时画布按外层宽渲染，观感等同该外层宽度
    · 440 档画布文档自带 +5px 横向溢出，元凶是画布自己的 `aside#pkRecordsDrawer`（`mine:false`）—— 画布本体零改动，不代改

---

## 9 文件清单 + 复现

    docs/demos/practice-right-column-261003/canvas-01.html      已改（顶替 pk-main-col + 插入卡槽 + 状态机桥 + 深墨注入 + 六条判决 + 视口档联动画布 iframe + 时钟感知兜底）· 634,893 字符 / 676,307 字节 / 16,231 行
    docs/demos/practice-right-column-261003/compose-03.html     已改（slot 去壳 + 指路文案同步为「顶替 pk-main-col」）· 36,408 字符 / 1,064 行
    docs/demos/practice-right-column-261003/spec-pixel-canvas-261011.md   本文件（正文 + §10 实测附录）
    docs/demos/practice-ticket-v4-260920.html                   未改（sha e86d4bc56163218d）
    六卡本体                                                    未改

    复现
      组合页：浏览器打开 docs/demos/practice-right-column-261003/canvas-01.html
      自检：同页加 ?audit=1（输出在页面底部 <pre id="audit">，首行 ASSERT_OK / failures []，JSON 顶部有 verdict）
      负控①：?audit=1&negctl=1（模块盒加回壳）｜ 负控②：?audit=1&negctl=insert（待命态自循环动画）
      负控③：?audit=1&negctl=row（窄屏仍强撑单行；要在 440/744 窗口跑）
      抖动自检：?audit=1&jitter=60（触发插卡后阻塞主线程 60ms，看 landedBy 是否仍为 onfinish）
      诊断：?audit=1&swallowfinish=1（吞掉 finish 事件，模拟「时钟推进但事件不派发」的会话 → 期望 onfinish-by-clock）
      重新生成：python3 ~/.hermes/profiles/pixel/cache/scratch/gen_canvas.py
      无头自跑：python3 ~/.hermes/profiles/pixel/cache/scratch/canvas_run.py one <宽> <高> 'audit=1' [存盘文件]
                （另有 jit 模式：canvas_run.py jit 60 1600 1000）
      真时钟复核（Playwright chromium）：cd ~/.hermes/profiles/pixel/cache/scratch/pw
        /usr/local/bin/python3 realclock.py   # ?audit=1 全量 + 三条交互（插卡 / 顶栏切回准备态 / Card A 暂停）
        /usr/local/bin/python3 p21.py         # 前台 / 抖 60 / 抖 80 / 事件不派发 / 事件不派发+抖动 五例出口对照
        /usr/local/bin/python3 jitter.py      # 空载 + 抖动 60ms + 抖动 80ms 的 landedBy 对照
        /usr/local/bin/python3 bridge.py      # 双向桥 + 顶栏点「卡内视口 744/440」的宽度联动

---

## 10 附录：本轮（261011f）实测原文

```
### A 交付态自跑（无头 Chrome + `--virtual-time-budget`；每格 24 组合 = 4 预设 × 3 卡内视口 × 2 皮肤）

| 窗口 | verdict | failures | 画布 iframe 实宽 | P0-1 模块列底 / 票卡底 | 轨 max-height | P2-1 出口 |
|---|---|---|---|---|---|---|
| 1600×1000 | ASSERT_OK | 0 | 1133（档 1133） | 745 / 831.7 | 689px | fallback |
| 1280×800 | ASSERT_OK | 0 | 1133（档 1133） | 599 / 599 | 481px | fallback |
| 1133×800 | ASSERT_OK | 0 | 1133（档 1133） | 599 / 599 | 481px | fallback |
| 744×900 | ASSERT_OK | 0 | 744（档 1133） | 2116.9 / 907.9 | (未设) | fallback |
| 440×900 | ASSERT_OK | 0 | 500（档 1133） | 2076.9 / 867.9 | (未设) | fallback |

### B 本轮 P2-1 诊断（261011f）：无头档为什么只能走兜底 —— 三个数说清

| 窗口 | clockProbe.advanced | 兜底时刻动画态 | 帧数 外层/画布 | 可见性/focus | 出口 | 断言 |
|---|---|---|---|---|---|---|
| 1600×1000 | False | {"playState": "running", "currentTime": 0, "startTime": null} | 4/4 | visible/True | fallback | SKIPPED（如实记，不判红） |
| 1280×800 | False | {"playState": "running", "currentTime": 0, "startTime": null} | 3/3 | visible/True | fallback | SKIPPED（如实记，不判红） |
| 1133×800 | False | {"playState": "running", "currentTime": 0, "startTime": null} | 4/4 | visible/True | fallback | SKIPPED（如实记，不判红） |
| 744×900 | False | {"playState": "running", "currentTime": 0, "startTime": null} | 3/3 | visible/True | fallback | SKIPPED（如实记，不判红） |
| 440×900 | False | {"playState": "running", "currentTime": 0, "startTime": null} | 3/3 | visible/True | fallback | SKIPPED（如实记，不判红） |

无头档 SKIPPED 原文（1600×1000）：

```
SKIPPED · P2-1 插入动画出口：SKIPPED：本环境没给插入动画跑的机会 —— 兜底时刻动画态 {"playState":"running","currentTime":0,"startTime":null} · 帧数 外层/画布 4/4 · 可见性 visible · focus true · clockProbe.advanced false；落定只能靠 500ms 兜底。真窗口实测（Playwright chromium 1280×800）：前台可见 onfinish 293ms · 抖 60ms onfinish 351ms · 抖 80ms onfinish 372ms · 事件不派发档（?swallowfinish=1）onfinish-by-clock 752ms —— 见 spec §10 C 节
```

### C 真时钟复核（Playwright chromium 1280×800；`?jitter=N` 造主线程负载，`?swallowfinish=1` 模拟事件不派发）

```
A 前台可见                     verdict=ASSERT_OK   failures=0
   landedBy=onfinish           landedAt=297.2ms · 复查=0 · 迟到/被吞 onfinish=None / None · clockProbe.advanced=True
   兜底时刻动画态=null
B 抖动 60ms                  verdict=ASSERT_OK   failures=0
   landedBy=onfinish           landedAt=354.5ms · 复查=0 · 迟到/被吞 onfinish=None / None · clockProbe.advanced=True
   兜底时刻动画态=null
B 抖动 80ms                  verdict=ASSERT_OK   failures=0
   landedBy=onfinish           landedAt=371.5ms · 复查=0 · 迟到/被吞 onfinish=None / None · clockProbe.advanced=True
   兜底时刻动画态=null
C 事件不派发（复现）                verdict=ASSERT_OK   failures=0
   landedBy=onfinish-by-clock  landedAt=751.3ms · 复查=2 · 迟到/被吞 onfinish=297.6 / None · clockProbe.advanced=True
   兜底时刻动画态={"playState": "finished", "currentTime": 280, "startTime": 1497.1050000167452}
C 事件不派发 + 抖 60ms           verdict=ASSERT_OK   failures=0
   landedBy=onfinish-by-clock  landedAt=753ms · 复查=2 · 迟到/被吞 onfinish=354.6 / None · clockProbe.advanced=True
   兜底时刻动画态={"playState": "finished", "currentTime": 280, "startTime": 1545.6150000100024}
```

### D agy 自带脚本 `scripts/verify-real-window-261011.py` 重跑（独立复核）

```
=== 2. HERMES SCENARIO (1265px window, #czVp=744) ===
{
  "preset_1": {
    "docClientW": 744,
    "stateVp": "744",
    "railFlexDir": "column",
    "railClientW": 580,
    "railScrollW": 580,
    "rowCount": 2,
    "modCount": 2
  },
  "preset_2": {
    "docClientW": 744,
    "stateVp": "744",
    "railFlexDir": "column",
    "railClientW": 580,
    "railScrollW": 580,
    "rowCount": 3,
    "modCount": 3
  },
  "preset_3": {
    "docClientW": 744,
    "stateVp": "744",
    "railFlexDir": "column",
    "railClientW": 580,
    "railScrollW": 580,
    "rowCount": 6,
    "modCount": 6
  }
}
```
```json
"direct_race": {
    "landedBy": "onfinish",
    "landTimeMs": 293.8,
    "finishEventTimeMs": 293.8
  },
  "jitter_race": {
    "landedBy": "onfinish",
    "landTimeMs": 329.9
  }
}
```
（§1 摘要：440 → docClientW 440 · column · rowCount 2/3/6；744 → docClientW 744 · column · rowCount 2/3/6；1280×800 → docClientW 1133 · row · rowCount 1 · modColBottom 686 = ticketBottom 686 · overflowP01 0）

### E 负控（真跑，红行都带两端原文）

- `?audit=1&negctl=1` @ 1600x1000 → verdict ASSERT_FAIL · **132 条红**
- `?audit=1&negctl=insert` @ 1600x1000 → verdict ASSERT_FAIL · **1 条红**
- `?audit=1&negctl=row` @ 440x900 → verdict ASSERT_FAIL · **66 条红**
- `?audit=1&negctl=row` @ 744x900 → verdict ASSERT_FAIL · **70 条红**
```

### 构建时刻快照 manifest（sha256 前 16 位 / 字节）

```json
{
 "built": "2026-10-11",
 "canvas": {
  "file": "practice-ticket-v4-260920.html",
  "sha256_16": "e86d4bc56163218d",
  "bytes": 183957
 },
 "cards": {
  "A": {
   "file": "dashboard-skin-01-v3.html",
   "sha256_16": "650c8a9b45021ce1",
   "bytes": 137191
  },
  "B": {
   "file": "metronome-01-v3.html",
   "sha256_16": "5b7e5c60e4016a47",
   "bytes": 114873
  },
  "S": {
   "file": "metronome-02-strip.html",
   "sha256_16": "4ea6d17e37f669e0",
   "bytes": 32180
  },
  "D": {
   "file": "practice-duration-card-01-v3.html",
   "sha256_16": "ea26b358155dc396",
   "bytes": 38074
  },
  "R": {
   "file": "today-records-01.html",
   "sha256_16": "3e7bdd493216ce76",
   "bytes": 30488
  },
  "Q": {
   "file": "requests-card-01-v3.html",
   "sha256_16": "bfb9e664be397627",
   "bytes": 44711
  }
 },
 "token_names": 77
}
```

## §0.7 · 261012c 四条（2026-10-12）

> 判决单：`brief-pixel-261012c.md`；上游 MRD `MRD-左右栏组合问题.md` §2610120839-demo v3.2。
> 只动 `docs/demos/`；画布底座 `practice-ticket-v4-260920.html` 零改动（sha256 前 16 位 `e86d4bc56163218d` 实测不变）。

### 第 1 条 · 票卡滑入卡槽那套动画：全部删除
- 删：`INSERT_MS` / `INSERT_EASE` / `FALLBACK_MS` / `FALLBACK_CHECK_STEP` / `FALLBACK_MAX_CHECKS`、`.cz-insert*` / `.cz-mini*` / `.cz-slot*` 全部 CSS、`runInsert()` / `resetInsert()` / `litDashboard()`、时钟探针 / `?jitter` / `?swallowfinish`、断言 H1–H8 与 P2-1、负控 `?negctl=insert`。
- 留：卡槽**占位**（`.cz-slot-host`：虚线框 + `TODO agy 规格（spec-agy-slot-261012）` + 一个极简按钮「开始练习」+ 状态字 准备态/计时态），无任何动画、无 `animation-name`、无 WAAPI。
- 占位从「轨上方」挪到「轨下方」：否则它把仪表盘顶下去，第 2 条的「顶部对齐」不成立。实测占位高 47 px。
- 新规格文件待 agy；本批只保证：占位存在、可点击切态、不影响其余断言。

### 第 2 条 · 仪表盘高 = 票卡高；画布高度按真实内容
- 画布 iframe 高：`max(视口高 − 顶条, 画布文档 scrollHeight)`（原来只看视口，小窗口把票卡压扁裁切）。
  配套：`CANVAS_SCOPE` 里把画布自己的 `100vh` 归零（`#practiceStage / .pk-stage-wrap / .pk-left-col / .pk-ticket / .pk-main-col { min-height: 0 }`），否则形成「iframe 越高 → 内容越高 → iframe 再高」的环。
- 仪表盘（卡 A）iframe 高 = `#pkLeftCol` 实测高（±1px）；卡内加 `html.cz-fill` 撑满链（`html / body / .stage-frame / .dash` 一律 `height:100%`）。
- 顶部对齐：`alignColTop()` 运行时把「票卡顶 − 模块列顶」差值写到轨 `margin-top`（抹平画布左右栏的 4px 内边距差，不动画布源文件）。
- 实测（1600×1000 / 画布文档 clientW 1133，预设2）：仪表盘高 1754 = 票卡高 1754.3 · 顶 56 = 56 · 画布 iframe 内联高 1834 ≥ 画布内容高 1834。
- 分档：宽屏（画布文档 clientW ≥ 1024）断「顶部对齐 ±1px」；窄屏画布自己纵向堆叠，改断「模块列落在票卡下方」。

### 第 3 条 · 准备态 ↔ 计时态 双向同步（静态切换，无动画）
- 画布侧：`setCanvasStage('run'|'prep')` → 调画布自己的 `enterRun()/exitRun()`；内容未选先点第一个 `.pk-session-pill`。
- 卡 A 侧：`setCardAMode('prep'|'run'|'pause')` → 点它自己的按钮（`#btnPrimary` 开始/暂停/继续、`#btnEarly` 提前结束），不伪造 `data-mode`。
- 正向（卡 A 点开始 → 画布进计时态）：`bridgeCardA()` 监听卡 A 两个按钮 → 镜像画布 + 顶栏品牌字。
- 反向（画布顶栏「切回准备态」→ 卡 A 回准备态）：`bridgeCanvas()` 监听 `#pkStateToggle`，等「画布自述态」稳定（连续两次同值 + ≥700ms，上限 1.8s）再镜像。
- **意图信号取「元素自述」而不是 class**：虚拟时间 / 无头下画布的 GSAP 过渡不跑完，`stage-running` 会停在旧值，但顶栏按钮文案（`切到练习态` / `切回准备态`）已经是画布自己的声明。class 与自述不一致时，宿主只补 DOM 终态（`forceCanvasStage()`，计数 `window.__czForce`），不动画布内部状态机。
- 实测（1600×1000）：① 卡 A 点开始 → 画布 `stage-running`、左栏收窄 220、按钮「暂停」、卡槽状态字「计时态」；② 顶栏切回准备态 → 画布 `stage-prep`、卡 A `prep`、按钮「开始」。
- 负控 `?negctl=onesided`（反向那一向关掉）→ **2 红**，全部落在 C3-2。

### 第 4 条 · 今日练习记录：小入口 + popout
- 右栏 R 模块不再渲染整卡 iframe，改为一个入口按钮 `#czRecordsEntry`（文字 + 「点击查看」）；点击 → 画布内 popout `#czRecordsPop`（`position: fixed` + `rgba(44,62,80,0.45)` 遮罩 + 面板 `min(760,100%-40) × min(560,100%-40)`，内嵌 `today-records-01.html`）。
- 关闭：点遮罩 / 点「关闭」/ ESC 三路；关后焦点回归入口（`document.activeElement === #czRecordsEntry`）。
- 卡内样式等 agy（`spec-agy-records-card-261012`）；本批只落结构、交互与 a11y 基线。
- 实测：`position=fixed` · 遮罩底色 `rgba(44, 62, 80, 0.45)` · 遮罩铺满画布视口 · 面板在画布视口内 · ESC 后关闭且焦点回归 `entry`。
- compose-03.html 同步：R 槽位保留旧整卡作对照，槽下加一行说明「正式形态已迁移到 canvas-01.html」。

### 联动 4.1 · 消息通道骨架（父页 ↔ 画布 ↔ 卡内 iframe）
- `bus`（挂在 `window.__cz.bus`）：`emit(scope, name, detail)`，scope ∈ `parent | canvas | cardA`；目标 window 收 `CustomEvent('cz:<name>')` → 回 `postMessage({cz:'ack', from})` → 父页入日志。
- 回环实测：发 2 条（`link-canvas` / `link-cardA`）→ 收到 2 条 ack（来自 canvas, cardA）。
- 字段映射未定，等 agy（`spec-agy-binding-261012`）；本批只保证通道通、证据可查。

### 本批门禁与负控（实测）
| 项 | 结果 |
|---|---|
| `?audit=1` 5 窗口 | 1600×1000 / 1280×800 / 1133×800 / 744×900 / 440×900 全部 `ASSERT_OK`，failures 0 |
| 负控 `?negctl=1`（加回被否的卡壳） | 133 红 |
| 负控 `?negctl=row`（窄屏强撑单行） | 440 档 66 红 / 744 档 70 红 |
| 负控 `?negctl=onesided`（状态同步只单向） | 2 红（C3-2） |
| `scripts/verify-demos.py canvas-01.html compose-03.html` | OK ×2 |
| `scripts/token-contrast.py canvas-01.html` | 门禁不合格 0 |
| 底座 `practice-ticket-v4-260920.html` | sha256 前 16 位 `e86d4bc56163218d`（未变） |
