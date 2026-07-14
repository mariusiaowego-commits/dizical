# STATUS.md - dizical 项目状态

**最后更新**: 2026-07-13 (PR #159 merge, main = ab57c49)
**当前 main**: ab57c49 (PR #159 squash merge fix/metronome-field-render-and-backfill-260713)
**生产服务**: 8765 running PID 73634 (load PR #159 新代码, 3/3 URL curl 200)
**pytest**: 13 failed / 294 passed (净回归 = 0, 13 全 pre-existing)

### 已完成 (2026-07-13 metronome 全链路支持)

**PR #159** - `fix(assignments): 渲染 + 编辑 metronome 字段` (1 commit, +17/-3, 2 files)
- **后端 config.py**: POST/PUT 接口 formatted items 多带 `metronome` 字段 (之前被静默丢弃)
- **前端 config-practice-log.html** 6 处:
  1. POST 录入表单 renderAssignEntries: 加 `<input class='metronome-input'>` + change 事件
  2. addAssignEntryBtn: assignEntries.push 加 metronome 默认空字符串
  3. submitAssignBtn: body.items 多带 metronome
  4. 历史列表 loadAssignments: 珊瑚红 pill 渲染 it.metronome (空不渲染)
  5. 编辑模式: 加 `<input class='edit-item-metro'>`, 保存时取这个值
  6. 本周总览 loadWeek: 同样渲染 metronome pill

**DB 改动 (不进 PR, 单独 SQL 已应用)**:
- #26 2026-07-12 stage_order 13→14, stage_start 7-12→7-13, stage_end 7-18→7-19 (修了 stage_order 重复 bug)
- B1 24 条 metronome 字段回填 (按语义合并, requirements 文本保留):
  - 例: 西藏舞曲 (2026-07-12) '4/4 ♪=80, 2/4 ♪=69-80'
  - 例: 采茶扑蝶 (2026-07-12) '♩=108、112'
  - 例: 单吐练习 (2026-03-14) '♩=52、56、60'
- 备份: `/tmp/weekly_assignments_backup_2026-07-13.json` (26 条全表)
- DB 备份: `/tmp/dizi.db.bak.before-2026-07-12-fix`
- 全表分布: 49 metronome 已填 / 34 空 (34 = B4 类 14 条 + 早期 stage_order=NULL 老 schema 20 条)

**用户偏好沉淀** (本次新增):
- "前端可以看到所有速度和原文, 而且可以编辑" — 录入和编辑界面都需要 metronome 输入框
- B1 24 条按"语义合并"而非"机械拼接" (例: 采茶扑蝶 '♩=108、♩=112' → '♩=108、112' 合并顿号, 西藏舞曲 '4/4 ♪=80, 2/4 ♪=69-80' 加乐段标注)
- requirements 文本不删 (保留可编辑), metronome 字段只填"提取/补全"的速度
- handoff 列问题先让 dad 看 5 个边界情况 (5 个 B1 边界全部由 dad 拍板"按语义合并")

### 已完成 (2026-07-13 录入要求改 textarea 多行)

**PR #157** - `fix(assign-entry): textarea 多行 + 换行布局` (+43/-24, 1 file)
- 录入老师要求时每个科目只能填一条（单行 input），改为 textarea 多行
- 科目选择器 + 删除按钮在上一行，textarea 独占下一行，宽度撑满卡片，高度 100px
- 录入行背景浅灰圆角，视觉分区

### 已完成 (2026-07-13 assignment 配置增强)

**PR #155** - `feat(assignment): 配置增强 — stage字段/配图上传/全端展示重排/编辑删除` (3 commits, +602/-56, 7 files)
- **后端 data layer**: database.py `save_weekly_assignment` images 参数忽略 bug 修复; config.py 新增 PUT/DELETE/upload 端点; stage 字段 UI 优先覆盖自动推算
- **配图上传**: POST /config/api/assignments/upload + data/uploads/raw/ + /uploads StaticFiles mount
- **录入表单**: stage_start/end/order 三个输入框; 图片上传 UI (文件选择+缩略图+删除)
- **全端展示重排**: prepare 页 4 部分 subject-block + 图片画廊; practice 页楼层 1 选中科目显示 4 部分; config-practice-log Tab2 历史卡片 4 部分 + edit/delete + stage pill; Tab3 周总览 same
- **skill**: dizical-image-style (跨 3 profile 同步)
- **卡片视觉重设计**: 珊瑚红 pill 阶段标签 / 科目左竖线 + a)b)c) 编号 / 图片 hover 放大 / 卡片阴影微边框 / 编辑删除 hover 反馈

