# STATUS.md — dizical 项目状态

**最后更新**: 2026-07-11 (report 页月份左右切换 PR #145)
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
