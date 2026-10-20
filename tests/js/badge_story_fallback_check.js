#!/usr/bin/env node
/*
 * Rework 1 自测 (2026-10-20, feat/badge-manual-award-261020 / PR #381)
 *
 * 复现的 bug:
 *   achievements.description 的默认占位是 "无" —— 在 JS 里 "无" 是 truthy,
 *   旧写法 storyText(d.story || d.storyShort) 会短路成 storyText("无"),
 *   把非空的 story_short 吞成 "故事准备中"。
 *
 * 本脚本不起浏览器、不引依赖:
 *   ① 用 vm + 最小 DOM stub 加载 src/kid_app/static/js/badge-ccg.js, 拿到 DizicalCCG;
 *   ② 直接断言 DizicalCCG.storyText(primary, secondary) 的四种组合;
 *   ③ 通过 DizicalCCG.mountCard 真渲染 focus 态与 wall 态, 断卡背 markup 里出现 story_short
 *      而不是 "故事准备中"。
 *
 * 跑法: node tests/js/badge_story_fallback_check.js
 * 退出码 0 = 全绿, 1 = 有断言失败 (红行会打印到 stderr)。
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const JS_PATH = path.join(__dirname, "..", "..", "src", "kid_app", "static", "js", "badge-ccg.js");

const STORY_SHORT = "指尖一抹，滑过竹林的风。";
const FALLBACK = "故事准备中";

let failures = 0;
function check(label, actual, expected) {
  const ok = actual === expected;
  if (!ok) {
    failures += 1;
    process.stderr.write(
      "FAIL " + label + "\n  expected: " + JSON.stringify(expected) +
      "\n  actual  : " + JSON.stringify(actual) + "\n"
    );
  } else {
    process.stdout.write("ok   " + label + " → " + JSON.stringify(actual) + "\n");
  }
}
function checkIncludes(label, haystack, needle) {
  const ok = typeof haystack === "string" && haystack.indexOf(needle) !== -1;
  if (!ok) {
    failures += 1;
    process.stderr.write("FAIL " + label + "\n  missing: " + JSON.stringify(needle) + "\n");
  } else {
    process.stdout.write("ok   " + label + " (含 " + JSON.stringify(needle) + ")\n");
  }
}

/* ─── 最小 DOM stub (只覆盖 badge-ccg.js 加载 + mountCard 用到的 API) ─── */
function makeEl(tag) {
  const el = {
    tagName: String(tag || "div").toUpperCase(),
    className: "",
    innerHTML: "",
    textContent: "",
    parentNode: null,
    attrs: {},
    children: [],
    _listeners: {},
    style: { setProperty: function () {}, display: "", removeProperty: function () {} },
    dataset: {},
    classList: {
      add: function () {},
      remove: function () {},
      toggle: function () {},
      contains: function () { return false; },
    },
    setAttribute: function (k, v) { this.attrs[k] = String(v); },
    getAttribute: function (k) {
      return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null;
    },
    setAttributeNS: function (_ns, k, v) { this.attrs[k] = String(v); },
    removeAttribute: function (k) { delete this.attrs[k]; },
    appendChild: function (c) { c.parentNode = this; this.children.push(c); return c; },
    insertBefore: function (c) { c.parentNode = this; this.children.unshift(c); return c; },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; },
    addEventListener: function (t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); },
    removeEventListener: function () {},
    closest: function () { return null; },
    getBoundingClientRect: function () { return { left: 0, top: 0, width: 200, height: 280 }; },
    dispatchEvent: function () { return true; },
    contains: function () { return false; },
  };
  Object.defineProperty(el, "firstChild", { get: function () { return this.children[0] || null; } });
  Object.defineProperty(el, "firstElementChild", {
    get: function () { return this.children[0] || null; },
  });
  return el;
}

const documentStub = {
  body: makeEl("body"),
  documentElement: makeEl("html"),
  getElementById: function () { return null; },
  createElement: function (t) { return makeEl(t); },
  createElementNS: function (_ns, t) { return makeEl(t); },
  querySelector: function () { return null; },
  querySelectorAll: function () { return []; },
  addEventListener: function () {},
  removeEventListener: function () {},
};
documentStub.body.getAttribute = function () { return null; };

