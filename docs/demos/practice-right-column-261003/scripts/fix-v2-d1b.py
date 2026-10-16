#!/usr/bin/env python3
"""D1 v2 修复（sprint 26100301）。每条替换断言出现次数，不匹配整体失败、不写文件。
对应 review-grok.md / review-agy.md 的实测 finding。
"""
import pathlib

P = pathlib.Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/dashboard-skin-01-v2.html")
t = P.read_text()
R = []

def add(old, new, cnt, why):
    R.append((old, new, cnt, why))

add(
    '  /* ── default skin. 组件里只引用这些变量。\n     第二套（换肤示范，默认不启用）：把下面整段注释打开，并给 <html data-skin="ink">。\n  :root[data-skin="ink"] {',
    '  /* ── default skin. 组件里只引用这些变量。 */\n  /* 第二套皮肤（深墨）：由顶栏「浅银/深墨」切换器写 <html data-skin="ink"> 生效 */\n  :root[data-skin="ink"] {',
    1, "ink 皮肤从注释里放出来",
)
add('}\n  */\n  :root {', '}\n  :root {', 1, "去掉注释收尾 */")
add(
    '  .dash {\n    container: dash / size;\n    width: min(100%, var(--vp-w));\n    height: 100%;\n    max-height: var(--vp-h);',
    '  .dash {\n    container: dash / size;\n    /* v2: 收成便携仪器比例。右栏宽度上限 420px；\n       --vp-w/--vp-h 只是演示视口框，不再让机身被拉成宽网页 */\n    width: min(100%, 420px);\n    height: auto;\n    max-height: 100%;',
    1, "机身宽度锁 420px、高度自适应",
)
add('    display: flex; justify-content: center; align-items: stretch;',
    '    display: flex; justify-content: center; align-items: flex-start;',
    1, "frame 顶部对齐，卡片按内容收拢")
add('    border-radius: 28px;\n    padding: 10px 14px 8px;',
    '    border-radius: 22px;   /* v2: 外壳 36 - 内边距 14 = 22，同心 */\n    padding: 10px 14px 8px;',
    1, "深色屏圆角 28 → 22（同心）")
add('    padding: 3px; border-radius: 16px;', '    padding: 3px; border-radius: 15px;', 1, "封面外框圆角 16 → 15")
add('    --dash-cover-line: rgba(255, 255, 255, 0.55);', '    --dash-cover-line: rgba(255, 255, 255, 0.10);', 1, "封面细线：纯白 10%（浅银）")
add('    --dash-cover-line: rgba(255, 248, 240, 0.45);', '    --dash-cover-line: rgba(255, 255, 255, 0.10);', 1, "封面细线：纯白 10%（深墨）")
add('    flex: 0 0 auto; width: 58px; height: 58px; border-radius: 50%;',
    '    flex: 0 0 auto; width: 44px; height: 44px; border-radius: 50%;   /* v2: 两套 ± 统一 44px */',
    1, "银面 ± 58 → 44")
add('    font-size: 26px; font-weight: 500; line-height: 1;', '    font-size: 22px; font-weight: 500; line-height: 1;', 1, "银面 ± 字号 26 → 22")
add('.round.mini { width: 32px; height: 32px; font-size: 18px;',
    '.round.mini { width: 44px; height: 44px; font-size: 20px;   /* v2: 与银面同一尺寸 */',
    1, "进度条 ± 32 → 44")
add('    display: flex; align-items: center; gap: 8px; width: 100%; max-width: 460px; margin-top: 2px;',
    '    display: flex; align-items: center; gap: 12px; width: 100%; max-width: 460px; margin-top: 2px;',
    1, "尺子与 ± 间距 8 → 12")
add('    .round { width: 48px; height: 48px; font-size: 22px; }',
    '    .round { width: 44px; height: 44px; font-size: 20px; }', 1, "窄视口银面 ± 48 → 44")
