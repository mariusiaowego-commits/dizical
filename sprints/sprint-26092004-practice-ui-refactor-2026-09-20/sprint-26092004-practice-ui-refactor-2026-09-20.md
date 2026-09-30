---
id: 26092004
type: sprint
version: 0.1.0-stub
date: 2026-09-20
status: 进行中（澄清已完成，等第一批模块 demo）
summary: "practice 页整体 UI 风格重构 — 可配置/模块化/可换主题的练习 dashboard；模块逐个过 demo"
tags: [sprint, dizical, practice, ui-refactor]
source: ai-agent
---

# Sprint 26092004 — practice 页整体 UI 重构（占位 stub）

> 本文件是 **stub**，随第一批模块 demo 定稿逐步回填为正式 sprint 主档。
> 决策来源（先读这两份，不要另起一套）：
> - `docs/practice页重构-决策记录-260920.md`（dad 2026-09-20 澄清结果 → 执行口径）
> - `docs/practice页重构-agy设计分析-260920.md`（agy 设计分析 + Hermes 复核）
> 原始需求：`MRD-practice页重构.md`（Obsidian `project-dizical/PRDs/`）

## 范围

**动**
- practice 页全部板块的 UI 风格 / 卡片元素 / 模块排布 / 动线：选科目、老师要求、速度 + 本次内容、刻度尺计时器卡片化、结束与打卡、今日练习记录、顶部状态与页脚
- 卡片体系做成**可配置、模块化、可换配色主题**（token 分层 + 模块边界）
- 无障碍欠账（触控 ≥44px、焦点环、放开缩放、对比度）
- 补录模块删除（历史使用 4.9%，最近一次 2026-06-13）

**不动**
- 打卡链路契约：`POST /api/log` 入参、`practice_at` CST 语义、速度/内容必填校验（改为预选默认 + 给原因，不放宽后端）
- 刻度尺核心联动（1-30 分钟 / 每分 2 格 / 红针）与 `tests/test_practice_timer_frontend.py` 全部断言
- 练习页单一路由 `/practice`；盲盒与徽章 enamel pin 资产
- 后端 API 形状（除老师要求 metronome 结构化字段，见决策记录 §2）

## 主线（按 dad 拍板的模块顺序，逐个出 demo 过审）

1. 卡片基础规范 + 状态矩阵
2. 选科目（归档可找、默认序 = 老师要求 → 最近练过 → 其他）
3. 老师要求（常驻 + 练习态大字排版；175 字长文与多速度段极限态）
4. 速度 + 本次内容（三档 ♩ / ♪ / ♬；9 标签极限态）
5. 刻度尺计时器卡片化（复用生产真件）
6. 结束与打卡（正常 / 提前结束 / 失败重试）
7. 今日练习记录（折叠 / modal 两态）
8. 顶部状态 + 页脚 + 主视觉（2D：刻度尺时钟 + 节拍器视觉）
9. 3D 沉浸式主视觉 → **Phase 2 占位**（见 plan §3D 计划）

## 关键约束

- 主视口 = **iPad 横屏 1133×744**，一屏闭环（不滚动完成：选科目 → 看要求 → 定速度内容 → 开始）；竖屏 744×1133 与 iPhone 440×956 为次视口
- 孩子视图 / 家长视图分离：孩子界面不含归档、编辑、删除
- 节拍器本期只做视觉；发声独立分支（dad 提供参考）
- 前端不交 minimax；模块化逐个过 demo；复杂问题可开 1-2 个 agy（Claude）pane 做深度分析

## 状态

- [x] dad 澄清 13 问 + 4 决策点（决策记录已落库）
- [x] 旧 260904 方案归档（`sprints/_archived-2026-09/`）
- [x] 第一批模块 demo（卡片基础规范 + 选科目）
- [x] **左栏定稿（2026-09-25）**: 练习票卡准备态/计时态 + 科目信息卡 + 顶栏 + session 选择器样式 —— `docs/demos/practice-ticket-v4-260920.html`（v4→v25，41 commit，未 push）；收拢态排版三方案对照页 `docs/demos/practice-runstate-rows-variants.html`（dad 选 Variant B）
- [x] **右栏首版（2026-09-25 晚，commit `ec24cb2`）**: 老师要求卡两态常驻（计时态 display=flex、正文 12.5px/行高 1.5、默认 2 条、展开全文层不停表）+ 仪表卡信息带（科目 20px/800 · session 胶囊 12.5px/700 · 速度 ♩=N 19px/800）+ 新增**今日记录抽屉**（顶栏 pill 两态可点、Esc/关闭钮、练习中不停表）
- [ ] **右栏视觉定稿（下个 session）**：等 dad 右栏参考图 → 逐项替换视觉层（新块样式已全部走变量，替换只改一处）；再补"计时结束回填今日累计"联动
- [x] 生产侧「练习页配置」模块（commit `532961a`，`/config/practice-page`，settings 键值存储无需 DDL，pytest 4 passed）
- [ ] 移植到生产 `practice.html` + 契约测试不回退（`tests/test_practice_timer_frontend.py` 29 条）
- [ ] 真机验收（iPad 横屏为主）—— 左栏已过，右栏首版待过（等参考图后再验一次）

## 左栏定稿摘要（2026-09-25 回填）

- **实测口径**: 十档视口零越界零页面滚动（1133×744 / 1024×768 doc 与 body 都 ≤ innerHeight）；PC 1728 票内空洞 209px→0；信息卡点阵方块宽高相等、相邻行列 −3~−3.5px；数字字形盒居中 0px；缺口几何 PC/iPad 0px 差
- **不许破的约束**: 真件 7 id 不改名 / 刻度尺动画交互不动 / 只 6 色 + alpha / 触控 ≥44px（`::after` 撑）/ 收拢以左边框为轴心且 prep=run 高度逐像素一致 / 蒙版 0.0875 且 `blur(`=0 / 计时态禁换科目 / `dizical` 全文 1 次
- **数据源**: 云库 CloudBase MySQL（MCP 只读）才是权威；本地 `data/dizi.db` 是旧快照（止于 2026-08-06）
- **详见**: `handoff-2026-09-25-practice-ui-left-col-closeout-right-col-next.md`
