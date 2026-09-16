---
id: 26091601
type: sprint
version: 1.0.0
start_date: 2026-09-16
end_date: 2026-09-16
status: 已完成
priority: 高
summary: "典藏卡全面重构 — 1px 细金掐丝边 + 矢量水墨泼墨名牌 + 7系分类底板与专属印章 + 3D 刚性整卡翻转"
tags: [sprint, dizical]
---

# sprint-26091601 · Oracle 典藏卡体系重构

- **状态**：已合并 main（dad squash merge）+ 全量回归通过 + CDP 视觉验收通过 + 独立代码审计 GO-with-nits
- **日期**：2026-09-16
- **分支**：`feat/oracle-ccg-card-redesign`
- **Commit**：`46f8ef5`（feature 分支）→ squash merge 为 `ca5363e`（main）
- **PR**：[#330](https://github.com/mariusiaowego-commits/dizical/pull/330)
- **触发**：dad 多轮反馈定稿收敛，要求彻底解决「粗重金框喧宾夺主」与「名牌多边形生硬切割」
- **分工**：Grok（前端 6 文件合流改造实施）→ MiniMax-M3（回归测试 + CDP 视觉验收 + 代码安全与兼容性审计）→ dad（视觉把关 + merge 授权）

## 交付范围（6 个前端生产文件，+817 / −85）

| 文件 | 变更 | 内容 |
|------|------|------|
| `src/kid_app/static/css/badge-ccg.css` | +500 / −60 | 主体：1px 细金掐丝边、水墨泼墨名牌、7 系底板与印章、3D 舞台分层 |
| `src/kid_app/static/js/badge-ccg.js` | +357 / −25 | 3D 跟手倾斜、pointer 事件驱动、整卡翻转交互、7 系印章/水墨 SVG 母版 |
| `src/kid_app/static/css/badge-ccg-themes.css` | +24 | 7 分类画窗氛围底 token（突破/巅峰/执着/晋级/神秘/段位/主题） |
| `src/kid_app/templates/_badge_claim_modal.html` | +15 / −7 | Modal 舞台结构（移除关闭钮、copy 区 hidden） |
| `src/kid_app/templates/achievements.html` | +3 / −1 | 卡墙接入新卡面 + 移除关闭钮 |
| `src/kid_app/templates/badges.html` | +3 / −1 | 卡墙接入新卡面 + 移除关闭钮 |

**非范围**：后端（`badge_theme.py` / `badge_db.py` / `routes/*`）零改动；`data/` 未触碰；pytest 未改动；无新增依赖。

## 4 项核心改进

| # | 改进 | 实现要点 |
|---|------|----------|
| 1 | **弱化粗金框 → 1px 细金掐丝边** | 由原 6px 粗重实心金框收敛为 `inset 0 0 0 1px rgba(255,255,255,.45)` + `inset 0 0 0 1.5px rgba(212,160,23,.35)`，视觉重心回归中央原画 |
| 2 | **矢量水墨泼墨名牌** | 宣纸渗墨滤镜（`feTurbulence` + `feDisplacementMap`）+ 飞白丝缕 + 自由迸溅墨星；替换原多边形硬切割名牌 |
| 3 | **7 系分类底板与专属印章** | 7 个分类（突破/巅峰/执着/晋级/神秘/段位/主题）各配专属画窗氛围渐变 + 精铸金章 SVG；`artToneFromTag()` 白名单映射 |
| 4 | **3D 刚性整卡 180° 翻转** | 纯 CSS 刚性整卡翻转，保证象牙白卡背与四角回纹完整展示；Modal 内沉浸式把玩舞台（无关闭钮 / 点毛玻璃空白退出） |

## 验收证据

### 自动化回归（本 commit 实测）

```
$ python3 -m pytest -q --ignore=tests/config_ui_fixes
768 passed, 8 skipped, 34 warnings in 34.67s
```

- **768 passed / 0 failed / 0 errors**，退出码 0
- 34 条 warning 均为既有技术债（`datetime.utcnow()` / `click.utils` DeprecationWarning），非本次引入

### CDP 视觉验收探针

```
$ python3.12 /tmp/minimax_qa_probe.py
Saved prod_oracle_achievements_grid.png
Saved prod_oracle_modal_front.png
Saved prod_oracle_modal_back.png
CDP probe completed successfully!
```

| 截图 | 内容 | 状态 |
|------|------|------|
| `prod_oracle_achievements_grid.png` | 卡面网格 1280×960 @2x | ✅ 通过 |
| `prod_oracle_modal_front.png` | Detail Modal 正面整卡 | ✅ 通过 |
| `prod_oracle_modal_back.png` | Detail Modal 卡背整卡翻转（典故故事） | ✅ 通过 |

### 独立代码安全与兼容性审计

审计结论：**GO-with-nits**（0 阻塞项）。详见 `verify-2026-09-16.md`。

- ✅ 改动范围严格限定 6 个前端文件，无 DB/后端/测试污染
- ✅ 无 untracked 运行时文件混入提交
- ✅ 无资源泄漏路径（setInterval 双路径清理正确、rAF 均有界、`bindModal` 幂等守卫）
- ✅ `-webkit-backface-visibility` / `-webkit-backdrop-filter` 前缀齐备
- ⚠️ `cqw` 容器查询无 px 兜底 → iOS < 16 存在文字溢出复现风险（待真机确认）
- ⚠️ 卡墙 hover tilt 仍生效（与本地 Demo「列表静态化」存在偏差，属 pre-existing 行为）
- ⚠️ 前端改动无自动化测试覆盖（768 pass 仅证明后端无回归）

## 遗留项（待 dad 决策）

- [ ] **真机 iPad 验证文字等比缩放** —— `cqw` 无 `@supports` 降级，iOS < 16 会复现「文字撑爆卡面」
- [ ] **需求 4「列表态静态化」是否属交付范围** —— 生产卡墙仍 hover tilt（maxTilt 22），与 Demo 行为不一致
- [ ] 删除 `ensureModal()` JS 回退模板里的 `.ccg-claim-close`（生产不可达，但破坏单一事实来源）
- [ ] 补 `esc()` 包裹 6 处字段插值（XSS 技术债，pre-existing，可另开 PR）
- [ ] 未打 git tag（按 skill §5 仅在 ALL P0 ✅ 且 dad 拍板后打）
- [ ] 未写 `shipped_tag`（按 skill §7 需 dad 拍板 closeout OK 后激活）

## Sprint 回顾

| 维度 | 内容 |
|------|------|
| 预计 vs 实际 | 视觉重构一轮到位；dad 多轮迭代收敛后一次 squash merge |
| 学到 | 演示态（Demo）与生产态的差量必须在交付说明中显式列出——本次「列表静态化」在 Demo 已实现但生产沿用 pre-existing hover tilt，属需求解读偏差 |
| 风险点 | `cqw` 容器查询的 iOS 版本门槛未做兜底；前端改动缺自动化覆盖，唯一证据为 CDP 探针 + 人工验收 |
