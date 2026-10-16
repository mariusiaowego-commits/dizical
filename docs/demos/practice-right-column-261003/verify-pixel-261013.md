# verify-pixel-261013 · 独立复量（pixel · 只读，不改 canvas-01.html）

被验对象：`docs/demos/practice-right-column-261003/canvas-01.html`
- mtime `2026-10-13 10:25:58` · 大小 `744,284 B` · sha256 前 16 位 `b72829d143b0cfd6`
- 对照单：`rework-pixel-261013a.md`（我上轮返工单）+ `brief-grok-261013.md` 验收清单；已知在修项见 `rework-grok-261013b.md`
- 复核方式：只读脚本 `/Users/mt16/.hermes/profiles/pixel/cache/scratch/pw/verify2_261013.py`（几何/等高/竖切/可见性）、`verify_261013.py`（组合树/卡槽/弹窗）、`probe_slot_bus.py`、`probe_frames_headed.py`
- 会话：Playwright chromium，宿主窗口 1280×800（画布档 1133/744/440）；**几何量在 headless 与真会话（headed）两遍都跑，数值一致**
- 画布源文件未动：`practice-ticket-v4-260920.html` sha256 前缀仍 `e86d4bc56163218d`

---

## 1 等高律（rework ① ② / brief 1）—— PASS

```
档     空模块 ticket.h   挂满 6 模块 ticket.h   delta   挂满后各卡 t/h/b
1133   584               584                  0       A/B/S/D/R/Q 全部 t=32 h=584 b=616
744    780               780                  0       A 58/780/838 · B 862 · S 1666 · D 2470 · R 3274 · Q 4078（下方行堆叠）
440    780               780                  0       同上（l 收窄到 18）
```
- verdict：**PASS**。每张卡高 = 票卡高（±0），顶边 32 = 票卡顶 32，底边 616 = 票卡底 616。
- 注意：H 不是写死的常量，随宿主高度变（本机 1280×800 → H=584；grok 高窗 1440×1100 → H=776；宿主高 744 → 579.3），与 `spec-grok-equalheight-261013.md` 的口径一致。

## 2 高度回环（rework ③）—— PASS

```
1133   iframe.clientHeight 594  ≠  画布 scrollHeight 630
744    689 ≠ 4894
440    689 ≠ 4894
```
- verdict：**PASS**（三档都不再恒等）；两次连续 `syncAll()` 后数值不变（幂等），未见自增放大。

## 3 画布被竖切（rework-grok-261013b ① / dad 反馈）—— FAIL

```
1133   iframe 可视 594  画布 scrollHeight 630    → 竖切 36px（票卡底 616 超出可视底 22px）
744    iframe 可视 689  画布 scrollHeight 4894   → 竖切 4205px（6 张卡堆到 4858）
440    iframe 可视 689  画布 scrollHeight 4894   → 竖切 4205px
```
- verdict：**FAIL**。1133 档缺 36px（票卡下半截需在 iframe 内再滚才看得到）；744/440 档 6 张卡纵向堆叠时缺 4205px，靠 iframe 内部滚动，画布内容不完整。
- 与 hermes 在真会话量到的 465 vs 630 同族（宿主更矮 → iframe 更矮 → 竖切更大）。

## 4 可见性 / 实例（brief 4）—— PASS

```
三档都实测：visibleMods = ["A","B","S","D","R","Q"]，state.mods 同值，.cz-mod 总数 = 6 = 定义数
单组合实测（1133）：组合1 visible=[A,D,R,S] / modCount 4；组合2 [A,S,R] / 3；组合3 [A,B,D,R] / 4
```
- verdict：**PASS**。无重复实例、无第二排游离（每个模块 DOM 唯一）。

## 5 组合树几何（rework 几何条 / brief 3，对照 image23/24）—— PASS（按等高分配规则）

```
1133 档 · 票卡 [l6 t32 w360 h584 b616]（track 左缘 376）

组合1  A [378,32,460,330]  dTop 0  dH −254      ← 仪表盘 = round(584×370/654)=330
       D [378,374,224,242] dTop 342 dBot 0      ← 与 R 并排卧底
       R [614,374,224,242] dTop 342 dBot 0
       S [854,32,130,584]  dTop 0  dH 0         ← 通高
       track clientW 751 / scrollW 751 → overflow 0（一屏收拢 ✓）

组合2  A [378,32,430,584] · S [824,32,76,584] · R [916,32,360,584]
       三块 dTop 0 / dH 0 / dBot 0；R 右缘 1276 > 画布 1133 → 超界
       track overflow 151（一屏右界 X=1127，超出量 143~151）
       ⚠ agy 原稿要求 >200，实测 151；grok spec 自定门槛 ≥150 → 按 agy 门槛算「低于预期」，按 grok 门槛算 PASS

组合3  A [378,32,430,584] · B [824,32,340,389] · D [824,433,340,183] · R [1180,32,360,584]
       B+D+gap12 = 584 = H ✓（复合列总高 = 票卡高）；track overflow 415 ✓
```
- verdict：**PASS**（组合1/2/3 逐块 rect 与 image23/24 结构一致：组合1 = 仪表盘 + 底部卧卡一行 + 最右通高竖条；组合2 = 一行并排等高、最右为超界记录卡；组合3 = 仪表盘 + 复合列 + 超界记录卡）。
- 唯一保留意见：组合2 超界量 151px（agy 原稿 >200）。

