#!/usr/bin/env node
/**
 * 26093002 回归锁：音乐符号面板「绝不压盖输入框」几何自检。
 *
 * 做法：从 src/kid_app/static/js/music-symbols-panel.js 抽出真实的 reposition() 源码，
 * 在假 DOM 上跑网格（5 种视口 × 3 种输入框高度 × 全高度扫描 × 2 种面板自然高），
 * 断言面板矩形与输入框矩形永不相交。
 *
 * 负控：同一份源码把「限高」改回 legacy 的 `Math.max(120, spaceXxx)`（MIN_H 强撑版）
 * 必须出现压盖场景 —— 否则说明这个自检根本没在检东西。
 *
 * 退出码：0 = 通过（新版 0 压盖 且 负控能红）；1 = 失败。
 */
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', '..', 'src', 'kid_app', 'static', 'js', 'music-symbols-panel.js');
const src = fs.readFileSync(FILE, 'utf8');

function constOf(name) {
  const m = src.match(new RegExp('var ' + name + '\\s*=\\s*(\\d+)'));
  if (!m) throw new Error('找不到常量 ' + name);
  return +m[1];
}
const GAP = constOf('GAP'), EDGE = constOf('EDGE'), MAX_W = constOf('MAX_W');

function extractFn(name) {
  const start = src.indexOf('function ' + name + '(');
  if (start < 0) throw new Error('找不到函数 ' + name);
  const i = src.indexOf('{', start);
  let depth = 0;
  for (let j = i; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') { depth--; if (depth === 0) return src.slice(start, j + 1); }
  }
  throw new Error('括号不配平: ' + name);
}
const positionSrc = extractFn('reposition');

function legacySrc() {
  const replaced = positionSrc
    .replace(/var hUp = Math\.min\(panelH, Math\.max\(0, spaceAbove\)\);/,
             'var hUp = Math.max(120, spaceAbove);')
    .replace(/var hDown = Math\.min\(panelH, Math\.max\(0, spaceBelow\)\);/,
             'var hDown = Math.max(120, spaceBelow);');
  if (replaced === positionSrc) throw new Error('负控改写失败：没匹配到限高语句（实现变了？）');
  return replaced;
}
const LEGACY_FN_SRC = legacySrc();

function makeRunner(bodySource) {
  return function run(vis, r, naturalH) {
    const panel = {
      style: { maxHeight: '', overflowY: '', width: '', top: '', left: '' },
      offsetHeight: naturalH,
      offsetWidth: 300,
      classList: { contains: () => true }
    };
    const target = { getBoundingClientRect: () => r };
    const viewportBounds = () => vis;
    const fn = new Function('panel', 'target', 'viewportBounds', 'GAP', 'EDGE', 'MAX_W',
      'var reposition = ' + bodySource + '; return reposition;')(panel, target, viewportBounds, GAP, EDGE, MAX_W);
    fn();
    const cap = panel.style.maxHeight === '' ? Infinity : parseFloat(panel.style.maxHeight);
    return { top: parseFloat(panel.style.top), rendered: Math.min(naturalH, cap) };
  };
}

function overlaps(top, h, r) {
  return !(top + h <= r.top + 0.001 || top >= r.bottom - 0.001);
}

const viewports = [
  { name: 'iPhone 竖 440x956', height: 956, width: 440 },
  { name: 'iPad mini 竖 744x1133', height: 1133, width: 744 },
  { name: 'iPad 横 1133x744', height: 744, width: 1133 },
  { name: 'iPad 横+软键盘 ~344', height: 344, width: 1133 },
  { name: 'iPad 横+软键盘 ~244', height: 244, width: 1133 }
];
const inputHeights = [44, 90, 136];
const naturals = [240, 150];

function sweep(bodySource) {
  const run = makeRunner(bodySource);
  let total = 0, bad = 0, first = null;
  for (const vp of viewports) {
    const vis = { top: 0, bottom: vp.height, left: 0, right: vp.width, width: vp.width };
    for (const ih of inputHeights) {
      for (let rtop = 0; rtop + ih <= vp.height; rtop += 7) {
        const r = { top: rtop, bottom: rtop + ih, left: 12, right: 300 };
        for (const nh of naturals) {
          total++;
          const o = run(vis, r, nh);
          if (overlaps(o.top, o.rendered, r)) {
            bad++;
            if (!first) first = { vp: vp.name, inputTop: r.top, inputBottom: r.bottom, panelTop: o.top, panelHeight: o.rendered };
          }
        }
      }
    }
  }
  return { total, bad, first };
}

const cur = sweep(positionSrc);
const leg = sweep(LEGACY_FN_SRC);

console.log('当前实现: 场景 ' + cur.total + ' | 压盖输入框 ' + cur.bad);
if (cur.first) console.log('  首个压盖: ' + JSON.stringify(cur.first));
console.log('负控(legacy MIN_H 强撑): 场景 ' + leg.total + ' | 压盖输入框 ' + leg.bad);
if (leg.first) console.log('  首个压盖: ' + JSON.stringify(leg.first));

const ok = cur.bad === 0 && leg.bad > 0;
console.log(ok ? 'GEOM_OK' : 'GEOM_FAIL');
process.exit(ok ? 0 : 1);
