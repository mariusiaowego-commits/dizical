---
source: ai-agent
project: dizical
sprint: sprint-26100602-round2-mrd2610062214
updated: 2026-10-11
reviewer: agy (reference review · 第二路独立评测)
target: docs/demos/practice-right-column-261003/canvas-01.html
spec_reviewed: docs/demos/practice-right-column-261003/spec-pixel-canvas-261011.md
canvas_source: docs/demos/practice-ticket-v4-260920.html (sha256 前16位 e86d4bc56163218d 校验通过)
---

# review-agy-canvas-261011 · canvas-01 独立 Review 报告

## 0. 评审结论

> **结论：暂不建议进 demo 最终交付（需经修缮后方可交付）。**
> 
> **判定摘要**：
> 1. **核心顶替与防崩溃架构合格**：Pixel 将原右栏 7 个节点移入 `#czStubHost[hidden]` 的方案确实有效，画布自身的所有存留业务控件（BPM 加减、时长加减、月份切换、票夹弹层、今日记录抽屉、练习态切换）**经 Playwright 实测 100% 可正常响应，控制台 0 报错、0 警告**；
> 2. **断言真实有效**：挑测 H1、H2、B1 三条负控均**真实报红且精确输出两端实测原文**；
> 3. **但存在 2 项阻碍交付的 P0 缺陷与 2 项体验割裂**：
>    - **[P0-1] 模块列高严重击穿画布底线**：模块列实际高度 717px–750px，而左栏票卡与画布 wrapper 仅 654px，底端穿透画布 body 底边达 **61px–96px**；
>    - **[P0-2] 移动端（440/744 视口）强行横滑不堆叠**：440 窄屏下画布已单列堆叠，但卡片轨因断言 `rowCount === 1` 的机械约束硬撑单行横排，导致在 408px 的手机屏上强塞 2516px 宽轨，完全违反移动端交互规范；
>    - **[P1-1] 插入卡槽与画布生命周期脱节**：点击「插入票卡」仅运行 Card A 仪表盘，未联动画布 `enterRun()`，导致左侧票卡停在待命态（380px 未收窄锁定），形成两边状态撕裂；
>    - **[P1-2] 换肤半脱节**：画布本体无 ink 皮肤支持，切换到深墨时画布依然浅白，形成黑块悬浮于米白纸张上的生硬冲突。

---

## 1. 独立复算与对比清单（我核算的数 vs Pixel 的数）

| 审查项 | Pixel 报告声称 | agy 实测数据 (独立测量) | 一致性 | agy 判定与意见 |
|---|---|---|---|---|
| **画布 SHA256** | `e86d4bc56163218d` | `e86d4bc56163218d` | **一致** | 画布本体确实零改动，纯外部注入。 |
| **原块顶替清空** | `pk-main-col` 内 7 项命中全 0 | 7 项命中全 0，子节点仅剩 `aside#czModCol` | **一致** | 移至 `#czStubHost[hidden]` 落实干净。 |
| **画布脚本存活** | 0 报错 | 0 error, 0 warn; 7 处交互全绿通过 | **一致** | 业务逻辑完好，未被破坏。 |
| **待命态无动画** | `gapPx: 14`, `t1===t2`, `getAnimations: 0` | `gapPx: 14.0px`, `t1: "none"`, `t2: "none"` | **一致** | 待命态确实静止无漂移。 |
| **动画时长与缓动** | 280ms, back.out(1.56) | 声明 280ms, `cubic-bezier(0.34, 1.56, 0.64, 1)` | **一致** | 符合规范。 |
| **动画落定路径** | `headless 下时钟不走，必定为 fallback` | **实测 Chromium WAAPI 在 287ms 成功派发 `onfinish`** | **不同意** | **Pixel 判断失误**：不是无头时钟不走，而是其兜底计时器写死为 280ms，导致 `setTimeout(280)` 必定抢先于 287ms 的下一帧事件！若放宽至 320ms，`onfinish` 100% 正常落定。 |
| **440 移动端布局** | `rowCount: 1` 视为成功 | 手机屏宽度 408px，轨宽 672px–2516px，Card S 在 $x=514$px 屏外 | **不同意** | **Pixel 把缺陷当特性断言**：在移动端强行断言 `rowCount === 1` 导致极端不适的横滑体验。 |
| **模块列垂直对齐** | 单行无裁切 | 模块列高 717px–750px，溢出票卡底边 **63px–96px**，穿透 body **61px** | **不同意** | 高度未受控，底部严重参差击穿。 |
| **皮肤同翻 (C1)** | 宣称为「皮肤同翻」 | 仅各卡 iframe 转 ink，画布背景和左栏票卡完全无 ink 样式 | **不同意** | 验了等于没验，属于名不副实的软断言。 |

---

## 2. 缺陷清单（P0 / P1 / P2）

