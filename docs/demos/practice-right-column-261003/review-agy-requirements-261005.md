# 全量需求对照 Review 报告（2026-10-05）

> **审计对象**：`docs/demos/practice-right-column-261003/` 下全部 Demo 与脚手架（服务端口 `http://localhost:8771/practice-right-column-261003/`）  
> **审计基准**：MRD 全量需求（含末尾 dad 针对 Q1–Q6 亲自答复）、`widget_prompt_ui.md`、`bauhaus_metronome_ui_design_guide.md`、`card-contract.md`、相关设计参考图。  
> **审计原则**：严格只读；逐项核验真实 DOM、CSS 规则、计算样式、`?audit=1` 输出，禁凭印象判定。  
> **判定四档**：**做到 / 部分 / 未做 / 做不到**

---

## 统计总览

| 模块类别 | 审查项数 | 做到 | 部分 | 未做 | 做不到 |
|:---|:---:|:---:|:---:|:---:|:---:|
| **1. 仪表盘卡 (D1 & D3)** | 18 | 15 | 3 | 0 | 0 |
| **2. 节拍器卡 (D2)** | 5 | 5 | 0 | 0 | 0 |
| **3. 老师要求卡 (D4)** | 5 | 5 | 0 | 0 | 0 |
| **4. 今日练习记录卡 (D5)** | 5 | 4 | 1 | 0 | 0 |
| **5. 今日练习时长卡 (D6)** | 5 | 5 | 0 | 0 | 0 |
| **6. 向右延伸卡片 Dashboard 总体架构** | 8 | 7 | 1 | 0 | 0 |
| **7. 共享刻度尺与契约门禁** | 4 | 4 | 0 | 0 | 0 |
| **8. 早期历史遗留需求** | 4 | 2 | 0 | 2 | 0 |
| **合计** | **54** | **47** | **5** | **2** | **0** |

---

## A. 逐条需求对照表

