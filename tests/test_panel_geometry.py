"""26093002 回归锁：音乐符号面板绝不压盖输入框（几何自检）。

驱动 `tests/js/panel_geometry_check.js`：从真实 JS 抽 reposition() 跑网格，
断言 ① 当前实现在 5 视口 × 3 输入框高度 × 全高度扫描下 0 压盖
     ② 负控（legacy 的 MIN_H 强撑版）必须出现压盖 —— 否则自检本身失效。
"""
import subprocess
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "js" / "panel_geometry_check.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="需要 node")
def test_panel_never_covers_input():
    assert HARNESS.exists(), f"缺少几何自检脚本: {HARNESS}"
    r = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True, timeout=60)
    out = (r.stdout or "") + (r.stderr or "")
    assert "GEOM_OK" in out, f"几何自检未通过:\n{out}"
    assert r.returncode == 0, f"退出码 {r.returncode}:\n{out}"
    # 断言负控真的报了压盖（自检有效性的证据行必须出现）
    assert "负控(legacy MIN_H 强撑)" in out, out
    for line in out.splitlines():
        if line.startswith("当前实现:"):
            assert "压盖输入框 0" in line, line


@pytest.mark.skipif(shutil.which("node") is None, reason="需要 node")
def test_panel_geometry_negative_control_bites():
    """负控行必须显示 > 0 的压盖数（证明这套断言能红）。"""
    r = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True, timeout=60)
    lines = [l for l in (r.stdout or "").splitlines() if l.startswith("负控")]
    assert lines, (r.stdout or "") + (r.stderr or "")
    count = int(lines[0].split("压盖输入框")[1].strip())
    assert count > 0, f"负控没有压盖场景, 说明自检形同虚设: {lines[0]}"
