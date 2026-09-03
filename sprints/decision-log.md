# dizical Sprint Decision Log (PDR)

格式: `| Date | Sprint | Decision | Why |` — 供下次 agent session 快速 rehydrate。

| Date | Sprint | Decision | Why |
|------|--------|----------|-----|
| 2026-09-03 | 26090903 | 桌面响应式 = fluid + max-width:420mm + `@media screen` 隔离 | agy 方案保守（!important 防御），grok 方案更彻底（:has() + sticky + JS fallback），dad 选 grok + agy polish |
| 2026-09-03 | 26090903 | fillMatrixToPaper 去 overflow='visible'，改 '' 清掉 inline | 让 CSS @media screen 接管 overflow-x:auto，比 !important 更安全 |
| 2026-09-03 | 26090903 | sticky 边框脱落 → box-shadow 1px 替代 | border-collapse:collapse 与 position:sticky 不兼容，box-shadow 保边框视觉 |
| 2026-09-03 | 26090903 | :has() 低版本 fallback → JS 并列 .is-table class | Safari 15.4 / Chrome 105 才支持 :has()，JS classList.toggle 兜底 |
| 2026-09-03 | 26090903 | 键盘无障碍 ← → 横滑 200px + focus-visible + aria-live | WKWebView / Safari 键盘操作需 Tab 聚焦后方向键横滑，纯键盘可达 |
| 2026-09-03 | 26090903 | group view 手机端 assign-grid 2 列 / iPad 3 列 | 纯 CSS 方案（不改 JS），保持桌面 4 列 + 210mm 居中 |
| 2026-09-03 | 26090903 | agy 换 Claude Opus 4.6 Thinking | 强推理 + 架构设计，适合复杂方案设计；grok 继续前端实现 |
| 2026-09-03 | 26090903 | sprint-workflow 本次未遵守（事后补救） | 判断为 small 用了 mini-plan in chat，但实际触发了多文件改动 + 多 agent 分工，应升级为 full sprint |
