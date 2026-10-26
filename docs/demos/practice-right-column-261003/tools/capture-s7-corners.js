const fs = require('fs');
const path = require('path');
const { chromium } = require('/Users/mt16/.hermes/profiles/quagmire/skills/ljg-skills/skills/ljg-card/node_modules/playwright');

const URL = 'http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html';
const OUT_DIR = '/tmp/v38-s7-inspect';

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  // Use deviceScaleFactor: 2 for 400% crisp inspection
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1600 },
    deviceScaleFactor: 2
  });
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  // Helper to get bounding rect of any mod card
  async function getCardBox(modKey) {
    return await page.evaluate((k) => {
      const cd = window.__cz.canvasDoc();
      const mod = cd.querySelector('.cz-mod[data-mod="' + k + '"]');
      if (!mod) return null;
      const r = mod.getBoundingClientRect();
      const cf = cd.defaultView.frameElement ? cd.defaultView.frameElement.getBoundingClientRect() : { left: 0, top: 0 };
      return {
        x: Math.round(cf.left + r.left),
        y: Math.round(cf.top + r.top),
        w: Math.round(r.width),
        h: Math.round(r.height)
      };
    }, modKey);
  }

  // 1. Light Mode Card A 4 Corners
  const aBoxLight = await getCardBox('A');
  console.log('Card A Box Light:', aBoxLight);
  if (aBoxLight) {
    const pad = 24;
    const cornerSize = 90;
    // Top-Left
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-a-tl-light.png'),
      clip: { x: aBoxLight.x - pad, y: aBoxLight.y - pad, width: cornerSize, height: cornerSize }
    });
    // Top-Right
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-a-tr-light.png'),
      clip: { x: aBoxLight.x + aBoxLight.w - cornerSize + pad, y: aBoxLight.y - pad, width: cornerSize, height: cornerSize }
    });
    // Bottom-Left
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-a-bl-light.png'),
      clip: { x: aBoxLight.x - pad, y: aBoxLight.y + aBoxLight.h - cornerSize + pad, width: cornerSize, height: cornerSize }
    });
    // Bottom-Right
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-a-br-light.png'),
      clip: { x: aBoxLight.x + aBoxLight.w - cornerSize + pad, y: aBoxLight.y + aBoxLight.h - cornerSize + pad, width: cornerSize, height: cornerSize }
    });

    // Panel bottom edge in light mode
    const panelBoxLight = await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const aFrame = cd.querySelector('.cz-mod[data-mod="A"] > iframe');
      const ad = aFrame.contentDocument;
      const panel = ad.getElementById('panel');
      const r = panel.getBoundingClientRect();
      const aRect = aFrame.getBoundingClientRect();
      const cf = cd.defaultView.frameElement ? cd.defaultView.frameElement.getBoundingClientRect() : { left: 0, top: 0 };
      return {
        x: Math.round(cf.left + aRect.left + r.left),
        y: Math.round(cf.top + aRect.top + r.bottom - 45),
        width: Math.round(r.width),
        height: 90
      };
    });
    if (panelBoxLight) {
      await page.screenshot({
        path: path.join(OUT_DIR, 's7-panel-bottom-light.png'),
        clip: panelBoxLight
      });
      // Panel bottom-left corner
      await page.screenshot({
        path: path.join(OUT_DIR, 's7-panel-bl-light.png'),
        clip: { x: panelBoxLight.x - 8, y: panelBoxLight.y, width: 80, height: 80 }
      });
      // Panel bottom-right corner
      await page.screenshot({
        path: path.join(OUT_DIR, 's7-panel-br-light.png'),
        clip: { x: panelBoxLight.x + panelBoxLight.width - 72, y: panelBoxLight.y, width: 80, height: 80 }
      });
    }
  }

  // 2. Dark Mode (Ink) Card A 4 Corners & Panel
  await page.evaluate(() => window.__cz.setSkin('ink'));
  await page.waitForTimeout(600);

  const aBoxInk = await getCardBox('A');
  if (aBoxInk) {
    const pad = 24;
    const cornerSize = 90;
    // Top-Left
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-a-tl-ink.png'),
      clip: { x: aBoxInk.x - pad, y: aBoxInk.y - pad, width: cornerSize, height: cornerSize }
    });
    // Top-Right
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-a-tr-ink.png'),
      clip: { x: aBoxInk.x + aBoxInk.w - cornerSize + pad, y: aBoxInk.y - pad, width: cornerSize, height: cornerSize }
    });
    // Bottom-Left
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-a-bl-ink.png'),
      clip: { x: aBoxInk.x - pad, y: aBoxInk.y + aBoxInk.h - cornerSize + pad, width: cornerSize, height: cornerSize }
    });
    // Bottom-Right
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-a-br-ink.png'),
      clip: { x: aBoxInk.x + aBoxInk.w - cornerSize + pad, y: aBoxInk.y + aBoxInk.h - cornerSize + pad, width: cornerSize, height: cornerSize }
    });

    // Panel bottom edge in ink mode
    const panelBoxInk = await page.evaluate(() => {
      const cd = window.__cz.canvasDoc();
      const aFrame = cd.querySelector('.cz-mod[data-mod="A"] > iframe');
      const ad = aFrame.contentDocument;
      const panel = ad.getElementById('panel');
      const r = panel.getBoundingClientRect();
      const aRect = aFrame.getBoundingClientRect();
      const cf = cd.defaultView.frameElement ? cd.defaultView.frameElement.getBoundingClientRect() : { left: 0, top: 0 };
      return {
        x: Math.round(cf.left + aRect.left + r.left),
        y: Math.round(cf.top + aRect.top + r.bottom - 45),
        width: Math.round(r.width),
        height: 90
      };
    });
    if (panelBoxInk) {
      await page.screenshot({
        path: path.join(OUT_DIR, 's7-panel-bottom-ink.png'),
        clip: panelBoxInk
      });
      // Panel bottom-left corner
      await page.screenshot({
        path: path.join(OUT_DIR, 's7-panel-bl-ink.png'),
        clip: { x: panelBoxInk.x - 8, y: panelBoxInk.y, width: 80, height: 80 }
      });
      // Panel bottom-right corner
      await page.screenshot({
        path: path.join(OUT_DIR, 's7-panel-br-ink.png'),
        clip: { x: panelBoxInk.x + panelBoxInk.width - 72, y: panelBoxInk.y, width: 80, height: 80 }
      });
    }
  }

  // 3. Combo 2 (Cards D, R, S) Corners in Light Mode
  await page.evaluate(() => window.__cz.setSkin('silver'));
  await page.evaluate(() => window.__cz.setCombo('2'));
  await page.waitForTimeout(600);

  const dBox = await getCardBox('D');
  if (dBox) {
    const pad = 20;
    const cornerSize = 80;
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-d-tl.png'),
      clip: { x: dBox.x - pad, y: dBox.y - pad, width: cornerSize, height: cornerSize }
    });
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-d-bl.png'),
      clip: { x: dBox.x - pad, y: dBox.y + dBox.h - cornerSize + pad, width: cornerSize, height: cornerSize }
    });
  }

  const sBox = await getCardBox('S');
  if (sBox) {
    const pad = 20;
    const cornerSize = 80;
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-s-tl.png'),
      clip: { x: sBox.x - pad, y: sBox.y - pad, width: cornerSize, height: cornerSize }
    });
    await page.screenshot({
      path: path.join(OUT_DIR, 's7-card-s-bl.png'),
      clip: { x: sBox.x - pad, y: sBox.y + sBox.h - cornerSize + pad, width: cornerSize, height: cornerSize }
    });
  }

  // Full prep overview for regression comparison
  await page.evaluate(() => window.__cz.setCombo('1'));
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT_DIR, 's7-overview-1133-c1.png') });

  console.log('✅ S7 Corner captures completed successfully in', OUT_DIR);
  await browser.close();
})();
