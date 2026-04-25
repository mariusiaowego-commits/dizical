"""
Obsidian Markdown 导出模块
将课程记录和缴费历史导出为 Markdown 文件，便于在 Obsidian 中查阅
"""
import os
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from .models import Lesson, Payment

load_dotenv()


class ObsidianExporter:
    """Obsidian Markdown 导出器"""

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.getenv(
            "OBSIDIAN_PATH",
            "/Users/mt16/Library/Mobile Documents/iCloud~md~obsidian/Documents/"
        )
        self.dizi_dir = Path(self.base_path) / "dizi-helper"
        self.dizi_dir.mkdir(parents=True, exist_ok=True)

    def _format_currency(self, amount: int) -> str:
        """格式化金额"""
        return f"{amount} 元"

    def _format_date(self, d: date) -> str:
        """格式化日期"""
        return d.strftime("%Y年%m月%d日")

    def export_monthly_report(self, year: int, month: int,
                               lessons: List[Lesson],
                               payments: List[Payment],
                               total_fee: int,
                               paid_amount: int) -> str:
        """
        导出月度报告

        Args:
            year: 年份
            month: 月份
            lessons: 课程列表
            payments: 缴费列表
            total_fee: 总学费
            paid_amount: 已缴金额

        Returns:
            生成的文件路径
        """
        # 统计信息
        scheduled = sum(1 for l in lessons if l.status == 'scheduled')
        attended = sum(1 for l in lessons if l.status == 'attended')
        cancelled = sum(1 for l in lessons if l.status == 'cancelled')
        balance = total_fee - paid_amount

        # 生成 Markdown
        lines = [
            f"# {year}年{month}月 竹笛学习记录",
            f"",
            f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"",
            f"## 📊 本月统计",
            f"",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总课程 | {len(lessons)} 节 |",
            f"| 已上课 | {attended} 节 |",
            f"| 待上课 | {scheduled} 节 |",
            f"| 已取消 | {cancelled} 节 |",
            f"| 总学费 | {self._format_currency(total_fee)} |",
            f"| 已缴费 | {self._format_currency(paid_amount)} |",
            f"| **余额** | **{self._format_currency(balance)}** |",
            f"",
            f"## 📅 课程记录",
            f"",
            f"| 日期 | 时间 | 状态 | 学费 | 缴费 | 备注 |",
            f"|------|------|------|------|------|------|",
        ]

        status_map = {
            'scheduled': '📋 已安排',
            'attended': '✅ 已上课',
            'cancelled': '❌ 已取消',
        }

        for lesson in sorted(lessons, key=lambda l: l.date):
            status = status_map.get(lesson.status, str(lesson.status))
            fee_paid = '✅' if lesson.fee_paid else '❌'
            notes = []
            if lesson.is_holiday_conflict:
                notes.append('⚠️ 节假日冲突')
            if lesson.notes:
                notes.append(lesson.notes)

            lines.append(
                f"| {self._format_date(lesson.date)} "
                f"| {lesson.time} "
                f"| {status} "
                f"| {self._format_currency(lesson.fee)} "
                f"| {fee_paid} "
                f"| {', '.join(notes)} |"
            )

        lines.extend([
            f"",
            f"## 💰 缴费记录",
            f"",
            f"| 日期 | 金额 | 备注 |",
            f"|------|------|------|",
        ])

        for payment in sorted(payments, key=lambda p: p.payment_date):
            lines.append(
                f"| {self._format_date(payment.payment_date)} "
                f"| {self._format_currency(payment.amount)} "
                f"| {payment.notes or ''} |"
            )

        lines.extend([
            f"",
            f"## 📝 学习笔记",
            f"",
            f"### 练习重点",
            f"- [ ] ",
            f"",
            f"### 曲目进度",
            f"- [ ] ",
            f"",
            f"### 老师点评",
            f"- ",
            f"",
        ])

        # 写入文件
        filename = f"{year:04d}-{month:02d}-report.md"
        filepath = self.dizi_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return str(filepath)

    def export_lesson_note(self, lesson_date: date, content: str = "") -> str:
        """
        导出单次课程笔记模板

        Args:
            lesson_date: 课程日期
            content: 初始内容

        Returns:
            生成的文件路径
        """
        lines = [
            f"# {self._format_date(lesson_date)} 竹笛课",
            f"",
            f"> 上课时间: {lesson_date.strftime('%Y-%m-%d')}",
            f"",
            f"## 📝 课堂内容",
            f"",
            f"- 练习重点：",
            f"- 新学曲目：",
            f"- 老师指导：",
            f"",
            f"## 🎵 课后练习",
            f"",
            f"- [ ] 练习 30 分钟/天",
            f"- [ ] 复习曲目：",
            f"- [ ] 预习：",
            f"",
            f"## 💡 学习笔记",
            f"",
            f"{content}",
        ]

        filename = f"{lesson_date.strftime('%Y-%m-%d')}-lesson.md"
        filepath = self.dizi_dir / "lessons" / filename
        filepath.parent.mkdir(exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return str(filepath)

    def create_index(self) -> str:
        """
        创建索引页面，列出所有月度报告

        Returns:
            索引文件路径
        """
        # 查找所有报告
        reports = sorted(self.dizi_dir.glob("????-??-report.md"), reverse=True)

        lines = [
            f"# 🎵 竹笛学习记录索引",
            f"",
            f"> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"",
            f"## 📁 月度报告",
            f"",
        ]

        for report in reports:
            year_month = report.stem.replace("-report", "")
            year, month = year_month.split("-")
            lines.append(f"- [[{report.name}|{year}年{int(month)}月报告]]")

        lines.extend([
            f"",
            f"## 📊 汇总统计",
            f"",
            f"- 总报告数: {len(reports)} 个月",
            f"- 学习时长: 待统计",
            f"",
            f"## 🎯 年度目标",
            f"",
            f"- [ ] 完成全部练习",
            f"- [ ] 学会 10 首曲目",
            f"",
        ])

        filepath = self.dizi_dir / "README.md"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return str(filepath)
