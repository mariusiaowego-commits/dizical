---
title: AI-PLAN CCG 卡 v2 (信息区重设计 + 背景主题系统)
source: ai-agent
author: agy (Claude Opus 4.6 Thinking) — planner, 不写代码
reviewer: hermes (coder profile)
project: dizical
sprint: 26091201
date: 2026-09-12
status: 待 dad 拍板 8 决策点 (hermes 已预决 4 项)
tags: [plan, dizical, badge, ccg, theme]
---

> **来源**: dad 2026-09-12 指示 agy 出方案（只出方案不写代码），本文件为 agy 方案原文 + hermes review 头。
> **参考**: https://poke-holo.simey.me/ / simeydotme/pokemon-cards-css
> **下游**: sprint 26091201，双开发 agent（hermes = A 线信息区，minimax = B 线主题资产），hermes 调度 + review。

## hermes review 结论

**总体**: 可直接实施。A 线给了逐区块尺寸/字号/间距的硬数字（用 `calc(var(--card-w) * …)` 表达，天然三端自适应），
B 线的 token 契约 + `[data-ccg-theme]` 纯 CSS 覆盖方案零 JS 开销，5 套主题色板齐备。

**已预决（低风险，dad 可推翻）**
- A-2 日期格式 → **A 完整「2026年6月16日」**（dad 早前已明确要这个格式）
- A-3 菱形装饰 → **B 仅左侧一颗**（极简偏好）
- B-2 初版主题数 → **C 全 5 套**（dad 诉求就是"只有深紫不够"；纯 CSS 增量小）
- B-3 暗纹按主题换 → **A 每套独立**（dad 明确提到"不同的风格和纹理"）
- B-4 demo 切换 → **C URL param + 下拉都做**（dad 要真机自己验）

**待 dad 拍板**: A-1（是否新增属性条）/ A-4（描述 2 行 vs 3 行）/ B-1（theme 来源）/ 以及 PR #323 是否先 merge

**review 补充要求（实施时必须遵守）**
1. 主题色的镭射色偏：plan 里 `--sunpillar-1~6` 逐段覆盖太脆，实现改为每主题一个 `--theme-laser-tint`（filter 表达式，如 `hue-rotate(-14deg) saturate(1.2)`），作用在 `.ccg-foil-laser` / `.ccg-foil-security` 上。
2. 暗纹 SVG 走**外部文件** `static/img/ccg-patterns/<theme>.svg`（plan 未指定形态）；现有暗纹是内联 data URI，改外部文件后 `mask-image` 语义不变，但需确认 `mask-repeat`/`mask-size` 沿用 `--theme-security-size`。
3. 新增主题后必须回归 v1 两个修复（否则视为打回）：指针出窗镭射无直角硬边（commit `6bef848`）；光斑滑出金框不压深色（`8af7ccc`）。
4. `achievements.theme` 若采纳 → 需登记 `API-CHANGELOG.md`（🟡 部分兼容）+ 小程序侧评估。

---

# dizical CCG 徽章卡 — 双方案设计规格书

> **角色**: agy (Claude Opus 4.6 Thinking) — 策略/架构 planner, 不写代码
> **日期**: 2026-09-12
> **分支**: `feat/sprint-26091101-badge-3d-ccg`
> **参考**: simeydotme/pokemon-cards-css, poke-holo.simey.me, poke-151.simey.me

---

## 方案 A — `.ccg-info-bar` + `.ccg-plate` + `.ccg-foot` 信息区重设计

### A.1 现状诊断

当前下 1/3 区域（画框底线 61% → 底 100%）包含三个独立绝对定位块:

| 区块 | 位置 | 当前问题 |
|------|------|---------|
| `.ccg-info-bar` 银数据条 | `top: 62.6%`, `height: 4.2%` | ①编号/标签/日期三列过于均匀,缺少主次; ②银色金属拉丝材质不够立体; ③与下方 plate 间距不足,视觉粘连 |
| `.ccg-plate` 米色说明栏 | `top: 68.8%`, `bottom: 12%` | ①标题两侧菱形装饰(`.ccg-orn`)在小卡面上过细看不清; ②标题行左对齐但 `.ccg-stars` 右对齐导致居中主义被打破; ③说明文字双行截断后行距不够松弛 |
| `.ccg-foot` 页脚 | `bottom: 3.2%` | ①殿堂名与 DIZICAL 品牌之间空旷; ②缺少细节收尾(如编号/序列号/稀有标记) |

