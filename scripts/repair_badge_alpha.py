"""badge alpha 破损批量复原 (A2) — 修复去背留下的「轮廓内破洞 + 硬二值边缘」

背景 (sprint 26100102):
  去背管线在 PIL 阈值分支出货时, alpha 只有 0/255 (无抗锯齿), 且轮廓内被割出大量小碎洞
  (recovery_first_practice_14_v1.png: 33047px = 画面 5.16%, 3052 个碎块)。
  PIL 阈值只写 `pixels[x,y] = (r, g, b, 0)` —— RGB 保留, 所以把 alpha 填回去即可复原画面。

做两件事:
  1. 轮廓内 alpha==0 的**小**连通块回填为不透明 (只在轮廓内, 不碰外部背景)
  2. 仅对**硬二值**图 (uniq_alpha == 2) 做 1px alpha 羽化, 消掉阶梯锯齿
     — 软边图 (uniq_alpha > 2, 例如 assign_pal_v2.png) 一律不动, 保证好图 0 变化

幂等: 跑两次结果一致 (第二次 0 改动 → 输出 md5 不变)。
安全: --apply 前先把原图复制到备份目录; 默认 dry-run 只报告。

用法:
  python3 scripts/repair_badge_alpha.py                    # dry-run, 全量报告
  python3 scripts/repair_badge_alpha.py --only assign_pal_v2  # 单张 (不含扩展名)
  python3 scripts/repair_badge_alpha.py --apply            # 真写 (先备份)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import shutil
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

BADGE_DIR = os.path.join("src", "kid_app", "static", "badges")
BACKUP_DIR = os.path.join("backups", "2026-10-01-badge-alpha")


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metrics(arr: np.ndarray) -> dict:
    """alpha 指标: uniq_alpha / partial% / 轮廓内破洞 px + 块数"""
    al = arr[:, :, 3]
    sil = ndimage.binary_fill_holes(al > 0)
    interior = sil & (al == 0)
    _, comps = ndimage.label(interior)
    return {
        "uniq_alpha": int(len(np.unique(al))),
        "partial_pct": round(float(((al > 0) & (al < 255)).mean()) * 100, 2),
        "interior_px": int(interior.sum()),
        "interior_pct": round(100.0 * float(interior.sum()) / max(1, int(sil.sum())), 2),
        "interior_comps": int(comps),
    }


def fill_interior_holes(arr: np.ndarray, max_hole: int, allow_flat: bool = False) -> tuple[np.ndarray, int, bool]:
    """轮廓内破洞回填 alpha=255 (max_hole<=0 = 不限大小)。

    返回 (新数组, 回填像素数, 回填区 RGB 是否单色)。
    **单色 = 画面内容被写回常量 (已毁), 调用方必须放弃回填并转 A3 重生图** ——
    证据 (2026-10-01):
      - `recovery_first_practice_14_v1.png` 被割 33047px 全为 (232,232,232) 单色,
        而同坐标在 `recovery_first_practice_7_v1.png` 里有 23648 种颜色 (真画面)
      - `early_bird_A.png` / `streak_7_v2.png` 全为 (0,0,0) 单色
    反例 (可安全回填): `grade_7-l.png` 被割 147357px 有 16152 种颜色 (mean 243,236,232),
    `streak_1.png` 765 种颜色 → 是 245 阈值割掉的近白画面像素, RGB 原样保留, 回填即复原。
    """
    al = arr[:, :, 3].copy()
    sil = ndimage.binary_fill_holes(al > 0)
    holes = sil & (al == 0)
    if not holes.any():
        return arr, 0, False

    if max_hole <= 0:
        fill = holes
    else:
        lbl, n = ndimage.label(holes)
        if n == 0:
            return arr, 0, False
        sizes = ndimage.sum(np.ones_like(lbl), lbl, index=range(1, n + 1))
        keep = [i + 1 for i in range(n) if sizes[i] <= max_hole]
        if not keep:
            return arr, 0, False
        fill = np.isin(lbl, keep)

    rgb = arr[:, :, :3][fill]
    uniq = np.unique(rgb.reshape(-1, 3), axis=0) if len(rgb) else []
    if len(uniq) == 1 and not allow_flat:
        # 单色 → 内容已毁, 回填只会画出灰/黑斑, 交给 A3 重生图
        return arr, 0, True

    out = arr.copy()
    out[:, :, 3] = np.where(fill, 255, al)
    return out, int(fill.sum()), False


def feather_binary_alpha(arr: np.ndarray, sigma: float = 1.0) -> tuple[np.ndarray, int]:
    """只对硬二值 alpha 做羽化: 在掩膜边缘 1-2px 带内用高斯权重替换 alpha。

    软边图原样返回 (0 改动)。
    """
    al = arr[:, :, 3]
    if len(np.unique(al)) != 2:
        return arr, 0

    mask = al > 127
    if not mask.any():
        return arr, 0

    soft = ndimage.gaussian_filter(mask.astype(np.float32), sigma=sigma) * 255.0
    band = ndimage.binary_dilation(mask, iterations=2) != ndimage.binary_erosion(mask, iterations=2)
    band &= mask | ndimage.binary_dilation(mask, iterations=2)

    new_al = al.astype(np.float32)
    new_al = np.where(band, soft, new_al)
    new_al = np.clip(new_al, 0, 255).astype(np.uint8)

    changed = int((new_al != al).sum())
    out = arr.copy()
    out[:, :, 3] = new_al
    return out, changed


def process(path: str, args) -> dict:
    name = os.path.basename(path)
    before = np.array(Image.open(path).convert("RGBA"))
    m0 = metrics(before)

    # 只处理「硬二值掩膜」—— 软边图 (uniq_alpha > 2, 例如 assign_pal_v2.png 256 级) 是 rembg
    # 正常输出, 一律不动, 保证好图 0 变化 (test-plan T12)。
    if m0["uniq_alpha"] != 2:
        return {
            "file": name,
            "uniq_a": f"{m0['uniq_alpha']}->(skip)",
            "holes%": f"{m0['interior_pct']}->(skip)",
            "holes_px": f"{m0['interior_px']}->(skip)",
            "comps": f"{m0['interior_comps']}->(skip)",
            "filled_px": 0,
            "feathered_px": 0,
            "filled_flat_rgb": False,
            "wrote": False,
            "soft_skip": True,
            "a3": m0["interior_pct"] >= args.a3_threshold,
        }

    arr, filled_px, flat = fill_interior_holes(before, args.max_hole, args.allow_flat_fill)
    arr, feathered_px = feather_binary_alpha(arr, args.feather)
    m1 = metrics(arr)

    wrote = False
    if args.apply and (filled_px or feathered_px):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        shutil.copy2(path, os.path.join(BACKUP_DIR, name))
        Image.fromarray(arr, mode="RGBA").save(path, optimize=True)
        wrote = True

    return {
        "file": name,
        "uniq_a": f"{m0['uniq_alpha']}->{m1['uniq_alpha']}",
        "holes%": f"{m0['interior_pct']}->{m1['interior_pct']}",
        "holes_px": f"{m0['interior_px']}->{m1['interior_px']}",
        "comps": f"{m0['interior_comps']}->{m1['interior_comps']}",
        "filled_px": filled_px,
        "feathered_px": feathered_px,
        "filled_flat_rgb": flat,
        "wrote": wrote,
        "soft_skip": False,
        # 单色破洞 (内容已毁) 或修完仍剩大破洞 → A3 重生图
        "a3": bool(flat) or m1["interior_pct"] >= args.a3_threshold,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真写 (先备份到 backups/2026-10-01-badge-alpha/)")
    ap.add_argument("--max-hole", type=int, default=0, help="轮廓内回填的最大连通块像素 (默认 0 = 不限大小; 单色破洞永远不回填)")
    ap.add_argument("--allow-flat-fill", action="store_true",
                    help="允许回填「单色」破洞。**只在白底原图备份证明该区域原本就是同色时才用** —— "
                         "证据链: badges_backup_white_bg/<name>.png 在破洞坐标上 RGB 与现图逐字节一致 (100%% 对齐). "
                         "实例: all_items.png 破洞 10445px 恒为 (255,255,255), 备份同坐标也是 (255,255,255) → 回填即真复原.")
    ap.add_argument("--feather", type=float, default=1.0, help="硬二值图的 alpha 羽化 sigma (默认 1.0)")
    ap.add_argument("--only", default="", help="只处理文件名含该子串的图 (不含 .png)")
    ap.add_argument("--dir", default=BADGE_DIR, help="要处理的目录 (默认 src/kid_app/static/badges; 可用于对 backups/ 里的原图重跑)")
    ap.add_argument("--a3-threshold", type=float, default=1.0, help="修完仍剩多少 %% 轮廓内破洞就转 A3 重生图 (默认 1.0)")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.dir, "*.png")))
    if args.only:
        paths = [p for p in paths if args.only in os.path.basename(p)]
    if not paths:
        print("没有匹配的图", file=sys.stderr)
        return 1

    rows, skipped = [], []
    for p in paths:
        try:
            rows.append(process(p, args))
        except Exception as exc:  # 坏文件不中断批次
            skipped.append((os.path.basename(p), str(exc)))

    rows.sort(key=lambda r: -int(r["filled_px"]))
    print(f"{'file':48s} {'uniqA':>10s} {'holes%':>16s} {'holes_px':>22s} {'comps':>14s} {'filled':>8s} {'feather':>8s} flat")
    for r in rows:
        print(
            f"{r['file']:48s} {r['uniq_a']:>10s} {r['holes%']:>16s} {r['holes_px']:>22s} "
            f"{r['comps']:>14s} {r['filled_px']:8d} {r['feathered_px']:8d} {r['filled_flat_rgb']}"
        )

    touched = [r for r in rows if r["filled_px"] or r["feathered_px"]]
    soft = [r for r in rows if r.get("soft_skip")]
    a3 = [r for r in rows if r.get("a3")]
    print()
    print(f"总数 {len(rows)} | 需要处理 {len(touched)} | 软边跳过 {len(soft)} | A3 重生图候选 {len(a3)} | 坏文件 {len(skipped)}")
    for name, err in skipped:
        print(f"  坏文件: {name} — {err}")
    if args.apply:
        print(f"已写回 {len([r for r in rows if r['wrote']])} 张, 备份在 {BACKUP_DIR}/")
    else:
        print("dry-run (没有写任何文件); 加 --apply 才落盘")
    print()
    print("A3 重生图候选 (回填区单色=内容已毁, 或修完仍剩 >= %.1f%% 破洞):" % args.a3_threshold)
    for r in a3:
        why = "单色破洞(内容已毁)" if r["filled_flat_rgb"] else "破洞仍大"
        print(f"  {r['file']:48s} holes%={r['holes%']:>14s} filled={r['filled_px']:8d}  {why}")
    print()
    print("软边图跳过清单 (rembg 正常输出, 未改动; 破洞大的仍需你眼验):")
    for r in soft:
        print(f"  {r['file']:48s} uniqA={r['uniq_a']:>10s} holes%={r['holes%']:>14s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
