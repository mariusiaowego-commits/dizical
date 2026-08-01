# Tech Spec — /config/practice-log 选中科目后展示 session 细节 + 默认速度

**Sprint**: 26080101
**Date**: 2026-08-01

---

## 改动文件清单

| 文件 | 类型 | 行数预估 |
|------|------|---------|
| `src/kid_app/templates/config-practice-log.html` | 改 | +120 行 (CSS + JS) |

后端 0 改动.

## 前端架构

### 复用 vs 复制

`practice.html` 的 `fillSessionDefaults` (line 1456) / `renderBpmPresets` (1491) / `renderContentTags` (1543) 操作单例 DOM (`#sessionPanel` / `#sessionContentTags`), **不能直接复用**.

**复制 + 重命名 + 适配多行**:
```js
// practice 单例版 → practice-log 多行版
async function fillEntryDefaults(idx, itemId) { ... }
function renderEntryBpmPresets(idx, itemId) { ... }
function renderEntryContentTags(idx, itemId) { ... }
```

每个函数接受 `idx`, 内部 querySelector 限定在 `.log-entry-row[data-idx="${idx}"]` 子树.

### 关键 DOM 节点 (单行内)

```html
<div class="log-entry-row" data-idx="${i}">
  <div class="entry-top">
    <select class="item-select" data-idx="${i}">...</select>
    <input minutes>
    <button class="apply-default-btn" data-idx="${i}">应用默认</button>
    <button class="remove-btn">×</button>
  </div>
  <div class="log-tempo-row" data-idx="${i}">
    <button class="tempo-note-mini">♪</button>
    <button class="tempo-note-mini">♩</button>
    <span>=</span>
    <div class="bpm-stepper">
      <button class="bpm-step" onclick="stepEntryBpm(-1, ${i})">−</button>
      <span class="bpm-value" data-idx="${i}">80</span>
      <button class="bpm-step" onclick="stepEntryBpm(+1, ${i})">+</button>
    </div>
    <input type="hidden" class="tempo-bpm-input" data-idx="${i}" value="80">
  </div>
  <div class="log-tempo-hint" data-idx="${i}">♪ = 80 (默认)</div>
  <div class="log-bpm-presets" data-idx="${i}"></div>
  <div class="log-content-tags" data-idx="${i}"></div>
  <input type="text" class="log-content-input" data-idx="${i}" placeholder="练什么?">
</div>
```

### CSS 新增 (跟 practice.html V4 样式对齐)

```css
.bpm-stepper {
  display: inline-flex; align-items: center; gap: 4px;
  background: #FFF8F0; border: 1px solid #E8D8B0; border-radius: 8px;
  padding: 2px 6px;
}
.bpm-step {
  width: 22px; height: 22px; border: none; background: transparent;
  cursor: pointer; font-size: 14px; font-weight: 700; color: #8B6914;
}
.bpm-value { min-width: 28px; text-align: center; font-weight: 600; color: #5D4037; }

.log-bpm-presets { display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap; }
.bpm-preset-mini {
  padding: 2px 8px; background: #FFF8F0; border: 1px solid #E8D8B0;
  border-radius: 6px; font-size: 11px; color: #8B6914; cursor: pointer;
}
.bpm-preset-mini:hover { background: #FF6B6B; color: #fff; border-color: #FF6B6B; }

.log-content-tags { display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap; }
.sp-content-tag-mini {
  padding: 3px 10px; background: #F0E8D0; border: 1px solid #D4B886;
  border-radius: 14px; font-size: 11px; color: #5D4037; cursor: pointer;
}
.sp-content-tag-mini:hover { background: #FF6B6B; color: #fff; border-color: #FF6B6B; }

.log-tempo-hint {
  font-size: 11px; color: #8B6914; margin-top: 2px;
}

.apply-default-btn {
  padding: 4px 10px; font-size: 11px; border: 1px solid #a8d5ba;
  background: rgba(168,213,186,0.15); color: #2E7D32;
  border-radius: 6px; cursor: pointer;
}
.apply-default-btn:hover { background: rgba(168,213,186,0.3); }
.apply-default-btn:disabled { opacity: 0.4; cursor: not-allowed; }
```

