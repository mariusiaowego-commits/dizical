---
type: sprint
sprint: "26112202"
doc: verify
date: 2026-11-22
---

# 验收记录

环境：8765（`dizical.kid-app` 注册端口），worktree `/Users/mt16/.codex/worktrees/1482/dizical` 代码，
Playwright Chromium + `deviceScaleFactor=2`，数据源云端 MySQL（默认科目 + `小看戏` 12 张卡）。

## 1. 静态

```
$ node --check × 26 个 <script> 段
failures: 0
```

## 2. 单测

```
$ pytest tests/test_practice_dsh*.py tests/test_practice_sessions*.py tests/test_practice_timer_frontend.py tests/test_config_practice_page.py
203 passed

$ pytest tests/ -q --ignore=tests/config_ui_fixes
5 failed, 1237 passed, 8 skipped
```

5 个失败与基线一致（`test_achievements_card_no`、`test_calc_seasonal_count`、`test_config_design` ×3），
本次新增 3 条结构契约（`.qc-shell` 实体边 / 宿主摘壳 / 2D 叠卡）全绿，计入 1237。

## 3. UI（Playwright，8765）

| 用例 | 结果 | 实测 |
|---|---|---|
| 440 档模块等宽左对齐 | PASS | A/Q/R `left=16, w=408` |
| 440 四角描边（浅色） | PASS | ΔY tl 52.5 / tr 52.5 / bl 39.7 / br 39.7 |
| 375 档（canvas `scale≈0.84`）四角 | PASS | ΔY 52.0 / 52.5 / 39.7 / 39.7 |
| 1133 档模块等高 | PASS | A/Q/R `top=78, bottom=822, h=744` |
| 1133 四角描边 | PASS | ΔY 52.5 / 52.5 / 40.1 / 39.7 |
| 深墨 1133 四角描边 | PASS | ΔY 38.2 / 37.7 / 49.0 / 48.6 |
| 翻页（下一张/上一张） | PASS | 2026-11-21 → 11-14 → 11-21 |
| 翻页中间帧有 transform | PASS | 90ms `matrix(0.9999,-0.0129,0.0129,0.9999,-27.4,0.7)` + `is-dragging` |
| 翻页后四角 | PASS | 与翻页前同值（52.5/52.5/39.7/39.7） |
| 底栏在纸面内 | PASS | `sheetBottom=394, footBottom=394` |
| `__czQFeedAudit` | PASS | `{F1:true, F2:true, F3:null(无便签), ok:true}` |
| dots 收拢 | PASS | 12 张卡只渲染 7 点 |

四角判据：沿 45° 从角点向内采样 20 步，基准取对角线末端的纸面中位数；
浅色要求 `max(基准−像素) ≥ 20`，深墨要求 `max(像素−基准) ≥ 18`。

## 4. 失败与跳过

| 项 | 状态 | 原因 |
|---|---|---|
| `runContractAudit` 的 `three viewports width must differ: 1133(330), 744(330), 440(330)` | **failed（历史项）** | 嵌入态 `html.cz-fill .req-card-chassis { width:100% }`，该断言只对独立打开有效。v3.54 主 checkout 同断言同样 330/330/330。 |
| `runContractAudit` D4-2 深墨未选点对比度 1.14:1 | **failed（历史项）** | 审计的 `getLum` 固定按浅底 (240,243,246) 混合，深墨半透明点必然算出低对比。v3.54 实测 1.23:1。浅色本次 3.33:1 通过。 |
| iPad Safari 真机四角 | **skipped** | 本机只能跑 Chromium；WebKit 的 `scale(k)` 重采样需 dad 在 iPad 上目视确认。 |
| 拖拽 >85px 抛飞后的四角 | **skipped** | 单卡数据下无可抛飞目标；按钮翻页已覆盖同一 `navTo` 路径。 |

## 5. 截图

- `/private/tmp/v-440-before.png`（440 浅色）
- `/private/tmp/v-375.png`（375 缩放档）
- `/private/tmp/v-1133.png` / `/private/tmp/v-1133-ink.png`（横排浅/深）