| # | dad 需求原文（摘要，保留关键限定词） | 落点（文件:行 或 页面元素） | 判定 | 证据（实测值 / DOM / 代码） |
|---|---|---|:---:|---|
| **1.0** | 逐帧 copy `科目卡片参考-04.jpg` 整体 UI 与 layout；拟物风格；可替换仪表盘样式的模式（默认样式） | `dashboard-skin-01-v2.html:20` | **做到** | 提供浅银与深墨两套拟物皮肤（圆角金属外框、高光拉丝底纹、内凹阴影），顶部带换肤切换器；68 个 `--dash-*` token 契约收口。 |
| **1.1** | `timer-block` 圆角矩形黄底 + 橙细边不要，重新设计，内部 `timerCard` 元素保留 | `dashboard-skin-01-v2.html:236` | **做到** | 历史黄底橙边色 `#F0D060`/`#FFFDF5`/`#FFF0E8` grep 计数为 0。改用深色面板 `--dash-panel` (`#1C1E21`/`#14181C`) + 金属银外壳。 |
| **1.2** | 仪表盘整体外框金属银色，顶部不规则超圆角 dark panel；最上通栏 bar（左麦克风 icon、时间、电池） | `dashboard-skin-01-v2.html:236,245` | **做到** | `.panel` 采用非对称超圆角 `border-radius: var(--dash-radius) var(--dash-radius) 18px 18px`；`.status` 内麦克风 SVG、`#liveClock`、电池槽+76% 读数全齐。 |
| **1.2.1** | 专辑封面位放科目图，裁切正方形，圆角矩形边框 + 浅灰细线圆角矩形外围边框；下方展示科目名称 | `dashboard-skin-01-v2.html:252` | **部分** | `.cover-col` 结构包含正方形裁切、外围细线圈 `.cover-ring` 及科目名「萨丽哈」。**缺口**：图源仍硬编码为通用占位图 `practice-hero-ticket-260922.png`，未能根据不同科目读取对应专属封面。 |
| **1.2.2** | 歌曲名位改放练习计时 readout；进度条位改放 ruler 刻度尺 | `dashboard-skin-01-v2.html:270` | **做到** | 歌曲名位为 `#ttCounter`（数字滚轮）+ `#metaVal`；进度条位为生产共享件 `.ruler-wrap > .ruler#ruler`。 |
| **1.2.3** | 歌词位置放 session 标签小标题 + 老师要求正文滚动播放（点击暂停/恢复）<br>*(注：MRD 2610041201 第 4 条及 Q5 拍板修正：彻底删除 lyric-col，老师要求放 D4 独立卡)* | `dashboard-skin-01-v2.html:260` | **做到** | 已遵照 dad 最新拍板口径将 `lyric-col` 彻底删除（grep `lyric-col` 计数为 0），下方模块顶上，严格贴合参考图 04。 |
| **1.2.4** | volume 位放速度 bpm 要求；track 位放今日累计练习时长 | `dashboard-skin-01-v2.html:285` | **部分** | `.panel-foot` 左侧显示 `#bpmRead`「♩=82」，右侧显示 `#todayTotal`「今日 42分」。**缺口**：`#todayTotal` 为静态 mock（标注有 `data-placeholder`），尚未连通真实后端统计 API。 |
| **1.2.5** | 左下 bpm 显示与下方银色控制面板大旋钮联动，显示当前练习设置的 bpm 速度 | `dashboard-skin-01-v2.html:766` | **做到** | 实测调节旋钮时，`setBpm()` 实时赋值 `#bpmRead`，数值与术语同步响应。 |
| **1.3** | 银色控制面板区 +/- 位置对调（右侧 +，左侧 -）；同一套 +/- 应用到进度条两侧，替换老 timerCard 的 +/-<br>*(注：MRD 2610041201 第 8 条修正：mid-row 控制计时，ruler-wrap 的 +/- 移除)* | `dashboard-skin-01-v2.html:275,306` | **做到** | 控制面板中 `#silverMinus` 居左、`#silverPlus` 居右；`.ruler-wrap` 内历史 `+ / -` 步进按钮已按最新指示彻底移除。 |
| **1.4** | Large Rotary Knob 为全新单独开发节拍器调节 bpm 旋钮，左小右大；旋转控制上方 bpm；练习进行时调用系统音响像真节拍器按 bpm 打出声音 | `dashboard-skin-01-v2.html:298`<br>`metronome-01-v2.html:369` | **部分** | 大旋钮旋转、弧度阻尼、调速已在 D1 落地；高精度 Web Audio 拍声引擎已在 D2 (`metronome-01-v2.html`) 完整实现。**缺口**：D1 页面内 `AudioContext` 引用数为 0，仪表盘大旋钮与拍声引擎分立在两页，尚未代码级合成。 |
| **1.4.1** | 参考 `bauhaus_metronome_ui_design_guide.md` + `节拍器ui.PNG` 评估开发对应功能 | `metronome-01-v2.html:625` | **做到** | 4 粒 beat 状态灯（含余晖衰减）、微调 ±1、常用速度芯片（60/72/82/96/120）及民乐术语全部落地。 |
| **1.5** | 银色控制面板下方分为左中右三个模块（扬声孔 / 操作按钮区 / 谱架模式入口） | `dashboard-skin-01-v2.html:302`<br>`dashboard-bottom-blocks-01-v2.html:268` | **做到** | D1 内置精简版 `.deck`，D3 (`dashboard-bottom-blocks-01-v2.html`) 交付完整高保真机身壳仿真模型。 |
| **1.5.1** | 左侧区域为扬声孔，随麦克风捕获声音/节奏震动动效 | `dashboard-bottom-blocks-01-v2.html:282` | **做到** | 48 孔阵支持真实麦克风 (`getUserMedia` + RMS 分析) 与 82 BPM 演示包络双链路，具备同心圆扩散波与惯性阻尼。 |
| **1.5.2** | 中间区域为操作按钮区，保留现有按钮逻辑与状态，UI 符合本仪表风格（参考 button-reference-01/02） | `dashboard-bottom-blocks-01-v2.html:342` | **做到** | 完整实现 `prep → run → pause` + `提前结束` 状态机；交付拟物凹面按键与扁平胶囊两套高精度变体。 |
| **1.5.3** | 右侧放谱架模式按钮入口，设计按钮 UI 样式 | `dashboard-bottom-blocks-01-v2.html:481` | **做到** | 交付实体键（74px×48px）与胶囊钮 b（44px 等高对齐）两种视觉变体。 |
| **1.5.4** | 谱架模式本期不做功能，点击无效果（出 UI 样式，后续开发补全） | `dashboard-bottom-blocks-01-v2.html:857` | **做到** | 点击谱架按钮仅就地弹出 2.5s 状态提示「本期仅样式」，无侵入跳转。 |
| **4101-D1.1** | 3 个宽度按钮（1133x744、744x1133、440x956）点击后下面 UI 必须有实际响应 | `dashboard-skin-01-v2.html:624` | **做到** | 点击切换实测宽度：1133 档为 420px，744 档为 480px，440 档为 390px，且中段列宽比与字号联动变化。 |
| **4101-D1.2** | ruler-wrap 必须用生产上确定好的元素（含 `notes-bubbles` 跳动 + `ruler-vine` 花盛开与生长） | `dashboard-skin-01-v2.html:275` | **做到** | 接入 `shared/ruler-production.{css,js}`，实测 60 刻度、22 气泡槽、卷草纹开花动画完全对齐生产。 |
| **4101-D1.3** | 保留 demo 中 "rule is dragging" 的拖拽动画效果并融合进生产尺子 | `dashboard-skin-01-v2.html:730` | **做到** | 拖拽刻度尺时保留微晃弹性反馈，松手触发阻尼回弹，与生产切片兼容共存。 |
| **4101-D1.5** | panel-foot left 节拍字数超出区域限制，只保留几分音符+速度；关联节拍器或老师要求；计时取快照 | `dashboard-skin-01-v2.html:286` | **做到** | 文本精简为「♩=82」无溢出；内部状态支持在计时启动时拍摄快照，防止计时中漂移。 |
| **4101-D1.6** | mid 圆弧太大了，收小圆弧，knob 往下探，左右 +/- 不覆盖 panel-foot | `dashboard-skin-01-v2.html:292` | **做到** | 圆弧半径由 140px 收小至 88px（深度 18px），旋钮上移并缩至 112px，左右 +/- 与 panel-foot 拥有 14px 安全留白。 |
| **4101-D3.1** | speaker 选择孔阵 2 金属沉头 | `dashboard-bottom-blocks-01-v2.html:328` | **做到** | `.grille-6x8.variant-countersink` 默认激活，具有外圈深环 + 内凹投影 + 下沿微光。 |
| **4101-D3.2** | speaker 太靠左，位置优化更协调 | `dashboard-bottom-blocks-01-v2.html:270` | **做到** | `.deck-row` 增加左右安全 padding (10px 18px)，扬声孔在侧翼视觉均衡。 |
| **4101-D3.3** | 按钮选择扁平胶囊 | `dashboard-bottom-blocks-01-v2.html:426` | **做到** | 交付 `.pill-flat` 变体，高度 44px，纯色填充搭配浅边框，无多余拟物投影。 |
| **4101-D3.4** | 谱架按钮用胶囊 b，高度与中间按钮对齐，不要圆角矩形外框，只需上面 icon + 下面文字 | `dashboard-bottom-blocks-01-v2.html:526` | **做到** | `.stand-btn-pill` 高度严格为 44px（与中间按键对齐），纵向排列 icon 与文字，无多余厚边框。 |
| **4101-D3.5** | 开启麦克风是用户主动行为，增加开启麦克风的入口（默认静止/关闭） | `dashboard-bottom-blocks-01-v2.html:585` | **做到** | 增加 `#micToggle` 胶囊开关，初始为 OFF（静止灰环），必须用户主动点击授权才激活律动。 |
| **4101-D2.1** | 节拍器强弱拍可以开启/关闭，默认关闭，要有按钮控制 | `metronome-01-v2.html:618` | **做到** | 状态栏包含 `#accentToggleBtn`，初始显示「强弱拍：关」，点击切换，默认关闭。 |
| **4101-D2.2** | 启动节拍器按钮不要那么大，上面的 knob 点击即可启动和暂停 | `metronome-01-v2.html:653,669` | **做到** | 主启动键缩减为 38px 紧凑胶囊；大旋钮 `#rotaryKnob` 绑定 `toggleMetronome()`，支持点击启停。 |
| **4101-D2.3** | ruler-input 恢复生产上的 UI 与动画效果（花开、气泡起跳） | `metronome-01-v2.html:680` | **做到** | 接入 `shared/ruler-production.{css,js}`，彻底替换早期原生 range input。 |
| **4101-D2.4** | `metronome-01-notes.md` 乱码排查确认 | `metronome-01-notes.md:末尾` | **做到** | 排查确认文件本身为合法 UTF-8，系 Obsidian 端预览编码兼容问题，已在手记末尾追加技术说明。 |
| **2.0 / Q5** | 老师要求卡改为独立卡片，与仪表盘同一层级，吹奏计时中随时可看（脱离 popout） | `requests-card-01.html:204` | **做到** | 彻底拆除弹窗外壳（无遮罩、无关闭钮），自成一体机身 `.req-card-chassis`。 |
| **2.1.1** | 老师要求卡默认展示本周最新要求，可查历史要求 | `requests-card-01.html:694` | **做到** | 默认加载 index=0 最新要求（带「本周最新」徽标），支持翻阅历史 6 次指导。 |
| **2.1.2** | 浏览交互用 3D 卡叠 (Deck) 变体 A（左右切换层叠推进，键盘 ←/→ 也能切） | `requests-card-01.html:728,891` | **做到** | GSAP 驱动 3D 深度堆叠，支持左右拖拽抛飞手势、底栏导航及键盘 `ArrowLeft/Right`。 |
| **B1** | 卡片中任何元素/可交互按钮里面的标题文字特别是标题类型的不能没事换行 | `requests-card-01.html:309` | **做到** | 标题采用弹性收缩与 `nowrap` 限制，全视口下无异常断行。 |
| **B2** | 老师要求正文要有排版、有段落、最好展示全文（非原始字段 dump） | `requests-card-01.html:674` | **做到** | 文本智能分段，句首带 `▪` 重点符号，老师备忘独立强调框，全文自适应纵向滚动展示。 |
| **3.1** | 今日练习记录打开样式 copy `2609252147-reference-01.png`，本项目主题配色，console 风，扁平化 | `today-records-01.html:165` | **做到** | 采用 `--dash-*` token（浅银/深墨），纯扁平控制台设计，字号、留白严格对齐参考规范。 |
| **3.2** | 头部通栏 bar 右侧保留“折叠/展开”双状态切换（科目级 ↔ session 级） | `today-records-01.html:293` | **做到** | `#btnFold` 与 `#btnOpen` 切换科目级汇总（3 行）与 session 明细级（12 行）。 |
| **3.3** | 头部下方 3 个 heroic 区：总时长、练习时长、相比昨日（红+绿-） | `today-records-01.html:298` | **部分** | UI 结构、三数字与红绿 delta 表现完全做到。**缺口**：数据库生产写入侧目前 `started_at` 仅在提交时写入，缺乏首个 session 启动的自然总时长模型。 |
| **3.4** | 列表区 6 列：科目、总时长、速度、单次、明细 (session)、占比 (%) | `today-records-01.html:220` | **做到** | 包含完整 6 列，占比条动态计算渲染，合计严格等于 100%。 |
| **3.5** | 列表滚动到卡片下方有渐进模糊效果（向下边缘模糊，离开变清晰） | `today-records-01.html:540` | **做到** | GSAP 逐帧计算边缘交叠距离，动态注入 `blur(...)` 滤镜，离开边缘迅速清零。 |
| **4101-Dur.1**| 今日练习时长卡：包豪斯极简暗黑/浅银 Widget 风格 | `practice-duration-card-01.html:18` | **做到** | 依据 `widget_prompt_ui.md` 规范构建，68 `--dash-*` token 换肤支持。 |
| **4101-Dur.2**| 顶部日期栏 ("Tuesday 17") + 大号几何镂空数字时钟 ("08:26" + "43") | `practice-duration-card-01.html:263,269` | **做到** | 日期栏显示「10月3日 周六」，时钟区为超大时分读数及小字号秒数。 |
| **4101-Dur.3**| 练习栏标题 "Practice" + 橙色胶囊总时长药丸 ("[3H 45M]") | `practice-duration-card-01.html:276` | **做到** | 标题栏展示「练习」与亮橙色胶囊 `#totalPill`（「57M」）。 |
| **4101-Dur.4**| 当日练习总进度时间轴 Bar：橙色大圆角胶囊、微垂直刻度、实线练习+虚线休息 | `practice-duration-card-01.html:283` | **做到** | 亮橙色胶囊轨道带密集刻度底纹，两端标明起止时间，内含实心练习段与虚线休息段。 |
| **4101-Dur.5**| 底部状态栏：最近一次科目时长 + 三角机械节拍器 icon + 皇冠 icon（超昨日高亮） | `practice-duration-card-01.html:289` | **做到** | 左下显示「吐音 1 分 30 秒」，右下排列节拍器 SVG 与超越昨日高亮皇冠 SVG。 |
| **4101.1** | practice 界面升级为向右（不能往下，保持纵向一屏）拖动/滑动查看更多卡片 | `compose-01.html:185`<br>`card-dashboard-skeleton-01.html:215` | **做到** | 横向轨道 `overflow-x: auto; scroll-snap-type: x mandatory`，高度锁定在一屏内。 |
| **4101.2** | 容纳 6 张模块化卡片（票夹、仪表盘、节拍器、老师要求、今日记录、今日时长） | `compose-01.html:234` | **做到** | 组合页包含 6 个卡槽，按契约完整装入全部卡片。 |
| **4101.4** | 可调整顺序、可编辑、可添加删除的组件化卡片组合 dashboard | `card-contract.md` | **部分** | 卡片组件化解耦与独立契约已确立。**缺口**：运行时用于用户拖拽调序、开关增删卡片的前端交互控制台尚未开发。 |
| **4101.5** | 向右延伸方式：键盘方向键 + iPad/iPhone 触摸滑动 + 松手吸附 | `card-dashboard-skeleton-01.html:219` | **做到** | 支持原生横向滑扫、`←/→/Home/End` 键盘切卡及松手自动吸附。 |
| **4101.6** | 组件化卡片相邻展示时有合理边缘间距（16px）与排布 | `card-contract.md:22` | **做到** | 轨道统一配置 `gap: 16px; padding: 16px`，卡片外沿呼吸感充分。 |
| **4101.7 / Q1** | 卡片高度不超设备视口；iPhone 440 档改为纵向往下排（不横滑，单卡铺满） | `compose-01.html:213`<br>`card-dashboard-skeleton-01.html:271` | **做到** | 440 档轨道转换为 `flex-direction: column`，宽度 100% 纵向堆叠，横向 0 滚动。 |
| **4101.8, 9 / Q3** | 每张卡独立命名、保留分支不删除；practice 独立分支持续迭代 | `card-contract.md:31` | **做到** | 主分支 `feat/practice-ui-iter-260920` 长期维护；卡片文件固定命名留存于 demo 目录。 |
| **4101.10 / Q2** | 每张卡声明 min / 默认 / max 宽度契约 | `card-contract.md:9` | **做到** | 6 张卡均在契约与代码中声明标准宽度（460/420/400/440/460/380）。 |
| **4101-Ruler.1**| 刻度尺必须使用生产切片件，禁止自造 | `shared/ruler-production.{css,js}` | **做到** | 生产 `practice.html` 逐行切片，D1 与 D2 均已接入，自检页实测 `ASSERT_OK`。 |
| **4101-Gate.1**| 68 `--dash-*` token 契约一致性门禁 | `scripts/verify-demos.py` | **做到** | 脚本静态检查 6 张卡页面，变量名集合完全一致，0 违规。 |
| **4101-Gate.2**| 浅银 / 深墨两套皮肤 WCAG AA 对比度门禁 | `scripts/token-contrast.py` | **做到** | 静态与动态抽检门禁不合格数为 0；正文 ≥4.5，大字号 ≥3.0。 |
| **4101-Gate.3**| `?audit=1` 契约自检实测与负控（弄红/弄绿） | 各卡自检逻辑 | **做到** | 核心卡片输出 JSON 报告，负控（改前红字 FAIL、改后绿字 OK）均已实测通过。 |
| **Prev-02.1** | 准备态/练习态双状态流（计时开始后锁定非核心模块，无需重载页面） | `dashboard-skin-01-v2.html:610` | **做到** | D1 通过 `data-mode="prep" / "run"` 驱动视觉流转，纯前端无刷新平滑切换。 |
| **Prev-02.2** | 今日练习金字塔概念（three.js / blender 互动 3D 薄卡片搭建金字塔） | — | **未做** | 原 MRD 归入概念脑爆与技术调研阶段，向右卡片 dashboard 推进期间未立项开发。 |
| **260922-3.1** | 英文字符与重要数字采用衬线字体规范 | `dashboard-skin-01-v2.html:93` | **做到** | 引入 `DESIGN.md` 指定 token `--font-serif`，标题与关键指标字体符合规范。 |
| **260922-3.7** | 步进加减号按钮按住长按加速数字变动 | `dashboard-skin-01-v2.html:785` | **未做** | 现有步进按钮仅绑定了单击 `click` 事件，尚未实现 `pointerdown` 长按加速递增递减。 |

