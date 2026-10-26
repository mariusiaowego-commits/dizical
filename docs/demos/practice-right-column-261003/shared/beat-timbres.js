/* 节拍器音色库 —— 单一真源。
   全卡节拍器（card-b-metronome-full）与竖条节拍器（card-s-metronome-strip）
   共用这一份音色定义与合成逻辑，保证 localStorage 里的音色选择在两卡之间可互换。

   每个音色：
     label      中文名（UI 显示）
     group      分组（机械 / 电子 / 自然）
     freq       普通拍主音频率（Hz）
     freqAccent 强拍主音频率（Hz）
     gain       该音色相对响度系数
     render(ac, dest, o)
       ac   AudioContext
       dest 目标节点
       o    { time: 绝对起始时刻, accent: 是否强拍, peak: 本拍目标峰值 }
*/
(function (global) {
  'use strict';

  /* 振荡器计数（供两卡的自检断言读取） */
  global.DIZI_TONE_STATS = global.DIZI_TONE_STATS || { oscs: 0 };
  function bumpOsc() { global.DIZI_TONE_STATS.oscs += 1; }

  /* ── 合成小工具 ── */
  function makeEnv(ac, peak, time, attack, decay) {
    var g = ac.createGain();
    var p = Math.max(0.0002, peak);
    g.gain.setValueAtTime(0.0001, time);
    g.gain.exponentialRampToValueAtTime(p, time + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, time + attack + decay);
    return g;
  }

  function makeNoise(ac, seconds) {
    var len = Math.max(1, Math.floor(ac.sampleRate * seconds));
    var buf = ac.createBuffer(1, len, ac.sampleRate);
    var data = buf.getChannelData(0);
    for (var i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;
    var src = ac.createBufferSource();
    src.buffer = buf;
    return src;
  }

  /* 一次性振荡器：可指定包络与频率滑落 */
  function tone(ac, dest, o) {
    var osc = ac.createOscillator();
    bumpOsc();
    osc.type = o.type || 'sine';
    osc.frequency.setValueAtTime(Math.max(1, o.freq), o.time);
    if (o.freqEnd) {
      osc.frequency.exponentialRampToValueAtTime(Math.max(1, o.freqEnd), o.time + (o.slide || o.dur));
    }
    var g = makeEnv(ac, o.peak, o.time, o.attack || 0.002, o.decay || 0.05);
    osc.connect(g);
    g.connect(dest);
    osc.start(o.time);
    osc.stop(o.time + (o.dur || 0.08) + 0.03);
    return osc;
  }

  /* 一次性噪声：带滤波器与独立包络 */
  function noiseHit(ac, dest, o) {
    var src = makeNoise(ac, o.dur);
    var f = ac.createBiquadFilter();
    f.type = o.filter || 'bandpass';
    f.frequency.setValueAtTime(Math.max(20, o.cutoff), o.time);
    if (o.freqEnd) f.frequency.exponentialRampToValueAtTime(Math.max(20, o.freqEnd), o.time + (o.slide || o.dur));
    f.Q.setValueAtTime(o.q == null ? 1 : o.q, o.time);
    var g = makeEnv(ac, o.peak, o.time, o.attack || 0.001, o.decay || 0.04);
    src.connect(f);
    f.connect(g);
    g.connect(dest);
    src.start(o.time);
    src.stop(o.time + o.dur + 0.02);
    return src;
  }

  /* ── 音色表 ── */
  var T = {

    /* 尼可机械节拍器：木质的 tick / tock 双音，短、硬、有木头味 */
    nikko: {
      label: '尼可双音', group: '机械',
      freq: 1568, freqAccent: 2093, gain: 1.0, peak: 0.45,
      render: function (ac, dest, o) {
        var high = o.accent ? 2093 : 1568;
        var low = o.accent ? 1318 : 1046;
        tone(ac, dest, { type: 'sine', freq: high, time: o.time, dur: 0.030,
          peak: o.peak * 0.85, attack: 0.0006, decay: 0.026 });
        tone(ac, dest, { type: 'sine', freq: low, time: o.time + 0.014, dur: 0.045,
          peak: o.peak * 0.55, attack: 0.001, decay: 0.040 });
        noiseHit(ac, dest, { cutoff: 2600, q: 0.9, dur: 0.026,
          time: o.time, peak: o.peak * 0.22, decay: 0.024 });
      }
    },

    /* 木鱼：下滑正弦 + 木质噪声 */
    wood: {
      label: '木鱼', group: '机械',
      freq: 720, freqAccent: 980, gain: 1.0, peak: 0.42,
      render: function (ac, dest, o) {
        tone(ac, dest, { type: 'sine', freq: o.accent ? 980 : 720, freqEnd: o.accent ? 280 : 210,
          time: o.time, dur: 0.085, peak: o.peak, attack: 0.002, decay: 0.078, slide: 0.080 });
        noiseHit(ac, dest, { cutoff: o.accent ? 1400 : 900, q: 0.8, dur: 0.045,
          time: o.time, peak: o.peak * 0.40, decay: 0.042 });
      }
    },

    /* 经典机械节拍器：双正弦 1:2.7 + 高通噪声，极短 */
    classic: {
      label: '经典机械', group: '机械',
      freq: 1046, freqAccent: 1318, freq2: 2825.55, gain: 1.0, peak: 0.4,
      render: function (ac, dest, o) {
        var f = o.accent ? 1318 : 1046;
        tone(ac, dest, { type: 'sine', freq: f, time: o.time, dur: 0.022, peak: o.peak, attack: 0.0005, decay: 0.012 });
        tone(ac, dest, { type: 'sine', freq: f * 2.7, time: o.time, dur: 0.018, peak: o.peak * 0.45, attack: 0.0005, decay: 0.010 });
        noiseHit(ac, dest, { filter: 'highpass', cutoff: 3200, dur: 0.014, time: o.time, peak: o.peak * 0.30, decay: 0.012 });
      }
    },

    /* 电子滴答：干净的正弦点击 */
    click: {
      label: '电子滴答', group: '电子',
      freq: 1850, freqAccent: 2400, gain: 1.0, peak: 0.4,
      render: function (ac, dest, o) {
        tone(ac, dest, { type: 'sine', freq: o.accent ? 2400 : 1850, time: o.time, dur: 0.040,
          peak: o.peak * 0.75, attack: 0.001, decay: 0.034 });
      }
    },

    /* 清脆 blip：方波 */
    blip: {
      label: '脆音', group: '电子',
      freq: 1320, freqAccent: 1760, gain: 1.0, peak: 0.34,
      render: function (ac, dest, o) {
        tone(ac, dest, { type: 'square', freq: o.accent ? 1760 : 1320, time: o.time, dur: 0.038,
          peak: o.peak * 0.32, attack: 0.001, decay: 0.030 });
      }
    },

    /* 牛铃：两只方波经带通，像牛颈上的铃 */
    cowbell: {
      label: '牛铃', group: '电子',
      freq: 540, freqAccent: 660, gain: 1.0, peak: 0.38,
      render: function (ac, dest, o) {
        var bp = ac.createBiquadFilter();
        bp.type = 'bandpass';
        bp.frequency.setValueAtTime(1400, o.time);
        bp.Q.setValueAtTime(4, o.time);
        var g = makeEnv(ac, o.peak * 0.6, o.time, 0.001, 0.150);
        bp.connect(g);
        g.connect(dest);
        var f1 = o.accent ? 660 : 540;
        var f2 = o.accent ? 980 : 780;
        [f1, f2].forEach(function (hz) {
          var sq = ac.createOscillator();
          bumpOsc();
          sq.type = 'square';
          sq.frequency.setValueAtTime(hz, o.time);
          sq.connect(bp);
          sq.start(o.time);
          sq.stop(o.time + 0.200);
        });
      }
    },

    /* 鼓槌：高通噪声点 + 一点中高频 */
    sticks: {
      label: '鼓槌', group: '电子',
      freq: 2200, freqAccent: 2800, gain: 1.0, peak: 0.42,
      render: function (ac, dest, o) {
        noiseHit(ac, dest, { filter: 'highpass', cutoff: o.accent ? 2600 : 2100, dur: 0.030,
          time: o.time, peak: o.peak * 0.62, decay: 0.026 });
        tone(ac, dest, { type: 'triangle', freq: o.accent ? 2800 : 2200, time: o.time, dur: 0.026,
          peak: o.peak * 0.35, attack: 0.0005, decay: 0.022 });
      }
    },

    /* 808 低鼓 */
    sub808: {
      label: '低鼓', group: '电子',
      freq: 110, freqAccent: 150, gain: 1.0, peak: 0.44,
      render: function (ac, dest, o) {
        tone(ac, dest, { type: 'sine', freq: o.accent ? 150 : 110, freqEnd: o.accent ? 48 : 40,
          time: o.time, dur: 0.090, peak: o.peak * 1.15, attack: 0.002, decay: 0.085, slide: 0.085 });
      }
    },

    /* 鼓边 */
    rim: {
      label: '鼓边', group: '电子',
      freq: 1450, freqAccent: 1900, gain: 1.0, peak: 0.38,
      render: function (ac, dest, o) {
        tone(ac, dest, { type: 'triangle', freq: o.accent ? 1900 : 1450, time: o.time, dur: 0.040,
          peak: o.peak * 0.45, attack: 0.001, decay: 0.034 });
        noiseHit(ac, dest, { filter: 'highpass', cutoff: o.accent ? 2200 : 1800, dur: 0.060,
          time: o.time, peak: o.peak * 0.55, decay: 0.055 });
      }
    },

    /* 竹节：短促高音，竹子敲击 */
    clave: {
      label: '竹节', group: '自然',
      freq: 2500, freqAccent: 3100, gain: 1.0, peak: 0.4,
      render: function (ac, dest, o) {
        tone(ac, dest, { type: 'sine', freq: o.accent ? 3100 : 2500, freqEnd: o.accent ? 2200 : 1800,
          time: o.time, dur: 0.034, peak: o.peak * 0.70, attack: 0.0006, decay: 0.030, slide: 0.028 });
        noiseHit(ac, dest, { cutoff: 4200, q: 1.6, dur: 0.020, time: o.time, peak: o.peak * 0.30, decay: 0.018 });
      }
    },

    /* 铜铃：FM 钟声，长衰减 */
    bell: {
      label: '铜铃', group: '自然',
      freq: 1245, freqAccent: 1568, gain: 1.0, peak: 0.36,
      render: function (ac, dest, o) {
        var carrier = ac.createOscillator();
        bumpOsc();
        carrier.type = 'sine';
        var f = o.accent ? 1568 : 1245;
        carrier.frequency.setValueAtTime(f, o.time);
        var mod = ac.createOscillator();
        bumpOsc();
        mod.type = 'sine';
        mod.frequency.setValueAtTime(f * 1.5, o.time);
        var modGain = ac.createGain();
        modGain.gain.setValueAtTime(f * 0.9, o.time);
        modGain.gain.exponentialRampToValueAtTime(1, o.time + 0.30);
        mod.connect(modGain);
        modGain.connect(carrier.frequency);
        var g = makeEnv(ac, o.peak * 0.80, o.time, 0.002, 0.520);
        carrier.connect(g);
        g.connect(dest);
        carrier.start(o.time);
        carrier.stop(o.time + 0.60);
        mod.start(o.time);
        mod.stop(o.time + 0.60);
      }
    },

    /* 水滴：下滑正弦 + 二次谐波 */
    drip: {
      label: '水滴', group: '自然',
      freq: 1650, freqAccent: 1980, gain: 1.0, peak: 0.4,
      render: function (ac, dest, o) {
        var f = o.accent ? 1980 : 1650;
        tone(ac, dest, { type: 'sine', freq: f, freqEnd: f * 0.32, time: o.time, dur: 0.075,
          peak: o.peak * 0.72, attack: 0.001, decay: 0.070, slide: 0.070 });
        tone(ac, dest, { type: 'sine', freq: f * 2, freqEnd: f * 0.64, time: o.time, dur: 0.045,
          peak: o.peak * 0.26, attack: 0.001, decay: 0.042, slide: 0.042 });
      }
    },

    /* 沙锤：高频噪声颗粒 */
    shake: {
      label: '沙锤', group: '自然',
      freq: 6200, freqAccent: 7000, gain: 1.0, peak: 0.34,
      render: function (ac, dest, o) {
        noiseHit(ac, dest, { cutoff: o.accent ? 7000 : 6200, q: 1.1, dur: 0.050,
          time: o.time, peak: o.peak * 0.66, decay: 0.046 });
        noiseHit(ac, dest, { filter: 'highpass', cutoff: 5200, dur: 0.026,
          time: o.time + 0.012, peak: o.peak * 0.24, decay: 0.024 });
      }
    },

    /* 原木：低沉的木鼓 */
    log: {
      label: '原木', group: '自然',
      freq: 300, freqAccent: 380, gain: 1.0, peak: 0.42,
      render: function (ac, dest, o) {
        var f = o.accent ? 380 : 300;
        tone(ac, dest, { type: 'sine', freq: f, freqEnd: f * 0.36, time: o.time, dur: 0.120,
          peak: o.peak * 0.95, attack: 0.002, decay: 0.115, slide: 0.115 });
        noiseHit(ac, dest, { filter: 'lowpass', cutoff: 420, dur: 0.060,
          time: o.time, peak: o.peak * 0.34, decay: 0.055 });
      }
    }
  };

  /* 展示顺序：机械 → 电子 → 自然 */
  var ORDER = ['nikko', 'wood', 'classic', 'click', 'blip', 'cowbell', 'sticks',
    'sub808', 'rim', 'clave', 'bell', 'drip', 'shake', 'log'];

  var LIST = ORDER.map(function (id) {
    return { id: id, label: T[id].label, group: T[id].group };
  });

  global.DIZI_TIMBRES = T;
  global.DIZI_TIMBRE_LIST = LIST;
  global.DIZI_TIMBRE_IDS = ORDER.slice();
})(window);
