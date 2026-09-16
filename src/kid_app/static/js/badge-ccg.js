/* sprint-26091101 — DizicalCCG tilt / holo / parallax / claim
   ── 卡面样式版本: v1.7.0-dev (sprint 26091302 B6 图鉴接线, 四轮定稿)
      v1.7.0-dev (2026-09-16): Oracle 典藏卡 markup / 精铸金章 / focus lerp 0.08。
      v1.6.0-dev (2026-09-13, 四轮):
        ① 列表卡 = demo 静止态逐图层一致 (绑 pointer / idle drift / hover tilt / 翻面全开;
           只把 .badge-grid .ccg-stage 的 --card-w 收到 min(160px,100%) 塞网格格子)
        ② IntersectionObserver 视口护栏: 不在视口的卡 tick 时跳过 paint (CSS vars 不变 = 正视图层)
        ③ 每张卡 mount 时随机相位偏移 (Math.random() ∈ [0,1) 进 sin/cos, 错开 44 张同步摇摆)
        ④ opts.idleSkip=N 默认 1; mount 时按列表/单卡传 2 (skip 调 idle drift 节奏);
           全局开关 DizicalCCG.setIdleSkip(n) 保留供调试
        ⑤ opts.locked=true 加 .is-locked class (CSS filter 灰度 + 右下角小锁 SVG)
        ⑥ 无 gsap 时 (老页面 / 测试 / 完全离线) — stage 加 .ccg-no-gsap class,
           CSS transition transform 0.7s 兜底翻面动画, 不用 gsap.to
      v1.5.0 (dad 2026-09-13 四轮): 本轮只改光照, 3D 代码零 Functional 改动, 只为跟随卡面样式一起升号
        (光照减弱/过渡全在 badge-ccg.css);
      v1.4.0-dev (dad 2026-09-13 三轮): 静止无光照 (IDLE_LIT 0.22→0, 光标不在卡上 lit=0) /
        跟随动画幅度加大 (maxTilt 15°→22°, 抬起 10px→20px; 视差与景深在 css);
      v1.3.0-dev (dad 2026-09-13 二轮): 聚光灯强度旋钮 --ccg-light-gain(默认 0.6, glare+spec 两层同乘) /
        页脚 (星级 + DIZICAL) DOM 移入 .ccg-plate 内, 页脚不再自带背景;
      v1.2.0-dev (dad 2026-09-13 l1): 箔层 DOM 改挂卡面级 —— artInner() 只出主体,
         frontMarkup() 出两组箔栈 (.ccg-foil-stack 背景组 z1 / .ccg-foil-stack.ccg-foil-over 扫光组 z6);
      v1.1.0-dev 本轮 3D 代码无功能改动, 只为跟随卡面样式版本一起升号;
      改了倾斜/翻转/视差/聚光灯逻辑 ⇒ 两个文件同时升号
      改本文件交互/几何 ⇒ 先升版本号 (本行 + badge-ccg.css + demo 页头 chip),
      再用 scripts/freeze-ccg-demo.sh <新版本号> "说明" 冻结, 登记表见 static/demo-archive/VERSIONS.md */
