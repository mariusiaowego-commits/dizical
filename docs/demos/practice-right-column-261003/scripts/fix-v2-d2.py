#!/usr/bin/env python3
"""D2 v2 结构性修复（含 969 行假证据）。"""
import pathlib, sys

P = pathlib.Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/metronome-01-v2.html")
t = P.read_text()
R = []


def add(old, new, cnt, why):
    R.append((old, new, cnt, why))


# ── ① 假证据：累积漂移写死 0，还断言「恒等于 0」；阈值断言也不看实测值 ──
add("""        let maxDriftMs = 0.0;
        let cumulativeDriftMs = 0.0;
        let detailsSample = [];""",
    """        let maxDriftMs = 0.0;
        let cumulativeDriftMs = 0.0;
        let lastPeakSample = 0;   // v2: 末拍实测位置，用于算真实累积偏移
        let detailsSample = [];""",
    1, "记录末拍实测位置")
add("""          if (i > 0) {""",
    """          lastPeakSample = peakSample;

          if (i > 0) {""",
    1, "循环内记录")
add("""        const lastExpectedSec = (totalBeats - 1) * interval;
        cumulativeDriftMs = 0.0; // 硬件声卡采样排程下累积误差绝对为 0

        logEl.textContent += `[PASS] 60秒离线渲染完成！共排程 ${totalBeats} 拍\\n`
          + `[METRICS] 单拍理论间隔: ${(interval * 1000).toFixed(2)} ms\\n`
          + `[METRICS] 最大采样点偏差: ${maxDriftMs.toFixed(4)} ms (< 0.1ms)\\n`
          + `[METRICS] 60秒累积时钟漂移: 0.0000 ms (恒等于 0)\\n`
          + `[SAMPLES] 典型采样点核验:\\n`
          + detailsSample.join('\\n') + `\\n`
          + `[CONCLUSION] 评定: 硬件声卡采样级精准，零累积漂移 (PASS)`;""",
    """        const lastExpectedSec = (totalBeats - 1) * interval;
        // v2: 这里原来把 cumulativeDriftMs 写死 0，并对外断言「恒等于 0」「< 0.1ms」——
        //     属假证据（实测最大拍间偏差 0.4535ms 与文案自相矛盾）。
        //     现在按末拍实测位置算真实累积偏移，判定阈值也由实测值算。
        cumulativeDriftMs = Math.abs(lastPeakSample - Math.round(lastExpectedSec * sampleRate)) / sampleRate * 1000;
        const THRESHOLD_MS = 1.0;
        const PROBE_RESOLUTION_MS = 20 / sampleRate * 1000;   // 探针搜索窗 20 样本的量化上限
        const maxOk = maxDriftMs <= THRESHOLD_MS;
        const cumOk = cumulativeDriftMs <= THRESHOLD_MS;
        const verdict = (maxOk && cumOk) ? 'PASS' : 'FAIL';

        logEl.textContent += `[DONE] 60秒离线渲染完成，共排程 ${totalBeats} 拍\\n`
          + `[METRICS] 单拍理论间隔: ${(interval * 1000).toFixed(2)} ms\\n`
          + `[METRICS] 实测最大拍间偏差: ${maxDriftMs.toFixed(4)} ms (阈值 ${THRESHOLD_MS} ms → ${maxOk ? 'PASS' : 'FAIL'})\\n`
          + `[METRICS] 60秒末拍累积偏移: ${cumulativeDriftMs.toFixed(4)} ms (阈值 ${THRESHOLD_MS} ms → ${cumOk ? 'PASS' : 'FAIL'})\\n`
          + `[NOTE] 探针搜索窗 20 样本 = 量化上限 ${PROBE_RESOLUTION_MS.toFixed(4)} ms（偏差未超过此值即等于零误差）\\n`
          + `[SAMPLES] 典型采样点核验:\\n`
          + detailsSample.join('\\n') + `\\n`
          + `[CONCLUSION] 评定: ${verdict}（以下数值全部为实测输出，无写死项）`;""",
    1, "累积漂移改为实测 + 判定由值算")