add('    .round.mini { width: 28px; height: 28px; font-size: 16px; }',
    '    .round.mini { width: 44px; height: 44px; font-size: 18px; }', 1, "窄视口进度条 ± 28 → 44")
add('    height: 4.6em; font-size: 12.5px; overflow: hidden; cursor: pointer; position: relative;',
    '    height: 84px;   /* v2: 4.6em → 84px 固定可读高度 */\n    font-size: 12.5px; overflow: hidden; cursor: pointer; position: relative;',
    1, "滚动窗高度改固定 84px")
add('    -webkit-mask-image: linear-gradient(to bottom, transparent, black 18%, black 82%, transparent);\n    mask-image: linear-gradient(to bottom, transparent, black 18%, black 82%, transparent);',
    '    -webkit-mask-image: linear-gradient(to bottom, transparent, black 8px, black calc(100% - 8px), transparent);\n    mask-image: linear-gradient(to bottom, transparent, black 8px, black calc(100% - 8px), transparent);',
    1, "遮罩 18% → 8px，不再吃掉可读高度")
add('    .lyric-col { grid-column: 1 / -1; height: 58px; }',
    '    .lyric-col { grid-column: 1 / -1; height: 112px; }', 1, "窄视口滚动窗 58 → 112px")
add('            <div class="lyric-kicker">老师要求</div>',
    '            <div class="lyric-kicker">老师要求 <span class="lyric-state" id="lyricState">滚动中</span></div>',
    1, "加「滚动中/已暂停」静态提示")
add('  .lyric-kicker { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: var(--dash-panel-dim); }',
    '  .lyric-kicker { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: var(--dash-panel-dim); }\n  /* v2: 暂停不能只有动效变化，补静态字 */\n  .lyric-state { font-weight: 600; letter-spacing: 0; color: var(--dash-panel-dim); opacity: 0.7; }',
    1, "静态提示样式")
add("  document.getElementById('lyricView').addEventListener('click', function () {\n    this.classList.toggle('is-paused');\n  });",
    "  document.getElementById('lyricView').addEventListener('click', function () {\n    var paused = this.classList.toggle('is-paused');\n    document.getElementById('lyricState').textContent = paused ? '已暂停' : '滚动中';\n  });",
    1, "点击切换同步静态字")
add(
    '  .hole {\n    width: 7px; height: 7px; border-radius: 50%; background: var(--dash-hole);\n    transform-origin: center;\n    animation: holePulse var(--dash-beat) ease-in-out infinite;\n    animation-delay: calc(var(--i) * var(--dash-beat) / 8);\n  }\n  @keyframes holePulse {\n    0%, 100% { transform: scale(1); }\n    45% { transform: scale(0.55); }\n  }',
    '  .hole {\n    width: 7px; height: 7px; border-radius: 50%; background: var(--dash-hole);\n    transform-origin: center;\n  }\n  /* v2: 只在计时中跳动；准备态静止（原来一进页面 48 个孔就在跳） */\n  .dash[data-mode="run"] .hole {\n    animation: holePulse var(--dash-beat) ease-in-out infinite;\n    animation-delay: calc(var(--i) * var(--dash-beat) / 8);\n  }\n  @keyframes holePulse {\n    0%, 100% { transform: scale(1); }\n    45% { transform: scale(0.9); }   /* v2: 0.55 → 0.9 */\n  }',
    1, "孔动效 gate 到计时中 + 振幅 0.55→0.9")
add(
    '        <div class="stand" role="group" aria-label="谱架模式">\n          <button type="button" class="stand-btn">谱架</button>\n          <button type="button" class="stand-btn accent">模式</button>\n        </div>',
    '        <div class="stand" role="group" aria-label="谱架模式入口">\n          <button type="button" class="stand-btn accent" id="standBtn" aria-disabled="true"\n                  title="谱架模式：本期只出样式，点击无效果">谱架模式</button>\n          <span class="stand-note">本期仅样式</span>\n        </div>',
    1, "「谱架/模式」两个残钮 → 单个「谱架模式」")
