# Badge 图片生成工作流 (V2.4, 2026-06-16)

> dizical badge 图生成的**完整**流程 + 验收清单 + 排错指南.
> 沉淀自 2026-06-16 用户反馈 "批改小帮手 灰方框" bug 调查, 防止下次重蹈覆辙.

---

## 1. 流程全景 (5 步)

```
STEP 1 表单填 meta       →  STEP 2 草稿         →  STEP 3 生图       →  STEP 4 去白底 (PIL + rembg)  →  STEP 5 commit
/config/badge 填字段       /api/badge/draft     /badge-image skill    skill step 7 (V2.4)               /api/badge/commit-from-draft
                                                                 ├─ 主路: PIL 阈值 245
                                                                 └─ 兜底: 透明<28% → rembg U2-Net
```

每步**强验收点** (不通过不能进下一步):
- STEP 1 验收: 表单**cond_text 必填**, **unlock_strategy 选 (calc/immediate)**
- STEP 2 验收: draft.json 写到 `data/lib/badge_data/{draft_id}.json`, status=`draft_created`
- STEP 3 验收: 图存 `.tmp/{draft_id}_v{n}.png`, 文件 > 500KB
- **STEP 4 验收 (关键)**: 4 角 alpha=0 **AND** 4 角 RGB 不画"软灰" + 真透明比例 ≥ 28%
- STEP 5 验收: 浏览器 `/badges` 看不到"灰方框"

---

## 2. STEP 4 去白底 — 双保险细节 (V2.4)

### 2.1 原理
- fal-ai/gpt-image-2 模型对 prompt 理解**不稳定**:
  - 老 prompt "isolated on a clean white background" → 输出 RGB(254) 真接近白 ✅
  - 新 prompt "isolated object, transparent PNG background" → 输出 RGB(237) 软灰 + 假透明棋盘格 ❌
- 老的 22 个 badge (first_log, streak_*, lucky_61_*, grade_*, daily_checkin 等) 都是老 prompt + PIL 阈值去, **稳定** 因为 RGB 接近 255
- 偶尔新 prompt 失败 → PIL 阈值无效 → 触发 **rembg U2-Net AI 抠图** 兜底

### 2.2 流程代码
```python
from PIL import Image
from rembg import remove
from io import BytesIO

img = Image.open(src_path)
if img.mode != "RGBA":
    img = img.convert("RGBA")

# 主路: PIL 阈值 245
THRESHOLD = 245
pixels = img.load()
w, h = img.size
for y in range(h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        if r > THRESHOLD and g > THRESHOLD and b > THRESHOLD:
            pixels[x, y] = (r, g, b, 0)

# 验证
alpha = img.split()[-1]
trans_pct = sum(1 for px in alpha.get_flattened_data() if px < 128) / (w*h) * 100

# 兜底: < 28% 触发 rembg
if trans_pct < 28:
    with open(src_path, "rb") as f:
        raw = f.read()
    out_bytes = remove(raw)
    img = Image.open(BytesIO(out_bytes))
    img.save(src_path, optimize=True)
```

### 2.3 验收指标
| 指标 | 阈值 | 其他 badge 范围 | 失败信号 |
|---|---|---|---|
| **真透明比例** (alpha < 128) | ≥ 28% | 28-69% | PIL 没去干净 / 假透明 |
| **4 角 alpha** | = 0 | 0 | rembg 失败残留 |
| **4 角 RGB** | 任意 (alpha=0 不展示) | RGB(254) 或 RGB(0) | 软灰 (237) = AI 画进图 |

---

## 3. 排错指南 (实战汇总)

### 3.1 用户报告 "灰方框和白色方块交织"
**根因**: AI 假装画"棋盘格"做假透明, RGB 通道里画了灰白方块, alpha=255
**验证**:
```bash
python3 -c "
from PIL import Image
img = Image.open('src/kid_app/static/badges/assign_pal_v2.png')
opaque_gray = sum(1 for y in range(img.size[1]) for x in range(img.size[0])
                   if img.getpixel((x,y))[3] >= 128 and img.getpixel((x,y))[0] > 200)
print(f'不透明灰白像素: {opaque_gray} (越低越好, < 8% OK)')
"
```
**修法**: rembg 处理 (skill step 7 自动触发, 透明 < 28% 时)

