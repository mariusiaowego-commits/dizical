---
id: 26083001
type: sprint
version: 1.0.0
start_date: 2026-08-30
end_date:
status: 待启动
priority: 高
summary: 老师要求视频上传 + practice 页 modal 播放 + 历史/编辑/prepare 三处入口
tags: [sprint, dizical]
---

# Sprint 26083001 — 老师要求视频上传

**Sprint Goal**: 让 dad 在录入老师要求时上传微信老师发的示范视频, 女儿在练习时 (以及 prepare 准备阶段) 能打开 modal 看视频示范。视频存腾讯云 COS, 多端登录用户都能播放。

**PRD 来源**: `tqob/05-Coding/project-dizical/PRDs/MRD-老师要求上传视频.md`

**PLAN**: `sprints/sprint-26083001-teacher-requirement-video/plan-teacher-requirement-video-260830.md`

## 决策记录 (从 plan 同步)

| 维度 | 决策 | 拍板人 |
|------|------|--------|
| 隐私/权限 | A 公开读 (跟图片同, UUID4 防枚举) | dad 8-30 |
| 大小上限 | 200MB | dad 8-30 |
| 格式白名单 | mp4 + mov (不加 webm) | dad 8-30 |
| PRD 音量控制 | 接受原生 `<video controls>` | dad 8-30 |
| 录入绑科目 | 上传后下拉绑定 (grok 推荐) | dad 8-30 |
| prepare 页入口 | 要, 同 modal 复用 | dad 8-30 |
| HEVC Chrome | 前端警告, 服务端不拒 | dad 8-30 |
| Sprint 切分 | S1-S4 4 sprint 独立 PR | 编排 agent |
| 分工 | agy (S1) + grok (S2+S3) + 编排 (S4) | dad 8-30 |

## Sprint 子任务

### S1 — 后端数据迁移 + 上传管线 (agy)
- [ ] `cos_client.upload_stream` 流式上传方法
- [ ] `api_upload_assignment_video` 端点 + 后端硬校验 200MB + 白名单 mp4/mov
- [ ] `save_weekly_assignment` 加 videos 参数 (双后端)
- [ ] 启动时 PRAGMA 幂等 ALTER ADD videos 列
- [ ] 独立迁移脚本 `src/migrate_add_videos_column.py` (支持 --mysql)
- [ ] `_serialize_assignment` 加 videos 字段 (避免 PUT 静默清空)
- [ ] 测试 `tests/test_upload_video_cos.py` 5 case PASS
- [ ] PR #298 创建

### S2 — 前端录入/编辑/prepare UI (grok)
- [ ] `config-practice-log.html` 视频区 (配图区下方, XHR 上传 + progress)
- [ ] accept="video/mp4,video/quicktime,.mp4,.mov" 不带 capture
- [ ] 绑定下拉: 本表 item / 本期通用
- [ ] localStorage 草稿 (跟 images 1193-1252 模式)
- [ ] beforeunload 拦截 + 重试同一文件
- [ ] `startEditAssignment` PUT body 加 videos
- [ ] `loadAssignments` 渲染历史视频
- [ ] `prepare.html` 视频 chip
- [ ] `openVideoPreview` 复用 openImagePreview modal 模式
- [ ] 测试 `tests/test_video_upload_ui.py` 7 case PASS
- [ ] PR #299 创建

### S3 — practice 页 chip + modal 播放器 (grok)
- [ ] `practice.html` chip 渲染 (选中 item 后, requirement 下方)
- [ ] chip 文案「老师示范」(4 字弱 CTA), 16px play SVG (currentColor)
- [ ] chip 过滤: item_id/name 匹配 + 本期通用 (item_id=null)
- [ ] modal `<video controls preload="metadata" playsinline webkit-playsinline>` 不 autoplay
- [ ] 不 GSAP transform, opacity 过渡
- [ ] 关闭后 paused=true; src=''
- [ ] webkitendfullscreen 状态机同步
- [ ] 440/744/1133 三断点布局测试
- [ ] `WEEKLY_ASSIGN.videos` 透传 (联动 S1)
- [ ] 测试 `tests/test_video_practice_modal.py` 6 case PASS
- [ ] PR #300 创建

### S4 — 部署 + 文档 + 验收 (我 + dad)
- [ ] CloudRun Dockerfile/cloudrun.yaml 检查 (请求超时/body size)
- [ ] 4 个端跨设备验收: iPhone Safari / iPad Safari / Mac Safari / Mac WKWebView / 小程序
- [ ] Obsidian `reference/teacher-requirement-video.md` 长期参考
- [ ] git tag v1.0.X
- [ ] Sprint closeout (3-1-1) verify-*.md

## Sprint 回顾 (完成后填)

- 预计 vs 实际:
- 学到:
- 风险点:

## Sprint 阻塞 (status: 已阻塞 时填)

- 阻塞原因:
- 解阻塞条件: