---
id: 26092004-tech-spec
type: tech-spec
version: 0.0.1-stub
date: 2026-09-20
status: 待实现后回填（sprint open 不做假回填）
sprint: 26092004
summary: "practice UI 重构技术契约占位 — token 分层 / 模块边界 / 移植路径 / 数据字段变更"
tags: [sprint, dizical, practice, tech-spec]
source: ai-agent
---

# tech-spec — practice 页 UI 重构（stub，待回填）

> 本文件在 sprint open 时是占位；**卡片规范与第一批模块 demo 定稿后回填**，不假装 sprint open 就写好了。

## 待回填清单

1. **token 分层契约**
   - 基础色（dizicute 6 色）→ tint / 透明度阶梯 → 语义 token（surface / border / text-primary / text-muted / accent / state-selected / state-disabled）
   - "可换配色主题"的落法：CSS 变量在 `:root` 一层覆盖，主题 = 一组 token 值；列出主题清单与覆盖方式
   - 现状基线：整页 107 个唯一 hex、CSS 变量只有 5 个 → 收敛目标与验收 grep 口径
2. **模块边界**
   - 每个模块的 DOM 根 + class 前缀 + 状态类命名（含孩子/家长视图的隐藏规则）
   - 卡片规范与模块的关系（模块只引用 token + 基础卡片类，不各自写边框阴影）
3. **移植路径**
   - 巨石 `practice.html`（3706 行：CSS 1015 / HTML 242 / JS 2376）如何分步替换，哪一步抽 `practice.css` / `practice.js`
   - 后端 `app.py` 的 `items_html` 拼接（L2591-2712，含英文硬编码 L2713）迁移为前端渲染的时机
4. **数据字段变更（老师要求 metronome 结构化）**
   - `section` / `beat_unit` / `bpm_min`（选填）/ `bpm_max`（必填）/ `notes`
   - 兼容读取：`requirement || requirements`（两键按时间分段、语义相同，从不混用）
   - 录入端校验：`beat_unit` 必选（音符漏写拦截）
   - 迁移与回填策略（老数据怎么映射）
5. **无障碍契约**
   - 触控目标 ≥44px（当前 ± 步进 38×32）、焦点环、放开 `user-scalable=no`、对比度（primary 白字 2.78 的处理）
6. **回归契约**
   - `tests/test_practice_timer_frontend.py` 全绿；打卡链路逐字不变；新增前端契约测试清单
