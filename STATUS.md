# 🎵 dizical 竹笛课程管理助手 - 当前开发状态

**最后更新**: 2026-05-14 16:30
**当前阶段**: behavior_log + report 日历选择 UI + 练习轨迹对比

## 阶段记录

**今日提交 (2026-05-14)**:
- `b612c3d` — feat: behavior_log + report UI + calendar selection
- `2da33a3` — fix: achievements locked card overlay - SVG b-lock sizing + grey mask; badges GSAP entrance; practice items JSON robustness
- `c9d6c09` — feat: 勋章墙重构 - 音乐之旅成就/弹窗详情/克制标签/简化卡片/解锁排序
- `b8c11dd` — fix: top2只展示第2名科目/top3只展示第3名科目
- `3e0e7f2` — feat: 勋章墙标签样式/段位金/巅峰紫/突破红/执着蓝/晋级绿细体胶囊
- `93a2d9c` — feat: top成就按未归档科目统计/弹窗condition直接展示科目名+时长
- `fix: 移除badges_page中多余的conn.close()避免关闭共享连接导致其他页面500`

**历史分支**:
- `feat/kid-ui-refresh` — Kid UI Phase 1: badge图片/praise返回按钮/练习记录删除，已合并
- `main` — 本次 session: 勋章墙 v4 重构（弹窗/标签/简化卡片/TOP科目）

---

## 📂 项目位置

- **main 分支 (生产)**: `/Users/mt16/dev/dizical/`
- **Git 模式**: 直接在 main 开发，未使用 worktree
- **remote**: origin/main 已切 SSH，正常连接

---

## ✅ 已完成

### 核心模块
- [x] `src/models.py` - Pydantic 数据模型 (Lesson, Payment, Settings, DailyPractice 等)
- [x] `src/database.py` - SQLite 操作封装 (DatabaseManager)
- [x] `src/lesson_manager.py` - 课程管理核心逻辑
- [x] `src/holiday.py` - 节假日识别 (chinese-calendar 库)
- [x] `src/payment.py` - 缴费计算逻辑
- [x] `src/cli.py` - Typer CLI + Rich TUI
- [x] `src/practice.py` - 练习追踪（打卡/统计/日历/热力图）
- [x] `src/practice_config.py` - 大科目/小科目增删改查 TUI
- [x] `src/notifier.py` - 通知格式化
- [x] `src/obsidian.py` - Obsidian Markdown 导出
- [x] `src/reminders.py` - Apple Reminders 双向同步 + 自然语言解析

### 配置文件
- [x] `requirements.txt` - 依赖清单
- [x] `pyproject.toml` - 项目配置
- [x] `setup.py` - 包配置
- [x] `.env.example` - 环境变量示例
- [x] `.gitignore`

### 测试
- [x] `tests/test_holiday.py` - 14 个测试
- [x] `tests/test_lesson.py` - 21 个测试
- [x] `tests/test_payment.py` - 14 个测试
- 总计: 49 个单元测试

### CLI 命令（完整列表）
```bash
# 状态监控
dizical status                 # 实时 dashboard（进程/端口/HTTP/练习记录）3秒自动刷新，Q退出

# 课程
dizical lesson generate 2026-05    # 生成月度课程
dizical lesson list                 # 课程列表
dizical lesson calendar             # 日历视图

# 缴费
dizical payment status              # 缴费状态
dizical payment history             # 缴费历史

# 练习追踪
dizical practice log 单吐:20        # 打卡
dizical practice today              # 今日练习
dizical practice week               # 本周练习
dizical practice calendar 4         # 4月日历视图
dizical practice stats 4            # 4月统计
dizical practice items              # 练习项目库
dizical practice category list      # 大科目列表
dizical practice category add 气息  # 新增大科目
dizical practice category set-item 单吐练习 基本功  # 设置小科目归属
dizical practice config             # 增删改查 TUI（配置管理）
dizical practice query              # 交互式练习查询 TUI
dizical practice import <csv>               # 导入时长 CSV
dizical practice import_logs <csv>         # 批量导入进展 log
dizical practice assign -d <YYYY-MM-DD> <项目:要求> [-i <图片路径>]  # 录入每周老师要求（含配图）
dizical practice assign -d <date> <4:要求> <1224:要求>  # 用 practice_item_id 精准命中科目
dizical practice assignments             # 查询每周老师要求
dizical practice import-assignments <csv>  # 批量导入每周老师要求

# 同步
dizical reminders sync              # 同步 Reminders
dizical obsidian export 4          # 导出4月报告
```

---

## 📊 数据库设计

两个 SQLite 数据库：`data/dizi.db`（课程+缴费）、`data/dizical.db`（练习）

**dizi.db 表**: lessons, payments, settings
**dizical.db 表**: practice_items, daily_practices, practice_config, teacher_requirements

---

## 👧 Kid UI Phase 2 完成（2026-05-08）

