"""
sprint 26092003-secret-scrub — 防 e2e 脚本明文密码回潮契约.

约定 (本仓库, sprint 26092003 起):
- scripts/e2e_sprint_*/ 任何 .py 都不允许出现明文 dad 密码
- PASSWORD 必须强制从 env 读取 (os.environ["PASSWORD"], 不带 fallback)
- README 必带 PASSWORD 必填的明确提示, 不得示例明文

回归防御:
- 旧值 `YoYo0905bamboo` (sprint 26091901 debug 用, 9-20 已删明文) 必须永远不再入仓
"""
import re
from pathlib import Path


SCRUB_TARGETS = [
    "scripts/e2e_sprint_26091901/e2e_dom_state.py",
    "scripts/e2e_sprint_26091901/e2e_interactions.py",
    "scripts/e2e_sprint_26091901/e2e_touch_action.py",
    "scripts/e2e_sprint_26091901/README.md",
]
FORBIDDEN_FALLBACK = re.compile(r'os\.environ\.get\(\s*["\']PASSWORD["\']\s*,\s*["\']')
FORBIDDEN_CLEARTEXT = "YoYo0905bamboo"


def test_no_plaintext_password_in_e2e_scripts():
    """sprint 26092003-secret-scrub: e2e 脚本全文 grep, 明文密码 0 命中."""
    for rel in SCRUB_TARGETS:
        path = Path(rel)
        assert path.exists(), f"缺少文件: {rel}"
        content = path.read_text(encoding="utf-8")
        assert FORBIDDEN_CLEARTEXT not in content, (
            f"{rel} 含明文 dad 密码 `{FORBIDDEN_CLEARTEXT}` (sprint 26091901 已弃, "
            f"请走 env `PASSWORD` 传入)"
        )


def test_e2e_scripts_force_password_env():
    """3 个 .py 必须用 `os.environ["PASSWORD"]` (KeyError 是预期), 不允许 fallback."""
    py_files = [t for t in SCRUB_TARGETS if t.endswith(".py")]
    for rel in py_files:
        content = Path(rel).read_text(encoding="utf-8")
        assert not FORBIDDEN_FALLBACK.search(content), (
            f"{rel} 用了 `os.environ.get('PASSWORD', default)` 写法, "
            f"sprint 26092003 起必须改 `os.environ['PASSWORD']` (无 fallback)"
        )
        assert 'os.environ["PASSWORD"]' in content, (
            f"{rel} 缺少 `os.environ['PASSWORD']` 强制 env 读取"
        )


def test_e2e_readme_has_password_required_hint():
    """README 必须显式说明 PASSWORD 是必填 env, 不能示例明文."""
    readme = Path("scripts/e2e_sprint_26091901/README.md").read_text(encoding="utf-8")
    assert "PASSWORD" in readme
    assert "必填" in readme or "必传" in readme or "必须" in readme, (
        "README 未明确说明 PASSWORD 是必填项"
    )
    assert FORBIDDEN_CLEARTEXT not in readme, (
        "README 含明文 dad 密码 (sprint 26092003 起必须删)"
    )
