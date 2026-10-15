"""
Badge discovery 按需扫 (V2, 2026-06-12).

设计:
- 不后台定时器 (用户 OUT-OF-BAND 拍板, 浪费资源)
- 触发点: 用户进 /config/badge Tab "待确认" → JS GET /api/badge/discoveries
- 扫 lib/badge_data/, 跟 DB 三表 diff, 返 [待确认] 列表
- 单次调用, 0 后台资源

V2 跟 V1.1 区别:
- V1.1 badge_portal.py: 扫 hermes profile 状态 (portal auth)
- V2 badge_discovery.py: 扫 dizical 项目 lib/badge_data/ (badge drafts)
"""
from __future__ import annotations

import logging
from typing import Any

from src.kid_app import badge_db, badge_draft

logger = logging.getLogger(__name__)


def scan_badge_data_dir() -> list[dict[str, Any]]:
    """扫 lib/badge_data/, 跟 DB 三表 diff, 返 [待确认] 列表.

    Returns:
        list of dict, 每个 dict 包含:
            - draft: BadgeDraft 的 to_dict()
            - image_url: str  (前端可访问的 /static/badges/...png 路径, 如果 image.path 存在)
            - is_committable: bool  (DB 还没这条 + image 已生成)
            - db_status: str  (not_exists / exists_committed)
            - conflict_reason: str | None  (不能 commit 的原因, e.g. "DB 已有同 id")
    """
    pending = []
    for draft in badge_draft.list_drafts():
        if draft.status != "draft_awaiting_confirm":
            # 跳过非待确认状态 (draft_created, confirmed, committed, discarded)
            continue
        if draft.image is None:
            logger.warning("draft '%s' status=draft_awaiting_confirm 但 image=None, 跳过", draft.draft_id)
            continue

        # 跟 DB diff
        badge_id = draft.meta.get("id")
        is_committable = True
        conflict_reason = None
        db_status = "not_exists"
        if badge_id and badge_db.badge_exists(badge_id):
            db_status = "exists_committed"
            is_committable = False
            conflict_reason = f"DB 已有 id='{badge_id}' 的 badge, 不能再 commit (V1.1 暂无删除 API, 手动 SQL 删)"

        # 待确认预览图. P2: 权威位置看 image.storage, 不先猜本地 static 文件.
        # storage=cos (或标记缺失但 image.url 已是 COS URL) → 直接给浏览器那条 PNG.
        # 标记说 cos 却没有 url → 不回落到本地路径.
        # 其余 (local / static / 没标记) 保持 V2.6: 本地 static 文件在就用 web 路径,
        # 否则 /config/api/badge/draft-image (端点只读本地 .tmp).
        image = draft.image if isinstance(draft.image, dict) else {}
        storage = str(image.get("storage") or "").strip().lower()
        raw_url = image.get("url")
        image_url = None
        badge_id = draft.meta.get("id")
        if storage == "cos" or (not storage and badge_draft.is_cos_url(raw_url)):
            image_url = raw_url or None
        elif badge_id:
            from pathlib import Path as _P
            # 生产 static/badges/ 路径: 用 __file__ 推导项目根 (跟 badge_draft._badge_data_dir 同一来源).
            # 不能依赖 data_dir 上溯 (测试 monkeypatch 后 data_dir 在 tmp, 上溯不到项目根).
            _project_root = _P(__file__).resolve().parent.parent.parent
            commit_static_path = _project_root / "src" / "kid_app" / "static" / "badges" / f"{badge_id}_v{draft.version}.png"
            if commit_static_path.is_file():
                image_url = f"/static/badges/{badge_id}_v{draft.version}.png"
            else:
                image_url = f"/config/api/badge/draft-image?draft_id={draft.draft_id}"
        elif image.get("path"):
            image_url = image["path"]
            if "/static/badges/" in image_url:
                image_url = "/static/badges/" + image_url.split("/static/badges/")[-1]

        pending.append({
            "draft": draft.to_dict(),
            "image_url": image_url,
            "is_committable": is_committable,
            "db_status": db_status,
            "conflict_reason": conflict_reason,
        })
    return pending


def get_pending_confirmations() -> list[dict[str, Any]]:
    """STEP 3 调: 返所有 [draft_awaiting_confirm] 草稿 (前端列表用)."""
    return scan_badge_data_dir()


def get_committ_candidate(draft_id: str) -> dict[str, Any] | None:
    """单个 draft 详情 (前端 [确认上线] 按钮确认弹窗用)."""
    for item in scan_badge_data_dir():
        if item["draft"]["draft_id"] == draft_id:
            return item
    return None
