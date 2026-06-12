"""
Badge 6 步流水线: prompt → FAL (走 Nous Portal Tool Gateway) → 拿图 → 去背 → 保存 → (commit 时再写 DB).

设计 (用户 2026-06-12 拍板, moni 模式):
- FAL 调用走 hermes Tool Gateway (image_generate 工具), 用 Nous Subscription credits
- 不直接连 FAL API, 不持 FAL key
- 调 `hermes --profile dizical chat -q <prompt> -t image_gen --yolo -Q`
- 跟 routes/config.py:980 月报框架同源, 但走 dizical profile
- 失败回滚: 任何一步异常, 已生成文件删除, 不写 DB

依赖:
- subprocess 调 hermes CLI
- PIL 处理图像
- src.kid_app.badge_prompts (单源模板)
- src.kid_app.badge_ai_placeholder (复用 _find_hermes / _get_profile)
- 路径: src/kid_app/badge_generator.py

历史:
- 2026-06-12 V1 PR-A 创建
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from src.kid_app.badge_ai_placeholder import _find_hermes, _get_profile
from src.kid_app.badge_db import (
    badge_write_tx,
    check_id_unique,
    fetch_max_sort_order,
    insert_achievement_row,
    insert_achievement_stats_row,
    insert_badge_row,
    next_version,
)
from src.kid_app.badge_prompts import build_unlocked_prompt
from src.kid_app.badge_portal import is_ready_for_badge_workflow

logger = logging.getLogger(__name__)

# Badge PNG 落盘目录
_BADGES_DIR = Path(__file__).parent / "static" / "badges"

# 单次生图超时 (秒). FAL gpt-image-2 30-60s, 给 180s 缓冲
_GEN_TIMEOUT = 180


# ─── 去白底 ─────────────────────────────────────────────────────────

def _dedupe_to_rgba(src: Path) -> bool:
    """把 RGB/RGBA PNG 的近白像素 → 透明. 复用 dedupe_bg_lucky61.py 29 行逻辑.

    Returns:
        True=成功去背 (mode 变 RGBA)
        False=去背失败 (图片可能本就是 RGBA 但有白方框, 留给用户决策)
    """
    try:
        im = Image.open(src).convert("RGBA")
        pixels = im.load()
        w, h = im.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                # 规则 1: 纯白 → 透明
                if r > 220 and g > 220 and b > 220 and a > 200:
                    pixels[x, y] = (r, g, b, 0)
                # 规则 2: 近白 + 低饱和度 (抗锯齿) → 透明
                elif r > 200 and g > 200 and b > 200:
                    if max(r, g, b) - min(r, g, b) < 30:
                        pixels[x, y] = (r, g, b, 0)
        im.save(src)
        # 验证 mode 必为 RGBA
        return Image.open(src).mode == "RGBA"
    except Exception as e:
        logger.warning(f"_dedupe_to_rgba 失败: {src} -> {e}")
        return False


# ─── 解析 hermes 输出 ─────────────────────────────────────────────

def _resolve_image_source(output: str) -> str | None:
    """从 hermes chat 输出里解析图片路径/URL.

    支持 3 种格式 (跟 routes/config.py:1001-1018 一致):
    - MEDIA:/abs/path.png  (hermes image_generate 默认输出)
    - http://...  (CDN URL)
    - /abs/path.png  (本地绝对路径)
    """
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 1. MEDIA: prefix
        if "MEDIA:" in line:
            parts = line.split("MEDIA:")
            if len(parts) > 1:
                candidate = parts[1].strip().split()[0]
                if Path(candidate).exists():
                    return candidate
                # 候选 path 不存在 (hermes 删临时文件), 跳过
                continue
        # 2. http(s) URL
        if line.startswith("http://") or line.startswith("https://"):
            if any(line.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
                return line
            if "fal" in line.lower() or ".media" in line.lower():
                return line
            continue
        # 3. 本地绝对路径
        if line.startswith("/") and any(line.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
            if Path(line).exists():
                return line
            continue
    return None


# ─── 调 hermes image_generate ────────────────────────────────────

def _call_hermes_image_gen(prompt: str, on_output: Callable[[str], None]) -> tuple[bool, str, str | None]:
    """调 hermes --profile dizical chat -t image_gen 生图.

    Args:
        prompt: 完整 enamel pin prompt
        on_output: 实时 stdout 行回调 (给 SSE 推)

    Returns:
        (ok, full_output, image_source)
        ok=True: 调通且拿到图, image_source 是路径/URL
        ok=False: 失败, full_output 含 hermes stderr / 错误描述
    """
    hermes = _find_hermes()
    profile = _get_profile()

    # hermes chat 调 image_gen 工具:
    # - `-t image_gen` 启用 image generate 工具集
    # - `-Q` quick mode (non-interactive)
    # - `--yolo` 自动确认 (non-interactive 必须)
    cmd = [
        hermes, "chat",
        "-q", prompt,
        "-t", "image_gen",
        "--profile", profile,
        "-Q",
        "--yolo",
    ]

    logger.info(f"调 hermes image_gen, profile={profile}, prompt_len={len(prompt)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            text=True,
        )
    except FileNotFoundError as e:
        return False, f"hermes CLI 找不到: {e}", None

    output_lines: list[str] = []
    try:
        for line in proc.stdout:
            line = line.rstrip()
            output_lines.append(line)
            on_output(line)
        proc.wait(timeout=_GEN_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, f"hermes image_gen 超时 ({_GEN_TIMEOUT}s)", None

    if proc.returncode != 0:
        err = (proc.stderr.read() if proc.stderr else "").strip()[:500]
        return False, f"hermes image_gen rc={proc.returncode}: {err}", None

    full_output = "\n".join(output_lines)
    image_source = _resolve_image_source(full_output)
    if image_source is None:
        return False, f"未找到图片. hermes 输出 (前 300 字符): {full_output[:300]}", None

    return True, full_output, image_source


def _download_or_copy_image(source: str, dest: Path) -> None:
    """下载 URL 或复制本地文件到 dest. 创建父目录."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.startswith("http://") or source.startswith("https://"):
        urllib.request.urlretrieve(source, dest)
    else:
        shutil.copy2(source, dest)


