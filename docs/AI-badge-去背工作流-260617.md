---
source: ai-agent
created: 2026-06-17
project: dizical
topic: badge 去背 (去白底) 全方案 + 工作流
version: V2.4-stable
status: 已落地
---

# dizical Badge 去背工作流 (一眼看懂版)

> **给任何 agent 30 秒上手** — 不管你是 dizical 内嵌脚本 / hermes skill / 一次性修复脚本, 按本文档干就不会出错.

---

## TL;DR — 30 秒上手

dizical 项目的去背**只用 1 套方案**, 叫 **"PIL 阈值 245 主路 + rembg U2-Net 兜底"**:

```
生图 → PIL 阈值 245 去白 (主路, 5-10s)
     ↓
     透明像素 < 28% ? ─── 否 ──→ 保存 RGBA, 完事 ✅
     │
     是 (软灰 / AI 假透明)
     ↓
rembg U2-Net AI 抠图 (兜底, 10s)
     ↓
保存 RGBA, 完事 ✅
```

**判断标准**: 透明像素 ≥ 28% = 主路成功; < 28% = 触发兜底.
**验收**: 4 角 alpha=0 (RGB 值任意) + 整体透明 ≥ 28%.

**总耗时**: 主路 ~5-10s, 兜底 ~10s, 一次性 5-20s 搞定.

---

## 1. dizical 项目实际用过几种方案?

历史上一共走过 **5 种去背方式**, 但**只有 1 种在用**:

| # | 方案 | 时期 | 状态 | 评语 |
|---|------|------|------|------|
| **1** | **PIL 阈值去白底 (阈值 220/245)** | V1 (2026-05) → V2.4 (现在) | ✅ **生产主路** | 快、稳、确定性强, 22+ 个老 badge 都用它 |
| **2** | **rembg U2-Net AI 抠图** | V2.4 (2026-06-16) 升级 | ✅ **生产兜底** | 主路失败时触发, 处理软灰 / AI 假透明 |
| 3 | rembg 单独使用 (无主路) | V2.0 早期 (2026-05-30) | ⚠️ 历史 | `remove_bg.py` / `download_and_rmbg.py` 单跑, 慢且无 fallback |
| 4 | PIL 阈值 220 (更宽松) | V1 (2026-05-20) | ⚠️ 已废弃 | `src/deband.py` / `src/dedupe_bg_lucky61.py`, 阈值比 245 激进, 会误杀浅色 badge |
| 5 | Photoshop 手动去背 | 老 22 个 badge 之前 (2026-04) | 🗑️ 弃用 | 人工操作不可复制, 已被 PIL 替代 |

**当前生产唯一方案 = 方案 1 + 2 双保险 (PIL 主 + rembg 兜底)**, 其他都是历史实验.

---

## 2. 完整 5 步生产流程 (V2.4, 当前生产)

**触发点**: dizical 后端调 `src/kid_app/badge_generator.py` 第 5 步, 或 hermes `/badge-image` skill 第 7 步.

### 2.1 完整代码 (推荐直接复制)

