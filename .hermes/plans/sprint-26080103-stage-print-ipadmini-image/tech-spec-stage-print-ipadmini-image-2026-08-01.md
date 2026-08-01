# Tech Spec — Stage 练习明细 (stage-print) iPad mini 适配 + 图片导出

**Sprint**: 26080103 (2026-08-01 第 3 个)
**对应 PRD**: [[prd-stage-print-ipadmini-image-2026-08-01]]
**对应 plan**: [[plan-stage-print-ipadmini-image-2026-08-01]]

---

## 1. 整体架构

```
+----------------------+        +---------------------+
| Browser (iPad mini)  |        | Browser (Mac)       |
| /report/stage-print  |        | 同 URL              |
+----------+-----------+        +----------+----------+
           | GET                          |
           v                              v
+---------------------------------------------+
|  FastAPI / uvicorn (8765)                   |
|  + src/kid_app/app.py                       |
|    ├─ GET  /report/stage-print (HTML)       |
|    ├─ GET  /api/practices/stages            |
|    ├─ GET  /api/practices/stage-detail      |
|    └─ POST /api/practices/stage-image [NEW] |
+----------+----------------------------------+
           |                                |
           |                                v
           |                +-------------------------------+
           |                | src/report_templates.py      |
           |                | build_stage_image_prompt     |
           |                +-------------------------------+
           |                                |
           |                                v
           |                +-------------------------------+
           |                | hermes chat subprocess        |
           |                | (Nous Portal + FAL GPT Image 2) |
           |                +-------------------------------+
           |                                |
           v                                v
       (HTML/JS)                   data/reports/stage-1-*.png
                                   report_artifacts table
```

## 2. 改动文件清单 (精确到行)

### 2.1 `src/kid_app/templates/stage-print.html` (1297 → ~1300 行)

#### 2.1.1 CSS 改造 (line 105-130 区域)

**改造前**:
```css
.paper { width: 210mm; min-height: 297mm; max-height: none; ... }
.paper.is-table.is-landscape { width: 297mm; height: 210mm; min-height: 210mm; max-height: 210mm; padding: 4mm 5mm 4mm; box-sizing: border-box; overflow: hidden; }
```

**改造后** (iPad mini 适配 + 表格可撑高):
```css
.paper { width: 210mm; min-height: 297mm; max-height: none; ... }
/* 表格视图: 屏上不限制高度, 打印时可多页 */
.paper.is-table.is-landscape { width: 297mm; min-height: 210mm; max-height: none; padding: 4mm 5mm; box-sizing: border-box; overflow: visible; }
```

#### 2.1.2 矩阵表 CSS 改造 (line 305-395 区域)

**改造前**:
```css
table.matrix { width: 100%; border-collapse: collapse; font-size: 8pt; table-layout: fixed; }
table.matrix td.m-item { width: 14mm; ... padding: 0.5mm 0.4mm; }
table.matrix td.m-total { width: 3.5mm; max-width: 4.5mm; ... }
```

**改造后** (取消 table-layout fixed, 字号放大, 短列 min-width 保底):
```css
table.matrix { width: 100%; border-collapse: collapse; font-size: 11pt; table-layout: auto; }
table.matrix thead th.th-item { background: #2a2015; min-width: 22mm; font-size: 11pt; }
table.matrix thead th.th-day { font-size: 11pt; }
table.matrix thead th.th-sub { background: #5c4a36; font-size: 8.5pt; }
table.matrix td.m-item { background: #f5f0e6; font-weight: 700; font-size: 11pt; text-align: center; min-width: 22mm; border-right: 1pt solid #c9a030; word-break: break-all; padding: 1mm 0.8mm; }
table.matrix td.m-total { font-weight: 700; color: var(--accent); white-space: nowrap; border-left: 1pt solid #c9a030; background: #fff8f0; font-size: 9pt; min-width: 14mm; padding: 0.6mm 0.4mm; }
table.matrix td.m-tempo { color: var(--gold); font-weight: 600; white-space: nowrap; font-size: 9pt; min-width: 16mm; padding: 0.6mm 0.4mm; }
table.matrix td.m-once { font-weight: 600; white-space: nowrap; font-size: 9pt; min-width: 12mm; padding: 0.6mm 0.4mm; }
table.matrix td.m-detail { text-align: left; padding: 0.8mm 1.2mm; font-size: 10pt; overflow-wrap: anywhere; min-width: 30mm; }
table.matrix tbody tr { min-height: 8mm; }
```

