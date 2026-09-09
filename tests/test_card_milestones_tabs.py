"""
Tests for Sprint 26090904: card-milestones 双 tab (milestone + seasonal) + achieved_at 排序 + UI 优化.

覆盖:
1. _milestone_html("milestone") 只选 milestone 类, _milestone_html("seasonal") 只选 seasonal 类
2. _milestone_html sort_by_achieved_at 排序行为 (降序)
3. /achievements 页面渲染包含双 tab 结构 (milestones-tabs, tab-pane-milestone, tab-pane-seasonal)
4. zizhudiao_a 等 milestone 类徽章正常出现在 milestone tab 中
"""
import pytest
from fastapi.testclient import TestClient

from src.kid_app.app import app, _milestone_html
from src.database import db
from src import db_adapter


@pytest.fixture
def client(monkeypatch):
    async def _mock_user(*args, **kwargs):
        return {"id": 1, "username": "yoyo", "role": "student"}
    monkeypatch.setattr("src.kid_app.auth.get_current_user", _mock_user)
    return TestClient(app)


def test_milestone_html_category_separation():
    """验证 _milestone_html 传 category='milestone' 与 'seasonal' 输出互斥."""
    m_html = _milestone_html("milestone")
    s_html = _milestone_html("seasonal")

    assert isinstance(m_html, str)
    assert isinstance(s_html, str)

    # 季节性成就不会出现在 milestone 结果中 (例如 early_riser, little_chick_commander)
    assert "data-id='early_riser'" not in m_html
    assert "data-id='little_chick_commander'" not in m_html

    # 里程碑成就不会出现在 seasonal 结果中 (例如 zizhudiao_a 或 grade 系列)
    assert "data-id='zizhudiao_a'" not in s_html


def test_milestone_html_achieved_at_sorting():
    """验证 unlocked_list 按 achieved_at 降序排列."""
    conn = db._get_connection()
    cur = conn.cursor()

    # 插入 2 个用于测试排序的 milestone badge
    cur.execute("""
        INSERT OR REPLACE INTO achievements (
            id, name, type, category, stat_logic, description,
            display_format, threshold, seasonal_type, unlock_strategy, achieved_at_override, sort_order
        ) VALUES
        ('test_sort_older', '老成就', '突破', 'milestone', '', '老成就描述', 'count', 1, 'monthly', 'immediate', '2026-08-01', 1),
        ('test_sort_newer', '新成就', '突破', 'milestone', '', '新成就描述', 'count', 1, 'monthly', 'immediate', '2026-09-08', 2)
    """)
    conn.commit()

    try:
        # 1. 默认 sort_by_achieved_at=True: 新成就 (2026-09-08) 应该排在 老成就 (2026-08-01) 前面
        html_sorted = _milestone_html("milestone", sort_by_achieved_at=True)
        idx_newer = html_sorted.find("data-id='test_sort_newer'")
        idx_older = html_sorted.find("data-id='test_sort_older'")
        assert idx_newer != -1 and idx_older != -1
        assert idx_newer < idx_older, "最新达成的成就应排在前面 (降序)"

        # 2. sort_by_achieved_at=False: 按照 sort_order 顺序 (test_sort_older sort_order=1 先于 test_sort_newer sort_order=2)
        html_unsorted = _milestone_html("milestone", sort_by_achieved_at=False)
        idx_newer_raw = html_unsorted.find("data-id='test_sort_newer'")
        idx_older_raw = html_unsorted.find("data-id='test_sort_older'")
        assert idx_newer_raw != -1 and idx_older_raw != -1
        assert idx_older_raw < idx_newer_raw, "不按时间排序时保持 sort_order 顺序"
    finally:
        cur.execute("DELETE FROM achievements WHERE id IN ('test_sort_older', 'test_sort_newer')")
        conn.commit()


def test_achievements_page_renders_dual_tabs(client):
    """GET /achievements 验证双 tab UI 结构完整性."""
    r = client.get("/achievements")
    assert r.status_code == 200
    html = r.text

    # 1. 板块容器
    assert 'id="card-milestones"' in html

    # 2. Tab 切换器按钮
    assert 'class="milestones-tabs"' in html
    assert 'data-tab="milestone"' in html
    assert 'data-tab="seasonal"' in html
    assert 'id="milestone-tab-count"' in html
    assert 'id="seasonal-tab-count"' in html

    # 3. 两个 Tab Pane
    assert 'id="tab-pane-milestone"' in html
    assert 'id="tab-pane-seasonal"' in html

    # 4. 每个 Tab 的已解锁/未解锁网格与计数
    assert 'id="unlocked-grid-milestone"' in html
    assert 'id="locked-grid-milestone"' in html
    assert 'id="unlocked-count-milestone"' in html
    assert 'id="locked-count-milestone"' in html

    assert 'id="unlocked-grid-seasonal"' in html
    assert 'id="locked-grid-seasonal"' in html
    assert 'id="unlocked-count-seasonal"' in html
    assert 'id="locked-count-seasonal"' in html

    # 5. Milestone Pane 默认 active, Seasonal 默认隐藏
    assert 'class="milestones-tab-pane active" id="tab-pane-milestone"' in html
    assert 'id="tab-pane-seasonal" role="tabpanel" style="display:none;"' in html


def test_zizhudiao_visible_in_milestone_tab(client):
    """紫竹调徽章 (zizhudiao_a) 属于 milestone, 必须出现在 milestone tab 中."""
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO achievements (
            id, name, type, category, stat_logic, description,
            display_format, threshold, seasonal_type, unlock_strategy, achieved_at_override
        ) VALUES (
            'zizhudiao_a', '紫竹调一遍过', '突破', 'milestone', '', '中秋演出紫竹调一遍过',
            'count', 1, 'monthly', 'immediate', '2026-09-05'
        )
    """)
    conn.commit()

    try:
        r = client.get("/achievements")
        assert r.status_code == 200
        html = r.text

        # 截取 milestone tab pane 的 HTML 区间
        m_pane_start = html.find('id="tab-pane-milestone"')
        s_pane_start = html.find('id="tab-pane-seasonal"')
        assert m_pane_start != -1 and s_pane_start != -1
        milestone_pane_html = html[m_pane_start:s_pane_start]

        # 验证 zizhudiao_a 出现在 milestone pane
        assert "data-id='zizhudiao_a'" in milestone_pane_html
        assert "紫竹调一遍过" in milestone_pane_html
    finally:
        cur.execute("DELETE FROM achievements WHERE id = 'zizhudiao_a'")
        conn.commit()
