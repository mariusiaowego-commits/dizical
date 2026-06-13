---
title: tech-spec badge 制作工作流
source: ai-agent
status: V2.1 定稿 (2026-06-14)
project: dizical
created: 2026-06-12
updated: 2026-06-14
author: coder agent
---

# tech-spec: Badge 制作工作流

> **AI 标注:** 本技术方案由 coder agent 生成, YAML `source: ai-agent`, 镜像到 Obsidian `tqob/05-Coding/project-dizical/docs/tech-spec-badge-workflow.md`.
> 配套 PRD: `PRDs/PRD-徽章制作工作流-260612.md` V2.1.

> **V2.1 变更摘要**: V1 的 6 步流水线 + hermes subprocess 架构已废弃. V2.1 改为文件契约 + skill 解耦. 详见 §0.1b.

---

## 0. 范围与依赖

### 0.1 范围 — ⚠️ V1 已废弃

> **V2.1 注**: 以下 V1 范围已废弃. V2.1 范围见 §0.1b.

本技术方案覆盖 V1 全部 3 个 PR：
- **PR-A** 前台化基础设施（4 步表单 + 后端 6 步流水线 + 写三表 + 失败回滚）
- **PR-B** BADGE_URLS / BADGE_FILES 改 DB-driven（PR-A 基础上的独立性改造）
- **PR-C** 批量模式（基于已认可 badge 衍生 N 个）

### 0.1b V2.1 范围 (2026-06-14)

本技术方案 V2.1 覆盖 PR #85-#90:

| PR | 范围 |
|----|------|
| #85 | V2 重构: 9 端点→4, 代码精简 50%+ |
| #86 | grade url 修复 + milestone 持久化 |
| #87 | practice_at CST + first_to_act 修复 |
| #88 | renderTrail CST/UTC 兼容 |
| #89 | all_items stage items 判定 |
| #90 | V2.1 阶段 2.1+2.2 UI 完整实现 |

**V2.1 架构核心**:
- **3 步解耦流程**: dizical draft → hermes skill → dizical commit
- **文件契约**: `data/lib/badge_data/{draft_id}.json` 是唯一接口
- **进程隔离**: dizical 不调 hermes, hermes 不调 dizical DB
- **calc 解耦**: 走 `/calc-apply` skill (git apply → PR → dad merge)
- **skill 3 profile**: dizical (主) + coder (symlink) + default (symlink)

### 0.2 设计依据
- **生产现状**（PR-A 起点）：6 个 Python 文件 + 1 个新模板 + 1 个新路由文件 + DB helper
- **复用资产**：
  - SSE 框架: `src/kid_app/routes/config.py:955-1096`（月报用）
  - 去白底: `src/dedupe_bg_lucky61.py`（29 行）
  - 模板: `docs/badge-prompts.md` line 9-12
  - Gemini Flash: `src/kid_app/subject_info.py:31-40`（API key 路径）
  - PIN 验证: `src/kid_app/templates/config-blindbox.html:319-323`
  - render: `src/kid_app/app.py`（在 `from kid_app.app import render` 函数内延迟 import）
- **约束**（用户 2026-06-12 拍板）：盲盒 = 7日打卡盲盒 = 不在范围；locked = 前端 CSS 灰度；版本管理 V1 启动

### 0.3 文件改动清单

| 动作 | 文件 | 行数估计 |
|------|------|----------|
| **新增** | `src/kid_app/badge_prompts.py` | ~30 (已写) |
| **新增** | `src/kid_app/badge_db.py` | ~120 (已写) |
| **新增** | `src/kid_app/badge_generator.py` | ~250 |
| **新增** | `src/kid_app/badge_ai_placeholder.py` (薄壳, 取代直连 LLM) | ~80 |
| **新增** | `src/kid_app/badge_portal.py` (Nous Portal 状态检查) | ~100 |
| **新增** | `src/kid_app/routes/badge_workflow.py` | ~400 |
| **新增** | `src/kid_app/templates/config-badge.html` | ~600 |
| **修改** | `src/kid_app/app.py` | -2 / +5 (注册 router + 重置 cache) |
| **修改** | `src/kid_app/templates/_sidebar.html` | +8 (Portal 加链接) |
| **新增** | `tests/test_badge_prompts.py` | (已写 17 cases) |
| **新增** | `tests/test_badge_db.py` | (已写 25 cases) |
| **新增** | `tests/test_badge_ai_placeholder.py` (薄壳版) | ~200 |
| **新增** | `tests/test_badge_portal.py` | ~150 |
| **新增** | `tests/test_badge_generator.py` | ~200 |
| **总计** | | ~2,400 行新代码 |

PR-B 范围另外估算（~150 行，主要是 app.py 两处 dict 改函数）。

### 0.4 跨 profile 副作用（用户 2026-06-12 ack）

PR-A 实施时会在 `~/.hermes/profiles/dizical/` 创建一个新 hermes profile:
- `hermes profile create dizical --clone-from moni --no-skills`（继承 moni 的 key, 不带 bundled skills）
- 重写 `SOUL.md` 为 dizical 专用 (跟 moni 内容分析 agent 不同, dizical 只做 placeholder 草拟)
- 清空 `memories/`（不让 moni 的记忆污染）
- `hermes model --profile dizical --provider deepseek -m deepseek-chat`（默认 model, 用户可切）
- **为什么不在 dizical 项目里持 key**: hermes 已经统一管理所有 provider, dizical 重复实现会失去版本管理, 也难以跟其它 hermes profile 共享 credit

