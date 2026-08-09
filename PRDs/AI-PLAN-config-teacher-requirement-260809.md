---
date: "2026-08-09"
doc_type:
  - plan
tags:
  - config
  - teacher-requirement
  - sprint
status: active
---

# AI-PLAN: config 老师要求录入优化 (260809)

> 主计划文件 — 接续 agent 第一入口。每次 sprint 完成后更新状态。
> 对应 PRD: `config配置-老师要求录入优化.md` (tqob Obsidian vault)
> 接续入口: `handoff-2026-08-09-config-teacher-requirement.md` (项目根目录)

## 已确认决策 (dad 拍板 2026-08-09)

| 决策项 | 结论 |
|--------|------|
| 整体方案 | A: 多 sprint 逐个完成 |
| 速度多档 | A1: 保留 `metronome` 字符串 + 新增 `metronome_segments` 数组 |
| segments 结构 | `[{ label: 自由文本, tempo: 字符串 }]`, label 不限 range, 覆盖时间分段/交替/situation 场景 |
| 单值 metronome 存法 | 斜杠拼接 (如 `♩=95/♩=100`), 老消费者可直接显示 |
| 上周预填策略 | B1: 录入日期前最近一次非空要求 + UI 标注来源日期 |
| 草稿范围 | D1: 仅"老师要求"Tab (不混入练习录入 Tab) |
| 接续机制 | AI-PLAN + handoff 双文件, 每 sprint 独立 PR |

## Sprint 分解与状态

