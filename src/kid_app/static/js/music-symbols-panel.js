/* 常用音乐符号面板（老师要求输入框随焦点取用）。
 *
 * 用法：
 *   DizicalSymbols.attach(inputEl)               // 单个输入框：聚焦即弹面板
 *   DizicalSymbols.attachAll(rootEl, selector)   // 批量；root 默认 document
 *   DizicalSymbols.attach(inputEl, {trigger:true}) // 额外在框右上角挂「符号」开关
 *
 * 硬约束（dad 2026-09-30）：面板打开时**不得遮挡正在输入的输入框**。
 *   下方空间够 → 贴下方；不够 → 翻上方；两边都不够 → 面板自身限高内滚。
 *   滚动 / 旋屏 / 软键盘（visualViewport）变化时持续重定位。
 *
 * 插入方式：插入到光标处（iPad 上系统剪贴板两条路径都不可用，故不用复制）。
 */
(function (global) {
  'use strict';

  /* 只收 BMP 基本区字符 + 词条：补充平面字符（𝄐 𝄞 等）在真机上是白框。 */
  var GROUPS = [
    { name: '记谱', items: ['♩', '♪', '♫', '♬', '♯', '♭', '♮', '=', '.', '·', '-', '0', '|', '‖', ':'] },
    { name: '技巧', items: ['tr', 'T', 'K', 'V', '↗', '↘', '◐', '○'] },
    { name: '力度与结构', items: ['p', 'mf', 'f', 'pp', 'ff', 'cresc.', 'dim.', 'D.C.', 'D.S.', 'Fine', '4/4', '3/4', '2/4', '6/8'] },
    { name: '词条', word: true, items: ['打音', '叠音', '赠音', '历音', '花舌', '气震音', '超吹', '长音', '渐快', '渐慢', '自由速度', '散板', '循环换气'] }
  ];

  var GAP = 8;          // 面板与输入框的间距
  var EDGE = 6;         // 面板与视口边缘的安全边距
  var MAX_W = 336;      // 面板宽度上限
  var MIN_H = 120;      // 限高时的最小可滚高度

  var panel = null;
  var panelBody = null;
  var target = null;
  var toastEl = null;
  var toastTimer = null;

  function el(tag, cls, text) {
    var d = document.createElement(tag);
    if (cls) d.className = cls;
    if (text != null) d.textContent = text;
    return d;
  }

  function buildPanel() {
    panel = el('div', 'msp-panel');
    panel.setAttribute('role', 'group');
    panel.setAttribute('aria-label', '常用音乐符号');
    panelBody = el('div', 'msp-body');
    GROUPS.forEach(function (g) {
      var grp = el('div', 'msp-grp');
      grp.appendChild(el('div', 'msp-gh', g.name));
      var syms = el('div', 'msp-syms');
      g.items.forEach(function (s) {
        var b = el('button', g.word ? 'msp-sym msp-word' : 'msp-sym', s);
        b.type = 'button';
        /* pointerdown 必须 preventDefault：否则输入框先失焦，光标位置丢掉 */
        b.addEventListener('pointerdown', function (e) { e.preventDefault(); });
        /* 双路兜底：正常走 click；万一 iPad Safari 在 preventDefault 后没派发 click，
           就在 pointerup 后 250ms 补一次插入（click 先到会 clearTimeout，不会重复插入） */
        var fallbackTimer = null;
        b.addEventListener('pointerup', function (e) {
          e.preventDefault();
          if (e.target !== b) return;               // 拖开再松手 → 不算点击
          clearTimeout(fallbackTimer);
          fallbackTimer = setTimeout(function () { insert(s); }, 250);
        });
        b.addEventListener('pointercancel', function () { clearTimeout(fallbackTimer); });
        b.addEventListener('click', function (e) {
          e.preventDefault();
          clearTimeout(fallbackTimer);
          insert(s);
        });
        syms.appendChild(b);
      });
      grp.appendChild(syms);
      panelBody.appendChild(grp);
    });
    panel.appendChild(panelBody);
    document.body.appendChild(panel);

    toastEl = el('div', 'msp-toast', '已插入');
    document.body.appendChild(toastEl);

    document.addEventListener('pointerdown', onDocPointerDown, true);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', reposition);
      window.visualViewport.addEventListener('scroll', reposition);
    }
  }

  function onDocPointerDown(e) {
    if (!panel || !panel.classList.contains('msp-open')) return;
    if (panel.contains(e.target)) return;
    if (target && (e.target === target || (target.parentNode && target.parentNode.contains(e.target)))) return;
    close();
  }

  function onBlur() {
    /* 面板按钮 pointerdown 已 preventDefault，正常不会失焦；这里兜住外部点击 */
    setTimeout(function () {
      if (document.activeElement && panel.contains(document.activeElement)) return;
      if (document.activeElement === target) return;
      close();
    }, 150);
  }

  function showToast(t) {
    if (!toastEl) return;
    toastEl.textContent = t;
    toastEl.classList.add('msp-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('msp-on'); }, 900);
  }

  function insert(sym) {
    if (!target) { showToast('先点一个输入框'); return; }
    var v = target.value == null ? '' : target.value;
    var start = target.selectionStart;
    var end = target.selectionEnd;
    if (start == null || end == null) { start = end = v.length; }
    target.value = v.slice(0, start) + sym + v.slice(end);
    var caret = start + sym.length;
    try { target.setSelectionRange(caret, caret); } catch (err) { /* number 型输入框会抛，忽略 */ }
    /* 让页面的草稿缓存 / 反读逻辑能看到这次改动 */
    target.dispatchEvent(new Event('input', { bubbles: true }));
    reposition();
    showToast('已插入 ' + sym);
  }

  function viewportBounds() {
    var vv = window.visualViewport;
    if (!vv) return { top: 0, bottom: window.innerHeight, left: 0, right: window.innerWidth, width: window.innerWidth };
    return {
      top: vv.offsetTop,
      bottom: vv.offsetTop + vv.height,
      left: vv.offsetLeft,
      right: vv.offsetLeft + vv.width,
      width: vv.width
    };
  }

  function reposition() {
    if (!panel || !panel.classList.contains('msp-open') || !target) return;
    var vis = viewportBounds();
    var r = target.getBoundingClientRect();

    /* 先复位，避免上一轮的限高干扰测量 */
    panel.style.maxHeight = '';
    panel.style.overflowY = 'visible';
    panel.style.width = Math.min(vis.width - EDGE * 2, MAX_W) + 'px';
    var panelH = panel.offsetHeight || 240;

    var spaceBelow = vis.bottom - r.bottom - GAP;
    var spaceAbove = r.top - vis.top - GAP;
    var top;
    if (spaceBelow >= panelH) {
      top = r.bottom + GAP;                              // 1) 下方放得下
    } else if (spaceAbove >= panelH) {
      top = r.top - GAP - panelH;                        // 2) 翻到上方
    } else if (spaceAbove > spaceBelow) {
      panel.style.maxHeight = Math.max(MIN_H, spaceAbove) + 'px';   // 3) 上方更大 → 上方限高内滚
      top = Math.max(vis.top + EDGE, r.top - GAP - Math.max(MIN_H, spaceAbove));
    } else {
      panel.style.maxHeight = Math.max(MIN_H, spaceBelow) + 'px';   // 4) 下方更大 → 下方限高内滚
      top = r.bottom + GAP;
    }
    panel.style.overflowY = 'auto';
    panel.style.top = Math.round(top) + 'px';
    var left = Math.min(Math.max(r.left, vis.left + EDGE), vis.right - panel.offsetWidth - EDGE);
    panel.style.left = Math.round(Math.max(vis.left + EDGE, left)) + 'px';
  }

  function open(input) {
    if (!panel) buildPanel();
    target = input;
    panel.classList.add('msp-open');
    if (input.__mspTrigger) input.__mspTrigger.classList.add('msp-on');
    reposition();
    /* 软键盘弹起是动画：再补两次测量 */
    requestAnimationFrame(reposition);
    setTimeout(reposition, 260);
  }

  function close() {
    if (!panel) return;
    panel.classList.remove('msp-open');
    if (target && target.__mspTrigger) target.__mspTrigger.classList.remove('msp-on');
    for (var k in triggers) { if (triggers[k]) triggers[k].classList.remove('msp-on'); }
    target = null;
  }

  var triggers = {};

  function attach(input, opts) {
    if (!input || input.__mspAttached) return;
    if (input.tagName !== 'TEXTAREA' && input.tagName !== 'INPUT') return;
    input.__mspAttached = true;
    input.addEventListener('focus', function () { open(input); });
    input.addEventListener('blur', onBlur);
    if (opts && opts.trigger) attachTrigger(input);
  }

  /* 可选开关按钮：挂在输入框所在容器的右上角（不改动输入框的父子结构，
     只在容器上加类，避免破坏页面既有的子选择器 / 栅格布局）。 */
  function attachTrigger(input) {
    var host = input.parentNode;
    if (!host || host === document.body) return;
    host.classList.add('msp-host');
    var btn = el('button', 'msp-trigger', '符号');
    btn.type = 'button';
    btn.addEventListener('pointerdown', function (e) { e.preventDefault(); });
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (panel && panel.classList.contains('msp-open') && target === input) { close(); return; }
      input.focus();
      open(input);
    });
    host.appendChild(btn);
    input.__mspTrigger = btn;
    triggers[input.id || (Math.random().toString(36).slice(2))] = btn;
  }

  function attachAll(root, selector, opts) {
    var scope = root || document;
    var list = scope.querySelectorAll(selector || 'textarea, input[type="text"]');
    for (var i = 0; i < list.length; i++) attach(list[i], opts);
  }

  global.DizicalSymbols = {
    GROUPS: GROUPS,
    attach: attach,
    attachAll: attachAll,
    open: open,
    close: close,
    reposition: reposition
  };
})(window);
