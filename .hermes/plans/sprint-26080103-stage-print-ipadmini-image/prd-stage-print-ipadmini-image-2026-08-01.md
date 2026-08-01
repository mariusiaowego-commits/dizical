# PRD — Stage 练习明细 (stage-print) iPad mini 适配 + 图片导出产出物

**Sprint**: 26080103 (2026-08-01 第 3 个)
**对应 plan**: [[plan-stage-print-ipadmini-image-2026-08-01]]

---

## 用户故事

> 我用 iPad mini 横屏打开 `/report/stage-print` 看女儿的竹笛练习明细 (打印预览), 现在的版本表格在 iPad 上字小得看不清, 短列还出现"…"省略号. 我希望能直接在 iPad 屏上读得清, 同时希望除了打印 PDF 还能"导出图片"——把这份明细图分享给老师看.

## 验收标准

### A. iPad mini 横屏可读 (Acceptance 1)

**Given**: iPad mini 1 代, Safari 14, 横屏 (1133×744 CSS 像素), 父设备是 LAN 访问 8765 端口
**When**: dad 打开 `http://10.0.0.14:8765/report/stage-print?stage_order=N`
**Then**:
- 工具条可点 (不用 hover)
- 分组视图: 表格内文字 ≥ 9.5pt 实际像素 (≈ 9.5 × 1.5 retina = 14.25 物理像素), session 内容列不出现 "…" 截断
- 表格视图: 矩阵主表文字 ≥ 11pt, 短列 (总时长/速度/单次) ≥ 32mm 物理宽
- 屏上可完整滚动, 不被 height 限制

### B. PDF 打印仍合理 (Acceptance 2)

**Given**: 接 A 的同一屏
**When**: dad 点 "打印 / PDF" → 系统打印对话框 → 选 "另存为 PDF"
**Then**:
- 分组视图 1 stage ≤ 7 天: 1 页 A4 竖向, statusMsg 写 "100% · A4 竖向 1 页"
- 表格视图 1 stage ≤ 4 天: 1 页 A4 横向, statusMsg 写 "100% · A4 横向 1 页"
- 表格视图 1 stage ≥ 5 天: 多页 A4 横向, 每页都重出 thead, 不出现单行跨页
- 矩阵里 cell 内容完整显示, 不被 hidden 吃掉

### C. 图片导出产出物 (Acceptance 3)

**Given**: 接 A 的同一屏
**When**: dad 点 "导出图片" 按钮
**Then**:
- 按钮立刻 disable + 显示 "正在生成图片…"
- SSE 状态流依次出 "构建 prompt…" → "正在调用 hermes + FAL…" → "图片已获取…" → "图片已保存…" → "done"
- 60 秒内 (多数情况 30-40s) 收到 done 事件, 弹模态框显示图片本地路径 `/Users/mt16/dev/dizical/data/reports/stage-1-20260801-1430.png` (举例)
- Mac Finder 双击图片能正常打开, 内容含: 周期 (stage_start ~ stage_end)、上课日 (lesson_date)、总时长、科目小计 (如"长音 60 分/10 次 50%"), 不需要跟 HTML 1:1 但要"看得懂这阶段的练习"
- 失败时 statusMsg 红字, 不弹 alert (dad 红线: 不用 alert 弹窗)

### D. 数据落盘 (Acceptance 4)

**Given**: 上一步成功生成
**When**: 后端 SSE done
**Then**:
- `data/reports/stage-{order}-{timestamp}.png` 文件存在, > 10KB
- `report_artifacts` 表新增 1 行: `(kind='stage_image', ref_id=N, image_path=…)`
- `practice_reports` 表 (月报专用) 不受影响

## Non-Goals

- N1: 不动月报图 (`/api/practice-report/generate` + `practice_reports` 表)
- N2: 不改 `/api/practices/stage-detail` 返回结构 (只复用)
- N3: 不动其他视图 (`/report` / `/practice` / `/config/practice-log`)
- N4: 不支持 iPhone 竖屏适配 (PC + iPad 优先)
- N5: 不生成"分享链接" (图片走 Mac Finder 分享)
- N6: 不支持多 stage 合并导出
- N7: iPad mini 之外的具体 iPad 型号不专门适配 (Safari 缩放 CSS 自动覆盖)

## 关键场景脚本 (3 步走)

### 场景 1: dad 在 iPad mini 看 + 打印 (30 秒)

1. 打开 `http://10.0.0.14:8765/report/stage-print?stage_order=1`
2. 横屏: 屏上 100%, 主表 11pt 可读 ✅
3. 点 "打印 / PDF" → 选另存 PDF → 1 页 ✅

### 场景 2: dad 导出图片 (60 秒)

1. 打开 `http://10.0.0.14:8765/report/stage-print?stage_order=1`
2. 点 "导出图片" → 弹 SSE 状态流
3. 50 秒后 done, 弹模态框 "图片已存到 data/reports/stage-1-20260801-1430.png"
4. dad 复制路径 → Mac Finder 打开 → 完美

### 场景 3: 旧数据回归 (5 分钟)

1. pytest 跑 268 passed
2. curl `/api/practices/stages` 200 OK
3. curl `/api/practices/stage-detail?stage_order=1` 200 OK, payload 字段不变
4. 切到非 stage-print 页面 (/report / /practice / /config) 视觉 0 改动

## 度量

- **屏上**: iPad mini 1133×744 视口下, 分组视图主表 font-size ≥ 9.5pt, 表格视图 font-size ≥ 11pt (查 DOM 实际值)
- **打印**: 默认 print-zoom = 1.0 (不动) 情况下, 4 天 stage 表格刚好 1 页 A4 横
- **生图**: 平均耗时 ≤ 45s, 失败率 ≤ 10% (走 Portal 网波动)
- **兼容**: 既有 stage_print 实测路径全部 200, payload 字段 0 改动
