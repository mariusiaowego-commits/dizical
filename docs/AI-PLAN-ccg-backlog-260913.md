---
source: ai-agent
project: dizical
type: plan-backlog
version: 1.1.0
updated: 2026-09-13
---

# AI-PLAN · CCG 卡片后续清单 (backlog)

> 来源: dad 2026-09-13 拍板 —— 「八、这个工作写进后续plan里 不在这次的sprint里做了，这次内容太多了」
> 范围: 本文件**不属于** sprint-26091201（该 sprint 只收 l1 视觉）。这里是等看/等拍/择期做的条目。
> 关联: `docs/AI-PLAN-ccg-v2-260912.md`（本次 sprint 主方案）· `docs/AI-PRD-徽章卡编号-260912.md` · `src/kid_app/static/demo-archive/VERSIONS.md`（版本登记）

---

## 为什么单开这份清单

dad 2026-09-13 原话两句定了规矩：

1. **「这几套主题不是为了前端能让用户选择展示的，而是为了我作为每次设计卡片时的选项，卡片设计完就成型了，以后要改也是我自己在 config 里面改」**
   → 主题 = **设计期材料**，不是用户功能。前端**不做**主题切换器；一张卡的主题在它被设计出来时定死。
2. **「这次内容太多了」**
   → 本 sprint 只收 l1 视觉；其余条目进本清单，等排期。

---

## 清单

| ID | 事项 | 现状 | 方案 | 阻塞 |
|----|------|------|------|------|
| **B1** | **徽章卡编号**（卡面 `No.007`） | ✅ 开发完成 = PR **#324**（分支 `feat/sprint-26091301-badge-card-no`，commit `b7edb03`），OPEN/MERGEABLE；作者 = 子 agent 主力（中途超时，主 agent 接手补完 fixture/测试）；**独立审计 = 进行中**（此前只有作者自检） | `achievements.card_no` 列（一卡一号永久不变）+ 回填现有 44 张 + 新徽章 `MAX+1` + 两处 API 加可选字段。全文见 `docs/AI-PRD-徽章卡编号-260912.md` | **合下去首次启动会改生产库**（加列 + 回填）→ 等独立审计结论 + dad 点头 |
| **B2** | **主题的「设计期选择入口」**（config 里改 card_theme） | ✅ 开发完成 = PR **#325**（分支 `feat/sprint-26091301b-badge-theme-picker`，commit `4ce0f6c`），OPEN/MERGEABLE；作者 = 子 agent；**独立审计 = 进行中**；已知缺口 = `/config/badge` 有 PIN gate，未做真机点击验证 | config 侧加「卡片主题」下拉（8 套），写入 `card_theme`；用户端维持现状（无选择器）。Python 侧补 3 淡色主题 + `THEME_LABELS` | dad 已说「325 好」；等同一轮审计结论一起合 |
| **B3** | **防伪强度定档 + 接生产** | ✅ **已定档 (2026-09-13)**：默认 **中 ×1.6**；淡色三套（pearl / mint / sakura）因底浅，单独用 **弱 ×1**。不做 `achievements.card_sec` 列（先一套定死，日后要「每卡不同纹样」再加列，走 `card_theme`/`card_stars` 同一套 resolve 模式） | 待实装：把默认值写死进卡面 CSS + 淡色主题覆盖 | 无 |
| **B4** | **金框最外那条 1px 暗掐丝（底座）去 / 留** | ✅ **已定稿 (2026-09-13)：留**（= 现值，`--ccg-frame-base-c` 保留） | 无 | 无 |
| **B5** | **卡片 / 3D 模型设计的版本化流程** | 已落地：`scripts/freeze-ccg-demo.sh` + `demo-archive/VERSIONS.md` + 三处版本号同步点 | 无需开发，只是把「改视觉前先升号 → 定稿再 freeze」当纪律执行 | 无 |
| **B6** | **图鉴两页接 CCG 卡**（「我的成就」`achievements.html` +「成就殿堂」`badges.html` 的卡墙与详情弹窗） | 🔄 **进行中** = sprint-26091302（分支 `feat/sprint-26091302-badge-wall-ccg-wiring`），minimax 实施 / 主 agent 审计把关；尚未 commit / 未开 PR | 卡墙 PNG → CCG 静态卡、详情弹窗 → CCG 双栏；**列表态**：移开＝精致静置、移上＝动态，modal＝动态；点卡**卡背翻面动画**；locked 保持纯前端 CSS 灰度；**页面外壳（页头/统计条/筛选 tab/底部导航/整页背景）不动** | 待 dad 真机验效果 → commit → PR |
| **B7** | **盲盒 7 图主题（ok_sea / rapunzel 等）是否也换 CCG** | dad 2026-09-13 拍：**这轮不动**（保持 PNG） | 另一类 badge，改造量 ≈ 再做一遍 B6；等独立徽章这套用顺了再评估 | 无 |
| **B8** | **锁卡（未解锁）小锁图标** | dad 2026-09-13 拍：**留**（灰度 + 左上角小锁；旧版 `b-lock` 本来就有） | 已实装于 B6（`.ccg-stage.is-locked::after`，位置左上 15%） | 无 |
| **B9** | **gsap 本地化 + 引擎去 gsap 硬依赖** | 未开始 | vendor gsap 到仓内（iPad 移动网络下 cdnjs 不稳，主设备可能一直走兜底路径）；进场动画 / 领卡弹窗动效也补 CSS 兜底，使「没有 gsap 也不丢动画」成为引擎不变量 | 无（风险低，可与 B6 并行） |

---

## 本 sprint 已收 / 未收（对照）

- 已收：**l1**（镭射铺满整卡 + 去掉一层圆角矩形 + 金环 11px→6px 且 5 环→3 环 + 文字区主题化对比处理），见 `badge-ccg.css` / `badge-ccg.js` 头注 v1.2.0-dev 与 sprint md §13。
- 未收（= 本文件）：B1 卡编号、B2 主题设计入口、B3 防伪定档接生产、B4 底座定稿。

---

## 待 dad 一句话的（看完 demo 就能拍，不需要开发时间）

1. ~~l1 新版本体：铺满 + 细金环 + 简化外框 → 就这么定，还是某一处再调？~~ → ✅ 已定稿（v1.5.0 freeze）
2. ~~B4 底座：留 / 去。~~ → ✅ **留**
3. ~~B3 防伪档位：1 / 1.6 / 2.4。~~ → ✅ **中 ×1.6（淡色三套 ×1）**

---

## 附带：仓库卫生（同日挂起，非 CCG 范围）

- 老 PR **#230**（小程序 URL 跳转）长期挂着 → 建议关闭。
- 未跟踪垃圾：`data/`(51M)、`dizical-ai/`(37M) 进 `.gitignore`；删 `badges.html.bak`；B6 对拍页 `_b6ab*.html` 不入库。
