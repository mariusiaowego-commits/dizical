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
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Schema version. 改了 schema 字段时 +1, 老读端要 backward-compatible.
SCHEMA_VERSION = 1

# 状态机: draft_created → draft_awaiting_confirm → confirmed → committed
#                                    ↑__丢弃 (skill 失败) ↑__ 放弃 (dizical 端)
VALID_STATUSES = frozenset(
    ["draft_created", "draft_awaiting_confirm", "confirmed", "committed", "discarded"]
)

# id 格式跟 V1 一样: ^[a-zA-Z0-9_]+$ (config-badge.html check-id 端点)
ID_RE = re.compile(r"^[a-zA-Z0-9_]+$")

# draft_id 唯一校验口径 (P1 返工 R1, 2026-10-14): 曾经有**两套**正则并存 ——
#   DRAFT_ID_RE      = ^\d{4}-\d{2}-\d{2}_..._[a-z0-9]{6,}$  (读路径用, 更严)
#   SAFE_DRAFT_ID_RE = ^[a-zA-Z0-9_-]+$                       (写路径用, 更松)
# 后果: `2026-10-14_x_l3g7`（哈希段 <6 位）写得进（本地 json + .tmp + COS 都有），但读路径被
# DRAFT_ID_RE 挡下 ⇒ get_draft_with_source 返 None ⇒ "写得进去读不回来"的静默失败（warden 实测）。
# 现在**只剩一套语义**：字符白名单。它同时满足
#   ① 本地文件名安全（无 / 无 . 无 ..） ② COS key 安全
#   ③ 历史草稿兼容（老 id 有顺序号/短哈希，严格模式反而读不到已存在的草稿）
DRAFT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

# 兼容别名: 指向**同一个** pattern → 语义必然一致（老 import 不必改）
SAFE_DRAFT_ID_RE = DRAFT_ID_RE


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

# 真实草稿 id 是 YYYY-MM-DD_{badge_id}_{6位hash}; 校验只看字符白名单 (见上方 DRAFT_ID_RE 注释)
# (P1 返工 R1) 原先这里另立一个"更松"的正则 → 读写判定不一致; 现在同一个对象


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
    if not DRAFT_ID_RE.match(draft_id or ""):
        raise ValueError(f"draft_id 非法, 不能做 COS key: {draft_id!r}")
    return f"{COS_PREFIX_DRAFT}{draft_id}.json"


def is_cos_url(url: Any) -> bool:
    """判定是不是 COS 公开 URL (用于 commit 复用 / 前端口径)."""
    return isinstance(url, str) and url.startswith("https://") and ".tcb.qcloud.la/" in url


# ─── 权威副本 + CAS (P1 sprint-261014, 2026-10-14) ─────────────────
# PLAN v1.2 §2: 草稿 JSON 与徽章图统一走 COS; draft 内 `storage` 标记裁决权威副本,
# `revision` 整数做写侧 CAS。本地文件退化为可选缓存。
STORAGE_LOCAL = "local"
STORAGE_COS = "cos"


class RevisionConflict(RuntimeError):
    """写侧 CAS 失败: 手里的 revision 不是最新的 (后写方拿 409, 不许静默覆盖)."""

    def __init__(self, draft_id: str, expected: int, actual: int) -> None:
        self.draft_id = draft_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"draft '{draft_id}' revision 冲突: 手里={expected}, 存储上={actual} "
            f"(有人先写过 → 重新读一次再写)"
        )


# ─── 数据类 ───────────────────────────────────────────────────────

@dataclass
class BadgeDraft:
    """Draft JSON 顶层 schema (V2 schema_version=1)。"""
    schema_version: int
    draft_id: str
    created_at: str  # ISO 8601
    version: int  # 图片 version (v1, v2, ...) — V1 已用
    meta: dict[str, Any]  # 业务字段 (id/name/type/category/...)
    image: dict[str, Any] | None  # None 时未生图
    status: str  # draft_created / draft_awaiting_confirm / confirmed / committed / discarded
    updated_at: str  # ISO 8601
    history: list[dict[str, Any]]  # 状态变更历史 (audit)
    # P1 (2026-10-14): 权威副本位置 + CAS 计数器。老 JSON 没这两个字段 → 读时给默认值
    # (storage=local / revision=1); 从 COS 读到的老 JSON 会被规范化为 storage=cos。
    storage: str = STORAGE_LOCAL
    revision: int = 1

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
            storage=(d.get("storage") or STORAGE_LOCAL),
            revision=int(d.get("revision") or 1),
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
    # P1: 权威副本 = 当前存储模式 (COS 可用 → cos, 否则 local); revision 从 1 起
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
        storage=storage_mode(),
        revision=1,
    )
    return draft


