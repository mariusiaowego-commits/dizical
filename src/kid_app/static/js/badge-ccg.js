/* sprint-26091101 — DizicalCCG tilt / holo / parallax / claim
   ── 卡面样式版本: v1.6.0-dev (sprint 26091302 B6 图鉴接线, 四轮定稿)
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
    hall: "呦呦成就殿堂"
  };

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

  function backMarkup(d) {
    return (
      '<div class="ccg-card-back ccg-back-face">' +
        '<div class="ccg-foil-stack">' +
          '<div class="ccg-foil-stock"></div>' +
          '<div class="ccg-foil-shine"></div>' +
          '<div class="ccg-foil-glitter"></div>' +
          '<div class="ccg-foil-glare"></div>' +
          '<div class="ccg-foil-security" aria-hidden="true"></div>' +
        '</div>' +
        '<div class="ccg-back-inner">' +
          '<div class="ccg-back-kicker">' + d.tag + ' · No.' + d.no + '</div>' +
          '<div class="ccg-back-title">' + d.name + '</div>' +
          '<div class="ccg-back-rule"></div>' +
          '<div class="ccg-back-field">' +
            '<div class="ccg-back-lbl">获取条件</div>' +
            '<div class="ccg-back-val">' + (d.cond || "") + '</div>' +
          '</div>' +
          '<div class="ccg-back-field">' +
            '<div class="ccg-back-lbl">获得日</div>' +
            '<div class="ccg-back-val">' + (d.date || "") + '</div>' +
          '</div>' +
          '<div class="ccg-back-field ccg-back-story">' +
            '<div class="ccg-back-lbl">典故</div>' +
            '<div class="ccg-back-val">' + (d.story || "") + '</div>' +
          '</div>' +
          '<div class="ccg-back-foot"><span class="ccg-stars">' + starsHtml(d.stars) + '</span></div>' +
        '</div>' +
        '<div class="ccg-frame"></div>' +
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
    return (
      '<div class="ccg-card-front' + (scheme === "px" ? " ccg-px-front" : "") + '">' +
        '<div class="ccg-foil-stack">' +
          '<div class="ccg-foil-stock"></div>' +
          '<div class="ccg-foil-shine"></div>' +
          '<div class="ccg-foil-glitter"></div>' +
          '<div class="ccg-foil-security" aria-hidden="true"></div>' +
        '</div>' +
        '<div class="ccg-art-frame">' +
          '<div class="ccg-art-window">' + artInner(scheme, d) + '</div>' +
        '</div>' +
        '<div class="ccg-foil-stack ccg-foil-over">' +
          '<div class="ccg-foil-glare"></div>' +
          '<div class="ccg-foil-spec"></div>' +
          '<div class="ccg-foil-laser"></div>' +
        '</div>' +
        '<div class="ccg-frame"></div>' +
        '<div class="ccg-holo-head">' +
          '<span class="ccg-chip">' + d.tag + '</span>' +
          '<span class="ccg-no">No.' + d.no + '</span>' +
        '</div>' +
        '<div class="ccg-info-bar">' +
          '<span class="ccg-bar-no">NO.' + d.no + '</span>' +
          '<span class="ccg-bar-tag">' + d.tag + '</span>' +
          '<span class="ccg-bar-date">' + d.date + '</span>' +
        '</div>' +
        '<div class="ccg-plate">' +
          '<div class="ccg-plate-head">' +
            titleHtml(d.name) +
          '</div>' +
          '<p class="ccg-plate-desc">' + (d.cond || "") + '</p>' +
          /* dad 2026-09-13: 页脚行 (星级 + DIZICAL) 并入说明栏内, 不再单独成块 */
          '<div class="ccg-foot">' +
            '<span class="ccg-stars">' + starsHtml(d.stars) + '</span>' +
            '<span>DIZICAL</span>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function cardMarkup(scheme, d) {
    return (
      '<div class="ccg-shadow"></div>' +
      '<div class="ccg-rotator">' +
        '<div class="ccg-card-flipper">' +
          frontMarkup(scheme, d) +
          backMarkup(d) +
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

  function mountCard(stage, scheme, data, opts) {
    var d = data || BADGE;
    var o = opts || {};
    var isLocked = o.locked === true;
    var stageClasses = "ccg-stage ccg-" + scheme + (isLocked ? " is-locked" : "");
    if (!hasGsap) stageClasses += " ccg-no-gsap";  // F7: 无 gsap 时启用 CSS 过渡翻面
    stage.className = stageClasses;
    stage.setAttribute("data-scheme", scheme);
    /* 主题 (B-1, sprint-26091201): 来自 achievements.card_theme (后端 resolve_card_theme 已做 type 兜底),
       前端只认 payload 字段, 不做第二套映射; d.theme 兼容 demo 页/老数据。
       非默认 4 套变量在 badge-ccg-themes.css, 覆盖 .ccg-stage[data-ccg-theme] */
    stage.setAttribute("data-ccg-theme", d.card_theme || d.theme || "azure");
    stage.innerHTML = cardMarkup(scheme, d);
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
    var state = { px: 50, py: IDLE_Y, rx: 0, ry: 0, lift: 0, flip: 0, nx: 0, ny: 0, fromCenter: 0, lit: IDLE_LIT };
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
      state.px = x * 100;
      state.py = y * 100;
      state.nx = clamp((x - 0.5) * 2, -1, 1);
      state.ny = clamp((y - 0.5) * 2, -1, 1);
      state.fromCenter = clamp(Math.hypot(state.nx, state.ny), 0, 1.4);
      state.rx = clamp(-state.ny * maxTilt, -maxTilt, maxTilt);
      state.ry = clamp(state.nx * maxTilt, -maxTilt, maxTilt);
      state.lift = 20;
      state.lit = 1;
      paint();
    }

    function springHome() {
      interacting = false;
      dragging = false;
      stage.classList.remove("is-dragging");
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
      if (!flipper || reduce) return;
      var from = state.flip;
      state.flip = state.flip === 0 ? 180 : 0;
      flipper.classList.toggle("is-flipped", state.flip === 180);
      var proxy = { f: from };
      if (hasGsap) {
        global.gsap.to(proxy, {
          f: state.flip,
          duration: 0.7,
          ease: "power3.inOut",
          overwrite: true,
          onUpdate: function () {
            flipper.style.setProperty("--flip", proxy.f + "deg");
          }
        });
      } else {
        flipper.style.setProperty("--flip", state.flip + "deg");
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
      if (wasTap && !reduce) flip();
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

    var rec = {
      el: stage,
      scheme: scheme,
      state: state,
      flip: flip,
      idleSkip: cardIdleSkip || idleSkip,  // F9: per-card override; 0 表示跟随全局 idleSkip
      _idleSkipFrozen: cardIdleSkip > 0,    // setIdleSkip(n) 跳过已固化的卡
      interacting: function () { return interacting; },
      tick: function (t) {
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
    var i = cards.findIndex(function (c) { return c.el === stage; });
    if (i >= 0) {
      cards[i].destroy();
      cards.splice(i, 1);
    }
    /* F6: IO unregister (card unmount 时视口不再需要追踪它) */
    if (visObserver && stage._ccgId) visVisible.delete(stage._ccgId);
    if (visObserver) visObserver.unobserve(stage);
    stage.classList.remove("ccg-stage", "ccg-holo", "ccg-px", "is-locked", "ccg-no-gsap", "is-ready");
    stage.removeAttribute("data-scheme");
    stage.removeAttribute("data-ccg-theme");
    stage.innerHTML = "";
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

  function normalize(data) {
    var d = data || BADGE;
    return {
      id: d.id || BADGE.id,
      name: d.name || BADGE.name,
      tag: d.tag || d.category || BADGE.tag,
      image: d.image || d.image_url || d.badge_url || BADGE.image,
      cond: d.cond || d.cond_text || BADGE.cond,
      story: d.story || d.zh_story || d.description || BADGE.story,
      date: d.date || d.achieved_at || BADGE.date,
      stars: d.card_stars != null ? d.card_stars
        : (d.stars != null ? d.stars : BADGE.stars),
      no: d.no || "001",
      hall: d.hall || BADGE.hall
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
    mountCard(stage, scheme || "holo", d);
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
    if (e.key === "Escape") closeClaim();
  });

  global.DizicalCCG = {
    BADGE: BADGE,
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
    flipAll: function () {
      cards.forEach(function (c) { if (c.flip) c.flip(); });
    }
  };
})(window);
