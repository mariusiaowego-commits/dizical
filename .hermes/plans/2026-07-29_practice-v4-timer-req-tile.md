# Plan: Practice V4 计时器+老师要求 Tile 修复 (4 个问题)

> **For Hermes / dad:** 修 practice 页 4 个 UI/逻辑问题, 1 个分支一次性闭环.
> **执行者:** 后续 subagent (plan 评审通过后派发).
> **范围:** 仅 `src/kid_app/templates/practice.html` + `src/kid_app/app.py` (1 个端点加字段).
> **不动:** 数据库结构, schema, 后端 CRUD, dizical-minip.

---

## 0. 已核实事实 (不靠印象, 全部 grep 验证)

| 编号 | 事实 | 证据 |
|------|------|------|
| F1 | `dci-assign` div (line 943) 只有 `<span class="dci-assign-label">老师要求</span><span class="dci-assign-text" id="dciAssignText">—</span>`, **前端 JS 完全没有写 `dciAssignText.textContent` 的代码** (全文件 0 处 `getElementById('dciAssignText')` 或类似) | `search_files` on `dciAssignText` → 仅 line 943 出现 |
| F2 | `data-req` HTML attribute 已由 server 端 (app.py:1688) 渲染到 item-btn 上, 值为 `metronome + '  ' + requirements` | `app.py:1681` `combined = (metro_text + '  ' if metro_text else '') + req_text` |
| F3 | `weekly_assignments.items` JSON 每条: `{item, item_id, metronome, requirements}`, 数据库 29 条, 字段 `requirements` 必填 (V3 schema 已有) | `sqlite3 data/dizi.db ".schema weekly_assignments"` + `SELECT * LIMIT 1` |
| F4 | `/api/assignments/latest?item_id=N` 已存在 (app.py:1080), 但只返 `tempo_note / tempo_bpm / lesson_date`, **不返 `requirements` 字段** | `app.py:1099-1106` JSONResponse 内容 |
| F5 | `dash-card-inline` 三列 grid `1fr 1fr 2fr` (line 802), `dci-name` 18px (line 804) 比 `dci-assign-label` 11px (line 811) 大. **父子标签字体倒挂** | 直接 Read file line 802/804/811 |
| F6 | `sp-tempo-row` `flex-wrap: nowrap` + 内部 6 元素 (label 36px + 3-note group ~120px + `=` 16px + bpm-stepper 36+48+36=120px + sp-tempo-hint margin-left:auto). iPad 1024 减去左右栏 ~700 后, session-panel 实际宽度 ~600px, **6 元素总和 > 600px** 导致 bpm-stepper 数字挤掉 | Read file 404-453 行 |
| F7 | `wheel-desc` (line 256) 出现在 `activity-wheel` (line 234) 每个 item 内 (`descs[v]`). 计时器左边是 `timerWheel`, 选分钟用. **dad 说的"占地方"指的是 wheel 左侧的 desc 文字** | Read file 256-273 + 2567 (wheel item render) |
| F8 | `extraSection` (line 994) 是补录 tab 的 wheel, 同样有 `wheel-desc` | `search_files wheel-desc` → 256, 269, 2567 |
| F9 | `.timer-block` 是 `display: flex; flex-direction: row; gap: 10px; align-items: stretch` (line 137). picker-card flex:0 0 auto (180+200=380px). session-panel flex:1. iPad 1024 减去容器 padding ~80 后, 计时器卡片实际 ~940px, 减去 picker 380 = session-panel 550px **仍然放不下 6 元素** | Read line 137-139 + 计算 |
| F10 | `updateDashboard()` (line 2262) 已写 `dciName/dciId/dciTempo/dciContent`, 缺 `dciAssignText`. 修改它一处即可填上 | Read 2262-2274 |
| F11 | `selectItem()` (line 1582) 调用链: selectItem → updateReqPanel(btn) + updateSelectedSummary + updateDashboard. `data-req` 来自 `btn.getAttribute('data-req')`. **同一份数据, dashboard 没接** | Read 1600-1616 |

---

## 1. 目标 / 非目标

### Goals
- **G1** 修复 4 个 UI 缺陷, 不引入新依赖, 不动后端 CRUD
- **G2** 老师要求**所有内容**展示在 dashboard 第三列 (metro + requirements 完整, 不截断)
- **G3** iPad mini 1024×768 横屏 (iPad mini 是女儿最常用设备) 友好, 极限情况 (科目名长 / req 内容长) 不破布局
- **G4** 视觉降密度: 计时器内 wheel 去掉 desc 文字, 整体右移

