"""
迁移: 为 daily_practices 加 practice_sessions 事实表
────────────────────────────────────────────────────────────────────────────
背景 (2026-07-27):
- 现有 daily_practices.items 是按科目维度汇总的 JSON 数组, save_daily_practice
  合并逻辑是"同 item 累加 minutes", 跟需求"每次计时细分内容"天然冲突:
  西藏舞曲 5min + 3min 不同内容, 旧逻辑压成 1 条 8min, 看不出"5+3"
- 现有 behavior_log 是 audit 用, 不能当 session 真相用, 否则污染审计语义
- 6-22 MRD 已经描述过需求但没做, 7-27 dad 拍板只做"每次科目计时细分内容",
  6-22 剩余 3 块(一天 N 场/AI 摘要/加速模式) 推迟 V2

新表: practice_sessions
- id / practice_date / item_id / item_name 名称快照 / duration_minutes
- tempo_note (♪ / ♩) / tempo_bpm (40-150) / content / content_source
- is_extra / started_at (CST ISO 无 Z) / created_at

迁移策略:
- 旧 behavior_log 每条 entry 拆 1 条 session (tempo_note='♪', tempo_bpm=80, content='')
- content_source='legacy', 不猜内容
- 缺 item_id 时按 item 名查 practice_items, 查不到 skip + WARN
- 幂等: 先 PRAGMA table_info 检查表存在, 存在则 return

红线 (dad 7-17):
- 迁移前生成 SQLite 备份 (data/backups/dizi_pre_session_<ts>.db)
- 本地 SQLite 永不删
"""
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


# ── 路径 ─────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_DB_PATH = _DATA_DIR / "dizi.db"
_BACKUP_DIR = _DATA_DIR / "backups"


