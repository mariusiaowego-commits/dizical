/* audit-contrast.js — 配色对比度审计（WCAG 2.1 相对亮度）
 *
 * 用法：打开任一 demo 页 → 浏览器控制台粘贴本文件全部内容 → 执行
 *   await auditContrast()            两种皮肤都测（自动调页面自己的皮肤按钮）
 *   auditContrast('ink')             只测深墨
 *   auditContrast('light', true)     打印全部条目（不只不合格项）
 *
 * 判定阈值（WCAG AA）：
 *   正文          >= 4.5   （< 24px 且 < 700 字重）
 *   大字号/粗体    >= 3.0   （>= 24px 或 >= 18.66px 且字重 >= 700）
 *   纯装饰/无文字元素不参与
 *
 * 背景解析：从元素向上收集各层 background-color，按「根 → 叶」顺序做 alpha 合成；
 * 遇到 background-image（渐变/图片）无法解析 → 计入 unknown，单独列出，不假冒通过。
 */
(function () {
  function parseColor(s) {
    var m = String(s).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    var p = m[1].split(/[,/\s]+/).filter(Boolean).map(parseFloat);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  }
  function comp(fg, bg) {
    var a = fg[3];
    return [fg[0] * a + bg[0] * (1 - a), fg[1] * a + bg[1] * (1 - a), fg[2] * a + bg[2] * (1 - a), 1];
  }
  function lum(c) {
    var f = function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  }
  function ratio(a, b) {
    var l1 = lum(a), l2 = lum(b), hi = Math.max(l1, l2), lo = Math.min(l1, l2);
    return (hi + 0.05) / (lo + 0.05);
  }
  function effBg(el) {
    var chain = [], n = el, hasImage = false;
    while (n && n.nodeType === 1) {
      var st = getComputedStyle(n);
      if (n !== el && st.backgroundImage && st.backgroundImage !== 'none') hasImage = true;
      var c = parseColor(st.backgroundColor);
      if (c && c[3] > 0) chain.push(c);
      n = n.parentElement;
    }
    var acc = [255, 255, 255, 1];
    for (var i = chain.length - 1; i >= 0; i--) acc = comp(chain[i], acc);
    return { color: acc, hasImage: hasImage };
  }
  function path(el) {
    var out = [], n = el;
    while (n && n.nodeType === 1 && out.length < 4) {
      out.unshift(n.className ? '.' + String(n.className).trim().split(/\s+/).join('.') : n.tagName.toLowerCase());
      n = n.parentElement;
    }
    return out.join(' > ');
  }
  function scan(skin) {
    var fails = [], unknown = [], min = { ratio: Infinity }, checked = 0;
    var nodes = document.querySelectorAll('body *');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var text = '';
      for (var k = 0; k < el.childNodes.length; k++) {
        if (el.childNodes[k].nodeType === 3) text += el.childNodes[k].textContent;
      }
      text = text.trim();
      if (text.length < 2) continue;
      var st = getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) < 0.15) continue;
      if (el.getBoundingClientRect().width === 0) continue;
      var fg = parseColor(st.color);
      if (!fg) continue;
      var bg = effBg(el);
      var fgc = comp(fg, bg.color);
      var r = ratio(fgc, bg.color);
      var fs = parseFloat(st.fontSize), fw = parseInt(st.fontWeight, 10) || 400;
      var need = (fs >= 24 || (fs >= 18.66 && fw >= 700)) ? 3.0 : 4.5;
      var row = {
        sel: path(el), text: text.slice(0, 18), ratio: +r.toFixed(2), need: need,
        color: st.color, bg: 'rgb(' + bg.color.slice(0, 3).map(Math.round).join(',') + ')',
        fs: fs, fw: fw
      };
      if (bg.hasImage) { unknown.push(row); continue; }
      checked++;
      if (r < min.ratio) min = row;
      if (r < need) fails.push(row);
    }
    return { skin: skin || 'light', checked: checked, fails: fails, unknown: unknown, min: min };
  }
  function setSkin(skin) {
    var btn = null;
    document.querySelectorAll('button').forEach(function (b) {
      var t = b.textContent.trim();
      if (skin === 'ink' && (t === '深墨' || t === 'ink' || /dark/i.test(t))) btn = b;
      if (skin === 'light' && (t === '浅银' || t === 'light')) btn = b;
    });
    if (btn) { btn.click(); return true; }
    if (skin === 'ink') document.documentElement.dataset.skin = 'ink';
    else delete document.documentElement.dataset.skin;
    return false;
  }
  window.auditContrast = async function (which, verbose) {
    var settle = function () { return new Promise(function (r) { setTimeout(r, 450); }); };
    var skins = which ? [which] : ['light', 'ink'];
    var out = [];
    for (var i = 0; i < skins.length; i++) {
      var s = skins[i];
      setSkin(s);
      await settle();   // 关键：切肤会触发 color transition，不等就会量到过渡起始值（假红）
      var r = scan(s);
      out.push(r);
      console.log('=== 皮肤 ' + s + ' ===  检查 ' + r.checked + ' 处文字, 不合格 ' + r.fails.length +
        ', 无法解析背景 ' + r.unknown.length + ', 最低对比度 ' + r.min.ratio + ' (' + (r.min.sel || '-') + ')');
      r.fails.sort(function (a, b) { return a.ratio - b.ratio; }).forEach(function (f) {
        console.log('  NG ' + f.ratio + ' < ' + f.need + '  ' + f.sel + '  « ' + f.text + ' »  color ' + f.color + ' on ' + f.bg + '  ' + f.fs + 'px/' + f.fw);
      });
      if (verbose) r.unknown.forEach(function (u) { console.log('  ? ' + u.sel + '（背景含渐变/图片，未判定）'); });
    }
    return out;
  };
  console.log('audit-contrast 已装载。执行 auditContrast() 测两种皮肤。');
})();
