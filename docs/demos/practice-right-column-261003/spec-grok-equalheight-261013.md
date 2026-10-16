# spec-grok-equalheight-261013 · 等高落地与价签实测

只改了 `canvas-01.html`。画布源 `practice-ticket-v4-260920.html` sha256 前缀仍是 `e86d4bc56163218d`。未 commit。

H 不写死。`ticketBox()` 取 `.pk-ticket` 的 `getBoundingClientRect().height` 再 `Math.round`。iframe 高 = min(宿主可用, 票卡带 − 24)，不读 `scrollHeight`，不把模块底边算进票卡带。

宽屏（画布 clientWidth ≥ 1024）分高：

- 顶格卡（组合 2/3 的 A、组合 1/2 的 S、组合 2/3 的今日记录 R）= H
- 组合 1 中轴列总高 = H。仪表盘 = round(H × 370/654)，卧卡 = H − 仪表盘 − 12，底边对齐票卡。竖条 S = H
- 组合 3 复合列总高 = H。节拍器 = round(H × 436/654)，时长卡 = H − 节拍器 − 12
- 列间隙 12px（与 `.cz-astack` / `.cz-comp` 的 gap 相同）

窄屏（< 1024）不拆列：每张卡 = H，堆进下方行。未做规格举例里的 480 轮播或 280–360 内容高。

## 价签（Chrome headless，窗口 1440×1100，inner 1440×1013，`?fresh=` 清掉 `canvas01_state`）

### 高窗 · vp 1133 · 票卡自然高

| 项 | 实测 | verdict |
|---|---|---|
| 票卡 `.pk-ticket` | 360 × 775.7（css `775.656px`），l16 t56 b831.7 | H = 775.7，round 后喂模块的数是 776。不是 559，也不是 520 |
| 挂满 6 模块后票卡 | 仍 360 × 775.65625 | delta 0。PASS |
| iframe / 画布 scrollHeight | client 1133×808，documentElement.scrollHeight 868 | 808 ≠ 868。PASS，无回环 |
| combo=off，mods [A,S] | 可见 A,S；`.cz-mod` 数 2 | visibleMods == state.mods。PASS |
| combo=off 挂满 | 可见 A,B,S,D,R,Q 各 h776 dTop 0 dH 0.3 | 每张 = H（±1）。PASS |

### 组合 1（image23）H=776

中轴列 460×776，底 832，与票卡底差 0.3。439 + 12 + 325 = 776。

| 块 | l | t | w | h | 相对票卡 | verdict |
|---|---|---|---|---|---|---|
| A 仪表盘 | 394 | 56 | 460 | 439 | dTop 0，dBot −336.7 | 顶对齐。高 = round(776×370/654)=439。PASS |
| D 时长 | 394 | 507 | 224 | 325 | dTop 451，dBot 0.3 | 与 R 并排，底对齐票卡。PASS |
| R 小卡 | 630 | 507 | 224 | 325 | dTop 451，dBot 0.3 | 与 D 同高同宽。PASS |
| S 竖条 | 870 | 56 | 130 | 776 | dTop 0，dH 0.3 | 通高，没有被拉成 2H。PASS |
| 轨道 | clientW 725，scrollW 725 | | | | overflow 0，右缘 x=1117 | 一屏收拢。PASS |
| 卡槽 | seam 6，槽宽 460 = 仪表盘宽 460，getAnimations 0 | | | | 无 `.cz-mini` / `.cz-slot` | PASS。`runInsert` / `FALLBACK_MS` 在本文件出现 0 次 |

可见 A,D,R,S，`.cz-mod` 数 4。PASS。

### 组合 2（image24）

| 块 | l | t | w | h | 右缘 | verdict |
|---|---|---|---|---|---|---|
| A | 394 | 56 | 430 | 776 | 824 | dTop 0，dH 0.3，dBot 0.3。PASS |
| S | 840 | 56 | 76 | 776 | 916 | 文字竖排：`writing-mode: vertical-rl`，`data-tate=1`。PASS |
| R 今日记录 | 932 | 56 | 360 | 776 | 1292 | 通高。PASS |
| 轨道 | clientW 725，scrollW 902 | | | | 轨道右缘 x=1117 | overflow 177。记录卡右缘比轨道多出 175，比画布 clientW 1133 多出 159。PASS（≥150） |

可见 A,S,R，`.cz-mod` 数 3。PASS。

### 组合 3

| 块 | l | t | w | h | verdict |
|---|---|---|---|---|---|
| A | 394 | 56 | 430 | 776 | 通高顶对齐。PASS |
| B | 840 | 56 | 340 | 517 | round(776×436/654)=517，顶对齐。PASS |
| D | 840 | 585 | 340 | 247 | 517+12+247=776，底差 0.3。PASS |
| 复合列 | 840 | 56 | 340 | 776 | 列高 = H。PASS |
| R | 1196 | 56 | 360 | 776 | 右缘 1556。PASS |
| 轨道 | scrollW 1166，clientW 725 | | | | overflow 441，轨道右缘 x=1117。PASS（≥150） |

可见 A,B,D,R，`.cz-mod` 数 4。PASS。

### 另两档（同一高窗，compact 媒体未开，因为 iframe 高 810 > 800）

| 档 | 票卡 | 模块 | iframe ≠ scroll | verdict |
|---|---|---|---|---|
| 744 | 580×775.7，t58 | A 576×776 t58；S 576×776 t858（dTop 800，下方行） | 810 ≠ 1670 | 每张 = H，S 在下方行。PASS |
| 440 | 408×775.7，t58 | A 404×776 t58；S 404×776 t858（dTop 800） | 810 ≠ 1670 | 同上。PASS |

### 宿主本身高 744（Emulation 1280×744，compact 媒体开）

票卡 360×579.3（css `579.312px`）。挂满 6 模块后仍 579.3，delta 0。A/S 高 579，dTop 0，dH −0.3。iframe 590 ≠ scrollHeight 625。PASS。这是 hermes 先前 559 的同一族，数值随 iframe 高变，不写进 CSS。

### 联动与弹窗（同一会话，组合 2）

| 项 | 前后值 | verdict |
|---|---|---|
| 左→右 | 左栏 60→59，竖条 82→59 | PASS。`DizicalPracticeBus` 在画布里。减速走 pointerdown |
| 右→左 | 竖条 59→60，左栏 59→60 | PASS |
| 负控 `?negctl=bus` | 左栏停在 60，竖条 82→83 | `R2-D1 fail [联动1 右→左] 左栏 60 ≠ 右栏 83`。报红。PASS |
| 曲目票夹 | open，position fixed，z-index 100，background `rgba(44, 62, 80, 0.45)`，1122×808，`elementFromPoint` 命中 `pkFolioModal` | 高 = iframe 808。宽 1122 是画布文档 client 宽（竖向滚动条占掉约 11px，iframe 宽 1133）。遮罩样式未改 |

## 和规格举例的差（有意）

- 规格表把 1133 档写成 H=559、仪表盘 315、卧卡 232。本机高窗票卡自然高是 775.7，所以仪表盘是 439、卧卡是 325。比例仍是 370/654，闭环仍是 H。宿主降到 744 高时 H 落到 579.3，不是回到 559。
- 组合 2 溢出实测 177，不是表里的 189。宽度保持 A430 / S76 / R360，没有为了凑 189 加宽。
- 654 档举例用 gap 16 得到卧卡 268。实现间隙是 12，所以若 H 恰为 654，卧卡是 272。闭环仍是 H。
