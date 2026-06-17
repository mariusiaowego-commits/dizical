# Badge 后台管理面板 - 开发文档

## 概述

Badge 后台管理面板是一个可视化界面，用于管理 dizical 项目中的 badge 元数据和展示配置。

## 功能特性

### 1. Badge 元数据管理
- 编辑 badge 名称
- 编辑条件文案 (modal-cond)
- 编辑描述 (modal-desc)
- 编辑统计逻辑说明
- 设置解锁策略 (calc/immediate)
- 设置解锁时间覆盖
- 设置排序权重
- 控制是否在 achievements 页面展示

### 2. Badge 图片预览
- 显示当前 badge 图片
- 显示图片版本信息
- 显示解锁状态

### 3. Achievements 展示排序
- 按获取时间降序 (默认)
- 按获取时间升序
- 按自定义排序权重
- 按类型分组

### 4. 筛选和搜索
- 按状态筛选 (已解锁/未解锁)
- 按类型筛选 (里程碑/季节性)
- 按名称搜索

## 技术实现

### 文件结构
```
src/kid_app/routes/badge_admin.py          # 路由 + API
src/kid_app/templates/config-badge-admin.html  # 模板
src/migrate_badge_admin_fields.py          # 数据库迁移
tests/test_badge_admin.py                  # 测试
```

### API 端点

#### 获取所有 badges
```
GET /config/badge-admin/api/badges
```

#### 获取单个 badge
```
GET /config/badge-admin/api/badges/{badge_id}
```

#### 更新 badge 元数据
```
PUT /config/badge-admin/api/badges/{badge_id}
Body: { name, cond_text, description, stat_logic, unlock_strategy, achieved_at_override, sort_order, display_on_achievements }
```

#### 批量更新排序
```
PUT /config/badge-admin/api/badges/sort-order
Body: { order: [{ id: "badge_id", sort_order: 1 }, ...] }
```

#### 获取显示配置
```
GET /config/badge-admin/api/display-config
```

#### 更新显示配置
```
PUT /config/badge-admin/api/display-config
Body: { sort_mode: "achieved_at_desc" }
```

### 数据库变更

新增字段：
- `achievements.display_on_achievements` (INTEGER DEFAULT 1)
- `achievements.sort_order_override` (INTEGER)

新增配置表 (可选)：
- `settings` 表中新增 `badge_display_*` 配置项

## 使用方法

### 访问管理页面
```
http://localhost:8765/config/badge-admin
```

### 编辑 badge
1. 在左侧列表中选择要编辑的 badge
2. 在右侧表单中修改元数据
3. 点击"保存"按钮

### 修改排序
1. 在编辑面板底部找到"排序配置"
2. 选择排序模式
3. 配置自动保存

## 测试

运行测试：
```bash
python3 -m pytest tests/test_badge_admin.py -xvs
```

测试覆盖率：
- API 端点测试: 9 个
- 集成测试: 1 个

## 注意事项

1. 所有修改需要 PIN 验证 (待实现)
2. 图片上传功能需要配合 badge workflow
3. 排序配置存储在 settings 表中