#### 2.1.3 分组视图字号 (line 181-227 区域)

**改造前**: `.days { font-size: 7.2pt; }` `table.sess { font-size: 6.8pt; }`
**改造后**: `.days { font-size: 9.5pt; }` `table.sess { font-size: 8.5pt; }` `table.sess th { font-size: 8pt; }` `table.sess td { padding: 0.8mm 1.5mm; line-height: 1.4; }`

#### 2.1.4 打印 @media print 改造 (line 408-458)

**改造前**: `.paper.is-landscape { ... max-height: 210mm; overflow: hidden }` `table.matrix { page-break-inside: avoid }`
**改造后**:
```css
@media print {
  ...
  .paper:not(.is-landscape) {
    width: 210mm !important; min-height: 297mm;
    padding: 5mm 6mm !important;
    /* 允许内容多时自然分页, 不用 overflow: hidden */
    overflow: visible !important;
  }
  .paper.is-landscape {
    width: 297mm !important; min-height: 210mm;
    padding: 3.5mm 4.5mm !important;
    overflow: visible !important;
  }
  /* thead 在多页重复, 行不跨页 */
  table.matrix thead { display: table-header-group !important; }
  table.matrix tbody tr { break-inside: avoid !important; page-break-inside: avoid !important; }
  table.matrix tfoot { display: table-row-group !important; break-before: avoid !important; }
  /* 屏上 paper zoom 在打印时仍生效, 但 floor 改 0.85, 让短 stage 保持 100% */
  .paper { zoom: var(--print-zoom, 1) !important; }
}
```

#### 2.1.5 工具条加 "导出图片" 按钮 (line 463-474)

**改造前**:
```html
<button type="button" class="btn btn-print" id="btnPrint">打印 / PDF</button>
```

**改造后**:
```html
<button type="button" class="btn btn-image" id="btnImage">导出图片</button>
<button type="button" class="btn btn-print" id="btnPrint">打印 / PDF</button>
```

加对应 CSS: `.btn-image { background: #4ecdc4; color: #fff; font-weight: 600; }`

#### 2.1.6 fillMatrixToPaper 改造 (line 1063-1110)

**改造前**: 强制 table.style.height = avail + 'px', rows 设固定 height
**改造后**: 不再强制高度, 只在打印前用 print-zoom 缩放; fillMatrixToPaper 改为 fillMatrixForPrint 只在 print 触发

```js
function fillMatrixForPrint() {
  if (viewMode !== 'table') return;
  // 只设置行 min-height 不设固定高, 让打印自然分页
  var rows = paper.querySelectorAll('table.matrix tbody tr');
  rows.forEach(function (r) { r.style.height = ''; r.style.minHeight = '8mm'; });
}
```

#### 2.1.7 打印按钮 handler 改造 (line 1258-1268)

**改造前**: `if (viewMode === 'table') fillMatrixToPaper(); var scale = preparePrintZoom();`
**改造后**: `fillMatrixForPrint(); var scale = preparePrintZoom(); // floor 改 0.85`

#### 2.1.8 导出图片 SSE 客户端 (新增, line ~1298)

