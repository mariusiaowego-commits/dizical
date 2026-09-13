---
id: 26091201-tech-spec
type: tech-spec
version: 0.1.0
date: 2026-09-12
status: 等待 agy 方案
tags: [tech-spec, dizical, badge, ccg, theme]
---

# TECH-SPEC — 徽章 CCG v2

## 1. 现状基线 (v1, 分支 feat/sprint-26091101-badge-3d-ccg)

- 卡面文件：`src/kid_app/static/css/badge-ccg.css` (1164 行)、`src/kid_app/static/js/badge-ccg.js`
- DOM 由 `badge-ccg.js` 的 `cardHTML()` 生成；demo `src/kid_app/static/badge-ccg-demo.html`
- 布局变量集中在 `.ccg-stage`：`--art-l 5.4% / --art-t 9.9% / --art-h 51.1% / --bar-t 62.6% / --bar-h 4.2% / --plate-t 68.8% / --foot-b 3.2% / --plate-pad-t 4.2% / --plate-pad-b 4.2%`（v1.3.0-dev 起 `--plate-b` 废除：说明栏直伸到页脚底 `--foot-b`，页脚已并入说明栏内；v1.4.0-dev 起栏内下留白由 `--plate-pad-b` 控制，页脚不再顶死栏底）
- 箔层栈 (art-window 内)：stock → shine → glitter → security → spec → laser → glare → holo-head
- 背景配色硬编码：`--ccg-void: #16224a`、箔底 `#0e1a3e`、`--ccg-sunpillar` 12 段光谱

## 2. 待 agy 方案回填

- A 线：info-bar / plate 版式规范（尺寸/层级/字号/间距/配色 token）
- B 线：主题系统架构（token 分层 / 数据结构 / 主题选择 / 元数据接口 / DDL）

## 3. v1 已踩坑 (实现时必须遵守)

- 箔层 `background-position` 百分比必须 clamp 在 0~100%（指针出窗时 ±110% 会让渐变盒滑出图层 ⇒ 直角硬边"方框"）
- `.ccg-stage` 用 fr 不用百分比+gap（会溢出）
- 三端适配：Mac 1440 / iPad 竖 744 / iPad 横 1133
