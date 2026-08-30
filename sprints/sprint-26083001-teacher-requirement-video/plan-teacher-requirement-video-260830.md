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

## Goal

让 dad 在录入老师要求时上传微信老师发的示范视频, 女儿在练习时 (以及 prepare 准备阶段) 能打开 modal 看视频示范。视频存腾讯云 COS, 多端登录用户都能播放, 单家庭场景下 UUID 文件名防枚举即可接受 (跟现有配图同级暴露)。

**验收**:
1. 在 `config-practice-log` 老师要求 Tab 能上传 mp4/mov 视频 (≤200MB), 视频列表显示在配图区下方, 可绑定到具体 item 或留作"本期通用"
2. `weekly_assignments.videos` 字段持久化视频元数据 + COS URL, 双后端 (SQLite + Cloud MySQL) 幂等迁移
3. `practice.html` 选中 item 后, 该 item 或本期如有视频, 显示"老师示范" chip, 点击打开 modal 播放
4. `prepare.html` 本周要求展示页同步显示视频 chip (同 modal 组件)
5. 历史/编辑 (existing assignment 加载 + PUT 更新) 不丢视频, 编辑时能删除单条
6. iPhone Safari + iPad + Mac + 小程序 WKWebView 都能播, 不全屏接管

## Blocking Questions

dad 8-30 已拍板 (3 字母 A 起走):

- Q1: 隐私/权限 → **A 公开读** (跟图片同, UUID4 防枚举, 单家庭场景跟配图同级暴露)
- Q2: 大小上限 → **200MB** (微信视频一般 ≤50MB, 4× 余量)
- Q3: 格式白名单 → **mp4 + mov** (不加 webm, iPhone Safari 黑屏)
- Q4: PRD 音量控制 → **接受原生 `<video controls>`** (iPhone/iPad 物理键是系统约定, 自造音量必失效)
- Q5: 录入绑科目交互 → **上传后下拉绑定** (grok 推荐, item 行已挤, 避免每行塞上传)
- Q6: prepare 页同期入口 → **要** (chip 同 modal 复用)
- Q7: HEVC Chrome 播不了 → **前端警告, 服务端不拒** (.mov ≠ HEVC, 拒扩展名会误杀 iPhone HEVC)

## Assumptions

1. **Data**: weekly_assignments 表新增 `videos TEXT NOT NULL DEFAULT '[]'` 字段 (JSON 数组); 双后端 (SQLite + Cloud MySQL) 通过 PRAGMA / INFORMATION_SCHEMA 幂等 ALTER ADD
2. **Failure**: 上传失败 → fail loud (RuntimeError 透传 500, 跟 images COS 失败一致); 客户端可重试
3. **Boundaries**: 视频 ≤200MB (前端 + 后端双校验, 后端用 413 Payload Too Large); 白名单 mp4/mov; 拒 webm/avi/mkv
4. **State**: `videos` 字段跟 `images` 一样独立存在, 互不影响; 编辑时 PUT 不带 videos 字段 = 保留现有 videos (同 images merge 语义)
5. **Environment**: CloudRun 容器无 ffmpeg, 不在容器内转码; COS 桶 (`636c-cloud1-d4gfwyvsk1435e2e4-1454535414`) 公开读, 现成 image pipeline 同桶
6. **Scope**: S1-S4 4 sprint 切分; 不做字幕/STT (PRD 明确后续); 不做上传断点续传 (grok 评估 v1 不做)
7. **Testing**: 单测 (cos 流式 / 200MB 限制 / save videos / MySQL 迁移幂等) + 模板断言 (playsinline / chip 过滤 / accept 白名单) + dad 跨端验收 (iPhone/iPad/Mac/WKWebView)

## Plan

**Sprint 切分** (4 sprint, 每 sprint 独立 PR):

### S1 — 后端数据迁移 + 上传管线
1. **修改** `src/kid_app/cos_client.py` 加 `upload_stream(filename, file_obj, content_type)` 方法, 接 `CosS3Client.put_object(Body=file_obj)` 流式
2. **新增** `src/kid_app/routes/config.py::api_upload_assignment_video(file: UploadFile)` 端点
   - 后端硬校验 200MB (流式累计字节, 超限 413)
   - 白名单 .mp4/.mov
   - COS 可用 → `upload_stream`; 不可用 → 落本地 `data/uploads/videos/` (开发环境)
   - 返 `{ok, url, filename, size, mime}`
3. **修改** `src/database.py::save_weekly_assignment` 签名加 `videos: Optional[List[Dict]] = None`, merge 语义跟 images 一致
4. **修改** `src/database_mysql.py::save_weekly_assignment` 同上
5. **修改** `src/database.py` 启动时 `PRAGMA table_info(weekly_assignments)` 缺 `videos` 列则 ALTER ADD, 跟 images 同模式
6. **新增** `src/migrate_add_videos_column.py` 独立迁移脚本 (支持 `--mysql` 给云端跑), `schema_mysql.sql` 补充 `videos TEXT NULL`
7. **修改** `src/kid_app/routes/config.py::api_post_assignment` / `api_put_assignment` / `api_assignment_serializer` (如果有) 都解析/序列化 `videos` 字段 — **agy P0 必修**: PUT 不带 videos 会静默清空
8. **修改** `src/kid_app/routes/config.py::api_upload_assignment_image` 旁路保护: 视频端点不依赖 image 端点, 但共享 cos_uploader 单例
9. **新增测试** `tests/test_upload_video_cos.py` — 5 case: COS 成功 / 超大 413 / 格式错 400 / PUT 不带 videos 保留 / MySQL 迁移幂等