### A.2 目标版式: 仿 Pokemon V-card 下三区重构

参考 simeydotme 的 Amazing Rare 版式信息层级,重构为 **四段式垂直流**:

```
┌──────────────────────────────────┐  ← 金框底线 61%
│           gap ≈ 1.6%             │
├────────── 银数据条 ──────────────┤  ← 62.6%  h=4.2%  (保留)
│           gap ≈ 2%               │
├────────── 招式说明栏 ────────────┤  ← 68.8%  (调整)
│  ┌ 标题行: 名称 + 星级 + 稀有度 ┐│
│  ├ 细分割线                      ││
│  └ 描述文本 (最多 2 行)         ┘│
│           gap ≈ 1.2%             │
├────────── 弱点/属性条 (新增) ───┤  ← ~85%   h=3.5% (新增可选)
│           gap ≈ 0.8%             │
├────────── 页脚                  ─┤  ← bottom 3.2%  (调整)
└──────────────────────────────────┘
```

### A.3 逐区块设计规格

#### A.3.1 银数据条 `.ccg-info-bar` (保留改良)

**保留**: clip-path 两端收尖六边形、绝对定位布局、指针事件穿透
**改**: 增强金属感 + 内容重排

```
结构: [编号] ——————— [中部分类 · 小竖线 · 日期] ——————— [稀有度图标]

- 编号 "NO.007"
    font-size: calc(var(--card-w) * 0.030)    ← 比现在大一档
    font-weight: 800
    letter-spacing: 0.06em
    color: #1f2329                              ← 更深,更醒目
    font-family: system-ui (非衬线等宽)

- 中部 "突破 · 2026年6月16日"
    font-size: calc(var(--card-w) * 0.026)
    color: #6b5839
    分类名 weight 700, 日期 weight 500
    用 "·" 中点分隔 (不留两个子 span)

- 右侧稀有度
    小菱形(◆) 或星标, 金色 #d4a017
    font-size: calc(var(--card-w) * 0.028)
```

**金属材质增强**:
```css
background:
  /* 第一层: 冲压倒角——上亮下暗 */
  linear-gradient(180deg,
    rgba(255,255,255,0.92) 0%,
    rgba(255,255,255,0.15) 38%,
    rgba(0,0,0,0) 50%,
    rgba(0,0,0,0.12) 78%,
    rgba(0,0,0,0.22) 100%),
  /* 第二层: 拉丝金属——边缘微暗中心亮 */
  linear-gradient(90deg,
    #8d939c 0%, #d8dde3 8%, #f5f7fa 42%, #f8fafc 58%, #d4d9df 92%, #888f98 100%);
/* 额外 1px 内嵌高光 */
box-shadow: inset 0 1px 0 rgba(255,255,255,0.7),
            inset 0 -1px 0 rgba(0,0,0,0.08);
```

**尺寸微调**:
- `height: 4.6%` (从 4.2% 升至 4.6%, 多 0.4% 用来给文字更多竖向呼吸)
- `padding: 0 5.6%` (从 6.4% 缩至 5.6%, 编号可以更靠边)

#### A.3.2 说明栏 `.ccg-plate` (主要改动)

**重新定义内容层级**:

```
┌──────────────────────────────────────────┐
│  ◆ 批改小帮手         ★★★  ← 标题行  │
│  ───────────────────────────── 分割线    │
│  协助完成课后批改                        │
│  连续参与3次课后作业批改, 表现优秀       │
└──────────────────────────────────────────┘
```

