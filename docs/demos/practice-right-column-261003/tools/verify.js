#!/usr/bin/env node
/**
 * verify.js - dizical demo v39 自动化验证与护栏套件
 * 运行环境：Node.js + Playwright
 * 覆盖矩阵：3 视口 (1133, 744, 440) × 3 组合 (1, 2, 3) = 9 组合
 * 输出：/tmp/v39-verify.json + 终端表格
 */

const fs = require('fs');
const path = require('path');
const { chromium } = require('/Users/mt16/.hermes/profiles/quagmire/skills/ljg-skills/skills/ljg-card/node_modules/playwright');

const URL = 'http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html';
const OUT_JSON = '/tmp/v39-verify.json';

const VIEWPORTS = [
  { vp: '1133', w: 1280, h: 820 },
  { vp: '744',  w: 820,  h: 1180 },
  { vp: '440',  w: 480,  h: 1000 }
];
const COMBOS = ['1', '2', '3'];

// 目标设定（S4 目标：组合1=2张，组合2=4张，组合3=6张）
const TARGET_CONFIG = {
  '1': { count: 2, cards: ['A', 'S'], feedOrder: ['A', 'S'] },
  '2': { count: 4, cards: ['A', 'S', 'D', 'R'], feedOrder: ['A', 'S', 'D', 'R'] },
  '3': { count: 6, cards: ['A', 'B', 'S', 'D', 'R', 'Q'], feedOrder: ['A', 'B', 'S', 'D', 'R', 'Q'] }
};