### Non-Goals
- 不动 `/api/assignments/latest` 的响应结构, 改用 button `data-req` 注入 (server 端已有, 不增加 round-trip)
- 不动 wheel 的弧形几何 (ARC_RADIUS, ARC_STEP_DEG)
- 不重做 picker-card 内部布局
- 不动 `summary-layout` / `item-section` 收拢逻辑
- 不增加新字段到 weekly_assignments 表

---

## 2. 4 个问题修复方案

### 修复 1: dci-assign 老师要求展示 (`practice.html:943`, `updateDashboard` line 2262)

**根因**: `dciAssignText` 元素存在但 JS 从未写它. 同一份 data 已在 `btn.getAttribute('data-req')` 上, 但 selectItem→updateDashboard 没把它传过去.

**修法** (2 处):
- `updateDashboard()` 接受可选参数 `reqText` (从 `selectItem` 传入)
- `updateDashboard` 内:
  ```js
  const reqEl = document.getElementById('dciAssignText');
  if (reqEl) reqEl.textContent = reqText || '—';
  ```
- `selectItem()` line 1616 `updateDashboard()` 改为 `updateDashboard(reqText)` (reqText 已在 1600 拿到)
- 限制: `data-req` 长度 ≤ 200 字 (app.py 没限制, 这里仅 textContent 安全; 不阻塞)

**视觉** (3.1 字体大小不协调同时修):
- `.dci-assign-label` 11px → **13px** (与 `dci-name` 18px 协调的副标题档位, 比 dci-tempo 14px 略小)
- `.dci-assign-text` 12px → **13px** (跟 dci-content 13px 对齐)
- `.dci-name` 18px 保持 (主科目标题, 是主)
- **新层级**: dci-name 18px (主) > dci-assign-label 13px (副) = dci-tempo 14px ≈ dci-content 13px (同级内容)

### 修复 2: sp-tempo-row 拥挤 / iPad 适应性 (2.1, 2.2)

**根因** (F6, F9): `sp-tempo-row` 一行 6 元素 + nowrap, iPad 1024 时放不下. 加上 dad 要求"做好 iPad 适应性展示" + "考虑极限情况".

**修法** (HTML 改结构 + CSS 改布局):
- HTML 结构调整: 当前 `<div class="sp-tempo-row">` 单行 → **两行布局**:
  - Row 1: `[速度] [note-group] [=] [bpm-stepper]` (核心控制, 1 行)
  - Row 2: `[sp-tempo-hint] [bpm-presets]` (辅助信息, 另 1 行, 整宽)
- CSS 调整:
  - 新增 `.sp-tempo-row-1` 和 `.sp-tempo-row-2` 两个 flex 容器
  - `.sp-tempo-hint` 去掉 `margin-left: auto` (在 row-2 内自然排)
  - `.bpm-presets` 保持 `display: flex; gap: 4px; flex-wrap: wrap`
  - **关键**: 加 `@media (max-width: 700px)` 媒体查询: bpm-stepper 内部 `width: 36px → 32px`, `bpm-value min-width: 48px → 40px`, bpm-step `font-size 18px → 16px`. iPad 1024-容器padding-sessionpanel 实际 ~600px, 700px 临界值覆盖.
- 极限情况: 
  - 科目名超长 → session-panel 整体 `min-width: 0` (已 line 139), 文字 `text-overflow: ellipsis; white-space: nowrap` (dciName 已 textContent 安全; bpm-value 数字等宽不超)
  - BPM 数字溢出 → bpm-stepper 加 `min-width: 0` + bpm-value 数字用 `font-variant-numeric: tabular-nums`

**结构示例** (timer + extra 两处都改):
```html
<div class="sp-tempo-row-1">
  <div class="sp-tempo-label">速度</div>
  <div class="sp-tempo-note-group">♪ ♩</div>
  <span class="sp-tempo-eq">=</span>
  <div class="bpm-stepper">[- 80 +]</div>
</div>
<div class="sp-tempo-row-2">
  <div class="sp-tempo-hint">♪ = 80 (默认)</div>
  <div class="bpm-presets">[60][80][100][120]</div>
</div>
```

### 修复 3: dash-card-inline 多处问题 (3.1, 3.2)

**3.1 字体**: 见修复 1 末尾.

**3.2 内容空**: 见修复 1 主体 (接 `data-req`).

**额外加固** (2.2 提到"考虑所有科目选中后的极限情况"):
- `.dash-card-inline.visible` 内部三列: 第 1 列 `dci-name` (科目名), 第 2 列 `dci-tempo + dci-content`, 第 3 列 `dci-assign (metro + requirements)`.
- 极限: requirements 文本可能 50-300 字. **当前 grid 1fr 1fr 2fr** 第 3 列占 50% 宽度 ≈ 280px, 单行 ~30 字, 200 字要 7 行.
- 修法: 
  - `.dci-assign-text` 加 `white-space: pre-wrap; word-break: break-word; max-height: 80px; overflow-y: auto;` (滚条 + 保留换行)
  - 整个 dashboard 加 `align-items: start` (已 line 802, 保持)
  - requirements 里 `\n` (DB 中是字面换行) 在 HTML 显示需 `white-space: pre-wrap`