**标题行 `.ccg-plate-head` 改造**:
```
- 去掉左右 ccg-orn 菱形装饰 (太细看不清, 不如简洁)
- 改为: 左侧一颗 ccg-orn 作 accent + 徽章名称 + 右侧星级

名称:
  font-family: var(--ccg-serif)
  font-size: calc(var(--card-w) * 0.052)   ← 从 0.048 升至 0.052 (≈15.6px)
  font-weight: 700
  color: #3d2a0a                            ← 更深墨金
  letter-spacing: 0.06em

星级:
  星星尺寸: calc(var(--card-w) * 0.032)    ← 从 0.034 微降
  gap: 3px
  位置: 弹性盒右对齐 flex: 0 0 auto

分割线:
  height: 1px
  background: linear-gradient(90deg,
    rgba(180,140,50,0.5) 0%,
    rgba(180,140,50,0.22) 40%,
    rgba(180,140,50,0) 100%)               ← 左重右轻, 比等宽横线有层次
  margin: calc(var(--card-w) * 0.012) 0
```

**描述区 `.ccg-plate-desc` 改造**:
```
font-size: calc(var(--card-w) * 0.031)     ← 从 0.0295 微升
line-height: 1.55                           ← 从 1.5 微升
color: #4d3e22                              ← 更深, 更可读
-webkit-line-clamp: 3                       ← 从 2 行改为 3 行 (若 plate 空间够)
```

**说明栏背景材质增强**:
```css
background:
  /* 顶弧高光 */
  radial-gradient(ellipse 88% 52% at 50% 0%,
    rgba(255,255,255,0.7), rgba(255,255,255,0) 70%),
  /* 仿宣纸/米色珐琅底 */
  linear-gradient(178deg, #fdf8ed 0%, #f7eed6 42%, #f0e4c8 100%);
box-shadow:
  inset 0 1px 0 rgba(255,255,255,0.9),
  0 1px 4px rgba(0,0,0,0.28),
  0 0 0 0.5px rgba(138,100,26,0.18);        ← 新增: 0.5px 极细描边增加"嵌入卡面"感
border-radius: 4px;                          ← 从 3px 升至 4px
```

**位置微调** (核心: 给 plate 更多空间):
```
--plate-t: 69.0%   (从 68.8% 降 0.2%, 给 info-bar 与 plate 间多留 gap)
--plate-b: 89.5%   (从 88% 升至 89.5%, 下方收紧 foot gap)
```

#### A.3.3 属性/类别条 (新增, 可选)

> **决策点 A-1**: 是否新增属性条? 如不需要可跳过

如果 dad 觉得需要更多信息层次, 可以在 plate 和 foot 之间加一条 **属性/类别条** (仿 Pokemon 弱点/抗性条):

```
┌────────────────────────────────────────┐
│  殿堂: 呦呦    │  类别: 突破   │ 2026  │
└────────────────────────────────────────┘

位置: top ~86%, height ~3.2%
背景: 半透明暗底 rgba(10, 8, 4, 0.08)
分隔: 两条竖向 1px 线
字号: calc(var(--card-w) * 0.024) ← 最小号
```

如果跳过, 这些信息已经在 info-bar + foot 里覆盖, 不重复。

#### A.3.4 页脚 `.ccg-foot` (微调)

```
位置: bottom: 2.8%  (从 3.2% 缩至 2.8%, 更贴底)

左侧: 殿堂名 "呦呦成就殿堂"
  font-size: calc(var(--card-w) * 0.024)   ← 从 0.0265 降
  color: #9a8154                            ← 更含蓄金
  letter-spacing: 0.06em

中间(新增): "★" 单颗微型稀有标 (可选)
  color: #c8a030
  font-size: calc(var(--card-w) * 0.022)

右侧: "DIZICAL"
  font-size: calc(var(--card-w) * 0.022)   ← 从 0.0265 降
  color: #d4a83a
  letter-spacing: 0.22em
  font-weight: 700

分割线:
  border-top: 1px solid rgba(200,160,30,0.3)  ← 更细更淡
```

### A.4 间距节奏总表

```
区块             top/bottom       高度/区间        间距
────────────────────────────────────────────────────
金框底线          61%              —                —
  ↓ gap                                           1.6%
info-bar          62.6%            4.6%             —
  ↓ gap                                           2.2%
plate             69.0% → 89.5%   20.5%            —
  ↓ gap                                           0.6%
foot-line         ~92%             —                —
foot              bottom 2.8%     ~5%              —
```