---

## B. 缺口清单（按严重度排）

### P0 — 挡住整体交付的硬缺口（2 项）

1. **D1 仪表盘大旋钮未合成 D2 拍声引擎（Req 1.4）**
   - **现象**：D1 仪表盘在练习计时时无法调用系统音响打出节拍声（代码中 `AudioContext` 出现次数为 0）；而成熟的 Web Audio 调度器仍留在独立的 D2 页面中。
   - **落点**：`docs/demos/practice-right-column-261003/dashboard-skin-01-v2.html`
   - **建议动作**：将 `metronome-01-v2.html` 的 Web Audio 调度引擎移植到 `dashboard-skin-01-v2.html`，在计时器进入 `run` 态时依据当前 BPM 启动发声。

2. **多卡组合在 `compose-01.html` 中依赖 iframe，无法直接作为生产方案（Req 4101.2）**
   - **现象**：组合页通过 6 个 iframe 拼装，在移动端（iPad / iPhone Safari / WKWebView）中会导致滚动手势拦截、内存开销及跨 iframe 状态共享失效（如 D1 启动时无法直接向 D4/D5 广播当前 session）。
   - **落点**：`docs/demos/practice-right-column-261003/compose-01.html`
   - **建议动作**：迁入生产前，将 6 张卡由 iframe 承载重构成基于单一 DOM 树的 Web Component 或原生模板组合，实现单应用状态总线直通。

