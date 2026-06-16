"""
Badge draft 草稿持久化 (V2, 2026-06-12).

设计:
- V2 工作流 STEP 1 → STEP 2 → STEP 3 通过 lib/badge_data/*.json 文件交流
- dizical 端 (routes/badge_workflow.py) 写 draft_initial (meta only, status=draft_created)
- hermes skill (badge-image) 调 update_draft_image 写 image + status=draft_awaiting_confirm
- dizical 端 (commit 端点) 读 draft, 调 badge_db 写三表, 标 status=committed
- 单向数据流: dizical → skill → dizical, 互不直接调

schema_version=1 锁定, 未来改 schema 时 +1, 老 dizical 端只读 schema_version=1 字段
(forward-compatible).

路径:
- /Users/mt16/dev/dizical/data/lib/badge_data/{draft_id}.json
- /Users/mt16/dev/dizical/data/lib/badge_data/.tmp/ (生图临时)
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

# Schema version. 改了 schema 字段时 +1, 老读端要 backward-compatible.
SCHEMA_VERSION = 1

# 状态机: draft_created → draft_awaiting_confirm → confirmed → committed
#                                    ↑__丢弃 (skill 失败) ↑__ 放弃 (dizical 端)
VALID_STATUSES = frozenset(
    ["draft_created", "draft_awaiting_confirm", "confirmed", "committed", "discarded"]
)

# id 格式跟 V1 一样: ^[a-zA-Z0-9_]+$ (config-badge.html check-id 端点)
ID_RE = re.compile(r"^[a-zA-Z0-9_]+$")

# draft_id 格式: 2026-06-12_grade-1_abc123 (日期_id_8字符hash)
DRAFT_ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[a-zA-Z0-9_-]+_[a-z0-9]{6,}$")


# ─── 路径解析 ────────────────────────────────────────────────────

def _badge_data_dir() -> Path:
    """lib/badge_data/ 根目录 (绝对路径, 跨调用一致)."""
    # __file__ = .../src/kid_app/badge_draft.py → 上 2 级 = dizical/
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "data" / "lib" / "badge_data"


def _tmp_dir() -> Path:
    """生图临时目录 (不在 badge_data/ 下, 不被 discovery 扫)."""
    return _badge_data_dir() / ".tmp"


# ─── 数据类 ───────────────────────────────────────────────────────

@dataclass
class BadgeDraft:
    """Draft JSON 顶层 schema (V2 schema_version=1)."""
    schema_version: int
    draft_id: str
    created_at: str  # ISO 8601
    version: int  # 图片 version (v1, v2, ...) — V1 已用
    meta: dict[str, Any]  # 业务字段 (id/name/type/category/...)
    image: dict[str, Any] | None  # None 时未生图
    status: str  # draft_created / draft_awaiting_confirm / confirmed / committed / discarded
    updated_at: str  # ISO 8601
    history: list[dict[str, Any]]  # 状态变更历史 (audit)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BadgeDraft":
        return cls(
            schema_version=d.get("schema_version", 1),
            draft_id=d["draft_id"],
            created_at=d["created_at"],
            version=d.get("version", 1),
            meta=d["meta"],
            image=d.get("image"),
            status=d.get("status", "draft_created"),
            updated_at=d.get("updated_at", d["created_at"]),
            history=d.get("history", []),
        )


# ─── CRUD ───────────────────────────────────────────────────────

def _validate_id(badge_id: str) -> None:
    """校验 badge id 格式 (跟 V1 check-id 端点一致)."""
    if not ID_RE.match(badge_id):
        raise ValueError(
            f"badge id '{badge_id}' 格式不对 (必须 ^[a-zA-Z0-9_]+$)"
        )


def _generate_draft_id(badge_id: str) -> str:
    """生成 draft_id: YYYY-MM-DD_{id}_{6位hash}."""
    date_part = time.strftime("%Y-%m-%d")
    hash_part = uuid.uuid4().hex[:6]
    return f"{date_part}_{badge_id}_{hash_part}"


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """原子写 JSON (tmp + rename, 防断电写一半)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)  # 原子 rename


def create_draft(meta: dict[str, Any]) -> BadgeDraft:
    """STEP 1 调: 创建 draft (meta only, status=draft_created).

    Args:
        meta: 业务字段 dict (id/name/type/category/placeholder/zh_story/...)

    Returns:
        BadgeDraft 实例 (尚未写文件, 调 save() 落盘)

    Raises:
        ValueError: meta 缺必填字段 或 id 格式错
    """
    # 必填字段校验 (跟 STEP 1 表单同步)
    # V2.2.1 (2026-06-15): cond_text 也必填 (用户拍板, 强制 modal-cond ≠ modal-desc)
    required = ["id", "name", "type", "category", "placeholder", "zh_story", "cond_text"]
    for k in required:
        if k not in meta or not meta[k]:
            raise ValueError(f"meta 缺必填字段: {k}")

    _validate_id(meta["id"])

    # category=seasonal 必填 seasonal_type
    if meta["category"] == "seasonal" and not meta.get("seasonal_type"):
        raise ValueError("category=seasonal 时必填 seasonal_type")

    draft_id = _generate_draft_id(meta["id"])
    now = _now_iso()
    draft = BadgeDraft(
        schema_version=SCHEMA_VERSION,
        draft_id=draft_id,
        created_at=now,
        version=1,
        meta=meta,
        image=None,
        status="draft_created",
        updated_at=now,
        history=[{"at": now, "from": None, "to": "draft_created", "by": "dizical"}],
    )
    return draft