```js
document.getElementById('btnImage').addEventListener('click', function () {
  if (!lastPayload) { statusMsg.textContent = '请先加载 stage'; statusMsg.style.color = '#b23a48'; return; }
  var btn = this;
  var order = stageSelect.value || (lastPayload && lastPayload.stage_order);
  var daysParam = appliedDays ? '?stage_order=' + encodeURIComponent(order) + '&days=' + encodeURIComponent(Object.keys(appliedDays).filter(function(k){return appliedDays[k];}).sort().join(',')) : '?stage_order=' + encodeURIComponent(order);
  btn.disabled = true;
  statusMsg.style.color = '';
  statusMsg.textContent = '正在生成图片…';
  fetch('/api/practices/stage-image' + daysParam, { method: 'POST' })
    .then(function(r) {
      if (!r.ok) { throw new Error('HTTP ' + r.status); }
      var reader = r.body.getReader();
      var dec = new TextDecoder();
      var buf = '';
      function pump() {
        return reader.read().then(function(res) {
          if (res.done) return;
          buf += dec.decode(res.value, { stream: true });
          var lines = buf.split('\n\n');
          buf = lines.pop() || '';
          lines.forEach(function(chunk) {
            var m = chunk.match(/^data: (.+)$/m);
            if (!m) return;
            try {
              var evt = JSON.parse(m[1]);
              if (evt.type === 'status') statusMsg.textContent = evt.message;
              else if (evt.type === 'output') {/* ignored */}
              else if (evt.type === 'error') { statusMsg.textContent = '图片生成失败: ' + evt.message; statusMsg.style.color = '#b23a48'; btn.disabled = false; return; }
              else if (evt.type === 'done') {
                statusMsg.textContent = '图片已存到 ' + evt.data.image_path;
                statusMsg.style.color = '';
                btn.disabled = false;
                showImageModal(evt.data);
              }
            } catch (e) {}
          });
          return pump();
        });
      }
      return pump();
    })
    .catch(function(e) { statusMsg.textContent = '图片生成失败: ' + e.message; statusMsg.style.color = '#b23a48'; btn.disabled = false; });
});

function showImageModal(data) {
  var modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;display:flex;align-items:center;justify-content:center;';
  modal.innerHTML = '<div style="background:#fffef9;padding:24px;border-radius:12px;max-width:560px;">' +
    '<h3 style="margin:0 0 12px;color:var(--ink);">图片已生成</h3>' +
    '<p style="font-size:13px;color:var(--muted);margin:0 0 8px;">路径:</p>' +
    '<pre style="background:#f5f0e6;padding:8px;border-radius:6px;font-size:12px;overflow-x:auto;">' + esc(data.image_path) + '</pre>' +
    '<p style="font-size:13px;color:var(--muted);">Artifact ID: ' + esc(data.report_id) + '</p>' +
    '<button type="button" class="btn-apply" id="modalClose" style="margin-top:12px;">好</button>' +
    '</div>';
  document.body.appendChild(modal);
  document.getElementById('modalClose').addEventListener('click', function () { modal.remove(); });
}
```

### 2.2 `src/kid_app/app.py` 新增 API (在 `report_stage_print_page` 后面)

