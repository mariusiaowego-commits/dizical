/* 节拍器时钟。声音排在 AudioContext 的绝对时刻上，灯由同一时刻在 rAF 里点亮。
   不使用 setInterval 当节拍时钟，也不使用 setTimeout 点灯或熄灯。
   四拍同一配方：没有重拍音高，也没有重拍增益。 */
(function (global) {
  'use strict';

  var SCHEDULE_AHEAD = 0.15;
  var ctx = null;
  var playing = false;
  var bpm = 82;
  var beatsPerBar = 4;
  var timbre = 'wood';
  var nextNoteTime = 0;
  var beatCount = 0;
  var queue = [];
  var rafId = 0;
  var onVisual = null;
  var samples = [];
  var recording = false;
  var oscCount = 0;
  var noiseBuf = null;
  var lastScheduled = null;
  var masterNode = null;

  /* 非重拍行。四拍共用这一行。 */
  var RECIPES = {
    wood: { kind: 'wood', freq: 720, freqEnd: 200, peak: 0.26, attack: 0.002, decay: 0.055, dur: 0.080 },
    beep: { kind: 'beep', freq: 2093, freqEnd: 2093, peak: 0.16, attack: 0.001, decay: 0.028, dur: 0.040 },
    cowbell: { kind: 'cowbell', freq: 540, freq2: 780, peak: 0.20, attack: 0.001, decay: 0.160, dur: 0.220 },
    sticks: { kind: 'sticks', freq: 2200, peak: 0.28, attack: 0.0005, decay: 0.016, dur: 0.030 },
    /* 经典机械节拍器：双正弦 1:2.7，加一段高通噪声。四拍同一峰值。 */
    classic: { kind: 'classic', freq: 1046.5, freq2: 2825.55, peak: 0.42, attack: 0.0005, decay: 0.012, dur: 0.018 }
  };

  function recipe() {
    return RECIPES[timbre] || RECIPES.wood;
  }

  /* 共享音色表（shared/beat-timbres.js）。有它就用它，
     全卡节拍器与竖条节拍器共用同一份音色定义，localStorage 里的选择可互换。 */
  function sharedDef(name) {
    var T = global.DIZI_TIMBRES || {};
    return T[name || timbre] || null;
  }

  function known(name) {
    return !!RECIPES[name] || !!sharedDef(name);
  }

  function master() {
    if (!ctx) return null;
    if (!masterNode) {
      masterNode = ctx.createGain();
      masterNode.gain.value = 1;
      masterNode.connect(ctx.destination);
    }
    return masterNode;
  }

  function ensure() {
    if (!ctx) {
      var AC = global.AudioContext || global.webkitAudioContext;
      ctx = new AC();
      try {
        if ('audioSession' in navigator) navigator.audioSession.type = 'playback';
      } catch (e) {}
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  function noise(ac) {
    if (noiseBuf && noiseBuf.sampleRate === ac.sampleRate) return noiseBuf;
    var len = ac.sampleRate;
    noiseBuf = ac.createBuffer(1, len, ac.sampleRate);
    var data = noiseBuf.getChannelData(0);
    for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    return noiseBuf;
  }

  function env(ac, peak, time, attack, decay) {
    var g = ac.createGain();
    var p = Math.max(0.0002, peak);
    g.gain.setValueAtTime(0.0001, time);
    g.gain.exponentialRampToValueAtTime(p, time + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, time + attack + decay);
    return g;
  }

  function hit(beat, time) {
    var ac = ctx;
    var sd = sharedDef(timbre);
    if (sd && sd.render) {
      var speak = (sd.peak || 0.42) * (sd.gain || 1);
      sd.render(ac, master() || ac.destination, { time: time, accent: false, peak: speak });
      var n = (global.DIZI_TONE_STATS && global.DIZI_TONE_STATS.oscs) || 0;
      if (n > oscCount) oscCount = n;
      lastScheduled = {
        timbre: timbre,
        freq: sd.freq,
        freq2: sd.freq2 || sd.freqAccent || sd.freq,
        peak: speak,
        beat: beat,
        accent: false
      };
      return lastScheduled;
    }
    var r = recipe();
    var g = env(ac, r.peak, time, r.attack, r.decay);
    g.connect(ac.destination);
    if (r.kind === 'wood') {
      var osc = ac.createOscillator();
      oscCount += 1;
      osc.type = 'sine';
      osc.frequency.setValueAtTime(r.freq, time);
      osc.frequency.exponentialRampToValueAtTime(r.freqEnd, time + 0.040);
      osc.connect(g);
      osc.start(time);
      osc.stop(time + r.dur);
      var src = ac.createBufferSource();
      src.buffer = noise(ac);
      var bp = ac.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.setValueAtTime(800, time);
      bp.Q.setValueAtTime(1.2, time);
      var ng = env(ac, r.peak * 0.25, time, r.attack, 0.040);
      src.connect(bp);
      bp.connect(ng);
      ng.connect(ac.destination);
      src.start(time);
      src.stop(time + 0.045);
    } else if (r.kind === 'beep') {
      var beep = ac.createOscillator();
      oscCount += 1;
      beep.type = 'sine';
      beep.frequency.setValueAtTime(r.freq, time);
      beep.connect(g);
      beep.start(time);
      beep.stop(time + r.dur);
    } else if (r.kind === 'cowbell') {
      var bp2 = ac.createBiquadFilter();
      bp2.type = 'bandpass';
      bp2.frequency.setValueAtTime(1400, time);
      bp2.Q.setValueAtTime(4, time);
      g.disconnect();
      g.connect(bp2);
      bp2.connect(ac.destination);
      [r.freq, r.freq2].forEach(function (hz) {
        var sq = ac.createOscillator();
        oscCount += 1;
        sq.type = 'square';
        sq.frequency.setValueAtTime(hz, time);
        sq.connect(g);
        sq.start(time);
        sq.stop(time + r.dur);
      });
    } else if (r.kind === 'classic') {
      [r.freq, r.freq2].forEach(function (hz) {
        var sine = ac.createOscillator();
        oscCount += 1;
        sine.type = 'sine';
        sine.frequency.setValueAtTime(hz, time);
        sine.connect(g);
        sine.start(time);
        sine.stop(time + r.dur);
      });
      var srcC = ac.createBufferSource();
      srcC.buffer = noise(ac);
      var hpC = ac.createBiquadFilter();
      hpC.type = 'highpass';
      hpC.frequency.setValueAtTime(3500, time);
      var ngC = env(ac, r.peak * 0.55, time, r.attack, 0.008);
      srcC.connect(hpC);
      hpC.connect(ngC);
      ngC.connect(ac.destination);
      srcC.start(time);
      srcC.stop(time + 0.012);
    } else {
      var src2 = ac.createBufferSource();
      src2.buffer = noise(ac);
      var hp = ac.createBiquadFilter();
      hp.type = 'highpass';
      hp.frequency.setValueAtTime(r.freq, time);
      src2.connect(hp);
      hp.connect(g);
      src2.start(time);
      src2.stop(time + r.dur);
      var src3 = ac.createBufferSource();
      src3.buffer = noise(ac);
      var bp3 = ac.createBiquadFilter();
      bp3.type = 'bandpass';
      bp3.frequency.setValueAtTime(4000, time);
      bp3.Q.setValueAtTime(1, time);
      var ng2 = env(ac, r.peak * 0.35, time, r.attack, r.decay);
      src3.connect(bp3);
      bp3.connect(ng2);
      ng2.connect(ac.destination);
      src3.start(time);
      src3.stop(time + r.dur);
    }
    lastScheduled = {
      timbre: timbre,
      freq: r.freq,
      freq2: r.freq2 || r.freq,
      peak: r.peak,
      beat: beat,
      accent: false
    };
    return lastScheduled;
  }

  function glow() {
    return Math.min(0.32, 0.7 * 60 / bpm);
  }

  function frame() {
    if (!playing || !ctx) return;
    var now = ctx.currentTime;
    if (nextNoteTime < now) nextNoteTime = now + 0.02;
    var horizon = now + SCHEDULE_AHEAD;
    while (nextNoteTime < horizon) {
      var beat = beatCount % beatsPerBar;
      var info = hit(beat, nextNoteTime);
      queue.push({
        time: nextNoteTime,
        beat: beat,
        accent: false,
        freq: info.freq,
        peak: info.peak,
        visualTime: null
      });
      nextNoteTime += 60 / bpm;
      beatCount += 1;
    }
    var gsec = glow();
    queue = queue.filter(function (n) { return now < n.time + gsec + 0.05; });
    var active = null;
    for (var i = 0; i < queue.length; i++) {
      var n = queue[i];
      if (n.time <= now && now < n.time + gsec) active = n;
    }
    if (active && active.visualTime == null) {
      active.visualTime = now;
      if (recording) {
        samples.push({
          audioTime: active.time,
          visualTime: now,
          beat: active.beat,
          accent: false,
          freq: active.freq,
          peak: active.peak
        });
      }
    }
    if (onVisual) onVisual(active);
    rafId = global.requestAnimationFrame(frame);
  }

  function start() {
    ensure();
    if (playing) stop();
    playing = true;
    beatCount = 0;
    nextNoteTime = ctx.currentTime + 0.05;
    queue = [];
    rafId = global.requestAnimationFrame(frame);
  }

  function stop() {
    playing = false;
    if (rafId) global.cancelAnimationFrame(rafId);
    rafId = 0;
    queue = [];
    if (onVisual) onVisual(null);
  }

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible' && playing && ctx) {
      ctx.resume();
      nextNoteTime = ctx.currentTime + 0.05;
      queue = [];
      if (onVisual) onVisual(null);
    }
  });

  global.BeatEngine = {
    visualDriver: 'raf',
    start: start,
    stop: stop,
    isPlaying: function () { return playing; },
    setBpm: function (n) {
      n = Math.round(Number(n));
      if (n >= 40 && n <= 200) bpm = n;
    },
    setTimbre: function (name) {
      if (known(name)) timbre = name;
    },
    setBeatsPerBar: function (n) {
      n = Math.round(Number(n));
      if (n >= 1 && n <= 12) beatsPerBar = n;
    },
    setOnVisual: function (fn) { onVisual = fn; },
    preview: function (name) {
      ensure();
      var prev = timbre;
      if (known(name)) timbre = name;
      var info = hit(0, ctx.currentTime + 0.03);
      timbre = prev;
      return info;
    },
    lastScheduled: function () { return lastScheduled; },
    peaks: function () {
      var o = {};
      Object.keys(RECIPES).forEach(function (k) { o[k] = RECIPES[k].peak; });
      var T = global.DIZI_TIMBRES || {};
      Object.keys(T).forEach(function (k) { o[k] = (T[k].peak || 0.42) * (T[k].gain || 1); });
      return o;
    },
    armSync: function () { samples = []; recording = true; },
    syncSamples: function () { return samples.slice(); },
    oscCreated: function () { return oscCount; },
    context: function () { return ctx; },
    active: function () {
      var now = ctx ? ctx.currentTime : 0;
      var gsec = glow();
      var active = null;
      for (var i = 0; i < queue.length; i++) {
        var n = queue[i];
        if (n.time <= now && now < n.time + gsec) active = n;
      }
      return active;
    },
    recipe: recipe
  };
})(window);
