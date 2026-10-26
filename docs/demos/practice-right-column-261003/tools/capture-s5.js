const fs = require('fs');
const path = require('path');
const { chromium } = require('/Users/mt16/.hermes/profiles/quagmire/skills/ljg-skills/skills/ljg-card/node_modules/playwright');

const URL = 'http://127.0.0.1:8771/practice-right-column-261003/canvas-01.html';
const OUT_DIR = '/tmp/v38-s5-shots';

if (!fs.existsSync(OUT_DIR)) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  console.log('Navigating to ' + URL);
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  const targets = [
    { vp: '1133', w: 1133, h: 744, combo: '2', name: '1133-c2.png' },
    { vp: '1133', w: 1133, h: 744, combo: '3', name: '1133-c3.png' },
    { vp: '744', w: 744, h: 1133, combo: '2', name: '744-c2.png' },
    { vp: '744', w: 744, h: 1133, combo: '3', name: '744-c3.png' },
    { vp: '440', w: 440, h: 956, combo: '2', name: '440-c2.png' },
    { vp: '440', w: 440, h: 956, combo: '3', name: '440-c3.png' },
  ];

  for (const t of targets) {
    await page.setViewportSize({ width: t.w, height: t.h });
    await page.click('#czVp [data-vp="' + t.vp + '"]');
    await page.waitForTimeout(400);
    await page.evaluate((c) => window.__cz.setCombo(c), t.combo);
    await page.waitForTimeout(600);

    const shotPath = path.join(OUT_DIR, t.name);
    await page.screenshot({ path: shotPath, fullPage: true });
    console.log(`Saved screenshot: ${shotPath}`);

    // 特别截取 440 C2 下 S 横条特写
    if (t.vp === '440' && t.combo === '2') {
      const sShotPath = path.join(OUT_DIR, '440-c2-card-s-bar.png');
      try {
        await page.evaluate(() => {
          const cd = window.__cz.canvasDoc();
          const s = cd.querySelector('.cz-mod[data-mod="S"]');
          if (s) s.scrollIntoView();
        });
        await page.waitForTimeout(300);
        await page.screenshot({ path: sShotPath, fullPage: true });
        console.log(`Saved Card S view: ${sShotPath}`);
      } catch (err) {
        console.warn('Card S close-up fallback:', err.message);
      }
    }
  }

  await browser.close();
  console.log('All screenshots captured successfully in ' + OUT_DIR);
})();
