---
type: sprint
sprint: "26112201"
doc: test-plan
date: 2026-11-22
---

# 测试计划

## 后端

| 用例 | 入口 | 期望 |
| --- | --- | --- |
| 结构化/历史文本解析 | `parse_practice_sessions` | JSON 与逗号/换行都返回统一结构 |
| BPM 提取优先级 | `extract_session_bpm` | `80乐段 ♪=90`→90；`中板70`→70；`低音3、4`→None |
| content-options 落库回读 | `PUT/GET /config/api/practice/items` | sessions 一致，options 为名称列表 |
| 非法输入 | 同上 | BPM 越界/名称超长 400 |
| 老师要求透传 | `POST /config/api/assignments` | 响应 sessions 保留；metronome 聚合 `♩=60 / ♪=98` |

## 前端（本地 8904 + Playwright）

- DSH 载荷：默认 / 选 `正常长音练习` / 选 `吹高音“6”`（原始名）/ 选 `80乐段 ♪=98`，断言 `tempo_bpm/tempo_note/content`。
- 多视口 1133×744、744×1133、440×956：A/B/Q/T 卡高、footer 在卡内、`sessions` 分组数、`is-hero=0`、无内部溢出。
- 深墨皮肤：`::before` 描边色与角部像素连续性。
- 翻页：按钮、指示点、拖拽三条路径，90ms 中间帧有 transform/opacity 变化。
- 配置页：`/config/practice` 环节行数量与值；`/config/practice-log` 选科目自动带出 3 行。

## 回归

- `tests/` 全量（忽略缺 `bs4` 的 `tests/config_ui_fixes`），与 baseline 失败列表比对。
