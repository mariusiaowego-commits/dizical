"""
测试 Badge 后台管理功能
"""

import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from src.kid_app.app import app
    return TestClient(app)


@pytest.fixture
def sample_badge():
    """示例 badge 数据"""
    return {
        "id": "test_badge_1",
        "name": "测试徽章",
        "type": "突破",
        "category": "milestone",
        "stat_logic": "测试统计逻辑",
        "description": "测试描述",
        "cond_text": "测试条件",
        "unlock_strategy": "calc",
        "sort_order": 100,
        "display_on_achievements": 1,
    }


class TestBadgeAdminAPI:
    """测试 Badge Admin API"""

    def test_get_badges(self, client):
        """测试获取所有 badges"""
        response = client.get("/config/badge-admin/api/badges")
        assert response.status_code == 200
        data = response.json()
        assert "badges" in data
        assert isinstance(data["badges"], list)

    def test_get_single_badge(self, client):
        """测试获取单个 badge"""
        # 先获取所有 badges
        response = client.get("/config/badge-admin/api/badges")
        badges = response.json()["badges"]
        
        if badges:
            badge_id = badges[0]["id"]
            response = client.get(f"/config/badge-admin/api/badges/{badge_id}")
            assert response.status_code == 200
            data = response.json()
            assert "badge" in data
            assert data["badge"]["id"] == badge_id

    def test_get_nonexistent_badge(self, client):
        """测试获取不存在的 badge"""
        response = client.get("/config/badge-admin/api/badges/nonexistent_badge")
        assert response.status_code == 404

    def test_update_badge_metadata(self, client):
        """测试更新 badge 元数据"""
        # 先获取一个 badge
        response = client.get("/config/badge-admin/api/badges")
        badges = response.json()["badges"]
        
        if badges:
            badge_id = badges[0]["id"]
            
            # 更新元数据
            update_data = {
                "name": "更新后的名称",
                "cond_text": "更新后的条件",
                "description": "更新后的描述",
            }
            
            response = client.put(
                f"/config/badge-admin/api/badges/{badge_id}",
                json=update_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True

    def test_update_badge_invalid_fields(self, client):
        """测试更新无效字段"""
        response = client.get("/config/badge-admin/api/badges")
        badges = response.json()["badges"]
        
        if badges:
            badge_id = badges[0]["id"]
            
            # 尝试更新无效字段
            update_data = {
                "invalid_field": "value",
                "id": "new_id",  # 不允许修改 id
            }
            
            response = client.put(
                f"/config/badge-admin/api/badges/{badge_id}",
                json=update_data
            )
            assert response.status_code == 400

    def test_update_sort_order(self, client):
        """测试批量更新排序"""
        # 先获取 badges
        response = client.get("/config/badge-admin/api/badges")
        badges = response.json()["badges"]
        
        if len(badges) >= 2:
            # 创建排序数据
            order_data = {
                "order": [
                    {"id": badges[0]["id"], "sort_order": 200},
                    {"id": badges[1]["id"], "sort_order": 100},
                ]
            }
            
            response = client.put(
                "/config/badge-admin/api/badges/sort-order",
                json=order_data
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True

    def test_get_display_config(self, client):
        """测试获取显示配置"""
        response = client.get("/config/badge-admin/api/display-config")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "sort_mode" in data["config"]

    def test_update_display_config(self, client):
        """测试更新显示配置"""
        update_data = {
            "sort_mode": "achieved_at_desc",
            "show_locked": True,
        }
        
        response = client.put(
            "/config/badge-admin/api/display-config",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_badge_admin_page(self, client):
        """测试管理页面加载"""
        response = client.get("/config/badge-admin")
        assert response.status_code == 200
        assert "Badge 后台管理" in response.text


class TestBadgeAdminIntegration:
    """集成测试"""

    def test_full_workflow(self, client):
        """测试完整工作流"""
        # 1. 获取所有 badges
        response = client.get("/config/badge-admin/api/badges")
        assert response.status_code == 200
        badges = response.json()["badges"]
        
        if not badges:
            pytest.skip("No badges in database")
        
        badge_id = badges[0]["id"]
        
        # 2. 更新 badge 元数据
        update_data = {
            "name": "集成测试徽章",
            "cond_text": "集成测试条件",
            "description": "集成测试描述",
        }
        
        response = client.put(
            f"/config/badge-admin/api/badges/{badge_id}",
            json=update_data
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True
        
        # 3. 验证更新
        response = client.get(f"/config/badge-admin/api/badges/{badge_id}")
        assert response.status_code == 200
        badge = response.json()["badge"]
        assert badge["name"] == "集成测试徽章"
        assert badge["cond_text"] == "集成测试条件"
        assert badge["description"] == "集成测试描述"
        
        # 4. 更新显示配置
        response = client.put(
            "/config/badge-admin/api/display-config",
            json={"sort_mode": "sort_order"}
        )
        assert response.status_code == 200
        
        # 5. 验证配置更新
        response = client.get("/config/badge-admin/api/display-config")
        assert response.status_code == 200
        config = response.json()["config"]
        assert config["sort_mode"] == "sort_order"
