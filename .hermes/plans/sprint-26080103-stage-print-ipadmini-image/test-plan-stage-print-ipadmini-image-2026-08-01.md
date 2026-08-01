# Test Plan — Stage 练习明细 (stage-print) iPad mini 适配 + 图片导出

**Sprint**: 26080103 (2026-08-01 第 3 个)

---

## T1 单元测试

### T1.1 `build_stage_image_prompt` happy path

- **Setup**: mock payload 含 stage_order=1, stage_start='2026-07-20', stage_end='2026-08-02', summary={total_minutes: 130, practice_days: 5, session_count: 12, item_count: 3}, by_item=[...], days=[{date:'2026-07-25', total_minutes: 30, groups:[{item_name:'长音', minutes:30, sessions:[{content:'吐音练习'}]}]}]
- **Action**: `from src.report_templates import build_stage_image_prompt; prompt, aspect = build_stage_image_prompt(payload, "YoYo")`
- **Expect**: 
  - 返回 tuple (str, str)
  - prompt 含 "Stage 1" "2026-07-20" "130" "5" "长音" "吐音练习"
  - aspect == "landscape"

### T1.2 `build_stage_image_prompt` empty days

- **Setup**: payload.days=[] by_item=[]
- **Action**: 同 T1.1
- **Expect**: prompt 含 "(暂无练习日)" + "(暂无数据)", 不抛错

### T1.3 `build_stage_image_prompt` 占位符全部填满

- **Setup**: payload 完整含所有字段
- **Action**: 同 T1.1
- **Expect**: prompt 中**不**含 `{stage_order}` `{total_minutes}` 等未替换占位符 (`.format()` 不能 KeyError)

## T2 集成测试 (mock subprocess)

### T2.1 `POST /api/practices/stage-image?stage_order=1` 走 SSE 一次完整流

- **Setup**: monkeypatch `subprocess.Popen` 返 mock proc, stdout 输出 "MEDIA:/tmp/test.png", `/tmp/test.png` 真实存在 (创建 1x1 PNG)
- **Action**: `httpx.AsyncClient` 或 `TestClient` POST 该 URL
- **Expect**: 
  - 收到 SSE event sequence: status → status → done
  - done.data.image_path 含 "data/reports/stage-1-"
  - 落盘文件 > 10KB
  - `report_artifacts` 表新增 1 行 kind='stage_image', ref_id='1'

### T2.2 API 错误 path: stage 不存在

- **Setup**: POST `/api/practices/stage-image?stage_order=999` (无该 stage)
- **Action**: 调 API
- **Expect**: SSE error event, message 含 "未找到 stage", 不写文件不写表

### T2.3 API 错误 path: hermes subprocess 失败

- **Setup**: monkeypatch `subprocess.Popen` 返空 stdout, exit=1
- **Action**: POST API
- **Expect**: SSE error event "未找到图片。hermes 输出:", 不抛 500

### T2.4 API 错误 path: 超时 (120s)

- **Setup**: monkeypatch `subprocess.Popen` 返 proc 永不结束
- **Action**: POST API
- **Expect**: SSE error event "生成超时（120秒）"

## T3 回归测试 (现有套件)

### T3.1 pytest 全套

- **Action**: `cd /Users/mt16/dev/dizical-stage-print-ipadmini && pytest -q`
- **Expect**: 268/268 passed (基线 + 新 T1/T2)

### T3.2 `curl /api/practices/stage-detail?stage_order=1`

- **Action**: 启动 dev 服务 (port 8766, 不影响 8765 主服务) → curl
- **Expect**: 200 OK, payload 字段 0 改动 (与 main 一样)

### T3.3 `curl /api/practices/stages`

- **Action**: 同 T3.2
- **Expect**: 200 OK, stage 列表正常返回

## T4 视觉验证 (dad 主导)

### T4.1 iPad mini 横屏可读

- **设备**: iPad mini 1 代 Safari, 横屏 1133×744
- **URL**: `http://10.0.0.14:8766/report/stage-print?stage_order=1`
- **期望**:
  - 工具条 4 个按钮清晰可点 (打印 / 导出图片 / 阶段选择 / 视图切换)
  - 分组视图: 主表文字 ≥ 9.5pt, 不被截断
  - 表格视图: 矩阵主表文字 ≥ 11pt, 短列 ≥ 14mm (测 DOM `getBoundingClientRect()`)
  - 屏上能完整滚动, 不被 height 限制 (matrix tbody 撑到 2-3 屏正常)

### T4.2 PDF 打印 1 页

- **操作**: 点 "打印 / PDF" → 选另存为 PDF
- **期望**:
  - 4 天 stage 表格 1 页 A4 横, statusMsg "100% · A4 横向 1 页"
  - 7 天 stage 表格 2 页 A4 横, thead 在第 2 页重出, 不出现单行跨页

### T4.3 导出图片 (60s)

- **操作**: 点 "导出图片" → 等 SSE done
- **期望**:
  - 状态流依次出: 构建 prompt → 调 hermes → 图片已获取 → 图片已保存 → done
  - done 弹模态框, 含图片本地路径
  - Mac Finder 双击图片能打开, 内容含: 周期/科目小计/按日练习, 学术风

## T5 跨分支冲突验证

- **Action**: `git fetch origin && git diff main origin/feature/report-session-edit-260801 -- src/kid_app/app.py src/kid_app/templates/stage-print.html src/report_templates.py schema_mysql.sql`
- **Expect**: 我们改的文件**没出现在**对方 diff 里 (无冲突)