这个动作会**修改非 dizical 项目的目录**（`~/.hermes/profiles/dizical/`）, 在 AGENTS.md 的 "跨 profile 副作用" 规则下需要显式用户授权。

---

## 1. 数据契约

### 1.1 写三表策略（用户拍板 2026-06-12 路径 A）

**所有 V1 新增 badge** 写 1 行 `achievement_badges` (`is_locked=0, version=1, is_current=1`)。**不沿用** `migrate_achievements.py:419` 老代码"milestone 写 2 行"。

跟 `add_badge_early.py:82-83` / `add_badge_lucky61.py:69-72` 5/20+ 实际惯例一致。

### 1.2 版本管理（V1 启动）

| 操作 | 文件命名 | DB 行为 |
|------|---------|---------|
| 新建第 1 张 | `{id}_v1.png` | INSERT (version=1, is_current=1) |
| 换新图 (US-5 "重新生图") | `{id}_v2.png` | UPDATE 旧行 is_current=0；INSERT 新行 (version=2, is_current=1) |
| 已存在 is_current=1 行 | (跳过) | 触发 "换新图" 流程 |

**SQL**：
```sql
-- 找下一个 version 号
SELECT COALESCE(MAX(version), 0) + 1
FROM achievement_badges
WHERE achievement_id = ?

-- 重新生图
UPDATE achievement_badges SET is_current = 0
WHERE achievement_id = ? AND is_current = 1;

INSERT INTO achievement_badges
  (achievement_id, url, is_locked, version, is_current)
VALUES (?, ?, 0, ?, 1);
```

**现有 60 行不动**（文件名 `{id}.png`），等下次"换新图"时再升级到 `_v{n}` 命名。

### 1.3 DB schema 不变

3 张表 schema 全部不变，只填新行。**不**做 `ALTER TABLE` / `CREATE TABLE`。

---

## 2. 模块拆分（5 个新文件）

### 2.1 `src/kid_app/badge_prompts.py` — 模板与组装

```python
"""Enamel pin prompt 模板 + placeholder 组装"""
UNLOCKED_TPL = (
    "An emoji-adjacent 3D enamel pin of [PLACEHOLDER]. "
    "Polished gold metal borders enclose flat, glossy enamel fills. "
    "The design is a centered, iconic illustration with a smooth, "
    "friendly silhouette and vibrant colors, matching a child's "
    "achievement badge style. Studio lighting reflects off the "
    "reflective enamel and raised gold metal edges. Orthographic, "
    "straight-on view, high quality, isolated on a clean white background."
)

def build_unlocked_prompt(placeholder: str) -> str:
    """组装完整 prompt. placeholder 必填, 长度 5-500 字符."""
    if not placeholder or len(placeholder.strip()) < 5:
        raise ValueError("placeholder 至少 5 字符")
    return UNLOCKED_TPL.replace("[PLACEHOLDER]", placeholder.strip())

def build_locked_template(placeholder: str) -> str:
    """locked 态 prompt (备用, V1 不存). 跟 unlock 模板同形, 改用灰度描述."""
    return (
        "An emoji-adjacent 3D enamel pin of [PLACEHOLDER], "
        "monochrome grayscale, no vibrant colors, raw iron-like finish, "
        "matching a child's locked achievement badge style..."
    )
```

### 2.2 `src/kid_app/badge_db.py` — DB 事务封装

```python
"""Badge 三表写入 + 事务 + 回滚"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.database import db

_BADGES_DIR = Path(__file__).parent / "static" / "badges"


@contextmanager
def badge_write_tx():
    """badge 上线事务, 失败自动回滚所有写入"""
    with db._get_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def check_id_unique(badge_id: str) -> bool:
    """检查 badge id 唯一. True=可用, False=已存在."""
    with db._get_connection() as conn:
        cur = conn.execute(
            "SELECT 1 FROM achievements WHERE id = ? LIMIT 1", (badge_id,))
        return cur.fetchone() is None


def next_version(badge_id: str) -> int:
    """返回下一个 version 号 (= MAX+1, 最小 1)."""
    with db._get_connection() as conn:
        cur = conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM achievement_badges "
            "WHERE achievement_id = ?", (badge_id,))
        return int(cur.fetchone()[0])


def insert_achievement_row(conn, ach: dict):
    """写 achievements 表 (1 行)"""
    conn.execute("""
        INSERT INTO achievements
          (id, name, type, category, stat_logic, description,
           display_format, threshold, unlocked_template, placeholder,
           sort_order, seasonal_type)
        VALUES
          (:id, :name, :type, :category, :stat_logic, :description,
           :display_format, :threshold, :unlocked_template, :placeholder,
           :sort_order, :seasonal_type)
    """, ach)


def insert_achievement_stats_row(conn, badge_id: str):
    """写 achievement_stats 表 (仅 milestone, 1 行, achieved='N')"""
    conn.execute("""
        INSERT INTO achievement_stats
          (achievement_id, achieved, raw_stats, computed_value)
        VALUES (?, 'N', '{}', NULL)
    """, (badge_id,))


def insert_badge_row(conn, badge_id: str, url: str, version: int):
    """写 achievement_badges 表 (1 行 unlocked)"""
    conn.execute("""
        INSERT INTO achievement_badges
          (achievement_id, url, is_locked, version, is_current)
        VALUES (?, ?, 0, ?, 1)
    """, (badge_id, url, version))


def fetch_max_sort_order() -> int:
    """返回当前 max(sort_order)"""
    with db._get_connection() as conn:
        cur = conn.execute("SELECT COALESCE(MAX(sort_order), 0) FROM achievements")
        return int(cur.fetchone()[0])


def fetch_badge_url(badge_id: str) -> str | None:
    """返回 is_current=1 行的 url (PR-B 用). None=未找到."""
    with db._get_connection() as conn:
        cur = conn.execute(
            "SELECT url FROM achievement_badges "
            "WHERE achievement_id = ? AND is_current = 1 LIMIT 1",
            (badge_id,))
        row = cur.fetchone()
        return row[0] if row else None
```

