"""sprint 26091901 e2e: 端到端 headless 模拟 iPad Safari 跑 practice 页, 抓 console + DOM 状态

用法: BASE_URL=http://127.0.0.1:8904 python3 e2e_dom_state.py
默认: http://127.0.0.1:8904 (本地 demo server)
"""
import os, json
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8904")
USERNAME = os.environ.get("USERNAME", "dad")
# sprint 26092003-secret-scrub: 强制要求 PASSWORD env, 不允许 fallback 默认值 (防 commit 明文回潮)
PASSWORD = os.environ["PASSWORD"]  # KeyError 是预期行为 (运维误用, 不要悄悄用错密码登录)

errors = []
warnings = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1024, "height": 768},
        user_agent="Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        ignore_https_errors=True,
    )
    page = ctx.new_page()

    page.on("console", lambda msg: (errors.append(msg.text) if msg.type == "error" else warnings.append(msg.text)))
    page.on("pageerror", lambda err: errors.append(f"PAGE_ERROR: {err}"))

    # 1) login
    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=15000)
    page.fill('input[name="username"]', USERNAME)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/practice", timeout=15000)

    # 2) 等计时器初始化
    page.wait_for_timeout(2000)

    # 3) DOM 状态
    state = page.evaluate("""() => {
      return {
        url: location.href,
        rulerInput: !!document.getElementById('rulerInput'),
        rulerRow: !!document.getElementById('rulerRow'),
        rulerRowChildren: document.getElementById('rulerRow')?.children.length || 0,
        ttCounter: !!document.getElementById('ttCounter'),
        ttCounterHTML: document.getElementById('ttCounter')?.innerHTML.substring(0, 200) || null,
        counterVar: typeof counter !== 'undefined',
        ticksVar: typeof ticks !== 'undefined' ? (ticks ? ticks.length : 'null') : 'undefined',
        gsapLoaded: typeof window.gsap !== 'undefined',
        gsapVersion: typeof window.gsap !== 'undefined' ? window.gsap.version : null,
        hasGsapFn: typeof hasGsap !== 'undefined',
        dragCtxVar: typeof dragCtx !== 'undefined' ? dragCtx.active : 'undefined',
        durationVar: typeof duration !== 'undefined' ? duration : 'undefined',
      };
    }""")

    print("=== STATE ===")
    print(json.dumps(state, ensure_ascii=False, indent=2))
    print("\n=== ERRORS ===")
    for e in errors:
        print("ERR:", e)
    print("\n=== WARNINGS ===")
    for w in warnings[:5]:
        print("WARN:", w)

    # 4) 点击科目尝试
    items = page.query_selector_all('.item-btn')
    print(f"\n=== ITEMS COUNT: {len(items)} ===")
    if items:
        items[0].click()
        page.wait_for_timeout(500)
        after_click = page.evaluate("() => ({selectedItemId: typeof selectedItemId !== 'undefined' ? selectedItemId : 'undef', startBtnDisabled: document.getElementById('startBtn')?.disabled})")
        print("AFTER CLICK:", after_click)

    browser.close()