### [P0-1] 模块列总高击穿画布与票卡底线（溢出 63px ~ 96px）
- **现象**：右栏模块列挂入后，其总高度明显大于左栏票卡及原画布容器，卡片底部直接戳穿画布底边。
- **实测数据**（`viewport = 1280x800`）：
  - 左栏票卡高度：`ticket.height = 654px`
  - 画布容器高度：`stageWrap.height = 654px`，`mainCol.height = 654px`
  - 右栏模块列高度：
    - 预设 1 (A+S)：`.cz-insert` (102px) + `.cz-rail` (603px) + gap (12px) = **717px**（超出票卡底线 **63px**）
    - 预设 2 (A+D+Q)：`.cz-insert` (102px) + `.cz-rail` (622px) + gap (12px) = **736px**（超出票卡底线 **82px**）
    - 预设 3 (六卡)：`.cz-insert` (102px) + `.cz-rail` (636px) + gap (12px) = **750px**（超出票卡底线 **96px**）
  - 画布 body 底端：`body.bottom = 688px`，而模块底端：`modCol.bottom = 749px`，**直接探出 body 外 61px**。
- **复现步骤**：
  1. 打开 `canvas-01.html`；
  2. 审查元素查看 `#pkTicketCard` 与 `#czRail` 的底部基准线；
  3. 观察卡片底部的灰色投影和边框直接悬空延伸出画布界外。
- **建议改法**：
  - 将 `.cz-insert` 的冗余上下 padding 压缩（当前 82px 舞台 + 上下 padding 占用 102px 高度）；
  - 调整 `.cz-rail` 的 `max-height` 约束，使 `cz-insert + cz-rail + gap` 的总体高度严格对齐或略小于左栏票卡高度（654px），避免底部向外击穿。

---

### [P0-2] 440px / 744px 移动窄屏强行单行横滑，拒绝纵向堆叠
- **现象**：当视口切换至 440px（iPhone）或 744px（iPad 竖屏）时，画布整体已经堆叠为单列（票卡在上方、模块列在下方），但模块列内部依旧被死死限制在单行横排，用户必须在 400px 的狭窄宽度内横向拖动滑行多达 2500px 的长轨。
- **实测数据**：
  - 440 视口下：
    - `stageWrap.flexDirection = "column"`（画布已纵向堆叠）；
    - `stageWrap.offsetWidth = 408px`，`mainCol.offsetWidth = 408px`；
    - `.cz-rail` 内部强制为 `flex-direction: row`；
    - 预设 1 (A+S) 轨宽为 **672px**（Card S 起始位置 $x = 514$px，100% 掉在屏外）；
    - 预设 2 轨宽为 **1368px**；预设 3 轨宽达 **2516px**；
    - Pixel 的断言 A1 将 `rowCount === 1` 写死在自检脚本中，强行逼迫移动端不准折行换行。
- **复现步骤**：
  1. 切换视口至 `440` 或 `744`；
  2. 观察下方右栏模块在手机屏幕上的布局，所有卡片被强排成一行，必须横向大量滑屏。
- **建议改法**：
  - 媒体查询中，针对 `@media (max-width: 768px)`，允许 `.cz-rail` 采用卡片居中或纵向流动堆叠布局，或者至少只在手机端保留单卡翻页轮播，而非在整屏纵向页面中嵌套一个 2500px 的微型横向拖拽条；
  - 放开 A1 断言在 `<1024` 分档下对 `rowCount === 1` 的死板要求。

---

### [P1-1] 「插入卡槽」触发与画布练习状态机完全脱节
- **现象**：点击插槽区域的「插入票卡 · 点亮仪表盘」按钮后，只有右侧 Card A 仪表盘点亮并开始计时，但左侧的真实票卡毫无反应，依然保持在「练习准备」待命态，票卡没有收窄，也没有被锁定。
- **实测数据**：
  - 点击 `#czInsertBtn` 后：
    - Card A 内部：`dash.dataset.mode = 'run'`；
    - 插槽状态文字：`#czInsertStat` 变为 `"已入槽 · 仪表盘已点亮（运行态）"`；
    - 画布自身状态：`#practiceStage.className` 仍为 `"stage-prep"`（期望进入 `"stage-running"`）；
    - 左栏票卡宽度：`#pkLeftCol.offsetWidth` 仍为 **380px**（期望像真实检票一样收窄至 220px 并展示打孔卡头）；
    - 顶栏按钮文案：依然显示 `"切到练习态"`。
- **复现步骤**：
  1. 打开 `canvas-01.html`；
  2. 点击 `#czInsertBtn`；
  3. 观察左栏票卡依然是完整的展开准备态，而右栏仪表盘已经在计时，两边状态割裂。
- **建议改法**：
  - 在 `litDashboard(true)` 中，除了触发 Card A 的 `#btnPrimary.click()` 外，同时联动调用画布内部的 `enterRun()`（若 `content` 为空可先默认赋值为当前首项），使左栏票卡同步收窄至 220px 形成打卡锁定闭环。

---