### 2.3 `src/kid_app/badge_generator.py` — 流水线协调

```python
"""6 步流水线: prompt → FAL → 拿图 → 去背 → 保存 → 写 DB"""
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Callable

from PIL import Image
from src.kid_app.badge_prompts import build_unlocked_prompt
from src.kid_app.badge_db import (
    badge_write_tx, check_id_unique, fetch_max_sort_order,
    insert_achievement_row, insert_achievement_stats_row,
    insert_badge_row, next_version,
)

_BADGES_DIR = Path(__file__).parent / "static" / "badges"

# 复用 config.py:955-1069 的 hermes 框架
_HERMES_CMD = 'hermes chat -q "$(cat {tmp_path})" -t image_gen --yolo -Q'


def _dedupe_to_rgba(src: Path) -> bool:
    """复用 dedupe_bg_lucky61.py 逻辑. True=成功去背, False=保留 RGB."""
    try:
        im = Image.open(src).convert("RGBA")
        pixels = im.load()
        w, h = im.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if r > 220 and g > 220 and b > 220 and a > 200:
                    pixels[x, y] = (r, g, b, 0)
                elif r > 200 and g > 200 and b > 200:
                    if max(r, g, b) - min(r, g, b) < 30:
                        pixels[x, y] = (r, g, b, 0)
        im.save(src)
        # 验证: 重读 mode, 必须是 RGBA
        return Image.open(src).mode == "RGBA"
    except Exception:
        return False


def _resolve_image_source(output: str, project_root: Path) -> str | None:
    """从 hermes 输出解析图片路径/URL (复用 config.py:1001-1018 逻辑)"""
    for line in output.split("\n"):
        line = line.strip()
        if "MEDIA:" in line:
            parts = line.split("MEDIA:")
            if len(parts) > 1:
                candidate = parts[1].strip().split()[0]
                if Path(candidate).exists():
                    return candidate
        if line.startswith("http") and (".png" in line or ".jpg" in line or "fal" in line):
            return line
        if line.startswith("/") and (line.endswith(".png") or line.endswith(".jpg")):
            if Path(line).exists():
                return line
    return None


def run_badge_pipeline(
    badge_id: str,
    placeholder: str,
    on_status: Callable[[str, str], None],  # (stage, message)
    project_root: Path,
) -> dict:
    """
    完整流水线. 返回:
      {
        "ok": bool,
        "image_path": str | None,   # 落盘文件
        "dedupe_ok": bool,           # 去背是否成功
        "error": str | None,
      }
    失败回滚: 任何一步抛异常, 已生成文件删除, 不写 DB.
    """
    created_files: list[Path] = []

    try:
        # ── 步骤 1: 校验 ──
        on_status("step1_validate", "校验 badge id 唯一")
        if not badge_id or not all(c.isalnum() or c == "_" for c in badge_id):
            return {"ok": False, "error": "badge id 必须只含英文/数字/下划线", "dedupe_ok": False}
        if not check_id_unique(badge_id):
            return {"ok": False, "error": f"badge id '{badge_id}' 已存在", "dedupe_ok": False}
        if not placeholder or len(placeholder.strip()) < 5:
            return {"ok": False, "error": "placeholder 至少 5 字符", "dedupe_ok": False}

        # ── 步骤 2: 写 prompt ──
        on_status("step2_prompt", "组装 enamel pin prompt")
        prompt = build_unlocked_prompt(placeholder)
        on_status("step2_prompt", f"prompt 已组装 ({len(prompt)} 字符)")

        # ── 步骤 3: 调 hermes + FAL (复用 config.py:971-984) ──
        on_status("step3_fal", "调用 hermes + FAL gpt-image-2 (30-60 秒)")
        query = f"用 image_generate 工具生成图片, prompt 如下, aspect_ratio 用 square:\n\n{prompt}"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(query)
            tmp_path = f.name
        shell_cmd = _HERMES_CMD.format(tmp_path=tmp_path)
        proc = subprocess.Popen(
            shell_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=str(project_root), bufsize=1, text=True,
        )
        output_lines = []
        for line in proc.stdout:
            output_lines.append(line.rstrip())
        proc.wait(timeout=120)
        output = "\n".join(output_lines)
        Path(tmp_path).unlink(missing_ok=True)

        # ── 步骤 4: 拿图 ──
        on_status("step4_fetch", "解析 hermes 输出拿图片")
        image_source = _resolve_image_source(output, project_root)
        if not image_source:
            return {"ok": False, "error": f"未找到图片. hermes 输出: {output[:200]}", "dedupe_ok": False}

        # ── 步骤 5: 保存到 _v1.png ──
        on_status("step5_save", "保存到 static/badges/{id}_v1.png")
        _BADGES_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = _BADGES_DIR / f"{badge_id}_v1.png"
        if image_source.startswith("http"):
            urllib.request.urlretrieve(image_source, dest_path)
        else:
            shutil.copy2(image_source, dest_path)
        created_files.append(dest_path)
        on_status("step5_save", f"图片已保存 ({dest_path.stat().st_size} bytes)")

        # ── 步骤 6: 去白底 ──
        on_status("step6_dedupe", "PIL 去白底 (RGB→RGBA)")
        dedupe_ok = _dedupe_to_rgba(dest_path)
        on_status("step6_dedupe", "去背成功" if dedupe_ok else "去背失败, 保留 RGB (前端会显示白方框)")

        return {
            "ok": True,
            "image_path": str(dest_path),
            "dedupe_ok": dedupe_ok,
            "error": None,
        }

    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "hermes 进程超时 (120 秒)", "dedupe_ok": False}
    except Exception as e:
        # ── 失败回滚: 删文件 ──
        for f in created_files:
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass
        return {"ok": False, "error": f"流水线异常: {e}", "dedupe_ok": False}


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
    把流水线的产物 (image_path) 写进三表. 走 badge_write_tx 事务.
    失败抛异常, 由调用方决定是否删 image_path.
    """
    sort_order = fetch_max_sort_order() + 1
    version = next_version(badge_id)  # 1 (新 badge)
    url = f"/static/badges/{Path(image_path).name}"  # /static/badges/{id}_v1.png

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

    return True
```

