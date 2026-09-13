---
id: 26091302
type: sprint
version: 0.1.0
start_date: 2026-09-13
end_date: —
status: 进行中
priority: 高
summary: "把已定稿的 CCG 卡面接进图鉴两页（我的成就 / 成就殿堂）：列表静态卡 + 详情弹窗 3D 交互卡 + locked 灰度。页面外壳不动。"
tags: [sprint, dizical, badge, ccg, wiring]
---

# SPRINT 26091302 — 图鉴接线（B6）

## 0. 来源

dad 2026-09-13 原话四问四答：

1. 「**config/badge 没问题，但是前端的卡片都设计好了吗？我现在 achievements 里面打开都还是原来的 modal**」
2. 「1 对 点开在 modal 里才展示 3d 的样式可以尽情交互」→ **列表静态 / 弹窗交互**
3. 「2 好」→ **locked 沿用纯前端 CSS 灰度**
4. 「3 好 可以先做 然后再看是否优化」→ 详情弹窗先沿用领取弹窗布局
5. 「4 页面外壳是哪里？我建议先只换卡和 modal」→ **只换卡 + 弹窗**

## 1. 现状（查证结论）

- CCG 卡面已定稿冻结（`static/demo-archive/v1.5.0/`），但**只接进了一个真实流程**：领取弹窗
  `templates/_badge_claim_modal.html`（被 `_sidebar.html:758` include，触发自
  `DizicalCCG.checkUnclaimed()`，见 `_sidebar.html:763` / `practice.html:2141,2230`）。
- `achievements.html`（961 行）grep `ccg` = **0 命中**；卡墙是老 `.b-card/.b-img-wrap/.b-img`（PNG），
  点开走 `openModal()`（:745）→ 老 `#modal-overlay/#modal-box/#modal-img`。
- `badges.html`（507 行）同为老结构（卡墙模板 `data-img="${esc(d.badge_url)}"` 在 :331，自带 `#modal-*`）。
- 两个 demo 页（`badge-ccg-demo.html` / `badge-ccg-compare.html`）只做演示，不是产品入口。

## 2. Goal（B6）

1. 图鉴两页卡墙改用 CCG 卡面渲染 —— **列表态静态卡**（无 tilt、无光效跟随、不进 rAF）
2. 点开详情 → **CCG 交互卡**（3D 倾斜 / 翻面 / 光效尽情交互），布局沿用领取弹窗双栏
3. locked 卡：**纯前端 CSS 灰度**（不生成灰度图），列表与弹窗一致
4. **不动页面外壳**：页头标题栏、统计条、筛选 tab、底部导航、整页背景一律不碰

## 3. 范围外

- 后端一行不动（`card_no` / `card_theme` / `card_stars` 已在 B1/B2 处理）
- 7 日盲盒区（`#card-daily-blindbox` / `blindbox-badges-grid`）本轮不动
- B3 防伪档位、B4 底座去留（等 dad 眼验）
- 不做用户端主题选择器（dad 已定：主题是设计期材料）

## 4. 决策记录（dad 已拍）

| 问 | 结论 |
|----|------|
| 列表性能 | **列表静态卡**（44–46 张不上 rAF/tilt），只有弹窗里那张交互 |
| locked 态 | **CSS 灰度**（沿用旧规矩，不生成灰度图） |
| 弹窗形态 | 先沿用领取弹窗（`.ccg-claim-*`）双栏，命名 / tag / 条件 / 日期 / 故事 |
| 页面外壳 | **只换卡 + 弹窗**，外壳不动 |

## 5. 验收标准

1. `/achievements` 与 `/badges` 卡墙渲染为 CCG 卡面；列表**无** pointer 跟随 / 无 3D 倾斜
2. 点开详情：CCG 交互动效可用（倾斜 ±22°/抬起 20px/翻面/光效），字段取自原 `data-*`（数据源不变）
3. locked 卡视觉 = 灰度 + 锁标；点开弹窗也是灰度的 CCG 卡（不是旧 PNG）
4. CCG 卡面编号（`No.%03d`）在列表与弹窗一致（承接 B1）
5. 全量 `pytest tests/` 绿（新分支基线 **732 passed / 8 skipped / 0 failed**）
6. 版本号按纪律升（`badge-ccg.js` + `badge-ccg.css` + demo 页 chip = **v1.6.0-dev**），
   `demo-archive/` 只读不覆盖

## 6. 执行方式与产物位置

- 分支：`feat/sprint-26091302-badge-wall-ccg-wiring`（基于 main `440eb5c`）
- 流程：local → test → feature → PR（**dad review + merge**，agent 不自主 merge）
- 文档：本目录 4 份，仓库与 Obsidian vault 两侧逐文件 md5 一致
- 验收：8766 测试环境（B1+B2+B6 合并）给 dad 真机点，agent 只做模板/数值层校验

## 7. 进度

- [x] 现状查证（grep 取证）+ dad 四问四答
- [x] 分支 + sprint 文档（本目录）
- [ ] 实施：`mountCard` 静态模式 + locked 类 + 两页接线 + 弹窗替换
- [ ] 全量 pytest 绿 + 8766 测试环境重建 + PR
- [ ] 收尾：STATUS / DEVELOPMENT_PLAN / API-CHANGELOG（本次无 API 变更）/ vibe log / vault 镜像

## 8. 待 dad 一句话

1. 弹窗优化方向（dad 原话「先做 然后再看是否优化」）
2. B3 防伪档位 1 / 1.6 / 2.4、B4 底座去留（上一 sprint 遗留）
3. PR #324（B1）+ #325（B2）是否 review 合并