### A.5 字体层级速查 (基于 card-w = 300px)

| 元素 | 字族 | 大小 (px) | 权重 | 颜色 | 字距 |
|------|------|----------|------|------|------|
| 编号 NO.007 | system-ui | 9.0 | 800 | #1f2329 | 0.06em |
| 分类·日期 | system-ui | 7.8 | 700/500 | #6b5839 | 0.04em |
| 徽章名 (plate) | 宋体 Serif | 15.6 | 700 | #3d2a0a | 0.06em |
| 描述文 (plate) | system-ui | 9.3 | 400 | #4d3e22 | 0 |
| 殿堂名 (foot) | system-ui | 7.2 | 600 | #9a8154 | 0.06em |
| DIZICAL (foot) | system-ui | 6.6 | 700 | #d4a83a | 0.22em |

### A.6 响应式断点

| 视口 | `--card-w` | 说明 |
|------|-----------|------|
| Mac (1728×1117) | 300px (max) | 完整版式 |
| iPad 横 (1133×744) | 300px | 同 Mac |
| iPad 竖 (744×1133) | min(300px, 78vw) ≈ 300px | 同 Mac |
| iPhone (440×956) | 78vw ≈ 343px | 卡面略大, 文字自动跟随 |

> 所有字号用 `calc(var(--card-w) * ...)` 表达, 自动适配, 无需额外 media query。

### A.7 JS DOM 变更清单

- `frontMarkup()` L151-166:
  - `.ccg-info-bar` 内容: `<span class="ccg-bar-no">` + `<span class="ccg-bar-info">{tag} · {date}</span>` + `<span class="ccg-bar-rarity">◆</span>`
  - `.ccg-plate-head`: 去掉右 `ccg-orn`, 改为 左 1 orn + name + 右 stars
  - `.ccg-plate-desc`: 保持, 可改 `-webkit-line-clamp: 3`
  - `.ccg-foot`: 保持两列, 可在中间加 `<span class="ccg-foot-mark">★</span>`

---

## 方案 B — 卡面背景主题化系统 (Theming Architecture)

### B.1 设计目标

让每套徽章卡可以有不同的**底衬色调 + 光照色温 + 防伪暗纹 + 说明栏底色**, 如 Pokemon 不同属性有不同卡面质感。

### B.2 架构: 纯 CSS 自定义属性 + `[data-ccg-theme]` 选择器

**核心思路**: 零 JS 开销, 纯 CSS 变量覆盖。theme 通过 `data-ccg-theme="..."` 属性声明在 `.ccg-stage` DOM 节点上。

#### B.2.1 CSS 变量契约 (Theme Token Contract)

```css
/* 主题 Token — 每个 theme 只需覆盖这些 */
:root {
  /* ── 底衬层 (.ccg-foil-stock) ── */
  --theme-stock-color:    #0e1a3e;        /* 基础背景色 */
  --theme-stock-gradient: linear-gradient(168deg, #22377e 0%, #182a66 34%, #1d1c52 66%, #2c1d40 100%);
  --theme-stock-filter:   saturate(1.22) contrast(1.08);

  /* ── 主光源 (径向光晕) ── */
  --theme-light-main:     rgba(255, 226, 148, 0.78);  /* 金色光 */
  --theme-light-sub:      rgba(86, 178, 255, 0.52);   /* 冷蓝补光 */
  --theme-light-accent:   rgba(134, 96, 255, 0.45);   /* 紫调辅光 */

  /* ── 光谱 (可选: 覆盖太阳柱色相) ── */
  --theme-sunpillar-1 ~ 6:  /* 默认不覆盖, 继承 :root 值 */

  /* ── 防伪暗纹 ── */
  --theme-security-pattern: var(--ccg-security-pattern);
  --theme-security-size:    132px 132px;

  /* ── 说明栏 ── */
  --theme-plate-bg-from:  #fdf8ed;
  --theme-plate-bg-to:    #f0e4c8;
  --theme-plate-text:     #3a2c14;

  /* ── 金框色调 (可选) ── */
  --theme-frame-hi:       #fff5c6;
  --theme-frame-lo:       #8a5a10;

  /* ── 外发光 (舞台灯光效果) ── */
  --theme-glow:           hsl(40, 80%, 60%);
}
```