### 2.4 `src/kid_app/badge_ai_placeholder.py` — AI 草拟 placeholder

```python
"""AI 草拟 placeholder (Gemini 2.5 Flash). 用户在 Step 2 选 (B) 时调. 复用 subject_info.py key 读取."""
import json
import urllib.request
from pathlib import Path


def _get_google_key() -> str:
    """复用 subject_info.py:31-40"""
    env_path = Path('/Users/mt16/.hermes/.env')
    if not env_path.exists():
        return ''
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith('GOOGLE_API_KEY=') and not line.startswith('#'):
            return line.split('=', 1)[1].strip()
    return ''


def draft_placeholder(zh_story: str, badge_name: str) -> str:
    """
    输入: 中文典故 + 中文 badge 名称.
    输出: 英文 placeholder (enamel pin 风格, 30-200 词).

    Fallback: API 失败时返回固定模板占位, 提示用户手动填.
    """
    api_key = _get_google_key()
    if not api_key:
        return f"a cute chibi girl with long black hair playing a bamboo flute, {badge_name}"

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={api_key}"
    )
    prompt = (
        f"Based on this Chinese reference story and badge name, write a 1-2 sentence "
        f"English description for an enamel pin badge image. "
        f"Focus on: character (chibi black-haired girl playing bamboo flute), "
        f"key visual element from story, dreamy/heroic style, "
        f"vibrant colors. Output ONLY the description, no preamble.\n\n"
        f"Badge name: {badge_name}\n"
        f"Reference story: {zh_story}\n"
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 200, "temperature": 0.7},
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        # Fallback 模板
        return f"a cute chibi girl with long black hair playing a bamboo flute, {badge_name}"
```

### 2.5 `src/kid_app/routes/badge_workflow.py` — FastAPI 路由