---

### P1 — 明显差一截的软缺口（4 项）

1. **D1 仪表盘今日累计时长为静态 Mock（Req 1.2.4）**
   - **现象**：D1 右下角写死「今日 42分」，带 `data-placeholder` 标记，未接真实统计接口。
   - **落点**：`dashboard-skin-01-v2.html:288`
   - **建议动作**：对接 `/api/practices/{today}` 接口，将打卡累计时间换算并动态填入 `#todayTotal`。

2. **D1 仪表盘科目图为全科目通用静态图（Req 1.2.1）**
   - **现象**：封面图硬编码引用静态资源，无法根据不同练习科目展示对应专有配图。
   - **落点**：`dashboard-skin-01-v2.html:253`
   - **建议动作**：在 JS 中维护 `item_id -> image_url` 映射表，切换科目时动态更新 `img.src`。

3. **运行时卡片调序/增删控制台尚未实现（Req 4101.4）**
   - **现象**：虽然卡片已高度组件化且各具契约，但界面中缺乏让用户「拖拽调序、勾选隐藏/展示卡片」的前端交互控制面板。
   - **落点**：`compose-01.html` / `card-dashboard-skeleton-01.html`
   - **建议动作**：在轨道顶栏增加「管理卡片」弹层，接入轻量级拖拽排序与本地 LocalStorage 状态持久化。