const windowStub = {
  document: documentStub,
  addEventListener: function () {},
  removeEventListener: function () {},
  matchMedia: function () {
    return {
      matches: false,
      addEventListener: function () {},
      removeListener: function () {},
    };
  },
  requestAnimationFrame: function () { return 1; },
  cancelAnimationFrame: function () {},
  setTimeout: function (fn) { return 0; },
  clearTimeout: function () {},
  performance: { now: function () { return 0; } },
  navigator: { userAgent: "node-selfcheck" },
  devicePixelRatio: 1,
  CustomEvent: function CustomEvent(type, opts) { this.type = type; this.detail = (opts || {}).detail; },
  dispatchEvent: function () { return true; },
};
windowStub.window = windowStub;
windowStub.globalThis = windowStub;

/* ─── 加载 badge-ccg.js ─── */
const src = fs.readFileSync(JS_PATH, "utf8");
const sandbox = windowStub;
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: "badge-ccg.js" });

const CCG = sandbox.DizicalCCG;
if (!CCG || typeof CCG.storyText !== "function") {
  process.stderr.write("FAIL 未加载到 DizicalCCG.storyText (导出缺失?)\n");
  process.exit(1);
}

/* ─── ① storyText 双参兜底 ─── */
process.stdout.write("\n[1] storyText(primary, secondary) 组合断言\n");
check("desc='无' + story_short 非空 → story_short", CCG.storyText("无", STORY_SHORT), STORY_SHORT);
check("desc 非空 + story_short 非空 → desc", CCG.storyText("长典故", STORY_SHORT), "长典故");
check("desc='无' + story_short='无' → 兜底", CCG.storyText("无", "无"), FALLBACK);
check("两者空串 → 兜底", CCG.storyText("", ""), FALLBACK);
check("两者 undefined → 兜底", CCG.storyText(undefined, undefined), FALLBACK);
check("desc 空白 + story_short 非空 → story_short", CCG.storyText("   ", STORY_SHORT), STORY_SHORT);
check("单参旧用法向后兼容 (desc='无')", CCG.storyText("无"), FALLBACK);

/* ─── ② 真渲染: mountCard 的两种 mode 都带出 story_short ─── */
process.stdout.write("\n[2] mountCard 实渲染 (focus / wall)\n");
const BASE = {
  id: "tech_hua_yin",
  name: "流云滑指灵",
  tag: "技巧",
  image: "/static/badges/tech_hua_yin_v1.png",
  cond: "三次圆润滑音",
  story: "无",          // DB 默认占位 —— bug 的触发条件
  story_short: STORY_SHORT,
  date: "2026-10-20",
  stars: 3,
  no: 63,
  card_theme: "azure",
};

["focus", "wall"].forEach(function (mode) {
  const stage = makeEl("div");
  try {
    CCG.mountCard(stage, "holo", BASE, { mode: mode });
  } catch (e) {
    failures += 1;
    process.stderr.write("FAIL mountCard(" + mode + ") 抛错: " + e.message + "\n");
    return;
  }
  checkIncludes(mode + " 态卡背含 story_short", stage.innerHTML, STORY_SHORT);
  if (stage.innerHTML.indexOf(FALLBACK) !== -1) {
    failures += 1;
    process.stderr.write("FAIL " + mode + " 态卡背仍出现「" + FALLBACK + "」(故事被吞)\n");
  } else {
    process.stdout.write("ok   " + mode + " 态卡背无「" + FALLBACK + "」\n");
  }
});

/* story_short 也缺失时才允许兜底 */
const bareStage = makeEl("div");
CCG.mountCard(bareStage, "holo", Object.assign({}, BASE, { story: "无", story_short: "" }),
  { mode: "focus" });
checkIncludes("两者皆空 → 卡背显示兜底文案", bareStage.innerHTML, FALLBACK);

process.stdout.write("\n" + (failures === 0 ? "ALL GREEN" : failures + " FAILURE(S)") + "\n");
process.exit(failures === 0 ? 0 : 1);
