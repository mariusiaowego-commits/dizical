"""Sync source to .cloudrun-deploy-new with smart exclude."""
import os, shutil

SRC = "/Users/mt16/dev/dizical"
DST = "/Users/mt16/dev/dizical/.cloudrun-deploy-new"

EXCLUDE_DIRS = {
    '.git', '.hermes', '.venv', 'venv', '__pycache__', 'data', 'docs', 'PRDs',
    'tests', 'scripts', '.pytest_cache', 'channels', 'comic', 'backups',
    '.alma-snapshots', 'logs', 'build', '.worktrees',
    'dizi_helper.egg-info', 'dizical.egg-info',
}
# 顶级 static/ 是 src/kid_app/static/ 的重复 (老的), runtime 走 src/ 那个
EXCLUDE_ROOT_DIRS = {'static', '.cloudrun-deploy', '.cloudrun-deploy-new'}
EXCLUDE_ROOT_FILES = {
    'vibe-coding-log.md', 'AGENTS.md', 'DEVELOPMENT_PLAN.md', '.tcbignore',
    'dizi.db', 'dizical.db', 'morning_check.json', 'crop_flutes.py',
    'download_and_rmbg.py', 'remove_bg.py', 'gsap-demo.html',
    'spike-deploy.sh', '.DS_Store', 'badges.html.bak',
}


def skip_dir(name, is_root=False):
    if is_root and name in EXCLUDE_ROOT_DIRS:
        return True
    return name in EXCLUDE_DIRS or name.endswith('.egg-info')


def skip_file(name, is_root=False):
    if is_root and name in EXCLUDE_ROOT_FILES:
        return True
    if name in EXCLUDE_ROOT_FILES:
        return True
    if name.startswith('handoff-') and name.endswith('.md'):
        return True
    if name.endswith(('.pyc', '.pyo', '.heic', '.heif', '.log', '.tmp', '.bak')):
        return True
    return False


# Clear dst
if os.path.exists(DST):
    for r, d, f in os.walk(DST, topdown=False):
        for x in f:
            try:
                os.remove(os.path.join(r, x))
            except OSError:
                pass
        for y in d:
            try:
                os.rmdir(os.path.join(r, y))
            except OSError:
                pass
os.makedirs(DST, exist_ok=True)

count = 0
total_bytes = 0
for root, dirs, files in os.walk(SRC):
    rel = os.path.relpath(root, SRC)
    is_root = (rel == '.')
    parts = rel.split(os.sep) if rel != '.' else []
    if any(skip_dir(p, is_root=False) for p in parts):
        dirs[:] = []
        continue
    # 第二层: 排除 顶级目录 (任何深度) (除 is_root=False 的 root/ 别名)
    for d in list(dirs):
        # 顶级目录 (root 下的) 才用 EXCLUDE_ROOT_DIRS
        if is_root and d in EXCLUDE_ROOT_DIRS:
            dirs.remove(d)
        elif d in EXCLUDE_DIRS:
            dirs.remove(d)
    for f in files:
        if skip_file(f, is_root=is_root):
            continue
        src = os.path.join(root, f)
        if os.path.islink(src):
            continue
        rel_file = os.path.relpath(src, SRC)
        dst = os.path.join(DST, rel_file)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
        total_bytes += os.path.getsize(dst)

print(f"copied {count} files, {total_bytes / (1024*1024):.1f} MB")
print(f"size on disk (incl dir overhead):")
os.system(f"du -sh {DST}")