# ─── 公开 API: 6 步流水线 ───────────────────────────────────────

def run_badge_pipeline(
    badge_id: str,
    placeholder: str,
    on_status: Callable[[str, str], None],  # (stage, message) -> None
    project_root: Path | None = None,
    regenerate: bool = False,
) -> dict[str, Any]:
    """
    完整 6 步流水线. 返回:
      {
        "ok": bool,
        "image_path": str | None,
        "dedupe_ok": bool,
        "version": int,
        "error": str | None,
      }

    失败回滚: 任何一步失败, 已生成文件删除, 不写 DB.
    写 DB 由调用方 (commit_badge_to_db) 负责.

    Args:
        regenerate: True=换新图 (走 update_badge_current 流程, version+=1).
                    False=新 badge (version=1, 必填 new_badge=True).
    """
    created_files: list[Path] = []

    try:
        # ── 步骤 0: Portal 前置检查 (用户 2026-06-12 拍板) ──
        on_status("step0_portal", "检查 Nous Portal 连接状态")
        ok, msg = is_ready_for_badge_workflow()
        if not ok:
            return {
                "ok": False,
                "image_path": None,
                "dedupe_ok": False,
                "version": 0,
                "error": f"Portal 不可用, 不能跑生图: {msg}. "
                         f"请先 `hermes --profile dizical portal info` 排查",
            }

        # ── 步骤 1: 校验输入 ──
        on_status("step1_validate", "校验输入")
        if not badge_id or not all(c.isalnum() or c == "_" for c in badge_id):
            return {
                "ok": False, "image_path": None, "dedupe_ok": False, "version": 0,
                "error": "badge id 必须只含英文/数字/下划线",
            }
        if not regenerate and not check_id_unique(badge_id):
            return {
                "ok": False, "image_path": None, "dedupe_ok": False, "version": 0,
                "error": f"badge id '{badge_id}' 已存在. 换新图请传 regenerate=True",
            }
        if not placeholder or len(placeholder.strip()) < 5:
            return {
                "ok": False, "image_path": None, "dedupe_ok": False, "version": 0,
                "error": "placeholder 至少 5 字符",
            }

        # ── 步骤 2: 写 prompt ──
        on_status("step2_prompt", "组装 enamel pin prompt")
        prompt = build_unlocked_prompt(placeholder)
        on_status("step2_prompt", f"prompt 已组装 ({len(prompt)} 字符)")

        # ── 步骤 3: 调 hermes image_gen (走 Nous Portal Tool Gateway) ──
        on_status("step3_fal", "调用 Nous Portal image_generate (30-60 秒)")

        def _on_output(line: str) -> None:
            if "session_id" in line:
                on_status("step3_fal", "hermes 会话已建立")
            elif "Error" in line or "error" in line.lower():
                on_status("step3_fal", f"⚠ {line[:200]}")

        ok, full_output, image_source = _call_hermes_image_gen(prompt, _on_output)
        if not ok:
            return {
                "ok": False, "image_path": None, "dedupe_ok": False, "version": 0,
                "error": full_output,
            }
        on_status("step3_fal", "✅ Nous Portal 已返回图片")

        # ── 步骤 4: 拿图 (download/copy 到目标路径) ──
        version = next_version(badge_id)
        on_status("step4_fetch", f"解析图片, 准备 version=v{version}")

        # 文件名: {id}_v{n}.png (V1 启动版本管理)
        filename = f"{badge_id}_v{version}.png"
        dest_path = _BADGES_DIR / filename

        try:
            _download_or_copy_image(image_source, dest_path)
        except Exception as e:
            return {
                "ok": False, "image_path": None, "dedupe_ok": False, "version": 0,
                "error": f"下载/复制图片失败: {e} (source={image_source})",
            }
        created_files.append(dest_path)
        on_status("step4_fetch", f"图片已保存 ({dest_path.stat().st_size} bytes)")

        # ── 步骤 5: 去白底 ──
        on_status("step5_dedupe", "PIL 去白底 (RGB→RGBA)")
        dedupe_ok = _dedupe_to_rgba(dest_path)
        if dedupe_ok:
            on_status("step5_dedupe", "✅ 去背成功")
        else:
            on_status("step5_dedupe", "⚠ 去背失败, 保留 RGB (前端会显示白方框, 等人工修)")

        return {
            "ok": True,
            "image_path": str(dest_path),
            "dedupe_ok": dedupe_ok,
            "version": version,
            "error": None,
        }

    except Exception as e:
        # ── 失败回滚: 删文件 ──
        for f in created_files:
            try:
                f.unlink(missing_ok=True)
                logger.warning(f"回滚: 删除 {f}")
            except Exception as cleanup_err:
                logger.error(f"回滚失败: {f} -> {cleanup_err}")
        return {
            "ok": False, "image_path": None, "dedupe_ok": False, "version": 0,
            "error": f"流水线异常: {e}",
        }