### 修复 4: wheel-desc 删除 + 整体右移 (dad 4)

**根因** (F7, F8): wheel-item 内的 desc 文字 (`descs[v]`) 计时器里多余, 选分钟不需要说明.

**修法**:
- `createActivityWheel` line 2567 渲染逻辑: 去掉 `<span class="wheel-desc">...</span>` 整段
- 删掉 CSS `.wheel-desc` (line 256-273) + `.wheel-item.selected .wheel-desc` (line 269-273)
- `.wheel-item` 现在只有 `wheel-right` (pill + icon + indicator) → wheel 横向宽度从 ~180px (descs + pill + icon) 缩到 ~80px
- 计时器 picker-card 整体宽度缩 → 计时器右移 (timer-block flex layout 自然调整)
- **同时** `activity-wheel` 容器 width 从 180px → 100px (line 236) 适配新宽度

---

## 3. 实施顺序 (每段 1-3 分钟, 真机/HTTP 验证)

### Phase 0 — 文档双写 (本 plan 已写, 现在补 PRD/handoff)
1. 主仓: `.hermes/plans/2026-07-29_practice-v4-timer-req-tile.md` (本文件)
2. Obsidian 镜像: `tqob/05-Coding/project-dizical/PRDs/AI-PRD-练习修复-v4-tile-260729.md`
3. `md5 -q` 校验一致 (本计划包含 plan body, 后续 handoff 单独双写)

### Phase 1 — wheel-desc 删除 (修复 4)
1. `practice.html:2567` 删 `<span class="wheel-desc">...</span>`
2. `practice.html:256-273` 删 `.wheel-desc` + `.wheel-item.selected .wheel-desc` CSS
3. `practice.html:236` `.activity-wheel` width 180px → 100px
4. **真机验证**: 打开 `http://localhost:8765/practice`, 看计时器 wheel, 确认 pill + icon 居中, 计时器右移 (与补录 tab 都验)
5. **不**重启服务 — practice.html 是 Jinja2 模板, FastAPI dev 会 reload; 但生产 8765 是 uvicorn prod, **需要重启** (AGENTS.md V1 badge 重启坑: `./scripts/stop-prod.sh && ./scripts/start-prod.sh`)

### Phase 2 — dci-assign 老师要求填充 (修复 1 + 3.1 + 3.2)
1. `practice.html:2262-2274` `updateDashboard` 加 `reqText` 参数 + 写 `dciAssignText`
2. `practice.html:1616` `selectItem` 调用改 `updateDashboard(reqText)`
3. `practice.html:811` `.dci-assign-label` 11px → 13px
4. `practice.html:812` `.dci-assign-text` 12px → 13px + 加 `white-space: pre-wrap; word-break: break-word; max-height: 80px; overflow-y: auto`
5. **真机验证**: 
   - 选 "萨丽哈" (有长 requirements: "全按作低音2 "4"的音准, 不要偏高...")
   - 选 "吸气长音" (短: "增加 高音6, 2-4指都可以...")
   - 选 "长音练习" (无 requirement, 应显示 "—")
   - 看 dashboard 第三列完整显示

### Phase 3 — sp-tempo-row 重排 (修复 2)
1. `practice.html:970-985` 主计时区: 把 `sp-tempo-row` 内容拆成 `sp-tempo-row-1` + `sp-tempo-row-2`
2. `practice.html:1018-1031` 补录区: 同样拆分
3. `practice.html:404-405` `.sp-tempo-row` 改名 `.sp-tempo-row-1` + 加 `.sp-tempo-row-2` 样式
4. `practice.html:450-453` `.sp-tempo-hint` 去 `margin-left: auto`
5. `practice.html:432-441` `.bpm-stepper` / `.bpm-step` / `.bpm-value` 加 `font-variant-numeric: tabular-nums`
6. 加 `@media (max-width: 700px)` 块: 缩 bpm-stepper 36→32, bpm-value 48→40
7. **真机验证**: 
   - iPad 1024×768 横屏 (开发机 DevTools 模拟) — 速度行不挤, hint 在第二行
   - 选科目后改 BPM 多次, bpm 数字不抖
   - 补录 tab 同验证

