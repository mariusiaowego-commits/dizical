# practice-ui-iter 2026-09-04 方案 — 作废归档

> 归档日期: 2026-09-20
> 状态: **全部作废**。新一轮 practice UI 重构以当前 main（刻度尺版）为基准重做，不以本目录内任何结论为依据。

---

## 这批文档是什么

2026-09-04，Hermes 与 agy 各自对 practice 页做了一份独立静态诊断，由 Hermes 整合成一份「12 个问题 / 4 个 sprint / 约 4.5 天」的方案，等 dad 拍 4 个决策点。决策一直没拍，方案挂在 `_pending` 一个月没动。

| 文件 | 作者 | 内容 |
|---|---|---|
| `practice-ui-iter-2026-09-04-hermes.md` | Hermes | 独立诊断，11 个问题 |
| `practice-ui-iter-2026-09-04-agy.md` | agy | 独立诊断，9 个问题，儿童物理场景视角 |
| `practice-ui-iter-2026-09-04-integrated.md` | Hermes (integrator) | 整合版，12 个问题 + 4 sprint 拆分 |
| `pending-practice-ui-iter-2026-09-04/` | 同上三份的 pending 副本 | 带 YAML 元数据 + 5 步启动 SOP + README |

---

## 为什么作废（三条硬理由）

1. **诊断对象已经不在了。** 三份稿都基于「旋钮 + 滚轮」那版代码（3067 行）。9-17 / 9-18 的 sprint 把主计时换成「滚轮数字 + 刻度尺 + ±1 步进」，9-19 又修掉刻度尺在 iPad 上的拖拽。方案里最重的两条 —— P0-3「dial-knob 灵敏度 / 废除」和 P1-5「activity-wheel 80×200 命中率」—— 在主路径上已经没有对应代码，旋钮只剩在补录 tab 里。
2. **整合稿自己有漏项。** agy 提的 P0「离线草稿（断网防丢）」在整合稿的差异表里写着「列为本次 P0-3」，但正文的 P0 编号被 dial-knob 占了，Sprint 1 清单里也没有它 —— 这条在整合那一步就丢了。当前代码 `localStorage` 零命中，确实没做。
3. **4 个决策点里两个被后续事实吸收。** ① dial-knob 存废：主路径已由 0918 sprint 换成刻度尺；② 女儿账号分离：账号体系现有 dad / student / family / teacher / reviewer 角色，student 即可登 `/practice` 并打卡、可改自己今天的 session（`src/kid_app/app.py:151,160`），落地只需开账号，不是 auth 大工程。

---

## 仍然成立的结论（当现状事实读，不当方案读）

这些是复核时在**当前代码**里实测到的，跟旧方案对错无关：

- dashboard 黑底渐变还在：`src/kid_app/templates/practice.html:992` `linear-gradient(#2C3E50,#34495E)`；`.dci-tempo` `#FFD93D` L999；`.dci-assign-label` `#FF8C5A` L1002
- 两个「重新选择」入口仍并存：`.resel-btn` L1099 + `.reselect-float` L1122
- token 漂移比当时更重：唯一 hex 从「30+」变成 107 个（CSS 块内 91 个），CSS 变量只有 5 个
- 开始按钮仍是青绿 `#4ECDC4`，不是品牌珊瑚红（这条 0904 没提，9-08 审计 H5 提了）
- 16 处 `alert()` / `confirm()` 仍在
- 页面规模从 3067 行涨到 3706 行（CSS 1015 / HTML 242 / JS 2376），仍是单文件

---

## 2026-09-20 dad 拍板（新一轮方向）

- **旧方案全部作废**，重新做 practice UI 重构，基准 = 当前 main（时间选择改成刻度尺那一版）
- **补录整个环节砍掉。** 数据支撑（`data/dizi.db` 只读统计）：`daily_practices.items` 里 `is_extra` 条目 45 / 920 = **4.9%**，补录分钟合计 396，用过补录的天数 23，**最近一次补录 2026-06-13** —— 三个多月没人用
- 评审起点：派 agy 做一轮前端 UI + layout 评审（只评审不改码），报告出来后另立新 sprint

---

## 使用提醒

- 引用本目录任何结论前，先看上面三条作废理由。
- **未作废的证据文档**：`docs/uiux-interaction-audit-2026-09-08.md`（Playwright 真机走查，Critical 4 / High 11 / Medium 12，截图 `docs/screenshots/uiux-audit-2026-09-08/`）。它仍然是有效的现状证据，但拍的是**刻度尺改版之前**的界面。