#### B.2.2 主题选择器层叠

```css
/* 默认主题: 星曜深蓝 — 不需要 data 属性 */
.ccg-foil-stock {
  background-color: var(--theme-stock-color);
  background-image:
    radial-gradient(ellipse 56% 42% at 50% 30%, var(--theme-light-main) 0%, ...),
    radial-gradient(ellipse 74% 58% at 13% 5%, var(--theme-light-sub) 0%, ...),
    radial-gradient(ellipse 68% 54% at 90% 95%, var(--theme-light-accent) 0%, ...),
    var(--theme-stock-gradient);
  filter: var(--theme-stock-filter);
}

/* 按属性切换 */
[data-ccg-theme="bamboo"]  { --theme-stock-color: ...; --theme-light-main: ...; }
[data-ccg-theme="coral"]   { --theme-stock-color: ...; --theme-light-main: ...; }
[data-ccg-theme="imperial"]{ --theme-stock-color: ...; --theme-light-main: ...; }
[data-ccg-theme="frost"]   { --theme-stock-color: ...; --theme-light-main: ...; }
```

#### B.2.3 JS 端: theme 来源

```javascript
// badge-ccg.js mountCard() 中, 从 badge 数据读取 theme 并设置:
stageEl.setAttribute('data-ccg-theme', d.theme || 'azure');
```

#### B.2.4 数据库端: achievements 表

```
方案 B-1 (推荐): achievements 表新增 "theme" TEXT 列 (DEFAULT 'azure')
方案 B-2: theme 根据 category 自动映射 (category→theme 映射表在 JS 或 Python 端定义)
```

> **决策点 B-1**: 用 achievements.theme 列 (灵活, 每个 badge 可以独立设置) 还是 category→theme 自动映射 (简单, 同类 badge 风格统一)?

### B.3 五套具体主题提案

#### 主题 1: 星曜深蓝 `azure` (默认, 现款优化)

```
用途: 日常突破、全勤
底色: #0e1a3e (深藏青蓝)
琉璃: linear-gradient(168deg, #22377e → #182a66 → #1d1c52 → #2c1d40)
光源: 金色光晕 rgba(255,226,148,0.78) + 冰蓝补光 rgba(86,178,255,0.52)
暗纹: 竹笛 + DIZICAL (现有)
说明栏: #fdf8ed → #f0e4c8 (米色)
外发光: hsl(40, 80%, 60%) 暖金
```

特点: 已经实现, 只需变量化

#### 主题 2: 竹影翠玉 `bamboo`

```
用途: 基本功、每日练习 (category: 执着/段位)
底色: #0a1f14 (深墨绿)
琉璃: linear-gradient(168deg, #1a3e2a → #143826 → #122e30 → #0e2420)
光源: 翡翠绿 rgba(120,220,160,0.72) + 冷玉 rgba(180,230,210,0.45)
辅光: 深碧 rgba(40,160,120,0.35)
暗纹: 竹叶重复图案 (新 SVG: 竹叶三片 + 水滴 + "笛" 字)
说明栏: #f2f6ef → #e4ead6 (淡竹青)
外发光: hsl(155, 60%, 55%) 翠玉
```

CSS 纹理技法:
- 底层 `repeating-linear-gradient(60deg, ...)` 做竹林竖纹肌理 (极低透明度)
- 镭射光谱偏冷: `--sunpillar-3` (绿) 和 `--sunpillar-4` (青) 增强, 红紫减弱

#### 主题 3: 朱霞流丹 `coral`

```
用途: 考级、舞台表演 (category: 巅峰/晋级)
底色: #2a0e14 (深酒红)
琉璃: linear-gradient(168deg, #5e1a2e → #481830 → #3a1428 → #2e0e1e)
光源: 珊瑚暖红 rgba(255,130,100,0.68) + 琥珀金 rgba(255,200,120,0.55)
辅光: 玫红 rgba(220,60,120,0.35)
暗纹: 祥云 + 音符 (新 SVG)
说明栏: #fdf2ef → #f0ddd4 (淡珊瑚)
外发光: hsl(8, 80%, 58%) 流丹
```