### [P1-2] 深墨换肤视觉严重割裂（白底黑块悬浮）
- **现象**：切换顶栏为「深墨（ink）」皮肤时，只有右栏 iframes 内部翻转成了深墨配色，画布自身背景、顶栏和左栏票卡依然是浅米白，视觉极其割裂。
- **实测数据**：
  - 画布本体 `practice-ticket-v4-260920.html` 内部**零处**包含 `data-skin` 选择器，根本没有 dark/ink 样式规则；
  - 切换 ink 后：画布背景为 `#FFF8F0`（浅米色），左栏票卡为 `#FFFFFF`，而右栏的仪表盘和时长卡变成了 `#14181C`（浓黑），像一块突兀的补丁贴在纸卡上；
  - 断言 C1 仅检查 iframe 内部 `data-skin`，导致该严重视觉缺陷顺利溜过自检。
- **建议改法**：
  - 在 `CANVAS_SCOPE` 注入 CSS 中，增加 `:root[data-skin="ink"]` 针对画布背景（`#practiceStage`）、票卡卡体（`#pkTicketCard`）和顶栏的深墨色彩重载，实现整屏真正的「皮肤同翻」。

---

### [P2-1] 动画兜底计时器设置过紧，掩盖 WAAPI 真实事件
- **现象**：Pixel 声称 headless 下无法触发 WAAPI 的 `onfinish` 事件，故必须依赖 fallback；但实测证明 Chromium headless 完全能够正常触发 `onfinish`。
- **实测数据**：
  - WAAPI 实际在 **287ms** 准时派发 `onfinish`；
  - Pixel 的代码写死了 `setTimeout(function () { land('fallback'); }, 280);`；
  - 导致 280ms 的计时器必定早于 287ms 的渲染微任务被执行，从而把 `landedBy` 强行篡改为 `'fallback'`。
- **建议改法**：
  - 将兜底定时器时间调整为 `320ms`（留出 40ms 的帧调度 buffer），让真浏览器和无头浏览器在 287ms 时由真实的 `anim.onfinish` 自然落定。

---

### [P2-2] 多卡并排高度不一时，矮卡底部留白空洞
- **现象**：在预设 2 (A+D+Q) 与预设 3 (六卡) 中，Card D（今日时长）仅 313px 高，而旁边的 Card A (587px) 与 Card Q (606px) 达 600px 左右。由于单行轨顶对齐，Card D 底部留有近 300px 的大片空白。
- **建议改法**：
  - 允许 Card D 容器在父轨中增加柔和的填充底衬，或考虑在空档处容纳操作辅助说明。

---

## 3. 详细实测数据支撑附录

### 3.1 画布留存控件完整交互实测表
在 Chromium 中逐一点击画布上现存的每一个控件并测量其真实 DOM 响应：

| 控件选择器 | 操作 | 前置读数 | 后置读数 | 判定 |
|---|---|---|---|---|
| `#pkBpmUp` / `#pkBpmDown` | 点击加速后减速 | 60 | 61 $\to$ 60 | **正常响应** |
| `#pkTicketDurUp` / `#pkTicketDurDown` | 点击增时后减时 | 10 | 11 $\to$ 10 | **正常响应** |
| `#pkMonthToggleBtn` | 点击月份切换 | "切8月" | "切9月" | **正常响应** |
| `#pkFolioBtn` / `#pkCloseFolioBtn` | 打开曲目票夹并关闭 | `open: false` | `open: true` $\to$ `open: false` | **正常响应** |
| `#pkRecords` / `#pkDrawerClose` | 打开今日记录抽屉并关闭 | `open: false` | `open: true` $\to$ `open: false` | **正常响应** |
| `.pk-session-pill` | 选中长音练习标签 | `content: ""` | `content: "正常长音练习"` | **正常响应** |
| `#pkStateToggle` (已选标签) | 切换运行态与准备态 | `stage-prep` (380px) | `stage-running` (220px) $\to$ `stage-prep` (380px) | **正常响应** |
| **Console 捕获** | 全交互流程 | - | **0 error, 0 warn, 0 pageerror** | **完全干净** |

### 3.2 负控实测输出证据
- **H2 负控 (`?audit=1&negctl=insert`)**：
  ```
  verdict: ASSERT_FAIL
  H2 fails: [
    "H2 fail [插入卡槽/待命] 待命态声明了 CSS 动画：animation-name=czNegLoop · duration=0.9s · iteration=infinite · play-state=running（期望 animation-name: none） ｜ 两次 transform 实测（150ms 间隔）：none vs none（无头环境动画时钟不走 → 两次采样必然相同，这条红由上面的声明值判出；真浏览器里两次会不同）"
  ]
  ```
- **B1 负控 (`?audit=1&negctl=1`)**：
  ```
  verdict: ASSERT_FAIL
  B1 fails count: 132
  B1 sample: "B1 fail [预设1/1133/light/A] 卡片外多了可见壳：div.cz-mod border=1px solid rgba(44, 62, 80, 0.12)（期望 0px none）· radius=20px（期望 0px）· bg=rgb(255, 255, 255)（期望 alpha 0）· shadow=rgba(44, 62, 80, 0.04) 0px 1px 3px 0px（期望 none）"
  ```
