#!/usr/bin/env python3
"""
verify-real-window-261011.py
Agy's independent real-window verification script for canvas-01.html
Verifies:
1. P0-2 (Narrow stacking / 窄屏纵向堆叠) in real windows vs #czVp button in desktop window.
2. P2-1 (landedBy & observedMs & clockProbe) under real clock & race condition analysis.
3. P0-1 (modCol.bottom vs ticket.bottom vs body.bottom) across presets and viewports.
"""

import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

DEMO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'canvas-01.html'))
FILE_URL = f"file://{DEMO_PATH}"

PRESETS = {
    '1': ['A', 'S'],
    '2': ['A', 'D', 'Q'],
    '3': ['A', 'B', 'S', 'D', 'R', 'Q']
}

VIEWPORTS = [
    ('1280x800', 1280, 800),
    ('1133x800', 1133, 800),
    ('744x1133', 744, 1133),
    ('440x956', 440, 956)
]

async def verify_viewports(browser):
    report = {}
    for name, w, h in VIEWPORTS:
        report[name] = {}
        page = await browser.new_page(viewport={'width': w, 'height': h})
        await page.goto(FILE_URL)
        await page.wait_for_timeout(1000)
        
        for p_name, p_mods in PRESETS.items():
            res = await page.evaluate('''([p_mods, p_name]) => {
                return new Promise((resolve) => {
                    window.__cz.setMods(p_mods, false);
                    setTimeout(() => {
                        const o = window.__cz.measure('预设' + p_name);
                        const cd = window.__cz.canvasDoc();
                        resolve({
                            docClientW: o.docClientW,
                            docScrollW: o.docScrollW,
                            railFlexDir: o.canvas.railFlexDir,
                            railClientW: o.railClientW,
                            railScrollW: o.railW,
                            modCount: o.modules.length,
                            rowCount: o.rowCount,
                            modTops: o.modules.map(m => Math.round(m.top)),
                            modColBottom: o.canvas.modColBottom,
                            ticketBottom: o.canvas.ticketBottom,
                            ticketH: o.canvas.ticketH,
                            bodyBottom: cd && cd.body ? +cd.body.getBoundingClientRect().bottom.toFixed(1) : null,
                            overflowP01: +(o.canvas.modColBottom - o.canvas.ticketBottom).toFixed(1)
                        });
                    }, 250);
                });
            }''', [p_mods, p_name])
            report[name][f'preset_{p_name}'] = res
        await page.close()
    return report

async def verify_hermes_scenario(browser):
    # Desktop window 1265px, click #czVp button '744'
    page = await browser.new_page(viewport={'width': 1265, 'height': 800})
    await page.goto(FILE_URL)
    await page.wait_for_timeout(1000)
    
    res = await page.evaluate('''() => {
        return new Promise((resolve) => {
            const btn744 = document.querySelector('#czVp button[data-vp="744"]');
            if (btn744) btn744.click();
            setTimeout(() => {
                const out = {};
                ['1', '2', '3'].forEach(pr => {
                    const mods = pr === '1' ? ['A', 'S'] : (pr === '2' ? ['A', 'D', 'Q'] : ['A', 'B', 'S', 'D', 'R', 'Q']);
                    window.__cz.setMods(mods, false);
                    const o = window.__cz.measure('预设' + pr + '/744/light');
                    out['preset_' + pr] = {
                        docClientW: o.docClientW,
                        stateVp: window.__cz.state.vp,
                        railFlexDir: o.canvas.railFlexDir,
                        railClientW: o.railClientW,
                        railScrollW: o.railW,
                        rowCount: o.rowCount,
                        modCount: o.modules.length
                    };
                });
                resolve(out);
            }, 250);
        });
    }''')
    await page.close()
    return res

async def verify_insert_and_timing(browser):
    page = await browser.new_page(viewport={'width': 1280, 'height': 800})
    await page.goto(FILE_URL)
    await page.wait_for_timeout(1000)
    
    # 1. Audit insert pass run
    audit_res = await page.evaluate('''() => window.__cz.runAudit()''')
    insert_audit = audit_res.get('insert', {})
    
    # 2. Direct runInsert() timing and finish race
    race_res = await page.evaluate('''() => {
        return new Promise((resolve) => {
            window.__cz.resetInsert();
            setTimeout(() => {
                const t0 = performance.now();
                const job = window.__cz.runInsert();
                let finishEventTime = null;
                job.anim.addEventListener('finish', () => {
                    finishEventTime = performance.now() - t0;
                });
                job.landed.then(() => {
                    const tLand = performance.now() - t0;
                    setTimeout(() => {
                        resolve({
                            landedBy: job.landedBy(),
                            landTimeMs: +tLand.toFixed(1),
                            finishEventTimeMs: finishEventTime ? +finishEventTime.toFixed(1) : null
                        });
                    }, 500);
                });
            }, 100);
        });
    }''')
    
    # 3. Simulate micro-jitter race
    jitter_res = await page.evaluate('''() => {
        return new Promise((resolve) => {
            window.__cz.resetInsert();
            setTimeout(() => {
                const t0 = performance.now();
                const job = window.__cz.runInsert();
                // 50ms main-thread block at 270ms
                setTimeout(() => {
                    const blockUntil = performance.now() + 50;
                    while (performance.now() < blockUntil) {}
                }, 270);
                job.landed.then(() => {
                    const tLand = performance.now() - t0;
                    setTimeout(() => {
                        resolve({
                            landedBy: job.landedBy(),
                            landTimeMs: +tLand.toFixed(1)
                        });
                    }, 500);
                });
            }, 100);
        });
    }''')
    
    await page.close()
    return {
        'audit_insert': insert_audit,
        'direct_race': race_res,
        'jitter_race': jitter_res
    }

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        print("=== 1. REAL WINDOW MEASUREMENTS (P0-2 & P0-1) ===")
        v_report = await verify_viewports(browser)
        print(json.dumps(v_report, indent=2, ensure_ascii=False))
        
        print("\n=== 2. HERMES SCENARIO (1265px window, #czVp=744) ===")
        h_report = await verify_hermes_scenario(browser)
        print(json.dumps(h_report, indent=2, ensure_ascii=False))
        
        print("\n=== 3. INSERT & TIMING RACING (P2-1) ===")
        t_report = await verify_insert_and_timing(browser)
        print(json.dumps(t_report, indent=2, ensure_ascii=False))
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
