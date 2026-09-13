#!/usr/bin/env bash
# 冻结 CCG 卡 demo 快照 (dad 2026-09-12: demo 必须版本化 —— 以后改卡片样式 /
# 3D 模型(倾斜·翻转·微视差)样式时, 要知道自己现在是第几版, 并且能回看旧版)。
#
# 用法:
#   bash scripts/freeze-ccg-demo.sh v1.0.0 "首次定稿: 8 主题 + 金框贴卡 + 画面窗对齐"
#
# 产物:
#   src/kid_app/static/demo-archive/<版本>/
#     index.html                  冻结版 demo 页 (资源已改为相对路径, 不随线上改动而变)
#     badge-ccg.css               卡面样式快照 (patterns 路径已改相对)
#     badge-ccg-themes.css        8 套主题 token 快照
#     badge-ccg.js                3D 交互 (倾斜/翻转/视差/聚光灯) 快照
#     patterns/*.svg              主题暗纹
#     MANIFEST.txt                版本 / 日期 / commit / 各文件 md5 / 未随包资产
#   src/kid_app/static/demo-archive/VERSIONS.md   版本登记表 (追加一行)
#
# 打开:  http://<host>:8765/static/demo-archive/<版本>/index.html
# 版本号不允许覆盖 (重冻结请用新版本号)。
set -euo pipefail

VER="${1:?用法: bash scripts/freeze-ccg-demo.sh v1.0.0 \"变更说明\"}"
NOTE="${2:-（未填说明）}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/src/kid_app/static"
ARCH="$SRC/demo-archive"
DST="$ARCH/$VER"

if [ -e "$DST" ]; then
  echo "✗ $VER 已存在 —— 版本号不允许覆盖, 请换新版本号 (如 v1.0.1 / v1.1.0)"
  exit 1
fi
mkdir -p "$DST/patterns"

python3 - "$SRC" "$DST" "$VER" <<'PY'
import pathlib, re, shutil, sys
src, dst, ver = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]

def copy(rel, out, subs=()):
    s = (src / rel).read_text(encoding="utf-8")
    if out == "index.html":
        # 冻结页自报版本号 (页头 chip + JS 常量 + meta 都改写成本版本)
        s = re.sub(r'CCG_DEMO_VERSION = "[^"]*"', 'CCG_DEMO_VERSION = "%s"' % ver, s)
        s = re.sub(r'(<span id="ccg-demo-ver"[^>]*>)[^<]*', r'\g<1>' + ver, s)
        s = re.sub(r'(<meta name="ccg-demo-version" content=")[^"]*', r'\g<1>' + ver, s)
    for a, b in subs:
        s = s.replace(a, b)
    (dst / out).write_text(s, encoding="utf-8")

copy("badge-ccg-demo.html", "index.html", [
    ('href="/static/css/badge-ccg.css"', 'href="./badge-ccg.css"'),
    ('href="/static/css/badge-ccg-themes.css"', 'href="./badge-ccg-themes.css"'),
    ('src="/static/js/badge-ccg.js"', 'src="./badge-ccg.js"'),
])
pat = [('url("/static/img/ccg-patterns/', 'url("./patterns/')]
copy("css/badge-ccg.css", "badge-ccg.css", pat)
copy("css/badge-ccg-themes.css", "badge-ccg-themes.css", pat)
copy("js/badge-ccg.js", "badge-ccg.js")

pdir = src / "img" / "ccg-patterns"
for f in sorted(pdir.glob("*.svg")):
    shutil.copy2(f, dst / "patterns" / f.name)

# 报告仍在引用绝对路径的资产 (同源 8765 仍能加载, 但不受快照保护)
left = set()
for f in ("index.html", "badge-ccg.css", "badge-ccg-themes.css", "badge-ccg.js"):
    for line in (dst / f).read_text(encoding="utf-8").splitlines():
        if "/static/" in line or "http://" in line or "https://" in line:
            for tok in line.replace('"', " ").replace("'", " ").split():
                if tok.startswith(("http://", "https://")) or "/static/" in tok:
                    left.add(tok.strip(",);"))
(dst / "_foreign-assets.txt").write_text("\n".join(sorted(left)) + "\n", encoding="utf-8")
print(len(left))
PY

{
  echo "版本:     $VER"
  echo "冻结时间: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "冻结依据: $(cd "$ROOT" && git rev-parse --short HEAD) ($(cd "$ROOT" && git log -1 --format=%s | cut -c1-60))"
  echo "变更说明: $NOTE"
  echo "入口:     /static/demo-archive/$VER/index.html"
  echo
  echo "md5:"
  (cd "$DST" && for f in index.html badge-ccg.css badge-ccg-themes.css badge-ccg.js; do printf '  %s  %s\n' "$(md5 -q "$f")" "$f"; done)
  printf '  %s  patterns/  (%s 个 svg)\n' "$(cd "$DST" && cat patterns/*.svg | md5 -q)" "$(ls "$DST/patterns" | wc -l | tr -d ' ')"
  echo
  echo "未随包资产 (走线上绝对路径, 同源服务器可加载):"
  sed 's/^/  /' "$DST/_foreign-assets.txt"
} > "$DST/MANIFEST.txt"
rm -f "$DST/_foreign-assets.txt"

if [ ! -f "$ARCH/VERSIONS.md" ]; then
  cat > "$ARCH/VERSIONS.md" <<'HDR'
# CCG 卡 demo 版本登记表

> 每次卡片样式 / 3D 模型(倾斜·翻转·视差) / 主题 token 定稿后冻结一版:
> `bash scripts/freeze-ccg-demo.sh <版本号> "变更说明"`
> 旧版本永不覆盖; 打开 `http://<host>:8765/static/demo-archive/<版本号>/index.html` 可回看。
> 当前开发版 = 线上 `static/badge-ccg-demo.html` (页面右上角显示自己的版本号)。

| 版本 | 冻结日期 | 冻结 commit | 变更说明 | 入口 |
|---|---|---|---|---|
HDR
fi

COMMIT="$(cd "$ROOT" && git rev-parse --short HEAD)"
printf '| %s | %s | `%s` | %s | [打开](/static/demo-archive/%s/index.html) |\n' \
  "$VER" "$(date '+%Y-%m-%d')" "$COMMIT" "$NOTE" "$VER" >> "$ARCH/VERSIONS.md"

echo "✓ 已冻结 $VER → $DST"
echo "  MANIFEST: $DST/MANIFEST.txt"
echo "  登记表:   $ARCH/VERSIONS.md"
echo "  打开:     http://<host>:8765/static/demo-archive/$VER/index.html"