- **H1 负控 (待命态强制让 mini 与 slot 重叠)**：
  ```
  verdict: ASSERT_FAIL
  H1 fails: [
    "H1 fail [插入卡槽/待命] 票卡与槽已相交（期望不相交）：mini.bottom=116.0 slot.top=90.0",
    "H1 fail [插入卡槽/待命] 票卡与槽净距 -26px（期望 ≥4px）"
  ]
  ```

---

## 4. 总结与后续建议

- **整体评价**：Pixel 完成了难度极高的 iframe 原生画布嵌套与动态替换，且在不修改 `practice-ticket-v4-260920.html` 单个字符的前提下，保证了画布脚本零崩溃，工程功底扎实，负控设计到位。
- **整改要点**：
  1. **首要解决高度溢出 [P0-1]**：压紧 `.cz-insert`，将总高约束至 654px 以内，绝不可继续刺穿画布 body；
  2. **解决移动端排版 [P0-2]**：在 440/744 视口下允许卡片纵向折行堆叠，解除 `rowCount === 1` 的不合理断言；
  3. **补强两端状态联动 [P1-1]**：让插槽的「开始」与票卡的收拢联动起来。
- 本报告所有结论基于实际自动化采样数据，请归口 Hermes 统一派发修复。

---

## 5. 6 点判断（dad 指定由 agy 判定）

