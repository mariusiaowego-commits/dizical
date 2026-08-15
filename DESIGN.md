# dizical Design Language

> dizical 是女儿的竹笛练习助手, 服务 7:15 早课 + 5/3 周末练习.
> 本文件描述 dizical kid-app (iPad + Mac webview) 的视觉设计语言.

## 来源 (Source of Truth)

本设计语言的**注册版本**保存在 `/Users/mt16/dev/designrepo/styles/dizicute/`:
- `DESIGN.md` (YAML tokens + rationale) — **机器可读, 单源权威**
- `AGENT.md` (机器合同: 组件硬规则 + WCAG 豁免说明)
- `src/` (编译产物: tailwind.theme.css, tokens.json)

本文件 (dizical 根目录) 是 dizical 项目的**本地副本 / 引用**, 跟 designrepo dizicute 同步. **如有不一致, designrepo 赢**.

## 设计语言: dizicute

### 一句话品牌

Coral-red warmth for a kid's dizi practice app — playful, supportive, never busy.

### 核心颜色 (6)

| Token | Hex | 用途 |
|---|---|---|
| `colors.primary` | `#FF6B6B` | 珊瑚红 — dizical 招牌. button / nav 选中 / icon 底色 / streak badge |
| `colors.secondary` | `#2C3E50` | 深蓝灰 — 主文字, header (h1/h2/body) |
| `colors.tertiary` | `#FFF8F0` | 暖白 — 页面背景 |
| `colors.neutral` | `#FFFFFF` | 纯白 — 卡片 / 容器 / input |
| `colors.muted` | `#666666` | 灰 — 副文字 / 未选中 nav item |
| `colors.accent` | `#FF8C5A` | 暖橙 — praise 渐变右端 (praise 页 only) |

### 字体 (4)

PingFang SC (苹方, iOS/macOS 系统自带). Web fallback: `system-ui, -apple-system, sans-serif`.

| Key | Size | Weight | Use |
|---|---|---|---|
| h1 | 24px | 700 | 页面大标题 |
| h2 | 20px | 600 | 卡片 / section header |
| body | 14px | 400 | 默认正文 |
| label | 12px | 500 | nav label / button text / tag |

### 圆角 (4)

`sm=8 / md=12 / lg=16 / full=9999`

### 间距 (5)

`sm=8 / md=16 / lg=24 / xl=32 / xxl=48`

### 组件 (7)

- `card-surface`: 白底, 24px padding, 16px 圆角
- `button-primary`: 珊瑚红, 12px padding, 16px 圆角
- `nav-item-default`: transparent, muted 文字, 48px 圆形
- `nav-item-active`: primary 底, white 文字, 48px 圆形
- `nav-icon-container`: 24×24, 8px 圆角
- `page-content`: 暖白背景, 24px padding
- `streak-badge`: 珊瑚红 pill, white 文字, 4px padding

## 不在 dizicute 范围内 (品牌资产, 独立管理)

下列资产属于 dizical **品牌资产**, 不在 dizicute token 集中. 修改需要明确指令.

- **dizical mac app 主 icon**: 桃色背景 + 女孩持笛 (珐琅 badge 风格)
- **dizical mac app 菜单栏 icon**: 3/4 侧脸粗剪影 (透明背景, template mode)
- **dizical 微信小程序 AppID/AppSecret**: 配置管理 (`channels/mini-program/config/`, chmod 600)
- **dizical 盲盒主题视觉风格 — enamel pin (强制约束)**: 所有盲盒主题 (ok_sea / rapunzel / 未来主题) 视觉风格**必须**是 enamel pin (cloisonné 掐丝 + 厚金边 + chibi Q版). 跨主题不变 (即使换 IP/角色/叙事独立, 也仍是 enamel pin); 同主题内 7 张图必须 enamel pin 一致 (不能某张偏离). 改这条需明确指令 (类似 mac app icon 待遇). 跟 alma 协作策划案时主动强调.

## 渠道 (Channels)

dizicute **服务**:
- iPhone Safari（同一份 kid-app web，phone 断点 ≤639 CSS px；iPhone 17 Pro Max = 440×956）
- iPad mini Safari（竖屏 744×1133 / 横屏 1133×744。2266×1488 是物理像素，不是 CSS）
- Mac Safari / Chrome（MacBook Pro 16" 默认 1728×1117）
- dizical mac app (SwiftUI WKWebView 嵌 dizical)

dizicute **不服务**:
- 微信小程序（独立渠道 dizical-minip，不是这套 HTML）
- 桌面端 PWA (桌面用 mac app)
- 第三方嵌入

## 硬规则 (跟 designrepo/berun/AGENT.md §4 一致)

1. **No colors outside the palette.** 扩展 palette 先, 改 dizicute DESIGN.md.
2. **All component values must be token references.** Inline hex 在 component 字段里是 spec 违规.
3. **No font family swaps.** 层级靠 weight + size, 不靠 family.
4. **No nested component variants.** `card-surface-hover` 是 sibling, 不是 child.

## WCAG 接受 trade-off

`colors.primary` (#FF6B6B) + white text ratio = **2.78**, 低于 WCAG AA (4.5). 

**接受理由**:
- dizicute 是 kid app, primary 用法是**短文字** (≤ 4 字: "准备", "练习", "成就", "报告", "配置", "表扬") 在 ≥ 14px
- 短文字 + 大字号补偿对比度
- 珊瑚红品牌色**不可谈判**

**应用限制**:
- primary fill 只用于短文字和高强调 surface
- 长文字**永远不用** primary fill
- body 文字**永远用** `colors.secondary`

## 何时更新本文件

1. designrepo dizicute 改了 → **同步本文件**
2. dizical 项目里发现新色 / 新字号 → **先回 designrepo dizicute 加 token, 再同步**
3. 不要在 dizical 项目里独立引入 hex 颜色

## 引用

- designrepo dizicute: `/Users/mt16/dev/designrepo/styles/dizicute/`
- designrepo catalog: `file:///Users/mt16/dev/designrepo/catalog/index.html`
- Google DESIGN.md 规范: https://github.com/google-labs-code/design.md
