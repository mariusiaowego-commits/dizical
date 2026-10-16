#!/usr/bin/env python3
"""D3 v2 结构性修复（review-grok/agy 实测 finding）。逐条断言，不匹配整体失败。"""
import pathlib, sys

P = pathlib.Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/dashboard-bottom-blocks-01-v2.html")
t = P.read_text()
R = []


def add(old, new, cnt, why):
    R.append((old, new, cnt, why))


# ── ① 误触级：开始 / 提前结束 只隔 5px（grok 实测） ──
add("""  .keypad-tactile {
    display: flex;
    gap: 6px;""",
    """  .keypad-tactile {
    display: flex;
    gap: 12px;   /* v2: 6 → 12，两钮不能连成一颗，实测间距 5px 会误触「提前结束」 */""",
    1, "拟物键间隙 6 → 12")
add("""  .pill-flat {
    display: flex;
    gap: 4px;""",
    """  .pill-flat {
    display: flex;
    gap: 8px;   /* v2: 4 → 8 */""",
    1, "胶囊键间隙 4 → 8")
add("""  .stage-frame[data-vp="iphone"]    { width: 440px; max-width: 100%; }""",
    """  .stage-frame[data-vp="iphone"]    { width: 440px; max-width: 100%; }

  /* v2: 440 视口下键帽留白收紧，避免两钮挤到贴边 */
  @media (max-width: 480px) {
    .keypad-tactile { gap: 10px; }
    .tactile-key { padding: 0 10px; font-size: 13.5px; }
    .pill-btn-core { padding: 0 11px; font-size: 13px; }
  }""",
    1, "440 视口收紧")

# ── ② transition: all ──
add("    transition: all 0.15s;\n  }\n  .p-btn.active {",
    "    transition: background 0.15s, color 0.15s, box-shadow 0.15s;\n  }\n  .p-btn.active {",
    1, "顶栏胶囊去 transition all")
add("    cursor: pointer;\n    transition: all 0.15s;\n  }\n  .pill-btn-core.primary-active {",
    "    cursor: pointer;\n    transition: background 0.15s, color 0.15s, box-shadow 0.15s;\n  }\n  .pill-btn-core.primary-active {",
    1, "扁平胶囊去 transition all")

# ── ③ 谱架钮补按下反馈（原来点击无任何自身反馈） ──
add("  .stand-btn-d1:hover { transform: translateY(-1px); }",
    """  .stand-btn-d1:hover { transform: translateY(-1px); }
  /* v2: 补按下反馈（原来只有 hover，触屏上完全无响应感） */
  .stand-btn-d1:active {
    transform: translateY(2px) scale(0.97);
    box-shadow: inset 0 2px 5px var(--dash-ink-a25);
  }""",
    1, "实体键 :active")
add("""    gap: 2px;
    cursor: pointer;
  }

  .stand-badge-tip {""",
    """    gap: 2px;
    cursor: pointer;
    transition: transform 0.12s, background 0.12s;
  }
  .stand-btn-pill:active { transform: scale(0.96); background: var(--dash-accent-line); }

  .stand-badge-tip {""",
    1, "胶囊钮 :active")

# ── ④ 提示条移进按钮自身附近（原来反馈跑到页面另一处诊断条） ──
add("""          <div class="stand-badge-tip">本期仅样式</div>""",
    """          <div class="stand-badge-tip" id="standTip">本期仅样式</div>""",
    1, "谱架提示加 id")
add("""    function onStandClick() {
      // 本期无功能，友好微提示
      const notice = document.getElementById('toastNotice');
      notice.innerHTML = '<strong>[谱架模式]</strong> 本期仅出 UI 样式，独立全屏谱架交互将在 Phase 3 单独立项。';
      setTimeout(() => {
        notice.innerHTML = '<span>提示：无需麦克风权限也能运行（默认以 82 BPM 模拟竹笛吹奏节奏震动）；点击「开启麦克风」可拾取现场真实声音。</span>';
      }, 3500);
    }""",
    """    let standTipTimer = null;
    function onStandClick() {
      // v2: 反馈就地显示在按钮下方（原来弹到页面另一头的诊断条，视线要跨屏）
      const tip = document.getElementById('standTip');
      tip.textContent = 'Phase 3 单独立项';
      tip.style.color = 'var(--dash-ink)';
      if (standTipTimer) clearTimeout(standTipTimer);
      standTipTimer = setTimeout(() => {
        tip.textContent = '本期仅样式';
        tip.style.color = '';
      }, 2500);
    }""",
    1, "谱架反馈就地化")

