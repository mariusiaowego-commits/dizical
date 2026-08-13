"""Replace .cloudrun-deploy with clean .cloudrun-deploy-new content.

- Removes old polluted .cloudrun-deploy (343M, contains dizi.db / backups / channels)
- Copies clean .cloudrun-deploy-new (162M, runtime-only) into place
- Safe: file-by-file, no rm -rf of project paths outside these two temp dirs
"""
import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OLD = str(PROJECT_ROOT / ".cloudrun-deploy")
NEW = str(PROJECT_ROOT / ".cloudrun-deploy-new")


def wipe_dir(path: str) -> None:
    """Delete everything inside path (the dir itself stays)."""
    if not os.path.exists(path):
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
            except OSError:
                pass
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))
            except OSError:
                pass


def copy_tree(src: str, dst: str) -> int:
    """Copy all files under src into dst. Returns file count."""
    count = 0
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        if rel == ".":
            rel = ""
        for f in files:
            s = os.path.join(root, f)
            d = os.path.join(dst, rel, f)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            count += 1
    return count


# 1. wipe old polluted dir
wipe_dir(OLD)
# 2. copy clean new content into it
n = copy_tree(NEW, OLD)
print(f"copied {n} files into .cloudrun-deploy")

# verify
size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OLD) for f in fs) / (1024 * 1024)
has_db = os.path.exists(os.path.join(OLD, "dizi.db"))
has_bak = os.path.exists(os.path.join(OLD, "backups"))
print(f"new .cloudrun-deploy size: {size:.0f}M, dizi.db={has_db}, backups={has_bak}")
