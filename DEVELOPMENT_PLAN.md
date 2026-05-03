# 🎵 dizical 竹笛课程管理助手 - 开发计划

## 📋 项目概述
竹笛课程管理 + 缴费提醒 + 练习追踪 + Apple Reminders 双向同步，支持可视化报表和定期数据备份。

**作者**: mtt
**创建时间**: 2026-04-25
**最后更新**: 2026-05-03 15:25

---

## 🎯 核心功能（已实现）

### 1. 课程管理
- **默认规则**: 每周六 17:15 上课
- **支持操作**: 添加、取消、调课、确认上课
- **节假日自动识别**: 使用 `chinese-calendar` 库，自动标记国定假日并提醒确认

### 2. 缴费管理
- **学费**: 600元/节，**只收现金**
- **缴费时间**: 每月最后一次上课时缴清当月费用
- **智能提醒**: 自动计算当月最后一个上课日，提前2天提醒

### 3. 练习追踪
- **打卡**: `dizical practice log 单吐:20`
- **日历视图**: ASCII 日历 + 热力图 + 进展记录
- **统计**: 月度/周度练习时长统计
- **项目库**: 大科目/小科目两级结构
- **每周老师要求**: 批量导入，自动关联周开始日期
- **practice config TUI**: 增删改查模式管理科目

### 4. Apple Reminders 双向同步
- **监控列表**: `dizi`
- **支持指令解析**:
  - `取消 5月9日` → 取消课程
  - `加课 5月16日` → 添加课程
  - `缴费 1800` → 记录缴费1800元
  - `改时间 5月9日 到 5月16日` → 调课

### 5. Obsidian 导出
- 月度报告模板
- Markdown 格式写入 Obsidian 库

### 6. 练习报告信息图（规划中）
- 通过 Hermes skill 调用 image generation 能力
- 将日报/月报汇总生成可视化信息图
- 风格: 高质量数学讲义 + 手绘教育海报

---

## 🏗 技术栈

```
Python 3.10+
├── pydantic + pydantic-settings  # 数据模型 + 配置
├── sqlite3                       # 数据库 (内置)
├── typer + rich                  # CLI + TUI 界面
├── python-telegram-bot[v20]      # Telegram 通知
├── chinese-calendar              # 中国节假日识别
├── remindctl (CLI)               # Apple Reminders 集成
└── Hermes Agent                  # Skill / Image Generation / Cron
```

---

## 📁 项目结构

```
dizical/
├── src/
│   ├── __init__.py
│   ├── models.py              # Pydantic 数据模型
│   ├── database.py            # SQLite 操作封装
│   ├── lesson_manager.py      # 课程管理核心逻辑
│   ├── payment.py             # 缴费计算逻辑
│   ├── holiday.py             # 节假日识别
│   ├── practice.py            # 练习追踪
│   ├── practice_config.py     # 大科目/小科目增删改查 TUI
│   ├── practice_query.py      # 交互式练习查询 TUI（今日/本周/月历/历史/搜索）
│   ├── notifier.py            # 通知格式化
│   ├── reminders.py           # Apple Reminders 同步 + 指令解析
│   ├── obsidian.py            # Obsidian Markdown 导出
│   └── cli.py                 # Typer CLI 入口
├── data/                       # SQLite 数据文件 (.gitignore)
│   ├── dizi.db                # 课程 + 缴费数据
│   └── dizical.db             # 练习追踪数据
├── tests/
│   ├── test_lesson.py
│   ├── test_payment.py
│   └── test_holiday.py
├── docs/                       # docs/使用指南.md, docs/表结构.md
├── .env.example
├── requirements.txt
├── pyproject.toml
├── setup.py
├── STATUS.md                   # 当前开发状态
├── DEVELOPMENT_PLAN.md         # 本文档
└── README.md
```

---

## 📊 数据库设计

### dizi.db - 课程与缴费

#### lessons 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| date | DATE | 上课日期 (YYYY-MM-DD) |
| time | TIME | 上课时间 (HH:MM, 默认 17:15) |
| status | TEXT | scheduled/attended/cancelled |
| fee | INTEGER | 学费 (默认 600) |
| fee_paid | BOOLEAN | 是否已缴费 |
| is_holiday_conflict | BOOLEAN | 是否与节假日冲突 |
| notes | TEXT | 备注 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

