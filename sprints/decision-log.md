# dizical Sprint Decision Log (PDR)

格式: `| Date | Sprint | Decision | Why |` — 供下次 agent session 快速 rehydrate。

| Date | Sprint | Decision | Why |
|------|--------|----------|-----|
| 2026-09-14 | 26091402 | 双 agent 分析合并：agy 写 brief D（独立分析）→ 与 hermes brief C 合并 brief E → agy 实施 | dad 拍板「分析也要让 agy 写一轮」；2.1 用 agy 纯 CSS 方案胜 hermes JS 量高取整行方案（字体回退/fons.ready/横竖屏切换风险） |
| 2026-09-14 | 26091402 | hover 真高光化：glare stops 末端归 transparent @ 65% + laser 回 color-dodge + spec 回 screen + foilOp 0.55→0.42（仅 pearl/mint/sakura 作用域）| pixel 基线：pearl hover gt6% 89.39%→47.93%、max @ 卡面中央跟随指针；azure 逐像素 0 差异 |
| 2026-09-03 | 26090903 | 桌面响应式 = fluid + max-width:420mm + `@media screen` 隔离 | agy 方案保守（!important 防御），grok 方案更彻底（:has() + sticky + JS fallback），dad 选 grok + agy polish |
| 2026-09-03 | 26090903 | fillMatrixToPaper 去 overflow='visible'，改 '' 清掉 inline | 让 CSS @media screen 接管 overflow-x:auto，比 !important 更安全 |
| 2026-09-03 | 26090903 | sticky 边框脱落 → box-shadow 1px 替代 | border-collapse:collapse 与 position:sticky 不兼容，box-shadow 保边框视觉 |
| 2026-09-03 | 26090903 | :has() 低版本 fallback → JS 并列 .is-table class | Safari 15.4 / Chrome 105 才支持 :has()，JS classList.toggle 兜底 |
| 2026-09-03 | 26090903 | 键盘无障碍 ← → 横滑 200px + focus-visible + aria-live | WKWebView / Safari 键盘操作需 Tab 聚焦后方向键横滑，纯键盘可达 |
| 2026-09-03 | 26090903 | group view 手机端 assign-grid 2 列 / iPad 3 列 | 纯 CSS 方案（不改 JS），保持桌面 4 列 + 210mm 居中 |
| 2026-09-03 | 26090903 | agy 换 Claude Opus 4.6 Thinking | 强推理 + 架构设计，适合复杂方案设计；grok 继续前端实现 |
| 2026-09-03 | 26090903 | sprint-workflow 本次未遵守（事后补救） | 判断为 small 用了 mini-plan in chat，但实际触发了多文件改动 + 多 agent 分工，应升级为 full sprint |
| 2026-09-11 | 26091101 | 3D卡牌方案一(纯CSS全息)与方案二(分层3D视差)同等精力双实现 | dad明确两套都要看效果可能都保留；纯CSS架构免除Three.js/Blender运行时负担，零依赖适配iPad mini WKWebView |
| 2026-09-11 | 26091101 | 状态模型解耦为 achieved='Y' 与 claimed_at IS NOT NULL | 解决女儿无获得感痛点，拦截强弹窗配合金色粒子礼花入库动效 |
| 2026-09-11 | 26091101 | 箔层 .ccg-foil-stack isolation；原画 translateZ(4px/5px) 不加 isolation | color-dodge 会吃掉插画；子层 backface-hidden 会在微倾时闪没 |
| 2026-09-11 | 26091101 | 3D 卡面 clip-path 代替 overflow:hidden | overflow+preserve-3d 会压平 translateZ，原画无法稳定浮在箔上 |
| 2026-09-16 | 26091601 | 典藏卡全面重构：1px 细金掐丝边 + 矢量水墨泼墨名牌 + 7系分类底板与专属印章 + 3D刚性整卡翻转 | dad 多轮定稿收敛，彻底解决粗重金框喧宾夺主与名牌多边形生硬切割；纯 CSS 刚性整卡 180° 翻转保证象牙白卡背与四角回纹完整展示 |
| 2026-09-16 | 26091602 | 典藏卡列表态缩放适配+类别印章字映射+成就墙响应式 | 彻底解决列表态泼墨框/印章过大失调；类别单字印章解耦 hardcode；modal 详情态去锁标保立绘；近期成就恢复5张；网格 auto-fill 宽窄屏自适应 |
| 2026-09-16 | 26091603 | CCG 移动端 3D 零卡顿治理 + WebP 双阶管线 | 逐帧诊断 MP4 痛点：列表态剥离 SVG 分形滤镜、Modal 挂起背景卡墙（body.is-frozen 短路 rAF tick 消除 blur 重排）、触屏列表态静止（0 写入）+ onDown 缓存 rect（0 次 Layout Thrashing）+ 响应式 WebP（116MB 锐降 97.4% 至 3.06MB） |
| 2026-09-18 | 26091801 | 计时器落地用「视觉层整段移植 + 只读状态桥 S」, 不重写 | 定稿 demo 的 26 个函数动效细节已被 dad 逐轮验收; 重写会引入不可控漂移。桥接 (getter/setter 指向 duration/elapsed/timerRunning) 让生产状态仍是唯一真值 |
| 2026-09-18 | 26091801 | GSAP 改本地自托管 (/static/vendor/gsap.min.js) + CDN 兜底 | 实测 CDN 间歇 ERR_CONNECTION_CLOSED, 一旦失败整页动效全死 (含本次新增花纹/气泡); +72KB 换掉这个单点 |
| 2026-09-18 | 26091801 | 数字字体用系统等宽栈, 不引自托管 mono 子集 | `~/dev/designrepo` 目录已不在, 「先回 designrepo 加 typography token 再同步 DESIGN.md」的仓库规矩当前无法执行; 系统等宽 0 字节且不挂 CDN |
| 2026-09-18 | 26091801 | 计时中与暂停中都锁尺子/步进键 (守卫用 started, 不是 timerRunning) | 独立审计发现暂停态仍能改时长 → 状态胶囊会丢「已暂停」; 时长选择只在选择态有意义 |
| 2026-09-18 | 26091801 | #timerCard 宽度显式写死 min(520px, 100%) | demo 的宽度来自它自己的 grid 舞台, 搬进生产 flex 行后卡片塌成 216px / 60 格尺子格距 1.8px 挤成一团 (审计一轮 CSS 推导判定阻塞, orchestrator Playwright 实测确认, 审计三轮微夹具独立复现); 移植定稿设计必须把尺寸写成约束 |
| 2026-09-18 | 26091801 | 计时器视觉层对 gsap 全部判空 + 先绑交互再建动效 | 本地与 CDN 双挂时动效可降级, 但「拖尺子改时长」这类交互绝不能因动效初始化异常而失效 |