4. **D5 今日记录卡「总时长」存在生产写入侧缺口（Req 3.3）**
   - **现象**：D5 中的「总时长（从首个 session 至今自然经过时间）」在前端表现完备，但生产 SQLite 数据库目前仅在保存时写单一时间戳，缺乏首个练习启动时刻的字段支持。
   - **落点**：`today-records-01.html` & 后端数据库模型
   - **建议动作**：在 `daily_practices` 扩展 `first_practice_at` 字段，或聚合 `practice_audit_log` 首条记录计算自然跨度。

---

### P2 — 用户体验与代码细节小瑕疵（3 项）

1. **加减号步进按钮缺少长按加速（Req 260922-3.7）**
   - **现象**：D1 与 D2 的 ± 按钮只能单次点按，快速大范围跨度调速费劲。
   - **落点**：`dashboard-skin-01-v2.html`、`metronome-01-v2.html`
   - **建议动作**：为 `.step-btn` 绑定 `pointerdown` 定时器，长按超过 400ms 后以指数加速步进。

2. **D3 下方三块仍保留 A/B 变体待 dad 拍板固化（Req 4101-D3.1–D3.4）**
   - **现象**：D3 页面依然包含孔阵、按键、谱架的切换开关，代码冗余。
   - **落点**：`dashboard-bottom-blocks-01-v2.html`
   - **建议动作**：待 dad 选型确认后，剥离对照代码，固化为单一沉头孔 + 扁平胶囊 + 胶囊 b 谱架。

