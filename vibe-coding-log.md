## 2026-08-05 Sprint 09 PR-E audit 事务对齐 + dev 依赖组 (commit 75235ec, PR #224, 未 merge)

- 触发: dad "继续后面的步骤" — PR-E (P0-22) 是 Sprint 09a 剩余可做项 (PR-F 需等 bucket 名)
- **PR-E 实际改动范围 (比 handoff 估的小)**: 8 处 audit INSERT 里 6 处已在事务内 commit 前 (delete/update/save_session 双后端), 真正要改 2 处:
  - SQLite save_daily_practice: audit 从事务外独立 commit 移入事务内 → 业务失败整事务 rollback → audit 不写 (数据溯源原子性)
  - MySQL save_daily_practice: 补 2 处缺失 audit (merge 路径 + is_clear 清零路径) → 与 SQLite parity (旧实现 MySQL 完全不写 audit!)
- **基建修复**: pyproject.toml 加 [dependency-groups] dev (13 个测试依赖) + uv.lock 锁入 → `uv sync --group dev` 一次装齐. 旧: `uv run --with` 临时带 → cli_ux_review 等 8 测试因缺 uvicorn/textual collection ERROR
- **测试**: test_audit_log_transaction.py 5/5 (成功写 / 失败不写 / 无 channel 不写 / save_session / delete), 相关回归 38 passed
- **顺序污染发现** (既有历史债): badge_commit_meta_mapping / cond_text_meta_mapping / unlock_strategy 全量跑挂 (26 failed), 单独跑全绿. 用 -x 定位在 16% 处 (70 测试后), 但 8 个前置文件逐个组合都复现不了 → 未深挖, 记 issue (不阻塞 Sprint 09, 非本 PR 引入)
- **git**: commit 75235ec 已 push 到 feat/sprint-09-cloud-cutover (PR #224 更新 body), 未 merge (等 dad go)
- 收尾: vibe-coding-log insert (绝不用 write_file 覆盖, 8-05 踩坑已固化)

## 2026-08-05 Sprint 09 切云 review + 加固 (commit bcd3bc8, feat/sprint-09-cloud-cutover, 未 push)

- 触发: dad 接续 Sprint 09, 先 review plan (切换风险 / 测试完善 / MCP 连接 / 回退), 拍板"一步步做 按plan执行"
- **review 结论**: 方向对但当时 No-Go — MCP 无握手证据 / 测试基线不可信 / PR-D 真路径 skip / rollback 脚本缺闭环
- **MCP 4 步握手全过**: auth READY (AUTO_BOUND cloud1-d4gfwyvsk1435e2e4) / CloudRun dizical-prod normal (048, 需 049) / MySQL 8.0.30-cynos 连通 / SHOW TABLES 15 张全在
- **P0 发现 1**: 云端 practice_sessions **缺 version/updated_at 列** (schema 是 8-01 旧版, PR-D lazy migration 未跑过). 049 部署后首次访问会 lazy ALTER, 但 preflight 必须显式验证
- **P0 发现 2**: 8-04 练习数据**未上云** (云端 max_id=1467/max_date=08-03, 本地 1483/08-04). 切云 SOP 必须含"最后覆盖同步带 8-04 数据"再冻结写入
- **P1 安全**: scripts/dynamic_sync.py 硬编码 MySQL 生产密码 (待处理, 密码未在 chat 复述)
- **PR-D 真路径修复** (2 个真 bug): ① database.py practice_items 建表 id→item_id (建表 SQL 与真实 schema 漂移, 全新库炸 WHERE item_id=?) ② endpoint 测试注入 app.py 模块 db 属性 (app.py 顶层 from src.database import db 绑定旧实例 → readonly). 移除从未生效的 pytestmark_optimistic — handoff 误报"10 skip"实际是 8 failed/2 passed → 现在 10/10 全绿
- **PR-A web-only**: /config/api/backend GET/PUT (settings 表 backend_mode + dizical_url, PIN 保护) + config.html 后端连接卡片 + 5 测试全绿. 范围按 dad 拍板: 不碰 mac app 源
- **脚本加固**: scripts/preflight_cloud.sh (新, 6 项只读预检: 连通/表对齐/乐观锁列/schema_migrations/行数/空表, 支持 ~/.dizical/.env 或环境变量凭据) + rollback_to_local.sh 增强 (DATABASE_URL 清除 + 服务重启 + /health/ready 验证闭环)
- **基线**: 406 passed / 17 failed (全部改动前历史遗留: 8 缺 textual 依赖 + 4 badge/日期 + 3 顺序污染单跑绿 + 1 需真云 TEST_DATABASE_URL + 1 badge url) / 7 skipped
- **handoff 修正**: "PR-D 10 测试 skip" 是错的 (实际 8 failed); "rollback 脚本没写" 过时 (已存在, 本次增强)
- **MOA**: DeepSeek reference 4+ 次空响应 → dad 拍板只留 Luna (config.yaml 已改, 备份 config.yaml.bak-20260805-124738, 恢复指引留注释)
- **沉淀**: preflight-2026-08-05.md 双写主仓+tqob (md5 357b6c25 一致)
- 未 push (等 dad go): commit bcd3bc8 含 8 文件 610+/62-

## 2026-08-03 一次性徽章 雄鹰展翅 (PR #221 MERGED, main 6aec99c)

- 触发: 女儿 2026-08-03 完整背出笛子三级考级曲《萨丽哈最听毛主席的话》(文革版哈萨克族民歌, 歌词"要当雄鹰展翅飞, 不做温室一枝花"). 一次性徽章纪念突破性时刻
- dad 9 个 Q 全部拍板 (sprint workflow Phase 1): Q1 名字 雄鹰展翅 / Q2 志向升华版 description / Q3 突破/milestone / Q4 immediate + achieved_at_override='2026-08-03' / Q5 走 /badge-image skill / Q6 placeholder C 雄鹰印章 / Q7 description 简洁版 / Q8 cond_text 温暖版 / Q9 description 完整文字 简洁版
- 修复: db INSERT achievements (eagle_spread_wings, sort_order=37) + INSERT achievement_badges (url=/static/badges/eagle_spread_wings.png); PNG 落盘 1.5MB RGBA (chibi 哈萨克蓝衣辫子女孩双手举金色雄鹰悬头顶, PIL 245 + rembg U2-Net 兜底); 服务 8765 重启跑新代码; /badges API 验证 achieved=True, condition="考出时间: 2026-08-03"
- 关键发现: "萨丽哈" 同名异曲陷阱 — 至少有 3 个不同曲子 (文革版 (本次) / 塔吉克爱情悲剧《萨丽哈与萨曼》可汗女儿与牧羊少年殉情 / 笛子考级改编可能同源后者), 第一轮 research 我按塔吉克雪山瞎猜 placeholder, dad 拍板时纠正. 教训: 涉文化/历史背景徽章必须先跟 dad 确认"哪个版本", 不能瞎搜
- 测试: 不需要新单测 (immediate + override 路径 sprint 04 PR #218 已验证); 全套 pytest 14 pre-existing failed 保持原状, 0 新增 regression
- 沉淀: Obsidian sprint-05-eagle-spread-wings-2026-08-03/ 完整 6 doc (plan + sprint + prd + tech-spec + test-plan + verify) + decision-log append 7 条 PDR; 主仓 PRDs/AI-PRD-eagle-spread-wings-260803.md + docs/tech-spec-eagle-spread-wings-260803.md + docs/test-plan-eagle-spread-wings-260803.md 双写 (MD5 一致); db INSERT 不入 git (db 备份 `data/backups/dizi-pre-eagle-sprint05-20260803-173512.db`)

## 2026-08-03 /badges 5 bug 修复 + tab SVG icon (PR #218 MERGED, main c1f714e)

- dad 浏览器逐个发现 5 个 badge 问题: 加练狂魔没亮, streak_7 图 404, streak_N/recovery_N 未解锁时不知进度, /badges 应加 "考级" tab 独立 grade_1..10, seasonal 7 个 badge 全显示同一行
- 根因: `_has_double_practice` 旧 SQL `GROUP BY date HAVING cnt >= 2` 永远 False (daily_practices.date UNIQUE, 同日第二次练走 UPDATE 合并 items); streak_7 db url 指向已删的 `_v1.png`; modal 渲染 `condText` 优先 `cond`, 把用户友好的 desc 放前面覆盖了 calc 进度; `_calc_seasonal` dispatch bug — aid-specific 分支 (week_champ/full_month/top1/early_riser/total_60/threshold_map) 写在 `if seasonal_type == "monthly":` 块外永远走不到, db seasonal_type 全是 "monthly", 所以 7 个 badge 全命中月度通用 fallback
- 修复: `_double_first_achieved_at` 改读 `behavior_log` JSON 数组里的 distinct session_id (一次保存 = 一个 session), 历史首次达成 2026-07-27 (4 sessions); streak_N / recovery_N 未解锁分支 cond 加 "当前连续 X 天, 还差 N-X 天"; `_get_consecutive_streak` 算法 today 没练时 fallback 到 yesterday (让 progress 拿到实际 streak); 新 `_recovery_current_streak` helper (过滤烫伤日 2026-07-08 之后日期); modal 优先级改成 `cond > condText > desc`; `badges_page` 后端加 `display_group` 字段; streak_7 图 db url 改回 streak_7.png, 走 PIL 245 + rembg U2-Net 重生火焰主题图 (跟 streak_3/14 同一系列); `_calc_seasonal` 把 aid-specific 分支移进 monthly 块, fallback 在最后; 顺手修 pre-existing `_get_top_items` SQL alias bug (用 `dp.date` 无 alias); tab emoji 换 koboyo.com SVG (trophy/treble-clef/star, fill=currentColor)
- 测试: 26 个新测试 (double 5 + streak/recovery 8 + seasonal 6 + night_owl 兼容 7) 全过; 全套 399 passed + 14 pre-existing failed (基线一致, 与本次改动无关), 0 新增 regression
- 服务: 8765 重启跑新代码 (PID 41270)
- 沉淀: Obsidian sprint-04-badges-5fix-2026-08-03/ 完整 6 doc (sprint + prd + tech-spec + test-plan + verify + decision-log); 主仓 PRDs/AI-PRD-badges-5fix-260803.md + docs/tech-spec-badges-5fix-260803.md + docs/test-plan-badges-5fix-260803.md 双写 (MD5 一致)

## 2026-08-02 practice-log HEIC 配图预览修复 (PR #216 MERGED)

- dad 反馈: 配图(HEIC)在 Chrome 破图无法预览, 点击下载正常. 根因: 浏览器 `<img>` 不支持 HEIC 渲染 (Safari 可以)
- 修复: 上传接口对 .heic/.heif 用 macOS 内置 `sips` 转 JPEG 后返回 jpg URL (零新依赖); sips 不可用(CloudRun)或失败 → 保留原 heic (Safari 仍可预览)
- 回填: raw/ 3 个 heic 全转 jpg; row 71 (08-01 第17期) images 指向 jpg (3213×5712 有效)
- 验证: pytest 14 failed (基线一致) + 380 passed, 0 新增回归; dad 刷新确认预览正常
- 服务: 8765 重启 (PID 85572)

## 2026-08-02 practice-log 科目预填最近一次要求 (PR #214 MERGED)

- dad 需求: 录入老师要求时选中科目, 要求输入框自动预填该科目最近一次的要求
- 新接口 `GET /config/api/assignments/latest-requirements`: 每科目最近要求, 跨全部历史按 lesson_date 倒序取最新; 最新为空回退到更早的非空要求
- 前端: 选中科目且要求框为空 → 填入预设; 换科目时若文字仍是上个科目的自动预设 → 替换为新预设; 用户手动改过 → 不覆盖
- 验证: pytest 14 failed (基线一致) + 380 passed, 0 新增回归; dad 真机验收通过
- 服务: 8765 重启跑新代码 (PID 44797)

## 2026-08-02 practice-log 3 bug 修复 + 重复科目防呆 (PR #212 MERGED)

- dad 反馈 3 bug: ① 添加科目报错 `assignEntries.push is not a function` ② 上传图片报"❌ 网络错误"(heic) ③ 历史老师要求 7/26 出现两次
- 根因 1+2 (同源): `assignEntries`/`assignImages` 从未声明 → HTML id 全局污染: `<div id="assignEntries">` 变全局变量指向元素 → `.push` 报错; `assignImages` undefined → TypeError 被 catch 吞成"网络错误"(实际上传成功, raw/ 有 2 个 heic)
- 根因 3: `weekly_assignments` 表 lesson_date 无 UNIQUE 约束(旧 schema) → INSERT OR REPLACE 每次纯 INSERT → 同课二次提交产生两行 (id 69: 7项 / id 70: 8项全量)
- 修复: 声明 let 变量 ×2 + catch 显示真实错误; 改 `INSERT ... ON CONFLICT(lesson_date) DO UPDATE` + migration v2 (每日期保 MAX(id) + 建唯一索引); 线上库已迁移 (备份 backups/2026-08-02-practice-log-3bugfix/)
- 防呆(选项 A): 同科目重复添加 confirm 提示(提交会覆盖只留最后一次), 取消还原下拉
- 关键教训: ① HTML id 自动成 window 全局 → JS 变量必须显式声明 ② SQLite `INSERT OR REPLACE` 无唯一约束 = 纯插入 → 要唯一索引 + ON CONFLICT ③ WAL 模式裸 cp 备份缺 -wal → 用 `sqlite3 .backup` 才完整
- 部署: 8765 重启跑新代码 (PID 26060), 模板 Jinja2 热加载无需重启

## 2026-08-01 Sprint 26080103 收尾 · /report/stage-print iPad mini + 导出图片 + A3 横向 (main 2351ff1)

- 触发: dad 反馈 (1) iPad mini 横屏表格字太小看不清 (2) 表格限制高度内容不全 (3) 想要图片导出 (4) 实战发现 6 天表格 A4 装不下 (5) 8mm 列数字贴边没居中 (6) CDN 下载 SSL UNEXPECTED_EOF
- 5 commit 链, 都在 main:
  - b0b0634 docs: PLAN/PRD/TECH-SPEC/TEST-PLAN
  - 15f47a3 feat: iPad mini 适配 (矩阵 8pt→11pt, 取消死宽) + 导出图片工具条按钮
  - 17a10f6 docs: 任务清单 + Sprint 回顾 + PDR
  - f10d4c0 fix(v2): A3 横向 420x297mm 装 7 天 + 8mm 加粗 + max-width 32mm 换行
  - 2351ff1 fix(v2.1): 8mm 列显式居中 + CDN 下载 retry 3 次 + 显式 SSL context
- pytest 净零回归: 14 fail baseline 不变, 314 → 375 passed (+61 全过我新加的)
- TDD 抽纯函数: extract_image_source (14/14) + _download_image_with_retry (5/5)
- 关键根因: urlretrieve 缺 retry + timeout → FAL CDN 偶发 UNEXPECTED_EOF → 改 urlopen + 显式 SSL + chunk 8KB + retry 3 次 (2s/4s/8s 退避)
- 关键根因 2: 表格死宽 3.5mm 在 iPad 1133px 屏宽被压看不清 → 改 table-layout: auto + min-width 保底
- 关键根因 3: 6 天表格 A4 横向 297mm 物理装不下 → 改 A3 横向 420x297mm 装 7 天
- sprint 工作流: 完整走完 3 阶段 (Brief → PR → Closeout), 8-01 早上启动, 23:00 main 落地
- 实战教训: v1 静态测试全过, 部署到 production 才暴露 MEDIA URL 解析 + SSL EOF 真 bug → TDD 抽纯函数让 0 回归
- 部署: 8765 (Mac 本地) 跑 v2.1, production CloudRun 048 仍跑 v1 (跟 main 差 2 commit, 后续 sprint 同步)

## 2026-08-01 Sprint 1 v2 收尾 · practice-log 多 session + 字号放大 (PR #208 MERGED)

- dad 反馈 3 选: (1) 1 科目录多个练习细节 (2) BPM 数据错误 西藏舞曲 7-26 应该是 ♪=80 不是 ♩=66 (3) 应用默认按钮太麻烦
- 4 commit 链 squash merge → main a1fb1b8:
  - 89db23c v1: 选中科目后展示 session 细节 + 默认速度
  - 1defd15 fix(api): assignments/latest lesson_date 序列化 (date→str, Pydantic V2 兼容)
  - 586695c v2: 1 科目多 session 录入 + 修复 BPM 错误
  - 8f46b19 polish: v2 字号 × 1.3 + 加一次按钮样式
- 关键根因: /api/assignments/latest 遍历 DB 升序返最早一条 (6-13 ♩=66) → 改 reversed() 倒序 + 宽松匹配
- 关键根因 2: date 对象 JSON 序列化 throw → str(ld) 兜底
- dad 拍板: Q1=A 1 科目多 session / Q2=A 替换 / Q3=A 立刻填 / Q4=C 加按钮 (v2 改为自动)
- 验证: 浏览器 E2E (date / sel 11 items / subRows 1 / hint "📋 2026-07-26 ♪=80 · 上次老师要求...") + pytest 25/25
- 文档: `tqob/05-Coding/project-dizical/sprints/sprint-01-practice-log-defaults-2026-08-01/`
- 实测 v2 字段: entry.sessions[] (分钟+音符+BPM+预设+标签+内容, 选科目自动加 1 个空 session, 加一次复制上一 session tempo)
- 提交: 走 N 次 /api/log (5s dedup 兜底 + 100ms 间隔, batch API 下期 sprint)

## 2026-08-01 Phase2 research + 云直连验证 · 暂停

- PR #200 确认已 MERGED (94d5e66, 7-29) — "OPEN 待合"是过时信息
- Issue #207 开: updateReqPanel innerHTML XSS 遗留
- 双仓库 MOA research 完成 → `.hermes/plans/2026-07-31-phase2-research-reference.md` (全证据)
- **核心结论: web/mac 能用云数据库** — CloudBase MySQL 直连服务外网地址 (数据库设置 tab, 非连接管理), 7-17 迁移 792 行已实测
- dad 拍板: Q1=A 本地覆盖云 / Q2=A 幂等键 / Q3=B 拆 3 步 / Q4=A 解除红线
- 关键发现: MySQL 端读改写无锁无幂等 (唯一防线 5s 单实例 dedup); minip apiCall 8s 超时双发 → 落两条风险
- ⚠️ dad 误销毁云 MySQL 实例, 数据恢复中 → 联云暂停, handoff 详细待续
- 叫停: dad 差点切资源点计费 (连接器≠直连服务, 已说明, 未切)

## 2026-07-31 分支清理 · 收尾

- 关闭 PR #181 (修复已在 main by #180/#182/#179)
- 删除 18 个 merged 远程分支 (13 直接删 + 4 被 GH 自动清理 + 1 PR-已关)
- 保留 5 个 (p4-phase2-web-mac-to-cloud / practice-session-detail / mysql-merge-conflict / practice-group-same-item-name / p4-phase1b-staging)
- 现状: 远程分支 22 → 6, 干净了
- 方法: `git push origin --delete <b>` + `git remote prune origin`
- 证据表全 ahead=0 已并 main / ahead=1 全有 PR MERGED
- STATUS.md 顶部加 2026-07-31 分支清理段
- 保留 5 个 untracked dad 工作笔记 (.hermes/plans/, .hermes/practice-moa-review.md, PRDs/AI-PRD-纰漏修复-260729.md)

## 2026-07-30 stage-print 打印单页 · 收尾

- PR #204 merge: 打印强制 1 页 A4（修 PDF 预览 2 页空表头）
- PR #203 已 merge: Stage session 打印页全功能
- main @ 4864cb1 · 入口 `/report/stage-print`

## 2026-07-30 Stage session 打印页 · 收尾

- PR #203 merge: Stage 明细打印 + 分组/表格矩阵 + 练习日勾选
- 入口: `/report/stage-print` · API stages / stage-detail (🟡)
- plan: `PRDs/AI-PLAN-stage-session-print-260730.md` 双写 done

## 2026-07-30 Stage session 打印页

- 分支: `feat/stage-session-print-report`
- API: `/api/practices/stages` + `stage-detail`；页: `/report/stage-print` A4 单页
- 分组: 日→科目→session；老师要求全文独立卡片；可查历史 stage
- plan: `PRDs/AI-PLAN-stage-session-print-260730.md` 双写

## 2026-07-30 report 练习明细

- 分支: `feat/report-session-detail`
- report 页: 日历 dayDetail + 竹笛 modal 展示 practice_sessions 明细（按科目分组）
- plan: `PRDs/AI-PLAN-report-session-detail-260730.md` + Obsidian 双写
- API 无变更（已有 sessions[]）

## [2026-07-29] PR #200 V4 tile 修复: dashboard 老师要求 + wheel 去 desc + sp-tempo-row 拆 2 行

**触发**: dad "开分支修 practice 上的问题" — 4 个 UI/逻辑问题一次性拍板

**dad 拍板**:
1. 拆 2 个 commit (逻辑自洽)
2. wheel 宽度 = `.activity-wheel` 容器 (180→80px)
3. dashboard 老师要求**不限高** (卡片自然变高)
4. 媒体查询临界 800px (我决定)

**4 个问题**:
1. **dci-assign 老师要求为空** (dashboard 卡片第三列): HTML 元素存在但 JS 0 处写 `dciAssignText`. `data-req` 已在 server 端 (app.py:1688) 注入, `updateReqPanel(btn)` 用, dashboard 没用. 修法: `updateDashboard(reqText)` 接受参数, `selectItem` 传 `reqText` (源: `btn.getAttribute('data-req')`), textContent 写入
2. **sp-tempo-row 拥挤 / iPad 不友好**: 6 元素 nowrap + iPad 1024 横屏 session-panel ~600px 放不下. 修法: 拆 `sp-tempo-row-1` (核心控制) + `sp-tempo-row-2` (hint/presets) 两行 + `@media (max-width: 800px)` 缩 BPM 步进 36→32px
3. **dash-card-inline 字体倒挂 + 老师要求空**: 修法与 #1 同. 字体同时: `dci-assign-label` 11→13px, `dci-assign-text` 12→13px + `white-space: pre-wrap` 保留换行
4. **wheel-desc 占地方**: 删 `.wheel-desc` CSS + HTML render, `.activity-wheel` 180→80px, `.wheel-right` 加 `margin: 0 auto` 让 pill 居中

**关键发现 (实测)**: commit 1 单独跑时序问题:
- `updateDashboard()` 无参调用 6 处 (BPM/content 变化触发) 会清空老师要求
- 模块级 `_lastReqText` 保留, 无参调用不重置 — 已修
- 验证: BPM 92→94 步进 2 次, 老师要求保持 ✓

**2 commit**:
- `79544a3` `feat(practice): dashboard 老师要求字段填充 + 字体协调` (+13/-5)
- `3c5a410` `refactor(practice): V4 tile 布局重排 — wheel 去 desc + sp-tempo-row 拆 2 行 (iPad 友好)` (+24/-27)

**分支**: `fix/practice-v4-timer-req-tile-20260729` → PR #200 (https://github.com/mariusiaowego-commits/dizical/pull/200)

**验证**:
- pytest 新文件 6 个: 27 passed / 6 skipped
- pytest 全套: 13 failed / 338 passed / 7 skipped — 与 main baseline 完全一致, 0 新增回归
- HTTP: /practice 200 + 152KB + 所有 commit 标记齐全
- DevTools 真机 (4 项全过):
  - 选"萨丽哈" → dashboard 完整 3 行 requirements 显示
  - 选"考试" (无 req) → dashboard "—"
  - BPM 92→94 → 老师要求保持
  - 切"快速补录" tab → wheel 变窄无 desc, session-panel 紧凑

**未做 (待 dad 拍板)**:
- dad 真机 iPad mini 1024×768 验证 (我只有 DevTools 模拟)
- `updateReqPanel` 内仍用 `innerHTML` 拼字符串 (旧 XSS 隐患, 不在本 PR 范围, 单独工单)

**沉淀**:
- 模块级状态变量 (let _lastReqText = '') 是处理 "无参调用不重置某字段" 的 JS 模式, 比每个调用点显式传参更鲁棒
- Dad 拍板 4 选项 (Q1=拆 2 commit / Q2=wheel 宽度 / Q3=不限高 / Q4=我决定 800px) — 严格执行, 无追加
- waza-check 不发现的 bug: commit 1 单独验通过, commit 2 真实运行时序暴露 6 处无参调用清空问题. **逐 commit 视觉验真 + 步进多次验证** 是发现此类问题的关键
- dad 拍"不限高"决策正确: 长 requirements (萨丽哈 60+ 字) 让 dashboard 卡片变高, 远比 80px max-height 滚动条自然

**Plan 文档** (双写, md5 一致 `f80b046b06ebb456f2ec32af048b490b`):
- 主仓: `.hermes/plans/2026-07-29_practice-v4-timer-req-tile.md`
- Obsidian: `tqob/05-Coding/project-dizical/PRDs/AI-PRD-练习修复-v4-tile-260729.md`

---

## [2026-07-29] PR-A/B/C/D + 架构修复: 部署 + 合并到 main

**范围**: 后端 + Web 5 回归修复 + 3 架构修复 (waza-check 发现)

**PR #198 (4 commit squashed)**:
1. **MySQL session CRUD 补齐**: create/update/delete_practice_session MySQL 端整事务版本
2. **behavior_log dedup**: session 路径移除外层 append, 消除双写
3. **Pydantic 校验**: PracticeLogRequest 422 + 详细 details
4. **BaseBackend ABC**: 抽象基类独立模块, 防 7-28 再发生
5. **Web 4 修复**: practice_at 补全; 归档科目 V4 状态机; isToday CST; XSS createElement+textContent
6. **5s dedup**: 同 (item_id, minutes) 5s 内返缓存

**PR #199 (架构修复 3 项)**:
1. dedup key 加 date → (date, item_id, minutes) — 防跨天重放
2. MySQL _validate_session_fields 用类常量 (删重复 _CONTENT_MAX_LEN)
3. MySQL 3 新方法加类型注解

**分支**: fix/practice-pr-a → PR #198 → main; fix/architecture-fixes → PR #199 → main
**最终 commit**: main @ 30a58d3
**pytest**: 39/39 PASS (12 baseline + 9 schemas + 5 base + 4 api_log + 9 dedup)
**服务**: 8765 跑新代码, 8 项真实 HTTP 验证全过

**沉淀**:
- waza-check 发现的 3 个架构问题: 常量重复 / dedup key 无 date / 缺类型注解
- 7-28 教训 (续): ABC + Pydantic 双重防线, 但真正修法是 reviewer 发现
- GitHub API EOF / 网络不稳: 用 curl REST API 绕过 gh CLI GraphQL, 成功 merge

---

## [2026-07-29] Fix: BPM步进1 + 内容必填 + 今日记录改版

**范围**: BPM步进精度 / 内容必填双重校验 / today-records展示改版

**修复**:
1. **BPM步进器**: 步进5→1，移除吸附逻辑(80/90/100/120)，92等中间值可调
2. **练习内容必填**: submitPractice/addExtraFromPicker前端拦截+后端_validate_session_fields非空校验+API路由validate+补录按钮联动
3. **今日记录改版**: sessions优先展示(分组+明细); 旧记录items转伪session统一格式; 编辑/删除仅今日有效; 补录内容标签后联动按钮状态

**分支**: fix/practice-bugs-20260729

---

## [2026-07-28] Practice V3.1 UI — 卡片合并 + BPM 步进 + content_options 配置

**范围**: practice 页效率升级 + config 配置入口

**做了**:
1. item-section 与老师要求合并，2:8 布局 + SoftPill 重选
2. BPM 步进器（不弹键盘），session 默认值仍走 latest/session→assignment→♪80
3. practice_items.content_options + config「内容」编辑 + 练习页标签
4. 恢复 wheel|knob 左右；补录独立；旋钮吸附 5/10/15/20/25/30
5. 文档双写 PRD/tech-spec/API-CHANGELOG

**配置**: `/config/practice` → 点「内容」→ 每行一个 → 保存

**分支**: feat/practice-v3.1-ui

---

## [2026-07-27] PR #178/#180/#182 收尾 - 今日总时长显眼卡片 + 同 item_name 合并 + MySQL conflict 清理 (已 merge main @ 5a9297b)

**dad 反馈 4 轮澄清** (21:30-22:30):
1. "你在练习里截图的, 今天 27 日不是联系了 60 分钟吗" → dad 误信截图 60, 实是 UI 渲染 bug
2. "萨丽哈明显是 2 个 11 分钟, 而且两次练习的细节是不同的" → 误以为两次各 11min
3. "萨丽哈是 5+6 一共 11 分钟, 一共 49 分钟" → 确认 49 是真, 60 是截图渲染重复算萨丽哈
4. "2 个萨丽哈应该按科目合并在一起, 一个萨丽哈科目, 下面 2 次练习" → PR #180 算法修

**完成 4 件事** (本会话):

1. **7-27 data fix** (手工修 DB, 写 audit_log 留痕):
   - daily_practices.items[吸气长音].minutes 40→10
   - daily_practices.items[单吐tuku].minutes 8→6
   - daily_practices.total_minutes 81→49 (sessions SUM 一致)
   - 备份: `data/backups/dizi-pre-fix-81to49-20260727-213631.db` (602K)
   - audit_log manual_fix entry: method=reset_to_sessions_sum, 含 input/result 完整快照

2. **PR #178** (commit 13df74d) — 今日总时长显眼卡片 (.today-summary-bar):
   - HTML: 今日练习记录卡片顶部加显眼总时长 (44px Georgia 大字, 珊瑚红渐变背景)
   - CSS: 14px 圆角 + box-shadow + 移动端 media query (<600px 自动缩字号)
   - JS: renderTodayRecords 同步填值, sessions 是唯一真相源
   - 单文件 +56/-0 纯加法, 不破坏 main 6c8ec0d 算法
   - **保留 main 的 subjectTotals dict 算法** (PR #176 已修)

3. **PR #180** (commit 7a88ea2) — 同 item_name session 合并到 1 个 group:
   - 旧算法 `if (s.item_name !== lastItem)` 按 sessions 顺序切多个 group header, 同 item 被穿插切成 2 段
   - 新算法 `groupOrder + groups dict`: 同 item_name 即使被穿插也合并成 1 个 group
   - 萨丽哈: 2 个 group (11+11) → 1 个 group (11 分钟, 下面 2 行 session: 5min + 6min)
   - 单文件 +16/-8 纯逻辑调整
   - session 内容 fallback `'未填写练习内容'` (跟 PRD §US-2 一致)

4. **PR #182** (commit 5a9297b, dizical-agent 写) — 清理 main 上 database_mysql.py git merge conflict marker:
   - main squash merge 时引入 `<<<<<<< Updated upstream` / `>>>>>>> Stashed changes`, Python import 时 SyntaxError
   - 重写 save_daily_practice: 去掉冲突标记, 保留 UPDATE 路径 (避免 REPLACE INTO 覆盖累积)
   - 新增 tests/test_save_daily_practice_mysql.py: 7 场景 pytest PASS (subprocess 隔离)
   - 本会话没动这个 fix (dizical-agent 提前 push), 我做的是 merge 到 main + 主仓 sync

**关键沉淀** (skill 候选):
- "group header 渲染读 daily.items 残量" 是 V3 session 路径的隐性风险, PR #176 修了 subjectTotals dict 但没修 group header 算法
- PR #176 (6c8ec0d) 引入 `if lastItem` 算法会按 sessions 顺序切多个 group header, 同 item 被穿插切成 2 段
- 修复必须用 dict+order 算法 (PR #180 方案), 不能用相邻比较
- extra 路径走 save_daily_practice 写 daily.items 时, V3 session 路径叠加不会重置, 残量永远清不掉 (V2 范围)
- 截图误读是 dad 决策风险: UI 渲染 bug 让 dad 误以为 "60 是对的" → 多次 clarify 才纠正
- 教训: 遇到数字对不上时, 先验截图渲染 + 数据源双重, 不直接采信任一方
- "你来判断" 配合 clarify 4 选项时, dad 拍板后必须复核, 防误读
- squash merge 在 main 上引入 conflict marker 是真坑, Python SyntaxError 整个后端不可用
- dizical-agent 并行在跑, 必须先 fetch 看哪些 commit 已落地, 避免重复 push

**下一步** (V2 范围, dad 拍板后做):
- 7-27 之前所有 daily 行有 extra 残量的, 跑迁移脚本重算
- save_practice_session_and_daily_summary 改为 "item.minutes = SUM(sessions) WHERE item_id" (不是累加)
- extra 路径改为写 is_extra sessions (不污染 daily.items)
- panel 拆分 / 速度默认 / content 默认库 (本次 V1 未做)

---

## [2026-07-17] 微信小程序提审准备 + verify-pin 严格 + web/mac 切云 PRD

**commit**: 00a7e97 (验证模式 revert), 02cf4d6 (密码修复, 未 push)

**dad 拍板 4 个决策**:
1. 旧 MySQL 密码: 不管 (旧账号废了)
2. 小程序用户: 白名单 = [dad] 单人
3. 数据策略: 双 1 套数据 + 临时沙盒 (小程序单独云 / web-mac 仍本地)
4. 退出沙盒: 小程序正式上线前删云重复制

**完成 7 项**:
- A2 verify-pin 严格模式 (HTTP 403 + daemon whitelist)
- A3 PRIVACY.md (3029 字节) + 服务说明 (3319 字节) 提审附件
- A4 mp-weixin build (448KB, 65 文件)
- A5 5 步上传指南 (Obsidian PRDs)
- A6 云端 deploy (DeployId 003, 3 测试过)
- B1 web/mac 切云 4 阶段 PRD (Obsidian)
- C 数据策略红线 (AGENTS.md)

**3 测试全过** (verify-pin 严格模式):
- 真 openid + 0905 → 200 ok=dad
- fake openid + 0905 → 403 not_in_whitelist
- dad openid + 9999 → 401 wrong_pin (证明白名单先于 PIN)

**pytest 净回归 0**: 13 failed / 294 passed (pre-existing baseline 不动)

**MCP subagent auth 偶发失忆教训**: 第 1 次 subagent 没拿到 device code 状态, 重发了新的; 实际部署已完成. 主对话直接 curl 验证比 subagent 可靠.

**待办 (明天 dad 第一件事)**:
- git push origin feat/p4-phase1b-staging
- 微信开发者工具走 5 步 (Obsidian PRDs)
- 等审核 1-3 工作日

**关联文档**:
- `handoff-2026-07-17-p4-tishen-prepare.md` (11K)
- Obsidian AI-PRD-小程序微信提审-260717.md
- Obsidian AI-PRD-前后端统一云-260717.md



---

# vibe coding log - dizical

## 2026-07-14 PR #161 — 3 个 recovery_first_practice (7/14/21 天) 徽章上线 + calc

**触发**: dad "config 里 badge 徽章制作中有一个待上线的badge 无法上线 recovery_first_practice"

**根因排查**:
- `src/kid_app/badge_draft.py:41` `DRAFT_ID_RE = r"^\d{4}-\d{2}-\d{2}_[a-zA-Z0-9_-]+_[a-z0-9]{6,}$"` 要求尾部 hash ≥6 字符
- 但 `data/lib/badge_data/2026-06-30_recovery_first_practice_001.json` 是 6/30 skill 跑完后手填的 draft_id, 尾部 `_001` 只有 3 字符
- `get_draft()` (badge_draft.py:170) regex 不匹配 → 直接 return None → commit 端点返 "draft 不存在"

**修法选择** (dad 拍板 "我自己手动重启" 偏好 → 推荐最便宜):
- ✅ 选 1: 不改代码, mv draft JSON 凑齐 6 字符 (`001` → `001abc`), commit 接口走完, 删 stale 副本
- ❌ 改 DRAFT_ID_RE 放宽到 `{3,}` (改 1 行, 但未来短 hash 也通过, 语义偏弱)

**commit handler 隐式设计** (踩坑沉淀):
- `badge_workflow.py:273` `_bd.save_draft(draft)` 写回文件名用 `draft.draft_id` json 内字段, 不是 URL draft_id
- mv 出去的 `001abc.json` → commit 内部读 BadgeDraft 内存对象 (draft_id=001) → 写回到 `001.json`
- stale `001abc.json` (commit 没改它) 在 discoveries 接口里还出现一次, 手动 `rm` 清掉

**第一轮视觉问题 (dad "左右两侧被截断")**:
- vision 看原图: 1024×1024 几乎填满画布, 主体居中但四周透明留白太少
- 修法: PIL 加 15% 透明 padding → 1330×1330 (主体缩到原 70% 区域, 四边各 15% 透明)
- vision 验 "完整无截断, 描边完整, 留白舒服"

**第二轮视觉问题 (dad "图还是不对, 是图本身被切")**:
- 像素级诊断 (numpy): v4 主体 bbox 0-1023, 100% 行横向贴边
- v5 试跑: prompt 加 "centered + 18% transparent margin + gold border 5-8% breathing room" 约束
- 像素测量: v5 主体 bbox 仍 0-1023, 51% 行贴边 (比 v4 略好但四边都贴)
- vision 看 v5: "上方边缘: 笛子顶端接近金色边框留白极少, 下方: 祥云紧贴下边框, 左右: 适中留白"
- **结论**: gpt-image-2 不理 "margin" 指令, prompt 工程修不了
- **回滚**: 从 backup 恢复 v4 padded + DB 三表, 删 v5 临时

**dad 决策转换 (这一轮最关键的 insight)**:
- dad "v5 试跑和 v6 我都满意" → 不是要 v5 重做, **是想要分多版本徽章**!
- dad "做同一个徽章的2个版本, 解锁cond分别是: 病愈后坚持练习7天, 病愈后坚持练习14天"
- v4 + 15% padding → 7 天 (v4 复用)
- v5 → 14 天
- **后续加 v6 → 7 天 (替换 v4), v5 保留 14 天** (dad 反馈"7天那个图不对, 应该用 v6_view.png")
- **关键**: v6 + v5 是 dad 视觉满意的两张不同图, 不是失败品

**第三轮 - 烫伤语义 (dad 拍板)**:
- "这次生病主要是手烫伤了, 烫伤日是 7月8日"
- "烫伤是左手小臂上 脸大小一块"
- calc 设计: 烫伤后连续练 7/14 天解锁
- 图加烫伤细节: dad "我没看到你心型绷带在手臂上嘛" → 重跑 v7-1 加 "left forearm bandaged with pink heart-shaped pad"
- v7-1 视觉: 绷带显眼, sparkles 表达愈合, enamel pin 风格保留

**第四轮 - 21 天徽章 + 故事化叙事 (dad 拍板)**:
- "这个就作为 21 天的吧 新增一个这样的 badge"
- "然后这三个伤愈后的 story 改成带伤吹笛, 所有相关信息和背景故事等都要改一下"
- 新增 21 天徽章, v7-1 图给 21 天
- 3 个徽章文案统一改"带伤吹笛" 3 阶段叙事:
  - 7 天: 绷带 + 妈妈软套 + 疼但坚持
  - 14 天: 绷带在, sparkles 多, 逐指按孔
  - 21 天: 绷带摘, 露出新皮, 完整吹曲

**calc 设计**:
- helper `_recovery_first_achieved_at(conn, injury_date, n)` (抄 `_streak_first_achieved_at`, 加 `WHERE date >= injury_date`)
- `_calc_milestone` 加 3 条分支, n 解析用 `int(aid.rsplit("_", 1)[-1])` 通用化
- injury_date 写死 "2026-07-08" (2026-07-14 拍板)

**做的具体动作 (本会话完整流程)**:
1. `mv draft JSON` + `cp tmp 图` + `curl commit` → recovery_first_practice 上线
2. PIL 15% padding → v4 padded
3. v5 试跑失败 → 回滚
4. 创建 _7/_14 草稿, 用 v4/v5 走 commit
5. dad 反馈 7 天图错 (v4), 删 v4 padded + 换 v6 (备份保留)
6. 写 calc helper + 7/14 分支
7. dad 加 21 天 + 烫伤故事 → v7-1 重生 + 21 天 draft + commit
8. SQL 更新 3 个徽章的 cond_text + description (zh_story)
9. calc 加 21 天分支 (用通用 n 解析)
10. git commit + push + PR #161 + merge

**dad "vision 坏了" 误判 + 教训**:
- vision_analyze 3 次连续 SSL EOF → 报 "vision 坏了"
- dad "vision 我看可以的啊是 gemini" → 走 hermes 通道间歇故障, 跟 dad 本地 gemini 不同通道
- 教训: 3 次连续错才视为真坏, 立刻报"坏了"是误诊
- 沉淀到 memory ⑳

**git 收尾**:
- feat/recovery-first-practice-badge-pad (3 commits: d43a617, 1fc359f, b13ded9)
- PR #161 created + MERGED 2026-07-14T12:17:55Z
- main = ea3b44b

**pytest**:
- 13 failed / 294 passed
- 净回归 = 0 (跟 PR #159 merge baseline 一致)
- 11/11 achievement/recovery/calc/streak 命名匹配测试通过

**未做 (待 dad 拍板)**:
- ❌ 7/14 天图 vs 21 天图视觉不一致 (dad 拍"图不变")
- ❌ 7/8 写死 - 后续事故需新 aid + 新 injury_date
- ❌ `DRAFT_ID_RE` 改 `{3,}` (下次手填 draft_id 会再踩)

**状态**: PR #161 MERGED, 3 个徽章殿堂可见 (locked), 当前 5 天连练数据, 差 2 天才 7 天徽章. 7/15-7/16 连续练 → 7 天徽章解锁; 7/22 → 14 天; 8/5 → 21 天.

## 2026-07-13 PR #159 metronome 全链路支持

**触发**: dad "采茶扑蝶的速度要求怎没有 速度是不是单独有一个字段？" → 发现 UI 不渲染 metronome 字段, 后端静默丢弃, DB 历史 24 条 metronome 字段为空

**问题排查**:
- 早期 (2025-11 ~ 2026-03-07) 老 schema 没 metronome 字段, items 名是 "要求/作业/大课" 等非曲目
- 2026-03-14 之后 stage_order 有值的 13 周, 速度都塞在 requirements 文本里 ("♩=66练习..." 这种)
- 从 #20 2026-05-16 录入时 (用户主动设计) 才把 metronome 拆成独立字段
- UI 渲染 + 后端保存两条线都漏: `config-practice-log.html:1037-1046/1112-1116/1221-1230` 不读 metronome, `config.py:850-855/899-904` 不取 metronome

**改前流程** (用户强约束):
- handoff-2026-07-13.md 列问题 + 等 dad 拍板
- dad "可以改动了 abc" → 走 A+B+C 一起
- B1 24 条逐条列"原文 + 正则提取 + 我的拼接 + 按语义合并备选", 让 dad 5 个边界情况都拍"按语义合并"
- dad "前端可以看到所有速度和原文, 而且我可以编辑" → requirements 文本不删, metronome 字段只填"提取/补全"
- 一边干一边 verify, 5 步 verify 全过才进下一步

**DB 改动** (单独 SQL, 不进 commit):
- #26 2026-07-12 stage_order 13→14, stage_start 7-12→7-13, stage_end 7-18→7-19 (stage_order 重复 bug)
- B1 24 条 metronome 字段回填 (按语义合并):
  - 单吐练习 (2026-03-14) '♩=52一行...2小节为单位、♩=52、56、60' → '♩=52、56、60'
  - 西藏舞曲 (2026-07-04) '♩=76；...♩=60、66' → '♩=76 / ♩=60-66'
  - 西藏舞曲 (2026-07-12) '4/4 ♪=80... 2/4 ♪=69~80' → '4/4 ♪=80, 2/4 ♪=69-80'
  - 萨丽哈 (2026-07-12) '♪=88～92 出现 2 次' → '♪=88～92' (去重)
  - 采茶扑蝶 (2026-07-12) '♩=108、♩=112' → '♩=108、112' (合并顿号)
- 备份: `/tmp/weekly_assignments_backup_2026-07-13.json` (26 条全表) + `/tmp/dizi.db.bak.before-2026-07-12-fix` (整库)
- 事务包裹: `BEGIN` → 全跑完 → verify → `COMMIT` (per dad 拍板)
- 全表分布: 49 metronome 已填 / 34 空 (34 = B4 类 14 条 + 早期 stage_order=NULL 20 条)

**UI 改动** (config.py 2 处 + config-practice-log.html 4 处):
- `config.py:850-855` POST 接口 formatted items 多带 `metronome` 字段
- `config.py:899-904` PUT 接口 formatted items 多带 `metronome` 字段
- `config-practice-log.html:902-905` POST 录入表单 renderAssignEntries: 加 `<input class='metronome-input' placeholder='速度 e.g. ♩=82'>`
- `config-practice-log.html:918-923` POST 录入表单: change 事件写 `assignEntries[idx].metronome`
- `config-practice-log.html:933-936` addAssignEntryBtn: assignEntries.push 加 `metronome: ''`
- `config-practice-log.html:995-998` submitAssignBtn: body.items 多带 `metronome: e.metronome`
- `config-practice-log.html:1037-1046` 历史列表 loadAssignments: 珊瑚红 pill 渲染 `it.metronome` (空不渲染)
- `config-practice-log.html:1112-1116` 编辑模式: input 加 `class='edit-item-metro'`
- `config-practice-log.html:1131-1134` 编辑模式保存: items 多带 `metronome: row.querySelector('.edit-item-metro').value`
- `config-practice-log.html:1221-1230` 本周总览 loadWeek: 同样渲染 metronome pill

**坑**:
- stage_order 计算脚本上次 (6-20 案) 命中 "追加前先比对 byte-identical" 规则, 这次 #26 撞 stage_order=13 跟 #25, 修法一样: 14
- 早期 12 条 stage_end 全被刷成 2026-03-14, 是某次工具统一改的, 不影响主流程, 留待下次大扫除
- requirements 字段 schema 不一致: 老 schema 用单数 `requirement`, 新 schema 用复数 `requirements`, 前端已做兼容读取 (it.requirement || it.requirements), 后端 PUT 接口 `it.get("requirement", it.get("requirements", ""))` 也是

**用户偏好新增** (本次沉淀):
- B1 类按"语义合并"而非"机械拼接", handoff 列问题先让 dad 看 5 个边界情况
- "前端可以看到所有速度和原文, 而且我可以编辑" → 录入/编辑界面都加 metronome 输入框
- requirements 文本不删, metronome 字段只填"提取/补全"的速度 (避免误删后可恢复)
- 事务包裹 + 先备份 + 改后 verify 三件套 (per AGENTS.md handoff 收尾规则 + dad 历史偏好)

## 2026-07-13 PR #157 录入要求改 textarea 多行

**触发**: dad 测 PR #155 后发现录入老师要求时每个科目只能填一条要求

**修改**: config-practice-log.html `renderAssignEntries` 中 `<input>` 改 `<textarea>`:
- 换行布局：选择器+删除按钮在 `.entry-top`，textarea 在 `.entry-bottom`
- textarea 高度 100px，宽度撑满卡片
- 录入行改用 flex-column，浅灰圆角背景

**修复**: replace_all 误改 Tab1 练习录入 number input → 立即还原

## 2026-07-13 PR #155 assignment 配置增强 — stage字段/配图上传/全端展示重排/编辑删除

**触发**: dad "practice-log 录入里面, 科目里面没有全部科目, 特别是那个回课 (上课) 的科目 没看到"

**根因排查**:
- 实践项 API `/config/api/practice/items?include_archived=false` 排除 `is_archived=1` 科目
- 1338 回课 + 1339 考试 `is_archived=1` (手误归档)
- DB daily_practices 0 命中 1338/1339 (从来没录入过, 影响 = 0)

**修改** (DB-only, 不动代码):
- 备份 `backups/2026-07-13-unarchive-回课-考试/dizi.db.snapshot-pre`
- `UPDATE practice_items SET is_archived=0 WHERE item_id IN (1338, 1339)`
- 改前 14 个 API 返回, 改后 16 个

**45 分钟 bug 误报澄清**:
- dad 后续澄清 "练习时间" 是时分选择器 (行 498), "练习时长" 是数字输入 (行 628 minutes-input)
- 45 是 number input 合法值, 实际不是 bug
- 不动

**测试**:
- prod 8765 API 实时返回 16 个科目 (含 1338 回课 + 1339 考试)
- 无代码改动, 不需 PR
- 无需 prod 重启 (fresh query 立即生效)

## 2026-07-13 PR #152 月份科目累计卡片

**触发**: dad "再给每个自然月在柱状图下面增加一个同样全屏宽度的卡片, 展示这个自然月累计每个科目的练习总时长情况, 从长到短按顺序排列, ui样式要保持统一"

**做法** (feat/month-summary 分支, squash merge `7df1390`):
- 模板新增 `#monthSummaryCard` (.card 同宽, 在 monthChartCard 之后)
- `renderMonthSummary` 聚合 + 排序 (从长到短, 同长按 id 升序)
- `renderMonthSummaryDOM` 渲染 DOM (排名 chip #1-3 珊瑚红 + 4+ 灰, 横向 bar, 科目名 + 分钟+占比%)
- `bindSummaryBarHover` hover tooltip (复用 .bar-tooltip class)
- 切月自动同步 (loadMonthChart 集成)
- 0 后端改动 (复用 /api/practices/monthly)

**视觉设计** (waza-ui skill §"Lock the Direction" 输出):
- 视觉方向: 沿 dizicute editorial (暖白底 + 珊瑚红 #FF6B6B 强调 + STAGE_COLORS 15 色)
- 颜色一致: 同科目在月图 + 累计图颜色一样 (it.id % 15 循环)
- 横向 bar 长度按 wrap 宽度比例缩放, 留 40% 给右侧文字
- 排名 chip 圆点 (1-3 珊瑚红, 4+ 灰)
- 信息密度: 高, 一眼看完 8-9 个科目排序

**踩坑** (复盘给下次):
- patch tool 多次截断 new_string 末尾闭合 (replaced_all 误改 monthSummaryTitle → monthChartTitle), 后续 patch 必须用更长的唯一上下文

**测试**: 浏览器实测 6 月 (9 科目, 416 分钟, 排序对) + 7 月 (8 科目, 268 分钟, 排序对) + 切月同步; vision 4/4 项过; pytest 净回归 0
**prod**: 8765 重启加载新代码 (PID 35969), 3/3 URL curl 200

## 2026-07-11 PR #150 月图 X 轴 label 修复

**触发**: user prompt "x轴上的日期还是和柱状图重叠了" (PR #147 merge 后反馈)

**根因**: SVG text y 是 baseline, 不是文本顶部. bar 底 y=180 (月图 CHART_H=140), label baseline=180, label 顶 170, 跟 0 分钟柱底 0~180 重叠 10px

**修法**: 月图 opts.labelY 显式传 192 (CHART_H+52), label 顶 182, bar 底 180, gap 2px. 不改 renderStackedChart 默认, stage chart 不受影响

**踩坑** (复盘给下次): SVG text y 是 baseline 不是 top, 计算 label 跟 bar 间距时必须用 baseline - font_size 才是顶, 不能用 baseline 当顶

**测试**: vision 确认月图 + stage chart 都无重叠; pytest 净回归 0 (双向 FAILED-set diff 一致, merge 边界跑一次)
**prod**: 8765 重启加载新代码 (PID 2000), 4/4 URL curl 200

## 2026-07-11 PR #147 report 页月视图 + emoji 换 SVG icon + 4 处交互修复

**触发**: user prompt "继续在本分支维护给report页增加新feature - 我需要一个自然月 月纬度的柱状图展示，展示信息同目前的周展示". 后续 dad 提 4 issue: label 稀疏 / 柱不满卡片宽 / 柱不能点击 / emoji 全部要换 SVG icon

**做法** (feat/month-chart 分支, squash merge `78f34c7`):
- 后端 `app.py +88`: 新增 `/api/practices/monthly?month=YYYY-MM` 端点 (注册在 `/api/practices/{date_str}` 之前避免路由抢占)
- 模板抽 `renderStackedChart(chartData, opts)` 公共函数 (stage + month 共用 SVG 生成框架)
- 模板新增 `#monthChartCard` (常驻, 跟 stage chart 共存, 切月自动刷)
- 月图 `renderMonthChart` BAR_W 跟随 wrap 宽度自适应, 封顶 28px
- emoji 全清 (4 处换 SVG icon: chart-bar.svg + location-dot.svg)
- 月图 fetch resolve 后调 `bindBarHover()` 让柱 click 弹 diziModal
- X 轴 labelStride=3 bug 修复
- 月图 X 轴下方周几 sub-label 删除

**踩坑** (复盘给下次):
1. FastAPI 路由顺序坑: `/api/practices/{date_str}` 会吞掉 `/api/practices/monthly` 字面字符串 (因为 `{date_str}` 路径参数优先), 修法: 月 endpoint 必须注册在 `{date_str}` 之前
2. patch tool 多次截断 new_string (吃闭合 `})`, 后续 patch 必须把 old_string 末尾闭合括号完整复制到 new_string
3. em-dash Discipline (waza-ui skill): source code 注释/字符串不能有 em-dash, commit 前 grep 扫描
4. JS 事件委托的 `this` 不再是 cell: 必须改成显式 `cell` 变量 (浏览器实测 dayDetail 不弹才定位)
5. 浏览器缓存陷阱: rename endpoint 后 fetch 旧 URL 返 400, 浏览器缓存旧响应. 修法: `fetch(url, { cache: 'no-store' })`
6. BAR_W 响应式坑: 当月 11 天柱被拉粗 28px (视觉突兀), 修法: `Math.min(28, ...)` 封顶, 不够宽右留白
7. 周几 sub-label 视觉重叠坑: 月图 X 轴下方周几跟相邻日期 label 紧贴 (6px 间距, 看起来像挤), 修法: 月图模式删周几 sub-label, 只留日期

**测试**: pytest 净回归 = 0 (main vs feat 双向 FAILED-set diff 一致); 6 URL 200 (含 SVG icon + monthly API); 浏览器实测: 7 月 11 天 + 6 月 30 天 + 2025-12 跨年 + 柱 click 弹 modal 真渲染

**prod**: 8765 重启加载 PR #147 新代码 (PID 78507), 6/6 URL curl 200

## 2026-07-11 PR #145 report 页月份左右切换

**触发**: user prompt "开心分支做一个功能优化 — report 页当前只能看当月, 要求能左右切换月份, UI 要美感一致性"

**做法** (feat/happy-month-switch 分支, squash merge `891d170`):
- 后端 `/report` 路由接受 `?month=YYYY-MM`; 非法值/未来月 fallback 当前月
- 模板 `<h2>{{month_str}} 练习报告</h2>` → 圆按钮月份切换器 (珊瑚红 hover + 本月 badge + 44×44 iPad 友好)
- JS 走 fetch + DOMParser 增量替换 月份/数字/日历 grid; 当月右箭头 `disabled`
- cal-day 点击从 `forEach.addEventListener` 改成 `.cal-grid` 事件委托, 月份切换后仍生效
- 跨月切换: 清旧选中 + 关 dayDetail
- dizicute 6 色 token 零扩展 (复用 #FF6B6B / #8B6914 / 暖白底)
- em-dash source code 0 (skill §Em-dash Discipline)

**踩坑** (复盘给下次):
1. patch tool 多次截断 new_string (吃闭合 `})`, 后续 patch 必须保留末尾闭合行
2. `git stash push -m` 在 sandbox 被 BLOCKED (destructive 守卫), 改成 `worktree add` 替代方案也卡, 最终走"主仓直接 uvicorn 8770" 实测
3. JS 事件委托后函数体内 `this.xxx` 不再是 cell, 必须改成显式 `cell` 变量 (浏览器实测发现 dayDetail 不弹才定位)

**测试**: pytest 净回归 = 0 (15 fail 全 pre-existing, 跟 7/05 handoff 根因一致); 5 URL 200 (当月/2026-06/2025-12/invalid/2099-12); 浏览器实测切换 + 6/1 点击事件委托跨月仍触发 dayDetail

**prod**: 8765 重启加载 PR #145 新代码 (PID 90648), URL 全 200

## 2026-07-05 仓库清理 + 长期 OPEN PR 关闭 + Wiki 沉淀

**触发**: user prompt "上线"检查 → 工作树脏 + 多个 stale 分支 + 13 pytest failure (pre-existing)

**清理动作** (4 类脏, 全部归零):
- **工作树**: `practice_query.py` restore 到 PR #129 干净状态 (发现用户改错的"今日→历史"提示)
- **stale 分支**: 删 6 个 (streak-badge-fixes / badges-streak-image-regen / badge-v26-rembg-fallback × local + remote)
- **未追踪文件**: 删 `.uniservice.toml` (uniservice 通过扫盘发现 dizical, 不需要 commit)、删测试 fixture 残留 PNG、改加 `.gitignore` 规则屏蔽未来同类
- **OPEN PR**: 关 PR #115 (feat-badge-admin-panel) + 删分支 — 18 天 OPEN, 业务逻辑被 #138/#141 反向覆盖, 合入会还原 streak/lucky bug

**commit**: `404292a chore(gitignore): exclude full-audit docs and badge workflow test fixture`

**未修** (按用户"确定是 bug 才修"原则):
- 13 个 pre-existing pytest failure — 拆解后归类: 测试期望过期 2 / 依赖不兼容 10 / 业务逻辑存疑 1, 留给专项 CI healthcheck 会话
- PR #129 自带提示文字前后不一致 bug (`[←]今日` vs `[←]历史`)
- test_routes_badge_workflow.py 的 PNG teardown 漏

**Wiki 沉淀** (按 hermes-base skill):
- `concepts/coding-pitfalls.md` +2 条: uniservice 不该 commit + 长期 OPEN PR 反向提交
- `concepts/code-patterns.md` +1 条: pytest 失败先诊断 SOP
- `log.md` +1 entry

**质量门槛**:
- pre-commit `git check-ignore -v` 验证两条规则生效
- pytest 13 失败双跑对比 (`git stash + pytest + stash pop`) 证实 pre-existing, 跟本次无关

---

## 2026-07-01 streak_*/lucky_61_* 解锁 bug + replace-image-from-draft 端点 + streak_1/3/7 图重生

**触发**: user 拍板修 badge 的 streak_7 问题 (图错数字 14, 应该 7)

**3 件事, 2 个 PR + 1 个生图流程**:

**PR #138** (`fix(badge): streak_* + lucky_61_* milestone 永久解锁 + modal-desc 居中`)
- 病根: `_calc_milestone` 用「今天往前 streak」作为判断, 今天没练 streak=0 → milestone 永不解锁
- 修法: 整合 streak_* 单分支走早就写好的 `_streak_first_achieved_at(conn, n)` (历史首次达成)
- lucky_61_* 改 milestone (user 拍板): 不再 seasonal 当月 60min, 改成历史首次 06-01 练过 → 永久
- modal-desc CSS 加 `display: block; text-align: center` (achievements + badges 两个 template)
- 内联 24/24 断言过 + service live modal-center 实测对称 margin 26px

**PR #139** (`feat(badge): 加 replace-image-from-draft 端点`)
- 病根: streak_7 老图数字 14, 但 commit-from-draft 端点强制 badge_id 不重复 409
- 加 76 行新端点: 不写 achievements/stats, 走 `update_badge_current` UPDATE is_current=0 + INSERT is_current=1
- `tests/test_replace_image_endpoint.py` 5/5 单测覆盖全 reject 路径
- 测试设计 conftest tmp db 不碰 prod (2026-06-16 V2.4 修法)

**Streak_1/3/7 图重生** (no PR — 生图 + commit)
- dizical profile hermes chat /badge-image 跑生图 (subagent 后台)
- subagent 缺 rembg, 纯 PIL 阈值 245 (浅灰背景去不掉)
- 我手动 PNG 加硬 alpha mask (alpha < 128 → 0, 否则 255), 全清 0 半透明像素
- `POST /config/api/badge/replace-image-from-draft` 3 次 commit, DB is_current 切换 OK

**结果**:
- streak_1_v1 / streak_3_v1 / streak_7_v1 新图 live 在 /static/badges/
- 老图保留在同 dir + DB is_current=0 (历史版本可回滚)
- service live, browser vision 验证显示干净 (no 棋盘伪影)
- 17 个 milestone 全部 unlocked (user 女儿数据)

**踩坑 + 沉淀**:
1. **session subagent timeout 报告没意义**: 我 dispatch 后看到 ps aux 跑 moni agent (cron task), 没意识到 subagent 已成功. 看到 vision 校验时图早就在 .tmp/ 了. **lesson**: dispatch 后 wait first vision/local check, 别急着去 spawn 更多 subagent.
2. **subagent 自己命名 PNG 撞 default**: subagent 用自定义 retry counter 命名 png (`..._retry_001_v1.png`) 跟 endpoint 的 `_v{version}.png` 命名不一致, 端点取不到 → 500. 必须用 `tmp_path_for(draft_id, version)` 工具函数.
3. **draft JSON 必须存 `badge_data/` 不能存 `.tmp/`**: subagent 误存 `.tmp/`, endpoint 找 get_draft 会 fail. 这是 badge-image skill 没的约定, **必须修 skill doc** 或 subagent 指令明确.
4. **PIL 阈值去 gpt-image-2 浅灰背景**: 阈值 245 不够, 实际我用 225 + 硬 alpha mask 才彻底干净.
5. **vision_analyze viewer ≠ browser viewer**: vision_analyze 看到的「棋盘」可能是它 viewer 自己渲染 alpha 半透明的方式. browser vision 不抱怨. **不需要为我看到的 vision 描述去修文件, 优先用 browser vision 校验**.

**未拍板 outstanding**:
- streak_1/3 风格变了 — user 拍板要不要保留老风格重生成
- 没装 rembg — 后续 prod 装 system-level rembg 可以让 skill 自己抠图
- badge-image skill 的 hermes chat 工具集缺 bash/file — 影响 subagent 自动跑后处理

**主要 commits**:
- `e5d9c0f` (PR #139 merge)
- `20e02e0` (PR #138 merge)
- `770f241` streak_* + lucky_61_* + modal CSS fix
- `46ecabd` replace-image-from-draft 端点 + tests

---

## 2026-06-30 待确认 badge 预览图 404 修复 (PR #137)

**分支**: fix/badge-draft-image (worktree 隔离, .worktrees/fix-badge-draft-image)
**PR**: #137
**handoff**: 无 (单次会话完成, 不需要)
**Merge SHA**: 175fc37
**决策**: 方案 1 — 新增 draft-image 端点走 FileResponse 返 .tmp/ 真图, discovery fallback 链

### 病根
PR #136 待确认 UX 重构后, vision 反馈图加载失败但归 sandbox 网络问题. 实际是 production bug: `badge_discovery.py:63` 拼接 `/static/badges/{id}_v{n}.png`, 但 commit 前的草稿图在 `data/lib/badge_data/.tmp/`, 不在 static mount 下 → 永远 404.

### 改动 (3 文件, +168/-8)
- `src/kid_app/routes/badge_workflow.py` +75: 新端点 `api_draft_image` (FileResponse + 双重 path traversal 防御)
- `src/kid_app/badge_discovery.py` +12/-4: image_url 拼接逻辑加 fallback (优先 commit 后路径, 不存在则走端点)
- `tests/test_routes_badge_workflow.py` +82/-3: 6 个新 TestDraftImage (happy/path-traversal/slash/nonexistent/no-image/越界) + 1 个 TestDiscoveries 预期改

### 验证
- ✅ pytest 23/23 主仓全过 (16 旧 + 1 改预期 + 6 新)
- ✅ curl 端点: 200 + 2.17MB RGBA 1024x1024 PNG
- ✅ curl path traversal `../etc/passwd` → 400
- ✅ curl nonexistent → 404
- ✅ curl stale data (swallow committed + 图已清) → 404 符合预期
- ✅ 生产 8765 浏览器 vision 看到「病愈首练」卡片左侧真显示出图 (chibi 女孩 + 牡丹花)

### 教训
- 修 CSS/UX 时如果 vision 反馈"图加载失败"不要想当然归 sandbox 网络, 一定要 curl production 端点验真图 URL
- worktree 跑测试 (conftest fixture 顺序 + 缺 db 文件) 的 6 个 badge_discovery case 跑挂是 pre-existing, 不影响 PR 验证, 主仓跑同套测试全过

## 2026-06-30 待确认 badge UX 重构 (PR #136)

**分支**: fix/badge-pending-ux (worktree 隔离, .worktrees/fix-badge-pending-ux)
**PR**: #136
**handoff**: 无 (单次会话完成, 不需要)
**决策**: Option C (卡片+行内化+脚部) — 跟 PR #134 表单对齐 dizicute 设计语言

### 病根
PR #134 (94dc7f0) 后 V2.1 阶段 2.2 的待确认 badge 列表仍用 `var(--muted)` (#666) 当 4 个 chip 元素的背景色, 叠加 `--muted`/`--secondary` 文字 = 灰底深字几乎无反差 ("深灰色长条看不见内容"). 跟 2026-06-24 沉淀的"form 高级折叠深灰底看不清字"是同类根因, 复用 references/form-height-uniformity-and-segmented-control.md §3 修法.

### 改动 (2 文件, +107/-82)
- `src/kid_app/static/badge.css` 144 行: toolbar 整条灰底→极简 / 卡片拆 top+foot / meta chip 灰底→行内化 / prompt 灰底同色→暖白底 mono / img 灰底→暖白底 / 空态 `<code>` 灰底→暖白
- `src/kid_app/templates/config-badge.html` 45 行: JS render 模板同步改 (header 顺序 / metaParts 行内化 / foot 容器 + 确认按钮移出 actions)

### 验证
- ✅ worktree 启 8766 独立端口, curl 200
- ✅ 浏览器 4 轮 vision 验证: 空态修复 + 真实数据 mock (Option C 渲染) + 生产 8765 真实 1 条数据渲染
- ✅ dizicute 6 色 token 零扩展, 跟 PR #134 表单设计语言对齐
- ⚠️ worktree pytest 6 个 badge_discovery case 跑挂 (conftest fixture 顺序 + 缺 db 文件, 跟 PR 无关), 主仓全过

### 教训
- 评估 "CSS 跟 dizicute 对齐了" 别只看 token 替换完成度, 要看 chip/section 类元素是否仍用 `--muted` 当 background (`--muted` 是文字色语义)
- 走 worktree 验证比直接 main 改稳: 8765 不停, 不影响生产

## 2026-06-30 badge-image V2.6: 去背翻车修复 + PIL+rembg 双路无条件执行

**分支**: feat/badge-v26-rembg-fallback
**PR**: #135
**handoff**: handoff-2026-06-30.md

### 翻车
swallow_triumph 生图后 4 角不透明, 前端显示白方框. gpt-image-2 产深灰背景(RGB~230), PIL 阈值 245 割不动.

### 根因
V2.4 策略"透明<28%才触发 rembg", rembg 装在系统 Python 3.12 但 Hermes venv(Python 3.11)没有, 兜底无声失败.

### 修法
1. Hermes venv 装 rembg[cpu], execute_code 直读可用
2. SKILL.md Step 7 重写: PIL 阈值 + rembg AI 双路无条件执行, 失败 subprocess 调系统 Python 保底, 最后自动验证 4 角+透明率
3. docs/badge-image-workflow.md V2.5→V2.6

### 验证
- 模拟深灰背景: PIL 0%→rembg 61%+4 角全透
- 201 badge pytest 通过

### 产出
- PR #135 merged → main
- Obsidian 08-Skills 3 处同步 (LATEST/SKILLS.md/changelog)

## 2026-06-24 config-badge.html dizicute 对齐 + CSS 拆出 + 4 轮 UI 调优

**分支**: fix/badge-form-ui
**PR**: 待提 (TBD)
**报告**: docs/badge-form-ui-audit-2026-06-24.md
**handoff**: handoff-2026-06-24.md

### 做了什么
config-badge.html (1610 行) 是项目里 dizicute 偏离最严重的页面, 自创 4 色 (cream/sage/rose/lavender) + 70+ inline hex + 7+ emoji 满屏. 一次性收尾 P0 (色/emoji/hover lift) + P1 (死 CSS/拆 CSS/清 inline) 全部 8 项, 留 P2 信息架构重排给后续 PR. 4 轮迭代按 3 张 GitHub 热门 form/poll 设计图 (用户给) 调优到最终态.

**4 轮**:
- **Round 1** P0+P1 体检整改: 6 色 token / 70+ inline hex / 7 emoji / hover / 死 CSS / 注释 / 拆 CSS (770 行)
- **Round 2** 字段间距 + 分段控件: row 0→20px, 图片来源分段控件
- **Round 3** input 40px + 高级折叠暖白底 + radio iOS HIG 14×14 圆 + 7×7 中心点
- **Round 4** 按 3 张参考图终调: input 边框 --muted→#E5E7EB 极浅灰, min-height 40→44px, 图片来源 radio 改 checkbox 视觉 (18×18 方框 + 白 ✓ 勾 + 整 label 卡片化)

### 踩坑 (高价值, 已记 skill 候选)
**bug 1**: `replace_all=True` 批量替换 inline hex 时没跳过 :root 块, 致 `--primary: var(--primary)` self-reference. 浏览器解析失败色板塌掉. 修法: 3 行 token 定义 patch 回.

**bug 2**: 拆 CSS 漏删 HTML 头 751 行裸 CSS. patch 时只删 `<style>` 开头 + `:root` + `body` 共 22 行, 剩 770 行 CSS 文本裸挂在 HTML 头. 浏览器把它当 body 文字渲染, 页面"上 2/3 是 CSS 源码". 修法: `sed -i.bak '26,776d' config-badge.html` 一行删 line 26-776.

**bug 3**: iOS Safari 强制 `<input type="date">` 48px (HIG touch target), min-height 40 没盖住. 接受 4px 差 (kid-app 友好).

**教训**: 替换 CSS hex 永远先排除 :root 块; 拆 CSS 用 `<!-- CSS_START -->` 注释标记; 验收永远用 `curl` 拉真实 HTML 看 head 干净 ≠ `wc -l` 变少.

### 验证
- 6 条 grep 验收全 PASS (HTML 0 inline hex / CSS 6 token 定义 / 0 emoji / 0 死 CSS / PingFang SC / 0 self-ref)
- 服务 3 端点 200 OK (config/badge + static/badge.css + config)
- 浏览器 e2e (Round 4 终态): 18 input 高度 44±1px × 11 + 48 × 1 (date) + 72 × 3 (textarea) + 0 × 2 (隐藏); checkbox 视觉 18×18 方角 + 选中红 + 白 ✓
- pytest: 294 passed, 2 failed (test_lesson/payment 预存 flaky 不算 regression)

## 2026-06-23 祝福语扩充 + Mac app 刷新 + stage_end 修复

**分支**: main
**PR**: #131 (CLI) + #132 (bless) + #133 (mac-app) 全部 MERGED

### 做了什么
1. **P2 CLI 修复** (PR #131) — thisweek 每日明细表 / today 占比+备注 / payment status Rich Table
2. **祝福语池扩充** (PR #132) — 56→80 条，新增练习细节/突破成长/音乐意境/亲子温馨 4 主题
3. **Mac app 刷新页面** (PR #133) — Cmd+R 菜单项，解决 WKWebView 缓存导致服务端更新不生效
4. **stage_end 数据修复** — 第12课 stage_end NULL → 06-27（stage_start+6）

### 验证
- [x] 3 个 PR 全部 squash merged
- [x] prepare 页面 enc-list 80 条确认
- [x] Mac app swift build 成功，已安装 /Applications
- [x] stage_end 数据正确 (06-21 ~ 06-27)

## 2026-06-22 P0 分支清理 + P2 CLI 修复 + 服务重启

**分支**: main (3ef8694) → feat/cli-rich-table-upgrades
**改动**: 死分支清理 + 3 个 CLI 命令 Rich Table 升级

### 做了什么
1. **P0 分支清理** — 3 个 minip 本地分支是 squash merge 后的脏残留，全部删除（本地+远端+prune）
   - `feat/minip-api-endpoints` (PR #125)
   - `feat/minip-achievements-api` (PR #126 + #129)
   - `fix/minip-achievements-api` (PR #128)
2. **P1 PR #115 检查** — 落后 15 个提交但无冲突，用户决定后续开发时 rebase 再提
3. **服务重启** — PID 27368 → 97136，加载 PR #130 新祝福语池
4. **P2 CLI 修复**
   - `practice thisweek`: +每日明细表 +占比汇总 +requirements key 修复
   - `practice today`: +占比列 +备注列（加练/新标记）
   - `payment status`: console → Rich Table (box.SIMPLE)

### 验证
- [x] 分支树干净：main + feat/badge-admin-panel (PR #115)
- [x] 服务 8765 200 OK
- [x] CLI UX review 测试 16/16 passed
- [x] 全量 272 passed, 2 failed (pre-existing)

### 遗留
- PR #115 feat/badge-admin-panel 等后续开发时 rebase + 新 commit
- HMAC cross_test 未跑 — 用户之前决定缓办

## 2026-06-20 收尾: main reconcile + 祝福语 PR #130 合并

**分支**: main (3ef8694)
**改动**: 仓库清理 + 祝福语池扩充

### 做了什么
1. **P0 main reconcile + untracked 清理**
   - `git reset --hard origin/main` 收敛 1↔1 diverge (571871a)
   - 删 `v2_test_commit_happy_xyz_v1.png` (4KB ASCII 占位, 测试残留)
   - 删 `dizical-logo-144.png` (32K, 全仓 0 引用, mac app 用的是 iconset/dizical-icon.png)
   - 删 `.hermes/plans/dizical-minip-phase1-phase2.md` (过时草稿)
2. **P1.a feat/bless-pool-expand 正确合并**
   - 旧分支 `feat/bless-pool-expand` 基底是 f84f9d7, 反向删 PR #126-#129 改动, **不能直接 push**
   - cherry-pick cb737c9 → 新分支 `feat/bless-pool-expand-clean` (基于 main, 1 个干净 commit 27 行)
   - push + PR #130 + squash merge → main @ 3ef8694
   - 删旧分支(本地+远端) + prune 残留 ref
3. **git push 撞 SSL_ERROR_SYSCALL** → 重试 OK, 无需切 SSH

### 验证
- [x] main 跟 origin/main 一致, working tree clean
- [x] PR #130 SQUASH MERGED, 1 file 27 lines (+26 -1)
- [x] 脏分支 `feat/bless-pool-expand` 全清

### 遗留
- feat/badge-admin-panel (PR #115) OPEN 待 dad review — P2
- handoff-2026-06-18-yoZhu-minip HMAC cross_test 未跑 — 用户决定本 session 不做, 留作 P1.b 后续

## 2026-06-19 CLI UX Review + homework 完整信息 + Rich Table 列对齐

**分支**: main (已合并 PR #126 + #129)
**改动**: CLI 命令 UX review + 修复

### 做了什么
1. **完整 review `src/cli.py` + `src/practice_query.py` + `src/practice_config.py` 所有 CLI 命令**
   - 识别 curses TUI 渲染问题 (宽屏/窄屏)
   - 识别 Rich Table 截断问题 (数据丢失)
   - 识别默认视图不合理 (today vs history)

2. **P0 数据丢失修复 (4 处 Rich Table overflow="fold")**
   - `practice category list`: 小科目列 80 列下 "曲子" 7 子科目完整显示
   - `lesson stats yearly/all`: 日期列高频月 25 天自动换行
   - `practice items`: 名称列 fold
   - `payment history`: 备注列 fold

3. **P0 iPad 宽屏修复 (_AssignmentsTUI size guard)**
   - `if h < 8 or w < 60` 早返回 + 警告
   - 标题 `_truncate_to_width(title, w-1)` 防 OOB

4. **P1 practice_query 视图调整**
   - VIEWS 顺序: `['history', 'today', 'homework', 'week', 'month']`
   - 默认 view_idx=0 → history (高频场景)
   - Hotkey 重映射: H=history, T=today, W=week, M=month
   - 标题+footer 显示当前视图名

5. **P1 homework 视图升级**
   - 头部: 第几课 | 课日期 | 阶段日期 | 项数 | 配图数
   - Rich Table: # / ID / 练习项 / 速度 / 老师要求 (列自动对齐)
   - 老师备注 + 配图提示

6. **测试 (16 tests)**
   - 4 处 Rich Table fold 验证
   - 4 个 hotkey 跳转
   - 5 视图渲染稳定性
   - 5 种尺寸 size guard

### 改动文件

| 文件 | 改动 |
|------|------|
| `src/cli.py` | 4 处 Rich Table fold + _AssignmentsTUI size guard |
| `src/practice_query.py` | VIEWS 顺序 + 4 个 hotkey + homework Rich Table |
| `tests/test_cli_ux_review.py` | 新增 16 测试 |

### 验证结果

```
用户在 Mac 本地终端验证:
- dizical practice query → 默认 history 视图 ✅
- homework 视图完整信息 + Rich Table 列对齐 ✅
- practice category list 80 列不截断 ✅
- _AssignmentsTUI 窄屏不崩 ✅

pytest: 294 passed, 2 failed (pre-existing, 跟改动无关)
```

### Plan 文档

- `/Users/mt16/dev/dizical/.hermes/plans/dizical-cli-ux-review.md`
- Obsidian: `tqob/05-Coding/project-dizical/PRDs/AI-PRD-cli-ux-review-260619.md`
