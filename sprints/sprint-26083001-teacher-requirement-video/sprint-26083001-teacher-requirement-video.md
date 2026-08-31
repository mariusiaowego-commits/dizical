---
id: 26083001
type: sprint
version: 1.0.0
start_date: 2026-08-30
end_date: 2026-08-30
status: 已完成
priority: 高
summary: 老师要求视频上传 + practice 页 modal 播放 + 历史/编辑/prepare 三处入口 + 云部署 + 音乐字符输入框渲染
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
| 大小上限 | 200MB (实际可用 ~32MB 受 CloudRun 网关限制) | dad 8-30 |
| 格式白名单 | mp4 + mov (不加 webm) | dad 8-30 |
| PRD 音量控制 | 接受原生 `<video controls>` (iOS Safari 物理键系统约定) | dad 8-30 |
| 录入绑科目 | 上传后下拉绑定 (grok 推荐) | dad 8-30 |
| prepare 页入口 | 要, 同 modal 复用 | dad 8-30 |
| HEVC Chrome | 前端警告, 服务端不拒 | dad 8-30 |
| Sprint 切分 | S1-S4 → 实际 S1-S6 (S5+S6 部署+修复追加) | 编排 agent |
| 分工 | agy (S1+S3) + grok (S2) + agy/grok关键拍板 (S3) + dizical-deepseek (S4) + 我 (S5+S6) | dad 8-30 |

## Sprint 子任务

### S1 — 后端数据迁移 + 上传管线 (agy) ✅ MERGED #298 (commit 355e83c)
- [x] `cos_client.upload_stream` 流式上传方法
- [x] `api_upload_assignment_video` 端点 + 后端硬校验 200MB + 白名单 mp4/mov
- [x] `save_weekly_assignment` 加 videos 参数 (双后端)
- [x] 启动时 PRAGMA 幂等 ALTER ADD videos 列
- [x] 独立迁移脚本 `src/migrate_add_videos_column.py` (支持 --mysql)
- [x] `_serialize_assignment` 加 videos 字段 (避免 PUT 静默清空)
- [x] 测试 `tests/test_upload_video_cos.py` 7/7 PASS (agy 自审加了 0字节 + GET videos case)
- [x] PR #298 创建并 merge (squash 7 commits)

### S2 — 前端录入/编辑/prepare UI (grok) ✅ MERGED #299 (commit f3376fb)
- [x] `config-practice-log.html` 视频区 (配图区下方, XHR 上传 + progress)
- [x] accept="video/mp4,video/quicktime,.mp4,.mov" 不带 capture
- [x] 绑定下拉: 本表 item / 本期通用
- [x] localStorage 草稿 (跟 images 1193-1252 模式)
- [x] beforeunload 拦截 + 重试同一文件
- [x] `startEditAssignment` PUT body 加 videos
- [x] `loadAssignments` 渲染历史视频
- [x] `prepare.html` 视频 chip
- [x] `openVideoPreview` 复用 openImagePreview modal 模式
- [x] 测试 `tests/test_video_upload_ui.py` 10/10 PASS
- [x] PR #299 创建并 merge (squash)
- [x] dad 8-30 浏览器验收通过 (截图确认视频区/绑定下拉/删除按钮/dizicute 设计)

### S3 — practice 页 chip + modal 播放器 (agy + grok 关键拍板) ✅ MERGED #300 (commit 796bd5b)
- [x] `practice.html` chip 渲染 (选中 item 后, requirement 下方)
- [x] chip 文案「老师示范」(4 字弱 CTA), 16px play SVG (currentColor)
- [x] chip 过滤: item_id/name 匹配 + 本期通用 (item_id=null)
- [x] modal `<video controls preload="metadata" playsinline webkit-playsinline>` 不 autoplay
- [x] 不 GSAP transform, opacity 过渡
- [x] 关闭后 paused=true; src=''
- [x] webkitendfullscreen 状态机 (grok 拍板 B: 不调 closeVideoPreview, 保留 overlay)
- [x] 440/744/1133 三断点布局测试
- [x] `WEEKLY_ASSIGN.videos` 透传 (S1+S2 已注入 payload)
- [x] 测试 `tests/test_video_practice_modal.py` 6/6 PASS
- [x] PR #300 创建并 merge (squash)

