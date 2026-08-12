"""
数据库备份模块
定期备份 SQLite 数据库到本地 data/backups/ 目录，
并同步冗余副本到 iCloud 目标路径。
"""

import datetime as dt
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


# 项目数据目录（指向项目根目录，data/ 是数据子目录）
_DATA_ROOT = Path(__file__).resolve().parent.parent
# 统一检查 data/ 子目录（main repo 和 worktree 共用此路径）
if not (_DATA_ROOT / "data" / "dizi.db").exists():
    # 兜底：指向 /Users/mt16/data（旧路径，保持兼容）
    _DATA_ROOT = Path("/Users/mt16/data")
DATA_DIR = _DATA_ROOT / "data" if (_DATA_ROOT / "data").exists() and _DATA_ROOT.name != "data" else _DATA_ROOT
BACKUP_DIR = DATA_DIR / "backups"
# iCloud 冗余备份路径 (2026-08-12 安全加固: 不再写死用户个人 iCloud 路径)
# 默认走项目本地 backups 目录; 要走 iCloud 在 ~/.dizical/.env 设 DIZICAL_ICLOUD_BACKUP_DIR=/your/path
ICLOUD_BACKUP_DIR = Path(os.environ.get(
    "DIZICAL_ICLOUD_BACKUP_DIR",
    str(DATA_DIR / "backups")
))
# 保留最近 N 个每日备份
KEEP_DAILY = 7


def _get_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def _backup_single_db(db_path: Path, backup_dir: Path, suffix: str = "daily") -> Path:
    """
    使用 shutil.copy2 复制单个数据库文件。
    返回备份文件路径。
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = db_path.stem  # e.g. "dizi" from "dizi.db"
    name = f"{stem}_{suffix}_{ts}.db"
    dest = backup_dir / name

    shutil.copy2(db_path, dest)
    return dest


def _verify_backup(backup_path: Path) -> Tuple[bool, str]:
    """
    验证备份文件可读且结构完整。
    返回 (success, message)。
    """
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        if tables:
            return True, f"✅ 验证通过，共 {len(tables)} 张表: {', '.join(tables)}"
        else:
            return False, "⚠️ 验证失败：数据库无表"
    except sqlite3.Error as e:
        return False, f"❌ 验证失败：{e}"


def _sync_to_icloud(backup_path: Path) -> Tuple[bool, str]:
    """
    将备份文件同步到 iCloud 冗余目录。
    返回 (success, message)。
    """
    try:
        ICLOUD_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        dest = ICLOUD_BACKUP_DIR / backup_path.name
        shutil.copy2(backup_path, dest)
        return True, f"✅ 已同步至 iCloud: {dest}"
    except Exception as e:
        return False, f"⚠️ iCloud 同步失败：{e}"


def backup_all(backup_dir: Optional[Path] = None) -> List[dict]:
    """
    备份所有数据库文件（dizi.db）。
    返回所有备份结果列表（每项含路径和验证/同步状态）。
    """
    backup_dir = backup_dir or _get_backup_dir()

    results: List[dict] = []
    for name in ("dizi.db",):
        p = DATA_DIR / name
        if p.exists() and p.stat().st_size > 0:
            bp = _backup_single_db(p, backup_dir)
            ok, msg = _verify_backup(bp)
            sync_ok, sync_msg = _sync_to_icloud(bp)
            results.append({
                "path": bp,
                "verified": ok,
                "verify_msg": msg,
                "icloud_synced": sync_ok,
                "icloud_msg": sync_msg,
            })

    # 清理旧备份
    _cleanup_old_backups(backup_dir)

    return results


def _cleanup_old_backups(backup_dir: Path) -> None:
    """
    清理过期的备份文件：保留最近 KEEP_DAILY 个。
    """
    if not backup_dir.exists():
        return

    # 按修改时间排序所有 .db 备份文件
    all_backups = sorted(backup_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)

    # 保留最近 KEEP_DAILY 个，其余删除
    for p in all_backups[KEEP_DAILY:]:
        p.unlink(missing_ok=True)


def list_backups(backup_dir: Optional[Path] = None) -> List[dict]:
    """列出所有备份文件信息"""
    backup_dir = backup_dir or _get_backup_dir()
    if not backup_dir.exists():
        return []

    results = []
    for p in sorted(backup_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = p.stat()
        results.append({
            "name": p.name,
            "path": str(p),
            "size_bytes": stat.st_size,
            "modified": dt.datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return results


def restore_from_backup(backup_path: Path, target_db_path: Path) -> None:
    """
    从备份文件恢复到目标数据库。
    注意：这会覆盖目标数据库文件。
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    shutil.copy2(backup_path, target_db_path)


# ── CLI 辅助 ────────────────────────────────────────────────────────────────


def backup_info() -> str:
    """返回备份状态摘要（供 CLI 显示）"""
    backups = list_backups()
    if not backups:
        return "暂无备份记录"

    total_size = sum(b["size_bytes"] for b in backups)
    lines = [
        f"备份目录: {BACKUP_DIR}",
        f"备份数量: {len(backups)} 个",
        f"总大小:   {total_size / 1024:.1f} KB",
        "",
        "最近 3 个备份:",
    ]
    for b in backups[:3]:
        mtime = dt.datetime.fromisoformat(b["modified"]).strftime("%m-%d %H:%M")
        size_kb = b["size_bytes"] / 1024
        lines.append(f"  {mtime}  {b['name']}  ({size_kb:.1f} KB)")
    return "\n".join(lines)
