"""
竹笛练习报告模板系统
支持多风格模板、参数可调、运行时可扩展
"""

import json
import datetime as dt
from typing import Dict, Any, Optional, Callable

# ---------------------------------------------------------------------------
# 模板注册表
# ---------------------------------------------------------------------------
# 每个模板是一个 dict，包含：
#   name:        str   - 模板显示名
#   description: str   - 简短描述
#   style:       str   - 视觉风格段落（开头描述 + 视觉要求）
#   layout:      str   - 布局要求段落（包含 {placeholder}）
#   data_fields: str   - 数据字段说明
#   aspect_ratio: str   - "portrait" | "landscape" | "square"
#
# 用户可通过 register_template() 动态添加新模板。
# ---------------------------------------------------------------------------

TEMPLATES: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# 预设模板 1：数学讲义风（原有风格）
# ---------------------------------------------------------------------------
TEMPLATES["academic"] = {
    "name": "数学讲义风",
    "description": "深蓝标题、浅纸底、少量青绿/金色点缀，学术感强",
    "style": """创作一张关于「竹笛练习月报」的可视化信息图，目标是帮助用户直观了解：本月练习概况、各项练习时长分布、每周练习进展、练习亮点与待改进点。

画面要像高质量数学讲义 + 手绘教育海报，优雅、清晰、信息丰富，但不要杂乱。

视觉风格：
- 竖版或横版均可，干净的浅色纸张背景
- 深蓝标题，黑色/深灰正文线条
- 少量优雅的蓝色、青绿色、金色、红色强调色
- 圆角卡片、细线边框、编号标签、手绘箭头、局部放大框和总结栏
- 整体要美观、平衡、有学术感，让人一眼看懂这个月练习得怎么样""",
    "layout": """请将以上数据转化为信息图布局，包含：
1. 标题区：{year}年{month}月练习月报
2. 核心指标卡：总练习时长{total_minutes}分钟、练习天数{practice_days}/{total_days}天
3. 各项练习时长分布（横向柱状图风格的手绘图表）：{item_bar_chart}
4. 每周练习时长趋势（{n}周：{week_mins}分钟）
5. 总结栏""",
    "data_fields": """数据说明：
- total_minutes: 本月总练习时长（分钟）
- practice_days: 有练习的天数
- total_days: 当月总天数
- item_totals: 各项练习时长 {"项目名": 分钟, ...}
- weeks: 每周汇总列表，每周total_minutes和practice_days""",
    "aspect_ratio": "portrait",
}


def register_template(
    template_id: str,
    name: str,
    description: str,
    style: str,
    layout: str,
    data_fields: Optional[str] = None,
    aspect_ratio: str = "portrait",
) -> None:
    """
    动态注册一个新模板。

    Args:
        template_id: 模板唯一标识符，如 "cute", "minimal", "vintage"
        name:         显示名称
        description:  简短描述
        style:        视觉风格段落（开头 + 视觉要求）
        layout:       布局要求段落（包含 {placeholder}）
        data_fields:  数据字段说明（可选，有默认值）
        aspect_ratio: 图片比例，默认 portrait
    """
    TEMPLATES[template_id] = {
        "name": name,
        "description": description,
        "style": style,
        "layout": layout,
        "data_fields": data_fields or (
            "数据说明：\n"
            "- total_minutes: 本月总练习时长（分钟）\n"
            "- practice_days: 有练习的天数\n"
            "- total_days: 当月总天数\n"
            "- item_totals: 各项练习时长 {\"项目名\": 分钟, ...}\n"
            "- weeks: 每周汇总列表\n"
            "- progress: 每天第一条进展记录 {\"日期\": \"进展内容\", ...}"
        ),
        "aspect_ratio": aspect_ratio,
    }


def list_templates() -> Dict[str, Dict[str, str]]:
    """返回所有可用模板的 id -> {name, description} 映射"""
    return {
        tid: {"name": t["name"], "description": t["description"]}
        for tid, t in TEMPLATES.items()
    }


def get_template(template_id: str) -> Dict[str, Any]:
    """获取指定模板，找不到则返回 academic 默认"""
    return TEMPLATES.get(template_id, TEMPLATES["academic"])


# ---------------------------------------------------------------------------
# build_prompt: 核心函数
# ---------------------------------------------------------------------------