# ── ⑤ 麦克风指示灯非颜色单通道（色盲/灰度下要能区分） ──
add("""  .mic-indicator-dot.demo   { background: var(--dash-accent); }""",
    """  /* v2: 不能只靠颜色区分。demo = 虚线空心环，active = 实心 + 光晕 */
  .mic-indicator-dot.demo {
    background: transparent;
    border: 1.5px dashed var(--dash-accent);
  }""",
    1, "指示灯形状通道")

# ── ⑥ 扬声孔动效 gate 到计时中（原来一进页面 48 孔就在动） ──
add("""    function animLoop(timestamp) {
      let targetEnergy = 0.0;""",
    """    let animOn = false;   // v2: 只有计时中/麦克风开启才驱动，准备态静止

    function resetHoles() {
      holes.forEach(dot => {
        dot.style.transform = 'scale(1)';
        dot.classList.remove('vibrating');
      });
    }

    function animLoop(timestamp) {
      if (!animOn) {
        requestAnimationFrame(animLoop);
        return;
      }
      let targetEnergy = 0.0;""",
    1, "动效 gate")
add("""    function startTimer() {
      if (timerTicker) clearInterval(timerTicker);""",
    """    function startTimer() {
      animOn = true;
      if (timerTicker) clearInterval(timerTicker);""",
    1, "计时开始驱动动效")
add("""    function stopTimer() {
      if (timerTicker) { clearInterval(timerTicker); timerTicker = null; }
    }""",
    """    function stopTimer() {
      if (timerTicker) { clearInterval(timerTicker); timerTicker = null; }
      if (!isMicActive) { animOn = false; resetHoles(); }   // v2: 暂停/结束后回静止
    }""",
    1, "暂停回静止")
add("""    function updateStatusHeader() {""",
    """    function toggleBeatDemo() {
      if (isMicActive) return;   // 麦克风模式下由真实声音驱动
      animOn = !animOn;
      if (!animOn) resetHoles();
      document.getElementById('animBtn').textContent = '节拍示意：' + (animOn ? '开' : '关');
    }

    function updateStatusHeader() {""",
    1, "手动开关")

# ── ⑦ 诊断条按钮组（新增节拍示意图标开关） ──
add("""  .mic-toggle-btn {""",
    """  .diag-actions { display: flex; gap: 8px; }
  .mic-toggle-btn {""",
    1, "诊断条按钮组样式")
add("""        <button class="mic-toggle-btn" id="micBtn" onclick="toggleMicrophone()">开启麦克风</button>""",
    """        <div class="diag-actions">
          <button class="mic-toggle-btn" id="animBtn" onclick="toggleBeatDemo()">节拍示意：关</button>
          <button class="mic-toggle-btn" id="micBtn" onclick="toggleMicrophone()">开启麦克风</button>
        </div>""",
    1, "诊断条加示意开关")

# 麦克风开启/关闭同步驱动开关
add("""        isMicActive = true;
        btn.textContent = '关闭麦克风';""",
    """        isMicActive = true;
        animOn = true;   // v2: 真实拾音驱动，打开动效
        btn.textContent = '关闭麦克风';""",
    1, "麦克风开 → 动效开")
add("""        isMicActive = false;
        btn.textContent = '开启麦克风';
        dot.className = 'mic-indicator-dot demo';
        statusText.textContent = '驱动源：82 BPM 演示节奏包络 (自动降级安全模式)';
        return;""",
    """        isMicActive = false;
        btn.textContent = '开启麦克风';
        dot.className = 'mic-indicator-dot demo';
        statusText.textContent = '驱动源：82 BPM 演示节奏包络 (自动降级安全模式)';
        if (currentMode === 'prep') { animOn = false; resetHoles(); }
        document.getElementById('animBtn').textContent = '节拍示意：' + (animOn ? '开' : '关');
        return;""",
    1, "麦克风关 → 回静止")

# ── ⑧ 封面细线契约对齐 D1（55% → 10%） ──
add("    --dash-cover-line: rgba(255, 255, 255, 0.55);",
    "    --dash-cover-line: rgba(255, 255, 255, 0.10);", 1, "浅银封面线对齐 D1")
add("    --dash-cover-line: rgba(255, 248, 240, 0.45);",
    "    --dash-cover-line: rgba(255, 255, 255, 0.10);", 1, "深墨封面线对齐 D1")

fail = []
for old, new, cnt, why in R:
    got = t.count(old)
    if got != cnt:
        fail.append(f"  x {why}: 期望 {cnt}，实际 {got}")
        continue
    t = t.replace(old, new)
if fail:
    print("FAIL — 未写入：")
    print("\n".join(fail))
    sys.exit(1)
P.write_text(t)
print(f"OK: {P.name} 修复 {len(R)} 条")
for _, _, _, why in R:
    print(f"  v {why}")
