# AI-PLAN — 老师要求视频上传 (sprint 26083001) v2

> 分支: `feat/teacher-requirement-video` (基于 origin/main c917b18)
> PRD: `tqob/05-Coding/project-dizical/PRDs/MRD-老师要求上传视频.md`
> 状态: **DRAFT v2 待 dad 拍板** — v1 + agy 后端评审 + grok 前端评审 合并
> 评审输入:
> - agy 后端评审: 8×P0/P1/P2/P3 + 2 盲点 (HEVC/AV1 iOS 黑屏 + 录入页已传视频 UI 缺失)
> - grok 前端评审: 5×P1/P2 + 5 盲点 (dizicute token / PUT 静默丢 videos / 历史/编辑/prepare 无入口 / COS 206 Range / webkitendfullscreen 不同步)

---

## 1. 需求拆解

| # | 需求 | 落地点 |
|---|------|--------|
| 1 | 视频可上传云服务，多端可查看 | COS (复用 `cos_client.py`) |
| 2 | 录入老师要求时可上传视频，绑某期老师要求，可选绑 item | `weekly_assignments.videos` 字段 (JSON list) |
| 3 | practice 选中 item 练习时如有视频有点击入口 + modal 播放器 | `practice.html` + `<video>` |
| 4 | **多端可查/删** (grok 盲点扩展): 历史/编辑/prepare 三处都要能看/删视频 | `loadAssignments` / `startEditAssignment` PUT / `prepare.html:690-693` |

**不做** (PRD 明确后续)：字幕识别 / STT。

---

## 2. 数据模型

### 2.1 weekly_assignments 新字段

JSON 数组，每条结构（v2 修订: 加 `item_id` 优先 + `item_name` 次选 + `item_index` 兜底）：

```json
{
  "url": "https://<bucket>.tcb.qcloud.la/videos/<uuid>.mp4",
  "filename": "<uuid>.mp4",
  "item_id": null,            // P1 agy: 优先; 录入后 bind, items 改动不失效
  "item_name": "长音练习",    // P1 agy: 次选; item_id 失效时按名匹配
  "item_index": 2,            // P1 agy: 兜底; 只用于本地缓存/历史对齐
  "size_bytes": 12345678,
  "duration_sec": null,       // loadedmetadata 回写, 不调 ffmpeg
  "uploaded_at": "2026-08-30T14:22:11",
  "mime": "video/mp4"
}
```

**绑定匹配优先级** (agy P1): `item_id` → `item_name` → `assignment-level` (无 item_id/name).

**理由**:
- 数组下标 `item_index` 在科目重排序/增删/fuzzy match 合并 (`database.py:688`) 时极易错位 → 不能作为唯一绑定锚点
- `item_id` 老数据多为 null → `item_name` 兜底
- `mime` 字段方便前端 chunk 加载策略 (mp4 vs mov metadata 不同)

### 2.2 迁移

- **SQLite (本地)**: `src/database.py` 启动 `PRAGMA table_info` 缺 `videos` 列则 `ALTER ADD TEXT NOT NULL DEFAULT '[]'`, 跟 `images` 同模式
- **MySQL (云)**: agy P1 — 新建独立迁移脚本 `src/migrate_add_videos_column.py` (支持 `--mysql`), 同时在 `schema_mysql.sql` 补充 `videos TEXT NULL`
  - 理由: `database_mysql.py` 启动不走 SQLite 那套 `_init_db` 自动 PRAGMA 检查, 只改 SQLite 会导致云端 MySQL 报 Unknown column
- **幂等**: 两边都先查列存在性再 ADD, 不存在才执行

---

## 3. API 设计

### 3.1 新端点 (v2 修订: 接受 agy P2 简化)

| Method+Path | 用途 |
|-------------|------|
| `POST /config/api/assignments/upload-video` | 上传视频 → COS, 返 `{ok, url, filename, size, mime}` |
| ~~`POST /config/api/assignments/{date}/video`~~ | **取消** — agy P2: 复用现有 POST/PUT /config/api/assignments, 前端组装进 form 提交 |
| ~~`DELETE /config/api/assignments/{date}/video/{idx}`~~ | **取消** — 同上, DELETE 由 PUT 全量替换 videos 数组完成 |

**保留理由**:
- **agy P2**: 三端点零散状态容易冲突, 一旦 PUT payload 没带 videos 字段 → 静默清空 (agy P0 已点破)
- 现有 `POST/PUT /config/api/assignments` 已经是「全量替换 items/images/notes」模型, videos 加进去对齐
- 解绑 = 编辑时把 videos 数组里那项剔除, 提交 PUT 即可

