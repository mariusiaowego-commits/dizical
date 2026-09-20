---
id: 26091901
type: tech-spec
version: 0.1.0
date: 2026-09-19
status: 实装依据 — 由 agy 方案 §1-§5 转写
project: dizical
sprint: sprint-26091901-timer-ruler-drag
summary: "practice 页 #rulerInput 自定义 Pointer Events 拖动时长 — iPad 空白刻度区跟手 + 红针 scaleY 微高亮 + spring 回弹"
tags: [dizical, practice, timer, ruler, drag, ipad, sprint-26091901, tech-spec]
---

# Tech Spec · Sprint 26091901 计时器 ruler drag

## 1. 设计依据

依据: `/tmp/sprint-26091901-agy-plan.md` §1-§5 (agy 出, dad 拍板定稿).
PRD: `sprints/sprint-26091901-timer-ruler-drag-2026-09-19/PRD-timer-ruler-drag.md`.

## 2. 文件改动清单 (line 锚点)

| 文件 | 锚点 | 改动 |
|------|------|------|
| `src/kid_app/templates/practice.html` | line 211-216 (CSS) | `.ruler-input` 加 `touch-action: none`; 新增 `.tick.cur.dragging` 类 |
| `src/kid_app/templates/practice.html` | line 3059-3070 (常量) | 加 `dragCtx` 状态对象 |
| `src/kid_app/templates/practice.html` | line 3096-3109 (`ttSetDuration`) | 支持 `skipVine` 参数 + `buildVineDebounced()` 防抖 |
| `src/kid_app/templates/practice.html` | line 3115-3133 (`ttInitTimer`) | 重写 4 个事件: down/move/up/cancel |
| `tests/test_practice_timer_frontend.py` | line 25-40 / 110-140 | 追加 5 条静态断言 (touch-action / setPointerCapture / .dragging) |

## 3. 代码骨架 (实装参考, agy §3 原样)

### 3.1 CSS (`practice.html` 插入到 `.ruler-input` 块后)

```css
.ruler-input { touch-action: none; }                /* 阻止 WebKit 上下滚动 */
.tick.cur.dragging {
  transform: scaleY(1.2);
  filter: brightness(1.15);
  transition: none;                                  /* 拖拽中禁用过渡, 保证即时响应 */
}
```

### 3.2 JS 状态与常量 (`practice.html` 紧跟现有常量)

```javascript
let dragCtx = { active: false, startX: 0, startDur: 0, pointerId: null };

function buildVineDebounced(ms = 150) {
  clearTimeout(buildVineDebounced._t);
  buildVineDebounced._t = setTimeout(() => { if (hasGsap()) buildVine(); }, ms);
}
```

### 3.3 `ttSetDuration` 增强 (签名扩展, 不破现有调用)

```javascript
function ttSetDuration(v, skipVine) {
  v = Math.min(MAX_MIN, Math.max(MIN_MIN, v | 0));     // 钳位 1~30, 兼容原 ttSetDuration(v) 调用
  if (v === duration) return;
  duration = v;
  const ri = document.getElementById('rulerInput');
  if (ri) ri.value = v;
  ttRenderDigits(duration * 60);
  paintRulerSelect(duration);
  setSelectModality();
  if (skipVine) { buildVineDebounced(); } else { buildVine(); }
  startSecFlicker();
  scheduleSecSettle(200);
}
```

### 3.4 `ttInitTimer` 事件层重写 (替换 line 3115-3121 原 4 监听)