# ── SQL ─────────────────────────────────────────────────────────────────
# 注意: 整张表 schema, 跟 PRD §5 + plan 阶段 1.1 一致
_CREATE_SESSIONS_TABLE = """
CREATE TABLE practice_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    practice_date DATE NOT NULL,
    item_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    tempo_note TEXT NOT NULL DEFAULT '♪',
    tempo_bpm INTEGER NOT NULL DEFAULT 80,
    content TEXT NOT NULL DEFAULT '',
    content_source TEXT NOT NULL DEFAULT 'manual',
    is_extra BOOLEAN NOT NULL DEFAULT 0,
    started_at TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES practice_items(item_id)
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_practice_sessions_date ON practice_sessions(practice_date);",
    "CREATE INDEX IF NOT EXISTS idx_practice_sessions_item_date ON practice_sessions(item_id, practice_date);",
]


# ── 备份 ────────────────────────────────────────────────────────────────
def _make_backup() -> Path:
    """复制 db 到 backups/ 目录, 命名 dizi_pre_session_<ts>.db
    失败直接 raise, 不写主 db.
    """
    if not _DB_PATH.exists():
        raise FileNotFoundError(f"DB 不存在: {_DB_PATH}")
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = _BACKUP_DIR / f"dizi_pre_session_{ts}.db"
    shutil.copy2(_DB_PATH, backup_path)
    # 验证备份可读
    conn = sqlite3.connect(str(backup_path))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    if not tables:
        raise RuntimeError(f"备份文件无表结构: {backup_path}")
    return backup_path


# ── 校验 CST ISO 格式 ───────────────────────────────────────────────────
_CST_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$"
)


def _normalize_started_at(raw: str | None) -> str | None:
    """校验 enter_time 是 CST ISO 格式 (无 Z 后缀).
    - 合法 → 原样返回
    - 不合法 → None
    - None → None
    """
    if not raw:
        return None
    if not isinstance(raw, str):
        return None
    if _CST_ISO_RE.match(raw):
        return raw
    # 不合法: 兼容 7-13 之前的 UTC ISO 格式 (带 Z) → 转 CST 无 Z
    # 2026-06-13 fix 之前是 JS new Date().toISOString() 出来的, 形如 2026-07-01T18:30:00.000Z
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.\d+)?Z$", raw)
    if m:
        return f"{m.group(1)} {m.group(2)}{m.group(3) or ''}"
    return None


# ── 主体迁移 ────────────────────────────────────────────────────────────
def _migrate() -> dict:
    """返回迁移统计 dict."""
    stats = {
        "already_exists": False,
        "backup_path": None,
        "behavior_log_rows_scanned": 0,
        "sessions_inserted": 0,
        "skipped_no_item": 0,
        "skipped_invalid_time": 0,
        "errors": [],
    }

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. 幂等检查: 表已存在直接 return
    cur.execute("PRAGMA table_info(practice_sessions)")
    if cur.fetchone() is not None:
        cur.close()
        conn.close()
        stats["already_exists"] = True
        return stats

    # 2. 备份
    backup_path = _make_backup()
    stats["backup_path"] = str(backup_path)

    # 3. 建表 + 索引
    cur.execute(_CREATE_SESSIONS_TABLE)
    for sql in _CREATE_INDEXES:
        cur.execute(sql)

    # 4. 预读 item 名称 → item_id 映射 (处理缺 item_id 的 entry)
    name_to_id: dict[str, int] = {}
    for row in cur.execute("SELECT item_id, name FROM practice_items").fetchall():
        name_to_id[row["name"]] = row["item_id"]

    # 5. 扫 daily_practices 拆 behavior_log → session
    rows = cur.execute(
        "SELECT id, date, behavior_log FROM daily_practices WHERE behavior_log IS NOT NULL"
    ).fetchall()

    insert_count = 0
    for row in rows:
        date_str = row["date"]
        log_json = row["behavior_log"]
        stats["behavior_log_rows_scanned"] += 1
        if not log_json or log_json == "[]":
            continue
        try:
            entries = json.loads(log_json)
        except (json.JSONDecodeError, TypeError) as e:
            stats["errors"].append(f"daily_practices.id={row['id']}: behavior_log 不是合法 JSON: {e}")
            continue
        if not isinstance(entries, list):
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            item_name = entry.get("item")
            if not item_name:
                continue
            minutes = entry.get("minutes")
            if not isinstance(minutes, (int, float)) or minutes <= 0:
                continue

            # 解析 item_id: 优先 entry 自带, 否则按名查
            item_id = entry.get("item_id")
            if not item_id:
                item_id = name_to_id.get(item_name)
            if not item_id:
                stats["skipped_no_item"] += 1
                continue

            # started_at: enter_time, 不合法置 NULL
            started_at = _normalize_started_at(entry.get("enter_time"))
            if entry.get("enter_time") and not started_at:
                stats["skipped_invalid_time"] += 1

            cur.execute(
                """INSERT INTO practice_sessions
                   (practice_date, item_id, item_name, duration_minutes,
                    tempo_note, tempo_bpm, content, content_source,
                    is_extra, started_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    date_str,
                    int(item_id),
                    item_name,
                    int(minutes),
                    "♪",
                    80,
                    "",
                    "legacy",
                    1 if entry.get("is_extra") else 0,
                    started_at,
                ),
            )
            insert_count += 1

    conn.commit()

    # 6. 写 schema_migrations 标记
    # 用 version=999 避免跟历史 migration (version=1 from database.py:180) 撞号.
    # 这里只做幂等防重跑标记, 跟 schema 版本号解耦.
    cur.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (999,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            (999,),
        )
        conn.commit()

    stats["sessions_inserted"] = insert_count
    cur.close()
    conn.close()
    return stats


def main():
    print("=== migrate_add_practice_sessions ===")
    if not _DB_PATH.exists():
        print(f"❌ DB 不存在: {_DB_PATH}")
        sys.exit(1)

    stats = _migrate()

    if stats["already_exists"]:
        print("✓ practice_sessions 表已存在, 无需迁移 (幂等)")
        return

    print(f"✓ 备份: {stats['backup_path']}")
    print(f"✓ 扫 daily_practices 行: {stats['behavior_log_rows_scanned']}")
    print(f"✓ 插入 sessions: {stats['sessions_inserted']}")
    print(f"  - skip (无 item_id/name): {stats['skipped_no_item']}")
    print(f"  - skip (enter_time 格式无效): {stats['skipped_invalid_time']}")
    if stats["errors"]:
        print("⚠️ 错误:")
        for e in stats["errors"]:
            print(f"  - {e}")

    # 二次运行验证幂等
    print()
    print("=== 二次运行验证幂等 ===")
    stats2 = _migrate()
    assert stats2["already_exists"], "二次运行应判 already_exists"
    print("✓ 幂等通过: 二次运行未重复生成 session")


if __name__ == "__main__":
    main()