### 3.2 save_weekly_assignment 改造 (agy P0 必修)

**问题**: 现有 PUT 是 DELETE+INSERT, `save_weekly_assignment(date, items, notes, images)` 签名不接 `videos` → 每次编辑文字要求视频全丢

**修复**:
- `database.py::save_weekly_assignment` 加 `videos: Optional[List[Dict]] = None` 参数, 沿用 images 的 merge 语义 (显式传入覆盖 / 未传入保留现有)
- `database_mysql.py::save_weekly_assignment` 同改
- `config.py::api_post_assignment` / `api_put_assignment` 都从 body 解析 `videos`, 传入 save
- `_serialize_assignment` 也加 `'videos': json.loads(row['videos']) if row.get('videos') else []` (agy P1)

### 3.3 COS 上传 (agy P0 必修: 流式防 OOM)

**问题**: `cos_client.py:46 upload(filename, content: bytes, content_type)` 接收完整 bytes, 200MB 视频 `await file.read()` 全量载入 RAM → CloudRun 容器 OOM Crash

**修复**:
- 扩展 `CosUploader` 加 `upload_stream(filename, file_obj, content_type)` 方法, 内部用 `CosS3Client.put_object(Body=file_obj)` 直接传文件句柄
- `api_upload_assignment_video` 端点改用 `await file.read()` 不行 → 改 `shutil.copyfileobj(file.file, temp)` 流式落临时文件 → 调 `upload_stream`
- **本地 fallback**: `shutil.copyfileobj(file.file, dest)` 流式写盘
- **后端硬校验 (agy P2)**: 流式累计字节数, 超过 200MB 立即 `413 Payload Too Large` + 拒绝 .webm/.avi (iOS 不原生支持)

### 3.4 practice 页读视频 (agy "现有方式" 优化)

agy 发现 `app.py:2535 db.get_weekly_assignment_for_week()` 会直接把 assignment 塞入 WEEKLY_ASSIGN 模板变量：

- **方案调整**: 利用现有 WEEKLY_ASSIGN (服务端模板渲染), 直接前台读 `WEEKLY_ASSIGN.videos`
- 不新增端点, 不改 `/api/practices/{date_str}` 职责
- config.py `/practice` 路由 (src/kid_app/app.py:2528) 已传 WEEKLY_ASSIGN, 只需要 `_serialize_assignment` 加 videos 字段即可自动透传

### 3.5 鉴权 (agy ❓ 已澄清)

视频端点继承现有 `app.py:35 reviewer_write_guard`, 不需额外白名单. 微信提审员只读模式自动覆盖.

---

## 4. 前端 UX (v2 修订: grok 设计系统约束 + 历史三处补全)

### 4.1 dizicute token 约束 (grok 🚫 盲点)

**禁止**: 新 hex 颜色 / 扩散 `#8B6914` / emoji 滥用
**只用**:
- primary `#FF6B6B` (accent)
- muted `#666` (次要文字)
- radius md
- 现有 `<video>`/`<button>` 基础样式继承

### 4.2 录入页 (config-practice-log 老师要求 Tab)

grok 反馈：
- **accept 白名单**: `accept="video/mp4,video/quicktime,.mp4,.mov"`, **不要 `capture`** (否则 iPhone 直接开摄像头)
- **预览方案**: 不要 canvas 抽第一帧 (COS CORS 会污染 canvas). 用 `<video preload="metadata">` 小窗 + duration loadedmetadata 回写
- **删除按钮**: 抄配图 × 模式 (1934-1941 行)
- **本地状态**: 已上传的 URL 进 localStorage (跟 images 一样, 1193-1252 行模式); 进行中的文件无法恢复, 刷新后提示「有未完成上传」

布局 (v1 草图, v2 文案对齐 dizicute 不滥用 emoji):
```
现有行: 科目 / 要求 / 速度 / [📷 配图 ×]
新增行: 科目 / 要求 / 速度 / [📷 配图 ×] / [🎬 视频 ×]
底部:   [🎬 本期通用视频 ×]
```

上传过程 = XHR progress bar (跟配图同 pattern), `<input type="file">` 单选 (`multiple` iOS 不稳 — grok P3).

### 4.3 practice 页 (P1/P2 修正)