| 2026-09-19 | 26091901 | ruler 拖拽改用自定义 Pointer Events (down/move/up/cancel + setPointerCapture) 而非保留 `<input type=range>` 原生 | iPad Safari 原生 input 行为是「按非 thumb 区域 = jump-to-position」, dad 9-19 实测要的是「按任何位置 = 相对位移增减」. 自定义 Pointer Events + 起点 clientX + 每帧重算 pxPerMin 是唯一干净实现 |
| 2026-09-19 | 26091901 | 1 tick = 30s (≈14px/min) 1:1 物理映射 | dad 拍板, 儿童手指滑多少红针走多少, 1 分钟 ≈ 2 ticks, 不漂移 |
| 2026-09-19 | 26091901 | dragging 类挂 `#timerCard.is-dragging` 而非 `.tick.cur.dragging` | agy 自审报 P1: paintRulerSelect 跨分钟时重写 tick.className, `.tick.cur.dragging` 类被覆盖丢失. 容器挂类 + CSS 选择器 `.ruler.is-dragging .tick.cur` 自动跟随 `.tick.cur` 切格 |
| 2026-09-19 | 26091901 | iPad Safari 双击 zoom 误操作修复 = CSS `touch-action: manipulation` 在 `#timerCard` + `.step-btn` | agy 出方案, dad 拍板备选 A. W3C 标准方案, 0 运行时开销, 局部隔离 (其他区域保留 zoom a11y). viewport user-scalable=no iOS 10+ 强制忽略, 排除 |
| 2026-09-19 | 26091901 | e2e 仓内化首例 (`scripts/e2e_sprint_26091901/` 4 文件) | 之前 sprint 的 e2e 验证只在 /tmp 临时跑过, wardne audit + dad 接手无现成脚本可独立复跑. 本次 3 playwright 脚本 + README + BASE_URL/USERNAME/PASSWORD 三个 env 参数化, 跨 demo/prod 可复用 |
| 2026-09-19 | 26091901 | 静态契约负控: 全文子串搜索 = 假阴性高发, 改用块内切片 + sprint marker 限定 | warden round-1 报 3 处测试假阴性 (handler 注释残留 + ruler-input 注释残留 + 老 dial knob 子串残留), round-2 强化后 8/8 BITE. 教训: 静态契约的负控必须 100% bite 才能证明契约真锁住功能 |