```python
"""
Badge 制作工作流路由 (config 子路由).
端点:
  GET  /config/badge               - 分步表单 HTML 页面
  GET  /config/api/badge/check-id  - 实时查重
  POST /config/api/badge/ai-draft  - AI 草拟 placeholder
  POST /config/api/badge/preview   - SSE 流式: 跑流水线 (只到预览, 不写 DB)
  POST /config/api/badge/commit    - 写三表 (走 commit_badge_to_db)
  GET  /config/api/badge/calc-snippet - 返回 calc logic 代码模板
  POST /config/api/badge/batch-preview  - (PR-C) 批量预览
  POST /config/api/badge/batch-commit   - (PR-C) 批量写库
"""
import json
import queue
import threading
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from src.kid_app import badge_db, badge_generator, badge_ai_placeholder
from src.kid_app.badge_prompts import build_unlocked_prompt, UNLOCKED_TPL

router = APIRouter(prefix="/config", tags=["badge-workflow"])
_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/


# ─── 页面 ──────────────────────────────────────────────────────────
@router.get("/badge", response_class=HTMLResponse)
def config_badge():
    from src.kid_app.app import render
    from src.database import db
    pin_locked = "true" if db.get_setting("dad_pin") else "false"
    return render("config-badge", active_nav="portal", pin_locked=pin_locked)


# ─── API: 实时查重 ──────────────────────────────────────────────
@router.get("/api/badge/check-id")
def api_check_id(id: str):
    return JSONResponse({"ok": badge_db.check_id_unique(id)})


# ─── API: AI 草拟 placeholder ───────────────────────────────────
@router.post("/api/badge/ai-draft")
async def api_ai_draft(request: Request):
    body = json.loads(await request.body())
    zh_story = body.get("story", "").strip()
    badge_name = body.get("name", "").strip()
    if not zh_story or len(zh_story) < 5:
        return JSONResponse({"ok": False, "error": "典故至少 5 字符"}, status_code=400)
    placeholder = badge_ai_placeholder.draft_placeholder(zh_story, badge_name)
    return JSONResponse({"ok": True, "placeholder": placeholder})


# ─── API: 预览 (SSE) ──────────────────────────────────────────────
@router.post("/api/badge/preview")
async def api_preview(request: Request):
    """SSE 流式跑流水线. 只到 preview, 不写 DB."""
    body = json.loads(await request.body())
    badge_id = body.get("id", "").strip()
    placeholder = body.get("placeholder", "").strip()

    if not badge_id or not placeholder:
        return JSONResponse({"ok": False, "error": "id 和 placeholder 必填"}, status_code=400)

    result_queue = queue.Queue()

    def run():
        result = badge_generator.run_badge_pipeline(
            badge_id=badge_id,
            placeholder=placeholder,
            on_status=lambda stage, msg: result_queue.put(("status", stage, msg)),
            project_root=_PROJECT_ROOT,
        )
        result_queue.put(("done", result))

    async def stream():
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        while True:
            try:
                item = result_queue.get(timeout=130)
                if item[0] == "status":
                    _, stage, msg = item
                    yield f"data: {json.dumps({'type': 'status', 'stage': stage, 'message': msg})}\n\n"
                elif item[0] == "done":
                    _, result = item
                    yield f"data: {json.dumps({'type': 'done', 'data': result})}\n\n"
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'error', 'message': '生成超时'})}\n\n"
                break

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── API: 写三表 (commit) ───────────────────────────────────────
@router.post("/api/badge/commit")
async def api_commit(request: Request):
    """写三表 + 处理失败回滚"""
    body = json.loads(await request.body())
    pin = body.get("pin", "")
    # PIN 验证 (跟 config-blindbox 一致)
    from src.database import db
    stored = db.get_setting("dad_pin")
    if stored and pin != stored:
        return JSONResponse({"ok": False, "error": "PIN 不对"}, status_code=401)

    badge_id = body["id"]
    image_path = body["image_path"]
    dedupe_ok = body.get("dedupe_ok", False)

    try:
        badge_generator.commit_badge_to_db(
            badge_id=badge_id,
            name=body["name"],
            type_label=body["type"],
            category=body["category"],
            stat_logic=body["stat_logic"],
            description=body["description"],
            display_format=body["display_format"],
            threshold=body.get("threshold"),
            placeholder=body["placeholder"],
            unlocked_template=build_unlocked_prompt(body["placeholder"]),
            seasonal_type=body.get("seasonal_type", "monthly"),
            image_path=image_path,
        )
    except Exception as e:
        # 失败: 删图片, 不写 DB
        Path(image_path).unlink(missing_ok=True)
        return JSONResponse({"ok": False, "error": f"写库失败: {e}"}, status_code=500)

    return JSONResponse({
        "ok": True,
        "badge_id": badge_id,
        "dedupe_ok": dedupe_ok,
        "warning": None if dedupe_ok else "去白底失败, 上线后 kid-app 会显示白方框, 待人工修复",
    })


# ─── API: calc logic 代码片段 ───────────────────────────────────
_CALC_TEMPLATES = {
    "milestone_streak": """# 贴到 src/achievement_definitions.py 的 _calc_milestone():
if aid == "{badge_id}":
    return CalcResult(
        achieved=streak >= {threshold},
        computed_value=streak,
        extra=None,
        achieved_at=achieved_at if streak >= {threshold} else None,
        "连续 ≥ {threshold} 天"
    )""",
    "milestone_total": """# 贴到 _calc_milestone():
if aid == "{badge_id}":
    return CalcResult(
        achieved=total_mins >= {threshold},
        computed_value=total_mins,
        extra=None,
        achieved_at=achieved_at if total_mins >= {threshold} else None,
        "累计 ≥ {threshold} 分钟"
    )""",
    # ... (其他模板)
}


@router.get("/api/badge/calc-snippet")
def api_calc_snippet(template: str, badge_id: str, threshold: int = 0):
    tpl = _CALC_TEMPLATES.get(template, "# 模板 {template} 不存在, 请人工写 calc 逻辑")
    code = tpl.format(badge_id=badge_id, threshold=threshold)
    return JSONResponse({"ok": True, "code": code})


# ─── PR-C 路由 (批量模式) ───────────────────────────────────────
# (PR-C 时实现, 现在先注释掉)
# @router.post("/api/badge/batch-preview")
# @router.post("/api/badge/batch-commit")
```

---

## 3. 前端骨架 (`config-badge.html`)

### 3.1 关键设计
- 沿用 dizicute 6 色 + 4 typography（DESIGN.md）
- 4 步进度条（圆点 + 数字）+ GSAP `back.out(1.4)` 切换
- 底部「上一步 / 下一步 / 保存草稿」三按钮（**V1 不做草稿持久化**，"保存草稿"按钮 disabled + tooltip "V1 不支持"）
- PIN 验证 modal 沿用 config-blindbox 模式

### 3.2 关键 DOM 结构

```html
<!-- Step 1: 元数据 -->
<div class="step active" data-step="1">
  <input id="badgeId" required pattern="[a-zA-Z0-9_]+">
  <input id="badgeName" required>
  <select id="type">  <!-- 突破/段位/巅峰/执着/晋级/神秘 -->
  <input type="radio" name="category" value="milestone|seasonal">
  <select id="seasonalType" disabled>  <!-- daily/weekly/monthly/stage -->
  <input id="sortOrder" type="number">
</div>

<!-- Step 2: placeholder + 典故 -->
<div class="step" data-step="2">
  <input type="radio" name="phSource" value="manual|ai">
  <textarea id="phManual">  <!-- (A) 我自己写 -->
  <textarea id="phAiStory">  <!-- (B) AI 草拟典故中文 -->
  <button id="aiDraftBtn">生成草稿</button>
  <textarea id="phAiResult" readonly>  <!-- AI 草拟结果, 用户可编辑 -->
  <textarea id="description">
  <input id="displayFormat">
  <div id="promptPreview">  <!-- 实时组装 prompt, 用户可"高级: 编辑模板" -->
</div>

<!-- Step 3: 计算逻辑 -->
<div class="step" data-step="3">
  <select id="calcTemplate">  <!-- streak_N / total_N / top1/2/3 / ... -->
  <pre id="calcSnippet">  <!-- 显示代码片段, [复制] 按钮 -->
</div>

<!-- Step 4: 生成 & 预览 -->
<div class="step" data-step="4">
  <button id="startGenBtn">开始生成</button>
  <div id="genStatus">  <!-- SSE 状态条: 1️⃣ 2️⃣ 3️⃣ ... -->
  <div id="genImages">  <!-- 预览: 原图 + 红底验证 -->
  <button id="regenBtn" disabled>重新生图</button>
  <button id="acceptBtn">接受当前结果</button>
  <button id="cancelBtn">取消</button>
</div>

<!-- Step 5: 确认上线 (独立确认页) -->
<div class="step" data-step="5">
  <div id="commitSummary">
  <input id="pinInput" type="password">
  <button id="commitBtn">写入数据库</button>
</div>

<!-- 上线成功页 -->
<div class="step" data-step="done">
  ✅ 上线成功
  <pre id="commitResult">
  <a href="/badges">查看成就殿堂</a>
  <button id="enterBatchBtn">进入批量模式</button>  <!-- PR-C 入口, V1 disabled -->
</div>
```