# ─── 公开 API: 写三表 (commit 时调) ─────────────────────────────

def commit_badge_to_db(
    badge_id: str,
    name: str,
    type_label: str,
    category: str,
    stat_logic: str,
    description: str,
    display_format: str,
    threshold: int | None,
    placeholder: str,
    unlocked_template: str,
    seasonal_type: str,
    image_path: str,
) -> bool:
    """
    把流水线产物 (image_path) 写进三表. 走 badge_write_tx 事务.

    失败抛异常, 由调用方决定是否删 image_path.

    PR-B 合并后: 末尾需清 BADGE_URLS cache 让新 badge 立刻生效.
    """
    sort_order = fetch_max_sort_order() + 1
    # 从 image_path 提取 version (文件名格式: {id}_v{n}.png)
    m = re.search(r"_v(\d+)\.png$", image_path)
    version = int(m.group(1)) if m else 1
    url = f"/static/badges/{Path(image_path).name}"

    with badge_write_tx() as conn:
        insert_achievement_row(conn, {
            "id": badge_id,
            "name": name,
            "type": type_label,
            "category": category,
            "stat_logic": stat_logic,
            "description": description,
            "display_format": display_format,
            "threshold": threshold,
            "unlocked_template": unlocked_template,
            "placeholder": placeholder,
            "sort_order": sort_order,
            "seasonal_type": seasonal_type,
        })
        if category == "milestone":
            insert_achievement_stats_row(conn, badge_id)
        insert_badge_row(conn, badge_id, url, version)

    # PR-B 集成: 让新 badge 立刻在 /badges 页面可见 (无需等 60s cache TTL)
    # 延迟 import 模式, 跟 routes/badge_workflow.py import render 一样
    from src.kid_app.app import _invalidate_badge_url_cache
    _invalidate_badge_url_cache()

    return True


