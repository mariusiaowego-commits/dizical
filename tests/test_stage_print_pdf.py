"""stage-print iPad 横屏适配 + iPad Safari PDF 完整输出 (sprint 26080801) 单测.

回归保护 6 处改动:
  T1 paper CSS viewport ≤1180px 时 paper 100%
  T2 @media print .paper.is-landscape max-width 420mm
  T3 @media print table.matrix table-layout: fixed
  T4 colgroup 短列 6 天时 = 2.8%
  T5 preparePrintZoom floor 0.95
  T6 syncPaperMode 状态条文案 "屏上可横滑 · 打印按内容自动分页"
"""
from pathlib import Path

import pytest

HTML_PATH = Path("/Users/mt16/dev/dizical/src/kid_app/templates/stage-print.html")


def _read_html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


def test_T1_paper_css_responsive_max_1180():
    """iPad viewport ≤1180px 时 paper 不再 420mm 硬限, 用 !important 防后写覆盖."""
    html = _read_html()
    assert "@media (max-width: 1180px)" in html
    block = html.split("@media (max-width: 1180px)", 1)[1]
    # 块内必须含 width: 100% !important + view-table-wrap overflow-x: auto !important + iPad 屏上 paper box-shadow none
    assert "width: 100% !important" in block
    assert "min-width: 0 !important" in block
    assert "overflow-x: auto !important" in block
    assert "box-shadow: none !important" in block
    # 关键: sprint-26080801 round 2 修复 - 第二个 .paper.is-table.is-landscape 块 (display: flex column) 必须被 @media 兜底覆盖
    assert ".paper.is-table.is-landscape { display: block !important" in block or "display: block !important" in block


def test_T2_paper_css_print_max_width_420():
    """@media print 强制 paper max-width 420mm (A3 横向)."""
    html = _read_html()
    # 找到 @media print 块
    assert "@media print" in html
    print_block = html.split("@media print", 1)[1]
    # 必须含 .paper.is-landscape { ... max-width: 420mm !important ... }
    assert ".paper.is-landscape" in print_block
    assert "max-width: 420mm" in print_block
    # 不能含裸 "  width: 420mm !important" (sprint 26080103 旧写法, 改 max-width 防 iPad Safari 越界)
    # 注意: max-width: 420mm !important 里也包含 width 子串, 必须用空格前缀避免误匹配
    assert "  width: 420mm !important" not in print_block
    assert "\n      width: 420mm !important" not in print_block


def test_T3_matrix_print_fixed_layout():
    """@media print 矩阵锁列宽 table-layout: fixed !important."""
    html = _read_html()
    print_block = html.split("@media print", 1)[1]
    assert "table.matrix" in print_block
    assert "table-layout: fixed !important" in print_block


def test_T4_colgroup_short_w_2_8_for_6_days():
    """colgroup 短列 6 天时 = 2.8% (sprint 26080801 从 2.4% 提, iPad viewport 1133px 上 ≈ 32px ≈ 8mm)."""
    html = _read_html()
    # 必须含字面量 "nDays <= 6 ? 2.8 : 2.4"
    assert "nDays <= 6 ? 2.8 : 2.4" in html


def test_T5_prepare_print_zoom_floor_0_95():
    """preparePrintZoom floor 0.95 (sprint 26080801 从 0.65/0.70 改)."""
    html = _read_html()
    # 必须含 floor = 0.95
    assert "var floor = 0.95;" in html
    # 不能再含旧的 isLs ? 0.65 : 0.70
    assert "isLs ? 0.65 : 0.70" not in html


def test_T6_sync_paper_mode_hint_text():
    """syncPaperMode 文案不再"打印一页约 X%"误导, 改 "屏上可横滑 · 打印按内容自动分页"."""
    html = _read_html()
    assert "表格 · A3 横向 · 屏上可横滑 · 打印按内容自动分页" in html
    # 不能再含旧的 "打印一页" 误导
    assert "表格 · A4 横向 · 科目×日期矩阵 · 打印一页" not in html


def test_T7_regression_sprint_26080103_preserved():
    """sprint 26080103 关键 CSS 不被本次改动破坏."""
    html = _read_html()
    # 屏上 min-height: 8mm (sprint 26080103 v2)
    assert "min-height: 8mm" in html
    # 矩阵打印 break-inside: avoid (sprint 26080103 v2)
    assert "break-inside: avoid" in html
    assert "page-break-inside: avoid" in html
    # 矩阵 thead 重复表头 (sprint 26080103 v2)
    assert "thead { display: table-header-group" in html


def test_T8_update_preview_status_overflow_message():
    """updatePreviewStatus 屏上溢出时显示 '已选 N 天 · 屏上可横滑 · 打印按内容自动分页'."""
    html = _read_html()
    assert "屏上可横滑 · 打印按内容自动分页" in html
    assert "已选" in html and "天 · 屏上可横滑" in html