### 3.3 关键 JS 流程

```js
// 状态机: 收集所有表单数据到 window._formData
let formData = {
  id: '', name: '', type: '', category: 'milestone', seasonalType: 'monthly',
  sortOrder: null, phSource: 'manual', placeholder: '', description: '',
  displayFormat: '', calcTemplate: '',
};

let previewResult = null;  // { imagePath, dedupeOk }

async function startGen() {
  const evtSource = new EventSource(...);  // 实际用 fetch + ReadableStream
  // 监听 status/done/error
  // 完成后把 imagePath 存到 formData.imagePath
}

async function commit() {
  const pin = document.getElementById('pinInput').value;
  const res = await fetch('/config/api/badge/commit', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({...formData, imagePath: previewResult.imagePath, dedupeOk: previewResult.dedupeOk, pin}),
  });
  const data = await res.json();
  if (data.ok) { showStep('done'); }
  else { showToast('error', data.error); }
}
```

### 3.4 红底预览渲染

```js
function renderRedBgPreview(imagePath) {
  // 用 PIL 在后端生成一个红底对比图? 还是前端 canvas?
  // 选前端: 不增加后端复杂度
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.src = '/static/badges/' + imagePath.split('/').pop();
  img.onload = () => {
    const canvas = document.createElement('canvas');
    canvas.width = img.width; canvas.height = img.height;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'rgb(255, 0, 0)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    document.getElementById('redBgImg').src = canvas.toDataURL();
  };
}
```

---

## 4. PR-A 实施步骤

### 4.1 顺序
1. **创建分支** `feat/badge-workflow-pr-a`（基于 main @ b559842）
2. **新增文件**（按依赖顺序）：
   - `src/kid_app/badge_prompts.py`（无依赖）
   - `src/kid_app/badge_db.py`（依赖 src.database）
   - `src/kid_app/badge_generator.py`（依赖 badge_prompts + badge_db）
   - `src/kid_app/badge_ai_placeholder.py`（独立）
   - `src/kid_app/routes/badge_workflow.py`（依赖前 4 个）
   - `src/kid_app/templates/config-badge.html`（独立）
3. **修改文件**：
   - `src/kid_app/app.py:1582-1584` 加 `from src.kid_app.routes.badge_workflow import router as badge_workflow_router; app.include_router(badge_workflow_router)`
   - `src/kid_app/templates/_sidebar.html` Portal 区域加 "徽章制作" 链接到 `/config/badge`
4. **新增测试**：
   - `tests/test_badge_workflow.py`：测试 `build_unlocked_prompt` / `_dedupe_to_rgba` / `_resolve_image_source` / `check_id_unique` / `next_version` / `commit_badge_to_db`（用临时 db 或 mock）
   - 集成测试：mock hermes 调用，跑完整 6 步流水线（不调真实 FAL）
5. **本地验证**：
   - `python3 -m pytest tests/test_badge_workflow.py -v`（必须全过）
   - 启动服务：PIDFILE 清，端口 8765 / 8766
   - 浏览器走完 4 步表单 + 上线一个新 badge
   - curl `/badges` 看到新 badge
   - curl `/achievements` 看到新 badge 在进度里
6. **commit + PR**：
   - 1 个 commit（或拆几个：模板 / DB / 路由 / 前端）
   - `gh pr create`（避免 security scan，**让用户手建**——AGENTS.md 已知）
7. **merge**（squash merge）

### 4.2 测试用例覆盖

| 测试 | 验证 |
|------|------|
| `test_build_unlocked_prompt_normal` | placeholder 替换 + 长度合理 |
| `test_build_unlocked_prompt_too_short` | placeholder < 5 字符抛 ValueError |
| `test_dedupe_rgba_success` | 白底像素→透明，mode=RGBA |
| `test_dedupe_rgba_rgb_input` | RGB 输入正确转 RGBA + 去背 |
| `test_resolve_image_source_media` | "MEDIA:/path" 格式 |
| `test_resolve_image_source_http` | "http://fal..." 格式 |
| `test_resolve_image_source_local` | "/path/to.png" 格式 |
| `test_check_id_unique` | 不存在/存在两种情况 |
| `test_next_version_new` | 新 badge 返回 1 |
| `test_next_version_existing` | 已存在 v1, v2 → 返回 3 |
| `test_commit_writes_3_tables` | 用 mock db, 验证 INSERT 顺序 + 参数 |
| `test_commit_rollback_on_failure` | 第 3 张表失败 → 前 2 张回滚 |
| `test_pipeline_failure_cleans_files` | 模拟步骤 3 失败, 验证图片被删 |
| `test_ai_draft_fallback` | API key 缺失 → 返回 fallback 字符串 |
| `test_calc_snippet_format` | 各 template 替换正确 |

