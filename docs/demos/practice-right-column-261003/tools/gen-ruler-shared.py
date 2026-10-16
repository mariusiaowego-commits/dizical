#!/usr/bin/env python3
"""从 src/kid_app/templates/practice.html 逐行切片，生成 docs/demos/.../shared/ruler-production.js
—— 只用「切片 + 头部状态/垫片 + 尾部 mount」，不改切片内容里的一个字符。

切片（行号含端点，1-indexed）：
  3993-4021  BUBBLE_*/VINE_*/TICKS 常量 + ticks/markerIdx
  4028-4038  buildVineDebounced
  4060-4078  ttStepMin / ttSetDuration
  4229-4500  glyphSupported → setRunningModality（气泡 / 卷草纹 / 尺子核心）
排除：计时数字滚轮（makeCounter/rollCol/ttRenderDigits/startSecFlicker…）—— 那是计时读数，不属于尺子；
      拖拽里引用到的 startSecFlicker/scheduleSecSettle 用空实现垫住。
"""
import re
from pathlib import Path

SRC = Path("/Users/mt16/dev/dizical/src/kid_app/templates/practice.html")
OUT = Path("/Users/mt16/dev/dizical/docs/demos/practice-right-column-261003/shared/ruler-production.js")
L = SRC.read_text(encoding="utf-8").split("\n")

def sl(a, b):
    return "\n".join(L[a - 1:b])

