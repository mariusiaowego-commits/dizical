# ⚠ 真源 (source of truth) = dizical/scripts/gate_v3.py —— skill 目录里的那份是镜像。
#   改动必须双向同步: 先改 repo, 再 cp 到 skill, 最后 md5 对拍两边相等。
"""badge 出图门禁 v3 —— 比例口径 + 杂点过滤。

用法: python3 gate_v3.py <badge.png> [more.png ...]
口径变更(相对 matte_and_gate.py 的 v2 门禁):
  - 封闭边缘缺口: 由「绝对 300px」改成「占剪影面积 < 1%」 (rim 上的 1px 针孔不再误报 FAIL;
    实测新图 0.16~0.19%, 出厂开放剪影 7.01%)
  - 计算任何剪影指标前先滤掉 < 10px 的连通分量 (角落 1px 杂点会把半径剖面撑爆)
  - 新增 alpha 数值门禁: alpha 上限 >= 250 且 可见区(alpha>0) 均值 >= 200
  - (P0 sprint-26101302, 2026-10-13) 判据文本补口径: 圆度 = 4πA / cv2.arcLength(c, True)²
    —— 周长口径不写清会漂 3 倍 (同图 0.308 / 0.898 / 0.999), 见 gate() 内注释。
"""
import sys, numpy as np, cv2
from PIL import Image
from scipy import ndimage

MIN_SPECK = 10
TIER = "gen" if "--gen" in sys.argv else ("regen" if "--regen" in sys.argv else "all")


def gate(path):
    im = Image.open(path)
    a = np.asarray(im.convert("RGBA"))
    al = a[:, :, 3].astype(float); rgb = a[:, :, :3]
    solid0 = al > 0
    lbl, n = ndimage.label(solid0, structure=np.ones((3, 3), bool))
    sizes = ndimage.sum(solid0, lbl, range(1, n + 1)) if n else np.array([])
    specks = int((sizes < MIN_SPECK).sum())
    keep = np.isin(lbl, [i + 1 for i, s in enumerate(sizes) if s >= MIN_SPECK])
    solid = keep
    res = {}
    res["size"] = f"{im.mode} {im.size}"
    res["specks"] = specks
    res["alpha_max"] = int(al.max())
    res["vis_mean"] = float(al[solid].mean()) if solid.any() else 0.0
    enc = ndimage.binary_fill_holes(solid) & ~solid
    res["holes"] = int(enc.sum())
    ys, xs = np.where(solid); cy, cx = ys.mean(), xs.mean()
    nb = 720
    rad = np.zeros(nb)
    for i, t in enumerate(np.linspace(0, 2 * np.pi, nb, endpoint=False)):
        for rr in range(520, 0, -1):
            y = int(round(cy + rr * np.sin(t))); x = int(round(cx + rr * np.cos(t)))
            if 0 <= y < a.shape[0] and 0 <= x < a.shape[1] and solid[y, x]:
                rad[i] = rr; break
    med = np.array([np.median(rad[max(0, i - 15):i + 16]) for i in range(nb)])
    res["dip"] = float((-np.min(rad - med)) / max(1e-9, np.median(rad)))
    hull = np.zeros(solid.shape, np.uint8)
    cnts, _ = cv2.findContours(solid.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    cv2.drawContours(hull, [cv2.convexHull(c)], -1, 1, -1)
    dents = int((hull.astype(bool) & ~solid & ~enc).sum())
    area = int(solid.sum())
    res["dents"] = dents
    res["dents_rel"] = dents / max(1, area)
    inner = solid & ndimage.binary_dilation(~solid, iterations=2)
    px = rgb[inner]
    res["fringe"] = float(((px[:, 0] > 225) & (px[:, 1] > 225) & (px[:, 2] > 225)).mean()) if len(px) else 0.0
    g = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    F = np.abs(np.fft.fftshift(np.fft.fft2(g - g.mean())))
    h, w = F.shape; cyf, cxf = h // 2, w // 2
    res["fft"] = float(max(F[cyf - 2:cyf + 3, int(cxf + w / p) - 2:int(cxf + w / p) + 3].max() for p in (8, 16)) / (np.median(F) + 1e-9))
    trans = al == 0
    res["trgb"] = len(np.unique(rgb[trans].reshape(-1, 3), axis=0)) if trans.sum() else 0
    res["circ"] = 4 * np.pi * cv2.contourArea(c) / max(1e-9, cv2.arcLength(c, True) ** 2)
    # 圆度口径 (P0 sprint-26101302, 2026-10-13): 只有 cv2.arcLength(闭合轮廓周长) 这一种算法,
    # 判据文本必须写出口径 —— 同一张图的圆度会随周长口径漂 3 倍 (同图实测 0.308 / 0.898 / 0.999):
    #   · cv2.arcLength(c, True)  (本脚本, 默认口径) → 0.898
    #   · 内接多边形边长求和 (顶点连线)              → 0.308
    #   · 4πA / (2πr̄)² 用平均半径算的周长           → 0.999
    # 任何引用「圆度 >= 0.85」的地方都必须注明 = cv2.arcLength(c, True)。
    res["checks_t1_all"] = [                       # 任何文件都要过
        ("alpha 上限 >= 250", res["alpha_max"] >= 250),
        ("可见区 alpha 均值 >= 200", res["vis_mean"] >= 200),
        ("无棋盘格 FFT < 60", res["fft"] < 60),
    ]
    res["checks_t2_regen"] = [                     # 经本管线重写过的文件(透明区按仓库约定归一)
        ("内圈 2px 近白 < 1%", res["fringe"] < 0.01),
        ("透明区 RGB 常量数 <= 4", res["trgb"] <= 4),
    ]
    res["checks_t3_gen"] = [                       # 仅"新生成的封闭容器"图
        ("封闭洞 == 0", res["holes"] == 0),
        ("封闭边缘缺口占剪影 < 1%", res["dents_rel"] < 0.01),
        ("半径剖面凹陷 < 1%", res["dip"] < 0.01),
        ("圆度 >= 0.85 (周长口径 = cv2.arcLength)", res["circ"] >= 0.85),
    ]
    res["checks"] = (res["checks_t1_all"]
                     + (res["checks_t2_regen"] if TIER in ("regen", "gen") else [])
                     + (res["checks_t3_gen"] if TIER == "gen" else []))
    return res


if __name__ == "__main__":
    allok = True
    for p in [x for x in sys.argv[1:] if not x.startswith("--")]:
        r = gate(p)
        ok = all(v for _, v in r["checks"])
        allok &= ok
        print(f"\n{'-'*104}\n{p}  [{r['size']}]  {'PASS' if ok else 'FAIL'}")
        print(f"  杂点(<{MIN_SPECK}px) {r['specks']} 个 | alpha 上限 {r['alpha_max']} | 可见区均值 {r['vis_mean']:.2f} | "
              f"封闭洞 {r['holes']} | 缺口 {r['dents']}px = {100*r['dents_rel']:.3f}% 剪影 | 凹陷 {100*r['dip']:.3f}% | "
              f"内圈近白 {100*r['fringe']:.2f}% | 棋盘格 {r['fft']:.1f} | 透明区RGB {r['trgb']} | 圆度 {r['circ']:.4f}")
        for k, v in r["checks"]:
            print(f"    [{'PASS' if v else 'FAIL'}] {k}")
    print(f"\n=== 总判定: {'全过' if allok else '有 FAIL'} ===")