### 4.3 验证脚本（手测，不用 pytest）

```bash
# 1. 启动服务
./scripts/start-prod.sh
# 2. 浏览器 http://localhost:8765/config/badge
# 3. 走完 4 步表单
# 4. curl /badges 验证新 badge 出现
curl -s http://localhost:8765/badges | grep "your_test_badge_id"
# 5. sqlite3 验证 3 表数据
sqlite3 data/dizi.db "SELECT * FROM achievements WHERE id='your_test_badge_id'"
sqlite3 data/dizi.db "SELECT * FROM achievement_badges WHERE achievement_id='your_test_badge_id'"
# 6. 检查文件
ls -la src/kid_app/static/badges/your_test_badge_id_v1.png
```

---

## 5. PR-B 技术方案

### 5.1 改动范围
- `app.py:420-439` `BADGE_URLS` dict → 函数 `def get_badge_url(aid: str) -> str`
- `app.py:1423-1442` `BADGE_FILES` dict → 函数 `def get_badge_file(aid: str) -> str`

### 5.2 实现

```python
# app.py 顶部
_BADGE_URL_CACHE = {"ts": 0, "data": {}}
_CACHE_TTL = 60  # 秒

def _refresh_badge_url_cache():
    """读 DB is_current=1 的所有 badge url. cache 60 秒."""
    with db._get_connection() as conn:
        cur = conn.execute(
            "SELECT achievement_id, url FROM achievement_badges WHERE is_current = 1"
        )
        _BADGE_URL_CACHE["data"] = {row[0]: row[1] for row in cur.fetchall()}
        _BADGE_URL_CACHE["ts"] = time.time()

def get_badge_url(aid: str, default: str = "/static/badges/medal_badge.png") -> str:
    """(替换 BADGE_URLS dict) 返回当前生效的 badge url. cache 60s."""
    if time.time() - _BADGE_URL_CACHE["ts"] > _CACHE_TTL:
        _refresh_badge_url_cache()
    return _BADGE_URL_CACHE["data"].get(aid, default)

def get_badge_file(aid: str, default: str = "/static/badges/medal_badge.png") -> str:
    """(替换 BADGE_FILES dict) — 跟 get_badge_url 一样实现. 重复为保持 dict 命名."""
    return get_badge_url(aid, default)
```

### 5.3 回归
- 现有 36 个 achievement 在 `/badges` / `/achievements` 渲染**像素级无变化**（手工走查）
- `pytest` 跑全部测试, 不能有 regression
- 性能: 每分钟 cache 刷新, 1 次 SQL `SELECT ... WHERE is_current=1` 查 ~36 行, 微秒级

### 5.4 commit hook
PR-B 合并后, `commit_badge_to_db` 写新行 → 需要**清 cache** 让新 badge 立刻生效:

```python
# badge_generator.py 末尾
def commit_badge_to_db(...):
    ...
    with badge_write_tx() as conn:
        ...
    # 写完清 cache, 让 PR-B 立刻读到新行
    from src.kid_app.app import _BADGE_URL_CACHE
    _BADGE_URL_CACHE["ts"] = 0
    return True
```

---

## 6. PR-C 技术方案

### 6.1 入口
- 上线成功页 (`Step done`) 加按钮 "进入批量模式: 基于此 badge 衍生 N 个"
- 点击后, Step 2 起走"简化流程", 元数据 + 典故 + calc 模板都**继承已认可 badge**, 只让用户填 placeholder N 次

### 6.2 简化流程

```html
<!-- 批量 Step 2 -->
<input id="batchN" type="number" min="1" max="20" value="5">
<textarea id="batchPlaceholders" placeholder="一行一个 placeholder">
<!-- 继承自来源 badge 的不可改字段: id prefix / name prefix / category / displayFormat / type / calcTemplate -->
<!-- 派生 N 个 badge id: lucky_61_2026 (源) → lucky_61_2026_1 / _2 / _3 ... -->
<button id="batchStartBtn">开始批量生成</button>
```

### 6.3 后端路由 (PR-C 新增)

```python
@router.post("/api/badge/batch-preview")
async def api_batch_preview(request: Request):
    """批量跑流水线, 每个 placeholder 一次 SSE 完整 status. 失败回退到单条."""
    body = json.loads(await request.body())
    source_badge = body["source_badge"]  # 已认可的 badge 元数据
    placeholders = body["placeholders"]  # list[str]
    n = len(placeholders)
    if n > 20:
        return JSONResponse({"ok": False, "error": "N 最多 20"}, status_code=400)

    async def stream():
        results = []
        for i, ph in enumerate(placeholders):
            badge_id = f"{source_badge['id']}_{i+1}"  # 派生 id
            yield f"data: {json.dumps({'type': 'item_start', 'index': i, 'badge_id': badge_id, 'placeholder': ph})}\n\n"
            # 跑单条流水线
            r = badge_generator.run_badge_pipeline(
                badge_id=badge_id, placeholder=ph,
                on_status=lambda stage, msg: ...,  # 嵌套 SSE 复杂, 改用聚合
                project_root=_PROJECT_ROOT,
            )
            results.append(r)
            yield f"data: {json.dumps({'type': 'item_done', 'index': i, 'result': r})}\n\n"
        yield f"data: {json.dumps({'type': 'all_done', 'results': results})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", ...)


@router.post("/api/badge/batch-commit")
async def api_batch_commit(request: Request):
    """一次写 N 行 achievements + N 行 achievement_badges.
    用户在前端对每个 item 决定: 通过 / 重试 / 跳过. 只 commit 通过的."""
    body = json.loads(await request.body())
    pin = body.get("pin", "")
    items = body["items"]  # [{badge_id, name, ..., imagePath, dedupeOk}, ...]
    # PIN 验证
    # 事务: 一次 INSERT N 行
    ...
```

