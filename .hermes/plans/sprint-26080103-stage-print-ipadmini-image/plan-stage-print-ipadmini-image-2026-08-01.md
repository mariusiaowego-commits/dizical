# Plan — /report/stage-print 适配 iPad mini 横屏 + 新增图片导出产出物

**Sprint**: 26080103 (2026-08-01 第 3 个)
**类型**: UI 适配 (iPad mini) + 新产出物 (图片导出)
**Appetite**: 半天-1 天

---

## 背景 (dad 强信号)

dad 在 iPad mini 横屏状态 (`1024×768` landscape, 物理 2266×1488) 反馈 `/report/stage-print` 的产出物字太小, 想让 ipadmini 上能直接用浏览器/Safari 看得清。**新需求**——除了 PDF 之外, 增加一种"图片"产出物类型, 用 hermes + Portal (FAL) 生成一张 report 表格图片 (走 `dizical-report` skill 类似的 prompt 路径, 但数据维度换成 stage 维).

约束:
- 表格高度**不限制**, 允许超 A4 多页 (现在很多 stage 阶段表格塞不下, 必须分页)
- iPad mini 横屏屏宽 1133 CSS px, A4 宽 794px, 占 70% 屏宽不算小; 真正问题在**字号 + 列宽**
- 图片产出物是新增的产出物类型 (跟 PDF 并列, 走相同的"print 流程"入口)
- 走 sprint 工作流: 先 plan + 拍板, 再改代码

---

## 目标

1. iPad mini 横屏 (1133×744) 上 `/report/stage-print` (group + table 视图) 屏上预览字清晰可读, 不缩到看不清
2. 表格视图**不再强行压一页**, 内容多时按内容自然撑高 (分页打印/导出时用 `break-inside` 避免撕裂)
3. 新增"导出图片"按钮: 走 hermes + Portal (FAL GPT Image 2) 生成 report 图, prompt 用 stage 维数据, 走 SSE 流式状态, 落盘到 `data/reports/`, 写 `report_artifacts` 表 (新表, 跟月报 `practice_reports` 分离)
4. **iPad mini PDF 打印仍能保持一页** (默认 `打印 / PDF` 按钮走 print-zoom 缩放, 行为不变)

## 拍板 (Q1-Q4)

| # | 问题 | 选项 | dad 拍板 |
|---|------|------|----------|
| Q1 | iPad mini 适配重点 | A 字号 + 列宽 + 关掉 table-layout fixed / B 只改字号 / C 整体重设计 |  |
| Q2 | 表格不限制高度后, PDF 怎么处理 | A 打印自动多页 (用 page-break 控制每块) / B 打印继续缩放一页 / C 屏上看完整, 打印强制 1 页 |  |
| Q3 | 图片产出物触发点 | A 工具条 "导出图片" 按钮 / B 视图切换加第三个 tab "图片" / C 仅分组视图有 |  |
| Q4 | 图片产出物异步反馈 | A SSE 流式状态 (跟月报图一致) / B 简单转圈 + 完成弹窗 / C 后台生成 + 弹通知 |  |

## 改动范围 (本 sprint)

**只动 4 处**:

| 文件 | 改动 |
|------|------|
| `src/kid_app/templates/stage-print.html` | CSS 改 iPad mini 适配 (关 `table-layout: fixed`, 字号 +10-20%, 列宽改 `fr`), 表格视图取消 `height/max-height/overflow:hidden` 限制, 打印策略按 Q2 改, 工具条加 "导出图片" 按钮 + SSE 客户端 |
| `src/kid_app/app.py` | 加新 API: `POST /api/practices/stage-image` (SSE 状态流), 调 `src/report_templates.build_stage_image_prompt` + hermes subprocess 跟月报图一致 |
| `src/report_templates.py` | 加 `build_stage_image_prompt(stage_payload, child_name, style)` 函数, prompt 模板用 stage 维字段 (周期/上课日/科目时长/小计) |
| `schema_mysql.sql` (新增) + 数据库自动迁移 | 新表 `report_artifacts (id, kind, ref_id, prompt, image_path, created_at)`, `kind` 留扩展 (当前 stage_image) |

**不动**:
- 后端 `/api/practices/stage-detail` (已含 stage 全量, 直接复用)
- 后端 `practice_reports` 表 (月报专用, 不污染)
- 其他模块 (`practice.html` / `report.html` / `practice-log` 等)
- 启动服务参数 / 端口

## 与并行分支冲突分析

| 并行分支 | 改什么 | 跟我们冲突? |
|---------|--------|------------|
| `origin/feature/report-session-edit-260801` | `app.py` + `report.html` (加 session 编辑按钮) | **零冲突** — 我们改 `stage-print.html` + `app.py` route 段不同行 |
| `origin/fix/report-trail-detail-260801` | `app.py` + `report.html` + `practice.html` | **零冲突** |
| `origin/feature/practice-log-defaults-260801` | `practice-log` | **零冲突** |

