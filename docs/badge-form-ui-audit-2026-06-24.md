# config-badge.html designmd 体检报告 (2026-06-24)

> 目标: 让 config-badge.html 跟 dizicute 设计语言对齐, 干掉自创 token / inline hex / emoji / 死代码.
> **状态**: 体检完成, 待用户拍板改动范围.
> **审计方法**: designmd skill + dizicute DESIGN.md (uiux-asset-library 主权威) + AGENTS.md §UI 偏好 + form-ui-design-spec (本仓沉淀).
> **作用域**: `/Users/mt16/dev/dizical/src/kid_app/templates/config-badge.html` (1610 行, 1 file).

## 1. 现状摘要 (TL;DR)

| 维度 | 现状 | dizicute 期望 | 偏离度 |
|------|------|---------------|--------|
| 色板 | 6 个 var: --cream/--sage/--rose/--lavender/--text/--radius | 6 个 dizicute token: primary/secondary/tertiary/neutral/muted/accent | **P0 硬违反** |
| Inline hex | 10+ 处 (#FF6B6B / #666 / #ddd / #eee / #2C3E50 等) | 0, 全部走 token | **P0 硬违反** |
| Emoji | 6+ 处 (✨🔄🈳✅🗑⚙) | 0, AGENTS.md §UI 偏好明令 | **P0 硬违反** |
| 字体 | Noto Sans SC (line 40) | PingFang SC (dizicute §字体) | P1 偏离 |
| 死 CSS | Portal 状态卡 CSS + 注释 (line 80-86, 101-102) | 0 死代码 | P1 可维护 |
| 文件头注释 | 说 4 步表单 (line 1-14) | 实际 V2.1 2-tab | P1 文档失同步 |
| 模板体积 | 1610 行 (内嵌 ~800 行 CSS) | 拆 static/badge.css | P1 可维护 |
| 间距 | section 48px / 字段 18px (form-ui-design-spec 已拍) | 同 | **已对齐** ✓ |
| 圆角 | sm 8px / md 12px (dizicute) | 同 | **已对齐** ✓ |
| 单列布局 | max-width 640px (.v21-form) | 同 | **已对齐** ✓ |

**核心矛盾**: 表单 7 个组件 token (.v21-form / .v21-field / .v21-section / .v21-submit-btn / .v21-ai-btn / .v21-pending-card / .v21-act-confirm) 整体设计**已对齐 form-ui-design-spec** (dizical 内部规范), 但色板完全脱离 dizicute 单源. 是**结构对, 颜色错**.

## 2. 偏离清单 (按 dizicute 严重度排序)

### P0 — dizicute 硬规则违反 (4 项)

**P0-1: 自创 4 色 token, 全部不在 dizicute 6 色里**

```
:root {
  --cream: #f5e6d3;       ← 不在 dizicute
  --sage: #a8d5ba;         ← 不在 dizicute (sage 命名 = 错认 token)
  --rose: #e8b4bc;         ← 不在 dizicute (rose 命名 = 错认 token)
  --lavender: #c5b8d9;     ← 不在 dizicute (lavender 命名 = 错认 token)
  --text: #3d3d3d;         ← 接近 dizicute secondary #2C3E50, 但不一致
  --radius: 20px;          ← 不在 dizicute 圆角 token
}
```

引用位置 (line 27-33 定义 + line 143/144/259/357/512/566/592/610/653/763 等 10+ 处).

dizicute DESIGN.md §硬规则 1: "No colors outside the palette. 扩展 palette 先, 改 dizicute DESIGN.md."

**处置方案 A (推荐)**: 全部映射到 dizicute 6 色
| 自创 var | dizicute 映射 | 用途 |
|----------|---------------|------|
| `--cream` 背景 | `--tertiary` (#FFF8F0) | 暖白页面底 |
| `--text` 文字 | `--secondary` (#2C3E50) | 主文字 |
| `--rose` 强调 | `--primary` (#FF6B6B) | CTA / 边框 / icon |
| `--sage` 成功 | `--primary` 半透明 或 `--secondary` (中性) | success 反馈 |
| `--lavender` 次强调 | `--secondary` 浅化 (调透明度) | 跳 tab 按钮 |
| `--radius` | `--md` (12px) | 卡片圆角 |

**处置方案 B (不推荐)**: 给 dizicute 提案加 token, 走 `uiux-asset-library` PR. 周期 1-2 天, 不合算.

**P0-2: inline hex 满天飞**

| Line | Hex | 用途 | 处置 |
|------|-----|------|------|
| 230 | #4CAF50 | check-status.unique | → `var(--secondary)` 60% |
| 230 | #FF6B6B | check-status.taken | → `var(--primary)` |
| 256/263 | rgba(232,180,188,0.4/0.5) | btn-primary shadow | → `rgba(255,107,107,...)` (primary) |
| 292 | #4CAF50 | status-line.done | → `var(--secondary)` 60% |
| 296 | #FF6B6B | status-line.error | → `var(--primary)` |
| 326 | #FF6B6B | warning-banner border | → `var(--primary)` |
| 327 | #C62828 | warning-banner text | → `var(--secondary)` 90% |
| 355/356/357 | #4CAF50 / #FF6B6B / var(--rose) | toast success/error/info | → token |
| 380/382 | #2C3E50 / #ecf0f1 | commit-snippet bg/fg | → `var(--secondary)` 95% + `var(--neutral)` |
| 464 | #FF6B6B | v21-field focus border | → `var(--primary)` |
| 473 | #6c5ce7 | v21-ai-btn bg | **新色, dizicute 没有 AI accent** → 用 `var(--secondary)` 或提案加 |
| 487 | #FF6B6B | radio accent-color | → `var(--primary)` |
| 522/526 | #888 | v21-clear-btn text/border | → `var(--muted)` (#666) |
| 565/574 | var(--sage) | v21-copy-btn | → 同 P0-1 |
| 592 | var(--lavender) | v21-jump-pending-btn | → 同 P0-1 |
| 614/617 | #DDD | v21-refresh-btn border | → `var(--muted)` 30% |
| 658/660 | #E74C3C / #FFF5F5 | pending-card conflict | → `var(--primary)` + tertiary |
| 663/664 | #FFE9E9 / #C0392B | v21-conflict | → `var(--primary)` 10% + dark |
| 694/699 | #999 / #F5F5F5 | pending-id | → `var(--muted)` + neutral |
| 707/711 | #666 / #FFFBEA | pending-type chip | → `var(--muted)` + tertiary |
| 725/729 | #555 / #F0F0F0 | meta-chip | → `var(--secondary)` + neutral 80% |
| 752/754/758 | #DDD / #333 | v21-act-btn | → `var(--muted)` 30% + secondary |
| 789 | #f0c040 | v21-help bg | **新色, gold help marker** → 提案加 或 用 primary |
| 789 | #c8860a | v21-help hover | 同上 |

**总处置**: 替换 ~20 个 inline hex, **6c5ce7 紫色 AI 按钮 + f0c040 金色 ? 标记** 是真正需要拍板"扩展 dizicute token"还是"用现有色凑合".

**P0-3: emoji 满屏**

| Line | Emoji | 用途 | 处置 |
|------|-------|------|------|
| 965 | ⚙ | 高级折叠 summary | → 文字 "高级" |
| 956 | ✨ | AI 生成按钮 | → 文字 "AI 生成" |
| 1017 | 🔄 | 刷新按钮 | → 文字 "刷新" |
| 1027 | 🈳 | 空态标题 | → 文字 "没有待确认 badge" |
| 1031 | ⠿ | braille spinner | **保留** (AGENTS.md §UI 偏好明令用 braille spinner) |
| 1119 | ⚠ | 冲突警告 | → 文字 "注意" |
| 1150 | ✅ | 确认按钮 | → 文字 "确认上线" |
| 1153 | 🗑 | 删除按钮 | → 文字 "删除" |
| 1206 | 复制命令 inline | → 已经是文字 | 保留 |
| 1562 | ? | help 标记 | **保留** (是 ASCII 字符, 不是 emoji; 但已是纯文字, 不需要改) |

**真正要删的 emoji**: ⚙ ✨ 🔄 🈳 ⚠ ✅ 🗑 = 7 个.

**P0-4: btn-primary hover lift 反 dizicute CTA 弱化**

```css
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(...); }
```

dizicute CTA 弱化 = 不动 / 不主动吸引注意. translateY -1px 是"主动跳"反馈, 跟 dizicute 哲学冲突. 

**处置**: hover 改成 background 微调 (加深 8%) + 去掉 transform. 或保留 lift 但限制 max(2px). 拍板.

### P1 — 死代码/可维护 (4 项)

**P1-1: 离线死 CSS (Portal 状态卡)**

Line 80-86 + line 101-102 注释说 "V2.5 2026-06-16 已删 /config/api/portal/status", 但还残留:

```css
/* ── Portal 状态卡 CSS (V2.5 2026-06-16 已删) ── */
  font-size: 10px;
  color: #FF6B6B;
  font-weight: 400;
}
```

更糟的是 line 82-86 在 `:root` 块外散着无选择器属性, **CSS 解析可能直接报错或被 silently dropped**. 跟 line 101 重复出现.

**处置**: 整段删. 关联: line 817 HTML 注释 "Portal 状态卡 已删" 也保留冗余, 同步删.

**P1-2: 文件头注释脱节 (line 1-14)**

```html
<!--
  config-badge.html — Badge 制作工作流 (V1 PR-A, 2026-06-12)
  4 步表单:
    ① 元数据 (id / 名称 / type 标签 / category / seasonal_type)
    ② placeholder + 典故 (二选一: 我自己写 / AI 草拟)
    ③ 计算逻辑模板 (calc template 选择)
    ④ 生成 & 预览 (SSE 流式 + 红底验证 + 3 按钮: 重新生图 / 接受 / 取消)
    ⑤ 确认上线 (PIN 输入 + 写入三表)
  顶部 Portal 状态卡: 绿/红/灰灯 + 最后检查时间 + 手动刷新
  Portal 红了: 禁用 Step 4 按钮, 弹 tooltip 解释
  ...
-->
```

实际是 V2.1 2-tab (line 819-1035: "新建 Badge 草稿" + "待确认 Badge"). 注释描述的 4 步 / 5 步 / Portal 状态卡 / SSE 流式 全部不存在.

**处置**: 重写注释成 V2.1 现状: 2 tab + STEP 1 表单 + STEP 2 (外部 hermes skill) + STEP 3 待确认 commit.

**P1-3: 1610 行大模板 + ~800 行内嵌 CSS**

config-badge.html 是项目里最重的内嵌 CSS (V21_* 命名空间占 ~600 行, .step / .progress / .preview-grid / .toast / .success-icon 历史 V1 CSS 占 ~200 行, 加 V2 状态条 / warning / commit-snippet / V2.1 form / V2.1 pending).

**处置**: 拆 `static/badge.css`, config-badge.html 只留 HTML + 必要 inline (none expected). 文件会瘦到 ~800 行. **注意**: dizicute `apply.mjs` 未来可能同步 CSS, 拆出去有利于 token 化.

### P1-4: 内联 style="display:..."

**状态 (2026-06-24 决策)**: **保留内联, 不动 JS**.

5 处 `display:none` + 1 处 `display:flex` 都由 18 处 `el.style.display = '...'` JS 操控 (含 `display: flex` 在 `v21SeasonalRow` 切 seasonal 时).

dizicute 没明令禁内联 display style, AGENTS.md §硬规则只说"用 token 不用 inline hex". 改 JS (18 处 .style.display → .hidden = true/false) 会撞 `v21SeasonalRow` 切到 `display: flex` 时 hidden attribute 失效, 风险 > 收益. JS 行为正确性优先, HTML 风格次之. 后续 P2 重构时统一换 class toggle.

**真实解决路径**: P2 信息架构重排时, 把"显示/隐藏"切到 class toggle (`.v21-row.is-visible`), JS 一并改 `el.classList.add/remove('is-visible')`.

### P2 — 信息架构 (3 项)

**P2-1: 基础信息 8 字段堆一起, 三联动字段散**

当前 (line 828-909): 8 字段按 ID 顺序横排 (id → name → type → category → unlock_strategy → achieved_at_override → seasonal_type → display_format → sort_order).

三联动 (category → unlock_strategy → achieved_at_override) 实际是同一个**"解锁策略决策树"**:
```
category (milestone | seasonal)
  └─ unlock_strategy (calc | immediate)
       └─ achieved_at_override (留空 | 填日期)
            └─ seasonal 时再展开 seasonal_type
```

**处置**: 把 category → unlock_strategy → achieved_at_override 收成一个 "**解锁策略**" 子 section, seasonal_type 嵌进 seasonal category 的子字段. display_format + sort_order 归 "展示设置" 子 section. 字段从 8 个 section 变成 3 个 section:
- 基础信息 (id, name, type)
- 解锁策略 (category, unlock_strategy, achieved_at_override, seasonal_type)
- 展示设置 (display_format, sort_order)

**P2-2: 图片来源 2 选项切时 placeholder 必填逻辑藏 JS**

v21ImageSourceChanged() 改 placeholder 的 required / minlength, 但用户切到 "已有图片" 时**只改 placeholder 标签的红色 \* 隐藏 + 路径输入展开**, 没有任何视觉提示 "placeholder 现在不要求了". 字段是不是必填? 用户靠"必填 \* 消失"猜.

**处置**: 切到"已有图片"时, placeholder textarea 灰化 (opacity 0.5 + cursor not-allowed), 配合 \* 消失. JS line 1293-1305 改 5 行.

**P2-3: 字体用 Noto Sans SC, dizicute 期望 PingFang SC**

Line 40: `font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;`

dizicute DESIGN.md §字体: "PingFang SC (苹方, iOS/macOS 系统自带). Web fallback: system-ui, -apple-system, sans-serif."

**处置**: 改 font-family = `system-ui, -apple-system, "PingFang SC", sans-serif;`. iPad Safari 跟 Mac Safari 都是 PingFang, 效果一致.

**附加 P2 (用户反馈时再加)**:
- P2-4: tab 切换 GSAP 动画 (line 1604 `gsap.fromTo(pendingContent, {opacity: 0, y: 8}...)`) 跟 dizicute "极简" 哲学有微妙冲突, 但 `back.out` 极简 OK, 建议保留
- P2-5: V21_HELP tooltip 14 个字段 (line 1537-1553) 鼠标悬停 ? 显示, 极简, **保留** (符合 dizicute 信息密度哲学)

## 3. 改动清单 (按 P0/P1/P2 分组)

### 改动包 A: P0 (4 项, 必须做)

| 编号 | 改动 | 涉及行数 | 验收 |
|------|------|----------|------|
| A-1 | 自创 4 色 var → dizicute 6 色 token | 33 个引用点 | grep 全文 0 个 #FF6B6B 等 inline hex (除 token 定义) |
| A-2 | inline hex 全部替换 token | ~30 处 | grep 0 个 inline hex, 0 个 6c5ce7 / f0c040 残留 |
| A-3 | 删 7 个 emoji (⚙✨🔄🈳⚠✅🗑) | 7 行 | grep 0 个 ⚙✨🔄🈳⚠✅🗑 |
| A-4 | btn-primary hover lift 改 background 微调 | 1 处 | DevTools hover 验证无 transform |

**包 A 验收命令**:
```bash
# A-1+A-2 验证
grep -nE '#[0-9a-fA-F]{6}' src/kid_app/templates/config-badge.html | grep -v "^[0-9]*:.*--"
# 期望输出: 仅 token 定义行

# A-3 验证
grep -nE '(⚙|✨|🔄|🈳|⚠|✅|🗑)' src/kid_app/templates/config-badge.html
# 期望输出: 0 行
```

### 改动包 B: P1 (4 项, 推荐做)

| 编号 | 改动 | 涉及行数 | 验收 |
|------|------|----------|------|
| B-1 | 删死 CSS (Portal 状态卡 + 关联 HTML 注释) | 10 行 | 浏览器 DevTools 无 parse warning |
| B-2 | 重写文件头注释成 V2.1 2-tab 现状 | 14 行 | 注释跟实际实现 100% 对齐 |
| B-3 | 拆 static/badge.css (内嵌 CSS 全外移) | 800 行 | config-badge.html < 850 行, static/badge.css 独立 |
| B-4 | 6 处 inline display style → class toggle | 6 行 | grep 0 个 `style="display` 残留 |

**包 B 验收**: `wc -l config-badge.html` < 1600 (CSS 拆出后从 1610 → ~1583, JS 段 800+ 暂留 HTML), `test -f static/badge.css` 存在.

### 改动包 C: P2 (3 项, 可选做)

| 编号 | 改动 | 涉及行数 | 验收 |
|------|------|----------|------|
| C-1 | 8 字段 → 3 section (基础/解锁/展示) | 80 行 | 视觉分 3 块, 不再 8 字段 1 块 |
| C-2 | 图片来源切换时 placeholder 灰化 | 10 行 | 切"已有图片"时 textarea 半透 + 不可点 |
| C-3 | 字体 Noto Sans SC → PingFang SC | 1 行 | 浏览器 DevTools 看到 PingFang SC |

### 改动包 D: 待用户拍板 (3 项)

| 编号 | 决策点 | 选项 |
|------|--------|------|
| D-1 | 6c5ce7 (AI 按钮紫) | (a) 用 secondary 蓝灰 (b) 加 AI token 给 dizicute |
| D-2 | f0c040 (? 标记金) | (a) 用 primary 珊瑚 (b) 加 help token 给 dizicute |
| D-3 | btn-primary hover | (a) 去掉 lift, 只改 background (b) 保留 lift 但限 2px |

## 4. 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| 改色后 1-2 个组件看不下去 (e.g. success sage 改成 secondary 60% 太冷) | 中 | 改完跑 iPad Safari 真机验证 5 分钟 |
| 拆 CSS 引用顺序错 (后面引用前面) | 低 | `apply.mjs` 风格是按组件分, 同文件内顺序保留 |
| tab 切换动画 + emoji 一起改, 回归测试盲区 | 低 | 跑 `v21LoadPending()` + `v21ConfirmBadge()` + 切 tab 三步 e2e |
| 用户"按钮只放名字" 原则跟 "复制 draft_id" "复制 JSON" 冲突 | 低 | 暂不碰 (UI spec 没明令 badge 页面要走那条) |

## 5. 验收脚本 (一次性)

```bash
cd /Users/mt16/dev/dizical

# 1. dizicute 单源验证 (A-1+A-2)
test -z "$(grep -nE '#[0-9a-fA-F]{6}' src/kid_app/templates/config-badge.html | grep -v 'dizicute')" && echo "✓ 0 inline hex" || echo "✗ 仍存在 inline hex"

# 2. emoji 验证 (A-3)
test -z "$(grep -nE '(⚙|✨|🔄|🈳|⚠|✅|🗑)' src/kid_app/templates/config-badge.html)" && echo "✓ 0 emoji" || echo "✗ 仍存在 emoji"

# 3. 死 CSS 验证 (B-1)
test -z "$(grep -nE 'Portal 状态卡' src/kid_app/templates/config-badge.html)" && echo "✓ 死 CSS 已删" || echo "✗ Portal 状态卡仍存在"

# 4. 文件大小验证 (B-3)
test $(wc -l < src/kid_app/templates/config-badge.html) -lt 850 && echo "✓ < 850 行" || echo "✗ 仍 > 850 行"

# 5. 字体验证 (C-3)
grep -q "PingFang SC" src/kid_app/templates/config-badge.html && echo "✓ PingFang SC" || echo "✗ 字体未改"

# 6. 服务跑通
./scripts/stop-prod.sh && ./scripts/start-prod.sh
sleep 2
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8765/config/badge
# 期望: 200
```

## 6. 待用户拍板

1. **改动包范围**: 选 A / A+B / A+B+C / 全部? (见 §3 表格)
2. **D-1/D-2 token 决策**: 6c5ce7 紫 + f0c040 金 是 (a) 用现有色凑合, 还是 (b) 走 uiux-asset-library PR 加新 token?
3. **D-3 hover lift**: 去掉 / 保留限 2px?
4. **commit 节奏**: 1 个 PR 收尾, 还是 2 个 PR (A 一个, B+C 一个)?

拍板后开干. 0 改代码等指令.