**最后更新**: 2026-07-13 (PR #152 月份科目累计卡片)
**当前 main**: 7df1390 (PR #152 squash merge feat/month-summary)
**生产服务**: 8765 running PID 35969 (load PR #152 新代码, 3/3 URL curl 200)
**pytest**: 13 failed / 294 passed (净回归 = 0, 全 pre-existing 跟 7/05 handoff 一致)

### 已完成 (2026-07-13 月份科目累计卡片)

**PR #152** - `feat(month-summary): 月份科目累计卡片 (横向 bar 排序, 同色跨图)` (squash merge `7df1390`)
- 模板新增 `#monthSummaryCard` (.card 同宽, 在 monthChartCard 之后)
- `renderMonthSummary` 聚合每科目总分钟 + 数组化 + 从长到短排序
- `renderMonthSummaryDOM` 渲染横向 bar 列表 (排名 chip + bar + 科目名 + 分钟+占比%)
- 颜色复用月图 STAGE_COLORS (it.id % 15) = 跨图同科目同色
- 自适应: 横向 bar 长度按 wrap 宽度比例缩放 (BAR_AREA_RATIO=0.6)
- hover tooltip (复用 .bar-tooltip class)
- 切月自动同步 (loadMonthChart 集成 renderMonthSummaryDOM)
- 0 后端改动, 0 新文件, 0 新 JS 库

UI 一致性: 0 新 hex, 0 新 JS 库, em-dash source code 0
pytest 净回归: 0 (双向 FAILED-set diff, 13/13 fail 同一集合)

**最后更新**: 2026-07-11 (PR #150 月图 X 轴 label 修复)
**当前 main**: d10f18b (PR #150 squash merge fix/month-label-overlap)
**生产服务**: 8765 running PID 2000 (load PR #150 新代码, 4/4 URL curl 200)
**pytest**: 16 failed / 291 passed (净回归 = 0, 全 pre-existing)

### 已完成 (2026-07-11 月图 X 轴 label 修复)

**PR #150** - `fix(month-chart): X 轴日期 label 不再与柱状图底部重叠` (squash merge `d10f18b`)
- 病根: SVG text y 是 baseline. 月图 CHART_H=140, bar 底 y=180, label baseline=180, label 顶 170, 跟 0 分钟柱底 0~180 重叠 10px
- 修法: 月图 opts.labelY 显式传 192 (CHART_H+52), label 顶 182, bar 底 180, gap 2px. 显式传 opts 不改 renderStackedChart 默认, stage chart 不受影响
- 验证: vision 确认月图 + stage chart 都无重叠, pytest 净回归 0

**最后更新**: 2026-07-11 (PR #147 月视图 + emoji 换 SVG icon + 4 处交互修复)
**当前 main**: 78f34c7 (PR #147 squash merge feat/month-chart)
**生产服务**: 8765 running PID 78507 (load PR #147 新代码, 6/6 URL curl 200)
**pytest**: 16 failed / 291 passed (净回归 = 0, 16 fail 全 pre-existing 跟 7/05 handoff 一致: 9 cli_ux_review typer×click + 3 config_design 进程冲突 + 2 payment 业务 + 1 badge_discovery fixture + 1 replace_image 业务)
**DB**: 未动

### 已完成 (2026-07-11 report 页月视图)

**PR #147** - `feat(month-chart): 月视图 + emoji 换 SVG icon + 4 处交互修复` (squash merge `78f34c7`)
- 后端 app.py +88: 新增 `/api/practices/monthly?month=YYYY-MM` (注册在 `/practices/{date_str}` 之前避免路由抢占)
- 模板抽 `renderStackedChart` 公共函数, stage 与 month 共用 15 色梯度 + SVG 生成框架
- 模板新增 `monthChartCard` (常驻, 跟 stage chart 共存, 切月自动刷)
- 月图 BAR_W 跟随 wrap 宽度自适应, 封顶 28px (修当月柱粗被拉宽问题)
- emoji 全清 (4 处换 `static/icons/chart-bar.svg` + `location-dot.svg`)
- 月图 fetch resolve 后调 `bindBarHover()` 让柱 click 弹 diziModal
- X 轴 labelStride=3 bug 修复 (此前 'wd === 周一' 二次过滤导致 stride 无效)
- 月图 X 轴下方周几 sub-label 删除 (避免跟相邻日期 label 视觉重叠)

UI 一致性: 0 新 hex, 0 新 JS 库, 0 新 CSS 文件, em-dash source code 扫描 0

**最后更新**: 2026-07-11 (PR #145 月份左右切换)
**当前 main**: 891d170 (PR #145 squash merge feat/happy-month-switch)
**生产服务**: 8765 running PID 90648 (load PR #145 新代码, 3 URL curl 全 200)
**pytest**: 15 failed / 292 passed (全 pre-existing, 跟 7/05 handoff 根因一致 — 9 cli_ux_review typer×click + 2 config_design 进程冲突 + 2 payment 业务 + 1 badge_discovery fixture + 1 replace_image 业务; 净回归 = 0)
**DB**: 未动 (只加 /report 查询参数解析)

### ✅ 已完成 (2026-07-11 report 页月份切换)

**PR #145** — `feat(report): 月份左右切换 — 看所有月份记录` (squash merge `891d170`)
- 病根: `/report` 路由硬写当前月 (app.py:1579), 模板标题 hardcode `{{month_str}} 练习报告`, 切月要改 URL
- 修法: `?month=YYYY-MM` 查询参数 + dizicute 圆按钮月份切换器 + fetch 增量替换 cal-grid + 事件委托保留跨月点击
- 验证: 5 URL 200 + 浏览器 6/1 跨月点击 dayDetail 真渲染 + pytest 净回归 0
- 8765 prod 重启加载新代码 PID 90648

**最后更新**: 2026-06-30 (待确认 badge 预览图 404 修复 PR #137)
**当前 main**: 175fc37 (PR #137 merge → +1 SHA from 5d379a4/#136)
**生产服务**: 8765 running (load PR #137 新代码, 已验证预览图真渲染)
**pytest**: 主仓 23/23 (16 旧 + 1 改预期 + 6 新 TestDraftImage)
**DB**: 未动 (新端点 + discovery image_url 拼接逻辑改)

**最后更新**: 2026-07-01 (streak_*/lucky_61_* 解锁 bug + replace-image-from-draft 端点 + streak_1/3/7 图重生)
**当前 main**: e5d9c0f (Merge PR #139 — streak image regen 端点)
**生产服务**: 8765 running (POST #139 端点 + 3 张新 _v1.png 已替换 streak_1/3/7 老图)

## 2026-07-01 重大 streak/lucky fix + badge 图重生

### ✅ 已完成 (2026-07-01 PR #138 + PR #139 + streak 图重生)

**PR #138** — `fix(badge): streak_* + lucky_61_* milestone 永久解锁 + modal-desc 居中` (merge → main @ 20e02e0)
- 病根: `_calc_milestone` 用 `_get_consecutive_streak()` (今天往前数连续), 今天没练 streak=0 → 全部 fail → milestone 永不解锁
- 修法: 整合 `aid.startswith('streak_') and aid[7:].isdigit()` 单分支走早就存在的 `_streak_first_achieved_at(conn, n)` (历史首次达成连续 ≥ N 天的日期)
- 同样改 `lucky_61_YYYY`: 用户拍板是 milestone (永久), 不再 seasonal 当月 60min 才解锁; 改成历史首次对应年份 06-01 练过 (total_minutes > 0) → 永久解锁
- DB 直 UPDATE: lucky_61_* category seasonal → milestone (现役)
- `src/restore_achievements_v1.py`: V2 数据契约跟进 (5 行 category 改 milestone)
- 加 `display: block; text-align: center; margin: 0 auto` 到 `achievements.html` `#modal-desc` + `badges.html` `text-align: left → center` + 加 `display: block`
- 验证: 24/24 内联断言 (streak calc + lucky calc + DB 写库 + cond_text), `test_replace_image_endpoint.py` 5/5 单测, service live 实测 modal-desc 居中 (margin-left 26px = margin-right 26px 完美对称)

**PR #139** — `feat(badge): 加 replace-image-from-draft 端点 (V2.x 换老图)` (merge → main @ e5d9c0f)
- 病根: V1 era 老图错了 (streak_7.png 数字 14 — 但 streak_7 应该是 7), commit-from-draft 端点强制 badge_id 不重复 (409) 不能用作「替换」
- 加 `POST /config/api/badge/replace-image-from-draft` 端点 (76 行):
  - 不写 achievements/stats 表, 只换 achievement_badges.url + version (走 `badge_db.update_badge_current` UPDATE old is_current=0 + INSERT new is_current=1, 事务)
  - 走的是 replace 语义 (跟 commit 的 insert 语义区分), 老图作为历史版本永久保留
  - 跟 commit 端点一样拿 image.version 数据源 (Bug #1 修法 2026-06-15)
- `tests/test_replace_image_endpoint.py` (5/5): happy_path 200 + static 图落盘 + DB 切换 is_current; rejects_wrong_status 400; rejects_unknown_badge 404; draft_without_image 400; invalid_draft_id 404
- 测试设计走 conftest tmp db, 不碰 prod DB (跟 2026-06-16 V2.4 修法一致)

### ✅ 已完成 (2026-07-01 streak_1/3/7 图重生 — commit + 去背)

**触发**: streak_7 老图数字错 (14 → 应是 7), streak_1/3 老图数字缺失. V1 era 生图时 prompt 不准.

**流程**:
1. dizical profile 的 `/badge-image` skill 跑生图 (subagent 后台调 hermes chat 调 fal.ai gpt-image-2)
2. V2.6 skill 自动 PIL 阈值 + rembg 抠图 (但 subagent 没装 rembg, PIL 阈值 245 用)
3. 大端点 `POST /config/api/badge/replace-image-from-draft` commit 替换

**结果** (DB + UI 都 live):
- `streak_1`: 老图 `streak_1.png` is_current=0, 新图 `streak_1_v1.png` is_current=1 (1024×1024, 50.7% 透明)
- `streak_3`: 老图 `streak_3.png` is_current=0, 新图 `streak_3_v1.png` is_current=1 (1024×1024, 45% 透明)
- `streak_7`: 老图 `streak_7.png` is_current=0, 新图 `streak_7_v1.png` is_current=1 (1024×1024, 49.9% 透明)
- 全图硬 alpha mask 修后 0 半透明像素 (viewer 不会再看到「棋盘」伪影)
- streak_14/30/100 数字正确, 不需换

**URL** (本地 Mac):
```
http://localhost:8765/static/badges/streak_1_v1.png
http://localhost:8765/static/badges/streak_3_v1.png
http://localhost:8765/static/badges/streak_7_v1.png
```

### ⚠️ 已知 outstanding (待 user 拍板)

1. **streak_1/3 风格变化**: 跟 V2 老图风格不一样 (原 streak_3 是「火焰」风格, 生图用了 streak_7 同款 chibi girl + 大金数字). user 拍板要不要重生成保留老风格
2. **没有 rembg**: 抠图只靠 PIL 阈值 225 (subagent 环境没装 rembg). 全 alpha mask 后 viewer OK, 但边缘轻微锯齿化
3. **badge-image skill 环境**: hermes chat subprocess 缺少 bash/file 工具, 无法自己跑 PIL+rembg 后处理. 现在靠 subagent 手补. 是 skill 工具集配置问题, 不在 dizical 仓范围内

### 📊 状态对照

**unlock_status**: 17 个 milestone 全 Y (streak_1/3/7/14/30 + lucky_61_2026 + total_300/600/1000 + first_log + all_items + top2/3 + assign_pal + night_owl + one_breath + grade_1)

**老图保留做历史**: streak_1.png / streak_3.png / streak_7.png (V1 era) 现在 static/ 还在, achievement_badges 表 is_current=0 行也还在 — 不删, 未来如需回滚直接 update is_current=1 即可

## 功能状态

### ✅ 已完成 (2026-06-30 待确认 badge 预览图 404 修复)
## 功能状态

### ✅ 已完成 (2026-06-30 待确认 badge 预览图 404 修复)

- **PR #137** fix(badge): 待确认列表预览图 404 — 加 draft-image 端点 (V2.6)
  - 病根: PR #136 浮现的图加载失败. discovery 返 `/static/badges/{id}_v{n}.png` 但 commit 前图在 `.tmp/`, 不在 static mount 下 → 404
  - 修法: 加 `GET /config/api/badge/draft-image?draft_id=xxx` 端点走 FileResponse 返 .tmp/ 真图 + discovery fallback 链
  - 安全: 双重 path traversal 防御 (draft_id 字符白名单 + image.path `relative_to(_badge_data_dir)`)
  - 验证: pytest 23/23 (16 旧 + 1 改预期 + 6 新 TestDraftImage) + curl 真图 200 2.17MB RGBA + 浏览器 vision 看到「病愈首练」卡片真显示出图
  - worktree 8767 启独立端口验证, main merge 后重启 8765 加载

### ✅ 已完成 (2026-06-30 待确认 badge UX 重构)

- **PR #136** fix(badge): 待确认列表 UX 重构 (Option C 卡片+行内化+脚部)
  - 病根: PR #134 后 4 个 chip 元素仍用 `var(--muted)` (#666) 当背景色, 叠加 `--muted`/`--secondary` 文字 = 灰底深字几乎无反差
  - 修 6 处: toolbar 整条灰底→极简 / id 灰底同色→mono 灰文字 / meta chip→行内化 / prompt 灰底同色→暖白底 mono / img 灰底→暖白底 / 空态 `<code>` 灰底→暖白底
  - 卡片结构: 顶部(主信息) + 脚部(操作), 主操作珊瑚红右下, 复制/删除左下
  - dizicute 6 色 token 零扩展, 跟 PR #134 表单对齐
  - 浏览器 4 轮 vision 验证全过: 空态 + 真实数据 + 主操作层级清晰
  - worktree 启 8766 独立验证, main merge 后重启 8765 加载

### 🚧 进行中

- **fix/badge-form-ui** refactor(badge-form): dizicute 对齐 + CSS 拆出 (PR #134 已 merge, 历史记录)
  - P0 (4 项): 自创 4 色 → dizicute 6 色 token / 70+ inline hex 替换 / 7 emoji × 14 处删除 / hover lift 改 background
  - P1 (4 项): 删死 CSS Portal 状态卡 / 文件头注释 V1→V2.1 / 拆 static/badge.css (770 行) / inline display 保留 (决策记 audit)
  - 8/8 完成, 报告: docs/badge-form-ui-audit-2026-06-24.md
  - 踩坑: replace_all 误改 :root token 定义, self-reference 致色板塌掉, patch 回 3 行修复
  - 验收: 6 条 grep 全 PASS / 服务 3 端点 200 / 浏览器 e2e 视觉过关

### ✅ 已完成 (2026-06-20 仓库清理 + 祝福语扩充)

- **PR #130** feat(bless): 扩展祝福语池 32→57 条 (新增 25 条鼓励语)
  - 1 个 commit 干净 cherry-pick 自 cb737c9, 1 文件 27 行
  - 25 条围绕 4 主题: 日常鼓励 / 音乐陪伴 / 节奏放松 / 亲子向
  - 无 DB migration, 无测试覆盖 (纯静态常量)
- **仓库清理**
  - main 跟 origin/main diverge 1↔1 → reset --hard 收敛
  - 删 3 untracked 噪音: 测试残留 PNG / 孤儿 logo (mac app 0 引用) / 过时 plan 草稿
  - 删脏分支 `feat/bless-pool-expand` (基底错) + 远端 ref prune

### 🚧 进行中

- **PR #115** feat(badge): 后台管理面板 (OPEN, 待 dad review)

### ✅ 已完成 (2026-06-19 CLI UX Review)

- **PR #126** feat(cli): Rich Table fold + practice_query history 默认 + TUI size guard
  - 4 处 Rich Table `overflow="fold"` (category list / lesson stats / payment history / practice items)
  - `_AssignmentsTUI` size guard (h<8 or w<60 → 警告窗口太小)
  - `practice_query` VIEWS 顺序: history 放第一位
  - hotkey 重映射: H=history, T=today, W=week, M=month
  - 标题+footer 显示当前视图名

- **PR #129** fix(practice_query): homework 视图完整信息 + Rich Table 列对齐
  - 头部: 第几课 | 课日期 | 阶段日期 | 项数 | 配图数
  - Rich Table: # / ID / 练习项 / 速度 / 老师要求 (列自动对齐)
  - 老师备注 + 配图提示

- **测试 (16 tests)**
  - 4 处 Rich Table fold 验证
  - 4 个 hotkey 跳转
  - 5 视图渲染稳定性
  - 5 种尺寸 size guard

- **验证**
  - `dizical practice query` → 默认 history 视图 ✅
  - homework 视图完整信息 + Rich Table 列对齐 ✅
  - `practice category list` 80 列不截断 ✅
  - `_AssignmentsTUI` 窄屏不崩 ✅

### ✅ 已完成 (2026-06-30 badge-image V2.6 去背翻车修复)

- **PR #135** fix(badge): 去背工作流 V2.6 — PIL+rembg 双路无条件执行 + system-python 保底
  - docs/badge-image-workflow.md V2.5→V2.6
  - swallow_triumph_v1.png: rembg U2-Net 重新去背, 4 角全透明
  - 根因: gpt-image-2 产深灰背景(RGB~230), PIL 阈值 245 割不动, rembg 无声失败
  - 外部: Hermes venv 装 rembg[cpu] + SKILL.md Step 7 重写
  - 验证: 模拟深灰场景 PIL 0%→rembg 61%+4 角全透

### 🚧 进行中 (2026-06-18)

- **PR #115** feat(badge): 后台管理面板 - 元数据编辑 + 排序管理 (OPEN, 待 dad review)

### ✅ 已完成 (2026-06-18 Badge 工作流 + UI 修复)

- **PR #124** fix(ui): achievements modal 同步 badges 修复
- **PR #123** fix(ui): modal 结构重构 + cond_text fallback 修正
- **PR #122** fix(ui): badge modal 整体滚动, 图片保持 400px heroic
- **PR #121** feat(badge): one_breath calc 逻辑
- **PR #120** fix(ui): badge 表单 UI 重构
- **PR #119** feat(badge): calc 策略 commit 后显示解锁操作指引
- **PR #118** feat(badge): 支持导入已有图片
- **PR #117** docs(badge): 去背工作流沉淀 V2.5
- **PR #116** fix(curses): CJK 宽字符截断按显示宽度而非字符数

### P2 Research 范围 (待定)

| 命令 | 当前问题 | research 方向 |
|------|----------|--------------|
| `practice thisweek` | 只打印 Panel + 简单 Table | 应有日历热力图 + 项目分布 |
| `practice today` | 仅 Panel + 简单 Table | 借鉴 practice_query.today |
| `practice stats` | 仅 3 行 console + 简单 Table | 应有趋势图 + 项目分布 |
| `practice calendar` | 仅日历视图 | 可加月度摘要 |
| `lesson stats` | 多个 function 各自格式 | 统一视觉风格 |
| `payment status` | 5 行 console 拼接 | 应用 Rich Table |

**优先级**: P2 research 待用户拍板后独立 PR。
