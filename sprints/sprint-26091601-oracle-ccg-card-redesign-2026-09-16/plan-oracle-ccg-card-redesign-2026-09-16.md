# sprint-26091601-oracle-ccg-card-redesign-2026-09-16

**父 sprint**：sprint-26091402-badge-ccg-modal-stage-2026-09-14（#329 已 merge main `19080bc`）

**发起人**：dad（多轮视觉反馈定稿收敛，要求「本地 Demo 先行，看满意后再投产」）

**目标**：在 #326–#329 已上生产的 CCG 卡面基础上，完成**典藏卡（Oracle）体系重构**——彻底解决「粗重金框喧宾夺主」与「名牌多边形生硬切割」两个核心视觉问题，并落地沉浸式 3D 整卡翻转舞台。

**范围（4 项核心改进）**

1. **弱化粗金框 → 1px 细金掐丝边**
   原 6px 粗重实心土豪金边框收敛为 1px 白边叠加 1.5px 微金属描边（`inset 0 0 0 1px rgba(255,255,255,.45)` + `inset 0 0 0 1.5px rgba(212,160,23,.35)`），让视觉重心回归中央原画。

2. **矢量水墨泼墨名牌**
   废弃原多边形（`clip-path: polygon`）硬切割名牌，改为矢量水墨泼墨：宣纸渗墨滤镜（`feTurbulence` fractalNoise + `feDisplacementMap`）+ 飞白丝缕 + 自由迸溅墨星，逐张卡独立渲染。

3. **7 系分类底板与专属印章**
   按 `artToneFromTag()` 白名单（突破 / 巅峰 / 执着 / 晋级 / 神秘 / 段位 / 主题）为画窗配专属氛围底渐变，并配对应精铸金章 SVG（`ORACLE_SEALS` 白名单查表）。

4. **3D 刚性整卡 180° 翻转舞台**
   纯 CSS 刚性整卡翻转（非分层视差），保证象牙白卡背与四角回纹完整展示；Modal 沉浸式把玩舞台（**无关闭按钮**，点击毛玻璃空白退出）。

**非范围（硬约束）**

- 后端零改动：`badge_theme.py` / `badge_db.py` / `routes/badge_workflow.py` / `routes/badge_claim.py` 不动
- `data/`、`pytest`、`requirements.txt` 不动，无新增依赖
- 3D 几何参数基线（`maxTilt` / perspective / 卡面比例）不做破坏性变更
- untracked 运行时产物（`data/`、`dizical-ai/`、`demo_ccg_v3.html` 等）不纳入提交

**验收线**

| # | 验收项 | 目标线 |
|---|--------|--------|
| 1 | 金框视觉重量 | 1px 白 + 1.5px 金属；视觉重心回归原画 |
| 2 | 名牌形态 | 矢量水墨泼墨（自然边缘），非多边形硬切 |
| 3 | 分类底板 | 7 系全部有专属氛围底 + 专属印章，无缺失/回退错配 |
| 4 | 整卡翻转 | 180° 刚性翻转，卡背象牙白 + 四角回纹完整 |
| 5 | Modal 关闭 | 0 个显式关闭按钮；点毛玻璃空白 / ESC 可退出 |
| 6 | 回归测试 | `pytest -q --ignore=tests/config_ui_fixes` → 768 passed / 0 failed |
| 7 | 改动隔离 | 仅 6 个前端生产文件；无后端/DB/untracked 污染 |

**实施顺序**

1. Grok 完成 6 个前端生产文件合流改造（feature 分支 `feat/oracle-ccg-card-redesign`）
2. 全量回归测试基线
3. CDP 视觉验收探针（网格 + Modal 正面 + Modal 背面）
4. 独立代码安全与兼容性审计
5. dad 视觉把关 → squash merge

**Alternative considered and rejected**：保留原 6px 金框仅调色 —— 拒绝，因为 dad 诉求是「视觉重心回归原画」，仅调色无法解决边框抢占视觉重量的问题。
