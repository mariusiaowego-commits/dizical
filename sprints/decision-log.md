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
