# dizical 渠道分发 (Channels)

dizical 项目的多端分发渠道, 每个目录是一个**独立可分发**的客户端。

## 当前渠道

| 渠道 | 状态 | 说明 |
|---|---|---|
| [mini-program/](./mini-program/) | Phase 0 准备中 | 微信小程序 (女儿 + 家庭用户微信打开) |
| [mac-app/](./mac-app/) | 暂未启动 | macOS 菜单栏原生 app (类似 mole) |
| web (主仓库根) | 已上线 | Python FastAPI + Jinja2 kid-app, iPad Safari 访问 |

## 共享后端

所有渠道共用一个 dizical Python 后端:
- 现有 API (~30 个 REST endpoint) 已在主仓库实现
- 各渠道通过 HTTPS 调用同一后端
- 后端部署: 你 Mac localhost:8765 (现状) → 内网穿透 (Tailscale/Cloudflare Tunnel)

## 配置隐私

每个渠道目录下 `config/` 存放:
- AppID / AppSecret (微信)
- 后端 URL
- 内网穿透 token

**`config/` 目录已被 .gitignore 排除, 不推 gh**。源代码可推, 配置本地。

## 关联

- 主仓库: `/Users/mt16/dev/dizical`
- PRD 草稿: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/tqob/05-Coding/project-dizical/distribution/wechat-miniapp-PRD.md`