def local_path_for(draft_id: str) -> Path:
    """本地副本路径 (缓存 or 权威, 取决于该 draft 的 storage 标记)."""
    return _badge_data_dir() / f"{draft_id}.json"


def _read_local_json(draft_id: str) -> dict[str, Any] | None:
    """读本地 json 原始 dict (不存在返 None)."""
    path = local_path_for(draft_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_cos_json(draft_id: str) -> dict[str, Any] | None:
    """读 COS 上的草稿 dict (不存在返 None). COS 读失败抛 (不许当成"不存在")."""
    from src.kid_app.cos_client import cos_uploader

    if not cos_uploader.is_available:
        return None
    try:
        raw = cos_uploader.download(cos_draft_key(draft_id))
    except FileNotFoundError:
        return None
    return json.loads(raw.decode("utf-8"))


def save_draft(draft: BadgeDraft, expect_revision: int | None = None) -> Path | None:
    """写**权威副本** (P1: storage 标记裁决), 带 CAS; 返本地缓存路径 (纯 COS 时 None).

    规则:
      - draft.storage == "cos" 且 storage_mode() == "cos" → 写 COS 的 badge_drafts/{id}.json
        (**不写本地 json** —— 验收 a: 本机不出现新增本地 json); COS 写失败直接抛, 不回落本地冒充
      - 否则 → 写本地 json (本地权威 / 老草稿 / COS 不可用)
    CAS: expect_revision 与存储上的 revision 不符 → RevisionConflict (调用方转 409)。
      写成功后 revision = 存储上 revision + 1 (单调递增)。
    """
    draft_id = draft.draft_id
    if not DRAFT_ID_RE.match(draft_id or ""):
        raise ValueError(f"draft_id 非法: {draft_id!r}")

    want_cos = (draft.storage == STORAGE_COS) and storage_mode() == "cos"
    stored = _read_cos_json(draft_id) if want_cos else _read_local_json(draft_id)

    expected = expect_revision if expect_revision is not None else draft.revision
    actual = int((stored or {}).get("revision") or 1)
    if stored is not None and expected != actual:
        raise RevisionConflict(draft_id, expected, actual)

    draft.revision = (actual if stored is not None else 0) + 1
    draft.updated_at = _now_iso()
    payload = json.dumps(draft.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")

    if want_cos:
        from src.kid_app.cos_client import cos_uploader

        # fail loud: COS 可用却写失败 → 抛 (RuntimeError 透传到端点 5xx), 不静默回落本地
        cos_uploader.upload(cos_draft_key(draft_id), payload, content_type="application/json")
        return None

    path = local_path_for(draft_id)
    _atomic_write_json(path, draft.to_dict())
    return path


def _draft_from_raw(raw: dict[str, Any] | None, draft_id: str, source: str) -> BadgeDraft | None:
    """raw dict → BadgeDraft; 不是一个草稿 JSON 时返 None (记 warning, 不当 500).

    (P1 返工 R1) id 校验放宽成字符白名单后, 本地目录里"名字像 id 但不是草稿"的文件
    (例: backup.json) 也会进到读路径 —— 这里必须软着陆, 不能把端点打成 500。
    """
    if not isinstance(raw, dict):
        return None
    try:
        return BadgeDraft.from_dict(raw)
    except (KeyError, TypeError, ValueError) as e:
        logger.warning("%s 副本不是合法草稿 (%s): %r", source, draft_id, e)
        return None


def get_draft_with_source(draft_id: str) -> tuple[BadgeDraft | None, str]:
    """读 draft, 返 (draft, 来源). 来源 ∈ {"local", "cos", "none"}.

    **权威副本裁决 (P1)**: 看草稿自带的 `storage` 标记, 不看"哪份文件"。本地 json 若标着
    storage=cos 就只是缓存 —— 绝不能拿它遮住 COS 上的新版本 (P0 audit 点名的坑)。

      ① 本地有 json:
         - 标记 == "cos" → 以 COS 为准 (本地只是缓存); COS 404 → 本地兜底 (来源记 "local",
           调用方可据 draft.storage 与来源不一致识别出"读到的是旧缓存")
         - 标记 != "cos" → 本地就是权威
      ② 本地没有 → COS 读 (storage_mode()=="cos" 时); 老 JSON 规范化 storage=cos

    id 校验与写侧**同一套语义** (DRAFT_ID_RE, 见文件头注释; P1 返工 R1)。

    Raises:
        RuntimeError: COS 可用但读失败 (网络/凭据) —— 不许静默当成"不存在"
    """
    if not DRAFT_ID_RE.match(draft_id or ""):
        return None, "none"

    try:
        local_raw = _read_local_json(draft_id)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        logger.warning("本地草稿读不动, 当不存在: %s %r", draft_id, e)
        local_raw = None
    local_marks_cos = bool(local_raw) and (local_raw.get("storage") == STORAGE_COS)

    if local_raw is not None and not local_marks_cos:
        d = _draft_from_raw(local_raw, draft_id, "local")
        return (d, "local") if d is not None else (None, "none")

    if storage_mode() != "cos":
        # BADGE_STORE=LOCAL 且本地只是"COS 的缓存" → 只能把缓存当最佳可得副本
        if local_raw is None:
            return None, "none"
        d = _draft_from_raw(local_raw, draft_id, "local")
        return (d, "local") if d is not None else (None, "none")

    cos_raw = _read_cos_json(draft_id)          # 读失败会抛 (可见)
    if cos_raw is not None:
        d = _draft_from_raw(cos_raw, draft_id, "cos")
        if d is not None:
            d.storage = STORAGE_COS              # 从 COS 读到的 (含老 JSON) 一律规范化
            return d, "cos"

    if local_raw is not None:                    # 标记 cos 但 COS 上没了 → 缓存兜底
        logger.warning(
            "draft %s 标记 storage=cos 但 COS 上不存在, 退回本地缓存 (可能是旧副本)",
            draft_id,
        )
        d = _draft_from_raw(local_raw, draft_id, "local")
        return (d, "local") if d is not None else (None, "none")
    return None, "none"


def get_draft(draft_id: str) -> BadgeDraft | None:
    """读 draft (None 表示不存在). 兼容壳: 需要知道来源时用 get_draft_with_source."""
    return get_draft_with_source(draft_id)[0]


def list_drafts(status: str | None = None) -> list[BadgeDraft]:
    """列所有 draft (可按 status 过滤). P1: COS 与本地**同源合并**, 按 storage 标记裁决。

    - storage_mode()=="cos" → 列 COS 的 badge_drafts/ + 本地目录的老草稿 (COS list 失败 → 抛, 不静默)
    - 否则 → 只扫本地目录 (离线/本地开发)
    - 每份都走 get_draft_with_source 的标记裁决 (本地缓存不会遮住 COS 版本)
    """
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"status '{status}' 不在 {VALID_STATUSES}")

    ids: list[str] = []
    if storage_mode() == "cos":
        from src.kid_app.cos_client import cos_uploader

        # 失败直接抛: 只返回本地那部分会让人以为"草稿没了"(静默半盲)
        for key in cos_uploader.list_keys(COS_PREFIX_DRAFT):
            name = key[len(COS_PREFIX_DRAFT):] if key.startswith(COS_PREFIX_DRAFT) else key
            if name.endswith(".json"):
                ids.append(name[: -len(".json")])
    for path in _badge_data_dir().glob("*.json"):
        ids.append(path.stem)

    drafts: list[BadgeDraft] = []
    for draft_id in sorted(set(ids)):
        try:
            d, _src = get_draft_with_source(draft_id)
        except (json.JSONDecodeError, KeyError) as e:
            # 单个草稿坏了不阻塞其他 (跟老行为一致)
            logger.warning("list_drafts: 跳过坏草稿 %s (%r)", draft_id, e)
            continue
        if d is None:
            continue
        if status is None or d.status == status:
            drafts.append(d)
    return sorted(drafts, key=lambda d: d.created_at, reverse=True)


def update_draft_image(draft_id: str, image_info: dict[str, Any], by: str = "skill",
                       expect_revision: int | None = None) -> BadgeDraft:
    """STEP 2 skill 调: 写 image 字段 + 状态变 draft_awaiting_confirm.

    Args:
        draft_id: 草稿 ID
        image_info: {path, model, prompt_used, alpha_verified, version, ...}
        by: 操作者 (skill / dizical / user)
        expect_revision: P1 CAS —— 调用方自己读过的 revision; 与存储上不符 → RevisionConflict

    Raises:
        FileNotFoundError: draft_id 不存在
        ValueError: 状态机非法 (例如从 committed → draft_awaiting_confirm)
        RevisionConflict: 写侧 CAS 失败 (有人先写过)
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
    save_draft(draft, expect_revision=expect_revision if expect_revision is not None else draft.revision)
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
    # status 不变; 写回**权威副本** (P1: 标记 storage=cos 的草稿写 COS, 老本地草稿仍写本地)
    save_draft(draft, expect_revision=draft.revision)
    return url


def mark_draft_status(draft_id: str, new_status: str, by: str = "dizical",
                      extra: dict[str, Any] | None = None,
                      expect_revision: int | None = None) -> BadgeDraft:
    """通用状态机推进. extra 可加 event 描述.

    Args:
        new_status: 目标状态
        extra: 加到 history 末尾的额外字段 (e.g. {"event": "user_confirmed"})
        expect_revision: P1 CAS —— 调用方自己读过的 revision; 不符 → RevisionConflict

    Raises:
        RevisionConflict: 写侧 CAS 失败 (有人先写过)
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
    save_draft(draft, expect_revision=expect_revision if expect_revision is not None else draft.revision)
    return draft


def delete_draft(draft_id: str) -> bool:
    """删 draft (idempotent). V1.1 末端 [放弃] 按钮用.

    P1: 两份都删 —— COS 对象 (storage_mode()=="cos" 时) + 本地文件。任一份删掉返 True。
    """
    deleted = False
    if storage_mode() == "cos":
        from src.kid_app.cos_client import cos_uploader

        try:
            deleted = cos_uploader.delete_object(cos_draft_key(draft_id)) or deleted
        except ValueError:      # 非法 id: 本地也没有对应文件, 直接按"没删到"处理
            pass
    path = local_path_for(draft_id)
    if path.exists():
        path.unlink()
        deleted = True
    return deleted


# ─── 临时文件 helper (skill 写图, dizical 复制) ─────────────────────

def tmp_path_for(draft_id: str, version: int) -> Path:
    """生图临时文件路径 (skill 用)."""
    return _tmp_dir() / f"{draft_id}_v{version}.png"


def write_tmp_image(draft_id: str, version: int, data: bytes) -> Path:
    """把成品图字节落 .tmp (原子写).

    P0 (sprint-26101302): 回传端点用 —— 与 skill 生图落盘**同一路径约定**, 所以
    commit_to_cos_or_static / 前端预览不用改就能吃这张图。
    """
    if not DRAFT_ID_RE.match(draft_id or ""):
        raise ValueError(f"draft_id 非法: {draft_id!r}")
    _tmp_dir().mkdir(parents=True, exist_ok=True)
    dst = tmp_path_for(draft_id, version)
    tmp = dst.with_suffix(dst.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(dst)  # 原子 rename
    return dst


def move_tmp_to_static(draft_id: str, version: int, badge_id: str | None = None) -> Path:
    """skill 完成后, 把临时图复制到 static/badges/{id}_v{n}.png (dizical commit 时用).

    V3.0 (2026-08-24) sprint 26082401: 仅本地 fallback 路径使用. 生产环境 (CloudRun)
    应走 commit_to_cos_or_static() 走 COS 上传, 写完整 https URL.
    badge_id 缺省取 draft.meta.id. replace 传入 DB 里的 id, 文件名跟写入的 url 一致.
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
    if not badge_id:
        draft = get_draft(draft_id)
        if draft is None:
            raise FileNotFoundError(f"draft '{draft_id}' 不存在")
        badge_id = draft.meta["id"]
    dst = static_dir / f"{badge_id}_v{version}.png"
    shutil.copy2(src, dst)
    return dst


def badge_object_keys(badge_id: str, version: int) -> dict[str, str]:
    """PNG 与两档 webp 共用同一个 stem ({id}_v{n}). 前端按 PNG 文件名改写, stem 必须一致."""
    stem = f"{badge_id}_v{version}"
    return {
        "stem": stem,
        "png": f"{COS_PREFIX_BADGE}{stem}.png",
        "thumb": f"{COS_PREFIX_BADGE}thumbs/{stem}.webp",
        "full": f"{COS_PREFIX_BADGE}full/{stem}.webp",
    }


_WEBP_MOD: Any = None


def _webp_script():
    """加载 scripts/generate_badge_webp.py (scripts/ 不是包, 用文件路径)."""
    global _WEBP_MOD
    if _WEBP_MOD is None:
        import importlib.util
        path = Path(__file__).resolve().parent.parent.parent / "scripts" / "generate_badge_webp.py"
        spec = importlib.util.spec_from_file_location("generate_badge_webp", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"无法加载 webp 派生脚本: {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _WEBP_MOD = mod
    return _WEBP_MOD


def _derive_webp(png_bytes: bytes, keys: dict[str, str]) -> tuple[bytes, bytes]:
    try:
        return _webp_script().webp_variants(png_bytes)
    except Exception as e:
        raise RuntimeError(
            f"webp 派生失败 key={keys['thumb']} key={keys['full']}: {e}"
        ) from e


def _upload_object(uploader: Any, key: str, data: bytes, content_type: str) -> str:
    try:
        return uploader.upload(key, data, content_type=content_type)
    except Exception as e:
        raise RuntimeError(f"COS 上传失败 key={key}: {e}") from e


def _static_badges_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "src" / "kid_app" / "static" / "badges"


def _write_static_webp(stem: str, thumb: bytes, full: bytes) -> None:
    static_dir = _static_badges_dir()
    for folder, data, key in (
        ("thumbs", thumb, f"{COS_PREFIX_BADGE}thumbs/{stem}.webp"),
        ("full", full, f"{COS_PREFIX_BADGE}full/{stem}.webp"),
    ):
        dest = static_dir / folder / f"{stem}.webp"
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        except OSError as e:
            raise RuntimeError(f"webp 落盘失败 key={key}: {e}") from e


def commit_image_from_draft(
    draft_id: str, version: int, badge_id: str | None = None,
) -> dict[str, Any]:
    """把成品图落到最终位置, 并在同一步写出两档 webp. 返 {path, url, storage, key}.

    storage ∈ {"cos", "static"}. 调用方拿它回话.
    PNG 与 webp 都成功才返回; 任一步失败抛错, 调用方不入库.
    规则:
      - COS 可用 + .tmp 图在   → 上传 badges/{stem}.png + thumbs/full webp
      - COS 可用 + .tmp 图不在 → image.url 已是 COS URL 时下载该 PNG 再补两档 webp
      - COS 不可用             → static/badges/ PNG + thumbs/full webp

    badge_id 缺省 draft.meta.id. replace-image 传入请求里的 badge_id, 与 DB url 同名.
    """
    draft = get_draft(draft_id)
    if draft is None:
        raise FileNotFoundError(f"draft '{draft_id}' 不存在")
    if not badge_id:
        badge_id = draft.meta["id"]
    if not badge_id:
        raise ValueError(f"draft '{draft_id}' meta 缺 id")
    keys = badge_object_keys(badge_id, version)
    src = tmp_path_for(draft_id, version)

    from src.kid_app.cos_client import cos_uploader

    if cos_uploader.is_available:
        reused_url: str | None = None
        if src.exists():
            png_bytes = src.read_bytes()
        else:
            existing_url = (draft.image or {}).get("url") if isinstance(draft.image, dict) else None
            if not is_cos_url(existing_url):
                raise FileNotFoundError(
                    f"临时图 '{src}' 不存在, 且 draft.image.url 不是 COS URL"
                )
            try:
                png_bytes = cos_uploader.download(keys["png"])
            except Exception as e:
                raise RuntimeError(f"COS 读取 PNG 失败 key={keys['png']}: {e}") from e
            reused_url = str(existing_url)
        thumb, full = _derive_webp(png_bytes, keys)
        if reused_url is None:
            url = _upload_object(cos_uploader, keys["png"], png_bytes, "image/png")
        else:
            url = reused_url
        _upload_object(cos_uploader, keys["thumb"], thumb, "image/webp")
        _upload_object(cos_uploader, keys["full"], full, "image/webp")
        return {
            "path": str(src) if src.exists() else None,
            "url": url,
            "storage": "cos",
            "key": keys["png"],
        }

    if not src.exists():
        raise FileNotFoundError(f"临时图 '{src}' 不存在")
    png_bytes = src.read_bytes()
    thumb, full = _derive_webp(png_bytes, keys)
    local_static = move_tmp_to_static(draft_id, version, badge_id=badge_id)
    _write_static_webp(keys["stem"], thumb, full)
    return {
        "path": str(local_static),
        "url": f"/static/badges/{keys['stem']}.png",
        "storage": "static",
        "key": keys["png"],
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
