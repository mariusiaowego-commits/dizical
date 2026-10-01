/* 练习时长展示口径 B。与 src/kid_app/duration_fmt.py 同一套规则。
   0 → 空；<60 → N秒；整分钟 → N分；有余 → N分M秒。
   short 给月历格子：mm:ss，分钟可以超过 59。 */
(function (global) {
  function asInt(v) {
    if (v === undefined || v === null || v === '' || v === true || v === false) return null;
    var n = Number(v);
    if (!isFinite(n)) return null;
    return Math.trunc(n);
  }

  function fmt(sec) {
    var n = asInt(sec);
    if (n === null || n <= 0) return '';
    if (n < 60) return n + '秒';
    var minutes = Math.floor(n / 60);
    var rem = n % 60;
    if (rem === 0) return minutes + '分';
    return minutes + '分' + rem + '秒';
  }

  function short(sec) {
    var n = asInt(sec);
    if (n === null || n <= 0) return '';
    var minutes = Math.floor(n / 60);
    var rem = n % 60;
    var rs = rem < 10 ? '0' + rem : String(rem);
    return minutes + ':' + rs;
  }

  /* 秒是真值。缺省，或秒为 0 但分钟 > 0（未回填的 DEFAULT 0），用分钟 × 60。
     负数秒 = 坏数据 → 0（与 Python pick_seconds / _item_secs 同口径）。 */
  function pick(seconds, minutes) {
    var mins = asInt(minutes);
    if (mins === null || mins < 0) mins = 0;
    if (seconds === undefined || seconds === null || seconds === '') return mins * 60;
    var s = asInt(seconds);
    if (s === null) return mins * 60;
    if (s < 0) return 0;
    if (s === 0 && mins > 0) return mins * 60;
    return s;
  }

  global.DizicalDur = { fmt: fmt, short: short, pick: pick };
})(window);