add('  .stand-btn {\n    width: 74px; min-height: 48px; border-radius: 16px; border: 0;',
    '  .stand-btn {\n    min-width: 74px; padding: 0 12px; white-space: nowrap; min-height: 48px; border-radius: 16px; border: 0;',
    1, "谱架钮宽度自适应文字")
add('  .stand-btn.accent {\n    background: linear-gradient(180deg, var(--dash-accent), var(--dash-coral));\n    color: var(--dash-white);\n  }',
    '  .stand-btn.accent {\n    background: linear-gradient(180deg, var(--dash-accent), var(--dash-coral));\n    color: var(--dash-white);\n  }\n  .stand-btn:active { transform: scale(0.96); }\n  .stand-note { font-size: 10px; color: var(--dash-muted); text-align: center; }',
    1, "谱架钮按下反馈 + 说明字")
add('          <div>今日 42分</div>',
    '          <div id="todayTotal" data-placeholder="1" title="占位：生产接今日累计练习时长">今日 42分</div>',
    1, "今日累计槽位标注为占位")
add('  var BPM_MIN = 40, BPM_MAX = 150;',
    '  /* v2: 量程统一到 40–200（与 D2 同值）；竹笛双吐快板可到 200 */\n  var BPM_MIN = 40, BPM_MAX = 200;',
    1, "BPM 上限 150 → 200")
add('aria-valuemin="40" aria-valuemax="150" aria-valuenow="82"',
    'aria-valuemin="40" aria-valuemax="200" aria-valuenow="82"', 1, "knob aria 上限同步")
add(
    "  function setBpm(next) {\n    bpm = Math.round(Math.min(BPM_MAX, Math.max(BPM_MIN, next)));\n    document.getElementById('bpmRead').textContent = '♩ = ' + bpm;",
    "  /* v2: 术语由 BPM 值算出来，不再写死「快板」和指针位置打架 */\n  function tempoTerm(b) {\n    if (b <= 60) return '慢板';\n    if (b <= 88) return '中板';\n    if (b <= 120) return '小快板';\n    if (b <= 160) return '快板';\n    return '急板';\n  }\n  function setBpm(next) {\n    bpm = Math.round(Math.min(BPM_MAX, Math.max(BPM_MIN, next)));\n    document.getElementById('bpmRead').textContent = '♩ = ' + bpm + ' ' + tempoTerm(bpm);",
    1, "加 tempoTerm，读数带术语")
add('    <div class="seg" id="modeSeg">',
    '    <div class="seg" id="skinSeg">\n      <button type="button" data-skin="light" class="is-on">浅银</button>\n      <button type="button" data-skin="ink">深墨</button>\n    </div>\n    <div class="seg" id="modeSeg">',
    1, "顶栏加皮肤切换器")
add("  function paintClock() {",
    "  document.getElementById('skinSeg').addEventListener('click', function (e) {\n    var b = e.target.closest('button');\n    if (!b) return;\n    if (b.dataset.skin === 'ink') document.documentElement.dataset.skin = 'ink';\n    else document.documentElement.removeAttribute('data-skin');\n    document.querySelectorAll('#skinSeg button').forEach(function (x) { x.classList.toggle('is-on', x === b); });\n  });\n\n  function paintClock() {",
    1, "皮肤切换器绑定")

fail = []
for old, new, cnt, why in R:
    got = t.count(old)
    if got != cnt:
        fail.append(f"  x {why}: 期望 {cnt} 次，实际 {got}")
        continue
    t = t.replace(old, new)
if fail:
    print("FAIL - 未写入任何文件:")
    print("\n".join(fail))
    raise SystemExit(1)
P.write_text(t)
print(f"OK: 写入 {P.name}，共 {len(R)} 条修复")
for _, _, _, why in R:
    print(f"  v {why}")