### Phase 4 — 视觉 + 回归
1. **HTTP 验证**: `curl -s http://localhost:8765/practice` 200 + HTML 含改动
2. **pytest** 仅新文件 + 现有 practice: 跑 `pytest tests/test_api_log_dedup.py tests/test_dedup_window.py -q` (无回归)
3. **真机 iPad 截图**: 用 DevTools 1024×768 + 2048×1536 各截一张, 验:
   - 选 "萨丽哈" 时 dashboard 老师要求完整 (含换行)
   - timer 区块 picker-card 紧凑, session-panel 宽松
   - wheel 没 desc 文字
4. **commit + push**:
   - 单 commit: `fix(practice): V4 tile 修复 — dci-assign 填充 + wheel 去 desc + sp-tempo-row 重排 (iPad 友好)`
   - push origin/fix/practice-v4-timer-req-tile-20260729
   - 推完开 PR, **不**自己 merge

### Phase 5 — 收尾
1. 主仓: `vibe-coding-log.md` append 一条; `STATUS.md` 加一行 "下一版 V4 tile 修复"
2. Obsidian: 双写 handoff `AI-handoff-2026-07-29-v4-tile.md` 到 `tqob/05-Coding/project-dizical/`
3. `md5 -q` 主仓 plan + Obsidian plan 一致
4. AGENTS.md 不动 (这是 UI 修复不是惯例变更)
5. 关键截图放 Obsidian `00-Artifacts/practice-v4-tile/`

---

## 4. 风险 / 反向论证

| 风险 | 应对 |
|------|------|
| `data-req` 含 HTML 特殊字符 (单引号已转义, 但 `<>&` 没转) | 现状已用 `textContent` 写入 (line 1191-1197 updateReqPanel 用 innerHTML 拼接, 是个旧 XSS 隐患, **不在本次范围**) — dashboard 用 textContent 安全 |
| wheel-desc 删除后, 选 5min vs 60min 失去文字提示 | descs 当前没数据 (timer wheel 传 descs={} 等), 实际无内容, 删了没影响 |
| sp-tempo-row 改两行后, 补录 tab 的 hint 跟主计时 hint 冲突 | 各自 id (`tempoHint` vs 无, 补录无 hint), 互不影响 |
| 真机 iPad 1024×768 测不了 (无 iPad) | DevTools 1024×768 + 2048×1536 模拟 = 接近真实; dad 拍板后在他 iPad 真机 1 次验证 |

---

## 5. 范围 / 不在范围 (YAGNI)

**接受**:
- HTML 结构改写 (sp-tempo-row 拆 2 行) — 是 CSS 改不动时唯一办法
- `data-req` 复用 (避免新 API) — server 端已注入, 不增加 round-trip
- dashboard scroll (80px max-height) — 接受滚动条, 不重排整 dashboard

**拒绝**:
- 不重做 wheel 弧形几何 (改 ARC_RADIUS 会动 selected 索引)
- 不加新 API (`/api/assignments/latest` 加 requirements 字段 — YAGNI, button attr 已含)
- 不动 picker-card 整体 (dad 没要求, 且与计时器冲突大)
- 不重写 `updateReqPanel` 的 innerHTML XSS (不在本次范围, 单独工单)

---

## 6. 验证矩阵

| 维度 | 命令 / 操作 | 通过判据 |
|------|------------|----------|
| 静态 | `curl -sI http://localhost:8765/practice` | 200 OK |
| 静态 | `curl -s http://localhost:8765/practice \| grep -E "dci-assign-text\|sp-tempo-row-[12]\|wheel-desc"` | dashboard 有 dci-assign-text, 无 wheel-desc, 有 row-1/row-2 |
| 单元 | `pytest tests/test_api_log_dedup.py tests/test_dedup_window.py -q` | 18 passed |
| 真机 | DevTools 1024×768 选 "萨丽哈" | dashboard 老师要求完整 + wheel 无 desc + speed row 不挤 |
| 真机 | DevTools 1024×768 选 "无要求"科目 (灰按钮) | dashboard 老师要求显示 "—" |
| 回归 | 全套 pytest (含 13 已知失败) | 13 仍 fail (pre-existing, 与本 PR 无关) |

---

## 7. Ship / Hold 判定

**SHIP** 一次性合, 4 个修复在一个 PR (`fix/practice-v4-timer-req-tile-20260729`).
- 阻塞级: 无
- 一次性小修, 不拆 commit, 但 commit message 清晰说明 4 处

---

*证据索引: practice.html L943 dci-assign 空, L1616 updateDashboard 无 reqText 参数, L2567 wheel-desc 渲染, L404 sp-tempo-row nowrap, L802 dci-assign 字体 11/12px, app.py L1681-1688 data-req 注入, app.py L1080-1113 /api/assignments/latest 无 requirements 字段, weekly_assignments 表结构 (sqlite3 验证)*
