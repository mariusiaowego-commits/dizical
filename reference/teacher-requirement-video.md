---
title: 老师要求示范视频上传 (Sprint 26083001)
tags: [dizical, sprint-26083001, teacher-requirement, video, cos, reference]
source: ai-agent
updated: 2026-08-30
---

# 老师要求示范视频 — 长期参考

> 所属: dizical 竹笛课程管理 (主仓 `~/dev/dizical`)
> Sprint: [26083001](/05-Coding/project-dizical/sprints/sprint-26083001-teacher-requirement-video/sprint-26083001-teacher-requirement-video.md)
> 功能: 录入老师要求时上传微信老师发的示范视频, 女儿练习/准备时打开 modal 看示范。

## 概述

- **是什么**: `weekly_assignments` (老师要求) 增加 `videos` 字段, 支持每期课挂最多多个示范视频。
- **为什么做**: 微信老师会发示范视频给 dad, 之前只能外链/短信, 女儿练习时看不到示范。现在录入时传上去, 练习页 / prepare 页打开 modal 播放。
- **数据流**: 浏览器多端 (iPhone/iPad/Mac Safari + Mac WKWebView) → CloudRun 后端 → 腾讯云 COS (公开读)。视频只存 COS, 客户端直接播放 CDN URL, 不占容器 /tmp。
- **单家庭隐私模型**: 视频跟配图同级 — COS 桶公开读 + 文件名 UUID4 随机 (防枚举), 不开鉴权。属可接受风险 (dad 2026-08-30 拍板 A)。

## 数据模型 — weekly_assignments.videos

`videos` 是 `weekly_assignments` 表新增列, 存 JSON 数组。每项一个视频 dict:

| 字段 | 类型 | 说明 |
|------|------|------|
| `url` | string | 视频地址 (COS CDN URL 或本地回落 `/uploads/videos/...`) |
| `filename` | string | 对象键文件名 (`{uuid4.hex}{ext}`, ext ∈ `.mp4`/`.mov`) |
| `item_id` | int \| null | 绑定的科目 id; `null` = 本期通用 (本课全部 item 可见) |
| `item_label` | string | 绑定科目的显示名 (前端渲染用) |
| `size_bytes` | int | 文件字节数 (≤ 200MB) |
| `uploaded_at` | string | 上传时间 (前端 nowCstLocal, CST ISO) |

> 注: 上传端返回体还有 `mime` (`video/mp4` 或 `video/quicktime`), 但**不落 videos dict**; dict 存上表 6 列。

- **硬上限**: 单视频 ≤ 200 MB (`MAX_VIDEO_SIZE = 200 * 1024 * 1024`, 后端流式累计, 超限返 413 Payload Too Large)。
- **格式白名单**: 仅 `.mp4` + `.mov` (`_ALLOWED_VIDEO_EXTS`), 拒 `.webm/.avi/.mkv` (iOS 兼容差)。传入非法后缀直接返 400 中文提示。
- **列迁移**: 启动时 PRAGMA 幂等 `ALTER TABLE weekly_assignments ADD COLUMN videos TEXT` (SQLite) + `src/migrate_add_videos_column.py --mysql` (MySQL)。字段默认 NULL, 未写时不参与序列化。
- **PUT 防静默清空**: `_serialize_assignment` 已带 `videos` 字段; PUT 时 `videos is None` 则从既有行保留 (防 PUT 覆盖全量替换时把老视频清掉)。

## API 契约 (模块 `src/kid_app/routes/config.py`, prefix `/config`)

### 1. POST `/config/api/assignments/upload-video` — 上传 (multipart)
- `form-data: file` (视频文件)
- 校验顺序: 扩展名白名单 → 流式 1MB chunk 读 + 大小 ≤200MB → 0 字节拒收
- COS 可用 → `cos_uploader.upload_stream("videos/{uuid4}.{ext}")` 流式传 COS; 否则本地回落 `data/uploads/videos/`
- `200` → `{ok, url, filename, size, mime}`; `400` (格式/空) / `413` (超限) / `500` (COS 上传失败, fail loud)
- 安全: 文件名 UUID4 随机防枚举; 无鉴权 (同配图上传, 走现有父网关守卫)