(function (global) {
  "use strict";

  var BADGE = {
    id: "assign_pal",
    name: "批改小帮手",
    tag: "突破",
    image: "/static/badges/assign_pal_v2.png",
    cond: "协助完成课后批改",
    story: "细心批改，温故知新。一笔一划帮同学改对题，小笛手也成了大家的批改小帮手。",
    date: "2026年6月16日",
    stars: 3,
    no: "007",
    hall: "呦呦成就殿堂",
    card_theme: "pearl"
  };


  /* ── Oracle 典藏卡生产合流 (2026-09-16) ── */
  var ORACLE_SEALS = {
  "突破": `<svg viewBox="0 0 64 64" shape-rendering="geometricPrecision" aria-hidden="true">
  <circle cx="32" cy="32" r="26.6" fill="none" stroke="#6b3f0a" stroke-width="1.4" opacity=".55"/>
  <circle cx="32" cy="32" r="25.2" fill="none" stroke="#fef08a" stroke-width=".9" opacity=".5"/>
  <g fill="#3d2a0a" opacity=".5" transform="translate(1 1.1)">
    <path d="M30.74 26.98L20.70 16.93L14.42 19.45L15.05 25.72L20.70 40.79L30.74 39.53Z"/>
    <path d="M33.26 26.98L43.30 16.93L49.58 19.45L48.95 25.72L43.30 40.79L33.26 39.53Z"/>
    <path d="M32.00 11.94L38.17 24.29L34.78 24.29L34.78 45.89L38.17 48.97L32.00 53.60L25.83 48.97L29.22 45.89L29.22 24.29L25.83 24.29Z"/>
  </g>
  <g fill="#5c3410" stroke="#fde68a" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round">
    <path d="M30.74 26.98L20.70 16.93L14.42 19.45L15.05 25.72L20.70 40.79L30.74 39.53Z"/>
    <path d="M33.26 26.98L43.30 16.93L49.58 19.45L48.95 25.72L43.30 40.79L33.26 39.53Z"/>
    <path d="M32.00 11.94L38.17 24.29L34.78 24.29L34.78 45.89L38.17 48.97L32.00 53.60L25.83 48.97L29.22 45.89L29.22 24.29L25.83 24.29Z"/>
  </g>
  <g fill="#ca8a04" transform="translate(-0.55 -0.8)">
    <path d="M30.75 28.25L23.25 20.76L19.51 22.00L20.76 27.00L25.75 35.75L30.75 34.50Z"/>
    <path d="M33.25 28.25L40.75 20.76L44.49 22.00L43.24 27.00L38.25 35.75L33.25 34.50Z"/>
    <path d="M32.00 18.00L35.11 25.78L33.24 25.78L33.24 41.33L32.00 43.67L30.76 41.33L30.76 25.78L28.89 25.78Z"/>
  </g>
  <g fill="#fef08a" opacity=".55">
    <path d="M30.75 28.25L23.25 20.76L19.51 22.00L20.76 27.00L25.75 35.75L30.75 34.50Z"/>
    <path d="M33.25 28.25L40.75 20.76L44.49 22.00L43.24 27.00L38.25 35.75L33.25 34.50Z"/>
    <path d="M32.00 18.00L35.11 25.78L33.24 25.78L33.24 41.33L32.00 43.67L30.76 41.33L30.76 25.78L28.89 25.78Z"/>
  </g>
  <circle cx="28.6" cy="26.2" r="1.7" fill="#fffbeb" opacity=".9"/>
</svg>`,
  "巅峰": `<svg viewBox="0 0 64 64" shape-rendering="geometricPrecision" aria-hidden="true">
  <circle cx="32" cy="32" r="26.6" fill="none" stroke="#6b3f0a" stroke-width="1.4" opacity=".55"/>
  <circle cx="32" cy="32" r="25.2" fill="none" stroke="#fef08a" stroke-width=".9" opacity=".5"/>
  <g fill="#3d2a0a" opacity=".5" transform="translate(1 1.1)">
    <path d="M16.73 47.27L16.73 38.36L18.64 28.18L21.18 38.36L24.36 23.09L27.55 38.36L32.00 16.73L36.45 38.36L39.64 23.09L42.82 38.36L45.36 28.18L47.27 38.36L47.27 47.27Z"/>
  </g>
  <g fill="#5c3410" stroke="#fde68a" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round">
    <path d="M16.73 47.27L16.73 38.36L18.64 28.18L21.18 38.36L24.36 23.09L27.55 38.36L32.00 16.73L36.45 38.36L39.64 23.09L42.82 38.36L45.36 28.18L47.27 38.36L47.27 47.27Z"/>
  </g>
  <g fill="#ca8a04" transform="translate(-0.55 -0.8)">
    <path d="M21.63 43.52L21.63 38.91L25.09 27.39L27.97 38.91L32.00 22.78L36.03 38.91L38.91 27.39L42.37 38.91L42.37 43.52Z"/>
  </g>
  <g fill="#fef08a" opacity=".55">
    <path d="M21.63 43.52L21.63 38.91L25.09 27.39L27.97 38.91L32.00 22.78L36.03 38.91L38.91 27.39L42.37 38.91L42.37 43.52Z"/>
  </g>
  <circle cx="28.6" cy="26.2" r="1.7" fill="#fffbeb" opacity=".9"/>
</svg>`,
  "执着": `<svg viewBox="0 0 64 64" shape-rendering="geometricPrecision" aria-hidden="true">
  <circle cx="32" cy="32" r="26.6" fill="none" stroke="#6b3f0a" stroke-width="1.4" opacity=".55"/>
  <circle cx="32" cy="32" r="25.2" fill="none" stroke="#fef08a" stroke-width=".9" opacity=".5"/>
  <g fill="#3d2a0a" opacity=".5" transform="translate(1 1.1)">
    <path d="M32.00 10.40L36.98 17.05L40.31 18.71L43.63 25.35L46.95 28.68L48.62 35.32L45.29 41.97L40.31 46.95L32.00 51.94L23.69 46.95L18.71 41.97L15.38 35.32L17.05 28.68L20.37 25.35L23.69 18.71L27.02 17.05Z"/>
    <path d="M27.24 46.29L36.76 46.29L38.35 52.64L25.65 52.64Z"/>
  </g>
  <g fill="#5c3410" stroke="#fde68a" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round">
    <path d="M32.00 10.40L36.98 17.05L40.31 18.71L43.63 25.35L46.95 28.68L48.62 35.32L45.29 41.97L40.31 46.95L32.00 51.94L23.69 46.95L18.71 41.97L15.38 35.32L17.05 28.68L20.37 25.35L23.69 18.71L27.02 17.05Z"/>
    <path d="M27.24 46.29L36.76 46.29L38.35 52.64L25.65 52.64Z"/>
  </g>
  <g fill="#ca8a04" transform="translate(-0.55 -0.8)">
    <path d="M32.00 18.50L36.22 25.25L38.75 28.62L39.59 35.38L36.22 42.12L32.00 45.50L27.78 42.12L24.41 35.38L25.25 28.62L27.78 25.25Z"/>
  </g>
  <g fill="#fef08a" opacity=".55">
    <path d="M32.00 18.50L36.22 25.25L38.75 28.62L39.59 35.38L36.22 42.12L32.00 45.50L27.78 42.12L24.41 35.38L25.25 28.62L27.78 25.25Z"/>
  </g>
  <circle cx="28.6" cy="26.2" r="1.7" fill="#fffbeb" opacity=".9"/>
</svg>`,
  "晋级": `<svg viewBox="0 0 64 64" shape-rendering="geometricPrecision" aria-hidden="true">
  <circle cx="32" cy="32" r="26.6" fill="none" stroke="#6b3f0a" stroke-width="1.4" opacity=".55"/>
  <circle cx="32" cy="32" r="25.2" fill="none" stroke="#fef08a" stroke-width=".9" opacity=".5"/>
  <g fill="#3d2a0a" opacity=".5" transform="translate(1 1.1)">
    <path d="M25.90 17.35L38.10 17.35L38.10 25.90L44.21 25.90L44.21 35.66L47.87 35.66L47.87 46.65L16.13 46.65L16.13 35.66L19.79 35.66L19.79 25.90L25.90 25.90Z"/>
  </g>
  <g fill="#5c3410" stroke="#fde68a" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round">
    <path d="M25.90 17.35L38.10 17.35L38.10 25.90L44.21 25.90L44.21 35.66L47.87 35.66L47.87 46.65L16.13 46.65L16.13 35.66L19.79 35.66L19.79 25.90L25.90 25.90Z"/>
  </g>
  <g fill="#ca8a04" transform="translate(-0.55 -0.8)">
    <path d="M26.92 20.58L37.08 20.58L37.08 26.92L42.15 26.92L42.15 34.54L37.08 34.54L26.92 34.54L26.92 26.92Z"/>
  </g>
  <g fill="#fef08a" opacity=".55">
    <path d="M26.92 20.58L37.08 20.58L37.08 26.92L42.15 26.92L42.15 34.54L37.08 34.54L26.92 34.54L26.92 26.92Z"/>
  </g>
  <circle cx="28.6" cy="26.2" r="1.7" fill="#fffbeb" opacity=".9"/>
</svg>`,
  "神秘": `<svg viewBox="0 0 64 64" shape-rendering="geometricPrecision" aria-hidden="true">
  <circle cx="32" cy="32" r="26.6" fill="none" stroke="#6b3f0a" stroke-width="1.4" opacity=".55"/>
  <circle cx="32" cy="32" r="25.2" fill="none" stroke="#fef08a" stroke-width=".9" opacity=".5"/>
  <g fill="#3d2a0a" opacity=".5" transform="translate(1 1.1)">
    <path fill-rule="evenodd" d="M32.00 10.80L50.53 42.90L13.47 42.90ZM32.00 53.60L13.47 21.50L50.53 21.50Z"/>
  </g>
  <g fill="#5c3410" stroke="#fde68a" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round">
    <path fill-rule="evenodd" d="M32.00 10.80L50.53 42.90L13.47 42.90ZM32.00 53.60L13.47 21.50L50.53 21.50Z"/>
  </g>
  <g fill="#ca8a04" transform="translate(-0.55 -0.8)">
    <path d="M32.00 21.50L34.30 28.02L41.09 26.75L36.60 32.00L41.09 37.25L34.30 35.98L32.00 42.50L29.70 35.98L22.91 37.25L27.40 32.00L22.91 26.75L29.70 28.02Z"/>
  </g>
  <g fill="#fef08a" opacity=".55">
    <path d="M32.00 21.50L34.30 28.02L41.09 26.75L36.60 32.00L41.09 37.25L34.30 35.98L32.00 42.50L29.70 35.98L22.91 37.25L27.40 32.00L22.91 26.75L29.70 28.02Z"/>
  </g>
  <circle cx="28.6" cy="26.2" r="1.7" fill="#fffbeb" opacity=".9"/>
</svg>`,
  "段位": `<svg viewBox="0 0 64 64" shape-rendering="geometricPrecision" aria-hidden="true">
  <circle cx="32" cy="32" r="26.6" fill="none" stroke="#6b3f0a" stroke-width="1.4" opacity=".55"/>
  <circle cx="32" cy="32" r="25.2" fill="none" stroke="#fef08a" stroke-width=".9" opacity=".5"/>
  <g fill="#3d2a0a" opacity=".5" transform="translate(1 1.1)">
    <path d="M20.69 51.23L51.23 20.69A5.60 5.60 0 0 1 43.31 12.77L12.77 43.31A5.60 5.60 0 0 1 20.69 51.23Z"/>
    <path d="M12.77 20.69L43.31 51.23A5.60 5.60 0 0 1 51.23 43.31L20.69 12.77A5.60 5.60 0 0 1 12.77 20.69Z"/>
    <path d="M32.00 23.80L40.20 32.00L32.00 40.20L23.80 32.00Z"/>
  </g>
  <g fill="#5c3410" stroke="#fde68a" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round">
    <path d="M20.69 51.23L51.23 20.69A5.60 5.60 0 0 1 43.31 12.77L12.77 43.31A5.60 5.60 0 0 1 20.69 51.23Z"/>
    <path d="M12.77 20.69L43.31 51.23A5.60 5.60 0 0 1 51.23 43.31L20.69 12.77A5.60 5.60 0 0 1 12.77 20.69Z"/>
    <path d="M32.00 23.80L40.20 32.00L32.00 40.20L23.80 32.00Z"/>
  </g>
  <g fill="#ca8a04" transform="translate(-0.55 -0.8)">
    <path d="M21.97 43.23L43.12 23.71A2.00 2.00 0 0 1 40.41 20.77L19.25 40.29A2.00 2.00 0 0 1 21.97 43.23Z"/>
    <path d="M19.25 23.71L40.41 43.23A2.00 2.00 0 0 1 43.12 40.29L21.97 20.77A2.00 2.00 0 0 1 19.25 23.71Z"/>
    <path d="M32.00 26.50L37.50 32.00L32.00 37.50L26.50 32.00Z"/>
  </g>
  <g fill="#fef08a" opacity=".55">
    <path d="M21.97 43.23L43.12 23.71A2.00 2.00 0 0 1 40.41 20.77L19.25 40.29A2.00 2.00 0 0 1 21.97 43.23Z"/>
    <path d="M19.25 23.71L40.41 43.23A2.00 2.00 0 0 1 43.12 40.29L21.97 20.77A2.00 2.00 0 0 1 19.25 23.71Z"/>
    <path d="M32.00 26.50L37.50 32.00L32.00 37.50L26.50 32.00Z"/>
  </g>
  <circle cx="28.6" cy="26.2" r="1.7" fill="#fffbeb" opacity=".9"/>
</svg>`,
  "主题": `<svg viewBox="0 0 64 64" shape-rendering="geometricPrecision" aria-hidden="true">
  <circle cx="32" cy="32" r="26.6" fill="none" stroke="#6b3f0a" stroke-width="1.4" opacity=".55"/>
  <circle cx="32" cy="32" r="25.2" fill="none" stroke="#fef08a" stroke-width=".9" opacity=".5"/>
  <g fill="#3d2a0a" opacity=".5" transform="translate(1 1.1)">
    <path d="M32.00 10.20L37.05 25.04L52.73 25.26L40.18 34.66L44.81 49.64L32.00 40.60L19.19 49.64L23.82 34.66L11.27 25.26L26.95 25.04Z"/>
  </g>
  <g fill="#5c3410" stroke="#fde68a" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round">
    <path d="M32.00 10.20L37.05 25.04L52.73 25.26L40.18 34.66L44.81 49.64L32.00 40.60L19.19 49.64L23.82 34.66L11.27 25.26L26.95 25.04Z"/>
  </g>
  <g fill="#ca8a04" transform="translate(-0.55 -0.8)">
    <path d="M31.20 18.50L34.14 26.95L43.09 27.14L35.96 32.55L38.55 41.11L31.20 36.00L23.85 41.11L26.44 32.55L19.31 27.14L28.26 26.95Z"/>
  </g>
  <g fill="#fef08a" opacity=".55">
    <path d="M31.20 18.50L34.14 26.95L43.09 27.14L35.96 32.55L38.55 41.11L31.20 36.00L23.85 41.11L26.44 32.55L19.31 27.14L28.26 26.95Z"/>
  </g>
  <circle cx="28.6" cy="26.2" r="1.7" fill="#fffbeb" opacity=".9"/>
</svg>`
};

  var INK_SVG_HTML = "<!-- nameplate \u6bdb\u7b14\u6c34\u58a8\u6cfc\u58a8\u6bcd\u7248 (\u5ba3\u7eb8\u6e17\u58a8\u6ee4\u955c + \u98de\u767d\u4e1d\u7f15 + \u81ea\u7531\u8ff8\u6e85\u58a8\u661f) -->\n<svg class=\"oracle-ink-defs\" width=\"0\" height=\"0\" style=\"position:absolute;visibility:hidden;\" aria-hidden=\"true\" focusable=\"false\">\n  <defs>\n    <!-- \u5ba3\u7eb8\u6c34\u58a8\u8fb9\u7f18\u6e17\u5316\u5fae\u7ed2\u8d28\u611f -->\n    <filter id=\"oracle-ink-bleed\" x=\"-6%\" y=\"-6%\" width=\"112%\" height=\"112%\">\n      <feTurbulence type=\"fractalNoise\" baseFrequency=\"0.04 0.018\" numOctaves=\"3\" result=\"noise\"/>\n      <feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" scale=\"3.0\" xChannelSelector=\"R\" yChannelSelector=\"G\"/>\n    </filter>\n    <linearGradient id=\"oracle-ink-flow\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\">\n      <stop offset=\"0%\" stop-color=\"#fff9f6\" stop-opacity=\"0.95\"/>\n      <stop offset=\"42%\" stop-color=\"#ffede8\" stop-opacity=\"0.90\"/>\n      <stop offset=\"68%\" stop-color=\"#fedacf\" stop-opacity=\"0.80\"/>\n      <stop offset=\"86%\" stop-color=\"#fed8ce\" stop-opacity=\"0.55\"/>\n      <stop offset=\"100%\" stop-color=\"#fed8ce\" stop-opacity=\"0.20\"/>\n    </linearGradient>\n    <g id=\"oracle-ink-splash-graphic\" filter=\"url(#oracle-ink-bleed)\" fill=\"url(#oracle-ink-flow)\">\n    <path d=\"M 0,16 C 0,6 6,0 16,0 C 130,-3 260,0 390,3 C 450,5 500,10 550,22 C 600,34 650,48 705,38 C 660,54 590,64 540,74 C 620,80 730,96 810,118 C 740,132 630,140 560,146 C 630,158 710,180 690,202 C 640,212 570,218 500,224 C 380,232 260,238 140,240 L 0,240 Z\" />\n    <path d=\"M 520,20 C 600,14 690,12 770,18 C 690,24 600,22 520,23 Z\" opacity=\"0.92\" />\n    <path d=\"M 550,34 C 640,26 740,26 820,36 C 740,42 640,36 550,36 Z\" opacity=\"0.9\" />\n    <path d=\"M 490,52 C 600,44 720,48 840,62 C 720,68 600,56 490,54 Z\" opacity=\"0.94\" />\n    <path d=\"M 530,74 C 650,68 780,76 880,94 C 780,102 650,88 530,79 Z\" opacity=\"0.96\" />\n    <path d=\"M 550,96 C 680,92 800,102 905,112 C 800,118 680,108 550,100 Z\" opacity=\"0.93\" />\n    <path d=\"M 520,118 C 640,122 760,128 870,126 C 760,134 640,128 520,122 Z\" opacity=\"0.9\" />\n    <path d=\"M 500,140 C 620,146 730,160 820,150 C 730,166 620,152 500,144 Z\" opacity=\"0.88\" />\n    <path d=\"M 510,166 C 610,178 700,194 775,180 C 700,198 610,184 510,172 Z\" opacity=\"0.85\" />\n    <path d=\"M 470,194 C 560,206 650,218 725,206 C 650,224 560,214 470,200 Z\" opacity=\"0.82\" />\n    <path d=\"M 580,14 C 670,8 760,8 830,14 C 760,19 670,16 580,16 Z\" opacity=\"0.8\" />\n    <path d=\"M 610,54 C 710,48 800,52 875,64 C 800,68 710,60 610,56 Z\" opacity=\"0.84\" />\n    <path d=\"M 630,132 C 730,138 820,140 890,134 C 820,144 730,144 630,136 Z\" opacity=\"0.82\" />\n    <ellipse cx=\"760.0\" cy=\"20.0\" rx=\"5.5\" ry=\"2.8\" transform=\"rotate(12.0 760.0 20.0)\" opacity=\"0.95\" />\n    <ellipse cx=\"805.0\" cy=\"34.0\" rx=\"5.0\" ry=\"2.5\" transform=\"rotate(10.0 805.0 34.0)\" opacity=\"0.92\" />\n    <ellipse cx=\"840.0\" cy=\"60.0\" rx=\"6.5\" ry=\"3.2\" transform=\"rotate(8.0 840.0 60.0)\" opacity=\"0.95\" />\n    <ellipse cx=\"875.0\" cy=\"92.0\" rx=\"7.5\" ry=\"3.6\" transform=\"rotate(5.0 875.0 92.0)\" opacity=\"0.95\" />\n    <ellipse cx=\"915.0\" cy=\"110.0\" rx=\"5.5\" ry=\"2.8\" transform=\"rotate(2.0 915.0 110.0)\" opacity=\"0.90\" />\n    <ellipse cx=\"865.0\" cy=\"128.0\" rx=\"6.5\" ry=\"3.2\" transform=\"rotate(-4.0 865.0 128.0)\" opacity=\"0.92\" />\n    <ellipse cx=\"825.0\" cy=\"150.0\" rx=\"5.5\" ry=\"2.8\" transform=\"rotate(-8.0 825.0 150.0)\" opacity=\"0.88\" />\n    <ellipse cx=\"780.0\" cy=\"178.0\" rx=\"4.8\" ry=\"2.5\" transform=\"rotate(-12.0 780.0 178.0)\" opacity=\"0.85\" />\n    <ellipse cx=\"735.0\" cy=\"204.0\" rx=\"4.2\" ry=\"2.2\" transform=\"rotate(-15.0 735.0 204.0)\" opacity=\"0.82\" />\n    <ellipse cx=\"777.7\" cy=\"21.5\" rx=\"1.2\" ry=\"1.0\" transform=\"rotate(12.0 777.7 21.5)\" opacity=\"0.71\" />\n    <ellipse cx=\"771.8\" cy=\"33.8\" rx=\"1.5\" ry=\"1.2\" transform=\"rotate(12.0 771.8 33.8)\" opacity=\"0.71\" />\n    <ellipse cx=\"815.2\" cy=\"36.2\" rx=\"1.2\" ry=\"1.0\" transform=\"rotate(10.0 815.2 36.2)\" opacity=\"0.69\" />\n    <ellipse cx=\"820.1\" cy=\"39.2\" rx=\"2.0\" ry=\"1.6\" transform=\"rotate(10.0 820.1 39.2)\" opacity=\"0.69\" />\n    <ellipse cx=\"860.3\" cy=\"57.9\" rx=\"1.2\" ry=\"0.9\" transform=\"rotate(8.0 860.3 57.9)\" opacity=\"0.71\" />\n    <ellipse cx=\"891.2\" cy=\"101.8\" rx=\"1.8\" ry=\"1.4\" transform=\"rotate(5.0 891.2 101.8)\" opacity=\"0.71\" />\n    <ellipse cx=\"889.7\" cy=\"98.9\" rx=\"1.5\" ry=\"1.2\" transform=\"rotate(5.0 889.7 98.9)\" opacity=\"0.71\" />\n    <ellipse cx=\"925.9\" cy=\"102.5\" rx=\"2.1\" ry=\"1.7\" transform=\"rotate(2.0 925.9 102.5)\" opacity=\"0.68\" />\n    <ellipse cx=\"933.7\" cy=\"118.2\" rx=\"1.0\" ry=\"0.8\" transform=\"rotate(2.0 933.7 118.2)\" opacity=\"0.68\" />\n    <ellipse cx=\"874.0\" cy=\"123.4\" rx=\"1.2\" ry=\"1.0\" transform=\"rotate(-4.0 874.0 123.4)\" opacity=\"0.69\" />\n    <ellipse cx=\"877.8\" cy=\"134.3\" rx=\"1.8\" ry=\"1.5\" transform=\"rotate(-4.0 877.8 134.3)\" opacity=\"0.69\" />\n    <ellipse cx=\"838.3\" cy=\"142.6\" rx=\"2.1\" ry=\"1.7\" transform=\"rotate(-8.0 838.3 142.6)\" opacity=\"0.66\" />\n    <ellipse cx=\"790.8\" cy=\"172.1\" rx=\"2.0\" ry=\"1.6\" transform=\"rotate(-12.0 790.8 172.1)\" opacity=\"0.64\" />\n    <ellipse cx=\"798.5\" cy=\"166.2\" rx=\"1.4\" ry=\"1.1\" transform=\"rotate(-12.0 798.5 166.2)\" opacity=\"0.64\" />\n    <ellipse cx=\"752.2\" cy=\"206.5\" rx=\"1.5\" ry=\"1.2\" transform=\"rotate(-15.0 752.2 206.5)\" opacity=\"0.61\" />\n    <ellipse cx=\"607.2\" cy=\"120.2\" rx=\"1.7\" ry=\"1.2\" transform=\"rotate(2.3 607.2 120.2)\" opacity=\"0.82\" />\n    <ellipse cx=\"616.4\" cy=\"119.1\" rx=\"3.2\" ry=\"1.8\" transform=\"rotate(7.9 616.4 119.1)\" opacity=\"0.83\" />\n    <ellipse cx=\"761.0\" cy=\"141.5\" rx=\"2.8\" ry=\"1.2\" transform=\"rotate(6.9 761.0 141.5)\" opacity=\"0.54\" />\n    <ellipse cx=\"700.9\" cy=\"157.1\" rx=\"4.4\" ry=\"2.8\" transform=\"rotate(8.7 700.9 157.1)\" opacity=\"0.68\" />\n    <ellipse cx=\"687.3\" cy=\"74.3\" rx=\"8.2\" ry=\"3.2\" transform=\"rotate(-11.1 687.3 74.3)\" opacity=\"0.69\" />\n    <ellipse cx=\"628.2\" cy=\"73.6\" rx=\"2.8\" ry=\"1.4\" transform=\"rotate(-10.2 628.2 73.6)\" opacity=\"0.72\" />\n    <ellipse cx=\"579.6\" cy=\"89.8\" rx=\"1.8\" ry=\"0.7\" transform=\"rotate(0.6 579.6 89.8)\" opacity=\"0.89\" />\n    <ellipse cx=\"689.4\" cy=\"111.0\" rx=\"1.7\" ry=\"1.1\" transform=\"rotate(1.6 689.4 111.0)\" opacity=\"0.62\" />\n    <ellipse cx=\"640.5\" cy=\"97.8\" rx=\"1.4\" ry=\"0.7\" transform=\"rotate(2.2 640.5 97.8)\" opacity=\"0.83\" />\n    <ellipse cx=\"790.4\" cy=\"87.6\" rx=\"5.4\" ry=\"2.7\" transform=\"rotate(0.2 790.4 87.6)\" opacity=\"0.58\" />\n    <ellipse cx=\"569.8\" cy=\"97.3\" rx=\"3.5\" ry=\"2.2\" transform=\"rotate(2.0 569.8 97.3)\" opacity=\"0.97\" />\n    <ellipse cx=\"701.4\" cy=\"93.4\" rx=\"5.1\" ry=\"2.3\" transform=\"rotate(-1.7 701.4 93.4)\" opacity=\"0.75\" />\n    <ellipse cx=\"742.7\" cy=\"156.8\" rx=\"2.2\" ry=\"1.2\" transform=\"rotate(4.4 742.7 156.8)\" opacity=\"0.59\" />\n    <ellipse cx=\"808.7\" cy=\"117.9\" rx=\"2.0\" ry=\"1.3\" transform=\"rotate(2.9 808.7 117.9)\" opacity=\"0.56\" />\n    <ellipse cx=\"682.2\" cy=\"97.9\" rx=\"1.3\" ry=\"0.9\" transform=\"rotate(-0.2 682.2 97.9)\" opacity=\"0.77\" />\n    <ellipse cx=\"704.4\" cy=\"107.1\" rx=\"1.7\" ry=\"1.2\" transform=\"rotate(5.0 704.4 107.1)\" opacity=\"0.76\" />\n    <ellipse cx=\"589.1\" cy=\"101.3\" rx=\"5.1\" ry=\"2.8\" transform=\"rotate(0.6 589.1 101.3)\" opacity=\"0.77\" />\n    <ellipse cx=\"639.9\" cy=\"161.0\" rx=\"2.7\" ry=\"1.2\" transform=\"rotate(11.1 639.9 161.0)\" opacity=\"0.66\" />\n    <ellipse cx=\"637.7\" cy=\"76.8\" rx=\"1.8\" ry=\"1.1\" transform=\"rotate(-10.1 637.7 76.8)\" opacity=\"0.66\" />\n    <ellipse cx=\"603.1\" cy=\"111.0\" rx=\"6.2\" ry=\"3.4\" transform=\"rotate(-3.9 603.1 111.0)\" opacity=\"0.75\" />\n    <ellipse cx=\"597.6\" cy=\"84.9\" rx=\"2.9\" ry=\"1.8\" transform=\"rotate(-0.0 597.6 84.9)\" opacity=\"0.79\" />\n    <ellipse cx=\"577.0\" cy=\"139.0\" rx=\"1.1\" ry=\"0.7\" transform=\"rotate(8.1 577.0 139.0)\" opacity=\"0.96\" />\n    <ellipse cx=\"831.2\" cy=\"106.9\" rx=\"4.6\" ry=\"2.4\" transform=\"rotate(-5.7 831.2 106.9)\" opacity=\"0.50\" />\n    <ellipse cx=\"564.1\" cy=\"112.5\" rx=\"8.1\" ry=\"3.4\" transform=\"rotate(-1.7 564.1 112.5)\" opacity=\"0.84\" />\n    <ellipse cx=\"569.1\" cy=\"84.4\" rx=\"8.1\" ry=\"3.4\" transform=\"rotate(-10.4 569.1 84.4)\" opacity=\"0.91\" />\n    <ellipse cx=\"813.9\" cy=\"215.6\" rx=\"1.9\" ry=\"1.4\" transform=\"rotate(19.7 813.9 215.6)\" opacity=\"0.48\" />\n    <ellipse cx=\"676.4\" cy=\"100.9\" rx=\"3.1\" ry=\"1.7\" transform=\"rotate(-1.8 676.4 100.9)\" opacity=\"0.62\" />\n    <ellipse cx=\"653.1\" cy=\"130.9\" rx=\"6.0\" ry=\"3.0\" transform=\"rotate(6.6 653.1 130.9)\" opacity=\"0.79\" />\n    <ellipse cx=\"720.4\" cy=\"116.8\" rx=\"2.1\" ry=\"1.6\" transform=\"rotate(6.8 720.4 116.8)\" opacity=\"0.72\" />\n    <ellipse cx=\"595.8\" cy=\"95.0\" rx=\"1.7\" ry=\"0.8\" transform=\"rotate(1.8 595.8 95.0)\" opacity=\"0.75\" />\n    <ellipse cx=\"748.1\" cy=\"128.9\" rx=\"1.9\" ry=\"1.0\" transform=\"rotate(3.8 748.1 128.9)\" opacity=\"0.53\" />\n    <ellipse cx=\"669.9\" cy=\"60.2\" rx=\"4.1\" ry=\"2.1\" transform=\"rotate(-10.4 669.9 60.2)\" opacity=\"0.74\" />\n    <ellipse cx=\"854.6\" cy=\"111.1\" rx=\"1.9\" ry=\"0.8\" transform=\"rotate(0.1 854.6 111.1)\" opacity=\"0.51\" />\n    <ellipse cx=\"623.5\" cy=\"85.6\" rx=\"1.8\" ry=\"1.2\" transform=\"rotate(-8.2 623.5 85.6)\" opacity=\"0.72\" />\n    <ellipse cx=\"661.7\" cy=\"81.0\" rx=\"1.4\" ry=\"0.9\" transform=\"rotate(-9.6 661.7 81.0)\" opacity=\"0.71\" />\n    <ellipse cx=\"628.9\" cy=\"89.8\" rx=\"2.8\" ry=\"1.9\" transform=\"rotate(0.1 628.9 89.8)\" opacity=\"0.86\" />\n    <ellipse cx=\"590.4\" cy=\"128.1\" rx=\"4.5\" ry=\"2.1\" transform=\"rotate(3.9 590.4 128.1)\" opacity=\"0.84\" />\n    <ellipse cx=\"571.1\" cy=\"111.6\" rx=\"3.3\" ry=\"1.5\" transform=\"rotate(4.5 571.1 111.6)\" opacity=\"0.89\" />\n    <ellipse cx=\"637.5\" cy=\"86.9\" rx=\"3.0\" ry=\"1.5\" transform=\"rotate(-2.9 637.5 86.9)\" opacity=\"0.86\" />\n    <ellipse cx=\"839.5\" cy=\"207.9\" rx=\"2.0\" ry=\"1.0\" transform=\"rotate(17.3 839.5 207.9)\" opacity=\"0.47\" />\n    <ellipse cx=\"619.3\" cy=\"130.7\" rx=\"1.2\" ry=\"0.6\" transform=\"rotate(8.9 619.3 130.7)\" opacity=\"0.89\" />\n    <ellipse cx=\"780.4\" cy=\"147.5\" rx=\"2.4\" ry=\"1.5\" transform=\"rotate(11.7 780.4 147.5)\" opacity=\"0.54\" />\n    <ellipse cx=\"650.2\" cy=\"121.8\" rx=\"4.1\" ry=\"2.0\" transform=\"rotate(-1.8 650.2 121.8)\" opacity=\"0.75\" />\n    <ellipse cx=\"695.6\" cy=\"81.4\" rx=\"5.2\" ry=\"2.6\" transform=\"rotate(-12.1 695.6 81.4)\" opacity=\"0.60\" />\n    <ellipse cx=\"635.8\" cy=\"127.2\" rx=\"4.0\" ry=\"2.3\" transform=\"rotate(3.0 635.8 127.2)\" opacity=\"0.76\" />\n    <ellipse cx=\"786.3\" cy=\"29.2\" rx=\"3.0\" ry=\"1.8\" transform=\"rotate(-12.7 786.3 29.2)\" opacity=\"0.60\" />\n    <ellipse cx=\"822.5\" cy=\"166.4\" rx=\"5.1\" ry=\"2.5\" transform=\"rotate(13.0 822.5 166.4)\" opacity=\"0.54\" />\n    <ellipse cx=\"775.2\" cy=\"172.4\" rx=\"7.9\" ry=\"3.8\" transform=\"rotate(11.2 775.2 172.4)\" opacity=\"0.59\" />\n    <ellipse cx=\"560.9\" cy=\"109.6\" rx=\"3.3\" ry=\"1.8\" transform=\"rotate(-2.6 560.9 109.6)\" opacity=\"0.89\" />\n    <ellipse cx=\"670.0\" cy=\"112.1\" rx=\"3.4\" ry=\"1.5\" transform=\"rotate(2.5 670.0 112.1)\" opacity=\"0.77\" />\n    <ellipse cx=\"614.3\" cy=\"80.2\" rx=\"2.5\" ry=\"1.2\" transform=\"rotate(-4.6 614.3 80.2)\" opacity=\"0.83\" />\n    <ellipse cx=\"607.4\" cy=\"82.8\" rx=\"2.6\" ry=\"1.2\" transform=\"rotate(-5.2 607.4 82.8)\" opacity=\"0.90\" />\n    <ellipse cx=\"597.9\" cy=\"117.8\" rx=\"3.1\" ry=\"1.2\" transform=\"rotate(3.8 597.9 117.8)\" opacity=\"0.84\" />\n    <ellipse cx=\"666.2\" cy=\"130.0\" rx=\"6.0\" ry=\"3.0\" transform=\"rotate(7.9 666.2 130.0)\" opacity=\"0.79\" />\n    </g>\n  </defs>\n</svg>";

  function ensureInkSvg() {
    if (typeof document === "undefined") return;
    if (document.getElementById("oracle-ink-splash-graphic")) return;
    var wrap = document.createElement("div");
    wrap.innerHTML = INK_SVG_HTML;
    var svg = wrap.firstElementChild;
    if (svg) document.body.insertBefore(svg, document.body.firstChild);
  }

  function artToneFromTag(tag) {
    var t = String(tag || "");
    var keys = ["突破", "巅峰", "执着", "晋级", "神秘", "段位", "主题"];
    var i;
    for (i = 0; i < keys.length; i++) {
      if (t.indexOf(keys[i]) !== -1) return keys[i];
    }
    return "主题";
  }

  var CATEGORY_ABBR = {
    "突破": "破",
    "巅峰": "极",
    "执着": "韧",
    "段位": "阶",
    "晋级": "跃",
    "神秘": "秘",
    "主题": "典"
  };

  function categoryAbbr(tag) {
    var key = artToneFromTag(tag);
    if (CATEGORY_ABBR[key]) return CATEGORY_ABBR[key];
    var t = String(tag || "");
    return t ? t.charAt(0) : "典";
  }

  function oracleSealHtml(tag) {
    var key = artToneFromTag(tag);
    var svg = ORACLE_SEALS[key] || ORACLE_SEALS["主题"] || "";
    return '<div class="oracle-seal" role="img" aria-label="' + key + ' · 精铸金章">' +
      '<span class="oracle-seal-face">' + svg + '</span></div>';
  }

  var reduce = false;
  try {
    reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) {}
  var coarse = false;
  try {
    coarse = window.matchMedia("(pointer: coarse)").matches;
  } catch (e2) {}

  var hasGsap = typeof global.gsap !== "undefined";
  /* dad 2026-09-13 (4): 跟随动画幅度加大 —— 最大倾角 15° -> 22°, 抬起 10px -> 20px */
  var maxTilt = 22;
  /* 静止态聚光灯: 停在上金边/画面上沿, 不压在图案正中 (dad 2026-09-12) */
  var IDLE_Y = 14;
  /* dad 2026-09-13 (3): 静止 = 无光照 —— 光标离开/未上卡时 lit 收到 0 (旧值 0.22 会留一层常亮).
     收到 0 后 glare/spec 两层 opacity 归零 (见 badge-ccg.css), 只有镭射/防伪常驻层还在。 */
  var IDLE_LIT = 0;
  var holoGain = 1;
  var cards = [];
  var lastCcgId = 0;  // F6: 自增 id 分配器 (每次 mountCard +1)
  var fpsState = { frames: 0, last: 0, el: null, raf: 0, frame: 0 };
  /* F6 静止态性能护栏: idle skip counter — 默认 1 (每帧 paint). 若 iPad 实测掉帧,
     调 DizicalCCG.setIdleSkip(2) 跳到每 2 帧 paint 一次. hover/交互期间强制 1 (不跳). */
  var idleSkip = 1;
  var currentClaimBadge = null;
  /* F6 视口观察者: 不在视口的卡 tick 时跳过 paint. null = SSR/旧浏览器降级 (全跑). */
  var visObserver = null;
  var visVisible = new Set();  // 已 mount 卡 id (在视口里)
  /* F6 启动期一次性建 IO: 滑出视口 → 从 Set 移除 (tick 跳过);
     滑入视口 → 加回 Set. SSR 不可用时 catch 静默降级 (visObserver=null → tick 里短路失效,
     退化为「全部跑」, 不影响功能). */
  if (typeof window !== "undefined" && "IntersectionObserver" in window) {
    visObserver = new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        var e = entries[i];
        var id = e.target._ccgId;
        if (!id) continue;
        if (e.isIntersecting) visVisible.add(id);
        else visVisible.delete(id);
      }
    }, { rootMargin: "40px 0px" });  // 略微放大视口边界, 滚动到边缘前就启动 paint
  }

  function clamp(n, a, b) { return Math.max(a, Math.min(b, n)); }

  /* 画面框几何: 光标在卡面坐标系 (0-100%) 的位置换算成画面框内的百分比,
     画面内的箔层/聚光灯才不会跟着卡面中心走 */
  function measureArtBox(stage) {
    var win = stage.querySelector(".ccg-art-window");
    var front = stage.querySelector(".ccg-card-front");
    if (!win || !front || !front.offsetWidth) return null;
    var l = 0, t = 0, node = win;
    while (node && node !== front) {
      l += node.offsetLeft;
      t += node.offsetTop;
      node = node.offsetParent;
    }
    if (node !== front) return null;
    return { l: l, t: t, w: win.offsetWidth, h: win.offsetHeight, cw: front.offsetWidth, ch: front.offsetHeight };
  }

  function applyVars(el, s, geo) {
    el.style.setProperty("--pointer-x", s.px + "%");
    el.style.setProperty("--pointer-y", s.py + "%");
    if (geo && geo.w > 0 && geo.h > 0) {
      /* 光斑允许跑出金框一点点 (边沿自然衰减), 但不能跑到框外很远:
         跑到框外时椭圆渐变的暗尾会摊满窗口 → 深色重叠 (dad 2026-09-12) */
      el.style.setProperty("--aw-x", clamp((((s.px / 100) * geo.cw) - geo.l) / geo.w * 100, -10, 110) + "%");
      el.style.setProperty("--aw-y", clamp((((s.py / 100) * geo.ch) - geo.t) / geo.h * 100, -10, 110) + "%");
    }
    el.style.setProperty("--rotate-x", s.rx + "deg");
    el.style.setProperty("--rotate-y", s.ry + "deg");
    el.style.setProperty("--rx", s.rx + "deg");
    el.style.setProperty("--ry", s.ry + "deg");
    el.style.setProperty("--holo-gain", String(holoGain));
    el.style.setProperty("--lift", s.lift ? s.lift + "px" : "0px");
    el.style.setProperty("--nx", String(s.nx || 0));
    el.style.setProperty("--ny", String(s.ny || 0));
    el.style.setProperty("--from-center", String(s.fromCenter || 0));
    el.style.setProperty("--lit", String(s.lit == null ? 0 : s.lit));
  }

  function titleHtml(name) {
    return '<div class="ccg-title"><i class="ccg-orn" aria-hidden="true"></i><span>' + name + '</span><i class="ccg-orn" aria-hidden="true"></i></div>';
  }

  function backMarkup(d, mode) {
    var isFocus = (mode === "focus");
    var storyVal = isFocus ? (d.story || d.storyShort || "") : (d.storyShort || d.story || "");
    var storyLbl = isFocus ? "典故" : "典故·短板";
    var kicker = (d.tag || "") + (d.no ? " · " + d.no : "");
    return (
      '<div class="oracle-face oracle-face-back">' +
        '<div class="oracle-card">' +
          '<div class="oracle-back-inner">' +
            '<div class="oracle-back-kicker">' + kicker + '</div>' +
            '<div class="oracle-back-title">' + d.name + '</div>' +
            '<div class="oracle-back-rule"></div>' +
            '<div class="oracle-back-field">' +
              '<div class="oracle-back-lbl">获取条件</div>' +
              '<div class="oracle-back-val">' + (d.cond || "") + '</div>' +
            '</div>' +
            '<div class="oracle-back-field oracle-back-story ccg-back-story">' +
              '<div class="oracle-back-lbl">' + storyLbl + '</div>' +
              '<div class="oracle-back-val ccg-back-val">' + storyVal + '</div>' +
              (isFocus ? '<div class="ccg-story-expand-btn">展开全文 ▾</div>' : "") +
            '</div>' +
            '<div class="oracle-back-seal">' + oracleSealHtml(d.tag) + '</div>' +
            '<div class="oracle-back-foot"><span>✦</span><span>DIZICAL</span></div>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function starsHtml(n) {
    var i, out = "";
    /* dad image#9/4: 星级来自后端 achievements.card_stars (resolve_card_stars);
       前端只做钳位, 不写死任何数量 */
    var c = Math.max(0, Math.min(5, parseInt(n, 10) || 0));
    for (i = 0; i < c; i++) out += '<span class="ccg-star"></span>';
    return out;
  }

  /* 画面内层: 方案二多一层 Z 轴悬浮主体, 方案一主体贴在箔层之上.
     dad 2026-09-13 l1: 箔层已整体搬到卡面级 (见 frontMarkup), 这里只出主体 ——
     画面窗不再拥有自己的镭射底 (= dad 数的第二个圆角矩形外框)。 */
  function artInner(scheme, d) {
    var img = '<img alt="" width="512" height="512" decoding="sync" fetchpriority="high" src="' + d.image + '">';
    return scheme === "px"
      ? '<div class="ccg-layer ccg-layer-subject">' + img + '</div>'
      : '<div class="ccg-holo-art">' + img + '</div>';
  }

  /* Amazing Rare 版式: 上 2/3 = 金框框住主视觉, 下 1/3 = 银数据条 + 米色说明栏 + 页脚
     dad 2026-09-13 l1「徽章那张画的 3d 镭射背景 我希望能整个铺满卡片」:
       箔层从画面窗 (5.4% 内缩 + 裁剪) 改挂卡面级, 分两组:
         · .ccg-foil-stack       = 背景镭射 (底衬/彩虹流光/星点/防伪纹) → z1, 在主体之下
         · .ccg-foil-stack.ccg-foil-over = 覆在主体之上的扫光 (聚光灯/主光/镭射) → z6
       主体 (z5) 夹在两组之间 ⇒ 与旧版同一条视觉顺序, 但镭射铺满整卡, 不再有第二层框。 */
  function frontMarkup(scheme, d) {
    var cat = (d.tag || "主题") + "成就";
    var catAbbr = categoryAbbr(d.tag);
    var catLabel = d.tag || "典藏";
    return (
      '<div class="oracle-face oracle-face-front">' +
        '<div class="oracle-card">' +
          '<div class="oracle-rotator">' +
            '<div class="oracle-pin" title="竹笛金章">' +
              '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#78350f" stroke-width="2.5" stroke-linecap="round">' +
                '<line x1="3" y1="21" x2="21" y2="3"/>' +
                '<circle cx="9" cy="15" r="1.2" fill="#78350f"/>' +
                '<circle cx="12" cy="12" r="1.2" fill="#78350f"/>' +
                '<circle cx="15" cy="9" r="1.2" fill="#78350f"/>' +
              '</svg>' +
            '</div>' +
            '<div class="oracle-frame">' +
              '<div class="oracle-art">' +
                '<img alt="" width="512" height="512" loading="lazy" decoding="async" src="' + d.image + '">' +
                '<div class="oracle-sheen"></div>' +
                '<div class="oracle-nameplate-wrap">' +
                  '<div class="oracle-nameplate">' +
                    '<svg class="oracle-ink-svg" viewBox="0 0 1000 240" width="100%" height="100%" preserveAspectRatio="none" aria-hidden="true"><use href="#oracle-ink-splash-graphic"></use></svg>' +
                    '<span class="oracle-cat">' + cat + '</span>' +
                    '<span class="oracle-name">' + d.name + '</span>' +
                  '</div>' +
                  '<div class="oracle-slogan">' + (d.cond || "") + '</div>' +
                '</div>' +
              '</div>' +
              '<div class="oracle-footer">' +
                '<div class="oracle-footer-l">' +
                  '<span class="oracle-avatar">' + catAbbr + '</span>' +
                  '<span class="oracle-owner-name">' + catLabel + '</span>' +
                '</div>' +
                oracleSealHtml(d.tag) +
                '<div class="oracle-footer-r"><span>✦</span><span>DIZICAL</span></div>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function cardMarkup(scheme, d, mode) {
    return (
      '<div class="ccg-shadow"></div>' +
      '<div class="ccg-rotator">' +
        '<div class="ccg-card-flipper oracle-flipper">' +
          frontMarkup(scheme, d) +
          backMarkup(d, mode) +
        '</div>' +
      '</div>'
    );
  }

  function bindReady(stage) {
    var imgs = stage.querySelectorAll("img");
    var left = imgs.length;
    if (!left) { stage.classList.add("is-ready"); return; }
    function done() {
      left -= 1;
      if (left <= 0) stage.classList.add("is-ready");
    }
    imgs.forEach(function (img) {
      if (img.complete) done();
      else {
        img.addEventListener("load", done, { once: true });
        img.addEventListener("error", done, { once: true });
      }
    });
  }

  /* ── 打字机故事托盘状态与动效 (dad 2026-09-14 需求 2.6 & 2.7) ── */
  var storyTrayState = {
    status: "closed", // 'closed' | 'typing' | 'done'
    timer: null,
    fullText: "",
    idx: 0,
    trayEl: null,
    textEl: null,
    cursorEl: null
  };

  function closeStoryTray() {
    if (storyTrayState.timer) {
      clearInterval(storyTrayState.timer);
      storyTrayState.timer = null;
    }
    if (storyTrayState.trayEl) {
      storyTrayState.trayEl.remove();
      storyTrayState.trayEl = null;
    }
    storyTrayState.status = "closed";
    storyTrayState.fullText = "";
    storyTrayState.idx = 0;
    storyTrayState.textEl = null;
    storyTrayState.cursorEl = null;
  }

  function finishStoryTyping() {
    if (storyTrayState.timer) {
      clearInterval(storyTrayState.timer);
      storyTrayState.timer = null;
    }
    if (storyTrayState.textEl) {
      storyTrayState.textEl.textContent = storyTrayState.fullText;
    }
    if (storyTrayState.cursorEl) {
      storyTrayState.cursorEl.style.display = "none";
    }
    storyTrayState.status = "done";
  }

  function handleStoryTrayToggle(stage, text) {
    if (storyTrayState.status === "typing") {
      finishStoryTyping();
      return;
    }
    if (storyTrayState.status === "done") {
      closeStoryTray();
      return;
    }

    closeStoryTray();

    var parentLayout = stage.closest(".ccg-claim-layout") ||
                       stage.closest(".ccg-claim-dialog") ||
                       stage.parentElement;
    if (!parentLayout) return;

    var tray = document.createElement("div");
    tray.className = "ccg-story-tray";
    tray.id = "ccg-story-tray";
    tray.innerHTML =
      '<div class="ccg-story-tray-card">' +
        '<div class="ccg-story-tray-head">' +
          '<span class="ccg-story-tray-title">📜 典故全文</span>' +
          '<span class="ccg-story-tray-tip">点击速览 · 再点收起</span>' +
        '</div>' +
        '<div class="ccg-story-tray-body">' +
          '<span class="ccg-story-text"></span><span class="ccg-story-cursor"></span>' +
        '</div>' +
      '</div>';

    var anchor = stage.closest(".ccg-claim-stage") || stage;
    if (anchor.nextSibling) {
      parentLayout.insertBefore(tray, anchor.nextSibling);
    } else {
      parentLayout.appendChild(tray);
    }

    var textEl = tray.querySelector(".ccg-story-text");
    var cursorEl = tray.querySelector(".ccg-story-cursor");

    tray.addEventListener("pointerdown", function (e) { e.stopPropagation(); });
    tray.addEventListener("click", function (e) {
      e.stopPropagation();
      if (storyTrayState.status === "typing") {
        finishStoryTyping();
      } else if (storyTrayState.status === "done") {
        closeStoryTray();
      }
    });

    storyTrayState.status = "typing";
    storyTrayState.fullText = text || "";
    storyTrayState.idx = 0;
    storyTrayState.trayEl = tray;
    storyTrayState.textEl = textEl;
    storyTrayState.cursorEl = cursorEl;

    var full = storyTrayState.fullText;
    storyTrayState.timer = setInterval(function () {
      storyTrayState.idx += 1;
      textEl.textContent = full.slice(0, storyTrayState.idx);
      if (storyTrayState.idx >= full.length) {
        finishStoryTyping();
      }
    }, 20);
  }

  function resetAllFlips() {
    for (var i = 0; i < cards.length; i++) {
      if (cards[i].resetFlip) cards[i].resetFlip();
    }
  }

  function mountCard(stage, scheme, data, opts) {
    var d = data || BADGE;
    var o = opts || {};
    var isLocked = o.locked === true;

    /* 模式判定 (dad 2026-09-14 需求 1):
       wall (列表态): 禁止翻面, 点击只打开 modal;
       focus (modal 放大态 / 把玩舞台): 允许点击翻面看卡背 */
    var isModal = !!(o.mode === "focus" || (stage.closest && stage.closest(".ccg-claim-stage, .ccg-claim-overlay, #ach-detail-stage, #bd-detail-stage, #ccg-claim-stage, .ccg-claim-layout, .ccg-claim-dialog")));
    var isWall = !!(o.mode === "wall" || (stage.closest && stage.closest(".badge-grid, .ccg-grid-cell, .b-card, .badge-card, .ccg-stage-mount")));
    var mode = o.mode || (isModal ? "focus" : (isWall ? "wall" : "focus"));
    var canFlip = (o.canFlip !== undefined) ? !!o.canFlip : (mode === "focus");
    var isFocus = (mode === "focus");

    ensureInkSvg();

    var stageClasses = "ccg-stage ccg-" + scheme + (isLocked ? " is-locked" : "");
    if (!hasGsap) stageClasses += " ccg-no-gsap";  // F7: 无 gsap 时启用 CSS 过渡翻面
    if (!canFlip) stageClasses += " ccg-no-flip";
    stage.className = stageClasses;
    stage.setAttribute("data-scheme", scheme);
    stage.setAttribute("data-mode", mode);

    /* 主题 (dad 2026-09-14 需求 3): 支持全局 body[data-theme] 或卡级主题, 默认 pearl 淡色主题 */
    var bodyTheme = (typeof document !== "undefined" && document.body && (document.body.getAttribute("data-theme") || document.body.getAttribute("data-ccg-theme"))) || null;
    stage.setAttribute("data-ccg-theme", bodyTheme || d.card_theme || d.theme || "pearl");
    stage.setAttribute("data-art-tone", artToneFromTag(d.tag));
    stage.innerHTML = cardMarkup(scheme, d, mode);
    bindReady(stage);

    /* F5: 撤掉 opts.static=true 短路路径 — 列表卡现在跟 demo 静止态逐图层一致:
       金框 135 度柔光 (.ccg-frame::after baseline .3) / 细闪 (.ccg-foil-glitter baseline .24) /
       金属反光 (.ccg-foil-shine::after brightness .4) 都保留; idle drift 照跑;
       hover tilt/翻面正常, locked 灰度仍生效 (F4 不变).
       opts 仍然存在作为扩展点, 但 opts.static === true 行为跟 opts={} 完全一致. */
    /* F9: opts.idleSkip=N (整数 ≥ 1) — 该卡 mount 后 tick 每 N 帧 paint 一次.
       默认 0 = 跟随模块 idleSkip (新 mount 走全局); 列表卡挂载传 2 节省帧率
       (第三轮实测 32 卡 skip=1 31fps, skip=2 55fps). 传值时固化 (_idleSkipFrozen=true),
       全局 DizicalCCG.setIdleSkip(n) 后续不再覆盖. */
    var cardIdleSkip = (typeof o.idleSkip === 'number' && o.idleSkip >= 1)
      ? Math.floor(o.idleSkip) : 0;
    /* 列表墙默认 idleSkip=4（约 15fps 闲置漂移）；hover/interacting 走 setFromPoint 满帧；
       focus/modal 不传此值 → 0 → 跟全局 1，60fps lerp + 翻转。 */
    if (!cardIdleSkip && mode === "wall") cardIdleSkip = 4;
    var state = { px: 50, py: IDLE_Y, rx: 0, ry: 0, lift: 0, flip: 0, nx: 0, ny: 0, fromCenter: 0, lit: IDLE_LIT };
    var aim = { px: 50, py: IDLE_Y, rx: 0, ry: 0, lift: 0, nx: 0, ny: 0, fromCenter: 0, lit: IDLE_LIT };
    var interacting = false;
    var dragging = false;
    var moved = 0;
    var startX = 0, startY = 0;
    var pointerId = null;
    var resetTween = null;
    var flipper = stage.querySelector(".ccg-card-flipper");
    var artGeo = measureArtBox(stage);

    function paint() { applyVars(stage, state, artGeo); }

    paint();
    if (flipper) flipper.style.setProperty("--flip", "0deg");

    /* F6: 给每张卡一个稳定 id + 随机相位偏移. id 用 _ccgId 给 IntersectionObserver 当 Set key.
       phase ∈ [0, 1), 跟 sin/cos 里的 t/1800 / t/2100 相乘成弧度偏移,
       把 44 张同款卡的 idle drift 错开 (避免视觉同步感). */
    var ccgId = ++lastCcgId;
    stage._ccgId = ccgId;
    stage._idlePhase = Math.random();
    if (visObserver) {
      visObserver.observe(stage);
      visVisible.add(ccgId);  // 默认在视口里 (IntersectionObserver 异步纠正)
    }

    function killReset() {
      if (resetTween && hasGsap) resetTween.kill();
      resetTween = null;
    }

    function setFromPoint(clientX, clientY) {
      var r = stage.getBoundingClientRect();
      var x = clamp((clientX - r.left) / r.width, 0, 1);
      var y = clamp((clientY - r.top) / r.height, 0, 1);
      var nx = clamp((x - 0.5) * 2, -1, 1);
      var ny = clamp((y - 0.5) * 2, -1, 1);
      var px = x * 100;
      var py = y * 100;
      var rx = clamp(-ny * maxTilt, -maxTilt, maxTilt);
      var ry = clamp(nx * maxTilt, -maxTilt, maxTilt);
      var fromCenter = clamp(Math.hypot(nx, ny), 0, 1.4);
      if (isFocus && !reduce) {
        aim.px = px; aim.py = py;
        aim.nx = nx; aim.ny = ny;
        aim.rx = rx; aim.ry = ry;
        aim.lift = 20; aim.lit = 1;
        aim.fromCenter = fromCenter;
        return;
      }
      state.px = px; state.py = py;
      state.nx = nx; state.ny = ny;
      state.rx = rx; state.ry = ry;
      state.fromCenter = fromCenter;
      state.lift = 20;
      state.lit = 1;
      paint();
    }

    function springHome() {
      interacting = false;
      dragging = false;
      stage.classList.remove("is-dragging");
      if (isFocus && !reduce) {
        return;
      }
      if (reduce) {
        state.px = 50; state.py = IDLE_Y; state.rx = 0; state.ry = 0; state.lift = 0;
        state.nx = 0; state.ny = 0; state.fromCenter = 0; state.lit = IDLE_LIT;
        paint();
        return;
      }
      if (hasGsap) {
        killReset();
        resetTween = global.gsap.to(state, {
          px: 50, py: IDLE_Y, rx: 0, ry: 0, lift: 0, nx: 0, ny: 0, fromCenter: 0, lit: IDLE_LIT,
          duration: 0.6,
          ease: "power3.out",
          overwrite: true,
          onUpdate: paint
        });
      } else {
        state.px = 50; state.py = IDLE_Y; state.rx = 0; state.ry = 0; state.lift = 0;
        state.nx = 0; state.ny = 0; state.fromCenter = 0; state.lit = IDLE_LIT;
        paint();
      }
    }

    function flip() {
      if (!flipper || reduce || !canFlip) return;
      var from = state.flip;
      state.flip = state.flip === 0 ? 180 : 0;
      flipper.classList.toggle("is-flipped", state.flip === 180);
      if (state.flip === 0) {
        closeStoryTray();
      } else {
        requestAnimationFrame(checkStoryOverflow);
      }
      var proxy = { f: from };
      if (hasGsap) {
        global.gsap.to(proxy, {
          f: state.flip,
          duration: 0.7,
          ease: "power3.inOut",
          overwrite: true,
          onUpdate: function () {
            flipper.style.setProperty("--flip", proxy.f + "deg");
          },
          onComplete: function () {
            if (state.flip === 180) checkStoryOverflow();
          }
        });
      } else {
        flipper.style.setProperty("--flip", state.flip + "deg");
        if (state.flip === 180) requestAnimationFrame(checkStoryOverflow);
      }
    }

    function resetFlip() {
      if (state.flip !== 0) {
        state.flip = 0;
        if (flipper) {
          flipper.classList.remove("is-flipped");
          flipper.style.setProperty("--flip", "0deg");
        }
      }
    }

    function onDown(ev) {
      if (ev.button != null && ev.button !== 0) return;
      interacting = true;
      dragging = false;
      moved = 0;
      startX = ev.clientX;
      startY = ev.clientY;
      pointerId = ev.pointerId;
      killReset();
      stage.classList.add("is-dragging");
      try { stage.setPointerCapture(ev.pointerId); } catch (err) {}
      if (coarse) {
        ev.preventDefault();
        setFromPoint(ev.clientX, ev.clientY);
      }
    }

    function onMove(ev) {
      if (pointerId != null && ev.pointerId !== pointerId) return;
      if (pointerId == null && coarse) return;
      if (pointerId != null) {
        var dx = ev.clientX - startX;
        var dy = ev.clientY - startY;
        moved = Math.max(moved, Math.hypot(dx, dy));
        if (moved > 6) dragging = true;
        ev.preventDefault();
      } else if (coarse) {
        return;
      }
      interacting = true;
      killReset();
      setFromPoint(ev.clientX, ev.clientY);
    }

    function onUp(ev) {
      if (pointerId != null && ev.pointerId !== pointerId) return;
      var wasTap = moved < 6;
      pointerId = null;
      try { stage.releasePointerCapture(ev.pointerId); } catch (err) {}
      if (wasTap && !reduce && canFlip) flip();
      springHome();
    }

    function onLeave() {
      if (pointerId != null) return;
      if (!coarse) springHome();
    }

    stage.addEventListener("pointerdown", onDown);
    stage.addEventListener("pointermove", onMove);
    stage.addEventListener("pointerup", onUp);
    stage.addEventListener("pointercancel", onUp);
    stage.addEventListener("lostpointercapture", function () {
      pointerId = null;
      springHome();
    });
    if (!coarse) stage.addEventListener("pointerleave", onLeave);

    /* 卡背故事展开交互 (dad 2026-09-14 需求 2.1 & 2.2 & Brief E)
       仅在 focus (modal) 态且文字真实溢出 (scrollHeight > clientHeight) 时出现展开按钮；
       正文保持透传翻面，只有点击「展开全文 ▾」按钮才呼出打字机托盘 */
    var fullStory = d.story || d.storyShort || "";
    var storyBlock = stage.querySelector(".oracle-back-story") || stage.querySelector(".ccg-back-story");

    function checkStoryOverflow() {
      if (!isFocus || !storyBlock) return;
      var valEl = storyBlock.querySelector(".ccg-back-val");
      if (!valEl) return;
      if (valEl.clientHeight > 0) {
        var overflows = (valEl.scrollHeight > valEl.clientHeight + 1);
        if (overflows) {
          storyBlock.classList.add("has-overflow");
        } else {
          storyBlock.classList.remove("has-overflow");
        }
      }
    }

    var expandBtn = storyBlock ? storyBlock.querySelector(".ccg-story-expand-btn") : null;
    if (expandBtn && isFocus) {
      function stopEvent(e) {
        if (e.stopPropagation) e.stopPropagation();
      }
      expandBtn.addEventListener("pointerdown", stopEvent);
      expandBtn.addEventListener("pointermove", stopEvent);
      expandBtn.addEventListener("pointerup", stopEvent);
      expandBtn.addEventListener("mousedown", stopEvent);
      expandBtn.addEventListener("mouseup", stopEvent);
      expandBtn.addEventListener("click", function (ev) {
        if (ev.stopPropagation) ev.stopPropagation();
        handleStoryTrayToggle(stage, fullStory);
      });
      requestAnimationFrame(checkStoryOverflow);
    }

    var rec = {
      el: stage,
      scheme: scheme,
      state: state,
      flip: flip,
      resetFlip: resetFlip,
      idleSkip: cardIdleSkip || idleSkip,  // F9: per-card override; 0 表示跟随全局 idleSkip
      _idleSkipFrozen: cardIdleSkip > 0,    // setIdleSkip(n) 跳过已固化的卡
      interacting: function () { return interacting; },
      tick: function (t) {
        if (isFocus && !reduce) {
          if (!interacting) {
            var phF = stage._idlePhase || 0;
            var sF = Math.sin((t + phF * 1800) / 1800);
            var cF = Math.cos((t + phF * 2100) / 2100);
            aim.rx = sF * 5.5;
            aim.ry = cF * 7;
            aim.nx = Math.sin((t + phF * 2100) / 2100) * 0.45;
            aim.ny = Math.cos((t + phF * 1800) / 1800) * 0.35;
            aim.px = 50 + aim.nx * 18;
            aim.py = 50 + aim.ny * 14;
            aim.lit = 0.72;
            aim.lift = 0;
            aim.fromCenter = Math.hypot(aim.nx, aim.ny);
          }
          var k = 0.08;
          state.rx += (aim.rx - state.rx) * k;
          state.ry += (aim.ry - state.ry) * k;
          state.nx += (aim.nx - state.nx) * k;
          state.ny += (aim.ny - state.ny) * k;
          state.px += (aim.px - state.px) * k;
          state.py += (aim.py - state.py) * k;
          state.lit += (aim.lit - state.lit) * k;
          state.lift += ((aim.lift || 0) - (state.lift || 0)) * k;
          state.fromCenter = Math.hypot(state.nx, state.ny);
          paint();
          return;
        }
        if (interacting || reduce || resetTween) return;
        /* F6 视口跳过: 卡没在视口里就不 paint (CSS vars 不变, 等于正视图层, 无感).
           用 el._ccgId (mountCard 里赋值) 当 Set key, 避免 DOM ref 持有. */
        if (visObserver && !visVisible.has(stage._ccgId)) return;
        /* F6/F9 idle skip: 每 N 帧 paint 一次. interacting/click-flip 时不跳.
           实时读 rec.idleSkip (per-card 或全局同步值). */
        if (rec.idleSkip > 1 && !interacting) {
          if ((fpsState.frame % rec.idleSkip) !== 0) return;
        }
        /* F6 每张卡加随机相位偏移 — 避免 44 张同款卡同步摇摆. phase ∈ [0, 2π). */
        var ph = stage._idlePhase || 0;
        var s = Math.sin((t + ph * 1800) / 1800);
        var c = Math.cos((t + ph * 2100) / 2100);
        var amp = scheme === "px" ? 3.0 : 3.4;
        state.rx = s * amp;
        state.ry = c * (amp + 0.3);
        state.nx = c * 0.55;
        state.ny = s * 0.55;
        /* 静止光扫只在上带 (金边 + 画面上沿) 游走, 不糊主视觉 */
        state.px = 50 + state.nx * 26;
        state.py = IDLE_Y + state.ny * 12;
        state.fromCenter = Math.hypot(state.nx, state.ny);
        state.lift = 0;
        state.lit = IDLE_LIT;
        paint();
      },
      destroy: function () {
        stage.removeEventListener("pointerdown", onDown);
        stage.removeEventListener("pointermove", onMove);
        stage.removeEventListener("pointerup", onUp);
        stage.removeEventListener("pointercancel", onUp);
        if (!coarse) stage.removeEventListener("pointerleave", onLeave);
        stage._ccgId = null;
      }
    };
    cards.push(rec);
    return rec;
  }

  function unmountAll(root) {
    cards.slice().forEach(function (c) {
      if (!root || root.contains(c.el)) {
        c.destroy();
        cards.splice(cards.indexOf(c), 1);
      }
    });
  }

  /* F14 (sprint 26091302 B6 第五轮): unmount(stage) 按 DOM 节点卸载单张卡.
     用途:
       - 详情弹窗关闭时 (openClaim 的 stage unmount, 避免 setProperty 引用泄漏)
       - 卡墙重渲染时 (switchTab 切 group / modal-toggle 重新挂载前)
     行为: 从 cards 数组摘除 + IO unobserve + 清 class/innerHTML.
     注: 第四轮前 opts.static=true 卡不入 cards 数组, 那段历史已删 — 现在所有卡都进数组. */
  function unmount(stage) {
    if (!stage) return;
    closeStoryTray();
    resetAllFlips();
    var stageEl = (stage.classList && stage.classList.contains("ccg-stage")) ? stage : (stage.querySelector ? stage.querySelector(".ccg-stage") : null);
    if (!stageEl) stageEl = stage;
    var i = cards.findIndex(function (c) { return c.el === stage || c.el === stageEl; });
    if (i >= 0) {
      cards[i].destroy();
      cards.splice(i, 1);
    }
    /* F6: IO unregister (card unmount 时视口不再需要追踪它) */
    if (visObserver && stageEl._ccgId) visVisible.delete(stageEl._ccgId);
    if (visObserver) visObserver.unobserve(stageEl);
    stageEl.classList.remove("ccg-stage", "ccg-holo", "ccg-px", "is-locked", "ccg-no-gsap", "is-ready", "ccg-no-flip");
    stageEl.removeAttribute("data-scheme");
    stageEl.removeAttribute("data-mode");
    stageEl.removeAttribute("data-ccg-theme");
    stageEl.removeAttribute("data-art-tone");
    stageEl.innerHTML = "";
  }

  function pulse(el) {
    var rotator = el.querySelector(".ccg-rotator") || el;
    var proxy = { p: 1 };
    function write() { rotator.style.setProperty("--pulse", proxy.p); }
    if (hasGsap) {
      global.gsap.timeline({ overwrite: true })
        .to(proxy, { p: 0.94, duration: 0.08, ease: "power2.in", onUpdate: write })
        .to(proxy, { p: 1.05, duration: 0.16, ease: "power3.out", onUpdate: write })
        .to(proxy, { p: 1, duration: 0.22, ease: "power3.out", onUpdate: write });
    }
  }

  function burst(originEl) {
    var r = originEl.getBoundingClientRect();
    var cx = r.left + r.width / 2;
    var cy = r.top + r.height / 2;
    var n = reduce ? 6 : 16;
    var i;
    for (i = 0; i < n; i++) {
      var p = document.createElement("span");
      p.className = "ccg-spark";
      p.style.left = cx + "px";
      p.style.top = cy + "px";
      document.body.appendChild(p);
      var ang = (i / n) * Math.PI * 2 + (Math.random() - 0.5) * 0.5;
      var dist = 70 + Math.random() * 110;
      var dx = Math.cos(ang) * dist;
      var dy = Math.sin(ang) * dist - 36;
      if (hasGsap) {
        global.gsap.fromTo(p,
          { x: 0, y: 0, scale: 0.35, opacity: 1, rotation: 0 },
          { x: dx, y: dy, scale: 0.15, opacity: 0, rotation: 80 + Math.random() * 80,
            duration: 0.55 + Math.random() * 0.22, ease: "power2.out",
            onComplete: function (node) { return function () { node.remove(); }; }(p)
        });
      } else {
        p.style.transition = "transform 0.6s ease, opacity 0.6s ease";
        requestAnimationFrame(function (node, x, y) {
          return function () {
            node.style.transform = "translate(" + x + "px," + y + "px) scale(0.2)";
            node.style.opacity = "0";
            setTimeout(function () { node.remove(); }, 650);
          };
        }(p, dx, dy));
      }
    }
  }

  function toast(msg) {
    var t = document.querySelector(".ccg-toast");
    if (!t) {
      t = document.createElement("div");
      t.className = "ccg-toast";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add("is-on");
    clearTimeout(t._tid);
    t._tid = setTimeout(function () { t.classList.remove("is-on"); }, 1600);
  }

  function claim(originEl) {
    pulse(originEl);
    burst(originEl);
    toast("已入库 · 呦呦成就殿堂");
  }

  function bindModal(ov) {
    if (ov.getAttribute("data-ccg-bound") === "1") return;
    ov.setAttribute("data-ccg-bound", "1");
    ov.addEventListener("click", function (e) {
      if (e.target === ov) closeClaim();
    });
    var closer = ov.querySelector(".ccg-claim-close");
    var skip = ov.querySelector("#ccg-claim-skip");
    var btn = ov.querySelector("#ccg-claim-btn");
    if (closer) closer.addEventListener("click", closeClaim);
    if (skip) skip.addEventListener("click", closeClaim);
    if (btn) btn.addEventListener("click", function () {
      var stage = document.getElementById("ccg-claim-stage");
      claim(stage);
      if (currentClaimBadge && currentClaimBadge.id) {
        var claimingId = currentClaimBadge.id;
        try {
          fetch('/api/badge/claim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ badge_id: claimingId })
          }).then(function (res) { return res.json(); })
            .then(function (resData) {
              window.dispatchEvent(new CustomEvent('dizical:badge-claimed', {
                detail: { badge_id: claimingId, result: resData }
              }));
            })
            .catch(function (err) {
              console.error('Failed to claim badge:', err);
            });
        } catch (e) {
          console.error(e);
        }
      }
      setTimeout(closeClaim, 720);
    });
  }

  function ensureModal() {
    var ov = document.getElementById("ccg-claim-overlay");
    if (!ov) {
      ov = document.createElement("div");
      ov.id = "ccg-claim-overlay";
      ov.className = "ccg-claim-overlay";
      ov.innerHTML =
        '<div class="ccg-claim-dialog" role="dialog" aria-modal="true" aria-labelledby="ccg-claim-name">' +
          '<button type="button" class="ccg-claim-close" aria-label="关闭">×</button>' +
          '<div class="ccg-claim-layout">' +
            '<div class="ccg-claim-stage" id="ccg-claim-stage"></div>' +
            '<div class="ccg-claim-copy">' +
              '<div class="ccg-claim-tag" id="ccg-claim-tag"></div>' +
              '<h2 class="ccg-claim-name" id="ccg-claim-name"></h2>' +
              '<p class="ccg-claim-cond" id="ccg-claim-cond"></p>' +
              '<p class="ccg-claim-date" id="ccg-claim-date"></p>' +
              '<p class="ccg-claim-story" id="ccg-claim-story"></p>' +
              '<div class="ccg-claim-actions">' +
                '<button type="button" class="ccg-btn-claim" id="ccg-claim-btn">领取入库</button>' +
                '<button type="button" class="ccg-btn-skip" id="ccg-claim-skip">先去练笛</button>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</div>';
      document.body.appendChild(ov);
    }
    bindModal(ov);
    return ov;
  }

  /* sprint 26091301 B1: 图鉴编号显示 token.
     来源 = 后端 achievements.card_no (图鉴编号, 永久不变) → 'No.%03d' (No.001);
     无值 (未回填) → '—' (破折号), 禁止再写死 '001' 假号.
     兼容: demo 页自带 BADGE.no / payload.no 仍可传入 → parseInt 后同样格式化. */
  function formatCardNo(raw) {
    if (raw === null || raw === undefined || raw === "") return "—";
    var n = parseInt(raw, 10);
    if (isNaN(n)) return String(raw);
    return "No." + ("00" + n).slice(-3);
  }

  /* sprint 26091301 B1: 卡面日期 'YYYY-MM-DD...' → '2026年6月16日' (纯前端格式化, 不动 DB).
     已是中文格式 / 其它字符串 → 原样返回; 空值 → '—'. */
  function formatCardDate(raw) {
    if (raw === null || raw === undefined || raw === "") return "—";
    var s = String(raw).trim();
    var m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
    if (m) return Number(m[1]) + "年" + Number(m[2]) + "月" + Number(m[3]) + "日";
    return s;
  }

  function normalize(data) {
    var d = data || BADGE;
    return {
      id: d.id || BADGE.id,
      name: d.name || BADGE.name,
      tag: d.tag || d.category || BADGE.tag,
      image: d.image || d.image_url || d.badge_url || BADGE.image,
      cond: d.cond || d.cond_text || BADGE.cond,
      story: d.story || d.zh_story || d.description || BADGE.story,
      /* sprint 26091401 F1: 卡背「典故·短板」= 后端 achievements.story_short (≤60 字).
         空 (未播种 / 新 badge) → 回落长典故, 卡背不留白; modal 右侧继续读 d.story 长文. */
      storyShort: d.story_short || d.storyShort || "",
      date: formatCardDate(d.date || d.achieved_at || BADGE.date),
      stars: d.card_stars != null ? d.card_stars
        : (d.stars != null ? d.stars : BADGE.stars),
      /* sprint 26091301 B1: 编号取后端 card_no (无值 → '—', 不再兜底 '001') */
      no: formatCardNo(d.card_no != null ? d.card_no : d.no),
      hall: d.hall || BADGE.hall,
      card_theme: d.card_theme || d.theme || "pearl"
    };
  }

  function openClaim(data, scheme) {
    var d = normalize(data);
    currentClaimBadge = d;
    var ov = ensureModal();
    document.getElementById("ccg-claim-tag").textContent = d.tag;
    document.getElementById("ccg-claim-name").textContent = d.name;
    document.getElementById("ccg-claim-cond").textContent = d.cond;
    document.getElementById("ccg-claim-date").textContent = d.date;
    document.getElementById("ccg-claim-story").textContent = d.story;
    var host = document.getElementById("ccg-claim-stage");
    unmountAll(host);
    host.innerHTML = "";
    var stage = document.createElement("div");
    host.appendChild(stage);
    mountCard(stage, scheme || "holo", d, { mode: "focus", canFlip: true });
    ov.removeAttribute("hidden");
    ov.classList.add("is-open");
    document.body.classList.add("ccg-modal-open");
    document.body.style.overflow = "hidden";
    if (hasGsap) {
      var box = ov.querySelector(".ccg-claim-dialog");
      global.gsap.fromTo(box, { scale: 0.86, opacity: 0, y: 18 },
        { scale: 1, opacity: 1, y: 0, duration: 0.32, ease: "power3.out" });
    }
  }

  function closeClaim() {
    closeStoryTray();
    resetAllFlips();
    currentClaimBadge = null;
    var ov = document.getElementById("ccg-claim-overlay");
    if (!ov) return;
    ov.classList.remove("is-open");
    ov.setAttribute("hidden", "");
    document.body.classList.remove("ccg-modal-open");
    document.body.style.overflow = "";
    unmountAll(document.getElementById("ccg-claim-stage"));
  }

  function checkUnclaimed(scheme) {
    return fetch('/api/badge/unclaimed')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !data.badges || data.badges.length === 0) return null;
        var badge = data.badges[0];
        var s = scheme || localStorage.getItem('dizical_ccg_scheme') || 'holo';
        openClaim(badge, s);
        return badge;
      })
      .catch(function (e) {
        console.debug('Badge claim check skipped:', e);
        return null;
      });
  }

  function loop(t) {
    fpsState.frames += 1;
    fpsState.frame = (fpsState.frame + 1) | 0;  // F6 idle-skip 用 (单调自增)
    if (!fpsState.last) fpsState.last = t;
    if (t - fpsState.last >= 1000) {
      var fps = fpsState.frames;
      fpsState.frames = 0;
      fpsState.last = t;
      if (fpsState.el) {
        fpsState.el.textContent = String(fps);
        fpsState.el.classList.toggle("is-mid", fps < 55 && fps >= 45);
        fpsState.el.classList.toggle("is-low", fps < 45);
      }
    }
    var i;
    for (i = 0; i < cards.length; i++) cards[i].tick(t);
    fpsState.raf = requestAnimationFrame(loop);
  }

  function startFps(el) {
    fpsState.el = el;
    if (!fpsState.raf) fpsState.raf = requestAnimationFrame(loop);
  }

  function setMaxTilt(n) {
    maxTilt = clamp(Number(n) || 15, 4, 24);
  }
  function setHoloGain(n) {
    holoGain = clamp(Number(n) || 1, 0, 1.4);
    cards.forEach(function (c) { applyVars(c.el, c.state); });
  }
  /* F13: setIdleSkip(n, force?) — 默认 force=false 只刷未固化的卡 (per-card mount 时
     idleSkip>0 的卡保持原值); force=true 连已固化的卡也改成 n, 让真机 A/B 实测能把
     44 张列表卡强制拉回 1 全速跑一遍再拉回 2. force 不影响未挂载的卡 (后续 mount 仍按
     opts.idleSkip 决定). */
  function setIdleSkip(n, force) {
    n = Math.max(1, parseInt(n, 10) || 1);
    idleSkip = n;
    var applyAll = !!force;
    for (var i = 0; i < cards.length; i++) {
      if (applyAll || !cards[i]._idleSkipFrozen) cards[i].idleSkip = n;
    }
    /* force=true 时也清掉 _idleSkipFrozen 标记, 后续若再调 setIdleSkip(m) 不带 force,
       已"强制改"的卡会跟随新全局值 — 防止调试切回默认时还有残留固化. */
    if (applyAll) {
      for (var j = 0; j < cards.length; j++) cards[j]._idleSkipFrozen = false;
    }
  }
  /* F13: 返回 IO 状态 + idleSkip 细账 — 调试用.
     idleSkip = 模块全局值 (mountCard 默认 / setIdleSkip(0) 不带 force 时刷此值)
     perCardFrozen = 仍带 _idleSkipFrozen=true 的卡数 (setIdleSkip(2) 不带 force 不会被刷)
     effectiveSkipCounts = {skip: count} 各 idleSkip 值的卡数分布 — 看一眼就知道 44 张是不是都 2.
     forceCapable = true (setIdleSkip 第二个参数支持 force, 强制覆盖所有卡) */
  function getPerfStats() {
    var counts = {};
    for (var i = 0; i < cards.length; i++) {
      var s = cards[i].idleSkip || 1;
      counts[s] = (counts[s] || 0) + 1;
    }
    return {
      ioSupported: !!visObserver,
      visible: visVisible.size,
      total: cards.length,
      idleSkip: idleSkip,
      perCardFrozen: cards.filter(function (c) { return c._idleSkipFrozen; }).length,
      effectiveSkipCounts: counts,
      forceCapable: true,
    };
  }

  if (!fpsState.raf) fpsState.raf = requestAnimationFrame(loop);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeStoryTray();
      closeClaim();
      resetAllFlips();
    }
  });

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t) return;
    if (t.matches && (t.matches(".ccg-claim-overlay, .ccg-claim-close, #modal-overlay") || t.closest(".ccg-claim-close"))) {
      closeStoryTray();
      resetAllFlips();
    }
  }, true);

  global.DizicalCCG = {
    BADGE: BADGE,
    ORACLE_SEALS: ORACLE_SEALS,
    mountCard: mountCard,
    unmount: unmount,
    unmountAll: unmountAll,
    claim: claim,
    openClaim: openClaim,
    closeClaim: closeClaim,
    checkUnclaimed: checkUnclaimed,
    startFps: startFps,
    setMaxTilt: setMaxTilt,
    setHoloGain: setHoloGain,
    setIdleSkip: setIdleSkip,    // F6: 性能护栏 (默认 1, iPad 掉帧调 2)
    getPerfStats: getPerfStats,  // F6: 调试用
    resetAllFlips: resetAllFlips, // dad 2026-09-14 需求 1
    closeStoryTray: closeStoryTray, // dad 2026-09-14 需求 2.7
    flipAll: function () {
      cards.forEach(function (c) { if (c.flip) c.flip(); });
    }
  };
})(window);