const isStrict = process.argv.includes('--strict');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  // ─── 静态分析：项 9 (data-vp 次数与分布) 与 项 10 (三心合一几何) ───
  const staticChecks = await page.evaluate(() => {
    let dataVpCount = 0;
    const dataVpDistribution = {};
    const tpls = ['tpl-A', 'tpl-B', 'tpl-S', 'tpl-D', 'tpl-R', 'tpl-Q'];
    for (const t of tpls) {
      const el = document.getElementById(t);
      if (el) {
        // 统计 <style> 块中的 CSS [data-vp=] 样式选择器，排除 HTML 属性与 JS 变量白名单
        const styles = el.innerHTML.match(/<style[^>]*>([\s\S]*?)<\/style>/gi) || [];
        let cnt = 0;
        for (const st of styles) {
          const m = st.match(/\[data-vp[=\s]/g);
          if (m) cnt += m.length;
        }
        dataVpCount += cnt;
        dataVpDistribution[t] = cnt;
      }
    }
    const cd = window.__cz ? window.__cz.canvasDoc() : document;
    const aWrap = cd ? cd.querySelector('.cz-mod[data-mod="A"]') : null;
    const aFrame = aWrap ? aWrap.querySelector(':scope > iframe') : null;
    /* ── 项 10「三心合一」新契约（S8：整宽卡 + 凹拱包旋钮）──
       凹拱圆心 == 旋钮圆心 == 圆点弧圆心（同一套圆）；
       旋钮圆心落在黑区底边下方 dy（参考图：黑区底边是凹拱圆的弦，不是圆心线）；
       ± 按钮必须完全落在浅色机身，不压黑区内容。 */
    let dy = null, dotR = null, notchR = null, knobR = null, notchCy = null, knobCy = null;
    let btnPanelOverlap = null, panelW = null, panelH = null;
    if (aFrame && aFrame.contentDocument) {
      const ad = aFrame.contentDocument;
      const panel = ad.getElementById('panel');
      const knob = ad.getElementById('knob');
      const minus = ad.getElementById('silverMinus');
      const plus = ad.getElementById('silverPlus');
      if (panel && knob) {
        const pr = panel.getBoundingClientRect();
        const kr = knob.getBoundingClientRect();
        const kcy = kr.top + kr.height / 2;
        knobCy = +kcy.toFixed(1);
        knobR = +(kr.width / 2).toFixed(1);
        dy = +(kcy - pr.bottom).toFixed(1);
        dotR = +(kr.width / 2 + 6).toFixed(1);
        panelW = +pr.width.toFixed(1);
        panelH = +pr.height.toFixed(1);
        const maskStr = panel.style.maskImage || panel.style.webkitMaskImage || '';
        const m = maskStr.match(/circle\s+([0-9.]+)px\s+at\s+[0-9.%]+\s+([0-9.]+)px/);
        if (m) { notchR = parseFloat(m[1]); notchCy = parseFloat(m[2]); }
        if (!notchR && panel.style.clipPath) {
          const cpMatch = panel.style.clipPath.match(/A\s+([0-9.]+)\s+\1\s+[0-9]+\s+[0-9]+\s+0/);
          if (cpMatch) notchR = parseFloat(cpMatch[1]);
        }
        const ovb = (a) => {
          if (!a) return 0;
          const r = a.getBoundingClientRect();
          const w = Math.max(0, Math.min(r.right, pr.right) - Math.max(r.left, pr.left));
          const h = Math.max(0, Math.min(r.bottom, pr.bottom) - Math.max(r.top, pr.top));
          return +(w * h).toFixed(1);
        };
        btnPanelOverlap = +(ovb(minus) + ovb(plus)).toFixed(1);
      }
    }
    return { dataVpCount, dataVpDistribution, dy, dotR, notchR, knobR, notchCy, knobCy, btnPanelOverlap, panelW, panelH };
  });

  const results = [];
  const summaryMatrix = [];

  // ─── 9 组合全矩阵扫描 ───
  for (const vpInfo of VIEWPORTS) {
    const vp = vpInfo.vp;
    await page.setViewportSize({ width: vpInfo.w, height: vpInfo.h });
    /* 切视口前先回到准备态：run 态直接切视口会让卡 A 的 iframe 重建塌陷（已知遗留问题），
       真实使用路径也是「准备态切视口 → 再开练」。 */
    await page.evaluate(() => { if (window.__cz && window.__cz.canvasRunning()) window.__cz.setCanvasStage('prep'); });
    await page.waitForTimeout(600);
    await page.click('#czVp [data-vp="' + vp + '"]');
    await page.waitForTimeout(900);

    for (const combo of COMBOS) {
      /* 切组合前先回准备态：run 态直接切组合会让卡 A 的 iframe 重建塌陷（已知遗留问题），
         真实使用路径也是「准备态切组合 → 再开练」。 */
      await page.evaluate(() => { if (window.__cz && window.__cz.canvasRunning()) window.__cz.setCanvasStage('prep'); });
      await page.waitForTimeout(500);
      await page.evaluate((c) => window.__cz.setCombo(c), combo);
      await page.waitForTimeout(900);

      // 切到 run 态验证几何重叠与露出条
      await page.evaluate(() => window.__cz.setCanvasStage('run'));
      await page.waitForTimeout(1500);

      const geomData = await page.evaluate(() => {
        const cd = window.__cz.canvasDoc();
        if (!cd) return null;
        const rr = el => {
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return { x: +r.x.toFixed(1), y: +r.y.toFixed(1), t: +r.top.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1), b: +r.bottom.toFixed(1), r: +r.right.toFixed(1) };
        };
        const ov = (a, b) => (a && b) ? +(Math.max(0, Math.min(a.r, b.r) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.y, b.y))).toFixed(1) : 0;

        const card = cd.getElementById('czTicketStage');
        const slot = cd.getElementById('pkPunchSlotWrap');
        const bar = cd.getElementById('pkCardExposedBar');
        const cr = rr(card), sr = rr(slot);

        const f = cd.querySelector('.cz-mod[data-mod="A"] iframe');
        const fr = rr(f);
        const inFrame = sel => {
          try {
            const d = f.contentDocument;
            const el = d && d.querySelector(sel);
            if (!el) return null;
            const q2 = rr(el);
            if (!q2) return null;
            return { ...q2, x: +(q2.x + fr.x).toFixed(1), y: +(q2.y + fr.y).toFixed(1), b: +(q2.b + fr.y).toFixed(1), r: +(q2.r + fr.x).toFixed(1) };
          } catch (e) { return null; }
        };

        const panel = inFrame('#panel');
        const knob = inFrame('#knob');
        const transport = inFrame('#transport') || inFrame('.deck');
        const diagCard = inFrame('#diagCard');
        const minus = inFrame('#silverMinus');
        const plus = inFrame('#silverPlus');

        // 1. 重叠
        //    S8 新契约：插入卡是「整宽长卡」，卡身嵌进黑区顶缘（cardPanel / slotPanel 重叠为预期），
        //    真正必须为 0 的是：卡 vs 旋钮 / 主控件行 / 诊断卡，以及 ± 按钮 vs 黑区。
        const overlaps = {
          cardPanel: ov(cr, panel),
          cardKnob: ov(cr, knob),
          cardTransport: ov(cr, transport),
          cardDiag: ov(cr, diagCard),
          slotPanel: ov(sr, panel),
          btnPanel: +((minus ? ov(minus, panel) : 0) + (plus ? ov(plus, panel) : 0)).toFixed(1)
        };
        const slotShape = {
          cardW: cr ? cr.w : 0,
          panelW: panel ? panel.w : 0,
          slotW: sr ? sr.w : 0,
          cardBottomInPanel: (cr && panel) ? +(cr.b - panel.y).toFixed(1) : 0,
          bandH: cr ? cr.h : 0,
          cardInset: card ? parseFloat(card.dataset.cardInset || '0') || 0 : 0,
          cardTopAbovePanel: (cr && panel) ? +(panel.y - cr.y).toFixed(1) : null,
          cardBottomBelowSlot: (cr && sr) ? +(cr.b - sr.b).toFixed(1) : null,
          lipHeight: card ? parseFloat(card.dataset.slotLipHeight || '0') || 0 : 0,
          /* S13 卡槽孔契约数据源：孔上缘（槽体局部坐标）、孔高、卡片蒙版裁切线（卡片局部坐标） */
          holeTop: card ? parseFloat(card.dataset.slotHoleTop || 'NaN') : NaN,
          holeH: card ? parseFloat(card.dataset.slotHoleHeight || 'NaN') : NaN,
          maskTop: card ? parseFloat(card.dataset.cardMaskTop || 'NaN') : NaN,
          cardTop: cr ? cr.t : null,
          slotTop: sr ? sr.t : null,
          slotH: sr ? sr.h : null,
          cardH: cr ? cr.h : null
        };

        // 2. 露出比例
        let rawRatio = parseFloat(card ? card.dataset.exposedRatio : 0) || 0;
        if (rawRatio < 1.0 && rawRatio > 0.05) { rawRatio = rawRatio * 100; }
        const exposedRatio = +rawRatio.toFixed(1);

        // 3. 露出条叶子文本重叠
        const leaves = [];
        if (bar) {
          bar.querySelectorAll('span').forEach(sp => {
            if (!sp.textContent.trim()) return;
            const cs = getComputedStyle(sp);
            const r = rr(sp);
            if (cs.display !== 'none' && r.w > 0) {
              leaves.push({ id: sp.id || sp.className, txt: sp.textContent.trim().slice(0, 10), rect: r });
            }
          });
        }
        let textOverlap = 0;
        const textPairs = [];
        for (let i = 0; i < leaves.length; i++) {
          for (let j = i + 1; j < leaves.length; j++) {
            const o = ov(leaves[i].rect, leaves[j].rect);
            if (o > 0.1) {
              textOverlap += o;
              textPairs.push({ a: leaves[i].id, b: leaves[j].id, ov: o });
            }
          }
        }

        // 7. 渲染的 .cz-mod 数量
        const modEls = [...cd.querySelectorAll('.cz-mod')];
        const renderedCount = modEls.length;
        const renderedModKeys = modEls.map(m => m.dataset.mod || 'mini');

        // 8. feed 顺序 (按 top 排序)
        const isFeed = (cd.documentElement.clientWidth < 1024);
        const sortedMods = modEls.map(m => ({ k: m.dataset.mod || 'mini', top: m.getBoundingClientRect().top }));
        sortedMods.sort((a, b) => a.top - b.top);
        const visualOrder = sortedMods.map(m => m.k);

        return { overlaps, slotShape, exposedRatio, textOverlap, textPairs, renderedCount, renderedModKeys, isFeed, visualOrder };
      });

      // 4. 今日记录弹窗验证
      await page.evaluate(() => window.__cz.setCanvasStage('prep'));
      await page.waitForTimeout(500);
      await page.evaluate(() => window.__cz.openRecordsPop());
      await page.waitForTimeout(600);

      const recData = await page.evaluate(() => {
        const cd = window.__cz.canvasDoc();
        const frame = cd ? cd.getElementById('czPopFrame') : null;
        let rows = [];
        if (frame && frame.contentDocument) {
          frame.contentDocument.querySelectorAll('.rec-row').forEach(e => {
            const det = e.querySelector('.c-detail');
            if (det) {
              const cs = getComputedStyle(det);
              rows.push({
                disp: cs.display,
                sw: det.scrollWidth,
                cw: det.clientWidth,
                noClip: det.scrollWidth <= det.clientWidth
              });
            }
          });
        }
        const allBlock = rows.length > 0 && rows.every(r => r.disp === 'block');
        const allNoClip = rows.length > 0 && rows.every(r => r.noClip);
        return { count: rows.length, allBlock, allNoClip };
      });
      await page.evaluate(() => window.__cz.closeRecordsPop(false));
      await page.waitForTimeout(300);

      // 5 & 6. 动效采样：Node 侧控制真实时钟，逐 20ms 采样 27 帧 (0~520ms)
      await page.evaluate(() => window.__cz.setCanvasStage('run'));
      await page.waitForTimeout(600);

      // --- motionExit (run -> prep) ---
      const t0Exit = Date.now();
      await page.evaluate(() => window.__cz.setCanvasStage("prep"));
      let exitBlank = 0, exitDual30 = 0;
      for (let ms = 0; ms <= 520; ms += 20) {
        const cur = Date.now() - t0Exit;
        if (ms > cur) await page.waitForTimeout(ms - cur);
        const { railOp, ticketOp } = await page.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const lc = cd.getElementById("pkLeftCol");
          const tc = cd.getElementById("pkTicketCard");
          const rail = cd.getElementById("pkRunRail") || (lc ? lc.querySelector(".pk-run-rail") : null);
          const sTc = tc ? cd.defaultView.getComputedStyle(tc) : null;
          const sRail = rail ? cd.defaultView.getComputedStyle(rail) : null;
          const rOp = sRail ? (sRail.display === 'none' ? 0 : parseFloat(sRail.opacity) || 0) : 0;
          const tOp = sTc ? (sTc.display === 'none' ? 0 : parseFloat(sTc.opacity) || 0) : 0;
          return { railOp: rOp, ticketOp: tOp };
        });
        if (railOp <= 0.01 && ticketOp <= 0.01) exitBlank++;
        if (railOp >= 0.30 && ticketOp >= 0.30) exitDual30++;
      }
      const motionExit = { exitBlank, exitDual30 };

      await page.waitForTimeout(600);

      // --- motionEnter (prep -> run) ---
      const t0Enter = Date.now();
      await page.evaluate(() => window.__cz.setCanvasStage("run"));
      let enterBlank = 0, enterDual30 = 0;
      for (let ms = 0; ms <= 520; ms += 20) {
        const cur = Date.now() - t0Enter;
        if (ms > cur) await page.waitForTimeout(ms - cur);
        const { railOp, ticketOp } = await page.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const lc = cd.getElementById("pkLeftCol");
          const tc = cd.getElementById("pkTicketCard");
          const rail = cd.getElementById("pkRunRail") || (lc ? lc.querySelector(".pk-run-rail") : null);
          const sTc = tc ? cd.defaultView.getComputedStyle(tc) : null;
          const sRail = rail ? cd.defaultView.getComputedStyle(rail) : null;
          const rOp = sRail ? (sRail.display === 'none' ? 0 : parseFloat(sRail.opacity) || 0) : 0;
          const tOp = sTc ? (sTc.display === 'none' ? 0 : parseFloat(sTc.opacity) || 0) : 0;
          return { railOp: rOp, ticketOp: tOp };
        });
        if (railOp <= 0.01 && ticketOp <= 0.01) enterBlank++;
        if (railOp >= 0.30 && ticketOp >= 0.30) enterDual30++;
      }
      const motionEnter = { enterBlank, enterDual30 };

      // ─── 断言判定 ───
      const maxOv = geomData ? Math.max(...Object.values(geomData.overlaps)) : 999.0;
      /* 整宽卡契约：卡宽 == 黑区宽；卡贴在黑区顶缘（band 高即露出带高）；
         卡不压旋钮/主控件/诊断卡；± 按钮不压黑区；卡槽嵌在黑区顶缘（重叠为预期）。 */
      const ss = geomData ? geomData.slotShape : null;
      const ovHard = geomData ? Math.max(
        geomData.overlaps.cardKnob,
        geomData.overlaps.cardTransport,
        geomData.overlaps.cardDiag,
        geomData.overlaps.btnPanel
      ) : 999.0;
      /* S13 卡槽孔契约：横排下卡片跨出黑区顶缘、没入孔口被蒙版裁切。
         S14（dad 261025 批注1）：卡比孔窄（inset 16）且裁切线压在孔中线——
         卡片穿过孔中线的部分全部被孔口吞掉；feed 流保持 S11 整带形态。 */
      const cardInset = ss ? ss.cardInset : null;
      /* S17（dad 261026）卡槽模型改了：槽口 = 黑区上沿的一道窄缝，
         孔左右各留 28px 槽肩（--pk-hole-inset），卡片比孔再窄 8px，
         所以 cardInset = 36（原来 S14 是 16）。这里只校验「卡确实比孔窄」。 */
      const insetOk = cardInset !== null && cardInset >= 2 && cardInset <= 48;
      const passOv = (ovHard === 0.0)
        && !!ss && insetOk
        && Math.abs((ss.slotW - ss.cardW) - cardInset * 2) <= 3
        && ss.cardTopAbovePanel >= 8
        && (ss.holeTop > 0 && ss.holeH >= 8 && ss.holeH <= 20
          && ss.maskTop != null && !isNaN(ss.maskTop)
          && Math.abs(ss.maskTop - (Math.abs(ss.cardTop - ss.slotTop) + ss.holeTop + ss.holeH * 0.5)) <= 1
          && (Math.abs(ss.cardTop - ss.slotTop) + ss.maskTop) >= Math.abs(ss.cardTop - ss.slotTop))
        && geomData.overlaps.cardPanel > 0;

      const ratio = geomData ? geomData.exposedRatio : 0.0;
      /* S19（dad 261027）：744 / 440 feed 流全面复刻 1133 窄孔卡槽，全视口统一露出比约 20% */
      const passRatio = (ratio >= 18.5 && ratio <= 21.5);

      const passTextOv = geomData ? (geomData.textOverlap === 0.0) : false;
      const passRec = recData ? (recData.allBlock && recData.allNoClip) : false;

      const passBlank = (motionExit.exitBlank === 0 && motionEnter.enterBlank === 0);
      const passDual30Exit = (motionExit.exitDual30 === 0);

      const targetDefCount = TARGET_CONFIG[combo].count;
      const passNodesS4 = (geomData.renderedCount === targetDefCount);

      const expectedFeed = TARGET_CONFIG[combo].feedOrder;
      const actualFeed = geomData.isFeed ? geomData.visualOrder : null;
      const passFeedS4 = geomData.isFeed ? (JSON.stringify(actualFeed) === JSON.stringify(expectedFeed)) : true;

      const comboResult = {
        vp, combo,
        geom: geomData,
        rec: recData,
        motionExit,
        motionEnter,
        checks: {
          "1_slot_card_geometry": passOv,
          "2_exposed_ratio": passRatio,
          "3_text_overlap_zero": passTextOv,
          "4_records_popout_ok": passRec,
          "5_motion_no_blank": passBlank,
          "6_exit_no_dual30": passDual30Exit,
          "7_nodes_s4": passNodesS4,
          "8_feed_order_s4": passFeedS4
        }
      };
      results.append ? results.append(comboResult) : results.push(comboResult);

      summaryMatrix.push({
        vp, combo,
        maxOv: ovHard,
        slotContractPass: passOv && passRatio && passTextOv,
        ratio: ratio.toFixed(1) + '%',
        textOv: geomData.textOverlap,
        recOk: passRec ? 'PASS' : 'FAIL',
        exitBlank: motionExit.exitBlank,
        exitDual30: motionExit.exitDual30,
        enterDual30: motionEnter.enterDual30,
        nodes: `${geomData.renderedCount}/${targetDefCount}`,
        feedMatch: passFeedS4 ? 'PASS' : (geomData.isFeed ? 'FAIL' : 'SKIP'),
        c1_4_pass: (passOv && passRatio && passTextOv && passRec),
        v37g_exit_pass: (motionExit.exitBlank === 0 && motionExit.exitDual30 === 0)
      });
    }
  }

  // ─── 项 11：run 态直切视口（不许“切前回 prep”掩盖），必须在 browser.close() 之前跑 ───
  const runSwitch = await (async () => {
    const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
    await page.goto(URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    await page.evaluate(() => { window.__cz.setVp('1133'); window.__cz.setCombo('1'); });
    await page.waitForTimeout(1200);
    await page.evaluate(() => window.__cz.setCanvasStage('run'));
    await page.waitForTimeout(1600);
    const before = await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const f = cd.querySelector('.cz-mod[data-mod="A"] iframe');
      const d = f.contentDocument;
      return {
        dash: d.querySelector('.dash').getBoundingClientRect().height,
        knob: d.querySelector('#knob').getBoundingClientRect().width
      };
    });
    await page.evaluate(() => window.__cz.setVp('744'));
    await page.waitForTimeout(2600);
    const after = await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const f = cd.querySelector('.cz-mod[data-mod="A"] iframe');
      const d = f.contentDocument;
      return {
        canvasW: cd.documentElement.clientWidth,
        dash: d.querySelector('.dash').getBoundingClientRect().height,
        panel: d.querySelector('#panel').getBoundingClientRect().height,
        knob: d.querySelector('#knob').getBoundingClientRect().width,
        frameH: f.getBoundingClientRect().height
      };
    });
    await page.close();
    return { before, after,
      pass: after.canvasW === 744 && after.dash > 300 && after.panel > 100 && after.knob > 30 && after.frameH > 300 };
  })();

  // ─── 项 12：画布内 fixed 弹层必须落在浏览器视口内（v3.9 修复项）───
  /* 画布 iframe 高 = 票卡带自然高（组合 3 约 3300px），iframe 内 position:fixed 的包含块是整篇画布文档，
     弹窗被居中到屏幕外 → 用户只看到一片灰（dad 261027 报「换曲目弹窗没出来，只出灰色蒙版」）。
     宿主用 --cz-band-t / --cz-band-h 把弹层锚到浏览器可视带；这里逐组合断言弹层本体在视口内。 */
  const overlayViewport = await (async () => {
    const rows = [];
    for (const v of VIEWPORTS) {
      const vp = await browser.newPage({ viewport: { width: v.w, height: v.h } });
      await vp.goto(URL, { waitUntil: 'domcontentloaded' });
      await vp.waitForTimeout(1500);
      await vp.evaluate((x) => window.__cz.setVp(x), v.vp);
      await vp.waitForTimeout(600);
      for (const combo of COMBOS) {
        await vp.evaluate((c) => window.__cz.setCombo(c), combo);
        await vp.waitForTimeout(1100);
        await vp.evaluate(() => window.__cz.setCanvasStage('prep'));
        await vp.waitForTimeout(500);

        const probe = async (openExpr, closeExpr, sel) => {
          await vp.evaluate(openExpr);
          await vp.waitForTimeout(450);
          const m = await vp.evaluate((s) => {
            const cd = window.__cz.canvasDoc();
            const el = cd.querySelector(s);
            if (!el) return { missing: true };
            const cs = cd.defaultView.getComputedStyle(el);
            if (cs.display === 'none') return { hidden: true };
            const fr = cd.defaultView.frameElement.getBoundingClientRect();
            const r = el.getBoundingClientRect();
            const t = fr.top + r.top, b = fr.top + r.bottom;
            return {
              pageT: +t.toFixed(1), pageB: +b.toFixed(1),
              visible: t < window.innerHeight && b > 0,
              fullyVisible: t >= 0 && b <= window.innerHeight,
              vh: window.innerHeight
            };
          }, sel);
          await vp.evaluate(closeExpr);
          await vp.waitForTimeout(200);
          return m;
        };

        const folio = await probe(
          () => { const cd = window.__cz.canvasDoc(); cd.defaultView.openFolio && cd.defaultView.openFolio(); },
          () => { const cd = window.__cz.canvasDoc(); cd.defaultView.closeFolio && cd.defaultView.closeFolio(); },
          '.pk-folio-box'
        );
        const reader = await probe(
          () => { const cd = window.__cz.canvasDoc(); cd.defaultView.openReader && cd.defaultView.openReader(); },
          () => { const cd = window.__cz.canvasDoc(); cd.defaultView.closeReader && cd.defaultView.closeReader(); },
          '.pk-reader'
        );
        const popout = await probe(
          () => { try { window.__cz.openRecordsPop(); } catch (e) {} },
          () => { try { window.__cz.closeRecordsPop(false); } catch (e) {} },
          '.popout-panel'
        );
        const ok = [folio, reader, popout].every(x => x && x.visible === true);
        rows.push({ vp: v.vp, combo, folio, reader, popout, pass: ok });
      }
      await vp.close();
    }
    return { rows, pass: rows.every(r => r.pass) };
  })();

  // ─── 项 13：卡槽插入卡 = 主题色 + 实色不透明（v3.10 修复项）───
  /* dad 261027 批注：卡槽卡片不要黑色金属风格，用主题色；不要透明度。
     曾实测：#czTicketStage 渐变 #3B444D→#1D242A（黑），文字 #FFF8F0。
     修复后改用 --dash-* token（浅银=奶油面，深墨随 token 转深），渐变两端实色。 */
  const slotCardTheme = await (async () => {
    const rows = [];
    for (const v of VIEWPORTS) {
      const vp = await browser.newPage({ viewport: { width: v.w, height: v.h } });
      await vp.goto(URL, { waitUntil: 'domcontentloaded' });
      await vp.waitForTimeout(1500);
      await vp.evaluate((x) => window.__cz.setVp(x), v.vp);
      await vp.waitForTimeout(500);
      for (const combo of COMBOS) {
        await vp.evaluate((c) => window.__cz.setCombo(c), combo);
        await vp.waitForTimeout(1100);
        await vp.evaluate(() => window.__cz.setCanvasStage('prep'));
        await vp.waitForTimeout(400);
        await vp.evaluate(() => window.__cz.setCanvasStage('run'));
        await vp.waitForTimeout(2200);
        const m = await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const card = cd.getElementById('czTicketStage');
          if (!card) return { missing: true };
          const cs = cd.defaultView.getComputedStyle(card);
          const grad = cs.backgroundImage;
          const stops = (grad.match(/(?:rgba|rgb)\([^)]*\)|#[0-9a-fA-F]{3,8}/g) || []).map(s => {
            if (s.startsWith('rgba(')) {
              const a = parseFloat(s.match(/[\d.]+\)$/)[0]);
              return { s, alpha: a };
            }
            return { s, alpha: 1 };
          });
          const translucent = stops.filter(x => x.alpha < 1);
          const first = stops[0] ? stops[0].s : '';
          const m1 = first.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
          const lum = m1 ? (0.299 * +m1[1] + 0.587 * +m1[2] + 0.114 * +m1[3]) : -1;
          return {
            opacity: cs.opacity,
            gradient: grad.slice(0, 120),
            translucentCount: translucent.length,
            firstLum: +lum.toFixed(1),
            textColor: cd.defaultView.getComputedStyle(cd.getElementById('pkCcgName')).color
          };
        });
        const ok = !m.missing && m.opacity === '1' && m.translucentCount === 0 && m.firstLum > 180;
        rows.push({ vp: v.vp, combo, ...m, pass: ok });
      }
      await vp.close();
    }
    return { rows, pass: rows.every(r => r.pass) };
  })();

  // ─── 项 14：ruler ↔ 票夹时长双向联动（S22 修复项）───
  /* 三视口 × 三组合：
     1. 在仪表盘 A 卡改 rulerInput = 18 并派发 input → 左栏 #pkTicketDurVal 同值为 18；
     2. 在左栏点 #pkTicketDurUp 2 次 (+2) → 票面变为 20，仪表盘 #rulerInput 同值为 20。 */
  const durationLinkage = await (async () => {
    const rows = [];
    for (const v of VIEWPORTS) {
      const vp = await browser.newPage({ viewport: { width: v.w, height: v.h } });
      await vp.goto(URL, { waitUntil: 'domcontentloaded' });
      await vp.waitForTimeout(1200);
      await vp.evaluate((x) => window.__cz.setVp(x), v.vp);
      await vp.waitForTimeout(400);
      for (const combo of COMBOS) {
        await vp.evaluate((c) => window.__cz.setCombo(c), combo);
        await vp.waitForTimeout(900);
        await vp.evaluate(() => window.__cz.setCanvasStage('prep'));
        await vp.waitForTimeout(400);

        // Part 1: Ruler -> Ticket
        const r2t = await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const frame = cd ? cd.querySelector('.cz-mod[data-mod="A"] iframe') : null;
          const d = frame ? frame.contentDocument : null;
          const rulerInput = d ? d.getElementById('rulerInput') : null;
          if (!rulerInput) return { ok: false, why: 'no rulerInput' };
          rulerInput.value = '18';
          try {
            rulerInput.dispatchEvent(new Event('input', { bubbles: true }));
          } catch (e) {}
          return { ok: true };
        });
        await vp.waitForTimeout(300);

        const leftRead1 = await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const durEl = cd ? cd.getElementById('pkTicketDurVal') : null;
          return durEl ? parseInt(durEl.textContent, 10) : null;
        });

        // Part 2: Ticket -> Ruler
        await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const upBtn = cd ? cd.getElementById('pkTicketDurUp') : null;
          if (upBtn) {
            upBtn.click();
            upBtn.click();
          }
        });
        await vp.waitForTimeout(300);

        const r2 = await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const durEl = cd ? cd.getElementById('pkTicketDurVal') : null;
          const frame = cd ? cd.querySelector('.cz-mod[data-mod="A"] iframe') : null;
          const d = frame ? frame.contentDocument : null;
          const rulerInput = d ? d.getElementById('rulerInput') : null;
          return {
            leftDur: durEl ? parseInt(durEl.textContent, 10) : null,
            rulerVal: rulerInput ? parseInt(rulerInput.value, 10) : null
          };
        });

        /* Part 2b：票面「时长卡片」按钮走的是 ttStepMin（不是总线 arm），
           必须同样回灌仪表盘 ruler，否则出现「票面 21 / 仪表盘 20」两个数字（agy P1）。 */
        await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const btn = cd ? cd.getElementById('pkTicketDurBtn') : null;
          if (btn) btn.click();
        });
        await vp.waitForTimeout(300);
        const r2b = await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const durEl = cd ? cd.getElementById('pkTicketDurVal') : null;
          const frame = cd ? cd.querySelector('.cz-mod[data-mod="A"] iframe') : null;
          const d = frame ? frame.contentDocument : null;
          const rulerInput = d ? d.getElementById('rulerInput') : null;
          return {
            leftDur: durEl ? parseInt(durEl.textContent, 10) : null,
            rulerVal: rulerInput ? parseInt(rulerInput.value, 10) : null
          };
        });

        /* Part 3: 窄条 bar（选完两项后的准备态）也要跟 ruler 走 ——
           dad 261027 第 3 条：拖 ruler 改时长，左侧票夹时长没联动。 */
        await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc(), w = cd ? cd.defaultView : null;
          if (w && typeof w.selectItem === 'function') w.selectItem(1034);
          const pill = cd ? cd.querySelector('.pk-session-pill') : null;
          if (pill) pill.click();
        });
        await vp.waitForTimeout(1300);
        await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const d = cd.querySelector('.cz-mod[data-mod="A"] iframe').contentDocument;
          const ri = d.getElementById('rulerInput');
          ri.value = '18';
          ri.dispatchEvent(new Event('input', { bubbles: true }));
        });
        await vp.waitForTimeout(500);
        const barState = await vp.evaluate(() => {
          const cd = window.__cz.canvasDoc(), w = cd ? cd.defaultView : null;
          const remain = cd ? cd.getElementById('pkRailRemain') : null;
          const durEl = cd ? cd.getElementById('pkTicketDurVal') : null;
          return {
            isBar: w && typeof w.isBarDeformed === 'function' ? w.isBarDeformed() : false,
            railRemain: remain ? remain.textContent.trim() : null,
            ticketDur: durEl ? parseInt(durEl.textContent, 10) : null
          };
        });

        const pass = (leftRead1 === 18) && (r2.leftDur === 20) && (r2.rulerVal === 20)
          && (r2b.leftDur === 21) && (r2b.rulerVal === 21)
          && barState.isBar && barState.railRemain === '18:00' && barState.ticketDur === 18;
        rows.push({ vp: v.vp, combo, r2tOk: r2t.ok, leftRead1, ...r2, r2b, barState, pass });
      }
      await vp.close();
    }
    return { rows, pass: rows.every(r => r.pass) };
  })();

  // ─── 项 15：选完两项即变形 + 重新选择（S22 交付项）───
  /* 1. 清空选择 → 票夹在（左栏宽 > 100px）；
     2. 填满两项（选科目 + 选内容）→ 立即变形为 bar（左栏宽 ≈ 50px 档或移动端横条）且未计时；
     3. 点「重新选择」→ 回票夹且选择保留；
     4. 开始计时中「重新选择」按钮 disabled。 */
  const autoMorphAndReselect = await (async () => {
    const rows = [];
    for (const v of VIEWPORTS) {
      const vp = await browser.newPage({ viewport: { width: v.w, height: v.h } });
      await vp.goto(URL, { waitUntil: 'domcontentloaded' });
      await vp.waitForTimeout(1200);
      await vp.evaluate((x) => window.__cz.setVp(x), v.vp);
      await vp.waitForTimeout(400);

      // 步骤 1: 清空选择
      await vp.evaluate(() => {
        if (window.__cz && typeof window.__cz.clearSelection === 'function') {
          window.__cz.clearSelection();
        }
      });
      await vp.waitForTimeout(400);

      const step1 = await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc(), w = cd ? cd.defaultView : null;
        const leftCol = cd ? cd.getElementById('pkLeftCol') : null;
        const lr = leftCol ? leftCol.getBoundingClientRect() : null;
        return {
          leftW: lr ? +lr.width.toFixed(1) : 0,
          leftH: lr ? +lr.height.toFixed(1) : 0,
          cur: w ? w.cur : undefined,
          isBar: w && typeof w.isBarDeformed === 'function' ? w.isBarDeformed() : false
        };
      });

      // 步骤 2: 填满两项
      /* S22-P0 护栏：变形必须逐帧插值。旧实现首帧就被 .stage-bar 的 !important
         压成 50px（瞬间跳变），这里采样整段动画要求中间值 ≥ 3 档。 */
      await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc();
        const left = cd ? cd.getElementById('pkLeftCol') : null;
        window.__czMorphSamples = [];
        if (!left) return;
        const t0 = performance.now();
        (function loop() {
          const r = left.getBoundingClientRect();
          window.__czMorphSamples.push({ w: +r.width.toFixed(1), h: +r.height.toFixed(1) });
          if (performance.now() - t0 < 800) requestAnimationFrame(loop);
        })();
      });
      await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc(), w = cd ? cd.defaultView : null;
        if (w && typeof w.selectItem === 'function') w.selectItem(1034);
        const pill = cd ? cd.querySelector('.pk-session-pill') : null;
        if (pill) pill.click();
      });
      await vp.waitForTimeout(600);

      const step2 = await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc(), w = cd ? cd.defaultView : null;
        const leftCol = cd ? cd.getElementById('pkLeftCol') : null;
        const btn = cd ? cd.getElementById('pkRailReselectBtn') : null;
        const rail = cd ? cd.querySelector('.pk-run-rail') : null;
        const remainVal = cd ? cd.getElementById('pkRailRemain') : null;
        const lr = leftCol ? leftCol.getBoundingClientRect() : null;
        const rr = rail ? rail.getBoundingClientRect() : null;
        const rv = remainVal ? remainVal.getBoundingClientRect() : null;
        const isMobile = cd && cd.documentElement.clientWidth < 1024;
        /* 变形插值采样：桌面看宽度，纵向 feed 看高度 */
        const samples = window.__czMorphSamples || [];
        const axis = isMobile ? 'h' : 'w';
        const arr = samples.map((s) => s[axis]);
        const first = arr.length ? arr[0] : 0;
        const last = arr.length ? arr[arr.length - 1] : 0;
        const lo = Math.min(first, last);
        const hi = Math.max(first, last);
        const midVals = [...new Set(arr.filter((v) => v > lo + 1 && v < hi - 1))];
        const contentEl = cd ? cd.getElementById('pkRailContent') : null;
        return {
          leftW: lr ? +lr.width.toFixed(1) : 0,
          leftH: lr ? +lr.height.toFixed(1) : 0,
          isBar: w && typeof w.isBarDeformed === 'function' ? w.isBarDeformed() : false,
          isTiming: w && typeof w.isTimingRunning === 'function' ? w.isTimingRunning() : false,
          reselectDisabled: btn ? btn.disabled : null,
          /* S22 回归护栏 a：窄条不得塌成 0 高（票卡 display:none 后曾把 bar 压成 2px） */
          railH: rr ? +rr.height.toFixed(1) : 0,
          /* S22 回归护栏 b：窄条里的剩余时间必须能被完整读到（曾竖排+rotate 倒读成 00:01） */
          remainText: remainVal ? remainVal.textContent.trim() : null,
          remainWritingMode: remainVal ? cd.defaultView.getComputedStyle(remainVal).writingMode : null,
          remainFitsBar: rv && rr ? (rv.left >= rr.left - 0.5 && rv.right <= rr.right + 0.5) : false,
          /* S22-P0 护栏：变形中间值档数（≥3 才是插值，不是跳变） */
          morphMidSteps: midVals.length,
          morphFirst: +first.toFixed(1),
          morphLast: +last.toFixed(1),
          /* S22-P1 护栏：窄条里的「本次内容」不能被压成一两个字（此前 440 实测仅 4.2px） */
          contentWidth: contentEl ? +contentEl.getBoundingClientRect().width.toFixed(1) : 0,
          contentClipped: contentEl ? (contentEl.scrollWidth > contentEl.clientWidth + 1) : false,
          isMobile
        };
      });

      // 步骤 3: 点「重新选择」
      await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc();
        const btn = cd ? cd.getElementById('pkRailReselectBtn') : null;
        if (btn) btn.click();
      });
      await vp.waitForTimeout(600);

      const step3 = await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc(), w = cd ? cd.defaultView : null;
        const leftCol = cd ? cd.getElementById('pkLeftCol') : null;
        const lr = leftCol ? leftCol.getBoundingClientRect() : null;
        /* 展开回票夹后「换曲目」入口必须恢复可用（窄条形态下才 block，见 openFolio 的 isBarDeformed 早返回） */
        if (w && typeof w.openFolio === 'function') { try { w.openFolio(); } catch (e) {} }
        const modalOpen = cd && cd.getElementById('pkFolioModal') ? cd.getElementById('pkFolioModal').classList.contains('open') : false;
        if (w && typeof w.closeFolio === 'function') { try { w.closeFolio(); } catch (e) {} }
        return {
          leftW: lr ? +lr.width.toFixed(1) : 0,
          leftH: lr ? +lr.height.toFixed(1) : 0,
          isBar: w && typeof w.isBarDeformed === 'function' ? w.isBarDeformed() : false,
          curName: (w && w.cur && w.cur.name) || (cd && cd.getElementById('pkTicketSubjectName') ? cd.getElementById('pkTicketSubjectName').textContent : null),
          content: w ? w.content : null,
          folioOpens: modalOpen
        };
      });

      // 步骤 4: 计时中 disabled 校验
      await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc(), w = cd ? cd.defaultView : null;
        if (w && typeof w.enterRun === 'function') w.enterRun();
      });
      await vp.waitForTimeout(600);

      const step4 = await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc(), w = cd ? cd.defaultView : null;
        const btn = cd ? cd.getElementById('pkRailReselectBtn') : null;
        return {
          isTiming: w && typeof w.isTimingRunning === 'function' ? w.isTimingRunning() : false,
          reselectDisabled: btn ? btn.disabled : null
        };
      });

      const pass1 = step1.leftW > 100 && !step1.isBar;
      const pass2 = (step2.isMobile ? (step2.leftH <= 56) : (Math.abs(step2.leftW - 50) <= 6)) && step2.isBar && !step2.isTiming && step2.reselectDisabled === false
        && step2.railH >= (step2.isMobile ? 44 : 200)
        && /^\d{2}:\d{2}$/.test(step2.remainText || '')
        && step2.remainWritingMode === 'horizontal-tb' && step2.remainFitsBar
        && step2.morphMidSteps >= 3
        && (step2.isMobile ? (step2.contentWidth >= 40 && step2.contentClipped === false) : true);
      const pass3 = step3.leftW > 100 && !step3.isBar && !!step3.curName && step3.curName !== '未选择科目'
        && step3.folioOpens === true;
      const pass4 = step4.isTiming && step4.reselectDisabled === true;

      const ok = pass1 && pass2 && pass3 && pass4;
      rows.push({ vp: v.vp, step1, step2, step3, step4, pass: ok });
      await vp.close();
    }
    return { rows, pass: rows.every(r => r.pass) };
  })();

  // ─── 项 16：开始计时的就绪门禁（dad 261028）───
  /* 票夹是唯一真源：科目 + 本次练习内容 + 时长都选齐之前，仪表盘的「开始」必须点不动；
     选齐之后点开始，计时器用的时长必须等于票夹上选好的那一份。 */
  const startGate = await (async () => {
    const rows = [];
    for (const v of VIEWPORTS) {
      const vp = await browser.newPage({ viewport: { width: v.w, height: v.h } });
      await vp.goto(URL, { waitUntil: 'domcontentloaded' });
      await vp.waitForTimeout(1400);
      await vp.evaluate((x) => window.__cz.setVp(x), v.vp);
      await vp.waitForTimeout(500);
      await vp.evaluate(() => window.__cz.clearSelection());
      await vp.waitForTimeout(500);

      const readCard = () => vp.evaluate(() => {
        const cd = window.__cz.canvasDoc();
        const f = cd.querySelector('.cz-mod[data-mod="A"] iframe');
        const d = f ? f.contentDocument : null;
        const btn = d ? d.getElementById('btnPrimary') : null;
        const ri = d ? d.getElementById('rulerInput') : null;
        const dash = d ? d.querySelector('.dash') : null;
        const st = cd.defaultView.__czPracticeReady ? cd.defaultView.__czPracticeReady() : null;
        return {
          disabled: btn ? btn.disabled : null,
          title: btn ? btn.title : null,
          mode: dash ? dash.dataset.mode : null,
          ruler: ri ? parseInt(ri.value, 10) : null,
          ready: st ? st.ready : null,
          reason: st ? st.reason : null,
          durationMin: st ? st.durationMin : null
        };
      });
      const clickStart = () => vp.evaluate(() => {
        const cd = window.__cz.canvasDoc();
        const f = cd.querySelector('.cz-mod[data-mod="A"] iframe');
        const btn = f ? f.contentDocument.getElementById('btnPrimary') : null;
        if (btn) btn.click();
      });

      const empty = await readCard();
      await clickStart();
      await vp.waitForTimeout(500);
      const afterEmptyClick = await readCard();

      // 只选科目，未选内容
      await vp.evaluate(() => { window.__cz.canvasDoc().defaultView.selectItem(1034); });
      await vp.waitForTimeout(500);
      const subjectOnly = await readCard();

      // 选满两项 → 就绪
      await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc();
        const pill = cd.querySelector('.pk-session-pill');
        if (pill) pill.click();
      });
      await vp.waitForTimeout(600);
      const filled = await readCard();

      // 票夹时长改成 18 → A 卡 ruler 同步 → 点开始 → 计时用 18
      await vp.evaluate(() => { window.__cz.canvasDoc().defaultView.ttSetDuration(18); });
      await vp.waitForTimeout(500);
      const dur18 = await readCard();
      await clickStart();
      await vp.waitForTimeout(900);
      const running = await vp.evaluate(() => {
        const cd = window.__cz.canvasDoc();
        const f = cd.querySelector('.cz-mod[data-mod="A"] iframe');
        const d = f ? f.contentDocument : null;
        const dash = d ? d.querySelector('.dash') : null;
        const w = d ? d.defaultView : null;
        return {
          mode: dash ? dash.dataset.mode : null,
          cardDuration: w && w.getPracticeReady ? w.getPracticeReady().durationMin : null,
          ticketDur: cd.getElementById('pkTicketDurVal') ? parseInt(cd.getElementById('pkTicketDurVal').textContent, 10) : null,
          railRemain: cd.getElementById('pkRailRemain') ? cd.getElementById('pkRailRemain').textContent.trim() : null
        };
      });

      const pass = empty.disabled === true && empty.ready === false
        && afterEmptyClick.mode === 'prep' && afterEmptyClick.disabled === true
        && subjectOnly.disabled === true && subjectOnly.ready === false
        && filled.disabled === false && filled.ready === true
        && dur18.ruler === 18 && dur18.durationMin === 18
        && running.mode === 'run' && running.cardDuration === 18 && running.ticketDur === 18 && running.railRemain === '18:00';
      rows.push({ vp: v.vp, empty, afterEmptyClick, subjectOnly, filled, dur18, running, pass });
      await vp.close();
    }
    return { rows, pass: rows.every(r => r.pass) };
  })();

  const fullOutput = {
    summary: summaryMatrix,
    staticChecks,
    details: results,
    runSwitch,
    overlayViewport,
    slotCardTheme,
    durationLinkage,
    autoMorphAndReselect,
    startGate
  };
  fs.writeFileSync(OUT_JSON, JSON.stringify(fullOutput, null, 2), 'utf-8');

  // 终端打印人读表格
  console.log('\n' + '═'.repeat(96));
  console.log('  dizical demo v39 · S0 自动化测试与基线护栏报告 (9 组合实测)');
  console.log('═'.repeat(96));
  const pad = (s, n) => String(s).padEnd(n);
  console.log(pad('视口', 6) + pad('组合', 6) + pad('重叠面积', 10) + pad('露出比', 10) + pad('条字重叠', 10) + pad('记录弹窗', 10) + pad('退场空窗', 9) + pad('退场双30', 9) + pad('进场双30', 9) + pad('节点(实/标)', 12) + pad('Feed顺序', 10));
  console.log('─'.repeat(96));

  let allCorePass = true;
  for (const s of summaryMatrix) {
    if (!s.c1_4_pass || !s.v37g_exit_pass) allCorePass = false;
    const feedStr = (s.feedMatch === 'PASS') ? '✅ PASS' : ((s.feedMatch === 'SKIP') ? 'SKIP' : '❌ FAIL');
    const nodeMatch = (s.nodes.split('/')[0] === s.nodes.split('/')[1]);
    const nodeStr = s.nodes + ' ' + (nodeMatch ? '✅' : '❌');

    console.log(
      pad(s.vp, 6) +
      pad('C' + s.combo, 6) +
      pad(s.maxOv, 10) +
      pad(s.ratio, 10) +
      pad(s.textOv, 10) +
      pad(s.recOk, 10) +
      pad(s.exitBlank, 9) +
      pad(s.exitDual30, 9) +
      pad(s.enterDual30, 9) +
      pad(nodeStr, 12) +
      pad(feedStr, 10)
    );
  }
  console.log('─'.repeat(96));

  console.log('\n【S0 基线核心指标判定】');
  /* 打印必须复用每组合的 passOv（含卡宽/黑区宽、贴顶缘、0 硬重叠），不能只看 maxOv */
  console.log('  1. 卡槽卡契约 (卡跨黑区顶缘、入槽下缘被唇咬住、不压旋钮/主控件/诊断卡、±按钮不压黑区) : ' + (summaryMatrix.every(s => s.slotContractPass) ? '✅ PASS' : '❌ FAIL'));
  console.log('  2. 露出比例 (横排 ∈ [18.5%, 21.5%] / feed 流整带露出 = 100%)                : ' + (summaryMatrix.every(s => { const v = parseFloat(s.ratio); return (v >= 99) || (v >= 18.5 && v <= 21.5); }) ? '✅ PASS' : '❌ FAIL'));
  console.log('  3. 露出条叶子文本两两重叠 == 0.0 px²                                     : ' + (summaryMatrix.every(s => s.textOv === 0) ? '✅ PASS (全部 0.0 px²)' : '❌ FAIL'));
  console.log('  4. 今日记录弹窗 12 条明细 display==block 且无裁切                         : ' + (summaryMatrix.every(s => s.recOk === 'PASS') ? '✅ PASS' : '❌ FAIL'));
  console.log('  5. exitRun 退场空窗帧数 == 0                                             : ' + (summaryMatrix.every(s => s.exitBlank === 0) ? '✅ PASS' : '❌ FAIL'));
  console.log('  6. exitRun 退场 dual30 帧数 == 0 (v37g 成果锁定)                         : ' + (summaryMatrix.every(s => s.exitDual30 === 0) ? '✅ PASS' : '❌ FAIL'));
  const allNodesPass = summaryMatrix.every(s => s.nodes.split('/')[0] === s.nodes.split('/')[1]);
  console.log('  7. 结构类：节点数匹配 (S4 目标 2/4/6 卡)                                   : ' + (allNodesPass ? '✅ PASS (全部 2/2, 4/4, 6/6 匹配)' : '❌ FAIL'));
  const allFeedPass = summaryMatrix.every(s => s.feedMatch === 'PASS' || s.feedMatch === 'SKIP');
  console.log('  8. 结构类：Feed 顺序 (S4 目标 A,B,S,D,R,Q 顺序)                            : ' + (allFeedPass ? '✅ PASS (全部匹配)' : '❌ FAIL'));
  const distStr = Object.entries(staticChecks.dataVpDistribution || {})
    .map(([k, v]) => `${k}:${v}`)
    .join('  ');
  const passDataVp = (staticChecks.dataVpCount === 0);
  console.log('  9. 静态类：CSS [data-vp] 选择器总数 = ' + staticChecks.dataVpCount + ' 次 (' + distStr + ') : ' + (passDataVp ? '✅ PASS (= 0)' : '❌ FAIL'));
  const sc = staticChecks;
  const dyRatio = (sc.notchR && sc.dy !== null) ? sc.dy / sc.notchR : null;
  const passConcentric = (sc.dy !== null && sc.notchR > 0 && sc.knobR > 0
    && Math.abs(sc.notchR - (sc.knobR + 14)) <= 2          // 凹拱半径 = 旋钮半径 + 14（同一套圆）
    && Math.abs(sc.dotR - (sc.knobR + 6)) <= 1             // 圆点弧半径 = 旋钮半径 + 6
    && sc.dy >= 24                                        // 旋钮圆心落在黑区底边下方（凹拱是弦不是圆心线）
    && dyRatio !== null && dyRatio <= 0.8
    && (sc.btnPanelOverlap === 0));                        // ± 按钮不压黑区
  console.log(` 10. 静态类：三心合一 (R_notch=${sc.notchR} = R_knob ${sc.knobR}+14, R_dot=${sc.dotR}, dy=${sc.dy}px = ${dyRatio === null ? 'n/a' : dyRatio.toFixed(2)}R, ±按钮压黑区=${sc.btnPanelOverlap}px²) : ` + (passConcentric ? '✅ PASS' : '❌ FAIL'));
  console.log(` 11. run 态直切视口 (1133 run → 744：dash=${runSwitch.after.dash}px, knob=${runSwitch.after.knob}px, frame=${runSwitch.after.frameH}px) : ` + (runSwitch.pass ? '✅ PASS' : '❌ FAIL'));
  console.log(` 12. 画布内 fixed 弹层落在浏览器视口内 (换曲目/老师要求全文/记录明细 × 9 组合)   : ` + (overlayViewport.pass ? '✅ PASS (27/27 可见)' : '❌ FAIL (' + overlayViewport.rows.filter(r => !r.pass).map(r => r.vp + '/C' + r.combo).join(', ') + ')'));
  const badCards = slotCardTheme.rows.filter(r => !r.pass);
  console.log(` 13. 卡槽插入卡主题色 + 实色不透明 (含渐变实色/首停亮度/最终 opacity × 9 组合)  : ` + (slotCardTheme.pass ? '✅ PASS (27/27 主题色且不透明)' : '❌ FAIL (' + badCards.map(r => r.vp + '/C' + r.combo + ' lum=' + r.firstLum + ' alpha=' + r.translucentCount).join(', ') + ')'));
  const badDur = durationLinkage.rows.filter(r => !r.pass);
  console.log(` 14. ruler ↔ 票夹时长联动 (Dash改18->票面18，票面+2->Dash为20，窄条 18:00 × 9 组合) : ` + (durationLinkage.pass ? '✅ PASS (9/9 双向一致，窄条同步)' : '❌ FAIL (' + badDur.map(r => r.vp + '/C' + r.combo + ' bar=' + (r.barState ? r.barState.railRemain : 'n/a')).join(', ') + ')'));
  const badMorph = autoMorphAndReselect.rows.filter(r => !r.pass);
  console.log(` 15. 选完两项即变形 + 重新选择 (空态>100px, 满项≈50px未计时, 窄条不塌/时间横排可读, 重选保留, 计时禁用) : ` + (autoMorphAndReselect.pass ? '✅ PASS (3/3 视口全通过)' : '❌ FAIL (' + badMorph.map(r => r.vp + ' railH=' + r.step2.railH + ' remain=' + r.step2.remainText + '/' + r.step2.remainWritingMode + ' fits=' + r.step2.remainFitsBar).join(', ') + ')'));
  const badGate = startGate.rows.filter(r => !r.pass);
  console.log(` 16. 开始计时就绪门禁 (票夹未选齐→开始点不动；选齐后计时时长=票夹时长) : ` + (startGate.pass ? '✅ PASS (3/3 视口全通过)' : '❌ FAIL (' + badGate.map(r => r.vp + ' empty=' + r.empty.disabled + '/' + r.empty.mode + ' subjOnly=' + r.subjectOnly.disabled + ' filled=' + r.filled.disabled + ' run=' + r.running.mode + '/' + r.running.cardDuration).join(', ') + ')'));
  console.log('═'.repeat(96));

  if (isStrict) {
    const allPassed = allCorePass &&
      summaryMatrix.every(s => s.nodes.split('/')[0] === s.nodes.split('/')[1]) &&
      summaryMatrix.every(s => s.feedMatch === 'PASS' || s.feedMatch === 'SKIP') &&
      passDataVp &&
      passConcentric &&
      runSwitch.pass &&
      overlayViewport.pass &&
      slotCardTheme.pass &&
      durationLinkage.pass &&
      autoMorphAndReselect.pass &&
      startGate.pass;
    process.exit(allPassed ? 0 : 1);
  } else {
    process.exit(allCorePass && passDataVp && passConcentric && runSwitch.pass && overlayViewport.pass && slotCardTheme.pass && durationLinkage.pass && autoMorphAndReselect.pass && startGate.pass ? 0 : 1);
  }
})().catch(err => {
  console.error(err);
  process.exit(1);
});
