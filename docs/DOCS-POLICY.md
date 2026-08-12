# dizical 主项目 — GitHub 仓库文档分类与隐私声明

**最后更新**: 2026-08-12
**适用**: https://github.com/mariusiaowego-commits/dizical

---

## 概览

dizical 是为女儿竹笛学习开发的私有工具。本仓库 GitHub 公开托管（OSS 习惯 + 跨设备协作），但**部分开发文档含真实数据路径、家庭信息、运维细节，不适合对外公开**。本文档说明哪些文件属于"本地 agent 协作参考"，哪些可对外。

---

## 本地参考文档（不上 GitHub）

下列文件**永远不推送 GitHub**，仅本地 agent（hermes）协作用：

| 文件 | 用途 | 为什么不上 |
|------|------|-----------|
| `STATUS.md` | 项目状态 + sprint 收尾 + 待办 | 含本地路径、生产 DB 备份路径、真实服务 PID/URL |
| `vibe-coding-log.md` | 每日开发记录 + 决策上下文 | 含 dad 真实习惯、agent 内部踩坑、prompt 调优细节 |
| `handoff-YYYY-MM-DD-*.md` | 会话交接文档 | 含未公开的产品决策、半成品方案、dad 隐私问题上下文 |
| `docs/handoff-archive/*.md` | 旧 handoff 归档 | 同上 |
| `docs/INTRODUCTION.md` | 项目起源故事 | 私人叙述 |
| `docs/OPENAI_PRO_PLAN.md` | AI 服务申请记录 | 包含申请材料草稿 |

**已配置 .gitignore**（含前缀严格匹配 + 兜底）：

```
# 根目录
/STATUS.md
/vibe-coding-log.md
STATUS.md
vibe-coding-log.md

# handoff 系列（根 + docs 子目录）
handoff-*.md
docs/handoff-*.md
docs/handoff-archive/

# 其他本地文档
docs/INTRODUCTION.md
docs/OPENAI_PRO_PLAN.md
```

---

## 上 GitHub 的文档（访客可见）

| 文件 | 用途 | 可见性 |
|------|------|--------|
| `README.md` | 项目介绍 + Quick Start | 公开 |
| `docs/CHANGELOG.md` | 版本变更日志（Keep a Changelog 风格） | 公开 |
| `docs/使用指南.md` | CLI 全命令指南 | 公开 |
| `docs/表结构.md` | SQLite schema | 公开 |
| `docs/badge-workflow.md` | Badge workflow 设计 | 公开 |
| `docs/badge-image-workflow.md` | Badge 图生图流水线 | 公开 |
| `docs/badge-prompts.md` | Badge prompt 模板库 | 公开 |
| `docs/PRIVACY.md` | 微信小程序"呦助"隐私政策（**注意：仅适用 mp 端**，不是 dizical 主项目） | 公开 |
| `docs/screenshots/*.png` | kid-app UI 截图（iPad Safari 1280×...，含练琴数据，但已是 iPad UI 渲染快照） | 公开 |

---

## 数据图片的特殊说明

`docs/screenshots/*.png` 是 kid-app iPad Safari 实际渲染快照，含：

- 练习科目名（如"单吐练习""回娘家"）
- 具体练习分钟数
- 解锁的徽章名（如"绕梁七日""情有独钟"）
- iPad 设备信息（部分截图含 Safari 头部）

**这些截图是 kid-app 真实使用数据**，但 kid-app 是私有工具不对外提供，README 用这些截图仅为文档演示。如未来要 OSS 化 kid-app 须先脱敏（科目 ID 化 / 数字遮罩 / 设备信息去除）。

---

## 跨项目协作引用

- `dizical-minip`（微信小程序"呦助"）：独立仓库，AppID 已在 `docs/PRIVACY.md` 公开
- `dizical-mac`（macOS 菜单栏 app）：私有，本地 `channels/mac-app/` 编译
- `uiux-asset-library`（dizicute 设计系统）：独立仓库，与本项目视觉对齐

---

## 隐私问题反馈

如发现本仓库任何文件含隐私信息被误推 GitHub：
- Issue: https://github.com/mariusiaowego-commits/dizical/issues
- 或直接联系 dad（项目 owner）
