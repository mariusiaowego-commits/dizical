"""sprint 26091901 follow-up e2e: playwright iPad Mini 算样式验证 touch-action:manipulation

用法: BASE_URL=http://127.0.0.1:8904 python3 e2e_touch_action.py
默认: http://127.0.0.1:8904 (本地 demo server)
"""
import os
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8904")
USERNAME = os.environ.get("USERNAME", "dad")
PASSWORD = os.environ.get("PASSWORD", "YoYo0905bamboo")

with sync_playwright() as p:
    ipad = p.devices['iPad Mini']
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(**ipad)
    page = ctx.new_page()

    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=15000)
    page.fill('input[name="username"]', USERNAME)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/practice", timeout=15000)
    page.wait_for_timeout(1500)

    state = page.evaluate("""() => ({
      timerCardTouchAction: getComputedStyle(document.getElementById('timerCard')).touchAction,
      stepPlusTouchAction: getComputedStyle(document.getElementById('ttStepPlus')).touchAction,
      stepMinusTouchAction: getComputedStyle(document.getElementById('ttStepMinus')).touchAction,
      stepPlusUserSelect: getComputedStyle(document.getElementById('ttStepPlus')).userSelect || getComputedStyle(document.getElementById('ttStepPlus')).webkitUserSelect,
      rulerInputTouchAction: getComputedStyle(document.getElementById('rulerInput')).touchAction,
      sessionPanelTouchAction: getComputedStyle(document.getElementById('sessionPanel')).touchAction,
    })""")

    print("=== iPad Mini UA 算样式 ===")
    for k, v in state.items():
        print(f"  {k:32s} = {v}")

    # 反向断言: 计时器区域 manipulation, 其他区域 auto, ruler none
    assert state['timerCardTouchAction'] == 'manipulation', f"#timerCard 期望 manipulation, 实测 {state['timerCardTouchAction']}"
    assert state['stepPlusTouchAction'] == 'manipulation'
    assert state['stepMinusTouchAction'] == 'manipulation'
    assert state['stepPlusUserSelect'] == 'none'
    assert state['rulerInputTouchAction'] == 'none', f".ruler-input 期望 none (sprint 26091901), 实测 {state['rulerInputTouchAction']}"
    assert state['sessionPanelTouchAction'] in ('auto', 'pan-y', 'manipulation'), \
        f"#sessionPanel 期望保持默认, 实测 {state['sessionPanelTouchAction']}"

    print("\n✅ ALL CHECKS PASS")
    browser.close()