#### payments 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| payment_date | DATE | 缴费日期 |
| amount | INTEGER | 缴费金额 |
| lesson_ids | TEXT | 覆盖的课程 ID (逗号分隔) |
| payment_method | TEXT | 固定为 '现金' |
| notes | TEXT | 备注 |
| created_at | DATETIME | 创建时间 |

#### settings 表
| 字段 | 类型 | 说明 |
|------|------|------|
| key | TEXT PK | 配置键 |
| value | TEXT | 配置值 |
| updated_at | DATETIME | 更新时间 |

### dizical.db - 练习追踪

#### practice_items 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| name | TEXT | 练习项目名称 |
| category_id | INTEGER FK | 所属大科目 |
| created_at | DATETIME | 创建时间 |

#### daily_practices 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| date | DATE | 练习日期 (YYYY-MM-DD) |
| total_minutes | INTEGER | 总时长 (分钟) |
| log | TEXT | 详细练习进展 |
| created_at | DATETIME | 创建时间 |

#### daily_practice_items 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| daily_practice_id | INTEGER FK | 关联每日练习 |
| practice_item_id | INTEGER FK | 关联练习项目 |
| minutes | INTEGER | 时长 (分钟) |

#### practice_categories 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| name | TEXT | 大科目名称 |
| parent_name | TEXT | 保留字段 (统一用 name) |

#### teacher_requirements 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| week_start | DATE | 周开始日期 (周一) |
| item | TEXT | 练习项目 |
| requirement | TEXT | 具体要求 |

---

## ⌨️ CLI 命令列表

```bash
# 课程管理
dizical lesson generate 2026-05    # 生成5月课程计划
dizical lesson list                 # 本月课程列表
dizical lesson list 2026-05         # 指定月份
dizical lesson add 2026-05-03      # 添加课程
dizical lesson cancel 2026-05-03   # 取消课程
dizical lesson reschedule 2026-05-03 2026-05-10  # 调课
dizical lesson confirm 2026-05-03   # 确认已上课

# 缴费管理
dizical payment status              # 查看当前应缴状态
dizical payment record 1800         # 记录缴费1800元(现金)
dizical payment history             # 缴费历史

# 练习追踪
dizical practice log 单吐:20        # 打卡
dizical practice log 单吐:10 --log "突破5连吐"  # 打卡+进展记录
dizical practice today              # 今日练习
dizical practice week               # 本周练习
dizical practice calendar 4         # 4月日历视图
dizical practice stats 4            # 4月统计
dizical practice items              # 练习项目库
dizical practice category list     # 大科目列表
dizical practice category add 气息练习  # 新增大科目
dizical practice category set-item 单吐练习 基本功  # 设置小科目归属
dizical practice config             # 增删改查 TUI（配置管理）
dizical practice query              # 交互式练习查询 TUI（今日/本周/月历/历史/搜索）
dizical practice import <csv>               # 导入时长 CSV
dizical practice import_logs <csv>          # 批量导入进展 log
dizical practice import-assignments <csv>   # 批量导入每周老师要求

# 同步
dizical reminders sync             # 同步 Reminders
dizical obsidian export 4          # 导出4月报告

# 备份
dizical backup run                 # 执行数据库备份
dizical backup list                # 查看备份状态
```

---

## 🧪 开发阶段计划

### ✅ 第一阶段：核心数据层
- [x] 数据模型 (models.py)
- [x] 数据库操作封装 (database.py)
- [x] 节假日识别 (holiday.py)

### ✅ 第二阶段：业务逻辑层
- [x] 课程管理核心 (lesson_manager.py)
- [x] 缴费计算逻辑 (payment.py)
- [x] 练习追踪 (practice.py)
- [x] practice_config TUI (practice_config.py)

### ✅ 第三阶段：CLI 界面
- [x] Typer CLI 入口 (cli.py)
- [x] Rich TUI 美化输出
- [x] practice_query.py 交互式练习查询 TUI

### ✅ 第四阶段：通知系统
- [x] Telegram 通知封装 (notifier.py)
- [x] Apple Reminders 同步 (reminders.py)
- [x] 指令解析 (自然语言理解)

### ✅ 第五阶段：集成与测试
- [x] 单元测试 (49 个测试)
- [x] Obsidian 导出
- [x] README 完整文档
- [x] practice_config 增删改查 TUI

### ✅ 第六阶段：数据安全与可视化
- [x] 数据库自动备份到本地 (`src/backup.py`, `dizical backup run/list`)
- [x] 练习报告信息图生成 (dizical-report skill via Hermes image generation)
- [x] 使用指南 (docs/使用指南.md) + 表结构文档 (docs/表结构.md)
- [x] Datasette 数据库查询方案