### 本次 Session 完成
- [x] **底部 Tab 导航** - 5个页面全部改为 position:fixed bottom，适合 iPad 单手操作
- [x] **practice_config TUI 重构** - 每个子菜单 while True 自循环，q 逐层返回，消灭死角
- [x] **practice_config 归档菜单** - 选项4：进菜单先显示已归档清单，unarchive 行为修正
- [x] **kid-ui 归档逻辑** - 已归档小科目默认隐藏，底部归档区按钮点击后弹窗选择
- [x] **practice log 逗号分隔** - 支持 `单吐:7，回娘家:4` 中文/英文逗号多种格式
- [x] **practice log 默认日期修正** - 从"昨天"改为"今天"，与 `practice today` 一致
- [x] **save_daily_practice 追加修复** - 同日期多次 log 改为合并（同名累加），不再覆盖
- [x] **修复归档 q 键无效** - `_archive_choose` 两次 `input()` 导致第二次读空字符串
- [x] **修复排序验证缺失** - `_category_sort` 增加重复ID检查 + 完整性覆盖检查

### 历史提交 (2026-05-08)
| Commit | 内容 |
|--------|------|
| `5d33c74` | docs: 更新README - kid-ui底部Tab/归档/CLI逗号分隔 |
| `ced8c4c` | feat(cli): practice log 支持逗号分隔多条记录 |
| `4b47107` | fix(database): save_daily_practice 改为追加合并而非整体替换 |
| `673b36e` | fix(cli): practice log 默认日期改为今天，与 practice today 一致 |
| `290b6a1` | fix(practice-config): 修复归档q键无效+排序验证缺失 |
| `9eeeb01` | refactor(practice-config): 全面重构TUI交互规范 |
| `f546d00` | feat(kid-ui): 固定底部Tab导航 + practice_config归档管理 |
| `a57140b` | feat(kid-ui): 4项优化 - 老科目归档/底部Tab/计时保护/快速录入/全屏烟花 |

## 👧 assign-phase1b 图片存储完成（2026-05-09）
- [x] `weekly_assignments` 表新增 `images TEXT` 列（迁移兼容）
- [x] `save_weekly_assignment` 支持 `images` 增量合并追加
- [x] CLI: `--image/-i` 可多次指定配图路径，录入后显示「📷 N 张已保存」
- [x] 查询显示「📷 N 张配图」，增量追加不丢失已有图片
- [x] `.gitignore`: `data/assignment_images/` 忽略
- [x] 使用指南：DB 路径合并，配图目录说明
- [x] 修复 iter 双重消费 bug（`img_list` 避免重复遍历）
- Commit: `4f62e66` | 49/49 tests pass

## 👧 assignments 阶段模型重构（2026-05-10）
- [x] `weekly_assignments` 表新增 `stage_start`、`stage_end`、`stage_order` 字段
- [x] `stage_start` = 上课后一天；`stage_end` = 下一节课当天；`stage_order` = 上课序号
- [x] 显示格式：`第4课  04-19  ~  04-25  单吐练习  ♩=82...`
- [x] `kid_app` practice 页优先用 `item_id` 精确匹配，fallback 名称匹配
- [x] 录入支持 `item_id:要求` 格式：`dizical practice assign 4:♩=82 1224:♩=80`
- [x] 历史数据批量回填 `item_id`（weekly_assignments 45条/23条含ID，daily_practices 653条/648条含ID）

## 👧 Kid UI Phase 3 UX 优化（2026-05-11）
- [x] **fuzzy match 重写** (`practice.py`): `_similarity()` 子串/超串分级(0.85/0.60)，`_levenshtein()` 编辑距离，新评分策略避免泛称误匹配
- [x] **prepare 页面优化**: 每日鼓励语(date-seeded从12条ENCOURAGEMENTS池选取)，老师要求为空时改为「暂无老师要求，直接开始练习吧！」
- [x] **achievements 页面增强**: 本周目标进度条(7天/周)，勋章墙落地页/badge图片，布局改为单列全宽卡片
- [x] **praise 页面重建** (方案A): 展示已解锁徽章+每日表扬语+截图分享，孩子iPad可独立操作，移除 Hermes redirect 依赖
- pytest 49/49 ✅

## 👧 kid-app 服务状态监控（2026-05-11）
- [x] **`dizical status` 命令**: curses TUI 实时 dashboard，监控 kid-app 进程/PID、端口 8765 监听、HTTP /prepare 响应+耗时
- [x] **显示内容**: 进程状态 ✅/❌、端口监听 ✅/❌、HTTP 200 ✅/⚠️/❌、iPad 访问地址、最近练习记录
- [x] **交互**: Q/Esc 退出，R 手动刷新，自动每 3 秒刷新
- [x] 入口: `dizical status`

