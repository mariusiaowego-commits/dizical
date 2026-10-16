#!/usr/bin/env python3
"""
verify-equalheight-261013.py
Agy's independent automated verification script for canvas-01.html
Tests:
1. Equal-height iron law (ticket vs cards)
2. Height loop check (iframe height vs scrollHeight)
3. Combo tree layout (Combo 1 / Combo 2 / Combo 3)
4. State mods vs visible mods
5. One-screen right boundary & horizontal scroll
6. Slot & bus linkage
"""

import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

DEMO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'canvas-01.html'))
FILE_URL = f"file://{DEMO_PATH}"

VIEWPORTS = [
    ('1133x800', 1133, 800),
    ('744x1133', 744, 1133),
    ('440x956', 440, 956)
]

async def run_verification():
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        for vp_name, width, height in VIEWPORTS:
            results[vp_name] = {}
            page = await browser.new_page(viewport={'width': width, 'height': height})
            await page.goto(FILE_URL)
            await page.wait_for_timeout(1500)
            
            # 1. Height loop & base measurements
            base_info = await page.evaluate('''() => {
                const iframe = document.querySelector('iframe#czIframe') || document.querySelector('iframe');
                if (!iframe) return { error: 'No iframe found' };
                const cDoc = iframe.contentDocument;
                if (!cDoc) return { error: 'No iframe contentDocument' };
                
                const ticket = cDoc.querySelector('.pk-ticket') || cDoc.querySelector('#pkTicketCard');
                const ticketRect = ticket ? ticket.getBoundingClientRect() : null;
                const iframeRect = iframe.getBoundingClientRect();
                
                return {
                    iframeClientH: iframe.clientHeight,
                    iframeScrollH: iframe.scrollHeight,
                    iframeRectH: iframeRect.height,
                    docScrollH: cDoc.documentElement.scrollHeight,
                    bodyScrollH: cDoc.body.scrollHeight,
                    docClientH: cDoc.documentElement.clientHeight,
                    ticketRect: ticketRect ? {
                        l: Math.round(ticketRect.left),
                        t: Math.round(ticketRect.top),
                        w: Math.round(ticketRect.width),
                        h: Math.round(ticketRect.height),
                        b: Math.round(ticketRect.bottom)
                    } : null
                };
            }''')
            results[vp_name]['base_info'] = base_info
            
            # 2. Check each combo preset
            combos = ['1', '2', '3']
            results[vp_name]['combos'] = {}
            for combo in combos:
                combo_res = await page.evaluate('''(cb) => {
                    return new Promise((resolve) => {
                        // Switch combo
                        if (window.__cz && typeof window.__cz.setCombo === 'function') {
                            window.__cz.setCombo(cb);
                        } else {
                            // Try finding combo button or radio
                            const btn = document.querySelector(`[data-combo="${cb}"]`) || document.querySelector(`#combo-${cb}`);
                            if (btn) btn.click();
                        }
                        
                        setTimeout(() => {
                            const iframe = document.querySelector('iframe#czIframe') || document.querySelector('iframe');
                            const cDoc = iframe ? iframe.contentDocument : null;
                            if (!cDoc) {
                                resolve({ error: 'No iframe content' });
                                return;
                            }
                            
                            const ticket = cDoc.querySelector('.pk-ticket') || cDoc.querySelector('#pkTicketCard');
                            const tRect = ticket ? ticket.getBoundingClientRect() : null;
                            
                            // Check mods
                            const mods = Array.from(cDoc.querySelectorAll('.cz-mod, [data-mod]'));
                            const modDetails = mods.map(m => {
                                const r = m.getBoundingClientRect();
                                const cs = window.getComputedStyle(m);
                                const isVisible = cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0;
                                return {
                                    id: m.dataset.mod || m.id || m.className,
                                    visible: isVisible,
                                    display: cs.display,
                                    l: Math.round(r.left),
                                    t: Math.round(r.top),
                                    w: Math.round(r.width),
                                    h: Math.round(r.height),
                                    b: Math.round(r.bottom)
                                };
                            });
                            
                            // Rail & scroller info
                            const rail = cDoc.querySelector('.cz-mod-rail') || cDoc.querySelector('#czModRail') || cDoc.querySelector('.cz-stage-wrap');
                            let railInfo = null;
                            if (rail) {
                                const rr = rail.getBoundingClientRect();
                                railInfo = {
                                    clientW: rail.clientWidth,
                                    scrollW: rail.scrollWidth,
                                    clientH: rail.clientHeight,
                                    scrollH: rail.scrollHeight,
                                    overflowX: window.getComputedStyle(rail).overflowX,
                                    l: Math.round(rr.left),
                                    w: Math.round(rr.width)
                                };
                            }
                            
                            // Slot
                            const slot = cDoc.querySelector('.cz-punch-slot');
                            
                            // State mods vs visible mods
                            let stateMods = null;
                            if (window.__cz && window.__cz.state) {
                                stateMods = window.__cz.state.mods;
                            }
                            
                            resolve({
                                ticket: tRect ? {
                                    l: Math.round(tRect.left),
                                    t: Math.round(tRect.top),
                                    w: Math.round(tRect.width),
                                    h: Math.round(tRect.height),
                                    b: Math.round(tRect.bottom)
                                } : null,
                                mods: modDetails,
                                rail: railInfo,
                                slotExists: !!slot,
                                stateMods: stateMods
                            });
                        }, 500);
                    });
                }''', combo)
                results[vp_name]['combos'][combo] = combo_res
                
            await page.close()
        await browser.close()
        
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    asyncio.run(run_verification())
