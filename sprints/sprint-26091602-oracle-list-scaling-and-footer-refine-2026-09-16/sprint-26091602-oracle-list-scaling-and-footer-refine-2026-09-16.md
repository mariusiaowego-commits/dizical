---
id: 26091602
type: sprint
version: 1.0.0
start_date: 2026-09-16
end_date: 2026-09-16
status: 已完成
priority: 高
summary: "Oracle 典藏卡列表态缩放与页脚细节三轮打磨 — 名牌收紧 / 单字类别映射 / 去双层白框 / 弹窗锁标隐藏 / 网格自适应多列与懒加载"
tags: [sprint, dizical]
---

# sprint-26091602 · Oracle 典藏卡列表缩放与页脚细节优化

- **状态**：**已合并入 main** + 全量回归通过 + CDP 视觉验收通过 + 本地服务重启验证通过
- **日期**：2026-09-16
- **分支**：`fix/oracle-list-scaling-and-footer-refine`（远端已删除；本地保留 @ `3daf66f`）
- **PR**：[#332](https://github.com/mariusiaowego-commits/dizical/pull/332) — **squash MERGED**
- **main commit**：**`5ef98fa5a63a0cf590d424ccb73ed99b0f746a66`**（短 `5ef98fa`），merged_at `2026-09-16T05:53:24Z`
- **基线**：main `44981b7`（= PR #330 `ca5363e` + PR #331）
- **触发**：dad 在 `localhost:8765` 真机验收 PR #330 合流后的典藏卡，**连续三轮**提出 UI/UX 打磨要求
- **dad 拍板**：「PR332 我觉得可以了 准备推进。那个加载慢的问题等这次 sprint 做好了收尾掉了以后 再另外专门来优化」

## 三个 commit（squash 为 main `5ef98fa`）

| 轮次 | commit | 触发 | 内容 |
|------|--------|------|------|
| 首轮 | `4496757` | 7 项 UI/UX 问题 | 列表缩放 / 动态单字类别 / 去双层白框 / 弹窗锁标隐藏 / 成就页限 3 张 / cache-buster |
| 二轮 | `248bf43` | 4 项视觉与性能打磨 | 名牌左对齐 / 立绘重心 / 网格自适应多列 / 懒加载 + 闲置降帧 / cache-buster 再升 |
| 三轮 | `3daf66f` | 1 项数量调整 | 成就页已解锁展示数量 **3 → 5 张** |

**累计**：6 个前端文件，**+456 / −70**。

## 首轮 7 项问题 → 方案

| # | 问题 | 方案 |
|---|------|------|
| 1 | 列表态水墨名牌过高，遮挡人物原画 | `.oracle-nameplate` 收紧高度 / 内边距 / 字号 |
| 2 | 胸针 / 印章 / 类别头像尺寸偏大 | 按卡宽等比收缩至 ~15–16px |
| 3 | 页脚 hardcode「晨晨」、类别名冗长 | 动态单字映射：突破→破、巅峰→极、执着→韧、段位→阶、晋级→跃、神秘→秘、主题→典 |
| 4 | 卡片外层仍有白底框 + 阴影 | 移除双层白框 / 边框 / 内边距（`.b-card` 侧排除盲盒） |
| 5 | 3D Modal 内锁标遮挡卡背典故 | 锁定卡在详情 Modal 放大 / 翻转时隐藏锁标 |
| 6 | 成就页已解锁列表过长 | 仅展示最近 3 张（**三轮改为 5 张**） |
| 7 | 静态资源缓存未刷新 | cache-buster `?v=26091602` → **二轮升至 `?v=26091603`** |

## 二轮 + 三轮

**二轮（`248bf43`，6 文件 +34/−28）**：
1. 名牌**文字左对齐** —— `align-items: flex-start !important` + `text-align: left !important` ×2 + `align-self: flex-start !important`（两级容器对齐链全改）
2. 立绘**重心微调** —— `object-position: center 26%` + `translateY(2px)` + 新增 `contain: layout style`
3. badges 卡墙**自适应多列** —— `@media (min-width: 480px) { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)) }`
4. **懒加载 + 闲置降帧** —— `<img loading="lazy" decoding="async">`；列表墙默认 `idleSkip=4`（≈15fps），hover 满帧，focus/modal 60fps

**三轮（`3daf66f`，1 文件 +4/−4）**：`achievements.html` tab 分组 JS `unlocked.slice(3)` → `slice(5)`（阈值与注释同步）

## 改动文件（累计 6 个，+456 / −70）

| 文件 | 说明 |
|------|------|
| `src/kid_app/static/css/badge-ccg.css` | 列表态缩放 / 单字类别 / 锁标隐藏 / 名牌左对齐 / 立绘重心 / `contain: layout style` |
| `src/kid_app/static/js/badge-ccg.js` | 动态类别单字映射 / `<img loading="lazy">` / 列表墙 `idleSkip=4` |
| `src/kid_app/static/oracle_production_audit.html` | **新建**：验收用 8 卡排演页（7 金卡 + 1 张「传说之音」未解锁测试卡） |
| `src/kid_app/templates/badges.html` | 去白框 / 网格自适应多列 / cache-buster |
| `src/kid_app/templates/achievements.html` | 去白框（排除盲盒）/ 展示数量 5 张 / wall `idleSkip: 4` / cache-buster |
| `src/kid_app/templates/_badge_claim_modal.html` | cache-buster |

**未触碰**：后端（`routes/*`、`badge_db.py`、`badge_theme.py`）、数据库、`data/`、pytest。无新增依赖。

## 验收证据

### 全量回归（四轮实测）

| 时机 | 结果 |
|------|------|
| 首轮提交前 | 768 passed, 8 skipped, 0 failed（33.60s） |
| 二轮提交前 | 768 passed, 8 skipped, 0 failed（32.97s） |
| 三轮提交前 | 768 passed, 8 skipped, 0 failed（33.79s） |
| **合并入 main 后** | **768 passed, 8 skipped, 0 failed（33.27s）** |

### CDP 视觉验收

多轮实景截图验收通过：列表态缩放 / 单字类别 / 去白框 / 弹窗锁标隐藏 / 网格自适应多列。

### 合并后本地生产服务

`./scripts/stop-prod.sh` + `./scripts/start-prod.sh` 重启成功：

| 检查 | 结果 |
|------|------|
| 监听 | PID **90279** on 8765 |
| `/health` | **200** `{"status":"ok","database":"ok","lesson_count":28}` |
| `/static/css/badge-ccg.css?v=26091603` | **200** |

## 遗留项（待 dad 定夺，未擅自处理）

- [ ] `achievements.html:218-226` 旧 ID 规则 `#tab-pane-milestone #locked-grid-milestone .b-card` 权重 (2,1,0) > 新版 (1,3,0)，milestone tab 未解锁卡**仍绘制白渐变底 + 红虚线框**
- [ ] `openClaim(data, scheme)` 仅 2 形参（`badge-ccg.js:1115`），第三参 `{ locked:true }` 被静默忽略 → Modal 内 `locked` 语义未透传
- [ ] `oracle_production_audit.html` 已随本 PR 合入 main，是否保留
- [ ] **性能专项**：dad 指示「加载慢」问题另开 sprint（线索见 handoff §九）

## Sprint 回顾

| 维度 | 内容 |
|------|------|
| 预计 vs 实际 | 首轮 7 项一轮到位；dad 三轮追加打磨后一次 squash merge，未返工 |
| 学到 | **Demo 已实现 ≠ 生产已交付** —— 行为性需求（性能 / 监听器 / 降级路径）必须在 PR 描述逐条标注，仅靠截图验收会系统性漏掉 |
| 风险点 | 静态资源 cache-buster 与多模板耦合，改版需同步 4 个引用点；性能问题已明确转入 backlog |
