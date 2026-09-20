---
id: 26091901
type: sprint
version: 1.0.0
start_date: 2026-09-19
end_date: 2026-09-19
status: 已完成
priority: 高
summary: "practice 页计时器选择态 — iPad ruler 自定义 Pointer Events 相对拖拽 + Touch+Mouse 统一 + Touch-action:manipulation 消双击 zoom + e2e 仓内化首例"
tags: [sprint, dizical, practice, timer, ruler, drag, ipad, touch-action, e2e, sprint-26091901]
---

# Sprint 26091901 · practice 计时器 ruler 自定义 Pointer Events 拖动时长

## 1. 背景与触发

sprint 26091801 (PR #338 squash → main `69a81c1`; closeout #339 → main `6c7fd1c`; Deploy #131) 已上线生产. dad 2026-09-19 在 iPad 真机验收时发现:

> 手屏幕按在非红色刻度位置移动时, 没有动画跟随. 这块的交互动效应该是: 不论手点击哪个区域 (在刻度尺范围内) 都需要能够左右拖动, 并且刻度尺的红色指针不是响应直接出现在手点击位置, 而是跟随手的滑动幅度与方向进行对应的增减时间, 并且有动画效果.

→ 现有 `<input type="range">` + 原生 `input` 事件 = iPad Safari 跳到点击位置 (jump-to-position), 不响应"滑动幅度+方向增量". 拍板 sprint 26091901 修复.

## 2. 团队分工

| 角色 | pane | 承担 |
|------|------|------|
| orchestrator | w10:p1 dizical-hermes | 计划 + 派活 + 实装 + 测试 + 收尾 |
| 决策&写作 | w10:p9 dizical-agy | 方案设计 (4 项决策反问) + 自审 (P1 dragging 容器类) + iPad Safari 双击 zoom follow-up |
| 独立审计 | w10:pA dizical-warden | round-1 audit (VERDICT=MERGE + P1-2 报) + round-2 复审 (PASS) |

## 3. 交付物

| # | 交付物 | 落点 / 证据 |
|---|--------|------------|
| 1 | 自定义 Pointer Events ruler 拖动 (4 项决策合入) | `src/kid_app/templates/practice.html:3122-3177` |
| 2 | P1 修法: dragging 容器挂类 (`#timerCard.is-dragging .tick.cur`) | `src/kid_app/templates/practice.html:217-219, 3142-3143, 3158-3159` |
| 3 | follow-up: iPad Safari 双击 zoom 修复 (CSS touch-action:manipulation) | `src/kid_app/templates/practice.html:137, 191-192` |
| 4 | 静态契约 42/42 + 全项目 855 passed / 0 failed | `tests/test_practice_timer_frontend.py` |
| 5 | e2e 仓内化 3 脚本 + README (sprint 内首例) | `scripts/e2e_sprint_26091901/` |
| 6 | 独立审计 2 轮 (round-1 MERGE + round-2 PASS) | `/tmp/sprint-26091901-warden-review.md` + `/tmp/sprint-26091901-warden-round2.md` |
| 7 | PR #340 merge → main `2aee3fb` | https://github.com/mariusiaowego-commits/dizical/pull/340 |
| 8 | CloudRun Deploy #132 (进行中, 待 dad 重启 MCP cloudbase 设备码) | `dizical-prod` 服务 |

## 4. 状态

- [x] Phase 1 PLAN + 拍板 (PRD + tech-spec + Obsidian 双写)
- [x] Phase 2 实现 + 单元测试 (42 契约 + 855 全项目)
- [x] Phase 2.5 agy 决策反问 (4 项决策 + P1 修法)
- [x] Phase 2.6 follow-up (iPad Safari 双击 zoom + touch-action)
- [x] Phase 3 warden audit round-1 (VERDICT=MERGE + P1-2 报)
- [x] Phase 3.5 P1-2 修 + commit `079d1e0`
- [x] Phase 3.7 warden audit round-2 (PASS 确认, 3/3 BITE 验证)
- [x] Phase 4 PR #340 squash merge → main `2aee3fb`
- [ ] **Phase 5 CloudRun Deploy #132** (⚠️ 阻塞: MCP cloudbase auth token 过期, 需 dad 重启设备码登录)
- [ ] Phase 6 收尾 6 项 (PRD/tech-spec 已写; verify/decision-log/STATUS/tag/Obsidian 待补)

## 5. Sprint 回顾

| 项 | 值 |
|---|----|
| 预计 vs 实际 | 半天: 实装 + 测试 + agy 反问 + follow-up + 双 audit + merge. Deploy 阶段因 MCP auth 阻塞需 dad 介入 |
| 学到 | ① **iPad 实机验才是最终关** — playwright iPad UA 不完全等价 iPad Safari 真机 (双击手势语义有差). ② **测试假阴性会骗人** — 注释残留子串 + 老代码残留会让契约 8 条注水只咬 5 条; 必须用块内切片 + sprint marker 限定. ③ **brace 错位漏检** — sprint 26091801 closeout 没跑 node --check, 本次实装 onDragEnd handler 多一个 `}` 被 iPad 真机发现 (无刻度尺), 加 node --check 静态断言锁住. ④ **MCP auth 过期有 fallback** — REST API + gh auth token 查 PR/merge, 但 CloudRun deploy 仍需 dad 设备码 |
| 风险点 | 老 extraSection dial knob SVG path warning (sprint 26091604 已知, 跟本次无关). `is_user_locked` 时区不对称 bug (独立 hotfix 候选, 等 dad 拍) |

## 6. commit 链 (squash merge)

```
PR #340 squash merge → 2aee3fb
  内含:
  - cd56a45 fix(practice): iPad ruler drag — 自定义 Pointer Events 相对拖拽 + iPad Safari 双击 zoom 修复
  - 079d1e0 test(timer): 强化 3 条契约消除注释/老代码子串残留导致的假阴性
base: 6c7fd1c (sprint 26091801 closeout)
```

## 7. 改动文件 (6 files / +553 / -6)

```
src/kid_app/templates/practice.html            (+66 / -6)
tests/test_practice_timer_frontend.py          (+152 / -0, 11 条新契约)
scripts/e2e_sprint_26091901/README.md           (+107)
scripts/e2e_sprint_26091901/e2e_dom_state.py    (+98)
scripts/e2e_sprint_26091901/e2e_touch_action.py (+57)
scripts/e2e_sprint_26091901/e2e_interactions.py (+157)
```

## 8. 不在范围

- `is_user_locked` 时区不对称 bug — 独立 hotfix 候选, 不在本 sprint
- 老 extraSection dial knob SVG warning — sprint 26091604 issue, 不在本次
- 计时器 UI 整体演进 — 后续 sprint, dad 拍板 `fix/timer-ruler-drag-260919` 分支长期保留
- practice 模块卡片重构 (inspora.design 学习) — 新分支 `refactor/practice-module-cards`, 下次 sprint 重点