```python
@app.post("/api/practices/stage-image")
async def api_practices_stage_image(
    request: Request,
    stage_order: Optional[int] = None,
    date: Optional[str] = None,
    days: Optional[str] = None,
):
    """生成 stage 维 report 图片 (SSE 流式状态).

    复用 /api/practices/stage-detail 的 payload 拼 prompt, 走 hermes + FAL GPT Image 2.
    days: 可选, "2026-07-01,2026-07-02,..." 过滤; 不传=全 stage 日子.
    落盘: data/reports/stage-{order}-{timestamp}.png
    写表: report_artifacts (kind='stage_image', ref_id=stage_order, image_path, prompt)
    """
    from src.report_templates import build_stage_image_prompt
    from src.database import db  # SQLite
    # 复用现有 api_practices_stage_detail 内部逻辑拿 payload
    payload = _build_stage_detail_payload_for_image(stage_order=stage_order, date=date, days=days)
    if payload.get("error"):
        return JSONResponse({"ok": False, "error": payload["error"]}, status_code=400)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    async def generate_stream():
        import asyncio
        import threading
        import queue as _q

        result_queue = _q.Queue()

        def run_generation():
            try:
                result_queue.put(("status", "构建 prompt..."))
                prompt, aspect_ratio = build_stage_image_prompt(payload, child_name())
                result_queue.put(("status", f"Prompt 已构建（{len(prompt)} 字符）"))

                import subprocess, tempfile
                result_queue.put(("status", "正在调用 hermes + FAL gpt-image-2 生成图片，约需 30-60 秒..."))
                query = f"用 image_generate 工具生成图片，prompt 如下，aspect_ratio 用 {aspect_ratio}：\n\n{prompt}"
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(query)
                    tmp_path = f.name
                shell_cmd = f'hermes chat -q "$(cat {tmp_path})" -t image_gen --yolo -Q'
                proc = subprocess.Popen(shell_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=project_root, bufsize=1, text=True)
                output_lines = []
                for line in proc.stdout:
                    line = line.rstrip()
                    output_lines.append(line)
                    result_queue.put(("output", line))
                proc.wait(timeout=120)
                output = "\n".join(output_lines)
                result_queue.put(("status", f"hermes 进程结束 (exit={proc.returncode})"))
                import os as _os
                try: _os.unlink(tmp_path)
                except Exception: pass

                image_source = None
                for line in output.split("\n"):
                    line = line.strip()
                    if "MEDIA:" in line:
                        cand = line.split("MEDIA:")[1].strip().split()[0]
                        if _os.path.exists(cand):
                            image_source = cand; break
                    if line.startswith("http") and (".png" in line or ".jpg" in line or "fal" in line):
                        image_source = line; break
                    if line.startswith("/") and (line.endswith(".png") or line.endswith(".jpg")):
                        if _os.path.exists(line):
                            image_source = line; break
                if not image_source:
                    result_queue.put(("error", f"未找到图片。hermes 输出:\n{output[:300]}"))
                    return

                result_queue.put(("status", "图片已获取，正在保存..."))
                report_dir = _os.path.join(project_root, "data", "reports")
                _os.makedirs(report_dir, exist_ok=True)
                from datetime import datetime as _dt
                ts = _dt.now().strftime("%Y%m%d-%H%M")
                order = payload.get("stage_order")
                filename = f"stage-{order}-{ts}.png"
                dest_path = _os.path.join(report_dir, filename)
                import urllib.request
                if image_source.startswith("http"):
                    urllib.request.urlretrieve(image_source, dest_path)
                else:
                    import shutil
                    shutil.copy2(image_source, dest_path)

                result_queue.put(("status", "图片已保存，正在记录到数据库..."))
                # 写新表 report_artifacts
                with db._get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS report_artifacts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            kind TEXT NOT NULL,
                            ref_id TEXT,
                            prompt TEXT,
                            image_path TEXT NOT NULL,
                            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    cur.execute(
                        "INSERT INTO report_artifacts (kind, ref_id, prompt, image_path) VALUES (?, ?, ?, ?)",
                        ("stage_image", str(order), prompt, dest_path)
                    )
                    artifact_id = cur.lastrowid
                    conn.commit()

                result_queue.put(("done", {
                    "ok": True,
                    "report_id": artifact_id,
                    "image_path": dest_path,
                    "image_url": f"/api/practices/stage-image/file/{artifact_id}",
                    "stage_order": order,
                }))
            except Exception as e:
                result_queue.put(("error", str(e)))

        thread = threading.Thread(target=run_generation)
        thread.start()

        while True:
            try:
                msg_type, msg_data = result_queue.get(timeout=120)
                import json
                if msg_type == "status":
                    yield f"data: {json.dumps({'type': 'status', 'message': msg_data})}\n\n"
                elif msg_type == "output":
                    yield f"data: {json.dumps({'type': 'output', 'message': msg_data})}\n\n"
                elif msg_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': msg_data})}\n\n"
                    break
                elif msg_type == "done":
                    yield f"data: {json.dumps({'type': 'done', 'data': msg_data})}\n\n"
                    break
            except _q.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': '生成超时（120秒）})}\n\n"
                break

        thread.join(timeout=5)

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/api/practices/stage-image/file/{artifact_id}")
def api_stage_image_file(artifact_id: int):
    """返回 stage 维 report 图片文件."""
    from src.database import db
    import os as _os
    from fastapi.responses import FileResponse
    with db._get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT image_path FROM report_artifacts WHERE id=?", (artifact_id,))
        row = cur.fetchone()
    if not row or not _os.path.exists(row["image_path"]):
        return JSONResponse({"ok": False, "error": "image not found"}, status_code=404)
    return FileResponse(row["image_path"], media_type="image/png")


def _build_stage_detail_payload_for_image(
    stage_order: Optional[int] = None,
    date: Optional[str] = None,
    days: Optional[str] = None,
) -> dict:
    """复用 stage-detail payload, 加 days 过滤. 返回 dict (与 SSE 内一致)."""
    # 走 api_practices_stage_detail 内部逻辑
    from src.kid_app.app import _resolve_stage_for_image
    stage = _resolve_stage_for_image(stage_order=stage_order, date=date)
    if not stage:
        return {"error": "未找到 stage"}
    payload = _build_stage_detail_payload(stage)
    if days:
        # days = "2026-07-01,2026-07-02"
        keep = set(d.strip() for d in days.split(",") if d.strip())
        payload["days"] = [d for d in payload.get("days", []) if d.get("date") in keep]
        # 重算 summary
        total = sum(d.get("total_minutes", 0) for d in payload["days"])
        sess_n = sum(d.get("session_count", 0) for d in payload["days"])
        item_map = {}
        for d in payload["days"]:
            for g in d.get("groups", []):
                gid = g.get("item_id")
                if gid is None: continue
                if gid not in item_map:
                    item_map[gid] = {"item_id": gid, "item_name": g.get("item_name", ""), "minutes": 0, "session_count": 0}
                item_map[gid]["minutes"] += g.get("minutes", 0)
                item_map[gid]["session_count"] += len(g.get("sessions", []))
        payload["summary"] = {
            "total_minutes": total,
            "practice_days": len(payload["days"]),
            "session_count": sess_n,
            "item_count": len(item_map),
        }
        payload["by_item"] = sorted(item_map.values(), key=lambda x: -x["minutes"])
    return payload
```