### S4 — 文档/CI/部署清单 (dizical-deepseek) ✅ MERGED #301 (commit f88297a)
- [x] CloudRun 配置校对 (Dockerfile/cloudrun.yaml/~/.dizical/.env)
- [x] body size 限制 (32MB 不够, 200MB 视频必须调, 列出 3 个解法)
- [x] Obsidian 长期参考 `reference/teacher-requirement-video.md` (双写 MD5 一致)
- [x] 部署清单 SOP `docs/cloudrun-deploy-video.md` (5 步 + 6 项验证)
- [x] closeout (3-1-1) `verify-260830.md`
- [x] pytest 全量回归 621 passed / 23 failed (跟 video 无关, main 既有)

### S5 — 云部署 + 双线 audit 修复 ✅ DEPLOYED #110 (PR #302 merge 8b280a5)
- [x] agy audit P0: PooledDB 加 `ping=7` (`src/database_mysql.py:75`) — 解决 CloudRun 容器唤醒时 MySQL 死连接 2013 500 根因
- [x] deepseek audit P0: `scripts/_sync_cloudrun_deploy.py` EXCLUDE 加 `_worktrees` — 部署包 1.3GB → 162MB (8 倍瘦身)
- [x] MCP `queryMysqlDatabase` 验 SELECT VERSION() + SHOW COLUMNS videos (列已存在)
- [x] MCP `manageCloudRun` action=deploy, targetPath=`.cloudrun-deploy-new` (RMW 保留 env)
- [x] 部署 #110 status=normal, FlowRatio=100, 镜像 `dizical-prod-110-20260830134342`
- [x] post-deploy smoke: `/health` 200 + `database:ok` + `lesson_count:28` + `/login` 200
- [x] MCP 警告: VpcConf 缺失 (MySQL 走公网 OK, 已知不阻塞)

### S6 — 音乐字符输入框渲染修复 ✅ MERGED #303 (commit f4036d8) + DEPLOYED #111
- [x] dad 8-30 反馈 `TK̇`/`K̲`/`tu3̇` 字符渲染错位 (dot 在字符右边不在头顶)
- [x] practice.html 3 处加 `font-feature-settings: "calt" 1, "ccmp" 1, "mark" 1, "mkmk" 1`
- [x] config-practice-log.html 6 处加 (4 class + 2 inline)
- [x] 现有数据不动 (dad 显式要求)
- [x] PR #303 创建并 merge (squash)
- [x] Deploy #111 status=normal, 100% 流量, 镜像 `dizical-prod-111-20260830144005`
- [x] 修复类 PR fast-path (dad 8-17 授权)

## Sprint 回顾 (完成后填)

**预计 vs 实际**:
- 预计 3-5 天 (4 sprint), 实际 ~6 小时 (8-30 单日完成全部 6 sprint + 部署上线)
- agy/grok/dizical-deepseek/我 4 agent 并行协作, dad 拍板 7 件事 + body size 限制
- 部署阶段触发 2 次 audit (agy/deepseek) 找 P0 根因 (MySQL ping=7 + _worktrees 1.1GB)
- 期间 dad 反馈"输入框字符渲染错位" 追加 S6 修复

**学到**:
- 修复类 PR 可走 fast-path (dad 8-17 授权): 一气直接 merge + deploy, 不需要建 worktree 长流程
- 双线 audit (agy + deepseek) 是关键 — 单视角会漏盲点 (MySQL ping=7 由 agy 找, _worktrees 1.1GB 由 deepseek 找)
- CloudRun VpcConf 警告可忽略 (走公网 MySQL)
- herdr 派活踩坑: agent 报告完留在 CLI 反馈 prompt 上, `0 + enter` 解锁

**风险点 (留给下 sprint)**:
- 32MB body size 限制 — 视频 >32MB 上传会被 CloudRun 网关拦, dad 接受现状 (微信视频 ≤30MB)
- 跨端验收 (iPhone/iPad/Mac/WKWebView) dad 自己走, 暂未做
- 字体 fallback 未加 (`system-ui`) — 如果 dad 浏览器 combining mark 仍不渲染, 需追加

## Sprint 阻塞 (status: 已阻塞 时填)

无。