def build_prompt(
    year: int,
    month: int,
    data: Dict[str, Any],
    template_id: str = "academic",
    extra_params: Optional[Dict[str, str]] = None,
) -> tuple[str, str]:
    """
    根据指定模板组装完整的 image prompt。

    Args:
        year:         年份
        month:        月份
        data:         get_month_summary() 返回的数据字典
        template_id:  模板 ID，默认 "academic"
        extra_params: 可选的额外布局参数，会合并进 layout.format()

    Returns:
        (prompt, aspect_ratio) 元组
    """
    tmpl = get_template(template_id)

    # 动态数据注入
    item_bars = "、".join(
        f"{k}{v}分钟" for k, v in data.get("item_totals", {}).items()
    )
    week_mins = "、".join(str(w["total_minutes"]) for w in data.get("weeks", []))

    layout_params = {
        "year": year,
        "month": month,
        "total_minutes": data.get("total_minutes", 0),
        "practice_days": data.get("practice_days", 0),
        "total_days": data.get("total_days", 0),
        "item_bar_chart": item_bars or "暂无数据",
        "n": len(data.get("weeks", [])),
        "week_mins": week_mins or "暂无数据",
    }
    if extra_params:
        layout_params.update(extra_params)

    layout = tmpl["layout"].format(**layout_params)

    prompt = (
        f"{tmpl['style']}\n"
        f"本月数据（JSON）：{json.dumps(data, default=_json_default, ensure_ascii=False)}\n"
        f"{layout}\n"
        f"{tmpl['data_fields']}"
    )

    return prompt, tmpl["aspect_ratio"]


