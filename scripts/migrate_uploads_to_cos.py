"""把历史 /uploads/raw/ 引用迁移到 COS (PR-F).

扫 weekly_assignments.images 里的 /uploads/raw/ URL:
- 本地 data/uploads/raw/<fname> 文件存在 → 上传 COS → 更新 DB images URL
- 文件不存在 (容器重启已丢) → 从 images 移除该 URL (降级, 不阻塞)

用法:
    source ~/.dizical/.env   # MYSQL_* + COS_* 凭据
    uv run python scripts/migrate_uploads_to_cos.py

幂等: 已迁移的 COS URL 自动跳过.
"""
import json
import os
import re
import sys
from pathlib import Path

# 项目根 (脚本在 scripts/ 下)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_UPLOAD_RAW = ROOT / "data" / "uploads" / "raw"
_UPLOAD_RE = re.compile(r"/uploads/raw/([0-9a-f]{32}\.[a-z]+)")


def _load_mysql_cfg():
    """从环境变量构造 MySQL 连接 (与 dynamic_sync.py 一致)."""
    import pymysql
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "sh-cynosdbmysql-grp-3nsxknle.sql.tencentcdb.com"),
        port=int(os.getenv("MYSQL_PORT", "22209")),
        user=os.getenv("MYSQL_USER", "dizical"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "cloud1-d4gfwyvsk1435e2e4"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _get_cos_uploader():
    """构造 CosUploader (复用生产代码)."""
    sys.path.insert(0, str(ROOT))
    from src.kid_app.cos_client import CosUploader
    u = CosUploader()
    if not u.is_available:
        print("⚠️  COS 未配置 (需 COS_BUCKET/COS_SECRET_ID/COS_SECRET_KEY), 无法迁移")
        sys.exit(1)
    return u


def main():
    conn = _load_mysql_cfg()
    uploader = _get_cos_uploader()

    with conn.cursor() as cur:
        cur.execute("SELECT id, images FROM weekly_assignments WHERE images LIKE '%/uploads/raw/%'")
        rows = cur.fetchall()

    if not rows:
        print("✅ 没有 /uploads/raw/ 引用需要迁移")
        return

    print(f"找到 {len(rows)} 条引用 /uploads/raw/ 的记录")
    migrated, missing, failed = 0, 0, 0

    for row in rows:
        wa_id = row["id"]
        images = json.loads(row["images"]) if row["images"] else []
        changed = False

        for i, img in enumerate(images):
            url = img if isinstance(img, str) else img.get("url", "")
            m = _UPLOAD_RE.search(url)
            if not m:
                continue
            fname = m.group(1)
            local_file = _UPLOAD_RAW / fname

            if local_file.exists():
                try:
                    ctype = "image/png" if fname.endswith(".png") else "image/jpeg"
                    cos_url = uploader.upload(fname, local_file.read_bytes(), ctype)
                    if isinstance(img, str):
                        images[i] = cos_url
                    else:
                        img["url"] = cos_url
                    migrated += 1
                    print(f"  ✅ wa#{wa_id} {fname} → COS")
                except Exception as e:
                    failed += 1
                    print(f"  ❌ wa#{wa_id} {fname} 上传失败: {e}")
            else:
                # 容器重启已丢 → 移除该 URL
                missing += 1
                print(f"  ⚠️  wa#{wa_id} {fname} 本地文件不存在, 移除引用")
                if isinstance(img, str):
                    images.pop(i)
                else:
                    images[i] = None
            changed = True

        if changed:
            new_images = [x for x in images if x is not None]
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE weekly_assignments SET images = %s WHERE id = %s",
                    (json.dumps(new_images, ensure_ascii=False), wa_id),
                )
            conn.commit()

    print(f"\n汇总: 迁移 {migrated}, 文件缺失移除 {missing}, 失败 {failed}")
    conn.close()


if __name__ == "__main__":
    main()
