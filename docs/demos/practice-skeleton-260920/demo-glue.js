/* demo 胶水层: 只驱动视觉状态, 不碰后端。真视觉逻辑在 real-timer-visual.js */
let duration = 10, elapsed = 0, timerRunning = false, paused = false, started = false;
let demoTickIv = null, demoBpm = 80, demoNote = '♪';

function demoSetSub(html) { const el = document.getElementById('metaVal'); if (el) el.innerHTML = html; }

function demoToggleTimer() {
  const btn = document.getElementById('startBtn');
  const early = document.getElementById('finishEarlyBtn');
  if (!duration) return;
  if (!started) {
    started = true; timerRunning = true; paused = false; elapsed = 0;
    btn.textContent = '暂停';
    if (early) early.style.display = 'inline-block';
    if (typeof ttOnStart === 'function') ttOnStart();
    demoStartTick();
    return;
  }
  if (timerRunning) {
    timerRunning = false; paused = true;
    btn.textContent = '继续';
    if (typeof ttPauseLabel === 'function') ttPauseLabel(true);
    clearInterval(demoTickIv); demoTickIv = null;
    return;
  }
  timerRunning = true; paused = false;
  btn.textContent = '暂停';
  if (typeof ttPauseLabel === 'function') ttPauseLabel(false);
  demoStartTick();
}

function demoStartTick() {
  clearInterval(demoTickIv);
  demoTickIv = setInterval(() => {
    if (!timerRunning) return;
    elapsed++;
    if (typeof ttRenderDigits === 'function') ttRenderDigits(elapsed);
    if (typeof paintRulerRunning === 'function') paintRulerRunning(Math.min(1, elapsed / (duration * 60)));
    if (typeof emitBubbles === 'function') emitBubbles();
    if (elapsed >= duration * 60) {
      clearInterval(demoTickIv); demoTickIv = null;
      timerRunning = false; started = false; paused = false;
      if (typeof ttOnExit === 'function') ttOnExit();
      const btn = document.getElementById('startBtn');
      const early = document.getElementById('finishEarlyBtn');
      if (btn) btn.textContent = '开始';
      if (early) early.style.display = 'none';
    }
  }, 1000);
}

function demoFinishEarly() {
  clearInterval(demoTickIv); demoTickIv = null;
  timerRunning = false; started = false; paused = false;
  if (typeof ttOnExit === 'function') ttOnExit();
  const btn = document.getElementById('startBtn');
  const early = document.getElementById('finishEarlyBtn');
  if (btn) btn.textContent = '开始';
  if (early) early.style.display = 'none';
}

/* 科目选择 / 收拢 */
function demoSelectItem(btn) {
  document.querySelectorAll('.item-btn').forEach(b => b.classList.remove('selected'));
  if (btn) btn.classList.add('selected');
  const name = btn ? btn.dataset.id : '';
  const label = btn ? btn.textContent.trim() : '';
  const req = btn ? (btn.dataset.req || '') : '';
  localStorage.setItem('demo_item_id', name);
  const sumName = document.getElementById('sumName');
  if (sumName) sumName.textContent = label;
  const sumId = document.getElementById('sumId');
  if (sumId) sumId.textContent = name ? ('#' + name) : '';
  const full = document.getElementById('sumFullName');
  if (full) full.textContent = label;
  const sumReq = document.getElementById('sumReq');
  if (sumReq) sumReq.textContent = req;
  const area = document.getElementById('selectionArea');
  const summary = document.getElementById('selectedSummary');
  if (area) { area.classList.remove('expanded'); area.classList.add('collapsed'); }
  if (summary) summary.classList.add('visible');
  demoStartBtnState();
}

function demoToggleReselect() {
  const area = document.getElementById('selectionArea');
  const summary = document.getElementById('selectedSummary');
  if (summary) summary.classList.remove('visible');
  if (area) { area.classList.remove('collapsed'); area.classList.add('expanded'); }
  demoStartBtnState();
}

function demoFilterItems(q) {
  const s = (q || '').trim().toLowerCase();
  document.querySelectorAll('#demoItemGrid .item-btn').forEach(b => {
    b.style.display = (!s || b.textContent.toLowerCase().indexOf(s) >= 0) ? '' : 'none';
  });
}

/* 开始按钮: demo 里改成"选了科目就能点", 并在按钮下给一行原因 (对比置灰无提示) */
function demoStartBtnState() {
  const btn = document.getElementById('startBtn');
  const hint = document.getElementById('demoStartHint');
  const picked = !!localStorage.getItem('demo_item_id');
  const content = (document.getElementById('demoContentInput') || {}).value || '';
  if (btn) btn.disabled = !picked;
  if (hint) hint.textContent = picked ? '' : '先选一个练习科目';
}

function demoSetNote(note) {
  demoNote = note;
  document.querySelectorAll('#sessionPanel .sp-tempo-note-btn').forEach(b => {
    b.classList.toggle('selected', b.dataset.note === note);
  });
  demoHint();
}

function demoStepBpm(d) {
  demoBpm = Math.max(40, Math.min(150, demoBpm + d));
  const v = document.getElementById('demoBpmValue');
  if (v) v.textContent = demoBpm;
  demoHint();
}

function demoHint() {
  const h = document.getElementById('demoTempoHint');
  if (h) h.textContent = demoNote + ' = ' + demoBpm;
}

function demoPickTag(btn, text) {
  const input = document.getElementById('demoContentInput');
  if (input) input.value = text;
  document.querySelectorAll('#demoContentTags .sp-content-tag').forEach(b => b.classList.remove('selected'));
  if (btn) btn.classList.add('selected');
}

/* 初始化: 绑定科目点击 + 起真视觉层 */
(function demoInit() {
  document.querySelectorAll('#demoItemGrid .item-btn').forEach(b => {
    b.addEventListener('click', () => demoSelectItem(b));
  });
  const input = document.getElementById('demoContentInput');
  if (input) input.addEventListener('input', () => { demoStartBtnState(); });
  if (typeof ttInitTimer === 'function') ttInitTimer();
  demoStartBtnState();
  demoHint();
})();
