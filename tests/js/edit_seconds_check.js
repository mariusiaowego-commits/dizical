#!/usr/bin/env node
/**
 * sprint 26100101 F3 锁：编辑弹窗保存时不得把「秒」抹掉。
 *
 * 改前：PUT body 写死 `duration_seconds: duration * 60` → 2 分钟（实际 1分30秒）的
 * 记录只改个音符，秒就从 90 变成 120（30 秒凭空长出来，且 PUT 校验 [1,86400] 也不会拦）。
 *
 * 做法：从 src/kid_app/templates/practice.html 抽出真实的三个纯函数，在 node 里跑用例；
 * 并断言 saveSessionEdit 真的调 buildEditPutBody（防"抽了函数却不接线"）。
 *
 * 负控：把 computeEditSeconds 换成 legacy 的 `Math.max(60, durNow * 60)` → 必须有用例红。
 *
 * 退出码 0 = 全过（新版全绿 且 负控能红）；1 = 失败。
 */
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', '..', 'src', 'kid_app', 'templates', 'practice.html');
const src = fs.readFileSync(FILE, 'utf8');

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

const fnSrc = ['clampEditMinutes', 'computeEditSeconds', 'buildEditPutBody'].map(extractFn).join('\n');

// 纯函数里没有 DOM 依赖，直接在一个函数体里 eval
function makeApi(override) {
  const code = (override || fnSrc) + '\nreturn {clampEditMinutes, computeEditSeconds, buildEditPutBody};';
  return new Function(code)();
}

const api = makeApi();

// [durNow, origMins, origSecs, 期望 minutes, 期望 seconds, 说明]
const CASES = [
  [2, 2, 90, 2, 90, '只改音符/内容：分钟没动 → 秒必须保住 90'],
  [3, 2, 90, 3, 180, '分钟被改 → 按新分钟重算'],
  [1, 1, null, 1, 60, '原记录没秒（老数据）→ 分钟×60'],
  [1, 1, 0, 1, 60, '原秒为 0 → 分钟×60'],
  [2, 2, '90', 2, 90, '原秒是字符串（getAttribute）→ 仍按 90 复用'],
  [1, 1, 10, 1, 10, '<60 秒也必须如实保住（后端下限是 1，不是 60）'],
  [1, 1, 45, 1, 45, '45 秒 → 45（warden 审计抓的回归点）'],
  [1, 1, 59, 1, 59, '59 秒 → 59'],
  [0, 2, 90, 1, 60, '分钟填 0 → 钳到 1（PUT 下限）'],
  [-1, 2, 90, 1, 60, '负分钟 → 钳到 1'],
  [2000, 1, 60, 1440, 86400, '超上限 → 分钟 1440 / 秒 86400 自洽'],
  [null, 2, 90, 1, 60, 'null → 1 分钟'],
  [undefined, 2, 90, 1, 60, 'undefined → 1 分钟'],
  ['abc', 2, 90, 1, 60, '非数字 → 1 分钟'],
  [2.7, 2.7, 90, 2, 90, '浮点 → parseInt 截断后与原分钟相等 → 保秒'],
];

let failed = 0;

function runCases(api, label) {
  let bad = 0;
  for (const [durNow, om, os, wantMin, wantSec, why] of CASES) {
    const body = api.buildEditPutBody('♪', 80, 'x', durNow, om, os, null);
    const okRange = body.duration_minutes >= 1 && body.duration_minutes <= 1440 &&
                    body.duration_seconds >= 1 && body.duration_seconds <= 86400;
    const ok = body.duration_minutes === wantMin && body.duration_seconds === wantSec && okRange;
    if (!ok) bad++;
    console.log(`${ok ? 'PASS' : 'FAIL'}  [${label}] (${JSON.stringify(durNow)},${om},${os}) →`
      + ` min:${body.duration_minutes} sec:${body.duration_seconds}  期望 min:${wantMin} sec:${wantSec}   ${why}`);
  }
  return bad;
}

failed += runCases(api, 'now');

// 契约：saveSessionEdit 必须真的调 buildEditPutBody（抽了不用 = 假锁）
if (!/const putBody = buildEditPutBody\(/.test(src)) {
  console.log('FAIL  saveSessionEdit 没有调用 buildEditPutBody（抽了函数却没接线）');
  failed++;
} else {
  console.log('PASS  saveSessionEdit 调用 buildEditPutBody');
}
// 且不得留下 duration * 60 的老写法
if (/duration_seconds:\s*duration\s*\*\s*60/.test(src)) {
  console.log('FAIL  仍存在 `duration_seconds: duration * 60` 老写法');
  failed++;
} else {
  console.log('PASS  无 `duration_seconds: duration * 60` 老写法');
}

// 负控：legacy 实现必须有用例红，否则自检没在检东西
const legacy = fnSrc.replace(
  /var out = \(isFinite\(om\) && isFinite\(os\) && d === om && os > 0\) \? os : d \* 60;/,
  'var out = d * 60;'
);
if (legacy === fnSrc) throw new Error('负控改写失败：没匹配到秒归一语句（实现变了？）');
console.log('\n--- 负控（legacy: 秒永远 = 分钟×60）---');
const legacyBad = runCases(makeApi(legacy), 'legacy');
if (legacyBad === 0) {
  console.log('FAIL  负控没红 → 这个自检是假的');
  failed++;
} else {
  console.log(`PASS  负控红了 ${legacyBad} 条（说明锁真的在检）`);
}

console.log(`\n${failed === 0 ? 'OK' : 'FAILED'}: now 用例 ${CASES.length} 条, 失败合计 ${failed}`);
process.exit(failed === 0 ? 0 : 1);
