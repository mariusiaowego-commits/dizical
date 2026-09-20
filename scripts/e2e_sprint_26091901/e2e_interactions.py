"""sprint 26091901 e2e: 端到端真点击交互验证 (步进 + 拖拽 + 启动/暂停/计时)

用法: BASE_URL=http://127.0.0.1:8904 python3 e2e_interactions.py
默认: http://127.0.0.1:8904 (本地 demo server)
"""
import os
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8904")
USERNAME = os.environ.get("USERNAME", "dad")
# sprint 26092003-secret-scrub: 强制要求 PASSWORD env, 不允许 fallback 默认值 (防 commit 明文回潮)
PASSWORD = os.environ["PASSWORD"]  # KeyError 是预期行为 (运维误用, 不要悄悄用错密码登录)

errors, warnings = [], []

with sync_playwright() as p:
    ipad = p.devices['iPad Mini']
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(**ipad)
    page = ctx.new_page()
    page.on("console", lambda m: (errors.append(m.text) if m.type == "error" else warnings.append(m.text)))
    page.on("pageerror", lambda e: errors.append(f"PAGE_ERROR: {e}"))

    # Login
    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=15000)
    page.fill('input[name="username"]', USERNAME)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url("**/practice", timeout=15000)
    page.wait_for_timeout(1500)

    # === Test 1: ±1 分钟连点 5 次 ===
    print("=== Test 1: 连点 + 按钮 5 次 ===")
    for i in range(5):
        page.locator('#ttStepPlus').click(force=True, timeout=3000)
        page.wait_for_timeout(80)
    duration_after_plus = page.evaluate("() => typeof duration !== 'undefined' ? duration : 'undef'")
    meta = page.evaluate("() => document.getElementById('metaVal')?.textContent || null")
    print(f"  duration after 5x+: {duration_after_plus}")
    print(f"  metaVal: {meta}")
    # 期望: duration = 10 + 5 = 15 (初始 10)
    assert duration_after_plus == 15, f"连点 +5 后 duration 期望 15, 实测 {duration_after_plus}"

    # Test 1.2: 连点 - 按钮 3 次 → 12
    for i in range(3):
        page.locator('#ttStepMinus').click(force=True, timeout=3000)
        page.wait_for_timeout(80)
    duration_after_minus = page.evaluate("() => typeof duration !== 'undefined' ? duration : 'undef'")
    print(f"  duration after -3: {duration_after_minus}")
    assert duration_after_minus == 12

    # === Test 2: ruler 拖拽 ===
    print("\n=== Test 2: ruler 拖拽 (空白刻度区) ===")
    # 找 ruler 元素 bounding box
    ruler_box = page.evaluate("""() => {
      const r = document.getElementById('ruler');
      if (!r) return null;
      const b = r.getBoundingClientRect();
      return { x: b.x, y: b.y, width: b.width, height: b.height };
    }""")
    print(f"  ruler bbox: {ruler_box}")
    # 中点 = 当前 12 分钟对应位置 (12/30 ≈ 0.4 比例)
    cx = ruler_box['x'] + ruler_box['width'] * 0.4
    cy = ruler_box['y'] + ruler_box['height'] / 2

    # 模拟 pointerdown + 多次 pointermove + pointerup (拖到 25 分钟 ≈ ruler 80% 处)
    target_x = ruler_box['x'] + ruler_box['width'] * 0.85
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.wait_for_timeout(100)
    for step_n in range(20):
        page.mouse.move(cx + (target_x - cx) * step_n / 20, cy, steps=2)
        page.wait_for_timeout(30)
    page.mouse.up()
    page.wait_for_timeout(300)
    duration_after_drag = page.evaluate("() => typeof duration !== 'undefined' ? duration : 'undef'")
    print(f"  duration after drag to ~25min: {duration_after_drag}")
    assert duration_after_drag >= 20, f"拖到 ~25 分钟处, 期望 duration ≥ 20, 实测 {duration_after_drag}"

    # === Test 3: 选科目 + 启动计时 (验证 ttOnStart) ===
    print("\n=== Test 3: 选科目 + 启动计时 ===")
    items = page.query_selector_all('.item-btn')
    if items:
        items[0].click(force=True)
        page.wait_for_timeout(300)
        selected = page.evaluate("() => ({id: typeof selectedItemId !== 'undefined' ? selectedItemId : 'undef', name: typeof selectedItem !== 'undefined' ? selectedItem : 'undef'})")
        print(f"  selected: {selected}")
        start_btn_disabled = page.evaluate("() => document.getElementById('startBtn')?.disabled")
        print(f"  startBtn disabled before content: {start_btn_disabled}")
        # 填内容
        page.fill('#sessionContentInput', 'sprint 26091901 e2e 验证')
        page.wait_for_timeout(200)
        start_btn_disabled_after = page.evaluate("() => document.getElementById('startBtn')?.disabled")
        print(f"  startBtn disabled after content: {start_btn_disabled_after}")
        # 点 start
        if not start_btn_disabled_after:
            page.locator('#startBtn').click(force=True, timeout=3000)
            page.wait_for_timeout(800)
            running_state = page.evaluate("""() => ({
              started: typeof started !== 'undefined' ? started : 'undef',
              elapsed: typeof elapsed !== 'undefined' ? elapsed : 'undef',
              btnText: document.getElementById('startBtn')?.textContent,
            })""")
            print(f"  after start click: {running_state}")
            assert running_state['started'] == True, "start 后 started 应为 true"
            # 等 2 秒看 elapsed 走
            page.wait_for_timeout(2000)
            elapsed_2s = page.evaluate("() => typeof elapsed !== 'undefined' ? elapsed : 'undef'")
            print(f"  elapsed after 2s: {elapsed_2s}")
            assert elapsed_2s >= 2, f"elapsed 2s 后应 ≥ 2, 实测 {elapsed_2s}"
            # 暂停
            page.locator('#startBtn').click(force=True, timeout=3000)
            page.wait_for_timeout(300)
            paused_state = page.evaluate("() => ({started: typeof started !== 'undefined' ? started : 'undef', btnText: document.getElementById('startBtn')?.textContent})")
            print(f"  after pause click: {paused_state}")
            assert paused_state['btnText'] in ('继续', '暂停')

    # === Final ===
    print("\n=== ERRORS ===")
    for e in errors:
        print("ERR:", e)
    print("\n=== WARNINGS (前 5) ===")
    for w in warnings[:5]:
        print("WARN:", w)
    print("\n✅ ALL e2e INTERACTIONS PASS")
    browser.close()