3. **个别卡片缺少 URL 级负控便捷测试触发（Req 4101-Gate.3）**
   - **现象**：D4 支持 `?neg=1` 直观红灯，而 D5/D6 需代码级传参或手动修改数据触发。
   - **落点**：`today-records-01.html`
   - **建议动作**：各卡统一支持 `?audit=1&neg=1` 参数，便于自动化回归测试。

---

## C. 口径提醒与跨卡一致性查验

### 1. 旧《需求对照表-261003.md》偏差纠正

在复核 2026-10-03 的历史对照表时，发现以下几处因迭代演进而产生的偏差，特此纠正：

1. **D5 今日练习记录卡（3.1–3.5）**：
   - *旧表记录*：全部列为【未做 5】（注明系漏派 grok 所致）。
   - *本次纠正*：**该结论已过时**。后续任务中 grok 已完整交付 `today-records-01.html`，agy 交付 `d5-design-probe.html`；折叠双态、3 个 heroic 指标、6 列明细表、占比微条及 GSAP 边缘模糊均已实测上线，判定转为【做到】。
2. **D4 老师要求卡（2.0–2.1.2）**：
   - *旧表记录*：将「做成 pop-out 弹窗」判为实现，将 2.1.2 判为部分。
   - *本次纠正*：**口径已变更**。Dad 在 MRD Q5 拍板明确要求：「老师要求就放 D4 独立卡片了……吹奏计时中随时随地可看……3D 卡叠 deck 样式」。W7 已重构为独立卡片 `requests-card-01.html`，拆除了弹窗外壳。因此「必须做成弹窗」的原口径作废，新卡片判定为【做到】。