def save_draft(draft: BadgeDraft) -> Path:
    """落盘 draft 到 lib/badge_data/{draft_id}.json (原子写)."""
    path = _badge_data_dir() / f"{draft.draft_id}.json"
    _atomic_write_json(path, draft.to_dict())
    return path


def get_draft(draft_id: str) -> BadgeDraft | None:
    """读 draft (None 表示文件不存在)."""
    if not DRAFT_ID_RE.match(draft_id):
        return None
    path = _badge_data_dir() / f"{draft_id}.json"
    if not path.exists():
        return None
    return BadgeDraft.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_drafts(status: str | None = None) -> list[BadgeDraft]:
    """列所有 draft (可按 status 过滤). 读 lib/badge_data/ 扫所有 .json."""
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"status '{status}' 不在 {VALID_STATUSES}")

    drafts = []
    for path in _badge_data_dir().glob("*.json"):
        try:
            d = BadgeDraft.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError) as e:
            # 单个 draft 文件坏了不阻塞其他 draft
            continue
        if status is None or d.status == status:
            drafts.append(d)
    return sorted(drafts, key=lambda d: d.created_at, reverse=True)


def update_draft_image(draft_id: str, image_info: dict[str, Any], by: str = "skill") -> BadgeDraft:
    """STEP 2 skill 调: 写 image 字段 + 状态变 draft_awaiting_confirm.

    Args:
        draft_id: 草稿 ID
        image_info: {path, model, prompt_used, alpha_verified, version, ...}
        by: 操作者 (skill / dizical / user)

    Raises:
        FileNotFoundError: draft_id 不存在
        ValueError: 状态机非法 (例如从 committed → draft_awaiting_confirm)
    """
    draft = get_draft(draft_id)
    if draft is None:
        raise FileNotFoundError(f"draft '{draft_id}' 不存在")

    valid_from = {"draft_created", "draft_awaiting_confirm"}
    if draft.status not in valid_from:
        raise ValueError(
            f"draft '{draft_id}' status={draft.status} 不允许 update_draft_image "
            f"(必须 {valid_from})"
        )

    now = _now_iso()
    old_status = draft.status
    draft.image = image_info
    draft.status = "draft_awaiting_confirm"
    draft.version = image_info.get("version", draft.version)
    draft.updated_at = now
    draft.history.append({
        "at": now, "from": old_status, "to": "draft_awaiting_confirm",
        "by": by, "event": "image_generated",
    })
    save_draft(draft)
    return draft


def mark_draft_status(draft_id: str, new_status: str, by: str = "dizical",
                      extra: dict[str, Any] | None = None) -> BadgeDraft:
    """通用状态机推进. extra 可加 event 描述.

    Args:
        new_status: 目标状态
        extra: 加到 history 末尾的额外字段 (e.g. {"event": "user_confirmed"})
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f"new_status '{new_status}' 不在 {VALID_STATUSES}")

    draft = get_draft(draft_id)
    if draft is None:
        raise FileNotFoundError(f"draft '{draft_id}' 不存在")

    now = _now_iso()
    old_status = draft.status
    draft.status = new_status
    draft.updated_at = now
    history_entry = {"at": now, "from": old_status, "to": new_status, "by": by}
    if extra:
        history_entry.update(extra)
    draft.history.append(history_entry)
    save_draft(draft)
    return draft


def delete_draft(draft_id: str) -> bool:
    """删 draft (idempotent). V1.1 末端 [放弃] 按钮用."""
    path = _badge_data_dir() / f"{draft_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


# ─── 临时文件 helper (skill 写图, dizical 复制) ─────────────────────

def tmp_path_for(draft_id: str, version: int) -> Path:
    """生图临时文件路径 (skill 用)."""
    return _tmp_dir() / f"{draft_id}_v{version}.png"


def move_tmp_to_static(draft_id: str, version: int) -> Path:
    """skill 完成后, 把临时图复制到 static/badges/{id}_v{n}.png (dizical commit 时用)."""
    import shutil
    src = tmp_path_for(draft_id, version)
    if not src.exists():
        raise FileNotFoundError(f"临时图 '{src}' 不存在")
    # static/badges/ 绝对路径
    project_root = Path(__file__).resolve().parent.parent.parent
    static_dir = project_root / "src" / "kid_app" / "static" / "badges"
    static_dir.mkdir(parents=True, exist_ok=True)
    # 从 draft_id 抽 badge id (e.g. "2026-06-12_grade-1_abc123" → "grade-1" 拿不到, 用 meta.id)
    draft = get_draft(draft_id)
    if draft is None:
        raise FileNotFoundError(f"draft '{draft_id}' 不存在")
    badge_id = draft.meta["id"]
    dst = static_dir / f"{badge_id}_v{version}.png"
    shutil.copy2(src, dst)
    return dst


def cleanup_tmp(draft_id: str, version: int) -> None:
    """删临时图 (commit 后或放弃时)."""
    path = tmp_path_for(draft_id, version)
    if path.exists():
        path.unlink()
