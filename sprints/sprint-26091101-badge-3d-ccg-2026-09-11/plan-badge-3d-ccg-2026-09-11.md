---
id: 26091101-plan
type: plan
version: 1.0.0
date: 2026-09-11
status: 进行中
tags: [plan, dizical, badge, 3d, ccg]
---

# PLAN - 徽章集卡化 3D CCG 改造 (Sprint 26091101)

## 1. Goal 目标
将现有成就徽章体系全面改造为宝可梦集换式卡牌（CCG）风格的 3D 全息互动卡牌：
1. **两套 3D 方案并重同等精力实现**：
   - 方案一 (Simey Holo)：纯 CSS 全息光影卡牌（七彩流光箔、动态反光镜面、指针跟手倾斜、Spring 回弹）
   - 方案二 (EverettFish Parallax)：纯 CSS 3D 分层视差深度卡牌（背景层、原画主体层、全息金边框层、文字层 Z 轴真实悬浮与景深）
   - 制作统一的独立 Demo 把玩对比页 `/static/badge-ccg-demo.html`，支持单卡把玩、双卡并排、参数微调、FPS 监控、横竖屏自适应。
2. **全局拦截领取机制**：
   - 数据库解耦：`achieved`（满足条件）与 `claimed_at`（点击领取）双状态分离。
   - 练习保存后及准备页轻量拦截：若有未领徽章，全屏高光弹出 3D 卡牌供触屏倾斜把玩，点击“领取入库”触发金色粒子雨动效入库。

## 2. In-Scope 范围
- **数据层**：`src/migrate_add_claimed_at.py`（新增 `claimed_at TEXT DEFAULT NULL`，历史数据初始化，部分索引 `idx_achievement_stats_unclaimed`）。
- **API 层**：`GET /api/badge/unclaimed`，`POST /api/badge/claim`（幂等处理，落 `practice_audit_log`）。
- **前端 3D 渲染器（双方案）**：
  - 方案一：纯 CSS3 Transform + Blend Mode 全息箔与反光
  - 方案二：纯 CSS3 `preserve-3d` 分层空间视差
  - iPad mini 触控隔离：`touch-action: none`，倾斜限制 ±15°，手势松开弹簧阻尼回正
- **Demo 把玩页面**：`/static/badge-ccg-demo.html`，供 dad 在 iPad 实机把玩评测。
- **全局拦截弹窗重构**：接入 `_sidebar.html`，左右双栏横屏适配，GSAP 金色粒子雨动效。
- **测试覆盖**：`tests/test_badge_claim.py`。

## 3. Out-of-Scope 非目标
- 不动底层 `calc_all()` 计算逻辑与 threshold_map。
- 陀螺仪重力感应跟随（需权限与特定系统事件，放后续 Sprint 调研）。
- 成就殿堂 20+ 徽章墙保持静态（禁止全息上墙，保证 iPad 丝滑）。

## 4. 三方 Agent 分工表

| 角色 | 对应 Agent | 核心任务清单 |
| :--- | :--- | :--- |
| **Orchestrator** | **agy (我)** | 1. 架构设计与 Sprint 规划推进，文档双写与 MD5 校验<br>2. Dizicute 视觉规范把控（珊瑚红、深蓝灰、暖白、珐琅金边）<br>3. 全局拦截器集成与任务统筹、验收汇报 |
| **Worker 1 (后端/工程)** | **minimax** (`w19:p2`) | 1. 编写数据库迁移脚本 `src/migrate_add_claimed_at.py`<br>2. 实现后端 API (`GET /api/badge/unclaimed`, `POST /api/badge/claim`)<br>3. 提取准备标杆徽章素材与切片数据（如 `assign_pal`）<br>4. 编写自动化测试 `tests/test_badge_claim.py` |
| **Worker 2 (前端/动效)** | **grok** (`w19:p3`) | 1. 方案一 (pokemon-cards-css) 纯 CSS 全息光影卡牌开发<br>2. 方案二 (holo-card-studio 理念) 纯 CSS 3D 分层视差深度卡牌开发<br>3. 制作 `/static/badge-ccg-demo.html` 独立把玩对比页<br>4. 全局拦截弹窗重构、横屏 744px 适配与 GSAP 粒子动效 |

## 5. 交付路线 (Phases)
- **Step 1**: 数据库迁移与 API 接口开发（minimax）+ 标杆徽章素材切片准备（minimax）
- **Step 2**: 方案一与方案二 3D 渲染器与 Demo 把玩对比页开发（grok）
- **Step 3**: 全局拦截弹窗组件接入 `_sidebar.html` + 粒子礼花领取动效（grok + agy）
- **Step 4**: 测试套件运行 + 本地与 iPad 服务验证 + Closeout（agy）
