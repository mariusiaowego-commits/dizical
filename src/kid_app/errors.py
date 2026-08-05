"""
Sprint 09 P0-12 (PR-D): 自定义异常

跨端写入冲突时 (web + mac app 同时改同 session), 旧版本不能覆盖新版本.
业务层抛 ConflictError, 路由层转 409.
"""
from typing import Optional, Any, Dict


class ConflictError(Exception):
    """乐观锁冲突 (HTTP 409). 携带当前版本供前端刷新."""

    def __init__(
        self,
        message: str,
        *,
        current_state: Optional[Dict[str, Any]] = None,
        current_version: Optional[int] = None,
    ):
        super().__init__(message)
        self.current_state = current_state
        self.current_version = current_version


class NotFoundError(Exception):
    """资源不存在 (HTTP 404)."""


class MaintenanceBlockedError(Exception):
    """Sprint 08 MAINTENANCE_MODE 拦截写操作 (HTTP 503)."""