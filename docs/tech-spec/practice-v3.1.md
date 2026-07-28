# 技术 Spec: Practice V3.1 UI/UX 效率升级

> **PRD**: AI-PRD-练习计时细分内容-260727.md §11
> **日期**: 2026-07-28
> **范围**: 练习页 5 大功能升级
> **目标**: 纯前端 + 轻量后端改动，不引新依赖，不硬改 dizicute token

---

## 目录

1. [整体架构](#1-整体架构)
2. [卡片合并（P0）](#2-卡片合并p0)
3. [速度默认值 + 快速选择（P0）](#3-速度默认值--快速选择p0)
4. [内容输入预置选项（P0）](#4-内容输入预置选项p0)
5. [布局融合（P0）](#5-布局融合p0)
6. [补录分离（P1）](#6-补录分离p1)
7. [旋钮阻力（P1）](#7-旋钮阻力p1)
8. [测试计划](#8-测试计划)
9. [风险评估](#9-风险评估)

---

## 1. 整体架构

### 改动范围
- **后端轻量改动**：1 个 DB 字段 + 1 个 API 字段扩展
  - `practice_items` 加 `content_options TEXT DEFAULT '[]'`
  - `GET /api/practice-items` 返回时包含 `content_options`
- **前端重点改动**：`practice.html` + `config.html`（90% 工作量在前端）
- **共享组件**：`TempoSelector`、`ContentTagList`（练习页 + 补录页共享）

### 文件清单
```
src/kid_app/templates/practice.html       # 主练习页（卡片合并 + 布局融合 + 速度选择 + 内容标签）
src/kid_app/templates/config.html         # 科目编辑加 content_options 文本框
src/kid_app/app.py                        # practice-items API 返 content_options
src/database.py                           # practice_items 表加 content_options 字段
migrations/007_add_practice_item_content_options.sql
static/js/practice-*.js                   # 拆分组件（可选，视复杂度）
tests/test_practice_v3_1.py               # 新增测试
```

### 向后兼容
- 旧数据 `content_options` 为 NULL/空数组 → 显示全局默认选项
- 不影响现有 API，小程序端完全无感

---

## 2. 卡片合并（P0）

### 2.1 DOM 结构调整

**Before**：
```html
<div class="item-section card">...</div>
<div class="floor floor-req">...</div>
```

**After**：
```html
<div class="item-section card merged">
  <!-- 原有：科目选择 / 进度条 / model-tag -->
  
  <!-- 新增：req-highlight 卡片 -->
  <div class="req-highlight-card">
    <span class="req-icon">✨</span>
    <span class="req-text">{{ req.highlight }}</span>
  </div>
  
  <!-- 原有：story-text（样式改为斜体+60%灰） -->
  <p class="story-text muted">{{ story_text }}</p>
  
  <!-- 2:8 区域 -->
  <div class="layout-2-8">
    <div class="zone-left">
      <span class="sum-tag">{{ total_minutes }}分钟</span>
      <button class="btn-soft-pill secondary">重 选</button>
    </div>
    <div class="zone-right">
      <!-- 预留空间，不新增内容 -->
    </div>
  </div>
</div>
```

### 2.2 SoftPillButton CSS 实现

```css
.btn-soft-pill {
  position: relative;
  display: block;
  border-radius: 9999px;
  text-align: center;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: -0.01em;
  border: none;
  cursor: pointer;
  backdrop-filter: blur(6px);
  transition: transform 0.2s;
}

.btn-soft-pill:active {
  transform: scale(0.98);
  transition-duration: 50ms;
}

/* secondary 变体（白色半透明） */
.btn-soft-pill.secondary {
  color: #222;
  box-shadow: 
    0 12px 24px -8px rgba(0, 0, 0, 0.12),
    0 4px 8px -2px rgba(0, 0, 0, 0.08),
    0 1px 2px rgba(0, 0, 0, 0.06);
}

.btn-soft-pill.secondary::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.2s;
}

.btn-soft-pill.secondary::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  background: 
    linear-gradient(rgb(255, 255, 255) 0%, rgba(255, 255, 255, 0) 100%);
  opacity: 0.32;
  transition: all 0.2s;
}

.btn-soft-pill.secondary:active::after {
  opacity: 0;
  transition-duration: 50ms;
}

/* 文字在最上层 */
.btn-soft-pill span {
  position: relative;
  z-index: 1;
}

/* 2:8 布局 */
.layout-2-8 {
  display: grid;
  grid-template-columns: 2fr 8fr;
  gap: 16px;
  margin-top: 12px;
}

.zone-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}
```

### 2.3 删除内容
- `req-content` div 中的科目名称和 item_id 整段删除
- 整个 `<div class="floor floor-req">` 删除

---

## 3. 速度默认值 + 快速选择（P0）

### 3.1 速度默认值

**API 调用**：选科目后调用
```javascript
GET /api/practice-sessions/latest?item_id=123
→ { tempo_note: '♩', tempo_bpm: 80, from_assignment: false }
```

**降级逻辑**：
1. API 返回有值 → 用 session 的
2. API 空 → 从 assignment metronome 字段正则解析（`/[♩♪]=(\d+)/`）
3. 都没有 → fallback `{ tempo_note: '♪', tempo_bpm: 80 }`

### 3.2 Mini Dial 速度选择器（不弹键盘）

**尺寸**：直径 80px（大旋钮的 1/3）
**范围**：40–150 BPM
**吸附点**：80/90/100/120（±2 强吸附）

**JS 实现骨架**：
```javascript
class MiniTempoDial {
  constructor(element, options = {}) {
    this.min = 40
    this.max = 150
    this.snapPoints = [80, 90, 100, 120]
    this.snapThreshold = 2 // ±2 内强吸附
    this.currentBpm = options.initial || 80
    
    this.bindEvents()
  }
  
  // 角度 → BPM（线性映射）
  angleToBpm(angle) { ... }
  
  // BPM → 角度
  bpmToAngle(bpm) { ... }
  
  // 吸附函数
  applySnap(bpm) {
    for (const point of this.snapPoints) {
      if (Math.abs(bpm - point) <= this.snapThreshold) {
        return point
      }
    }
    return bpm
  }
  
  // 触摸/鼠标事件
  onDragStart(e) { ... }
  onDragMove(e) {
    const rawBpm = this.angleToBpm(calculateAngle(e))
    this.currentBpm = this.applySnap(rawBpm)
    this.updateUI()
  }
  onDragEnd(e) { ... }
}
```

**备选方案**（如果小转盘交互不好）：横向滑动条 + ±5 步进按钮

---

## 4. 内容输入预置选项（P0）

### 4.1 数据库迁移

```sql
-- SQLite
ALTER TABLE practice_items ADD COLUMN content_options TEXT DEFAULT '[]';

-- MySQL（同步）
ALTER TABLE practice_items ADD COLUMN content_options TEXT DEFAULT '[]';
```

迁移脚本：`migrations/007_add_practice_item_content_options.sql`

### 4.2 config 编辑页面

在科目编辑 form 里加多行文本框：
```html
<div class="form-group">
  <label>✨ 练习内容预置选项</label>
  <textarea 
    name="content_options" 
    rows="4"
    placeholder="第一分句&#10;第二分句&#10;整首连奏&#10;（每行一个选项）"
  >{{ item.content_options?.join('\n') || '' }}</textarea>
  <p class="form-hint">每行一个选项，留空即无；前端选科目后自动显示为标签按钮</p>
</div>
```

**后端保存逻辑**：
```python
# 在 save_practice_item() 里
content_options_text = form.get('content_options', '')
content_options = [line.strip() for line in content_options_text.split('\n') if line.strip()]
# 存为 JSON 字符串
item['content_options'] = json.dumps(content_options, ensure_ascii=False)
```

### 4.3 前端展示组件

```javascript
// ContentTagList 组件（练习页 + 补录页共享）
function renderContentTags(container, options, onSelect) {
  // 全局默认选项
  const globalDefaults = ['连吐练习', '换气练习', '长音保持', '节奏稳定']
  
  // 合并：科目选项在前，全局在后
  const allOptions = [...(options || []), ...globalDefaults]
  
  // 渲染标签（去重）
  const seen = new Set()
  allOptions.forEach(opt => {
    if (seen.has(opt)) return
    seen.add(opt)
    
    const tag = document.createElement('button')
    tag.className = 'content-tag'
    tag.textContent = opt
    tag.onclick = () => onSelect(opt)
    container.appendChild(tag)
  })
}

// 使用方式：
// 选科目后拿到 item.content_options（JSON.parse）
// 调用 renderContentTags(tagContainer, parsedOptions, (text) => {
//   input.value = text
// })
```

---

## 5. 布局融合（P0）

### 5.1 DOM 结构调整

**Before**：
```html
<div class="timer-card card">...</div>
<div class="session-panel card">...</div>
```

**After**：
```html
<div class="practice-main-card card merged">
  <div class="practice-main-layout">
    <!-- 左侧：大旋钮 -->
    <div class="knob-column">
      <div class="dial-knob-container">
        <!-- 原有大旋钮，大小不变 -->
      </div>
    </div>
    
    <!-- 右侧：session panel -->
    <div class="session-column">
      <h4>✨ 本次练习</h4>
      
      <!-- 速度行：mini dial + 音符选择器 -->
      <div class="tempo-row">
        <span>速度</span>
        <div class="mini-tempo-dial"></div>
        <span class="bpm-display">80</span>
        <select class="note-select">
          <option>♩</option>
          <option>♪</option>
        </select>
      </div>
      
      <!-- 内容行：标签 + 输入框 -->
      <div class="content-row">
        <span>内容</span>
        <div class="content-tags"></div>
        <input type="text" class="content-input" placeholder="或手动输入...">
      </div>
      
      <!-- 开始按钮（往下移） -->
      <div class="action-row">
        <button class="btn-soft-pill primary">开始计时</button>
      </div>
    </div>
  </div>
</div>
```

### 5.2 CSS Grid 布局

```css
.practice-main-layout {
  display: grid;
  grid-template-columns: 280px 1fr; /* 固定旋钮宽度，剩余给内容 */
  gap: 24px;
  align-items: center;
}

.knob-column {
  display: flex;
  justify-content: center;
}

.session-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* waza-ui 检查点 */
.practice-main-card {
  /* 与其他卡片统一的 box-shadow */
  box-shadow: var(--card-shadow);
  /* 统一的圆角 */
  border-radius: var(--card-radius);
  /* 统一的内边距 */
  padding: 24px;
}
```

### 5.3 waza-ui 检查清单（开发完成后必须过）

- [ ] 没有 emoji，全用 SVG icon
- [ ] 卡片深度统一（一套 box-shadow）
- [ ] 所有内边距 ≥ 16px
- [ ] CTA 按钮不突兀（SoftPill primary 风格）
- [ ] 不硬改 `dizicute` token 变量
- [ ] 圆角/阴影/字体大小与其他页面保持一致

---

## 6. 补录分离（P1）

### 6.1 组件拆分原则

| 组件 | 练习页用 | 补录页用 | 共享逻辑 |
|---|---|---|---|
| 速度选择 | `MiniTempoDial` | `MiniTempoDial` | ✅ 共享 |
| 内容标签 | `ContentTagList` | `ContentTagList` | ✅ 共享 |
| Item 选择 | `ItemSelectorPractice` | `ItemSelectorRecall` | ❌ 独立 |
| Session Panel | `SessionPanelPractice` | `SessionPanelRecall` | ❌ 独立 |

### 6.2 代码组织方式

```javascript
// 共享组件（放在文件顶部）
function MiniTempoDial(container, options) { ... }
function ContentTagList(container, options, onSelect) { ... }

// 练习页专用
function SessionPanelPractice(element) {
  this.dial = new MiniTempoDial(element.querySelector('.tempo-dial'))
  this.tags = new ContentTagList(element.querySelector('.tag-container'))
  // ... 练习页特有状态机：计时中可改 / 开始按钮逻辑 / 提交逻辑
}

// 补录页专用
function SessionPanelRecall(element) {
  this.dial = new MiniTempoDial(element.querySelector('.tempo-dial'))
  this.tags = new ContentTagList(element.querySelector('.tag-container'))
  // ... 补录页特有逻辑：历史数据回填 / 保存按钮逻辑
}

// 初始化
if (isPracticePage) {
  new SessionPanelPractice(document.querySelector('.session-panel'))
} else if (isRecallPage) {
  new SessionPanelRecall(document.querySelector('.session-panel'))
}
```

### 6.3 删除的代码

所有 `if (isRecall)` / `if (page === 'recall')` 之类的条件判断全部删除，用不同组件替代。

---

## 7. 旋钮阻力（P1）

### 7.1 吸附函数实现

```javascript
// dial-knob.js 原有基础上修改

const SNAP_POINTS = [5, 10, 15, 20, 25, 30]
const SNAP_STRONG_THRESHOLD = 0.5 // ±0.5° 内强吸附（直接跳）
const SNAP_WEAK_THRESHOLD = 1.0   // ±1° 内弱吸附（阻尼 0.3）

function applySnap(minutes, delta) {
  for (const point of SNAP_POINTS) {
    const dist = Math.abs(minutes - point)
    
    // 强吸附：直接跳到目标值
    if (dist <= SNAP_STRONG_THRESHOLD) {
      return point
    }
    
    // 弱吸附：阻尼 0.3
    if (dist <= SNAP_WEAK_THRESHOLD) {
      // 计算方向
      const direction = minutes < point ? 1 : -1
      // delta 乘以阻尼系数
      const dampedDelta = delta * 0.3
      return minutes + dampedDelta
    }
  }
  
  // 正常线性
  return minutes + delta
}

// 在旋转事件里用：
function onRotate(angleDelta) {
  const rawDelta = angleToMinutes(angleDelta)
  const newMinutes = applySnap(currentMinutes, rawDelta)
  currentMinutes = clamp(newMinutes, 1, 60)
  updateUI()
}
```

### 7.2 视觉配合

```css
.dial-knob.snapping {
  transition: transform 0.1s ease-out;
}
```

在强吸附时临时加 `snapping` class，让旋转有"卡入"的视觉效果。

---

## 8. 测试计划

### 8.1 后端测试
```python
def test_practice_item_content_options_default():
    # 新建科目默认是空数组
    item = db.create_practice_item('测试科目', 1)
    assert item.get('content_options') == '[]'

def test_practice_item_content_options_save():
    # 保存多行文本能正确解析为数组
    form = {'name': '测试', 'content_options': '第一分句\n第二分句\n'}
    saved = db.save_practice_item(1, form)
    parsed = json.loads(saved['content_options'])
    assert parsed == ['第一分句', '第二分句']
```

### 8.2 前端手动测试清单
见 PRD §11.8 验收标准（25 项全量测试）

---

## 9. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| Mini tempo dial 交互不好用 | 中 | 中 | 准备备选方案（横向滑动条 + 步进按钮） |
| 融合布局在 iPad mini 上溢出 | 中 | 中 | 开发完成后必须实机测试；实在不行改为上下布局 |
| 旋钮阻尼感太强/太弱，手感不对 | 高 | 低 | 做成可配置系数，实机调整 |
| content_options 字段忘记加 MySQL 迁移 | 低 | 高 | 开发 checklist 第一条就是写两个迁移脚本 |
| 组件拆分引入回归 bug | 中 | 中 | 开发前先备份当前 JS，改完后逐功能回归测试 |

---

## 讨论点（需要其他 agent 提意见）

1. **Mini tempo dial 交互方案**：圆形小转盘 vs 横向滑动条，哪个更好？
2. **组件拆分粒度**：MiniTempoDial + ContentTagList 两个共享组件够了吗？要不要拆更细？
3. **布局融合方案**：左旋钮右内容的 grid 布局，在 iPad mini 横屏会不会太挤？
4. **旋钮阻力实现**：吸附函数用角度计算还是用分钟数直接算？
5. **content_options 数据库类型**：TEXT 存 JSON 够了吗？要不要用 MySQL JSON 类型？