def _json_default(obj):
    """JSON 序列化时处理 date 等非内置类型"""
    if isinstance(obj, dt.date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ---------------------------------------------------------------------------
# 便捷入口：单月练习报告
# ---------------------------------------------------------------------------

def build_monthly_report_prompt(
    year: int,
    month: int,
    template_id: str = "academic",
    extra_params: Optional[Dict[str, str]] = None,
) -> tuple[str, str, Dict[str, Any]]:
    """
    获取本月练习数据并构建 prompt。

    Returns:
        (prompt, aspect_ratio, data) - data 可用于后续处理或调试
    """
    # 延迟导入避免循环
    from .practice import get_month_summary

    data = get_month_summary(year, month)
    prompt, aspect_ratio = build_prompt(year, month, data, template_id, extra_params)
    return prompt, aspect_ratio, data


# ---------------------------------------------------------------------------
# Stage 维 report 图片 (sprint-26080103)
# ---------------------------------------------------------------------------

TEMPLATES["stage_academic"] = {
    "name": "Stage 表格 · 干净 UI 风",
    "description": "Stage 维 session 明细的 AI 配图, kami 干净 UI, 表格清晰, 不走 baoyu 可爱风",
    "style": """创作一张关于「竹笛练习明细 (Stage 维)」的横版信息图, 目的是让老师在 1 张图里快速看清本阶段女儿的练习情况.

# 视觉风格: kami 干净 UI (不是儿童插画/不是 baoyu/不是数学讲义手绘)

画面要像现代 SaaS 数据看板 (例如 Linear / Notion / Stripe Dashboard), 干净、专业、信息密度高. 横版 (landscape) 构图.

- 背景: 干净的 off-white parchment 纸张 (浅米白 #faf8f3), 不要卡通纹理
- 主色: 深蓝标题 (#1a365d), 黑色/深灰正文 (#2d3748), 钢蓝强调 (#2563eb)
- 辅色: 中灰 (#718096) 次要文字, 浅灰边框 (#e2e8f0), 浅绿 (#10b981) 数据高亮
- 排版: 圆角矩形卡片, 细线边框 (1px solid #e2e8f0), 表格 grid 严格对齐
- 字体: 无衬线 (Inter / system-ui), 严格层级 (大标题 36pt, 副标题 18pt, 正文 13pt, 数据 14pt)
- 装饰: 不要! 不要卡通人物/不要 emoji/不要云朵/不要手绘箭头/不要植物/不要竹子/不要几何装饰

# 内容布局 (从最重要的信息开始, 左到右 上到下)

1. 标题区: "竹笛练习明细 · Stage {stage_order}" (深蓝大字 36pt, 左对齐)
   副标题: "周期 {stage_start} ~ {stage_end} · 上课日 {lesson_date}" (中灰 14pt)

2. 核心指标卡 (3 个并排, 等宽, 圆角边框):
   - 总时长: {total_minutes} 分钟 (大数字 32pt 深蓝, 标签"总时长"中灰 12pt)
   - 练习天数: {practice_days} 天 (同上)
   - 总次数: {session_count} 次 (同上)

3. 科目小计 (横向柱状图, 表格风格):
   {item_bar_chart}
   - 每行: 科目名 (左) + 时长数字 (中) + 占比% (右) + 短横向条 (右, 浅绿色)
   - 不要饼图, 不要花式图表

4. 按日练习明细 (真正的表格, 不是堆叠):
   - 表头: 日期 | 总时长 | 主科目 | 内容摘要
   - 数据行: 一行一天, 紧凑对齐, 交替浅色行底
   - 内容摘要最多 30 字, 超出截断加 "..."

5. 底部: 生成时间 (中灰 11pt, 右下角), 学员名 (左下角, 小灰字)

整体要像 Linear Dashboard 的 monthly report 截图, 干净、可读、专业. 不像幼儿园海报.""",
    "layout": """请将以上数据转化为信息图布局 (横版, 1 张), 包含:
1. 标题区: "竹笛练习明细 · Stage {stage_order}" (深蓝大字)
2. 周期副标题: "周期 {stage_start} ~ {stage_end} · 上课日 {lesson_date}"
3. 核心指标卡: 总时长 {total_minutes} 分钟, 练习天数 {practice_days} 天, 共 {session_count} 次
4. 科目小计 (横向柱状图风格): {item_bar_chart} — 每科一行: 名称 + 时长 + 占比%
5. 按日练习表 (简化矩阵): 日期 | 总时长 | 主要科目 | 主要内容片段
6. 总结栏: 一句话评语 ("本期总时长 xx 分钟, 主要练习了 X / Y, 节奏稳定")""",
    "data_fields": """数据说明:
- stage_order: stage 编号
- stage_start / stage_end: 周期起止
- lesson_date: 上课日 (本节课日期)
- total_minutes: 本阶段总练习时长 (分钟)
- practice_days: 实际练习天数
- session_count: 总 session 数
- item_totals: 各项练习时长 {"项目名": 分钟, ...}
- days: [{date, total_minutes, item_summaries:[{name, content_preview}]}]""",
    "aspect_ratio": "landscape",
}


def _truncate(s: str, n: int = 30) -> str:
    """内容预览截断: 避免 prompt 过长."""
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _build_stage_item_bar_chart(by_item: list, total_minutes: int) -> str:
    """科目小计 (text 形式的 bar chart 给 LLM 拼图)."""
    if not by_item or total_minutes <= 0:
        return "(暂无数据)"
    lines = []
    for it in by_item[:5]:
        m = it.get("minutes", 0) or 0
        pct = round(m / total_minutes * 100) if total_minutes else 0
        bar = "█" * max(1, pct // 5)
        lines.append(f"- {it.get('item_name', '?')}: {m} 分钟 ({pct}%) {bar}")
    return "\n".join(lines)


def _build_stage_day_summary(days: list) -> str:
    """按日练习摘要 (text form)."""
    if not days:
        return "(暂无练习日)"
    lines = []
    for d in days:
        item_summaries = []
        for g in d.get("groups", []) or []:
            contents = [
                _truncate(s.get("content", ""), 30)
                for s in (g.get("sessions") or [])
            ]
            contents = [c for c in contents if c]
            preview = " / ".join(contents[:2]) if contents else "(无内容)"
            item_summaries.append(f"{g.get('item_name', '?')}: {preview}")
        joined = " · ".join(item_summaries) or "(无)"
        lines.append(f"- {d.get('date', '?')} ({d.get('total_minutes', 0)} 分钟): {joined}")
    return "\n".join(lines)


def build_stage_image_prompt(
    payload: dict,
    child_name: str = "YoYo",
) -> tuple[str, str]:
    """构造 stage 维 report 图片的 prompt.

    payload 来自 _build_stage_detail_payload, 含:
      stage_order / stage_start / stage_end / lesson_date /
      summary / by_item / days[]

    Returns: (prompt_text, aspect_ratio)
    """
    summary = payload.get("summary", {}) or {}
    template = TEMPLATES["stage_academic"]
    style_para = template["style"]
    aspect = template["aspect_ratio"]
    layout_tpl = template["layout"]
    data_fields = template["data_fields"]

    by_item = payload.get("by_item") or []
    total_m = int(summary.get("total_minutes", 0) or 0)
    practice_days = int(summary.get("practice_days", 0) or 0)
    session_count = int(summary.get("session_count", 0) or 0)
    item_bar_chart = _build_stage_item_bar_chart(by_item, total_m)
    days_text = _build_stage_day_summary(payload.get("days") or [])

    stage_order = payload.get("stage_order", "?")
    stage_start = payload.get("stage_start") or "?"
    stage_end = payload.get("stage_end") or payload.get("effective_end") or "?"
    lesson_date = payload.get("lesson_date") or "?"

    try:
        layout_filled = layout_tpl.format(
            stage_order=stage_order,
            stage_start=stage_start,
            stage_end=stage_end,
            lesson_date=lesson_date,
            total_minutes=total_m,
            practice_days=practice_days,
            session_count=session_count,
            item_bar_chart=item_bar_chart,
        )
    except KeyError as e:
        # 容错: 任何缺失字段都用 "?" 兜底
        layout_filled = layout_tpl.replace("{" + str(e).strip("'") + "}", "?")

    days_block = "按日练习明细:\n" + days_text

    prompt = f"""{style_para}

{layout_filled}

{days_block}

{data_fields}

学员名字: {child_name}
数据真实, 不要编造. 用英文/中文混排都行, 但数字和日期要跟数据一致.
"""
    return prompt, aspect