### JS 逻辑

```js
// 应用默认按钮: 拉 3 个 fetch 链
async function fillEntryDefaults(idx) {
  const entry = logEntries[idx];
  if (!entry || !entry.item_id) return;
  const itemId = entry.item_id;

  // 1. 老师要求
  try {
    let r = await fetch('/api/assignments/latest?item_id=' + itemId);
    let d = await r.json();
    if (d.found && d.tempo_note) {
      applyEntryTempo(idx, d.tempo_note, d.tempo_bpm, '老师要求');
      return;
    }
  } catch(e) {}

  // 2. 上次
  try {
    let r = await fetch('/api/practice-sessions/latest?item_id=' + itemId);
    let d = await r.json();
    if (d.found && d.tempo_note) {
      applyEntryTempo(idx, d.tempo_note, d.tempo_bpm, '上次');
      return;
    }
  } catch(e) {}

  // 3. 默认
  applyEntryTempo(idx, '♪', 80, '默认');
}

function applyEntryTempo(idx, note, bpm, source) {
  const row = document.querySelector(`.log-entry-row[data-idx="${idx}"]`);
  if (!row) return;
  // 音符按钮
  row.querySelectorAll('.tempo-note-mini').forEach(b => b.classList.remove('selected'));
  row.querySelector(`.tempo-note-mini[data-note="${note}"]`)?.classList.add('selected');
  // BPM 显示 + 隐藏 input
  row.querySelector('.bpm-value').textContent = bpm;
  row.querySelector('.tempo-bpm-input').value = bpm;
  // hint
  row.querySelector('.log-tempo-hint').textContent = note + ' = ' + bpm + ' (' + source + ')';
  // 同步到 logEntries[idx]
  logEntries[idx].tempo_note = note;
  logEntries[idx].tempo_bpm = bpm;
  // 渲染预设 + 标签
  renderEntryBpmPresets(idx);
  renderEntryContentTags(idx);
}

function stepEntryBpm(delta, idx) {
  const input = document.querySelector(`.tempo-bpm-input[data-idx="${idx}"]`);
  let v = parseInt(input.value) || 80;
  v = Math.max(40, Math.min(150, v + delta));
  input.value = v;
  document.querySelector(`.bpm-value[data-idx="${idx}"]`).textContent = v;
  logEntries[idx].tempo_bpm = v;
  // 同步 hint (去掉 source 后缀)
  const note = document.querySelector(`.log-entry-row[data-idx="${idx}"] .tempo-note-mini.selected`)?.dataset?.note || '♪';
  const hint = document.querySelector(`.log-tempo-hint[data-idx="${idx}"]`);
  if (hint) hint.textContent = note + ' = ' + v;
}

function renderEntryBpmPresets(idx) {
  const entry = logEntries[idx];
  if (!entry || !entry.item_id) return;
  const container = document.querySelector(`.log-bpm-presets[data-idx="${idx}"]`);
  if (!container) return;
  let presets = [60, 80, 100, 120];
  // V4 跟 practice 一致: 老师要求 BPM 单独提一个
  // 但 practice-log 已经点过"应用默认", state 里知道 source, 用当前 BPM 即可
  const cur = parseInt(entry.tempo_bpm) || 80;
  if (cur) presets = [cur, ...presets.filter(p => p !== cur)];
  container.innerHTML = [...new Set(presets)].slice(0, 5).map(p =>
    `<span class="bpm-preset-mini" onclick="setEntryBpm(${p}, ${idx})">${p}</span>`
  ).join('');
}

function setEntryBpm(bpm, idx) {
  bpm = Math.max(40, Math.min(150, parseInt(bpm) || 80));
  document.querySelector(`.tempo-bpm-input[data-idx="${idx}"]`).value = bpm;
  document.querySelector(`.bpm-value[data-idx="${idx}"]`).textContent = bpm;
  logEntries[idx].tempo_bpm = bpm;
  stepEntryBpm(0, idx); // 同步 hint, 不动 BPM
}

function renderEntryContentTags(idx) {
  const entry = logEntries[idx];
  if (!entry || !entry.item_id) return;
  const container = document.querySelector(`.log-content-tags[data-idx="${idx}"]`);
  if (!container) return;
  const item = practiceItems.find(it => it.item_id == entry.item_id);
  let options = [];
  if (item && item.content_options) {
    options = String(item.content_options).split(/[,，]/).map(s => s.trim()).filter(Boolean);
  }
  if (!options.length) options = ['长音练习', '吐音练习', '连吐练习', '换气练习'];
  container.innerHTML = options.map(opt =>
    `<span class="sp-content-tag-mini" onclick="setEntryContent('${opt.replace(/'/g, "\\'")}', ${idx})">${opt}</span>`
  ).join('');
}

