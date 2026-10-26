#!/usr/bin/env node
/**
 * capture-s6-frames.js - S6 计时态入场/退场串行动画 + 卡槽插卡 + FLIP 抽卡展开逐帧截图取证脚本
 * 采样策略：独立单轮重放，复位等待 550ms 保证上一轮 Timeline 彻底清理，确保每个时间截点精度 ±3ms
 * 产出目录：/tmp/v38-s6-frames/
 */

const fs = require('fs');
const path = require('path');
const { chromium } = require('/Users/mt16/.hermes/profiles/quagmire/skills/ljg-skills/skills/ljg-card/node_modules/playwright');

const URL = 'http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html';
const OUT_DIR = '/tmp/v38-s6-frames';

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  // 使用 iPad 视口（1133x744 横屏，物理 1280x820）
  const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  // 切到组合 1（A + S），聚焦观察卡槽与票夹
  await page.evaluate(() => window.__cz.setCombo('1'));
  await page.waitForTimeout(600);

  console.log('=== STEP 1: 入场串行动画采样 (0~500ms, 独立单轮精确定时) ===');
  const enterTimestamps = [0, 60, 120, 180, 240, 260, 300, 360, 420, 500];
  const enterLog = [];

  for (const targetMs of enterTimestamps) {
    // 每次复位到 prep 并等待 550ms 确保 exitRun 彻底完成
    await page.evaluate(() => window.__cz.setCanvasStage('prep'));
    await page.waitForTimeout(550);

    // 触发 run
    await page.evaluate(() => window.__cz.setCanvasStage('run'));

    if (targetMs > 0) {
      await page.waitForTimeout(targetMs);
    }

    const shotPath = path.join(OUT_DIR, `enter-${String(targetMs).padStart(3, '0')}ms.png`);
    await page.screenshot({ path: shotPath, clip: { x: 0, y: 0, width: 880, height: 750 } });

    const metrics = await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const tc = cd.getElementById('pkTicketCard');
      const lc = cd.getElementById('pkLeftCol');
      const stage = cd.getElementById('czTicketStage');
      const rail = cd.getElementById('pkRunRail');

      const sTc = tc ? cd.defaultView.getComputedStyle(tc) : null;
      const sLc = lc ? cd.defaultView.getComputedStyle(lc) : null;
      const sStage = stage ? cd.defaultView.getComputedStyle(stage) : null;
      const sRail = rail ? cd.defaultView.getComputedStyle(rail) : null;

      return {
        ticketWidth: sTc ? sTc.width : null,
        ticketOpacity: sTc ? parseFloat(sTc.opacity || '0') : null,
        leftColWidth: sLc ? sLc.width : null,
        slotOpacity: sStage ? parseFloat(sStage.opacity || '0') : null,
        slotTransform: sStage ? sStage.transform : null,
        slotDisplay: sStage ? sStage.display : null,
        slotVisibility: sStage ? sStage.visibility : null,
        railOpacity: sRail ? parseFloat(sRail.opacity || '0') : null
      };
    });

    enterLog.push({ ms: targetMs, ...metrics, shot: shotPath });
    console.log(`[Enter ${targetMs}ms] TicketW: ${metrics.ticketWidth}, TicketOp: ${metrics.ticketOpacity?.toFixed(2)}, SlotOp: ${metrics.slotOpacity?.toFixed(2)}, SlotTr: ${metrics.slotTransform}`);
  }

  // 停在计时态
  await page.evaluate(() => window.__cz.setCanvasStage('run'));
  await page.waitForTimeout(600);

  console.log('\n=== STEP 2: 计时态卡槽与露出部特写截图 ===');
  const slotShotPath = path.join(OUT_DIR, 'slot-exposed-card.png');
  const slotClip = await page.evaluate(() => {
    const cd = window.__cz.canvasDoc();
    const crown = cd.querySelector('.cz-astack-crown') || cd.getElementById('pkPunchSlotWrap');
    if (!crown) return { x: 380, y: 30, width: 450, height: 120 };
    const r = crown.getBoundingClientRect();
    const frameRect = cd.defaultView.frameElement ? cd.defaultView.frameElement.getBoundingClientRect() : { left: 0, top: 0 };
    return {
      x: Math.max(0, Math.floor(frameRect.left + r.left - 20)),
      y: Math.max(0, Math.floor(frameRect.top + r.top - 15)),
      width: Math.ceil(r.width + 40),
      height: Math.ceil(r.height + 60)
    };
  });
  await page.screenshot({ path: slotShotPath, clip: slotClip });
  console.log(`[Slot close-up saved] ${slotShotPath}`);

  console.log('\n=== STEP 3: FLIP 抽卡展开动画采样 (0~320ms, 独立单轮精确定时) ===');
  const flipOpenTimestamps = [0, 60, 120, 180, 240, 320];
  const flipOpenLog = [];
  for (const targetMs of flipOpenTimestamps) {
    // 确保弹窗关闭
    await page.evaluate(() => window.__cz.closeCardOverlay());
    await page.waitForTimeout(350);

    // 触发展开
    await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const stage = cd.getElementById('czTicketStage');
      if (stage) stage.click();
      else window.__cz.openCardOverlay();
    });

    if (targetMs > 0) {
      await page.waitForTimeout(targetMs);
    }

    const shotPath = path.join(OUT_DIR, `flip-open-${String(targetMs).padStart(3, '0')}ms.png`);
    await page.screenshot({ path: shotPath, clip: { x: 200, y: 30, width: 880, height: 720 } });

    const pRect = await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const pop = cd.getElementById('czCardPopup') || (cd.getElementById('czCardOverlay') ? cd.getElementById('czCardOverlay').querySelector('.cz-card-popup') : null);
      if (!pop) return null;
      const r = pop.getBoundingClientRect();
      const cs = cd.defaultView.getComputedStyle(pop);
      return {
        x: r.left.toFixed(1),
        y: r.top.toFixed(1),
        w: r.width.toFixed(1),
        h: r.height.toFixed(1),
        transform: cs.transform,
        opacity: cs.opacity
      };
    });
    flipOpenLog.push({ ms: targetMs, ...pRect, shot: shotPath });
    console.log(`[FLIP Open ${targetMs}ms] w: ${pRect?.w}, h: ${pRect?.h}, opacity: ${pRect?.opacity}, transform: ${pRect?.transform}`);
  }

  console.log('\n=== STEP 4: FLIP 塞回卡槽关闭动画采样 (0~260ms, 独立单轮精确定时) ===');
  const flipCloseTimestamps = [0, 60, 120, 180, 260];
  const flipCloseLog = [];
  for (const targetMs of flipCloseTimestamps) {
    // 确保弹窗先完全展开
    await page.evaluate(() => window.__cz.openCardOverlay());
    await page.waitForTimeout(450);

    // 触发关闭
    await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const btn = cd.getElementById('czPopupCloseBtn');
      if (btn) btn.click();
      else window.__cz.closeCardOverlay();
    });

    if (targetMs > 0) {
      await page.waitForTimeout(targetMs);
    }

    const shotPath = path.join(OUT_DIR, `flip-close-${String(targetMs).padStart(3, '0')}ms.png`);
    await page.screenshot({ path: shotPath, clip: { x: 200, y: 30, width: 880, height: 720 } });

    const pRect = await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const pop = cd.getElementById('czCardPopup') || (cd.getElementById('czCardOverlay') ? cd.getElementById('czCardOverlay').querySelector('.cz-card-popup') : null);
      if (!pop) return null;
      const r = pop.getBoundingClientRect();
      const cs = cd.defaultView.getComputedStyle(pop);
      return {
        x: r.left.toFixed(1),
        y: r.top.toFixed(1),
        w: r.width.toFixed(1),
        h: r.height.toFixed(1),
        transform: cs.transform,
        opacity: cs.opacity
      };
    });
    flipCloseLog.push({ ms: targetMs, ...pRect, shot: shotPath });
    console.log(`[FLIP Close ${targetMs}ms] w: ${pRect?.w}, h: ${pRect?.h}, opacity: ${pRect?.opacity}, transform: ${pRect?.transform}`);
  }

  console.log('\n=== STEP 5: 退场串行动画采样 (0~480ms, 独立单轮精确定时) ===');
  const exitTimestamps = [0, 60, 120, 180, 200, 240, 300, 360, 420, 480];
  const exitLog = [];

  for (const targetMs of exitTimestamps) {
    // 确保先稳定在计时态
    await page.evaluate(() => window.__cz.setCanvasStage('run'));
    await page.waitForTimeout(550);

    // 触发退场
    await page.evaluate(() => window.__cz.setCanvasStage('prep'));

    if (targetMs > 0) {
      await page.waitForTimeout(targetMs);
    }

    const shotPath = path.join(OUT_DIR, `exit-${String(targetMs).padStart(3, '0')}ms.png`);
    await page.screenshot({ path: shotPath, clip: { x: 0, y: 0, width: 880, height: 750 } });

    const metrics = await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const tc = cd.getElementById('pkTicketCard');
      const lc = cd.getElementById('pkLeftCol');
      const stage = cd.getElementById('czTicketStage');
      const rail = cd.getElementById('pkRunRail');

      const sTc = tc ? cd.defaultView.getComputedStyle(tc) : null;
      const sLc = lc ? cd.defaultView.getComputedStyle(lc) : null;
      const sStage = stage ? cd.defaultView.getComputedStyle(stage) : null;
      const sRail = rail ? cd.defaultView.getComputedStyle(rail) : null;

      return {
        ticketWidth: sTc ? sTc.width : null,
        ticketOpacity: sTc ? parseFloat(sTc.opacity || '0') : null,
        leftColWidth: sLc ? sLc.width : null,
        slotOpacity: sStage ? parseFloat(sStage.opacity || '0') : null,
        slotTransform: sStage ? sStage.transform : null,
        railOpacity: sRail ? parseFloat(sRail.opacity || '0') : null
      };
    });

    exitLog.push({ ms: targetMs, ...metrics, shot: shotPath });
    console.log(`[Exit ${targetMs}ms] SlotOp: ${metrics.slotOpacity?.toFixed(2)}, SlotTr: ${metrics.slotTransform}, RailOp: ${metrics.railOpacity?.toFixed(2)}, TicketW: ${metrics.ticketWidth}, TicketOp: ${metrics.ticketOpacity?.toFixed(2)}`);
  }

  // 保存全量采样数据 JSON
  const record = {
    enter: enterLog,
    flipOpen: flipOpenLog,
    flipClose: flipCloseLog,
    exit: exitLog
  };
  fs.writeFileSync(path.join(OUT_DIR, 's6-frame-metrics.json'), JSON.stringify(record, null, 2), 'utf-8');
  console.log(`\n✅ 全量逐帧采样完成，元数据写入 ${path.join(OUT_DIR, 's6-frame-metrics.json')}`);

  await browser.close();
})();