3. **D1 歌词展示区（1.2.3）**：
   - *旧表记录*：将「歌词处老师要求 16s 线性滚动」判为实现。
   - *本次纠正*：**原需求已废弃**。Dad 在 MRD 2610041201 第 4 条明确要求彻底删除 `lyric-col`，让下方模块顶上来。D1 当前已完全删除该区块，符合 dad 最新指示。

---

### 2. 跨卡契约与一致性验证数据

- **六卡宽度声明**：
  `card-contract.md` 规定默认宽度为：
  `card-practice-timer` (460) / `card-metronome` (420) / `card-transport-blocks` (400) / `card-requests` (440) / `card-today-records` (460) / `card-practice-duration` (380)。
  实测 `compose-01.html:235-257` 挂载各卡槽宽度与契约 **100% 精确对齐**。
- **两套皮肤 WCAG AA 对比度**：
  运行 `python3 scripts/token-contrast.py` 实测，浅银与深墨两套模式下，所有文字与承载面组合 **门禁不合格合计均为 0**（正文对比度均 ≥4.5，标题 ≥3.0）。
- **iPhone 440px 视口无横滑**：
  所有卡片机身均设置 `@media (max-width: 480px) { width: 100%; min-width: 0; }`；`compose-01.html` 与 `card-dashboard-skeleton-01.html` 在 440 档自动收拢为纵向单列卡片（`is-narrow`），实测 `scrollWidth <= clientWidth`，横向无溢出。
