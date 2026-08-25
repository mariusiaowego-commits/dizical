"""prepare 页 UI 1.0 / 2.0 双版本回归.

覆盖:
- 模板同时含 v1 + v2 markup (data-version)
- 默认走 v2 (head script localStorage fallback '2.0')
- ?ui=v1 / ?ui=v2 由 JS 识别 (client-side, HTML 始终双份)
- 齿轮切换 + localStorage.prepare_ui
- 粒子 canvas + 暖色 token + reduced-motion
- v1 老结构仍在 (hero / tap-hint / steps-section)
- 0 新依赖 (无 three.js / framer-motion)
- 静态 css/js 可被 /static 访问
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.kid_app.app import app, render

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "src" / "kid_app" / "templates" / "prepare.html"
CSS = ROOT / "src" / "kid_app" / "static" / "css" / "prepare-2dot0.css"
JS = ROOT / "src" / "kid_app" / "static" / "js" / "prepare-2dot0.js"


def _html():
    return render(
        "prepare",
        eyebrow="竹笛练习准备",
        bless_main="今天的练习",
        bless_accent="会很棒",
        enc_list_json="[]",
        weekday="周一",
        today_str="08月25日",
        streak=7,
        encouragement="深呼吸三次",
        steps_html='<div class="step-card" id="step1" onclick="toggleStep(this)"><div class="step-check" id="check1"></div></div>',
        assign_eyebrow="本周练习要求",
        assign_title="作业",
        assign_items_html="<div class='assign-subject'></div>",
        assign_images=[],
        cta_btn_text="开始行动",
        active_nav="prepare",
    )


@pytest.fixture(scope="module")
def html():
    return _html()


@pytest.fixture(scope="module")
def tpl_src():
    return TPL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css_src():
    return CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js_src():
    return JS.read_text(encoding="utf-8")


def test_files_exist():
    assert TPL.is_file()
    assert CSS.is_file()
    assert JS.is_file()


def test_both_versions_in_markup(html):
    assert 'data-version="1.0"' in html
    assert 'data-version="2.0"' in html
    assert html.count("data-version") >= 2


def test_v1_structure_kept(html):
    assert 'class="hero"' in html
    assert 'id="hero"' in html
    assert "tap-hint" in html
    assert 'id="stepsSection"' in html
    assert "点击任意处继续" in html
    assert "function toggleStep" in html


def test_v2_particle_hero(html):
    assert 'id="heroV2"' in html
    assert 'id="pollen"' in html
    assert 'id="uiToggle"' in html
    assert "/static/css/prepare-2dot0.css" in html
    assert "/static/js/prepare-2dot0.js" in html


def test_default_is_v2(tpl_src, js_src):
    assert "localStorage.getItem(k) || '2.0'" in tpl_src
    assert "prepare_ui" in tpl_src
    assert "prepare_ui" in js_src


def test_query_ui_v1_v2_handled(tpl_src, js_src):
    assert "p === 'v1'" in tpl_src
    assert "p === 'v2'" in tpl_src
    assert "ui=v1" in js_src or "v1" in js_src
    assert "ui=v2" in js_src or "v2" in js_src


def test_no_new_deps(html, js_src, css_src):
    blob = html + js_src + css_src
    assert "three.js" not in blob
    assert "three.min.js" not in blob
    assert "framer-motion" not in blob
    assert "lenis" not in blob.lower()


def test_warm_palette_not_dark_navy(css_src, tpl_src):
    blob = css_src + tpl_src
    assert "--coral:" in blob or "--coral:" in tpl_src
    assert "--peach:" in tpl_src
    assert "#0a0e27" not in blob
    assert "#14193d" not in blob


def test_reduced_motion_and_ipad_touch(css_src, js_src):
    assert "prefers-reduced-motion" in css_src
    assert "touch-action: none" in css_src
    assert "preventDefault" in js_src
    assert "IntersectionObserver" in js_src
    assert "cancelAnimationFrame" in js_src


def test_static_css_js_public():
    client = TestClient(app)
    r_css = client.get("/static/css/prepare-2dot0.css")
    r_js = client.get("/static/js/prepare-2dot0.js")
    assert r_css.status_code == 200, r_css.text[:200]
    assert r_js.status_code == 200, r_js.text[:200]
    assert "hero-v2" in r_css.text
    assert "startParticles" in r_js.text or "Particle" in r_js.text


def test_single_step_id_not_duplicated(html):
    """steps_html 只注入一次, 避免 v1/v2 双份 id 冲突."""
    assert html.count('id="step1"') == 1
    assert html.count('id="check1"') == 1
