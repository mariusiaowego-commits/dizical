#!/usr/bin/env python3
"""对「背景从未去掉」的 badge 图跑 rembg 去背 + 过出图闸门。

背景故事 (2026-10-01 事故):
  生产 `static/badges/` 里有 4 张 1024×1024 的图 alpha 唯一值 = 1 (整张完全不透明),
  四角像素 RGB 232~250 —— 说明去背管线**从来没在它们身上跑过**, 前端会显示成白/灰方框.
  (同类破损的另一半是 `uniq_alpha == 2` 的硬二值掩膜, 由 scripts/repair_badge_alpha.py 处理.)

本脚本只做 one thing: 对这些图跑 rembg (u2net), 然后过与 badge-image skill V2.8 一致的闸门:
  uniq_alpha > 2 且 轮廓内破洞 < 1.0% (回填区单色时需 < 0.5%)
闸门不过 = 不写盘, 让调用方决定重生图.

安全性:
  - 默认 dry-run; `--apply` 才写, 且写前把原图备份到 backups/2026-10-01-badge-alpha/
  - 只处理 `uniq_alpha == 1` 的图; 已经是软边的不碰
  - 不生成也不删任何文件, 不改路径 (前端引用零影响)

证据 (为什么这不等于「重生图」):
  `badges_backup_white_bg/<name>.png` (去背前的白底原图) 与现图在所有不透明像素上
  RGB 逐字节一致 (100%, 2026-10-01 实测 5/5 张) → 同一版画面, 只是背景没割.
  所以本脚本产出的是**原画复原**, 无画风漂移.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from io import BytesIO

import numpy as np
from PIL import Image
from scipy import ndimage

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BADGE_DIR = os.path.join(REPO_ROOT, "src", "kid_app", "static", "badges")
BACKUP_DIR = os.path.join(REPO_ROOT, "backups", "2026-10-01-badge-alpha")


def metrics(arr: np.ndarray) -> dict:
    al = arr[:, :, 3]
    sil = ndimage.binary_fill_holes(al > 0)
    holes = sil & (al == 0)
    interior_pct = float(holes.sum()) / max(int(sil.sum()), 1) * 100.0
    flat = False
    if holes.any():
        rgb = arr[:, :, :3][holes]
        flat = len(np.unique(rgb.reshape(-1, 3), axis=0)) == 1
    return {
        "uniq_alpha": int(len(np.unique(al))),
        "interior_pct": round(interior_pct, 2),
        "flat": bool(flat),
    }


def gate(m: dict) -> tuple[bool, str]:
    if m["uniq_alpha"] <= 2:
        return False, f"仍是硬二值掩膜 (uniq_alpha={m['uniq_alpha']})"
    if m["interior_pct"] >= 1.0:
        return False, f"轮廓内破洞 {m['interior_pct']}% >= 1.0%"
    if m["flat"] and m["interior_pct"] >= 0.5:
        return False, f"回填区单色且破洞 {m['interior_pct']}% >= 0.5%"
    return True, "OK"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*", help="图名 (不含 .png); 留空 = 扫全目录里 uniq_alpha==1 的图")
    ap.add_argument("--apply", action="store_true", help="真写 (写前备份到 backups/2026-10-01-badge-alpha/)")
    args = ap.parse_args()

    try:
        from rembg import remove
    except Exception as exc:  # noqa: BLE001
        print(f"rembg 不可用: {exc!r} -> 先 `pip install 'rembg[cpu]'`", file=sys.stderr)
        return 2

    if args.names:
        cand = [os.path.join(BADGE_DIR, n + ".png") for n in args.names]
    else:
        cand = sorted(os.path.join(BADGE_DIR, f) for f in os.listdir(BADGE_DIR) if f.endswith(".png"))

    todo = []
    for p in cand:
        if not os.path.exists(p):
            print(f"[skip] 不存在: {p}")
            continue
        arr = np.asarray(Image.open(p).convert("RGBA"))
        m = metrics(arr)
        if m["uniq_alpha"] != 1:
            print(f"[skip] {os.path.basename(p):30s} 已是软边 (uniq_alpha={m['uniq_alpha']})")
            continue
        todo.append((p, m))

    if not todo:
        print("没有需要处理的图 (全部已去背).")
        return 0

    print(f"\n待去背 {len(todo)} 张 (uniq_alpha == 1 = 背景从未割过):")
    written = raised = 0
    for p, m0 in todo:
        name = os.path.basename(p)
        raw = open(p, "rb").read()
        out = remove(raw)  # 真跑 rembg (u2net)
        new = np.asarray(Image.open(BytesIO(out)).convert("RGBA"))
        m1 = metrics(new)
        ok, why = gate(m1)
        line = (f"  {name:30s} 前 uniq={m0['uniq_alpha']:3d} 破洞={m0['interior_pct']:6.2f}%"
                f"  →  后 uniq={m1['uniq_alpha']:3d} 破洞={m1['interior_pct']:6.2f}% 单色={m1['flat']}  闸门={'PASS' if ok else 'RAISE'} ({why})")
        if not ok:
            raised += 1
            print(line)
            continue
        if args.apply:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            shutil.copy2(p, os.path.join(BACKUP_DIR, name))
            Image.fromarray(new, "RGBA").save(p, optimize=True)
            written += 1
            print(line + "  [已写回]")
        else:
            print(line + "  [dry-run]")

    print(f"\n合计: 待处理 {len(todo)} | 闸门拦下 {raised} | 写回 {written}"
          + ("" if args.apply else " (dry-run, 加 --apply 才写)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