HEAD = r'''/* ============================================================================
 * 共享件 · 生产刻度尺（ruler + notes-bubbles + ruler-vine）
 * 来源：src/kid_app/templates/practice.html 逐行切片（行号见每段注释），几何/动效/参数一字未改。
 * 契约：demo 里的尺子必须用这一份，不许各卡自己重造（dad 要求「用我生产上的那套」）。
 * 改法：生产改了 → 先改 practice.html，再重跑 tools/gen-ruler-shared.py 重新切片。
 * 依赖：window.gsap 可选（没 gsap 时花纹/气泡不建，尺子本体照常可用）。
 * 用法：
 *   <link rel="stylesheet" href="shared/ruler-production.css">
 *   <script src="../vendor/gsap.min.js"></script>
 *   <script src="shared/ruler-production.js"></script>
 *   ... 生产同名 markup（.ruler-wrap > #ruler > #rulerRow + .notes-bubbles + #rulerInput）...
 *   RulerProduction.mount({ minutes: 10 });
 *   RulerProduction.mount({ root: document.querySelector('.card-x'), minutes: 10 });   // 多实例：限定作用域根
 * 注意：同一页面只应有一份尺子。**不托管尺子的页面不要引这两个文件**（引了就会把 .tick/.ruler 样式洒进来）；
 *      scripts/verify-demos.py 里有一条守卫：引了共享尺子的页面必须含尺子 markup，否则判 NG。
 * ========================================================================= */
(function () {
"use strict";

/* ── 生产里这些是页面级全局，这里收进模块，通过 API 改 ── */
let duration = 10;          // 当前选择时长（分钟）
let started  = false;       // 计时中/暂停 → true（拖拽守卫）
const S = { durMin: 10, running: false };   // buildVine 用 S.durMin 做纹样种子
const dragCtx = { active: false, startX: 0, startDur: 0, pointerId: null };
const hasGsap = () => (typeof window.gsap !== "undefined") && !!window.gsap;   // 同生产 4048
function setHint() {}                                                          // 同生产 4049

/* ── 作用域根（2026-10-06 加固）─────────────────────────────────────────────
 * 踩过的坑：本件原来用全局 ID（#ruler / #rulerInput / #metaVal）与 document 查询，
 * 于是「引了这份 CSS/JS 却没有尺子」的页面也会被样式命中（节拍器卡里长出刻度尺）。
 * 现在：mount 可传 root（默认 document，保持生产页单实例行为不变），
 * 切片里的 document.getElementById / document.querySelector(All) 统一改走 q / qAll / byId。
 * ─────────────────────────────────────────────────────────────────────── */
let rootEl = document;
const box  = () => (rootEl === document ? document : rootEl);
const q    = (sel) => box().querySelector(sel);
const qAll = (sel) => [].slice.call(box().querySelectorAll(sel));
const byId = (id) => box().querySelector("#" + id);
/* 拖拽里引用的秒位闪烁（属于计时读数，本件不搬）→ 空实现垫住 */
function startSecFlicker() {}
function scheduleSecSettle() {}

/* 计时读数（数字滚轮）也是卡片的职责，不属于尺子：
 * 切片里的 ttSetDuration 会调 ttRenderDigits(v*60) → 这里给空实现，卡片用
 * RulerProduction.onDurationChange = fn 接管（不接管也不影响尺子/红针/花纹）。 */
let _onDurationChange = null;
function ttRenderDigits(totalSec) { if (typeof _onDurationChange === "function") _onDurationChange(totalSec); }

/* ↓↓↓ VERBATIM-BEGIN 以下全部逐行摘自 practice.html，禁手改 ↓↓↓ */

/* practice.html:4022-4024 —— 秒位状态 / reducedMotion / counter 声明（reducedMotion 被尺子绘制用到） */
__SL0__

/* practice.html:3993-4021 —— 常量与状态 */
__SL1__

/* practice.html:4028-4038 —— buildVineDebounced */
__SL2__

/* practice.html:4060-4078 —— ttStepMin / ttSetDuration */
__SL3__

/* practice.html:4229-4500 —— glyphSupported → setRunningModality（气泡 / 卷草纹 / 尺子核心） */
__SL4__

/* ↑↑↑ VERBATIM-END ↑↑↑ */

/* ── 挂载：对应生产 ttInitTimer 里属于「尺子」的那部分（计时数字滚轮不搬） ── */
function mount(opts) {
  opts = opts || {};
  const rowId   = opts.rowId   || "rulerRow";
  const inputId = opts.inputId || "rulerInput";
  const rulerId = opts.rulerId || "ruler";
  rootEl = opts.root || document;            // 作用域根：多实例页面传进来，默认整页
  if (typeof opts.minutes === "number") { duration = opts.minutes; S.durMin = duration; }

  /* 生产 setSelectModality() 会写 #metaVal（计时读数文案）。卡片若没有这个元素，
   * 补一个隐藏占位，保证「尺子路径」不被读数层拖死（切片仍一字未改）。 */
  if (!byId("metaVal")) {
    const stub = document.createElement("span");
    stub.id = "metaVal"; stub.hidden = true;
    const host = byId(rulerId);
    (host && host.closest(".ruler-wrap") || host || box().body || document.body).appendChild(stub);
  }

  const ri = byId(inputId);
  const rulerEl = byId(rulerId);
  if (ri) {
    ri.value = String(duration);
    // a) 原生 input 事件保留 → 键盘/辅助技术兜底（生产 4088）
    ri.addEventListener("input", () => ttSetDuration(parseInt(ri.value, 10)));
    // b) Pointer Events 整段相对拖拽，不跳变（生产 4091-4134）
    ri.addEventListener("pointerdown", (e) => {
      if (started) return;
      if (e.button !== undefined && e.button !== 0) return;
      dragCtx.active = true; dragCtx.startX = e.clientX;
      dragCtx.startDur = duration; dragCtx.pointerId = e.pointerId;
      try { ri.setPointerCapture(e.pointerId); } catch (_) {}
      if (rulerEl) rulerEl.classList.add("is-dragging");
      startSecFlicker();
    });
    ri.addEventListener("pointermove", (e) => {
      if (!dragCtx.active) return;
      const w = rulerEl ? rulerEl.getBoundingClientRect().width : 0;
      if (w <= 0) return;
      const pxPerMin = w / (MAX_MIN - MIN_MIN);
      const deltaMin = Math.round((e.clientX - dragCtx.startX) / pxPerMin);
      const nextDur = Math.min(MAX_MIN, Math.max(MIN_MIN, dragCtx.startDur + deltaMin));
      if (nextDur !== duration) ttSetDuration(nextDur, true);
    });
    const onDragEnd = () => {
      if (!dragCtx.active) return;
      try { ri.releasePointerCapture(dragCtx.pointerId); } catch (_) {}
      if (rulerEl) rulerEl.classList.remove("is-dragging");
      const cur = q(".tick.cur");
      if (cur) {
        if (hasGsap()) gsap.fromTo(cur, { scaleY: 1.2 }, { scaleY: 1.0, duration: 0.24, ease: "back.out(2)", clearProps: "transform" });
        else cur.style.transform = "";
      }
      scheduleSecSettle(80);
      buildVineDebounced(150);
      dragCtx.active = false;
    };
    ri.addEventListener("pointerup", onDragEnd);
    ri.addEventListener("pointercancel", onDragEnd);
    window.addEventListener("blur", onDragEnd);
  }
  try {
    buildRuler(document.getElementById(rowId));
    if (hasGsap()) { buildBubbles(); buildVine(); }
    paintRulerSelect(duration);
    setSelectModality();
  } catch (err) {
    console.warn("[ruler] 视觉层初始化失败:", err);
  }
  return { ticks: ticks.length, vine: !!q(".ruler-vine"), bubbles: bubblePool.length };  // 计数按 mount 时的根
}

window.RulerProduction = {
  mount,
  emitBubbles, buildBubbles, stopBubbles, buildVine, bloomFlowersUpTo,
  revealVine, retractVine, celebrateVine, paintRulerSelect, paintRulerRunning,
  setMarker, pulseMarker, setSelectModality, setRunningModality, buildVineDebounced,
  step: ttStepMin,
  set onDurationChange(fn) { _onDurationChange = fn; },
  get duration() { return duration; },
  setDuration(v, skipVine) { ttSetDuration(v, skipVine); },
  setStarted(on) { started = !!on; S.running = !!on; },
  get tickCount() { return ticks.length; }
};
})();
'''

