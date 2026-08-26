/* prepare UI 2.0 — 暖色粒子喷流 + v1/v2 切换
   依赖: 页面已有 GSAP CDN (可选增强). 无新依赖. */
(function () {
  var KEY = 'prepare_ui';
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var particleCtl = null;

  function currentUi() {
    return document.documentElement.getAttribute('data-ui') || '2.0';
  }

  function initToggle() {
    var btn = document.getElementById('uiToggle');
    if (!btn) return;
    var label = btn.querySelector('.toggle-label');
    var cur = currentUi();
    if (label) label.textContent = 'v' + cur;
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var next = cur === '2.0' ? '1.0' : '2.0';
      try { localStorage.setItem(KEY, next); } catch (err) {}
      if (particleCtl) particleCtl.destroy();
      var url = new URL(location.href);
      url.searchParams.set('ui', next === '2.0' ? 'v2' : 'v1');
      location.replace(url.toString());
    });
  }

  /* canvas-particle-flow: bezier + trail + glow circle, no shadowBlur */
  function startParticles() {
    var hero = document.getElementById('heroV2');
    var canvas = document.getElementById('pollen');
    if (!hero || !canvas) return null;
    var ctx = canvas.getContext('2d');
    if (!ctx) return null;

    var COLORS = [
      [255, 107, 107],
      [255, 140, 90],
      [232, 180, 188],
      [168, 213, 186],
      [240, 192, 96],
      [184, 212, 232]
    ];

    function Particle(sx, sy, tx, ty, rgb, burst) {
      this.sx = sx; this.sy = sy; this.tx = tx; this.ty = ty;
      this.x = sx; this.y = sy; this.rgb = rgb;
      this.size = burst ? (2.8 + Math.random() * 4) : (2.0 + Math.random() * 3.2);
      this.progress = 0;
      this.speed = (burst ? 0.018 : 0.008) + Math.random() * (burst ? 0.02 : 0.012);
      var dx = tx - sx, dy = ty - sy;
      var dist = Math.sqrt(dx * dx + dy * dy) || 1;
      var px = -dy / dist, py = dx / dist;
      var bulge = (Math.random() - 0.5) * dist * (burst ? 0.55 : 0.32);
      this.cp1x = sx + dx * 0.3 + px * bulge;
      this.cp1y = sy + dy * 0.3 + py * bulge;
      this.cp2x = sx + dx * 0.7 + px * bulge * 0.5;
      this.cp2y = sy + dy * 0.7 + py * bulge * 0.5;
      this.alive = true;
      this.trail = [];
    }
    Particle.prototype.update = function () {
      this.progress += this.speed;
      if (this.progress >= 1) { this.alive = false; return; }
      var t = this.progress, mt = 1 - t;
      this.x = mt * mt * mt * this.sx + 3 * mt * mt * t * this.cp1x + 3 * mt * t * t * this.cp2x + t * t * t * this.tx;
      this.y = mt * mt * mt * this.sy + 3 * mt * mt * t * this.cp1y + 3 * mt * t * t * this.cp2y + t * t * t * this.ty;
      this.trail.push({ x: this.x, y: this.y });
      if (this.trail.length > 5) this.trail.shift();
    };
    Particle.prototype.draw = function (c) {
      var r = this.rgb[0], g = this.rgb[1], b = this.rgb[2];
      for (var i = 0; i < this.trail.length; i++) {
        var a = (i / this.trail.length) * 0.22 * (1 - this.progress * 0.3);
        c.beginPath();
        c.arc(this.trail[i].x, this.trail[i].y, this.size * 0.4, 0, Math.PI * 2);
        c.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + a.toFixed(3) + ')';
        c.fill();
      }
      var a2 = 0.85 - this.progress * 0.35;
      c.beginPath();
      c.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      c.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + a2.toFixed(3) + ')';
      c.fill();
      c.beginPath();
      c.arc(this.x, this.y, this.size * 3, 0, Math.PI * 2);
      c.fillStyle = 'rgba(' + r + ',' + g + ',' + b + ',' + (a2 * 0.08).toFixed(3) + ')';
      c.fill();
    };

    var flow = null;
    var particles = [];
    var raf = 0;
    var bursting = false;
    var listeners = [];

    function on(el, ev, fn, opts) {
      el.addEventListener(ev, fn, opts);
      listeners.push([el, ev, fn, opts]);
    }

    function resize() {
      var rect = hero.getBoundingClientRect();
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = rect.width + 'px';
      canvas.style.height = rect.height + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      flow = { w: rect.width, h: rect.height, cx: rect.width * 0.5, cy: rect.height * 0.46 };
    }

    function color() { return COLORS[(Math.random() * COLORS.length) | 0]; }

    function spawnAt(x, y, n, burst) {
      if (!flow) return;
      for (var i = 0; i < n; i++) {
        var destX, destY;
        if (burst) {
          var ang = Math.random() * Math.PI * 2;
          var dist = 80 + Math.random() * 220;
          destX = x + Math.cos(ang) * dist;
          destY = y + Math.sin(ang) * dist;
        } else {
          destX = flow.cx + (Math.random() - 0.5) * 90;
          destY = flow.cy + (Math.random() - 0.5) * 70;
        }
        particles.push(new Particle(x, y, destX, destY, color(), !!burst));
      }
      if (particles.length > 160) particles.splice(0, particles.length - 160);
    }

    function ambient() {
      if (!flow || reduce) return;
      var x = Math.random() * flow.w;
      var y = flow.h + 8;
      spawnAt(x, y, 1, false);
      var last = particles[particles.length - 1];
      if (last) {
        last.tx = x + (Math.random() - 0.5) * 40;
        last.ty = -20;
      }
    }

    function loop() {
      if (!flow) return;
      ctx.clearRect(0, 0, flow.w, flow.h);
      if (!reduce && Math.random() < 0.45) ambient();
      for (var i = particles.length - 1; i >= 0; i--) {
        var p = particles[i];
        p.update();
        if (!p.alive) particles.splice(i, 1);
        else p.draw(ctx);
      }
      raf = requestAnimationFrame(loop);
    }

    function localXY(e) {
      var rect = hero.getBoundingClientRect();
      var src = (e.touches && e.touches[0]) ? e.touches[0] : e;
      return { x: src.clientX - rect.left, y: src.clientY - rect.top };
    }

    function goSteps() {
      var steps = document.getElementById('stepsSection');
      if (steps) steps.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' });
    }

    resize();
    on(window, 'resize', resize);

    if (!reduce) {
      var seed = 0;
      while (seed++ < 36) ambient();
      raf = requestAnimationFrame(loop);
      on(hero, 'mousemove', function (e) {
        var p = localXY(e);
        spawnAt(p.x, p.y, 2, false);
      });
      /* 限定 preventDefault 只在 canvas 上, 避免整页卡住滚动 */
      on(canvas, 'touchmove', function (e) {
        e.preventDefault();
        var p = localXY(e);
        spawnAt(p.x, p.y, 2, false);
      }, { passive: false });
    }

    on(hero, 'click', function (e) {
      if (e.target.closest('.ui-toggle')) return;
      if (e.target.closest('.hero-v2-bless')) return;
      if (e.target.closest('a')) return;
      if (bursting) return;
      bursting = true;
      var p = localXY(e);
      if (!reduce) spawnAt(p.x, p.y, 48, true);
      var hasGsap = typeof gsap !== 'undefined';
      if (hasGsap && !reduce) {
        gsap.to('#heroV2Copy', { y: -18, opacity: 0, duration: 0.45, ease: 'power2.in' });
        gsap.to('.hero-v2-hint', { opacity: 0, duration: 0.3 });
        setTimeout(function () {
          goSteps();
          gsap.set('#heroV2Copy', { y: 0, opacity: 1, overwrite: 'auto' });
          gsap.set('.hero-v2-hint', { opacity: 1, overwrite: 'auto' });
          bursting = false;
        }, 500);
      } else {
        goSteps();
        bursting = false;
      }
    });

    return {
      destroy: function () {
        if (raf) cancelAnimationFrame(raf);
        raf = 0;
        particles.length = 0;
        listeners.forEach(function (item) {
          item[0].removeEventListener(item[1], item[2], item[3]);
        });
        listeners.length = 0;
        try { canvas.remove(); } catch (err) {}
      }
    };
  }

  function ioReveal() {
    if (reduce) return;
    var hasGsap = typeof gsap !== 'undefined';
    var nodes = document.querySelectorAll(
      '.steps-section .section-label, .steps-section .section-title, .steps-section .step-card, .assignment-card, .cta-float-btn'
    );
    if (!nodes.length) return;
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (ent) {
        if (!ent.isIntersecting) return;
        var el = ent.target;
        if (hasGsap) {
          gsap.fromTo(el, { y: 16 }, { y: 0, duration: 0.5, ease: 'power2.out', overwrite: 'auto' });
        }
        io.unobserve(el);
      });
    }, { threshold: 0.2, rootMargin: '0px 0px -8% 0px' });
    nodes.forEach(function (el) { io.observe(el); });
  }

  function enhanceV2Hero() {
    if (reduce || typeof gsap === 'undefined') return;
    gsap.from('.hero-v2-eyebrow', { y: 10, duration: 0.55, ease: 'power2.out' });
    gsap.from('.hero-v2-bless', { y: 18, duration: 0.7, delay: 0.08, ease: 'power3.out' });
    gsap.from('.hero-v2-row, .hero-v2-sub, .hero-v2-hint', {
      y: 10, duration: 0.5, delay: 0.2, stagger: 0.08, ease: 'power2.out'
    });
  }

  initToggle();

  window.addEventListener('load', function () {
    if (currentUi() !== '2.0') return;
    if (!reduce) particleCtl = startParticles();
    enhanceV2Hero();
    ioReveal();
  });

  window.addEventListener('pagehide', function () {
    if (particleCtl) particleCtl.destroy();
    particleCtl = null;
  });
})();