## 👧 prepare 新样式完成（2026-05-11）
- [x] **新配色**：cream/sage绿/rose粉渐变/lavender紫，iPad 3:2 响应式断点（2266×1488）
- [x] **GSAP ScrollTrigger 入场动画**：hero 渐次淡入、step cards 滚动触发、CTA 弹性按钮
- [x] **全局点击滚一屏**：逐屏 hero→steps→assignment→CTA，floatingTap 浮动提示（右下角）
- [x] **后端可配置化**：BLESS_POOL(12条)/PREPARE_STEPS/CTA 文案，app.py render 动态生成
- [x] **toggleStep**：点击勾选 + localStorage 每日重置持久化
- [x] **DB 修复**：weekly_assignments stage_end 2026-03-14→2026-05-17
- [x] **swap 兜底**：stage_start > stage_end 时自动交换
- Commit: `8eae04a` | PR #26 ✅

### 历史遗留问题（已归档）
- ~~**feat/prepare-gsap-scrolltrigger 分支**~~（已删除）：曾实现"步骤式检查逻辑"——三个准备工作依次点完→展示本周 assignment→流畅滚动到开始按钮。该分支从未合并 main，且模板仅 215 行（半成品），style 与当前 main 不兼容。**决定：舍弃，main 当前 ScrollTrigger 实现为正式版本**。
- ~~**待办**：将步骤式逻辑以 CSS transition 方式重新实现到 main 当前版本（或合并分支时解决冲突）~~ **已归档**：该方案已废弃，main ScrollTrigger 为正式版

## 👧 数据结构统一（2026-05-10）
- [x] `practice_items.id` → `item_id`（表列已改名）
- [x] `practice_items` 表外键：`category_id`（引用 `practice_categories.id`）
- [x] `weekly_assignments.items` JSON：增加 `item_id` 字段（fuzzy match 回填）
- [x] `daily_practices.items` JSON：增加 `item_id` 字段（fuzzy match 回填，653条中648条已回填）
- [x] `daily_practices` 表：新增 `practiced TEXT NOT NULL DEFAULT 'Y'`（Y=已练习，N=未练习如病假）
- [x] `save_daily_practice`：写入时自动 fuzzy-match 回填 `item_id`
- [x] `save_weekly_assignment`：写入时自动 fuzzy-match 回填 `item_id`
- [x] `DailyPracticeLog` Pydantic 模型：增加 `practiced` 字段
- [x] 所有代码引用：`item['id']` → `item['item_id']`，`practice_item_id` → `item_id`
- 迁移脚本：`src/migrate_item_id.py`（可重复安全执行）

## 👧 item_id 四位数重编号（2026-05-10）
- [x] `practice_items.item_id` 从原值（1~1335）重写为 1001~1039 四位序号
- [x] `weekly_assignments.items` JSON 全部 209 条同步更新
- [x] `daily_practices.items` JSON 全部更新
- [x] 历史数据错配修正：`基本功-长音` → 1037，`基本功-颤音` → 1035
- [x] `save_weekly_assignment` / `save_daily_practice` / `get_weekly_assignment` 入参 string→date 转换修复
- [x] CLI 示例 ID 更新：`4` → `1003`（单吐练习），`1224` → `1026`（采茶扑蝶）
- 迁移脚本：`src/migrate_renumber_item_id.py`（dry-run 验证后再执行）
- pytest 49/49 ✅，kid_app 5路由 200 ✅

## 🚀 下一步开发计划

### 优先级 P0 - 数据安全 ✅ 全部完成
1. **数据库备份** - ✅ 本地 `data/backups/`
2. **备份 iCloud 同步** - ✅ 自动同步到 iCloud 目标路径
3. **备份验证** - ✅ `sqlite3` 连接验证

### 优先级 P1 - 练习录入防误录 ✅
4. **模糊匹配 + 确认拦截** - 已完成（_similarity / find_similar_items / practice_log 拦截）

---

## 🧪 测试命令

```bash
cd /Users/mt16/dev/dizical/
python3 -m pytest tests/ -v           # 运行所有测试
python3 -m pytest tests/test_holiday.py::TestHolidayChecker::test_is_holiday_may_day -v  # 单个测试

# 手动功能测试
dizical lesson generate 2026-05
dizical lesson list
dizical practice calendar 4
dizical practice stats 4
```

---

## 📝 开发规范

- 使用 PEP8 代码风格
- 完整的类型注解 (type hints)
- 每个功能要有对应的单元测试
- 提交信息格式: `feat: xxx` / `fix: xxx` / `docs: xxx` / `chore: xxx`
- Git worktree 模式：功能开发在 `.worktrees/hermes-xxx` 分支，测试通过后合到 main
- PR 流程：改代码 → 本地调试 → 报结果 → 用户确认 → 再提 PR
- **开发收尾**：每次 session 结束前更新 `STATUS.md` 和 `DEVELOPMENT_PLAN.md`，保持后续接手 agent 可读

---

## 🔧 环境

- Python 3.14
- 依赖已通过 `pip install -e .` 安装
- `dizical` CLI 命令已在 PATH 中可用
- 数据库: SQLite (`data/dizical.db`, `data/dizi.db`)