### 6.4 简化决策
- N=0 跳过整个批量
- 每个 item 独立: 失败 = 该 item `ok=false`, 不影响其他
- 前端 UI: 表格列出每个 item (placeholder + 状态 + 通过/重试/跳过按钮)
- 全部完成后批量写库 (1 个事务)
- 重试: 跟单条预览一样, 重跑流水线产生 v+1

---

## 7. 错误处理矩阵

| 失败点 | 表现 | 兜底 |
|--------|------|------|
| badge id 重复 | API 返回 ok=false | 前端实时查重, 阻止提交 |
| placeholder < 5 字符 | API 422 | 前端 input minlength=5 |
| FAL 调用超时 (120s) | SSE error | 前端显示"重新生图"按钮 |
| hermes 输出无图片 | run_badge_pipeline 返回 error | 前端显示原因 + 重新生图 |
| PIL 去背失败 | `dedupe_ok=False` | 前端 3 按钮 (用户决策): 重新生图 / 接受带白底 / 取消 |
| 写三表失败 (UNIQUE 冲突等) | 事务回滚 + 删图 | 前端显示原因, 回到 Step 1 改 id |
| PIN 错 | 401 | 前端 PIN 输入框红框 |
| 批量模式某 1 个失败 | 该 item status=error | 前端显示"重试/跳过"二选一, 其他继续 |
| 用户刷新页面 | 表单数据丢失 | V1 不做草稿持久化, 接受这个限制 |

---

## 8. 不在范围 (硬性约束)

实施时**不能**改:
- `src/achievement_definitions.py` (计算逻辑, V1 让人工贴)
- `THEMES` dict / `config-blindbox.html` (盲盒 = 7日打卡盲盒, 不在范围)
- `static/badges/` 现有 60 个 PNG 文件名
- `achievement_badges` schema (不 ALTER)
- `app.py` 已有 22 个 API 路由 (不动)

---

## 9. V2.1 实现备注 (2026-06-14)

> **V2.1 已完成**, 以下记录实现过程中的 tradeoff 和架构决策.

### 9.1 V1 → V2.1 架构变迁

| 维度 | V1 (PR #81-84, 已废弃) | V2.1 (PR #85-90, 当前) |
|------|----------------------|----------------------|
| 流程 | 4 步表单 + 6 步流水线 (dizical 内调 hermes subprocess) | 3 步解耦 (dizical draft → hermes skill → dizical commit) |
| 生图 | dizical 服务内 spawn hermes chat | hermes agent 独立跑 skill |
| 通信 | subprocess stdout 解析 | 文件契约 (draft JSON) |
| 端点 | 9 个 | 4 个 (POST draft, GET draft, POST commit, GET discoveries) |
| 批量 | PR-C 批量模式 | 不做 |

### 9.2 V2.1 关键文件

| 文件 | 行数 | 用途 |
|------|------|------|
| `src/kid_app/badge_draft.py` | 298 | draft CRUD |
| `src/kid_app/badge_discovery.py` | 90 | discoveries 查询 |
| `src/kid_app/badge_db.py` | 205 | DB 事务封装 |
| `src/kid_app/badge_generator.py` | 587 | 流水线协调 (备用) |
| `src/kid_app/badge_portal.py` | 404 | Nous Portal 状态检查 |
| `src/kid_app/badge_prompts.py` | 53 | enamel pin prompt 模板 |
| `src/kid_app/badge_ai_placeholder.py` | 210 | AI 草拟 placeholder |
| `src/kid_app/routes/badge_workflow.py` | 196 | 4 端点 |
| `src/kid_app/templates/config-badge.html` | 1133 | V2.1 完整 UI |

### 9.3 V2.1 端点清单

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/config/api/badge/draft` | STEP 1 创建 draft |
| GET | `/config/api/badge/draft/{draft_id}` | STEP 2 skill 读 draft |
| POST | `/config/api/badge/commit-from-draft` | STEP 3 写三表 |
| GET | `/config/api/badge/discoveries` | 待确认列表 |
| POST | `/config/api/badge/ai-draft` | AI 草拟 placeholder |
| DELETE | `/config/api/badge/draft/{draft_id}` | 删除 draft |

### 9.4 踩坑

1. **SQLite WAL mode cp 丢数据** — 必须先 `PRAGMA wal_checkpoint(TRUNCATE)` 再 cp
2. **save_daily_practice UPDATE 不覆盖 practice_at** — 保留首次练习时间
3. **behavior_log.enter_time CST 兼容** — `if t.indexOf('T') >= 0` 兼容旧 UTC 格式
4. **GitHub URL 笔误** — 必须 `mariusia**wego**-commits`, gh pr list 拷 URL
5. **Portal 降级** — 不可用时写 1x1 placeholder 到 `.tmp/`, 不是 skill 目录
6. **PR 拆细 vs 合大** — 非 bug 多阶段 feature 合 1 PR
