# 🎵 dizical 竹笛课程管理助手 - 当前开发状态

**最后更新**: 2026-05-03 15:25
**当前阶段**: 遗留问题修复 — STATUS.md/DEVELOPMENT_PLAN.md 日期修正，worktree/main 同步

---

## 📂 项目位置

- **main 分支 (生产)**: `/Users/mt16/dev/dizical/`
- **hermes 分支 (当前会话 worktree)**: `/Users/mt16/dev/dizical/.worktrees/hermes-eb075c87/`
- **Git 模式**: worktree 模式，hermes/hermes-eb075c87 与 main 完全同步
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

## 📦 待提交改动

| 文件 | 说明 |
|------|------|
| 无 | 所有代码已提交并同步，worktree 与 main 完全同步 |

## 🔄 最近提交 (2026-05-02)

| Commit | 内容 |
|--------|------|
| `3d8eae8` | fix: TUI 进度条 █ → = (macOS BSD curses 无 ACS_BLOCK) |
| `413bb89` | fix: 恢复 █ 填充符，cli/rich 进度条保持 █，TUI 用 = |
| `74abed2` | fix: 进度条填充满字符 # → = |

## 🚀 下一步开发计划

### 优先级 P0 - 数据安全
1. **数据库备份** - 定期自动备份 SQLite 文件到本地（防止数据丢失）
2. **备份恢复验证** - 确保备份可还原

### 优先级 P1 - 可视化报表
3. **练习报告信息图** - 通过 Hermes skill 调用 image generation 能力，将日报/月报汇总生成可视化信息图
4. **Skill 集成** - 创建 dizical-report skill，封装报告生成逻辑

### 优先级 P2 - 增强功能
5. **复习计划优化** - 基于老师每周要求智能生成复习建议
6. **进度提醒增强** - 根据练习数据动态调整提醒策略

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

- Python 3.12+
- 依赖已通过 `pip install -e .` 安装
- `dizical` CLI 命令已在 PATH 中可用
- 数据库: SQLite (`data/dizical.db`, `data/dizi.db`)