`_resolve_stage_for_image` 是新加的小工具，从 `_build_stage_detail_payload` 反查 stage 用, 跟现有 `api_practices_stage_detail` 内部查 stage 逻辑一致 (具体实现照搬, 不引入新 SQL).

### 2.3 `src/report_templates.py` 加 `build_stage_image_prompt` (在 line 178 `build_monthly_report_prompt` 后面)

```python
TEMPLATES["stage_academic"] = {
    "name": "Stage 表格 · 学术风",
    "description": "Stage 维 session 明细的 AI 配图, 数学讲义风, 跟月报同款色板",
    "style": """创作一张关于「竹笛练习明细 (Stage 维)」的可视化信息图, 目的是让老师在 1 张图里快速看清本阶段女儿的练习情况.

画面要像高质量数学讲义 + 手绘教育海报, 优雅、清晰、信息丰富, 但不要杂乱. 横版 (landscape) 构图.

视觉风格:
- 横版, 干净的浅色纸张背景 (off-white parchment)
- 深蓝标题, 黑色/深灰正文线条
- 少量优雅的蓝色、青绿色、金色、红色强调色
- 圆角卡片、细线边框、编号标签、手绘箭头、局部放大框和总结栏
- 整体要美观、平衡、有学术感""",
    "layout": """请将以上数据转化为信息图布局 (横版, 1 张), 包含:
1. 标题区: "竹笛练习明细 · Stage {stage_order}" (深蓝大字)
2. 周期副标题: "周期 {stage_start} ~ {stage_end} · 上课日 {lesson_date}"
3. 核心指标卡: 总时长 {total_minutes} 分钟, 练习天数 {practice_days} 天, 共 {session_count} 次
4. 科目小计 (横向柱状图风格): {item_bar_chart} — 每科一行: 名称 + 时长 + 占比%
5. 按日练习表 (简化矩阵): 日期 | 总时长 | 主要科目 | 主要内容片段
6. 总结栏: 一句话评语 ("本期总时长 xx 分钟, 主要练习了 X / Y, 节奏稳定")""",
    "data_fields": """数据说明:
- stage_order: stage 编号
- stage_start / stage_end: 周期起止
- lesson_date: 上课日 (本节课日期)
- total_minutes: 本阶段总练习时长 (分钟)
- practice_days: 实际练习天数
- session_count: 总 session 数
- item_totals: 各项练习时长 {"项目名": 分钟, ...}
- days: [{date, total_minutes, item_summaries:[{name, content_preview}]}]""",
    "aspect_ratio": "landscape",
}


def build_stage_image_prompt(payload: dict, child_name: str = "YoYo") -> tuple[str, str]:
    """构造 stage 维 report 图片的 prompt.

    payload 来自 _build_stage_detail_payload, 含:
      stage_order / stage_start / stage_end / lesson_date / summary / by_item / days[]
    Returns: (prompt_text, aspect_ratio)
    """
    sum_ = payload.get("summary", {})
    template = TEMPLATES["stage_academic"]
    style = template["style"]
    aspect = template["aspect_ratio"]
    layout = template["layout"]
    data_fields = template["data_fields"]

    by_item = payload.get("by_item", [])
    total_m = sum_.get("total_minutes", 0)
    # 科目柱状图 (文字版给 LLM 拼)
    bar_lines = []
    for it in by_item[:5]:
        pct = round(it["minutes"] / total_m * 100) if total_m else 0
        bar = "█" * max(1, int(pct / 5))
        bar_lines.append(f"- {it['item_name']}: {it['minutes']} 分钟 ({pct}%) {bar}")
    item_bar_chart = "\n".join(bar_lines) if bar_lines else "(暂无数据)"

    # 按日摘要
    day_lines = []
    for d in payload.get("days", []):
        item_summaries = []
        for g in d.get("groups", []):
            contents = [s.get("content", "")[:30] for s in g.get("sessions", [])]
            contents = [c for c in contents if c]
            preview = " / ".join(contents[:2]) if contents else "(无内容)"
            item_summaries.append(f"{g.get('item_name', '?')}: {preview}")
        day_lines.append(
            f"- {d['date']} ({d['total_minutes']} 分钟): {' · '.join(item_summaries) or '(无)'}"
        )
    days_text = "\n".join(day_lines) if day_lines else "(暂无练习日)"

    # 填 placeholder
    layout_filled = layout.format(
        stage_order=payload.get("stage_order", "?"),
        stage_start=payload.get("stage_start", "?"),
        stage_end=payload.get("stage_end") or payload.get("effective_end", "?"),
        lesson_date=payload.get("lesson_date", "?"),
        total_minutes=total_m,
        practice_days=sum_.get("practice_days", 0),
        session_count=sum_.get("session_count", 0),
        item_bar_chart=item_bar_chart,
    )
    days_block = "按日练习明细:\n" + days_text

    prompt = f"""{style}

{layout_filled}

{days_block}

{data_fields}

学员名字: {child_name}
数据真实, 不要编造. 用英文/中文混排都行, 但数字和日期要跟数据一致.
"""
    return prompt, aspect
```