**派活**: **agy** (Gemini 3.7 Flash High, 86% weekly 富余). 跨 5+ 文件改动是 Flash 强项.

### S2 — 前端录入/编辑/prepare UI
1. **修改** `src/kid_app/templates/config-practice-log.html` 老师要求 Tab
   - 视频区 (跟配图区并列, 不是每行按钮): 上传按钮 + 已传视频列表 (缩略图 + 大小 + 绑定下拉: 本表已选 item / 本期通用) + 删除按钮
   - 上传走 XHR 流式 (progress bar), `accept="video/mp4,video/quicktime,.mp4,.mov"`, 不 `capture`
   - beforeunload 拦截 + 失败"重试同一文件" (input 不清太早)
   - localStorage 草稿 (跟 images 1193-1252 行模式)
2. **修改** `config-practice-log.html:2107-2116` `startEditAssignment` PUT body 加 `videos` 字段
3. **修改** `src/kid_app/templates/config-practice-log.html:2023` `loadAssignments` 渲染历史视频 (跟配图同模式)
4. **新增** `src/kid_app/templates/prepare.html` 视频 chip (沿用 openImagePreview 同 modal 模式, 改名 `openVideoPreview`)
5. **新增测试** `tests/test_video_upload_ui.py` — 7 case: accept 白名单 / progress 渲染 / delete UI / localStorage / PUT 携带 / 格式错误提示 / 网络失败重试

**派活**: **grok** (Grok 4.6 High). 67% 额度但明天 22:00 重置; 前端交互拍板是 grok 强项.

### S3 — practice 页 chip + modal 播放器
1. **修改** `src/kid_app/templates/practice.html` — 选中 item 后, requirement 文本下方显示 chip
   - chip 文案: 「老师示范」(4 字弱 CTA), 单条不显示 (1), 多条显示 (N)
   - 16px play 三角 SVG (currentColor), 不用 emoji
   - 样式: 描边 chip + muted #666 + radius md (dizicute 合规)
   - **过滤逻辑**: 仅显示该 item (item_id/item_name 匹配) + 本期通用 (item_id=null)
2. **新增** modal `<video controls preload="metadata" playsinline webkit-playsinline>`, **不 autoplay**
   - 顶部标题 + × 关闭; 多视频左右箭头 (single video 隐藏)
   - body 滚动锁 + Esc 关闭 + 点遮罩关闭
   - **不要 GSAP transform** (iOS 视频黑屏), opacity 过渡
   - 关闭后 `paused = true; src = ''`
   - 打开后 `video.focus()`
3. **状态机同步**: `webkitendfullscreen` 跟 overlay 状态统一 (用户点原生全屏再 × 也要清理)
4. **修改** `src/kid_app/app.py:2528` `/practice` 路由 (或 WEEKLY_ASSIGN 注入) 透传 `videos` 字段 (agy P1 联动, `_serialize_assignment` 加 videos)
5. **新增测试** `tests/test_video_practice_modal.py` — 6 case: playsinline + 无 autoplay / 关闭清理 paused+src / Esc+遮罩 / chip 过滤 / 440+744+1133 布局 / webkitendfullscreen

**派活**: **grok** (iOS Safari 状态机是 grok 绝对强项, 留给关键拍板).

### S4 — CloudRun 部署 + 文档 + 跨端验收
1. **修改** `Dockerfile` / `cloudrun.yaml` — 请求超时确认 (200MB / 4G ≈ 1-2 min, 15min 默认够), body size 限制 (CloudRun 默认 32MB 可能不够, 确认)
2. **环境变量**: COS_* 已就绪, 无新增
3. **PR** #298 (S1) → #299 (S2) → #300 (S3)
4. **Obsidian 文档**: `reference/teacher-requirement-video.md` (长期参考)
5. **跨端验收**: iPhone Safari / iPad Safari / Mac Safari / Mac WKWebView / 小程序
6. **隐私审核**: 视频跟图片同级 (公开读 + UUID4), 无新增风险

**派活**: 我 (编排) + dad (验收).

### Whole-sprint deliverables

- `tests/` 新增 3 测试文件 (S1 + S2 + S3), 全量 pytest PASS
- `git log` 4 个独立 commit (S1/S2/S3/S4), 各自 PR
- Obsidian `sprints/sprint-26083001-teacher-requirement-video/` 8 文件 (plan/prd/tech-spec/test-plan/sprint-doc/3 verify/decisions)
- `sprints/decision-log.md` 追加本 sprint 决策

**Alternative considered and rejected**:
- **A. 一次 PR 装 S1-S3**: rejected — 跨 10+ 文件, agy/grok 8-29 教训"scope 蔓延"会丢拍板, 不接受
- **B. 私有桶 + 签名 URL**: rejected — agy + grok 三方一致认为复杂度不划算, 单家庭场景公开读 + UUID4 足够
- **C. 自建音量条 / 自建播放器**: rejected — iOS Safari 物理键是系统约定, 自造必失效; PRD "一般播放功能" 原生 `<video controls>` 满足