### 3.2 用户报告 "图四周锯齿 / 边缘狗牙"
**根因**: PIL 阈值太严 (>240), 误伤浅金边抗锯齿像素
**修法**: 阈值保持 245, 让 rembg (U2-Net AI) 兜底, 不要手动调 PIL 阈值

### 3.3 STEP 4 跑后 transparent < 28%, 但 rembg 也失败
**根因**: rembg 未装或模型下载失败
**修法**:
```bash
/usr/local/bin/python3 -m pip install rembg
# 首次会下载 u2net.onnx (~176MB) 到 ~/.u2net/
```

### 3.4 用户报告 "徽章整体扁平, 不像 3D enamel pin"
**根因**: prompt 写 "2D illustration" 跟 enamel pin 风格冲突
**修法**: 用标准 prompt 模板 (V2.3):
```
An emoji-adjacent 3D enamel pin of {PLACEHOLDER}. Polished gold metal borders
enclose flat, glossy enamel fills. ... Orthographic, straight-on view,
high quality, isolated object, transparent PNG background.
```

---

## 4. 已知不修 (out of scope, 留 followup)

- 老 4 个 RGB fallback 图: `fire_badge.png`, `medal_badge.png`, `star_badge.png`, `week_star_badge.png` (纯占位图, 业务上未使用, 跟 AI 生图无关)
- 老 22 个 badge 已 PIL 去背过 (2026-05-12), 不需重做
- 灰方框问题修了后, 整个 dizical 所有 RGBA badge 视觉一致

---

## 5. 验证脚本 (用户验收用)

```bash
# 5.1 单图验证 (PIL)
python3 -c "
from PIL import Image
import sys
p = sys.argv[1]
img = Image.open(p)
w, h = img.size
trans = sum(1 for px in img.split()[-1].get_flattened_data() if px < 128)
opaque_gray = sum(1 for y in range(h) for x in range(w)
                   if img.getpixel((x,y))[3] >= 128 and img.getpixel((x,y))[0] > 200)
print(f'{p}: mode={img.mode}, 透明 {trans/(w*h)*100:.1f}%, 灰白不透明 {opaque_gray/(w*h)*100:.1f}%')
" src/kid_app/static/badges/assign_pal_v2.png

# 5.2 批量验证 (所有 badge)
python3 -c "
from PIL import Image
import os
for f in sorted(os.listdir('src/kid_app/static/badges')):
    if not f.endswith('.png'): continue
    p = f'src/kid_app/static/badges/{f}'
    img = Image.open(p)
    w, h = img.size
    if img.mode == 'RGBA':
        trans = sum(1 for px in img.split()[-1].get_flattened_data() if px < 128)
        op = sum(1 for y in range(h) for x in range(w)
                 if img.getpixel((x,y))[3] >= 128 and img.getpixel((x,y))[0] > 200)
        print(f'{f:<35} RGBA 透明 {trans/(w*h)*100:>5.1f}% 灰白 {op/(w*h)*100:>5.1f}%')
    else:
        print(f'{f:<35} RGB  (无 alpha 通道, 老 fallback 图)')
"

# 5.3 浏览器实际视觉
# open http://127.0.0.1:8765/badges 找 "批改小帮手" 看是否干净浮卡片
```

---

## 6. 变更历史

| 版本 | 日期 | 变更 | 触发 |
|---|---|---|---|
| V1 | 2026-05-12 | PIL 去白底 (老 22 个 badge) | `docs/badge-prompts.md` |
| V2.1 | 2026-05-20 | workflow 文档初版 | `docs/badge-workflow.md` |
| V2.3 | 2026-06-16 | 改 prompt 删 "clean white background" | PR #101 |
| **V2.4** | **2026-06-16** | **PIL 阈值 + rembg 兜底 (双保险), 验收清单** | **本次 (assign_pal 灰方框调查)** |
