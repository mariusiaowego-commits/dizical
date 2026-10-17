"""badge WebP 派生模块必须能随 src/ 进镜像 (2026-10-17 线上事故的回归守卫).

事故经过: badge commit 的 webp 派生曾从 `scripts/generate_badge_webp.py` 按文件路径动态加载。
生产 CloudRun 走 tcb 上传 ZIP, `.tcbignore` 把 `scripts/` 整目录排除 → 容器里根本没有
`/app/scripts/generate_badge_webp.py`, 于是 commit 抛

    commit 失败: webp 派生失败 key=badges/thumbs/...webp: [Errno 2] No such file or directory:
    '/app/scripts/generate_badge_webp.py'

commit 是 Storage First 全链 (PNG + 两档 webp 都成功才入库), 派生失败 = 徽章永远落不了地。

断言:
1. `src/kid_app/badge_webp.py` 提供可用的 webp_variants (两档都能解码, 尺寸/通道正确, 不放大)
2. `badge_draft` 的派生走 `src/` 下的模块 —— 而不是 `scripts/`
3. 静态守卫: `src/kid_app/**/*.py` 里不许出现「从 scripts/ 加载 .py」这种运行时代码依赖
4. CLI 壳 `scripts/generate_badge_webp.py` 与运行时模块共用同一实现 (identity, 没有第二份规格)
"""
import io
import re
import sys
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.kid_app import badge_draft, badge_webp  # noqa: E402

KID_APP_DIR = PROJECT_ROOT / "src" / "kid_app"
RUNTIME_MODULE = KID_APP_DIR / "badge_webp.py"


def _png_bytes(size: int = 1024) -> bytes:
    """造一张带透明通道的测试 PNG (透明底 + 中间不透明方块 + 半透明方块)。"""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    quarter = size // 4
    im.paste((255, 107, 107, 255), (quarter, quarter, quarter * 3, quarter * 3))
    im.paste((46, 62, 80, 128), (quarter * 3, quarter, quarter * 4, quarter * 2))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


# ─── 1. 模块本体 ─────────────────────────────────────────────────────

def test_runtime_module_exists_under_src():
    """模块必须在 src/kid_app/ 下 —— 这是它能进镜像的唯一理由。"""
    assert RUNTIME_MODULE.is_file(), f"缺 {RUNTIME_MODULE} (运行时代码必须住在 src/)"
    assert Path(badge_webp.__file__).resolve() == RUNTIME_MODULE.resolve()


def test_webp_variants_two_valid_files():
    thumb, full = badge_webp.webp_variants(_png_bytes(1024))
    assert thumb and full

    with Image.open(io.BytesIO(thumb)) as t, Image.open(io.BytesIO(full)) as f:
        assert t.format == "WEBP" and f.format == "WEBP"
        assert t.size == badge_webp.THUMB_SIZE == (320, 320)
        assert f.size == badge_webp.FULL_SIZE == (1024, 1024)
        # 透明通道必须保住 (前端白底/灰底都要合成)
        assert t.mode == "RGBA" and f.mode == "RGBA"
        assert t.getpixel((0, 0))[3] == 0, "左上角应保持透明"
        assert t.getpixel((160, 160))[3] == 255, "中心应是不透明方块"


def test_webp_variants_never_upscale():
    """小图不放大: thumbnail 语义 —— 免得把小 badge 拉成糊图。"""
    thumb, full = badge_webp.webp_variants(_png_bytes(64))
    with Image.open(io.BytesIO(thumb)) as t, Image.open(io.BytesIO(full)) as f:
        assert t.size == (64, 64)
        assert f.size == (64, 64)


def test_webp_variants_rejects_garbage():
    """坏字节要抛错 (commit 靠它判断能否入库), 不许静默返回空图。"""
    with pytest.raises(UnidentifiedImageError):
        badge_webp.webp_variants(b"not a png at all")


# ─── 2. badge_draft 的取自 src/, 不是 scripts/ ──────────────────────

def test_badge_draft_webp_module_comes_from_src():
    mod = badge_draft._webp_script()
    mod_path = Path(mod.__file__).resolve()
    assert mod_path == RUNTIME_MODULE.resolve(), f"派生模块应取自 src/, 实际 {mod_path}"
    assert "scripts" not in mod_path.parts


def test_badge_draft_derive_webp_works_and_wraps_errors():
    keys = badge_draft.badge_object_keys("regression_badge", 1)
    thumb, full = badge_draft._derive_webp(_png_bytes(256), keys)
    assert thumb and full

    with pytest.raises(RuntimeError) as ei:
        badge_draft._derive_webp(b"garbage", keys)
    msg = str(ei.value)
    assert "webp 派生失败" in msg and keys["thumb"] in msg and keys["full"] in msg


# ─── 3. 静态守卫: 运行时代码不许从 scripts/ 加载 .py ────────────────

def test_no_runtime_import_of_py_from_scripts_dir():
    offenders: list[str] = []
    for path in sorted(KID_APP_DIR.rglob("*.py")):
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if '"scripts"' not in line and "'scripts'" not in line:
                continue
            # 只关心「加载 .py」这种运行时依赖 (scripts/intro-*.sh 之类的 CLI 调用不算)
            if re.search(r"\.py\b", line):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{num}: {line.strip()}")
    assert not offenders, (
        "运行时代码不许从 scripts/ 加载 .py —— .tcbignore 排除 scripts/, 生产容器里没有这个目录, "
        "线上会直接 FileNotFoundError (2026-10-17 badge commit 事故)。把模块挪进 src/kid_app/:\n"
        + "\n".join(offenders)
    )


# ─── 4. CLI 壳与模块共用一份实现 ────────────────────────────────────

def test_cli_shell_shares_runtime_implementation():
    import importlib.util

    script = PROJECT_ROOT / "scripts" / "generate_badge_webp.py"
    spec = importlib.util.spec_from_file_location("generate_badge_webp_cli", script)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.webp_variants is badge_webp.webp_variants, "CLI 壳不许复刻第二份实现"
    assert mod.THUMB_SIZE == badge_webp.THUMB_SIZE
    assert mod.THUMB_QUALITY == badge_webp.THUMB_QUALITY
    assert mod.FULL_SIZE == badge_webp.FULL_SIZE
    assert mod.FULL_QUALITY == badge_webp.FULL_QUALITY
    assert Path(mod.SRC_DIR).name == "badges"
