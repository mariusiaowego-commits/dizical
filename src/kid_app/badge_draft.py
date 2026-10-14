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
- data/lib/badge_data/{draft_id}.json (项目内, 相对路径)
- data/lib/badge_data/.tmp/ (生图临时)
"""
from __future__ import annotations

import json
import os
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


# ─── 存储位置 (P0 sprint-26101302, 2026-10-13) ─────────────────────
# PLAN v1.2 目标: 草稿 JSON 与徽章图统一走 COS, 本地文件退化为可选缓存。
# P0 只落「读侧一条路径 (GET /draft/{id}) + 老草稿 image.url 补全」, 其余读点与写侧归 P1。
COS_PREFIX_BADGE = "badges/"        # 沿用现名, 不动历史 key
COS_PREFIX_DRAFT = "badge_drafts/"  # 草稿 JSON (读取走 SDK get_object, 不用 CDN)
BADGE_STORE_ENV = "BADGE_STORE"

# 真实草稿 id 是 YYYY-MM-DD_{id}_{6位hash}; DRAFT_ID_RE 偏严(▲历史注释), COS key 用白名单校验
SAFE_DRAFT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def storage_mode() -> str:
    """解析 BADGE_STORE → 'local' | 'cos'.

    AUTO (默认) = COS 凭据与 SDK 都就绪就用 COS, 否则本地。
    默认 AUTO 而不是 LOCAL: 生产忘配也走 COS (退回容器本地盘正是 2026-10-13 的事故形态)。
    """
    raw = (os.getenv(BADGE_STORE_ENV) or "AUTO").strip().upper()
    if raw == "LOCAL":
        return "local"
    from src.kid_app.cos_client import cos_uploader
    if raw == "COS":
        # 显式要 COS 但不可用 → 落 LOCAL, 但必须可见 (/health cos_ok=false, 不回退静默)
        return "cos" if cos_uploader.is_available else "local"
    return "cos" if cos_uploader.is_available else "local"


def cos_available() -> bool:
    """COS 是否真可用 (凭据 + SDK 都就绪). /health 与启动日志用."""
    from src.kid_app.cos_client import cos_uploader
    return cos_uploader.is_available


def cos_draft_key(draft_id: str) -> str:
    """草稿 JSON 在 COS 上的 key. 非法 id 直接拒 (防 key 注入)."""
    if not SAFE_DRAFT_ID_RE.match(draft_id or ""):
        raise ValueError(f"draft_id 非法, 不能做 COS key: {draft_id!r}")
    return f"{COS_PREFIX_DRAFT}{draft_id}.json"


def is_cos_url(url: Any) -> bool:
    """判定是不是 COS 公开 URL (用于 commit 复用 / 前端口径)."""
    return isinstance(url, str) and url.startswith("https://") and ".tcb.qcloud.la/" in url


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

    Sprint 26091201 feat/badge-3d-ccg B-1:
      meta 可选带 'card_theme' (str slug). 合法值在 VALID_CARD_THEMES 才入库;
      脏数据 (非 str / 不在表里) 直接 reject, 不走兜底 (draft 是新数据, 越严越好).
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

    # Sprint 26091201 B-1: card_theme 可选字段校验 — 给就必须是合法 slug
    if "card_theme" in meta and meta["card_theme"] is not None:
        # 延迟 import 避免循环 (badge_theme 不依赖 draft, 反之亦然)
        from src.kid_app.badge_theme import VALID_CARD_THEMES
        v = meta["card_theme"]
        if not isinstance(v, str) or v.strip().lower() not in VALID_CARD_THEMES:
            raise ValueError(
                f"meta.card_theme 非法: {v!r}, 必须是 {VALID_CARD_THEMES} 之一"
            )
        # 规整后写回 meta (strip + lower)
        meta["card_theme"] = v.strip().lower()

    # dad image#9/4: card_stars 可选字段校验 — 给就必须是 1..5 整数
    if "card_stars" in meta and meta["card_stars"] is not None:
        from src.kid_app.badge_theme import STARS_MAX, STARS_MIN, normalize_card_stars

        n = normalize_card_stars(meta["card_stars"])
        if n is None:
            v = meta["card_stars"]
            raise ValueError(
                f"meta.card_stars 非法: {v!r}, 必须是 {STARS_MIN}..{STARS_MAX} 的整数"
            )
        meta["card_stars"] = n

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


def get_draft_with_source(draft_id: str) -> tuple[BadgeDraft | None, str]:
    """读 draft, 返 (draft, 来源). 来源 ∈ {"local", "cos", "none"}.

    P0 (sprint-26101302): 本地文件优先 (本地开发 / 老草稿), 本地没有才查 COS —— 生产容器
    重建后草稿仍在 COS 上, 本地服务也能读到生产草稿 (2026-10-13 只能人工搬草稿的根修)。

    Raises:
        RuntimeError / json 异常: COS 可用但读失败 (网络/凭据) —— 不许静默当成"不存在"
    """
    if not DRAFT_ID_RE.match(draft_id):
        return None, "none"
    path = _badge_data_dir() / f"{draft_id}.json"
    if path.exists():
        return BadgeDraft.from_dict(json.loads(path.read_text(encoding="utf-8"))), "local"
    if storage_mode() != "cos":
        return None, "none"

    from src.kid_app.cos_client import cos_uploader

    try:
        raw = cos_uploader.download(cos_draft_key(draft_id))
    except FileNotFoundError:
        return None, "none"
    return BadgeDraft.from_dict(json.loads(raw.decode("utf-8"))), "cos"


def get_draft(draft_id: str) -> BadgeDraft | None:
    """读 draft (None 表示不存在). 兼容壳: 需要知道来源时用 get_draft_with_source."""
    return get_draft_with_source(draft_id)[0]


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


def backfill_image_url(draft: BadgeDraft) -> str | None:
    """老草稿惰性补 image.url (P0 sprint-26101302).

    条件全满足才动手: draft.image 是 dict + 有本地 path + 没有 url + 本地图文件还在 +
    storage_mode()==cos。上传 key = badges/{badge_id}_v{n}.png (沿用现名) 并写回 image.url。
    返回 url; 任一条不满足返 None 且**不动** draft。

    注意: 这是读接口里的写副作用 —— 只在 GET /draft/{id} 一处显式调用, 不埋在 get_draft 里。
    """
    image = draft.image
    if not isinstance(image, dict):
        return None
    if image.get("url") or not image.get("path"):
        return None
    if storage_mode() != "cos":
        return None
    src = Path(str(image["path"]))
    if not src.is_file():
        return None
    badge_id = draft.meta.get("id")
    if not badge_id:
        return None
    version = int(image.get("version") or draft.version or 1)

    from src.kid_app.cos_client import cos_uploader

    key = f"{COS_PREFIX_BADGE}{badge_id}_v{version}.png"
    url = cos_uploader.upload(key, src.read_bytes(), content_type="image/png")
    image["url"] = url
    image["storage"] = "cos"
    now = _now_iso()
    draft.updated_at = now
    draft.history.append({
        "at": now, "from": draft.status, "to": draft.status,
        "by": "dizical", "event": "image_url_backfilled", "key": key,
    })
    # P0: 草稿 JSON 仍写本地 (写侧远端化归 P1); status 不变
    save_draft(draft)
    return url


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


def write_tmp_image(draft_id: str, version: int, data: bytes) -> Path:
    """把成品图字节落 .tmp (原子写).

    P0 (sprint-26101302): 回传端点用 —— 与 skill 生图落盘**同一路径约定**, 所以
    commit_to_cos_or_static / 前端预览不用改就能吃这张图。
    """
    if not SAFE_DRAFT_ID_RE.match(draft_id or ""):
        raise ValueError(f"draft_id 非法: {draft_id!r}")
    _tmp_dir().mkdir(parents=True, exist_ok=True)
    dst = tmp_path_for(draft_id, version)
    tmp = dst.with_suffix(dst.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(dst)  # 原子 rename
    return dst


def move_tmp_to_static(draft_id: str, version: int) -> Path:
    """skill 完成后, 把临时图复制到 static/badges/{id}_v{n}.png (dizical commit 时用).

    V3.0 (2026-08-24) sprint 26082401: 仅本地 fallback 路径使用. 生产环境 (CloudRun)
    应走 commit_to_cos_or_static() 走 COS 上传, 写完整 https URL.
    """
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


def commit_image_from_draft(draft_id: str, version: int) -> dict[str, Any]:
    """V3.1 / P0 (sprint-26101302, 2026-10-13): 把成品图落到最终位置, 返 {path, url, storage, key}.

    storage ∈ {"cos", "static"} —— 调用方拿它回话 (commit 响应的 prod_visibility 不再硬编码)。
    规则:
      - COS 可用 + .tmp 图在      → 上传 badges/{id}_v{n}.png (沿用现名)
      - COS 可用 + .tmp 图不在    → 若 draft.image.url 已是 COS URL 直接复用 (回传端点/远端草稿)
      - COS 不可用                → static/badges/ fallback (老行为, 需 PR+deploy 才可见)

    Raises:
        FileNotFoundError: 临时图不存在且 draft.image.url 也不可用
        RuntimeError: COS 上传失败 (Storage First, DB 零写入 → 抛回给 commit handler)
    """
    draft = get_draft(draft_id)
    if draft is None:
        raise FileNotFoundError(f"draft '{draft_id}' 不存在")
    badge_id = draft.meta["id"]
    src = tmp_path_for(draft_id, version)

    from src.kid_app.cos_client import cos_uploader

    if cos_uploader.is_available:
        key = f"{COS_PREFIX_BADGE}{badge_id}_v{version}.png"
        if src.exists():
            url = cos_uploader.upload(key, src.read_bytes(), content_type="image/png")
            return {"path": str(src), "url": url, "storage": "cos", "key": key}
        existing_url = (draft.image or {}).get("url") if isinstance(draft.image, dict) else None
        if is_cos_url(existing_url):
            return {"path": None, "url": str(existing_url), "storage": "cos", "key": key}
        raise FileNotFoundError(f"临时图 '{src}' 不存在, 且 draft.image.url 不是 COS URL")

    local_static = move_tmp_to_static(draft_id, version)
    return {
        "path": str(local_static),
        "url": f"/static/badges/{badge_id}_v{version}.png",
        "storage": "static",
        "key": f"{COS_PREFIX_BADGE}{badge_id}_v{version}.png",
    }


def commit_to_cos_or_static(draft_id: str, version: int) -> tuple[Path | None, str]:
    """兼容壳 (P0 起改调 commit_image_from_draft): 返 (本地路径, 写入 DB 的 url).

    新代码请用 commit_image_from_draft —— 它会额外告诉你 storage=cos|static。
    """
    r = commit_image_from_draft(draft_id, version)
    return (Path(r["path"]) if r["path"] else None), r["url"]


def cleanup_tmp(draft_id: str, version: int) -> None:
    """删临时图 (commit 后或放弃时)."""
    path = tmp_path_for(draft_id, version)
    if path.exists():
        path.unlink()


def copy_external_image(src_path: str, draft_id: str, version: int) -> Path:
    """用户已有图片时, 复制到 .tmp/ 统一入口 (跟 skill 生图走同一条 commit 路径).

    src_path: 用户提供的本地文件路径 (绝对路径或相对项目根).
    返回 .tmp/{draft_id}_v{version}.png 的 Path.
    """
    import shutil
    src = Path(src_path).expanduser()
    if not src.is_absolute():
        # 相对路径以项目根为基准
        project_root = Path(__file__).resolve().parent.parent.parent
        src = project_root / src
    if not src.exists():
        raise FileNotFoundError(f"图片源文件 '{src}' 不存在")
    if not src.is_file():
        raise FileNotFoundError(f"图片源路径 '{src}' 不是文件")
    dst = tmp_path_for(draft_id, version)
    _tmp_dir().mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst
