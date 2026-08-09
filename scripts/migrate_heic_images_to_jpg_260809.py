#!/usr/bin/env python3
"""历史配图 HEIC → JPG 修复 (2026-08-09 需求6, dad 拍板 Q2=A).

背景: 8-08 上传的 2 张配图以 .heic 存 COS (当时 CloudRun Linux 无 sips 转换失败),
Chrome 无法预览. 修复: 本地 macOS sips 转 jpg → COS 重传 → 更新 weekly_assignments.images.
以后上传端已拦截 heic (见 config.py _ALLOWED_EXTS), 此脚本为一次性历史修复.

用法: source ~/.dizical/.env && .venv/bin/python scripts/migrate_heic_images_to_jpg_260809.py
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.kid_app.cos_client import cos_uploader  # noqa: E402


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def _heic_to_jpeg(src_path: Path, jpg_path: Path) -> bool:
    sips = shutil.which("sips")
    if not sips:
        return False
    try:
        subprocess.run(
            [sips, "-s", "format", "jpeg", str(src_path), "--out", str(jpg_path)],
            check=True, capture_output=True, timeout=90,
        )
        return jpg_path.exists() and jpg_path.stat().st_size > 0
    except Exception:
        return False


def _build_database_url() -> str:
    """优先 DATABASE_URL, 否则 MYSQL_* 拼装 (跟 start-prod.sh 逻辑一致)."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if all(os.environ.get(k) for k in ("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")):
        from urllib.parse import quote
        return (
            f"mysql+pymysql://{os.environ['MYSQL_USER']}:{quote(os.environ['MYSQL_PASSWORD'])}"
            f"@{os.environ['MYSQL_HOST']}:{os.environ['MYSQL_PORT']}/{os.environ['MYSQL_DATABASE']}"
        )
    return ""


def main() -> None:
    if not cos_uploader.is_available:
        print("FATAL: COS 未配置 (COS_BUCKET/SECRET_ID/SECRET_KEY 缺失)")
        sys.exit(1)
    database_url = _build_database_url()
    if not database_url:
        print("FATAL: DATABASE_URL / MYSQL_* 均未设置 (先 source ~/.dizical/.env)")
        sys.exit(1)

    # 1. 查所有带配图的记录
    import pymysql
    from src.database_mysql import MySQLBackend
    db = MySQLBackend(database_url)
    conn = db._get_connection()
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(
            "SELECT lesson_date, images FROM weekly_assignments "
            "WHERE images IS NOT NULL AND images != '[]' AND images != ''"
        )
        rows = cur.fetchall()

    tmpdir = Path("/tmp/heic_migrate_260809")
    tmpdir.mkdir(parents=True, exist_ok=True)

    changed = 0
    for row in rows:
        lesson_date = row["lesson_date"]
        images = json.loads(row["images"]) if isinstance(row["images"], str) else row["images"]
        new_images = []
        need_update = False
        for url in images:
            if ".heic" in url.lower() or ".heif" in url.lower():
                fname = url.split("/")[-1]
                src = tmpdir / fname
                jpg_name = fname.rsplit(".", 1)[0] + ".jpg"
                jpg_path = tmpdir / jpg_name
                src.write_bytes(_download(url))
                if not _heic_to_jpeg(src, jpg_path):
                    print(f"  [FAIL] {fname} 转换失败, 保留原 URL")
                    new_images.append(url)
                    continue
                new_url = cos_uploader.upload(jpg_name, jpg_path.read_bytes(), "image/jpeg")
                new_images.append(new_url)
                need_update = True
                changed += 1
                print(f"  [OK] {lesson_date} {fname} -> {new_url}")
            else:
                new_images.append(url)
        if need_update:
            with conn.cursor(pymysql.cursors.DictCursor) as cur2:
                cur2.execute(
                    "UPDATE weekly_assignments SET images = %s WHERE lesson_date = %s",
                    (json.dumps(new_images, ensure_ascii=False), lesson_date),
                )
            conn.commit()
            print(f"  [UPDATE] {lesson_date} images 已更新")

    print(f"完成: 转换 {changed} 张 heic -> jpg")


if __name__ == "__main__":
    main()