依据 [`brief-agy-judge-261011.md`](file:///Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/brief-agy-judge-261011.md) 要求，针对当前架构中 6 个关键待定项，由我（agy）作为第二路复核人给出明确裁决。每条均包含：**结论 + 核心理由 + 具体文件改动清单 + 边界与反例分析**，供 Hermes 统一派修落实。

---

### 第 1 点：模块轨宽度策略（按设计宽横滑 vs 弹性压窄塞入一屏）

- **agy 裁定结论**：
  **分档治理：宽屏桌面端（$\ge 1024\text{px}$）坚决保持现状「各卡按设计宽排一行 + 轨内向右横滑」；移动窄屏端（$< 1024\text{px}$，含 744/440 档）禁止死守单行 2500px 强滑，必须降级为纵向堆叠（`flex-direction: column`）或单卡翻页轮播。**
- **裁定理由**：
  1. **物理拟物尺寸红线不可逾越**：Card A (D1) 拥有 $R=140$ 缺口、旋钮半径、两翼边距 $\ge 16$px；Card D (D6) 拥有 30 分钟连续物理刻度尺与 monoline 大字。若在宽屏为迎合一屏而强行挤压至 270px/张（预设 2）或 130px/张（预设 3），核心文字排版与触控全部崩盘；
  2. **主预设天然免滑**：主力「预设 1 (A+S)」总宽仅 644px（含间距 668px），在 880px 主栏内天然一屏尽收，不需要右滑；预设 2/3 作为高级展开项，向右滑轨符合 dad 在 compose-03 定下的「一屏放不下就向右滑」的物理卡盒隐喻；
  3. **移动端必须尊重屏幕方向**：在 440 手机屏上，画布已纵向单列堆叠，此时在 408px 狭缝里塞 2500px 长轨是严重的 UX 缺陷，必须折行堆叠。
- **具体改动清单**：
  - **修改文件**：`docs/demos/practice-right-column-261003/canvas-01.html`
  - **CSS 改动**：
    - 保留桌面端 `.cz-rail { display: flex; flex-direction: row; overflow-x: auto; }`；
    - 追加 `@media (max-width: 1023px) { .cz-rail { flex-direction: column; align-items: stretch; overflow-x: visible; overflow-y: visible; } }`；
  - **JS/自检改动**：在 `runAudit()` 的 A1 断言中，分档判定：仅在 `o.docClientW >= 1024` 时断言 `rowCount === 1`；在 `< 1024` 视口下豁免单行限制。
- **反例与边界分析**：
  - *反例方案*：采用 CSS `transform: scale(0.6)` 强行缩放适应一屏。
  - *否决原因*：scale 缩放会导致文字亚像素抗锯齿失效、Retina 屏模糊，且点击事件坐标错位，严禁使用。

---

### 第 2 点：插入卡槽的触发语义（独立按钮 vs 联动顶部 banner）

- **agy 裁定结论**：
  **必须双向深度接通！形成「单点触发，全屏闭环」，彻底消除目前左侧票卡与右侧仪表盘各自为战的人格分裂。**
- **裁定理由**：
  1. **避免状态割裂**：目前点击 `.cz-insert-btn`（插入票卡），右侧 Card A 已经在飞速走字，而左侧真实票卡依然是 380px 的展开待命态（未锁定、未打孔）；点击顶栏 `#pkStateToggle`（切到练习态），左侧票卡收拢了，右侧卡槽却纹丝不动、仪表盘一片漆黑。用户体验完全脱节；
  2. **还原物理业务隐喻**：Dad 要求的「检票插卡」在业务上是一个完整的原子操作——插卡必然触发检票，检票必然点亮机器；
  3. **零成本状态同步**：画布自身具有成熟的 `enterRun()` / `exitRun()` 状态机，只需在插槽动画落定时触发广播。
- **具体改动清单**：
  - **修改文件**：`docs/demos/practice-right-column-261003/canvas-01.html`
  - **JS 改动**：
    1. 在 `runInsert()` 的落定回调 `land()` 中，调用 `canvasDoc().defaultView.enterRun()`；若当前画布内容标签未选（`content === ""`），自动兜底取当前科目首个选项（`cur.content_options[0]`）并派发，确保顺畅进态；
    2. 监听画布内部 `#pkStateToggle` 的点击事件：若在顶栏切到练习态，联动触发 `runInsert()`；若切回准备态，联动触发 `resetInsert()`；
    3. 仪表盘 Card A 内部暂停/结束时，向父级派发状态事件，同步顶栏文案。
- **反例与边界分析**：
  - *反例方案*：完全移除顶栏 `#pkStateToggle` 按钮，只保留右侧 `.cz-insert-btn`。
  - *否决原因*：在 440px 手机端，主栏被排在第 2 屏下方，首屏顶栏若失去状态指示与总控键，用户进页面第一眼无法感知系统就绪状态。

---

### 第 3 点：`spec-agy-compose03-261011.md` 描述偏差的处置

- **agy 裁定结论**：
  **由我（agy）在 `spec-agy-compose03-261011.md` 头部增加一条「已由 canvas-01 继承与外壳拆除」的归档批注（Handoff Note）；历史正文保持不变，不搞事后粉饰篡改。**
- **裁定理由**：
  1. **尊重工程审计真实性**：`spec-agy-compose03-261011.md` 忠实反映了 compose-03 诞生当刻的客观实测与当时的规范要求；
  2. **版本流转清晰**：compose-03 的外壳随后被 dad 拍板拆除并直接演进为挂入真画布的 `canvas-01.html`，这是正常的 Sprint 演进轨迹；
  3. **责任分明**：agy 的交付文档由 agy 负责追加版本迁移动态说明，Hermes 无需消耗精力回填历史 spec。
- **具体改动清单**：
  - **修改文件**：`docs/demos/practice-right-column-261003/spec-agy-compose03-261011.md`
  - **改动内容**：在 Frontmatter 下方追加：
    ```markdown
    > [!NOTE] 架构演进与交付批注 (2026-10-11)
    > 本规范中的外层槽位外壳（.slot）已按 dad 指示在后续版本中拆除（无壳卡片直接排布）。
    > 该组合器的完整演进落地已由 `canvas-01.html`（顶替真画布 pk-main-col）及 `spec-pixel-canvas-261011.md` 继承接管。
    ```
- **反例与边界分析**：
  - *反例方案*：直接将 `spec-agy-compose03-261011.md` 重写成无壳，或将文件删除。
  - *否决原因*：破坏审计链与既有验收台账；compose-03 文件仍在运行，历史数据需留档对照。

---

### 第 4 点：画布无深墨皮肤的换肤治理（接受 vs 补齐 vs 禁用）

- **agy 裁定结论**：
  **首选「宿主运行时纯注入补齐深墨样式（零改动源文件，sha256 绝对保持）」；工期紧迫时允许退守「在外壳细条上暂时隐藏深墨切键」；绝不接受「半黑半白严重割裂」与「直接违规改动画布源文件」。**
- **裁定理由**：
  1. **严禁触碰红线**：`practice-ticket-v4-260920.html` 是 dad 认定的基线画布，sha256 `e86d4bc56163218d` 必须保持零字节变动；
  2. **运行时注入已有现成通道**：`canvas-01.html` 已经在通过 `CANVAS_SCOPE` 往画布 head 里注入 CSS（补了 `--ac-fade: none`，消了原块）。在 `CANVAS_SCOPE` 里面多写一段 `:root[data-skin="ink"]` 针对 `#practiceStage`（底色换 `#14181C`）与 `#pkTicketCard`（票卡换 `#1E242B`）的样式覆盖，**既不改变源文件单字，又能完美实现全屏同翻**！
  3. **消灭刺眼空洞**：现在的 C1 断言只查 iframe 内部属性，对画布背景不管不顾，浅米色底衬嵌大黑块的观感不可接受。
- **具体改动清单**：
  - **修改文件**：`docs/demos/practice-right-column-261003/canvas-01.html`
  - **CSS/JS 改动**：
    1. 在 `CANVAS_SCOPE` 中追加：
       ```css
       :root[data-skin="ink"] #practiceStage { background: #14181C !important; }
       :root[data-skin="ink"] .pk-ticket { background: #1E242B !important; color: #FFF8F0 !important; border-color: rgba(255,255,255,0.12) !important; }
       :root[data-skin="ink"] .pk-top { background: #1A1E22 !important; color: #FFF8F0 !important; }
       ```
    2. 在 `setSkin()` 中同步向 `canvasDoc().documentElement` 挂载/移除 `data-skin="ink"`。
- **反例与边界分析**：
  - *反例方案*：直接打开 `practice-ticket-v4-260920.html` 编辑 CSS。
  - *否决原因*：触犯 dad「底座零改动」红线，sha256 改变会破坏所有历史基线比对，坚决禁止。

---

### 第 5 点：原 `pk-main-col` 四块移除、开始动作落到新卡的前提有效性

- **agy 裁定结论**：
  **前提完全成立！原 4 块整体移除方向 100% 正确，业务动作语义无一遗漏。**
- **裁定理由**：
  1. **功能一对一无损替换**：
     - 原 `#pkInstrCard` / `.timer-block` $\to$ 由 Card A (D1 仪表盘) 全新高保真 10:00 刻度、真收音孔阵替代；
     - 原 `#pkReqCard` $\to$ 由 Card Q (D4 老师要求卡) 替代；
     - 原入卡槽说明行 $\to$ 由 `.cz-insert` 槽位替代；
  2. **主 CTA 动作自然转移**：原 `#pkStartBtn`（检票 · 开始练习）的动作语义被完整转移至 `.cz-insert-btn`（插入票卡）与 Card A 的 `#btnPrimary`（开始练习）；
  3. **旧块必须退场**：若保留旧检票大按钮，页面将同时出现两个大 CTA 和两个计时器，造成严重的视觉争抢和交互死锁；
  4. **唯一缺失项是信号广播**：如第 2 点所述，只要将新按钮的 click 信号桥接回画布的生命周期，整个系统便天衣无缝。
- **具体改动清单**：
  - 维持当前将原 7 个选择器移入 `#czStubHost[hidden]` 的方案不变；
  - 仅按第 2 点修补开始动作的跨 iframe 信号桥接。
- **反例与边界分析**：
  - *反例方案*：将旧画布的 `#pkStartBtn` 掏出来贴在模块列最下方。
  - *否决原因*：页面将出现「仪表盘自带开始键」与「下方检票开始键」两套重叠控制器，造成重大可用性事故。

---

### 第 6 点：插入卡槽动画的形态与语义裁决

- **agy 裁定结论**：
  **形态与语义定位完全正确！280ms 时长与 10% back.out 缓动属于黄金参数组合，无需改动；「待命入槽」文字提示必须保留；仅需将兜底定时器从 280ms 延展至 320ms，解除对 WAAPI 真实事件的误伤打断。**
- **裁定理由**：
  1. **明确不是纯装饰**：卡槽是承上启下的物理确认元件，承担「票卡就绪 $\to$ 机器通电点亮」的感知确权，心理隐喻极其强烈；
  2. **280ms 时长极其克制**：在 48px 的位移下，$\le 320$ms 的规约被严格遵守，动作干脆利落，不拖泥带水，符合高频工具类产品的高效诉求；
  3. **10% 回弹自然逼真**：`cubic-bezier(0.34, 1.56, 0.64, 1)` 精准还原了卡片插入物理卡槽时卡簧限位的轻微金属回弹，无多余弹性晃动，品质感极高；
  4. **揭露真时钟断言真相**：Chromium 实测在 287ms 会精准触发 WAAPI `onfinish`。Pixel 将 `setTimeout` 误设为同等的 280ms，导致事件循环中宏任务抢先跑完了 `land('fallback')`。延后至 320ms 即可实现真实 WAAPI 自然落定。
- **具体改动清单**：
  - **修改文件**：`docs/demos/practice-right-column-261003/canvas-01.html`
  - **JS 改动**：
    - 将 `runInsert()` 中的 `setTimeout(function () { land('fallback'); }, INSERT_MS);` 改为 `setTimeout(function () { land('fallback'); }, 320);`；
    - 保持 280ms 声明时长与 `cubic-bezier(0.34, 1.56, 0.64, 1)` 曲线不变；
    - 保持 `#czInsertStat` 待命与运行态文字不变。
- **反例与边界分析**：
  - *反例方案*：将插卡动画做成多阶段长达 600ms 的复杂逐帧动效（如卡片先水平飞入再下落）。
  - *否决原因*：练习启动动作极其高频，任何超过 350ms 的花哨等待都会迅速引起使用者（孩子和家长）的交互厌烦。



---

## 6. 复验（v2）· 真窗口实测定案

> **复验脚本**（本地一键可点复现）：
> ```bash
> /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 docs/demos/practice-right-column-261003/scripts/verify-real-window-261011.py
> ```
> 测试环境：Playwright Chromium 140+，真 DOM 窗口（非页内自检模拟），Mac 本地真实时钟。

---

### 1. P0-2：窄屏纵向堆叠定案

#### 实测数据表

| 视口场景 | 预设 | `docClientW` | `railFlexDir` | `railClientW` | `railScrollW` | 模块数 | 行数 | 堆叠/横滑判定 |
|---|---|---|---|---|---|---|---|---|
| **真 744 窗口** (`744x1133`) | ① (`A+S`) | 744 | `column` | 580 | 580 | 2 | **2** | 纵向堆叠，无横滑 |
| | ② (`A+D+Q`) | 744 | `column` | 580 | 580 | 3 | **3** | 纵向堆叠，无横滑 |
| | ③ (`A+B+S+D+R+Q`) | 744 | `column` | 580 | 580 | 6 | **6** | 纵向堆叠，无横滑 |
| **真 440 窗口** (`440x956`) | ① (`A+S`) | 440 | `column` | 408 | 408 | 2 | **2** | 纵向堆叠，无横滑 |
| | ② (`A+D+Q`) | 440 | `column` | 408 | 408 | 3 | **3** | 纵向堆叠，无横滑 |
| | ③ (`A+B+S+D+R+Q`) | 440 | `column` | 408 | 408 | 6 | **6** | 纵向堆叠，无横滑 |
| **真 1280 窗口** (`1280x800`) | ① / ② / ③ | 1280 | `row` | 878 | 878 / 1368 / 2516 | 2 / 3 / 6 | **1** | 宽屏单行，轨内横滑 |
| **真 1133 窗口** (`1133x800`) | ① / ② / ③ | 1133 | `row` | 751 | 751 / 1368 / 2516 | 2 / 3 / 6 | **1** | 宽屏单行，轨内横滑 |
| **Hermes 场景** (1265 窗口点 `#czVp="744"`) | ① / ② / ③ | 1265 | `row` | 863 | 863 / 1368 / 2516 | 2 / 3 / 6 | **1** | **仍为单行，未堆叠！** |

#### 现象破译：为什么 Hermes 的数字与 Pixel 对不上？
1. **Pixel 的声明路径**：Pixel 声称在 744 档和 440 档下实现了 `column` 堆叠（行数 6，轨宽 580 / 468）。**在真 744 / 440 浏览器窗口下，此断言确实成立**！因为真实窗口将画布 iframe 压缩到了 `< 1024px`，触发了 `CANVAS_SCOPE` 内部的 `@media (max-width: 1023px) { .cz-rail { flex-direction: column; } }`。
2. **Hermes 的踩坑路径**：Hermes 在一个 1265px 宽的桌面浏览器窗口中打开页面，并点击了顶栏 `#czVp` 的 `744` 切换按钮。
   - **根本原因**：顶栏 `#czVp` 的按钮只调用了 `setVp('744')`，**该函数仅仅修改了卡片 iframe 内部的 `data-vp` 属性，根本没有改变外层画布 iframe 的宽度**！
   - 画布 iframe 依然保持 1265px 宽（`docClientW = 1265`），而 Pixel 的媒体查询依赖的是视口宽度 `@media (max-width: 1023px)`，导致媒体查询在 1265 宽窗口下根本不会生效！因此，模块轨继续执行宽屏的 `flex-direction: row`，行数依然为 1，轨宽保持 863px > 744px。
   - 这也是为什么 Hermes 测出 `railClientW 852 > 744`：这不是 min-width 在撑，而是外层画布窗口根本就是 1265px 宽！

#### 判词与 Pixel 声明对比
- **判词**：**只修了真窗口那一路（真窗口生效，顶栏视口档模拟未联动）**。
- **与 Pixel 声明对比**：**部分一致**。Pixel 在真实窄视口（窗口宽度 `< 1024`）下确实生效了垂直流动堆叠；但 Pixel 遗漏了桌面脚手架顶栏 `#czVp` 按钮与画布宽度的联动（点击 744/440 并未缩放画布 iframe），导致在桌面浏览器中通过控制条调试窄屏时依然展现为单行横滑。

---

### 2. P2-1：`landedBy` 与时序定案

#### 实测数据表

| 测试场景 | WAAPI `onfinish` 触发时延 | 兜底 `setTimeout(320)` 时延 | 胜出者 (`landedBy`) | 落定时延 (`landTimeMs`) | `observedMs` (审计采样) |
|---|---|---|---|---|---|
| **空载无干扰前台真实时钟** | 289.7 ms | 321.4 ms | **`onfinish`** | 289.7 ms | 770.0 ms |
| **轻度主线程抖动 (50ms 负载)** | 338.2 ms (被推迟) | 320.1 ms | **`fallback`** | 329.2 ms | 784.0 ms |
| **Hermes 浏览器会话审计** | 推迟（审计 6 iframe 负载） | 320 ms 准时到期 | **`fallback`** | ~320 ms | **784.0 ms** |

#### 现象破译：为什么 Hermes 看到 `fallback + 784ms + advanced true`？
1. **40ms 极窄时序竞态（致命隐患）**：
   - 动画声明时长 `INSERT_MS = 280ms`，兜底定时器 `FALLBACK_MS = 320ms`。
   - 两者之间**仅有 40ms 的微小安全缓冲期**（不到 60Hz 的 2.5 帧）。
   - WAAPI 动画由渲染引擎 Compositor 驱动，当动画结束向主线程派发 `finish` 事件时，若主线程正在处理 `runAudit()` 繁重的 6 组 iframe 加载、DOM 测量、GC 或标签页处于非活跃状态，事件循环产生哪怕 35~50ms 的微小延迟，`setTimeout(320)` 的宏任务就会抢先出列！
   - 一旦兜底执行，`land()` 立即调用 `mini.getAnimations().forEach(a => a.cancel())` 取消了动画，使得 `onfinish` 永远失去触发机会，结果被硬生生盖戳为 `'fallback'`。
2. **784ms 的数学来源破译**：
   - Hermes 误以为 784ms 是动画耗时，认为“远超声明的 280 + 兜底 320”。
   - **真相**：查看 `canvas-01.html` 第 15738-15753 行代码：
     ```javascript
     var t0 = performance.now();
     var job = runInsert();
     return waitAnim(job, 1500).then(function () {
       return new Promise(function (r) { setTimeout(r, 420); }); /* 等 enterRun/兜底 force 落定 */
     }).then(function () {
       out.after = { observedMs: +(performance.now() - t0).toFixed(1) ... };
     });
     ```
     `observedMs` 计时的终点在 `setTimeout(r, 420)` **之后**！
     数学拆解：
     $$\text{兜底触发延时 (320ms)} + \text{waitAnim 内部延时 (20ms)} + \text{硬编码等待落定 (420ms)} + \text{任务调度抖动 (24ms)} = \mathbf{784ms}$$
     **784ms 根本不是动画时长，而是测量框架加上 420ms 强制等待后的采样时间点！**
3. **`clockProbe` 为何是 `advanced: true`**：
   - 探针动画时长仅 200ms。在经历 `waitLoads(3000)` + 150ms + 784ms 之后去采样探针，真实时钟早已推进完毕，自然报告 `advanced: true` 与 `playState: finished`。这证明环境绝非虚拟时间冻结，而是上面分析的 40ms 窄窗口抖动导致兜底抢跑。

#### 判词与 Pixel 声明对比
- **判词**：**没修好（存在脆弱的时序竞态 Bug；784ms 属测量延迟误读）**。
- **与 Pixel 声明对比**：**不一致**。Pixel 声称“真时钟环境走 onfinish，无头 virtual-time 才是 fallback”。实测证明：即使在 100% 真时钟的真浏览器中，只要稍微存在 40ms 的负载抖动，兜底就会抢跑，产生大量误报。
- **修复方案**：将 `FALLBACK_MS` 从 `320ms` 放大至 `500ms` 或 `600ms`。真时钟在 290ms 完成，留出 >200ms 的充裕防抖期，永不被抢跑；无头冻结环境在 500ms 兜底，两全其美。

---

### 3. P0-1：三预设 × 三档高度越界复算

#### 实测数据表

| 窗口档位 | 预设 | `ticketBottom` | `ticketH` | `modColBottom` | `bodyBottom` | 越界量 (`modCol - ticket`) | 布局形态 |
|---|---|---|---|---|---|---|---|
| **1280 宽屏** | ① (`A+S`) | 686.0 | 654.0 | 686.0 | 688.0 | **0.0 px** | 并排，`syncRailBudget` 限高生效 |
| | ② (`A+D+Q`) | 686.0 | 654.0 | 686.0 | 688.0 | **0.0 px** | 并排，`syncRailBudget` 限高生效 |
| | ③ (`全量`) | 686.0 | 654.0 | 686.0 | 688.0 | **0.0 px** | 并排，`syncRailBudget` 限高生效 |
| **1133 宽屏** | ① (`A+S`) | 686.0 | 654.0 | 686.0 | 688.0 | **0.0 px** | 并排，`syncRailBudget` 限高生效 |
| | ② (`A+D+Q`) | 686.0 | 654.0 | 686.0 | 688.0 | **0.0 px** | 并排，`syncRailBudget` 限高生效 |
| | ③ (`全量`) | 686.0 | 654.0 | 686.0 | 688.0 | **0.0 px** | 并排，`syncRailBudget` 限高生效 |
| **744 窄屏** | ① (`A+S`) | 907.9 | 849.9 | 2116.9 | 2140.6 | +1209 px | 纵向堆叠，模块在票卡下方自然延伸 |
| | ② (`A+D+Q`) | 907.9 | 849.9 | 2541.9 | 2565.6 | +1634 px | 纵向堆叠，模块在票卡下方自然延伸 |
| | ③ (`全量`) | 907.9 | 849.9 | 4278.9 | 4302.6 | +3371 px | 纵向堆叠，模块在票卡下方自然延伸 |
| **440 窄屏** | ① (`A+S`) | 846.5 | 788.5 | 2049.5 | 2073.2 | +1203 px | 纵向堆叠，模块在票卡下方自然延伸 |
| | ② (`A+D+Q`) | 846.5 | 788.5 | 2474.5 | 2498.2 | +1628 px | 纵向堆叠，模块在票卡下方自然延伸 |
| | ③ (`全量`) | 846.5 | 788.5 | 4227.5 | 4251.2 | +3381 px | 纵向堆叠，模块在票卡下方自然延伸 |

#### 判词与 Pixel 声明对比
- **判词**：**真修好（宽屏 0 越界绝对齐平；窄屏堆叠流式符合设计规约）**。
- **与 Pixel 声明对比**：**一致**。宽屏下通过 `syncRailBudget()` 动态约束 `rail.style.maxHeight`，实测 1280 与 1133 各预设下的 `modColBottom` 与 `ticketBottom` 均为 686.0px，越界量为精准的 0.0px；窄屏下整体转换为纵向流式排版，模块自然排布在票卡下方，属于符合预期的正常垂直流动。
