/*
 * shared/hollow-digits.js — 空心 geometric monoline 数字引擎（从 practice-duration-card-01-v3.html 抽出）
 *
 * 来源：D6 时长卡的 HOLLOW_DIGITS（SVG monoline 线框字形，1.8px 描边 / 无填充）。
 * 用途：D1 仪表盘的计时读数改用它（dad 2610102107：计时数字要用 card-practice-duration 里的数字）。
 * 约定：42 单位行高（viewBox 高 52，字形占 2..50），字符宽 32、冒号 12，字距 5、冒号后 4。
 *
 * API（挂 window.HollowDigits）：
 *   HollowDigits.html(str)          -> { html, totalWidth }
 *   HollowDigits.render(svgEl, str) -> 写 viewBox + innerHTML，并设置 aria-label
 *   HollowDigits.viewBoxFor(str)    -> '0 0 W 52'
 */
(function () {
  'use strict';

  var HOLLOW_DIGITS = {
    '0': '<rect x="2" y="2" width="28" height="48" rx="10" stroke="currentColor" stroke-width="1.8" / fill="none"/><line x1="8" y1="42" x2="24" y2="10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" / fill="none"/>',
    '1': '<path d="M 9,12 L 16,2 L 16,50 M 7,50 L 25,50" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" / fill="none"/>',
    '2': '<path d="M 3,14 C 3,-2.2 29,-2.2 29,15 C 29,26 4,37 2,50 L 30,50" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" / fill="none"/>',
    '3': '<path d="M 4,8 C 7,-0.8 28,-0.8 28,14 C 28,23 18,26 13,26 C 20,26 28,29 28,38 C 28,52.5 7,52.5 3,44" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" / fill="none"/>',
    '4': '<path d="M 22,2 L 4,34 L 28,34 M 22,2 L 22,50" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" / fill="none"/>',
    '5': '<path d="M 28,2 L 4,2 L 4,22 C 7,19 16,19 22,22 C 28,25 29,32 28,39 C 27,51 14,51 4,50" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" / fill="none"/>',
    '6': '<path d="M 24,2 C 12,2 2,14 2,36 A 14 14 0 1 0 16,22 A 14 14 0 0 0 2.8,32" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" / fill="none"/>',
    '7': '<path d="M 2,2 L 30,2 L 10,50 M 14,26 L 24,26" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" / fill="none"/>',
    '8': '<rect x="3" y="2" width="26" height="23" rx="8" stroke="currentColor" stroke-width="1.8" / fill="none"/><rect x="2" y="25" width="28" height="25" rx="9" stroke="currentColor" stroke-width="1.8" / fill="none"/>',
    '9': '<path d="M 8,50 C 20,50 30,38 30,16 A 14 14 0 1 0 16,30 A 14 14 0 0 0 29.2,20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" / fill="none"/>',
    ':': '<circle cx="6" cy="18" r="2.2" fill="currentColor" /><circle cx="6" cy="34" r="2.2" fill="currentColor" />'
  };

  var CHAR_W = 32;
  var COLON_W = 12;
  var TRACK = 5;       // 字距
  var COLON_TRACK = 4; // 冒号后字距
  var LINE_H = 52;     // viewBox 高（字形 2..50，上下各留 2）

  function html(str) {
    str = String(str == null ? '' : str);
    var x = 0;
    var out = '';
    for (var i = 0; i < str.length; i++) {
      var ch = str.charAt(i);
      var glyph = HOLLOW_DIGITS[ch];
      if (!glyph) continue; // 未定义字符跳过（不静默画错形）
      var w = (ch === ':') ? COLON_W : CHAR_W;
      out += '<g transform="translate(' + x + ',0)" data-char="' + ch + '" fill="none">' + glyph + '</g>';
      x += w + (ch === ':' ? COLON_TRACK : TRACK);
    }
    return { html: out, totalWidth: x > 0 ? x - TRACK : 0 };
  }

  function viewBoxFor(str) {
    var res = html(str);
    return '0 0 ' + res.totalWidth + ' ' + LINE_H;
  }

  function render(svgEl, str) {
    if (!svgEl) return null;
    var res = html(str);
    svgEl.setAttribute('viewBox', '0 0 ' + res.totalWidth + ' ' + LINE_H);
    svgEl.setAttribute('preserveAspectRatio', 'xMinYMid meet');
    svgEl.setAttribute('aria-label', String(str));
    svgEl.innerHTML = res.html;
    return res;
  }

  window.HollowDigits = {
    MAP: HOLLOW_DIGITS,
    LINE_H: LINE_H,
    CHAR_W: CHAR_W,
    COLON_W: COLON_W,
    html: html,
    render: render,
    viewBoxFor: viewBoxFor
  };
})();
