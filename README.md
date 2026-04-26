# 🎵 dizical

> 竹笛课程管理 + 缴费提醒 + Apple Reminders 双向同步

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/tests-49%20passed-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/lessons-211%20days%20imported-blue" alt="Lessons">
</p>

## 🤔 为什么叫 dizical？

```
dizi + cal(endar) = dizical
 竹笛    日历        ↓
            发音 ≈ Descartes（笛卡尔）

📅 管它什么哲学，我只要管好我的竹笛课表 🎵
```

---

## ✨ Features

- 📅 **自动排课** - 每周六自动生成课程，节假日冲突检测
- 💰 **缴费管理** - 自动统计欠缴、已缴，最后一节课当天提醒
- 🍎 **Reminders 同步** - 在 Apple Reminders 写自然语言就能操作
- 🔔 **Telegram 通知** - 上课提醒/缴费提醒/月度计划，自动推送
- 📊 **可视化课表** - 表格视图 + ASCII 日历视图
- 📝 **Obsidian 导出** - 自动生成月度学习报告
- 🎵 **练习追踪** - 打卡、统计、热力图、老师每周要求导入

## 🚀 Quick Start

```bash
# 安装
pip install -e .

# 生成课程
dizical lesson generate 2026-05

# 查看课表
dizical lesson list
dizical lesson calendar

# 同步 Reminders
dizical reminders sync
```

## ⚙️ Configuration

创建 `.env` 文件：

```env
REMINDER_LIST_NAME=dizi
OBSIDIAN_PATH=/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/
DEFAULT_FEE=600
DEFAULT_TIME=17:15
DEFAULT_WEEKDAY=5
DB_PATH=data/dizi.db
```

## 📦 Commands

```bash
# 课程
dizical lesson list           # 课程表
dizical lesson calendar       # 日历视图
dizical lesson generate 2026-05

# 缴费
dizical payment status        # 缴费状态
dizical payment history       # 缴费历史

# 练习
dizical practice log 基本功:20 单吐:15  # 打卡
dizical practice today        # 今日练习
dizical practice week         # 本周练习
dizical practice calendar 4   # 4月日历
dizical practice stats 4      # 4月统计
dizical practice import <csv> # 导入CSV

# 同步
dizical reminders sync        # 同步 Reminders
dizical obsidian export 4     # 导出4月报告
```

## 🏗️ Architecture

```
src/
├── cli.py            # CLI 入口
├── lesson_manager.py # 课程管理
├── payment.py        # 缴费管理
├── practice.py       # 练习追踪（打卡/统计/导入）
├── reminders.py      # Apple Reminders 同步
├── notifier.py       # 通知格式化
├── obsidian.py       # Obsidian Markdown 导出
├── database.py       # SQLite 持久化
└── models.py         # 数据模型
```

## 📄 License

MIT
