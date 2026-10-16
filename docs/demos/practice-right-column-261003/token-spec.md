# practice 右栏 demo · Token 规格 (v2)

> 由 `gen-token-spec.py` 从 `dashboard-skin-01-v2.html` 读出真值生成，非手抄。
> 四文件（D1/D2/D3/D4 的 `-v2.html`）共享同一份 `--dash-*` 名集合（62 个），契约由 `verify-v2b.py` 校验。

## 一、浅银皮肤 `:root`（64 项）

| token | 值 | v2 |
|-------|-----|----|
| `--dash-page` | `#FFF8F0` |  |
| `--dash-shell-hi` | `#F3F4F6` |  |
| `--dash-shell-lo` | `#D5D8DE` |  |
| `--dash-shell-inset` | `rgba(44, 62, 80, 0.16)` |  |
| `--dash-shell-shadow` | `rgba(44, 62, 80, 0.18)` |  |
| `--dash-glint` | `rgba(255, 255, 255, 0.85)` |  |
| `--dash-panel` | `#1C1E21` |  |
| `--dash-panel-text` | `#F7F4EF` |  |
| `--dash-panel-dim` | `rgba(247, 244, 239, 0.62)` |  |
| `--dash-cover-line` | `rgba(255, 255, 255, 0.10)` |  |
| `--dash-coral` | `#FF6B6B` |  |
| `--dash-accent` | `#FF8C5A` |  |
| `--dash-white` | `#FFFFFF` |  |
| `--dash-ink` | `#2C3E50` |  |
| `--dash-muted` | `#666666` |  |
| `--dash-tick-future` | `rgba(247, 244, 239, 0.28)` |  |
| `--dash-tick-past` | `rgba(247, 244, 239, 0.78)` |  |
| `--dash-tick-rail` | `rgba(247, 244, 239, 0.34)` |  |
| `--dash-btn-face-hi` | `#3A3E44` |  |
| `--dash-btn-face-lo` | `#14171A` |  |
| `--dash-btn-glyph` | `#F7F4EF` |  |
| `--dash-btn-rim` | `rgba(255, 255, 255, 0.22)` |  |
| `--dash-knob-hi` | `#4A5058` |  |
| `--dash-knob-lo` | `#121417` |  |
| `--dash-mark` | `#F7F4EF` |  |
| `--dash-dot` | `rgba(255, 255, 255, 0.42)` |  |
| `--dash-dot-on` | `#FFFFFF` |  |
| `--dash-hole` | `#2C3E50` |  |
| `--dash-pill-track` | `#14171A` |  |
| `--dash-pill-idle` | `rgba(247, 244, 239, 0.55)` |  |
| `--dash-stand` | `#16191C` |  |
| `--dash-stand-text` | `#F7F4EF` |  |
| `--dash-battery` | `#7DCEA0` |  |
| `--dash-kicker` | `rgba(44, 62, 80, 0.72)` |  |
| `--dash-num` | `52px` |  |
| `--dash-beat` | `0.73s` |  |
| `--dash-notch` | `96px` |  |
| `--dash-radius` | `36px` |  |
| `--vp-w` | `1133px` |  |
| `--vp-h` | `744px` |  |
| `--dash-hole-active` | `#FF6B6B` |  |
| `--dash-tray-inset` | `rgba(44, 62, 80, 0.12)` |  |
| `--dash-key-hi` | `#FFFFFF` |  |
| `--dash-coral-soft` | `#FFA5A5` |  |
| `--dash-mic-on` | `#10B981` |  |
| `--dash-notice-bg` | `#FFF8F0` |  |
| `--dash-notice-ink` | `#9A3412` |  |
| `--dash-surface-2` | `#F4EFEB` |  |
| `--dash-surface-3` | `#E9ECEF` |  |
| `--dash-surface-soft` | `#FFFDFB` |  |
| `--dash-gold` | `#D4AF37` |  |
| `--dash-coral-solid` | `#CC3B3B` | **新增 (2026-10-09, dad 选 A)**: 珊瑚**实心底**, 专给压白字的按钮/胶囊。`--dash-coral #FF6B6B` 压白字只有 2.78:1 (不达 AA), 深一档 4.93:1 过关。点/环/光/描边仍用 `--dash-coral` 保持品牌色 |
| `--dash-accent-solid` | `#B8531F` | **新增 (2026-10-09)**: 品牌橙实心底。`--dash-accent #FF8C5A` 压白字 2.29:1 → 深一档 4.89:1 (与浅银 `--dash-accent-text` 同值) |
| `--dash-ink-a04` | `rgba(44, 62, 80, 0.04)` | 新增 |
| `--dash-ink-a12` | `rgba(44, 62, 80, 0.12)` | 新增 |
| `--dash-ink-a16` | `rgba(44, 62, 80, 0.16)` | 新增 |
| `--dash-ink-a25` | `rgba(44, 62, 80, 0.25)` | 新增 |
| `--dash-ink-a42` | `rgba(44, 62, 80, 0.42)` | 新增 |
| `--dash-coral-glow` | `rgba(255, 107, 107, 0.45)` | 新增 |
| `--dash-coral-a25` | `rgba(255, 107, 107, 0.25)` | 新增 |
| `--dash-accent-soft` | `#FFA073` | 新增 |
| `--dash-accent-wash` | `rgba(255, 140, 90, 0.08)` | 新增 |
| `--dash-accent-line` | `rgba(255, 140, 90, 0.30)` | 新增 |
| `--dash-accent-glow` | `rgba(255, 140, 90, 0.35)` | 新增 |
| `--dash-gold-a35` | `rgba(212, 175, 55, 0.35)` | 新增 |
| `--dash-gold-glow` | `rgba(255, 210, 100, 0.60)` | 新增 |