---

## 🔧 数据库备份方案（规划）

### 需求
- 定期备份 `data/dizi.db` 和 `data/dizical.db` 到本地
- 保留多版本历史备份
- 备份验证机制

### 实现方案
1. **备份脚本**: `src/backup.py`
2. **备份频率**: 每小时一次（通过 Hermes cron）
3. **备份保留**: 最近 7 天 + 每周日 20:00 额外备份当月版本
4. **备份位置**: `data/backups/` 目录下
5. **备份命名**: `{db_name}_{YYYYMMDD_HHMMSS}.db`

---

## 🎨 练习报告信息图方案（规划）

### 需求
通过 Hermes skill 调用 image generation 能力，将练习数据生成可视化信息图

### 使用方式
```
用户: "生成2026年4月练习汇总报告"
Skill: 获取练习数据 → 生成 image generation prompt → 输出图片
```

### 信息图内容
- 月度练习总时长、练习天数
- 各科目练习时长占比
- 每日练习热力图
- 老师每周要求完成情况
- 进展记录亮点

### 视觉风格
- 竖版或横版均可
- 干净的浅色纸张背景
- 深蓝标题，黑色/深灰正文线条
- 少量优雅的蓝色、青绿色、金色、红色强调色
- 圆角卡片、细线边框、编号标签、手绘箭头
- 局部放大框和总结栏
- 整体: 美观、平衡、有学术感

### 技术实现
- 创建 `dizical-report` skill
- skill 调用 dizical CLI 获取报告数据
- 生成详细的 image prompt
- 使用 Hermes image_generate 工具输出

---

## 📝 业务规则细节

### 节假日识别规则
1. 每月1日生成课程计划时，调用 `chinese_calendar.get_holiday_detail()`
2. 如果是节假日，标记 `is_holiday_conflict=True`，notes 填节假日名称
3. 提醒时显示 ⚠️ 标记，等待用户确认

### 缴费提醒逻辑
```python
def get_last_lesson_date(year, month):
    # 找到当月所有周六
    # 过滤已取消的课程
    # 返回最后一个上课日
    return last_saturday

def get_payment_reminder_date(last_lesson_date):
    # 提前2天提醒
    return last_lesson_date - timedelta(days=2)
```

### Reminder 指令解析规则
支持自然语言模糊匹配：
- 包含 "取消" + 日期 → 取消课程
- 包含 "请假" + 日期 → 取消课程
- 包含 "加课" + 日期 → 添加课程
- 包含 "缴费" + 金额 → 记录缴费
- 包含 "改" + 日期 + "到" + 日期 → 调课

---

## 🔧 配置说明

### .env 文件
```env
REMINDER_LIST_NAME=dizi
OBSIDIAN_PATH=/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/
DEFAULT_FEE=600
DEFAULT_TIME=17:15
DEFAULT_WEEKDAY=5
DB_PATH=data/dizi.db
DIZICAL_DB_PATH=data/dizical.db
```

### Hermes Cron 任务（已配置）
```bash
# 每月1日 09:00 - 生成当月课程计划
0 9 1 * * dizi remind monthly

# 每周日 20:00 - 同步 Reminders
0 20 * * 0 dizi reminders sync

# 每天 10:00 - 检查缴费提醒
0 10 * * * dizi remind payment

# 每天 8:00 / 18:00 - Reminders sync
0 8,18 * * * dizi reminders sync
```

---

## ✅ 验收标准

1. `dizical lesson generate 2026-05` 能正确生成5月所有周六课程，标记劳动节
2. `dizical payment status` 能正确计算应缴金额
3. `dizical reminders sync` 能解析 Reminders 中的简单指令
4. `dizical practice config` 增删改查 TUI 正常工作
5. 所有单元测试通过
6. 数据库每日自动备份
7. 可通过 skill 生成练习报告信息图

---

## 📌 注意事项

- 时区统一使用 Asia/Shanghai (UTC+8)
- 所有日期时间操作使用 datetime.date/datetime.time，避免时区问题
- 数据库操作使用参数化查询，防止 SQL 注入
- 所有对外接口有异常处理和重试机制
- 配置通过 pydantic-settings 统一管理

---

**开发收尾**：每次 session 结束前更新 `STATUS.md` 和 `DEVELOPMENT_PLAN.md`，保持后续接手 agent 可读。