# ── ② 自检面板塞在机身卡内（grok 实测把卡撑到 552px）→ 移出 ──
add("""      <!-- 精度自检面板 (Dad 验收硬证据) -->
      <div class="audit-panel">
        <div class="audit-header">
          <div class="audit-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
            路线 A 精度自检 (OfflineAudioContext 60s)
          </div>
          <button class="audit-run-btn" id="runAuditBtn" onclick="runAccuracyAudit()">开始自检</button>
        </div>
        <div class="audit-terminal" id="auditLog">点击「开始自检」以运行 60 秒声卡采样级精确度诊断...</div>
      </div>

    </div>
  </main>""",
    """    </div>

    <!-- 精度自检面板 (Dad 验收硬证据) — v2: 移出机身卡，避免把节拍器撑长（原 552px） -->
    <div class="audit-panel">
      <div class="audit-header">
        <div class="audit-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
          路线 A 精度自检 (OfflineAudioContext 60s)
        </div>
        <button class="audit-run-btn" id="runAuditBtn" onclick="runAccuracyAudit()">开始自检</button>
      </div>
      <div class="audit-terminal" id="auditLog">点击「开始自检」以运行 60 秒声卡采样级精确度诊断...</div>
    </div>
  </main>""",
    1, "自检面板移出机身卡")
add("""  .stage-frame {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    width: 100%;
    transition: width 0.3s ease;
  }""",
    """  .stage-frame {
    display: flex;
    flex-direction: column;   /* v2: 机身卡与自检面板上下排列（原来并排） */
    align-items: center;
    justify-content: flex-start;
    gap: 14px;
    width: 100%;
    transition: width 0.3s ease;
  }""",
    1, "舞台改纵向排列")
add("""  .audit-panel {
    background: var(--dash-panel);""",
    """  .audit-panel {
    width: 100%;
    max-width: 480px;   /* v2: 与机身卡同宽 */
    background: var(--dash-panel);""",
    1, "自检面板对齐卡宽")

# ── ③ BPM 量程与 D1 统一（D1 已改 40–200；D2 原 40–240） ──
add("    const MAX_BPM = 240;",
    "    const MAX_BPM = 200;   // v2: 与 D1 统一量程 40–200", 1, "量程统一")

# ── ④ 术语写死 bpm===82，不随指针走，且与 D1 用词不一致 ──
add("""    function getChineseTempoTerm(bpm) {
      if (bpm < 60) return '慢板 · 深情舒缓';
      if (bpm < 80) return '中板 · 优美抒情';
      if (bpm === 82) return '快板 · 萨丽哈指定★';
      if (bpm < 120) return '快板 · 欢快热烈';
      if (bpm < 160) return '小快板 · 颗粒吐音';
      return '急板 · 飞速技巧';
    }""",
    """    // v2: 术语只由 BPM 值域决定，阈值与 D1 tempoTerm 完全一致（原来写死 bpm===82，
    //     指针走了术语不变，且『小快板/快板』次序与值域相反）。萨丽哈标记交给预设芯片。
    function getChineseTempoTerm(bpm) {
      if (bpm <= 60) return '慢板 · 深情舒缓';
      if (bpm <= 88) return '中板 · 优美抒情';
      if (bpm <= 120) return '小快板 · 欢快活泼';
      if (bpm <= 160) return '快板 · 欢快热烈';
      return '急板 · 飞速技巧';
    }""",
    1, "术语跟指针走")

# ── ⑤ transition: all ──
add("    box-shadow: 0 4px 14px var(--dash-coral-glow);\n    transition: all 0.15s;",
    "    box-shadow: 0 4px 14px var(--dash-coral-glow);\n    transition: background 0.15s, box-shadow 0.15s, transform 0.15s;",
    1, "主按钮去 transition all")
add("    cursor: pointer;\n    text-align: center;\n    transition: all 0.15s;",
    "    cursor: pointer;\n    text-align: center;\n    transition: background 0.15s, color 0.15s, border-color 0.15s;",
    1, "预设芯片去 transition all")

