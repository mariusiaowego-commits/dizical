"""practice 页计时器前端契约测试 (sprint 26091801)

这些断言锁的是「页面必须长成什么样」和「打卡链路不许被改坏」两件事:
  · 新计时器元素在位 (滚轮数字/刻度尺/步进键/花纹层/气泡层) —— 旧 picker 与方案 B 倒计时 overlay 必须已移除
  · 打卡链路 (POST /api/log + practice_at CST + behavior_log + 速度/内容必填) 逐字未变
  · 计时三态标签语义 (开始→暂停→继续)、提前结束弹窗、放弃回选择态
  · GSAP 本地优先 + CDN 兜底; 花纹/气泡常量与定稿 demo 一致
反面断言 (NOT CONTAINS) 与正面断言成对出现: 只写正面会让「页面里同时留着旧 UI」这种半途改动照样通过。
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRACTICE = ROOT / "src" / "kid_app" / "templates" / "practice.html"
GSAP_VENDOR = ROOT / "src" / "kid_app" / "static" / "vendor" / "gsap.min.js"


@pytest.fixture(scope="module")
def html() -> str:
    return PRACTICE.read_text(encoding="utf-8")


# ── 1. 新计时器元素在位 ──────────────────────────────────────────────
@pytest.mark.parametrize("element_id", [
    "ttCounter",       # 滚轮数字根容器
    "ruler",           # 刻度尺 (花纹 SVG 挂载点)
    "rulerRow",        # 60 个刻度格
    "rulerInput",      # 透明 range 拖拽层
    "ttStepMinus",     # −1 分钟
    "ttStepPlus",      # +1 分钟
    "metaVal",         # 状态胶囊 (N 分钟 / 总计 N 分钟 / 已暂停)
    "startBtn",        # 开始 / 暂停 / 继续
    "finishEarlyBtn",  # 提前结束
    "confirmArea",     # 打卡成功提示区 (submitPractice 依赖)
    "confirmMins",     # 打卡分钟数载体
])
def test_new_timer_element_present(html, element_id):
    assert f'id="{element_id}"' in html, f"计时器缺少元素 #{element_id}"


# ── 2. 旧 UI 必须已移除 (半途改动会被这条抓住) ────────────────────────
@pytest.mark.parametrize("legacy", [
    'id="timerKnobEl"',       # dial knob
    'id="timerTicks"',
    'id="timerWheel"',        # activity wheel (主计时器)
    'id="timerValue"',
    'id="timerCountdown"',    # 方案 B 倒计时 overlay
    "function enterRunningUI",
    "function exitRunningUI",
    "function updateRunningProgress",
    ".timer-countdown",
])
def test_legacy_timer_ui_removed(html, legacy):
    assert legacy not in html, f"旧计时器残留: {legacy}"


def test_main_picker_instantiation_removed_but_extra_kept(html):
    """主计时器的 picker 实例必须删掉; 补录 (extraSection) 的必须留着"""
    assert "timerPicker = createDialKnob" not in html, "主计时器还在创建 dial knob"
    assert "timerWheel = createActivityWheel" not in html, "主计时器还在创建 activity wheel"
    assert "extraPicker = createDialKnob" in html, "补录的 dial knob 被误删"
    assert "extraWheel = createActivityWheel" in html, "补录的 activity wheel 被误删"


# ── 3. 打卡链路契约 (改动计时器最容易顺手改坏的部分) ──────────────────
def test_submit_practice_contract_intact(html):
    assert "fetch('/api/log'" in html, "打卡端点被改动"
    assert "practice_at: nowCstLocal()" in html, "practice_at (CST 无 Z) 传递丢失"
    assert "behavior_log: [{enter_time: enterTime" in html, "behavior_log.enter_time 丢失"
    assert "date: todayDate, item: selectedItem, item_id: selectedItemId," in html
    assert "minutes: finalMins" in html
    assert "body.tempo_note = noteEl.dataset.note" in html
    assert "body.tempo_bpm = parseInt(bpmEl.value) || 80" in html
    assert "body.content = contentEl.value.trim()" in html
    # 内容必填 + 防重放
    assert "请填写本次练习内容后再打卡" in html
    assert "if (submitting) return;" in html


def test_start_button_gate_unchanged(html):
    """开始按钮三条件: 选科目 + 内容非空 + bpm 40~150"""
    assert "if (!selectedItemId) { btn.disabled = true; return; }" in html
    assert "if (!content) { btn.disabled = true; return; }" in html
    assert "if (bpm < 40 || bpm > 150) { btn.disabled = true; return; }" in html


# ── 4. 三态语义与结束流程 ────────────────────────────────────────────
def test_timer_state_labels(html):
    assert "document.getElementById('startBtn').textContent = '暂停';" in html
    assert "document.getElementById('startBtn').textContent = '继续';" in html
    assert "document.getElementById('startBtn').textContent = '开始';" in html
    assert "ttPauseLabel(true);" in html, "暂停时状态胶囊未切「已暂停」"
    assert "ttPauseLabel(false);" in html, "继续时状态胶囊未复位"
    assert "function finishEarly()" in html and "function abortFinishEarly()" in html
    assert "function confirmFinishEarly()" in html


def test_running_tick_drives_visuals(html):
    """每秒 tick 必须同时驱动: 数字 + 尺子进度 + 花纹 + 脉冲 + 气泡"""
    assert "pulseMarker();" in html
    assert "emitBubbles();" in html
    assert "paintRulerRunning(p)" in html
    assert "revealVine(p)" in html
    assert "celebrateVine();" in html, "归零时花纹收尾动效丢失"


# ── 5. 花纹 / 气泡常量 = dad 定稿值 ──────────────────────────────────
def test_vine_config_is_dad_final(html):
    assert "const VINE_CFG={density:0.90,depth:19,chord:16,random:1.0,flower:1.5};" in html, \
        "花纹参数不是 dad 定稿的 0.90/19/16/1.00/1.5"
    assert "const VINE_RAIL_Y=0.6" in html
    assert "const TICKS=60, SLOTS_PER_MIN=2, MIN_MIN=1, MAX_MIN=30;" in html


def test_six_flower_species_and_bmp_symbols(html):
    for sp in ["five", "cross", "bell", "tulip", "star", "berry"]:
        assert f"{sp}:" in html, f"缺少花种 {sp}"
    # 气泡符号只允许 BMP 基本乐符 (补充区缺字形会渲染成白框)。
    # 只锁符号集常量那一行 —— 页面注释里为了说明原因会提到补充区字符, 不能一概禁
    line = [l for l in html.splitlines() if l.strip().startswith("const BUBBLE_SYMBOLS=")]
    assert line, "找不到气泡符号集常量"
    code = line[0].split("//")[0]          # 只看代码部分, 注释里为说明原因会提到补充区字符
    assert code.strip().startswith(
        "const BUBBLE_SYMBOLS=['♪','♫','♩','♬','♭','♯','♮'];"), "符号集不是纯 BMP 基本乐符"
    assert "\U0001D11E" not in code and "\U0001D13D" not in code, "符号集混入补充区字符 (会出白框)"
    # 气泡元素类名必须与 CSS 的 .tt-bubble 同名 (生产页已有 .bubble 类)
    assert "b.className='tt-bubble'" in html


# ── 6. GSAP 自托管 ───────────────────────────────────────────────────
def test_gsap_self_hosted_first_with_cdn_fallback(html):
    assert GSAP_VENDOR.exists(), "本地 GSAP 缺失 src/kid_app/static/vendor/gsap.min.js"
    assert GSAP_VENDOR.stat().st_size > 50_000, "本地 GSAP 体积异常 (不像完整构建)"
    assert '<script src="/static/vendor/gsap.min.js"></script>' in html, "页面未优先加载本地 GSAP"
    assert "if(!window.gsap)" in html, "缺少 CDN 兜底"


def test_timer_module_is_state_bridge_not_second_source_of_truth(html):
    """S 必须是只读桥 (getter/setter 指向生产变量), 不许另起状态"""
    assert "get durMin(){ return duration; }" in html
    assert "get sec(){ return elapsed; }" in html
    assert "get running(){ return timerRunning; }" in html


def test_inline_page_script_no_js_syntax_error(html):
    """sprint 26091901: inline page script 不能有 JS 语法错 (上轮 brace 错位导致整个 IIFE 抛 'Unexpected token }' → 计时器全部丢渲染).
       静态提取 <script>...</script> 块, 替换 Jinja 变量, 用 node --check 验语法.
    """
    import re, subprocess, tempfile, os
    scripts = re.findall(r'<script>(.+?)</script>', html, re.DOTALL)
    # 找含 ttInitTimer 的内联 script (page-level)
    page_scripts = [s for s in scripts if 'ttInitTimer' in s or 'onDragEnd' in s]
    assert page_scripts, "找不到 inline page script (ttInitTimer/onDragEnd), sprint 24091901 可能未实装"
    # 替换 Jinja 变量 {{xxx}} → null, 防止 node 把它当语法错
    for i, s in enumerate(page_scripts):
        cleaned = re.sub(r'\{\{[^}]+\}\}', 'null', s)
        # 写到临时文件, node --check
        with tempfile.NamedTemporaryFile(suffix='.js', delete=False, mode='w') as f:
            f.write(cleaned)
            tmp = f.name
        try:
            r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True, timeout=15)
            assert r.returncode == 0, f"inline page script #{i} 有 JS 语法错:\n{r.stderr}"
        finally:
            os.unlink(tmp)


# ── 7. sprint 26091901: iPad ruler 自定义 Pointer Events 拖拽 ─────────────
def test_ruler_input_touch_action_none(html):
    """iPad WebKit 上手必须用 touch-action:none 拦截上下滚动 (否则 pointercancel 频繁触发)
       P1-2 fix: 用 .ruler-input{} 块内切片检查, 防注释/老代码残留子串干扰
    """
    idx = html.find(".ruler-input{")
    assert idx > 0, "缺 .ruler-input 块"
    block = html[idx:idx + 500]
    assert "touch-action:none" in block, \
        ".ruler-input 块内必须 touch-action:none (防注释残留干扰)"


def test_timer_card_and_step_btn_touch_action_manipulation(html):
    """sprint 26091901 follow-up: iPad Safari 双击 zoom 误操作
       CSS touch-action:manipulation 在 #timerCard 与 .step-btn 上, 消 300ms 点击延迟 + 禁双击 zoom
    """
    # #timerCard 卡片容器
    timer_block_idx = html.find("#timerCard{")
    assert timer_block_idx > 0
    block = html[timer_block_idx:timer_block_idx + 700]
    assert "touch-action:manipulation" in block, \
        "#timerCard 必须 touch-action:manipulation (消双击 zoom + 300ms 延迟)"
    # .step-btn 步进按钮
    step_block_idx = html.find(".step-btn{")
    assert step_block_idx > 0
    step_block = html[step_block_idx:step_block_idx + 800]
    assert "touch-action:manipulation" in step_block, \
        ".step-btn 必须 touch-action:manipulation"
    assert "user-select:none" in step_block, \
        ".step-btn 必须 user-select:none (防狂点误选 +/- 文本)"


def test_ruler_input_touch_action_none_not_regressed(html):
    """sprint 26091901 follow-up: .ruler-input 仍保持 touch-action:none (sprint 26091901 实装, 不被 #timerCard 容器覆盖)"""
    # 检查 .ruler-input 块内仍有 touch-action:none
    ruler_block_idx = html.find(".ruler-input{")
    assert ruler_block_idx > 0
    ruler_block = html[ruler_block_idx:ruler_block_idx + 500]
    assert "touch-action:none" in ruler_block, \
        ".ruler-input 仍必须 touch-action:none (sprint 26091901 拖拽功能)"


def test_ruler_pointer_capture_used(html):
    """pointerdown 必须调用 setPointerCapture, pointerup 必须 releasePointerCapture
       P1-2 fix: 老 dial knob (extraSection, sprint 26091604) 也有 setPointerCapture 残留, 用 sprint 26091901 marker 之后限定 ruler 区域
    """
    # 找 sprint 26091901 自定义 Pointer Events 事件块 marker (line ~3133)
    pdown = html.find("sprint 26091901: 自定义 Pointer Events — 整段尺子按下相对拖拽")
    assert pdown > 0, "找不到 sprint 26091901 自定义 Pointer Events 事件块, 拖拽事件未实装"
    # 在 ruler 区域内 (sprint 26091901 ttInitTimer 块) 检查 setPointerCapture / releasePointerCapture
    ruler_block = html[pdown:pdown + 4000]  # 整段 ttInitTimer 块
    assert "setPointerCapture" in ruler_block, "sprint 26091901 ruler 缺 setPointerCapture"
    assert "releasePointerCapture" in ruler_block, "sprint 26091901 ruler 缺 releasePointerCapture"


def test_tick_cur_dragging_class(html):
    """拖拽中红针微高亮: .ruler.is-dragging .tick.cur (P1 修法: 容器挂类, 跨分钟不掉)"""
    assert ".ruler.is-dragging .tick.cur" in html, \
        "缺 .ruler.is-dragging .tick.cur (P1 修法: 容器挂类, paintRulerSelect 切格时不会丢)"
    # 必须三件套绑在该选择器块内 (不是散落)
    block_idx = html.find(".ruler.is-dragging .tick.cur")
    assert block_idx > 0
    block = html[block_idx:block_idx + 220]
    assert "scaleY(1.2)" in block, ".ruler.is-dragging .tick.cur 缺 scaleY(1.2)"
    assert "brightness(1.15)" in block, ".ruler.is-dragging .tick.cur 缺 brightness(1.15)"
    assert "transition:none" in block, ".ruler.is-dragging .tick.cur 缺 transition:none (60fps 跟手要禁用过渡)"


def test_ruler_drag_toggles_container_is_dragging(html):
    """P1: pointerdown 给 #ruler 加 .is-dragging, onDragEnd 移除"""
    # pointerdown 加类 (用精确 marker, line ~3133 区别于常量块 3068)
    pdown = html.find("sprint 26091901: 自定义 Pointer Events — 整段尺子按下相对拖拽")
    pdown_start = html.find("ri.addEventListener('pointerdown'", pdown)
    assert pdown_start > 0
    handler = html[pdown_start:pdown_start + 800]
    assert "rulerEl.classList.add('is-dragging')" in handler, \
        "pointerdown 必须给 #ruler 加 .is-dragging"
    # onDragEnd 移除类
    pend = html.find("const onDragEnd =")
    handler_end = html[pend:pend + 700]
    assert "rulerEl.classList.remove('is-dragging')" in handler_end, \
        "onDragEnd 必须移除 #ruler .is-dragging"


def test_ruler_drag_uses_relative_displacement(html):
    """pointermove 用相对位移 (dragCtx.startX + deltaMin), 绝不能 jump-to-click-position"""
    assert "dragCtx.startX" in html, "pointermove 必须用 dragCtx.startX 起点"
    assert "dragCtx.startDur" in html, "pointermove 必须以按下时 duration 为基准"
    assert "deltaMin" in html, "缺 deltaMin 相对位移变量"


def test_ruler_drag_clamps_to_1_30_minutes(html):
    """钳位 1~30 分钟, 永不出现 0 分钟 (与 ttSetDuration 钳位 + MIN_MIN/MAX_MIN 一致)"""
    # ttSetDuration 现有钳位
    assert "Math.min(MAX_MIN, Math.max(MIN_MIN" in html, "ttSetDuration 必须钳位"
    # pointermove 二次钳位
    assert "Math.min(MAX_MIN, Math.max(MIN_MIN, dragCtx.startDur" in html, \
        "pointermove 必须钳位, 否则允许越界"
    # MIN_MIN=1 保证不会出现 0
    assert "MIN_MIN=1" in html and "MAX_MIN=30" in html, \
        "边界常量必须锁在 1~30 (与打卡链路 finalMins>=1 兼容)"


def test_ruler_drag_running_guard(html):
    """计时中/暂停态 (started===true) 在 pointerdown 第一行必须守卫返回, 不允许改时长
       P1-2 fix: 必须找到 pointerdown handler 的"真正第一行", 不是注释或无关子串
    """
    # 找 sprint 26091901 自定义 Pointer Events 的事件块 marker (line ~3133, 区别于常量块 3068)
    pdown = html.find("sprint 26091901: 自定义 Pointer Events — 整段尺子按下相对拖拽")
    assert pdown > 0, "找不到 sprint 26091901 自定义 Pointer Events 事件块, 拖拽事件未实装"
    # 找 pointerdown handler 起点
    pdown_start = html.find("ri.addEventListener('pointerdown'", pdown)
    assert pdown_start > 0
    handler_start = pdown_start + html[pdown_start:pdown_start + 200].find("(e) =>") + 6
    # 跳过 opening paren, 取 handler 函数体内**前 100 字符** (去掉注释干扰)
    handler_body = html[handler_start:handler_start + 100]
    assert "if (started) return" in handler_body, \
        f"pointerdown handler 第一行必须以 started 守卫开头 (防计时中改时长), 实测 handler 前 100 字符: {handler_body!r}"


def test_ruler_drag_pointermove_has_skipvine(html):
    """pointermove 期间调 ttSetDuration 必须 skipVine=true, 防 SVG 高频重画掉帧"""
    pmove = html.find("ri.addEventListener('pointermove'")
    assert pmove > 0
    handler = html[pmove:pmove + 600]
    assert "ttSetDuration(nextDur, true)" in handler, \
        "pointermove 必须 skipVine=true (高频拖拽期间 SVG 防抖)"


def test_ruler_drag_release_has_spring_back(html):
    """pointerup 必须有 GSAP spring 回弹 (scaleY 1.2 → 1.0, back.out)"""
    pend = html.find("const onDragEnd =")
    assert pend > 0
    handler = html[pend:pend + 700]
    assert "back.out(2)" in handler, "松手缺 back.out(2) spring 回弹"
    assert "scaleY: 1.2" in handler and "scaleY: 1.0" in handler, \
        "松手缺 scaleY 1.2 → 1.0 回弹过渡"


def test_ruler_drag_buildvine_debounced(html):
    """buildVineDebounced 必须存在, 拖拽期间防抖重建花纹, 避免每帧重画"""
    assert "function buildVineDebounced" in html, "缺 buildVineDebounced 防抖函数"
    assert "buildVineDebounced(150)" in html, "松手后必须触发 buildVineDebounced(150)"
