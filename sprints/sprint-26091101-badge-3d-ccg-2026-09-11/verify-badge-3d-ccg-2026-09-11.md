---
id: 26091101
type: test-report
version: 1.0.0
date: 2026-09-11
sprint: 26091101
status: PASSED
pass_rate: 100%
tags: [sprint, closeout, badge, 3d, ccg]
---

# 🏆 Sprint 26091101 Closeout — 徽章集卡化 3D CCG 改造

## 📸 验资截图 (High-DPI Retina)

### 1. 双方案并排对比把玩 (Mac Retina 2880×1800)
![Mac Both Schemes](/Users/mt16/dev/dizical/docs/screenshots/sprint-26091101/mac-both.png)

### 2. 方案一：纯 CSS 全息光影 (iPad mini 竖屏 1488×2266)
![iPad Port Holo](/Users/mt16/dev/dizical/docs/screenshots/sprint-26091101/ipad-port-holo.png)

### 3. 方案二：3D 分层视差与翻转卡背 (Mac 2880×1800)
![Mac Parallax](/Users/mt16/dev/dizical/docs/screenshots/sprint-26091101/mac-px.png)

### 4. 全局拦截领取弹窗 (iPad mini 横屏 2266×1488 左右分栏)
![iPad Land Modal](/Users/mt16/dev/dizical/docs/screenshots/sprint-26091101/ipad-land-modal.png)

---

## 📦 What shipped (3 bullets)

1. **双 3D CCG 把玩方案并重交付与独立对比页**：
   - **方案一（全息光影）**：纯 CSS 实现彩虹全息镭射底纸、掐丝金边、镜面漫游反光、Spring 弹簧阻尼平滑回正，光影只打在卡纸金边，不遮蔽角色原画面部。
   - **方案二（分层 3D 视差）**：利用 `preserve-3d` 与多层 translateZ 悬浮视差，支持轻点翻转查看定制纯金卡背（“呦呦成就殿堂”专属印章与序列号）。
   - **独立对比页 `/static/badge-ccg-demo.html`**：支持单方案与并排对比模式切换，内置 FPS 性能监控仪表与倾角/全息强度实时调节滑块。

2. **数据库获得与领取解耦及完整后端 API**：
   - `achievement_stats` 扩充 `claimed_at` 字段并建立 `idx_achievement_stats_unclaimed` 部分索引，历史 25 行徽章安全平滑回填，防老用户上线被轰炸；`practice_audit_log` 增补 `detail` 字段。
   - 暴露 `GET /api/badge/unclaimed`（拉取待领徽章全量结构）与 `POST /api/badge/claim`（幂等领取回写 `claimed_at` 并落 `practice_audit_log` 审计）。
   - 自动化测试 `tests/test_badge_claim.py` 10/10 全部 PASS（覆盖幂等性、未达成拦截、审计防重等边界）。

3. **全局拦截领取弹窗与练笛动线闭环**：
   - 全局弹窗组件 `_badge_claim_modal.html` 接入 `_sidebar.html`，横屏自适应左右双栏排版，触控层添加 `touch-action: none` 与 `overscroll-behavior: contain` 防穿透。
   - 闭环拦截机制：练笛计时结束打卡与手动补录成功后自动检查未领徽章，点击“领取入库”触发金色粒子礼花爆发动效；保留“先去练笛”跳过入口，兼顾惊喜感与练笛专注度。

---

## 💡 What was learned / decided (1 bullet)

- **纯 CSS 空间变换全面超越 WebGL 重量级方案**：在 iPad mini WKWebView 环境下，利用原生 CSS3 `transform: rotateX/rotateY/translateZ` + CSS 变量跟随 + GSAP 弹簧回正，不仅实现媲美实体镭射收藏卡的把玩质感，还彻底规避了 Three.js/WebGL 的 GPU 上下文丢失、内存占用高与耗电卡顿问题，FPS 稳定在 60 帧满帧，且不引入任何大型第三方 runtime。

---

## 🎯 Next steps (1 bullet)

- **Dad iPad 真机眼验两套手感并拍板**：访问局域网 `http://10.0.0.14:8765/static/badge-ccg-demo.html` 或准备页实机拖拽把玩，决定方案一、方案二的最终保留策略（默认保留方案一全息作为通用弹窗，方案二视差翻转作为高阶/纪念卡牌模式）。