# ── ⑥ 预设芯片触控目标（grok 实测 31px 高 / 间距 6px） ──
add("""  .preset-row {
    display: flex;
    gap: 6px;
    justify-content: center;
  }""",
    """  .preset-row {
    display: flex;
    gap: 8px;          /* v2: 6 → 8 */
    justify-content: center;
  }""",
    1, "预设行间距")
add("""    background: var(--dash-white);
    padding: 6px 4px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    color: var(--dash-ink);""",
    """    background: var(--dash-white);
    padding: 8px 6px;
    min-height: 40px;   /* v2: 实测只有 31px 高，触控目标不足 */
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
    color: var(--dash-ink);""",
    1, "预设芯片触控高")
add("""  .preset-chip.active {
    background: var(--dash-accent);""",
    """  @media (max-width: 480px) {
    .preset-chip { font-size: 11px; padding: 8px 3px; }
  }
  .preset-chip.active {
    background: var(--dash-accent);""",
    1, "440 预设收紧")

# ── ⑦ 文字字形 ▶ / ⏸ 换 SVG ──
add("""        <button class="primary-toggle-btn" id="mainToggleBtn" onclick="toggleMetronome()">
          <span id="toggleIcon">▶</span>
          <span id="toggleText">启动节拍器</span>
        </button>""",
    """        <button class="primary-toggle-btn" id="mainToggleBtn" onclick="toggleMetronome()">
          <span class="tg-icon tg-play" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="7 4 21 12 7 20 7 4"></polygon></svg>
          </span>
          <span class="tg-icon tg-pause" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4.5" height="16" rx="1.2"></rect><rect x="13.5" y="4" width="4.5" height="16" rx="1.2"></rect></svg>
          </span>
          <span id="toggleText">启动节拍器</span>
        </button>""",
    1, "启停图标 SVG 化")
add("""  .primary-toggle-btn:active {
    transform: scale(0.98);
  }""",
    """  .primary-toggle-btn:active {
    transform: scale(0.98);
  }
  /* v2: ▶ / ⏸ 文字字形换成矢量图形，由 .running 切换 */
  .primary-toggle-btn .tg-icon { display: inline-flex; align-items: center; }
  .primary-toggle-btn .tg-pause { display: none; }
  .primary-toggle-btn.running .tg-play { display: none; }
  .primary-toggle-btn.running .tg-pause { display: inline-flex; }""",
    1, "启停图标样式")
add("      const toggleIcon = document.getElementById('toggleIcon');\n", "", 1, "删 toggleIcon 引用")
add("        toggleIcon.textContent = '⏸';\n", "", 1, "删 ⏸ 写死")
add("        toggleIcon.textContent = '▶';\n", "", 1, "删 ▶ 写死")

# ── ⑧ 切前台只重置基准；注释别承诺补拍，且必须清灯 ──
add("""    // iOS 4条规避 4: 切前台防暴风连环补发
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && isPlaying && audioCtx) {
        audioCtx.resume();
        nextNoteTime = audioCtx.currentTime + 0.05; // 重置时钟基准
      }
    });""",
    """    // iOS 4条规避 4: 切回前台重置时钟基准，避免一次性补发积压的拍。
    // v2 说明：这里不承诺「补回后台漏掉的拍」——节拍器不补拍，只从当前时刻继续；
    //          但灯必须清一次，否则会停在后台最后一拍的亮态。
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && isPlaying && audioCtx) {
        audioCtx.resume();
        nextNoteTime = audioCtx.currentTime + 0.05;
        clearAllLeds();
      }
    });""",
    1, "切前台清灯 + 注释收紧")

# ── ⑨ 同心圆角：16 外 / 12 内边距 → 内层 4 ──
add("""    background: rgba(0,0,0,0.35);
    border-radius: 8px;""",
    """    background: rgba(0,0,0,0.35);
    border-radius: 4px;   /* v2: 与面板 16 - 内边距 12 同心 */""",
    1, "终端圆角同心")

# ── ⑩ 封面细线契约对齐 D1 ──
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
