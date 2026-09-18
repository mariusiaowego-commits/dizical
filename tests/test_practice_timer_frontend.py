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