CSS 纹理技法:
- `radial-gradient(circle at 50% 50%, ...)` 做中心辐射暖光
- 镭射偏暖: `--sunpillar-1` (红) 和 `--sunpillar-2` (黄) 增强

#### 主题 4: 紫霄耀金 `imperial`

```
用途: 里程碑殿堂大奖 (category: milestone/神秘)
底色: #1a1030 (深皇紫)
琉璃: linear-gradient(168deg, #2e1a58 → #281650 → #221448 → #1c1040)
光源: 耀金 rgba(255,210,100,0.82) + 紫霞 rgba(180,100,255,0.55)
辅光: 深金 rgba(200,160,60,0.4)
暗纹: 笛韵 + 皇冠 + 星芒 (新 SVG, 在现有基础上加冕)
说明栏: #faf4f8 → #ece0e8 (淡紫米)
外发光: hsl(280, 70%, 60%) 紫曜
```

CSS 纹理技法:
- 双径向光: 上部亮金 + 下部深紫, 形成"拱顶穹隆"效果
- 金框 override: 金色更浓烈 (`--theme-frame-hi: #ffe8a0`)
- 镭射全色相: 不偏向, 六色均衡 (最华丽)

#### 主题 5: 冰霜晶蓝 `frost`

```
用途: 季节/冬季限定 (category: seasonal)
底色: #0c1824 (深冰蓝)
琉璃: linear-gradient(168deg, #1a3050 → #162a48 → #122440 → #0e1e38)
光源: 冰晶白 rgba(200,230,255,0.75) + 极光蓝 rgba(100,200,255,0.55)
辅光: 冰紫 rgba(140,130,255,0.3)
暗纹: 雪花 + 竹笛 (新 SVG)
说明栏: #f0f4f8 → #dce6ee (淡冰蓝)
外发光: hsl(205, 80%, 65%) 霜蓝
```

CSS 纹理技法:
- 微弱 `repeating-conic-gradient(...)` 做冰晶碎片效果
- 镭射偏冷: `--sunpillar-4` (青) 和 `--sunpillar-5` (蓝) 增强

### B.4 主题 → Category 默认映射表

> **决策点 B-2**: 这个映射是否合理? 需要 dad 确认

| category | 默认 theme | 说明 |
|----------|-----------|------|
| 突破 | `azure` | 日常突破,沉稳深蓝 |
| 执着 | `bamboo` | 每日坚持,竹林翠绿 |
| 段位 | `bamboo` | 基本功进阶,同翠绿 |
| 巅峰 | `coral` | 大型考级/舞台,热烈珊瑚 |
| 晋级 | `coral` | 考级晋升,同珊瑚 |
| milestone | `imperial` | 殿堂里程碑,皇紫耀金 |
| 神秘 | `imperial` | 隐藏成就,同皇紫 |
| seasonal | `frost` | 季节限定,冰霜蓝 |

### B.5 文件组织建议

```
src/kid_app/static/css/
├── badge-ccg.css            ← 主文件, 包含默认 azure 主题变量
├── badge-ccg-themes.css     ← 新增: 4 个额外主题的变量覆盖
│                              [data-ccg-theme="bamboo"] { ... }
│                              [data-ccg-theme="coral"]  { ... }
│                              [data-ccg-theme="imperial"]{ ... }
│                              [data-ccg-theme="frost"]  { ... }
```

总计新增 CSS ~180 行 (每个主题 ~40 行变量覆盖 × 4 + 少量共用)。

### B.6 防伪暗纹 SVG 制作规范

每套主题可以有专属暗纹, 规范:
- 画布: 132px × 132px (与现有一致)
- 填色: 纯白 `#fff` (mask-composite 时会自动变成光影色)
- 笔画: `stroke-width: 2.2px`, `stroke-linecap: round`
- 必须包含: DIZICAL 字样 (品牌一致性)
- 可包含: 竹笛/竹叶/音符/雪花/祥云/星芒/皇冠 等元素

### B.7 实施路径 (给 hermes/minimax 的开发步骤)

