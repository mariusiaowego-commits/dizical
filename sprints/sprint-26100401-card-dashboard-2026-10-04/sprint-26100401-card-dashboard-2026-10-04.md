---
type: sprint
project: dizical
sprint: sprint-26100401
title: 向右延伸卡片 dashboard + 各卡修正
date: 2026-10-04
status: in-progress
branch: feat/practice-ui-iter-260920
tags: [dizical, practice-ui, card-dashboard]
---

# sprint-26100401 · 向右延伸卡片 dashboard + 各卡修正

## 需求来源
dad MRD `2610041201` 段（vault `PRDs/MRD-练习页前端重构prompt集合（feat-practice-ui-iter-260920）.md`）
前序：`sprint-26100301-practice-right-column-2026-10-03`（右栏零件页 + 深墨对比度修复）

## dad 已答 6 条（执行口径）
1. 高度预算算得下；**无底部 navigation**（页面是顶部 `.nav` ≈53px）；iPhone 440 宽度不变、纵向一个一个往下排
2. 卡宽：每张卡自己声明 min/max，dashboard 统一间距与吸附
3. 分支：practice 一个独立 branch 一直迭代；其余按 git 惯例（我方口径见 `card-contract.md` §3）
4. 节拍取值：计时开始那一刻**快照**
5. title-col = 计时时间 + ruler 区域，与老师要求无关；老师要求 = **独立卡片**、与仪表盘同层级、练习中可看
6. 并行铺开多 worker；今日练习时长卡先做 demo

## 工作流与分工（按文件所有权切块）
| # | 工作流 | 文件 | 主导 | 状态 |
|---|--------|------|------|------|
| W1 | D1 仪表盘 9 条修正 | `dashboard-skin-01-v2.html` | agy | 进行中 |
| W2 | D3 下方三块 5 条修正（+ 自引用 token 修复） | `dashboard-bottom-blocks-01-v2.html` | agy | 进行中 |
| W3 | D2 节拍器 4 条修正 | `metronome-01-v2.html` | agy（W2 后） | 排队 |
| W4 | 新卡：今日练习时长卡 | `practice-duration-card-01.html` | hermes | ✅ 交付 `ASSERT_OK`（含负控） |
| W5 | 卡片 dashboard 骨架 | `card-dashboard-skeleton-01.html` | hermes | ✅ 交付 `ASSERT_OK` |
| W6 | 生产 ruler 抽成共享件 | `shared/ruler-production.*` | hermes | ✅ 交付 `ASSERT_OK` |
| W7 | D4 改独立卡片 | `requests-card-01.html` | 待派 | 等变体拍板 |

## 本轮已交付（hermes lane）
- `shared/ruler-production.{css,js}`：生产 ruler 逐行切片成共享件（CSS 580-637 / JS 3993-4021、4028-4038、4060-4078、4229-4500），
  几何与动效一字未改；颜色提成 `--ruler-*`（默认=生产值）+ 末尾深墨覆盖块。生成器 `tools/gen-ruler-shared.py`（生产改了重跑即可）
- `ruler-shared-check.html`：接入自检页 `?audit=1` = **ASSERT_OK**（ticks 60 / vine 存在 / 气泡池 22 / step 红针 18→20 / 拖拽 11→13 且 is-dragging 挂摘 / 深墨变量换暖白）
  负控：修前真红过三条（红针不动、emitBubbles 空、深墨假红），修完才绿
- `card-dashboard-skeleton-01.html`：向右延伸轨道 + `scroll-snap` 吸附 + ←/→ Home/End 切卡 + 440 纵向堆叠；`?audit=1` = `ASSERT_OK`
- `card-contract.md`：6 张卡 min/默认/max 宽 + 布局规则 + 分支口径 + §5 共享刻度尺接法
- 修 `requests-popout-v1-v2.html` 7 行**自引用 token**（`--dash-x: var(--dash-x)` = 循环引用 → 计算值无效 → 阴影/描边/背景整条被丢弃；浅银皮肤下静默失效）
- 修 `scripts/token-contrast.py`：不再因解析失败崩溃，并把解析不了的 token 显式点出来（就是靠这个抓到自引用）

## 待办
- [ ] W6 ruler 共享件（D1/D2 都照抄生产那套：practice.html:583 + :585 + :616 + buildBubbles/vine）
- [ ] W4 时长卡
- [ ] W7 D4 独立卡（等 dad 选 3D 交互变体）
- [ ] 骨架三遍负控补跑（键盘断言已在一次真实回归中弄红过）
- [ ] 七文件契约纳入 `verify-demos.py` 默认列表