**分支策略**: 在 worktree `/Users/mt16/dev/dizical-stage-print-ipadmini` (已建) 改, 永远不跟 main 路径打架, PR 走 `feat/stage-print-ipadmini-and-image-260801` → main.

## 设计原则 (iPad mini 适配)

- **取消** `.paper.is-landscape { height: 210mm; max-height: 210mm; overflow: hidden }` — 让表格自然撑高
- **取消** `table.matrix { table-layout: fixed; font-size: 8pt }` — 改 `table-layout: auto`, 主表 `font-size: 11pt` (iPad 上 ~11pt 才"看着不累")
- **取消** `<col style="width: 14mm">` 死宽 — 改 `<col style="width: 14%">` 短列 / `<col>` 自适应, 用 CSS `:has()` 或 `min-width: 32mm` 保底
- 表格行高 `min-height: 8mm` (iPad 上 8mm ≈ 30px, 触摸友好)
- 分组视图字号从 `7.2pt` → `9.5pt`, 表格视图主表 `8pt` → `11pt`
- 打印策略: `break-inside: avoid` 在 day-block / item-block / matrix 块上, `page-break-after: auto`, 打印时**关缩放**让浏览器自然分页 (CR `print-zoom` floor 改 0.85, 不到溢出 1 页就不缩)

## 设计原则 (图片导出)

- **入口**: 工具条加 "导出图片" 按钮, 跟 "打印 / PDF" 并列, 行为一致
- **触发**: 按钮 → fetch `POST /api/practices/stage-image?stage_order=…&days=…` (Bubbles: `application/json` body 同理) → 后端 spawn subprocess 调 hermes chat + FAL GPT Image 2 → SSE 回流 status / output / done
- **prompt**: 跟月报同源 (academic / 数学讲义风), 但 layout 段换 stage 维: 周期、起止、上课日、科目小计、按日/科目的会话矩阵, 不要再带 "月份" 字样
- **aspect_ratio**: 选 `landscape` (因为 stage 表格本身是横向, 图片也横版更对齐)
- **落盘**: `data/reports/stage-{order}-{YYYYMMDD-HHmm}.png`, 同时写 `report_artifacts` 表 (`kind='stage_image'`, `ref_id=stage_order`)
- **前端**: SSE status 进 statusMsg, 完成后弹模态框 + 给图片本地路径, 可直接拖到微信/相册
- **失败兜底**: 任何 SSE error → statusMsg 红字, 不阻塞

## 风险

- **R1**: 关 `table-layout: fixed` 后矩阵列宽不稳定 → 用 `min-width: 32mm` 给短列保底, 主明细列不设宽
- **R2**: 打印分页后矩阵的 thead 会跨页重复 → 用 `thead { display: table-header-group }` (默认行为) + `tr { break-inside: avoid }` 避免单行跨页
- **R3**: hermes subprocess 启动慢 + FAL 30-60s → SSE 状态流必跑, 失败有 timeout
- **R4**: iPad mini Safari 触摸事件跟桌面不同 → 工具条按钮用 `<button>`, 不依赖 hover
- **R5**: 新表 `report_artifacts` 在云端 MySQL 没建 → `schema_mysql.sql` 加, 同时 `p4-phase2-assets/sync_local_to_cloud.py` 表列表加, 跑自动迁移; 跟 main 上 PR #210 不冲突 (那条没动 schema)

## 验证 (单源真值 + 三方比对)

- [ ] 屏上预览 iPad mini 横屏 1133×744: 表格主表字号 ≥ 11pt, 短列 ≥ 32mm, 不溢出
- [ ] PDF 打印默认 1 页: print-zoom 计算后 statusMsg 写 "100% · A4 横向 1 页" 或 "N% · N 页"
- [ ] 表格视图多日 (e.g. 7 天) 时屏上能完整滚动, 打印分 2 页正常
- [ ] 工具条 "导出图片" 按钮: 点击 → SSE 状态流 → 60s 内返回图片本地路径
- [ ] 生成的 stage 图可在 Mac Finder 打开, 内容含周期 + 科目小计 + 矩阵骨架 (不要求跟 HTML 1:1)
- [ ] `pytest -q` 净零回归 (基线 268 passed 不退步)
- [ ] `curl /report/stage-print?stage_order=1` 200 OK
- [ ] `curl -X POST /api/practices/stage-image?stage_order=1` 走 SSE 一次完整流

## 非目标 (本期不动)

- 多人多 stage 批量生成
- 老师/家长分享 (生成后只落本地, 分享走 macOS 分享菜单)
- 月报图的改造 (那是月报, 不是 stage)
- 旧 `practice_reports` 表的 `kind` 扩展 (单独新表, 不动月报)
- iPad mini 之外的其它 iPad 型号适配 (Apple 缩放 CSS 自动兼容)