## 二、深墨皮肤 `:root[data-skin="ink"]`（覆盖 50 项）

| token | 深墨值 | 说明 |
|-------|--------|------|
| `--dash-page` | `#2C3E50` |  |
| `--dash-shell-hi` | `#5C6770` |  |
| `--dash-shell-lo` | `#3E474E` |  |
| `--dash-shell-inset` | `rgba(44, 62, 80, 0.45)` |  |
| `--dash-shell-shadow` | `rgba(44, 62, 80, 0.35)` |  |
| `--dash-glint` | `rgba(255, 255, 255, 0.28)` |  |
| `--dash-panel` | `#14181C` |  |
| `--dash-panel-text` | `#FFF8F0` |  |
| `--dash-panel-dim` | `rgba(255, 248, 240, 0.62)` |  |
| `--dash-cover-line` | `rgba(255, 255, 255, 0.10)` |  |
| `--dash-coral` | `#FF6B6B` |  |
| `--dash-accent` | `#FF8C5A` |  |
| `--dash-white` | `#FFFFFF` |  |
| `--dash-ink` | `#2C3E50` |  |
| `--dash-muted` | `#666666` |  |
| `--dash-tick-future` | `rgba(255, 248, 240, 0.28)` |  |
| `--dash-tick-past` | `rgba(255, 248, 240, 0.72)` |  |
| `--dash-tick-rail` | `rgba(255, 248, 240, 0.35)` |  |
| `--dash-btn-face-hi` | `#2A3036` |  |
| `--dash-btn-face-lo` | `#101316` |  |
| `--dash-btn-glyph` | `#FFF8F0` |  |
| `--dash-btn-rim` | `rgba(255, 255, 255, 0.18)` |  |
| `--dash-knob-hi` | `#3A4148` |  |
| `--dash-knob-lo` | `#0E1114` |  |
| `--dash-mark` | `#FFF8F0` |  |
| `--dash-dot` | `rgba(255, 248, 240, 0.38)` |  |
| `--dash-dot-on` | `#FFFFFF` |  |
| `--dash-hole` | `#2C3E50` |  |
| `--dash-pill-track` | `#1A1E22` |  |
| `--dash-pill-idle` | `rgba(255, 248, 240, 0.55)` |  |
| `--dash-stand` | `#1A1E22` |  |
| `--dash-stand-text` | `#FFF8F0` |  |
| `--dash-battery` | `#7BC96F` |  |
| `--dash-kicker` | `rgba(255, 248, 240, 0.72)` |  |
| `--dash-hole-active` | `#FF8C5A` |  |
| `--dash-tray-inset` | `rgba(0, 0, 0, 0.35)` |  |
| `--dash-key-hi` | `rgba(255, 255, 255, 0.22)` |  |
| `--dash-coral-soft` | `#FFA5A5` |  |
| `--dash-mic-on` | `#34D399` |  |
| `--dash-notice-bg` | `rgba(255, 248, 240, 0.10)` |  |
| `--dash-notice-ink` | `#FFD9A0` |  |
| `--dash-surface-2` | `#3E474E` |  |
| `--dash-surface-3` | `#4A5058` |  |
| `--dash-surface-soft` | `#1A1E22` |  |
| `--dash-gold` | `#D4AF37` |  |
| `--dash-ink-a04` | `rgba(255, 248, 240, 0.04)` | 深墨下把中性透明翻向暖白 |
| `--dash-ink-a12` | `rgba(255, 248, 240, 0.10)` | 深墨下把中性透明翻向暖白 |
| `--dash-ink-a16` | `rgba(255, 248, 240, 0.14)` | 深墨下把中性透明翻向暖白 |
| `--dash-ink-a25` | `rgba(255, 248, 240, 0.22)` | 深墨下把中性透明翻向暖白 |
| `--dash-ink-a42` | `rgba(0, 0, 0, 0.45)` | 深墨下把中性透明翻向暖白 |

未被深墨覆盖的 token 继承浅银值（品牌色 `--dash-coral` / `--dash-accent` / `--dash-gold` 及各自 alpha 阶梯，两套皮肤一致）。

## 三、审查规则（v2 起生效，脚本化）

1. **非中性色禁止字面量**：蓝灰 `rgb(44,62,80)`、`#FF6B6B` coral、`#FF8C5A` accent、`#D4AF37` gold 及其 alpha 混色，组件里一律只能 `var(--dash-*)`。
2. **中性黑/白 alpha 允许保留**：`rgba(0,0,0,α)`、`rgba(255,255,255,α)`、`#000`、`#fff` —— 属投影/内阴影/高光层级，不是颜色身份，换肤不需要改。
3. **禁止 `transition: all`**：必须列具体属性。
4. **深墨皮肤必须活体**：`:root[data-skin="ink"]` 不得被注释掉。

校验入口：`python3 verify-v2b.py`（四文件非中性色字面量 = 0 / `transition:all` = 0 / ink 活体 / 花括号平衡 / 内联 JS 过 `node --check` / 引用 token 全部有定义 / `--dash-*` 名集合四文件一致）。