function setEntryContent(text, idx) {
  const input = document.querySelector(`.log-content-input[data-idx="${idx}"]`);
  if (input) {
    input.value = text;
    logEntries[idx].content = text;
  }
}

// 应用默认按钮点击
function applyDefaultBtnHandler(idx) {
  const entry = logEntries[idx];
  if (!entry || !entry.item_id) {
    alert('请先选择科目');
    return;
  }
  // R4: 防误覆盖
  const hasUserInput = (entry.tempo_bpm && entry.tempo_bpm !== 80) ||
                       (entry.content && entry.content.trim());
  // 简化: 只在 content 已填时确认 (BPM 改动频繁, 不挡)
  if (entry.content && entry.content.trim()) {
    if (!confirm('已填写练习内容, 应用默认将保留你填的速度但重置内容为预设, 继续?')) {
      return;
    }
  }
  fillEntryDefaults(idx);
}
```

**重要**: entry-level state (`logEntries[idx].tempo_note / tempo_bpm / content`) 必须跟 DOM 双向同步, 否则提交时拿到的是 stale 值.

### 既有 renderLogEntries 修改点

加 "应用默认" 按钮 (line 806 后) + 加 hint/presets/tags 容器 (line 808-813 替换 log-tempo-row).

加 item-select change 监听 (line 819-826) 末尾: 切换科目后清空 entries[idx] 的 tempo_note/tempo_bpm/content (跟 practice 的 `selectItem` line 1589-1591 一致) + 重渲染 tags.

加 remove-btn 监听 (line 858-864) 末尾: splice + 重新 renderLogEntries (已有).

## 验证清单

| # | 项 | 命令 / 操作 |
|---|----|------------|
| 1 | 选中已有老师要求的科目 → 应用默认 | 手测, BPM=82, hint="老师要求" |
| 2 | 选无要求有历史的科目 → 应用默认 | 手测, BPM=75, hint="上次" |
| 3 | 选新科目 → 应用默认 | 手测, BPM=80, hint="默认" |
| 4 | 选 2 科目行, 各自点应用默认 | 手测, 互不串 |
| 5 | 已填 content → 再点应用默认 | 手测, 弹 confirm |
| 6 | presets / tags 点击写入 | 手测 |
| 7 | 提交后数据正确 | curl POST /api/log 看 sessions 表 |
| 8 | 重启服务后页面加载无报错 | `./scripts/start-prod.sh` |

## 风险与缓解

| # | 风险 | 缓解 |
|---|------|------|
| 1 | 多行 DOM selectors 串行 | 严格 `[data-idx]` 隔离, 单元函数单独 |
| 2 | 切换科目频繁 fetch | 不缓存 (按按钮触发, 用户感知可控) |
| 3 | 既有 `submitLogBtn` 拿到 stale state | 同步 entry.tempo_note/bpm/content (上面已加) |
| 4 | CSS 跟全局 style.css 冲突 | 用专用 class 前缀 `.bpm-preset-mini` / `.sp-content-tag-mini` 跟 practice 错开 |