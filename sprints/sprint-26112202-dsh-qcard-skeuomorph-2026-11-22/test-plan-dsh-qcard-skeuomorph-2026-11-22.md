---
type: sprint
sprint: "26112202"
doc: test-plan
date: 2026-11-22
---

# 测试计划

## 静态

| 用例 | 入口 | 期望 |
| --- | --- | --- |
| 内联脚本语法 | 13 个 `<script>` 抽段 `node --check` | 全部 exit 0 |
| 结构契约 | `tests/test_practice_dsh.py` | 无 `.deck-card::before` 描边、无静态 `preserve-3d`、`.qc-shell` 有 `border: 1px`、宿主 Q 无圆角 |

## 接口

| 用例 | 入口 | 期望 |
| --- | --- | --- |
| 老师要求载荷 | `GET /practice-dsh` 页面 + `/config/api/assignments` | `sessions` 分组数、`tempo_bpm` 与 v3.54 一致 |
| 契约审计 | `/practice-dsh?audit=1` | 全绿，含 D4-2 dot 对比度 ≥ 3.0:1 |

## 像素（8765，Playwright）

| 场景 | 断言 |
| --- | --- |
| 440×956 / 1133×744，浅色 | 四角 45° 扫描检出 ΔY ≥ 20 的连续边线；直边与弧段同源 |
| 同上，深墨 | 四角检出 ΔY ≥ 18 |
| 翻页：按钮 / dot / 拖拽 >85px / 回弹 | 动画结束 320ms 后复测四角；底栏底边 ≤ sheet 底边 +1 |
| 三档 440 / 408 / 368 | Q 左右边与兄弟卡差 ≤ 1px；`__czQFeedAudit().ok === true` |
| 1133 横排 | Q 与 A/B/T 等高差 ≤ 1px，叠卡底缘不被裁 |

## 回归

- `pytest tests/ -q --ignore=tests/config_ui_fixes`，对比基线 1234 passed / 5 既有失败 / 8 skipped。
