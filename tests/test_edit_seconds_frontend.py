"""sprint 26100101 F3 锁（Python 侧）：驱动 tests/js/edit_seconds_check.js + 断言接线。

改前：编辑弹窗保存写死 `duration_seconds: duration * 60` → 1分30秒 的记录只改音符
就被抹成 2 分钟（秒真值丢失）。JS 侧的 15 条行为用例（含 <60 秒三条）+ 负控在 node 脚本里。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
JS_CHECK = REPO_ROOT / "tests" / "js" / "edit_seconds_check.js"
TEMPLATE = REPO_ROOT / "src" / "kid_app" / "templates" / "practice.html"


def test_js_edit_seconds_check_passes_with_negative_control():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 不在 PATH")
    r = subprocess.run([node, str(JS_CHECK)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node 检查失败:\n{r.stdout}\n{r.stderr}"
    assert "OK: now 用例 15 条, 失败合计 0" in r.stdout
    assert "负控红了" in r.stdout, "负控没跑或没红"


def test_edit_session_reads_original_seconds_from_row():
    """弹窗必须从行上读原秒并带进保存路径（只抽函数不接线 = 假修）。"""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "getAttribute('data-duration-seconds')" in html
    assert "_editingDurationSeconds" in html
    assert "buildEditPutBody(note, bpm, content, duration," in html
    assert "_editingDurationMinutes, _editingDurationSeconds, reps" in html
    assert "duration_seconds: duration * 60" not in html