### 2. POST `/config/api/assignments` — 保存/新建 (body 加 `videos`)
- body `videos` 为 video dict 数组; 传了就写 `save_weekly_assignment(..., videos=...)`
- 不传 `videos` → 不写 (兼容老请求)

### 3. PUT `/config/api/assignments/{lesson_date}` — 全量更新 (body 加 `videos`)
- `videos is None` → 读既有行保留, 防静默清空 (S1 联动修复)
- 传数组 → 全量替换 (items/images/notes/videos 一并)
- 前端 `startEditAssignment` 改 PUT body 带 `videos` (`config-practice-log.html:2278`)

## 前端 UX (三处入口)

### 录入/编辑页 `config-practice-log.html`
- 老师要求 Tab, 配图区下方 `assign-videos` 视频区:
  - 上传按钮 + 已传视频列表 (缩略/大小 + 绑定下拉 + 删除)
  - 绑定下拉: 本表已选 item / **本期通用** (`item_id=null`) — 上传后选绑定 (grok 推荐, 避免每行塞按钮)
  - 上传走 XHR 流式 + progress bar; `accept="video/mp4,video/quicktime,.mp4,.mov"`；**不设 `capture`**
  - localStorage 草稿 + `beforeunload` 拦截 + 重试同一文件 (跟 images 1200-1250 模式)
- 历史渲染: `loadAssignments` + `assignHistoryVideosHtml(a.videos)` 显示旧期视频

### 练习页 `practice.html`
- 选中 item 后, requirement 下方渲染色块 chip「老师示范」(4 字弱 CTA) + 16px play SVG (currentColor)
- chip 过滤: `item_id`/`item_label` 匹配当前选中 item **或** `item_id=null` (本期通用)
- 数据: `WEEKLY_ASSIGN` 服务端注入透传 `videos` (S1 联动)

### 准备页 `prepare.html`
- assignment 视频 chip, 复用同 modal (`openVideoPreview` 复用 `openImagePreview` modal 模式)

## iOS Safari 边角 (test_video_practice_modal.py 6 case)

- `<video controls preload="metadata" playsinline webkit-playsinline>` — **不 autoplay**
- **不 GSAP transform** — 用 opacity 过渡 (GSAP 动 transform 会干扰原生播放器/z-index)
- 关闭后清 `paused=true; src=''` (释放流, 防后台继续下载) + 隐藏
- `webkitendfullscreen` 状态机同步 — 用户点原生全屏再 ×, overlay 状态要跟着清理
- 三断点 440 (iPhone Safari) / 744 (iPad 竖屏) / 1133 (iPad 横屏 / Mac) 布局测试

## COS 公开读 + UUID4 防枚举安全模型

- 桶: 现有配图同桶 (`cos_client.py`, CDN 域名 `tcb.qcloud.la` 已验证 200; COS 直连域名对公开读桶 403)
- 对象键: `videos/{uuid4.hex}{ext}` — UUID4 128-bit 随机, 无 URL 泄露风险 (单家庭场景够)
- **不做** 私有桶 + 签名 URL (复杂度不划算, dad/agy/grok 三方一致 rejected)
- 容器重启不丢视频 (COS 持久化, 非 /tmp)
- HEVC (H.265) 视频 Chrome/Safari 支持差异: **前端警告, 服务端不拒** (Sprint 决策)

## 未来扩展点 (v1 未做)

- **断点续传**: 大视频 (接近 200MB) 弱网易断; v1 靠 XHR progress + 重试, 未做切片断点续传 (grok 评估 v1 不做)
- **STT/字幕**: 给视频转文字稿/字幕, 提高检索; PRD 明确后续
- **转码**: 容器无 ffmpeg, 不在容器内转码; COS 也未挂转码服务 (HEVC 兼容靠前端警告处理)

## 相关文档

- Sprint 总览: `sprints/sprint-26083001-teacher-requirement-video/sprint-26083001-teacher-requirement-video.md`
- 部署清单: `docs/cloudrun-deploy-video.md`
- 部署 skill: `hermes: dizical-cloudrun-deploy`
- 数据红线 / 收尾规范: [AGENTS.md](/05-Coding/project-dizical/AGENTS.md)