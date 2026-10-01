/* 负数秒 = 坏数据：duration-fmt.js 的 pick 必须返回 0，不得回退 minutes*60。
   与 Python `pick_seconds` / `_item_secs` 同口径（sprint 26100101 F4b）。
   用法: node tests/js/duration_pick_negative_check.js
   退出码 0 = 全过, 1 = 有失败。 */
const path = require('path');
const fs = require('fs');

// duration-fmt.js 是 IIFE, 以 `window` 为宿主 → 先造一个假 window
const src = fs.readFileSync(
  path.join(__dirname, '..', '..', 'src', 'kid_app', 'static', 'js', 'duration-fmt.js'),
  'utf8'
);
const win = {};
new Function('window', src)(win);
const D = win.DizicalDur;

const cases = [
  // [seconds, minutes, expected, why]
  [-5, 3, 0, '负数秒 = 坏数据 → 0（本条是负控目标：旧实现给 180）'],
  [-1, 0, 0, '负数秒 + 分钟 0 → 0'],
  [0, 3, 180, '秒为 0 且分钟 > 0 = 未回填 → 回退 minutes*60'],
  [0, 0, 0, '双方 0 → 0'],
  [90, 2, 90, '有真值秒 → 用秒'],
  [45, 0, 45, '秒 < 1 分钟且分钟 0 → 保留秒'],
  [undefined, 3, 180, '缺省 → 回退'],
  [null, 3, 180, 'null → 回退'],
  ['', 3, 180, '空串 → 回退'],
  ['-5', 3, 0, '字符串负数也要判负'],
];

let failed = 0;
for (const [sec, min, want, why] of cases) {
  const got = D.pick(sec, min);
  const ok = got === want;
  if (!ok) failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  pick(${JSON.stringify(sec)}, ${min}) = ${got}  期望 ${want}   ${why}`);
}
console.log(`\n${cases.length - failed}/${cases.length} passed`);
process.exit(failed === 0 ? 0 : 1);
