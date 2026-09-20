---
id: 26091901
type: prd
version: 0.1.0-draft
date: 2026-09-19
status: agy 方案占位 — 待 agy 反问 + 出方案后回填
project: dizical
sprint: sprint-26091901-timer-ruler-drag
summary: "practice 页计时器选择态 — iPad 端非红针位置按压拖动后无视觉跟随；改为整段尺子范围内可拖动，红针按手指滑动距离 + 方向做动画增减时长"
tags: [dizical, practice, timer, ruler, drag, ipad, sprint-26091901]
---

# PRD · 计时器刻度尺 iPad 拖动时长重做

## 1. 背景与触发 (dad 实测反馈)

2026-09-18 sprint 26091801 已上生产 (Deploy #131)。dad 9-19 在 iPad 上打开 practice 页验证:

> 手屏幕按在非红色刻度位置移动时，没有动画跟随。

dad 期望:
> 这块的交互动效应该是不论手点击哪个区域 (在刻度尺范围内) 都需要能够左右拖动，并且刻度尺的红色指针不是响应直接出现在手点击位置，而是跟随手的滑动幅度与方向进行对应的增减时间，并且有动画效果。

→ 现有 demo + 生产行为: 在红针落点附近点击/拖动红针本身 (drag handle) 时有跟手效果，但离开红针、按在尺子其它位置 (空白刻度区域) 时**没有视觉跟随**。dad 希望整个尺子范围内都可拖动 + 红针按手指位移增量增减 + 缓动动画。

## 2. 范围

| # | 项 | 改/不改 |
|---|----|--------|
| 1 | 选择态 (timerPickerCard 选择时长) | 改 |
| 2 | 运行态 (正计时中) | 不改 (sprint 26091801 已锁控件) |
| 3 | 暂停态 | 不改 |
| 4 | 补录 (extraSection) 选择器 | 不改 |
| 5 | 步进键 ±1 分钟 | 不改 (保留备选) |
| 6 | 数字滚轮 MM:SS 动效 | 不改 |

## 3. dad 已定约束

- **继承 sprint 26091801 所有硬约束** (动效层整段移植 + 只读状态桥、GSAP 判空、本地优先 CDN 兜底、#timerCard 宽度 `min(520px, 100%)`、暂停/运行守卫 `started`、29 条前端契约测试)
- **不引新依赖** (vanilla + GSAP)
- **不破坏打卡链路**: `/api/log`、`practice_at` (CST 无 Z)、behavior_log、速度/内容必填、开始按钮三条件、正常/提前结束弹窗、chime/confetti/CCG/今日记录全原样
- **跨设备一致性**: Mac + iPad mini 横屏 + iPhone 都要跟手
- **iPad 真机验证**: dad 自验 (Tailscale 入口，端口 8904 待起)

## 4. dad 已拍板开放项 (agy 反问后)

| # | 项 | 拍板 | 备注 |
|---|----|------|------|
| A | 跟手距离映射 | **1 tick = 30s (≈14px/min)** | 1:1 物理映射, 儿童手指滑多少红针走多少; 60 tick = 30 分钟 |
| B | 红针动画策略 | **拖拽期 scaleY(1.2) 微高亮 + 松手回弹** | 加 .is-dragging 类, GSAP 180ms 落点 + 220ms scaleY 回弹 |
| C | 边界 | **严格钳位 1~30 分钟** | 永不 0 分钟; 与 `finalMins >= 1` + 开始按钮守卫兼容 |
| D | 触摸 vs 鼠标 | **Touch + Mouse 统一为整段按下相对拖拽** | 全部输入走 `pointerdown/move/up` + `setPointerCapture` + `touch-action:none` |

→ agy 已在 `/tmp/sprint-26091901-agy-plan.md` 出初版方案 (80 行), 待 dad 拍板后 agy 落最终方案进 `/tmp/sprint-26091901-agy-plan.md` 的 §"已确认决策"段

## 5. 必读现状文件

| 文件 | 重点读 |
|------|------|
| `docs/demos/timer-counter-v3.1-demo-2026-09-18.html` | 选择态完整动效 + 拖动红针的现有交互 (drag handle) |
| `src/kid_app/templates/practice.html` | 生产页 picker DOM 接入点 + 状态桥 S 的接入层 |
| `src/kid_app/static/js/` (timer 模块) | 拖动红针逻辑、状态桥 (getter/setter)、started 守卫 |
| `sprints/sprint-26091801-practice-timer-integration-2026-09-18/` | 整段移植 SOP + 9 个函数命名 + 视觉层/逻辑层切分 |

## 6. agy 交付要求

**输出文件**: `/tmp/sprint-26091901-agy-plan.md`

**必含**:
1. 现状代码路径定位 (file:line + 注释)
2. 拖动失败的根因 (按现有事件绑定 + 边界检测逻辑推断)
3. 4 个待定项 (A/B/C/D) 的最终推荐方案 + 备选 + 理由 (每个 ≤5 行)
4. 改动范围 (file:line 级清单)
5. 验证口径 (Playwright/真机 + 至少 1 条反向断言)
6. 是否需要多轮 clarify (如需要，列在文件末尾 "待 dad 拍" 段)

**约束**:
- read-only (不动任何产品文件)
- 不动 `.gitignore`/隐私/agent 配置
- 写 `/tmp/` 不写仓内
- 报告只回一行路径 + 一句总结，方案全文在 `/tmp/...md`

## 7. 暂列 sprint 7 步 (agy 出方案 + dad 拍后再调整)

```
□ 1. 主仓 PLAN (本 PRD + tech-spec)
□ 2. worktree 实装 + race fix + pytest 全过
□ 3. PR → warden audit → fix → re-audit → merge
□ 4. CloudRun deploy + curl 验线上
□ 5. dad iPad 真机自验
□ 6. 主仓收尾 (STATUS / vibe-coding-log / handoff)
□ 7. Obsidian 双写 (vault + 主仓 4 文件 md5 一致)
```