def test_T9_beforeprint_ipad_safari_paper_fix():
    """sprint-26080801: iPad Safari WKWebView 忽略 @page A3 landscape, 用 beforeprint 直接改 paper 元素尺寸."""
    html = _read_html()
    # 必须有 applyPrintPaperFix 函数 + beforeprint 监听
    assert "function applyPrintPaperFix" in html
    assert "addEventListener('beforeprint'" in html
    assert "addEventListener('afterprint'" in html
    # paper.style.width = wMm + 'mm' 420mm
    assert "420mm" in html
    assert "297mm" in html
    # 矩阵 in iOS 打印强制走 fixed
    assert "t.style.tableLayout = 'fixed'" in html


def test_T10_fill_matrix_min_height_8mm():
    """sprint-26080801: fillMatrixToPaper 行高统一设 8mm (回归 sprint 26080103 v2 触摸友好行高)."""
    html = _read_html()
    assert "r.style.minHeight = '8mm'" in html


def test_T11_m_total_m_tempo_m_once_font_size_8pt():
    """sprint-26080802: 矩阵短列字号 9.5pt/9pt → 8pt 防 iPad Safari 速度列文字溢出."""
    html = _read_html()
    # m-total/m-tempo/m-once 必须 font-size: 8pt (含 sprint-26080802 注释)
    assert "table.matrix td.m-total {" in html
    block_total = html.split("table.matrix td.m-total {", 1)[1].split("}", 1)[0]
    assert "font-size: 8pt" in block_total
    assert "9.5pt → 8pt" in block_total  # sprint 标记
    assert "table.matrix td.m-tempo {" in html
    block_tempo = html.split("table.matrix td.m-tempo {", 1)[1].split("}", 1)[0]
    assert "font-size: 8pt" in block_tempo
    assert "overflow-wrap: anywhere" in block_tempo  # 防速度字符串溢出
    assert "table.matrix td.m-once {" in html
    block_once = html.split("table.matrix td.m-once {", 1)[1].split("}", 1)[0]
    assert "font-size: 8pt" in block_once


def test_T12_no_style_label_in_header():
    """sprint-26080802: 表格视图不再含 '表格 · 科目×日期 · A4 横向' 冗余字符串."""
    html = _read_html()
    assert "表格 · 科目×日期 · A4 横向" not in html
    # 但 JS 函数 styleLabel 变量可能还在 (已无引用), 验证无 ph-sub 拼入
    assert "html += ' · ' + styleLabel;" not in html


def test_T13_pf_no_generated_time():
    """sprint-26080802: pf 块不含生成时间 + '矩阵 · A4 横向'."""
    html = _read_html()
    assert "生成 '" not in html
    assert "矩阵 · A4 横向" not in html
    assert "分组 · A4 竖向" not in html


def test_T14_ph_sub_no_redundant_period():
    """sprint-26080802: ph-sub 不含 '周期 X ~ Y · 上课日 · 截止' 冗余."""
    html = _read_html()
    assert "html += '<div class=\"ph-sub\">周期 ' + esc(data.stage_start || '')" not in html
    assert "html += ' · 上课日 '" not in html
    assert "html += ' · 截止 '" not in html


def test_T15_dash_chars_unaffected_css():
    """sprint-26080802: 8月1日列 m-tempo overflow-wrap 已加, days-1/2 短列字号 9.5pt 兜底."""
    html = _read_html()
    # days-1 / days-2 短列字号必须 9.5pt (sprint-26080802 10.5pt → 9.5pt)
    assert "table.matrix.days-1 td.m-once," in html
    assert "table.matrix.days-2 td.m-once { font-size: 9.5pt;" in html


def test_T16_title_english_for_ios_safari_pdf_filename():
    """sprint-26080804: document.title 用日期范围 YYMMDD-YYMMDD (iOS Safari 打印文件名源).

    修前: document.title = "竹笛练习明细 · Stage 16 · 表格 · 6天"
    修后: document.title = "Dizical-Practice-Detail-260727-260801-Table-6days"
          PDF 文件名: "Dizical-Practice-Detail-260727-260801-Table-6days.pdf"
          (纯 ASCII, 全 - 连接, 无空格, 无中文, 日期范围格式)

    PDF 内容标题 (ph-title) 保留中文 "竹笛练习明细 · Stage 16".
    """
    html = _read_html()
    # document.title 含日期范围格式 (toYYMMDD + - 拼接)
    assert "Dizical-Practice-Detail-" in html
    assert "toYYMMDD(data.stage_start) + '-' + toYYMMDD(data.stage_end)" in html
    assert "-Table" in html and "-Grouped" in html
    # 不再用 Stage 序号做文件名
    assert "Dizical-Practice-Detail-Stage-" not in html
    # PDF 内容标题保留中文
    assert "竹笛练习明细 · Stage " in html