# dizical Sprint Decision Log (PDR)

格式: `| Date | Decision | Why |` — 供下次 agent session 快速 rehydrate。

| Date | Sprint | Decision | Why |
|------|--------|----------|-----|
| 2026-08-30 | 26083001 | 视频 COS 公开读 + UUID4 文件名 | 跟现有图片同级, 单家庭场景跟配图同级暴露可接受; 私有签名 URL 实现复杂, 不划算 |
| 2026-08-30 | 26083001 | 200MB body size 上限 | 微信视频 ≤50MB, 4× 余量; 实际 CloudRun 网关 32MB 限制, 长视频需后续 COS 预签名 |
| 2026-08-30 | 26083001 | 格式白名单 mp4 + mov (不加 webm) | webm iPhone Safari 直接黑屏; 微信/相册主出 mp4+mov |
| 2026-08-30 | 26083001 | PRD 音量控制 = 原生 `<video controls>` | iPhone/iPad Safari JS 改音量无效, 物理键是系统约定 |
| 2026-08-30 | 26083001 | 视频录入绑科目 = 上传后下拉绑定 | item 行已挤(科目/速度/分段/×), 每行塞上传 iPad mini 会换行 |
| 2026-08-30 | 26083001 | prepare 页加同期视频入口 | chip 同 modal 复用, "各端可查看"包含 prepare |
| 2026-08-30 | 26083001 | HEVC Chrome 警告, 不拒 | .mov ≠ HEVC, 拒扩展名会误杀老师 iPhone HEVC; 文案"若无法播放请用 Safari" |
| 2026-08-30 | 26083001 | video dict 结构 = 6 字段 (url/filename/item_id/item_label/size_bytes/uploaded_at) | upload_video 返回的 mime 不落 dict; 按 S1 实际实现写 |
| 2026-08-30 | 26083001 | COS 流式上传 (cos_client.upload_stream Body=file_obj) | 200MB 视频一次 read 撑爆容器; 流式防 OOM |
| 2026-08-30 | 26083001 | save_weekly_assignment 加 videos 参数 (merge 语义同 images) | 现有 PUT 是 DELETE+INSERT, 不加 videos 参数会静默清空视频 |
| 2026-08-30 | 26083001 | MySQL 迁移独立脚本 `migrate_add_videos_column.py` (支持 --mysql) | database_mysql.py 启动不走 SQLite 那套 PRAGMA 自检, 只改 SQLite 会让云端 MySQL 报 Unknown column |
| 2026-08-30 | 26083001 | item_id → item_name → item_index 三级 fallback 绑定匹配 | 现有 fuzzy match 合并 + 重排序会让单一数组下标错位 |
| 2026-08-30 | 26083001 | webkitendfullscreen handler 不调 closeVideoPreview (grok 拍板 B) | 用户退出原生全屏应回到 modal 缩略图状态, 不是看完关闭; overlay 退出后 × 仍可关 |
| 2026-08-30 | 26083001 | PooledDB ping=7 (CloudRun 容器唤醒时自动 reconnect) | 不修 → 容器被唤醒池里连接已被 NAT/超时断开, 首个请求必 2013 Lost connection 500 |
| 2026-08-30 | 26083001 | sync 脚本 EXCLUDE 加 `_worktrees` (下划线开头) | 之前只排 `.worktrees` (点号开头), 漏了下划线开头 — `_worktrees/` 1.1GB 跟着 deploy 包进 CloudRun 必 create_failed |
| 2026-08-30 | 26083001 | 音乐字符输入框统一加 font-feature-settings "calt/ccmp/mark/mkmk" | 浏览器默认不启 OpenType combining mark 堆叠, dot/low line 字符显示错位 |
| 2026-08-30 | 26083001 | 历史数据不 migrate (dad 显式要求) | 现有 _ (ASCII 下划线) 保持原样, 新输入用 combining low line (U+0332) |