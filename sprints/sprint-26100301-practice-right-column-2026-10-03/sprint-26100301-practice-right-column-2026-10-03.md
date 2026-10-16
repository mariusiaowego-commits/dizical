---
id: 26100301
type: sprint
version: 0.1.0-stub
date: 2026-10-03
status: 进行中（需求已收，等 demo 拍板）
summary: "practice 页右栏重构 — 拟物仪表盘卡（可换皮肤）+ 老师要求卡改 pop-out + 今日练习记录重做"
tags: [sprint, dizical, practice, ui-refactor, right-column]
source: ai-agent
---

# Sprint 26100301 — practice 页右栏重构

> 需求来源：dad 2026-10-03 brief（编号 `2610011327`），全文见 `plan-practice-right-column-26100301.md` §0。
> 承接 sprint 26092004（左栏已定稿，**本期不动左栏**；右栏定型后左栏可能还要改）。

## 范围

**动（右栏 + 弹出的老师要求卡）**
1. **仪表盘卡**（拟物金属银外框、可替换皮肤的第一个默认样式）
   - 顶部超圆角深色 top panel：科目图 + 科目名 + 练习计时 readout + ruler 进度条 + 老师要求滚动正文 + bpm 显示 + 今日累计
   - 银色控制面板区：大 rotary knob（节拍器 BPM）+ ± 时长步进（左右对调，且镜像到 top panel 进度条两侧）
   - 下方左中右：扬声孔（随节奏震动动效）/ 操作按钮组 / 谱架模式入口按钮
2. **老师要求卡** → 改为 pop-out（入口移到 pk-top），弹窗重做，含历史要求
3. **今日练习记录** → 展开态重做（3 个 heroic 指标 + 科目/session 双层列表 + 渐进模糊动效）

**不动**
- 左栏（票卡 + 科目信息卡）：已验收的 demo 定稿，本期不改
- 打卡链路契约（`POST /api/log` 入参、`practice_at` CST 语义、校验规则）
- 计时契约（1–30 分钟 / 每分 2 格 / 红针）与 `tests/test_practice_timer_frontend.py` 断言

## 分期

| 期 | 内容 | 前置 |
|---|---|---|
| P1 | 仪表盘卡默认皮肤 + 今日练习记录重做 + 老师要求 pop-out 骨架 | demo 拍板 |
| P2 | 节拍器旋钮 + 拍声（含市面实现调研） | 调研 + 拍板 |
| P3 | 谱架模式（谱架卡片 + 仪表卡缩窄态） | **单独 plan + 单独 demo，dad 定后再开工；本期只出入口按钮 UI** |

## 交付物

- demo（可点变体对照页，全部落 `docs/demos/practice-right-column-261003/`）
- 生产移植（`src/kid_app/templates/practice.html` 等）
- 每个 demo 由 warden 独立验收，再交 dad 拍板

## 状态

- [x] dad 需求已收（含 5 张参考图 + 节拍器 design guide 逐帧读完）
- [x] dad 四条拍板（2026-10-03）：换肤粒度=仅配色 token ／ 先 demo 后移植（本期不碰生产页面）／ 相比昨日无数据显 `--` ／ D4 参考改用 dizical badge 页 three.js + 交互由我方出 2–3 变体
- [x] **token 契约统一 + 硬编码 hex 收编**（4 个 demo 一份契约，`docs/demos/practice-right-column-261003/token-spec.md`，含负控验证）
- [ ] 生产右栏 DOM/JS/数据契约盘点（grok 已交，见 plan §1b）
- [ ] 节拍器实现路线调研（agy 已交，路线 A 已拍板）
- [x] 节拍器拍声路线拍板（路线 A 纯 Web Audio，零依赖）
- [ ] D1–D6 demo 逐个定稿
- [ ] 生产移植 + 契约测试不回退
- [ ] 真机验收（iPad 横屏 1133×744 为主视口）
