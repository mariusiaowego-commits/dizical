---
type: sprint
sprint: "26112201"
doc: plan
date: 2026-11-22
---

# 实施计划

1. `src/practice.py`：session 解析/序列化/命名；BPM 提取先认 `♩/♪/♬=nn`，否则取最后一个合法数字。
2. `src/kid_app/routes/config.py`：`content-options` 接受 `sessions` 并校验（≤20、名称 ≤50、BPM 40–200、要求 ≤200）；`assignments` / `by-item` 输出 `sessions`；`_format_assignment_item` 透传并聚合老字段。
3. `src/kid_app/app.py`：`/api/items` 输出 `sessions`。
4. `practice-dsh.html`：
   - 速度联动 `resolveSessionTempo/applySessionTempo/pushTempoToFrames`，名称比对统一经 `cleanSessionText`。
   - Q 卡删 `is-hero`，按环节分组（结构化 requirement → 名称归属 → 编号清单），卡内底栏，统一翻页 `navTo`。
   - 角描边改 `::before` 全周 1px；Q iframe 去掉宿主 24px 圆角。
   - T 卡改原生 DOM（无 iframe），数据从抽屉真节点反读；窄档独立卡。
5. `config-practice.html`：环节行编辑器（名称/BPM/音符/要求 + 增删 + 保存）。
6. `config-practice-log.html`：老师要求行的「练习环节」区，选科目自动带出，草稿与编辑态透传 sessions。
7. 版本 `v3.54`；补 pytest 与 DESIGN.md。
8. 本地 Playwright 多视口验收 + PR + 独立 audit。

## 不做

- 不改数据库 schema（`content_options` 已是 TEXT；`sessions` 存在既有 JSON 结构内）。
- 不迁移历史自由文本要求为环节（只在无可归属时退回编号清单）。
- 不改小程序端读接口逻辑（靠聚合老字段兼容）。
