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

        # image 路径
        image_url = None
        if draft.image.get("path"):
            image_url = draft.image["path"]
            # 转 web 路径: /Users/mt16/.../static/badges/xxx.png → /static/badges/xxx.png
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
