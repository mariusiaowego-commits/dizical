# Handoff - 2026-07-11 PR #147 月视图

**Session**: dizical report 页月视图 + emoji 换 SVG icon + 4 处交互修复 (feat/month-chart - PR #147 merged)
**Status**: 全 ship-ready - PR merged, prod 服务 8765 加载新代码
**Owner**: dad
**Last updated**: 2026-07-11

---

## TL;DR

user prompt "继续在本分支维护给report页增加新feature - 我需要一个自然月 月纬度的柱状图展示，展示信息同目前的周展示". 后续 dad 提 4 issue: label 稀疏 / 柱不满卡片宽 / 柱不能点击 / emoji 全部要换 SVG icon

**当前状态**:
- main: `78f34c7` (PR #147 squash merge)
- 生产服务: 8765 PID 78507 跑新代码, 6/6 URL curl 200
- 0 stale 分支, 0 OPEN PR, 0 worktree
- pytest: 16 fail / 291 pass (净回归 = 0, 全 pre-existing)
- DB: 未动

---

## 完成的 files

### 后端 (`src/kid_app/app.py` +88)
- 新增 `/api/practices/monthly?month=YYYY-MM` 端点
- **路由顺序坑**: 必须注册在 `/api/practices/{date_str}` 之前避免 FastAPI 路由抢占
- 返回结构跟 stage chart 同: `{month, month_start, month_end, end_date, dates[], items[], data[date][id]}`
- 当前月截止今天, 历史月画完整

### 前端 (`src/kid_app/templates/report.html` +131)
- 抽 `renderStackedChart(chartData, opts)` 公共函数 (stage + month 共用)
- `renderStageChart` 改成 wrapper 调公共函数, 保留原行为
- 新增 `renderMonthChart(opts={barW, barGap, chartH, labelStride})` - 窄柱+稀疏 label
- 新增 `loadMonthChart(monthStr)` - fetch + 渲染 + legend + gsap 渐入 + bindBarHover
- 模板加 `<div id="monthChartCard">` (cal-grid 之后, stageChartCard 之前)
- 初始加载 + 切月自动刷 (复用 navigateMonth 钩子)
- X 轴 labelStride=3 bug 修复 (此前 'wd === 周一' 二次过滤导致 stride 无效)
- 月图 X 轴下方周几 sub-label 删除 (避免跟相邻日期 label 视觉重叠)
- emoji 4 处替换 SVG icon (chart-bar.svg + location-dot.svg)
- BAR_W 封顶 28px (修当月柱粗被拉宽问题)
- loadMonthChart resolve 后调 bindBarHover (修月图柱不能点击 bug)

### 新增文件
- `src/kid_app/static/icons/chart-bar.svg` (16×16, 3 色 rect, dizicute 配色)
- `src/kid_app/static/icons/location-dot.svg` (16×16, 珊瑚红定位针)

---

## dizicute 一致性

- 0 新 hex (复用 STAGE_COLORS 15 色梯度)
- 0 新 JS 库
- 0 新 CSS 文件
- em-dash source code 扫描: 0 (commit 前 grep)
- 4 处 emoji 全清 (📊×3 + 📍)

---

## 测试覆盖

- pytest 净回归 = 0 (main vs feat 双向 FAILED-set diff 一致, 16/16 fail 同一集合)
- 6 URL curl 200/400 边界 (3 report + monthly + 2 SVG icon)
- 浏览器实测: 7 月 11 天 + 6 月 30 天 + 2025-12 跨年
- 柱 click - diziModal 真渲染 (实测 7/2 数据: 30 分钟, 5 segments)
- X 轴 label 密度: 06/01/04/07/10/13/16/19/22/25/28/30 = 11 label (stride=3 + 月末)

---

## 踩坑 (沉淀给下次)

1. **FastAPI 路由顺序坑**: `/api/practices/{date_str}` 会吞掉字面字符串 `/monthly`. 修法: 月 endpoint 必须注册在 `{date_str}` 之前
2. **浏览器缓存陷阱**: rename endpoint 后 fetch 旧 URL 返 400, 浏览器缓存旧响应. 修法: `fetch(url, { cache: 'no-store' })`
3. **BAR_W 响应式坑**: 当月 11 天柱被拉粗 28px (视觉突兀). 修法: `Math.min(28, ...)` 封顶, 不够宽右留白
4. **周几 sub-label 视觉重叠**: 月图 X 轴下方周几跟相邻日期 label 紧贴. 修法: 月图模式删周几 sub-label
5. **labelStride=3 bug**: 'wd === 周一' 二次过滤导致 stride 无效. 修法: 直接按 stride 标, 周几独立判断
6. **cal-day click 事件委托**: 从 forEach.addEventListener 改成 .cal-grid 事件委托, 切月后 cal-grid 内容替换不影响监听

## 服务现状 (live)

- **PID**: 78507, port 8765, main `78f34c7`
- **URL**: http://localhost:8765 / http://10.0.0.14:8765 / http://100.67.215.121:8765
- **6/6 URL 200**: /report, /report?month=2026-06, /report?month=2025-12, /api/practices/monthly, /static/icons/chart-bar.svg, /static/icons/location-dot.svg

## Notes for future session

1. **PR #147 走通端到端**: 分支 - 实测 - dad 验 (跨多轮迭代) - commit - PR - merge - prod 重启, 全程 1 个 session
2. **pytest 净回归 SOP 成熟**: `git checkout main - pytest FAILED > A` `git checkout feat - pytest FAILED > B` `diff A B`, 空 = 0 净回归
3. **em-dash Discipline 习惯**: 写完 commit 前 grep `\u2014` source code, 0 才 commit
4. **emoji 0 容忍**: dizical UI 全局禁止 emoji, 统一用 inline SVG icon (16×16, dizicute 配色)
5. **路由顺序**: FastAPI 按声明顺序匹配, 字面 endpoint 必须在路径参数 endpoint 之前