```python
"""
dizical badge 去背 — V2.4 双保险
主路: PIL 阈值 245 去白底
兜底: rembg U2-Net (透明<28% 触发)
"""
from io import BytesIO
from PIL import Image

# 阈值 245: 跟老 22 个 badge 完全一致 (4 角 RGB≈254, 留 9 容差)
THRESHOLD = 245
# 兜底阈值: 28% 是经验值, 老 badge 范围 28-69%, 低于说明 PIL 没去干净
FALLBACK_PCT = 28

def dedupe_to_rgba(path: str) -> dict:
    """
    Returns:
        {
          "ok": bool,             # True=最终 RGBA
          "method": "pil" | "rembg" | "none",
          "trans_pct": float,     # 最终透明像素占比
        }
    """
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    pixels = img.load()
    w, h = img.size

    # ── 主路: PIL 阈值 245 ──
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if r > THRESHOLD and g > THRESHOLD and b > THRESHOLD:
                pixels[x, y] = (r, g, b, 0)

    # 验证透明比例
    alpha = img.split()[-1]
    trans_count = sum(1 for px in alpha.getdata() if px < 128)
    trans_pct = trans_count / (w * h) * 100

    method = "none"
    if trans_pct >= FALLBACK_PCT:
        img.save(path, optimize=True)
        method = "pil"
    else:
        # ── 兜底: rembg U2-Net ──
        try:
            from rembg import remove
            with open(path, "rb") as f:
                raw = f.read()
            out_bytes = remove(raw)
            img = Image.open(BytesIO(out_bytes))
            img.save(path, optimize=True)
            # 重新验证
            if img.mode == "RGBA":
                alpha2 = img.split()[-1]
                trans2 = sum(1 for px in alpha2.getdata() if px < 128)
                trans_pct = trans2 / (w * h) * 100
            method = "rembg"
        except ImportError:
            # rembg 没装, 保留 PIL 结果 (主路)
            img.save(path, optimize=True)
            method = "pil"
            print("⚠️ rembg 未装, 跳过兜底. 安装: pip install rembg")
        except Exception as e:
            img.save(path, optimize=True)
            method = "pil"
            print(f"⚠️ rembg 兜底失败: {e}, 保持 PIL 结果")

    return {"ok": Image.open(path).mode == "RGBA", "method": method, "trans_pct": trans_pct}
```

### 2.2 跑在哪个文件?

| 触发点 | 文件:函数 | 用途 |
|---|---|---|
| **dizical 后端生图** | `src/kid_app/badge_generator.py::_dedupe_to_rgba` | 6 步流水线第 5 步, 自动跑 |
| **hermes skill 生图** | `~/.hermes/profiles/dizical/skills/badge-image/SKILL.md` step 7 | /badge-image 调, 自动跑 |
| **一次性修复** | `src/deband.py` (阈值 220) / `src/dedupe_bg_lucky61.py` (阈值 220) | 老 fallback, **新代码不要用** |
| **单文件 rembg 独立跑** | `remove_bg.py` / `download_and_rmbg.py` | 老 V1 测试脚本, 已被取代 |

**生产主入口 = badge_generator.py (后端) / SKILL.md step 7 (skill)**, 其他都别用.

---

## 3. 为什么是这套方案? (为什么用户认为它效果最好)

### 3.1 三层选型理由

**为什么 PIL 阈值能当主路?**
- dizical badge 都是 **enamel pin 风格** (珐琅勋章), AI 生图背景**几乎都是纯白/接近白**, 阈值一刀切**100% 命中**
- 老 22 个 badge 全用 PIL 跑过, 4 角 alpha=0 干净 (透明 33-69%), 没出过事故
- 极快: 1024×1024 PNG 5-10s, 纯像素遍历无依赖

**为什么阈值用 245 不用 220?**
- 老脚本用 220 (太宽松), 偶尔把"浅黄高光"误判为白底, 切到主体边缘
- 245 更保守, 只去 RGB(254-255) 的真白 + RGB(245-254) 的近白, 不碰浅色
- 实际数据: 22 个老 badge 4 角 RGB=254±1, 阈值 245 余量 9 完全够

**为什么需要 rembg 兜底?**
- 2026-06-15 assign_pal 事故: AI 模型偶尔**假装"透明"画棋盘格**, 4 角 RGB=237 (软灰), PIL 阈值 245 漏掉
- 兜底条件 `trans_pct < 28%` 是**经验值**: 老 badge 范围 28-69%, 低于说明 PIL 失败 (软灰/棋盘)
- rembg U2-Net 是**真 AI 抠图**, 识别主体边缘, 软灰/棋盘都识别得出
- 性能: 首次下载模型 ~176MB, 之后缓存, 跑 1 张 ~10s

### 3.2 用户拍板记录