- **入口 chip**: 选中某 item 后, 在 requirement 文本下方显示一行 chip. **过滤** (grok P2): 仅显示"该 item (item_id/name 匹配) + 本期通用"两类视频, 不显示别的科目视频. 1 条不显示 (1), 多条才 (2)
- **modal 播放器** (v2 多处修订):
  - `<video controls preload="metadata" playsinline webkit-playsinline>`, **不要 `autoplay`**, **不要 GSAP transform** (iOS 视频变黑 — grok P2)
  - 打开后 `video.focus()` (grok P2)
  - 顶部标题 + 关闭 ×; 多视频用左右箭头 (single video 隐藏)
  - body 滚动锁 + Esc 关闭
  - 关闭后 `paused = true; src = ''` (grok 测试点)
  - 关 modal 时同步处理 `webkitendfullscreen` (用户可能点原生全屏再 ×) — 状态机统一

### 4.4 COS 配置 (grok 🚫 盲点)

- **COS 需 HTTP 206 Range 支持**: 现有公开读桶已支持 (CloudRun 默认), 但前端需要 `Range` header (浏览器自动发, 无需手写)
- **PUT Content-Type**: `video/mp4` 或 `video/quicktime`, **不要 `application/octet-stream`** (iOS 某些场景无法识别)

### 4.5 历史/编辑/prepare 三处补全 (grok P1 必修)

| 位置 | 现状 | v2 改动 |
|------|------|---------|
| `config-practice-log.html:2023` `loadAssignments` | 只渲配图 | 加 video 渲染 (缩略图 + 标题 + 删除按钮) |
| `config-practice-log.html:2107-2116` `startEditAssignment` PUT | 只发 `items+notes` | 加 `videos` 字段, 否则静默清空 |
| `prepare.html:690-693` 配图展示 | 还在 `window.open` (grok 指: 视频也用 window.open 会下载, 跟历史配图 bug 一致) | 沿用 `openImagePreview` 模式, 视频版 `openVideoPreview` |
| 编辑页 PUT 携带 videos | 缺 | 后端 PUT 端点必须从 body 解析 videos (agy P0 联动) |

### 4.6 测试覆盖 (grok + agy 合并)

**前端**:
- `<video>` 有 `playsinline` + `webkit-playsinline` 且无 `autoplay`
- 关 modal 后 `paused = true` 且 `src` 空
- Esc / 遮罩 关闭
- chip 过滤 (科目 + 本期, 不含其它科目)
- 440 / 744 / 1133 三断点布局
- 客户端拒 200MB + webm
- accept 白名单 mp4+mov
- 历史列表能渲视频
- 编辑保存不丢 videos (PUT 携带)
- 不用 `window.open` 打开视频 (沿用 `test_image_preview_modal.py` 模式)

**后端**:
- 上传失败 / 超大 (413) / 格式错 (400) / 绑定解绑 / item 删除后视频显示 (item_id→item_name fallback)
- MySQL 迁移幂等 (重复跑不报错)

---

## 5. 边界 / 风险 (v2 增订)

| 风险 | 缓解 |
|------|------|
| **OOM** (agy P0) | 流式上传, 不一次 read |
| **PUT 静默清空** (agy P0) | save_weekly_assignment 加 videos, 三处 PUT 端点都解析 |
| **item 索引错位** (agy P1) | item_id → item_name → index 三级 fallback |
| **MySQL 迁移遗漏** (agy P1) | 独立迁移脚本 + schema_mysql.sql 同步 |
| **_serialize 漏字段** (agy P1) | 集中改一处 |
| **HEVC/AV1 iOS Safari 黑屏** (agy 盲点) | 上传提示"推荐系统相册录制 / H.264", HEVC .mov 在 Chrome 播放警告 |
| **历史三处无入口** (grok P1) | loadAssignments / startEditAssignment / prepare.html 三处统一加视频渲染 |
| **COS 206 Range** (grok 🚫) | 公开读桶已支持, 浏览器自动发 Range |
| **webkitendfullscreen 不同步** (grok 🚫) | modal 状态机统一 |
| **Modal GSAP transform 黑屏** (grok P2) | opacity 过渡或无动画 |
| **iPhone capture 误开摄像头** (grok P2) | accept 不要 capture |
| **iOS 音量控制受限** (PRD 要求 vs iOS 限制) | 待 dad 拍板 (grok ❓) |
| CloudRun 容器磁盘易失 | 强制走 COS |
| HEIC 教训: CloudRun Linux 无 ffmpeg | 客户端限制 mp4/mov, 不在容器内转码 |
| COS 单文件 5GB 上限 | 限制前端 200MB, 后端再校验 (413) |
| 隐私审核 | COS 公开读 (跟图片一致) |

---

## 6. 多 sprint 切分 (v2 修订: 兼顾三处入口)

dad 历史偏好: 多 sprint, 每 sprint 独立 PR。