## 6 卡槽（rework 卡槽条 / spec-agy-slot-261012）—— 半 PASS

```
.czpunch-slot 存在 ✓（l378 t38 w430 h48，宽 = 仪表盘宽 430）
getAnimations(subtree) = 0 ✓ · .cz-mini = 0 ✓ · .cz-slot = 0 ✓ · 文件里 runInsert/FALLBACK_MS 计数 0 ✓
待命态：slot.dataset.mode=prep · #pkInsertedHead display=none · #pkSlotIdle display=flex ✓
计时态（真会话 headed，调 setCanvasStage('run')）：stage-running · slotMode=run
        · head display=flex · idle display=none · canvasRunning=true ✓（真会话成立；headless 档 stage 不跟随，属无头口径问题）
接缝：仪表盘顶 32 − 槽底 86 = **−54px（重叠）** ✗ 与 agy 无头量到的 +6px 不一致
```
- verdict：**存在/无动画/两态 = PASS；接缝 = FAIL**（槽压在仪表盘顶部 54px 内，不满足「正上方 + 6~8px 接缝」）。此项已在 `rework-grok-261013b.md` ② 在修。

## 7 联动总线（rework 联动条 / spec-agy-binding）—— 未判定（NOT VERIFIED）

```
window.DizicalPracticeBus 存在 ✓（api=true）
左栏自身步进 ✓：#pkBpmVal 60 → 点两下 #pkBpmUp → 62（真会话/无头一致）
右栏读数取不到 ✗：在 S 卡 iframe 内 #bpmFace / .bpm 两个选择器都命中不到（元素确实存在，
        my 可见性探针 hasBpm=true）→ 我拿不到「右栏真值」，故
        左→右：left [60,62]  right [null,null]   ← 无法判定
        右→左：btn=null（S 卡里没有 #stepUpBtn / #bpmUp / #stepUp）  ← 无法判定
        负控：right [null,null]                  ← 无法判定（无法观测右栏）
        api.read().int = {bpm:null, rulerValue:null, tag:null}  ← 总线自己也读不到右栏
        唯一可确认的联动：session 映射有 log 记录（{op:'session', dir:'L2R', title:'正常长音练习', clockHidden:true}）
```
- verdict：**NOT VERIFIED**（不是红也不是绿）。需要 grok 在 `rework-grok-261013b.md` ③ 里给出：右栏 BPM 真选择器 + 未挂 B 卡时该值的落点（A? S?）+ 可复现读数步骤。我拿到后按同一脚本复量。

## 8 弹窗遮罩（保持项，勿回退）—— PASS

```
#pkFolioBtn 点击后：#pkFolioModal.open = true · position=fixed · z-index=100
· background rgba(44, 62, 80, 0.45) · 覆盖 1133×594（= iframe 可视区）· elementFromPoint 命中 pkFolioModal
```
- verdict：**PASS**，与 hermes 10:25 的真会话实测一致，未回退。

---

## 环境说明（重要，写给我的下一轮）

- **无头 vs 真会话**：headless 下模块 iframe 的 srcdoc 内容实测不渲染（`docHtmlLen=26 / bodyKids=0`，
  A/D/S 三卡全空），同一次探测改真会话（headed）后 A=164,561 字符 / 9 个 body 子节点 / 有 `#rulerInput`，
  S 有 bpm 元素 → **内容类断言必须走真会话**，几何类两遍一致可互证。我上轮的「卡片是空的」结论**撤回**，
  那是我的无头口径问题，不是交付缺陷。
- 本机 H=584（宿主 1280×800），grok 价签的 776 是 1440×1100 高窗，两者是同一族的比例闭环，不矛盾。

## 待 grok 交 b 返工后再补量

```
① 竖切（本节 3）：要求 iframe.clientHeight ≥ 画布 scrollHeight（1133 档差 36px，744/440 档差 4205px）
② 卡槽接缝（本节 6）：要求 slot.bottom + 6~8 == A.top（现值 −54）
③ 联动（本节 7）：要求给出右栏真选择器与读数步骤，再跑 左→右 / 右→左 / 负控 三组前后值
```
补量时我仍只读，脚本：`/usr/local/bin/python3 pw/verify2_261013.py "<标签>" --headed`