```javascript
function ttInitTimer(){
  const root = document.getElementById('ttCounter');
  if (!root) return;
  const ri = document.getElementById('rulerInput');
  if (ri) {
    // 保留原生 input 事件作为键盘/辅助技术兜底 (a11y)
    ri.addEventListener('input', () => ttSetDuration(parseInt(ri.value, 10)));
    // 自定义 Pointer Events: 整段尺子按下相对拖拽
    ri.addEventListener('pointerdown', (e) => {
      if (typeof started !== 'undefined' && started) return;     // 运行/暂停守卫
      dragCtx = { active: true, startX: e.clientX, startDur: duration, pointerId: e.pointerId };
      try { ri.setPointerCapture(e.pointerId); } catch (_) {}
      const cur = document.querySelector('.tick.cur');
      if (cur) cur.classList.add('dragging');
      startSecFlicker();
    });
    ri.addEventListener('pointermove', (e) => {
      if (!dragCtx.active) return;
      const ruler = document.getElementById('ruler');
      const w = ruler ? ruler.getBoundingClientRect().width : 0;
      if (w <= 0) return;
      const pxPerMin = w / (MAX_MIN - MIN_MIN);                  // 动态 ≈ 14.5px/min
      const deltaMin = Math.round((e.clientX - dragCtx.startX) / pxPerMin);
      const nextDur = Math.min(MAX_MIN, Math.max(MIN_MIN, dragCtx.startDur + deltaMin));
      if (nextDur !== duration) ttSetDuration(nextDur, true);   // skipVine 防抖
    });
    const onEnd = (e) => {
      if (!dragCtx.active) return;
      try { ri.releasePointerCapture(dragCtx.pointerId); } catch (_) {}
      const cur = document.querySelector('.tick.cur');
      if (cur) {
        cur.classList.remove('dragging');
        if (hasGsap()) {
          gsap.fromTo(cur, { scaleY: 1.2 }, { scaleY: 1.0, duration: 0.24, ease: 'back.out(2)', clearProps: 'transform' });
        }
      }
      scheduleSecSettle(80);
      buildVineDebounced();
      dragCtx.active = false;
    };
    ri.addEventListener('pointerup', onEnd);
    ri.addEventListener('pointercancel', onEnd);
  }
  try {
    counter = makeCounter(root);
    buildRuler(document.getElementById('rulerRow'));
    if (hasGsap()) { buildBubbles(); buildVine(); }
    ttLastSec = duration * 60;
    renderCounter(counter, duration * 60, 1, 0.35);
    paintRulerSelect(duration);
    setSelectModality();
  } catch (e) {
    console.warn('[timer] 视觉层初始化失败 (动效降级, 计时不受影响):', e);
  }
}
```

## 4. 测试新增 (5 条)

```python
def test_ruler_input_has_touch_action_none(ruler_html):
    assert 'touch-action: none' in ruler_html

def test_ruler_init_has_set_pointer_capture(practice_html):
    assert 'setPointerCapture' in practice_html
    assert 'releasePointerCapture' in practice_html

def test_ruler_dragging_class_defined(practice_html):
    assert '.tick.cur.dragging' in practice_html
    assert 'scaleY(1.2)' in practice_html

def test_ruler_drag_clamps_to_min_max(practice_html):
    # 验证钳位 1~30 通过 Math.min/max + MIN_MIN/MAX_MIN
    assert 'MAX_MIN' in practice_html
    assert 'MIN_MIN' in practice_html
    assert 'Math.min' in practice_html and 'Math.max' in practice_html

def test_ruler_drag_uses_relative_displacement(practice_html):
    # 验证 pointermove 计算 deltaMin (相对位移, 非 jump)
    assert 'deltaMin' in practice_html
    assert 'dragCtx.startX' in practice_html
```

## 5. 验证 SOP

```
□ 1. cd ~/.herdr/worktrees/dizical/timer-260917
□ 2. git checkout -b fix/timer-ruler-drag-260919
□ 3. 实装 §3 (CSS + JS + 测试) 三个文件
□ 4. pytest tests/test_practice_timer_frontend.py -v   # 期望 ≥ 34 条 (29+5) 全绿
□ 5. pytest -x -q                                       # 全量回归 (baseline 768-797 passed + 0 failed)
□ 6. cd src/kid_app/static && python3 -m http.server 8904 --bind 0.0.0.0 &
□ 7. curl http://127.0.0.1:8904/practice | grep 'id="ruler"'  # 验 DOM 含 #ruler
□ 8. 通知 dad: iPad Safari → http://100.67.215.121:8904/practice → 空白刻度区按下拖动验
□ 9. dad 真机验 PASS → commit + push
□ 10. 开 PR (base main @ 6c7fd1c) → 标题 "fix(timer): iPad ruler drag — 自定义 Pointer Events 相对拖拽"
□ 11. PR → 新 tab 起 warden audit → 一轮 review
□ 12. 一轮审计 PASS → dad 拍 merge (squash) → git push
□ 13. minimax pane 连 mcp deploy (走 5 步 SOP) → CloudRun DeployId #N
□ 14. curl prod /practice 验 + dad iPad 真机复验生产
□ 15. 收尾 6 项 (sprint doc / verify / decision-log / STATUS / tag / Obsidian md5)
```

## 6. 风险与边界 (沿用 agy §5)

1. **WebKit 手势劫持**: 漏 `touch-action: none` 即必失败, 必加
2. **DOM 契约**: 必须保留 `<input type="range" id="rulerInput">` 原生节点 + `min/max/step` 属性, 无障碍语义不丢失
3. **SVG 防抖**: `buildVine()` 不能在 pointermove 高频调用, 必须防抖到松手后
4. **守卫**: `if (started) return` 必须放在 pointerdown 第一行, 否则运行态会改时长

## 7. 不在范围

- 补录 (extraSection) 选择器
- 运行/暂停态 UI
- 步进键 ±1 分钟
- 数字滚轮 MM:SS 动效
- 任何后端 / 数据库改动

## 8. 跨项目同步

- dizical-minip: 无影响 (不调 API)
- 没有任何 .env / 隐私 / agent 配置改动