| Sprint | 内容 | 状态 | 完成日期 |
|--------|------|------|----------|
| S0 | 现状验证: active 科目过滤 / 配图预览截图 / weekly_assignments 数据分布 / 预填解析链路 | 已完成 (部分) | 2026-08-09 |
| S1 | 需求5 (picker 只列 active) + 需求6 (配图预览) 收尾 | 已完成 + 已上线 (PR #244, CloudRun 076) | 2026-08-09 |
| S2 | 需求2 增强预填: API 改"日期前最近一次"语义 + 前端填 metronome + 标来源日期 | 已完成 + 已上线 (PR #244, CloudRun 076) | 2026-08-09 |
| S3 | 需求3 历史3次: 新 API `/api/assignments/by-item?item_id=X&limit=3` + 选中科目后展示(带复制) | 待开始 | - |
| S4 | 需求1 草稿缓存 + 刷新拦截: localStorage + beforeunload, 仅老师要求 Tab | 待开始 | - |
| S5 | 需求4 速度多档: metronome_segments 全链路 (录入表单分段控件 + 展示 + 预填防御) | 待开始 | - |

## 需求清单 (PRD 原文映射)

1. **草稿缓存 + 刷新拦截**: config 表单录入内容先缓存, 刷新前二次确认
2. **预填上周要求**: 优先把上次同科目要求预填 (B1: 日期前最近一次非空 + 标日期)
3. **历史 3 次展示**: 选中科目 → 展示该科目历史 3 次要求 (含速度), 可复制
4. **速度多档**: 一个科目一次要求可有多种速度 (A1 + segments label 方案)
5. **picker 只列 active**: 不列 archived 科目
6. **配图预览**: 上传后能预览

## 关键技术地图 (接续 agent 必读)

- **录入 UI**: `src/kid_app/templates/config-practice-log.html` (Tab 2 老师要求, 行 771-819 表单, 行 1276-1453 JS)
- **录入 API**: `src/kid_app/routes/config.py`
  - GET `/api/assignments/latest-requirements` (行 977): 预填用, 跨全部历史取最近一次, 有回退逻辑
  - GET `/api/assignments` (行 951): 历史列表, 支持 ?item= 过滤
  - POST `/api/assignments` (行 1008): 录入, formatted items 行 1033-1041
  - PUT `/api/assignments/{lesson_date}` (行 1067): 编辑全量替换
  - POST `/api/assignments/upload` (行 1154): 配图上传 (COS 或本地回落)
- **DB 层**: `src/database.py` save_weekly_assignment (行 681) / get_weekly_assignment_for_week (行 746); MySQL 版 `src/database_mysql.py` (行 404-462)
- **⚠️ 预填解析陷阱**: `src/database.py:1315` SQL `wi.metronome` 直读 + `split('=')` 解析 → S5 加防御 (取第一段或完整串)
- **metronome 全量消费者** (7处):
  1. config.py:1039,1089 (写入)
  2. database.py:1315 (预填解析, 高危)
  3. config-practice-log.html:1291,1462,1538,1650 (表单/历史/编辑/周览)
  4. cli.py:1504 (CLI 老师要求 TUI)
  5. cli.py:1627 (CLI 周报)
  6. practice_query.py:290 (CLI 练习查询 TUI)
  7. tests (test_cli_ux_review.py:269 等)
- **科目列表 API**: `/config/api/practice/items?include_archived=false` (前端 loadItems 已传 false, S1 需验证后端过滤)

## Sprint 详细计划

### S0: 现状验证 (0 代码改动)
- [ ] curl `/config/api/practice/items?include_archived=false` → 确认只返 active
- [ ] curl `/config/api/practice/items?include_archived=true` → 确认差异
- [ ] 浏览器打开 config-practice-log 老师要求 Tab → 上传配图 → 截图验证预览
- [ ] SQL 查 weekly_assignments: 总条数 / items JSON 里 metronome 字段分布 (单值/空/格式)
- [ ] 读 database.py:1315 上下文确认预填链路
- 产出: S0 报告写进 sprint 目录 + AI-PLAN 状态更新

### S1: picker active 过滤 + 配图预览 (0.5h, 低风险)
- 后端: 确认/修复 practice/items 的 include_archived 过滤
- 前端: picker 已传 false, 若后端已过滤则纯验证
- 配图: 上传预览已实现, 截图确认为准, 若 HEIC 转换/预览有 bug 则修

### S2: 预填增强 (1h, 中风险)
- API: latest-requirements 语义改为 "某日期前最近一次非空要求" (新增可选参数 anchor_date)
- 返回加 `lesson_date` 字段 (来源日期), 供 UI 标注
- 前端: 切换科目时填 requirements + metronome + 标注 `📌 上次 2026-08-01: ♩=95`
- 注意: 现有回退逻辑 (最新为空用更早) 保留

### S3: 历史 3 次 (1.5h, 中风险)
- 新 API: GET `/api/assignments/by-item?item_id=X&limit=3` → 最近 3 次含 lesson_date/metronome/requirements
- 前端: 选中科目后, 在该行下方展示 3 条历史 (label 显示日期 + 速度), 每条带"复制"按钮
- 复用 loadAssignments 渲染逻辑避免重复代码

### S4: 草稿缓存 (1.5h, 中风险)
- localStorage key: `dizical:assign-draft:v1:<lesson_date|auto>`
- 保存时机: input/change 事件防抖写入 (500ms)
- 恢复时机: init 时若 key 存在且有内容 → 填回 + 提示"已恢复草稿 2026-08-09 14:32"
- 刷新拦截: beforeunload 时若有未提交内容 → confirm 弹窗
- 提交成功后清除 key
- 范围: 仅老师要求 Tab 的 assignEntries/assignNotes/assignImages (URL)/stage 字段

### S5: 速度多档 (3h, 高风险, 单独 PR)
- 数据结构: items JSON 加 `metronome_segments: [{label, tempo}]`; `metronome` 存斜杠拼接
- 写入: POST/PUT 接受 metronome_segments, 组装 metronome 斜杠串
- 表单: 每个科目行加"分段速度"控件 (label + tempo 输入 + 添加/删除), 折叠在"＋ 添加分段"按钮下
- 展示: 历史列表/周览渲染 segments 为多行小胶囊; 无 segments 时回退单值
- ⚠️ database.py:1315 预填解析: metronome 含 `/` 时取第一段或完整串 (定: 取第一段, 因为练习页 tempo_bpm 是单值)
- 测试: 新增 segments 写入/读取单测 + 老数据兼容 (无 segments 字段)

## 验证标准 (每 sprint)
- 后端: pytest 相关测试全绿
- 前端: 浏览器实测 + 截图存档
- 每 sprint 独立 feature branch → PR → dad 确认后 merge
