---
id: 26091101
type: test-report
version: 1.1.0
date: 2026-09-11
sprint: 26091101
status: PASSED
pass_rate: 100%
tags: [sprint, closeout, badge, 3d, ccg]
---

# Sprint 26091101 Closeout — 徽章集卡化 3D CCG

## 验资截图

方案一正面（V 级镭射 + 原画悬浮）：

![mac-holo](/Users/mt16/dev/dizical/docs/screenshots/sprint-26091101/mac-holo.png)

方案一卡背（笛韵印章）：

![mac-holo-flip](/Users/mt16/dev/dizical/docs/screenshots/sprint-26091101/mac-holo-flip.png)

方案二微视差（主体约 54%，封装在卡框内）：

![mac-px](/Users/mt16/dev/dizical/docs/screenshots/sprint-26091101/mac-px.png)

拦截弹窗横屏左右栏：

![mac-modal](/Users/mt16/dev/dizical/docs/screenshots/sprint-26091101/mac-modal.png)

## What shipped (3)

1. 方案一：深色底衬 Pokemon V 级对角彩虹箔 + glitter + 指针高光；轻点翻转卡背（掐丝金纹、竹笛暗纹、笛韵 / DIZICAL 印章）。原画 `translateZ(4px)` 浮在箔层上，脸不被 color-dodge 冲掉。
2. 方案二：`clip-path` 封装防穿模，主体约卡面 54%，Z 轴 0/2/5px 微视差，同一套 V 级箔。两套都是点翻面、拖倾斜（位移 &lt; 6px 当 tap）。
3. 领取闭环：`claimed_at` 迁移 + `GET /api/badge/unclaimed` / `POST /api/badge/claim`；`pytest tests/test_badge_claim.py` 10/10 PASS。Demo：`http://localhost:8765/static/badge-ccg-demo.html` 200。

## 1 thing we learned

箔层必须单独 `isolation`（`.ccg-foil-stack`），原画不要 `isolation` / `backface-visibility`。否则 `mix-blend-mode: color-dodge` 会把插画合成没，或微倾时闪没。3D 面用 `clip-path: inset(0 round 18px)` 代替 `overflow: hidden`，`translateZ` 才不会被压平。

## Next

Dad 在 iPad mini 打开 `http://10.0.0.14:8765/static/badge-ccg-demo.html`：方案一拖动看彩虹扫金边、轻点看卡背；方案二确认原画缩在框里不散架。两套都可留。