| Sprint | 内容 | PR |
|--------|------|-----|
| **S1** | 数据迁移 (SQLite+MySQL+独立脚本) + `CosUploader.upload_stream` + `api_upload_assignment_video` + save_weekly_assignment 加 videos + _serialize 加 videos + 后端硬校验 200MB/格式 | #298 |
| **S2** | 录入页 UI (上传/预览/删除/本地状态) + 编辑页 PUT 携带 videos + prepare.html 视频渲染 (含 openVideoPreview) | #299 |
| **S3** | practice 页入口 chip (过滤逻辑) + modal 播放器 (playsinline/iOS兼容/webkitendfullscreen) + 历史列表视频渲染 + E2E 测试 | #300 |
| **S4** | CloudRun 部署 + Obsidian 文档 + 隐私审核 + 跨端验收 (iPhone/iPad/Mac/WKWebView) | — |

(由原 3 sprint 拆 4 sprint, 因 P1/P2 + 三处入口工作量翻倍)

---

## 7. 待 dad 拍板

1. **隐私/权限**: 视频走 COS 公开读 (跟图片同) vs 私有 + 临时签名 URL?
   - **推荐 A: 公开读** (跟图片一致, 实现简单)
2. **大小上限**: 200MB / 500MB / 不限?
   - **推荐 200MB** (微信视频单条一般 50MB 内, 留 4x 余量)
3. **格式白名单**: mp4 / mov / webm?
   - **推荐 mp4 + mov** (微信老师发的通常这俩; webm iOS Safari 不支持)
4. **PRD 音量控制 vs iOS 限制**: iPhone Safari 音量只能静音键控制, 无法 in-page 调音量条
   - **推荐**: 接受原生 `<video controls>` 自带控件 (Mac/Chrome/iPad 可拖音量), iPhone 用户用物理键
   - **备选**: 限定 Mac 自建音量条, 其他端走原生控件
5. **录入绑科目交互**: 每 item 行一个按钮 (v1) vs 上传后下拉绑定 (grok 推荐后者)
   - **推荐 B: 下拉绑定** (UX 更连贯, 减少每行视觉噪音)
6. **prepare 页同期入口**: 要 / 不要?
   - **推荐要** (PRD "各端可查看" 包含 prepare, 且配置完整性)
7. **微信视频 HEVC Chrome 播不了**: 上传时仅警告, 还是服务端拒绝?
   - **推荐仅警告** (iPhone Safari/WKWebView 仍能播, dad 自己用 iPad 看, Chrome 限制不致命)

---

## 8. 评审合并日志

### agy 后端评审采纳
- ✅ P0-1 流式上传 (CosUploader.upload_stream) §3.3
- ✅ P0-2 save_weekly_assignment + 三处 PUT 携带 videos §3.2
- ✅ P1-1 item_id → item_name → index 三级 fallback §2.1
- ✅ P1-2 _serialize_assignment 加 videos §3.2
- ✅ P1-3 MySQL 独立迁移脚本 + schema_mysql.sql §2.2
- ✅ P2 API 端点精简 (取消两个独立端点) §3.1
- ✅ P2 后端硬校验 200MB/格式 §3.3
- ✅ P3 不污染 practice_audit_log (修正原 plan 误写)
- ✅ 盲点-1 录入页已传视频预览/删除 UI §4.2
- ✅ 盲点-2 HEVC/AV1 iOS Safari 黑屏警告 §5

### grok 前端评审采纳
- ✅ P1-1 历史/编辑/prepare 三处补全 §4.5
- ✅ P2-1 COS 206 Range (确认已支持) §4.4
- ✅ P2-2 Modal 不要 GSAP transform + opacity/无动画 + video.focus() §4.3
- ✅ P2-3 webkitendfullscreen 状态机统一 §4.3
- ✅ P2-4 accept 白名单不要 capture §4.2
- ✅ P2-5 Chip 过滤仅当前科目+本期 §4.3
- ✅ P2-6 错误态/草稿/单一文件 §4.2
- ✅ 🚫 dizicute token 约束 (禁止新 hex) §4.1
- ✅ 🚫 PUT 静默丢 videos (联动 §3.2)
- ❓ 4 项待 dad 拍板 (音量/绑科/prepare/HEVC) §7

### 主动调整
- 🔄 S1-S3 拆 S1-S4: 因 P1/P2 工作量翻倍 + 三处入口
- 🔄 data model 加 item_id 优先: 原 v1 只用 item_index 是错的
- 🔄 practice 页取视频方案调整: 利用现有 WEEKLY_ASSIGN 模板变量, 不另开 API

---

## Changelog
- 2026-08-30 v1: 初版, 待评审
- 2026-08-30 v2: agy+grok 双线评审合并, P0×2/P1×3/P2×5/P3×1 + 5 盲点全部纳入, 拆 4 sprint
