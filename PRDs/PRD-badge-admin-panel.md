# PRD: Badge 后台管理面板

## 1. 背景

当前 badge 管理需要直接操作数据库或通过 badge workflow 创建新 badge。用户需要一个可视化的后台管理面板来：
- 编辑 badge 的元数据（名称、条件、描述）
- 预览和管理 badge 图片
- 控制 achievements 页面的展示和排序

## 2. 功能需求

### 2.1 Badge 元数据管理
- **编辑字段**：
  - `name` (badge 名称)
  - `cond_text` (modal 条件文案)
  - `description` (modal 描述)
  - `stat_logic` (统计逻辑说明)
  - `unlock_strategy` (解锁策略: calc/immediate)
  - `achieved_at_override` (表彰型 badge 的解锁时间)
- **只读字段**：
  - `id` (badge ID)
  - `type` (类型标签)
  - `category` (分类)
  - `threshold` (阈值)

### 2.2 Badge 图片管理
- 预览当前 badge 图片
- 显示图片版本信息
- 支持上传新图片（可选，需要配合 badge workflow）

### 2.3 Achievements 展示排序
- **排序模式**：
  - 按获取时间降序（默认）
  - 按获取时间升序
  - 按 sort_order 自定义排序
  - 按类型分组排序
- **显示控制**：
  - 控制哪些 badge 在 achievements 页面展示
  - 已解锁/未解锁分组

### 2.4 批量操作
- 批量更新 sort_order
- 批量修改 unlock_strategy

## 3. 数据模型

### 3.1 新增字段（achievements 表）
```sql
ALTER TABLE achievements ADD COLUMN display_on_achievements INTEGER DEFAULT 1;
ALTER TABLE achievements ADD COLUMN sort_order_override INTEGER;
```

### 3.2 新增配置表（可选）
```sql
CREATE TABLE badge_display_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 4. API 设计

### 4.1 获取所有 badges
```
GET /config/badge-admin/api/badges
```

### 4.2 更新 badge 元数据
```
PUT /config/badge-admin/api/badges/{badge_id}
Body: { name, cond_text, description, ... }
```

### 4.3 更新排序
```
PUT /config/badge-admin/api/badges/sort-order
Body: { order: [{ id: "badge_id", sort_order: 1 }, ...] }
```

### 4.4 获取排序配置
```
GET /config/badge-admin/api/display-config
```

### 4.5 更新排序配置
```
PUT /config/badge-admin/api/display-config
Body: { sort_mode: "achieved_at_desc", ... }
```

## 5. UI 设计

### 5.1 页面布局
- 左侧：Badge 列表（可拖拽排序）
- 右侧：Badge 详情编辑区

### 5.2 Badge 列表
- 显示 badge 图片缩略图
- 显示 badge 名称和状态（已解锁/未解锁）
- 支持搜索和筛选

### 5.3 编辑区
- 表单编辑元数据
- 图片预览
- 排序控制

## 6. 技术实现

### 6.1 路由结构
```
/config/badge-admin          # 管理页面
/config/badge-admin/api/*    # API 端点
```

### 6.2 文件结构
```
src/kid_app/routes/badge_admin.py    # 路由 + API
src/kid_app/templates/config-badge-admin.html  # 模板
tests/test_badge_admin.py            # 测试
```

## 7. 验收标准

1. 可以编辑 badge 的 name、cond_text、description
2. 可以预览 badge 图片
3. 可以修改 achievements 页面的排序方式
4. 可以控制 badge 在 achievements 页面的显示
5. 所有操作需要 PIN 验证
6. 测试覆盖率 > 80%

## 8. 优先级

- P0: 元数据编辑
- P1: 排序管理
- P2: 图片上传（可选）
