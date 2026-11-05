"""Sync source to .cloudrun-deploy-new with smart exclude."""
import os, shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = str(PROJECT_ROOT)
DST = str(PROJECT_ROOT / ".cloudrun-deploy-new")

EXCLUDE_DIRS = {
    '.git', '.hermes', '.venv', 'venv', '__pycache__', 'data', 'docs', 'PRDs',
    'tests', 'scripts', '.pytest_cache', 'channels', 'comic', 'backups',
    '.alma-snapshots', 'logs', 'build', '.worktrees',
    # Sprint 26083001 S5: deepseek audit P0 修复 — 排除下划线开头 _worktrees (之前漏掉, 1.1GB 跟着 deploy 包进 CloudRun 必 create_failed)
    '_worktrees',
    'dizi_helper.egg-info', 'dizical.egg-info',
    # 2026-11-03 practice-dsh 部署: 以下三个目录会让 deploy 包从 196M 涨到 710M,
    # tcb 上传 ZIP 必 create_failed (同 _worktrees 事故):
    #   .local-archive 498M 本地归档 / dizical-ai 37M 生成物 / sprints 632K 过程文档
    '.local-archive', 'dizical-ai', 'sprints',
}
# 顶级 static/ 是 src/kid_app/static/ 的重复 (老的), runtime 走 src/ 那个
EXCLUDE_ROOT_DIRS = {'static', '.cloudrun-deploy', '.cloudrun-deploy-new'}
EXCLUDE_ROOT_FILES = {
    'STATUS.md', 'vibe-coding-log.md', 'AGENTS.md', 'DEVELOPMENT_PLAN.md', '.tcbignore',
    'dizi.db', 'dizical.db', 'morning_check.json', 'crop_flutes.py',
    'download_and_rmbg.py', 'remove_bg.py', 'gsap-demo.html',
    'spike-deploy.sh', '.DS_Store', 'badges.html.bak', 'result.md',
}
# .tcbignore 是 tcb 上传时的排除清单, 必须随包一起进 .cloudrun-deploy,
# 否则部署包会带上 700M+ 非运行时文件 (排除在 EXCLUDE_ROOT_FILES 之外)。
EXCLUDE_ROOT_FILES.discard('.tcbignore')


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


def write_build_info():
    """镜像里没有 .git，构建信息只能在打包时落盘成静态 JSON。"""
    import datetime
    import json
    import subprocess

    def git(*args):
        try:
            out = subprocess.run(
                ["git", "-C", SRC, *args],
                capture_output=True, text=True, check=False,
            )
            return out.stdout.strip()
        except Exception:
            return ""

    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    commit = git("rev-parse", "--short", "HEAD") or "unknown"
    top = git("rev-parse", "--show-toplevel")
    source = "main checkout"
    if top and os.path.realpath(top) != os.path.realpath(SRC):
        source = "worktree:" + os.path.basename(top)
    # 只看已跟踪文件的改动：打包目录 .cloudrun-deploy-new 本身就是产物，
    # 用默认的 untracked 统计会让 dirty 永远是 true。
    dirty = "1" if git("status", "--porcelain", "--untracked-files=no") else "0"
    version = "unknown"
    tpl = os.path.join(SRC, "src/kid_app/templates/practice-dsh.html")
    try:
        import re
        with open(tpl, encoding="utf-8") as fh:
            m = re.search(r"var DSH_VERSION = '([^']+)'", fh.read())
        if m:
            version = m.group(1)
    except OSError:
        pass

    info = {
        "version": version,
        "branch": branch,
        "commit": commit,
        "source": source,
        "dirty": dirty == "1",
        "built_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    dst = os.path.join(DST, "src/kid_app/static/build-info.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=2)
    print("build-info:", json.dumps(info, ensure_ascii=False))


write_build_info()
print(f"size on disk (incl dir overhead):")
os.system(f"du -sh {DST}")