# ─── PR-C 批量模式 (2026-06-12) ──────────────────────────────────
# 设计: 基于一个已上线 badge 的元数据, 衍生 N 个同风格新 badge.
# 每个新 badge 只换 placeholder (一次填 N 个), 元数据继承来源 badge.
# 失败累计: 任何一条失败, 该条 result["ok"]=False 但不阻断其他.
# 限制: N <= 20 (防止长 prompt 撑爆 hermes chat 命令行).
# 派生 id 规则: {source_id}_{i+1} (例如 lucky_61_2026_1, _2, _3 ...)

BATCH_MAX_N = 20


def _derive_batch_badge_id(source_id: str, index: int) -> str:
    """派生 N 个新 badge id. index 从 1 开始."""
    return f"{source_id}_{index}"


def run_badge_pipeline_batch(
    source_badge_meta: dict[str, Any],
    placeholders: list[str],
    on_status: Callable[[str, str, str], None],  # (stage, badge_id, message)
    project_root: Path | None = None,
) -> dict[str, Any]:
    """
    批量跑流水线. 每条 placeholder 派生一个新 badge.

    Args:
        source_badge_meta: 来源 badge 的元数据 (name / type / category / stat_logic /
                          description / display_format / seasonal_type), 用于继承
        placeholders: 英文 placeholder 列表, 每条生成一个新 badge
        on_status: 实时状态回调 (stage, badge_id, message)
                    推 SSE 状态用

    Returns:
        {
            "ok": bool,                    # 全部成功
            "results": [                   # 每条的结果
                {
                    "badge_id": str,
                    "image_path": str | None,
                    "dedupe_ok": bool,
                    "version": int,
                    "ok": bool,
                    "error": str | None,
                },
                ...
            ],
            "n_total": int,
            "n_success": int,
            "n_failed": int,
        }
    """
    n = len(placeholders)
    if n == 0:
        return {"ok": True, "results": [], "n_total": 0, "n_success": 0, "n_failed": 0}
    if n > BATCH_MAX_N:
        return {
            "ok": False, "results": [], "n_total": n, "n_success": 0, "n_failed": 0,
            "error": f"N 最多 {BATCH_MAX_N} (实际 {n})",
        }

    source_id = source_badge_meta.get("id", "")
    if not source_id:
        return {
            "ok": False, "results": [], "n_total": n, "n_success": 0, "n_failed": 0,
            "error": "source_badge_meta 必须含 id",
        }

    results: list[dict[str, Any]] = []
    n_success = 0
    n_failed = 0

    for i, placeholder in enumerate(placeholders, start=1):
        badge_id = _derive_batch_badge_id(source_id, i)

        # 单条流水线
        def on_status_for_item(stage: str, msg: str) -> None:
            on_status(stage, badge_id, msg)

        result = run_badge_pipeline(
            badge_id=badge_id,
            placeholder=placeholder,
            on_status=on_status_for_item,
            project_root=project_root,
        )

        # 单条结果整合 (extract image_path / version)
        item_result = {
            "badge_id": badge_id,
            "image_path": result.get("image_path"),
            "dedupe_ok": result.get("dedupe_ok", False),
            "version": result.get("version", 0),
            "ok": result.get("ok", False),
            "error": result.get("error"),
            "placeholder": placeholder,
        }
        results.append(item_result)
        if item_result["ok"]:
            n_success += 1
        else:
            n_failed += 1
        # 推 batch 进度
        on_status("batch_progress", badge_id, f"{i}/{n} 完成 ({n_success} 成功 / {n_failed} 失败)")

    return {
        "ok": n_failed == 0,
        "results": results,
        "n_total": n,
        "n_success": n_success,
        "n_failed": n_failed,
    }