- **2026-05-12**: 第一次大规模去背, 阈值 220 (老脚本) → 阈值 245 改进 → 用到现在
- **2026-06-12**: V2 工作流定型, 仍走 PIL 阈值
- **2026-06-15**: assign_pal 灰方框事故 → 决定加 rembg 兜底 (PR #102)
- **2026-06-16**: V2.4 双保险正式落地 (PR #103 文档沉淀)

**用户原话证据** (assign_pal 反馈, 2026-06-15):
> "批改小帮手有灰方框" → 触发 rembg 兜底机制

**用户认为效果最好** = **PIL 阈值 245 主路 + rembg 兜底**, 因为:
- 22+ 个 badge 跨 1.5 月稳定运行
- assign_pal 灰方框事故后用 rembg 修了, 后续没复发
- 跑得快 (5-20s 一张)
- 脚本 30 行内, 任何 agent 都能复刻

---

## 4. 一眼能看懂的检查清单

### 4.1 生成后**必跑**的 4 角 alpha 验收

```python
from PIL import Image
img = Image.open("path/to/badge.png")
w, h = img.size
corners = [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]
for x, y in corners:
    r, g, b, a = img.getpixel((x, y))
    assert a == 0, f"4 角 alpha 必须 = 0, 实际 ({x},{y})={a}"
print("✅ 4 角干净")
```

### 4.2 透明比例验收 (脚本 6.1 节里也有)

```python
img = Image.open("path/to/badge.png")
w, h = img.size
if img.mode == "RGBA":
    alpha = img.split()[-1]
    trans = sum(1 for px in alpha.getdata() if px < 128)
    pct = trans / (w * h) * 100
    assert pct >= 28, f"透明比例 {pct:.0f}% < 28% 阈值"
    print(f"✅ 透明比例 {pct:.0f}% 达标")
else:
    raise AssertionError("❌ 不是 RGBA, 走老 fallback 图, 会显示白方框")
```

### 4.3 4 角 RGB 防"软灰"额外检查

```python
# 防止 AI 假装透明 (RGB=237 软灰) - 这种 PIL 主路会漏
for x, y in [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]:
    r, g, b, a = img.getpixel((x, y))
    if a == 0 and (r > 200 and g > 200 and b > 200):
        print(f"⚠️ 4 角 ({x},{y}) 是软灰透明, PIL 主路漏了, 需 rembg 兜底")
```

---

## 5. 排错指南 (一眼对照)

| 现象 | 真凶 | 修法 |
|---|---|---|
| `/badges` 显示**白方框**包围徽章 | 图是 RGB 无 alpha 通道 | 跑本文档 §2.1 脚本去背 |
| `/badges` 显示**灰方框**包围徽章 | 软灰透明 (AI 假装) | 透明<28%, rembg 兜底没装/没触发 |
| badge 4 角**有 1 角不透明** | PIL 阈值漏, 主体贴边 | 跑兜底 (trans_pct < 28% 触发) |
| badge 主体**边缘残影** | PIL 太激进 (阈值 220 老脚本) | 用新脚本 (阈值 245) |
| rembg 跑**第一次很慢** | 首次下载模型 ~176MB | 等 1 次, 模型缓存到 `~/.u2net/` |
| rembg 跑**仍然失败** | 模型未下完 / 网络问题 | 跑 `pip install rembg` + 离线重试 |
| rembg 跑出来**主体边缘糊** | U2-Net 对小细节不友好 | 接受 / 改 prompt 重生图 |

---

## 6. 一键验收脚本 (复制即用)

```python
"""
跑: python3 verify_badge.py <badge.png>
返回 0 = 全部通过, 1 = 失败
"""
import sys
from PIL import Image

def verify(path: str) -> int:
    img = Image.open(path)
    w, h = img.size

    # 检查 1: 必须是 RGBA
    if img.mode != "RGBA":
        print(f"❌ {path}: mode={img.mode} (非 RGBA, 会显示白方框)")
        return 1

    # 检查 2: 4 角 alpha=0
    corners = [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]
    for x, y in corners:
        r, g, b, a = img.getpixel((x, y))
        if a != 0:
            print(f"❌ 4 角 ({x},{y}) alpha={a} (非 0)")
            return 1
    print(f"✅ 4 角 alpha=0 干净")

    # 检查 3: 透明比例 >= 28%
    alpha = img.split()[-1]
    trans = sum(1 for px in alpha.getdata() if px < 128)
    pct = trans / (w * h) * 100
    if pct < 28:
        print(f"⚠️ 透明比例 {pct:.0f}% < 28% (软灰, 需 rembg 兜底)")
        return 1
    print(f"✅ 透明比例 {pct:.0f}% 达标 (>= 28%)")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 verify_badge.py <badge.png>")
        sys.exit(2)
    sys.exit(verify(sys.argv[1]))
```

---

## 7. 快速参考卡片

```
┌─────────────────────────────────────────────────────────────┐
│  dizical 去背工作流 V2.4 — 30 秒版                          │
├─────────────────────────────────────────────────────────────┤
│  阈值:         245 (主路 PIL 阈值)                          │
│  兜底阈值:     透明 < 28% 触发 rembg                        │
│  主路耗时:     5-10s / 1024×1024 PNG                        │
│  兜底耗时:     ~10s (含模型) / 首次 +10s 下载               │
│  输出格式:     RGBA, 4 角 alpha=0                           │
│  验收:         4 角 alpha=0 + 透明 >= 28%                   │
│  依赖:         Pillow (主路), rembg + onnxruntime (兜底)    │
│  安装:         pip install pillow rembg                     │
├─────────────────────────────────────────────────────────────┤
│  入口文件:                                                   │
│    后端: src/kid_app/badge_generator.py::_dedupe_to_rgba    │
│    skill: ~/.hermes/profiles/dizical/skills/badge-image/    │
│           SKILL.md step 7                                   │
├─────────────────────────────────────────────────────────────┤
│  不要再用:                                                   │
│    ❌ 阈值 220 (老脚本 src/deband.py)                        │
│    ❌ rembg 独立使用 (remove_bg.py)                          │
│    ❌ Photoshop 手动                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. 变更历史

| 版本 | 日期 | 变更 | 触发 |
|---|---|---|---|
| V1 (22 个 badge) | 2026-05-12 | PIL 阈值 220 (老脚本) | docs/badge-prompts.md 沉淀 |
| V2.0 | 2026-05-30 | rembg 独立脚本 (V1 早期) | remove_bg.py 创建 |
| V2.3 | 2026-06-16 | 改 prompt 删 "clean white background" | PR #101 |
| V2.4 (本版) | 2026-06-16 | **PIL 阈值 245 + rembg 兜底 (双保险)** | PR #103 (assign_pal 灰方框调查) |
| V2.5 | 2026-06-16 | 通用字段 + 表彰型徽章设计 | PR #106-#111 (去背未变) |
| V2.5 文档沉淀 | 2026-06-17 | **本文档上线** (一眼看懂版, 独立于 docs/badge-image-workflow.md) | 本次 session |

---

## 9. 关联文件 (本项目内)

- `docs/badge-image-workflow.md` — V2.5 完整 5 步工作流 (含表单字段、commit 端点、calc 规则)
- `docs/badge-prompts.md` — 22 个老 badge 的 enamel pin prompt 模板
- `src/kid_app/badge_generator.py` — 后端 6 步流水线, 内含 `_dedupe_to_rgba` 函数
- `src/kid_app/badge_draft.py` — V2 draft schema + tmp 路径
- `~/.hermes/profiles/dizical/skills/badge-image/SKILL.md` — hermes 端 SKILL 完整 8 步
- `src/deband.py` / `src/dedupe_bg_lucky61.py` — 老 PIL 阈值 220 脚本, 不要再用
- `remove_bg.py` / `download_and_rmbg.py` — 老 rembg 独立脚本, 不要再用

---

## 10. 一句话总结

**dizical badge 去背 = PIL 阈值 245 (主) + rembg U2-Net (兜底透明<28%), 30 行代码 5-20s 搞定, 任何 agent 按本文档 §2.1 抄就行.**