body = (HEAD
        .replace("__SL0__", sl(4022, 4024))
        .replace("__SL1__", sl(3993, 4021))
        .replace("__SL2__", sl(4028, 4038))
        .replace("__SL3__", sl(4060, 4078))
        .replace("__SL4__", sl(4229, 4500)))

# ── 作用域改写（只动「查询 DOM 的方式」，不动任何几何/动效/参数）──────────────
# 切片里的 document.getElementById/querySelector(All) → byId / q / qAll（受 mount 的 root 约束）
before_scoped = len(re.findall(r"document\.(?:getElementById|querySelectorAll|querySelector)\(", body))
body = re.sub(r"document\.querySelectorAll\(", "qAll(", body)
body = re.sub(r"document\.querySelector\(", "q(", body)
body = re.sub(r"document\.getElementById\(", "byId(", body)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(body, encoding="utf-8")

# 自检 1：切片里的函数名是否都在（防切片边界错）
need = ["buildBubbles", "emitBubbles", "buildVine", "bloomFlowersUpTo", "revealVine",
        "retractVine", "celebrateVine", "buildRuler", "setMarker", "paintRulerSelect",
        "setRunningModality", "ttSetDuration", "buildVineDebounced", "VINE_FLOWERS"]
missing = [n for n in need if not re.search(rf"(?:function|const|let|var)\s+{n}\b", body)]

# 自检 2：作用域改写是否彻底（不许残留 document.getElementById/querySelector*）
leftover = re.findall(r"document\.(?:getElementById|querySelectorAll|querySelector)\(", body)

print(f"WROTE {OUT}  ({len(body)} 字符, {body.count(chr(10))+1} 行)")
print(f"缺失函数: {missing or '无'}")
print(f"未替换占位: {re.findall(r'__SL[0-9]__', body) or '无'}")
print(f"作用域改写: 改写 {before_scoped} 处 / 残留 {leftover or '无'}")
print(f"作用域根: {'rootEl 已声明' if 'let rootEl = document;' in body else '缺 rootEl!'} / "
      f"mount root 参数: {'有' if 'opts.root' in body else '缺!'}")
