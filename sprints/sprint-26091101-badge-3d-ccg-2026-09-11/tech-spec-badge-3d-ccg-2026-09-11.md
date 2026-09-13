---
id: 26091101-tech-spec
type: tech-spec
version: 1.0.0
date: 2026-09-11
status: 进行中
tags: [tech-spec, dizical, badge, 3d, ccg]
---

# TECH-SPEC - 徽章集卡化 3D CCG 改造技术规范

## 1. 架构总览

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                    前端页面全局拦截 (_sidebar.html)                     │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ fetch('/api/badge/unclaimed')
                                      ▼
                        后端路由 (badge_claim API)
                                      │
                 ┌────────────────────┴────────────────────┐
                 │ 检查 achievement_stats 表                │
                 │ (achieved='Y' AND claimed_at IS NULL)   │
                 └────────────────────┬────────────────────┘
                                      │ 返回未领徽章列表
                                      ▼
                      全局高光 3D CCG 弹窗 (Modal)
                 ┌─────────────────────────────────────────┐
                 │ 模式A: 方案一 (纯 CSS 全息光影卡牌)     │
                 │ 模式B: 方案二 (纯 CSS 3D 分层视差卡牌)  │
                 │ 交互: iPad Pointer/Touch 倾斜拖拽把玩   │
                 │ 操作: 点击 [ 领取入库 ]                 │
                 └────────────────────┬────────────────────┘
                                      │ POST('/api/badge/claim')
                                      ▼
                          更新 claimed_at = NOW()
                          写入 practice_audit_log
                          触发金色粒子飞入成就殿堂动效
```

## 2. 数据库变更规范

### 表：`achievement_stats`
```sql
-- 1. 新增字段
ALTER TABLE achievement_stats ADD COLUMN claimed_at TEXT DEFAULT NULL;

-- 2. 历史既得数据平滑迁移 (将既有 achieved='Y' 标记为已领，避免上线弹窗轰炸)
UPDATE achievement_stats 
SET claimed_at = achieved_at 
WHERE achieved = 'Y' AND claimed_at IS NULL AND achieved_at IS NOT NULL;

-- 3. 创建未领取部分索引
CREATE INDEX IF NOT EXISTS idx_achievement_stats_unclaimed 
ON achievement_stats(achievement_id) 
WHERE achieved = 'Y' AND claimed_at IS NULL;
```

## 3. 后端 API 规范

### 3.1 `GET /api/badge/unclaimed`
- **语义**：查询当前未领取的徽章列表。
- **返回结构**：
```json
{
  "unclaimed_count": 1,
  "badges": [
    {
      "id": "assign_pal",
      "name": "批改小帮手",
      "tag": "突破",
      "category": "milestone",
      "image_url": "/static/badges/assign_pal.png",
      "cond_text": "协助完成课后批改",
      "zh_story": "细心批改，温故知新。",
      "achieved_at": "2026-06-16 07:57:17",
      "theme_color": "#FF6B6B"
    }
  ]
}
```

### 3.2 `POST /api/badge/claim`
- **入参**：`{ "badge_id": "assign_pal" }`
- **SQL 幂等执行**：
```sql
UPDATE achievement_stats 
SET claimed_at = datetime('now', 'localtime') 
WHERE achievement_id = ? AND achieved = 'Y' AND claimed_at IS NULL;
```
- **返回**：`{ "status": "ok", "badge_id": "assign_pal", "claimed_at": "..." }`。若行数为 0 返回 `{ "status": "ok", "already_claimed": true }`。
- **审计记录**：向 `practice_audit_log` 插入 `channel='web', method='badge_claim', detail=badge_id`。

## 4. 3D 卡牌渲染引擎规范（双方案并重）

### 4.1 方案一：纯 CSS 全息光影 (Simey Holo)
- **DOM 结构**：
  ```html
  <div class="card-holo-container">
    <div class="card-holo-rotator">
      <div class="card-holo-face">
        <div class="card-holo-art" style="background-image:url(...)"></div>
        <div class="card-holo-shine"></div>
        <div class="card-holo-glare"></div>
      </div>
    </div>
  </div>
  ```
- **核心变量与着色**：
  - `--pointer-x`, `--pointer-y`, `--rotate-x`, `--rotate-y`。
  - `.card-holo-shine`：`background: radial-gradient(...)` + `mix-blend-mode: color-dodge` 全息彩虹流光。
  - `.card-holo-glare`：`radial-gradient(...)` + `mix-blend-mode: overlay` 镜面反光光斑。
  - **关键红线**：流光打在卡框和底衬，角色主体避免高强度冲色。

### 4.2 方案二：纯 CSS 3D 分层视差 (EverettFish Parallax)
- **DOM 结构**：
  ```html
  <div class="card-parallax-container">
    <div class="card-parallax-box">
      <div class="layer layer-bg" style="transform: translateZ(0px)"></div>
      <div class="layer layer-holo" style="transform: translateZ(16px)"></div>
      <div class="layer layer-subject" style="transform: translateZ(32px)"><img src="..." /></div>
      <div class="layer layer-frame" style="transform: translateZ(48px)"></div>
      <div class="layer layer-text" style="transform: translateZ(60px)"><h3>...</h3></div>
    </div>
  </div>
  ```
- **核心技术**：`transform-style: preserve-3d; perspective: 1000px;`，手指倾斜时各层产生真实的空间视差错落感。

### 4.3 触控与性能硬规范 (iPad mini & Mac)
- `touch-action: none;` 在卡面上，弹窗 `overscroll-behavior: contain;`。
- 倾斜幅度限制：最大 ±15°。
- 回正动画：使用 `gsap.to(vars, { ease: 'power3.out', duration: 0.6 })` 平滑归零。