### 2.4 `schema_mysql.sql` 加 `report_artifacts` 表 (line 124 后面)

```sql
DROP TABLE IF EXISTS `report_artifacts`;
CREATE TABLE report_artifacts (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  kind TEXT NOT NULL,            -- 'stage_image' | 'badge_image' | 留扩展
  ref_id TEXT,                   -- stage_order / badge_id
  prompt TEXT,
  image_path TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_kind (kind),
  INDEX idx_ref (ref_id)
);
```

### 2.5 `p4-phase2-assets/sync_local_to_cloud.py` 表列表加 (line 196 区域)

`'report_artifacts'` 加进 `other_tables` 列表, 跟 `practice_reports` 一起参与云端同步.

## 3. 验证脚本 (走 TDD)

- `tests/test_stage_image_prompt.py`: 测 `build_stage_image_prompt` 接受 dict payload 返回 (str, str) tuple, 含 stage_order / total_minutes 占位符
- `tests/test_api_stage_image.py`: 测 `POST /api/practices/stage-image` happy + error path (用 monkeypatch 替 subprocess)
- `tests/test_report_artifacts_table.py`: 测 CREATE TABLE IF NOT EXISTS + INSERT 行为
- 端到端: `pytest -q` 净 0 回归 (基线 268 passed)

## 4. 回滚

```bash
git checkout main -- src/kid_app/templates/stage-print.html src/kid_app/app.py src/report_templates.py schema_mysql.sql
# 不需要数据迁移, report_artifacts 表不影响其它逻辑
```