def commit_badge_batch_to_db(
    source_badge_meta: dict[str, Any],
    items: list[dict[str, Any]],  # batch preview 返回的 results
) -> dict[str, Any]:
    """
    批量写库. 一次事务 INSERT N 行 achievements + (可选) N 行 achievement_stats + N 行 achievement_badges.

    Args:
        source_badge_meta: 继承的元数据 (id/name/type/category/stat_logic/description/
                          display_format/threshold/seasonal_type/placeholder/unlocked_template)
        items: run_badge_pipeline_batch 返回的 results, 只处理 ok=True 的项

    Returns:
        {
            "ok": bool,
            "committed_count": int,        # 实际写入的 badge 数
            "failed": [                   # 写入失败的 items
                {"badge_id": str, "error": str},
            ],
        }
    """
    valid_items = [it for it in items if it.get("ok") and it.get("image_path")]
    if not valid_items:
        return {"ok": True, "committed_count": 0, "failed": []}

    failed: list[dict[str, str]] = []
    n_committed = 0

    # 继承字段 (id/name/category 不复用, 用各 item 自己的)
    name_tpl = source_badge_meta.get("name", "")
    type_label = source_badge_meta.get("type", "突破")
    stat_logic = source_badge_meta.get("stat_logic", "")
    description = source_badge_meta.get("description", "")
    display_format = source_badge_meta.get("displayFormat") or source_badge_meta.get("display_format", "days")
    threshold = source_badge_meta.get("threshold")
    seasonal_type = source_badge_meta.get("seasonalType") or source_badge_meta.get("seasonal_type", "monthly")
    category = source_badge_meta.get("category", "milestone")
    unlocked_template_tpl = source_badge_meta.get("unlocked_template", "")

    # 用一个事务包所有 INSERT
    try:
        with badge_write_tx() as conn:
            for item in valid_items:
                badge_id = item["badge_id"]
                placeholder = item["placeholder"]
                image_path = item["image_path"]
                # 名称: 继承来源名 + 后缀 (避免重名)
                # 例如 "幸运六一节 (1)" / "幸运六一节 (2)" ...
                # 如果来源名已经有 "(N)" 后缀, 替换它
                import re as _re
                m = _re.search(r"\s*\((\d+)\)\s*$", name_tpl)
                if m:
                    item_name = _re.sub(r"\s*\(\d+\)\s*$", f" ({item['version']})", name_tpl)
                else:
                    item_name = f"{name_tpl} ({item['version']})"
                # unlocked_template 重新组装 (placeholder 不同)
                try:
                    item_unlocked_template = build_unlocked_prompt(placeholder) if placeholder else unlocked_template_tpl
                except Exception:
                    item_unlocked_template = unlocked_template_tpl
                # 写 3 张表
                insert_achievement_row(conn, {
                    "id": badge_id,
                    "name": item_name,
                    "type": type_label,
                    "category": category,
                    "stat_logic": stat_logic,
                    "description": description,
                    "display_format": display_format,
                    "threshold": threshold,
                    "unlocked_template": item_unlocked_template,
                    "placeholder": placeholder,
                    "seasonal_type": seasonal_type,
                })
                if category == "milestone":
                    insert_achievement_stats_row(conn, badge_id)
                # url 从 image_path 提取
                url = f"/static/badges/{Path(image_path).name}"
                insert_badge_row(conn, badge_id, url, item["version"])
                n_committed += 1
    except Exception as e:
        return {
            "ok": False,
            "committed_count": 0,
            "failed": [{"badge_id": it["badge_id"], "error": str(e)} for it in valid_items],
        }

    # PR-B 集成: 让 N 个新 badge 立刻在 /badges 可见
    from src.kid_app.app import _invalidate_badge_url_cache
    _invalidate_badge_url_cache()

    return {"ok": True, "committed_count": n_committed, "failed": failed}
