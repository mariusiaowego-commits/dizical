# 深墨对比度修复 + 3.5 方案2 落地 — 证据链（2026-10-03）

dad 两条反馈 → 我实测定位 → 修 → 逐项实测复核。**所有数字都是浏览器 computed style / 脚本实测，非文字断言。**

## 1 你报的问题与实测确认

你的原话：深墨 theme 下 `session-indent` 等内容文字对比度不强。

实测（改前，浏览器全页扫描，含 alpha 合成解析背景）：
```
深墨  .brand「D5 今日记录」     #2C3E50 on #2C3E50  → 1.00   完全看不见（比你看到的更严重）
深墨  .c-detail session 明细    #2C3E50 on #1A1E34  → 1.53   ← 你报的这条
深墨  .c-name 科目名            #666666 on #1A1E34  → 2.92
深墨  「展开」未选中按钮         #666666 on #3E474E  → 1.65
浅银  .v.delta.up「+27」        #FF6B6B on #FFFFFF  → 2.78   < 3.0（两皮肤都不达标）
```

## 2 根因

`--dash-ink`(#2C3E50) 与 `--dash-muted`(#666666) 在 `:root[data-skin="ink"]` 里**照抄浅银值、没翻转**，
却被当**正文色**用 → 深底上仍是深色字。

关键约束：这两枚 token **同时当填充色用**（`background: var(--dash-ink)`、渐变色标、`.is-on` 反色钮、
D3 `background: var(--dash-muted)`）→ **不能直接翻转**，否则按钮/渐变全坏。

## 3 修法：新增会翻转的语义文字 token（不是改旧 token 值）

| token | 浅银 | 深墨 | 用途 |
|---|---|---|---|
| `--dash-text` | #2C3E50 | #FFF8F0 | 正文/主信息 |
| `--dash-text-soft` | #666666 | rgba(255,248,240,0.68) | 次级信息 |
| `--dash-delta-up` | #E04A4A | #FF6B6B |「相比昨日」多（红字） |
| `--dash-delta-down` | #0C8A60 | #10B981 |「相比昨日」少（绿字） |
| `--dash-accent-text` | #B8531F | #FF8C5A | 品牌橙当文字（如「补录」标签） |
| `--dash-coral-text` | #E04A4A | #FF6B6B | coral 当文字（第四轮，进行中） |

替换规则：**按属性名逐条判断** —— 只有 `color:` 换，`background`/`border`/`box-shadow`/`linear-gradient`/`fill`/`stroke` 一律保留。
六个文件（4 个 v2 + D5 + 探针）一起改，`--dash-*` 契约名从 62 → 66 → 67（第六轮后 68）。

## 4 改前 / 改后（D5 浏览器实测）

| 位置 | 改前 | 改后 |
|---|---|---|
| 深墨 `.brand` | 1.00 | 达标（不再出现在不合格清单） |
| 深墨 `.c-detail` 明细 | 1.53 | 达标 |
| 深墨 `.c-name` | 2.92 | 达标 |
| 深墨 `.seg .is-on` 三处 | 1.04 | 10.43 |
| 浅银 `.tag`「补录」11px | 2.12 | 达标（≥4.5） |
| 浅银 `.v.delta.up`「+27」28px | 2.26 | 3.94 |
| **D5 不合格总数（两皮肤）** | **9** | **0**（各 77 处文字全过；深墨最低 5.18、浅银最低 3.94） |

静态门禁 `scripts/token-contrast.py`：改前六文件 × 两皮肤共 **60 处**不合格 → 改后 **0**。

## 5 六页全量实测（带渐变背景识别，避免把渐变底当页面底色）

| 页面 | 深墨 | 浅银 | 结论 |
|---|---|---|---|
| D1 仪表盘 | 0 | 0 | 干净（深墨最低 10.43） |
| D5 今日记录 | 0 | 0 | 干净 |
| D2 节拍器 | 3 | 3 | 不合格全在**注记层脚手架**（`cal` / `[路线 A 已拍板]` / 「开始自检」）+ 1 处 coral 当文字 |
| D3 下方三块 | 2 | 2 | 同上（`cal` / `[扬声孔…]`） |
| D4 需求弹窗 | 2 | 2 | 同上（`cal` / 「变体 A…」）+ `.card-metro-val` coral 当文字 |

「注记层」= 实施者为 demo 加的说明文字/自检按钮/变体切换条，**不是产品 UI**，按脚手架处理不改。

## 6 3.5 落地 = 方案2（GSAP 逐帧），dad 已拍板

- 本地 `../vendor/gsap.min.js`，`gsap.ticker` 逐帧按「行到容器上下边缘距离」算模糊（带 32px、上限 5px），离边快速收清
- `prefers-reduced-motion` 下不做模糊
- `?audit=1` 新增实测字段并**条件化断言**（修掉「初始态默认红」）：
```
初始/顶端  {ok:true, scrollZone:"top",  blurExpected:false, edgeBlurMax:5, blurCleared:false}
中段       {ok:true, scrollZone:"mid",  blurExpected:true,  edgeBlurMax:5, blurCleared:false}   ← 关键断言
底端       {ok:true, scrollZone:"bottom",blurExpected:false, edgeBlurMax:0, blurCleared:true}
负控：注释掉 gsap.ticker → 中段 ASSERT_FAIL edgeBlur: got 0 want > 0.5；恢复 → 绿
```

## 7 收皮项核对（浏览器实测）

| 项 | 规格 | 实测 | 结论 |
|---|---|---|---|
| heroic 数值 | 28px / 850 | 28px / 850 | ✓ |
| 表头 | 34 高 / 11.5px / 750 | h=34 / 11.5px / 750 / 底 surface-2 | ✓ |
| 行高 | 科目 44 / session 40 | 44 / 40 | ✓ |
| 744 档隐藏「明细」列 | display:none | display:none，5 列无溢出 | ✓ |
| 440 档 | 三层卡片网格 | 现为「339px 48px」两列 + 换行拼凑 | ✗ 第四轮改 |
| 占比微条 | 48×4（轨 ink-a12 / 条 coral） | 未落地（只有百分比） | ✗ 第四轮补 |
| 折叠/展开过渡 | GSAP 淡出上移 | 已实现 | ✓ |

## 8 工具（三件，都可重复跑）

| 工具 | 作用 | 用法 |
|---|---|---|
| `scripts/verify-demos.py` | 静态八项 + 契约一致性 + 旧文字色门禁 | `python3 scripts/verify-demos.py` |
| `scripts/token-contrast.py` | token 配对对比度表（按皮肤限定配对 + 复合背景 + OPEN 项分离），有不合规则退出码非 0 | `python3 scripts/token-contrast.py` |
| `scripts/audit-contrast.js` | 浏览器全页实测：逐层 alpha 合成解析背景、渐变背景标注为「未判定」、按 WCAG AA 阈值判 | 页面控制台粘贴后 `await auditContrast()` |

**我这轮修掉的两个工具错误（避免冤枉人）**
1. 静态配对表跨皮肤乱配对 → NG 假涨 10→17；改成按皮肤限定 + 已知项归 OPEN
2. 浏览器实测切皮肤后立即取值 → 量到 `color` transition 的**起始值**，假报「深墨 6 处不合格」；加 450ms settle 后复测，真实为 0

## 9 未决 / 待拍板

1. **白字压在 coral 底上**（产品 UI，2.29～2.78，<4.5）：`.preset-chip.active`（D2）/「开始」按钮（D1）/`.m-term-badge`（D2）—— 只测不改，等 dad 定
2. 注记层脚手架对比度不足（不改）
3. 科目 hero 图源仍是全科目共用占位图（Q2 拍板 A）
4. 3.3「总时长」写入侧新列 `first_start_at`（Q1 拍板 A）—— 属 P4b，未开工
5. 合成页（P2：D1 上 + D3 三块 + D5 下 + D4 入口）未开工
