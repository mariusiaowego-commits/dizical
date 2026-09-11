/* sprint-26091101 — DizicalCCG tilt / holo / parallax / claim */
(function (global) {
  "use strict";

  var BADGE = {
    id: "assign_pal",
    name: "批改小帮手",
    tag: "突破",
    image: "/static/badges/assign_pal_v2.png",
    cond: "协助完成课后批改",
    story: "细心批改，温故知新。",
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
  var maxTilt = 15;
  var holoGain = 1;
  var cards = [];
  var fpsState = { frames: 0, last: 0, el: null, raf: 0 };
  var currentClaimBadge = null;

  function clamp(n, a, b) { return Math.max(a, Math.min(b, n)); }

  function applyVars(el, s) {
    el.style.setProperty("--pointer-x", s.px + "%");
    el.style.setProperty("--pointer-y", s.py + "%");
    el.style.setProperty("--rotate-x", s.rx + "deg");
    el.style.setProperty("--rotate-y", s.ry + "deg");
    el.style.setProperty("--holo-gain", String(holoGain));
    el.style.setProperty("--lift", s.lift ? s.lift + "px" : "0px");
  }

  function starsHtml(n) {
    var i, out = "";
    for (i = 0; i < n; i++) out += '<span class="ccg-star"></span>';
    return out;
  }

  function holoMarkup(d) {
    return (
      '<div class="ccg-shadow"></div>' +
      '<div class="ccg-rotator">' +
        '<div class="ccg-face ccg-holo-face">' +
          '<div class="ccg-holo-stock"></div>' +
          '<div class="ccg-holo-shine"></div>' +
          '<div class="ccg-holo-art"><img alt="" width="512" height="512" decoding="async" fetchpriority="high" src="' + d.image + '"></div>' +
          '<div class="ccg-holo-glare"></div>' +
          '<div class="ccg-frame"></div>' +
          '<span class="ccg-corner tl"></span><span class="ccg-corner tr"></span>' +
          '<span class="ccg-corner bl"></span><span class="ccg-corner br"></span>' +
          '<div class="ccg-holo-head"><span class="ccg-chip">' + d.tag + '</span><span class="ccg-no">No.' + d.no + '</span></div>' +
          '<div class="ccg-meta">' +
            '<div class="ccg-kicker">ACHIEVEMENT</div>' +
            '<div class="ccg-title">' + d.name + '</div>' +
            '<div class="ccg-sub">' + d.date + '</div>' +
            '<div class="ccg-stars">' + starsHtml(d.stars) + '</div>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function parallaxMarkup(d) {
    return (
      '<div class="ccg-shadow"></div>' +
      '<div class="ccg-flip-hint">轻点翻转 · 拖动把玩</div>' +
      '<div class="ccg-rotator">' +
        '<div class="ccg-px-flipper">' +
          '<div class="ccg-px-front">' +
            '<div class="ccg-layer ccg-layer-bg"></div>' +
            '<div class="ccg-layer ccg-layer-holo"></div>' +
            '<div class="ccg-layer ccg-layer-subject"><img alt="" width="512" height="512" decoding="async" fetchpriority="high" src="' + d.image + '"></div>' +
            '<div class="ccg-layer ccg-layer-frame"></div>' +
            '<div class="ccg-layer ccg-layer-text">' +
              '<div class="ccg-kicker">' + d.tag + ' · No.' + d.no + '</div>' +
              '<div class="ccg-title">' + d.name + '</div>' +
              '<div class="ccg-sub">' + d.date + '</div>' +
            '</div>' +
          '</div>' +
          '<div class="ccg-px-back">' +
            '<div class="ccg-px-seal"><span>笛</span></div>' +
            '<div class="hall">' + d.hall + '</div>' +
            '<div class="bname">' + d.name + '</div>' +
            '<div class="serial">No. ' + d.no + '</div>' +
            '<div class="brand">dizical</div>' +
          '</div>' +
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

  function mountCard(stage, scheme, data) {
    var d = data || BADGE;
    stage.className = "ccg-stage ccg-" + scheme;
    stage.setAttribute("data-scheme", scheme);
    stage.innerHTML = scheme === "px" ? parallaxMarkup(d) : holoMarkup(d);
    bindReady(stage);

    var state = { px: 50, py: 50, rx: 0, ry: 0, lift: 0, flip: 0 };
    var interacting = false;
    var dragging = false;
    var moved = 0;
    var startX = 0, startY = 0;
    var pointerId = null;
    var resetTween = null;

    applyVars(stage, state);
    if (scheme === "px") {
      stage.querySelector(".ccg-px-flipper").style.setProperty("--flip", "0deg");
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
      state.rx = clamp(-(y - 0.5) * 2 * maxTilt, -maxTilt, maxTilt);
      state.ry = clamp((x - 0.5) * 2 * maxTilt, -maxTilt, maxTilt);
      state.lift = 10;
      applyVars(stage, state);
    }

    function springHome() {
      interacting = false;
      dragging = false;
      stage.classList.remove("is-dragging");
      if (reduce) {
        state.px = 50; state.py = 50; state.rx = 0; state.ry = 0; state.lift = 0;
        applyVars(stage, state);
        return;
      }
      if (hasGsap) {
        killReset();
        resetTween = global.gsap.to(state, {
          px: 50, py: 50, rx: 0, ry: 0, lift: 0,
          duration: 0.6,
          ease: "power3.out",
          overwrite: true,
          onUpdate: function () { applyVars(stage, state); }
        });
      } else {
        state.px = 50; state.py = 50; state.rx = 0; state.ry = 0; state.lift = 0;
        applyVars(stage, state);
      }
    }

    function flip() {
      if (scheme !== "px") return;
      var from = state.flip;
      state.flip = state.flip === 0 ? 180 : 0;
      var flipper = stage.querySelector(".ccg-px-flipper");
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
        if (moved > 8) dragging = true;
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
      var wasTap = moved < 8;
      pointerId = null;
      try { stage.releasePointerCapture(ev.pointerId); } catch (err) {}
      if (wasTap && scheme === "px" && !reduce) flip();
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
      interacting: function () { return interacting; },
      tick: function (t) {
        if (interacting || reduce || resetTween) return;
        var s = Math.sin(t / 1800);
        var c = Math.cos(t / 2100);
        var amp = scheme === "px" ? 6.2 : 3.2;
        state.rx = s * amp;
        state.ry = c * (amp + 0.4);
        state.px = 50 + c * 16;
        state.py = 50 + s * 12;
        state.lift = 0;
        applyVars(stage, state);
      },
      destroy: function () {
        stage.removeEventListener("pointerdown", onDown);
        stage.removeEventListener("pointermove", onMove);
        stage.removeEventListener("pointerup", onUp);
        stage.removeEventListener("pointercancel", onUp);
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
      stars: d.stars || BADGE.stars,
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

  if (!fpsState.raf) fpsState.raf = requestAnimationFrame(loop);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeClaim();
  });

  global.DizicalCCG = {
    BADGE: BADGE,
    mountCard: mountCard,
    unmountAll: unmountAll,
    claim: claim,
    openClaim: openClaim,
    closeClaim: closeClaim,
    checkUnclaimed: checkUnclaimed,
    startFps: startFps,
    setMaxTilt: setMaxTilt,
    setHoloGain: setHoloGain
  };
})(window);
