"""
Obsidian Markdown 导出模块
将竹笛学习数据导出为 Obsidian 可读的 Markdown 文件
"""

import os
import datetime as dt
from pathlib import Path
from typing import Optional, List

from .database import db


class ObsidianExporter:
    """Obsidian Markdown 导出器"""

    def __init__(self, base_path: Optional[str] = None):
        """
        初始化

        Args:
            base_path: Obsidian 库路径，默认从环境变量读取
        """
        if base_path is None:
            base_path = os.getenv(
                "OBSIDIAN_PATH",
                "/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/",
            )
        self.base_path = Path(base_path)
        self.dizi_path = self.base_path / "dizi-helper"

    def _ensure_dir(self, path: Path) -> None:
        """确保目录存在"""
        path.mkdir(parents=True, exist_ok=True)

    def export_monthly_report(self, year: int, month: int) -> str:
        """
        导出月度报告

        Args:
            year: 年份
            month: 月份

        Returns:
            导出文件的绝对路径
        """
        # 获取当月数据
        lessons = db.get_lessons_by_month(year, month)
        payments = db.get_payments_by_month(year, month)

        # 过滤已缴费的课程
        paid_lessons = [l for l in lessons if l.fee_paid]
        unpaid_lessons = [l for l in lessons if not l.fee_paid]

        total_paid = sum(l.fee for l in paid_lessons)
        total_unpaid = sum(l.fee for l in unpaid_lessons)

        # 生成 Markdown
        month_name = f"{year}年{month:02d}月"
        file_path = self.dizi_path / f"{year}-{month:02d}-竹笛学习月报.md"
        self._ensure_dir(file_path.parent)

        content = f"""# {month_name} 竹笛学习月报

## 📅 课程统计

| 项目 | 数量 |
|------|------|
| 计划课程 | {len(lessons)} 节 |
| 已上课 | {len([l for l in lessons if l.status.value == 'attended'])} 节 |
| 已取消 | {len([l for l in lessons if l.status.value == 'cancelled'])} 节 |
| 已缴费 | {len(paid_lessons)} 节 |

## 💰 缴费情况

| 项目 | 金额 |
|------|------|
| 已缴 | {total_paid} 元 |
| 待缴 | {total_unpaid} 元 |

## 📝 课程详情

"""

        # 课程详情表格
        content += "| 日期 | 时间 | 状态 | 缴费 | 备注 |\n"
        content += "|------|------|------|------|------|\n"

        for lesson in sorted(lessons, key=lambda x: x.date):
            status_icon = {"attended": "✅", "cancelled": "❌", "scheduled": "📅"}.get(
                lesson.status.value, "📅"
            )
            paid_icon = "💰" if lesson.fee_paid else "⏳"
            notes = lesson.notes or ""
            content += f"| {lesson.date} | {lesson.time} | {status_icon} {lesson.status.value} | {paid_icon} | {notes} |\n"

        # 缴费历史
        if payments:
            content += "\n## 💵 缴费记录\n\n"
            content += "| 日期 | 金额 | 覆盖课程 | 备注 |\n"
            content += "|------|------|----------|------|\n"
            for p in sorted(payments, key=lambda x: x.payment_date):
                content += f"| {p.payment_date} | {p.amount}元 | {p.lesson_ids} | {p.notes or ''} |\n"

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def export_yearly_report(self, year: int) -> str:
        """
        导出年度总结

        Args:
            year: 年份

        Returns:
            导出文件的绝对路径
        """
        # 收集全年数据
        total_lessons = 0
        total_attended = 0
        total_cancelled = 0
        total_paid = 0
        monthly_stats = []

        for month in range(1, 13):
            lessons = db.get_lessons_by_month(year, month)
            if not lessons:
                continue

            total_lessons += len(lessons)
            total_attended += len([l for l in lessons if l.status.value == "attended"])
            total_cancelled += len([l for l in lessons if l.status.value == "cancelled"])
            total_paid += sum(l.fee for l in lessons if l.fee_paid)

            monthly_stats.append(
                {
                    "month": month,
                    "lessons": len(lessons),
                    "attended": len([l for l in lessons if l.status.value == "attended"]),
                    "paid": sum(l.fee for l in lessons if l.fee_paid),
                }
            )

        file_path = self.dizi_path / f"{year}-年度总结.md"
        self._ensure_dir(file_path.parent)

        content = f"""# {year} 年竹笛学习年度总结

## 📊 年度统计

| 项目 | 数量 |
|------|------|
| 计划课程 | {total_lessons} 节 |
| 实际上课 | {total_attended} 节 |
| 取消课程 | {total_cancelled} 节 |
| 已缴学费 | {total_paid} 元 |

## 📈 月度趋势

| 月份 | 课程数 | 上课数 | 已缴 |
|------|--------|--------|------|
"""

        for stat in monthly_stats:
            content += f"| {stat['month']}月 | {stat['lessons']} | {stat['attended']} | {stat['paid']}元 |\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)

    def export_weekly_practice_report(self, week_start: dt.date) -> str:
        """
        导出周练习报告

        Args:
            week_start: 周开始日期（周一）

        Returns:
            导出文件的绝对路径
        """
        from .practice import get_week_practices, get_week_stats

        practices = get_week_practices(week_start)
        stats = get_week_stats(week_start)

        week_end = week_start + dt.timedelta(days=6)
        file_name = f"practice-{week_start}-to-{week_end}.md"
        file_path = self.dizi_path / "practice" / file_name
        self._ensure_dir(file_path.parent)

        content = f"""# 🎵 {week_start} ~ {week_end} 练习周报

## 📊 本周练习统计

| 项目 | 数据 |
|------|------|
| 练习天数 | {stats['practice_days']} 天 |
| 总时长 | {stats['total_minutes']} 分钟 |
| 日均时长 | {stats['avg_minutes']:.0f} 分钟 |

## 📝 每日练习

"""

        daily: List[dict] = practices.get("daily", [])
        for day_data in daily:
            content += f"### {day_data['date']}\n\n"
            content += f"总时长: {day_data['total_minutes']} 分钟\n\n"

            items = day_data.get("items", [])
            if items:
                content += "| 项目 | 时长 |\n|------|------|\n"
                for item in items:
                    content += f"| {item['item']} | {item['minutes']} 分钟 |\n"
                content += "\n"

            progress = day_data.get("progress_note")
            if progress:
                content += f"📝 进展: {progress}\n\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)


# 全局单例
_exporter: Optional[ObsidianExporter] = None


def get_exporter() -> ObsidianExporter:
    """获取全局导出器实例"""
    global _exporter
    if _exporter is None:
        _exporter = ObsidianExporter()
    return _exporter