```
Step 1: 变量化 — 将 .ccg-foil-stock 的 6 个写死颜色值改为 CSS 变量引用
Step 2: 默认值 — :root 中定义 --theme-* 系列变量, 默认值 = 现有 azure 值
Step 3: 新建 badge-ccg-themes.css, 4 个 [data-ccg-theme=...] 块
Step 4: JS mountCard() 中读取 d.theme, 写入 data-ccg-theme 属性
Step 5: demo 页面加主题切换按钮 (或下拉选择)
Step 6: (后续) 数据库 achievements.theme 列 + API 传递
```

> Step 6 可以后做, 先在 demo 页用 URL param `?theme=bamboo` 快速验证。

---

## 待 Dad 拍板的决策清单

### 方案 A 决策

| # | 问题 | 选项 |
|---|------|------|
| **A-1** | 是否新增 `.ccg-attr-bar` 属性条? | **A)** 新增 (三列: 殿堂+类别+年份, 更丰富) / **B)** 不增 (保持现有三区: bar+plate+foot, 够了) / **C)** 后续再定 |
| **A-2** | info-bar 中 "日期" 显示格式? | **A)** 完整 "2026年6月16日" / **B)** 简写 "2026.06.16" / **C)** 更短 "06/16" |
| **A-3** | plate 标题行 ccg-orn 菱形装饰? | **A)** 保留左右两颗菱形 (现款) / **B)** 改为仅左侧一颗 / **C)** 全部去掉, 纯文字+星 |
| **A-4** | plate-desc 行数限制? | **A)** 2 行 (现款, 紧凑) / **B)** 3 行 (更多描述空间) |

### 方案 B 决策

| # | 问题 | 选项 |
|---|------|------|
| **B-1** | Theme 来源? | **A)** achievements 表新增 theme 列 (每张卡独立配置) / **B)** category→theme 自动映射 (同类卡统一风格) / **C)** 两者并存: theme 列优先, 未设则 fallback 到 category 映射 |
| **B-2** | 初版实现几套主题? | **A)** 只做 azure (默认, 变量化即可) / **B)** 做 azure + 1 套 (验证架构) / **C)** 全部 5 套一步到位 |
| **B-3** | 防伪暗纹是否按主题换? | **A)** 每套主题独立暗纹 (竹叶/祥云/雪花...) / **B)** 统一用现有竹笛暗纹 (省事) |
| **B-4** | demo 页主题切换入口? | **A)** URL param `?theme=bamboo` / **B)** demo 页加下拉选择器 / **C)** 两者都加 |

---

## 附录: 技术参考来源

| 来源 | 用途 |
|------|------|
| [`base.css`](https://poke-holo.simey.me/css/cards/base.css) | sunpillar 六色光谱, `--card-glow` 属性主题色, 基础几何 |
| [`cards.css`](https://poke-holo.simey.me/css/cards.css) | `--grain`, `--glitter` 纹理 URL, 五色彩虹变量, clip-path 遮罩 |
| [`regular-holo.css`](https://poke-holo.simey.me/css/cards/regular-holo.css) | 双光栅干涉莫尔纹, 扫描线 |
| [`amazing-rare.css`](https://poke-holo.simey.me/css/cards/amazing-rare.css) | Amazing Rare 版式 glitter + 径向聚光灯 |
| [`v-full-art.css`](https://poke-holo.simey.me/css/cards/v-full-art.css) | V 全画幅箔层合成 |
| `Card.svelte` | 指针追踪 JS (spring 弹簧, RAF 批处理), data-* 属性选择器架构 |
| dizical [`badge-ccg.css`](file:///Users/mt16/dev/dizical/src/kid_app/static/css/badge-ccg.css#L172-L188) | 现有 foil-stock 实现 (变量化改造基线) |
| dizical [`badge-ccg.js`](file:///Users/mt16/dev/dizical/src/kid_app/static/js/badge-ccg.js#L139-L169) | 现有 frontMarkup() DOM 结构 (方案 A 改造基线) |
| dizical [`minip_api.py`](file:///Users/mt16/dev/dizical/src/kid_app/routes/minip_api.py#L184) | achievements.category 枚举: milestone/突破/巅峰/执着/段位/晋级/神秘/seasonal |
